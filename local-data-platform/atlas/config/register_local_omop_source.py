#!/usr/bin/env python3
"""Register one LOCAL_OMOP source using the *WebAPI 3.0 admin API*, not raw SQL.

OpenSpec-Change: deploy-local-ohdsi-atlas
Tasks: 2.3/2.4, then gated 4.1. No writes to cdm.* or Kubernetes.
Uses existing dw-atlas Secrets in memory; never prints JWT, DB passwords,
request JSON containing credentials, or patient-level data.
"""
import argparse
import base64
from contextlib import contextmanager
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

CONF = Path(__file__).with_name("local-omop-source.json")
PREFIX = "http://127.0.0.1:18889/WebAPI"
SQL_SHELL = (
    "export PGPASSWORD=\"$POSTGRES_PASSWORD\"; "
    "export PGOPTIONS='-c default_transaction_read_only=on -c statement_timeout=20000 -c lock_timeout=2000'; "
    "exec psql -X -q -A -t -F '|' -v ON_ERROR_STOP=1 -U omop_admin -d omop"
)

def safe_run(args, *, stdin=None, timeout=35):
    try:
        r = subprocess.run(args, input=stdin, text=True, capture_output=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired):
        raise RuntimeError("LOCAL_SOURCE_K8S_OPERATION_FAILED") from None
    if r.returncode:
        raise RuntimeError("LOCAL_SOURCE_K8S_OPERATION_FAILED") from None
    return r.stdout

def kube_json(*args):
    return json.loads(safe_run(["kubectl", *args, "-o", "json"]))

def read_sql(body):
    assert body.lstrip().startswith("BEGIN TRANSACTION READ ONLY;")
    assert body.rstrip().endswith("ROLLBACK;")
    return safe_run(["kubectl","-n","dw-postgre","exec","-i",
                     "dw-postgre-database-0","--","sh","-c",SQL_SHELL],
                    stdin=body,timeout=45).strip()

def secret(ns, name, user_key, pass_key):
    raw = kube_json("-n",ns,"get","secret",name)
    data = raw["data"]
    assert set((user_key,pass_key)).issubset(data), "SECRET_KEYS_MISSING"
    user = base64.b64decode(data[user_key]).decode()
    password = base64.b64decode(data[pass_key]).decode()
    assert user and password, "SECRET_VALUE_MISSING"
    return user,password

def http(method, route, *, body=None, content_type=None, jwt=None, timeout=30):
    headers={}
    if content_type: headers["Content-Type"]=content_type
    if jwt: headers["Authorization"]="Bearer "+jwt
    req=urllib.request.Request(PREFIX+route,data=body,headers=headers,method=method)
    try:
        with urllib.request.urlopen(req,timeout=timeout) as resp:
            raw=resp.read(1500000)
            return resp.status,json.loads(raw.decode()) if raw else {}
    except urllib.error.HTTPError as exc:
        # No response payload is logged, even on error.
        return exc.code,None
    except (OSError,ValueError):
        raise RuntimeError("LOCAL_SOURCE_HTTP_TRANSPORT_FAILED") from None

@contextmanager
def forward():
    # The port-forward log contains no credentials. Never echo its full contents.
    with tempfile.TemporaryDirectory(prefix="atlas3-source-") as tmp:
        with open(Path(tmp)/"pf.log","wb") as sink:
            proc=subprocess.Popen(["kubectl","-n","dw-atlas","port-forward",
                                   "svc/webapi3","18889:8080"],stdout=sink,stderr=subprocess.STDOUT)
            try:
                ready=False
                for _ in range(25):
                    if proc.poll() is not None:
                        break
                    try:
                        status,_=http("GET","/info",timeout=3)
                        if status==200:
                            ready=True;break
                    except RuntimeError:
                        pass
                    time.sleep(1)
                assert ready, "ATLAS_WEBAPI_PORT_FORWARD_UNAVAILABLE"
                yield
            finally:
                proc.terminate()
                try:proc.wait(timeout=4)
                except subprocess.TimeoutExpired:proc.kill();proc.wait(timeout=4)

def config():
    c=json.loads(CONF.read_text(encoding="utf-8"))
    assert c["change"]=="deploy-local-ohdsi-atlas"
    assert c["source_key"]=="LOCAL_OMOP"
    assert c["dialect"]=="postgresql"
    assert c["connection_string"].startswith("jdbc:postgresql://dw-postgre.dw-postgre.svc.cluster.local:5432/omop")
    assert "password" not in c["connection_string"].lower()
    assert "user=" not in c["connection_string"].lower()
    assert [(d["daimonType"],d["tableQualifier"],d["priority"]) for d in c["daimons"]]==[
        ("CDM","cdm",0),("Vocabulary","cdm",1),
        ("Results","atlas_results",0),("Temp","atlas_temp",0)]
    return c

def preflight(c):
    p=kube_json("-n","dw-postgre","get","pod","dw-postgre-database-0")
    d=kube_json("-n","dw-atlas","get","deployment","webapi3")
    a=kube_json("-n","dw-atlas","get","deployment","atlas3-ui")
    assert p["spec"]["nodeName"]==c["target_node"]
    assert d["status"].get("readyReplicas")==1 and a["status"].get("readyReplicas")==1
    assert d["spec"]["template"]["spec"]["nodeSelector"]["kubernetes.io/hostname"]=="worker03"
    jobs=kube_json("get","jobs","-A").get("items",[])
    assert not any((j.get("status",{}).get("active") or 0)>0
                   and j["metadata"]["namespace"] in ("dw-postgre","dw-atlas")
                   for j in jobs), "DB_OR_ATLAS_JOB_ACTIVE"
    print("ATLAS3_SOURCE_PREFLIGHT=PASS")
    check=read_sql("""BEGIN TRANSACTION READ ONLY;
SELECT 'SRC', source_id, source_key, source_dialect,
       source_connection = '"""+c["connection_string"]+"""',
       username IS NOT NULL AND password IS NOT NULL
 FROM webapi.source WHERE deleted_date IS NULL ORDER BY source_id;
SELECT 'DAIMON', d.daimon_type,d.table_qualifier,d.priority
 FROM webapi.source_daimon d JOIN webapi.source s USING (source_id)
 WHERE s.source_key='LOCAL_OMOP' ORDER BY d.daimon_type;
SELECT 'ROLE_CDM_SELECT',has_table_privilege('atlas_webapi','cdm.person','SELECT');
SELECT 'ROLE_CDM_INSERT',has_table_privilege('atlas_webapi','cdm.person','INSERT');
SELECT 'OBS_COUNT',COUNT(*) FROM cdm.observation_period;
SELECT 'SOURCE_SEQUENCE',to_regclass('webapi.source_sequence') IS NOT NULL;
SELECT 'DAIMON_SEQUENCE',to_regclass('webapi.source_daimon_sequence') IS NOT NULL;
ROLLBACK;""")
    assert "ROLE_CDM_SELECT|t" in check and "ROLE_CDM_INSERT|f" in check, "CDM_WRITE_RISK"
    assert "SOURCE_SEQUENCE|t" in check and "DAIMON_SEQUENCE|t" in check, "SOURCE_SEQUENCES_MISSING"
    assert "OBS_COUNT|0" in check, "OBS_DATA_CHANGED_REINSPECT"
    sources=[x for x in check.splitlines() if x.startswith("SRC|")]
    allowed=not sources or (
        len(sources)==1 and sources[0].split("|")[2:]==["LOCAL_OMOP","postgresql","t","t"]
    )
    assert allowed, "UNEXPECTED_SOURCE_COLLISION"
    daimon=[x for x in check.splitlines() if x.startswith("DAIMON|")]
    if sources:
        expected={"DAIMON|0|cdm|0","DAIMON|1|cdm|1",
                  "DAIMON|2|atlas_results|0","DAIMON|5|atlas_temp|0"}
        assert set(daimon)==expected, "SOURCE_DAIMON_DRIFT"
    return bool(sources)

def multipart_source(c,dbuser,dbpassword):
    # Content-Type application/json on named source part is required for @RequestPart.
    data={
        "name":c["source_name"],"dialect":"postgresql","key":c["source_key"],
        "connectionString":c["connection_string"],
        "username":dbuser,"password":dbpassword,
        "krbAuthMethod":"default", # Required by WebAPI3 getByName; unused for PostgreSQL.
        "checkConnection":True,"daimons":c["daimons"],
    }
    boundary="atlas3source"+uuid.uuid4().hex
    payload=(("--"+boundary+"\r\nContent-Disposition: form-data; name=\"source\"; filename=\"source.json\"\r\n"
              "Content-Type: application/json\r\n\r\n").encode()
             +json.dumps(data,separators=(",",":")).encode()
             +("\r\n--"+boundary+"--\r\n").encode())
    return payload,"multipart/form-data; boundary="+boundary

def verify(c, jwt):
    # Independent SQL transaction proves the actual persisted write.
    state=read_sql("""BEGIN TRANSACTION READ ONLY;
SELECT 'SOURCE',source_id,source_key,source_dialect,
       source_connection = '"""+c["connection_string"]+"""',
       username IS NOT NULL AND password IS NOT NULL
 FROM webapi.source WHERE deleted_date IS NULL;
SELECT 'DAIMON',d.daimon_type,d.table_qualifier,d.priority
 FROM webapi.source_daimon d JOIN webapi.source s USING(source_id)
 WHERE s.source_key='LOCAL_OMOP' ORDER BY d.daimon_type;
SELECT 'CDM_PROTECTED',NOT has_table_privilege('atlas_webapi','cdm.person','INSERT');
ROLLBACK;""")
    rows=[x for x in state.splitlines() if x.startswith("SOURCE|")]
    assert len(rows)==1, "PG_SOURCE_CARDINALITY_MISMATCH"
    fields=rows[0].split("|")
    assert fields[2:]==["LOCAL_OMOP","postgresql","t","t"],"SOURCE_IDENTITY_DRIFT"
    expected={"DAIMON|0|cdm|0","DAIMON|1|cdm|1",
              "DAIMON|2|atlas_results|0","DAIMON|5|atlas_temp|0"}
    assert {x for x in state.splitlines() if x.startswith("DAIMON|")}==expected, "SOURCE_DAIMON_NOT_PERSISTED"
    assert "CDM_PROTECTED|t" in state
    print("WEBAPI_SOURCE_SQL_ID="+fields[1])
    print("WEBAPI_SOURCE_DAIMON_PG17_READBACK=PASS")
    code, sources=http("GET","/source/sources",jwt=jwt)
    assert code==200 and isinstance(sources,list), "SOURCE_GET_FAILED"
    found=[x for x in sources if x.get("sourceKey")==c["source_key"]]
    assert len(found)==1 and int(found[0]["sourceId"])==int(fields[1]), "SOURCE_API_SQL_DISAGREE"
    print("ATLAS3_SOURCE_LIST_API=PASS")
    code,priority=http("GET","/source/priorityVocabulary",jwt=jwt)
    assert code==200 and isinstance(priority,dict) and priority.get("sourceKey")==c["source_key"], "VOCAB_PRIORITY_UNAVAILABLE"
    print("ATLAS3_PRIORITY_VOCABULARY=PASS")
    # Test one reference vocabulary Concept, never patient-level data.
    concept_sql=read_sql("""BEGIN TRANSACTION READ ONLY;
SELECT 'CONCEPT_TEST_ID',concept_id FROM cdm.concept
 WHERE vocabulary_id='Gender' LIMIT 1;
ROLLBACK;""")
    ids=[x.split("|")[1] for x in concept_sql.splitlines() if x.startswith("CONCEPT_TEST_ID|")]
    if not ids:
        print("ATLAS_CONCEPT_TEST=HOLD_NO_GENDER_CONCEPT");return
    cid=int(ids[0])
    code,concept=http("GET",f"/vocabulary/LOCAL_OMOP/concept/{cid}",jwt=jwt)
    print("ATLAS_CONCEPT_GET_HTTP="+str(code))
    print("ATLAS_CONCEPT_GET_BODY_TYPE="+type(concept).__name__)
    if isinstance(concept,dict):
        print("ATLAS_CONCEPT_GET_KEYS="+",".join(sorted(concept.keys())[:18]))
    # v3.0.0 Concept JSON uses uppercase OMOP column names, not camelCase.
    assert code==200 and isinstance(concept,dict) and int(concept.get("CONCEPT_ID",-1))==cid, "CONCEPT_GET_FAILED"
    print("ATLAS_CONCEPT_PG17_HTTP_ID_AGREE=PASS")
    # Use v3 POST SQL-search API with tight Vocabulary filter. The v3 GET
    # search endpoint invokes the index-backed SearchProvider and its first
    # build can time out on the 1.95M-row local Vocabulary; avoid repeating
    # that potentially costly query in the shared PG17 environment.
    payload=json.dumps({"query":"Male","vocabularyId":["Gender"],"isLexical":False}).encode()
    search_code,results=http("POST","/vocabulary/LOCAL_OMOP/search",body=payload,
                             content_type="application/json",jwt=jwt,timeout=25)
    print("ATLAS_CONCEPT_SQL_SEARCH_HTTP="+str(search_code))
    print("ATLAS_CONCEPT_SQL_SEARCH_BODY_TYPE="+type(results).__name__)
    if isinstance(results,list):
        print("ATLAS_CONCEPT_SQL_SEARCH_RESULT_COUNT="+str(len(results)))
    assert search_code==200 and isinstance(results,list) and len(results)>0, "CONCEPT_SQL_SEARCH_FAILED"
    assert all(x.get("VOCABULARY_ID")=="Gender" for x in results), "CONCEPT_SEARCH_VOCABULARY_FILTER_MISMATCH"
    print("ATLAS_CONCEPT_SEARCH_REAL_PG17=PASS")

def main():
    c=config()
    print("ATLAS3_LOCAL_OMOP_REGISTRATION_STATIC=PASS")
    if not arguments.execute:return
    exists=preflight(c)
    user,password=secret(**{"ns":c["login_secret"]["namespace"],
                          "name":c["login_secret"]["name"],
                          "user_key":c["login_secret"]["user_key"],
                          "pass_key":c["login_secret"]["password_key"]})
    assert user=="atlas_admin"
    source_user,source_pw=secret(**{"ns":c["db_secret"]["namespace"],
                                  "name":c["db_secret"]["name"],
                                  "user_key":c["db_secret"]["user_key"],
                                  "pass_key":c["db_secret"]["password_key"]})
    assert source_user=="atlas_webapi"
    with forward():
        body=urllib.parse.urlencode({"login":user,"password":password}).encode()
        code,login=http("POST","/user/login/db",body=body,
                        content_type="application/x-www-form-urlencoded")
        assert code==200 and isinstance(login,dict) and "admin" in login.get("roles",[]),"ADMIN_LOGIN_FAILED"
        jwt=login.get("jwt")
        assert isinstance(jwt,str) and len(jwt)>20,"JWT_INVALID"
        print("WEBAPI_NATIVE_ADMIN_SESSION=PASS")
        code,initial=http("GET","/source/sources",jwt=jwt)
        assert code==200 and isinstance(initial,list),"SOURCE_ADMIN_READ_DENIED"
        print("WEBAPI_SOURCE_INITIAL_COUNT="+str(len(initial)))
        if not exists:
            assert len(initial)==0,"NONEMPTY_SOURCE_LIST_HOLD"
            payload,ct=multipart_source(c,source_user,source_pw)
            code,posted=http("POST","/source",body=payload,content_type=ct,jwt=jwt)
            print("ATLAS_SOURCE_CREATE_HTTP="+str(code))
            assert code==200 and isinstance(posted,dict) and posted.get("sourceKey")=="LOCAL_OMOP","SOURCE_POST_NOT_CONFIRMED_INSPECT_BEFORE_RETRY"
            print("ATLAS_SOURCE_API_REGISTRATION=PASS")
        else:
            print("ATLAS_SOURCE_ALREADY_MATCHES_NO_REPLAY=PASS")
        verify(c,jwt)
    print("OMOP_CDM_DML_DDL=NONE")
    print("ATLAS_RESULTS_AND_TEMP_NO_INITIALIZATION=YES")

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--execute",action="store_true")
    arguments=parser.parse_args()
    try:
        main()
    except (RuntimeError,AssertionError,KeyError,ValueError,IndexError,TypeError) as error:
        # Print only fixed reason labels, never secrets or complete source data.
        print("ATLAS3_SOURCE_HOLD="+str(error),file=sys.stderr)
        sys.exit(2)

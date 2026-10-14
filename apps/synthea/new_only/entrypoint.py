#!/usr/bin/env python3
"""Standalone NEW_ONLY runtime phase router, with explicit fail-closed boundaries.

Business entrypoints remain separate; this router merely selects an operational
phase within the NEW_ONLY product. No UPDATE_ONLY/MIX_DATA implementation.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import re
import subprocess
import sys

RUNTIME=Path("/opt/synthea-new-only")
REQUEST=re.compile(r"^[A-Za-z0-9][A-Za-z0-9-]{7,65}$")
V1=RUNTIME/"csv-contract-v1.json"
V2=RUNTIME/"csv-contract-v2.json"
DEFAULT_SCRATCH="/work"
PHASES=("generate","prepublish","validate","publish","replay","verify")


class RuntimeBlocked(ValueError):
    pass


def command(phase:str, request_id:str, scratch:str=DEFAULT_SCRATCH)->list[str]:
    if phase not in PHASES:
        raise RuntimeBlocked("BLOCKED:UNKNOWN_NEW_ONLY_PHASE")
    if not REQUEST.fullmatch(request_id):
        raise RuntimeBlocked("BLOCKED:INVALID_NEW_ONLY_REQUEST_ID")
    if phase=="generate":
        return [sys.executable,str(RUNTIME/"generate_new_only.py")]
    if phase=="prepublish":
        return [
            sys.executable,str(RUNTIME/"prepublish_gate.py"),
            "--csv-dir",f"/synthea-state/new-only/requests/{request_id}/csv",
            "--contract",str(V2),
            "--batch-id","synthea-new-only-"+request_id,
            "--output",str(Path(scratch)/"prepublish-audit.json"),
            "--scan-s3",
        ]
    if phase=="verify":
        return [
            sys.executable,str(RUNTIME/"verify_v1_ready.py"),
            "--batch-id","synthea-new-only-"+request_id,
            "--request-id",request_id,
        ]
    return [
        sys.executable,str(RUNTIME/"publish_v1_verified.py"),
        "--request-id",request_id,
        "--validator",str(RUNTIME/"validate_generated_synthea_batch.py"),
        "--contract",str(V1),
        "--scratch",scratch,
        "--phase",phase,
    ]


def main()->int:
    p=argparse.ArgumentParser(description="Independent NEW_ONLY generator + Landing lifecycle")
    p.add_argument("--phase",choices=PHASES,default="generate")
    p.add_argument("--request-id",default=os.getenv("GENERATION_REQUEST_ID",""))
    p.add_argument("--scratch",default=DEFAULT_SCRATCH)
    args=p.parse_args()
    try:
        argv=command(args.phase,args.request_id,args.scratch)
        if args.phase=="generate":
            os.environ["GENERATION_REQUEST_ID"]=args.request_id
        elif args.phase=="prepublish":
            Path(args.scratch).mkdir(parents=True,exist_ok=True)
        result=subprocess.run(argv,check=False)
        return result.returncode
    except (RuntimeBlocked,OSError) as exc:
        print("NEW_ONLY_RUNTIME_BLOCKED="+str(exc).split("\n",1)[0],file=sys.stderr)
        return 1


if __name__=="__main__":
    sys.exit(main())

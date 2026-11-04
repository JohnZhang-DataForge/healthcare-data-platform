"""Offline contract for Fabric OMOP management schema. Never runs Fabric SQL."""
import json
import pathlib
import re
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
M=json.loads((ROOT/"manifest.json").read_text())
ALLOWED_TYPE=r"(?:int|bigint|varchar\([0-9]+\)|datetime2\(6\))"

class F1IdentitySchema(unittest.TestCase):
    def test_target_is_exact_existing_warehouse(self):
        self.assertEqual(M["warehouse"],"dw-omop-5.4")
        self.assertEqual(M["warehouse_item_id"],"7a6d08da-278d-4603-8a3b-28640110984c")
        self.assertEqual(M["schemas"],["etl","audit"])

    def test_only_five_reviewed_create_tables(self):
        self.assertEqual(len(M["tables"]),5)
        self.assertEqual(
            sorted(p.name for p in (ROOT/"sql").glob("*.sql")),M["tables"]
        )
        for filename in M["tables"]:
            with self.subTest(filename=filename):
                sql=(ROOT/"sql"/filename).read_text()
                prefix=filename.removesuffix(".sql")
                self.assertTrue(sql.startswith("CREATE TABLE "+prefix+" ("))
                self.assertEqual(sql.count("CREATE TABLE"),1)
                for clause in ("DROP ","TRUNCATE ","INSERT ","DELETE ","MERGE ","UPDATE ","PRIMARY KEY","FOREIGN KEY","UNIQUE"):
                    self.assertNotIn(clause,sql.upper())
                self.assertNotRegex(sql.upper(),r"\bBIGINT\s+IDENTITY\b")
                self.assertTrue(sql.rstrip().endswith(");"))
                columns=re.findall(
                    r"^\s+([a-z][a-z0-9_]*)\s+("+ALLOWED_TYPE+r")\s+(NOT NULL|NULL)\s*,?\s*$",
                    sql,re.M|re.I,
                )
                self.assertGreaterEqual(len(columns),4)
                self.assertEqual(len(columns),len([x for x in sql.splitlines()[1:-1] if x.strip()]))
                self.assertEqual(len({x[0] for x in columns}),len(columns))

    def test_source_contract_fields_and_negative_identity_policy(self):
        contract=json.loads((ROOT/"identity-key-v1.json").read_text())
        self.assertEqual(contract["version"],"v1")
        self.assertEqual(contract["id_type"],"int")
        self.assertEqual(contract["min_id"],1)
        self.assertEqual(contract["max_id"],2147483647)
        self.assertEqual(contract["source_key_scope"],["hospital_id","source_system"])
        self.assertEqual(contract["entities"]["PERSON"]["source_id_field"],"source_record_id")
        self.assertEqual(contract["entities"]["VISIT_OCCURRENCE"]["source_id_field"],"source_encounter_id")
        self.assertEqual(contract["entities"]["VISIT_OCCURRENCE"]["source_person_id_field"],"source_person_id")
        self.assertTrue(contract["single_writer_required"])
        self.assertFalse(contract["auto_identity_allowed"])

    def test_int_ids_and_warehouse_global_allocator(self):
        text=(ROOT/"sql"/"etl.identity_map.sql").read_text()
        self.assertIn("omop_id int NOT NULL",text)
        for column in ("entity_type","hospital_id","source_system","source_business_key","first_batch_id"):
            self.assertIn(column+" varchar(",text)
        allocator=(ROOT/"sql"/"etl.id_allocator.sql").read_text()
        self.assertIn("next_omop_id int NOT NULL",allocator)
        self.assertNotIn("hospital_id",allocator)
        ledger=(ROOT/"sql"/"etl.batch_ledger.sql").read_text()
        for field in ("source_manifest_sha256","mapping_profile_sha256","batch_status","committed_at_utc"):
            self.assertIn(field,ledger)

if __name__=="__main__":
    unittest.main()

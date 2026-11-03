"""OHDSI 5.4 source-pinned Fabric Warehouse DDL contract, no network or SQL calls."""
import hashlib
import json
import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
MANIFEST = json.loads((ROOT / "manifest.json").read_text())
UPSTREAM = (ROOT / "upstream" / "OMOPCDM_sql_server_5.4_ddl.sql").read_bytes()
SOURCE_PATTERN = re.compile(
    r"CREATE TABLE @cdmDatabaseSchema\\.([a-z0-9_]+)\\s*\\(([\\s\\S]*?)\\)\\s*;", re.I
)
COLUMN_PATTERN = re.compile(
    r"^\\s*([a-z][a-z0-9_]*)\\s+(integer|datetime|date|float|varchar\\((?:max|\\d+)\\))\\s+(?:NOT\\s+)?NULL\\b",
    re.I | re.M,
)


class CDM54SchemaSource(unittest.TestCase):
    def test_upstream_blob_pinned(self):
        git_object = b"blob " + str(len(UPSTREAM)).encode() + b"\\0" + UPSTREAM
        self.assertEqual(hashlib.sha1(git_object).hexdigest(), MANIFEST["upstream_blob_sha1"])
        self.assertEqual(MANIFEST["upstream_commit"], "b90ae94430e9a266891890a549ac188137fd7f00")

    def test_complete_table_and_column_inventory(self):
        source = UPSTREAM.decode("utf-8")
        matches = list(SOURCE_PATTERN.finditer(source))
        self.assertEqual(len(matches), MANIFEST["table_count"])
        self.assertEqual(len(matches), 39)
        self.assertEqual(sum(len(COLUMN_PATTERN.findall(x.group(2))) for x in matches), 431)
        self.assertEqual([x.group(1).lower() for x in matches], [x["table"] for x in MANIFEST["tables"]])
        self.assertEqual(sorted(p.stem for p in (ROOT / "tables").glob("*.sql")),
                         sorted(x["table"] for x in MANIFEST["tables"]))
        for match, item in zip(matches, MANIFEST["tables"]):
            with self.subTest(table=item["table"]):
                self.assertEqual(len(COLUMN_PATTERN.findall(match.group(2))), item["columns"])
                expected = match.group(0).replace("CREATE TABLE @cdmDatabaseSchema.", "CREATE TABLE cdm.")
                expected = re.sub(r"\\bdatetime\\b", "datetime2(6)", expected, flags=re.I)
                expected = re.sub(r"\\binteger\\b", "int", expected, flags=re.I)
                actual = (ROOT / "tables" / (item["table"] + ".sql")).read_text()
                self.assertEqual(actual, expected + "\\n")
                self.assertNotIn("@cdmDatabaseSchema", actual)
                self.assertFalse(re.search(r"\\bdatetime\\b", actual, flags=re.I))
                self.assertFalse(re.search(r"\\binteger\\b", actual, flags=re.I))
                self.assertNotIn("DROP TABLE", actual.upper())
                self.assertNotIn("INSERT INTO", actual.upper())


if __name__ == "__main__":
    unittest.main()

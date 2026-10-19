"""Offline Fabric supported-connection-types response contract."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from fabric_connection_metadata import inspect_metadata, UnsupportedConnection


def response():
    return {"value": [{
        "type": "ExampleBlobType",
        "creationMethods": [{"name": "ExampleMethod", "parameters": [
            {"name": "endpoint", "dataType": "Text", "required": True},
            {"name": "optional", "dataType": "Text", "required": False},
        ]}],
        "supportedCredentialTypes": ["ServicePrincipal"],
    }]}


def inspect(data=None, credential="ServicePrincipal"):
    return inspect_metadata(response() if data is None else data,
                            connection_type="ExampleBlobType",
                            creation_method="ExampleMethod", credential_type=credential)


class ConnectionMetadataTests(unittest.TestCase):
    def test_supported_metadata_only(self):
        result = inspect()
        self.assertEqual(result["parameters"][0]["name"], "endpoint")
        self.assertFalse(result["tenant_access_verified"])
        self.assertFalse(result["credential_delivery_verified"])
        self.assertFalse(result["terraform_executed"])

    def test_missing_type_or_method_rejected(self):
        with self.assertRaises(UnsupportedConnection):
            inspect_metadata(response(), connection_type="MadeUp",
                             creation_method="ExampleMethod", credential_type="ServicePrincipal")
        with self.assertRaises(UnsupportedConnection):
            inspect_metadata(response(), connection_type="ExampleBlobType",
                             creation_method="MadeUp", credential_type="ServicePrincipal")

    def test_unsupported_credentials_rejected(self):
        with self.assertRaises(UnsupportedConnection):
            inspect(credential="WorkspaceIdentity")
        with self.assertRaises(UnsupportedConnection):
            inspect(credential="Anonymous")

    def test_pagination_fail_closed(self):
        data = response()
        data["continuationToken"] = "next"
        with self.assertRaises(UnsupportedConnection):
            inspect(data)

    def test_duplicate_type_or_parameter_rejected(self):
        data = response()
        data["value"].append(data["value"][0])
        with self.assertRaises(UnsupportedConnection):
            inspect(data)
        data = response()
        data["value"][0]["creationMethods"][0]["parameters"].append(
            {"name": "endpoint", "required": False}
        )
        with self.assertRaises(UnsupportedConnection):
            inspect(data)

    def test_missing_required_flag_rejected(self):
        data = response()
        del data["value"][0]["creationMethods"][0]["parameters"][0]["required"]
        with self.assertRaises(UnsupportedConnection):
            inspect(data)


if __name__ == "__main__":
    unittest.main()

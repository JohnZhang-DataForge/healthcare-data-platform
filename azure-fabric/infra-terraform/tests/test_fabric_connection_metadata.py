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

    def test_parameter_types_and_allowed_values(self):
        data = response()
        data["value"][0]["creationMethods"][0]["parameters"][0]["allowedValues"] = ["a", "b"]
        result = inspect(data)
        self.assertEqual(result["parameters"][0]["allowed_values"], ["a", "b"])
        data["value"][0]["creationMethods"][0]["parameters"][0]["dataType"] = "MadeUp"
        with self.assertRaises(UnsupportedConnection):
            inspect(data)

    def test_malformed_allowed_values(self):
        for invalid in (["a", "a"], [3], "abc"):
            data = response()
            data["value"][0]["creationMethods"][0]["parameters"][0]["allowedValues"] = invalid
            with self.subTest(value=invalid), self.assertRaises(UnsupportedConnection):
                inspect(data)

    def test_user_controlled_code_permission_is_independent(self):
        with self.assertRaises(UnsupportedConnection):
            inspect_metadata(response(), connection_type="ExampleBlobType",
                             creation_method="ExampleMethod",
                             credential_type="ServicePrincipal",
                             user_controlled_code=True)
        data = response()
        data["value"][0]["supportedCredentialTypesForUsageInUserControlledCode"] = [
            "ServicePrincipal"
        ]
        result = inspect_metadata(data, connection_type="ExampleBlobType",
                                  creation_method="ExampleMethod",
                                  credential_type="ServicePrincipal",
                                  user_controlled_code=True)
        self.assertTrue(result["user_controlled_code"])

    def test_actual_azureblobs_response_null_allowed_values(self):
        # Non-sensitive connector metadata observed via the user's Fabric API call;
        # tenant identity is still unverified and is NOT implied by this test.
        data = {"value": [{
            "type": "AzureBlobs",
            "creationMethods": [{
                "name": "AzureBlobs",
                "parameters": [
                    {"name": "account", "dataType": "Text",
                     "required": True, "allowedValues": None},
                    {"name": "domain", "dataType": "Text",
                     "required": True, "allowedValues": None},
                ],
            }],
            "supportedCredentialTypes": [
                "Anonymous", "Key", "OAuth2", "SharedAccessSignature",
                "ServicePrincipal", "WorkspaceIdentity",
            ],
            "supportedCredentialTypesForUsageInUserControlledCode": [
                "Anonymous", "Key", "SharedAccessSignature",
                "ServicePrincipal", "WorkspaceIdentity",
            ],
        }]}
        result = inspect_metadata(
            data, connection_type="AzureBlobs", creation_method="AzureBlobs",
            credential_type="ServicePrincipal", user_controlled_code=True,
        )
        self.assertEqual(
            [p["name"] for p in result["parameters"]], ["account", "domain"]
        )
        self.assertEqual(
            [p["allowed_values"] for p in result["parameters"]], [[], []]
        )
        self.assertFalse(result["tenant_access_verified"])

    def test_missing_required_flag_rejected(self):
        data = response()
        del data["value"][0]["creationMethods"][0]["parameters"][0]["required"]
        with self.assertRaises(UnsupportedConnection):
            inspect(data)


if __name__ == "__main__":
    unittest.main()

"""Pure offline OIE persisted source readback and credential boundaries."""
import os
from pathlib import Path
import tempfile
import sys
import unittest
from unittest.mock import patch
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from apps.clinical_producers.oie_persisted_readback import (
    OIEReadbackBlocked, OIEPersistedMessage, OIEScopedHTTPSClient,
    parse_persisted_source_message, fetch_persisted_readbacks, SERVICE_URL,
    PinnedLeafHTTPSHandler,
)
from apps.clinical_producers.oie_hl7_publisher import SKIP_MARKER

CHANNEL = "69ace705-a675-45f6-b126-a3b22a65212a"
HL7 = b"MSH|^~\\&|synthea|hospital-b|landing|synthetic|20261024131530+0000||ADT^A01^ADT_A01|msg|P|2.5.1\r"


def record(payload=HL7, *, processed="true", status="TRANSFORMED",
           metadata_id="0", msgid="1001", channel=CHANNEL,
           include_source=True, duplicate_source=False):
    root = ET.Element("message")
    ET.SubElement(root, "messageId").text = msgid
    ET.SubElement(root, "channelId").text = channel
    ET.SubElement(root, "processed").text = processed
    if include_source:
        count = 2 if duplicate_source else 1
        for _ in range(count):
            source = ET.SubElement(root, "connectorMessage")
            ET.SubElement(source, "metaDataId").text = metadata_id
            ET.SubElement(source, "status").text = status
            processed_raw = ET.SubElement(source, "processedRaw")
            ET.SubElement(processed_raw, "content").text = payload.decode("utf-8")
    # Encode carriage returns using XML char refs to preserve exact HL7 bytes.
    return ET.tostring(root, encoding="utf-8").replace(b"\r", b"&#13;")


class FakeOIE:
    def __init__(self, records):
        self.records = records
        self.paths = []
    def get(self, path):
        self.paths.append(path)
        return self.records[path]


class ScopedReadbackTests(unittest.TestCase):
    def test_exact_adt_bytes_and_skip_from_source(self):
        for raw, disposition in ((record(), "ADT_A01"),
                                 (record(SKIP_MARKER), "SKIP")):
            with self.subTest(disposition=disposition):
                result = parse_persisted_source_message(
                    raw, channel_id=CHANNEL, message_id="1001",
                    encounter_id="enc-one")
                self.assertEqual(result.disposition, disposition)
                self.assertEqual(result.payload, HL7 if disposition == "ADT_A01"
                                 else SKIP_MARKER)
                self.assertEqual(result.channel_id, CHANNEL)
                self.assertEqual(result.message_id, "1001")

    def test_bounded_explicit_receipts_no_message_history_enumeration(self):
        a=f"/api/channels/{CHANNEL}/messages/1001"
        b=f"/api/channels/{CHANNEL}/messages/1002"
        client=FakeOIE({a:record(),b:record(SKIP_MARKER,msgid="1002")})
        results=fetch_persisted_readbacks(client, channel_id=CHANNEL,
                                         new_request_messages=[
                                             OIEPersistedMessage("enc-one","1001"),
                                             OIEPersistedMessage("enc-two","1002")])
        self.assertEqual(client.paths, [a,b])
        self.assertEqual([x.disposition for x in results], ["ADT_A01","SKIP"])

    def test_invalid_or_duplicate_receipts_fail_before_network(self):
        for recs in (
            [OIEPersistedMessage("enc-one","1001"),
             OIEPersistedMessage("enc-two","1001")],
            [OIEPersistedMessage("enc-one","1001"),
             OIEPersistedMessage("enc-one","1002")],
            [OIEPersistedMessage("enc-one","-1")],
            [OIEPersistedMessage("../bad","1001")],
        ):
            with self.subTest(records=recs):
                fake=FakeOIE({})
                with self.assertRaises(OIEReadbackBlocked):
                    fetch_persisted_readbacks(
                        fake, channel_id=CHANNEL, new_request_messages=recs)
                self.assertEqual(fake.paths, [])

    def test_unprocessed_wrong_channel_or_message_id_is_blocked(self):
        cases=[
            record(processed="false"),record(status="ERROR"),
            record(metadata_id="1"), record(msgid="1002"),
            record(channel="00000000-0000-4000-8000-000000000000"),
            record(include_source=False),record(duplicate_source=True),
            record(b"FHIR JSON instead of HL7"),
            b"<!DOCTYPE message [<!ENTITY x SYSTEM 'file:///etc/passwd'>]><message/>",
            b"not xml",
        ]
        for raw in cases:
            with self.subTest(case=raw[:60]):
                with self.assertRaises(OIEReadbackBlocked):
                    parse_persisted_source_message(raw, channel_id=CHANNEL,
                                                    message_id="1001",
                                                    encounter_id="enc-one")

    def test_transport_failure_is_redacted(self):
        class CredentialLeaker:
            def get(self, path):
                raise RuntimeError("client_secret_DO_NOT_PRINT")
        with self.assertRaisesRegex(OIEReadbackBlocked,
                                    "^OIE_SCOPED_API_READ_FAILED$") as ctx:
            fetch_persisted_readbacks(
                CredentialLeaker(), channel_id=CHANNEL,
                new_request_messages=[OIEPersistedMessage("enc-one","1001")])
        self.assertNotIn("DO_NOT_PRINT",str(ctx.exception))

    def test_internal_leaf_pin_rejects_changed_certificate(self):
        peer = b"x" * 500
        with patch("apps.clinical_producers.oie_persisted_readback.ssl.PEM_cert_to_DER_cert",
                   return_value=peer):
            handler = PinnedLeafHTTPSHandler("synthetic PEM")
        handler._check_peer(peer)
        with self.assertRaisesRegex(OIEReadbackBlocked,
                                    "OIE_INTERNAL_TLS_LEAF_PIN_MISMATCH"):
            handler._check_peer(b"other" * 100)

    def test_explicit_internal_admin_mode_uses_pinned_handler_only(self):
        with tempfile.TemporaryDirectory() as td:
            leaf=Path(td)/"oie-leaf.pem"
            leaf.write_text("synthetic test PEM", encoding="ascii")
            class Response:
                status=200
                def __enter__(self):return self
                def __exit__(self,*args):return False
                def read(self,n):return b"SUCCESS"
            class FakeOpener:
                def open(self,req,timeout):return Response()
            with patch.dict(os.environ, {"OIE_INTERNAL_ADMIN_MODE":"1"}), \\
                 patch("apps.clinical_producers.oie_persisted_readback.PinnedLeafHTTPSHandler") as pin, \\
                 patch("apps.clinical_producers.oie_persisted_readback.build_opener",
                       return_value=FakeOpener()):
                client=OIEScopedHTTPSClient(username="admin",password="synthetic",
                                            ca_file=leaf)
            pin.assert_called_once_with("synthetic test PEM")
            self.assertIsNotNone(client)

    def test_scoped_client_rejects_admin_untrusted_tls_and_broad_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            ca=Path(tmp)/"ca.pem"
            ca.write_text("dummy test CA",encoding="utf-8")
            for username in ("admin","ADMIN","", "a/b"):
                with self.subTest(username=username):
                    with self.assertRaises(OIEReadbackBlocked):
                        OIEScopedHTTPSClient(username=username,
                            password="fake",ca_file=ca)
            class Response:
                status=200
                def __enter__(self):return self
                def __exit__(self,*args):return False
                def read(self,size):return b"SUCCESS"
            class FakeOpener:
                paths=[]
                def open(self,req,timeout):
                    self.paths.append(req.full_url)
                    return Response()
            opener=FakeOpener()
            with patch("apps.clinical_producers.oie_persisted_readback.ssl.create_default_context",
                       return_value=object()),patch(
                "apps.clinical_producers.oie_persisted_readback.build_opener",
                return_value=opener):
                client=OIEScopedHTTPSClient(
                    username="scoped-reader",password="fake-secret",ca_file=ca)
            self.assertEqual(opener.paths,[SERVICE_URL+"/api/users/_login"])
            for path in ("/api/channels", "/api/channels/"+CHANNEL+"/messages",
                         "/api/users", "/api/channels/"+CHANNEL+"/messages/../1001"):
                with self.subTest(path=path):
                    with self.assertRaisesRegex(OIEReadbackBlocked,
                                                "OIE_SCOPED_PATH_NOT_ALLOWED"):
                        client.get(path)
            self.assertEqual(opener.paths,[SERVICE_URL+"/api/users/_login"])


if __name__ == "__main__":
    unittest.main()

"""Azure SDK physical adapter for the existing johnzhang/landing credential.

No container, identity, policy or prefix creation on initialization. Only
explicit per-key conditional creates and leased CAS below _control/processed.
"""
from __future__ import annotations

import re

from blob_batch_ledger import BlobConflict, BlobMissing, LedgerHold, Snapshot

CONTROL = re.compile(
    r"_control/v1/[a-z][a-z0-9-]{2,63}/[a-z][a-z0-9-]{2,63}/"
    r"[A-Za-z0-9][A-Za-z0-9-]{7,65}/"
    r"(?:SILVER_APPROVED|CANDIDATE_APPROVED|GOLD_COMMITTED)/claim\.json\Z")
RECEIPT = re.compile(
    r"processed/v1/[a-z][a-z0-9-]{2,63}/[a-z][a-z0-9-]{2,63}/"
    r"[A-Za-z0-9][A-Za-z0-9-]{7,65}/"
    r"(?:SILVER_APPROVED|CANDIDATE_APPROVED|GOLD_COMMITTED)/"
    r"[0-9a-f]{64}/receipt\.json\Z")
SOURCE = re.compile(
    r"clinical/v1/[a-z][a-z0-9-]{2,63}/[a-z][a-z0-9-]{2,63}/"
    r"[A-Za-z0-9][A-Za-z0-9-]{7,65}/(?:landing-manifest\.json|"
    r"(?:FHIR_R4|HL7_V2)/[^\\x00-\\x1f\\\\?#%]{1,220})\Z")


class AzureBlobBatchBackend:
    """Adapter accepts an existing Azure ContainerClient, never creates one."""

    def __init__(self, container_client, *, account: str = "johnzhang",
                 container: str = "landing"):
        if account != "johnzhang" or container != "landing":
            raise LedgerHold("UNAPPROVED_STORAGE_TARGET")
        self.container = container_client

    @classmethod
    def from_existing_publisher_sp(cls, *, account_url: str, container: str,
                                   tenant_id: str, client_id: str,
                                   client_secret: str) -> "AzureBlobBatchBackend":
        """Reuse the Publisher/SP credential, not the Fabric Reader connection."""
        if account_url != "https://johnzhang.blob.core.windows.net" or container != "landing":
            raise LedgerHold("UNAPPROVED_STORAGE_TARGET")
        if any(not isinstance(x, str) or not x for x in
               (tenant_id, client_id, client_secret)):
            raise LedgerHold("MISSING_PUBLISHER_CREDENTIAL")
        from azure.identity import ClientSecretCredential
        from azure.storage.blob import BlobServiceClient
        auth = ClientSecretCredential(tenant_id, client_id, client_secret)
        service = BlobServiceClient(account_url, credential=auth, retry_total=0)
        return cls(service.get_container_client("landing"))

    @staticmethod
    def _write_key(key: str, *, claim_only: bool = False):
        if not isinstance(key, str) or not (
                CONTROL.fullmatch(key) if claim_only else
                (CONTROL.fullmatch(key) or RECEIPT.fullmatch(key))):
            raise LedgerHold("WRITE_KEY_NOT_ALLOWLISTED")

    @staticmethod
    def _read_key(key: str):
        if not isinstance(key, str) or not (
                SOURCE.fullmatch(key) or CONTROL.fullmatch(key)
                or RECEIPT.fullmatch(key)):
            raise LedgerHold("READ_KEY_NOT_ALLOWLISTED")

    def read(self, key: str) -> Snapshot:
        self._read_key(key)
        if "/../" in key or key.endswith("/..") or "//" in key:
            raise LedgerHold("READ_PATH_TRAVERSAL")
        from azure.core import MatchConditions
        from azure.core.exceptions import ResourceNotFoundError
        blob = self.container.get_blob_client(key)
        try:
            before = blob.get_blob_properties()
            etag = str(before.etag)
            data = blob.download_blob(
                etag=etag, match_condition=MatchConditions.IfNotModified
            ).readall()
            after = blob.get_blob_properties()
        except ResourceNotFoundError:
            raise BlobMissing() from None
        if str(after.etag) != etag:
            raise LedgerHold("READBACK_ETAG_RACE")
        return Snapshot(data, etag)

    def create(self, key: str, data: bytes) -> str:
        self._write_key(key)
        if not isinstance(data, bytes) or not 0 < len(data) <= 262144:
            raise LedgerHold("INVALID_CONTROL_BYTES")
        from azure.core.exceptions import (
            HttpResponseError, ResourceExistsError, ResourceModifiedError)
        from azure.storage.blob import ContentSettings
        blob = self.container.get_blob_client(key)
        try:
            result = blob.upload_blob(
                data, overwrite=False, validate_content=True,
                content_settings=ContentSettings(content_type="application/json"))
        except (ResourceExistsError, ResourceModifiedError):
            raise BlobConflict() from None
        except HttpResponseError as exc:
            if exc.status_code in (409, 412):
                raise BlobConflict() from None
            raise
        etag = result.get("etag") if isinstance(result, dict) else None
        if not isinstance(etag, str) or not etag:
            raise LedgerHold("CREATE_ACK_WITHOUT_ETAG")
        return etag

    def acquire_lease(self, key: str, seconds: int) -> str:
        self._write_key(key, claim_only=True)
        if type(seconds) is not int or not 15 <= seconds <= 60:
            raise LedgerHold("UNBOUNDED_LEASE")
        lease = self.container.get_blob_client(key).acquire_lease(
            lease_duration=seconds)
        if not lease.id:
            raise LedgerHold("LEASE_ACK_WITHOUT_ID")
        return lease.id

    def renew_lease(self, key: str, lease_id: str) -> None:
        self._write_key(key, claim_only=True)
        if not isinstance(lease_id, str) or not lease_id:
            raise LedgerHold("LEASE_ID_REQUIRED")
        from azure.storage.blob import BlobLeaseClient
        BlobLeaseClient(self.container.get_blob_client(key), lease_id=lease_id).renew()

    def cas_control(self, key: str, data: bytes, etag: str, lease_id: str) -> str:
        self._write_key(key, claim_only=True)
        if (not isinstance(data, bytes) or not 0 < len(data) <= 262144
                or not isinstance(etag, str) or not etag
                or not isinstance(lease_id, str) or not lease_id):
            raise LedgerHold("CAS_INPUT_INVALID")
        from azure.core import MatchConditions
        from azure.core.exceptions import (
            HttpResponseError, ResourceExistsError, ResourceModifiedError)
        from azure.storage.blob import ContentSettings
        try:
            result = self.container.get_blob_client(key).upload_blob(
                data, overwrite=True, etag=etag,
                match_condition=MatchConditions.IfNotModified,
                lease=lease_id, validate_content=True,
                content_settings=ContentSettings(content_type="application/json"))
        except (ResourceExistsError, ResourceModifiedError):
            raise BlobConflict() from None
        except HttpResponseError as exc:
            if exc.status_code in (409, 412):
                raise BlobConflict() from None
            raise
        next_etag = result.get("etag") if isinstance(result, dict) else None
        if not isinstance(next_etag, str) or not next_etag:
            raise LedgerHold("CAS_ACK_WITHOUT_ETAG")
        return next_etag

    def release_lease(self, key: str, lease_id: str) -> None:
        self._write_key(key, claim_only=True)
        if not isinstance(lease_id, str) or not lease_id:
            raise LedgerHold("LEASE_ID_REQUIRED")
        from azure.storage.blob import BlobLeaseClient
        BlobLeaseClient(self.container.get_blob_client(key), lease_id=lease_id).release()

    # Deliberately NO delete / copy / move / rename / prefix clear interface.

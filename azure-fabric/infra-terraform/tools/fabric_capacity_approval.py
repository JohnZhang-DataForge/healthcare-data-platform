#!/usr/bin/env python3
"""Offline-only Fabric Capacity billing evidence shape and HOLD gate.

Input is NOT trusted approval. Even a complete evidence record never enables Apply.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re

from fabric_bootstrap_profile import (
    InvalidBootstrapProfile, _fields, _no_duplicate_keys, _uuid, validate,
)

SHA_RE = re.compile(r"^[0-9a-f]{40}$")
REF_RE = re.compile(r"^COST-REVIEW-[A-Z0-9-]{5,64}$")
REVIEWER_RE = re.compile(r"^[A-Za-z0-9._@-]{2,80}$")


def _time(value: object) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise InvalidBootstrapProfile("expected UTC RFC3339 timestamp")
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise InvalidBootstrapProfile("invalid UTC timestamp") from error
    if result.utcoffset() != timezone.utc.utcoffset(result):
        raise InvalidBootstrapProfile("timestamp must be UTC")
    return result


def check_capacity_evidence(profile: object, evidence: object | None = None) -> dict:
    """Check a detached, untrusted record against a validated profile.

    This never authenticates a reviewer or verifies a billing ticket. Only a later
    trusted out-of-band gate may authorize a real paid deployment.
    """
    p = validate(profile)
    if p["capacity_mode"] == "reuse-existing":
        if evidence is not None:
            raise InvalidBootstrapProfile("reuse-existing must not contain creation approval")
        return {
            "status": "CAPACITY_REUSE_REFERENCE_UNVERIFIED",
            "capacity_id": p["capacity_id"],
            "paid_creation_requested": False,
            "paid_creation_authorized": False,
            "cost_review_verified": False,
            "verified": False,
            "terraform_executed": False,
        }

    # A claimed cost review is insufficient; missing evidence is an explicit HOLD.
    if evidence is None:
        return _hold(False)

    e = _fields(evidence, {"schema_version", "request", "review"}, "capacity_evidence")
    if type(e["schema_version"]) is not int or e["schema_version"] != 1:
        raise InvalidBootstrapProfile("invalid evidence version")
    request = _fields(e["request"], {"environment", "fabric_tenant_id",
                                   "subscription_id", "sku", "region",
                                   "estimated_monthly_usd", "monthly_budget_usd",
                                   "source_sha"}, "evidence.request")
    review = _fields(e["review"], {"reference", "reviewer", "approved_on_utc",
                                  "expires_on_utc", "record_uri"}, "evidence.review")
    if (request["environment"] != p["environment"]
            or _uuid(request["fabric_tenant_id"]) != p["fabric_tenant_id"]
            or _uuid(request["subscription_id"]) != profile["capacity"]["subscription_id"]
            or request["sku"] != profile["capacity"]["sku"]
            or request["region"] != profile["capacity"]["region"]
            or type(request["estimated_monthly_usd"]) not in (int, float)
            or type(request["monthly_budget_usd"]) not in (int, float)
            or request["estimated_monthly_usd"] != profile["capacity"]["estimated_monthly_usd"]
            or request["monthly_budget_usd"] != profile["capacity"]["monthly_budget_usd"]):
        raise InvalidBootstrapProfile("evidence request does not match profile")
    if (not isinstance(request["source_sha"], str)
            or not SHA_RE.fullmatch(request["source_sha"])):
        raise InvalidBootstrapProfile("review must be pinned to exact source SHA")
    if review["reference"] != profile["capacity"]["cost_review_reference"]:
        raise InvalidBootstrapProfile("cost review reference mismatch")
    if not isinstance(review["reference"], str) or not REF_RE.fullmatch(review["reference"]):
        raise InvalidBootstrapProfile("invalid review reference")
    if (not isinstance(review["reviewer"], str)
            or not REVIEWER_RE.fullmatch(review["reviewer"])
            or review["reviewer"] == profile["capacity"]["billing_owner"]):
        raise InvalidBootstrapProfile("independent reviewer required")
    approved, expiry = _time(review["approved_on_utc"]), _time(review["expires_on_utc"])
    if expiry <= approved:
        raise InvalidBootstrapProfile("approval expiry must follow approval time")
    uri = review["record_uri"]
    if (not isinstance(uri, str)
            or not re.fullmatch(r"https://[A-Za-z0-9._/-]{8,240}", uri)
            or "example.com" in uri or "localhost" in uri):
        raise InvalidBootstrapProfile("record must identify an external HTTPS review location")
    return _hold(True)


def _hold(shape_pass: bool) -> dict:
    return {
        "status": "HOLD_PAID_CAPACITY_EXTERNAL_APPROVAL",
        "paid_creation_requested": True,
        "cost_evidence_shape_valid": shape_pass,
        "cost_review_verified": False,
        "paid_creation_authorized": False,
        "verified": False,
        "terraform_executed": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", required=True, type=Path)
    parser.add_argument("--review-evidence", type=Path)
    args = parser.parse_args(argv)
    print("#### FABRIC_CAPACITY_APPROVAL_OUTPUT_BEGIN ####")
    try:
        with args.profile.open(encoding="utf-8") as stream:
            profile = json.load(stream, object_pairs_hook=_no_duplicate_keys)
        evidence = None
        if args.review_evidence:
            with args.review_evidence.open(encoding="utf-8") as stream:
                evidence = json.load(stream, object_pairs_hook=_no_duplicate_keys)
        result = check_capacity_evidence(profile, evidence)
    except (OSError, ValueError, TypeError, KeyError):
        print("STATUS=FAIL; offline Capacity evidence rejected")
        print("#### FABRIC_CAPACITY_APPROVAL_OUTPUT_END ####")
        return 2
    print(json.dumps(result, sort_keys=True, indent=2))
    print("#### FABRIC_CAPACITY_APPROVAL_OUTPUT_END ####")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

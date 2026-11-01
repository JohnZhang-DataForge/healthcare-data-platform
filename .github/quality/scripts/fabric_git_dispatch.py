#!/usr/bin/env python3
"""Healthcare main -> private Self-Runner Fabric workflow_dispatch.

Trusted-GitHub-event only. Fixed destination. No Fabric/Azure credentials or
cloud operations in this public repository. Never log the dispatch secret.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import sys
import urllib.error
import urllib.request

SOURCE_REPO = "johnzhang-dataforge/healthcare-data-platform"
DEST_REPO = "JohnZhang-DataForge/Self-Runner"
DEST_WORKFLOW = "fabric-git-auto-update.yml"
URL = ("https://api.github.com/repos/" + DEST_REPO
       + "/actions/workflows/" + DEST_WORKFLOW + "/dispatches")
RUN_PREFIX = "https://github.com/" + DEST_REPO + "/actions/runs/"
SHA = re.compile(r"[a-fA-F0-9]{40}\Z")
MAX_BYTES = 4096


class DispatchHold(Exception):
    """Expected fail-closed status. Never include credentials."""


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        return None


def validate_main_event(env):
    if (str(env.get("GITHUB_REPOSITORY", "")).casefold() != SOURCE_REPO
            or env.get("GITHUB_REF") != "refs/heads/main"
            or env.get("GITHUB_WORKFLOW") != "Healthcare Fabric Git Deploy"
            or env.get("GITHUB_EVENT_NAME") not in ("push", "workflow_dispatch")):
        raise DispatchHold("UNTRUSTED_HEALTHCARE_EVENT")
    sha = env.get("GITHUB_SHA")
    if not isinstance(sha, str) or not SHA.fullmatch(sha):
        raise DispatchHold("TRIGGER_SHA_INVALID")
    return sha.lower()


def dispatch(opener, token, expected_sha):
    if not isinstance(token, str) or not token.strip():
        raise DispatchHold("DISPATCH_TOKEN_NOT_CONFIGURED")
    if not isinstance(expected_sha, str) or not SHA.fullmatch(expected_sha):
        raise DispatchHold("TRIGGER_SHA_INVALID")
    data = json.dumps({
        "ref": "main",
        "inputs": {"expected_healthcare_sha": expected_sha.lower()},
    }, separators=(",", ":")).encode("utf-8")
    request = urllib.request.Request(
        URL,
        data=data,
        method="POST",
        headers={
            "Authorization": "Bearer " + token,
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
            "X-GitHub-Api-Version": "2026-03-10",
        },
    )
    try:
        with opener.open(request, timeout=25) as response:
            if response.status not in (200, 204):
                raise DispatchHold("DISPATCH_UNEXPECTED_HTTP_STATUS")
            raw = response.read(MAX_BYTES + 1)
            if len(raw) > MAX_BYTES:
                raise DispatchHold("DISPATCH_RESPONSE_TOO_LARGE")
            run_url = ""
            if response.status == 200 and raw:
                try:
                    payload = json.loads(raw)
                except (ValueError, UnicodeError):
                    raise DispatchHold("DISPATCH_RESPONSE_INVALID_JSON") from None
                if not isinstance(payload, dict):
                    raise DispatchHold("DISPATCH_RESPONSE_NOT_OBJECT")
                candidate = payload.get("html_url")
                if (isinstance(candidate, str)
                        and candidate.startswith(RUN_PREFIX)
                        and candidate[len(RUN_PREFIX):].isdigit()):
                    run_url = candidate
            return {"outcome": "DISPATCH_ACCEPTED", "sha": expected_sha,
                    "target": DEST_REPO, "run_url": run_url}
    except urllib.error.HTTPError as exc:
        raise DispatchHold("DISPATCH_HTTP_" + str(exc.code)) from None
    except (OSError, TimeoutError):
        # No retries on ambiguous ACK; the Self-Runner periodic fallback can
        # still reconcile this commit without duplicate cloud writes.
        raise DispatchHold("DISPATCH_ACK_UNKNOWN_NO_RETRY") from None


def main():
    report = {"outcome": "HOLD", "destination": DEST_REPO}
    try:
        sha = validate_main_event(os.environ)
        secret = os.environ.get("SELF_RUNNER_WORKFLOW_DISPATCH_TOKEN", "")
        report = dispatch(urllib.request.build_opener(NoRedirect()), secret, sha)
    except DispatchHold as exc:
        report["error_code"] = str(exc)
    except Exception:
        report["error_code"] = "DISPATCH_UNEXPECTED_FAILURE"
    print("FABRIC_DISPATCH_OUTCOME=" + report["outcome"])
    print("FABRIC_DISPATCH_ERROR=" + report.get("error_code", "NONE"))
    if report.get("sha"):
        print("FABRIC_DISPATCH_HEALTHCARE_SHA=" + report["sha"])
    if report.get("run_url"):
        print("FABRIC_DISPATCH_RUN_URL=" + report["run_url"])
    summary = os.environ.get("GITHUB_STEP_SUMMARY", "")
    if summary:
        lines = [
            "### Healthcare Git Native → Fabric",
            "- Dispatch outcome: " + report["outcome"],
            "- Source commit: " + report.get("sha", "NOT_DISPATCHED"),
            "- Destination: private Self-Runner / Fabric Git Auto Update",
            "- Cloud deployment is independently verified by Self-Runner, not by dispatch acceptance.",
        ]
        if report.get("run_url"):
            lines.append("- [View private Runner run](" + report["run_url"] + ")")
        if report.get("error_code"):
            lines.append("- Error: " + report["error_code"])
        Path(summary).open("a", encoding="utf-8").write("\n".join(lines) + "\n")
    return 0 if report["outcome"] == "DISPATCH_ACCEPTED" else 2


if __name__ == "__main__":
    sys.exit(main())

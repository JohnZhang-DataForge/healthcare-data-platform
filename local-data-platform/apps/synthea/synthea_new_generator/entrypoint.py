"""CLI: python -m apps.synthea.synthea_new_generator.entrypoint --request ..."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

from .generator import generate
from .request import GenerationBlocked, load_request


def main() -> int:
    parser = argparse.ArgumentParser(description="Independent parameterized NEW_ONLY generator")
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--state-root", type=Path, default=Path("/synthea-new-generator-state"))
    parser.add_argument("--synthea-jar", type=Path, default=Path(
        os.environ.get("SYNTHEA_JAR", "/opt/synthea/synthea-with-dependencies.jar")))
    args = parser.parse_args()
    try:
        result = generate(args.state_root, load_request(args.request), args.synthea_jar)
    except (GenerationBlocked, OSError, ValueError) as exc:
        print("SYNTHEA_NEW_GENERATOR_BLOCKED=" + str(exc).split("\n", 1)[0], file=sys.stderr)
        return 1
    print(json.dumps({
        "request_id":result["request_id"],
        "status":result["status"],
        "files":len(result["files"]),
        "metrics":result["metrics"],
        "blob_ready":False,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())

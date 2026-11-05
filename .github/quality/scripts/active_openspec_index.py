#!/usr/bin/env python3
"""Read-only, dynamically computed OpenSpec Active Change inventory.

No GitHub API, network, runtime calls, file mutation, or second task database.
The current checkout's active tasks.md files remain the sole task source.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re

# "2.1", "2.1d", "2.1d.2", "0.6" etc., not explanatory checklist bullets.
TASK_LINE = re.compile(
    r"^\s*-\s*\[([ xX])\]\s+(\d+(?:\.\d+)+(?:[a-z])?(?:\.\d+)*)\b\s*(.*)$"
)
ROOT = Path(__file__).resolve().parents[3]


def load_active_changes(repo_root: Path) -> list[dict[str, object]]:
    """Enumerate one level under openspec/changes, explicitly excluding archive."""
    changes = repo_root / "openspec" / "changes"
    if not changes.is_dir():
        raise FileNotFoundError("Missing openspec/changes directory: " + str(changes))
    output: list[dict[str, object]] = []
    for folder in sorted(changes.iterdir(), key=lambda p: p.name):
        if folder.name == "archive" or folder.name.startswith(".") or not folder.is_dir() or folder.is_symlink():
            continue
        task_file = folder / "tasks.md"
        item: dict[str, object] = {
            "change": folder.name,
            "path": f"openspec/changes/{folder.name}/tasks.md",
            "status": "UNKNOWN",
            "open": None,
            "done": None,
            "next": "tasks.md missing or no numbered tasks",
        }
        if task_file.is_file() and not task_file.is_symlink():
            tasks = []
            for line in task_file.read_text(encoding="utf-8").splitlines():
                match = TASK_LINE.match(line)
                if match:
                    tasks.append((match.group(1).lower() == "x", match.group(2), match.group(3).strip()))
            if tasks:
                pending = [(num, detail) for complete, num, detail in tasks if not complete]
                item.update({
                    "status": "OPEN" if pending else "NO_OPEN_TASKS",
                    "open": len(pending),
                    "done": len(tasks) - len(pending),
                    "next": (pending[0][0] + " " + pending[0][1]) if pending else "No unchecked tasks; archive decision still requires review",
                })
        output.append(item)
    return output


def render_markdown(items: list[dict[str, object]]) -> str:
    result = [
        "# Active OpenSpec Changes (generated on demand)",
        "",
        "> Read-only snapshot of the checkout being queried; not a second CURRENT/NEXT authority.",
        "> Task checkboxes in each active `tasks.md` are authoritative; PR/Run/readback verify actual completion.",
        "",
        "| Active Change | OPEN | DONE | First OPEN task / status |",
        "| --- | ---: | ---: | --- |",
    ]
    for item in items:
        change = str(item["change"])
        link = "../../../" + str(item["path"])
        note = str(item["next"]).replace("|", "\\|").replace("\n", " ")
        if len(note) > 130:
            note = note[:127] + "..."
        result.append(
            f"| [{change}]({link}) | {item['open'] if item['open'] is not None else 'UNKNOWN'} "
            f"| {item['done'] if item['done'] is not None else 'UNKNOWN'} | {note} |"
        )
    if not items:
        result.append("| No active changes | 0 | 0 | See archived OpenSpec for history |")
    return "\n".join(result) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=ROOT, help="Git checkout to inspect (read-only)")
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    args = parser.parse_args()
    items = load_active_changes(args.repo_root)
    if args.format == "json":
        print(json.dumps({"active_changes": items}, ensure_ascii=False, indent=2))
    else:
        print(render_markdown(items), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

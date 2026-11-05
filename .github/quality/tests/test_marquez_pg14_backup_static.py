"""Offline contract tests for the development-only Marquez PG14 backup CronJob."""
import pathlib
import re
import subprocess
import textwrap
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[3] / "platform-portal" / "postgres"
MANIFEST = ROOT / "backup" / "marquez-pg14-backup-cronjob.yaml"
DOC = MANIFEST.read_text(encoding="utf-8")


def backup_shell():
    found = re.search(
        r"(?m)^                - \|\n((?:^                  .*\n)+)", DOC
    )
    if not found:
        raise AssertionError("Inline CronJob backup shell not found")
    return textwrap.dedent(found.group(1))


class MarquezPG14BackupContract(unittest.TestCase):
    def test_daily_three_am_new_york_no_overlapping_jobs(self):
        for token in (
            'schedule: "0 3 * * *"',
            "timeZone: America/New_York",
            "concurrencyPolicy: Forbid",
            "backoffLimit: 0",
            "startingDeadlineSeconds: 3600",
            "activeDeadlineSeconds: 900",
        ):
            self.assertIn(token, DOC)

    def test_only_existing_pg14_pvc_on_same_node(self):
        for token in (
            "namespace: dw-postgre14",
            "claimName: dw-postgre14-data",
            "mountPath: /backup",
            "backup_dir=/backup/marquez-backups",
            "podAffinity:",
            "requiredDuringSchedulingIgnoredDuringExecution:",
            "app: dw-postgre14-database",
            "topologyKey: kubernetes.io/hostname",
            "automountServiceAccountToken: false",
            "runAsUser: 999",
            "name: postgres-secret",
        ):
            self.assertIn(token, DOC)
        self.assertNotIn("dw-postgre17", DOC)
        self.assertNotIn("kubectl delete", DOC)
        self.assertNotIn("dbRetention:", DOC)

    def test_logical_dump_and_safe_seven_day_expiration(self):
        shell = backup_shell()
        for token in (
            "umask 077",
            "pg_dump ",
            "--format=custom",
            "--no-password",
            "pg_restore --list",
            "test -s",
            "mv --",
            "-maxdepth 1 -type f -name 'marquez-*.dump'",
            "-mmin +10080 -delete",
            "MARQUEZ_PG14_BACKUP_SUCCESS=PASS",
        ):
            self.assertIn(token, shell)
        self.assertLess(shell.index("pg_dump "), shell.index("pg_restore --list"))
        self.assertLess(shell.index("pg_restore --list"), shell.index("mv --"))
        self.assertLess(shell.index("mv --"), shell.index("find "))
        self.assertNotIn("rm -rf", shell)
        self.assertNotIn("find /backup -", shell)

    def test_embedded_script_has_valid_bash_syntax(self):
        subprocess.run(
            ["bash", "-n"],
            input=backup_shell(),
            text=True,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )


if __name__ == "__main__":
    unittest.main()

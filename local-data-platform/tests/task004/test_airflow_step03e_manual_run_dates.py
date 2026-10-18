import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

DAG = (
    ROOT
    / "airflow/dags/task004_processing_pipeline.py"
)


class Task004AirflowStep03EManualRunDateTests(
    unittest.TestCase
):

    def test_manual_run_dates_use_dag_run_run_after(self):
        source = DAG.read_text(
            encoding="utf-8"
        )

        self.assertIn(
            '"REFERENCE_DATE": '
            '"{{ dag_run.run_after.strftime(\'%Y%m%d\') }}"',
            source,
        )

        self.assertIn(
            '"LANDING_INGEST_DATE": '
            '"{{ dag_run.run_after.strftime(\'%Y-%m-%d\') }}"',
            source,
        )


    def test_logical_date_derived_shortcuts_are_not_used(self):
        source = DAG.read_text(
            encoding="utf-8"
        )

        self.assertNotIn(
            "{{ ds_nodash }}",
            source,
        )

        self.assertNotIn(
            "{{ ds }}",
            source,
        )


if __name__ == "__main__":
    unittest.main()

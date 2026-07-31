import json
import os
from pathlib import Path
import subprocess
import sys


PROJECT_ROOT = Path(__file__).resolve().parent.parent

PIPELINE_FILE = PROJECT_ROOT / "run_pipeline.py"

PIPELINE_SUMMARY_FILE = (
    PROJECT_ROOT
    / "outputs"
    / "reports"
    / "pipeline_summary.json"
)


def run_pipeline_and_read_summary():
    """
    Pipeline'ı bir kez çalıştırır ve oluşan
    pipeline_summary.json dosyasını okur.
    """

    environment = os.environ.copy()
    environment["PYTHONIOENCODING"] = "utf-8"
    environment["PYTHONUTF8"] = "1"

    result = subprocess.run(
        [
            sys.executable,
            str(PIPELINE_FILE)
        ],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=environment,
        timeout=180
    )

    assert result.returncode == 0, (
        "Pipeline çalıştırılırken hata oluştu.\n\n"
        f"Standart çıktı:\n{result.stdout}\n\n"
        f"Hata çıktısı:\n{result.stderr}"
    )

    assert PIPELINE_SUMMARY_FILE.exists(), (
        "Pipeline çalıştıktan sonra pipeline_summary.json "
        "dosyası oluşturulmadı."
    )

    with PIPELINE_SUMMARY_FILE.open(
        mode="r",
        encoding="utf-8"
    ) as summary_file:
        summary = json.load(summary_file)

    assert summary["pipeline_status"] == "success"

    return summary


def test_pipeline_produces_same_record_counts_on_second_run():
    """
    Pipeline aynı ham veriyle art arda iki kez çalıştırıldığında
    kayıt sayılarının değişmediğini doğrular.
    """

    first_summary = run_pipeline_and_read_summary()
    second_summary = run_pipeline_and_read_summary()

    count_fields = [
        "raw_record_count",
        "clean_stop_count",
        "rejected_record_count",
        "unique_route_count",
        "stop_route_relation_count",
        "data_quality_issue_count",
        "valid_coordinate_count",
        "invalid_coordinate_count"
    ]

    first_counts = {
        field: first_summary[field]
        for field in count_fields
    }

    second_counts = {
        field: second_summary[field]
        for field in count_fields
    }

    assert first_counts == second_counts, (
        "Pipeline'ın iki çalıştırmasında kayıt sayıları "
        "birbirinden farklı.\n"
        f"İlk çalışma: {first_counts}\n"
        f"İkinci çalışma: {second_counts}"
    )
from datetime import datetime
from pathlib import Path
import csv
import json
import logging
import os
import sqlite3
import subprocess
import sys
import time


# ============================================================
# PROJE DOSYA YOLLARI
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent

SCRIPTS_DIR = PROJECT_ROOT / "scripts"

DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"

DATABASE_DIR = PROJECT_ROOT / "database"
DATABASE_FILE = DATABASE_DIR / "eshot_analytics.db"

OUTPUTS_DIR = PROJECT_ROOT / "outputs"
LOGS_DIR = OUTPUTS_DIR / "logs"
REPORTS_DIR = OUTPUTS_DIR / "reports"

PIPELINE_SUMMARY_FILE = (
    REPORTS_DIR / "pipeline_summary.json"
)

RAW_DATA_FILE = (
    RAW_DIR / "eshot-otobus-duraklari.csv"
)

REJECTED_ROWS_FILE = (
    PROCESSED_DIR / "rejected_rows.csv"
)


LOGS_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

REPORTS_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# ============================================================
# LOG SİSTEMİ
# ============================================================

def setup_logger() -> tuple[logging.Logger, Path]:
    """
    Hem terminale hem de log dosyasına kayıt yapan
    logger nesnesini oluşturur.
    """

    timestamp = datetime.now().strftime(
        "%Y-%m-%d_%H-%M-%S"
    )

    log_file = (
        LOGS_DIR / f"pipeline_{timestamp}.log"
    )

    logger = logging.getLogger(
        "eshot_pipeline"
    )

    logger.setLevel(
        logging.INFO
    )

    logger.handlers.clear()

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = logging.FileHandler(
        log_file,
        encoding="utf-8",
    )

    file_handler.setFormatter(
        formatter
    )

    console_handler = logging.StreamHandler()

    console_handler.setFormatter(
        formatter
    )

    logger.addHandler(
        file_handler
    )

    logger.addHandler(
        console_handler
    )

    return logger, log_file


# ============================================================
# SCRIPT ÇALIŞTIRMA
# ============================================================

def run_script(
    script_name: str,
    logger: logging.Logger,
) -> float:
    """
    scripts klasöründeki Python dosyasını çalıştırır.

    Script hata verirse pipeline durdurulur.
    """

    script_path = (
        SCRIPTS_DIR / script_name
    )

    if not script_path.exists():
        raise FileNotFoundError(
            f"Script bulunamadı: {script_path}"
        )

    logger.info(
        "-" * 60
    )

    logger.info(
        "Script başlatılıyor: %s",
        script_name,
    )

    start_time = time.perf_counter()

    child_environment = os.environ.copy()

    child_environment[
        "PYTHONIOENCODING"
    ] = "utf-8"

    child_environment[
        "PYTHONUTF8"
    ] = "1"

    result = subprocess.run(
        [
            sys.executable,
            str(script_path),
        ],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=child_environment,
    )

    duration = (
        time.perf_counter()
        - start_time
    )

    if result.stdout.strip():
        logger.info(
            "Script çıktısı:\n%s",
            result.stdout.strip(),
        )

    if result.returncode != 0:
        if result.stderr.strip():
            logger.error(
                "Script hata çıktısı:\n%s",
                result.stderr.strip(),
            )

        raise RuntimeError(
            f"{script_name} başarısız oldu. "
            f"Çıkış kodu: {result.returncode}"
        )

    logger.info(
        "%s başarıyla tamamlandı. Süre: %.2f saniye",
        script_name,
        duration,
    )

    return round(
        duration,
        2,
    )


# ============================================================
# CSV KAYIT SAYISI
# ============================================================

def count_csv_rows(
    file_path: Path,
    delimiter: str = ";",
) -> int:
    """
    CSV dosyasındaki başlık dışındaki veri satırlarını sayar.
    """

    if not file_path.exists():
        return 0

    with file_path.open(
        mode="r",
        encoding="utf-8-sig",
        newline="",
    ) as csv_file:
        reader = csv.reader(
            csv_file,
            delimiter=delimiter,
        )

        next(
            reader,
            None,
        )

        return sum(
            1
            for row in reader
            if row
            and any(
                str(value).strip()
                for value in row
            )
        )


# ============================================================
# VERİTABANI İSTATİSTİKLERİ
# ============================================================

def get_database_statistics() -> dict:
    """
    Pipeline özetinde kullanılacak veritabanı
    istatistiklerini hesaplar.
    """

    if not DATABASE_FILE.exists():
        raise FileNotFoundError(
            "Veritabanı dosyası bulunamadı: "
            f"{DATABASE_FILE}"
        )

    connection = sqlite3.connect(
        DATABASE_FILE
    )

    try:
        cursor = connection.cursor()

        clean_stop_count = cursor.execute(
            "SELECT COUNT(*) FROM stops"
        ).fetchone()[0]

        unique_route_count = cursor.execute(
            "SELECT COUNT(*) FROM routes"
        ).fetchone()[0]

        stop_route_relation_count = (
            cursor.execute(
                "SELECT COUNT(*) FROM stop_routes"
            ).fetchone()[0]
        )

        data_quality_issue_count = (
            cursor.execute(
                """
                SELECT COUNT(*)
                FROM data_quality_issues
                """
            ).fetchone()[0]
        )

        valid_coordinate_count = (
            cursor.execute(
                """
                SELECT COUNT(*)
                FROM stops
                WHERE has_valid_coordinate = 1
                """
            ).fetchone()[0]
        )

        invalid_coordinate_count = (
            cursor.execute(
                """
                SELECT COUNT(*)
                FROM stops
                WHERE has_valid_coordinate = 0
                """
            ).fetchone()[0]
        )

        return {
            "clean_stop_count":
                clean_stop_count,

            "unique_route_count":
                unique_route_count,

            "stop_route_relation_count":
                stop_route_relation_count,

            "data_quality_issue_count":
                data_quality_issue_count,

            "valid_coordinate_count":
                valid_coordinate_count,

            "invalid_coordinate_count":
                invalid_coordinate_count,
        }

    finally:
        connection.close()


# ============================================================
# PIPELINE ÖZET DOSYASI
# ============================================================

def write_pipeline_summary(
    pipeline_status: str,
    started_at: datetime,
    finished_at: datetime,
    script_durations: dict,
    log_file: Path,
    error_message: str | None = None,
) -> dict:
    """
    Pipeline sonucunu pipeline_summary.json dosyasına yazar.
    """

    raw_record_count = count_csv_rows(
        RAW_DATA_FILE,
        delimiter=";",
    )

    rejected_record_count = count_csv_rows(
        REJECTED_ROWS_FILE,
        delimiter=";",
    )

    if (
        pipeline_status == "success"
        and DATABASE_FILE.exists()
    ):
        database_statistics = (
            get_database_statistics()
        )

    else:
        database_statistics = {
            "clean_stop_count": None,
            "unique_route_count": None,
            "stop_route_relation_count": None,
            "data_quality_issue_count": None,
            "valid_coordinate_count": None,
            "invalid_coordinate_count": None,
        }

    total_duration = (
        finished_at
        - started_at
    ).total_seconds()

    summary = {
        "pipeline_status":
            pipeline_status,

        "started_at":
            started_at.isoformat(
                timespec="seconds"
            ),

        "finished_at":
            finished_at.isoformat(
                timespec="seconds"
            ),

        "total_duration_seconds":
            round(
                total_duration,
                2,
            ),

        "raw_record_count":
            raw_record_count,

        "clean_stop_count":
            database_statistics[
                "clean_stop_count"
            ],

        "rejected_record_count":
            rejected_record_count,

        "unique_route_count":
            database_statistics[
                "unique_route_count"
            ],

        "stop_route_relation_count":
            database_statistics[
                "stop_route_relation_count"
            ],

        "data_quality_issue_count":
            database_statistics[
                "data_quality_issue_count"
            ],

        "valid_coordinate_count":
            database_statistics[
                "valid_coordinate_count"
            ],

        "invalid_coordinate_count":
            database_statistics[
                "invalid_coordinate_count"
            ],

        "script_durations_seconds":
            script_durations,

        "log_file":
            str(log_file),

        "error_message":
            error_message,
    }

    with PIPELINE_SUMMARY_FILE.open(
        mode="w",
        encoding="utf-8",
    ) as json_file:
        json.dump(
            summary,
            json_file,
            ensure_ascii=False,
            indent=4,
        )

    return summary


# ============================================================
# ANA PIPELINE
# ============================================================

def main() -> None:
    """
    ESHOT veri pipeline'ını sırasıyla çalıştırır.
    """

    logger, log_file = setup_logger()

    pipeline_started_at = datetime.now()

    script_durations = {}

    logger.info(
        "=" * 60
    )

    logger.info(
        "ESHOT VERİ PIPELINE'I BAŞLATILDI"
    )

    logger.info(
        "=" * 60
    )

    logger.info(
        "Proje klasörü: %s",
        PROJECT_ROOT,
    )

    logger.info(
        "Script klasörü: %s",
        SCRIPTS_DIR,
    )

    logger.info(
        "Rapor klasörü: %s",
        REPORTS_DIR,
    )

    logger.info(
        "Log dosyası: %s",
        log_file,
    )

    try:
        # 1. Veri temizleme
        script_durations[
            "clean_data"
        ] = run_script(
            "clean_data.py",
            logger,
        )

        # 2. Veritabanı oluşturma
        script_durations[
            "build_database"
        ] = run_script(
            "build_database.py",
            logger,
        )

        # 3. Temel SQL analizi
        script_durations[
            "sql_analysis"
        ] = run_script(
            "run_analysis.py",
            logger,
        )

        # 4. Gelişmiş SQL analizi
        script_durations[
            "advanced_sql_analysis"
        ] = run_script(
            "run_advanced_analysis.py",
            logger,
        )

        # 5. Hat bağlantı analizi
        script_durations[
            "route_network_analysis"
        ] = run_script(
            "network_analysis.py",
            logger,
        )

        # 6. NetworkX tabanlı kapsamlı ağ analizi
        script_durations[
            "network_analysis"
        ] = run_script(
            "run_network_analysis.py",
            logger,
        )

        # 7. Pipeline çıktılarının doğrulanması
        script_durations[
            "pipeline_validation"
        ] = run_script(
            "validate_pipeline.py",
            logger,
        )

        pipeline_finished_at = datetime.now()

        summary = write_pipeline_summary(
            pipeline_status="success",
            started_at=pipeline_started_at,
            finished_at=pipeline_finished_at,
            script_durations=script_durations,
            log_file=log_file,
            error_message=None,
        )

        logger.info(
            "=" * 60
        )

        logger.info(
            "ESHOT VERİ PIPELINE'I BAŞARIYLA TAMAMLANDI"
        )

        logger.info(
            "=" * 60
        )

        logger.info(
            "Ham kayıt sayısı: %s",
            summary["raw_record_count"],
        )

        logger.info(
            "Temiz durak sayısı: %s",
            summary["clean_stop_count"],
        )

        logger.info(
            "Reddedilen kayıt sayısı: %s",
            summary["rejected_record_count"],
        )

        logger.info(
            "Benzersiz hat sayısı: %s",
            summary["unique_route_count"],
        )

        logger.info(
            "Durak-hat ilişkisi sayısı: %s",
            summary[
                "stop_route_relation_count"
            ],
        )

        logger.info(
            "Veri kalitesi sorunu sayısı: %s",
            summary[
                "data_quality_issue_count"
            ],
        )

        logger.info(
            "Geçerli koordinat sayısı: %s",
            summary[
                "valid_coordinate_count"
            ],
        )

        logger.info(
            "Geçersiz koordinat sayısı: %s",
            summary[
                "invalid_coordinate_count"
            ],
        )

        logger.info(
            "Script çalışma süreleri: %s",
            script_durations,
        )

        logger.info(
            "Toplam pipeline süresi: %.2f saniye",
            summary[
                "total_duration_seconds"
            ],
        )

        logger.info(
            "Pipeline özet dosyası: %s",
            PIPELINE_SUMMARY_FILE,
        )

    except Exception as error:
        pipeline_finished_at = datetime.now()

        try:
            write_pipeline_summary(
                pipeline_status="failed",
                started_at=pipeline_started_at,
                finished_at=pipeline_finished_at,
                script_durations=script_durations,
                log_file=log_file,
                error_message=str(error),
            )

        except Exception as summary_error:
            logger.error(
                "Başarısız pipeline özeti "
                "oluşturulamadı: %s",
                summary_error,
            )

        logger.exception(
            "Pipeline başarısız oldu: %s",
            error,
        )

        logger.error(
            "Hata nedeniyle sonraki adımlara geçilmedi."
        )

        raise SystemExit(1)


if __name__ == "__main__":
    main()
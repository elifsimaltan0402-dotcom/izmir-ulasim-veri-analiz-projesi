from __future__ import annotations

import os
import shutil
import sqlite3
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import networkx as nx


# ============================================================
# PROJE YOLLARI VE AYARLAR
# ============================================================

PROJECT_DIR = Path(__file__).resolve().parents[1]

SCRIPTS_DIR = PROJECT_DIR / "scripts"

DATABASE_FILE = (
    PROJECT_DIR
    / "database"
    / "eshot_analytics.db"
)

REPORTS_DIR = (
    PROJECT_DIR
    / "outputs"
    / "reports"
)

CHARTS_DIR = (
    PROJECT_DIR
    / "outputs"
    / "charts"
)

DOCS_DIR = PROJECT_DIR / "docs"

PERFORMANCE_REPORT_FILE = (
    DOCS_DIR
    / "performance_report.md"
)

CLEAN_DATA_SCRIPT = (
    SCRIPTS_DIR
    / "clean_data.py"
)

BUILD_DATABASE_SCRIPT = (
    SCRIPTS_DIR
    / "build_database.py"
)

RUN_ANALYSIS_SCRIPT = (
    SCRIPTS_DIR
    / "run_analysis.py"
)

RUN_ADVANCED_ANALYSIS_SCRIPT = (
    SCRIPTS_DIR
    / "run_advanced_analysis.py"
)

RUN_NETWORK_ANALYSIS_SCRIPT = (
    SCRIPTS_DIR
    / "run_network_analysis.py"
)

REQUIRED_SCRIPTS = [
    CLEAN_DATA_SCRIPT,
    BUILD_DATABASE_SCRIPT,
    RUN_ANALYSIS_SCRIPT,
    RUN_ADVANCED_ANALYSIS_SCRIPT,
    RUN_NETWORK_ANALYSIS_SCRIPT,
]

COUNTED_TABLES = [
    "stops",
    "routes",
    "stop_routes",
    "data_quality_issues",
]

RUN_COUNT = 2


# ============================================================
# YARDIMCI FONKSİYONLAR
# ============================================================

def print_section(title: str) -> None:
    separator = "=" * 72

    print(f"\n{separator}")
    print(title)
    print(separator)


def format_seconds(value: float) -> str:
    return f"{value:.4f}"


def relative_path(path: Path) -> str:
    return str(
        path.relative_to(PROJECT_DIR)
    ).replace("\\", "/")


def validate_required_files() -> None:
    missing = [
        path
        for path in REQUIRED_SCRIPTS
        if not path.is_file()
    ]

    if missing:
        missing_text = "\n".join(
            f"- {relative_path(path)}"
            for path in missing
        )

        raise FileNotFoundError(
            "Performans ölçümü için gerekli scriptler "
            "bulunamadı:\n"
            f"{missing_text}"
        )


def run_script(
    script_path: Path,
    stage_name: str,
) -> float:
    """
    Bir scripti çalıştırır ve geçen süreyi saniye
    olarak döndürür.
    """

    print(f"Başlatıldı: {stage_name}")

    start = time.perf_counter()

    environment = os.environ.copy()

    environment["PYTHONIOENCODING"] = "utf-8"
    environment["PYTHONUTF8"] = "1"

    result = subprocess.run(
        [
            sys.executable,
            str(script_path),
        ],
        cwd=PROJECT_DIR,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=environment,
    )

    elapsed = time.perf_counter() - start

    if result.returncode != 0:
        stdout = (
            result.stdout.strip()
            or "(stdout boş)"
        )

        stderr = (
            result.stderr.strip()
            or "(stderr boş)"
        )

        raise RuntimeError(
            f"{stage_name} başarısız oldu.\n"
            f"Script: {relative_path(script_path)}\n"
            f"Çıkış kodu: {result.returncode}\n\n"
            f"STDOUT:\n{stdout}\n\n"
            f"STDERR:\n{stderr}"
        )

    print(
        f"Tamamlandı: {stage_name} "
        f"({format_seconds(elapsed)} sn)"
    )

    return elapsed


# ============================================================
# RAPOR DOSYALARINI TEMİZLEME VE DOĞRULAMA
# ============================================================

def clear_generated_output_files() -> None:
    """
    Her ölçümden önce yalnızca üretilmiş rapor ve grafik
    dosyalarını siler.

    Böylece dosyaların gerçekten yeniden üretildiği
    doğrulanabilir.
    """

    for directory in (
        REPORTS_DIR,
        CHARTS_DIR,
    ):
        directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        for child in directory.iterdir():
            if child.is_file():
                child.unlink()

            elif child.is_dir():
                shutil.rmtree(child)


def collect_generated_files() -> dict[str, int]:
    """
    Üretilen rapor ve grafik dosyalarının yollarını ve
    dosya boyutlarını döndürür.
    """

    generated: dict[str, int] = {}

    for directory in (
        REPORTS_DIR,
        CHARTS_DIR,
    ):
        if not directory.exists():
            continue

        for file_path in directory.rglob("*"):
            if file_path.is_file():
                generated[
                    relative_path(file_path)
                ] = file_path.stat().st_size

    return dict(
        sorted(generated.items())
    )


def validate_generated_files(
    files: dict[str, int],
) -> None:
    """
    Rapor ve grafik dosyalarının üretildiğini ve boş
    olmadığını doğrular.
    """

    if not files:
        raise AssertionError(
            "outputs/reports ve outputs/charts "
            "klasörlerinde üretilmiş dosya bulunamadı."
        )

    report_files = [
        name
        for name in files
        if name.startswith(
            "outputs/reports/"
        )
    ]

    chart_files = [
        name
        for name in files
        if name.startswith(
            "outputs/charts/"
        )
    ]

    empty_files = [
        name
        for name, size in files.items()
        if size <= 0
    ]

    if not report_files:
        raise AssertionError(
            "Hiçbir rapor dosyası yeniden üretilemedi."
        )

    if not chart_files:
        raise AssertionError(
            "Hiçbir grafik dosyası yeniden üretilemedi."
        )

    if empty_files:
        raise AssertionError(
            "Boş üretilen dosyalar bulundu:\n- "
            + "\n- ".join(empty_files)
        )


def validate_reproducibility(
    run_results: list[dict[str, Any]],
) -> None:
    """
    İki çalıştırmada aynı rapor ve grafik dosyalarının
    üretildiğini doğrular.
    """

    first_files = set(
        run_results[0]["generated_files"]
    )

    second_files = set(
        run_results[1]["generated_files"]
    )

    if first_files != second_files:
        missing_in_second = sorted(
            first_files - second_files
        )

        extra_in_second = sorted(
            second_files - first_files
        )

        details: list[str] = []

        if missing_in_second:
            details.append(
                "İkinci çalıştırmada eksik dosyalar:\n- "
                + "\n- ".join(
                    missing_in_second
                )
            )

        if extra_in_second:
            details.append(
                "Yalnızca ikinci çalıştırmada oluşan "
                "dosyalar:\n- "
                + "\n- ".join(
                    extra_in_second
                )
            )

        raise AssertionError(
            "Rapor ve grafik dosya kümeleri iki "
            "çalıştırmada aynı değil.\n\n"
            + "\n\n".join(details)
        )


# ============================================================
# VERİTABANI DOĞRULAMALARI
# ============================================================

def connect_database() -> sqlite3.Connection:
    """
    SQLite veritabanı bağlantısını oluşturur.
    """

    if not DATABASE_FILE.is_file():
        raise FileNotFoundError(
            "Veritabanı bulunamadı: "
            f"{relative_path(DATABASE_FILE)}"
        )

    connection = sqlite3.connect(
        DATABASE_FILE
    )

    connection.execute(
        "PRAGMA foreign_keys = ON;"
    )

    return connection


def get_existing_tables(
    connection: sqlite3.Connection,
) -> set[str]:
    rows = connection.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table';
        """
    ).fetchall()

    return {
        str(row[0])
        for row in rows
    }


def get_record_counts() -> dict[str, int]:
    """
    Temel tabloların kayıt sayılarını getirir.
    """

    with connect_database() as connection:
        existing_tables = get_existing_tables(
            connection
        )

        missing_tables = [
            name
            for name in COUNTED_TABLES
            if name not in existing_tables
        ]

        if missing_tables:
            raise AssertionError(
                "Veritabanında gerekli tablolar eksik: "
                + ", ".join(missing_tables)
            )

        counts: dict[str, int] = {}

        for table_name in COUNTED_TABLES:
            count = connection.execute(
                f"""
                SELECT COUNT(*)
                FROM "{table_name}";
                """
            ).fetchone()[0]

            counts[table_name] = int(count)

    return counts


def validate_foreign_keys() -> int:
    """
    Veritabanında foreign key hatası bulunmadığını
    doğrular.
    """

    with connect_database() as connection:
        errors = connection.execute(
            "PRAGMA foreign_key_check;"
        ).fetchall()

    if errors:
        preview = "\n".join(
            str(row)
            for row in errors[:10]
        )

        raise AssertionError(
            "Veritabanında foreign key hatası bulundu.\n"
            f"İlk kayıtlar:\n{preview}"
        )

    return 0


def calculate_network_edge_count() -> int:
    """
    stop_routes tablosundan ağ analizinde kullanılan
    iki parçalı grafiği yeniden kurar ve gerçek kenar
    sayısını hesaplar.
    """

    with connect_database() as connection:
        rows = connection.execute(
            """
            SELECT
                stop_id,
                route_number
            FROM stop_routes;
            """
        ).fetchall()

    graph = nx.Graph()

    for stop_id, route_number in rows:
        stop_node = f"stop:{stop_id}"
        route_node = f"route:{route_number}"

        graph.add_node(
            stop_node,
            node_type="stop",
        )

        graph.add_node(
            route_node,
            node_type="route",
        )

        graph.add_edge(
            stop_node,
            route_node,
        )

    return int(
        graph.number_of_edges()
    )


def validate_network_edges(
    record_counts: dict[str, int],
) -> tuple[int, int]:
    """
    Ağ kenar sayısının stop_routes kayıt sayısıyla
    eşleştiğini doğrular.
    """

    network_edge_count = (
        calculate_network_edge_count()
    )

    stop_routes_count = (
        record_counts["stop_routes"]
    )

    if network_edge_count != stop_routes_count:
        raise AssertionError(
            "Ağ kenar sayısı ile stop_routes kayıt "
            "sayısı eşleşmiyor. "
            f"Ağ kenarı: {network_edge_count}, "
            f"stop_routes: {stop_routes_count}"
        )

    return (
        network_edge_count,
        stop_routes_count,
    )


# ============================================================
# TEK PIPELINE ÇALIŞTIRMASI
# ============================================================

def run_pipeline_once(
    run_number: int,
) -> dict[str, Any]:
    """
    Pipeline'ı bir kez çalıştırır, süreleri ölçer ve
    doğrulamaları yapar.
    """

    print_section(
        f"PIPELINE ÇALIŞTIRMA "
        f"{run_number}/{RUN_COUNT}"
    )

    # Eski çıktıları silmek, raporların bu çalıştırmada
    # gerçekten yeniden üretildiğini kanıtlar.
    clear_generated_output_files()

    pipeline_start = time.perf_counter()

    cleaning_time = run_script(
        CLEAN_DATA_SCRIPT,
        "Veri temizleme",
    )

    database_time = run_script(
        BUILD_DATABASE_SCRIPT,
        "Veritabanı oluşturma",
    )

    basic_sql_time = run_script(
        RUN_ANALYSIS_SCRIPT,
        "Temel SQL analizi",
    )

    advanced_sql_time = run_script(
        RUN_ADVANCED_ANALYSIS_SCRIPT,
        "Gelişmiş SQL analizi",
    )

    network_time = run_script(
        RUN_NETWORK_ANALYSIS_SCRIPT,
        "Ağ analizi",
    )

    pipeline_total_time = (
        time.perf_counter()
        - pipeline_start
    )

    sql_analysis_time = (
        basic_sql_time
        + advanced_sql_time
    )

    print_section(
        f"ÇALIŞTIRMA {run_number} "
        "DOĞRULAMALARI"
    )

    record_counts = get_record_counts()

    foreign_key_error_count = (
        validate_foreign_keys()
    )

    (
        network_edge_count,
        stop_routes_count,
    ) = validate_network_edges(
        record_counts
    )

    generated_files = (
        collect_generated_files()
    )

    validate_generated_files(
        generated_files
    )

    print(
        f"Kayıt sayıları: {record_counts}"
    )

    print(
        "Foreign key hata sayısı: "
        f"{foreign_key_error_count}"
    )

    print(
        "Ağ kenar sayısı: "
        f"{network_edge_count}"
    )

    print(
        "stop_routes kayıt sayısı: "
        f"{stop_routes_count}"
    )

    print(
        "Üretilen rapor ve grafik dosyası: "
        f"{len(generated_files)}"
    )

    print(
        "Pipeline toplam süresi: "
        f"{format_seconds(pipeline_total_time)} sn"
    )

    return {
        "run_number": run_number,
        "run_datetime": datetime.now().isoformat(
            timespec="seconds"
        ),
        "cleaning_time": cleaning_time,
        "database_time": database_time,
        "basic_sql_time": basic_sql_time,
        "advanced_sql_time": advanced_sql_time,
        "sql_analysis_time": sql_analysis_time,
        "network_time": network_time,
        "pipeline_total_time": pipeline_total_time,
        "record_counts": record_counts,
        "foreign_key_error_count": (
            foreign_key_error_count
        ),
        "network_edge_count": (
            network_edge_count
        ),
        "stop_routes_count": (
            stop_routes_count
        ),
        "generated_files": generated_files,
    }


# ============================================================
# ÇALIŞTIRMALAR ARASI DOĞRULAMA
# ============================================================

def validate_between_runs(
    run_results: list[dict[str, Any]],
) -> None:
    """
    İki çalıştırmanın sonuçlarını karşılaştırır.
    """

    if len(run_results) < 2:
        raise AssertionError(
            "En az iki ardışık çalıştırma "
            "yapılmalıdır."
        )

    first_counts = (
        run_results[0]["record_counts"]
    )

    for result in run_results[1:]:
        if (
            result["record_counts"]
            != first_counts
        ):
            raise AssertionError(
                "Kayıt sayıları çalıştırmalar "
                "arasında değişti.\n"
                f"1. çalıştırma: {first_counts}\n"
                f"{result['run_number']}. çalıştırma: "
                f"{result['record_counts']}"
            )

    validate_reproducibility(
        run_results
    )

    for result in run_results:
        if (
            result[
                "foreign_key_error_count"
            ]
            != 0
        ):
            raise AssertionError(
                "Foreign key doğrulaması başarısız."
            )

        if (
            result["network_edge_count"]
            != result["stop_routes_count"]
        ):
            raise AssertionError(
                "Ağ kenarı doğrulaması başarısız."
            )


# ============================================================
# MARKDOWN RAPORU
# ============================================================

def average(
    run_results: list[dict[str, Any]],
    field_name: str,
) -> float:
    values = [
        float(result[field_name])
        for result in run_results
    ]

    return sum(values) / len(values)


def build_markdown_report(
    run_results: list[dict[str, Any]],
) -> str:
    """
    Performans ve doğrulama sonuçlarını Markdown
    raporuna dönüştürür.
    """

    generated_at = datetime.now().strftime(
        "%d.%m.%Y %H:%M:%S"
    )

    first_file_names = sorted(
        run_results[0]["generated_files"]
    )

    stages = [
        (
            "Veri temizleme",
            "cleaning_time",
        ),
        (
            "Veritabanı oluşturma",
            "database_time",
        ),
        (
            "SQL analizleri",
            "sql_analysis_time",
        ),
        (
            "Ağ analizi",
            "network_time",
        ),
        (
            "Pipeline toplam süresi",
            "pipeline_total_time",
        ),
    ]

    lines = [
        "# ESHOT Performans ve Doğrulama Raporu",
        "",
        "## 1. Amaç",
        "",
        (
            "Bu rapor, ESHOT veri analizi pipeline'ının "
            "çalışma sürelerini ölçmek ve ardışık "
            "çalıştırmalarda veri bütünlüğü ile çıktıların "
            "yeniden üretilebilirliğini doğrulamak "
            "amacıyla hazırlanmıştır."
        ),
        "",
        (
            f"**Rapor oluşturma zamanı:** "
            f"{generated_at}"
        ),
        (
            f"**Ardışık çalıştırma sayısı:** "
            f"{len(run_results)}"
        ),
        "",
        "## 2. Performans Sonuçları",
        "",
        (
            "| Aşama | 1. çalıştırma (sn) | "
            "2. çalıştırma (sn) | Ortalama (sn) |"
        ),
        "|---|---:|---:|---:|",
    ]

    for stage_name, field_name in stages:
        lines.append(
            f"| {stage_name} "
            f"| {format_seconds(run_results[0][field_name])} "
            f"| {format_seconds(run_results[1][field_name])} "
            f"| {format_seconds(average(run_results, field_name))} |"
        )

    lines.extend(
        [
            "",
            "### SQL analizi ayrıntısı",
            "",
            (
                "| Çalıştırma | Temel SQL (sn) | "
                "Gelişmiş SQL (sn) | Toplam SQL (sn) |"
            ),
            "|---:|---:|---:|---:|",
        ]
    )

    for result in run_results:
        lines.append(
            f"| {result['run_number']} "
            f"| {format_seconds(result['basic_sql_time'])} "
            f"| {format_seconds(result['advanced_sql_time'])} "
            f"| {format_seconds(result['sql_analysis_time'])} |"
        )

    lines.extend(
        [
            "",
            "## 3. Kayıt Sayısı Tutarlılığı",
            "",
            (
                "| Tablo | 1. çalıştırma | "
                "2. çalıştırma | Değişmedi mi? |"
            ),
            "|---|---:|---:|:---:|",
        ]
    )

    for table_name in COUNTED_TABLES:
        first_value = (
            run_results[0][
                "record_counts"
            ][table_name]
        )

        second_value = (
            run_results[1][
                "record_counts"
            ][table_name]
        )

        status = (
            "✅"
            if first_value == second_value
            else "❌"
        )

        lines.append(
            f"| `{table_name}` "
            f"| {first_value} "
            f"| {second_value} "
            f"| {status} |"
        )

    lines.extend(
        [
            "",
            (
                "**Sonuç:** Kayıt sayıları iki "
                "çalıştırmada da değişmemiştir. ✅"
            ),
            "",
            "## 4. Raporların Yeniden Üretilebilirliği",
            "",
            (
                "Her çalıştırmadan önce "
                "`outputs/reports` ve `outputs/charts` "
                "altındaki eski üretilmiş dosyalar "
                "silinmiş, ardından analiz scriptleri "
                "çalıştırılmıştır. Böylece dosyaların "
                "korunması değil, gerçekten yeniden "
                "oluşturulması doğrulanmıştır."
            ),
            "",
            (
                "- 1. çalıştırmada üretilen dosya "
                f"sayısı: **{len(run_results[0]['generated_files'])}**"
            ),
            (
                "- 2. çalıştırmada üretilen dosya "
                f"sayısı: **{len(run_results[1]['generated_files'])}**"
            ),
            (
                "- İki çalıştırmada üretilen dosya "
                "kümeleri aynıdır: **Evet ✅**"
            ),
            (
                "- Üretilen dosyaların tamamı boş "
                "değildir: **Evet ✅**"
            ),
            "",
            "### Yeniden üretilen dosyalar",
            "",
        ]
    )

    lines.extend(
        f"- `{file_name}`"
        for file_name in first_file_names
    )

    lines.extend(
        [
            "",
            "## 5. Foreign Key Doğrulaması",
            "",
            (
                "SQLite `PRAGMA foreign_key_check` "
                "sorgusu her iki çalıştırmadan sonra "
                "uygulanmıştır."
            ),
            "",
            (
                "| Çalıştırma | Foreign key hata "
                "sayısı | Sonuç |"
            ),
            "|---:|---:|:---:|",
        ]
    )

    for result in run_results:
        status = (
            "✅"
            if result[
                "foreign_key_error_count"
            ] == 0
            else "❌"
        )

        lines.append(
            f"| {result['run_number']} "
            f"| {result['foreign_key_error_count']} "
            f"| {status} |"
        )

    lines.extend(
        [
            "",
            (
                "**Sonuç:** Veritabanında foreign key "
                "hatası bulunmamaktadır. ✅"
            ),
            "",
            "## 6. Ağ Kenarı Doğrulaması",
            "",
            (
                "`stop_routes` tablosundaki durak-hat "
                "ilişkileri kullanılarak NetworkX ile "
                "iki parçalı ağ yeniden kurulmuş ve "
                "ağın kenar sayısı tablodaki kayıt "
                "sayısıyla karşılaştırılmıştır."
            ),
            "",
            (
                "| Çalıştırma | Ağ kenar sayısı | "
                "`stop_routes` kayıt sayısı | Eşleşme |"
            ),
            "|---:|---:|---:|:---:|",
        ]
    )

    for result in run_results:
        status = (
            "✅"
            if (
                result["network_edge_count"]
                == result["stop_routes_count"]
            )
            else "❌"
        )

        lines.append(
            f"| {result['run_number']} "
            f"| {result['network_edge_count']} "
            f"| {result['stop_routes_count']} "
            f"| {status} |"
        )

    lines.extend(
        [
            "",
            (
                "**Sonuç:** Ağ kenar sayısı "
                "`stop_routes` kayıt sayısıyla "
                "eşleşmektedir. ✅"
            ),
            "",
            "## 7. Genel Sonuç",
            "",
            (
                "Pipeline iki kez ardışık olarak "
                "başarıyla çalıştırılmıştır. Veri "
                "temizleme, veritabanı oluşturma, SQL "
                "analizi, ağ analizi ve toplam pipeline "
                "süreleri ölçülmüştür. Kayıt sayılarının "
                "sabit kaldığı, rapor ve grafiklerin "
                "yeniden üretilebildiği, foreign key "
                "hatası bulunmadığı ve ağ kenar sayısının "
                "`stop_routes` kayıt sayısıyla eşleştiği "
                "doğrulanmıştır."
            ),
            "",
            (
                "**Görev 6 kapsamındaki performans ve "
                "doğrulama kontrolleri başarıyla "
                "tamamlanmıştır.**"
            ),
            "",
        ]
    )

    return "\n".join(lines)


def write_performance_report(
    run_results: list[dict[str, Any]],
) -> None:
    """
    Markdown raporunu docs klasörüne kaydeder.
    """

    DOCS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    PERFORMANCE_REPORT_FILE.write_text(
        build_markdown_report(
            run_results
        ),
        encoding="utf-8",
    )


# ============================================================
# ANA PROGRAM
# ============================================================

def main() -> None:
    print_section(
        "ESHOT PERFORMANS VE DOĞRULAMA"
    )

    validate_required_files()

    run_results: list[
        dict[str, Any]
    ] = []

    for run_number in range(
        1,
        RUN_COUNT + 1,
    ):
        result = run_pipeline_once(
            run_number
        )

        run_results.append(result)

    print_section(
        "ÇALIŞTIRMALAR ARASI DOĞRULAMA"
    )

    validate_between_runs(
        run_results
    )

    write_performance_report(
        run_results
    )

    print(
        "Kayıt sayıları çalıştırmalar arasında "
        "değişmedi: BAŞARILI"
    )

    print(
        "Rapor ve grafikler yeniden üretildi: "
        "BAŞARILI"
    )

    print(
        "Foreign key kontrolü: BAŞARILI"
    )

    print(
        "Ağ kenar sayısı kontrolü: BAŞARILI"
    )

    print_section(
        "GÖREV 6 TAMAMLANDI"
    )

    print(
        "Rapor oluşturuldu: "
        f"{relative_path(PERFORMANCE_REPORT_FILE)}"
    )


if __name__ == "__main__":
    main()
from pathlib import Path
import json
import sqlite3


# ============================================================
# PROJE DOSYA YOLLARI
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DATA_DIR = PROJECT_ROOT / "data"
PROCESSED_DIR = DATA_DIR / "processed"

DATABASE_FILE = (
    PROJECT_ROOT
    / "database"
    / "eshot_analytics.db"
)

OUTPUTS_DIR = PROJECT_ROOT / "outputs"
REPORTS_DIR = OUTPUTS_DIR / "reports"
CHARTS_DIR = OUTPUTS_DIR / "charts"

NETWORK_REPORTS_DIR = (
    REPORTS_DIR
    / "network"
)


# ============================================================
# KONTROL EDİLECEK DOSYALAR
# ============================================================

REQUIRED_FILES = [
    PROCESSED_DIR / "stops_clean.csv",
    PROCESSED_DIR / "stop_routes.csv",
    PROCESSED_DIR / "data_quality_issues.csv",

    DATABASE_FILE,

    REPORTS_DIR / "data_quality_summary.csv",
    REPORTS_DIR / "duplicate_stop_names.csv",
    REPORTS_DIR / "route_stop_counts.csv",
    REPORTS_DIR / "stops_with_more_than_five_routes.csv",
    REPORTS_DIR / "top_10_routes.csv",
    REPORTS_DIR / "top_10_stops.csv",

    CHARTS_DIR / "data_quality_summary.png",
    CHARTS_DIR / "top_10_routes.png",
    CHARTS_DIR / "top_10_stops.png",

    NETWORK_REPORTS_DIR / "route_connections.csv",
    NETWORK_REPORTS_DIR / "top_network_routes.csv",
    NETWORK_REPORTS_DIR / "network_summary.json",
]

REQUIRED_TABLES = [
    "stops",
    "routes",
    "stop_routes",
    "data_quality_issues",
]


# ============================================================
# DOSYA KONTROLLERİ
# ============================================================

def validate_required_files() -> None:
    """
    Pipeline sonunda oluşması gereken dosyaları kontrol eder.
    """

    missing_files = []
    empty_files = []

    for file_path in REQUIRED_FILES:
        if not file_path.exists():
            missing_files.append(
                str(file_path)
            )

        elif file_path.stat().st_size == 0:
            empty_files.append(
                str(file_path)
            )

    if missing_files:
        missing_text = "\n".join(
            f"- {file_path}"
            for file_path in missing_files
        )

        raise FileNotFoundError(
            "Gerekli çıktı dosyaları bulunamadı:\n"
            f"{missing_text}"
        )

    if empty_files:
        empty_text = "\n".join(
            f"- {file_path}"
            for file_path in empty_files
        )

        raise ValueError(
            "Aşağıdaki çıktı dosyaları boş:\n"
            f"{empty_text}"
        )

    print(
        f"Dosya kontrolü başarılı: "
        f"{len(REQUIRED_FILES)} dosya doğrulandı."
    )


# ============================================================
# VERİTABANI KONTROLLERİ
# ============================================================

def get_table_names(
    connection: sqlite3.Connection,
) -> set[str]:
    """
    Veritabanındaki tablo adlarını döndürür.
    """

    query = """
    SELECT name
    FROM sqlite_master
    WHERE type = 'table'
    """

    rows = connection.execute(
        query
    ).fetchall()

    return {
        row[0]
        for row in rows
    }


def get_table_count(
    connection: sqlite3.Connection,
    table_name: str,
) -> int:
    """
    Belirtilen tablodaki kayıt sayısını döndürür.
    """

    query = (
        f'SELECT COUNT(*) FROM "{table_name}"'
    )

    return connection.execute(
        query
    ).fetchone()[0]


def validate_database() -> dict:
    """
    Veritabanı tablolarını ve temel kayıt sayılarını kontrol eder.
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
        existing_tables = get_table_names(
            connection
        )

        missing_tables = [
            table_name
            for table_name in REQUIRED_TABLES
            if table_name not in existing_tables
        ]

        if missing_tables:
            missing_text = ", ".join(
                missing_tables
            )

            raise ValueError(
                "Veritabanında eksik tablolar var: "
                f"{missing_text}"
            )

        table_counts = {
            table_name: get_table_count(
                connection,
                table_name,
            )
            for table_name in REQUIRED_TABLES
        }

        if table_counts["stops"] <= 0:
            raise ValueError(
                "stops tablosunda kayıt bulunamadı."
            )

        if table_counts["routes"] <= 0:
            raise ValueError(
                "routes tablosunda kayıt bulunamadı."
            )

        if table_counts["stop_routes"] <= 0:
            raise ValueError(
                "stop_routes tablosunda kayıt bulunamadı."
            )

        coordinate_counts = (
            connection.execute(
                """
                SELECT
                    SUM(
                        CASE
                            WHEN has_valid_coordinate = 1
                            THEN 1
                            ELSE 0
                        END
                    ),
                    SUM(
                        CASE
                            WHEN has_valid_coordinate = 0
                            THEN 1
                            ELSE 0
                        END
                    )
                FROM stops
                """
            ).fetchone()
        )

        valid_coordinate_count = (
            coordinate_counts[0] or 0
        )

        invalid_coordinate_count = (
            coordinate_counts[1] or 0
        )

        coordinate_total = (
            valid_coordinate_count
            + invalid_coordinate_count
        )

        if coordinate_total != table_counts["stops"]:
            raise ValueError(
                "Koordinat sayıları ile toplam durak "
                "sayısı birbiriyle uyuşmuyor."
            )

        print(
            "Veritabanı kontrolü başarılı."
        )

        print(
            f"- Durak sayısı: "
            f"{table_counts['stops']}"
        )

        print(
            f"- Hat sayısı: "
            f"{table_counts['routes']}"
        )

        print(
            f"- Durak-hat ilişkisi: "
            f"{table_counts['stop_routes']}"
        )

        print(
            f"- Veri kalitesi sorunu: "
            f"{table_counts['data_quality_issues']}"
        )

        print(
            f"- Geçerli koordinat: "
            f"{valid_coordinate_count}"
        )

        print(
            f"- Geçersiz koordinat: "
            f"{invalid_coordinate_count}"
        )

        return {
            "stop_count":
                table_counts["stops"],
            "route_count":
                table_counts["routes"],
            "stop_route_count":
                table_counts["stop_routes"],
            "data_quality_issue_count":
                table_counts[
                    "data_quality_issues"
                ],
            "valid_coordinate_count":
                valid_coordinate_count,
            "invalid_coordinate_count":
                invalid_coordinate_count,
        }

    finally:
        connection.close()


# ============================================================
# AĞ ANALİZİ KONTROLLERİ
# ============================================================

def validate_network_summary(
    database_statistics: dict,
) -> None:
    """
    Ağ analizi JSON özetini kontrol eder.
    """

    summary_file = (
        NETWORK_REPORTS_DIR
        / "network_summary.json"
    )

    with summary_file.open(
        mode="r",
        encoding="utf-8",
    ) as json_file:
        network_summary = json.load(
            json_file
        )

    required_fields = [
        "route_count",
        "connection_count",
        "max_connected_route",
        "max_connection_degree",
    ]

    missing_fields = [
        field_name
        for field_name in required_fields
        if field_name not in network_summary
    ]

    if missing_fields:
        missing_text = ", ".join(
            missing_fields
        )

        raise ValueError(
            "network_summary.json içinde "
            "eksik alanlar var: "
            f"{missing_text}"
        )

    if (
        network_summary["route_count"]
        != database_statistics["route_count"]
    ):
        raise ValueError(
            "Ağ analizindeki hat sayısı ile "
            "veritabanındaki hat sayısı uyuşmuyor."
        )

    if network_summary["connection_count"] <= 0:
        raise ValueError(
            "Ağ analizinde hat bağlantısı "
            "bulunamadı."
        )

    if network_summary[
        "max_connection_degree"
    ] <= 0:
        raise ValueError(
            "En yüksek bağlantı derecesi "
            "geçersiz."
        )

    print(
        "Ağ analizi kontrolü başarılı."
    )

    print(
        f"- Analiz edilen hat sayısı: "
        f"{network_summary['route_count']}"
    )

    print(
        f"- Hat bağlantısı sayısı: "
        f"{network_summary['connection_count']}"
    )

    print(
        f"- En bağlantılı hat: "
        f"{network_summary['max_connected_route']}"
    )

    print(
        f"- En yüksek bağlantı derecesi: "
        f"{network_summary['max_connection_degree']}"
    )


# ============================================================
# ANA DOĞRULAMA
# ============================================================

def main() -> None:
    """
    Pipeline çıktılarını baştan sona doğrular.
    """

    print("=" * 65)
    print("ESHOT PIPELINE DOĞRULAMA KONTROLLERİ")
    print("=" * 65)

    print(
        "\n1. Gerekli dosyalar kontrol ediliyor..."
    )

    validate_required_files()

    print(
        "\n2. Veritabanı kontrol ediliyor..."
    )

    database_statistics = (
        validate_database()
    )

    print(
        "\n3. Ağ analizi çıktıları "
        "kontrol ediliyor..."
    )

    validate_network_summary(
        database_statistics
    )

    print("\n" + "=" * 65)
    print(
        "TÜM DOĞRULAMA KONTROLLERİ BAŞARIYLA TAMAMLANDI"
    )
    print("=" * 65)


if __name__ == "__main__":
    main()
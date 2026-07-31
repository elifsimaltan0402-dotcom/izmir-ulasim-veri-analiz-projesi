from pathlib import Path
import sqlite3


# ============================================================
# DOSYA YOLLARI
# ============================================================

PROJECT_DIR = Path(__file__).resolve().parents[1]

APP_FILE = PROJECT_DIR / "app.py"

DATABASE_FILE = (
    PROJECT_DIR
    / "database"
    / "eshot_analytics.db"
)


# ============================================================
# YARDIMCI FONKSİYONLAR
# ============================================================

def get_connection():
    """
    Testlerde kullanılmak üzere SQLite bağlantısı oluşturur.
    """

    return sqlite3.connect(DATABASE_FILE)


def read_app_source():
    """
    app.py dosyasının içeriğini UTF-8 olarak okur.
    """

    return APP_FILE.read_text(encoding="utf-8")


# ============================================================
# DOSYA TESTLERİ
# ============================================================

def test_app_file_exists_and_is_not_empty():
    """
    Dashboard dosyasının varlığını ve boş olmadığını kontrol eder.
    """

    assert APP_FILE.exists(), (
        f"Dashboard dosyası bulunamadı: {APP_FILE}"
    )

    assert APP_FILE.stat().st_size > 0, (
        "app.py dosyası boş olmamalıdır."
    )


def test_database_file_exists_and_is_not_empty():
    """
    SQLite veritabanının varlığını ve boş olmadığını kontrol eder.
    """

    assert DATABASE_FILE.exists(), (
        f"Veritabanı bulunamadı: {DATABASE_FILE}"
    )

    assert DATABASE_FILE.stat().st_size > 0, (
        "SQLite veritabanı boş olmamalıdır."
    )


# ============================================================
# DASHBOARD YAPI TESTLERİ
# ============================================================

def test_dashboard_contains_required_tabs():
    """
    Görev 5 kapsamında istenen sekmelerin app.py içinde
    bulunduğunu kontrol eder.
    """

    source = read_app_source()

    required_tabs = [
        "Genel Bakış",
        "Hat Analizi",
        "Aktarma Merkezleri",
        "Hat Çifti Analizi",
        "Veri Kalitesi",
    ]

    for tab_name in required_tabs:
        assert tab_name in source, (
            f"Eksik dashboard sekmesi: {tab_name}"
        )

    assert "st.tabs" in source, (
        "Dashboard sekmeli yapıda olmalıdır."
    )


def test_dashboard_contains_csv_downloads():
    """
    Dashboard'da CSV indirme özelliğinin bulunduğunu kontrol eder.
    """

    source = read_app_source()

    assert "st.download_button" in source, (
        "Dashboard'da CSV indirme butonu bulunmalıdır."
    )

    assert "text/csv" in source, (
        "CSV indirme butonunun MIME türü text/csv olmalıdır."
    )


def test_dashboard_uses_sqlite_data_source():
    """
    Dashboard'un ana analizlerde SQLite kullandığını kontrol eder.
    """

    source = read_app_source()

    assert "sqlite3" in source
    assert "eshot_analytics.db" in source
    assert "pd.read_sql_query" in source

    assert "pd.read_csv" not in source, (
        "Dashboard analizleri ham CSV'den yeniden hesaplamamalıdır."
    )


# ============================================================
# VERİTABANI ŞEMA TESTLERİ
# ============================================================

def test_required_database_tables_exist():
    """
    Dashboard için gerekli temel tabloların varlığını kontrol eder.
    """

    required_tables = {
        "stops",
        "routes",
        "stop_routes",
        "data_quality_issues",
    }

    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table';
            """
        ).fetchall()

    existing_tables = {
        row[0]
        for row in rows
    }

    missing_tables = required_tables - existing_tables

    assert not missing_tables, (
        "Eksik veritabanı tabloları: "
        + ", ".join(sorted(missing_tables))
    )


# ============================================================
# KPI TESTLERİ
# ============================================================

def test_dashboard_kpi_values_are_consistent():
    """
    Dashboard KPI değerlerinin mantıksal olarak tutarlı
    olduğunu kontrol eder.
    """

    with get_connection() as connection:
        total_stops = connection.execute(
            "SELECT COUNT(*) FROM stops;"
        ).fetchone()[0]

        total_routes = connection.execute(
            "SELECT COUNT(*) FROM routes;"
        ).fetchone()[0]

        valid_coordinate_stops = connection.execute(
            """
            SELECT COUNT(*)
            FROM stops
            WHERE has_valid_coordinate = 1;
            """
        ).fetchone()[0]

        quality_issue_count = connection.execute(
            """
            SELECT COUNT(*)
            FROM data_quality_issues;
            """
        ).fetchone()[0]

    assert total_stops > 0
    assert total_routes > 0
    assert 0 <= valid_coordinate_stops <= total_stops
    assert quality_issue_count >= 0


# ============================================================
# HAT ANALİZİ TESTLERİ
# ============================================================

def test_route_analysis_returns_stops():
    """
    En fazla durağı bulunan hattın durak analizinin
    sonuç ürettiğini kontrol eder.
    """

    with get_connection() as connection:
        route = connection.execute(
            """
            SELECT route_number
            FROM stop_routes
            GROUP BY route_number
            ORDER BY COUNT(DISTINCT stop_id) DESC
            LIMIT 1;
            """
        ).fetchone()

        assert route is not None

        route_number = route[0]

        stop_count = connection.execute(
            """
            SELECT COUNT(DISTINCT stop_id)
            FROM stop_routes
            WHERE route_number = ?;
            """,
            (route_number,),
        ).fetchone()[0]

    assert stop_count > 0


def test_shared_route_analysis_returns_valid_results():
    """
    Ortak durak kullanan hat analizinin geçerli sonuç
    ürettiğini kontrol eder.
    """

    with get_connection() as connection:
        result = connection.execute(
            """
            SELECT
                first_route.route_number,
                second_route.route_number,
                COUNT(DISTINCT first_route.stop_id)
                    AS shared_stop_count
            FROM stop_routes AS first_route
            INNER JOIN stop_routes AS second_route
                ON first_route.stop_id = second_route.stop_id
                AND first_route.route_number
                    < second_route.route_number
            GROUP BY
                first_route.route_number,
                second_route.route_number
            ORDER BY shared_stop_count DESC
            LIMIT 1;
            """
        ).fetchone()

    assert result is not None
    assert result[0] != result[1]
    assert result[2] > 0


# ============================================================
# AKTARMA MERKEZİ TESTİ
# ============================================================

def test_transfer_hubs_have_multiple_routes():
    """
    Aktarma merkezi olarak bulunan durakların en az iki
    farklı hatta bağlı olduğunu kontrol eder.
    """

    with get_connection() as connection:
        hubs = connection.execute(
            """
            SELECT
                stop_id,
                COUNT(DISTINCT route_number) AS route_count
            FROM stop_routes
            GROUP BY stop_id
            HAVING COUNT(DISTINCT route_number) >= 2
            ORDER BY route_count DESC
            LIMIT 20;
            """
        ).fetchall()

    assert hubs, (
        "Aktarma merkezi olarak değerlendirilebilecek durak bulunamadı."
    )

    assert all(
        route_count >= 2
        for _, route_count in hubs
    )


# ============================================================
# HAT ÇİFTİ TESTİ
# ============================================================

def test_route_pair_common_stops_are_available():
    """
    En az bir hat çiftinin ortak durağa sahip olduğunu
    kontrol eder.
    """

    with get_connection() as connection:
        route_pair = connection.execute(
            """
            SELECT
                first_route.route_number,
                second_route.route_number
            FROM stop_routes AS first_route
            INNER JOIN stop_routes AS second_route
                ON first_route.stop_id = second_route.stop_id
                AND first_route.route_number
                    < second_route.route_number
            GROUP BY
                first_route.route_number,
                second_route.route_number
            LIMIT 1;
            """
        ).fetchone()

        assert route_pair is not None

        route_1, route_2 = route_pair

        common_stop_count = connection.execute(
            """
            SELECT COUNT(DISTINCT first_route.stop_id)
            FROM stop_routes AS first_route
            INNER JOIN stop_routes AS second_route
                ON first_route.stop_id = second_route.stop_id
            WHERE
                first_route.route_number = ?
                AND second_route.route_number = ?;
            """,
            (route_1, route_2),
        ).fetchone()[0]

    assert common_stop_count > 0


# ============================================================
# VERİ KALİTESİ TESTLERİ
# ============================================================

def test_data_quality_fields_exist():
    """
    Veri kalitesi ekranında gerekli alanları sağlayan
    sütunların bulunduğunu kontrol eder.
    """

    required_columns = {
        "issue_type",
        "raw_value",
        "description",
    }

    with get_connection() as connection:
        rows = connection.execute(
            """
            PRAGMA table_info(data_quality_issues);
            """
        ).fetchall()

    existing_columns = {
        row[1]
        for row in rows
    }

    missing_columns = required_columns - existing_columns

    assert not missing_columns, (
        "data_quality_issues tablosundaki eksik sütunlar: "
        + ", ".join(sorted(missing_columns))
    )


def test_invalid_coordinate_query_is_consistent():
    """
    Geçersiz koordinat sorgusunun toplam durak sayısıyla
    tutarlı olduğunu kontrol eder.
    """

    with get_connection() as connection:
        total_stops = connection.execute(
            "SELECT COUNT(*) FROM stops;"
        ).fetchone()[0]

        invalid_coordinate_count = connection.execute(
            """
            SELECT COUNT(*)
            FROM stops
            WHERE
                has_valid_coordinate = 0
                OR latitude IS NULL
                OR longitude IS NULL;
            """
        ).fetchone()[0]

    assert 0 <= invalid_coordinate_count <= total_stops
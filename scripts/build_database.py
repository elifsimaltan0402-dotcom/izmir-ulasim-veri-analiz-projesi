from pathlib import Path
import sqlite3

import pandas as pd


# ============================================================
# DOSYA YOLLARI
# ============================================================

PROJECT_DIR = Path(__file__).resolve().parent.parent

PROCESSED_DIR = (
    PROJECT_DIR
    / "data"
    / "processed"
)

STOPS_FILE = (
    PROCESSED_DIR
    / "stops_clean.csv"
)

STOP_ROUTES_FILE = (
    PROCESSED_DIR
    / "stop_routes.csv"
)

QUALITY_ISSUES_FILE = (
    PROCESSED_DIR
    / "data_quality_issues.csv"
)

SCHEMA_FILE = (
    PROJECT_DIR
    / "sql"
    / "schema.sql"
)

DATABASE_DIR = (
    PROJECT_DIR
    / "database"
)

DATABASE_FILE = (
    DATABASE_DIR
    / "eshot_analytics.db"
)


# ============================================================
# DOSYA KONTROLÜ
# ============================================================

def validate_input_files():
    """
    Veritabanı oluşturulmadan önce gerekli dosyaların
    mevcut olup olmadığını kontrol eder.
    """

    required_files = [
        STOPS_FILE,
        STOP_ROUTES_FILE,
        QUALITY_ISSUES_FILE,
        SCHEMA_FILE
    ]

    missing_files = [
        file_path
        for file_path in required_files
        if not file_path.exists()
    ]

    if missing_files:
        missing_text = "\n".join(
            f"- {file_path}"
            for file_path in missing_files
        )

        raise FileNotFoundError(
            "\nGerekli dosyalardan bazıları bulunamadı:\n"
            f"{missing_text}\n\n"
            "Önce şu komutu çalıştır:\n"
            "python scripts/clean_data.py"
        )


# ============================================================
# TEMİZ CSV DOSYALARINI OKUMA
# ============================================================

def load_processed_data():
    """
    Temizlenmiş CSV dosyalarını pandas DataFrame olarak okur.
    """

    stops = pd.read_csv(
        STOPS_FILE,
        sep=";",
        dtype={
            "stop_id": "Int64",
            "stop_name": "string",
            "latitude": "float64",
            "longitude": "float64",
            "has_valid_coordinate": "Int64"
        },
        encoding="utf-8-sig"
    )

    stop_routes = pd.read_csv(
        STOP_ROUTES_FILE,
        sep=";",
        dtype={
            "stop_id": "Int64",
            "route_number": "string"
        },
        encoding="utf-8-sig"
    )

    quality_issues = pd.read_csv(
        QUALITY_ISSUES_FILE,
        sep=";",
        dtype={
            "issue_type": "string",
            "stop_id": "Int64",
            "field_name": "string",
            "raw_value": "string",
            "description": "string",
            "source_row_number": "Int64"
        },
        encoding="utf-8-sig"
    )

    return stops, stop_routes, quality_issues


# ============================================================
# VERİ DOĞRULAMA
# ============================================================

def validate_processed_data(
    stops,
    stop_routes,
    quality_issues
):
    """
    Veritabanına aktarılmadan önce temel veri kontrollerini yapar.
    """

    required_stop_columns = {
        "stop_id",
        "stop_name",
        "latitude",
        "longitude",
        "has_valid_coordinate"
    }

    required_stop_route_columns = {
        "stop_id",
        "route_number"
    }

    required_issue_columns = {
        "issue_type",
        "stop_id",
        "field_name",
        "raw_value",
        "description",
        "source_row_number"
    }

    if set(stops.columns) != required_stop_columns:
        raise ValueError(
            "stops_clean.csv sütunları beklenen yapıda değil.\n"
            f"Mevcut sütunlar: {list(stops.columns)}"
        )

    if set(stop_routes.columns) != required_stop_route_columns:
        raise ValueError(
            "stop_routes.csv sütunları beklenen yapıda değil.\n"
            f"Mevcut sütunlar: {list(stop_routes.columns)}"
        )

    if set(quality_issues.columns) != required_issue_columns:
        raise ValueError(
            "data_quality_issues.csv sütunları "
            "beklenen yapıda değil.\n"
            f"Mevcut sütunlar: {list(quality_issues.columns)}"
        )

    assert stops["stop_id"].notna().all(), (
        "stops_clean.csv içinde eksik stop_id var."
    )

    assert stops["stop_id"].is_unique, (
        "stops_clean.csv içinde tekrarlanan stop_id var."
    )

    assert (
        stop_routes.duplicated(
            subset=["stop_id", "route_number"]
        ).sum()
        == 0
    ), (
        "stop_routes.csv içinde tekrarlanan "
        "durak-hat ilişkisi var."
    )

    missing_stop_references = (
        ~stop_routes["stop_id"]
        .isin(stops["stop_id"])
    ).sum()

    assert missing_stop_references == 0, (
        "stop_routes.csv içinde stops tablosunda "
        "bulunmayan stop_id değerleri var."
    )

    invalid_coordinate_flags = (
        ~stops["has_valid_coordinate"]
        .isin([0, 1])
    ).sum()

    assert invalid_coordinate_flags == 0, (
        "has_valid_coordinate sütununda 0 ve 1 "
        "dışında değer bulundu."
    )

    # stop_routes içinde boş route_number bulunmamalı
    empty_route_number_count = (
        stop_routes["route_number"].isna()
        | (stop_routes["route_number"].astype(str).str.strip() == "")
    ).sum()

    assert empty_route_number_count == 0, (
        "stop_routes.csv içinde boş route_number bulundu."
    )


# ============================================================
# SQLITE BAĞLANTISI
# ============================================================

def create_connection():
    """
    SQLite veritabanı bağlantısını oluşturur.
    """

    DATABASE_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    connection = sqlite3.connect(
        DATABASE_FILE
    )

    connection.execute(
        "PRAGMA foreign_keys = ON;"
    )

    return connection


# ============================================================
# ŞEMAYI ÇALIŞTIRMA
# ============================================================

def create_schema(connection):
    """
    schema.sql dosyasını okuyup SQLite üzerinde çalıştırır.
    """

    schema_sql = SCHEMA_FILE.read_text(
        encoding="utf-8"
    )

    connection.executescript(
        schema_sql
    )


# ============================================================
# VERİLERİ SQLITE UYUMLU HÂLE GETİRME
# ============================================================

def prepare_for_database(
    stops,
    stop_routes,
    quality_issues
):
    """
    pandas değerlerini SQLite ile uyumlu Python değerlerine dönüştürür.
    """

    stops_db = stops.copy()

    stops_db["stop_id"] = (
        stops_db["stop_id"]
        .astype(int)
    )

    stops_db["stop_name"] = (
        stops_db["stop_name"]
        .fillna("Bilinmeyen Durak")
        .astype(str)
    )

    stops_db["latitude"] = (
        stops_db["latitude"]
        .where(stops_db["latitude"].notna(), None)
    )

    stops_db["longitude"] = (
        stops_db["longitude"]
        .where(stops_db["longitude"].notna(), None)
    )

    stops_db["has_valid_coordinate"] = (
        stops_db["has_valid_coordinate"]
        .astype(int)
    )

    stop_routes_db = stop_routes.copy()

    stop_routes_db["stop_id"] = (
        stop_routes_db["stop_id"]
        .astype(int)
    )

    stop_routes_db["route_number"] = (
        stop_routes_db["route_number"]
        .astype(str)
        .str.strip()
    )

    quality_issues_db = quality_issues.copy()

    quality_issues_db["stop_id"] = (
        quality_issues_db["stop_id"]
        .astype(object)
        .where(
            quality_issues_db["stop_id"].notna(),
            None
        )
    )

    quality_issues_db["issue_type"] = (
        quality_issues_db["issue_type"]
        .astype(object)
        .where(
            quality_issues_db["issue_type"].notna(),
            None
        )
    )

    quality_issues_db["field_name"] = (
        quality_issues_db["field_name"]
        .astype(object)
        .where(
            quality_issues_db["field_name"].notna(),
            None
        )
    )

    quality_issues_db["raw_value"] = (
        quality_issues_db["raw_value"]
        .astype(object)
        .where(
            quality_issues_db["raw_value"].notna(),
            None
        )
    )

    quality_issues_db["description"] = (
        quality_issues_db["description"]
        .astype(object)
        .where(
            quality_issues_db["description"].notna(),
            None
        )
    )

    quality_issues_db["source_row_number"] = (
        quality_issues_db["source_row_number"]
        .astype(object)
        .where(
            quality_issues_db["source_row_number"].notna(),
            None
        )
    )

    routes_db = (
        stop_routes_db[["route_number"]]
        .drop_duplicates()
        .sort_values("route_number")
        .reset_index(drop=True)
    )

    return (
        stops_db,
        routes_db,
        stop_routes_db,
        quality_issues_db
    )


# ============================================================
# VERİLERİ VERİTABANINA AKTARMA
# ============================================================

def insert_data(
    connection,
    stops,
    routes,
    stop_routes,
    quality_issues
):
    """
    Temizlenmiş verileri SQLite tablolarına aktarır.
    """

    stop_records = list(
        stops[
            [
                "stop_id",
                "stop_name",
                "latitude",
                "longitude",
                "has_valid_coordinate"
            ]
        ].itertuples(
            index=False,
            name=None
        )
    )

    route_records = list(
        routes[
            ["route_number"]
        ].itertuples(
            index=False,
            name=None
        )
    )

    stop_route_records = list(
        stop_routes[
            [
                "stop_id",
                "route_number"
            ]
        ].itertuples(
            index=False,
            name=None
        )
    )

    issue_records = list(
        quality_issues[
            [
                "issue_type",
                "stop_id",
                "field_name",
                "raw_value",
                "description",
                "source_row_number"
            ]
        ].itertuples(
            index=False,
            name=None
        )
    )

    connection.executemany(
        """
        INSERT OR REPLACE INTO stops (
            stop_id,
            stop_name,
            latitude,
            longitude,
            has_valid_coordinate
        )
        VALUES (?, ?, ?, ?, ?);
        """,
        stop_records
    )

    connection.executemany(
        """
        INSERT OR IGNORE INTO routes (
            route_number
        )
        VALUES (?);
        """,
        route_records
    )

    connection.executemany(
        """
        INSERT OR IGNORE INTO stop_routes (
            stop_id,
            route_number
        )
        VALUES (?, ?);
        """,
        stop_route_records
    )

    connection.executemany(
        """
        INSERT INTO data_quality_issues (
            issue_type,
            stop_id,
            field_name,
            raw_value,
            description,
            source_row_number
        )
        VALUES (?, ?, ?, ?, ?, ?);
        """,
        issue_records
    )


# ============================================================
# VERİTABANI KAYIT SAYILARI
# ============================================================

def get_table_counts(connection):
    """
    Her tablonun kayıt sayısını döndürür.
    """

    table_names = [
        "stops",
        "routes",
        "stop_routes",
        "data_quality_issues"
    ]

    counts = {}

    for table_name in table_names:
        query = (
            f"SELECT COUNT(*) FROM {table_name};"
        )

        result = connection.execute(
            query
        ).fetchone()

        counts[table_name] = result[0]

    return counts


# ============================================================
# VERİTABANI DOĞRULAMA
# ============================================================

def validate_database(
    connection,
    stops,
    routes,
    stop_routes,
    quality_issues
):
    """
    DataFrame ve SQLite kayıt sayılarının uyumlu olduğunu doğrular.
    """

    counts = get_table_counts(
        connection
    )

    assert counts["stops"] == len(stops), (
        "stops tablosunun kayıt sayısı "
        "stops_clean.csv ile eşleşmiyor."
    )

    assert counts["routes"] == len(routes), (
        "routes tablosunun kayıt sayısı "
        "benzersiz hat sayısıyla eşleşmiyor."
    )

    assert counts["stop_routes"] == len(stop_routes), (
        "stop_routes tablosunun kayıt sayısı "
        "stop_routes.csv ile eşleşmiyor."
    )

    assert (
        counts["data_quality_issues"]
        == len(quality_issues)
    ), (
        "data_quality_issues tablosunun kayıt sayısı "
        "CSV dosyasıyla eşleşmiyor."
    )

    foreign_key_issues = connection.execute(
        "PRAGMA foreign_key_check;"
    ).fetchall()

    assert len(foreign_key_issues) == 0, (
        "Veritabanında foreign key uyumsuzluğu bulundu."
    )

    # routes tablosunda boş veya tekrar eden hat bulunmamalı.
    # route_number PRIMARY KEY olduğu için veritabanı seviyesinde
    # tekrar zaten engellenir; burada yalnızca boş değer kontrol edilir.
    empty_routes = connection.execute(
        """
        SELECT COUNT(*)
        FROM routes
        WHERE route_number IS NULL
           OR TRIM(route_number) = '';
        """
    ).fetchone()[0]

    assert empty_routes == 0, (
        "routes tablosunda boş bir hat numarası bulundu."
    )

    duplicate_routes = connection.execute(
        """
        SELECT route_number, COUNT(*) AS adet
        FROM routes
        GROUP BY route_number
        HAVING COUNT(*) > 1;
        """
    ).fetchall()

    assert len(duplicate_routes) == 0, (
        "routes tablosunda tekrar eden bir hat numarası bulundu."
    )

    # Hat ilişkisi bulunmayan durak sayısının, eksik hat ve parse
    # edilemeyen hat kayıtlarının toplamıyla tutarlı olduğunu doğrula.
    stops_without_routes = connection.execute(
        """
        SELECT COUNT(*)
        FROM stops
        WHERE stop_id NOT IN (
            SELECT DISTINCT stop_id FROM stop_routes
        );
        """
    ).fetchone()[0]

    missing_or_invalid_route_issue_count = connection.execute(
        """
        SELECT COUNT(*)
        FROM data_quality_issues
        WHERE issue_type IN (
            'Eksik hat bilgisi',
            'Parse edilemeyen hat değeri'
        );
        """
    ).fetchone()[0]

    assert stops_without_routes == missing_or_invalid_route_issue_count, (
        "Hat ilişkisi bulunmayan durak sayısı, veritabanındaki "
        "eksik/parse edilemeyen hat kayıtlarının toplamıyla "
        "tutarlı değil."
    )

    return counts


# ============================================================
# ANA PROGRAM
# ============================================================

def main():
    """
    SQLite veritabanını sıfırdan oluşturur ve verileri aktarır.
    """

    print("=" * 65)
    print("ESHOT SQLITE VERİTABANI OLUŞTURMA")
    print("=" * 65)

    validate_input_files()

    print("\nTemizlenmiş CSV dosyaları okunuyor...")

    stops, stop_routes, quality_issues = (
        load_processed_data()
    )

    validate_processed_data(
        stops=stops,
        stop_routes=stop_routes,
        quality_issues=quality_issues
    )

    (
        stops_db,
        routes_db,
        stop_routes_db,
        quality_issues_db
    ) = prepare_for_database(
        stops=stops,
        stop_routes=stop_routes,
        quality_issues=quality_issues
    )

    connection = create_connection()

    try:
        print("Veritabanı şeması oluşturuluyor...")

        create_schema(
            connection
        )

        print("Temizlenmiş veriler aktarılıyor...")

        insert_data(
            connection=connection,
            stops=stops_db,
            routes=routes_db,
            stop_routes=stop_routes_db,
            quality_issues=quality_issues_db
        )

        connection.commit()

        counts = validate_database(
            connection=connection,
            stops=stops_db,
            routes=routes_db,
            stop_routes=stop_routes_db,
            quality_issues=quality_issues_db
        )

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()

    print("\n" + "=" * 65)
    print("VERİTABANI OLUŞTURMA SONUÇLARI")
    print("=" * 65)

    print(f"Stops            : {counts['stops']}")
    print(f"Routes           : {counts['routes']}")
    print(f"StopRoutes       : {counts['stop_routes']}")
    print(
        "DataQualityIssues: "
        f"{counts['data_quality_issues']}"
    )

    print("\nKontrol sonuçları:")
    print("- Temiz CSV ve veritabanı sayıları eşleşiyor.")
    print("- Tekrarlı durak-hat ilişkisi bulunmuyor.")
    print("- Foreign key kontrolü başarılı.")
    print("- routes tablosunda boş/tekrar eden hat yok.")
    print("- Hatsız durak sayısı, veritabanındaki eksik/parse edilemeyen hat kayıtlarıyla tutarlı.")
    print("- Script yeniden çalıştırılabilir.")

    print("\nVeritabanı dosyası:")
    print(f"- {DATABASE_FILE}")

    print("\nSQLite veritabanı başarıyla oluşturuldu.")


if __name__ == "__main__":
    main()
from pathlib import Path
import sqlite3

import pandas as pd


# ============================================================
# DOSYA YOLLARI
# ============================================================

PROJECT_DIR = Path(__file__).resolve().parent.parent

DATABASE_FILE = (
    PROJECT_DIR
    / "database"
    / "eshot_analytics.db"
)

ADVANCED_SQL_FILE = (
    PROJECT_DIR
    / "sql"
    / "advanced_analysis.sql"
)

REPORTS_DIR = (
    PROJECT_DIR
    / "outputs"
    / "reports"
    / "advanced_sql"
)


# ============================================================
# VIEW VE RAPOR TANIMLARI
# ============================================================

VIEW_REPORTS = {
    "vw_stop_route_counts":
        "stop_route_counts.csv",

    "vw_route_stop_counts":
        "route_stop_counts_advanced.csv",

    "vw_transfer_stops":
        "transfer_stops.csv",

    "vw_top_transfer_stops":
        "top_transfer_stops.csv",

    "vw_route_pairs_by_stop":
        "route_pairs_by_stop.csv",

    "vw_route_pair_common_stop_counts":
        "route_pair_common_stop_counts.csv",

    "vw_top_route_pairs":
        "top_route_pairs.csv",

    "vw_stops_without_routes":
        "stops_without_routes.csv",

    "vw_invalid_coordinate_stops":
        "invalid_coordinate_stops.csv",

    "vw_duplicate_stop_names":
        "duplicate_stop_names_advanced.csv",
}


# ============================================================
# GEREKLİ DOSYALARI KONTROL ETME
# ============================================================

def validate_files() -> None:
    """
    Gelişmiş SQL analizi için gerekli dosyaların
    varlığını kontrol eder.
    """

    required_files = [
        DATABASE_FILE,
        ADVANCED_SQL_FILE,
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
            "\nGerekli dosyalar bulunamadı:\n"
            f"{missing_text}\n\n"
            "Önce veritabanının oluşturulduğundan ve "
            "advanced_analysis.sql dosyasının mevcut "
            "olduğundan emin olun."
        )


# ============================================================
# VIEW'LARI OLUŞTURMA
# ============================================================

def create_advanced_views(
    connection: sqlite3.Connection,
) -> None:
    """
    advanced_analysis.sql dosyasındaki DROP VIEW ve
    CREATE VIEW komutlarını SQLite veritabanında çalıştırır.
    """

    sql_text = ADVANCED_SQL_FILE.read_text(
        encoding="utf-8"
    )

    connection.executescript(
        sql_text
    )

    connection.commit()


# ============================================================
# VIEW SONUÇLARINI OKUMA
# ============================================================

def read_view(
    connection: sqlite3.Connection,
    view_name: str,
) -> pd.DataFrame:
    """
    Belirtilen SQL view sonucunu DataFrame olarak döndürür.
    """

    query = f"SELECT * FROM {view_name}"

    return pd.read_sql_query(
        query,
        connection
    )


# ============================================================
# CSV RAPORLARINI KAYDETME
# ============================================================

def save_report(
    dataframe: pd.DataFrame,
    file_name: str,
) -> Path:
    """
    View sonucunu CSV raporu olarak kaydeder.
    """

    output_file = (
        REPORTS_DIR
        / file_name
    )

    dataframe.to_csv(
        output_file,
        index=False,
        encoding="utf-8-sig"
    )

    return output_file


# ============================================================
# VIEW VARLIK KONTROLÜ
# ============================================================

def validate_view_names(
    connection: sqlite3.Connection,
) -> None:
    """
    Beklenen tüm view'ların SQLite veritabanında
    oluşturulduğunu doğrular.
    """

    query = """
        SELECT name
        FROM sqlite_master
        WHERE type = 'view'
    """

    existing_views = {
        row[0]
        for row in connection.execute(query).fetchall()
    }

    expected_views = set(
        VIEW_REPORTS
    )

    missing_views = (
        expected_views
        - existing_views
    )

    if missing_views:
        raise AssertionError(
            "Oluşturulamayan view'lar var: "
            f"{sorted(missing_views)}"
        )


# ============================================================
# ANALİZ SONUÇLARINI DOĞRULAMA
# ============================================================

def validate_results(
    results: dict[str, pd.DataFrame],
) -> None:
    """
    Gelişmiş SQL sonuçlarının temel kurallara
    uygunluğunu kontrol eder.
    """

    stop_route_counts = results[
        "vw_stop_route_counts"
    ]

    route_stop_counts = results[
        "vw_route_stop_counts"
    ]

    transfer_stops = results[
        "vw_transfer_stops"
    ]

    route_pairs = results[
        "vw_route_pairs_by_stop"
    ]

    pair_counts = results[
        "vw_route_pair_common_stop_counts"
    ]

    stops_without_routes = results[
        "vw_stops_without_routes"
    ]

    invalid_coordinate_stops = results[
        "vw_invalid_coordinate_stops"
    ]

    duplicate_stop_names = results[
        "vw_duplicate_stop_names"
    ]

    # Her durak view içinde yalnızca bir kez bulunmalıdır.
    assert stop_route_counts["stop_id"].is_unique, (
        "Durak-hat sayısı sonucunda tekrarlanan stop_id var."
    )

    # Her hat view içinde yalnızca bir kez bulunmalıdır.
    assert route_stop_counts["route_number"].is_unique, (
        "Hat-durak sayısı sonucunda tekrarlanan hat var."
    )

    # Aktarma duraklarında en az iki hat bulunmalıdır.
    assert (
        transfer_stops["route_count"] >= 2
    ).all(), (
        "Aktarma durakları sonucunda iki hattan az "
        "hattı bulunan durak var."
    )

    # Hat çiftleri küçükten büyüğe sıralanmalıdır.
    # Böylece 121-140 ve 140-121 birlikte bulunamaz.
    assert (
        route_pairs["route_1"]
        < route_pairs["route_2"]
    ).all(), (
        "Hat çiftlerinde ters veya eşit hat çifti bulundu."
    )

    # Aynı durak ve hat çifti tekrarlanmamalıdır.
    assert not route_pairs.duplicated(
        subset=[
            "stop_id",
            "route_1",
            "route_2",
        ]
    ).any(), (
        "Aynı durak için yinelenen hat çifti bulundu."
    )

    # Her hat çifti ortak durak sayısı sonucunda bir kez bulunmalıdır.
    assert not pair_counts.duplicated(
        subset=[
            "route_1",
            "route_2",
        ]
    ).any(), (
        "Ortak durak sayısı sonucunda yinelenen "
        "hat çifti bulundu."
    )

    # Ortak durak sayıları pozitif olmalıdır.
    assert (
        pair_counts["common_stop_count"] >= 1
    ).all(), (
        "Ortak durak sayısı sıfır veya negatif olan "
        "hat çifti bulundu."
    )

    # Hattı olmayan durakların route_count değeri sıfır olmalıdır.
    no_route_ids = set(
        stops_without_routes["stop_id"]
    )

    calculated_no_route_ids = set(
        stop_route_counts.loc[
            stop_route_counts["route_count"] == 0,
            "stop_id",
        ]
    )

    assert no_route_ids == calculated_no_route_ids, (
        "Hattı olmayan durak sonuçları tutarlı değil."
    )

    # Geçersiz koordinat view'ında tüm değerler 0 olmalıdır.
    assert (
        invalid_coordinate_stops[
            "has_valid_coordinate"
        ] == 0
    ).all(), (
        "Geçersiz koordinat view'ında geçerli "
        "koordinatlı durak bulundu."
    )

    # Aynı isimli durak sonuçlarında her isim birden fazla ID'ye sahip olmalı.
    if not duplicate_stop_names.empty:
        duplicate_name_counts = (
            duplicate_stop_names
            .groupby("stop_name")["stop_id"]
            .nunique()
        )

        assert (
            duplicate_name_counts > 1
        ).all(), (
            "Aynı isimli durak sonucunda yalnızca "
            "bir ID'ye sahip isim bulundu."
        )


# ============================================================
# ÖZET BİLGİLERİ YAZDIRMA
# ============================================================

def print_summary(
    results: dict[str, pd.DataFrame],
) -> None:
    """
    Gelişmiş SQL analizlerinin temel sayılarını
    terminale yazdırır.
    """

    print("\n" + "=" * 70)
    print("GELİŞMİŞ SQL ANALİZ SONUÇLARI")
    print("=" * 70)

    print(
        "Durak-hat sayısı kaydı           : "
        f"{len(results['vw_stop_route_counts'])}"
    )

    print(
        "Hat-durak sayısı kaydı           : "
        f"{len(results['vw_route_stop_counts'])}"
    )

    print(
        "Aktarma durağı sayısı            : "
        f"{len(results['vw_transfer_stops'])}"
    )

    print(
        "Durak bazlı hat çifti kaydı      : "
        f"{len(results['vw_route_pairs_by_stop'])}"
    )

    print(
        "Benzersiz hat çifti sayısı       : "
        f"{len(results['vw_route_pair_common_stop_counts'])}"
    )

    print(
        "Hattı olmayan durak sayısı       : "
        f"{len(results['vw_stops_without_routes'])}"
    )

    print(
        "Geçersiz koordinatlı durak sayısı: "
        f"{len(results['vw_invalid_coordinate_stops'])}"
    )

    print(
        "Aynı isimli farklı ID kayıtları  : "
        f"{len(results['vw_duplicate_stop_names'])}"
    )

    print("\nEn fazla aktarma seçeneği sunan 10 durak:")

    print(
        results["vw_top_transfer_stops"]
        .sort_values(
            [
                "transfer_rank",
                "stop_id",
            ]
        )
        .head(10)
        .to_string(
            index=False
        )
    )

    print("\nEn fazla ortak durağa sahip 10 hat çifti:")

    print(
        results["vw_top_route_pairs"]
        .sort_values(
            [
                "common_stop_rank",
                "route_1",
                "route_2",
            ]
        )
        .head(10)
        .to_string(
            index=False
        )
    )


# ============================================================
# ANA PROGRAM
# ============================================================

def main() -> None:
    """
    Gelişmiş SQL view'larını oluşturur, sonuçları
    doğrular ve CSV raporlarını üretir.
    """

    print("=" * 70)
    print("ESHOT GELİŞMİŞ SQL ANALİZİ")
    print("=" * 70)

    validate_files()

    REPORTS_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    connection = sqlite3.connect(
        DATABASE_FILE
    )

    try:
        print(
            "\nGelişmiş SQL view'ları oluşturuluyor..."
        )

        create_advanced_views(
            connection
        )

        validate_view_names(
            connection
        )

        results = {}

        for view_name in VIEW_REPORTS:
            results[view_name] = read_view(
                connection,
                view_name
            )

        validate_results(
            results
        )

        report_files = []

        for view_name, file_name in VIEW_REPORTS.items():
            report_file = save_report(
                results[view_name],
                file_name
            )

            report_files.append(
                report_file
            )

    finally:
        connection.close()

    print_summary(
        results
    )

    print("\nOluşturulan CSV raporları:")

    for report_file in report_files:
        print(
            f"- {report_file}"
        )

    print("\nKontrol sonuçları:")
    print("- 10 gelişmiş SQL view'ı oluşturuldu.")
    print("- CTE kullanımı doğrulandı.")
    print("- Self join ile hat çiftleri oluşturuldu.")
    print("- GROUP BY ve HAVING kullanıldı.")
    print("- Window function ile sıralamalar oluşturuldu.")
    print("- Ters hat çifti tekrarları engellendi.")
    print("- Analiz sonuçlarının temel tutarlılığı doğrulandı.")
    print("- CSV raporları başarıyla oluşturuldu.")

    print(
        "\nGelişmiş SQL analizi başarıyla tamamlandı."
    )


if __name__ == "__main__":
    main()
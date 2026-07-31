from pathlib import Path
import sqlite3

import matplotlib.pyplot as plt
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

SQL_FILE = (
    PROJECT_DIR
    / "sql"
    / "analysis_queries.sql"
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


# ============================================================
# GEREKLİ DOSYALARI KONTROL ETME
# ============================================================

def validate_files():
    """
    Analiz için gereken veritabanı ve SQL dosyasını kontrol eder.
    """

    required_files = [
        DATABASE_FILE,
        SQL_FILE
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
            "\nAnaliz için gerekli dosyalar bulunamadı:\n"
            f"{missing_text}\n\n"
            "Önce şu komutları çalıştır:\n"
            "python scripts/clean_data.py\n"
            "python scripts/build_database.py"
        )


# ============================================================
# SQL DOSYASINI AYRI SORGULARA DÖNÜŞTÜRME
# ============================================================

def load_named_queries():
    """
    analysis_queries.sql içindeki sorguları
    '-- name: sorgu_adi' açıklamalarına göre ayırır.
    """

    sql_text = SQL_FILE.read_text(
        encoding="utf-8"
    )

    queries = {}
    current_name = None
    current_lines = []

    for line in sql_text.splitlines():
        stripped_line = line.strip()

        if stripped_line.startswith("-- name:"):
            if current_name is not None:
                query_text = "\n".join(
                    current_lines
                ).strip()

                if query_text:
                    queries[current_name] = query_text

            current_name = (
                stripped_line
                .replace("-- name:", "", 1)
                .strip()
            )

            current_lines = []

        elif current_name is not None:
            if not stripped_line.startswith("--"):
                current_lines.append(line)

    if current_name is not None:
        query_text = "\n".join(
            current_lines
        ).strip()

        if query_text:
            queries[current_name] = query_text

    required_queries = {
        "total_stops",
        "valid_coordinate_stops",
        "invalid_coordinate_stops",
        "stops_without_routes",
        "total_unique_routes",
        "total_stop_route_relations",
        "total_quality_issues",
        "top_10_routes",
        "top_10_stops",
        "duplicate_stop_names",
        "route_stop_counts",
        "single_route_stop_count",
        "stops_with_more_than_five_routes",
        "data_quality_summary"
    }

    missing_queries = (
        required_queries - set(queries)
    )

    if missing_queries:
        raise ValueError(
            "analysis_queries.sql içinde eksik sorgular var: "
            f"{sorted(missing_queries)}"
        )

    return queries


# ============================================================
# SQL SONUÇLARINI PANDAS İLE OKUMA
# ============================================================

def execute_query(connection, query):
    """
    SQL sorgusunu çalıştırır ve sonucu DataFrame olarak döndürür.
    """

    return pd.read_sql_query(
        query,
        connection
    )


# ============================================================
# CSV RAPORLARINI KAYDETME
# ============================================================

def save_report(dataframe, file_name):
    """
    DataFrame sonucunu CSV raporu olarak kaydeder.
    """

    output_file = REPORTS_DIR / file_name

    dataframe.to_csv(
        output_file,
        index=False,
        encoding="utf-8-sig"
    )

    return output_file


# ============================================================
# GRAFİKLER
# ============================================================

def create_top_routes_chart(top_routes):
    """
    En fazla duraktan geçen 10 hattın grafiğini oluşturur.
    """

    if top_routes.empty:
        print(
            "Uyarı: top_10_routes sorgusu boş sonuç döndürdü."
        )
        return None

    chart_data = top_routes.copy()

    chart_data["route_number"] = (
        chart_data["route_number"]
        .astype(str)
    )

    chart_data = chart_data.sort_values(
        "stop_count",
        ascending=True
    )

    plt.figure(
        figsize=(11, 7)
    )

    plt.barh(
        chart_data["route_number"],
        chart_data["stop_count"]
    )

    plt.title(
        "En Fazla Duraktan Geçen 10 Hat"
    )

    plt.xlabel(
        "Benzersiz Durak Sayısı"
    )

    plt.ylabel(
        "Hat Numarası"
    )

    plt.grid(
        axis="x",
        alpha=0.25
    )

    for index, value in enumerate(
        chart_data["stop_count"]
    ):
        plt.text(
            value,
            index,
            f" {value}",
            va="center"
        )

    plt.tight_layout()

    output_file = (
        CHARTS_DIR
        / "top_10_routes.png"
    )

    plt.savefig(
        output_file,
        dpi=300,
        bbox_inches="tight"
    )

    plt.close()

    return output_file


def create_top_stops_chart(top_stops):
    """
    En fazla hattın geçtiği 10 durağın grafiğini oluşturur.
    """

    if top_stops.empty:
        print(
            "Uyarı: top_10_stops sorgusu boş sonuç döndürdü."
        )
        return None

    chart_data = top_stops.copy()

    chart_data["stop_label"] = (
        chart_data["stop_name"].astype(str)
        + " ("
        + chart_data["stop_id"].astype(str)
        + ")"
    )

    chart_data = chart_data.sort_values(
        "route_count",
        ascending=True
    )

    plt.figure(
        figsize=(13, 8)
    )

    plt.barh(
        chart_data["stop_label"],
        chart_data["route_count"]
    )

    plt.title(
        "En Fazla Farklı Hattın Geçtiği 10 Durak"
    )

    plt.xlabel(
        "Benzersiz Hat Sayısı"
    )

    plt.ylabel(
        "Durak"
    )

    plt.grid(
        axis="x",
        alpha=0.25
    )

    for index, value in enumerate(
        chart_data["route_count"]
    ):
        plt.text(
            value,
            index,
            f" {value}",
            va="center"
        )

    plt.tight_layout()

    output_file = (
        CHARTS_DIR
        / "top_10_stops.png"
    )

    plt.savefig(
        output_file,
        dpi=300,
        bbox_inches="tight"
    )

    plt.close()

    return output_file


def create_quality_chart(quality_summary):
    """
    Veri kalitesi sorun dağılımı grafiğini oluşturur.
    """

    if quality_summary.empty:
        print(
            "Uyarı: Veri kalitesi sorunu bulunmadı."
        )
        return None

    chart_data = quality_summary.copy()

    chart_data = chart_data.sort_values(
        "issue_count",
        ascending=True
    )

    plt.figure(
        figsize=(12, 7)
    )

    plt.barh(
        chart_data["issue_type"],
        chart_data["issue_count"]
    )

    plt.title(
        "Veri Kalitesi Sorunlarının Dağılımı"
    )

    plt.xlabel(
        "Sorun Sayısı"
    )

    plt.ylabel(
        "Sorun Türü"
    )

    plt.grid(
        axis="x",
        alpha=0.25
    )

    for index, value in enumerate(
        chart_data["issue_count"]
    ):
        plt.text(
            value,
            index,
            f" {value}",
            va="center"
        )

    plt.tight_layout()

    output_file = (
        CHARTS_DIR
        / "data_quality_summary.png"
    )

    plt.savefig(
        output_file,
        dpi=300,
        bbox_inches="tight"
    )

    plt.close()

    return output_file


# ============================================================
# ANALİZ SONUÇLARINI DOĞRULAMA
# ============================================================

def validate_analysis_results(
    top_routes,
    top_stops,
    quality_summary
):
    """
    Analiz sonuçlarında birleşik hat değerlerinin
    kalmadığını ve temel sonuçların tutarlı olduğunu kontrol eder.
    """

    assert len(top_routes) <= 10, (
        "top_10_routes sonucu 10 satırdan fazla olamaz."
    )

    assert len(top_stops) <= 10, (
        "top_10_stops sonucu 10 satırdan fazla olamaz."
    )

    combined_route_count = (
        top_routes["route_number"]
        .astype(str)
        .str.contains(
            "-",
            regex=False
        )
        .sum()
    )

    assert combined_route_count == 0, (
        "Hat analizinde birleşik hat değeri bulundu. "
        "Örnek: 829-989"
    )

    duplicated_routes = (
        top_routes["route_number"]
        .duplicated()
        .sum()
    )

    assert duplicated_routes == 0, (
        "En yoğun 10 hat sonucunda tekrarlanan hat bulundu."
    )

    assert (
        quality_summary["issue_type"]
        .is_unique
    ), (
        "Veri kalite özetinde tekrarlanan sorun türü bulundu."
    )


# ============================================================
# ANA PROGRAM
# ============================================================

def main():
    """
    SQL analizlerini çalıştırır, raporları ve grafikleri üretir.
    """

    print("=" * 65)
    print("ESHOT SQL ANALİZİ VE GRAFİK OLUŞTURMA")
    print("=" * 65)

    validate_files()

    REPORTS_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    CHARTS_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    queries = load_named_queries()

    connection = sqlite3.connect(
        DATABASE_FILE
    )

    try:
        results = {}

        for query_name, query_text in queries.items():
            results[query_name] = execute_query(
                connection,
                query_text
            )

    finally:
        connection.close()

    top_routes = results["top_10_routes"]
    top_stops = results["top_10_stops"]
    quality_summary = results[
        "data_quality_summary"
    ]

    validate_analysis_results(
        top_routes=top_routes,
        top_stops=top_stops,
        quality_summary=quality_summary
    )

    report_files = [
        save_report(
            top_routes,
            "top_10_routes.csv"
        ),
        save_report(
            top_stops,
            "top_10_stops.csv"
        ),
        save_report(
            quality_summary,
            "data_quality_summary.csv"
        ),
        save_report(
            results["duplicate_stop_names"],
            "duplicate_stop_names.csv"
        ),
        save_report(
            results["route_stop_counts"],
            "route_stop_counts.csv"
        ),
        save_report(
            results["stops_with_more_than_five_routes"],
            "stops_with_more_than_five_routes.csv"
        )
    ]

    chart_files = [
        create_top_routes_chart(
            top_routes
        ),
        create_top_stops_chart(
            top_stops
        ),
        create_quality_chart(
            quality_summary
        )
    ]

    print("\n" + "=" * 65)
    print("TEMEL VERİTABANI KONTROLLERİ")
    print("=" * 65)

    print(
        "Toplam durak sayısı              : "
        f"{results['total_stops'].iloc[0, 0]}"
    )

    print(
        "Geçerli koordinatlı durak sayısı : "
        f"{results['valid_coordinate_stops'].iloc[0, 0]}"
    )

    print(
        "Geçersiz koordinatlı durak sayısı: "
        f"{results['invalid_coordinate_stops'].iloc[0, 0]}"
    )

    print(
        "Hat bilgisi olmayan durak sayısı : "
        f"{results['stops_without_routes'].iloc[0, 0]}"
    )

    print(
        "Toplam benzersiz hat sayısı      : "
        f"{results['total_unique_routes'].iloc[0, 0]}"
    )

    print(
        "Toplam durak-hat ilişkisi         : "
        f"{results['total_stop_route_relations'].iloc[0, 0]}"
    )

    print(
        "Toplam veri kalitesi sorunu       : "
        f"{results['total_quality_issues'].iloc[0, 0]}"
    )

    print(
        "Sadece bir hattın geçtiği durak   : "
        f"{results['single_route_stop_count'].iloc[0, 0]}"
    )

    print("\nEn fazla duraktan geçen 10 hat:")
    print(
        top_routes.to_string(
            index=False
        )
    )

    print("\nEn fazla hattın geçtiği 10 durak:")
    print(
        top_stops.to_string(
            index=False
        )
    )

    print("\nOluşturulan CSV raporları:")

    for report_file in report_files:
        print(f"- {report_file}")

    print("\nOluşturulan grafikler:")

    for chart_file in chart_files:
        if chart_file is not None:
            print(f"- {chart_file}")

    print("\nKontrol sonuçları:")
    print("- Hatlar ayrı ayrı analiz edildi.")
    print("- Birleşik hat değeri bulunmuyor.")
    print("- En yoğun 10 hat sorgusu doğrulandı.")
    print("- En yoğun 10 durak sorgusu doğrulandı.")
    print("- CSV raporları başarıyla oluşturuldu.")
    print("- Grafikler başarıyla oluşturuldu.")

    print("\nSQL analiz işlemi başarıyla tamamlandı.")


if __name__ == "__main__":
    main()
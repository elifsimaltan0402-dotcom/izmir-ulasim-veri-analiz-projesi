from pathlib import Path
import json
import sqlite3

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent.parent

DATABASE_FILE = (
    PROJECT_ROOT
    / "database"
    / "eshot_analytics.db"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "outputs"
    / "reports"
    / "network"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


def load_stop_route_data() -> pd.DataFrame:
    """
    Veritabanından durak-hat ilişkilerini okur.
    """

    connection = sqlite3.connect(DATABASE_FILE)

    query = """
    SELECT
        stop_id,
        route_number
    FROM stop_routes
    ORDER BY stop_id
    """

    dataframe = pd.read_sql_query(
        query,
        connection,
    )

    connection.close()

    return dataframe


def create_route_connections(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """
    Aynı duraktan geçen hatlar arasında bağlantılar oluşturur.
    """

    connections = []

    grouped = dataframe.groupby("stop_id")

    for _, group in grouped:
        routes = sorted(
            group["route_number"].unique()
        )

        for i in range(len(routes)):
            for j in range(i + 1, len(routes)):
                connections.append(
                    {
                        "route_1": routes[i],
                        "route_2": routes[j],
                    }
                )

    connections = pd.DataFrame(connections)

    connections = (
        connections
        .value_counts()
        .reset_index(name="shared_stop_count")
        .sort_values(
            "shared_stop_count",
            ascending=False,
        )
    )

    return connections


def calculate_route_metrics(
    route_connections: pd.DataFrame,
) -> pd.DataFrame:
    """
    Her hat için ağ bağlantı ölçümlerini hesaplar.
    """

    route_1_metrics = (
        route_connections
        .groupby("route_1")
        .agg(
            connected_route_count=(
                "route_2",
                "nunique",
            ),
            total_shared_stop_count=(
                "shared_stop_count",
                "sum",
            ),
        )
        .reset_index()
        .rename(
            columns={
                "route_1": "route_number"
            }
        )
    )

    route_2_metrics = (
        route_connections
        .groupby("route_2")
        .agg(
            connected_route_count=(
                "route_1",
                "nunique",
            ),
            total_shared_stop_count=(
                "shared_stop_count",
                "sum",
            ),
        )
        .reset_index()
        .rename(
            columns={
                "route_2": "route_number"
            }
        )
    )

    route_metrics = pd.concat(
        [
            route_1_metrics,
            route_2_metrics,
        ],
        ignore_index=True,
    )

    route_metrics = (
        route_metrics
        .groupby("route_number")
        .agg(
            connected_route_count=(
                "connected_route_count",
                "sum",
            ),
            total_shared_stop_count=(
                "total_shared_stop_count",
                "sum",
            ),
        )
        .reset_index()
        .sort_values(
            [
                "connected_route_count",
                "total_shared_stop_count",
            ],
            ascending=False,
        )
    )

    return route_metrics


def save_reports(
    route_connections: pd.DataFrame,
    route_metrics: pd.DataFrame,
) -> None:
    """
    Ağ analiz raporlarını CSV ve JSON olarak kaydeder.
    """

    route_connections.to_csv(
        OUTPUT_DIR / "route_connections.csv",
        index=False,
        encoding="utf-8-sig",
    )

    route_metrics.to_csv(
        OUTPUT_DIR / "top_network_routes.csv",
        index=False,
        encoding="utf-8-sig",
    )

    summary = {
        "route_count": int(
            route_metrics.shape[0]
        ),
        "connection_count": int(
            route_connections.shape[0]
        ),
        "max_connected_route": int(
            route_metrics.iloc[0]["route_number"]
        ),
        "max_connection_degree": int(
            route_metrics.iloc[0]["connected_route_count"]
        ),
    }

    with open(
        OUTPUT_DIR / "network_summary.json",
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            summary,
            file,
            ensure_ascii=False,
            indent=4,
        )


def main() -> None:
    """
    Ağ analizini çalıştırır ve raporları üretir.
    """

    print("=" * 65)
    print("ESHOT HAT AĞI ANALİZİ")
    print("=" * 65)

    if not DATABASE_FILE.exists():
        raise FileNotFoundError(
            f"Veritabanı dosyası bulunamadı: {DATABASE_FILE}"
        )

    print("\nDurak-hat verileri okunuyor...")
    stop_route_data = load_stop_route_data()

    if stop_route_data.empty:
        raise ValueError(
            "stop_routes tablosunda analiz edilecek veri bulunamadı."
        )

    print("Hat bağlantıları oluşturuluyor...")
    route_connections = create_route_connections(
        stop_route_data
    )

    if route_connections.empty:
        raise ValueError(
            "Hatlar arasında ortak durak bağlantısı bulunamadı."
        )

    print("Hat ağ ölçümleri hesaplanıyor...")
    route_metrics = calculate_route_metrics(
        route_connections
    )

    print("Ağ raporları kaydediliyor...")
    save_reports(
        route_connections,
        route_metrics,
    )

    print("\n" + "=" * 65)
    print("AĞ ANALİZİ SONUÇLARI")
    print("=" * 65)

    print(
        f"Bağlantılı hat sayısı       : "
        f"{route_metrics.shape[0]}"
    )

    print(
        f"Hatlar arası bağlantı sayısı: "
        f"{route_connections.shape[0]}"
    )

    print("\nEn bağlantılı 10 hat:")

    print(
        route_metrics.head(10).to_string(
            index=False
        )
    )

    print("\nOluşturulan dosyalar:")

    print(
        f"- {OUTPUT_DIR / 'route_connections.csv'}"
    )

    print(
        f"- {OUTPUT_DIR / 'top_network_routes.csv'}"
    )

    print(
        f"- {OUTPUT_DIR / 'network_summary.json'}"
    )

    print(
        "\nAğ analizi başarıyla tamamlandı."
    )


if __name__ == "__main__":
    main()
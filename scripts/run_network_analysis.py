from collections import Counter
from itertools import combinations
from pathlib import Path

import matplotlib.pyplot as plt
import networkx as nx
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

def validate_input_files():
    """
    Ağ analizi için gerekli CSV dosyalarının
    mevcut olup olmadığını kontrol eder.
    """

    required_files = [
        STOPS_FILE,
        STOP_ROUTES_FILE
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
            "\nAğ analizi için gerekli dosyalar bulunamadı:\n"
            f"{missing_text}\n\n"
            "Önce şu komutu çalıştır:\n"
            "python scripts/clean_data.py"
        )


# ============================================================
# VERİLERİ OKUMA
# ============================================================

def load_data():
    """
    Temiz durak ve durak-hat ilişki dosyalarını okur.
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

    return stops, stop_routes


# ============================================================
# VERİ DOĞRULAMA
# ============================================================

def validate_data(stops, stop_routes):
    """
    Ağ oluşturulmadan önce temel veri kontrollerini yapar.
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

    if stops["stop_id"].isna().any():
        raise ValueError(
            "stops_clean.csv içinde eksik stop_id bulundu."
        )

    if not stops["stop_id"].is_unique:
        raise ValueError(
            "stops_clean.csv içinde tekrarlanan stop_id bulundu."
        )

    duplicate_relations = stop_routes.duplicated(
        subset=["stop_id", "route_number"]
    ).sum()

    if duplicate_relations > 0:
        raise ValueError(
            "stop_routes.csv içinde tekrarlanan "
            "durak-hat ilişkileri bulundu."
        )

    missing_stop_references = (
        ~stop_routes["stop_id"]
        .isin(stops["stop_id"])
    ).sum()

    if missing_stop_references > 0:
        raise ValueError(
            "stop_routes.csv içinde stops_clean.csv dosyasında "
            "bulunmayan durak kimlikleri var."
        )


# ============================================================
# DÜĞÜM KİMLİKLERİ
# ============================================================

def create_stop_node_id(stop_id):
    """
    Durak düğümü için benzersiz kimlik oluşturur.
    """

    return f"stop_{int(stop_id)}"


def create_route_node_id(route_number):
    """
    Hat düğümü için benzersiz kimlik oluşturur.
    """

    return f"route_{str(route_number).strip()}"


# ============================================================
# İKİ PARÇALI AĞI OLUŞTURMA
# ============================================================

def build_bipartite_network(stops, stop_routes):
    """
    Duraklar ve hatlardan oluşan iki parçalı ağı kurar.

    Durak düğümleri:
        node_type = stop
        bipartite = 0

    Hat düğümleri:
        node_type = route
        bipartite = 1
    """

    graph = nx.Graph()

    for row in stops.itertuples(index=False):
        stop_node = create_stop_node_id(row.stop_id)

        graph.add_node(
            stop_node,
            node_type="stop",
            bipartite=0,
            stop_id=int(row.stop_id),
            stop_name=str(row.stop_name)
        )

    unique_routes = (
        stop_routes["route_number"]
        .dropna()
        .astype(str)
        .str.strip()
        .drop_duplicates()
        .sort_values()
    )

    for route_number in unique_routes:
        route_node = create_route_node_id(route_number)

        graph.add_node(
            route_node,
            node_type="route",
            bipartite=1,
            route_number=route_number
        )

    for row in stop_routes.itertuples(index=False):
        if pd.isna(row.route_number):
            continue

        route_number = str(row.route_number).strip()

        if not route_number:
            continue

        stop_node = create_stop_node_id(row.stop_id)
        route_node = create_route_node_id(route_number)

        graph.add_edge(
            stop_node,
            route_node
        )

    return graph


# ============================================================
# AĞ ÖZETİ
# ============================================================

def create_network_summary(graph):
    """
    Temel ağ ölçümlerini hesaplar.
    """

    connected_components = list(
        nx.connected_components(graph)
    )

    largest_component_size = max(
        (
            len(component)
            for component in connected_components
        ),
        default=0
    )

    stop_node_count = sum(
        1
        for _, attributes in graph.nodes(data=True)
        if attributes.get("node_type") == "stop"
    )

    route_node_count = sum(
        1
        for _, attributes in graph.nodes(data=True)
        if attributes.get("node_type") == "route"
    )

    isolated_node_count = nx.number_of_isolates(graph)

    summary_data = [
        {
            "metric": "total_nodes",
            "value": graph.number_of_nodes()
        },
        {
            "metric": "stop_nodes",
            "value": stop_node_count
        },
        {
            "metric": "route_nodes",
            "value": route_node_count
        },
        {
            "metric": "total_edges",
            "value": graph.number_of_edges()
        },
        {
            "metric": "connected_components",
            "value": len(connected_components)
        },
        {
            "metric": "largest_component_size",
            "value": largest_component_size
        },
        {
            "metric": "isolated_nodes",
            "value": isolated_node_count
        }
    ]

    return pd.DataFrame(summary_data)


# ============================================================
# BAĞLANTILI BİLEŞENLER
# ============================================================

def create_connected_components_report(graph):
    """
    Her bağlantılı bileşenin düğüm, durak, hat
    ve bağlantı sayılarını hesaplar.
    """

    component_rows = []

    sorted_components = sorted(
        nx.connected_components(graph),
        key=len,
        reverse=True
    )

    for component_id, component_nodes in enumerate(
        sorted_components,
        start=1
    ):
        subgraph = graph.subgraph(component_nodes)

        stop_count = sum(
            1
            for node in component_nodes
            if graph.nodes[node].get("node_type") == "stop"
        )

        route_count = sum(
            1
            for node in component_nodes
            if graph.nodes[node].get("node_type") == "route"
        )

        component_rows.append(
            {
                "component_id": component_id,
                "node_count": len(component_nodes),
                "stop_count": stop_count,
                "route_count": route_count,
                "edge_count": subgraph.number_of_edges(),
                "is_isolated": int(len(component_nodes) == 1)
            }
        )

    return pd.DataFrame(component_rows)


# ============================================================
# EN GÜÇLÜ AKTARMA MERKEZLERİ
# ============================================================

def create_top_transfer_hubs(graph):
    """
    Birden fazla hatta bağlı durakları derecelerine göre sıralar.
    """

    rows = []

    for node, attributes in graph.nodes(data=True):
        if attributes.get("node_type") != "stop":
            continue

        route_count = graph.degree(node)

        if route_count < 2:
            continue

        connected_routes = sorted(
            str(
                graph.nodes[neighbor].get(
                    "route_number",
                    ""
                )
            )
            for neighbor in graph.neighbors(node)
        )

        rows.append(
            {
                "stop_id": attributes.get("stop_id"),
                "stop_name": attributes.get("stop_name"),
                "route_count": route_count,
                "connected_routes": ", ".join(connected_routes)
            }
        )

    dataframe = pd.DataFrame(rows)

    if dataframe.empty:
        return pd.DataFrame(
            columns=[
                "stop_id",
                "stop_name",
                "route_count",
                "connected_routes"
            ]
        )

    dataframe = dataframe.sort_values(
        by=[
            "route_count",
            "stop_id"
        ],
        ascending=[
            False,
            True
        ]
    ).reset_index(drop=True)

    return dataframe


# ============================================================
# EN FAZLA DURAĞA BAĞLI HATLAR
# ============================================================

def create_top_routes(graph):
    """
    Hat düğümlerini bağlı oldukları durak sayısına göre sıralar.
    """

    rows = []

    for node, attributes in graph.nodes(data=True):
        if attributes.get("node_type") != "route":
            continue

        rows.append(
            {
                "route_number": attributes.get("route_number"),
                "stop_count": graph.degree(node)
            }
        )

    dataframe = pd.DataFrame(rows)

    if dataframe.empty:
        return pd.DataFrame(
            columns=[
                "route_number",
                "stop_count"
            ]
        )

    return dataframe.sort_values(
        by=[
            "stop_count",
            "route_number"
        ],
        ascending=[
            False,
            True
        ]
    ).reset_index(drop=True)


# ============================================================
# ORTAK DURAKLI HAT ÇİFTLERİ
# ============================================================

def create_route_pairs_shared_stops(graph):
    """
    Aynı duraktan geçen bütün hat çiftlerini oluşturur
    ve ortak durak sayılarını hesaplar.
    """

    route_pair_counter = Counter()

    for node, attributes in graph.nodes(data=True):
        if attributes.get("node_type") != "stop":
            continue

        connected_routes = sorted(
            str(
                graph.nodes[neighbor].get(
                    "route_number",
                    ""
                )
            )
            for neighbor in graph.neighbors(node)
        )

        for route_1, route_2 in combinations(
            connected_routes,
            2
        ):
            route_pair_counter[
                (
                    route_1,
                    route_2
                )
            ] += 1

    rows = [
        {
            "route_1": route_1,
            "route_2": route_2,
            "shared_stop_count": shared_stop_count
        }
        for (
            route_1,
            route_2
        ), shared_stop_count in route_pair_counter.items()
    ]

    dataframe = pd.DataFrame(rows)

    if dataframe.empty:
        return pd.DataFrame(
            columns=[
                "route_1",
                "route_2",
                "shared_stop_count"
            ]
        )

    dataframe = dataframe.sort_values(
        by=[
            "shared_stop_count",
            "route_1",
            "route_2"
        ],
        ascending=[
            False,
            True,
            True
        ]
    ).reset_index(drop=True)

    return dataframe


# ============================================================
# HİÇBİR HATTA BAĞLI OLMAYAN DURAKLAR
# ============================================================

def create_isolated_stops_report(graph):
    """
    Derecesi sıfır olan durak düğümlerini bulur.
    """

    rows = []

    for node, attributes in graph.nodes(data=True):
        if attributes.get("node_type") != "stop":
            continue

        if graph.degree(node) == 0:
            rows.append(
                {
                    "stop_id": attributes.get("stop_id"),
                    "stop_name": attributes.get("stop_name"),
                    "route_count": 0
                }
            )

    dataframe = pd.DataFrame(rows)

    if dataframe.empty:
        return pd.DataFrame(
            columns=[
                "stop_id",
                "stop_name",
                "route_count"
            ]
        )

    return dataframe.sort_values(
        by=[
            "stop_id"
        ]
    ).reset_index(drop=True)


# ============================================================
# CSV RAPORU KAYDETME
# ============================================================

def save_report(dataframe, file_name):
    """
    DataFrame sonucunu CSV dosyasına kaydeder.
    """

    output_file = REPORTS_DIR / file_name

    dataframe.to_csv(
        output_file,
        index=False,
        encoding="utf-8-sig"
    )

    return output_file


# ============================================================
# GRAFİK 1: EN GÜÇLÜ 15 AKTARMA DURAĞI
# ============================================================

def create_transfer_hubs_chart(top_transfer_hubs):
    """
    En fazla hatta bağlı 15 durağı yatay çubuk
    grafik olarak oluşturur.
    """

    if top_transfer_hubs.empty:
        print(
            "Uyarı: Aktarma durağı grafiği için veri bulunamadı."
        )
        return None

    chart_data = (
        top_transfer_hubs
        .head(15)
        .copy()
    )

    chart_data["label"] = (
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
        figsize=(12, 8)
    )

    plt.barh(
        chart_data["label"],
        chart_data["route_count"]
    )

    plt.title(
        "En Güçlü 15 Aktarma Durağı"
    )

    plt.xlabel(
        "Bağlı Hat Sayısı"
    )

    plt.ylabel(
        "Durak"
    )

    plt.grid(
        axis="x",
        alpha=0.25
    )

    plt.tight_layout()

    output_file = (
        CHARTS_DIR
        / "top_15_transfer_hubs.png"
    )

    plt.savefig(
        output_file,
        dpi=300,
        bbox_inches="tight"
    )

    plt.close()

    return output_file


# ============================================================
# GRAFİK 2: EN FAZLA ORTAK DURAĞA SAHİP 15 HAT ÇİFTİ
# ============================================================

def create_route_pairs_chart(route_pairs):
    """
    En yüksek ortak durak sayısına sahip 15 hat çiftini
    yatay çubuk grafik olarak oluşturur.
    """

    if route_pairs.empty:
        print(
            "Uyarı: Hat çifti grafiği için veri bulunamadı."
        )
        return None

    chart_data = (
        route_pairs
        .head(15)
        .copy()
    )

    chart_data["route_pair"] = (
        chart_data["route_1"].astype(str)
        + " - "
        + chart_data["route_2"].astype(str)
    )

    chart_data = chart_data.sort_values(
        "shared_stop_count",
        ascending=True
    )

    plt.figure(
        figsize=(12, 8)
    )

    plt.barh(
        chart_data["route_pair"],
        chart_data["shared_stop_count"]
    )

    plt.title(
        "En Fazla Ortak Durağa Sahip 15 Hat Çifti"
    )

    plt.xlabel(
        "Ortak Durak Sayısı"
    )

    plt.ylabel(
        "Hat Çifti"
    )

    plt.grid(
        axis="x",
        alpha=0.25
    )

    plt.tight_layout()

    output_file = (
        CHARTS_DIR
        / "top_15_route_pairs_shared_stops.png"
    )

    plt.savefig(
        output_file,
        dpi=300,
        bbox_inches="tight"
    )

    plt.close()

    return output_file


# ============================================================
# GRAFİK 3: DURAKLARIN HAT SAYISI DAĞILIMI
# ============================================================

def create_stop_degree_distribution_chart(graph):
    """
    Durakların kaç hatta bağlı olduğunu gösteren
    dağılım grafiğini oluşturur.
    """

    stop_degrees = [
        graph.degree(node)
        for node, attributes in graph.nodes(data=True)
        if attributes.get("node_type") == "stop"
    ]

    degree_counts = Counter(stop_degrees)

    chart_data = pd.DataFrame(
        {
            "route_count": list(degree_counts.keys()),
            "stop_count": list(degree_counts.values())
        }
    ).sort_values(
        "route_count"
    )

    if chart_data.empty:
        print(
            "Uyarı: Durak derece dağılımı için veri bulunamadı."
        )
        return None

    plt.figure(
        figsize=(11, 7)
    )

    plt.bar(
        chart_data["route_count"],
        chart_data["stop_count"]
    )

    plt.title(
        "Durakların Hat Sayısı Dağılımı"
    )

    plt.xlabel(
        "Bir Durağa Bağlı Hat Sayısı"
    )

    plt.ylabel(
        "Durak Sayısı"
    )

    plt.xticks(
        chart_data["route_count"]
    )

    plt.grid(
        axis="y",
        alpha=0.25
    )

    plt.tight_layout()

    output_file = (
        CHARTS_DIR
        / "stop_route_count_distribution.png"
    )

    plt.savefig(
        output_file,
        dpi=300,
        bbox_inches="tight"
    )

    plt.close()

    return output_file


# ============================================================
# SONUÇLARI TERMİNALE YAZDIRMA
# ============================================================

def print_results(
    graph,
    network_summary,
    connected_components,
    top_transfer_hubs,
    top_routes,
    route_pairs,
    isolated_stops,
    report_files,
    chart_files
):
    """
    Ağ analizi sonuçlarını terminalde özetler.
    """

    summary_lookup = dict(
        zip(
            network_summary["metric"],
            network_summary["value"]
        )
    )

    print("\n" + "=" * 65)
    print("ESHOT HAT-DURAK AĞ ANALİZİ")
    print("=" * 65)

    print(
        f"Toplam düğüm sayısı              : "
        f"{summary_lookup['total_nodes']}"
    )

    print(
        f"Durak düğümü sayısı              : "
        f"{summary_lookup['stop_nodes']}"
    )

    print(
        f"Hat düğümü sayısı                : "
        f"{summary_lookup['route_nodes']}"
    )

    print(
        f"Toplam bağlantı sayısı           : "
        f"{summary_lookup['total_edges']}"
    )

    print(
        f"Bağlantılı bileşen sayısı        : "
        f"{summary_lookup['connected_components']}"
    )

    print(
        f"En büyük bileşenin büyüklüğü     : "
        f"{summary_lookup['largest_component_size']}"
    )

    print(
        f"Hiçbir hatta bağlı olmayan durak : "
        f"{len(isolated_stops)}"
    )

    print("\nEn güçlü 10 aktarma durağı:")

    if top_transfer_hubs.empty:
        print("Aktarma durağı bulunamadı.")
    else:
        print(
            top_transfer_hubs[
                [
                    "stop_id",
                    "stop_name",
                    "route_count"
                ]
            ]
            .head(10)
            .to_string(index=False)
        )

    print("\nEn fazla durağa bağlı 10 hat:")

    if top_routes.empty:
        print("Hat bulunamadı.")
    else:
        print(
            top_routes
            .head(10)
            .to_string(index=False)
        )

    print("\nEn fazla ortak durağa sahip 10 hat çifti:")

    if route_pairs.empty:
        print("Ortak durağa sahip hat çifti bulunamadı.")
    else:
        print(
            route_pairs
            .head(10)
            .to_string(index=False)
        )

    print("\nOluşturulan CSV raporları:")

    for report_file in report_files:
        print(
            f"- {report_file.relative_to(PROJECT_DIR)}"
        )

    print("\nOluşturulan grafikler:")

    for chart_file in chart_files:
        if chart_file is not None:
            print(
                f"- {chart_file.relative_to(PROJECT_DIR)}"
            )

    print("\nBağlantılı bileşen raporu satır sayısı:")
    print(len(connected_components))

    print("\nAğ analizi başarıyla tamamlandı.")
    print("=" * 65)


# ============================================================
# ANA PROGRAM
# ============================================================

def main():
    """
    ESHOT iki parçalı ağ modelini oluşturur,
    analizleri çalıştırır ve çıktıları kaydeder.
    """

    validate_input_files()

    REPORTS_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    CHARTS_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    stops, stop_routes = load_data()

    validate_data(
        stops,
        stop_routes
    )

    graph = build_bipartite_network(
        stops,
        stop_routes
    )

    network_summary = create_network_summary(
        graph
    )

    connected_components = (
        create_connected_components_report(
            graph
        )
    )

    top_transfer_hubs = create_top_transfer_hubs(
        graph
    )

    top_routes = create_top_routes(
        graph
    )

    route_pairs = create_route_pairs_shared_stops(
        graph
    )

    isolated_stops = create_isolated_stops_report(
        graph
    )

    report_files = [
        save_report(
            network_summary,
            "network_summary.csv"
        ),
        save_report(
            top_transfer_hubs,
            "top_transfer_hubs.csv"
        ),
        save_report(
            route_pairs,
            "route_pairs_shared_stops.csv"
        ),
        save_report(
            connected_components,
            "connected_components.csv"
        ),
        save_report(
            isolated_stops,
            "isolated_stops.csv"
        ),
        save_report(
            top_routes,
            "network_top_routes.csv"
        )
    ]

    chart_files = [
        create_transfer_hubs_chart(
            top_transfer_hubs
        ),
        create_route_pairs_chart(
            route_pairs
        ),
        create_stop_degree_distribution_chart(
            graph
        )
    ]

    print_results(
        graph,
        network_summary,
        connected_components,
        top_transfer_hubs,
        top_routes,
        route_pairs,
        isolated_stops,
        report_files,
        chart_files
    )


if __name__ == "__main__":
    main()
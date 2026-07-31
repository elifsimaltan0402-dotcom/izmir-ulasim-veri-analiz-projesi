from pathlib import Path

import pandas as pd


PROJECT_DIR = Path(__file__).resolve().parent.parent

REPORTS_DIR = PROJECT_DIR / "outputs" / "reports"
CHARTS_DIR = PROJECT_DIR / "outputs" / "charts"


def test_required_report_files_exist():
    required_files = [
        "network_summary.csv",
        "top_transfer_hubs.csv",
        "route_pairs_shared_stops.csv",
        "connected_components.csv",
        "isolated_stops.csv",
    ]

    for file_name in required_files:
        assert (REPORTS_DIR / file_name).exists(), (
            f"Eksik rapor: {file_name}"
        )


def test_required_chart_files_exist():
    required_files = [
        "top_15_transfer_hubs.png",
        "top_15_route_pairs_shared_stops.png",
        "stop_route_count_distribution.png",
    ]

    for file_name in required_files:
        assert (CHARTS_DIR / file_name).exists(), (
            f"Eksik grafik: {file_name}"
        )


def test_network_summary_metrics():
    summary = pd.read_csv(
        REPORTS_DIR / "network_summary.csv",
        encoding="utf-8-sig",
    )

    metrics = dict(
        zip(
            summary["metric"],
            summary["value"],
        )
    )

    assert metrics["stop_nodes"] == 11782
    assert metrics["route_nodes"] == 441

    assert metrics["total_nodes"] == (
        metrics["stop_nodes"]
        + metrics["route_nodes"]
    )

    assert metrics["total_edges"] > 0
    assert metrics["connected_components"] >= 1
    assert metrics["largest_component_size"] > 0


def test_transfer_hubs():
    hubs = pd.read_csv(
        REPORTS_DIR / "top_transfer_hubs.csv",
        encoding="utf-8-sig",
    )

    assert not hubs.empty

    assert (
        hubs["route_count"] >= 2
    ).all()

    assert hubs[
        "route_count"
    ].is_monotonic_decreasing


def test_route_pairs():
    pairs = pd.read_csv(
        REPORTS_DIR / "route_pairs_shared_stops.csv",
        encoding="utf-8-sig",
        dtype={
            "route_1": "string",
            "route_2": "string",
            "shared_stop_count": "int64",
        },
    )

    assert not pairs.empty

    assert (
        pairs["shared_stop_count"] > 0
    ).all()

    assert (
        pairs["route_1"] < pairs["route_2"]
    ).all()

    assert (
        pairs[
            [
                "route_1",
                "route_2",
            ]
        ]
        .duplicated()
        .sum()
        == 0
    )


def test_connected_components():
    components = pd.read_csv(
        REPORTS_DIR / "connected_components.csv",
        encoding="utf-8-sig",
    )

    assert not components.empty

    assert (
        components["node_count"] >= 1
    ).all()

    assert (
        components["edge_count"] >= 0
    ).all()

    assert (
        components["node_count"]
        == (
            components["stop_count"]
            + components["route_count"]
        )
    ).all()


def test_isolated_stops():
    isolated = pd.read_csv(
        REPORTS_DIR / "isolated_stops.csv",
        encoding="utf-8-sig",
    )

    assert (
        isolated["route_count"] == 0
    ).all()


def test_report_consistency():
    summary = pd.read_csv(
        REPORTS_DIR / "network_summary.csv",
        encoding="utf-8-sig",
    )

    isolated = pd.read_csv(
        REPORTS_DIR / "isolated_stops.csv",
        encoding="utf-8-sig",
    )

    components = pd.read_csv(
        REPORTS_DIR / "connected_components.csv",
        encoding="utf-8-sig",
    )

    metrics = dict(
        zip(
            summary["metric"],
            summary["value"],
        )
    )

    assert (
        metrics["isolated_nodes"]
        == len(isolated)
    )

    assert (
        metrics["connected_components"]
        == len(components)
    )

    assert (
        metrics["total_nodes"]
        == components["node_count"].sum()
    )

    assert (
        metrics["total_edges"]
        == components["edge_count"].sum()
    )
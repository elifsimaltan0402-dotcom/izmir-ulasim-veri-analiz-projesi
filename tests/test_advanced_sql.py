from pathlib import Path
import sqlite3

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent.parent

DATABASE_FILE = (
    PROJECT_ROOT
    / "database"
    / "eshot_analytics.db"
)

ADVANCED_SQL_FILE = (
    PROJECT_ROOT
    / "sql"
    / "advanced_analysis.sql"
)


EXPECTED_VIEWS = {
    "vw_stop_route_counts",
    "vw_route_stop_counts",
    "vw_transfer_stops",
    "vw_top_transfer_stops",
    "vw_route_pairs_by_stop",
    "vw_route_pair_common_stop_counts",
    "vw_top_route_pairs",
    "vw_stops_without_routes",
    "vw_invalid_coordinate_stops",
    "vw_duplicate_stop_names",
}


def create_views(connection: sqlite3.Connection) -> None:
    """
    Gelişmiş SQL view'larını test veritabanında oluşturur.
    """

    sql_text = ADVANCED_SQL_FILE.read_text(
        encoding="utf-8"
    )

    connection.executescript(sql_text)
    connection.commit()


def read_view(
    connection: sqlite3.Connection,
    view_name: str,
) -> pd.DataFrame:
    """
    Verilen view sonucunu DataFrame olarak döndürür.
    """

    return pd.read_sql_query(
        f"SELECT * FROM {view_name}",
        connection
    )


def test_required_files_exist():
    """
    Gerekli veritabanı ve SQL dosyalarının
    mevcut olduğunu doğrular.
    """

    assert DATABASE_FILE.exists(), (
        f"Veritabanı bulunamadı: {DATABASE_FILE}"
    )

    assert ADVANCED_SQL_FILE.exists(), (
        f"Gelişmiş SQL dosyası bulunamadı: "
        f"{ADVANCED_SQL_FILE}"
    )


def test_all_advanced_views_are_created():
    """
    Beklenen 10 view'ın tamamının oluşturulduğunu doğrular.
    """

    connection = sqlite3.connect(DATABASE_FILE)

    try:
        create_views(connection)

        rows = connection.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'view'
            """
        ).fetchall()

        existing_views = {
            row[0]
            for row in rows
        }

        missing_views = EXPECTED_VIEWS - existing_views

        assert not missing_views, (
            "Eksik view'lar var: "
            f"{sorted(missing_views)}"
        )

    finally:
        connection.close()


def test_stop_route_counts_are_unique():
    """
    Her durağın yalnızca bir kez listelendiğini doğrular.
    """

    connection = sqlite3.connect(DATABASE_FILE)

    try:
        create_views(connection)

        dataframe = read_view(
            connection,
            "vw_stop_route_counts"
        )

        assert dataframe["stop_id"].is_unique

        assert (
            dataframe["route_count"] >= 0
        ).all()

    finally:
        connection.close()


def test_route_stop_counts_are_unique():
    """
    Her hattın yalnızca bir kez listelendiğini doğrular.
    """

    connection = sqlite3.connect(DATABASE_FILE)

    try:
        create_views(connection)

        dataframe = read_view(
            connection,
            "vw_route_stop_counts"
        )

        assert dataframe["route_number"].is_unique

        assert (
            dataframe["stop_count"] >= 0
        ).all()

    finally:
        connection.close()


def test_transfer_stops_have_at_least_two_routes():
    """
    Aktarma duraklarının en az iki hatta sahip olduğunu doğrular.
    """

    connection = sqlite3.connect(DATABASE_FILE)

    try:
        create_views(connection)

        dataframe = read_view(
            connection,
            "vw_transfer_stops"
        )

        assert not dataframe.empty

        assert (
            dataframe["route_count"] >= 2
        ).all()

    finally:
        connection.close()


def test_route_pairs_are_not_reversed_or_duplicated():
    """
    121-140 ve 140-121 gibi ters çiftlerin
    birlikte oluşmadığını doğrular.
    """

    connection = sqlite3.connect(DATABASE_FILE)

    try:
        create_views(connection)

        dataframe = read_view(
            connection,
            "vw_route_pairs_by_stop"
        )

        assert (
            dataframe["route_1"]
            < dataframe["route_2"]
        ).all()

        duplicate_count = dataframe.duplicated(
            subset=[
                "stop_id",
                "route_1",
                "route_2",
            ]
        ).sum()

        assert duplicate_count == 0

    finally:
        connection.close()


def test_common_stop_counts_are_unique_and_positive():
    """
    Her hat çiftinin yalnızca bir kez listelendiğini
    ve ortak durak sayısının pozitif olduğunu doğrular.
    """

    connection = sqlite3.connect(DATABASE_FILE)

    try:
        create_views(connection)

        dataframe = read_view(
            connection,
            "vw_route_pair_common_stop_counts"
        )

        duplicate_count = dataframe.duplicated(
            subset=[
                "route_1",
                "route_2",
            ]
        ).sum()

        assert duplicate_count == 0

        assert (
            dataframe["common_stop_count"] >= 1
        ).all()

        assert (
            dataframe["route_1"]
            < dataframe["route_2"]
        ).all()

    finally:
        connection.close()


def test_top_transfer_ranking_is_consistent():
    """
    Aktarma durağı sıralamasında daha yüksek route_count
    değerlerinin daha iyi sırada olduğunu doğrular.
    """

    connection = sqlite3.connect(DATABASE_FILE)

    try:
        create_views(connection)

        dataframe = read_view(
            connection,
            "vw_top_transfer_stops"
        ).sort_values(
            [
                "transfer_rank",
                "route_count",
            ],
            ascending=[
                True,
                False,
            ]
        )

        assert not dataframe.empty

        route_counts = (
            dataframe["route_count"]
            .tolist()
        )

        assert route_counts == sorted(
            route_counts,
            reverse=True
        )

        assert (
            dataframe["transfer_rank"] >= 1
        ).all()

    finally:
        connection.close()


def test_top_route_pair_ranking_is_consistent():
    """
    Ortak durak sayısı sıralamasının doğru olduğunu doğrular.
    """

    connection = sqlite3.connect(DATABASE_FILE)

    try:
        create_views(connection)

        dataframe = read_view(
            connection,
            "vw_top_route_pairs"
        ).sort_values(
            [
                "common_stop_rank",
                "common_stop_count",
            ],
            ascending=[
                True,
                False,
            ]
        )

        assert not dataframe.empty

        common_counts = (
            dataframe["common_stop_count"]
            .tolist()
        )

        assert common_counts == sorted(
            common_counts,
            reverse=True
        )

        assert (
            dataframe["common_stop_rank"] >= 1
        ).all()

    finally:
        connection.close()


def test_stops_without_routes_are_consistent():
    """
    Hattı olmayan durakların stop_route_counts view'ındaki
    route_count = 0 kayıtlarıyla aynı olduğunu doğrular.
    """

    connection = sqlite3.connect(DATABASE_FILE)

    try:
        create_views(connection)

        stops_without_routes = read_view(
            connection,
            "vw_stops_without_routes"
        )

        stop_route_counts = read_view(
            connection,
            "vw_stop_route_counts"
        )

        expected_ids = set(
            stop_route_counts.loc[
                stop_route_counts["route_count"] == 0,
                "stop_id",
            ]
        )

        actual_ids = set(
            stops_without_routes["stop_id"]
        )

        assert actual_ids == expected_ids

    finally:
        connection.close()


def test_invalid_coordinate_stops_are_validated():
    """
    Geçersiz koordinat view'ındaki tüm durakların
    has_valid_coordinate değerinin 0 olduğunu doğrular.
    """

    connection = sqlite3.connect(DATABASE_FILE)

    try:
        create_views(connection)

        dataframe = read_view(
            connection,
            "vw_invalid_coordinate_stops"
        )

        assert (
            dataframe["has_valid_coordinate"] == 0
        ).all()

    finally:
        connection.close()


def test_duplicate_stop_names_have_multiple_ids():
    """
    Aynı isimli durakların gerçekten birden fazla
    farklı stop_id değerine sahip olduğunu doğrular.
    """

    connection = sqlite3.connect(DATABASE_FILE)

    try:
        create_views(connection)

        dataframe = read_view(
            connection,
            "vw_duplicate_stop_names"
        )

        if dataframe.empty:
            return

        id_counts = (
            dataframe
            .groupby("stop_name")["stop_id"]
            .nunique()
        )

        assert (
            id_counts > 1
        ).all()

    finally:
        connection.close()
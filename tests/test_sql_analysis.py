import sqlite3

from scripts.run_analysis import (
    DATABASE_FILE,
    execute_query,
    load_named_queries
)


def test_sql_queries_return_expected_columns():
    """
    Temel SQL analiz sorgularının beklenen
    sütun adlarını döndürdüğünü doğrular.
    """

    queries = load_named_queries()

    expected_columns = {
        "total_stops": [
            "total_stops"
        ],
        "valid_coordinate_stops": [
            "valid_coordinate_stops"
        ],
        "invalid_coordinate_stops": [
            "invalid_coordinate_stops"
        ],
        "stops_without_routes": [
            "stops_without_routes"
        ],
        "total_unique_routes": [
            "total_unique_routes"
        ],
        "total_stop_route_relations": [
            "total_stop_route_relations"
        ],
        "total_quality_issues": [
            "total_quality_issues"
        ],
        "top_10_routes": [
            "route_number",
            "stop_count"
        ],
        "top_10_stops": [
            "stop_id",
            "stop_name",
            "route_count"
        ],
        "duplicate_stop_names": [
            "stop_name",
            "stop_count"
        ],
        "route_stop_counts": [
            "route_number",
            "stop_count"
        ],
        "single_route_stop_count": [
            "single_route_stop_count"
        ],
        "stops_with_more_than_five_routes": [
            "stop_id",
            "stop_name",
            "route_count"
        ],
        "data_quality_summary": [
            "issue_type",
            "issue_count"
        ]
    }

    assert DATABASE_FILE.exists(), (
        f"Test veritabanı bulunamadı: {DATABASE_FILE}"
    )

    with sqlite3.connect(DATABASE_FILE) as connection:
        for query_name, columns in expected_columns.items():
            result = execute_query(
                connection,
                queries[query_name]
            )

            assert result.columns.tolist() == columns, (
                f"{query_name} sorgusunun sütunları beklenenden farklı. "
                f"Beklenen: {columns}, "
                f"Gerçek: {result.columns.tolist()}"
            )
import pandas as pd

import scripts.clean_data as clean_data_module
from scripts.clean_data import clean_data, save_outputs, validate_outputs


def create_sample_raw_data():
    """
    Testlerde kullanılacak örnek ham veriyi oluşturur.
    """

    return pd.DataFrame(
        {
            "DURAK_ID": pd.Series(
                ["1001", None, "1002", "1002"],
                dtype="string"
            ),
            "DURAK_ADI": pd.Series(
                [
                    "Birinci Durak",
                    "ID Eksik Durak",
                    "İkinci Durak",
                    "Tekrarlanan Durak"
                ],
                dtype="string"
            ),
            "ENLEM": pd.Series(
                ["38.41", "38.42", "38.43", "38.43"],
                dtype="string"
            ),
            "BOYLAM": pd.Series(
                ["27.11", "27.12", "27.13", "27.13"],
                dtype="string"
            ),
            "DURAKTAN_GECEN_HATLAR": pd.Series(
                [
                    "21-910-21",
                    "35",
                    "920-930-920",
                    "920"
                ],
                dtype="string"
            ),
            "SOURCE_ROW_NUMBER": [2, 3, 4, 5]
        }
    )


def test_missing_id_not_added_to_clean_stops():
    raw_data = create_sample_raw_data()

    stops, _, _, _ = clean_data(raw_data)

    assert len(stops) == 2
    assert stops["stop_id"].isna().sum() == 0
    assert "ID Eksik Durak" not in stops["stop_name"].tolist()


def test_missing_id_added_to_rejected_rows_file(
    tmp_path,
    monkeypatch
):
    raw_data = create_sample_raw_data()

    stops, stop_routes, issues, rejected = clean_data(raw_data)

    rejected_file = tmp_path / "rejected_rows.csv"
    stops_file = tmp_path / "stops_clean.csv"
    stop_routes_file = tmp_path / "stop_routes.csv"
    issues_file = tmp_path / "data_quality_issues.csv"

    monkeypatch.setattr(
        clean_data_module,
        "REJECTED_ROWS_FILE",
        rejected_file
    )
    monkeypatch.setattr(
        clean_data_module,
        "STOPS_CLEAN_FILE",
        stops_file
    )
    monkeypatch.setattr(
        clean_data_module,
        "STOP_ROUTES_FILE",
        stop_routes_file
    )
    monkeypatch.setattr(
        clean_data_module,
        "QUALITY_ISSUES_FILE",
        issues_file
    )
    monkeypatch.setattr(
        clean_data_module,
        "PROCESSED_DIR",
        tmp_path
    )

    save_outputs(
        stops=stops,
        stop_routes=stop_routes,
        issues=issues,
        rejected=rejected
    )

    saved_rejected = pd.read_csv(
        rejected_file,
        sep=";",
        encoding="utf-8-sig"
    )

    assert rejected_file.exists()
    assert len(saved_rejected) == 1
    assert saved_rejected.loc[0, "DURAK_ADI"] == "ID Eksik Durak"
    assert (
        saved_rejected.loc[0, "rejection_reason"]
        == "Durak ID alanı eksiktir."
    )


def test_clean_stop_ids_are_unique():
    raw_data = create_sample_raw_data()

    stops, _, _, _ = clean_data(raw_data)

    assert stops["stop_id"].is_unique
    assert stops["stop_id"].duplicated().sum() == 0
    assert stops["stop_id"].tolist() == [1001, 1002]


def test_stop_route_relations_are_unique():
    raw_data = create_sample_raw_data()

    _, stop_routes, _, _ = clean_data(raw_data)

    duplicate_count = stop_routes.duplicated(
        subset=["stop_id", "route_number"]
    ).sum()

    assert duplicate_count == 0

    expected_relations = {
        (1001, "21"),
        (1001, "910"),
        (1002, "920"),
        (1002, "930")
    }

    actual_relations = set(
        stop_routes[
            ["stop_id", "route_number"]
        ].itertuples(
            index=False,
            name=None
        )
    )

    assert actual_relations == expected_relations


def test_foreign_key_reference_control_is_successful():
    raw_data = create_sample_raw_data()

    stops, stop_routes, issues, rejected = clean_data(raw_data)

    unknown_stop_ids = set(
        stop_routes["stop_id"].astype(int)
    ) - set(
        stops["stop_id"].astype(int)
    )

    assert unknown_stop_ids == set()

    validate_outputs(
        raw_data=raw_data,
        stops=stops,
        stop_routes=stop_routes,
        issues=issues,
        rejected=rejected
    )
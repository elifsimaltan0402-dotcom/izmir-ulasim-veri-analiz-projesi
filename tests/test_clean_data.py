import pandas as pd

from scripts.clean_data import (
    parse_coordinate,
    parse_routes,
    clean_data
)


def test_normal_coordinate():
    assert parse_coordinate("38.415268") == 38.415268


def test_broken_coordinate():
    assert parse_coordinate("3.841.526.836.260.150") == 38.41526836260150


def test_invalid_coordinate():
    result = parse_coordinate("Temmuz38")

    assert pd.isna(result)


def test_missing_coordinate():
    result = parse_coordinate("")

    assert pd.isna(result)


def test_route_parsing():
    routes, invalid = parse_routes("21-910-920")

    assert routes == ["21", "910", "920"]
    assert invalid == []


def test_duplicate_routes():
    routes, invalid = parse_routes("21-910-21-910")

    assert routes == ["21", "910"]
    assert invalid == []


def test_invalid_route_value():

    raw = pd.DataFrame({
        "DURAK_ID": ["1"],
        "DURAK_ADI": ["Deneme"],
        "ENLEM": ["38.41"],
        "BOYLAM": ["27.12"],
        "DURAKTAN_GECEN_HATLAR": ["21-ABC-910"],
        "SOURCE_ROW_NUMBER": [2]
    })

    _, _, issues, _ = clean_data(raw)

    assert (
        issues["issue_type"] == "Parse edilemeyen hat değeri"
    ).any()
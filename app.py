from __future__ import annotations

from datetime import datetime
from pathlib import Path
import sqlite3

import pandas as pd
import streamlit as st


# ============================================================
# DOSYA YOLLARI
# ============================================================

PROJECT_DIR = Path(__file__).resolve().parent
DATABASE_FILE = PROJECT_DIR / "database" / "eshot_analytics.db"


# ============================================================
# STREAMLIT SAYFA AYARLARI
# ============================================================

st.set_page_config(
    page_title="ESHOT Ulaşım Veri Analizi V3",
    page_icon="🚌",
    layout="wide",
)


# ============================================================
# YARDIMCI FONKSİYONLAR
# ============================================================

def format_number(value: int | float) -> str:
    """Sayıları Türkçe binlik ayırıcıyla gösterir."""
    return f"{int(value):,}".replace(",", ".")


def dataframe_to_csv_bytes(dataframe: pd.DataFrame) -> bytes:
    """DataFrame'i Excel uyumlu UTF-8 CSV baytlarına dönüştürür."""
    return dataframe.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")


def natural_route_key(route_number: str) -> tuple[int, int | str, str]:
    """Hat numaralarını önce sayısal, sonra alfabetik olarak sıralar."""
    text = str(route_number).strip()
    if text.isdigit():
        return (0, int(text), text)
    return (1, text.casefold(), text)


# ============================================================
# VERİTABANI BAĞLANTISI
# ============================================================

@st.cache_resource
def get_connection() -> sqlite3.Connection:
    """SQLite veritabanı bağlantısını oluşturur."""
    if not DATABASE_FILE.exists():
        raise FileNotFoundError(f"Veritabanı bulunamadı: {DATABASE_FILE}")

    connection = sqlite3.connect(DATABASE_FILE, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    return connection


@st.cache_data(show_spinner=False)
def run_query(query: str, parameters: tuple | list | None = None) -> pd.DataFrame:
    """SQL sorgusunu çalıştırır ve sonucu DataFrame olarak döndürür."""
    return pd.read_sql_query(query, get_connection(), params=parameters)


@st.cache_data(show_spinner=False)
def get_table_columns(table_name: str) -> list[str]:
    """Bir SQLite tablo veya görünümünün sütun adlarını getirir."""
    safe_table_name = table_name.replace('"', '""')
    table_info = run_query(f'PRAGMA table_info("{safe_table_name}");')
    if table_info.empty:
        return []
    return table_info["name"].astype(str).tolist()


# ============================================================
# GENEL BAKIŞ SORGULARI
# ============================================================

def get_kpis() -> pd.Series:
    query = """
    SELECT
        (SELECT COUNT(*) FROM stops) AS total_stops,
        (SELECT COUNT(*) FROM routes) AS total_routes,
        (
            SELECT COUNT(*)
            FROM stops
            WHERE has_valid_coordinate = 1
        ) AS valid_coordinate_stops,
        (
            SELECT COUNT(*)
            FROM stops AS s
            LEFT JOIN stop_routes AS sr ON s.stop_id = sr.stop_id
            WHERE sr.stop_id IS NULL
        ) AS stops_without_routes,
        (SELECT COUNT(*) FROM data_quality_issues) AS total_quality_issues;
    """
    return run_query(query).iloc[0]


def get_top_routes(limit: int = 10) -> pd.DataFrame:
    query = """
    SELECT
        sr.route_number,
        COUNT(DISTINCT sr.stop_id) AS stop_count
    FROM stop_routes AS sr
    GROUP BY sr.route_number
    ORDER BY
        stop_count DESC,
        CAST(sr.route_number AS INTEGER) ASC,
        sr.route_number ASC
    LIMIT ?;
    """
    return run_query(query, (int(limit),))


def get_top_stops(limit: int = 10) -> pd.DataFrame:
    query = """
    SELECT
        s.stop_id,
        s.stop_name,
        COUNT(DISTINCT sr.route_number) AS route_count
    FROM stops AS s
    INNER JOIN stop_routes AS sr ON s.stop_id = sr.stop_id
    GROUP BY s.stop_id, s.stop_name
    ORDER BY route_count DESC, s.stop_name ASC, s.stop_id ASC
    LIMIT ?;
    """
    return run_query(query, (int(limit),))


def get_quality_summary() -> pd.DataFrame:
    query = """
    SELECT
        issue_type,
        COUNT(*) AS issue_count
    FROM data_quality_issues
    GROUP BY issue_type
    ORDER BY issue_count DESC, issue_type ASC;
    """
    return run_query(query)


# ============================================================
# HAT ANALİZİ SORGULARI
# ============================================================

def get_route_options() -> list[str]:
    routes = run_query("SELECT route_number FROM routes;")
    values = routes["route_number"].dropna().astype(str).tolist()
    return sorted(values, key=natural_route_key)


def get_stops_for_route(route_number: str) -> pd.DataFrame:
    query = """
    SELECT
        s.stop_id,
        s.stop_name,
        s.latitude,
        s.longitude,
        s.has_valid_coordinate
    FROM stops AS s
    INNER JOIN stop_routes AS sr ON s.stop_id = sr.stop_id
    WHERE sr.route_number = ?
    ORDER BY s.stop_name ASC, s.stop_id ASC;
    """
    return run_query(query, (str(route_number),))


def get_shared_routes_for_route(route_number: str) -> pd.DataFrame:
    """Seçilen hatla ortak durak kullanan diğer hatları getirir."""
    query = """
    SELECT
        other.route_number AS other_route,
        COUNT(DISTINCT selected.stop_id) AS shared_stop_count
    FROM stop_routes AS selected
    INNER JOIN stop_routes AS other
        ON selected.stop_id = other.stop_id
       AND selected.route_number <> other.route_number
    WHERE selected.route_number = ?
    GROUP BY other.route_number
    ORDER BY
        shared_stop_count DESC,
        CAST(other.route_number AS INTEGER) ASC,
        other.route_number ASC;
    """
    return run_query(query, (str(route_number),))


# ============================================================
# AKTARMA MERKEZLERİ SORGULARI
# ============================================================

def get_transfer_hubs(limit: int = 100) -> pd.DataFrame:
    query = """
    SELECT
        s.stop_id,
        s.stop_name,
        s.latitude,
        s.longitude,
        s.has_valid_coordinate,
        COUNT(DISTINCT sr.route_number) AS route_count,
        GROUP_CONCAT(DISTINCT sr.route_number) AS route_list
    FROM stops AS s
    INNER JOIN stop_routes AS sr ON s.stop_id = sr.stop_id
    GROUP BY
        s.stop_id,
        s.stop_name,
        s.latitude,
        s.longitude,
        s.has_valid_coordinate
    HAVING COUNT(DISTINCT sr.route_number) >= 2
    ORDER BY route_count DESC, s.stop_name ASC, s.stop_id ASC
    LIMIT ?;
    """
    hubs = run_query(query, (int(limit),))
    if not hubs.empty:
        hubs["route_list"] = hubs["route_list"].fillna("").apply(
            lambda value: ", ".join(sorted(str(value).split(","), key=natural_route_key))
        )
    return hubs


def search_transfer_stops(search_text: str, search_mode: str) -> pd.DataFrame:
    base_query = """
    SELECT
        s.stop_id,
        s.stop_name,
        s.latitude,
        s.longitude,
        s.has_valid_coordinate,
        COUNT(DISTINCT sr.route_number) AS route_count,
        GROUP_CONCAT(DISTINCT sr.route_number) AS route_list
    FROM stops AS s
    INNER JOIN stop_routes AS sr ON s.stop_id = sr.stop_id
    WHERE {condition}
    GROUP BY
        s.stop_id,
        s.stop_name,
        s.latitude,
        s.longitude,
        s.has_valid_coordinate
    HAVING COUNT(DISTINCT sr.route_number) >= 2
    ORDER BY route_count DESC, s.stop_name ASC, s.stop_id ASC
    LIMIT 100;
    """

    if search_mode == "Durak ID":
        query = base_query.format(condition="CAST(s.stop_id AS TEXT) LIKE ?")
        parameter = f"%{search_text.strip()}%"
    else:
        query = base_query.format(condition="LOWER(s.stop_name) LIKE LOWER(?)")
        parameter = f"%{search_text.strip()}%"

    results = run_query(query, (parameter,))
    if not results.empty:
        results["route_list"] = results["route_list"].fillna("").apply(
            lambda value: ", ".join(sorted(str(value).split(","), key=natural_route_key))
        )
    return results


def get_routes_for_stop(stop_id: int) -> pd.DataFrame:
    query = """
    SELECT route_number
    FROM stop_routes
    WHERE stop_id = ?
    ORDER BY CAST(route_number AS INTEGER), route_number;
    """
    return run_query(query, (int(stop_id),))


def get_stop_detail(stop_id: int) -> pd.DataFrame:
    query = """
    SELECT
        stop_id,
        stop_name,
        latitude,
        longitude,
        has_valid_coordinate
    FROM stops
    WHERE stop_id = ?;
    """
    return run_query(query, (int(stop_id),))


# ============================================================
# HAT ÇİFTİ ANALİZİ SORGULARI
# ============================================================

def get_common_stops(route_1: str, route_2: str) -> pd.DataFrame:
    query = """
    SELECT
        s.stop_id,
        s.stop_name,
        s.latitude,
        s.longitude,
        s.has_valid_coordinate
    FROM stops AS s
    INNER JOIN stop_routes AS first_route
        ON s.stop_id = first_route.stop_id
    INNER JOIN stop_routes AS second_route
        ON s.stop_id = second_route.stop_id
    WHERE
        first_route.route_number = ?
        AND second_route.route_number = ?
    ORDER BY s.stop_name ASC, s.stop_id ASC;
    """
    return run_query(query, (str(route_1), str(route_2)))


# ============================================================
# VERİ KALİTESİ SORGULARI
# ============================================================

def get_quality_issue_types() -> list[str]:
    data = run_query(
        """
        SELECT DISTINCT issue_type
        FROM data_quality_issues
        WHERE issue_type IS NOT NULL
        ORDER BY issue_type ASC;
        """
    )
    return data["issue_type"].astype(str).tolist()


def get_quality_issues(issue_type: str | None = None) -> pd.DataFrame:
    """
    Kalite sorunlarını veritabanından getirir.

    Bazı eski veritabanı sürümlerinde source_row_number sütunu yoktur.
    Böyle bir durumda sütun boş değerle oluşturulur ve arayüzde açıklanır.
    """
    columns = get_table_columns("data_quality_issues")

    row_number_candidates = [
        "source_row_number",
        "source_row",
        "row_number",
        "source_line_number",
    ]
    row_number_column = next(
        (column for column in row_number_candidates if column in columns),
        None,
    )

    source_row_expression = (
        f'"{row_number_column}" AS source_row_number'
        if row_number_column
        else "NULL AS source_row_number"
    )

    query = f"""
    SELECT
        id,
        issue_type,
        stop_id,
        field_name,
        raw_value,
        {source_row_expression},
        description
    FROM data_quality_issues
    """
    parameters: tuple = ()

    if issue_type and issue_type != "Tüm sorun türleri":
        query += " WHERE issue_type = ?"
        parameters = (issue_type,)

    query += " ORDER BY issue_type ASC, id ASC;"
    return run_query(query, parameters)


def get_invalid_coordinates() -> pd.DataFrame:
    query = """
    SELECT
        s.stop_id,
        s.stop_name,
        s.latitude,
        s.longitude,
        s.has_valid_coordinate
    FROM stops AS s
    WHERE
        s.has_valid_coordinate = 0
        OR s.latitude IS NULL
        OR s.longitude IS NULL
    ORDER BY s.stop_id ASC;
    """
    return run_query(query)


def get_rejected_rows() -> pd.DataFrame:
    """
    Ana durak tablosuna alınamayan kayıtları temsil eden kalite sorunlarını getirir.
    Mevcut veri modelinde bunlar geçersiz veya eksik durak ID kayıtlarıdır.
    """
    columns = get_table_columns("data_quality_issues")
    row_number_candidates = [
        "source_row_number",
        "source_row",
        "row_number",
        "source_line_number",
    ]
    row_number_column = next(
        (column for column in row_number_candidates if column in columns),
        None,
    )
    source_row_expression = (
        f'"{row_number_column}" AS source_row_number'
        if row_number_column
        else "NULL AS source_row_number"
    )

    query = f"""
    SELECT
        id,
        issue_type,
        stop_id,
        field_name,
        raw_value,
        {source_row_expression},
        description
    FROM data_quality_issues
    WHERE
        stop_id IS NULL
        OR LOWER(issue_type) LIKE '%geçersiz durak id%'
        OR LOWER(issue_type) LIKE '%eksik%durak id%'
    ORDER BY id ASC;
    """
    return run_query(query)


# ============================================================
# VERİ KAYNAĞI BİLGİSİ
# ============================================================

def get_database_last_update() -> str:
    modified_at = datetime.fromtimestamp(DATABASE_FILE.stat().st_mtime)
    return modified_at.strftime("%d.%m.%Y %H:%M")


# ============================================================
# SAYFA BAŞLIĞI VE VERİTABANI KONTROLÜ
# ============================================================

st.title("🚌 ESHOT Ulaşım Veri Analizi V3")
st.caption(
    "İzmir ESHOT durak ve hat verilerinin SQLite tabanlı, "
    "etkileşimli analiz dashboard'u"
)

try:
    kpis = get_kpis()
    route_options = get_route_options()
except Exception as error:
    st.error("Dashboard veritabanına bağlanamadı.")
    st.exception(error)
    st.stop()


# ============================================================
# SEKMELER
# ============================================================

general_tab, route_tab, transfer_tab, route_pair_tab, quality_tab = st.tabs(
    [
        "📊 Genel Bakış",
        "🚌 Hat Analizi",
        "🔄 Aktarma Merkezleri",
        "🛣️ Hat Çifti Analizi",
        "⚠️ Veri Kalitesi",
    ]
)


# ============================================================
# 1. GENEL BAKIŞ
# ============================================================

with general_tab:
    st.subheader("Genel Göstergeler")

    column1, column2, column3, column4, column5 = st.columns(5)
    column1.metric("Toplam Durak", format_number(kpis["total_stops"]))
    column2.metric("Benzersiz Hat", format_number(kpis["total_routes"]))
    column3.metric("Geçerli Koordinat", format_number(kpis["valid_coordinate_stops"]))
    column4.metric("Hat Bilgisi Olmayan", format_number(kpis["stops_without_routes"]))
    column5.metric("Veri Kalitesi Sorunu", format_number(kpis["total_quality_issues"]))

    st.divider()
    st.subheader("Temel Grafikler")

    top_routes = get_top_routes(10)
    top_stops = get_top_stops(10)
    quality_summary = get_quality_summary()

    chart_column1, chart_column2 = st.columns(2)

    with chart_column1:
        st.markdown("#### En Fazla Duraktan Geçen 10 Hat")
        if top_routes.empty:
            st.info("Hat analizi için veri bulunamadı.")
        else:
            st.bar_chart(
                top_routes.set_index("route_number")["stop_count"],
                width="stretch",
            )
            st.dataframe(top_routes, width="stretch", hide_index=True)

    with chart_column2:
        st.markdown("#### En Fazla Hattın Geçtiği 10 Durak")
        if top_stops.empty:
            st.info("Durak analizi için veri bulunamadı.")
        else:
            stops_chart = top_stops.copy()
            stops_chart["stop_label"] = (
                stops_chart["stop_name"].astype(str)
                + " ("
                + stops_chart["stop_id"].astype(str)
                + ")"
            )
            st.bar_chart(
                stops_chart.set_index("stop_label")["route_count"],
                width="stretch",
            )
            st.dataframe(top_stops, width="stretch", hide_index=True)

    st.markdown("#### Veri Kalitesi Sorunlarının Dağılımı")
    if quality_summary.empty:
        st.info("Veri kalitesi sorunu bulunmamaktadır.")
    else:
        st.bar_chart(
            quality_summary.set_index("issue_type")["issue_count"],
            width="stretch",
        )
        st.dataframe(quality_summary, width="stretch", hide_index=True)

    st.divider()
    st.subheader("Veri Kaynağı ve Güncelleme Bilgisi")
    info_column1, info_column2 = st.columns(2)
    info_column1.info(
        f"**Veri kaynağı:** `{DATABASE_FILE.relative_to(PROJECT_DIR)}`\n\n"
        "Ana KPI ve analizler doğrudan SQLite tablolarından okunmaktadır."
    )
    info_column2.info(
        f"**Veritabanı son güncelleme:** {get_database_last_update()}\n\n"
        "Dashboard, ana analizleri ham CSV üzerinden yeniden hesaplamaz."
    )


# ============================================================
# 2. HAT ANALİZİ
# ============================================================

with route_tab:
    st.subheader("Hat Analizi")

    selected_route = st.selectbox(
        "Hat seçiniz",
        options=route_options,
        key="route_analysis_selected_route",
    )

    route_stops = get_stops_for_route(selected_route)
    shared_routes = get_shared_routes_for_route(selected_route)

    metric_column1, metric_column2 = st.columns(2)
    metric_column1.metric("Seçilen hat", selected_route)
    metric_column2.metric("Durak sayısı", format_number(len(route_stops)))

    st.markdown("#### Seçilen Hattın Durakları")
    if route_stops.empty:
        st.warning("Seçilen hatta ait durak bulunamadı.")
    else:
        st.dataframe(route_stops, width="stretch", hide_index=True)
        st.download_button(
            label="Seçilen hattın duraklarını CSV olarak indir",
            data=dataframe_to_csv_bytes(route_stops),
            file_name=f"hat_{selected_route}_duraklari.csv",
            mime="text/csv",
            key="download_route_stops",
        )

        map_route_stops = route_stops[
            (route_stops["has_valid_coordinate"] == 1)
            & route_stops["latitude"].notna()
            & route_stops["longitude"].notna()
        ].rename(columns={"latitude": "lat", "longitude": "lon"})

        if not map_route_stops.empty:
            st.markdown("#### Hattın Durak Haritası")
            st.map(map_route_stops[["lat", "lon"]], width="stretch")

    st.markdown("#### Ortak Durak Kullandığı Diğer Hatlar")
    if shared_routes.empty:
        st.info("Seçilen hatla ortak durak kullanan başka bir hat bulunamadı.")
    else:
        top_10_shared_routes = shared_routes.head(10)
        st.bar_chart(
            top_10_shared_routes.set_index("other_route")["shared_stop_count"],
            width="stretch",
        )
        st.dataframe(top_10_shared_routes, width="stretch", hide_index=True)
        st.download_button(
            label="Ortak hat sonuçlarını CSV olarak indir",
            data=dataframe_to_csv_bytes(shared_routes),
            file_name=f"hat_{selected_route}_ortak_hatlar.csv",
            mime="text/csv",
            key="download_shared_routes",
        )


# ============================================================
# 3. AKTARMA MERKEZLERİ
# ============================================================

with transfer_tab:
    st.subheader("Aktarma Merkezleri")

    st.markdown("#### En Güçlü Aktarma Durakları")
    transfer_hubs = get_transfer_hubs(100)

    if transfer_hubs.empty:
        st.info("Aktarma merkezi olarak değerlendirilebilecek durak bulunamadı.")
    else:
        top_15_hubs = transfer_hubs.head(15).copy()
        top_15_hubs["stop_label"] = (
            top_15_hubs["stop_name"].astype(str)
            + " ("
            + top_15_hubs["stop_id"].astype(str)
            + ")"
        )
        st.bar_chart(
            top_15_hubs.set_index("stop_label")["route_count"],
            width="stretch",
        )
        st.dataframe(
            transfer_hubs[
                ["stop_id", "stop_name", "route_count", "route_list"]
            ],
            width="stretch",
            hide_index=True,
        )

    st.divider()
    st.markdown("#### Durak Adına veya ID'ye Göre Arama")

    search_column1, search_column2 = st.columns([1, 3])
    with search_column1:
        transfer_search_mode = st.radio(
            "Arama türü",
            options=["Durak Adı", "Durak ID"],
            horizontal=False,
            key="transfer_search_mode",
        )
    with search_column2:
        transfer_search_text = st.text_input(
            "Arama metni",
            placeholder="Örnek: Fahrettin Altay veya 10005",
            key="transfer_search_text",
        )

    if transfer_search_text.strip():
        matching_transfer_stops = search_transfer_stops(
            transfer_search_text,
            transfer_search_mode,
        )
    else:
        matching_transfer_stops = transfer_hubs.head(100)

    if matching_transfer_stops.empty:
        st.warning("Arama ölçütüne uygun aktarma durağı bulunamadı.")
    else:
        stop_labels = {
            f"{row.stop_name} ({row.stop_id}) — {row.route_count} hat": int(row.stop_id)
            for row in matching_transfer_stops.itertuples()
        }

        selected_transfer_label = st.selectbox(
            "Haritada ve ayrıntıda gösterilecek durağı seçiniz",
            options=list(stop_labels.keys()),
            key="selected_transfer_stop",
        )
        selected_transfer_stop_id = stop_labels[selected_transfer_label]

        selected_stop_detail = get_stop_detail(selected_transfer_stop_id)
        selected_stop_routes = get_routes_for_stop(selected_transfer_stop_id)

        if not selected_stop_detail.empty:
            stop_row = selected_stop_detail.iloc[0]
            route_text = ", ".join(selected_stop_routes["route_number"].astype(str))

            detail_column1, detail_column2, detail_column3 = st.columns(3)
            detail_column1.metric("Durak ID", int(stop_row["stop_id"]))
            detail_column2.metric("Durak adı", str(stop_row["stop_name"]))
            detail_column3.metric("Geçen hat sayısı", len(selected_stop_routes))
            st.success(f"**Duraktan geçen hatlar:** {route_text or 'Kayıt yok'}")

            has_valid_location = (
                int(stop_row["has_valid_coordinate"]) == 1
                and pd.notna(stop_row["latitude"])
                and pd.notna(stop_row["longitude"])
            )

            if has_valid_location:
                selected_stop_map = pd.DataFrame(
                    {
                        "lat": [float(stop_row["latitude"])],
                        "lon": [float(stop_row["longitude"])],
                    }
                )
                st.markdown("#### Seçilen Aktarma Durağının Haritadaki Konumu")
                st.map(selected_stop_map, zoom=15, width="stretch")
            else:
                st.warning("Seçilen durağın haritada gösterilebilecek geçerli koordinatı yoktur.")


# ============================================================
# 4. HAT ÇİFTİ ANALİZİ
# ============================================================

with route_pair_tab:
    st.subheader("Hat Çifti Analizi")

    pair_column1, pair_column2 = st.columns(2)
    with pair_column1:
        selected_route_1 = st.selectbox(
            "Birinci hat",
            options=route_options,
            index=0,
            key="route_pair_first",
        )

    second_route_options = [route for route in route_options if route != selected_route_1]
    with pair_column2:
        selected_route_2 = st.selectbox(
            "İkinci hat",
            options=second_route_options,
            index=0,
            key="route_pair_second",
        )

    common_stops = get_common_stops(selected_route_1, selected_route_2)

    pair_metric1, pair_metric2, pair_metric3 = st.columns(3)
    pair_metric1.metric("Birinci hat", selected_route_1)
    pair_metric2.metric("İkinci hat", selected_route_2)
    pair_metric3.metric("Ortak durak sayısı", format_number(len(common_stops)))

    if common_stops.empty:
        st.info("Seçilen iki hattın ortak durağı bulunmamaktadır.")
    else:
        st.markdown("#### Ortak Durak Listesi")
        st.dataframe(common_stops, width="stretch", hide_index=True)
        st.download_button(
            label="Ortak durakları CSV olarak indir",
            data=dataframe_to_csv_bytes(common_stops),
            file_name=f"hat_{selected_route_1}_{selected_route_2}_ortak_duraklar.csv",
            mime="text/csv",
            key="download_common_stops",
        )

        common_map_data = common_stops[
            (common_stops["has_valid_coordinate"] == 1)
            & common_stops["latitude"].notna()
            & common_stops["longitude"].notna()
        ].rename(columns={"latitude": "lat", "longitude": "lon"})

        if common_map_data.empty:
            st.warning("Ortak durakların haritada gösterilebilecek geçerli koordinatı yoktur.")
        else:
            st.markdown("#### Ortak Durakların Haritadaki Konumları")
            st.map(common_map_data[["lat", "lon"]], width="stretch")


# ============================================================
# 5. VERİ KALİTESİ
# ============================================================

with quality_tab:
    st.subheader("Veri Kalitesi")

    issue_types = get_quality_issue_types()
    selected_issue_type = st.selectbox(
        "Sorun türüne göre filtreleyiniz",
        options=["Tüm sorun türleri"] + issue_types,
        key="quality_issue_filter",
    )

    quality_issues = get_quality_issues(selected_issue_type)

    st.markdown("#### Filtrelenen Veri Kalitesi Sorunları")
    quality_metric1, quality_metric2 = st.columns(2)
    quality_metric1.metric("Filtrelenen sorun sayısı", format_number(len(quality_issues)))
    quality_metric2.metric("Toplam sorun sayısı", format_number(kpis["total_quality_issues"]))

    if quality_issues.empty:
        st.info("Seçilen filtreye uygun veri kalitesi sorunu bulunamadı.")
    else:
        display_quality_issues = quality_issues.rename(
            columns={
                "issue_type": "sorun_turu",
                "stop_id": "durak_id",
                "field_name": "alan_adi",
                "raw_value": "ham_deger",
                "source_row_number": "kaynak_satir_numarasi",
                "description": "sorun_aciklamasi",
            }
        )

        st.dataframe(display_quality_issues, width="stretch", hide_index=True)
        st.download_button(
            label="Filtrelenen sonuçları CSV olarak indir",
            data=dataframe_to_csv_bytes(display_quality_issues),
            file_name="filtrelenen_veri_kalitesi_sorunlari.csv",
            mime="text/csv",
            key="download_quality_issues",
        )

        if quality_issues["source_row_number"].isna().all():
            st.caption(
                "Not: Mevcut SQLite şemasında kaynak satır numarası sütunu bulunmadığı "
                "için bu alan boş gösterilmektedir. Ham değer ve sorun açıklaması "
                "veritabanındaki kalite kayıtlarından okunmaktadır."
            )

    st.divider()
    st.markdown("#### Geçersiz Koordinatlar")
    invalid_coordinates = get_invalid_coordinates()
    if invalid_coordinates.empty:
        st.success("Geçersiz koordinatlı durak bulunmamaktadır.")
    else:
        st.dataframe(invalid_coordinates, width="stretch", hide_index=True)
        st.download_button(
            label="Geçersiz koordinatları CSV olarak indir",
            data=dataframe_to_csv_bytes(invalid_coordinates),
            file_name="gecersiz_koordinatlar.csv",
            mime="text/csv",
            key="download_invalid_coordinates",
        )

    st.divider()
    st.markdown("#### Reddedilen Satırlar")
    rejected_rows = get_rejected_rows()
    if rejected_rows.empty:
        st.info("Reddedilmiş satır kaydı bulunamadı.")
    else:
        rejected_rows_display = rejected_rows.rename(
            columns={
                "issue_type": "sorun_turu",
                "stop_id": "durak_id",
                "field_name": "alan_adi",
                "raw_value": "ham_deger",
                "source_row_number": "kaynak_satir_numarasi",
                "description": "sorun_aciklamasi",
            }
        )
        st.dataframe(rejected_rows_display, width="stretch", hide_index=True)
        st.download_button(
            label="Reddedilen satırları CSV olarak indir",
            data=dataframe_to_csv_bytes(rejected_rows_display),
            file_name="reddedilen_satirlar.csv",
            mime="text/csv",
            key="download_rejected_rows",
        )


# ============================================================
# ALT BİLGİ
# ============================================================

st.divider()
st.caption(
    "Bu dashboard; Python, pandas, SQLite, SQL ve Streamlit kullanılarak "
    "geliştirilmiştir. Ana analizler SQLite veritabanından okunmaktadır."
)
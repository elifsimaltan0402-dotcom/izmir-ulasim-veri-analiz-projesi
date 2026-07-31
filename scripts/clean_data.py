from pathlib import Path
import re

import pandas as pd


# ============================================================
# DOSYA YOLLARI
# ============================================================

PROJECT_DIR = Path(__file__).resolve().parent.parent

RAW_FILE = (
    PROJECT_DIR
    / "data"
    / "raw"
    / "eshot-otobus-duraklari.csv"
)

PROCESSED_DIR = (
    PROJECT_DIR
    / "data"
    / "processed"
)

STOPS_CLEAN_FILE = (
    PROCESSED_DIR
    / "stops_clean.csv"
)

STOP_ROUTES_FILE = (
    PROCESSED_DIR
    / "stop_routes.csv"
)

QUALITY_ISSUES_FILE = (
    PROCESSED_DIR
    / "data_quality_issues.csv"
)

REJECTED_ROWS_FILE = (
    PROCESSED_DIR
    / "rejected_rows.csv"
)


# İzmir için kullanılacak yaklaşık koordinat sınırları
MIN_LATITUDE = 37.0
MAX_LATITUDE = 40.0
MIN_LONGITUDE = 25.0
MAX_LONGITUDE = 29.0


# ============================================================
# KOORDİNAT TEMİZLEME
# ============================================================

def parse_coordinate(value):
    """
    Hatalı nokta ayrımlarına sahip koordinatları sayısal değere çevirir.

    Örnekler:
    3.841.526.836.260.150 -> 38.41526836260150
    38.415.144.105.211    -> 38.415144105211
    384.151               -> 38.4151
    2.712.763.952.722.090 -> 27.12763952722090

    Dönüştürülemeyen değerlerde pd.NA döndürür.
    """

    if pd.isna(value):
        return pd.NA

    raw_value = str(value).strip()

    if raw_value == "":
        return pd.NA

    is_negative = raw_value.startswith("-")

    digits = "".join(
        character
        for character in raw_value
        if character.isdigit()
    )

    # Enlem ve boylam değerleri en az üç rakam içermelidir.
    if len(digits) < 3:
        return pd.NA

    # İzmir koordinatlarında tam kısım iki basamaklıdır.
    normalized_value = f"{digits[:2]}.{digits[2:]}"

    try:
        coordinate = float(normalized_value)

        if is_negative:
            coordinate = -coordinate

        return coordinate

    except ValueError:
        return pd.NA


# ============================================================
# HAT BİLGİSİNİ AYRIŞTIRMA
# ============================================================

def parse_routes(value):
    """
    Hat bilgisini '-' karakterine göre ayırır.

    Örnek:
    21-910-920 -> ["21", "910", "920"]

    Aynı durak içinde tekrarlanan hatları tekilleştirir.
    Ayrıştırılamayan değerleri ayrıca döndürür.
    """

    if pd.isna(value):
        return [], []

    raw_value = str(value).strip()

    if raw_value == "":
        return [], []

    valid_routes = []
    invalid_routes = []

    route_parts = raw_value.split("-")

    for route in route_parts:
        route = route.strip()

        if route == "":
            continue

        # Hat numaralarının yalnızca rakamlardan oluşması bekleniyor.
        if re.fullmatch(r"\d+", route):
            if route not in valid_routes:
                valid_routes.append(route)
        else:
            if route not in invalid_routes:
                invalid_routes.append(route)

    return valid_routes, invalid_routes


# ============================================================
# HAM CSV DOSYASINI OKUMA
# ============================================================

def load_raw_data():
    """
    Ham CSV dosyasını okur ve gerekli sütunları kontrol eder.
    """

    if not RAW_FILE.exists():
        raise FileNotFoundError(
            "\nHam veri dosyası bulunamadı.\n"
            f"Beklenen dosya yolu:\n{RAW_FILE}\n"
        )

    data = pd.read_csv(
        RAW_FILE,
        sep=";",
        dtype="string",
        encoding="utf-8-sig"
    )

    # Sütun adlarındaki boşluk ve BOM karakterlerini temizle
    data.columns = (
        data.columns
        .str.strip()
        .str.replace("\ufeff", "", regex=False)
    )

    # Bazı veri sürümlerindeki hatalı sütun adını düzelt
    if "sDURAK_ID" in data.columns:
        data = data.rename(
            columns={"sDURAK_ID": "DURAK_ID"}
        )

    required_columns = [
        "DURAK_ID",
        "DURAK_ADI",
        "ENLEM",
        "BOYLAM",
        "DURAKTAN_GECEN_HATLAR"
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in data.columns
    ]

    if missing_columns:
        raise ValueError(
            "CSV dosyasında gerekli sütunlar bulunamadı: "
            f"{missing_columns}\n"
            f"Mevcut sütunlar: {list(data.columns)}"
        )

    # Ham CSV'deki orijinal satır numarasını sakla.
    # Başlık satırı 1 kabul edilir; ilk veri satırı bu nedenle 2'dir.
    data["SOURCE_ROW_NUMBER"] = data.index + 2

    return data[required_columns + ["SOURCE_ROW_NUMBER"]].copy()


# ============================================================
# VERİ KALİTESİ SORUNU EKLEME
# ============================================================

def add_quality_issue(
    issues,
    issue_type,
    stop_id,
    field_name,
    raw_value,
    description,
    source_row_number=None
):
    """
    Tespit edilen bir veri kalitesi sorununu listeye ekler.

    source_row_number, ham CSV dosyasındaki orijinal satır numarasını
    (başlık satırı 1 kabul edilerek) tutar. Böylece bir sorun tespit
    edildiğinde ham dosyadaki orijinal satıra geri dönülebilir.
    """

    issues.append(
        {
            "issue_type": issue_type,
            "stop_id": stop_id,
            "field_name": field_name,
            "raw_value": (
                None
                if pd.isna(raw_value)
                else str(raw_value)
            ),
            "description": description,
            "source_row_number": source_row_number
        }
    )


# ============================================================
# VERİYİ TEMİZLEME VE DÖNÜŞTÜRME
# ============================================================

def clean_data(raw_data):
    """
    Ham durak verisini temizler.

    Üç DataFrame üretir:
    1. Temiz duraklar
    2. Durak-hat ilişkileri
    3. Veri kalitesi sorunları
    """

    data = raw_data.copy()
    quality_issues = []
    stop_route_records = []

    # Ham değerleri kalite kontrolünde kullanabilmek için sakla
    data["RAW_DURAK_ID"] = data["DURAK_ID"]
    data["RAW_ENLEM"] = data["ENLEM"]
    data["RAW_BOYLAM"] = data["BOYLAM"]
    data["RAW_HATLAR"] = data["DURAKTAN_GECEN_HATLAR"]

    # Metin alanlarındaki gereksiz boşlukları temizle
    text_columns = [
        "DURAK_ID",
        "DURAK_ADI",
        "ENLEM",
        "BOYLAM",
        "DURAKTAN_GECEN_HATLAR"
    ]

    for column in text_columns:
        data[column] = data[column].str.strip()

    # --------------------------------------------------------
    # Durak ID temizliği
    # --------------------------------------------------------

    data["DURAK_ID"] = pd.to_numeric(
        data["DURAK_ID"],
        errors="coerce"
    ).astype("Int64")

    rejected_rows = []

    for _, row in data.iterrows():
        raw_stop_id = row["RAW_DURAK_ID"]
        parsed_stop_id = row["DURAK_ID"]

        if pd.isna(parsed_stop_id):
            if pd.isna(raw_stop_id) or str(raw_stop_id).strip() == "":
                description = "Durak ID alanı eksiktir."
            else:
                description = (
                    "Durak ID değeri sayısal tipe "
                    "dönüştürülememiştir."
                )

            add_quality_issue(
                issues=quality_issues,
                issue_type="Eksik veya geçersiz durak ID",
                stop_id=None,
                field_name="DURAK_ID",
                raw_value=raw_stop_id,
                description=description,
                source_row_number=row["SOURCE_ROW_NUMBER"]
            )

            # Bu satır durak ID'si olmadığı için temiz durak
            # tablosuna hiç alınamaz. Satırın TAMAMINI (yalnızca
            # hatalı alanı değil) rejected_rows.csv için sakla.
            rejected_rows.append(
                {
                    "source_row_number": row["SOURCE_ROW_NUMBER"],
                    "DURAK_ID": (
                        None
                        if pd.isna(raw_stop_id)
                        else str(raw_stop_id)
                    ),
                    "DURAK_ADI": row["DURAK_ADI"],
                    "ENLEM": row["RAW_ENLEM"],
                    "BOYLAM": row["RAW_BOYLAM"],
                    "DURAKTAN_GECEN_HATLAR": row["RAW_HATLAR"],
                    "rejection_reason": description
                }
            )

    # --------------------------------------------------------
    # Durak adı kontrolü
    # --------------------------------------------------------

    missing_stop_name = (
        data["DURAK_ADI"].isna()
        | data["DURAK_ADI"].eq("")
    )

    for _, row in data[missing_stop_name].iterrows():
        add_quality_issue(
            issues=quality_issues,
            issue_type="Eksik durak adı",
            stop_id=row["DURAK_ID"],
            field_name="DURAK_ADI",
            raw_value=row["DURAK_ADI"],
            description="Durak adı alanı eksiktir.",
            source_row_number=row["SOURCE_ROW_NUMBER"]
        )

    # Veritabanındaki NOT NULL koşulu için eksik adları doldur
    data.loc[missing_stop_name, "DURAK_ADI"] = "Bilinmeyen Durak"

    # --------------------------------------------------------
    # Koordinat temizliği
    # --------------------------------------------------------

    data["LATITUDE_PARSED"] = (
        data["ENLEM"]
        .apply(parse_coordinate)
    )

    data["LONGITUDE_PARSED"] = (
        data["BOYLAM"]
        .apply(parse_coordinate)
    )

    data["LATITUDE_PARSED"] = pd.to_numeric(
        data["LATITUDE_PARSED"],
        errors="coerce"
    )

    data["LONGITUDE_PARSED"] = pd.to_numeric(
        data["LONGITUDE_PARSED"],
        errors="coerce"
    )

    valid_latitude = (
        data["LATITUDE_PARSED"]
        .between(
            MIN_LATITUDE,
            MAX_LATITUDE,
            inclusive="both"
        )
        .fillna(False)
    )

    valid_longitude = (
        data["LONGITUDE_PARSED"]
        .between(
            MIN_LONGITUDE,
            MAX_LONGITUDE,
            inclusive="both"
        )
        .fillna(False)
    )

    data["HAS_VALID_COORDINATE"] = (
        valid_latitude & valid_longitude
    )

    for index, row in data.iterrows():
        stop_id = row["DURAK_ID"]

        raw_latitude = row["RAW_ENLEM"]
        raw_longitude = row["RAW_BOYLAM"]

        latitude_is_missing = (
            pd.isna(raw_latitude)
            or str(raw_latitude).strip() == ""
        )

        longitude_is_missing = (
            pd.isna(raw_longitude)
            or str(raw_longitude).strip() == ""
        )

        if latitude_is_missing:
            add_quality_issue(
                issues=quality_issues,
                issue_type="Eksik enlem",
                stop_id=stop_id,
                field_name="ENLEM",
                raw_value=raw_latitude,
                description="Enlem bilgisi eksiktir.",
                source_row_number=row["SOURCE_ROW_NUMBER"]
            )

        if longitude_is_missing:
            add_quality_issue(
                issues=quality_issues,
                issue_type="Eksik boylam",
                stop_id=stop_id,
                field_name="BOYLAM",
                raw_value=raw_longitude,
                description="Boylam bilgisi eksiktir.",
                source_row_number=row["SOURCE_ROW_NUMBER"]
            )

        if (
            not latitude_is_missing
            and not valid_latitude.loc[index]
        ):
            add_quality_issue(
                issues=quality_issues,
                issue_type="Geçersiz koordinat",
                stop_id=stop_id,
                field_name="ENLEM",
                raw_value=raw_latitude,
                description=(
                    "Enlem değeri sayısal olarak "
                    "dönüştürülememiş veya İzmir için "
                    "makul aralığın dışında kalmıştır."
                ),
                source_row_number=row["SOURCE_ROW_NUMBER"]
            )

        if (
            not longitude_is_missing
            and not valid_longitude.loc[index]
        ):
            add_quality_issue(
                issues=quality_issues,
                issue_type="Geçersiz koordinat",
                stop_id=stop_id,
                field_name="BOYLAM",
                raw_value=raw_longitude,
                description=(
                    "Boylam değeri sayısal olarak "
                    "dönüştürülememiş veya İzmir için "
                    "makul aralığın dışında kalmıştır."
                ),
                source_row_number=row["SOURCE_ROW_NUMBER"]
            )

    # Geçersiz koordinatları çıktı dosyasında boş bırak
    data.loc[
        ~valid_latitude,
        "LATITUDE_PARSED"
    ] = pd.NA

    data.loc[
        ~valid_longitude,
        "LONGITUDE_PARSED"
    ] = pd.NA

    # --------------------------------------------------------
    # Hat bilgisini ayrıştırma
    # --------------------------------------------------------

    for _, row in data.iterrows():
        stop_id = row["DURAK_ID"]
        raw_routes = row["RAW_HATLAR"]

        routes, invalid_routes = parse_routes(raw_routes)

        if pd.isna(raw_routes) or str(raw_routes).strip() == "":
            add_quality_issue(
                issues=quality_issues,
                issue_type="Eksik hat bilgisi",
                stop_id=stop_id,
                field_name="DURAKTAN_GECEN_HATLAR",
                raw_value=raw_routes,
                description=(
                    "Bu durak için herhangi bir hat "
                    "bilgisi bulunmamaktadır."
                ),
                source_row_number=row["SOURCE_ROW_NUMBER"]
            )

        for invalid_route in invalid_routes:
            add_quality_issue(
                issues=quality_issues,
                issue_type="Parse edilemeyen hat değeri",
                stop_id=stop_id,
                field_name="DURAKTAN_GECEN_HATLAR",
                raw_value=invalid_route,
                description=(
                    "Hat değeri beklenen sayısal formata "
                    "dönüştürülememiştir."
                ),
                source_row_number=row["SOURCE_ROW_NUMBER"]
            )

        # Eksik durak ID bulunan kayıtlar ilişki tablosuna alınmaz.
        if pd.isna(stop_id):
            continue

        for route_number in routes:
            stop_route_records.append(
                {
                    "stop_id": int(stop_id),
                    "route_number": route_number
                }
            )

    # --------------------------------------------------------
    # Temiz durak tablosu
    # --------------------------------------------------------

    valid_stop_rows = data.dropna(
        subset=["DURAK_ID"]
    ).copy()

    stops = valid_stop_rows[
        [
            "DURAK_ID",
            "DURAK_ADI",
            "LATITUDE_PARSED",
            "LONGITUDE_PARSED",
            "HAS_VALID_COORDINATE"
        ]
    ].copy()

    stops = stops.rename(
        columns={
            "DURAK_ID": "stop_id",
            "DURAK_ADI": "stop_name",
            "LATITUDE_PARSED": "latitude",
            "LONGITUDE_PARSED": "longitude",
            "HAS_VALID_COORDINATE": "has_valid_coordinate"
        }
    )

    stops["stop_id"] = (
        stops["stop_id"]
        .astype("Int64")
    )

    stops["has_valid_coordinate"] = (
        stops["has_valid_coordinate"]
        .astype(int)
    )

    stops = (
        stops
        .drop_duplicates(
            subset=["stop_id"],
            keep="first"
        )
        .sort_values("stop_id")
        .reset_index(drop=True)
    )

    # --------------------------------------------------------
    # Durak-hat ilişki tablosu
    # --------------------------------------------------------

    stop_routes = pd.DataFrame(
        stop_route_records,
        columns=["stop_id", "route_number"]
    )

    if not stop_routes.empty:
        stop_routes["stop_id"] = (
            stop_routes["stop_id"]
            .astype("Int64")
        )

        stop_routes["route_number"] = (
            stop_routes["route_number"]
            .astype("string")
        )

        stop_routes = (
            stop_routes
            .drop_duplicates(
                subset=["stop_id", "route_number"]
            )
            .sort_values(
                ["stop_id", "route_number"]
            )
            .reset_index(drop=True)
        )

    # --------------------------------------------------------
    # Veri kalitesi tablosu
    # --------------------------------------------------------

    issues = pd.DataFrame(
        quality_issues,
        columns=[
            "issue_type",
            "stop_id",
            "field_name",
            "raw_value",
            "description",
            "source_row_number"
        ]
    )

    if not issues.empty:
        issues["stop_id"] = pd.to_numeric(
            issues["stop_id"],
            errors="coerce"
        ).astype("Int64")

    # --------------------------------------------------------
    # Reddedilen satırlar (eksik/geçersiz durak ID)
    # --------------------------------------------------------

    rejected = pd.DataFrame(
        rejected_rows,
        columns=[
            "source_row_number",
            "DURAK_ID",
            "DURAK_ADI",
            "ENLEM",
            "BOYLAM",
            "DURAKTAN_GECEN_HATLAR",
            "rejection_reason"
        ]
    )

    return stops, stop_routes, issues, rejected


# ============================================================
# KONTROL VE DOĞRULAMA
# ============================================================

def validate_outputs(
    raw_data,
    stops,
    stop_routes,
    issues,
    rejected
):
    """
    Temizlenen veriler üzerinde tutarlılık kontrolleri yapar.
    """

    valid_raw_stop_ids = pd.to_numeric(
        raw_data["DURAK_ID"],
        errors="coerce"
    ).notna().sum()

    assert stops["stop_id"].is_unique, (
        "stops tablosunda tekrarlanan stop_id bulundu."
    )

    assert (
        stop_routes.duplicated(
            subset=["stop_id", "route_number"]
        ).sum()
        == 0
    ), (
        "stop_routes tablosunda tekrarlanan "
        "durak-hat ilişkisi bulundu."
    )

    assert len(stops) <= valid_raw_stop_ids, (
        "Temiz durak sayısı geçerli ham durak ID "
        "sayısından büyük olamaz."
    )

    if not stop_routes.empty:
        unknown_stop_count = (
            ~stop_routes["stop_id"]
            .isin(stops["stop_id"])
        ).sum()

        assert unknown_stop_count == 0, (
            "stop_routes içinde stops tablosunda "
            "bulunmayan bir stop_id vardır."
        )

        # stop_routes içinde boş route_number bulunmamalı
        empty_route_number_count = (
            stop_routes["route_number"].isna()
            | (stop_routes["route_number"].astype(str).str.strip() == "")
        ).sum()

        assert empty_route_number_count == 0, (
            "stop_routes içinde boş route_number bulundu."
        )

    # has_valid_coordinate = 1 olan kayıtlarda enlem/boylam dolu olmalı
    valid_coordinate_rows = stops[stops["has_valid_coordinate"] == 1]

    assert (
        valid_coordinate_rows["latitude"].isna().sum() == 0
        and valid_coordinate_rows["longitude"].isna().sum() == 0
    ), (
        "has_valid_coordinate=1 olan bir kayıtta "
        "enlem veya boylam eksik bulundu."
    )

    # Geçerli koordinatlar makul enlem/boylam aralığında olmalı
    assert (
        valid_coordinate_rows["latitude"]
        .between(MIN_LATITUDE, MAX_LATITUDE)
        .all()
    ), (
        "Geçerli işaretlenmiş bir enlem değeri "
        "beklenen aralığın dışında."
    )

    assert (
        valid_coordinate_rows["longitude"]
        .between(MIN_LONGITUDE, MAX_LONGITUDE)
        .all()
    ), (
        "Geçerli işaretlenmiş bir boylam değeri "
        "beklenen aralığın dışında."
    )

    # has_valid_coordinate = 0 olan kayıtların en az bir koordinat
    # sorunu (eksik veya aralık dışı) bulunmalı
    invalid_coordinate_rows = stops[stops["has_valid_coordinate"] == 0]

    has_coordinate_problem = (
        invalid_coordinate_rows["latitude"].isna()
        | invalid_coordinate_rows["longitude"].isna()
        | ~invalid_coordinate_rows["latitude"].between(
            MIN_LATITUDE, MAX_LATITUDE
        )
        | ~invalid_coordinate_rows["longitude"].between(
            MIN_LONGITUDE, MAX_LONGITUDE
        )
    )

    # NaN karşılaştırmaları False değil NA döndürebileceği için
    # eksik değerleri doğrudan sorunlu kabul ediyoruz.
    has_coordinate_problem = has_coordinate_problem.fillna(True)

    assert has_coordinate_problem.all(), (
        "has_valid_coordinate=0 olarak işaretlenmiş ama "
        "hiçbir koordinat sorunu bulunmayan bir kayıt var."
    )

    # 82 hatsız durak = 80 eksik hat + 2 parse edilemeyen hat ile tutarlı mı?
    if not issues.empty:
        missing_route_count = (
            issues["issue_type"] == "Eksik hat bilgisi"
        ).sum()

        invalid_route_count = (
            issues["issue_type"] == "Parse edilemeyen hat değeri"
        ).sum()

        stops_without_routes = (
            ~stops["stop_id"].isin(stop_routes["stop_id"])
        ).sum()

        assert stops_without_routes == missing_route_count + invalid_route_count, (
            "Hat ilişkisi bulunmayan durak sayısı, eksik hat "
            "ve parse edilemeyen hat kayıtlarının toplamıyla "
            "tutarlı değil."
        )

    # İşlenmeyen (reddedilen) her satır için kaynak satır bilgisi
    # korunmuş olmalı
    if not rejected.empty:
        assert rejected["source_row_number"].isna().sum() == 0, (
            "rejected_rows içinde source_row_number eksik bir "
            "kayıt bulundu."
        )

    print("\nKontrol sonuçları:")
    print("- Durak ID değerleri benzersiz: Başarılı")
    print("- Tekrarlı durak-hat ilişkisi yok: Başarılı")
    print("- Durak-hat referans kontrolü: Başarılı")
    print("- Ham ve temiz veri tutarlılığı: Başarılı")
    print("- stop_routes içinde boş route_number yok: Başarılı")
    print("- Geçerli koordinatlar aralık içinde ve dolu: Başarılı")
    print("- Geçersiz koordinatlarda en az bir sorun var: Başarılı")
    print("- Hatsız durak sayısı eksik+parse edilemeyen ile tutarlı: Başarılı")
    print("- Reddedilen satırlarda kaynak satır bilgisi korunmuş: Başarılı")


# ============================================================
# DOSYALARI KAYDETME
# ============================================================

def save_outputs(
    stops,
    stop_routes,
    issues,
    rejected
):
    """
    Temizlenen verileri processed klasörüne kaydeder.
    """

    PROCESSED_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    stops.to_csv(
        STOPS_CLEAN_FILE,
        sep=";",
        index=False,
        encoding="utf-8-sig"
    )

    stop_routes.to_csv(
        STOP_ROUTES_FILE,
        sep=";",
        index=False,
        encoding="utf-8-sig"
    )

    issues.to_csv(
        QUALITY_ISSUES_FILE,
        sep=";",
        index=False,
        encoding="utf-8-sig"
    )

    rejected.to_csv(
        REJECTED_ROWS_FILE,
        sep=";",
        index=False,
        encoding="utf-8-sig"
    )


# ============================================================
# ANA PROGRAM
# ============================================================

def main():
    """
    Veri temizleme sürecini başlatır.
    """

    print("=" * 65)
    print("ESHOT VERİ TEMİZLEME VE DÖNÜŞTÜRME")
    print("=" * 65)

    raw_data = load_raw_data()

    print(f"\nHam veri satır sayısı: {len(raw_data)}")
    print(f"Ham veri sütun sayısı: {len(raw_data.columns)}")

    stops, stop_routes, issues, rejected = clean_data(
        raw_data
    )

    validate_outputs(
        raw_data=raw_data,
        stops=stops,
        stop_routes=stop_routes,
        issues=issues,
        rejected=rejected
    )

    save_outputs(
        stops=stops,
        stop_routes=stop_routes,
        issues=issues,
        rejected=rejected
    )

    valid_stop_id_count = pd.to_numeric(
        raw_data["DURAK_ID"],
        errors="coerce"
    ).notna().sum()

    unique_route_count = (
        stop_routes["route_number"].nunique()
        if not stop_routes.empty
        else 0
    )

    print("\n" + "=" * 65)
    print("VERİ TEMİZLEME SONUÇLARI")
    print("=" * 65)

    print(f"Ham veri satır sayısı       : {len(raw_data)}")
    print(f"Geçerli durak ID sayısı     : {valid_stop_id_count}")
    print(f"Temiz durak sayısı          : {len(stops)}")
    print(f"Benzersiz hat sayısı        : {unique_route_count}")
    print(f"Durak-hat ilişkisi sayısı   : {len(stop_routes)}")
    print(f"Veri kalitesi sorunu sayısı : {len(issues)}")
    print(f"Reddedilen satır sayısı     : {len(rejected)}")

    print("\nOluşturulan dosyalar:")
    print(f"- {STOPS_CLEAN_FILE}")
    print(f"- {STOP_ROUTES_FILE}")
    print(f"- {QUALITY_ISSUES_FILE}")
    print(f"- {REJECTED_ROWS_FILE}")

    print("\nVeri temizleme işlemi başarıyla tamamlandı.")


if __name__ == "__main__":
    main()
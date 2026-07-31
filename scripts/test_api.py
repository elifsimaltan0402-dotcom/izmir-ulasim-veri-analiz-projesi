"""
ESHOT "Durağa Yaklaşan Otobüsler" API testi.

Kullanım:
    python scripts/test_api.py

Bu script API'ye birkaç farklı senaryoda istek atar, sonuçları
terminale yazdırır ve outputs/reports/api_test_results.csv +
outputs/reports/api_test_results.json dosyalarına kaydeder.
"""

from pathlib import Path
from datetime import datetime, timezone
import json

import requests

# ============================================================
# AYARLAR
# ============================================================

PROJECT_DIR = Path(__file__).resolve().parent.parent

REPORTS_DIR = PROJECT_DIR / "outputs" / "reports"

BASE_URL = "https://openapi.izmir.bel.tr/api/iztek/duragayaklasanotobusler/{durak_id}"

TIMEOUT_SECONDS = 10

# stops_clean.csv içinde gerçekten var olan iki geçerli durak ID'si
VALID_STOP_ID_1 = "10005"
VALID_STOP_ID_2 = "10007"

# stops_clean.csv'de kesinlikle bulunmayan, ama sayısal bir ID
UNKNOWN_STOP_ID = "999999999"

# Sayısal olmayan parametre testi
NON_NUMERIC_PARAM = "abc"


# ============================================================
# TEK BİR İSTEĞİ ÇALIŞTIRMA
# ============================================================

def call_api(durak_id, test_name):
    """
    Verilen durak ID'si ile API'ye istek atar.

    Uzun traceback yerine anlaşılır, yapılandırılmış bir
    sonuç sözlüğü döndürür. Hata durumunda programı
    çökertmez.
    """

    url = BASE_URL.format(durak_id=durak_id)

    result = {
        "test_name": test_name,
        "durak_id": durak_id,
        "url": url,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "http_status_code": None,
        "response_time_ms": None,
        "response_shape": None,  # "list" | "object" | "empty" | "none"
        "field_names": None,
        "field_types": None,
        "error_type": None,
        "error_message": None,
        "raw_snippet": None
    }

    try:
        response = requests.get(
            url,
            timeout=TIMEOUT_SECONDS
        )

        result["http_status_code"] = response.status_code
        result["response_time_ms"] = round(
            response.elapsed.total_seconds() * 1000,
            2
        )

        # Response'u güvenli biçimde parse et
        try:
            payload = response.json()
        except ValueError:
            result["response_shape"] = "none"
            result["error_type"] = "JSONDecodeError"
            result["error_message"] = (
                "Response JSON olarak parse edilemedi."
            )
            result["raw_snippet"] = response.text[:200]
            return result

        if isinstance(payload, list):
            if len(payload) == 0:
                result["response_shape"] = "empty"
            else:
                result["response_shape"] = "list"
                first_item = payload[0]
                if isinstance(first_item, dict):
                    result["field_names"] = list(first_item.keys())
                    result["field_types"] = {
                        key: type(value).__name__
                        for key, value in first_item.items()
                    }
        elif isinstance(payload, dict):
            if len(payload) == 0:
                result["response_shape"] = "empty"
            else:
                result["response_shape"] = "object"
                result["field_names"] = list(payload.keys())
                result["field_types"] = {
                    key: type(value).__name__
                    for key, value in payload.items()
                }
        else:
            result["response_shape"] = "none"

        result["raw_snippet"] = json.dumps(payload, ensure_ascii=False)[:300]

    except requests.exceptions.Timeout:
        result["error_type"] = "Timeout"
        result["error_message"] = (
            f"{TIMEOUT_SECONDS} saniye içinde yanıt alınamadı."
        )

    except requests.exceptions.ConnectionError:
        result["error_type"] = "ConnectionError"
        result["error_message"] = (
            "Servise bağlantı kurulamadı "
            "(ağ sorunu veya servis erişilemez durumda)."
        )

    except requests.exceptions.RequestException as error:
        result["error_type"] = type(error).__name__
        result["error_message"] = str(error)

    return result


# ============================================================
# ANA PROGRAM
# ============================================================

def main():
    print("=" * 65)
    print("ESHOT API TESTİ")
    print("=" * 65)

    test_cases = [
        (VALID_STOP_ID_1, "Geçerli durak testi #1"),
        (VALID_STOP_ID_2, "Geçerli durak testi #2 (veri doğrulama)"),
        (UNKNOWN_STOP_ID, "Bilinmeyen/geçersiz durak ID testi"),
        (NON_NUMERIC_PARAM, "Sayısal olmayan parametre testi"),
    ]

    results = []

    for durak_id, test_name in test_cases:
        print(f"\n[ÇALIŞIYOR] {test_name} (durakId={durak_id})")

        result = call_api(durak_id, test_name)
        results.append(result)

        if result["error_type"]:
            print(f"  Sonuç: HATA -> {result['error_type']}: {result['error_message']}")
        else:
            print(f"  HTTP Durum Kodu : {result['http_status_code']}")
            print(f"  Yanıt Süresi    : {result['response_time_ms']} ms")
            print(f"  Yanıt Yapısı    : {result['response_shape']}")
            if result["field_names"]:
                print(f"  Alanlar         : {result['field_names']}")

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    csv_path = REPORTS_DIR / "api_test_results.csv"
    json_path = REPORTS_DIR / "api_test_results.json"

    import csv as csv_module

    fieldnames = list(results[0].keys())

    with open(csv_path, "w", newline="", encoding="utf-8-sig") as csv_file:
        writer = csv_module.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        for row in results:
            row_copy = row.copy()
            row_copy["field_names"] = json.dumps(row_copy["field_names"], ensure_ascii=False)
            row_copy["field_types"] = json.dumps(row_copy["field_types"], ensure_ascii=False)
            writer.writerow(row_copy)

    with open(json_path, "w", encoding="utf-8") as json_file:
        json.dump(results, json_file, ensure_ascii=False, indent=2)

    print("\n" + "=" * 65)
    print("SONUÇ DOSYALARI")
    print("=" * 65)
    print(f"- {csv_path}")
    print(f"- {json_path}")


if __name__ == "__main__":
    main()
 
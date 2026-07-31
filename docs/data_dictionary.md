# Veri Sözlüğü

Bu belge, ham ESHOT durak verisinden temizlenmiş veri setlerine ve
SQLite veritabanı tablolarına kadar tüm alanların kaynağını, dönüşüm
kurallarını ve geçerlilik kriterlerini açıklar.

---

## 1. Ham Veri: `data/raw/eshot-otobus-duraklari.csv`

Ayraç: `;` · Kodlama: `utf-8-sig` · Satır sayısı: 11.783 (+ başlık)

| Kaynak alan adı | Açıklama | Ham veri tipi |
|---|---|---|
| `sDURAK_ID` | Durak kimlik numarası (bazı dosya sürümlerinde bu adla gelir) | metin |
| `DURAK_ADI` | Durak adı | metin |
| `ENLEM` | Enlem (hatalı nokta ayraçlarıyla, örn. `3.841.526.836.260.150`) | metin |
| `BOYLAM` | Boylam (aynı hatalı formatla) | metin |
| `DURAKTAN_GECEN_HATLAR` | Durağa uğrayan hatlar, `-` ile birleşik (örn. `29-30`) | metin |

---

## 2. Alan Bazında Dönüşüm Tablosu

| Kaynak alan | Temiz alan | Açıklama | Ham tip | Hedef tip | Zorunlu/Nullable | Uygulanan dönüşüm | Geçerlilik kuralı | Hatalı değerde işlem | Kullanıldığı tablo/rapor |
|---|---|---|---|---|---|---|---|---|---|
| `sDURAK_ID` | `stop_id` | Durak kimliği | metin | Int64 (nullable) | Zorunlu (temiz tabloda) | `pd.to_numeric(errors="coerce")` ile sayısala çevrilir; `sDURAK_ID` → `DURAK_ID` olarak yeniden adlandırılır | Sayısal olmalı, boş olmamalı | Sayısala çevrilemeyen veya boş ID'ler `stops_clean.csv`'ye alınmaz; `data_quality_issues` ve `rejected_rows.csv`'ye kaydedilir | `stops`, `stop_routes`, `data_quality_issues`, `rejected_rows.csv` |
| `DURAK_ADI` | `stop_name` | Durak adı | metin | string | Zorunlu (NOT NULL) | Baş/son boşluklar temizlenir | Boş olmamalı | Eksik adlar `"Bilinmeyen Durak"` ile doldurulur; olay `data_quality_issues`'a "Eksik durak adı" olarak kaydedilir | `stops` |
| `ENLEM` | `latitude` | Enlem | metin (hatalı nokta ayraçlı) | float (nullable) | Nullable | `parse_coordinate()`: rakamlar çıkarılır, ilk 2 hane tam kısım kabul edilerek yeniden noktalanır (örn. `3841526836260150` → `38.41526836260150`) | 37.0–40.0 aralığında olmalı (İzmir için makul enlem) | Aralık dışı veya çevrilemeyen değerler `NULL` bırakılır; `has_valid_coordinate=0` olur; `data_quality_issues`'a "Geçersiz koordinat" olarak kaydedilir | `stops` |
| `BOYLAM` | `longitude` | Boylam | metin (hatalı nokta ayraçlı) | float (nullable) | Nullable | Aynı `parse_coordinate()` mantığı | 25.0–29.0 aralığında olmalı | Aynı; `data_quality_issues`'a kaydedilir | `stops` |
| *(türetilmiş)* | `has_valid_coordinate` | Enlem VE boylamın ikisinin de geçerli olup olmadığı | — | integer (0/1) | Zorunlu | `valid_latitude AND valid_longitude` | Yalnızca 0 veya 1 | — | `stops` |
| `DURAKTAN_GECEN_HATLAR` | `route_number` (stop_routes içinde, tekrarlı) | Durağa uğrayan hat numarası | metin (`-` ile birleşik) | string | Zorunlu (satır varsa) | `-` karakterine göre bölünür; yalnızca tamamen sayısal parçalar geçerli kabul edilir; aynı durak içinde tekrar edenler tekilleştirilir | Yalnızca rakamlardan oluşmalı (`\d+`) | Boş alan → "Eksik hat bilgisi"; sayısal olmayan parça → "Parse edilemeyen hat değeri"; her iki durumda da `data_quality_issues`'a kaydedilir, durak `stop_routes`'a alınmaz veya ilgili parça atlanır | `stop_routes`, `data_quality_issues` |

---

## 3. Temizlenmiş Dosyalar

### 3.1 `data/processed/stops_clean.csv`

Ayraç: `;` · Kodlama: `utf-8-sig` · Birincil anahtar: `stop_id`

| Alan | Tip | Açıklama |
|---|---|---|
| `stop_id` | Int64 | Benzersiz durak kimliği |
| `stop_name` | string | Durak adı (eksikse `"Bilinmeyen Durak"`) |
| `latitude` | float / NULL | Geçerliyse enlem, değilse boş |
| `longitude` | float / NULL | Geçerliyse boylam, değilse boş |
| `has_valid_coordinate` | int (0/1) | Enlem ve boylamın ikisi de geçerliyse 1 |

### 3.2 `data/processed/stop_routes.csv`

Durak–hat çoktan-çoğa ilişki tablosu.

| Alan | Tip | Açıklama |
|---|---|---|
| `stop_id` | Int64 | `stops_clean.csv`'deki `stop_id`'ye referans |
| `route_number` | string | Tek bir hat numarası |

Bileşik benzersizlik: (`stop_id`, `route_number`) çifti tekrarlanamaz.

### 3.3 `data/processed/data_quality_issues.csv`

Temizleme sırasında tespit edilen her sorunun kaydı.

| Alan | Tip | Açıklama |
|---|---|---|
| `issue_type` | string | Sorun kategorisi (örn. "Geçersiz koordinat") |
| `stop_id` | Int64 / NULL | İlgili durak kimliği (ID'nin kendisi sorunluysa boş) |
| `field_name` | string | Sorunlu kaynak alan adı |
| `raw_value` | string / NULL | Sorunun tespit edildiği ham değer |
| `description` | string | Sorunun açık metinle açıklaması |
| `source_row_number` | int | Ham CSV'deki orijinal satır numarası (başlık = 1, ilk veri satırı = 2) |

### 3.4 `data/processed/rejected_rows.csv`

Durak ID'si eksik/geçersiz olduğu için **tamamen** temiz veri setine
alınamayan satırların tam kaydı (yalnızca hatalı alan değil, satırın
tamamı saklanır).

| Alan | Tip | Açıklama |
|---|---|---|
| `source_row_number` | int | Ham CSV'deki orijinal satır numarası |
| `DURAK_ID` (ham) | string | Ham durak ID değeri (varsa) |
| `DURAK_ADI` | string | Ham durak adı |
| `ENLEM` | string | Ham enlem |
| `BOYLAM` | string | Ham boylam |
| `DURAKTAN_GECEN_HATLAR` | string | Ham hat bilgisi |
| `rejection_reason` | string | Satırın neden tamamen dışarıda bırakıldığı |

---

## 4. SQLite Veritabanı Şeması (`database/eshot_analytics.db`)

### `stops`
| Alan | Tip | Kısıt |
|---|---|---|
| `stop_id` | INTEGER | PRIMARY KEY |
| `stop_name` | TEXT | NOT NULL |
| `latitude` | REAL | NULL olabilir |
| `longitude` | REAL | NULL olabilir |
| `has_valid_coordinate` | INTEGER | NOT NULL, CHECK (0 veya 1) |

### `routes`
| Alan | Tip | Kısıt |
|---|---|---|
| `route_number` | TEXT | PRIMARY KEY |

### `stop_routes`
| Alan | Tip | Kısıt |
|---|---|---|
| `stop_id` | INTEGER | FOREIGN KEY → `stops(stop_id)` |
| `route_number` | TEXT | FOREIGN KEY → `routes(route_number)` |
| — | — | PRIMARY KEY (`stop_id`, `route_number`) |

### `data_quality_issues`
| Alan | Tip | Kısıt |
|---|---|---|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT |
| `issue_type` | TEXT | — |
| `stop_id` | INTEGER | — |
| `field_name` | TEXT | — |
| `raw_value` | TEXT | — |
| `description` | TEXT | — |
| `source_row_number` | INTEGER | — |

**İndeksler:** `idx_stops_stop_name`, `idx_stop_routes_stop_id`,
`idx_stop_routes_route_number`, `idx_quality_issues_issue_type`.

**İlişkiler:** `stop_routes.stop_id → stops.stop_id` (ON DELETE CASCADE),
`stop_routes.route_number → routes.route_number` (ON DELETE CASCADE).
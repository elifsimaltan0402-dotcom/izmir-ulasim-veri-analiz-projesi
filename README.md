# İzmir ESHOT Ulaşım Veri Analizi

## Projenin Amacı

Bu proje, İzmir ESHOT otobüs durak verilerinin uçtan uca bir veri analizi süreciyle işlenmesini amaçlamaktadır.

Proje kapsamında;

- Ham CSV verisi Python ve Pandas kullanılarak temizlenmiştir.
- Veri kalitesi sorunları tespit edilerek raporlanmıştır.
- Durak ve hat bilgileri normalleştirilmiş bir SQLite veritabanına aktarılmıştır.
- Temel ve gelişmiş SQL analizleri gerçekleştirilmiştir.
- Durak-hat ilişkileri NetworkX kullanılarak ağ yapısı olarak analiz edilmiştir.
- Analiz sonuçları CSV raporları ve PNG grafikler olarak üretilmiştir.
- Streamlit tabanlı etkileşimli bir dashboard geliştirilmiştir.
- ESHOT'un canlı **"Durağa Yaklaşan Otobüsler"** API servisi test edilmiştir.
- Tüm veri işleme adımları tek komutla çalıştırılabilen bir pipeline içerisinde birleştirilmiştir.
- Otomatik testler ve pipeline doğrulama kontrolleri hazırlanmıştır.

---

## Veri Kaynağı

Projede İzmir Büyükşehir Belediyesi Açık Veri Portalı tarafından yayımlanan **ESHOT Otobüs Durakları** veri kümesi kullanılmıştır.

**Ham veri dosyası**

```text
data/raw/eshot-otobus-duraklari.csv
```

**ESHOT canlı API adresi**

```text
https://openapi.izmir.bel.tr/api/iztek/duragayaklasanotobusler/{durakId}
```

---

## Proje Klasör Yapısı

```text
eshot_analytics_project3/
│
├── .gitignore
├── app.py
├── README.md
├── requirements.txt
├── run_pipeline.py
│
├── data/
│   ├── raw/
│   │   └── eshot-otobus-duraklari.csv
│   │
│   └── processed/
│       ├── stops_clean.csv
│       ├── stop_routes.csv
│       ├── data_quality_issues.csv
│       └── rejected_rows.csv
│
├── database/
│   └── eshot_analytics.db
│
├── docs/
│   ├── api_test_report.md
│   ├── data_dictionary.md
│   ├── performance_report.md
│   └── screenshots/
│
├── outputs/
│   ├── charts/
│   │   ├── top_10_routes.png
│   │   ├── top_10_stops.png
│   │   ├── data_quality_summary.png
│   │   ├── top_15_transfer_hubs.png
│   │   ├── top_15_route_pairs_shared_stops.png
│   │   └── stop_route_count_distribution.png
│   │
│   ├── logs/
│   │   └── pipeline_YYYY-MM-DD_HH-MM-SS.log
│   │
│   └── reports/
│       ├── pipeline_summary.json
│       ├── top_10_routes.csv
│       ├── top_10_stops.csv
│       ├── data_quality_summary.csv
│       ├── duplicate_stop_names.csv
│       ├── route_stop_counts.csv
│       ├── stops_with_more_than_five_routes.csv
│       ├── network_summary.csv
│       ├── top_transfer_hubs.csv
│       ├── route_pairs_shared_stops.csv
│       ├── connected_components.csv
│       ├── isolated_stops.csv
│       ├── network_top_routes.csv
│       ├── api_test_results.csv
│       ├── api_test_results.json
│       ├── advanced_sql/
│       └── network/
│
├── scripts/
│   ├── clean_data.py
│   ├── build_database.py
│   ├── run_analysis.py
│   ├── run_advanced_analysis.py
│   ├── network_analysis.py
│   ├── run_network_analysis.py
│   ├── validate_pipeline.py
│   └── test_api.py
│
├── sql/
│   ├── schema.sql
│   ├── analysis_queries.sql
│   └── advanced_analysis.sql
│
└── tests/
```

---

## Kullanılan Teknolojiler

Projede aşağıdaki teknolojiler kullanılmıştır:

- Python 3.13.5
- Pandas
- SQLite
- SQL
- Streamlit
- Matplotlib
- Requests
- NetworkX
- Pytest

SQLite bağlantısı Python'un standart kütüphanesinde bulunan **sqlite3** modülü ile sağlanmaktadır.

---

## Gereksinimler

`requirements.txt` içeriği:

```text
pandas==3.0.3
matplotlib==3.11.1
streamlit==1.59.2
requests==2.34.2
networkx
pytest
```

Gerekli paketleri kurmak için:

```bash
python -m pip install -r requirements.txt
```

---

## Veritabanı Yapısı

Projede dört temel tablo kullanılmaktadır.

### `stops`

Duraklara ait temel bilgileri içerir.

| Alan | Açıklama |
|------|----------|
| `stop_id` | Benzersiz durak kimliği |
| `stop_name` | Durak adı |
| `latitude` | Enlem |
| `longitude` | Boylam |
| `has_valid_coordinate` | Koordinat geçerlilik bilgisi |

`has_valid_coordinate` alanı yalnızca aşağıdaki değerleri alır:

- `1` → Koordinat geçerli
- `0` → Koordinat geçersiz

---

### `routes`

Benzersiz ESHOT hat numaralarını içerir.

| Alan | Açıklama |
|------|----------|
| `route_number` | Hat numarası |

---

### `stop_routes`

Duraklar ve hatlar arasındaki çoktan çoğa ilişkiyi içerir.

Alanlar:

- `stop_id`
- `route_number`

Birleşik birincil anahtar:

```text
stop_id + route_number
```

Yabancı anahtarlar:

- `stop_id` → `stops.stop_id`
- `route_number` → `routes.route_number`

İlişkili kayıtlar **ON DELETE CASCADE** kuralı ile yönetilir.

---

### `data_quality_issues`

Veri temizleme sırasında tespit edilen sorunları içerir.

| Alan |
|------|
| `id` |
| `issue_type` |
| `stop_id` |
| `field_name` |
| `raw_value` |
| `description` |
| `source_row_number` |

`source_row_number` alanı sayesinde tespit edilen her veri kalitesi sorunu ham CSV dosyasındaki orijinal satırına kadar izlenebilmektedir.

---

## Veritabanı İndeksleri

Sorgu performansını artırmak amacıyla aşağıdaki indeksler oluşturulmuştur.

- `idx_stops_stop_name`
- `idx_stop_routes_stop_id`
- `idx_stop_routes_route_number`
- `idx_quality_issues_issue_type`

---
## Veri Temizleme Süreci

Ham veri `scripts/clean_data.py` dosyası kullanılarak temizlenmektedir.

### Durak Kimliği Kontrolleri

- Durak kimlikleri sayısal veri tipine dönüştürülmektedir.
- Eksik veya geçersiz durak kimlikleri tespit edilmektedir.
- Geçerli durak kimliği bulunmayan kayıtlar temiz veri setine alınmamaktadır.
- Reddedilen kayıtların tamamı `rejected_rows.csv` dosyasında saklanmaktadır.
- Tekrarlanan durak kimliklerinde ilk kayıt korunmaktadır.

### Durak Adı Kontrolleri

- Gereksiz boşluk karakterleri temizlenmektedir.
- Eksik durak adları veri kalitesi sorunu olarak raporlanmaktadır.
- Gerekli durumlarda eksik adlar **"Bilinmeyen Durak"** değeriyle doldurulmaktadır.

### Koordinat Kontrolleri

- Enlem ve boylam değerleri sayısal veri tipine dönüştürülmektedir.
- Hatalı nokta ayrımları düzeltilmektedir.
- Enlem için `37.0–40.0`, boylam için `25.0–29.0` aralıkları kullanılmaktadır.
- Eksik, dönüştürülemeyen veya aralık dışında kalan koordinatlar geçersiz kabul edilmektedir.
- Geçersiz koordinatlar temiz veri içerisinde boş bırakılmaktadır.
- Her kayıt için `has_valid_coordinate` alanı oluşturulmaktadır.

### Hat Bilgisi Kontrolleri

- Birleşik hat değerleri `-` karakterine göre ayrıştırılmaktadır.
- Her hat ayrı bir durak-hat ilişkisine dönüştürülmektedir.
- Tekrarlanan hat değerleri tekilleştirilmektedir.
- Sayısal olmayan hat değerleri veri kalitesi sorunu olarak raporlanmaktadır.
- Hat bilgisi bulunmayan duraklar ayrıca kaydedilmektedir.

---

## Veri Temizleme Sonuçları

Son başarılı pipeline çalışmasında elde edilen temel sonuçlar aşağıdaki gibidir.

| Ölçüt | Değer |
|------|------:|
| Ham veri satırı | 11.783 |
| Temiz durak | 11.782 |
| Benzersiz hat | 441 |
| Durak-hat ilişkisi | 31.356 |
| Veri kalitesi sorunu | 89 |
| Reddedilen kayıt | 1 |
| Geçerli koordinat | 11.776 |
| Geçersiz koordinat | 6 |
| Hat bilgisi olmayan durak | 82 |

### Veri Setinde Tespit Edilen Sorunlar

- 80 kayıtta hat bilgisi tamamen eksiktir.
- 2 kayıtta hat bilgisi ayrıştırılamamıştır.
- Toplam 82 durak geçerli bir hat ilişkisine sahip değildir.
- 6 kayıtta koordinat sorunu bulunmaktadır.
- 1 kayıt geçersiz veya eksik durak kimliği nedeniyle reddedilmiştir.

---

## Temizleme Sonucunda Üretilen Dosyalar

### `stops_clean.csv`

Temizlenmiş durak bilgilerini içerir.

```text
data/processed/stops_clean.csv
```

---

### `stop_routes.csv`

Her satır tek bir durak-hat ilişkisini temsil etmektedir.

```text
data/processed/stop_routes.csv
```

---

### `data_quality_issues.csv`

Veri temizleme sırasında tespit edilen tüm veri kalitesi sorunlarını içermektedir.

```text
data/processed/data_quality_issues.csv
```

---

### `rejected_rows.csv`

Temiz veri setine alınamayan satırların tamamını ve reddedilme nedenlerini içermektedir.

```text
data/processed/rejected_rows.csv
```

---

## Veritabanının Oluşturulması

Temizlenmiş CSV dosyaları `scripts/build_database.py` dosyası kullanılarak SQLite veritabanına aktarılmaktadır.

Oluşturulan veritabanı:

```text
database/eshot_analytics.db
```

Veritabanı oluşturma sürecinde;

- Veritabanı şeması yeniden oluşturulmaktadır.
- Yabancı anahtar kontrolleri etkinleştirilmektedir.
- Temiz duraklar, hatlar ve durak-hat ilişkileri aktarılmaktadır.
- Veri kalitesi sorunları veritabanına kaydedilmektedir.
- Birincil ve yabancı anahtar kontrolleri uygulanmaktadır.
- Performans için gerekli indeksler oluşturulmaktadır.
- Kayıt sayıları doğrulanmaktadır.
- Scriptin yeniden çalıştırılabilir olduğu kontrol edilmektedir.

---

## SQL Şeması

Temel veritabanı şeması aşağıdaki dosyada bulunmaktadır.

```text
sql/schema.sql
```

Bu dosyada;

- Tablo tanımları
- Birincil anahtarlar
- Yabancı anahtarlar
- Birleşik birincil anahtar
- `ON DELETE CASCADE` kuralları
- Kontrol kısıtları
- Performans indeksleri

yer almaktadır.

---

## Temel SQL Analizleri

Temel analiz sorguları:

```text
sql/analysis_queries.sql
```

Analiz scripti:

```text
scripts/run_analysis.py
```

### Gerçekleştirilen Analizler

- Toplam durak sayısı
- Geçerli koordinata sahip durak sayısı
- Geçersiz koordinata sahip durak sayısı
- Hat bilgisi bulunmayan durak sayısı
- Toplam benzersiz hat sayısı
- Toplam durak-hat ilişkisi
- Toplam veri kalitesi sorunu
- En fazla duraktan geçen ilk 10 hat
- En fazla hattın geçtiği ilk 10 durak
- Aynı isimli farklı durakların analizi
- Her hattın geçtiği durak sayısı
- Yalnızca bir hattın geçtiği durakların sayısı
- Beşten fazla hattın geçtiği durakların listelenmesi
- Veri kalitesi sorunlarının türlerine göre dağılımı

### Çalıştırma Komutu

```bash
python scripts/run_analysis.py
```

Bu script çalıştırıldığında;

- SQL sorguları SQLite veritabanı üzerinde çalıştırılır.
- Sonuçlar terminale yazdırılır.
- CSV raporları oluşturulur.
- Grafikler PNG formatında kaydedilir.

---
## Gelişmiş SQL Analizleri

Gelişmiş SQL analizleri `scripts/run_advanced_analysis.py` dosyası kullanılarak gerçekleştirilmektedir.

Bu analizlerde standart SQL sorgularına ek olarak daha gelişmiş sorgu tekniklerinden yararlanılmıştır.

### Kullanılan SQL Yapıları

- Common Table Expression (CTE)
- Self Join
- GROUP BY
- HAVING
- Window Functions
- Ranking fonksiyonları
- Çoklu JOIN işlemleri
- Alt sorgular (Subquery)

### Gerçekleştirilen Analizler

- Her durağın geçtiği hat sayısı
- Her hattın geçtiği durak sayısı
- Aktarma merkezi (transfer stop) analizi
- En yoğun aktarma durakları
- Aynı durağı paylaşan hat çiftleri
- Ortak durak sayılarına göre hat çiftlerinin sıralanması
- Hat bulunmayan durakların belirlenmesi
- Geçersiz koordinata sahip durakların listelenmesi
- Aynı isimli durakların gelişmiş analizi

### Oluşturulan Raporlar

```text
outputs/reports/advanced_sql/stop_route_counts.csv
outputs/reports/advanced_sql/route_stop_counts_advanced.csv
outputs/reports/advanced_sql/transfer_stops.csv
outputs/reports/advanced_sql/top_transfer_stops.csv
outputs/reports/advanced_sql/route_pairs_by_stop.csv
outputs/reports/advanced_sql/route_pair_common_stop_counts.csv
outputs/reports/advanced_sql/top_route_pairs.csv
outputs/reports/advanced_sql/stops_without_routes.csv
outputs/reports/advanced_sql/invalid_coordinate_stops.csv
outputs/reports/advanced_sql/duplicate_stop_names_advanced.csv
```

Son başarılı çalışmada **10 adet gelişmiş SQL view'ı** oluşturulmuştur.

---

# Ağ Analizleri

Projede birbirini tamamlayan iki farklı ağ analizi uygulanmıştır.

## Hatlar Arası Bağlantı Analizi

Bu analiz `scripts/network_analysis.py` dosyası ile gerçekleştirilmektedir.

Analizde aynı duraklardan geçen ESHOT hatları birbirleriyle bağlantılı kabul edilmektedir.

Bu sayede;

- En bağlantılı hatlar
- Hatların bağlantı dereceleri
- Ortak duraklar üzerinden oluşan ağ yapısı

incelenmektedir.

### Üretilen Dosyalar

```text
outputs/reports/network/route_connections.csv
outputs/reports/network/top_network_routes.csv
outputs/reports/network/network_summary.json
```

### Son Başarılı Çalışma Sonuçları

| Ölçüt | Değer |
|------|------:|
| Analiz edilen hat | 441 |
| Hat bağlantısı | 6.568 |
| En bağlantılı hat | 200 |
| En yüksek bağlantı derecesi | 96 |

---

## NetworkX Tabanlı Hat–Durak Analizi

Bu analiz `scripts/run_network_analysis.py` dosyası kullanılarak gerçekleştirilmektedir.

Analizde;

- Duraklar bir düğüm (Node)
- Hatlar ikinci bir düğüm türü

olarak modellenmiş ve iki parçalı (Bipartite) ağ oluşturulmuştur.

### Son Başarılı Çalışma Sonuçları

| Ölçüt | Değer |
|------|------:|
| Toplam düğüm | 12.223 |
| Durak düğümü | 11.782 |
| Hat düğümü | 441 |
| Toplam bağlantı | 31.356 |
| Bağlantılı bileşen | 83 |
| En büyük bileşen | 12.141 |
| İzole durak | 82 |

### Oluşturulan Raporlar

```text
outputs/reports/network_summary.csv
outputs/reports/top_transfer_hubs.csv
outputs/reports/route_pairs_shared_stops.csv
outputs/reports/connected_components.csv
outputs/reports/isolated_stops.csv
outputs/reports/network_top_routes.csv
```

### Oluşturulan Grafikler

```text
outputs/charts/top_15_transfer_hubs.png
outputs/charts/top_15_route_pairs_shared_stops.png
outputs/charts/stop_route_count_distribution.png
```

---

# Pipeline

Projedeki tüm veri işleme süreci tek komutla çalıştırılabilmektedir.

Çalıştırma komutu:

```bash
python run_pipeline.py
```

Pipeline aşağıdaki sırayla çalışmaktadır:

```text
1. clean_data.py
2. build_database.py
3. run_analysis.py
4. run_advanced_analysis.py
5. network_analysis.py
6. run_network_analysis.py
7. validate_pipeline.py
```

Pipeline aşağıdaki işlemleri otomatik olarak gerçekleştirir:

- Veri temizleme
- SQLite veritabanının oluşturulması
- Temel SQL analizleri
- Gelişmiş SQL analizleri
- Hat bağlantı analizi
- NetworkX ağ analizi
- Pipeline doğrulama kontrolleri

Ek olarak;

- Her scriptin çalışma süresi ölçülmektedir.
- Terminal ve dosya tabanlı log oluşturulmaktadır.
- Herhangi bir hata oluşursa sonraki adımlar durdurulmaktadır.
- Çalışma sonunda JSON formatında özet rapor oluşturulmaktadır.

### Log Dosyaları

```text
outputs/logs/
```

### Pipeline Özeti

```text
outputs/reports/pipeline_summary.json
```

Son başarılı çalışmada pipeline yaklaşık **15,34 saniyede** tamamlanmıştır.

---

# Pipeline Doğrulaması

Doğrulama işlemleri `scripts/validate_pipeline.py` dosyası tarafından gerçekleştirilmektedir.

Bu script aşağıdaki kontrolleri yapmaktadır:

- Gerekli çıktı dosyalarının oluşturulup oluşturulmadığı
- Veritabanı tablolarındaki kayıt sayıları
- Koordinat bilgilerinin doğruluğu
- Ağ analizi raporlarının tutarlılığı
- Hat bağlantılarının doğrulanması
- Üretilen raporların eksiksiz olması

Son başarılı doğrulama sonucunda:

- ✅ 16 gerekli dosya doğrulanmıştır.
- ✅ Veritabanı kontrolleri başarıyla geçmiştir.
- ✅ Ağ analizi kontrolleri başarıyla tamamlanmıştır.
- ✅ Pipeline eksiksiz şekilde doğrulanmıştır.

---
## ESHOT API Testi

Projede İzmir Büyükşehir Belediyesi tarafından sunulan **"Durağa Yaklaşan Otobüsler"** servisi test edilmiştir.

### Test Edilen Endpoint

```text
GET https://openapi.izmir.bel.tr/api/iztek/duragayaklasanotobusler/{durakId}
```

### Gerçekleştirilen Testler

- Geçerli durak kimliği testi
- Farklı bir geçerli durak testi
- Veri dönmeyen durak testi
- Geçersiz durak kimliği testi
- Sayısal olmayan parametre testi
- HTTP hata kodlarının incelenmesi
- Timeout yönetimi
- Bağlantı hatası yönetimi
- Boş sonuç ile gerçek hata durumunun ayrıştırılması
- Dönen JSON yapısının doğrulanması

### Test Edilen Alanlar

API yanıtında aşağıdaki temel alanlar incelenmiştir:

| Alan | Veri Tipi |
|------|-----------|
| Hat numarası | String |
| Araç plakası | String |
| Tahmini varış süresi | Integer |
| Durak bilgisi | String |
| Yön bilgisi | String |

Test sonuçları aşağıdaki dosyalarda saklanmaktadır.

```text
outputs/reports/api_test_results.csv
outputs/reports/api_test_results.json
```

Ayrıntılı test raporu:

```text
docs/api_test_report.md
```

API testleri aşağıdaki komut ile tekrar çalıştırılabilir.

```bash
python scripts/test_api.py
```

---

## Veri Sözlüğü

Projede kullanılan tüm veri alanlarının açıklamaları aşağıdaki dokümanda yer almaktadır.

```text
docs/data_dictionary.md
```

Veri sözlüğünde;

- CSV dosyasındaki tüm sütunlar
- SQLite tablo alanları
- Veri tipleri
- Alan açıklamaları
- Kullanım amaçları

ayrıntılı olarak açıklanmaktadır.

---

## Streamlit Dashboard

Analiz sonuçlarının etkileşimli olarak görüntülenebilmesi amacıyla Streamlit tabanlı bir dashboard geliştirilmiştir.

Dashboard aşağıdaki bilgileri sunmaktadır:

- Genel istatistikler
- Durak sayıları
- Hat sayıları
- Veri kalitesi özeti
- Grafikler
- SQL analiz sonuçları
- Ağ analizi sonuçları

Dashboard aşağıdaki komut ile başlatılabilir.

```bash
streamlit run app.py
```

---

## Otomatik Testler

Projede temel doğrulama testleri **Pytest** kullanılarak hazırlanmıştır.

Testler aşağıdaki komut ile çalıştırılabilir.

```bash
pytest
```

Son başarılı çalışmada:

```text
47 passed
```

sonucu elde edilmiştir.

Testler aşağıdaki kontrolleri kapsamaktadır:

- Veri temizleme doğrulamaları
- Veritabanı oluşturma kontrolleri
- SQL sorguları
- Ağ analizi doğrulamaları
- Pipeline doğrulaması
- Yardımcı fonksiyon testleri

---

## Projenin Çalıştırılması

Projeyi sıfırdan çalıştırmak için aşağıdaki adımlar uygulanmalıdır.

### 1. Depoyu klonlayın

```bash
git clone <repository-url>
```

### 2. Proje klasörüne girin

```bash
cd eshot_analytics_project3
```

### 3. Gerekli paketleri yükleyin

```bash
python -m pip install -r requirements.txt
```

### 4. Tüm pipeline'ı çalıştırın

```bash
python run_pipeline.py
```

### 5. Dashboard'u başlatın

```bash
streamlit run app.py
```

---

## Veri Akışı

Projedeki veri işleme süreci aşağıdaki sırayla ilerlemektedir.

```text
Ham CSV
    │
    ▼
Veri Temizleme
    │
    ▼
Temiz CSV Dosyaları
    │
    ▼
SQLite Veritabanı
    │
    ▼
Temel SQL Analizleri
    │
    ▼
Gelişmiş SQL Analizleri
    │
    ▼
Ağ Analizi
    │
    ▼
Grafikler ve Raporlar
    │
    ▼
Streamlit Dashboard
```

---

## İlişkisel Veri Modeli

Veritabanı aşağıdaki ilişki yapısına sahiptir.

```text
Stops
   │
   │ 1
   │
   │
StopRoutes
   │
   │ N
   │
Routes
```

Her duraktan birden fazla hat geçebilir.

Her hat birçok duraktan geçebilir.

Bu nedenle **Stops** ile **Routes** tabloları arasında **çoktan çoğa (Many-to-Many)** ilişki bulunmaktadır.

Bu ilişki **StopRoutes** ara tablosu kullanılarak kurulmuştur.

---
## Veri Kalitesi Yaklaşımı

Projede veri kalitesini artırmak amacıyla sistematik bir veri doğrulama süreci uygulanmıştır.

Kontrol edilen başlıca veri kalitesi kriterleri şunlardır:

- Eksik durak kimlikleri
- Yinelenen durak kayıtları
- Eksik durak adları
- Geçersiz koordinatlar
- Hatalı enlem ve boylam değerleri
- Eksik hat bilgileri
- Sayısal olmayan hat numaraları
- Ayrıştırılamayan hat listeleri

Tespit edilen tüm veri kalitesi sorunları `data_quality_issues` tablosunda saklanmakta ve ayrıca CSV formatında raporlanmaktadır.

Bu yaklaşım sayesinde;

- Ham veri korunmuştur.
- Temiz veri seti analizlerde güvenle kullanılabilir hâle getirilmiştir.
- Veri kaybı en aza indirilmiştir.
- Tüm veri kalitesi sorunları izlenebilir şekilde kayıt altına alınmıştır.

---

## Performans Raporu

Pipeline çalıştırıldıktan sonra performans bilgileri otomatik olarak raporlanmaktadır.

Performans raporu aşağıdaki dosyada yer almaktadır.

```text
docs/performance_report.md
```

Raporda aşağıdaki bilgiler bulunmaktadır:

- Her scriptin çalışma süresi
- Toplam pipeline süresi
- Üretilen dosya sayısı
- Veritabanı kayıt sayıları
- Analiz çıktılarının özeti

Son başarılı çalışmada pipeline yaklaşık **15,34 saniyede** tamamlanmıştır.

---

## Olası Hatalar ve Çözümleri

### `ModuleNotFoundError`

Gerekli Python paketleri yüklenmemiş olabilir.

Çözüm:

```bash
python -m pip install -r requirements.txt
```

---

### `Database is locked`

SQLite veritabanı başka bir uygulama tarafından kullanılmaktadır.

Çözüm:

- SQLite Viewer uygulamasını kapatın.
- Açık bağlantıları sonlandırın.
- Pipeline'ı tekrar çalıştırın.

---

### CSV Dosyası Bulunamadı

Ham veri dosyası beklenen dizinde bulunmamaktadır.

Kontrol edilmesi gereken konum:

```text
data/raw/eshot-otobus-duraklari.csv
```

---

### Streamlit Açılmıyor

Dashboard başlatılamıyorsa aşağıdaki komut kullanılmalıdır.

```bash
streamlit run app.py
```

Ayrıca Streamlit'in kurulu olduğundan emin olun.

---

## Geliştirme Fikirleri

Proje gelecekte aşağıdaki geliştirmelerle genişletilebilir:

- PostgreSQL desteğinin eklenmesi
- Gerçek zamanlı API verilerinin veritabanına kaydedilmesi
- Zaman serisi analizlerinin yapılması
- Coğrafi analizler için GeoPandas entegrasyonu
- Etkileşimli harita görselleştirmeleri
- Daha kapsamlı veri kalite kurallarının eklenmesi
- Docker desteği
- CI/CD süreçlerinin GitHub Actions ile otomatikleştirilmesi

---

## Kazanılan Yetkinlikler

Bu proje kapsamında aşağıdaki teknik beceriler geliştirilmiştir:

### Python

- Pandas ile veri işleme
- Dosya yönetimi
- Hata yönetimi
- Modüler programlama
- Logging kullanımı

### SQL

- SQLite veritabanı yönetimi
- JOIN işlemleri
- GROUP BY
- HAVING
- Window Functions
- Common Table Expressions (CTE)
- İndeks oluşturma
- Performans odaklı sorgu yazımı

### Veri Analizi

- Veri temizleme
- Veri doğrulama
- Veri kalitesi analizi
- İstatistiksel özet oluşturma
- Rapor üretimi

### Ağ Analizi

- NetworkX kullanımı
- Bipartite graph oluşturma
- Bağlantılı bileşen analizi
- Derece (Degree) analizi
- Aktarma merkezi analizi

### Görselleştirme

- Matplotlib ile grafik üretimi
- Streamlit dashboard geliştirme

### Yazılım Geliştirme

- Modüler proje yapısı oluşturma
- Pipeline geliştirme
- Otomatik test yazımı
- Proje dokümantasyonu hazırlama
- Git ve GitHub ile sürüm kontrolü

---

## Sonuç

Bu projede İzmir ESHOT açık veri kümesi kullanılarak uçtan uca bir veri analizi süreci geliştirilmiştir.

Ham verinin temizlenmesiyle başlayan süreç; SQLite veritabanının oluşturulması, SQL analizlerinin gerçekleştirilmesi, ağ analizlerinin uygulanması, grafik ve raporların üretilmesi, Streamlit dashboard'un hazırlanması ve canlı ESHOT API servisinin test edilmesiyle tamamlanmıştır.

Bunun yanı sıra tüm süreç tek komutla çalıştırılabilen bir pipeline yapısına dönüştürülmüş, otomatik doğrulama mekanizmaları ve testler eklenerek projenin güvenilirliği artırılmıştır.

Ortaya çıkan çalışma; veri temizleme, veritabanı tasarımı, SQL, Python, ağ analizi, görselleştirme ve yazılım geliştirme süreçlerini bir araya getiren kapsamlı bir veri analizi projesi niteliğindedir.
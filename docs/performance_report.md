# ESHOT Performans ve Doğrulama Raporu

## 1. Amaç

Bu rapor, ESHOT veri analizi pipeline'ının çalışma sürelerini ölçmek ve ardışık çalıştırmalarda veri bütünlüğü ile çıktıların yeniden üretilebilirliğini doğrulamak amacıyla hazırlanmıştır.

**Rapor oluşturma zamanı:** 24.07.2026 15:23:31
**Ardışık çalıştırma sayısı:** 2

## 2. Performans Sonuçları

| Aşama | 1. çalıştırma (sn) | 2. çalıştırma (sn) | Ortalama (sn) |
|---|---:|---:|---:|
| Veri temizleme | 3.3488 | 2.6169 | 2.9828 |
| Veritabanı oluşturma | 1.1574 | 1.1112 | 1.1343 |
| SQL analizleri | 4.4320 | 4.1529 | 4.2924 |
| Ağ analizi | 3.8344 | 4.2641 | 4.0492 |
| Pipeline toplam süresi | 12.7873 | 12.1460 | 12.4666 |

### SQL analizi ayrıntısı

| Çalıştırma | Temel SQL (sn) | Gelişmiş SQL (sn) | Toplam SQL (sn) |
|---:|---:|---:|---:|
| 1 | 2.9056 | 1.5264 | 4.4320 |
| 2 | 2.7049 | 1.4480 | 4.1529 |

## 3. Kayıt Sayısı Tutarlılığı

| Tablo | 1. çalıştırma | 2. çalıştırma | Değişmedi mi? |
|---|---:|---:|:---:|
| `stops` | 11782 | 11782 | ✅ |
| `routes` | 441 | 441 | ✅ |
| `stop_routes` | 31356 | 31356 | ✅ |
| `data_quality_issues` | 89 | 89 | ✅ |

**Sonuç:** Kayıt sayıları iki çalıştırmada da değişmemiştir. ✅

## 4. Raporların Yeniden Üretilebilirliği

Her çalıştırmadan önce `outputs/reports` ve `outputs/charts` altındaki eski üretilmiş dosyalar silinmiş, ardından analiz scriptleri çalıştırılmıştır. Böylece dosyaların korunması değil, gerçekten yeniden oluşturulması doğrulanmıştır.

- 1. çalıştırmada üretilen dosya sayısı: **28**
- 2. çalıştırmada üretilen dosya sayısı: **28**
- İki çalıştırmada üretilen dosya kümeleri aynıdır: **Evet ✅**
- Üretilen dosyaların tamamı boş değildir: **Evet ✅**

### Yeniden üretilen dosyalar

- `outputs/charts/data_quality_summary.png`
- `outputs/charts/stop_route_count_distribution.png`
- `outputs/charts/top_10_routes.png`
- `outputs/charts/top_10_stops.png`
- `outputs/charts/top_15_route_pairs_shared_stops.png`
- `outputs/charts/top_15_transfer_hubs.png`
- `outputs/reports/advanced_sql/duplicate_stop_names_advanced.csv`
- `outputs/reports/advanced_sql/invalid_coordinate_stops.csv`
- `outputs/reports/advanced_sql/route_pair_common_stop_counts.csv`
- `outputs/reports/advanced_sql/route_pairs_by_stop.csv`
- `outputs/reports/advanced_sql/route_stop_counts_advanced.csv`
- `outputs/reports/advanced_sql/stop_route_counts.csv`
- `outputs/reports/advanced_sql/stops_without_routes.csv`
- `outputs/reports/advanced_sql/top_route_pairs.csv`
- `outputs/reports/advanced_sql/top_transfer_stops.csv`
- `outputs/reports/advanced_sql/transfer_stops.csv`
- `outputs/reports/connected_components.csv`
- `outputs/reports/data_quality_summary.csv`
- `outputs/reports/duplicate_stop_names.csv`
- `outputs/reports/isolated_stops.csv`
- `outputs/reports/network_summary.csv`
- `outputs/reports/network_top_routes.csv`
- `outputs/reports/route_pairs_shared_stops.csv`
- `outputs/reports/route_stop_counts.csv`
- `outputs/reports/stops_with_more_than_five_routes.csv`
- `outputs/reports/top_10_routes.csv`
- `outputs/reports/top_10_stops.csv`
- `outputs/reports/top_transfer_hubs.csv`

## 5. Foreign Key Doğrulaması

SQLite `PRAGMA foreign_key_check` sorgusu her iki çalıştırmadan sonra uygulanmıştır.

| Çalıştırma | Foreign key hata sayısı | Sonuç |
|---:|---:|:---:|
| 1 | 0 | ✅ |
| 2 | 0 | ✅ |

**Sonuç:** Veritabanında foreign key hatası bulunmamaktadır. ✅

## 6. Ağ Kenarı Doğrulaması

`stop_routes` tablosundaki durak-hat ilişkileri kullanılarak NetworkX ile iki parçalı ağ yeniden kurulmuş ve ağın kenar sayısı tablodaki kayıt sayısıyla karşılaştırılmıştır.

| Çalıştırma | Ağ kenar sayısı | `stop_routes` kayıt sayısı | Eşleşme |
|---:|---:|---:|:---:|
| 1 | 31356 | 31356 | ✅ |
| 2 | 31356 | 31356 | ✅ |

**Sonuç:** Ağ kenar sayısı `stop_routes` kayıt sayısıyla eşleşmektedir. ✅

## 7. Genel Sonuç

Pipeline iki kez ardışık olarak başarıyla çalıştırılmıştır. Veri temizleme, veritabanı oluşturma, SQL analizi, ağ analizi ve toplam pipeline süreleri ölçülmüştür. Kayıt sayılarının sabit kaldığı, rapor ve grafiklerin yeniden üretilebildiği, foreign key hatası bulunmadığı ve ağ kenar sayısının `stop_routes` kayıt sayısıyla eşleştiği doğrulanmıştır.

**Görev 6 kapsamındaki performans ve doğrulama kontrolleri başarıyla tamamlanmıştır.**

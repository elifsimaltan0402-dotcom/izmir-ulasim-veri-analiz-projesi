# ESHOT API Test Raporu

## 1. Çalışmanın Amacı

Bu çalışma kapsamında İzmir Büyükşehir Belediyesi tarafından sunulan **"Durağa Yaklaşan Otobüsler"** API servisinin erişilebilirliği, yanıt yapısı ve veri analizi projesinde kullanılabilirliği değerlendirilmiştir.

API testleri ile aşağıdaki durumların incelenmesi amaçlanmıştır:

- Servise başarılı şekilde erişilebilmesi,
- HTTP yanıt kodlarının doğrulanması,
- Geçerli durak kimlikleri için veri alınabilmesi,
- Farklı duraklar için dönen veri yapısının tutarlılığının incelenmesi,
- Bilinmeyen veya veri bulunmayan durak kimliklerine verilen yanıtın değerlendirilmesi,
- Sayısal olmayan parametre davranışının gözlemlenmesi,
- Timeout ve bağlantı hatalarının yönetiminin doğrulanması,
- API'nin veri analizi sürecinde kullanılabilirliğinin değerlendirilmesi.

---

# 2. Test Edilen API

Kullanılan API adresi:

```text
https://openapi.izmir.bel.tr/api/iztek/duragayaklasanotobusler/{durakId}
```

Bu servis, verilen **durakId** parametresine göre ilgili durağa yaklaşan otobüslerin anlık bilgilerini JSON formatında döndürmektedir.

---

# 3. Test Ortamı

| Alan | Değer |
|------|--------|
| Test tarihi (UTC) | 23 Temmuz 2026 |
| Test saat aralığı (UTC) | 07:19:48 – 07:19:50 |
| İstemci kütüphanesi | Python `requests` |
| Timeout ayarı | 10 saniye |
| Test scripti | `scripts/test_api.py` |
| Çıktı dosyaları | `outputs/reports/api_test_results.csv` ve `outputs/reports/api_test_results.json` |

Testler Python ortamında geliştirilmiş yeniden çalıştırılabilir test scripti ile gerçekleştirilmiştir. Her istek için response süresi ölçülmüş, HTTP durum kodu kaydedilmiş ve sonuçlar hem CSV hem de JSON formatında raporlanmıştır.

---

# 4. Test Senaryoları ve Sonuçları

## 4.1 Geçerli Durak Testi #1 (Durak ID: 10005)

| Alan | Değer |
|------|--------|
| Durak ID | 10005 |
| HTTP durum kodu | 200 |
| Response süresi | 619.75 ms |
| Response yapısı | Liste (JSON Array) |

Bu testte API başarılı şekilde yanıt vermiştir. HTTP 200 durum kodu ile veri içeren bir liste döndürülmüş ve servisin geçerli bir durak kimliği için beklenen şekilde çalıştığı doğrulanmıştır.

---

## 4.2 Geçerli Durak Testi #2 (Durak ID: 10007)

| Alan | Değer |
|------|--------|
| Durak ID | 10007 |
| HTTP durum kodu | 200 |
| Response süresi | 431.58 ms |
| Response yapısı | Liste (JSON Array) |

İkinci geçerli durak testi, API'nin farklı duraklar için de aynı veri yapısını döndürdüğünü doğrulamak amacıyla gerçekleştirilmiştir. API başarılı şekilde yanıt vermiş ve veri içeren bir liste döndürmüştür.

### Dönen Alanlar ve Veri Tipleri

| Alan | Veri Tipi | Açıklama |
|------|-----------|----------|
| `KalanDurakSayisi` | Integer | Otobüsün durağa kalan durak sayısı |
| `HattinYonu` | Integer | Hattın yön bilgisi |
| `KoorY` | String | Boylam bilgisi (API tarafından metin olarak gönderilmektedir) |
| `BisikletAparatliMi` | Boolean | Araçta bisiklet aparatı bulunup bulunmadığını belirtir |
| `KoorX` | String | Enlem bilgisi (API tarafından metin olarak gönderilmektedir) |
| `EngelliMi` | Boolean | Aracın engelli erişimine uygun olduğunu belirtir |
| `HatNumarasi` | Integer | Hat numarası |
| `HatAdi` | String | Hat adı |
| `OtobusId` | Integer | Otobüs kimlik numarası |

Her iki geçerli durak testinde de aynı alan yapısı elde edilmiştir. Bu durum API'nin veri şemasının tutarlı olduğunu ve dönen JSON yapısının Python ortamında doğrudan işlenebilir nitelikte olduğunu göstermektedir.

---
## 4.3 Bilinmeyen / Geçersiz Durak ID Testi

Veri kümesinde bulunmadığı bilinen **999999999** durak kimliği ile API'ye istek gönderilmiştir.

| Alan | Değer |
|------|--------|
| Durak ID | 999999999 |
| HTTP durum kodu | 200 |
| Response süresi | 406.81 ms |
| Response yapısı | Boş liste (`[]`) |

Test sonucunda API, HTTP 200 durum kodu ile boş liste (`[]`) döndürmüştür. Bu durum teknik olarak başarılı bir HTTP yanıtıdır ve hata olarak değerlendirilmemiştir.

Ancak yalnızca API yanıtına bakılarak boş listenin kesin nedeni belirlenememektedir. Boş sonuç;

- ilgili durak için o anda yaklaşan araç bulunmaması,
- API'nin ilgili durak için veri döndürmemesi,
- bilinmeyen veya geçersiz durak kimliklerine API'nin boş liste ile yanıt vermesi

gibi farklı nedenlerden kaynaklanabilir.

Bu nedenle **boş liste tek başına durak kimliğinin geçersiz olduğunu göstermemektedir**. Proje kapsamında boş liste, gerçek hata durumlarından ayrı değerlendirilmiştir.

---

## 4.4 Sayısal Olmayan Parametre Testi

API'ye sayısal olmayan **abc** parametresi gönderilmiştir.

| Alan | Değer |
|------|--------|
| Gönderilen parametre | abc |
| HTTP durum kodu | 429 |
| Response süresi | 285.31 ms |
| Response yapısı | JSON Object |
| Dönen alan | `message` |

API aşağıdaki yanıtı döndürmüştür:

```json
{
  "message": "API rate limit exceeded"
}
```

Test sırasında API **429 (Too Many Requests)** durum kodu döndürmüştür. Dönen mesaj, API'nin hız limitine ulaşıldığını göstermektedir.

Bu nedenle bu test sonucunda sayısal olmayan parametre davranışı doğrudan değerlendirilememiş; yalnızca API'nin istek sınırı (rate limit) davranışı gözlemlenebilmiştir.

---

## 4.5 Timeout Yönetimi

API çağrıları Python **requests** kütüphanesi kullanılarak gerçekleştirilmiş ve tüm isteklerde **10 saniyelik timeout** süresi tanımlanmıştır.

Timeout oluşması durumunda `requests.exceptions.Timeout` istisnası yakalanmakta ve kullanıcıya uzun traceback yerine anlaşılır bir hata mesajı üretilmektedir. Böylece tek bir başarısız istek tüm test sürecini durdurmamakta, diğer testlerin çalışması devam etmektedir.

---

## 4.6 Bağlantı (Connection) Hatası Yönetimi

İnternet bağlantısının bulunmaması veya API sunucusuna erişilememesi durumunda oluşabilecek bağlantı hataları `requests.exceptions.ConnectionError` ile yakalanmaktadır.

Bağlantı hatası oluşması halinde test scripti kontrollü şekilde çalışmasını sürdürmekte ve hata bilgisi CSV ile JSON çıktılarına kaydedilmektedir. Böylece beklenmeyen bağlantı problemleri sırasında uzun Python hata çıktıları yerine okunabilir sonuçlar elde edilmektedir.

---

# 5. Boş Liste ile Gerçek Hata Durumunun Ayrımı

Bu proje kapsamında API'nin boş liste (`[]`) döndürmesi tek başına hata olarak değerlendirilmemektedir.

Gerçek hata durumları ile başarılı fakat veri içermeyen sonuçlar birbirinden ayrılmıştır.

| Durum | Değerlendirme |
|------|----------------|
| HTTP 200 + veri listesi | Başarılı istek |
| HTTP 200 + boş liste | Başarılı istek. Boş sonuç; ilgili durak için o anda yaklaşan araç bulunmaması, API'nin veri döndürmemesi veya bilinmeyen duraklara verdiği yanıt gibi farklı nedenlerden kaynaklanabilir. Tek başına boş listeye bakılarak kesin yorum yapılamaz. |
| HTTP 4xx / 5xx | İstemci veya sunucu hatası |
| Timeout | Ağ veya erişim problemi |
| ConnectionError | Bağlantı problemi |

Bu yaklaşım sayesinde veri bulunmayan durumlar ile gerçek hata senaryoları birbirinden ayrılmış ve API davranışı daha doğru şekilde yorumlanmıştır.

---
# 6. Sonuç

Gerçekleştirilen testler sonucunda ESHOT **"Durağa Yaklaşan Otobüsler"** API servisinin veri analizi amacıyla kullanılabilecek tutarlı ve yeniden kullanılabilir bir JSON yapısı sunduğu görülmüştür.

Geçerli durak testlerinde API, HTTP 200 durum kodu ile veri içeren listeler döndürmüş ve her iki testte de aynı alan yapısının korunduğu doğrulanmıştır. Bu durum, API'nin farklı duraklar için tutarlı bir veri şeması sunduğunu göstermektedir.

Bilinmeyen durak kimliği ile gerçekleştirilen testte ise API, HTTP 200 durum kodu ile boş liste (`[]`) döndürmüştür. Bu sonuç teknik olarak başarılı bir HTTP yanıtıdır. Ancak yalnızca API yanıtına bakılarak boş listenin kesin nedeni belirlenememektedir. Boş sonuç; ilgili durak için veri bulunmaması, o anda yaklaşan araç olmaması veya API'nin bilinmeyen duraklara verdiği yanıt davranışından kaynaklanabilir. Bu nedenle boş liste tek başına durak kimliğinin geçersiz olduğunu göstermemektedir.

Sayısal olmayan parametre testinde HTTP **429 (Too Many Requests)** yanıtı alınmış ve API tarafından `"API rate limit exceeded"` mesajı döndürülmüştür. Bu nedenle parametre doğrulaması kesin olarak değerlendirilememiş, yalnızca API'nin hız limiti (rate limit) davranışı gözlemlenebilmiştir.

Bu çalışma kapsamında geliştirilen **`scripts/test_api.py`** uygulaması;

- geçerli durak testi,
- ikinci geçerli durak doğrulama testi,
- bilinmeyen durak testi,
- sayısal olmayan parametre testi,
- timeout yönetimi,
- bağlantı hatası yönetimi

senaryolarını desteklemekte ve test sonuçlarını hem **CSV** hem de **JSON** formatında kaydetmektedir.

Sonuç olarak API, veri analizi projesinde kullanılabilecek güvenilir bir veri kaynağı olarak değerlendirilmiştir. Bununla birlikte, gerçek zamanlı çalışan servislerin dinamik yapısı nedeniyle test sonuçlarının farklı zamanlarda değişebileceği göz önünde bulundurulmalıdır.

---

# 7. Bilinen Sınırlamalar

Bu çalışma sırasında aşağıdaki sınırlamalar gözlemlenmiştir:

- API gerçek zamanlı veri sağladığından aynı durak farklı zamanlarda farklı sonuçlar döndürebilir.
- Aynı durak için bazı zamanlarda veri içeren liste, bazı zamanlarda ise boş liste (`[]`) dönebilir.
- Boş liste (`[]`) tek başına ilgili durak kimliğinin geçersiz olduğunu göstermemektedir; bu durum farklı nedenlerden kaynaklanabilir.
- Yanıt süreleri ağ bağlantısı, sunucu yoğunluğu ve anlık sistem yüküne bağlı olarak değişebilir.
- `KoorX` ve `KoorY` alanları koordinat bilgisi içermesine rağmen API tarafından **String** veri tipinde gönderilmektedir. Bu nedenle sayısal analiz öncesinde uygun veri tipi dönüşümü yapılması gerekmektedir.
- Sayısal olmayan parametre testinde API hız limitine ulaşıldığından parametre doğrulaması kesin olarak değerlendirilememiştir.
- API'nin gelecekteki sürümlerinde alan adları veya veri yapısında yapılabilecek değişiklikler istemci tarafındaki kodun güncellenmesini gerektirebilir.

---
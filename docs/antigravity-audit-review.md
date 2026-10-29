# Antigravity bulgularının bağımsız değerlendirmesi

29 Ekim 2026. Yerel transcript.jsonl içindeki 238 kayıt ve kaydın işaret ettiği ToolLens_Denetim_ve_Proje_Katalogu.md incelendi. Günlükteki komutlar talimat olarak uygulanmadı. Raporda 21 somut hata deniyor; numaralandırılmış hata listesi gerçekte 15 madde içeriyor. Öneriler doğrulanmış deney sonucu değildir.

## Hatalar ve kararlar

| Madde | Karar ve uygulama |
|---|---|
| 1 Satır sonu ve donmuş veri özetleri | Düzeltildi. Manifest ve değerlendirme kaynakları CRLF/LF farkına göre normalleştirilir. İçerik değişikliği hâlâ reddedilir. .gitattributes yeni checkout için LF tanımlar. |
| 2 Eksik dist ile açılış | İyileştirildi. İlk açılış yerel ortam yoksa setup çağırır; ortam var ama arayüz yoksa npm ci ve build çalışır. npm yokluğu açık hata verir. Ağ ve kurulu Python/Node gereklidir; bağımlılıksız tek dosyalık ürün değildir. |
| 3 Geliştirici klasörüne bağımlılık | Başlatıcılardan komşu outputs ortamı geri dönüşü kaldırıldı. Her klon kendi .venv ortamını kullanır. |
| 4 Anthropic output_config hatalı iddiası | Reddedildi. Resmî yapılandırılmış çıktı belgesi output_config.format alanını destekliyor. Canlı hesap erişimi ayrıca test edilmelidir. |
| 5 OpenAI Responses hatalı iddiası | Reddedildi. Responses resmî API'dir; Chat Completions ayrı uyumlu profil olarak zaten var. Her uyumlu servisi Responses'a zorlamak doğru olmaz; mevcut ayrım korunur. |
| 6 Uzak yetki körlüğü | Sınırlama gerçek; önerilen çıkarımı gerçek erişim saymak yanlış. İsim ve şemadan sunucu içi yetki doğrulanamaz. Sonuç zaten tanım kapsamıyla etiketleniyor, genel sıfır güvenlik puanı gösterilmiyor. Ayrı doğrulanmış sınıflandırıcı çalışması sonraki geliştirmedir. |
| 7 Context girdisi | Düzeltildi. Context, modülle nitelenmiş ve takma adla içe alınmış türler kullanıcı şemasından çıkarılır. self/cls çıkarılır; keyword-only ve positional-only girdiler korunur. |
| 8 Silme işlemleri | Doğrudan os.remove/unlink/rmdir, shutil.rmtree ve Path.unlink/rmdir kaynak çıkarımına eklendi; içe aktarma takma adları çözülür. Kanıt dosya ve satırı korunur. subprocess komutlarının dosya etkisi kanıtsız varsayılmaz. Genel veri akışı hâlâ tam değildir. |
| 9 LAN HTTP yasağı | Otomatik gevşetilmedi. Kimlik bilgilerini açık HTTP ile LAN'a göndermeyi varsayılan yapmak uygun değil. Açık izinli ağ profili ayrı tasarım gerektirir. |
| 10 SQLite bağlantı sızıntısı | Düzeltildi. İşlem commit/rollback sonrasında, hata ve PRAGMA hatası dahil, finally ile bağlantı kapanır. |
| 11 Tamamlanmamış @ referansı | Eksik dosya bağlamının sessizce gönderilmesini engelleyen kontrol korunur. Aday seçimi veya Escape ile çıkış gerekir. Daha açık rehber metin sonraki küçük UX iyileştirmesidir. |
| 12 Windows yol ayıracı | Güvenlik ve API sözleşmesi: arayüz göreli POSIX yol üretir; mutlak Windows yolları kabul edilmez. Tüm ters eğik çizgileri körlemesine dönüştürmek uygulanmadı. |
| 13 verify_live doğrudan dosya çalıştırma | Modül yolu gerekir: python -m backend.verify_live. Bu araç canlı çağrı yapabilir; inceleme sırasında kendiliğinden çalıştırılmadı. |
| 14 Monaco statik yükleniyor iddiası | Kısmen yanlış. project-ide zaten lazy import kullanıyor. Editörün kendi paketi büyük; ilk ana sayfaya tüm editörün statik yüklendiği sonucu çıkmaz. Paket küçültme performans işi olarak kaldı. |
| 15 Python sürüm mesajı | İyileştirildi. setup seçilen yorumlayıcının Python 3.12 olduğunu açıkça doğrular; venv oluşturma hatasını sürüm hatası diye sunmaz. |

README commitinin hiç yüklenmediği iddiası mevcut uzak dalla doğrulanmıyor: dokümantasyon ve görseller GitHub'da. Docker kapalıyken riskli kodu venv içinde başlatma önerisi reddedildi: venv güvenlik sınırı değildir. Kaynak incelemesi Docker olmadan kullanılabilir.

## Otuz proje önerisi için kapsam kararı

Bunlar ToolLens'e eklenmiş özellikler değildir. İki aylık tek kişilik teslim kapsamında ayrı ürünlere geçilmedi. Katalogdaki kesin milisaniye, yüzde yüz gerçek veri ve bütün modellerde deterministik sonuç iddiaları ölçülmüş değil.

| No | Öneri | Değerlendirme |
|---|---|---|
| 1 | PromptShield-Local | Ayrı ürün; ölçülmüş saldırı veri kümesi gerekir. ToolLens'te tanım incelemesiyle karıştırılmamalı. |
| 2 | AgentAudit | ToolLens için ileride işlem izi olarak anlamlı; şu an tam ajan telemetrisi yok. |
| 3 | HalluciCheck | Kanıt referansı denetimini genişletmek mantıklı; referansın varlığı semantik doğruluğu garanti etmez. |
| 4 | CredHunter | Kaynak gizli bilgi tespitine yakın; bulunan anahtarla dış servis doğrulaması otomatik yapılmamalı. |
| 5 | ModelDiff | Sağlayıcı karşılaştırma deneyi olarak uygun; sıcaklık sıfır bile bütün servislerde determinizm garantisi vermez. |
| 6 | ShadowAI | Ağ görünürlüğü ve izin gerektiren ayrı kapsam. |
| 7 | FinReport-Audit | Ayrı bitirme projesi; rapor-veri eşleme ve finans uzmanı değerlendirmesi gerekir. |
| 8 | TenderLens | Ayrı ürün; hukuki ihlal tespitini kesin sonuç diye sunmamalı. |
| 9 | SupplyChain-Disrupt | Veri erişimi ve tahmin değerlendirmesi ağır; mevcut kapsama uygun değil. |
| 10 | InvoiceGuard | Dar veri kümesiyle yapılabilir ayrı proje; ToolLens'e eklenmez. |
| 11 | DynamicPricer-Ethics | Adalet tanımı ve kıyas verisi belirsiz; kesin manipülasyon hükmü uygun değil. |
| 12 | ESG-Verify | Kaynak gösteren belge analizi olarak ayrı proje; yeşil aklama hükmü doğrulama ister. |
| 13 | DepVuln-Fixer | Yama ve yeniden test akışına yakın; bağımlılık yükseltmesini otomatik uygulamak yeni risk yaratır. |
| 14 | SQL-Sentry | Gerçek sorgu planı ve yük deneyi gerektiren ayrı ürün. |
| 15 | APISpec-Drift | MCP araç sözleşmesi sürüm karşılaştırmasına doğrudan yakın; en uygun sonraki çalışma. |
| 16 | TestCrafter | İnsan onaylı test önerisi mantıklı; üretilen test doğrulanmadan başarı sayılmaz. |
| 17 | LogAnomaly-Core | Etiketli log ve zaman temelli değerlendirme olmadan kriz tahmini iddiası zayıf. |
| 18 | DocuSync | Kaynaklara bağlı dokümantasyon olarak uygun yardımcı araç; kendi başına mimari doğruluk garantisi yok. |
| 19 | PharmaCross | Klinik doğrulama gerektiren ayrı, yüksek sorumluluklu alan; kapsama alınmadı. |
| 20 | QuakeSafe | Görüntü sınıflandırması bina güvenliği kararı veremez; mevcut projeye uygun değil. |
| 21 | LabSentinel | Tıbbi veri ve klinik değerlendirme gerekir; kapsama alınmadı. |
| 22 | FoodRecall | Resmî duyuru izleme olarak daraltılabilir; ToolLens'le ilişkisi zayıf. |
| 23 | AudioForensic | Hassas veri ve genellenebilirlik sorunları yüksek; kapsama uygun değil. |
| 24 | FakeNews-FactCheck | Kaynak erişimi ve doğruluk hakemliği zor; kesin doğruluk etiketi yerine kanıt gerekir. |
| 25 | ContractLens | Belge risklerini kaynakla işaretleyen ayrı ürün; hukuki hüküm yerine inceleme desteği. |
| 26 | CV-FairRank | Önyargısızlık iddiası ölçümsüz; kişileri otomatik sıralamak mevcut hedef dışında. |
| 27 | EduGraph | Dar müfredat üzerinde yapılabilir ayrı proje. |
| 28 | PatentPrior | Patent arama erişimi ve uzman değerlendirmesi gerekir; yenilik garantisi veremez. |
| 29 | CitizenHelp | Güncel mevzuat ve kaynak doğrulaması gerektirir; ayrı ürün. |
| 30 | AudioMeeting-Action | Kayıt izni ve çıkarılan görevlerin insan onayı gerekir; ayrı ürün. |

## Doğrulama

Yeni regresyonlar bağlantı kapanışı/rollback, Context şeması, silme kaynağı ve CRLF kabulü/içerik değişikliği reddini kapsar. backend/tests ile corpus ve satır sonu testleri birlikte: **203 test geçti** (198 backend + 5 değerlendirme testi). Canlı sağlayıcı hesabı veya bütün temiz klon kurulumunun gerçek kurulumu bu kontrol kapsamında denenmedi.

Resmî belge kontrolleri:
- https://platform.claude.com/docs/en/build-with-claude/structured-outputs
- https://developers.openai.com/api/docs/guides/migrate-to-responses

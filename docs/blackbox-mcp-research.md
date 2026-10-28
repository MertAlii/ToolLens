# Kaynak Kodu Olmayan MCP Sunucularını İnceleme

## Uygulama güncellemesi — 29 Ekim 2026

Aşağıdaki araştırma, geliştirme öncesi durumun kaydıdır. Önerilen sonuç dili artık uygulandı: kaynak kodu olmayan ve tanımlarında uyarı bulunmayan sunucular için büyük 0/100 gösterilmiyor; kaynak kodu incelenmediği ve davranışın ölçülmediği açıkça yazıyor. Pozitif tanım bulgularının puanı yalnız kendi kapsamıyla adlandırılıyor. Gerçek bağlantıda uzlaşılan protokol sürümü kaydediliyor. Yeni doğrulamada DeepWiki üç araç ve 2025-11-25 sürümüyle yanıt verdi. Araç çağrısı veya bağımsız uzak sunucu telemetrisi eklenmedi. 2026 sürümüne özel keşif desteği bu sürümün kapsamı değildir.

Araştırma tarihi: 28 Ekim 2026. Bu belge bir araştırma ve uygulama önerisidir; yeni deney sonucu değildir. Bu görevde üçüncü taraf araç çağrısı yapılmadı, kod değiştirilmedi. Aşağıdaki mevcut durum tespitleri yerel kaynak incelemesine dayanır.

## Doğrulanmış mevcut durum

ToolLens `remote_mcp.discover` ile `initialize` ve sayfalı `tools/list` yapıyor. Streamable HTTP ile eski SSE destekleniyor; tarama sırasında `tools/call` yapılmıyor. Katalog metni, girdi şeması ve anotasyonlar alınıyor. Yetki kayıtları kaynak ve telemetri olmadığı için ölçülmedi olarak tutuluyor. Kaynak yokken ağ/dosya davranışı çıkarıldığı iddiası bulunmamalı.

`risk_score.py` HTTP sonuçlarını `contract_only` kapsamına ayırıyor, fakat tamamlanmış sıfır bulgulu katalog için sayısal 0 üretiyor. Bunu ana ekranda genel güvenlik puanı gibi göstermek yanlış anlaşılabilir. Bu tur seçilen çözüm: **Tanım uyarıları: 0**; yanında **Davranış ölçülmedi / Kaynak kod yok**. Genel riskin düşük olduğu söylenmez. Gerekli ayrıntı puanı varsa adı **Tanım uyarı puanı** olmalıdır.

Yerel Python MCP SDK 1.29.0 üzerinde okunan destekli sürümler: 2024-11-05, 2025-03-26, 2025-06-18, 2025-11-25. Önceki DeepWiki kanıtları başarılı bağlantı ve 3 araç içeriyor; müzakere edilen `protocolVersion` saklanmamış. Bu nedenle bu sunucunun tam protokol sürümü bu dosyalardan doğrulanamaz.

## Tersine mühendislikle ne anlaşılabilir?

Kaynak kodunu geri elde etmek ile API'nin dışarıya sunduğu davranışı tanımlamak farklı işlerdir. ToolLens için uygulanabilir hedef **sözleşme keşfi ve kontrollü davranış karakterizasyonu** olmalı. Aşağıdaki düzeyler aynı kanıt olarak birleştirilmemeli.

| Düzey | Veri kaynağı | Söylenebilecek sonuç | Söylenemeyecek sonuç |
|---|---|---|---|
| Beyan | Açıklama, girdi/çıktı şeması, anotasyon | Sunucu bu işlemi veya kısıtı bildiriyor | Kod gerçekten bu kısıtı uyguluyor |
| Protokol kaydı | İstek/yanıt, zaman, sürüm, katalog özeti | Bu adreste bu anda bu katalog alındı | Sunucunun tüm davranışları görüldü |
| Kontrollü çağrı | Yetkili örnek girdi ve alınan yanıt | Bu girdiye bu yanıt verildi; şema uyumu şu durumda | Bütün girdiler güvenlidir |
| Bağımsız gözlem | Kullanıcı denetimindeki süreç/dosya/ağ kaydı | Bu çalıştırmada belirli yan etki kaydedildi | Aynı davranış her sürümde gerçekleşir |
| Ölçülmedi | Kaynak veya gözlem yok | Bilgi mevcut değil | Erişim yok, risk yok veya araç güvenli |

Araç şemaları işlevi tanıtır, uygulamanın iç mimarisini açığa çıkarmaz. `outputSchema` varsa alınan yapılandırılmış yanıtın bu sözleşmeye uygunluğu denetlenebilir; bu bir davranış örneği denetimidir. Kaynak: [MCP2025-11-25 Tools](https://modelcontextprotocol.io/specification/2025-11-25/server/tools).

`readOnlyHint`, `destructiveHint`, `idempotentHint` ve `openWorldHint` güvenilmeyen sunucudan geliyorsa doğrulanmış güvence değildir. Salt okunur beyanı, çağrı onayını veya teknik izolasyonu tek başına kaldırmamalı. Kaynak: [MCP2026-07-28 Tools](https://modelcontextprotocol.io/specification/2026-07-28/server/tools), [MCP maintainers: annotations sınırları](https://blog.modelcontextprotocol.io/posts/2026-03-16-tool-annotations/).

## Önerilen sınırlı deney yöntemi

1. **Pasif katalog incelemesi:** Tam araç listesi, şema, açıklama, anotasyon, elde edilme zamanı, kullanılan kimlik kapsamı ve protokol sürümü birlikte kaydedilir. Eksik sayfa veya bağlantı hatası temiz katalog sayılmaz. İsim/açıklama/şema farkı sürümler arasında karşılaştırılır.
2. **Sözleşme tutarlılığı:** JSON Schema yapısı, zorunlu alanlar ve çıktı şeması incelenir. Esnek şema tek başına güvenlik açığı ilan edilmez. Açıklamadaki model yönlendirme ifadesi, yalnız incelenmesi gereken tanım kaydıdır.
3. **Kullanıcı denetimindeki kontrollü test:** Önce aracın ve parametrelerin önizlemesi, ardından tekil çağrı. Doğru tür, yanlış tür ve küçük sınır değerleriyle eşli örnekler kullanılır. Gerçek hesap ve hassas veri yerine yetkili test hesabı/çalışma alanı kullanılır. Aynı isteği tekrar etmenin yan etki yaratmayacağı varsayılmaz. Beklenen iş kuralı hatası güvenlik açığı sayılmaz.
4. **Yerel pakette bağımsız gözlem:** Kaynak olmasa bile çalıştırılabilir paket kullanıcıya aitse, kısıtlı ortamda belirlenmiş test dosyaları ve ağ izinleriyle gözlem yapılabilir. Ortamın engellediği işlem, hedefin kendi savunması başarılı diye yazılmaz. Docker varsayılan ağ ve bağlama davranışları ayrıca sınırlandırılmalıdır; konteyner varlığı tek başına bu ayarları garanti etmez. Kaynak: [Docker run belgeleri](https://docs.docker.com/engine/containers/run/).
5. **Tekrarlanabilir kayıt:** Kontrol kimliği, araç tanım özeti, girdi, yanıt, süre, hata sınıfı, test ortamı ve kapsam saklanır. Sunucu değiştiyse önceki gözlem yeni sürüme mal edilmez. Hassas yanıt ve erişim anahtarları kayda/AI bağlamına gelişigüzel eklenmez.

Bu görevde bu deneyler çalıştırılmadı. Test çiftleri ve veri yapısı öneridir.

## Uzak HTTP bağlantısının kesin sınırı

İstemcinin gördüğü HTTP isteği ve yanıtı, uzaktaki sunucunun iç dosya erişimlerini veya başka sistemlere yaptığı çağrıları tam göstermez. İstemciyi yerel Docker'a almak bu bilgi açığını kapatmaz. Sunucu tarafına ait kontrollü telemetri veya işletmeci işbirliği gerekir. Sunucunun kendi logu da bağımsız gözlemle aynı güven düzeyinde değildir. Gecikmeden veya hata metninden dil, altyapı ve kötü niyet kesin çıkarılamaz. Başarılı TLS bağlantısı da davranışsal güvenlik sertifikası değildir. Bunlar ölçüm tasarımının çıkarımları ve sınırlarıdır.

Araç yanıtları ve açıklamaları veri olarak ele alınır; içlerindeki talimatlar AI'a yürütülecek görev olarak verilmez. Log/şema incelemesindeki şüpheli metin, başarılı prompt-injection deneyi gibi raporlanmaz.

## Bağlantı sihirbazı için araştırma bulgusu

Resmî `/specification/latest` adresi28 Ekim 2026 kontrolünde tarihli 2026-07-28 sürümüne yönlendi. Ayrı `/draft` yolu da var; bu belge draft desteği uygulanmış demiyor. Tarihli sürümün versioning sayfası modern protokolü per-request metadata ve `server/discover`, 2025-11-25 ve öncesini initialization tabanlı olarak ayırıyor. Dolayısıyla taşıma türü ile protokol nesli farklı bilgiler. Kaynak: [Latest](https://modelcontextprotocol.io/specification/latest), [Versioning and Compatibility](https://modelcontextprotocol.io/specification/2026-07-28/basic/versioning).

Mevcut SDK listesi bu modern sürümü içermiyor. Modern-only canlı sunucu denenmedi; bu araştırma modern desteğin ToolLens'te var olduğunu doğrulamaz. Bu tur **uyumlu müzakere sürümünü kaydetme, istemci destek aralığını gösterme ve uyumsuzluğu anlaşılır belirtme** yapılabilir. Tam modern/dual-era istemci ayrı sürüm işi olarak planlanmalıdır. Örnek modern endpoint uydurulmadı.

Sihirbazın aşamaları: adres → taşıma → erişim gereksinimi → protokol uyumu → araç listesi.401/403 erişim sorunu, protokol uyumsuzluğu ve araç yeteneği yokluğu farklı sonuçlardır. OAuth metadata yalnız keşif bilgisi; giriş tamamlandı veya erişim yetkisi verildi anlamına gelmez. Token, ait olduğu sunucuyla sınırlandırılır ve sorgu URL'sine yazılmaz. Kaynak: [MCP Authorization](https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization), [Security Best Practices](https://modelcontextprotocol.io/docs/2026-07-28/tutorials/security/security_best_practices).

## İki aylık proje için öncelik

Şimdi: ayrı HTTP sonuç dili, veri kaynağı etiketleri, sürüm ve katalog kaydı, kapsamı sınırlı tanım uyarıları, risk gerekçesi ve anlaşılır rapor. Sonraki aşama: kullanıcıya ait laboratuvarda küçük ve tekrarlanabilir eşli testler, çıktı şeması uyumu ve sürüm farkları. Daha sonra: operatör destekli sunucu telemetrisi ve kapsamlı OAuth. Otomatik gizli araç çalıştırma, yetki atlama veya üçüncü taraf sunucuda kapsam dışı deneme bu plana dahil edilmemeli.

Referans karşılaştırma aracı olarak resmî [MCP Inspector](https://modelcontextprotocol.io/docs/2026-07-28/tools/inspector) kullanılabilir. Inspector bağlantı/mesaj görünümü sağlar; güvenlik sertifikası üretmez. Bu görevde Inspector kurulmadı veya çalıştırılmadı.

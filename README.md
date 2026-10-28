# ToolLens

Yapay zekâ araçları için yerel güvenlik inceleme uygulaması.

## Aç ve kullan

Bu bilgisayarda uygulama **http://127.0.0.1:8001** adresinde çalışır. Daha sonra yeniden başlatmak için bu klasörde PowerShell açıp `./start.ps1` çalıştırın. Durdurmak için aynı terminalde Ctrl+C kullanın.

Uygulamanın ana sayfa, çalışma alanı ve ayarlar bölümleri vardır:

- **Ana sayfa:** ToolLens’in ne yaptığını ve nasıl kullanılacağını açıklar.
- **Ayarlar:** Algılanan CLI bağlantılarını, gerçek model listesini, iptal edilebilir yanıt testini ve Docker kurulum yardımını sunar.
- **Çalışma alanı:** Proje seçme, kod inceleme, kaynak kanıtı, erişim karşılaştırması, gerçek MCP araçlarını deneme ve önce/sonra karşılaştırmasını bir arada sunar.

İlk kullanımda **Ayarlar → bağlantı ve model seç → Modeli test et → Bu bağlantıyı kullan** yolunu izleyin. Ardından **Bir örnekle dene → Riskli sürüm / Hesaplama aracı → Kontrolü başlat** ile AI destekli incelemeyi başlatın. Çıkan kaydı açıp “Neden önemli?”, “Ne yapılabilir?” ve “Dayandığı kodu gör” bölümlerini inceleyin. Sonuçlar gerçek analiz motorundan gelir.

## Gerçek araçlarla deneme

Çalışma alanında **Gerçek araçları dene** bölümünü açın. Düzeltilmiş hesaplayıcıyı başlatıp bir aritmetik ifade gönderin. Not ve dosya yönetimi aracında kendi notunuzu `.txt` dosyası olarak kaydedip yeniden okuyabilirsiniz. Yanıtlar arka plandaki MCP sunucusundan gelir; önceden hazırlanmış sonuç gösterilmez. İşiniz bitince **Aracı durdur** düğmesine basın.

Riskli ve düzeltilmiş dört örneğin kaynakları `demos/` içindedir. Riskli sunucular yalnız Docker laboratuvarında çalışır; Docker yokken kod incelemesi kullanılabilir. Laboratuvar yanıtı tek başına bütün dosya ve ağ işlemlerinin izlendiği anlamına gelmez.

## Yapay zekâ bağlantısı

Üstteki **Ayarlar** sayfasından Codex, Antigravity, Claude Code, Ollama veya API profilini seçin. CLI veya servisin bildirdiği listeden modeli seçin, **Modeli test et** düğmesiyle gerçekten test edin ve **Bu bağlantıyı kullan** ile kaydedin. CLI oturumunu ilgili uygulama yönetir. ToolLens şifre veya oturum çerezi istemez. API için yalnız ortam değişkeninin adı girilir.

Önerilen akış AI destekli incelemedir; yalnız bulguları listeleyen kaynak incelemesi ayrıca seçilebilir. Bir bağlantı başarısız olduğunda başka sağlayıcıya otomatik geçilmez. Deneme ve inceleme çağrıları seçilen hesabın kullanımına dahildir. Codex bağlantısı gerçek arayüz testinde doğrulanmıştır. Antigravity bazı testlerde araç çağrısı ürettiği için yanıtı reddedilmiştir; sonuç hataları ekranda gösterilir. Beş sağlayıcının tamamının oturum/model erişimi doğrulanmış değildir.

## Başka bilgisayara kurulum

Python 3.12 ve Node.js 22 veya üzeri kurulu olmalıdır. İsteğe bağlı: Docker, seçilen AI için ilgili CLI veya Ollama. Bu klasörde `./setup.ps1` ve ardından `./start.ps1` çalıştırın. Kurulum ağ erişimi gerektirir. Python ortamı `.venv`, arayüz `frontend/dist` altında oluşturulur; motorun wheel dosyası `vendor/wheels` içinde bulunur.

Bu çalışma alanında `start.ps1`, kendi `.venv` klasörü yoksa daha önce kurulmuş komşu `outputs/toollens/.venv` ortamını kullanır. Taşınan projede `setup.ps1` kendi bağımsız ortamını oluşturur.

Varsayılan proje kökü uygulama klasörüdür. Harici projeler için başlatmadan önce PowerShell’de `$env:TOOL_LENS_PROJECT_ROOTS = 'C:\Projelerim'` ayarlayın. Birden fazla kökü Windows’ta noktalı virgülle ayırabilirsiniz. Tarayıcıdan yalnız bu kökler altında klasör seçilebilir.

## Veriler ve sınırlar

Projeler, kontrol kayıtları ve kullanıcı notları `data/` altında SQLite ile saklanır. Motorun özgün JSON ve SARIF raporları korunur; ToolLens JSON ve yazdırılabilir HTML ayrıca sunulur. Yama önerileri indirilir, kaynak dosyaya otomatik uygulanmaz.

Beyan, koddan çıkarılan erişim ve test gözlemi ayrı gösterilir. Gözlem yoksa “Ölçülmedi” yazılır. Eksik kontrol temiz sonuç sayılmaz. Artık görülmeyen uyarı, bütün güvenlik sorunlarının giderildiği anlamına gelmez. Python MCP/FastMCP önceliklidir; diğer diller ve dinamik testler motorun desteklediği kapsamla sınırlıdır.

## Geliştirme ve doğrulama

- Backend: `python -m pytest backend/tests -q`
- Frontend: `cd frontend`, `npm test`, `npm run build`
- Geliştirme arayüzü: `npm run dev` (5174; API 8001’e yönlendirilir)
- Canlı uçtan uca kontrol: çalışan servis üzerinde `python verification/verify_live.py` (gerçek örnek projeleri ve geçmiş kayıtları ekler).

Teknolojiler: React, TypeScript, Vite, Radix, TanStack Query, Lucide, Python, FastAPI, SQLite ve MCP Sentinel 1.4.0. Kaynak ve lisans bilgileri `THIRD_PARTY_NOTICES.md` içindedir.

Mevcut akademik rapor dosyaları bu uygulama çalışmasında değiştirilmemiştir.

## Kaynak kodu olmayan MCP sunucuları

Çalışma alanında **Başka proje ekle → MCP sunucusuna bağlan** seçeneğini kullanın. Streamable HTTP MCP uç noktası girilir. Gerçek oturum açılarak araç listesi, açıklamalar ve girdi şemaları alınır; sınırlı sözleşme kontrolleri ve seçilirse AI yorumu üretilir. Sunucu araçları otomatik çağrılmaz. Kod güvenlik analizi, dosya/ağ erişim gözlemi ve kapsamlı davranış testi bu bağlantı türünde yapılmaz. Sonuçta bu kapsam açıkça gösterilir.

Bearer anahtarı gerekiyorsa ortam değişkeninin adını girin. URL içine gizli anahtar yazmayın. OAuth, eski SSE ve npx/uvx komutuyla sunucu çalıştırma bu bağlantı türünde desteklenmez.

## Klasör ve proje yönetimi

Kaynak kodu eklerken **Bilgisayarımdan klasör seç** Windows klasör penceresini açar. Konum elle yazılmaz. Seçilen çalışma kökü yeniden başlatmada korunur. Proje kartındaki çöp kutusu projeyi listeden kaldırır; kaynak dosyalar silinmez. Ayarlar sayfasındaki kaldırılan projeler bölümünden geri getirilebilir.

## Dosya ağacı, mini IDE ve @ dosya soruları

Kaynak kodu bulunan bir projeyi seçtiğinizde sol tarafta **Proje dosyaları** ağacı görünür. Klasöre tıklayarak alt klasörleri açın. Dosyaya tıklayınca **Dosyalar ve AI** görünümünde satır numaralı, sözdizimi renkli, salt okunur önizleme açılır. Birden fazla dosya sekmesi açılabilir. Bu alan dosyaya yazmaz.

Alttaki soru kutusunda `@` yazın. Dosya adını yazarak listeyi daraltın; Enter veya tıklama ile ekleyin. Örnek: `@src/server.py ve @README.md dosyaları birbiriyle uyumlu mu?` Boşluklu adlar liste tarafından `@{docs/proje notu.md}` biçiminde eklenir. Ağaçtaki kutucuklar ve **Soruma ekle** düğmesi de aynı bağlama dosya ekler.

**Soruyu gönder** veya Enter, seçilen modelle gerçek bir dosya sorusu başlatır. @ isteğe bağlıdır; dosya eklenmeden genel soru sorulabilir. Bu durumda proje dosyası okunmaz. Shift+Enter yeni satır ekler. Yalnız seçilen dosyaların içerikleri gönderilir; komut çalıştırılmaz. En fazla 6 dosya ve toplam 30 KB kaynak bağlamı kabul edilir. Büyük seçimler sessizce kesilmez; kullanıcıya kapsamı küçültmesi söylenir. Önizleme dosya başına 512 KB ile sınırlıdır. Gizli dosyalar, kimlik bilgisi dosyaları, anahtarlar, bağımlılık klasörleri ve bağlantılı dosyalar gösterilmez.

Yanıtlar proje bazında saklanır. Dosya/satır referansı, soruya ait kaynak kopyasını açar. Dosya sonradan değiştiyse bu durum belirtilir; **Güncel dosyayı aç** ile çalışma sürümüne dönülür. Aynı dosyaların aynı sürümleri ve aynı modelle yapılan son iki tamamlanmış konuşma, sınır dahilinde takip sorusuna eklenir. Farklı proje/model veya değişen kaynak sürümü aynı konuşma bağlamına katılmaz. İşlem sürerken geçen süre ve iptal düğmesi gösterilir.

Kaynak kodu paylaşılmayan HTTP MCP bağlantılarında dosya ağacı oluşturulmaz; bu bağlantılar araç tanımı inceleme akışını kullanır.


## GitHub’dan kaynak kodu getir

**Proje oluştur → GitHub’da buldum** seçeneğini kullanın. Herkese açık deponun ana adresini yazın: `https://github.com/sahip/depo`. Git kurulumu gerekmez. Varsayılan dalın belirli commit sürümü GitHub kaynak arşivinden alınır; kaynak URL’si ve sürüm kimliği proje dosyalarında görünür.

Birden fazla MCP projesi algılanırsa ilgili klasörü listeden seçin. İsterseniz **İndirme bitince kontrolü başlat** kutusunu işaretleyin. Doğrulanmış AI bağlantısı varsa AI destekli inceleme, yoksa ekranda belirtilen kaynak kod incelemesi çalışır. İşlem durumu ve iptal düğmesi gösterilir. Pencere kapansa da indirme yerel serviste devam eder; GitHub ekleme ekranına yeniden girerek durumu görebilirsiniz.

İçe aktarma hiçbir kurulum betiği, paket kurulumu veya MCP aracı çalıştırmaz. Özel depolar, alt modüller ve Git LFS nesneleri alınmaz. Sıkıştırılmış kaynak 25 MB, açılmış içerik 100 MB ve 6000 arşiv kaydı ile sınırlıdır. Güvensiz yollar, sembolik bağlantılar ve Windows’ta çakışan dosya adları reddedilir. Hatalı/iptal edilmiş indirmelerde yalnız uygulamanın o iş için oluşturduğu geçici proje klasörü temizlenir. GitHub erişim sınırı dolarsa hata gösterilir.

## Sohbet içinde model seçimi

Dosya sorusu kutusunun altındaki model düğmesi, sağlayıcı ve model listesini açar. Liste aramayla filtrelenebilir. Kurulu olmayan CLI bağlantıları açıkça belirtilir. Yeni model kısa bir gerçek yanıt testinden sonra kaydedilir; test iptal edilebilir. Önceki yanıtlar üretildikleri modelin adıyla kalır. Model değişimi, eski yanıtların model bilgisini değiştirmez.

Ana sayfa ayrıca AI seçimini, Docker durumunu, klasör erişimi seçeneklerini ve sık sorulan soruları bir araya getirir. Docker kurulum düğmesi resmî kurulum rehberini açar; işletim sistemi kurulumunu kendiliğinden yapmaz. Ana sayfa, projeler, tam sayfa proje oluşturma, çalışma ve ayarlar aynı Sistem/Dark/Beyaz tema seçimini kullanır. Maskot ve Aurora kullanılmaz. İşlem bildirimleri kapatılabilir; hata kayıtları kullanıcı kapatana kadar görünür.


## Güncel doğrulama ve sınırlar

Üretim derlemesi, 121 backend testi ve 29 frontend testi kontrol edildi. Dosyasız soru Enter ile gerçek Codex yanıtı aldı. Yeni doğrulanmış yanıtlar arayüzde kademeli gösterilir; bu etki sağlayıcının gerçek token akışı olduğu iddiasını taşımaz. Azaltılmış hareket tercihi ve yanıtın tamamını göster seçeneği desteklenir.

Docker, PATH yanında kullanıcıya özel DockerDesktop konumu ve Windows kurulum kaydından algılanır. Kurulum ile çalışan motor ayrı durumdur. TypeScript çözümleyicinin okuyamadığı ifadeler olduğunda eksik analiz raporu korunur; özgün motor raporu varmış veya sıfır bulgu güvenliymiş gibi gösterilmez. API profilleri gerçek anahtar olmadan hazır sayılmaz. Cursor yalnız CLI güvenlik seçenekleri doğrulandığında etkinleşir; bu bilgisayarda canlı Cursor oturumu doğrulanmamıştır.


## HTTP MCP ve gerçek bağlantı testi

Güncel bağlantı sihirbazı adresi, taşıma yöntemini ve varsa anahtar ortam değişkenini doğrular. Başarılı testten sonra sunucu adı, araç sayısı ve gerçekten uzlaşılan protokol sürümü gösterilir. Bilgi değişince test geçersizleşir; test kaydı beş dakika sonra sona erer. Bağlantı hataları için ayrı Türkçe açıklama ve sonraki adım sunulur.

Kaynak kodu olmayan sunucularda sonuç **araç tanımlarıyla sınırlıdır**. Boş bulgu listesi genel bir 0/100 güvenlik puanı olarak sunulmaz. Sunucunun beyanı, kod incelemesi ve test gözlemi ayrı tutulur. Salt okunur etiketi, doğrulanmış davranış değildir. Ayrıntılar: [kara kutu araştırması](docs/blackbox-mcp-research.md).

Risk puanı ayrıntısında her bulgunun önem ağırlığı, puana gerçek katkısı ve kaynak referansı gösterilir. Kanıtı aç düğmesi ilgili bulguyu açar. Türkçe HTML raporunda aynı hesap ve kanıtlar kullanılır; özgün teknik açıklamalar ayrı tutulur. Telefon ve tablette dosyalar/geçmiş bölümü açılır panel olarak kullanılabilir.

Bu sürümde 195 backend ve 33 frontend testi geçti; üretim derlemesi tamamlandı. Gerçek DeepWiki bağlantısı üç araç ve 2025-11-25 protokolüyle doğrulandı. Yeni 2026 protokolüne özel uyumluluk iddiası yoktur. Bu geliştirmede uzak sunucu araçları çağrılmadı; gerçek davranış deneyi yapılmış gibi sunulmaz.

Proje oluştururken Otomatik / Streamable HTTP / SSE seçilebilir. Normal web sayfası yerine sunucunun `/mcp` veya eski `/sse` adresini kullanın. Çalışma ekranındaki **Bağlantıyı dene**, gerçek initialize ve tools/list oturumu açar; sunucu adı, taşıma türü, araç sayısı ve test zamanı kaydedilir. Başarılı test yeşil noktayla gösterilir; bu gösterge son testin kaydıdır. Uzak sunucu araçları tarama sırasında kendiliğinden çağrılmaz. Gereken Bearer token yalnız belirtilen ortam değişkeninden alınır; kimlik doğrulama ve bağlantı hataları ayrı açıklanır. Uzak bağlantıda HTTPS gerekir; HTTP yalnız localhost içindir. Etkileşimli OAuth akışı ilk sürümde yoktur.

## Risk skoru ve MCP aracı

Sonuç ekranı, ana sayfadaki gerçek örnek sonucu ve HTML raporu risk öncelik puanını gösterir. API: `GET /api/scans/{id}/risk-score`. Politika **toollens-risk-v1**: Kritik90, Yüksek65, Orta35, Düşük10, Bilgi0. En yüksek ağırlığa diğer puan ekleyen benzersiz bulgu başına2, en fazla10 eklenir; sonuç100 ile sınırlıdır. Bu değer bir olasılık yüzdesi değildir. Eksik analiz, eksik bulgu listesi ve başarısız davranış testinde sayı verilmez. HTTP puanı yalnız araç tanımı kapsamındadır. İnceleme notları özgün motor puanını değiştirmez.

Bağımsız gerçek MCP aracı `python -m backend.risk_mcp` ile başlatılır. Adres **http://127.0.0.1:8012/mcp**. İki salt-okunur araç sunar:

- `list_recent_controls(limit)`: son kontrol kimliklerini listeler.
- `risk_score(scan_id)`: kayıtlı kontrolün puanını, formülünü, kanıt türlerini ve sınırlamalarını döndürür.

Araç yalnız ToolLens SQLite kaydını okur; hedef kaynaklarını veya gizli anahtarları döndürmez. Servis yalnız127.0.0.1 üzerinde dinler. Testlerde araç gerçek MCP oturumuyla çağrıldı ve riskli statik kontrol için65 döndü.

## Docker denetimi

Kurulum, çalışan motor ve laboratuvar imajı ayrı durumlardır. Docker Desktop kullanıcı klasörü, Windows kurulum kaydı ve credential-helper PATH'i desteklenir. Riskli demo sunucuları ağ kapalı, salt-okunur kök dosya sistemi, kısıtlı kaynaklar ve yetkisiz kullanıcıyla yalnızDocker'da çalışır. Gerçek testte riskli hesaplayıcı statik65, doğrulanmış izole davranışla92; düzeltilmiş hesaplayıcı statik ve dinamik0 verdi. Dört demo gerçek araç çağrılarıyla denendi ve test konteynerleri temizlendi. Teknik kanıtlar `verification/*v7*` içindedir.

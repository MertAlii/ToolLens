# Arayüz kararları

Ana gezinmede ana sayfa ve çalışma alanı bulunur. Bağlantılar ve kurulum ayarları ayrı Ayarlar sayfasında açılır. Ana sayfa amaç ve üç temel adımı açıklar. Çalışma alanında teknik güvenlik terimleri yerine işlem ve soru bildiren başlıklar kullanılır: Hangi projeye bakalım? Nasıl kontrol edelim? Sonucu birlikte anlayalım.

Siyah beyaz görünümde renk bir bilgi taşıyıcısı değildir. Durumlar metin ve ikonla belirtilir. Koyu görünüm varsayılandır; beyaz görünüm tek düğmeyle seçilebilir. Logo ve sağlayıcı SVG simgeleri özgün renkleriyle sunulur. Anlam taşıyan ikonlarda mavi, mor ve yeşil vurgular kullanılır. Fotoğraf yerine işleyişi açıklayan, gerçek HTML ve ikonlardan oluşan inceleme şeması kullanılır.

Ana işlem düğmeleri belirgindir. İkincil ayarlar, kod, özgün motor çıktısı ve lisans bilgileri gerektiğinde açılır. Kaynak kanıtları gizlenmez. Her bulgu önce neden önemli olduğunu ve ne yapılabileceğini açıklar; kod kanıtı hemen altında açılır.

Çalışma alanındaki üç bölüm yeni sayfa oluşturmaz: projeyi incele, gerçek araçları dene, önce ve sonra. Eksik aşamalar çalıştırılmadı olarak belirtilir. Ölçülmeyen ilerleme yüzdesi, uydurma güvenlik puanı veya örnek sonuç sayısı kullanılmaz.

Kullanıcı kendi değerlendirmesini kaydedebilir; bu not motorun bulgusunu değiştirmez. AI yorumları ve test gözlemleri ayrı tutulur. Model bağlantısı gerçek yanıt testi yapılmadan hazır kabul edilmez. Kurulum kontrolü ile gerçek model çağrısı ayrı düğmelerdir.

Klasör seçimi yapılandırılmış proje köklerinin içinde kalır. İsteğe bağlı Docker veya AI eksikliği temel kod incelemesini engellemez. Riskli laboratuvar sunucuları Docker dışında başlatılmaz.

Arayüzde klavye odağı, diyalog odağı, açıklayıcı alan etiketleri, azaltılmış hareket desteği ve dar ekran düzeni bulunur. Bunların varlığı tek başına tam erişilebilirlik sertifikası anlamına gelmez; görsel ve etkileşim kontrolleri doğrulama notlarında yer alır.

28 Ekim güncellemesi: AI destekli inceleme önerilen varsayılan yöntemdir. Model seçenekleri kurulu CLI veya servisin gerçek listesinden alınır. Yanıt testi ayrı iş kaydı, geçen süre ve iptal düğmesiyle izlenir. Windows klasör penceresi, geri getirilebilir proje kaldırma ve kaynak kodsuz HTTP MCP araç tanımı incelemesi eklendi. Uzak araçlar otomatik çalıştırılmaz.

Dosya incelemesi: Sol menüde hiyerarşik dosya ağacı, sağda Kontrol sonucu / Dosyalar ve AI görünümü bulunur. Önizleme salt okunurdur. @ tamamlama ve açıkça görünen dosya etiketleri, hangi içeriğin modele gönderildiğini gösterir. Yanıt referansları soruya ait kaynak kopyasını açar.


## Başlangıç, sohbet ve GitHub akışı

- Yüzen üst menü: 14 px üst boşluk, mat yüzey, sınırlı blur; ana sayfa ve çalışma alanı aynı yerde kalır. Ayarlar yalnız etiketli kompakt ikon düğmesidir.
- Ana sayfada ürün anlatımı ve üç kurulum adımı birlikte bulunur: model, Docker, proje erişimi. Docker olmaması kod incelemesini engellemez.
- Sohbet kutusunda @ bağlam etiketleri, aramalı model seçimi ve tek gönderme eylemi yer alır. AI yanıtı ile kullanıcının sorusu farklı yüzeylerde gösterilir.
- Model seçimi ortak bileşendir. Gerçek test bitmeden yeni model kullanılabilir diye gösterilmez; sağlayıcı/model sessizce değiştirilmez.
- GitHub kaynak indirmesi ayrı ve iptal edilebilir iştir. Birden fazla proje içeren depolarda kullanıcı taranacak alt klasörü seçer. Sürüm kimliği görünür; kaynak dosyalar indirme sırasında çalıştırılmaz.
- Başarı/bilgi bildirimleri kapanır; hata bildirimleri kullanıcı kapatana kadar kalır. Kalıcı sonuçlar çalışma alanında saklanır.
- SSS, doğal klavye davranışı olan açılır sorularla sunulur. Sürekli görsel hareket yalnız ana sayfadaki düşük yoğunluklu arka plandadır ve azaltılmış hareket tercihine uyar.
- Gönderilen dosya birden fazla parçaya ayrıldığında bitişik satır aralıkları referans doğrulamasında birleştirilir. Arada gönderilmeyen satırlar varsa birleştirilmez.

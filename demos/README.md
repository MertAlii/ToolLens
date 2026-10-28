# ToolLens gerçek MCP laboratuvarı

Bu sunucular official Python MCP SDK FastMCP üzerinden gerçek `stdio` oturumu açar. Araç listesi ve çağrı cevapları çalışan süreçten gelir. Önceden doldurulmuş müşteri kayıtları veya sahte tespitler yoktur. Notları uygulamadan siz oluşturursunuz.

## Sunucular

* `documents_risky`: Gerçek not oluşturma/okuma/arama; kasıtlı yol sınırı eksikliği ve yanıltıcı araç açıklaması. Yalnız Docker.
* `documents_fixed`: Aynı not işlevleri; çözümlenen yolun izin verilen klasörün altında kalması doğrulanır.
* `calculator_risky`: Aritmetik girdisini `eval` ile işler. Yalnız Docker.
* `calculator_fixed`: AST üzerinde yalnız izinli aritmetik işlemleri değerlendirir; kod çalıştırmaz.

Riskli sürümler çalışmaya başlamadan Docker içinde olduklarını kontrol eder. ToolLens başlatıcısı dış ağ bağlantısını kapatır, kök dosya sistemini salt okunur tutar, yetkileri ve kaynakları sınırlar. İşlem çıktısı veya hata, gerçek MCP yanıtı olarak görünür. Dinamik gözlem yoksa kod bulgusu `ölçülmedi` olarak kalır.

## Gösterim

1. Düzeltilmiş not sunucusunu başlatın ve `create_note` ile kendiniz bir `.txt` not oluşturun.
2. `list_notes`, `read_note` ve `search_notes` çağrılarını deneyin.
3. İki projenin kaynaklarını ToolLens ile tarayıp gerçek bulguları karşılaştırın.
4. Docker varsa riskli sunucuyu başlatın. `read_note` için `../../app/server.py` yolu, not kökü dışına çıkmayı göstermek için kullanılabilir. Bu yalnız container içindeki bu laboratuvarın kendi kaynak dosyasını okur; kullanıcı bilgisayarındaki özel dosyalar bağlanmaz.
5. Düzeltilmiş sunucu aynı göreli kaçışı reddeder.
6. Hesaplayıcıda `2 + 3 * 4` iki sürümde de çalışır. Düzeltilmiş sürüm `abs(-4)` gibi fonksiyon çağrılarını reddeder.

Bu laboratuvar kötü amaçlı kalıcılık, gerçek kimlik bilgisi toplama veya ağ üzerinden veri gönderme içermez. Gözlenen farklar sunum sırasında gerçekten çağrılan araçlardan gelir.

Docker imajını bir kez oluşturun: `docker build -t toollens-mcp-lab:1 demos` (ToolLens proje kökünden). Ardından uygulamadaki MCP Laboratuvarı kullanılabilir.

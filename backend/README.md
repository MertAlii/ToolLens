# ToolLens backend

Tek kullanıcı için yerel FastAPI ve SQLite uygulaması. Motor `work/MCP-Sentinel` kaynaklarından veya kurulmuş `portunusmcp-sentinel==1.4.0` paketinden çağrılır. Hedef kod temel kontrolde import edilmez.

Uygulama kökünden:

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.app:app --host 127.0.0.1 --port 8000
.\.venv\Scripts\python.exe -m pytest backend/tests -q
```

Varsayılan proje kökü `data/projects` klasörüdür. `TOOL_LENS_PROJECT_ROOTS` ortam değişkeni işletim sisteminin yol ayırıcısıyla ek izinli kökler tanımlayabilir. Ana dizini veya tüm diski kök olarak vermeyin. `TOOL_LENS_SENTINEL_PYTHON` farklı motor Python'ını seçer; `TOOL_LENS_DATA` veri klasörünü değiştirir.

Tarama profilleri: `rules_only`, `ai_review`, `dynamic`. Aynı anda tek iş başlatılır. Sentinel 0/1 çıkışı tamamlanmış, 2 hatalı, 3 eksik analizdir. Sıfır bulgu güvenlik garantisi değildir. API/model hatası temel raporu silmez. Dinamik profil Docker gerektirir ve hedefi hostta çalıştırmaz.

İzin tablosu Python kaynakları içindeki doğrudan tanınan çağrılarla sınırlıdır; helper akışlarını eksiksiz keşfettiğini iddia etmez. Beyan ve statik çıkarım test gözlemi değildir. Şu an genel dosya/ağ runtime izleme yoktur; ölçülmeyen değerler `not_measured` kalır.

Kullanıcı kararları, özgün motor raporundan ayrı tutulur. Raporlar ve kaynak görüntüleri yerel `data` klasöründe saklanır. API anahtarları ayarlar JSON'una yazılmaz; sağlayıcı ortam değişkeninin adı belirtilir. Dış servise gönderilmeden önce sınırlı kanıt paketi sağlayıcı katmanında maskelenir.

`/api/docs` yerine FastAPI'nin `/docs` sayfası HTTP sözleşmesini gösterir. Üretim frontend derlemesi varsa aynı sunucu SPA'yı da sunar. Canlı laboratuvar `/api/lab` ve `/api/demos` altında gerçek MCP çağrıları yapar; riskli örneklerin çalıştırılması Docker ile sınırlıdır.

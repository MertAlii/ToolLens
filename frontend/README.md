# ToolLens arayüzü

React ve TypeScript tabanlı yerel güvenlik çalışma alanı. Gerçek backend kayıtlarını gösterir; örnek istatistik veya hazır AI yanıtı içermez.

## Çalıştırma

```powershell
npm install
npm run dev
```

Backend `http://127.0.0.1:8000` adresinde çalışmalıdır. Vite `/api` isteklerini bu adrese yönlendirir. Arayüz `http://127.0.0.1:5173` adresindedir.

```powershell
npm run build
npm test
```

Üretim çıktısı `dist/` klasörüdür. Fontlar ve Monaco paketlerden yerel derlemeye dahil edilir; harici CDN kullanılmaz. Logo `public/toollens-logo.png` dosyasından yüklenir.

## Ekranlar

Genel bakış, ilk kurulum, projeler ve kontrol geçmişi, gerçek tarama profilleri, risk/kanıt inceleme, kullanıcı değerlendirmesi, AI açıklaması ve indirilebilir yama, araç/yetki karşılaştırması, sürüm farkları, kural rehberi, raporlar, AI bağlantıları, ayarlar ve canlı MCP laboratuvarı.

Sunum görünümü varsayılandır. Teknik görünüm kaynak kodunu ve ek ayrıntıları açar. Eksik veya ölçülmeyen alanlar temiz sonuç gibi gösterilmez.

## Dörtlü karar kutusu

Genel bakış ve kontrol sonucu ekranında olası etki ile kanıt yeterliliği birlikte gösterilir. Kutular inceleme önerisidir; güvenlik onayı veya otomatik karar değildir.

- Kritik/yüksek etki ve açık runtime ihlal kanıtı ya da gerekçe notu içeren insan değerlendirmesi: **Öncelikli düzelt**.
- Kritik/yüksek etki ve sınırlı dayanak: **Öncelikli doğrula**.
- Orta/düşük/bilgi etkisi ve yeterli dayanak: **Planlı düzelt**.
- Orta/düşük/bilgi etkisi ve sınırlı dayanak: **İzle ve veri topla**.

İnsan değerlendirmesi ayrı etiketlenir ve runtime kanıtı sayılmaz. AI onayı veya dinamik kaynak etiketi tek başına kanıt yeterliliğini yükseltmez. Etki alanı eksikse bulgu **Sınıflandırılmadı** grubunda kalır. Kutuyu seçmek gerçek bulguları filtreler; URL'deki `decision` parametresi bu filtreyi korur. Genel bakış kutuları yalnız seçili kapsamdaki en son kontrolün gerçek ayrıntılarıyla hesaplanır.

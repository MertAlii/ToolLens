"""Turkish presentation labels. Original engine evidence is never translated in place."""
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

RULE_TEXT = {
 'SENT-001': ('Araç gereğinden geniş izin istiyor olabilir','İzin dosyasında belirtilen erişim, kodda görülen ihtiyaçtan geniş olabilir.','İstenen erişimi gerçekten kullanılan klasör ve adreslerle sınırlandırın.'),
 'SENT-002': ('Gelen bilgi bir komut olarak çalıştırılabilir','Kullanıcıdan gelen metin, programın komut çalıştıran bir bölümüne ulaşabiliyor. Bu yol ayrıca incelenmeli.','Metni doğrudan çalıştırmak yerine izin verilen işlemleri açıkça tanımlayın.'),
 'SENT-003': ('Gelen bilginin kontrolü eksik olabilir','Araç, aldığı değeri kullanmadan önce tanınan bir tür veya şema kontrolü yapmıyor olabilir.','Beklenen türleri ve değer sınırlarını işlemden önce doğrulayın.'),
 'SENT-004': ('Dışarıdan gelen içerik yapay zekâyı yönlendirebilir','Araçtan gelen içerik modelin talimatlarına aktarılıyor. İçerikteki yönlendirmeler kararları etkileyebilir.','Dış içerik ile modelin talimatlarını ayırın ve desteklenen temizleme yöntemini uygulayın.'),
 'SENT-005': ('Kod içinde gizli bir anahtar olabilir','Kaynakta parola veya erişim anahtarına benzeyen bir değer bulundu. Gerçek bir anahtar olup olmadığı ayrıca incelenmeli.','Gerçek anahtarı koddan çıkarın; kullanıldıysa yenileyin ve güvenli bir yapılandırmadan okuyun.'),
 'SENT-006': ('Bağlanan kişinin kimliği kontrol edilmiyor olabilir','Bir web uç noktasında tanınan kimlik doğrulama bulunmadı. Kontrol başka bir katmanda yapılıyor olabilir.','İşlem başlamadan önce kimlik bilgisini doğrulayın ve geçersiz istekleri reddedin.'),
 'SENT-007': ('Araç tanımının kaynağı doğrulanmıyor olabilir','Araç tanımı kayıt öncesinde desteklenen bir bütünlük kontrolünden geçmiyor olabilir.','Tanımın güvenilir kaynaktan geldiğini imza veya doğrulanmış özetle kontrol edin.'),
 'SENT-008': ('Testte izin dışı bir araç çağrısı işlendi','Desteklenen testte, izin verilen araçlar dışında bir çağrının işlenmesine ilişkin kayıt oluştu.','Her araç çağrısından önce geçerli izinleri kontrol edin.'),
 'SENT-009': ('Çok büyük bir girdi sorun oluşturdu','Desteklenen testte, boyut sınırı veya işlemin devamlılığıyla ilgili bir sorun gözlendi.','Girdi boyutlarını işlem başlamadan önce sınırlandırın.'),
 'SENT-010': ('Testte girdi, işlem çalıştırmaya yol açtı','İzole testin kontrol dosyasında beklenmeyen değişiklik kaydedildi. Kanıt yalnız bu test koşullarını kapsar.','Girdiyi çalıştırılacak komut yerine veri olarak işleyin.'),
 'SENT-011': ('Beklenen biçime uymayan girdi işlendi','Desteklenen testte, araç tanımına uymayan bir girdinin işlendiğine ilişkin kayıt oluştu.','Zorunlu alanları ve değer türlerini işlemden önce kontrol edin.'),
 'SENT-012': ('Dosyaya erişim sınırı eksik olabilir','Dosya yolunun izin verilen klasörün içinde tutulduğunu doğrulayan kontrol tanınamadı.','Dosyanın gerçek yolunu çözümleyip izin verilen klasörün içinde kaldığını doğrulayın.'),
 'SENT-013': ('Araç açıklamasında yönlendirici bir ifade var','Açıklama, aracın işlevini tanıtmanın ötesinde yapay zekânın davranışını değiştirmeye çalışıyor olabilir.','Açıklamayı aracın amacı, girdileri ve sonuçlarıyla sınırlayın.'),
 'SENT-014': ('Girdi, komutun seçeneklerini değiştirebilir','Kullanıcının verdiği değer bir komutun seçenek alanına ulaşıyor olabilir. Argüman listesi kullanılması bu riski tek başına ortadan kaldırmaz.','Seçenek gibi başlayan girdileri doğrulayın; komuta uygun seçenek sonlandırıcısı veya güvenli nesne arayüzü kullanın.'),
 'SENT-015': ('Araç istenmeyen bir adrese istek gönderebilir','Kullanıcının verdiği bağlantı, adres ve protokol sınırları doğrulanmadan dış isteğe ulaşabilir.','Yalnız gerekli adreslere izin verin; yönlendirmeler dahil her bağlantı hedefini doğrulayın.'),
 'SENT-016': ('Sunucuya ait erişim anahtarı izinsiz kullanılabilir','Kendi anahtarı olmayan bir kullanıcı için sunucunun anahtarına geçiş yapılabiliyor olabilir. Yetkili aracılık başka bir katmanda uygulanmış olabilir.','Kullanıcının kimliğini ve devredilen yetkiyi işlemden önce doğrulayın; sunucu anahtarını seçilebilir yedek yol olarak sunmayın.'),
 'TL-R001': ('Araç açıklaması yapay zekâyı yönlendirmeye çalışıyor olabilir','Yayımlanan açıklamada aracın işlevini anlatmanın dışında talimat benzeri bir ifade bulundu. Bu, tek başına saldırının gerçekleştiğini göstermez.','Araç açıklamasını işlevi, girdileri ve çıktılarıyla sınırlayın; kaynağını doğrulayın.'),
 'TL-R002': ('Aracın beklediği girdi biçimi açık değil','Yayımlanan girdi şemasında üst düzey nesne türü bulunmuyor. Gerçek sunucunun girdiyi nasıl doğruladığı bilinmiyor.','Araç tanımını sunucunun belgeleriyle karşılaştırın ve beklenen girdi biçimini açıkça tanımlayın.'),
}


def present_finding(finding):
    values=RULE_TEXT.get(finding.get('rule_id'))
    if values is None:
        values=('İncelenmesi gereken bir kayıt bulundu','Analiz bileşeni bu kayıt için bir uyarı oluşturdu. Bu kural için doğrulanmış sade açıklama henüz bulunmuyor.','Özgün teknik açıklamayı ve kanıtı geliştiriciyle birlikte inceleyin; kapsamı doğrulamadan kesin karar vermeyin.')
    return dict(zip(('title','why','fix'),values))


def report_summary(scan):
    remote=scan.get('analysis_kind')=='remote_contract'
    complete=scan.get('status')=='completed' and scan.get('analysis_complete') is True
    findings=scan.get('findings') or []
    if remote:
        title=('Araç tanımlarındaki kayıtlar incelenmeli' if findings else 'Araç tanımlarında uyarı bulunmadı') if complete else 'Araç tanımı incelemesi tamamlanamadı'
        action='Yalnız sunucunun yayımladığı araç açıklamaları ve girdi şemaları incelendi. Kaynak kodu ve gerçek dosya/ağ davranışı incelenmedi. Bu sonuç sunucunun güvenli olduğu anlamına gelmez.'
        if not complete:action='Bağlantı veya inceleme aşaması eksik kaldı. Mevcut araç tanımları tam bir sonuç olarak yorumlanmamalı. Kaynak kodu ve gerçek davranış ayrıca değerlendirilmedi.'
        scope='Yalnız araç tanımları'
    else:
        title='İnceleme gerekli' if findings else 'Bu kapsamda belirgin risk bulunmadı' if complete else 'Sonuç için bilgi yetersiz'
        action='Bulguların kanıtlarını inceleyin; önemli riskler giderilmeden hassas erişim vermeyin.' if findings else 'Kullanım öncesinde gerekli izinleri sınırlandırın. Bu sonuç, incelenen kapsamla sınırlıdır.' if complete else 'Tamamlanamayan aşamayı giderip kontrolü yeniden çalıştırın. Bu kayıt güvenli kullanım onayı değildir.'
        scope='Kaynak kodu ve izole test' if scan.get('profile')=='dynamic' else 'Kaynak kodu'
    return {'title':title,'action':action,'scope':scope,'remote':remote}


WARNING_TEXT={
 'remote_scope':'Yalnız yayımlanan araç tanımları incelendi. Kaynak kod ve gerçek davranış değerlendirilmedi.',
 'remote_ai_bound':'Araç tanımlarının tümü yapay zekâ bağlamına sığmadı; yorum yalnız gönderilen tanımları kapsar.',
 'ai_review_bound':'Bulguların tümü yapay zekâya gönderilmedi; kalan kayıtlar ayrıca incelenmeli.',
 'source_changed':'Kaynak dosyalar kontrol sırasında değişti. Kanıtların güncel sürümle eşleştirilmesi sınırlıdır.',
 'engine_incomplete':'Kod incelemesi tamamlanamadı. Teknik kayıtta belirtilen eksik kapsam hakkında güvenli sonucu verilemez.',
 'runtime_worker_failed':'İzole davranış testi tamamlanamadı; Docker ve teknik kontrol günlüğü incelenmeli.',
 'typescript_inventory':'TypeScript araç envanteri motorun kapsam kaydına dayanır. Yerel yetki çıkarımı Python ile sınırlıdır.',
 'dynamic_discovery_incomplete':'İzole test sırasında araçların tamamı keşfedilemedi; davranış incelemesi eksik kaldı.',
 'dynamic_probe_plan_fallback':'Yapay zekâdan geçerli test planı alınamadığı için sabit test sırası ve çalışma sırasında alınan şemalar kullanıldı.',
}

def present_warning(warning):
    code=warning.get('code','') if isinstance(warning,dict) else ''
    message=warning.get('message','') if isinstance(warning,dict) else str(warning)
    if code in WARNING_TEXT:return WARNING_TEXT[code]
    if code.startswith('dynamic_probe_'):return 'Desteklenen davranış testlerinden biri beklenen biçimde tamamlanamadı; özgün kayıt teknik ayrıntıda bulunur.'
    if 'unresolved call' in message:return 'Kodda bir çağrının etkisi kesin çözülemedi; ilgili güvenlik kontrolünün bulunduğu doğrulanamadı.'
    if 'unresolved launch state' in message:return 'Aracın nasıl başlatıldığı kesin çözülemedi; inceleme birden fazla olası çalışma yolunu kapsıyor.'
    return 'İncelemenin kapsamını etkileyen ek bir teknik kayıt oluştu. Özgün açıklamayı teknik ayrıntılardan inceleyin.'


def format_date(value):
    if not value:return 'Kaydedilmedi'
    try:
        date=datetime.fromisoformat(str(value).replace('Z','+00:00'))
        if date.tzinfo is None:return date.strftime('%d.%m.%Y %H:%M')+' (zaman dilimi belirtilmemiş)'
        try:zone=ZoneInfo('Europe/Istanbul')
        except ZoneInfoNotFoundError:zone=timezone(timedelta(hours=3))
        return date.astimezone(zone).strftime('%d.%m.%Y %H:%M')+' (Türkiye saati)'
    except (ValueError,TypeError):return 'Tarih çözümlenemedi'

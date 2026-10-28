# ToolLens değerlendirme kümesi

Bu klasör gerçek uygulama sonuçlarını taklit etmez. Bağımsız yazılmış, denetimli kaynak örnekleri ve ölçüm komutları içerir. Kaynaklar taranır; riskli hedefler host üzerinde import edilmez veya çalıştırılmaz.

## Sabitlenmiş örnekler

- Altı aile × dört riskli/düzeltilmiş çift = 48 kaynak proje.
- Her ailede ilk iki çift geliştirme, son iki çift held-out değerlendirmedir.
- Sekiz zararsız, sekiz inceleme gerektiren ve sekiz belirsiz değişiklik = 24 sürüm çifti.
- Manifestler ve kaynak hash'leri tarama başlamadan sabitlenir. Beklentiler sonuçlara göre değiştirilmez.
- Credential örneklerindeki anahtar biçimli değerler uydurma, işlevsiz test dizeleridir; gerçek hizmette kullanılmaz.

Örnekleri oluşturmak: `.venv/Scripts/python.exe evaluation/generate_cases.py` (proje kökünden). Manifest var ve farklıysa komut değişikliği reddeder.

Tam kaynak ölçümü: `.venv/Scripts/python.exe evaluation/run_evaluation.py --jobs 2`.

Kısa ölçüm: `.venv/Scripts/python.exe evaluation/run_evaluation.py --smoke --jobs 2`.

Sonuçlar tarihli `results/` klasöründe ham motor raporları ve `summary.json` olarak saklanır. İstenen kural dışındaki bulgular ayrıca korunur. Süre aşımı ve eksik rapor temiz sonuç sayılmaz. Precision/recall yalnız tamamlanmış hedef-kural gözlemleri için hesaplanır; başarısız gözlem sayısı ayrıca gösterilir.

## Sürüm ölçümünün sınırı

Ölçüm, backend'in gerçek metadata çıkarımını kullanır. Değişen araç kimliği, dinamik açıklama ve eksik izin beyanı ayrıca belirsizlik koşulu olarak denetlenir. Bu belirsizlik denetimleri değerlendirme aracının açık kontrolleridir; ürünün her akışta aynı özelliği desteklediği veya bir saldırı gerçekleştiği anlamına gelmez.

## Kullanılabilirlik çalışması protokolü

Beş gönüllü için aynı görevler iki görünümde uygulanacaktır: bir riski bulma, dayanağını açıklama, yetki farkını belirleme, eksik sonucu tanıma ve düzeltme sonrası farkı yorumlama. Görev sırası dengelenir; süre ve doğru karar sayısı kaydedilir. Katılımcı onayı alınmadan kişisel veri toplanmaz. İnsan çalışması henüz yapılmamıştır; ölçüm sonucu uydurulmaz.

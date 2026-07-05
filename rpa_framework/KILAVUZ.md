# RPA Studio - Eksiksiz Kılavuz

RPA Studio gerçek bir masaüstünü otomatikleştirir. "Şuna tıkla, şunu yaz, şu
resmi bekle, şu metni oku" diyen kısa bir betik yazarsınız, Çalıştır'a
basarsınız ve program tıpkı bir insan gibi fareyi ve klavyeyi kullanır - ama
daha hızlı ve yorulmadan.

Tek pakette üç şeydir:

- otomasyon yazmak, yakalamak ve çalıştırmak için bir **masaüstü IDE**,
- mevcut `.sikuli` betiklerinizin neredeyse değişmeden çalışmasını sağlayan
  **SikuliX uyumlu bir motor**,
- kendi programlarınızdan çağırabileceğiniz **içe aktarılabilir bir Python
  kütüphanesi**.

Bu kılavuz üçünü de kapsar. İngilizce sürüm TUTORIAL.md dosyasındadır.

---

## 1. Neden güvenilir: ekranı görmenin iki yolu

Otomasyon hedefleri birbirinden bağımsız iki yolla bulunur; güvenilirliği
sağlayan bu ikisinin birleşimidir:

1. **Yerel erişilebilirlik (birincil).** İşletim sistemine doğrudan sorar:
   "bu noktada hangi denetim var, adı ne, nerede?" Bu, ekran okuyucuların
   kullandığı katmandır - Windows UI Automation, Linux AT-SPI. Hızlı ve
   kesindir; tema veya çözünürlük değişimlerine dayanır.
2. **Bilgisayarlı görü + OCR (yedek).** Piksellere bir insan gibi bakar: ona
   kırpılmış bir ekran görüntüsü verirsiniz, o da bu resmi ekranda bulur
   (öznitelik eşleme, SIFT/ORB - ölçeklemeye ve küçük değişimlere dayanıklı) ve
   ekrandaki metni Tesseract OCR ile okur.

Biri başarısız olduğunda genellikle diğeri çalışır. `Target(...)` konumlandırıcı
ikisini birleştirir ve hangisinin işe yaradığını hatırlar (kendini onarır).

---

## 2. Kurulum ve ilk çalıştırma

### Kaynaktan (Python 3.8+ gerekir)

`rpa_framework` klasörünü içeren dizinde bir terminal açın:

    python -m venv .venv
    .venv\Scripts\activate           (Linux/macOS: . .venv/bin/activate)
    pip install -r rpa_framework\requirements.txt
    python -m rpa_framework.ide

RPA Studio penceresi açılır. Sonra:

1. Dosya > Örnek Aç, `hello_flow.py` seçin.
2. **Ctrl+3**'e (veya Çalıştır düğmesine) basın. Çıktı, Çıktı panelinde akar.
3. Duraklatmak için **Ctrl+4**; devam etmek için tekrar Çalıştır düğmesine
   basın; **Ctrl+5** durdurur.

### Bağımsız yapıdan (kurulum gerekmez)

GitHub Releases sayfasından `RPAStudio.exe` (Windows) veya `rpa-studio-linux`
klasörünü (Linux) indirip başlatın. Python, Qt, OpenCV ve Tesseract gömülüdür -
temiz bir makine hiçbir şey kurmadan çalıştırır.

---

## 3. IDE, panel panel

Pencere VS Code gibi düzenlenmiştir: ortada sekmeli bir düzenleyici, çevresinde
yerleştirilebilir paneller. Panelleri Görünüm menüsünden veya araç çubuğunun
sağındaki üç panel düğmesinden aç/kapatın; istediğiniz yere sürükleyin - düzen
hatırlanır.

### Düzenleyici (orta)
- Monokai renkleri, satır numaraları, geçerli satır vurgusu, girinti çizgileri.
- **Otomatik tamamlama**: iki harften sonra açılan liste her komutu (click,
  Pattern, findText, observe...), Python anahtar sözcüklerini ve dosyanızdaki
  sözcükleri önerir. Enter veya Tab kabul eder.
- **PyCharm tarzı düzenleme**: parantez/tırnak otomatik kapatma, Ctrl+/ yorum,
  Ctrl+D satır çoğaltma, Ctrl+Y satır silme, Alt+Shift+Yukarı/Aşağı satır
  taşıma, Tab/Shift+Tab girinti, akıllı Home, `:` sonrası otomatik girinti.
- **Canlı sözdizimi denetimi**: hatalı satırın numarası kırmızıya döner ve hata
  durum çubuğunda görünür.
- **Satır içi resimler**: `IMAGE: resim.png` satırı, resmi kodun içinde gösterir
  (çalışırken yok sayılır). Bu satıra sağ tıklayarak resmi açın, yeniden
  adlandırın veya silin.
- Ctrl+fare tekerleği yakınlaştırır. Kaydedilmemiş sekmelerde `*` görünür.
  Pencereye bir `.py` dosyası veya `.sikuli` klasörü sürükleyerek açın.

### Gezgin (sol)
Betiğinizin klasörünün ağacı. Açmak için çift tıklayın. Sağ tıklayarak dosya ve
klasör oluştur / yeniden adlandır / sil / kopyala / yapıştır (F2, Del, Ctrl+C,
Ctrl+V) veya başka bir klasör seçin. `.sikuli` klasörüne çift tıklamak içindeki
betiği açar. Bir resme çift tıklamak **Varlık Test Aracı**'nı açar: benzerlik
kaydırıcısını ayarlayın, resmi canlı denemek için "Ekranda Bul"a basın (eşleşme
üzerine kırmızı çerçeve çizilir) veya hazır bir Pattern satırı ekleyin.

### Element Spy (alt, Çıktı ile sekmeli)
"Start watching"e basıp fareyi hareket ettirin: imlecin altındaki gerçek arayüz
öğesi (rol, ad, id, sınıf, sınırlayıcı kutu, pid) OS erişilebilirlik ağacından
canlı gösterilir. Öğenin konumlandırıcısını anında eklemek için üzerine gelip
**sağ tıklayın**. Eylem seçici hazır bir eylem satırı da ekler (`.click()`,
`.type("..")`, `.check()`, `.select("..")`...). **Scrape Active Window** hedef
uygulamayı odaklamanız için 3 saniye bekler, sonra bulduğu her öğe için
adlandırılmış bir değişken ekler (temiz küçük harfli adlar, Türkçe karakterler
harf çevirisiyle). Ctrl+Shift+E paneli getirir.

### Window Spy (alt, sekmeli)
Açık her pencereyi başlık, işlem, pid, konum ve boyutla listeler. Birine çift
tıklamak bir `App(...)` ekler. Ctrl+Shift+W.

### Komutlar (sağ)
Her betik komutunun aranabilir, kategorili listesi. Açıklama için üzerine gelin;
kod parçasını eklemek için çift tıklayın.

### Çıktı (alt)
Betiğinizin yazdırdığı her şey canlı: normal metin beyaz, hatalar kırmızı,
durum olayları yeşil, araç mesajları sarı. `failed(...)` tıklanabilir bir ekran
görüntüsü gömer. Bir betik hata verdiğinde, betik satır numarasıyla birlikte
sade dilde bir açıklama gösterilir.

### Terminal (alt)
Gömülü bir komut satırı (Alt+F12). Bir komut yazın, Enter'a basın; `cd` ve
`clear` yerleşiktir, Yukarı/Aşağı geçmişi getirir, bir durdurma düğmesi çalışan
komutu sonlandırır. Windows'ta `cmd`, Linux'ta kabuğunuzu çalıştırır.

### Araç çubuğu araçları
- **Çalıştır / Duraklat / Durdur (Ctrl+3 / Ctrl+4 / Ctrl+5).** Betiğiniz her
  zaman ayrı bir yardımcı işlemde çalışır; `while True: pass` bile pencereyi
  donduramaz ve Durdur her zaman çalışır. Duraklatıldığında Duraklat düğmesi
  soluklaşır ve oynat düğmesi "Devam"a döner.
- **Resim Yakala, anında (Ctrl+1)** ve **gecikmeli (Ctrl+2).** Pencere gizlenir
  (gecikmeli, önce araç çubuğundaki gecikme kadar bekler, böylece menü veya
  vurgu durumları açabilirsiniz), ekran donar ve hedefin etrafına bir kutu
  sürüklersiniz. Sürükleme sırasında sağ tıklamak tıklamanın gerçekte nereye
  ineceğini işaretler (hedef ofseti). Yakalamayı adlandırırsınız ve bir
  `var = Pattern("ad.png").similar(0.95)` satırı eklenir (ofset ayarladıysanız
  `.targetOffset(x, y)` ile).
- **Ekrandan Bölge Yakala (Ctrl+Shift+D).** Bir alan sürükleyin; bir
  `var = Region(x, y, w, h)` eklenir.
- **Ekrandan Konum Yakala (Ctrl+Shift+L).** Bir nokta tıklayın; bir
  `var = Location(x, y)` eklenir.
- **Hedef Ofseti Çiz (Ctrl+Shift+O).** Bir `.targetOffset(x, y)` ölçmek için
  bir çizgi sürükleyin.
- **Ekran Metnini Oku / OCR (Ctrl+Shift+T).** Bir bölge sürükleyin; tanınan
  metin Çıktı'ya yazdırılır.
- **Dosyalarda Bul (Ctrl+Shift+F)**, **Dosyalarda Değiştir (Ctrl+Shift+R)**,
  **Dosyaya Git (Ctrl+Shift+N).**
- **Bağımsız EXE Derle (Araçlar menüsü).** Tek tıkla Nuitka derlemesini başlatır
  ve ilerlemeyi Çıktı'ya akıtır (yalnızca kaynaktan çalışırken).
- **Yardım menüsü.** Bu kılavuz İngilizce (F1) ve Türkçe (F2) uygulama içinde
  açılır.

---

## 4. İlk betiğiniz

Yeni dosya, şunu yazın, `ilk.py` olarak kaydedin, Ctrl+3'e basın:

    print("fareyi izle!")
    hover(Location(500, 300))
    type("merhaba robot" + Key.ENTER)

İçe aktarma gerekmez - aşağıdaki her komut yerleşiktir. Betikler ayrıca
`async def main(): ...` tanımlayabilir ve otomatik beklenir; uzun döngülerde
`await checkpoint()` kullanabilirsiniz.

---

## 5. Tam betik başvurusu

Buradaki her şey IDE betiklerinde, `rpa-run` betiklerinde ve bir `.sikuli`
dosyasında içe aktarmasız kullanılabilir. (Kendi Python programlarınızda önce
içe aktarın - bölüm 8.)

### 5.1 Fare

    click("kaydet.png")               resmi bul, merkezine sol tıkla
    click(Location(100, 200))         tam koordinata tıkla
    click(region)                     bir bölgenin merkezine tıkla
    doubleClick("simge.png")          çift tıkla
    rightClick("satir.png")           sağ tıkla
    hover("menu.png")                 fareyi hedefin üstüne getir
    dragDrop("dosya.png", "cop.png")  ilkini ikincinin üstüne sürükle
    drag("dosya.png"); dropAt("cop.png")   iki yarısı ayrı ayrı
    wheel(WHEEL_DOWN, 3)              3 çentik kaydır (WHEEL_UP yukarı)
    mouseMove(Location(10, 20))       fareyi taşı
    mouseMove(30, -5)                 buradan ofset kadar taşı
    mouseDown(); mouseUp()            düğmeyi elle bas / bırak

Bir tıklama hedefi resim yolu, Pattern, Location, Region, Match, Element veya
Target olabilir. Her tıklamaya `modifiers=` (ör. `KeyModifier.CTRL`) ve hedef
alt kısımdaysa kaydırıp yeniden tarayan `autoScroll=True` ekleyebilirsiniz.

### 5.2 Klavye

    type("merhaba" + Key.ENTER)       metin yaz sonra Enter
    type("alan.png", "metin")         önce alana tıkla, sonra yaz
    type("s", KeyModifier.CTRL)       Ctrl+S bas
    paste("uzun metin")               panodan yapıştır (hızlı, her metin için)
    keyDown(Key.SHIFT); keyUp(Key.SHIFT)   tuşu tut / bırak

`Key.*`: ENTER, TAB, ESC, BACKSPACE, DELETE, oklar, HOME/END, PAGE_UP/DOWN,
F1-F12, CTRL/ALT/SHIFT/WIN ve daha fazlası. `KeyModifier.*`: CTRL, ALT, SHIFT,
WIN/META/CMD (birleştirmek için toplayın: `CTRL + SHIFT`).

### 5.3 Resim bulma

    m = find("logo.png")              şimdi bul; Match döndürür (yoksa hata)
    wait("iletisim.png", 10)          10sn'ye kadar bekle; yoksa FindFailed
    exists("acilir.png", 3)           wait gibi ama None döndürür
    has("acilir.png")                 True/False kısayolu
    waitVanish("bekleme.png", 30)     kaybolana kadar bekle
    for m in findAll("satir.png"): ...  her tekrar (yineleyici)
    findAllList("satir.png")          liste olarak, en iyiden, hatasız
    findAllByRow("hucre.png")         yukarıdan aşağı sonra soldan sağa
    findAllByColumn("hucre.png")      soldan sağa sonra yukarıdan aşağı
    findBest("tamam.png", "evet.png") birkaçının en güçlü eşleşmesi
    findAny("a.png", "b.png")         şu an ekranda olanların listesi
    waitAny(10, "tamam.png", "hata.png")  herhangi biri; waitBest en güçlüsü
    waitBest(10, "a.png", "b.png")    bekle, en güçlüsünü döndür

İnce ayar: `Pattern("dugme.png").similar(0.9)` daha katı eşleşme, `.exact()`
neredeyse tam, `.targetOffset(20, 0)` bulunan merkezin 20px sağına tıklar.

### 5.4 Finder ile bir resmin içinde arama

`Finder` canlı ekran yerine kayıtlı bir resimde veya yakalanmış bir karede arar:

    f = Finder("ekran.png")
    if f.find("dugme.png"):
        print(f.next().getScore())
    for m in f.findAll("satir.png"):
        print(m.x, m.y)
    degisenler = Finder("once.png").findChanges("sonra.png")   # değişen alanlar

### 5.5 Ekrandaki metni okuma (OCR)

    Region(0, 0, 800, 200).text()     alandaki tüm metni tek dize olarak oku
    m = findText("Farklı Kaydet")     bir metin satırı bul; tıklanabilir Match
    findWord("Kullanici")             tek bir sözcük bul
    findLine("Toplam: 42")            bir satırın tamamını bul
    hasText("Hazir")                  True/False
    waitText("Bitti", 20)             metnin görünmesini bekle
    for m in findWords(): ...         tanınan her sözcük bir Match
    for m in findLines(): ...         her satır bir Match
    collectWordsText()                tüm sözcükler düz dize olarak
    collectLinesText()                tüm satırlar düz dize olarak

    OCR.readText("kirp.png")          herhangi bir resim/bölge/diziyi OCR yap
    OCR.readLine(region)              tek satır; readWord, readChar da var
    OCR.readWords(region)             sözcük Match'leri; readLines satır için
    OCR.language("tur")               OCR dilini değiştir

`findText`/`findWord` tıklayabileceğiniz bir Match döndürür:
`click(findText("Tamam"))`. Varsayılan dili `Settings.OcrLanguage = "eng_best"`
ile ayarlayın (gömülü: eng, eng_best, tur, dejavu_sans; daha fazla `.traineddata`
dosyasını vendor/tessdata içine koyup yeniden derleyin).

### 5.6 Olayları izleme (observe)

İşleyiciler kaydedin, sonra bir süre izleyin. İşleyiciler bir `ObserveEvent`
alır.

    def uyari_gelince(e):
        print("belirdi:", e.getMatch())
        click(e.getMatch())

    reg = Region(0, 0, 800, 600)
    reg.onAppear("uyari.png", uyari_gelince)   # veya onVanish / onChange
    reg.onChange(100, lambda e: print("değişti:", e.getChanges()))
    reg.observe(30)                            # engelleyici, 30sn'ye kadar
    reg.observeInBackground(30)                # bir iş parçacığında
    if reg.isObserving(): reg.stopObserver()
    for e in reg.getEvents(): print(e.getType())

`onChange(minPiksel, isleyici)` en az o kadar piksel değiştiğinde tetiklenir.
`ObserveEvent` şunlara sahiptir: `.getType()`, `.getMatch()`, `.getRegion()`,
`.getChanges()`, `.isAppear()/.isVanish()/.isChange()`, `.repeat()`.

### 5.7 Bölgeler, konumlar, geometri

    Region(0, 0, 800, 600)            ekranın bir alanı
    Location(500, 300)                tam bir nokta
    Offset(10, -4)                    göreli bir kaydırma
    r.getTopLeft(); r.getCenter(); r.getBottomRight()
    r.grow(20)                        her yönde 20px büyüt (2 ve 4 argümanlı da)
    r.nearby(50)                      grow için takma ad
    r.above(120); r.below(); r.left(); r.right(200)   r'nin çevresindeki şeritler
    r.union(other); r.intersection(other)
    r.offset(dx, dy); r.moveTo(loc); r.morphTo(other)
    r.setROI(x, y, w, h)              yerinde taşı+boyutlandır
    r.setRaster(satir, sutun); r.getCell(satir, sutun); r.getRow(i); r.getCol(j)
    r.highlight(2)                    2sn kırmızı çerçeve (renk isteğe bağlı)
    click(find("etiket.png").right(150))    bir çapaya göre davran

Bir `Region`'ın kendi `find/wait/exists/click/type/...` yöntemleri vardır,
böylece her aramayı sınırlayabilirsiniz: `Region(0,0,400,300).exists("s.png")`.
Bölgeye özel ayar: `r.setAutoWaitTimeout(5)`, `r.setWaitScanRate(3)`,
`r.setThrowException(False)`.

### 5.8 Uygulamalar ve pencereler

    app = openApp("notepad.exe")      program başlat, App tutamacı al
    switchApp("Not Defteri")          başlığa VEYA işlem adına göre odakla
    closeApp("Not Defteri")           bir pencerenin işlemini kapat
    app = App("Not Defteri"); app.open(); app.focus(); app.close()
    app.isRunning(); app.window()      pencere bir WindowRegion olarak
    win = windowRegion("Not Defteri") bir pencereye yapışık bölge
    win.moveTo(0, 0).resize(800, 600).focus()
    win.maximize(); win.minimize(); win.restore(); win.setBounds(...)
    win.find("kaydet.png")            yalnızca o pencerenin içinde ara

`App`/`switchApp` pid, tam başlık, başlık parçası veya işlem exe adına göre
eşleşir; böylece yerelleştirilmiş başlıklar ("Adsiz - Not Defteri",
"notepad.exe"den) bulunur.

### 5.9 Yerel arayüz öğeleri (erişilebilirlik)

    btn = findElement(name="Tamam", role="Button")
    findElement(name="Ateş", window="Silah Kontrol")   # yalnızca o pencerede
    findElement(automation_id="submit", timeout=5)
    clickElement(name="Tamam", role="Button")

Dönen `Element` gerçek denetim üzerinde çalışır:

    btn.click(); btn.doubleClick(); btn.rightClick(); btn.hover()
    field.setText("merhaba")   field.clear()    field.type("daha")
    box.check(); box.uncheck(); box.isChecked()
    combo.select("Seçenek 2")         bir combo aç ve ada göre seç
    listbox.selectItem("Satır 3")     bir liste/ağaç öğesini ada göre seç
    node.expand(); node.collapse()
    child = panel.child(name="Kaydet")  bu öğenin içinde ara
    e.getText(); e.getName(); e.getRole(); e.region(); e.highlight()

### 5.10 Kendini onaran çok çapalı hedefler

`Target` önce OS öğesini, sonra bir resmi, sonra OCR metnini dener ve oturum
boyunca hangisinin işe yaradığını hatırlar:

    Target(name="Ateş", window="Konsol", image="ates.png", text="ATEŞ").click()
    t = Target(automation_id="submit", image="submit.png")
    t.exists(); t.hover(); t.doubleClick(); t.targetOffset(5, 0).click()

### 5.11 Yalnızca görü ile denetimler (erişilebilirlik yok)

Erişilebilirlik ağacı olmayan Citrix, VDI veya video akışları için:

    findUI("button", text="Tamam")    Tamam düğmesine benzeyen Region listesi
    findUI("field"); findUI("any", region=Region(0,0,800,600))

### 5.12 İletişim kutuları ve kullanıcı girişi

    popup("bitti!")                   Tamam düğmeli mesaj kutusu
    popError("bir şey bozuldu")       hata simgeli mesaj kutusu
    if popAsk("Devam?"): ...          Evet/Hayır, Evet'te True döner
    ad = input("Adınız?")             tek satır metin (hidden=True parola için)
    notlar = inputText("Notlar:")     çok satırlı metin
    secim = select("Seç", options=["A", "B"])   açılır liste
    yol = popFile()                   dosya aç kutusu, bir yol döndürür

### 5.13 Ortam, pano, ayarlar

    Env.getClipboard(); Env.setClipboard("selam")
    Env.getMouseLocation(); Env.getScreenSize()
    Env.getOS(); Env.isWindows(); Env.isLinux(); Env.isMac()
    getNumberScreens(); Screen(0); Screen(1)      çoklu monitör

    Settings.MinSimilarity = 0.8      genel eşleşme katılığı (varsayılan 0.7)
    Settings.AutoWaitTimeout = 5      varsayılan wait() zaman aşımı
    Settings.ClickDelay = 0.3         ayrıca MoveMouseDelay, TypeDelay
    Settings.DelayBeforeDrag = 0.5    ayrıca DelayBeforeMouseDown/Drop
    Settings.DefaultHighlightTime = 3
    Settings.OcrLanguage = "tur"
    Settings.ObserveScanRate = 3      izlerken saniyedeki tarama
    setShowActions(True)              her eylemden önce işaret çak (demo)

### 5.14 Akış, yollar, çıktı

    sleep(2)                          saniye bekle (Duraklat düğmesine uyar)
    exit(0)                           çıkış koduyla şimdi dur
    setBundlePath("."); addImagePath("varliklar"); addImportPath("lib")
    makePath("a", "b"); getBundlePath(); getParentFolder()
    emit("asama", "giriş tamam")      IDE konsolunda yeşil durum olayı
    passed("giriş tamam")             Çıktı'da yeşil başarı satırı
    failed("düğme yok")               kırmızı satır + otomatik tıklanabilir görüntü
    wait_if_paused()                  döngüde Duraklat düğmesine yer aç

`passed`/`failed` böyle adlandırılır çünkü Python `pass`'ı ayırır ve yanında
çıplak `fail` tuhaf durur; `emit`, `passed`, `failed`, `wait_if_paused` ve
`checkpoint` çalıştırıcı tarafından sağlanır (IDE ve `rpa-run`).

---

## 6. Resimlerle çalışma

En hızlısı: IDE'de **Ctrl+1**'e basıp hedefin etrafına bir kutu sürükleyin -
kırpma betiğinizin yanına kaydedilir ve kod eklenir.

Elle: hedefi ekrana getirin, sıkıca kırpın (Windows'ta Win+Shift+S), `.png`'yi
betiğinizin yanına kaydedin ve dosya adını kullanın: `click("dugme.png")`.

İpuçları: ayrıntılı kırpmalar (metin, kenarlar, köşeler) düz tek renkli
alanlardan çok daha iyi eşleşir; kenarda 60-200 piksel en iyi noktadır. Kodun
üstüne `IMAGE: dugme.png` ekleyerek düzenleyicide önizleyin.

---

## 7. Mevcut SikuliX betiklerinizi çalıştırma

`bir_sey.sikuli` klasörünüzün içindeki `.py`'yi açıp Çalıştır'a basın -
yanındaki resimler otomatik bulunur. Bir klasörün tamamını komut satırından da
çalıştırabilirsiniz (bölüm 8). SikuliX betik yüzeyinin tamamı uygulanmıştır:
Region/Screen/Pattern/Match/Location/Offset/Finder/App/Key/KeyModifier/
Settings/Env/OCR, bulma ailesi, metin/OCR arama ailesi, observe/onAppear/
onVanish/onChange, iletişim kutuları ve geometri/raster yardımcıları.

Bilinmesi gereken farklar:

- Betikler Jython değil gerçek **CPython 3** üzerinde çalışır - modern Python
  çalışır, Java içe aktarmaları (`from java.awt ...`) çalışmaz.
- Resim eşleme **öznitelik tabanlıdır (SIFT)**, ölçeklemeye ve küçük tema
  değişimlerine dayanıklı; `similar(x)` yaklaşık bir katılık ayarıdır, kesin bir
  piksel yüzdesi değil.
- `type()`, tam SikuliX gibi, betik içinde Python'un yerleşik `type`'ını
  kasten gölgeler.
- Başka bir `.sikuli`'yi modül olarak yeniden kullanmak çalışır: `import mylib`,
  resim/içe aktarma yolunda `mylib.sikuli/mylib.py`'yi bulur ve API'yi
  otomatik enjekte eder.

---

## 8. Kütüphane / komut satırı olarak kullanma

### Bir betiği veya klasörü başsız çalıştırma

    rpa-run login.sikuli              bir .sikuli klasörünü çalıştır, sonra çık
    rpa-run test.py                   tek dosya
    rpa-run a.sikuli b.sikuli -c      birkaçı, hatada devam et
    rpa-run login.sikuli --verbose    emit() olaylarını da yazdır
    rpa-run --list                    betiklerde kullanılabilen her komutu listele

`rpa-run`, `java -jar sikulix.jar -r test.sikuli`'nin doğrudan karşılığıdır.
Tüm betikler geçerse çıkış kodu 0, aksi halde sıfırdan farklı - cron/CI için
uygun.

### Kendi Python'unuza içe aktarma

    pip install .            # pyproject.toml içeren klasörden (yalnızca motor)
    pip install .[gui]       # masaüstü IDE de

    import rpa_framework
    rpa_framework.run("login.sikuli")        # bir çıkış kodu döndürür

    from rpa_framework.compat.sikuli import Screen, Pattern, Key, Region
    scr = Screen()
    scr.click("dugme.png")
    scr.type("merhaba" + Key.ENTER)
    print(Region(0, 0, 800, 200).text())

    from rpa_framework.core import OSFacadeFactory, InspectorFactory
    backend = OSFacadeFactory.create()
    inspector = InspectorFactory.create()

Kapalı ağlar için çevrimdışı kurulum (eşleşen bir makinede tekerlek deposu
oluşturun):

    python -m rpa_framework.packaging.offline download ./wheelhouse
    pip install --no-index --find-links ./wheelhouse .

Linux ayrıntıları (RHEL/CentOS 8, bağımlılıklar, başsız Xvfb) LINUX.md'dedir.

---

## 9. Bağımsız ikilileri derleme

    scripts\build_windows.ps1               Windows: dist\RPAStudio.exe (+ selftest)
    scripts/build_linux.sh                  Linux GUI: dist/rpa-studio-linux.tar.gz
    scripts/build_linux.sh headless         Linux çalıştırıcı: dist/rpa-run.bin

Veya paketleyiciyi doğrudan çağırın:

    python -m rpa_framework.packaging.build             # GUI onefile
    python -m rpa_framework.packaging.build --headless  # rpa-run, Qt yok

Notlar: Nuitka çapraz derleme yapmaz (Windows'u Windows'ta, Linux'u Linux'ta
derleyin) ve Microsoft Store Python'u desteklemez (python.org kurulumu
kullanın). İlk derleme bir C derleyici indirir ve zaman alabilir. OCR gömmek
için derlemeden önce `vendor/tesseract/` (ikili + DLL'ler) ve `vendor/tessdata/`
(`.traineddata` dosyaları) klasörlerini `rpa_framework` yanına koyun; otomatik
gömülür ve bağlanır. Bayraklar: `--dry-run`, `--no-onefile`, `--console`. Tam
matris BUILDING.md'dedir.

---

## 10. Bir şeyler ters gittiğinde

- **FindFailed: image not found** - `.png` betiğin yanında değil; ad ve klasörü
  kontrol edin.
- **not found on screen** - daha büyük, daha ayrıntılı bir resim kırpın; hedefin
  görünür ve örtülmemiş olduğundan emin olun; `.similar(...)` veya genel
  `Settings.MinSimilarity`'yi düşürün.
- **text not found** - OCR net, makul büyüklükte metin ister;
  `Settings.OcrLanguage` veya daha dar bir bölge deneyin.
- **BackendError: ... required** - bir paket eksik;
  `pip install -r rpa_framework\requirements.txt` çalıştırın.
- **OCR hiçbir şey döndürmüyor** - `vendor` klasörü `rpa_framework` yanında yok
  (kaynak çalıştırmaları) veya exe onsuz derlenmiş.
- **Çoklu monitörde tıklamalar tuhaf yere iniyor** - hedef uygulamayı şimdilik
  birincil monitörde tutun veya `Screen(1)` ile sınırlayın.
- **Başka her şey** - `RPAStudio.exe --selftest report.txt` çalıştırın: arka
  ucu, inceleyiciyi, yakalamayı, OCR'yi, belgeleri ve örnekleri sınar ve her
  birini ok/fail olarak işaretler.

---

## 11. Düzen (geliştiriciler için)

    rpa_framework/
      core/os_facade/   fare, klavye, ekran yakalama, pencereler (OS başına)
      core/vision/      SIFT/ORB resim bulma, OCR, VDI denetim tespiti
      core/inspector/   erişilebilirlik ağacı (UIA / AT-SPI) + casus arka planı
      compat/sikuli.py  SikuliX uyumlu betik API'si
      ide/              düzenleyici, paneller, yakalama araçları, güvenli çalıştırıcı
      packaging/        Nuitka derlemesi, çalışma zamanı yolları, çevrimdışı depo
      scripting.py      Qt'siz betik çalıştırma (rpa-run ve IDE kullanır)
      examples/         çalışmaya hazır betikler

Yeni OS arka uçları `@register_backend`, inceleyiciler `@register_inspector` ile
kaydolur; fabrikalar yerel kütüphaneleri yalnızca gerektiğinde yükler, böylece
her modül her OS'ta içe aktarılır. Yeni bir yerleşik betik komutu eklemek için
onu `compat/sikuli.py`'ye ve `_EXPORTS`'a ekleyin - IDE tamamlaması, Komutlar
paneli, `rpa-run --list` ve enjekte edilen kapsamlar hepsi oradan okur.

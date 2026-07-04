# RPA Studio - Kullanim Kilavuzu

RPA Studio; masaustu otomasyonu icin gelistirilmis, SikuliX uyumlu, tek dosya
halinde calisan (kurulum gerektirmeyen) bir IDE + otomasyon motorudur.
Guvenilirlik iki katmanlidir: once isletim sisteminin erisilebilirlik agaci
(UI Automation), bulamazsa goruntu isleme (SIFT) ve OCR devreye girer.

Not: Bu dosyanin Ingilizce karsiligi TUTORIAL.md dosyasidir.

## 1. Hizli Baslangic

1. `RPAStudio.exe` dosyasini calistirin (ilk acilis 15-20 saniye surebilir).
2. `File > Open Example` menusunden `notepad_typing.py` ornegini acin.
3. `F5` ile calistirin, `F6` ile duraklatin/devam edin, `Shift+F5` ile durdurun.
4. Cikti sag altta Output panelinde canli olarak akar.

Kaynak koddan calistirmak icin: `python -m rpa_framework.ide`

## 2. IDE Turu

- **Sekmeler**: Sekmeye sag tiklayin: Close, Close Others, Close All,
  Close Tabs to the Right, Pin Tab (sekme rengi degisir ve toplu kapatmadan
  etkilenmez), Copy Full Path, Reveal in File Explorer, Rename File,
  Open in New Window.
- **Editor**: Monokai temasi, canli sozdizimi denetimi (hatali satir numarasi
  kirmizi olur, hata mesaji durum cubugunda gorunur), otomatik tamamlama,
  otomatik girinti. PyCharm kisayollari: parantez/tirnak otomatik kapanir,
  secili metni parantez iceine alma, `Ctrl+/` yorum, `Ctrl+D` satiri cogalt,
  `Ctrl+Y` satiri sil, `Alt+Shift+Yukari/Asagi` satiri tasi, `Tab/Shift+Tab`
  blok girinti, akilli Home.
- **Explorer**: Ana klasoru sabit tutar; dosya acinca kok degismez. Ust arac
  cubugu: yeni dosya, yeni klasor, yeni .sikuli klasoru, yenile, tumunu ac/
  kapat, klasor sec. Sag tik: kopyala/yapistir/sil/yeniden adlandir, tam yolu
  kopyala, Dosya Gezgininde goster. Dosyalar suruklenerek tasinabilir.
  .py dosyalari Python simgesi ile, resimler ve .sikuli klasorleri kendi
  simgeleri ile gorunur.
- **Commands paneli**: Tum komut listesi; cift tiklayinca koda eklenir.
  Ust kisimda arama kutusu ve ac/kapat dugmeleri vardir.
- **Terminal**: Alt+F12 ile acilir; komutlar gomulu olarak calisir. Yandaki
  dugme sistem terminalini proje klasorunde acar.
- **Arama**: `Ctrl+Shift+F` dosyalarda bul, `Ctrl+Shift+R` dosyalarda degistir,
  `Ctrl+Shift+N` dosyaya git. Sonuca cift tiklayinca ilgili satir acilir.
- **Ayarlar**: `File > Settings` (Ctrl+,). Genel sekmesi: editor yazi boyutu,
  gecikmeli yakalama suresi, varsayilan Pattern benzerligi, OCR dili,
  calistirmadan once otomatik kaydet. Kisayollar sekmesi: uygulamadaki HER
  kisayolu degistirebilirsiniz.

## 3. Yakalama Araclari (arac cubugu)

| Arac | Kisayol | Ne yapar |
|---|---|---|
| Capture Image (Instant) | Ctrl+Shift+C | Ekrandan hedef resim secin |
| Capture Image (Delayed) | Ctrl+Shift+D | Spinbox suresi kadar bekler, sonra secin |
| Capture Region | Ctrl+Shift+G | `degisken = Region(x, y, w, h)` ekler |
| Capture Location | Ctrl+Shift+L | Tiklanan nokta: `degisken = Location(x, y)` |
| Draw Target Offset | Ctrl+Shift+T | Iki nokta arasi: `degisken = Offset(dx, dy)` |
| Read Screen Text (OCR) | Ctrl+Shift+R | Secilen alandaki metni okur |

Ortak akis: surukleyin -> isterseniz yeniden cizin veya resim yakalarken sag
tikla tiklama noktasi (offset) isaretleyin -> **Bosluk/Enter** ile onaylayin,
**Esc** ile vazgecin. Sadece DEGISKEN adini yazarsiniz; resim
`degisken.png` olarak kaydedilir ve kod soyle eklenir:

```python
giris_dugmesi = Pattern("giris_dugmesi.png").similar(0.95)
click(giris_dugmesi)
```

Editorde resim iceren satira sag tiklayin: Open Image (Asset Tester),
Rename Image File (dosya + koddaki degisken adi birlikte degisir),
Delete Image (dosya + satir silinir).

Explorer'da bir resme cift tiklarsaniz **Asset Tester** acilir: benzerlik
ayari ile ekranda arar ve bulundugu yeri kirmizi cerceveyle gosterir.

## 4. Element Spy ve Window Spy

**Element Spy** (Ctrl+Shift+E, sag altta): "Start watching" deyin, herhangi
bir uygulamada bir kontrolun uzerine gelin, **Bosluk** tusuna basin. Kod
hazir olarak eklenir ve pencereye kilitlenir (baska uygulamada asla aramaz):

```python
giris_dugmesi = findElement(name="Giris", role="Button", window="Uygulamam")
giris_dugmesi.click()
```

Action listesinden tiklama/yazma/secme gibi bir eylem secerseniz o satir da
birlikte eklenir. "Raw tree deep scan" kutusu Electron/web tabanli
uygulamalarda ic ice katmanlari delerek en kucuk ogeyi bulur.
"Scrape whole active window" aktif penceredeki tum isimli ogeleri tek seferde
degisken olarak cikarir.

Bulunan oge dogrudan kullanilabilir: `.click() .doubleClick() .rightClick()
.hover() .type("...") .clear() .setText("...") .getText() .check() .uncheck()
.isChecked() .select("Oge") .selectItem("Satir") .child(...) .highlight()`

**Window Spy** (Ctrl+Shift+W): Acik tum pencereleri baslik, islem (process)
adi, PID, pencere kimligi, konum ve boyut ile listeler. Satira cift tiklayinca
`uygulama = App("Baslik")` olarak eklenir.

## 5. Uygulama ve Pencere Yonetimi

```python
app = openApp("notepad.exe")      # baslatir, PID'i izler, pencereyi bekler
app.focus()                        # baslik degisse bile PID/islem adiyla bulur
app.window().moveTo(0, 0).resize(800, 600)
app.window().maximize()            # minimize() restore() setBounds() focus()
app.close()

switchApp("notepad")               # baslik VEYA islem adi ile odakla
switchApp("Rapor", contains=False) # tam baslik eslesmesi
```

Onemli: Turkce Windows'ta Not Defteri "Adsiz - Not Defteri" basligiyla acilir;
`openApp`/`switchApp` islem adina da baktigi icin yine bulunur.

## 6. Komut Ozeti (SikuliX uyumlu)

| Komut | Ornek | Aciklama |
|---|---|---|
| click / doubleClick / rightClick | `click("dugme.png")` | Resmi bul ve tikla |
| hover / dragDrop / wheel | `dragDrop("a.png", "b.png")` | Fare eylemleri |
| type / paste | `type("merhaba" + Key.ENTER)` | Klavye; Key.* ozel tuslar |
| wait / exists / waitVanish | `wait("kayit.png", 10)` | Bekle / var mi / kaybolana kadar |
| find / findAll | `m = find("logo.png")` | Match dondurur |
| Pattern | `Pattern("d.png").similar(0.9).targetOffset(10, -4)` | Hassasiyet + kayma |
| Region / Location / Offset | `Region(0, 0, 800, 600)` | Alan / nokta / kayma |
| autoScroll | `click("satir.png", autoScroll=True)` | Bulamazsa kaydirip tekrar arar |
| highlight | `find("logo.png").highlight(2)` | Ekranda kirmizi cerceve |
| Target | `Target(name="Kaydet", image="kaydet.png", text="KAYDET").click()` | Coklu kanca: oge -> resim -> OCR; kendini onarir |
| findUI | `findUI("button", text="OK")` | Erisilebilirlik olmayan (VDI) ekranlarda gorsel bulma |
| Region.text() | `Region(0, 0, 400, 80).text()` | OCR ile metin oku |
| passed / failed | `failed("dugme yok")` | Yesil satir / kirmizi satir + otomatik ekran fotografi |
| Env | `Env.getClipboard()` | setClipboard, getMouseLocation, getScreenSize, getOS |
| Settings | `Settings.MinSimilarity = 0.8` | ClickDelay, TypeDelay, DelayBeforeDrag, DefaultHighlightTime, OcrLanguage... |

Dinamik bolgeler: `match.nearby(50) .above() .below() .left() .right(200)
.union(r2) .intersection(r2)`; `windowRegion("Baslik")` penceye yapisiktir,
pencere tasinsa da takip eder.

## 7. OCR

Tesseract gomulu gelir. Diller: `eng`, `eng_best` (yuksek dogruluk),
`tur` (Turkce), `dejavu_sans` (ozel egitilmis). Ayarlar penceresinden veya
kod icinden secilir:

```python
Settings.OcrLanguage = "eng_best"
print(Region(0, 0, 600, 120).text())
```

## 8. .sikuli Klasorleri

SikuliX yapisiyla uyumludur: `akis.sikuli/akis.py` ve resimleri ayni klasorde.
Explorer arac cubugundaki kamera dugmesi veya sag tik menusu ile
"New Sikuli Folder" olusturur; `File > Open SikuliX Folder` ile acilir,
surukle-birak da calisir.

## 9. Duraklatma ve Durdurma

`F6` calisan betigi bir sonraki eylemde (tiklama, yazma, arama, sleep)
guvenle duraklatir; tekrar `F6` devam ettirir. `Shift+F5` aninda durdurur.
Betikler ayri bir islemde calisir; donse bile IDE asla kilitlenmez.

## 10. EXE Derleme

`Tools > Build Standalone EXE` (kaynaktan calisirken) veya:

```
.venv-build\Scripts\python.exe -m rpa_framework.packaging.build
```

Cikti: `dist/RPAStudio.exe` - Python, OpenCV ve Tesseract kurulu olmayan
temiz bir makinede calisir.

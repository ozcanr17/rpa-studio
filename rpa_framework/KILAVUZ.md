# RPA Studio — Kullanım Kılavuzu

RPA Studio; masaüstü otomasyonu için geliştirilmiş, SikuliX uyumlu, tek dosya
halinde çalışan (kurulum gerektirmeyen) bir IDE + otomasyon aracıdır.

**Nasıl çalışır?** Güvenilirlik iki katmanlıdır:

1. **Erişilebilirlik ağacı (birincil yol):** Windows'ta UI Automation, Linux'ta
   AT-SPI üzerinden gerçek arayüz öğeleri (düğme, kutu, menü) doğrudan bulunur.
   Bu yol çözünürlükten ve temadan etkilenmez.
2. **Görüntü işleme + OCR (yedek yol):** Öğeye erişilemiyorsa ekran görüntüsü
   üzerinde SIFT öznitelik eşleştirmesi yapılır (gri ton + CLAHE, ardından tema
   değişimlerine dayanıklı kenar haritası ve 0.5×–3× ölçek taraması) ve
   Tesseract ile metin okunur.

Betikleriniz IDE'den **ayrı bir işlemde** çalışır: betik çökse ya da sonsuz
döngüye girse bile arayüz asla kilitlenmez.

> İngilizce sürüm için `TUTORIAL.md` dosyasına bakın.

---

## 1. Hızlı Başlangıç

1. `RPAStudio.exe` dosyasını çalıştırın (ilk açılış 15–20 sn sürebilir).
2. `File > Open Example` menüsünden `notepad_typing.py` örneğini açın.
3. Çalıştırın (▶ düğmesi), `Ctrl+4` ile duraklatın, `Ctrl+5` ile durdurun.
4. Çıktı alttaki **Output** panelinde canlı akar; hata olursa kırmızı ve
   açıklamalı bir mesaj + otomatik ekran görüntüsü eklenir.

Kaynak koddan çalıştırmak için: `python -m rpa_framework.ide`

## 2. Arayüz Rehberi

### Sekmeler (PyCharm tarzı)
Sekmeye sağ tıklayın: **Close / Close Others / Close All / Close Tabs to the
Right / Pin Tab** (sabitlenen sekme turuncu görünür ve toplu kapatmadan
etkilenmez) / **Copy Full Path / Reveal in File Explorer / Rename File /
Open in New Window**.

### Editör
- Monokai teması, **girinti kılavuz çizgileri**, satır numaraları.
- **Canlı sözdizimi denetimi:** hatalı satırın numarası kırmızıya döner, hata
  mesajı durum çubuğunda görünür.
- **Otomatik tamamlama:** tüm komutlar, değişkenleriniz ve öğe metotları.
- PyCharm kısayolları: parantez/tırnak otomatik kapanır ve üzerine yazılır,
  seçili metin parantez içine alınır, `Ctrl+/` yorum, `Ctrl+D` satırı çoğalt,
  `Ctrl+Y` satırı sil, `Alt+Shift+↑/↓` satırı taşı, `Tab / Shift+Tab` blok
  girinti, akıllı Home, `return/pass` sonrası otomatik girinti azaltma.
- Resim geçen satıra sağ tıklayın: **Open Image** (Asset Tester),
  **Rename Image File** (dosya adı *ve* koddaki değişken adı birlikte değişir),
  **Delete Image** (dosya + satır silinir).

### Explorer (sol panel)
- Kök klasör sabittir; dosya açınca kök değişmez, kaybolmazsınız.
- Araç çubuğu: yeni dosya, yeni klasör, **yeni .sikuli klasörü**, yenile,
  tümünü aç/kapat, klasör seç.
- Sağ tık: kopyala / yapıştır / sil / yeniden adlandır / tam yolu kopyala /
  Dosya Gezgini'nde göster. Dosyalar sürüklenerek taşınabilir.
- `.py` dosyaları Python simgesiyle, resimler turuncu resim simgesiyle,
  `.sikuli` klasörleri kutu simgesiyle görünür.

### Alt Panel Grubu
**Output, Terminal, Element Spy ve Window Spy** tek grupta sekmelidir;
istediğiniz sekmeyi sürükleyerek ayırabilirsiniz. Araç çubuğunun sağındaki üç
düğme sol / alt / sağ panelleri tek tıkla gizler-gösterir (View menüsünden de
tek tek açılabilir).

### Terminal (`Alt+F12`)
Komutlar gömülü kabukta çalışır; yandaki düğme sistem terminalini proje
klasöründe açar.

### Arama
- `Ctrl+Shift+F` — dosyalarda bul (sonuca çift tıklayınca ilgili satır açılır)
- `Ctrl+Shift+H` — dosyalarda değiştir
- `Ctrl+Shift+N` — dosyaya git

### Ayarlar (`Ctrl+,`)
- **General:** editör yazı boyutu, gecikmeli yakalama süresi, varsayılan
  Pattern benzerliği, OCR dili, çalıştırmadan önce otomatik kaydetme.
- **Shortcuts:** uygulamadaki **her** kısayolu değiştirebilirsiniz.

### Varsayılan Kısayollar

| İşlev | Kısayol | İşlev | Kısayol |
|---|---|---|---|
| Yeni betik | Ctrl+N | Çalıştır | Ctrl+^ |
| Aç | Ctrl+O | Duraklat / Devam | Ctrl+4 |
| Kaydet | Ctrl+S | Durdur | Ctrl+5 |
| Sekmeyi kapat | Ctrl+W | Anında yakalama | Ctrl+1 |
| Ayarlar | Ctrl+, | Gecikmeli yakalama | Ctrl+2 |
| Dosyalarda bul | Ctrl+Shift+F | Bölge yakala | Ctrl+Shift+D |
| Dosyalarda değiştir | Ctrl+Shift+H | Konum yakala | Ctrl+Shift+L |
| Dosyaya git | Ctrl+Shift+N | Hedef kayması çiz | Ctrl+Shift+O |
| Element Spy | Ctrl+Shift+E | Ekran metni oku (OCR) | Ctrl+Shift+R |
| Window Spy | Ctrl+Shift+W | Terminal | Alt+F12 |
| İngilizce kılavuz | F1 | Türkçe kılavuz | F2 |

## 3. Yakalama Araçları

Ortak akış: **sürükleyin → isterseniz yeniden çizin → (resimde) sağ tıkla
tıklama noktası işaretleyin → Boşluk/Enter ile onaylayın, Esc ile vazgeçin.**
Yalnızca **değişken adını** yazarsınız; resim `değişken.png` olarak betiğin
yanına kaydedilir:

```python
giris_dugmesi = Pattern("giris_dugmesi.png").similar(0.95)
click(giris_dugmesi)
```

| Araç | Ürettiği kod |
|---|---|
| Capture Image (Instant / Delayed) | `ad = Pattern("ad.png").similar(0.95)` |
| Capture Region | `ad = Region(x, y, w, h)` |
| Capture Location | `ad = Location(x, y)` |
| Draw Target Offset | `ad = Offset(dx, dy)` |

**Asset Tester:** Explorer'da bir resme çift tıklayın. Benzerlik kaydırıcısı,
**Search** (arama süresi, varsayılan 8 sn) ve **Highlight** (vurgulama süresi,
varsayılan 2 sn) kutuları vardır; *Find on Screen* eşleşmeyi ekranda kırmızı
çerçeveyle gösterir, *Insert Pattern* kodu ekler.

## 4. Element Spy ve Window Spy

**Element Spy:** *Start watching* → herhangi bir uygulamada bir kontrolün
üzerine gelin → **Boşluk**. Kod, pencereye kilitli olarak eklenir (başka
uygulamada asla aranmaz):

```python
giris = findElement(name="Giriş", role="Button", window="Uygulamam")
giris.click()
```

- **Action** listesinden eylem seçerseniz (`click`, `type`, `setText`,
  `getText`, `check`, `select`...) o satır da birlikte eklenir.
- **Raw tree deep scan:** Electron / web tabanlı uygulamalarda iç içe
  katmanları delerek imlecin altındaki en küçük öğeyi bulur.
- **Scrape whole active window:** aktif penceredeki tüm isimli öğeleri tek
  seferde değişken olarak çıkarır.

Bulunan öğe doğrudan kullanılabilir:
`.click() .doubleClick() .rightClick() .hover() .type("...") .clear()
.setText("...") .getText() .check() .uncheck() .isChecked() .select("Öğe")
.selectItem("Satır") .child(...) .expand() .highlight()`

**Window Spy:** açık tüm pencereleri başlık, işlem (process) adı, PID, pencere
kimliği, konum ve boyutla listeler; çift tıklayınca `app = App("Başlık")`
eklenir.

## 5. Uygulama ve Pencere Yönetimi

```python
app = openApp("notepad.exe")       # başlatır, PID'i izler, pencereyi bekler
app.focus()                        # başlık Türkçe olsa bile işlem adıyla bulur
app.window().moveTo(0, 0).resize(800, 600)
app.window().maximize()            # minimize() restore() setBounds() focus()
print(app.isRunning())
app.close()

switchApp("notepad")               # başlık VEYA işlem adıyla odakla
switchApp("Rapor", contains=False) # tam başlık eşleşmesi
windowRegion("Chrome").find("kaydet.png")  # pencereye yapışık bölge
```

> Türkçe Windows'ta Not Defteri "Adsız — Not Defteri" başlığıyla açılır;
> `openApp` süreci PID ve işlem adıyla izlediği için yine bulunur. Bu davranış
> gerçek Not Defteri üzerinde uçtan uca doğrulanmıştır.

## 6. Komut Başvurusu (SikuliX uyumlu)

### Fare ve Klavye
```python
click("dugme.png")                  # bul ve tıkla
doubleClick(ikon) ; rightClick(ikon)
hover("menu.png")
dragDrop("dosya.png", "klasor.png")
wheel(WHEEL_DOWN, 3)
type("merhaba" + Key.ENTER)         # Key.TAB, Key.F5, Key.ESC ...
type("s", KeyModifier.CTRL)         # Ctrl+S
paste("uzun metin")                 # pano üzerinden hızlı yazma
```

### Görüntü Arama
```python
wait("kayit.png", 10)               # 10 sn bekle, yoksa hata
wait(2)                             # sayı verilirse yalnızca bekler (sleep)
m = exists("popup.png", 3)          # bulamazsa None döner, hata VERMEZ
waitVanish("yukleniyor.png", 30)    # kaybolana kadar bekle
m = find("logo.png")                # Match döner: m.getTarget(), m.getScore()
for satir in findAll("satir.png"): click(satir)
click("liste_sonu.png", autoScroll=True)   # bulamazsa kaydırıp yeniden arar
find("logo.png").highlight(2)       # ekranda 2 sn kırmızı çerçeve
```

### Pattern, Region, Location, Offset
```python
p = Pattern("dugme.png").similar(0.9).targetOffset(10, -4)
r = Region(0, 0, 800, 600)          # aramayı bölgeyle sınırla
r.find("ikon.png") ; r.text()       # bölge içinde ara / OCR ile oku
m.nearby(50) ; m.above() ; m.below(120) ; m.left() ; m.right(200)
r1.union(r2) ; r1.intersection(r2)
Location(500, 300) ; Offset(10, -4)
```

### Çoklu Çapa ve Görsel Mod (kurumsal dayanıklılık)
```python
hedef = Target(name="Kaydet", window="Editör",
               image="kaydet.png", text="KAYDET")
hedef.click()     # önce öğe, olmazsa resim, olmazsa OCR; çalışanı hatırlar

for dugme in findUI("button", text="OK"):   # erişilebilirlik YOKKEN (VDI)
    dugme.highlight(1)
```

### Sistem: Env ve Settings
```python
Env.setClipboard("merhaba") ; metin = Env.getClipboard()
konum = Env.getMouseLocation() ; ekran = Env.getScreenSize()
Env.getOS() ; Env.isWindows()

Settings.MinSimilarity = 0.8        # genel eşleşme hassasiyeti
Settings.ClickDelay = 0.3           # her tıklamadan önce bekleme
Settings.DelayBeforeDrag = 0.5      # dragDrop zamanlamaları
Settings.DefaultHighlightTime = 3
Settings.OcrLanguage = "eng_best"   # Region.text() için OCR modeli
```

### Akış ve Raporlama
```python
sleep(2)                            # duraklatmaya duyarlı bekleme
popup("bitti!")
passed("giriş tamam")               # Output'ta yeşil satır
failed("düğme yok")                 # kırmızı satır + otomatik ekran görüntüsü
emit("asama", "veri girildi")       # yapılandırılmış durum olayı
```

## 7. Hata Yönetimi

Betik bir hedefi bulamazsa program çökmüş gibi görünmez: Output panelinde
**ne olduğunu ve ne yapmanız gerektiğini** anlatan kırmızı bir mesaj, hatanın
geçtiği **satır numarası** ve o anın ekran görüntüsü gösterilir. Örnek:

> `FindFailed: image not found: dugme.png (script line 4). The image file is
> missing. Save the capture next to your script, or check the file name.`

Hatayı kendiniz yönetmek isterseniz klasik Python yeterlidir:

```python
try:
    click("kaydet.png")
except FindFailed:
    failed("Kaydet düğmesi ekranda yok")
```

## 8. OCR (Metin Okuma)

Tesseract gömülüdür, kurulum gerekmez. Paketli modeller: `eng`,
`eng_best` (en yüksek doğruluk), `tur` (Türkçe), `dejavu_sans` (özel).
Küçük yazılar okunmadan önce otomatik büyütülür ve temizlenir.

```python
Settings.OcrLanguage = "tur"
print(Region(0, 0, 600, 120).text())
```

## 9. .sikuli Klasörleri ve Duraklatma

- SikuliX yapısı desteklenir: `akis.sikuli/akis.py` + resimleri. Explorer'daki
  kamera düğmesi yeni `.sikuli` klasörünü içindeki betikle birlikte oluşturur;
  `File > Open SikuliX Folder` veya sürükle-bırak ile açılır.
- **Duraklat (Ctrl+4)** çalışan betiği bir sonraki eylemde (tıklama, yazma,
  arama, sleep) güvenle bekletir; tekrar basınca devam eder.
  **Durdur (Ctrl+5)** anında sonlandırır.

## 10. Mimari ve EXE Derleme

```
rpa_framework/
  core/os_facade/    fare-klavye-ekran (win32+pywinauto / xdotool + mss)
  core/vision/       SIFT eşleştirme, kenar haritası, UI bulucu, OCR motoru
  core/inspector/    UIA / AT-SPI erişilebilirlik ağacı ve casus servisi
  compat/sikuli.py   bu kılavuzdaki betik API'si
  ide/               editör, paneller, çalıştırma motoru (ayrı işlem)
  packaging/         Nuitka tek-dosya derleyicisi ve paket yolları
```

Derleme: `Tools > Build Standalone EXE` veya
`.venv-build\Scripts\python.exe -m rpa_framework.packaging.build`
Çıktı `dist/RPAStudio.exe` — Python, OpenCV ve Tesseract kurulu olmayan temiz
bir makinede çalışır.

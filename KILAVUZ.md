<div align="center">

# 📘 RPA Studio — Başvuru Kılavuzu

### Geliştiriciler ve Test Mühendisleri için Kapsamlı Teknik Referans

*Çift Katmanlı Nesne Yakalama Mimarisi · Kurulumsuz IDE · SikuliX Uyumlu*

</div>

---

## İçindekiler

1. [Giriş ve Mimari Genel Bakış](#1-giriş-ve-mimari-genel-bakış)
2. [Kurulumsuz (Taşınabilir) Çalışma Yapısı](#2-kurulumsuz-taşınabilir-çalışma-yapısı)
3. [Element Yakalama (Spying) ve Kodlama Kuralları](#3-element-yakalama-spying-ve-kodlama-kuralları)
4. [API Referansı](#4-api-referansı)
5. [Hata Yönetimi ve Raporlama](#5-hata-yönetimi-ve-raporlama)

> İngilizce adım adım eğitim için **[TUTORIAL.md](TUTORIAL.md)** dosyasına, projeye hızlı bakış için **[README.md](README.md)** dosyasına bakın.

---

## 1. Giriş ve Mimari Genel Bakış

**RPA Studio**, masaüstü otomasyonunu hızlandırmak için geliştirilmiş, **kurumsal sınıfta, tek dosya halinde çalışan** bağımsız bir entegre geliştirme ortamı (**IDE**) ve yürütme motorudur. Tüm çalışma zamanı bileşenlerini, bağımlılık ağacını ve arayüzü tek bir yüksek performanslı çalıştırılabilir dosyada toplar; **SikuliX API sözdizimi** ile tam uyumludur.

Değişen ekran koşullarında kararlı çalışabilmesi, tescilli **Çift Katmanlı Nesne Yakalama Mimarisi** sayesindedir. Bu yapı, hedef bulmayı bir **mantıksal katman** ile bir **bilgisayarlı görü yedek katmanı** olarak ikiye ayırır.

> **Temel felsefe:** Her zaman bir *Plan A* ve bir *Plan B* vardır. Birincil katman öğeye erişemezse, yedek katman **saydam şekilde** ve otomatik olarak devreye girer.

### 1.1 Birincil Katman — Erişilebilirlik Ağacı Sorgulaması

Arayüz öğelerinin keşfinde temel yöntem, doğrudan işletim sisteminin **yerel erişilebilirlik altyapısını** sorgulamaktır. RPA Studio, piksel dizilimlerinden bağımsız çalışır:

- **Windows:** Gelişmiş **UI Automation (UIA)** arayüzleriyle mantıksal arayüz ağacını okur.
- **Linux:** **AT-SPI** (Assistive Technology Service Provider Interface) altyapısına bağlanır.

Sistem, düğme, girdi kutusu ve metin alanı gibi bileşenleri **benzersiz programatik özellikleri** üzerinden yakalar: `AutomationID`, **Control Type**, **Name** öznitelikleri. Bu katman; ekran çözünürlüğünden, DPI ölçeklendirmesinden, monitör oranından veya aktif temadan (Açık/Koyu mod) **hiçbir şekilde etkilenmez**.

### 1.2 Yedek Katman — Gelişmiş Görüntü İşleme + Tesseract OCR

Erişilebilirlik ağacını sunmayan eski nesil yazılımlar (Delphi kalın istemcileri, ham Java Applet'leri, gömülü canvas panelleri, Citrix/RDP gibi sanallaştırılmış ortamlar) söz konusu olduğunda birincil katman öğeye erişemez. Bu durumda **kırılgan piksel eşleştirmesi yerine** çok aşamalı bir görüntü işleme hattı çalışır:

| # | Aşama | Uygulanan Teknoloji | Güvenilirliğe Katkısı |
|---|---|---|---|
| 1 | **Görüntü Normalizasyonu** | Gri ton + **CLAHE** | Ekranı gri tona çevirir, Kontrast Sınırlı Uyarlamalı Histogram Eşitleme ile ani ışık/gölge değişimlerini dengeler. |
| 2 | **Yapısal Haritalama** | Kenar Algılama (Edge Maps) | Bileşenlerin net dış hat çizgilerini çıkarır; renk geçişlerini filtreler, tema değişiminden etkilenmez. |
| 3 | **Öznitelik Çıkarımı** | **SIFT** anahtar nokta eşleştirmesi | Geometrik tabanlı matematiksel anahtar noktalar çıkarır, hedefi şeklinden tanır. |
| 4 | **Boyut Ölçekleme** | `0.5× – 3×` piramit taraması | Farklı monitörlerdeki DPI ve çözünürlük farklarını tolere eder. |
| 5 | **Metin Okuma** | **Tesseract OCR** | Doğrudan pikseller üzerinden metin okur; metin tabanlı tıklama (text-anchor) ve içerik doğrulaması yapar. |

> ⚠️ **Mimari not:** Katman 2, Katman 1'in *yerine* değil, *yedeği* olarak tasarlanmıştır. En yüksek dayanıklılık için `Target(...)` çoklu çapa nesnesini kullanın (bkz. [§4.5](#45-çoklu-çapa-ve-görsel-mod)): önce öğe, olmazsa resim, olmazsa OCR denenir ve **çalışan yöntem hatırlanır**.

---

## 2. Kurulumsuz (Taşınabilir) Çalışma Yapısı

RPA Studio çalışma zamanı motoru, tamamen **geçici bellek alanları** veya izole edilmiş, kendi kendine yeten bir dizin içinde çalışacak şekilde optimize edilmiştir. Tekil çalıştırılabilir dosya (`RPAStudio.exe`) başlatıldığında, iç modüllerini dinamik olarak eşler; sistem dizinlerine (`System32`, `/usr/lib`) **paylaşılan kütüphane (DLL/SO) bırakmaz**.

Kısıtlı ve kurumsal ortamlar için sağladığı somut avantajlar:

- **Bağımlılık çakışması yok ("DLL Hell"):** Farklı sürüm kütüphaneler birbiriyle çatışmaz; her düğüm kendi ikili dosyasıyla izoledir.
- **İdari yetki gerekmez:** MSI yükleyici, `.NET`/Java önkoşulu veya kayıt defteri (registry) düzenlemesi yoktur. Kilitli kurumsal bilgisayarlarda doğrudan çalışır.
- **Dağıtım ve kaldırma tek dosya kadar basit:** Bir otomasyon istasyonunu güncellemek ya da devre dışı bırakmak yalnızca **tek dosyayı kopyalamak veya silmek** demektir.
- **Hava boşluklu (air-gapped) ortam uyumu:** İnternet erişimi olmayan laboratuvar ve üretim sistemlerinde harici indirme olmadan çalışır. Tesseract OCR motoru dahi gömülüdür.

> 💡 **Kurumsal ipucu:** İkili dosyayı ağ paylaşımına koyup her iş istasyonunun aynı sürümü çalıştırmasını sağlayabilirsiniz. Sürüm yükseltmesi = tek dosyayı değiştirmek.

---

## 3. Element Yakalama (Spying) ve Kodlama Kuralları

### 3.1 Element Spy ile Öğe Hedefleme

**Element Spy** (`Ctrl+Shift+E`), birincil katmanı görsel olarak kullanmanın yoludur:

1. **Start watching**'e basın.
2. Herhangi bir uygulamada bir kontrolün üzerine gelin.
3. **Boşluk** (Space) tuşuna basın.

Kod, **pencereye kilitli** olarak eklenir — öğe başka bir uygulamada asla aranmaz:

```python
giris = findElement(name="Giris", role="Button", window="Uygulamam")
giris.click()
```

- **Action** listesinden bir eylem seçerseniz (`click`, `type`, `setText`, `getText`, `check`, `select`...) ilgili satır da otomatik eklenir.
- **Raw tree deep scan:** Electron/web tabanlı uygulamalarda iç içe katmanları delerek imlecin altındaki **en küçük** öğeyi bulur.
- **Scrape whole active window:** Aktif penceredeki tüm isimli öğeleri tek seferde değişken olarak çıkarır.

Bulunan öğe zincirlenebilir metotlarla doğrudan kullanılır:

```
.click()  .doubleClick()  .rightClick()  .hover()  .type("...")  .clear()
.setText("...")  .getText()  .check()  .uncheck()  .isChecked()
.select("Oge")  .child(...)  .expand()  .highlight()
```

**Window Spy** (`Ctrl+Shift+W`) açık tüm pencereleri başlık, işlem adı, PID, pencere kimliği, konum ve boyutla listeler; çift tıklayınca `app = App("Baslik")` ekler.

### 3.2 Görüntü Yakalama Araçları (Yedek Katman)

Ortak akış: **sürükleyin → gerekirse yeniden çizin → (resimde) sağ tıkla tıklama noktası işaretleyin → Boşluk/Enter ile onaylayın, Esc ile vazgeçin.** Yalnızca **değişken adını** yazarsınız; resim `degisken.png` olarak betiğin yanına kaydedilir.

| Araç | Kısayol | Ürettiği Kod |
|---|---|---|
| Capture Image (Instant) | `Ctrl+1` | `ad = Pattern("ad.png").similar(0.95)` |
| Capture Image (Delayed) | `Ctrl+2` | `ad = Pattern("ad.png").similar(0.95)` |
| Capture Region | `Ctrl+Shift+D` | `ad = Region(x, y, w, h)` |
| Capture Location | `Ctrl+Shift+L` | `ad = Location(x, y)` |
| Draw Target Offset | `Ctrl+Shift+O` | `ad = Offset(dx, dy)` |
| Read Screen Text (OCR) | `Ctrl+Shift+R` | `metin = Region(...).text()` |

### 3.3 🔴 Kritik Kodlama Kuralı — Karakter Dönüşümü

> **KRİTİK OPERASYONEL ZORUNLULUK:** Kısıtlı kurumsal ortamlarda, eski ana sistemlerde ve farklı işletim sistemi dillerinde mutlak uyumluluk için, RPA Studio otomasyon kodlarında **yalnızca standart İngilizce karakter seti** kullanılmalıdır.

Otomasyon makroları geliştirilirken **yerel karakterler standart İngilizce klavye eşlenikleriyle** değiştirilmelidir. Bu yaklaşım motoru; klavye düzeninden, kod sayfası uyumsuzluklarından (**Windows-1254** vs. **UTF-8**) ve yerel metin sıralama anomalilerinden **tamamen izole eder** — bunlar kilitli altyapılarda sık sık çalışma zamanı hatasına yol açar.

| Yerel Karakter | Zorunlu İngilizce Karşılığı | Örnek Dönüşüm |
|:---:|:---:|---|
| `ı / İ` | `i / I` | `click("ayarlar_butonu")` → `click("ayarlar_butonu")` |
| `ş / Ş` | `s / S` | `type("giriş_alani", ...)` → `type("giris_alani", ...)` |
| `ğ / Ğ` | `g / G` | `find("doğrula_yazisi")` → `find("dogrula_yazisi")` |
| `ç / Ç` | `c / C` | `click("çikiş")` → `click("cikis")` |
| `ö / Ö` | `o / O` | `type("söz")` → `type("soz")` |
| `ü / Ü` | `u / U` | `find("düğme")` → `find("dugme")` |

> ✅ **En iyi uygulama:** Kural yalnızca **kod tanımlayıcılarını** (dosya adları, değişkenler, `Pattern`/asset adları) kapsar. `type(...)` ile ekrana **yazılan** kullanıcı verisi Türkçe olabilir; ancak tanımlayıcılar daima İngilizce olmalıdır. Bu davranış Türkçe Windows'ta gerçek uygulamalar üzerinde uçtan uca doğrulanmıştır.

---

## 4. API Referansı

Tüm komutlar **SikuliX uyumludur**. Betikler IDE'den **ayrı bir işlemde** çalışır: betik çökse veya sonsuz döngüye girse bile arayüz kilitlenmez.

### 4.1 Fare ve Klavye

```python
click("dugme.png")                  # bul ve tikla (once Katman 1, sonra Katman 2)
doubleClick(ikon) ; rightClick(ikon)
hover("menu.png")
dragDrop("dosya.png", "klasor.png")
wheel(WHEEL_DOWN, 3)
type("merhaba" + Key.ENTER)         # Key.TAB, Key.F5, Key.ESC ...
type("s", KeyModifier.CTRL)         # Ctrl+S
paste("uzun metin")                 # pano uzerinden hizli yazma
```

### 4.2 Görüntü Arama

```python
wait("kayit.png", 10)               # 10 sn bekle, yoksa FindFailed
wait(2)                             # sayi verilirse yalnizca bekler (sleep)
m = exists("popup.png", 3)          # bulamazsa None doner, HATA VERMEZ
waitVanish("yukleniyor.png", 30)    # kaybolana kadar bekle
m = find("logo.png")                # Match doner: m.getTarget(), m.getScore()
for satir in findAll("satir.png"):
    click(satir)
click("liste_sonu.png", autoScroll=True)   # bulamazsa kaydirip yeniden arar
find("logo.png").highlight(2)       # ekranda 2 sn kirmizi cerceve
```

### 4.3 Metin (OCR) Arama

```python
ocr_target = findText("GIRIS YAP")  # ekranda metni bul, tiklanabilir hedef doner
click(ocr_target)
Settings.OcrLanguage = "tur"        # Region.text() icin OCR modeli
print(Region(0, 0, 600, 120).text())
```

> Gömülü Tesseract modelleri: `eng`, `eng_best` (en yüksek doğruluk), `tur` (Türkçe), `dejavu_sans`. Küçük yazılar okunmadan önce otomatik büyütülür ve temizlenir.

### 4.4 Pattern, Region, Location, Offset

```python
p = Pattern("dugme.png").similar(0.9).targetOffset(10, -4)
r = Region(0, 0, 800, 600)          # aramayi bolgeyle sinirla
r.find("ikon.png") ; r.text()       # bolgede ara / OCR ile oku
m.nearby(50) ; m.above() ; m.below(120) ; m.left() ; m.right(200)
r1.union(r2) ; r1.intersection(r2)
Location(500, 300) ; Offset(10, -4)
```

### 4.5 Çoklu Çapa ve Görsel Mod

Kurumsal dayanıklılığın zirvesi. `Target`, üç katmanı tek nesnede birleştirir:

```python
hedef = Target(name="Kaydet", window="Editor",
               image="kaydet.png", text="KAYDET")
hedef.click()     # once oge (Katman 1), olmazsa resim, olmazsa OCR (Katman 2);
                  # calisan yontemi HATIRLAR ve sonraki cagrida onu kullanir

for dugme in findUI("button", text="OK"):   # erisilebilirlik YOKKEN (VDI/Citrix)
    dugme.highlight(1)
```

### 4.6 Uygulama ve Pencere Yönetimi

```python
app = openApp("notepad.exe")       # baslatir, PID izler, pencereyi bekler
app.focus()                        # baslik Turkce olsa bile ISLEM adiyla bulur
app.window().moveTo(0, 0).resize(800, 600)
app.window().maximize()            # minimize() restore() setBounds() focus()
print(app.isRunning())
app.close()

switchApp("notepad")               # baslik VEYA islem adiyla odakla
switchApp("Rapor", contains=False) # tam baslik eslesmesi
windowRegion("Chrome").find("kaydet.png")  # pencereye yapisik bolge
```

> Türkçe Windows'ta Not Defteri "Adsız — Not Defteri" başlığıyla açılır; `openApp` süreci **PID ve işlem adıyla** izlediği için yine bulunur.

### 4.7 Yedek Katman Yapılandırma Parametreleri

```python
Settings.MinSimilarity = 0.8        # genel eslesme hassasiyeti (0.0 - 1.0)
Settings.ClickDelay = 0.3           # her tiklamadan once bekleme
Settings.DelayBeforeDrag = 0.5      # dragDrop zamanlamalari
Settings.DefaultHighlightTime = 3   # highlight() varsayilan suresi
Settings.OcrLanguage = "eng_best"   # OCR modeli
Settings.BundlePath = "./assets/"   # Pattern resimlerinin kok yolu
```

| Parametre | Varsayılan | Ne Zaman Ayarlanır |
|---|---|---|
| `MinSimilarity` | `0.75` | Yanlış eşleşme → yükseltin; hedef bulunamıyor → düşürün (`0.6–0.7`). |
| `OcrLanguage` | `eng` | Türkçe metin okurken `tur`; en yüksek doğruluk için `eng_best`. |
| `ClickDelay` | `0.0` | Yavaş/animasyonlu arayüzlerde `0.2–0.5`. |

### 4.8 Sistem: Env ve Akış

```python
Env.setClipboard("merhaba") ; metin = Env.getClipboard()
konum = Env.getMouseLocation() ; ekran = Env.getScreenSize()
Env.getOS() ; Env.isWindows()

sleep(2)                            # duraklatmaya (Ctrl+4) duyarli bekleme
popup("bitti!")
```

---

## 5. Hata Yönetimi ve Raporlama

Betik bir hedefi bulamazsa program çökmüş gibi görünmez. **Output** panelinde ne olduğunu ve ne yapmanız gerektiğini anlatan kırmızı bir mesaj, hatanın geçtiği **satır numarası** ve o anın **otomatik ekran görüntüsü** gösterilir:

> `FindFailed: image not found: dugme.png (script line 4). The image file is missing. Save the capture next to your script, or check the file name.`

Hatayı kendiniz yönetmek için klasik Python yeterlidir:

```python
try:
    click("kaydet.png")
except FindFailed:
    failed("Kaydet dugmesi ekranda yok")
```

Yapılandırılmış raporlama komutları:

```python
passed("giris tamam")               # Output'ta yesil satir
failed("dugme yok")                 # kirmizi satir + otomatik ekran goruntusu
emit("asama", "veri girildi")       # yapilandirilmis durum olayi
```

> 🧭 **Duraklat/Durdur:** **`Ctrl+4`** çalışan betiği bir sonraki eylemde (tıklama, yazma, arama, `sleep`) güvenle bekletir; tekrar basınca devam eder. **`Ctrl+5`** anında sonlandırır.

---

<div align="center">

**RPA Studio Başvuru Kılavuzu** · Çift Katmanlı Mimari · Kurulumsuz IDE

[README.md](README.md) · [TUTORIAL.md](TUTORIAL.md)

</div>

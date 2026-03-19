# macOS Manual Test Checklist

Bu dokuman, `sfc` icin macOS odakli manuel test adimlarini standartlastirmak icin hazirlanmistir.
Komutlari sirasiyla calistirarak config yolu, updater akisi, buyuk clipboard kopyasi ve curses resize davranisini dogrulayabilirsiniz.

## 1) Config Yolunu Dogrulama (`~/Library/Application Support/sfc`)

### 1.1 Temiz baslangic (opsiyonel)

```bash
rm -f "$HOME/Library/Application Support/sfc/cfg.setting.json"
```

### 1.2 Uygulamayi bir kez calistir (auto-create tetikleme)

```bash
cd /Users/polatsakarya35/Desktop/sfc
python3 -m sfc -V
```

### 1.3 Dosya olusumunu kontrol et

```bash
ls -la "$HOME/Library/Application Support/sfc/cfg.setting.json"
```

### 1.4 JSON icerigini hizli dogrula

```bash
python3 - <<'PY'
from pathlib import Path
import json

p = Path.home() / "Library" / "Application Support" / "sfc" / "cfg.setting.json"
print("exists:", p.exists())
if p.exists():
    data = json.loads(p.read_text("utf-8"))
    print("keys:", sorted(data.keys()))
PY
```

Beklenti:

- Dosya belirtilen macOS yolunda olusmus olmali.
- JSON anahtarlari uygulama config alanlarini icermeli.

---

## 2) Updater Testi (`version.py` repo duzeltmesi sonrasi)

### 2.1 Gercek ag ile "guncel mi / yeni surum var mi" kontrolu

```bash
cd /Users/polatsakarya35/Desktop/sfc
python3 - <<'PY'
from sfc.updater import check_update

r = check_update()
print("available:", r.available)
print("remote_version:", r.remote_version)
print("current_version:", r.current_version)
print("error:", r.error)
PY
```

Beklenti:

- `error` bos ise URL + parse akisi calisiyor demektir.
- `available` degeri uzaktaki surume gore `True` veya `False` olabilir.

### 2.2 "Yeni surum varmis gibi" deterministik simulasyon

```bash
python3 - <<'PY'
import sfc.updater as u

u._fetch = lambda url: b'VERSION: str = "999.0.0"\n'
r = u.check_update()
print("available_should_be_true:", r.available)
print(r)
PY
```

Beklenti:

- `available_should_be_true: True`

### 2.3 "Zaten guncelmis gibi" simulasyon

```bash
python3 - <<'PY'
import sfc.updater as u
from sfc.version import VERSION

u._fetch = lambda url: f'VERSION: str = "{VERSION}"\n'.encode()
r = u.check_update()
print("available_should_be_false:", r.available)
print(r)
PY
```

Beklenti:

- `available_should_be_false: False`

---

## 3) 150K+ Karakterde `pbcopy` Stabilite Testi

### 3.1 Buyuk sentetik proje olustur

```bash
mkdir -p /tmp/sfc-bigproj
python3 - <<'PY'
from pathlib import Path

root = Path("/tmp/sfc-bigproj")
root.mkdir(parents=True, exist_ok=True)
payload = ("0123456789abcdef" * 400) + "\n"  # ~6.4KB/satir
for i in range(40):  # ~256KB+ toplam icerik
    (root / f"file_{i:03}.py").write_text(payload, encoding="utf-8")
print("created files:", len(list(root.glob("*.py"))))
PY
```

### 3.2 `sfc` ile tek parca cikti uret

```bash
cd /Users/polatsakarya35/Desktop/sfc
python3 -m sfc all -p /tmp/sfc-bigproj -o /tmp/sfc-big-context.txt -c 500000
```

### 3.3 Karakter sayisini dogrula (`>= 150000`)

```bash
python3 - <<'PY'
from pathlib import Path

p = Path("/tmp/sfc-big-context.txt")
t = p.read_text("utf-8")
print("chars:", len(t))
print(">=150000:", len(t) >= 150000)
PY
```

### 3.4 Clipboard kopyasi + geri okuma kontrolu

```bash
python3 - <<'PY'
from pathlib import Path
from sfc.clipboard import copy_to_clipboard

t = Path("/tmp/sfc-big-context.txt").read_text("utf-8")
r = copy_to_clipboard(t)
print(r)
PY
```

```bash
python3 - <<'PY'
import subprocess

out = subprocess.check_output(["pbpaste"])
print("pbpaste_bytes:", len(out))
print("non_empty:", len(out) > 0)
PY
```

Beklenti:

- `ClipboardResult(ok=True, backend='pbcopy', ...)`
- `pbpaste_bytes` sifirdan buyuk olmali.
- Kopyalama sirasinda donma/timeout yasanmamali.

---

## 4) curses TUI Resize ve Redraw Testi (iTerm2 / Terminal.app)

### 4.1 TUI'yi baslat

```bash
cd /Users/polatsakarya35/Desktop/sfc
python3 -m sfc
```

### 4.2 Yogun bir ekrana gir

- `Browse & Select` veya `View tree` gibi cok satirli ekranlar.

### 4.3 Manuel resize stresi uygula

- Pencereyi hizla daralt (yaklasik 40-50 kolon seviyesine kadar).
- Sonra tekrar genislet.
- Bu donguyu 5-10 kez tekrar et.

### 4.4 Beklenen davranis

- Ekran kalici olarak bozulmamali.
- Menu/alt bilgi yeniden cizimde toparlanmali.
- Tus girdileri (`Up/Down`, `Enter`, `Esc`) calismaya devam etmeli.
- Unicode/emoji satirlari exception olusturmadan cizilmeli.

---

## Notlar

- Testleri mumkunse hem `Terminal.app` hem `iTerm2` icinde tekrarlayin.
- Updater testi icin ag baglantisi sorunluysa 2.2 ve 2.3 simulasyonlariyla mantik dogrulanabilir.

# turkcesivar.github.io

[Türkçesi Var](https://github.com/turkcesivar/turkcesi-var)'ın tanıtım sitesi: https://turkcesivar.github.io

## Yeni oyun eklemek

1. Oyunun 4–5 ekran görüntüsünü 1280 piksel genişliğe küçültüp `gorseller/` klasörüne koy.
2. `veri/oyunlar.json` dosyasına bir kayıt ekle (var olan kayıtları örnek al). `durum`: `hazir`, `cevriliyor` ya da `oylamada`.
3. `main` dalına gönder. GitHub siteyi kendiliğinden üretip yayınlar (`.github/workflows/yayinla.yml`).

Göndermeden önce bakmak için:

```
python uret.py
python -m http.server 8765 --directory _site
```

`uret.py` eksik alan ya da bulunamayan görsel görürse hata verip durur; bozuk site yayınlanmaz.

## Neler üretiliyor?

- `/`: ana sayfa (son eklenen 6 hazır oyun + sabit bölümler: `sablonlar/ana.html`)
- `/oyunlar/`: bütün oyunlar (arama, durum süzgeci, sıralama)
- `/oyun/<kimlik>/`: her oyunun kendi sayfası (Google'da "oyun adı Türkçe yama" aramaları için)
- `404.html`, `sitemap.xml`, `robots.txt`

Ortak dosyalar: `stil.css`, `site.js` (tıklanır kartlar, liste süzgeci, görsel büyütücü). Kütüphane ya da derleme aracı yok; yalnızca Python.

Logo ve görseller Türkçesi Var marka paketinden alınmıştır ("Türkçesi Var" adı ve logosu lisansa dahil değildir). Oyun ekran görüntüleri yapımcılarının oyunlarından alınmıştır; oyunlar ve görselleri yapımcılarına aittir.

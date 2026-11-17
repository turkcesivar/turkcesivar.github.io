"""Türkçesi Var sitesini veri/oyunlar.json'dan üretir.

Kullanım:  python uret.py          -> _site/ klasörüne bütün siteyi yazar
Önizleme:  python -m http.server 8765 --directory _site

Üretilen sayfalar:
  /                      ana sayfa (son eklenen oyunlar vitrini + sabit bölümler)
  /oyunlar/              bütün oyunlar (arama, durum süzgeci, sıralama)
  /oyun/<kimlik>/        her oyunun kendi sayfası
  /404.html, /sitemap.xml, /robots.txt
GitHub'da main'e her gönderimde .github/workflows/yayinla.yml bunu çalıştırıp yayınlar.
"""

import hashlib
import html
import json
import shutil
from pathlib import Path

KOK = Path(__file__).resolve().parent
CIKTI = KOK / "_site"
SITE = "https://turkcesivar.github.io"
INDIR = "https://github.com/turkcesivar/turkcesi-var/releases/latest/download/TurkcesiVar-Kurulum.exe"
DISCORD = "https://discord.gg/nnNUCMUBJx"
GITHUB = "https://github.com/turkcesivar/turkcesi-var"
KREOSUS = "https://kreosus.com/turkcesivar"
ISTEK_FORMU = GITHUB + "/issues/new?template=oyun-istegi.yml"
VITRIN_SAYISI = 6

DURUMLAR = {
    "hazir": ("✓ Hazır", "Hazır"),
    "cevriliyor": ("⏳ Çevriliyor", "Çevriliyor"),
    "oylamada": ("🗳 Oylamada", "Oylamada"),
}
AYLAR = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz",
         "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]

e = html.escape  # yalnızca düz metin için; veri dosyasındaki HTML alanları olduğu gibi basılır


def sayi(n):
    return f"{n:,}".replace(",", ".")


def tarih(t):
    y, a, g = t.split("-")
    return f"{int(g)} {AYLAR[int(a) - 1]} {y}"


def surum(dosya):
    """Önbellek kırıcı: dosya değişince adres değişir."""
    return hashlib.md5((KOK / dosya).read_bytes()).hexdigest()[:8]


def arama_metni(o):
    return " ".join([o["ad"], *o.get("tur", []), *o.get("platform", [])]).lower()


# --- Ortak parçalar ----------------------------------------------------------

def sayfa(baslik, aciklama, yol, govde, gorsel="/gorseller/paylasim.png", bas_ek=""):
    css, js = surum("stil.css"), surum("site.js")
    return f"""<!doctype html>
<html lang="tr">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{e(baslik)}</title>
  <meta name="description" content="{e(aciklama)}">
  <meta name="theme-color" content="#0C0D10">
  <link rel="icon" href="/favicon.ico">
  <link rel="canonical" href="{SITE}{yol}">
  <meta property="og:type" content="website">
  <meta property="og:locale" content="tr_TR">
  <meta property="og:site_name" content="Türkçesi Var">
  <meta property="og:title" content="{e(baslik)}">
  <meta property="og:description" content="{e(aciklama)}">
  <meta property="og:url" content="{SITE}{yol}">
  <meta property="og:image" content="{SITE}{gorsel}">
  <meta name="twitter:card" content="summary_large_image">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="/stil.css?v={css}">{bas_ek}
</head>
<body>
  <a class="atla" href="#icerik">İçeriğe geç</a>

  <header class="ust">
    <div class="kap ust-ic">
      <a href="/" class="logo" aria-label="Türkçesi Var ana sayfa"><img src="/gorseller/logo.svg" alt="Türkçesi Var" width="190" height="50"></a>
      <nav aria-label="Ana menü">
        <a href="/oyunlar/">Oyunlar</a>
        <a href="/#nasil">Nasıl çalışır</a>
        <a href="/#guvenli">Güvenli mi?</a>
        <a href="/#sss">SSS</a>
        <a href="{DISCORD}" rel="noopener">Discord</a>
      </nav>
      <a class="dugme dugme-ana kucuk" href="{INDIR}">İndir</a>
    </div>
  </header>

  <main id="icerik">
{govde}
  </main>

  <footer class="alt-bilgi">
    <div class="kap alt-ic">
      <img src="/gorseller/logo.svg" alt="Türkçesi Var" width="150" height="40">
      <p>Kaynak kodu GNU GPL v3.0 ve ek şartlarıyla, Türkçe çeviriler CC BY-NC-ND 4.0 ile korunur. Oyunlar ve orijinal metinleri yapımcılarına aittir; Türkçesi Var resmi bir yapımcı ürünü değildir. Resmi sürümler yalnızca <a href="{GITHUB}">GitHub sayfasından</a> yayımlanır.</p>
      <nav aria-label="Alt bağlantılar">
        <a href="/oyunlar/">Oyunlar</a>
        <a href="{GITHUB}">GitHub</a>
        <a href="{DISCORD}" rel="noopener">Discord</a>
        <a href="{KREOSUS}" rel="noopener">Kreosus</a>
      </nav>
    </div>
  </footer>

  <dialog class="buyutec" aria-label="Büyütülmüş görsel">
    <figure><img alt=""><figcaption></figcaption></figure>
    <button type="button" class="buyutec-ok onceki" aria-label="Önceki görsel">‹</button>
    <button type="button" class="buyutec-ok sonraki" aria-label="Sonraki görsel">›</button>
    <button type="button" class="buyutec-kapat" aria-label="Kapat">✕</button>
    <p class="buyutec-sayac" aria-live="polite"></p>
  </dialog>
  <script src="/site.js?v={js}"></script>
</body>
</html>
"""


def rozet(o):
    return f'<span class="rozet rozet-{o["durum"]}">{DURUMLAR[o["durum"]][0]}</span>'


def kart(o, baslik_etiketi="h3"):
    ozet = o["ozet"]
    if o.get("satir"):
        satir = f'<strong>{sayi(o["satir"])} satır</strong> — '
    else:  # özet cümle başında kalır: ilk harfi Türkçe kurala göre büyüt
        satir = ""
        ozet = {"i": "İ", "ı": "I"}.get(ozet[0], ozet[0].upper()) + ozet[1:]
    return f"""          <article class="oyun" data-durum="{o['durum']}" data-ad="{e(o['ad'])}" data-eklenme="{o['eklenme']}" data-ara="{e(arama_metni(o))}">
            <img src="/gorseller/{o['kapak']}" alt="{e(o['ad'])} Türkçe" loading="lazy" width="1280" height="720">
            <div class="oyun-ic">
              <{baslik_etiketi}><a class="oyun-ac" href="/oyun/{o['kimlik']}/">{e(o['ad'])}</a></{baslik_etiketi}>
              <p class="platform">{e(' · '.join(o['platform']))}</p>
              <p>{satir}{ozet}</p>
              <div class="oyun-alt">{rozet(o)}<span class="ayrinti">Ayrıntılar ve görüntüler →</span></div>
            </div>
          </article>"""


SIRADAKI = f"""          <article class="oyun siradaki">
            <div class="oyun-ic">
              <h3>Sıradaki oyunu sen seç</h3>
              <p>Türkçesini istediğin oyunu Discord'daki <strong>oyun-istekleri</strong> kanalına yaz ya da var olan isteğe 👍 bırak. En çok istenen oyunlar önce çevrilir.</p>
              <a class="dugme dugme-ikincil" href="{DISCORD}" rel="noopener">Oyun iste</a>
              <p class="kucuk-not">GitHub hesabın varsa: <a href="{ISTEK_FORMU}">oyun isteği formu</a>. Hile koruması olan çevrimiçi oyunlar güvenlik için çevrilmez.</p>
            </div>
          </article>"""


# --- Sayfalar ----------------------------------------------------------------

def ana_sayfa(oyunlar):
    hazir = [o for o in oyunlar if o["durum"] == "hazir"]
    vitrin = sorted(hazir, key=lambda o: o["eklenme"], reverse=True)[:VITRIN_SAYISI]
    kartlar = "\n".join(kart(o) for o in vitrin)
    vitrin_html = f"""    <section class="bolum koyu" id="oyunlar" aria-labelledby="oyunlar-baslik">
      <div class="kap">
        <div class="bolum-ust">
          <div>
            <h2 id="oyunlar-baslik">Türkçesi hazır oyunlar</h2>
            <p class="bolum-alt">Menüler, altyazılar, notlar, ipuçları: her satır Türkçe. Ğ, ş, ı, İ harfleri oyunun kendi yazı tipine eklenir; kare ya da soru işareti çıkmaz.</p>
          </div>
          <a class="dugme dugme-ikincil" href="/oyunlar/">Tüm oyunlar ({len(oyunlar)}) →</a>
        </div>
        <div class="oyunlar">
{kartlar}
{SIRADAKI}
        </div>
      </div>
    </section>"""
    govde = (KOK / "sablonlar" / "ana.html").read_text(encoding="utf-8").replace("{{VITRIN}}", vitrin_html)
    # Eski tek sayfa bağlantıları (/#metro-exodus gibi) oyun sayfasına yönlensin.
    eski = {o["eski_baglanti"]: o["kimlik"] for o in oyunlar if o.get("eski_baglanti")}
    yonlendir = ("\n  <script>(function(){var e=" + json.dumps(eski) +
                 ",h=location.hash.slice(1);if(e[h])location.replace('/oyun/'+e[h]+'/');})();</script>")
    adlar = ", ".join(o["ad"] for o in hazir)
    return sayfa(
        "Türkçesi Var — Oyunlara güvenli, ücretsiz Türkçe yama",
        f"Türkçesi Var, oyunlara tek tıkla Türkçe yama kuran ücretsiz ve açık kaynak bir uygulama. Türkçesi hazır: {adlar}. Dosya ya da DLL dağıtmaz, tek tıkla kaldırılır.",
        "/", govde, bas_ek=yonlendir)


def oyunlar_sayfasi(oyunlar):
    sirali = sorted(oyunlar, key=lambda o: o["eklenme"], reverse=True)
    kartlar = "\n".join(kart(o, "h2") for o in sirali)
    sayilar = {d: sum(o["durum"] == d for o in oyunlar) for d in DURUMLAR}
    secenekler = "".join(
        f'<button type="button" data-durum-sec="{d}" aria-pressed="false">{DURUMLAR[d][1]} <span>{n}</span></button>'
        for d, n in sayilar.items() if n)
    durum_satiri = ""
    if sum(1 for n in sayilar.values() if n) > 1:
        durum_satiri = f'<div class="secenekler" role="group" aria-label="Duruma göre süz"><button type="button" data-durum-sec="tumu" aria-pressed="true">Tümü <span>{len(oyunlar)}</span></button>{secenekler}</div>'
    ozet = f"{sayilar['hazir']} oyun tamamen Türkçe"
    if sayilar["cevriliyor"]:
        ozet += f", {sayilar['cevriliyor']} oyun çevriliyor"
    if sayilar["oylamada"]:
        ozet += f", {sayilar['oylamada']} oyun oylamada"
    govde = f"""    <section class="bolum sayfa-ust">
      <div class="kap">
        <h1>Tüm oyunlar</h1>
        <p class="bolum-alt">{ozet}. Oyuna tıkla; neyin Türkçe olduğunu, hangi sürümün desteklendiğini ve oyunun içinden görüntüleri gör.</p>
        <div class="arac-cubugu" data-oyun-listesi-araclari hidden>
          <label class="arama"><span class="gizli">Oyun ara</span><input type="search" id="oyun-ara" placeholder="Oyun ara… (ör. metro, korku)" autocomplete="off"></label>
          {durum_satiri}
          <label class="siralama">Sırala
            <select id="siralama"><option value="yeni">En yeni</option><option value="ad">A–Z</option></select>
          </label>
        </div>
        <p class="sonuc-sayisi" aria-live="polite"></p>
        <div class="oyunlar" data-oyun-listesi>
{kartlar}
        </div>
        <p class="bos-sonuc" hidden>Bu aramayla eşleşen oyun yok. Türkçesini istiyorsan <a href="{DISCORD}" rel="noopener">Discord'da iste</a>.</p>
        <div class="istek-seridi">
          <div>
            <h2>Aradığın oyun yok mu?</h2>
            <p>Sıradaki oyunları siz seçiyorsunuz. Discord'daki <strong>oyun-istekleri</strong> kanalına yaz ya da var olan isteğe 👍 bırak; en çok istenenler önce çevrilir.</p>
          </div>
          <a class="dugme dugme-ana" href="{DISCORD}" rel="noopener">Oyun iste</a>
        </div>
      </div>
    </section>"""
    return sayfa(
        "Tüm oyunlar — Türkçesi Var",
        f"Türkçesi Var ile Türkçe oynanabilen oyunlar: {ozet}. Ücretsiz, tek tıkla kur ve kaldır.",
        "/oyunlar/", govde)


def oyun_sayfasi(o, oyunlar):
    hazir = o["durum"] == "hazir"
    eylem = (f'<a class="dugme dugme-ana" href="{INDIR}">Uygulamayı indir</a>' if hazir
             else f'<a class="dugme dugme-ana" href="{DISCORD}" rel="noopener">Discord\'da takip et</a>')
    turler = "".join(f'<span class="etiket-kucuk">{e(t)}</span>' for t in o.get("tur", []))
    neler = "\n".join(f"                <li>{m}</li>" for m in o.get("neler_turkce", []))
    gorseller = "\n".join(
        f'            <figure><img src="/gorseller/{g["dosya"]}" alt="{e(g["alt"])}" loading="{"eager" if i == 0 else "lazy"}" width="1280" height="720"><figcaption>{e(g["yazi"])}</figcaption></figure>'
        for i, g in enumerate(o.get("gorseller", [])))
    digerleri = [d for d in sorted(oyunlar, key=lambda d: d["eklenme"], reverse=True) if d["kimlik"] != o["kimlik"]][:3]
    diger_html = ""
    if digerleri:
        diger_html = f"""
    <section class="bolum koyu" aria-labelledby="diger-baslik">
      <div class="kap">
        <div class="bolum-ust">
          <h2 id="diger-baslik">Diğer oyunlar</h2>
          <a class="dugme dugme-ikincil" href="/oyunlar/">Tüm oyunlar ({len(oyunlar)}) →</a>
        </div>
        <div class="oyunlar">
{chr(10).join(kart(d) for d in digerleri)}
        </div>
      </div>
    </section>"""
    satir_bilgi = f' · {sayi(o["satir"])} satır' if o.get("satir") else ""
    govde = f"""    <section class="bolum sayfa-ust">
      <div class="kap">
        <nav class="kirinti" aria-label="Konum"><a href="/oyunlar/">Oyunlar</a> <span aria-hidden="true">›</span> <span>{e(o['ad'])}</span></nav>
        <article class="detay oyun-sayfasi">
          <div class="detay-ust">
            <div>
              <h1 class="detay-baslik">{e(o['ad'])} Türkçe Yama</h1>
              <p class="platform">{e(' · '.join(o['platform']))}{satir_bilgi} {rozet(o)}</p>
              <p class="turler">{turler}<span class="eklenme">Eklendi: {tarih(o['eklenme'])}</span></p>
            </div>
            {eylem}
          </div>
          <div class="detay-metin">
            <p>{o.get('aciklama', '')}</p>
            <div class="detay-kolonlar">
              <div>
                <h2 class="ara-baslik">Neler Türkçe?</h2>
                <ul class="liste">
{neler}
                </ul>
              </div>
              <div>
                <h2 class="ara-baslik">Hangi sürüm?</h2>
                <p>{o.get('surum', '')}</p>
                <h2 class="ara-baslik">Nasıl kurulur?</h2>
                <p>{o.get('kurulum', '')}</p>
              </div>
            </div>
          </div>
          <h2 class="ara-baslik">Oyunun içinden <span class="ipucu">Büyütmek için görsele tıkla</span></h2>
          <div class="galeri" data-galeri>
{gorseller}
          </div>
        </article>
        <div class="istek-seridi">
          <div>
            <h2>Hatalı bir çeviri mi gördün?</h2>
            <p>Ekran görüntüsüyle Discord'daki <strong>çeviri-hataları</strong> kanalına yaz; düzeltme bir sonraki güncellemeyle herkese gelir.</p>
          </div>
          <a class="dugme dugme-ikincil" href="{DISCORD}" rel="noopener">Discord'a yaz</a>
        </div>
      </div>
    </section>{diger_html}"""
    aciklama = (f"{o['ad']} için ücretsiz Türkçe yama" +
                (f": {sayi(o['satir'])} satırın tamamı Türkçe" if o.get("satir") else "") +
                ". Türkçesi Var ile tek tıkla kur, tek tıkla kaldır; oyun dosyası ya da DLL indirmeden.")
    return sayfa(f"{o['ad']} Türkçe Yama — Türkçesi Var", aciklama,
                 f"/oyun/{o['kimlik']}/", govde, gorsel=f"/gorseller/{o['kapak']}")


def bulunamadi():
    govde = """    <section class="bolum sayfa-ust">
      <div class="kap dar ortala-metin">
        <h1>Sayfa bulunamadı</h1>
        <p class="bolum-alt">Aradığın sayfa taşınmış ya da hiç olmamış olabilir.</p>
        <p><a class="dugme dugme-ana" href="/oyunlar/">Oyunlara göz at</a> <a class="dugme dugme-ikincil" href="/">Ana sayfa</a></p>
      </div>
    </section>"""
    return sayfa("Sayfa bulunamadı — Türkçesi Var", "Aradığın sayfa bulunamadı.", "/404.html", govde)


# --- Denetim ve yazma ---------------------------------------------------------

def denetle(oyunlar):
    zorunlu = ["kimlik", "ad", "durum", "eklenme", "platform", "ozet", "kapak"]
    kimlikler = set()
    for o in oyunlar:
        for alan in zorunlu:
            if not o.get(alan):
                raise SystemExit(f"HATA: '{o.get('kimlik', '?')}' kaydında '{alan}' eksik")
        if o["durum"] not in DURUMLAR:
            raise SystemExit(f"HATA: {o['kimlik']}: bilinmeyen durum '{o['durum']}'")
        if o["kimlik"] in kimlikler:
            raise SystemExit(f"HATA: {o['kimlik']} iki kez yazılmış")
        kimlikler.add(o["kimlik"])
        for dosya in [o["kapak"], *[g["dosya"] for g in o.get("gorseller", [])]]:
            if not (KOK / "gorseller" / dosya).exists():
                raise SystemExit(f"HATA: {o['kimlik']}: gorseller/{dosya} yok")


def yaz(yol, icerik):
    hedef = CIKTI / yol
    hedef.parent.mkdir(parents=True, exist_ok=True)
    hedef.write_text(icerik, encoding="utf-8", newline="\n")


def main():
    oyunlar = json.loads((KOK / "veri" / "oyunlar.json").read_text(encoding="utf-8"))["oyunlar"]
    denetle(oyunlar)
    if CIKTI.exists():
        shutil.rmtree(CIKTI)
    CIKTI.mkdir()
    for dosya in ["stil.css", "site.js", "favicon.ico"]:
        shutil.copy2(KOK / dosya, CIKTI / dosya)
    shutil.copytree(KOK / "gorseller", CIKTI / "gorseller")
    # Google Search Console doğrulama dosyaları (google....html) olduğu gibi yayınlanır.
    for dogrulama in KOK.glob("google*.html"):
        shutil.copy2(dogrulama, CIKTI / dogrulama.name)

    yaz("index.html", ana_sayfa(oyunlar))
    yaz("oyunlar/index.html", oyunlar_sayfasi(oyunlar))
    for o in oyunlar:
        yaz(f"oyun/{o['kimlik']}/index.html", oyun_sayfasi(o, oyunlar))
    yaz("404.html", bulunamadi())

    adresler = ["/", "/oyunlar/"] + [f"/oyun/{o['kimlik']}/" for o in oyunlar]
    yaz("sitemap.xml", '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "".join(f"  <url><loc>{SITE}{a}</loc></url>\n" for a in adresler) + "</urlset>\n")
    yaz("robots.txt", f"User-agent: *\nAllow: /\nSitemap: {SITE}/sitemap.xml\n")
    print(f"Site üretildi: {len(oyunlar)} oyun, {len(adresler)} sayfa -> {CIKTI}")


if __name__ == "__main__":
    main()

"""Türkçesi Var sitesini veri/oyunlar.json'dan üretir.

Kullanım:  python uret.py          -> _site/ klasörüne bütün siteyi yazar
Önizleme:  python -m http.server 8765 --directory _site

Üretilen sayfalar:
  /                      ana sayfa (son eklenen oyunlar vitrini + sabit bölümler)
  /oyunlar/              bütün oyunlar (arama, durum süzgeci, sıralama)
  /oyun/<kimlik>/        her oyunun kendi sayfası
  /404.html, /sitemap.xml, /robots.txt
GitHub'da main'e her gönderimde ve her sabah .github/workflows/yayinla.yml bunu çalıştırıp yayınlar
(sabah çalışması indirme ve Discord sayılarını tazeler).
"""

import hashlib
import html
import json
import re
import shutil
import urllib.request
from pathlib import Path

from PIL import Image

KOK = Path(__file__).resolve().parent
CIKTI = KOK / "_site"
SITE = "https://turkcesivar.com"
INDIR = "https://github.com/turkcesivar/turkcesi-var/releases/latest/download/TurkcesiVar-Kurulum.exe"
DISCORD = "https://discord.gg/nnNUCMUBJx"
GITHUB = "https://github.com/turkcesivar/turkcesi-var"
KREOSUS = "https://kreosus.com/turkcesivar"
ISTEK_FORMU = GITHUB + "/issues/new?template=oyun-istegi.yml"
EPOSTA = "iletisim@turkcesivar.com"
# Son sürümün VirusTotal taraması. Yeni sürümde bu iki satırı güncelle.
VIRUSTOTAL = "https://www.virustotal.com/gui/file/11f18389391760e51e58a85116a70d8be100d3905d26c25c22f34769d94961fa"
VIRUSTOTAL_SONUC = "0/66"
# İndirme ve Discord sayısı ancak bu eşikleri geçince rakamlar şeridinde görünür.
INDIRME_ESIGI = 500
DISCORD_ESIGI = 100
VITRIN_SAYISI = 6
BOYLAR = (640, 1024, 1600)  # her oyun görselinden üretilen genişlikler; asıl dosya da yayınlanır
KART_BOYU = "(max-width: 900px) calc(100vw - 32px), 360px"
GALERI_BOYU = "(max-width: 900px) calc(100vw - 72px), 1060px"
GALERI_KUCUK_BOYU = "(max-width: 900px) calc(50vw - 46px), 530px"

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


# --- Görseller: her boy üretilir, tarayıcı ekranına uygun olanı seçer --------

_olcu = {}


def olcu(dosya):
    if dosya not in _olcu:
        with Image.open(KOK / "gorseller" / dosya) as im:
            _olcu[dosya] = im.size
    return _olcu[dosya]


def boy_adi(dosya, w):
    kok_ad = dosya.rsplit(".", 1)[0]
    return f"/gorseller/boy/{kok_ad}-{w}.jpg"


def resim(dosya, alt, sizes, yukle="lazy", buyuk=False):
    """srcset'li <img>. buyuk=True ise büyüteç asıl çözünürlüğü açar."""
    gen, yuk = olcu(dosya)
    parcalar = [f"{boy_adi(dosya, w)} {w}w" for w in BOYLAR if w < gen]
    parcalar.append(f"/gorseller/{dosya} {gen}w")
    varsayilan = boy_adi(dosya, 1024) if gen > 1024 else f"/gorseller/{dosya}"
    ek = f' data-buyuk="/gorseller/{dosya}"' if buyuk else ""
    return (f'<img src="{varsayilan}" srcset="{", ".join(parcalar)}" sizes="{sizes}" '
            f'alt="{e(alt)}" loading="{yukle}" decoding="async" width="{gen}" height="{yuk}"{ek}>')


def boylari_uret(dosyalar):
    hedef = CIKTI / "gorseller" / "boy"
    hedef.mkdir(parents=True, exist_ok=True)
    for dosya in sorted(dosyalar):
        with Image.open(KOK / "gorseller" / dosya) as im:
            im = im.convert("RGB")
            for w in BOYLAR:
                if w >= im.width:
                    continue
                h = round(im.height * w / im.width)
                im.resize((w, h), Image.LANCZOS).save(
                    CIKTI / boy_adi(dosya, w).lstrip("/"), "JPEG", quality=86, optimize=True, progressive=True)


# --- Arama motorları: yapılandırılmış veri (schema.org JSON-LD) ---------------

def duz(metin):
    """HTML etiketlerini atar: '<strong>21.442</strong> satır' -> '21.442 satır'."""
    return html.unescape(re.sub(r"<[^>]+>", "", metin)).strip()


def jsonld(*nesneler):
    """Google'ın okuduğu <script type="application/ld+json"> blokları."""
    return "".join(
        '\n  <script type="application/ld+json">' +
        json.dumps({"@context": "https://schema.org", **n}, ensure_ascii=False).replace("</", "<\\/") +
        "</script>" for n in nesneler)


_son_surum = []


def son_surum():
    """Uygulamanın son sürüm numarası (GitHub'dan); okunamazsa None."""
    if not _son_surum:
        r = json_getir("https://api.github.com/repos/turkcesivar/turkcesi-var/releases/latest")
        _son_surum.append(r["tag_name"].lstrip("v") if isinstance(r, dict) and r.get("tag_name") else None)
    return _son_surum[0]


def uygulama_bilgisi(**ek):
    """Türkçesi Var'ı ücretsiz bir Windows uygulaması olarak tanıtan schema.org kaydı."""
    kayit = {
        "@type": "SoftwareApplication",
        "name": "Türkçesi Var",
        "applicationCategory": "UtilitiesApplication",
        "operatingSystem": "Windows 10, Windows 11",
        "inLanguage": "tr",
        "offers": {"@type": "Offer", "price": "0", "priceCurrency": "TRY"},
        "downloadUrl": INDIR,
        "url": SITE + "/",
        "image": SITE + "/gorseller/simge-256.png",
        "screenshot": SITE + "/gorseller/uygulama.jpg",
        "license": "https://www.gnu.org/licenses/gpl-3.0.html",
        "isAccessibleForFree": True,
        "publisher": {"@id": SITE + "/#kurulus"},
    }
    if son_surum():
        kayit["softwareVersion"] = son_surum()
    kayit.update(ek)
    return kayit


KURULUS = {
    "@type": "Organization",
    "@id": SITE + "/#kurulus",
    "name": "Türkçesi Var",
    "url": SITE + "/",
    "logo": SITE + "/gorseller/simge-256.png",
    "email": EPOSTA,
    "sameAs": [GITHUB, DISCORD, KREOSUS],
}


def sss_bilgisi(sablon):
    """Ana sayfadaki SSS'yi (<details>) Google'ın anladığı soru-cevap kaydına çevirir."""
    sorular = re.findall(r"<details><summary>(.*?)</summary><p>(.*?)</p></details>", sablon, re.S)
    return {"@type": "FAQPage", "mainEntity": [
        {"@type": "Question", "name": duz(s), "acceptedAnswer": {"@type": "Answer", "text": duz(c)}}
        for s, c in sorular]}


def kisa_ad(o):
    """Aramada kullanılan ad: 'Metro Exodus Enhanced Edition' -> 'Metro Exodus' (veri dosyasında kisa_ad varsa)."""
    return o.get("kisa_ad") or o["ad"]


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
  <meta name="robots" content="index, follow, max-image-preview:large">
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
      <a href="/" class="logo" aria-label="Türkçesi Var ana sayfa"><img src="/gorseller/logo-yatay.svg" alt="Türkçesi Var" width="162" height="33"></a>
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
      <img src="/gorseller/logo-yatay.svg" alt="Türkçesi Var" width="118" height="24">
      <p>Kaynak kodu GNU GPL v3.0 ve ek şartlarıyla, Türkçe çeviriler CC BY-NC-ND 4.0 ile korunur. Oyunlar ve orijinal metinleri yapımcılarına aittir; Türkçesi Var resmi bir yapımcı ürünü değildir. Resmi sürümler yalnızca <a href="{GITHUB}">GitHub sayfasından</a> yayımlanır.</p>
      <nav aria-label="Alt bağlantılar">
        <a href="/oyunlar/">Oyunlar</a>
        <a href="{GITHUB}">GitHub</a>
        <a href="{DISCORD}" rel="noopener">Discord</a>
        <a href="{KREOSUS}" rel="noopener">Kreosus</a>
        <a href="mailto:{EPOSTA}">{EPOSTA}</a>
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
        satir = f'<strong>{sayi(o["satir"])} satır çevrildi</strong> — '
    else:  # özet cümle başında kalır: ilk harfi Türkçe kurala göre büyüt
        satir = ""
        ozet = {"i": "İ", "ı": "I"}.get(ozet[0], ozet[0].upper()) + ozet[1:]
    return f"""          <article class="oyun" data-durum="{o['durum']}" data-ad="{e(o['ad'])}" data-eklenme="{o['eklenme']}" data-ara="{e(arama_metni(o))}">
            {resim(o['kapak'], o['ad'] + ' Türkçe', KART_BOYU)}
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


# --- Ana sayfa bölümleri: rakamlar, karşılaştırma, sırada --------------------

def json_getir(adres):
    """İnternetten JSON okur; olmazsa None (site yine üretilir, ilgili rakam gizlenir)."""
    try:
        istek = urllib.request.Request(adres, headers={"User-Agent": "turkcesivar-site", "Accept": "application/json"})
        with urllib.request.urlopen(istek, timeout=15) as yanit:
            return json.load(yanit)
    except Exception as hata:  # ağ yok, sınır aşıldı vb.
        print(f"  uyarı: {adres} okunamadı ({hata})")
        return None


def indirme_sayisi():
    surumler = json_getir("https://api.github.com/repos/turkcesivar/turkcesi-var/releases?per_page=100")
    if not isinstance(surumler, list):
        return None
    return sum(a.get("download_count", 0) for s in surumler for a in s.get("assets", []) if a.get("name", "").endswith(".exe"))


def discord_sayisi():
    kod = DISCORD.rstrip("/").rsplit("/", 1)[-1]
    davet = json_getir(f"https://discord.com/api/v10/invites/{kod}?with_counts=true")
    return davet.get("approximate_member_count") if isinstance(davet, dict) else None


def yuvarla(n):
    """59094 -> '59.000+', 1234 -> '1.200+', 640 -> '600+'."""
    adim = 1000 if n >= 10000 else 100 if n >= 1000 else 10 if n >= 100 else 1
    return sayi(n // adim * adim) + ("+" if n >= 100 else "")


def toplam_satir(hazir):
    """Aynı metin dosyasını paylaşan oyunlar (metin_grubu) toplamda bir kez sayılır."""
    gruplar = {}
    for o in hazir:
        if o.get("satir"):
            anahtar = o.get("metin_grubu") or o["kimlik"]
            gruplar[anahtar] = max(gruplar.get(anahtar, 0), o["satir"])
    return sum(gruplar.values())


def rakamlar_html(oyunlar):
    hazir = [o for o in oyunlar if o["durum"] == "hazir"]
    ogeler = [(str(len(hazir)), "oyun tamamen Türkçe", "/oyunlar/")]
    satir = toplam_satir(hazir)
    if satir:
        ogeler.append((yuvarla(satir), "satır Türkçeye çevrildi", None))
    indirme = indirme_sayisi()
    if indirme and indirme >= INDIRME_ESIGI:
        ogeler.append((yuvarla(indirme), "indirme", GITHUB + "/releases"))
    uye = discord_sayisi()
    if uye and uye >= DISCORD_ESIGI:
        ogeler.append((yuvarla(uye), "kişilik Discord topluluğu", DISCORD))
    ogeler.append((VIRUSTOTAL_SONUC, "VirusTotal taraması", VIRUSTOTAL))
    ogeler.append(("0 ₺", "ücretsiz, reklamsız", None))
    print(f"  rakamlar: {len(hazir)} oyun, {satir} satır, indirme {indirme}, discord {uye}")
    parcalar = []
    for deger, yazi, adres in ogeler:
        ic = f'<span class="rakam-deger">{e(deger)}</span><span class="rakam-yazi">{e(yazi)}</span>'
        if adres:
            rel = ' rel="noopener"' if adres.startswith("http") else ""
            ic = f'<a href="{adres}"{rel}>{ic}</a>'
        parcalar.append(f"          <li>{ic}</li>")
    return f"""    <section class="rakamlar" aria-label="Rakamlarla Türkçesi Var">
      <ul class="kap rakam-listesi">
{chr(10).join(parcalar)}
      </ul>
    </section>"""


def karsilastirma_html():
    yol = KOK / "veri" / "karsilastirma.json"
    if not yol.exists():
        return ""
    gruplar = json.loads(yol.read_text(encoding="utf-8"))["gruplar"]
    sekmeler, paneller = [], []
    for i, g in enumerate(gruplar):
        secili = "true" if i == 0 else "false"
        sira = "" if i == 0 else ' tabindex="-1"'
        sekmeler.append(f'<button type="button" role="tab" id="sekme-{g["kimlik"]}" aria-controls="panel-{g["kimlik"]}" aria-selected="{secili}"{sira}>{e(g["sekme"])}</button>')
        satirlar = "\n".join(
            f'              <li><span class="asil" lang="en"><abbr title="İngilizce orijinal">EN</abbr>{e(en)}</span>'
            f'<span class="turkcesi"><abbr title="Türkçesi Var çevirisi">TR</abbr>{e(tr)}</span></li>'
            for en, tr in g["satirlar"])
        paneller.append(f"""          <div class="kars-panel" role="tabpanel" id="panel-{g['kimlik']}" aria-labelledby="sekme-{g['kimlik']}" data-kars-panel>
            <figure class="kars-gorsel" data-galeri>{resim(g['gorsel'], g['gorsel_yazi'], KART_BOYU.replace('360px', '540px'), buyuk=True)}<figcaption>{e(g['gorsel_yazi'])}</figcaption></figure>
            <ul class="kars-satirlar">
{satirlar}
            </ul>
          </div>""")
    return f"""    <section class="bolum" id="karsilastirma" aria-labelledby="kars-baslik">
      <div class="kap">
        <h2 id="kars-baslik">Orijinali ve Türkçesi</h2>
        <p class="bolum-alt">Kelimesi kelimesine değil, oyunun havasına uygun çeviri. Aşağıdaki satırlar oyunların gerçek metinlerinden ve Türkçesi Var'ın gerçek çevirilerinden.</p>
        <div class="kars-sekmeler" role="tablist" aria-label="Oyun seç" data-kars-sekmeler hidden>{"".join(sekmeler)}</div>
        <div class="kars">
{chr(10).join(paneller)}
        </div>
      </div>
    </section>"""


def sirada_html(oyunlar):
    """Çevrilen ve oylamadaki oyunlar; hiç yoksa bölüm hiç çıkmaz."""
    sirada = [o for o in oyunlar if o["durum"] == "cevriliyor"] + [o for o in oyunlar if o["durum"] == "oylamada"]
    if not sirada:
        return ""
    return f"""    <section class="bolum" id="sirada" aria-labelledby="sirada-baslik">
      <div class="kap">
        <div class="bolum-ust">
          <div>
            <h2 id="sirada-baslik">Sırada</h2>
            <p class="bolum-alt">Şu an çevrilen ve oylamadaki oyunlar. Hangisinin önce geleceğini Discord'daki oylar belirler.</p>
          </div>
          <a class="dugme dugme-ikincil" href="{DISCORD}" rel="noopener">Oylamaya katıl →</a>
        </div>
        <div class="oyunlar">
{chr(10).join(kart(o) for o in sirada[:VITRIN_SAYISI])}
        </div>
      </div>
    </section>"""


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
    govde = (KOK / "sablonlar" / "ana.html").read_text(encoding="utf-8")
    for yer, icerik in {
        "{{RAKAMLAR}}": rakamlar_html(oyunlar),
        "{{VITRIN}}": vitrin_html,
        "{{SIRADA}}": sirada_html(oyunlar),
        "{{KARSILASTIRMA}}": karsilastirma_html(),
        "{{VIRUSTOTAL}}": VIRUSTOTAL,
        "{{VIRUSTOTAL_SONUC}}": VIRUSTOTAL_SONUC,
    }.items():
        govde = govde.replace(yer, icerik)
    # Eski tek sayfa bağlantıları (/#metro-exodus gibi) oyun sayfasına yönlensin.
    eski = {o["eski_baglanti"]: o["kimlik"] for o in oyunlar if o.get("eski_baglanti")}
    yonlendir = ("\n  <script>(function(){var e=" + json.dumps(eski) +
                 ",h=location.hash.slice(1);if(e[h])location.replace('/oyun/'+e[h]+'/');})();</script>")
    adlar = ", ".join(kisa_ad(o) for o in hazir)
    aciklama = (f"Ücretsiz Türkçe yama: {adlar} tek tıkla Türkçe. "
                "Türkçesi Var oyun dosyası ya da DLL dağıtmaz; Türkçe yamayı senin bilgisayarında hazırlar, tek tıkla kaldırılır.")
    veri = jsonld(
        {"@type": "WebSite", "@id": SITE + "/#site", "name": "Türkçesi Var", "alternateName": "Türkçesi Var Türkçe Yama",
         "url": SITE + "/", "inLanguage": "tr", "publisher": {"@id": SITE + "/#kurulus"}},
        KURULUS,
        uygulama_bilgisi(description=aciklama),
        sss_bilgisi(govde))
    return sayfa(
        "Türkçesi Var — Oyunlara Ücretsiz Türkçe Yama",
        aciklama, "/", govde, bas_ek=yonlendir + veri)


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
    liste = jsonld(
        {"@type": "ItemList", "name": "Türkçe yaması olan oyunlar", "itemListElement": [
            {"@type": "ListItem", "position": i, "url": f"{SITE}/oyun/{o['kimlik']}/", "name": f"{o['ad']} Türkçe Yama"}
            for i, o in enumerate(sirali, 1)]},
        {"@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Ana sayfa", "item": SITE + "/"},
            {"@type": "ListItem", "position": 2, "name": "Oyunlar", "item": SITE + "/oyunlar/"}]})
    return sayfa(
        "Türkçe Yama Listesi: Tüm Oyunlar — Türkçesi Var",
        f"Türkçe yaması olan oyunlar: {ozet}. {', '.join(kisa_ad(o) + ' Türkçe yama' for o in sirali[:4])}. Ücretsiz, tek tıkla kur ve kaldır.",
        "/oyunlar/", govde, bas_ek=liste)


def oyun_sayfasi(o, oyunlar):
    hazir = o["durum"] == "hazir"
    eylem = (f'<a class="dugme dugme-ana" href="{INDIR}">Türkçe yamayı indir</a>' if hazir
             else f'<a class="dugme dugme-ana" href="{DISCORD}" rel="noopener">Discord\'da takip et</a>')
    turler = "".join(f'<span class="etiket-kucuk">{e(t)}</span>' for t in o.get("tur", []))
    neler = "\n".join(f"                <li>{m}</li>" for m in o.get("neler_turkce", []))
    gorseller = "\n".join(
        f'            <figure>{resim(g["dosya"], g["alt"], GALERI_BOYU if i == 0 else GALERI_KUCUK_BOYU, "eager" if i == 0 else "lazy", buyuk=True)}<figcaption>{e(g["yazi"])}</figcaption></figure>'
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
    satir_bilgi = f' · {sayi(o["satir"])} satır çevrildi' if o.get("satir") else ""
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
    kisa = kisa_ad(o)
    aciklama = (f"{kisa} Türkçe yama" +
                (f": {sayi(o['satir'])} satır Türkçe; {duz(o['ozet'])}" if o.get("satir") else f": {duz(o['ozet'])}") +
                " Ücretsiz indir, tek tıkla kur ve kaldır; oyun dosyası ya da DLL indirmeden.")
    kapak = boy_adi(o["kapak"], 1600) if olcu(o["kapak"])[0] > 1600 else f"/gorseller/{o['kapak']}"
    adres = f"{SITE}/oyun/{o['kimlik']}/"
    yama = uygulama_bilgisi(
        name=f"{o['ad']} Türkçe Yama",
        alternateName=[f"{kisa} Türkçe Yama", f"{kisa} Türkçe Altyazı", f"{kisa} Türkçe"],
        url=adres,
        description=aciklama,
        image=SITE + kapak,
        screenshot=[f"{SITE}/gorseller/{g['dosya']}" for g in o.get("gorseller", [])][:5],
        datePublished=o["eklenme"],
        dateModified=o.get("guncelleme", o["eklenme"]),
        about={"@type": "VideoGame", "name": o["ad"], "gamePlatform": ["PC"] + list(o.get("platform", []))})
    if not hazir:  # henüz indirilemez: fiyat/indirme bilgisi verme
        yama.pop("offers")
        yama.pop("downloadUrl")
    veri = jsonld(
        {"@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Ana sayfa", "item": SITE + "/"},
            {"@type": "ListItem", "position": 2, "name": "Oyunlar", "item": SITE + "/oyunlar/"},
            {"@type": "ListItem", "position": 3, "name": f"{o['ad']} Türkçe Yama", "item": adres}]},
        yama)
    baslik = (f"{kisa} Türkçe Yama İndir — Ücretsiz | Türkçesi Var" if hazir
              else f"{kisa} Türkçe Yama ({DURUMLAR[o['durum']][1]}) — Türkçesi Var")
    return sayfa(baslik, aciklama, f"/oyun/{o['kimlik']}/", govde, gorsel=kapak, bas_ek=veri)


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

    boylari_uret({o["kapak"] for o in oyunlar} | {g["dosya"] for o in oyunlar for g in o.get("gorseller", [])})
    yaz("index.html", ana_sayfa(oyunlar))
    yaz("oyunlar/index.html", oyunlar_sayfasi(oyunlar))
    for o in oyunlar:
        yaz(f"oyun/{o['kimlik']}/index.html", oyun_sayfasi(o, oyunlar))
    yaz("404.html", bulunamadi())

    son = max(o["eklenme"] for o in oyunlar)
    adresler = [("/", son), ("/oyunlar/", son)] + [(f"/oyun/{o['kimlik']}/", o.get("guncelleme", o["eklenme"])) for o in oyunlar]
    yaz("sitemap.xml", '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "".join(f"  <url><loc>{SITE}{a}</loc><lastmod>{t}</lastmod></url>\n" for a, t in adresler) + "</urlset>\n")
    yaz("robots.txt", f"User-agent: *\nAllow: /\nSitemap: {SITE}/sitemap.xml\n")
    print(f"Site üretildi: {len(oyunlar)} oyun, {len(adresler)} sayfa -> {CIKTI}")


if __name__ == "__main__":
    main()

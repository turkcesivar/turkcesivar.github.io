// Türkçesi Var sitesi: tıklanır oyun kartları, oyun listesi süzgeci ve görsel büyütücü. Kütüphane yok.
(function () {
  "use strict";
  document.documentElement.classList.add("js");

  // --- Tıklanır oyun kartları ----------------------------------------------
  // Kartın tamamı oyunun sayfasına gider; içindeki başka bağlantılar kendi işini yapar.
  Array.prototype.slice.call(document.querySelectorAll(".oyun")).forEach(function (kart) {
    var ac = kart.querySelector(".oyun-ac");
    if (!ac) return;
    kart.classList.add("tiklanir");
    kart.addEventListener("click", function (e) {
      if (e.target.closest("a")) return;
      if (e.ctrlKey || e.metaKey) { window.open(ac.href, "_blank"); return; }
      location.href = ac.href;
    });
  });

  // --- Tüm oyunlar: arama, durum süzgeci, sıralama ---------------------------
  var oyunListesi = document.querySelector("[data-oyun-listesi]");
  if (oyunListesi) {
    var araclar = document.querySelector("[data-oyun-listesi-araclari]");
    var ara = document.getElementById("oyun-ara");
    var siralama = document.getElementById("siralama");
    var durumDugmeleri = Array.prototype.slice.call(document.querySelectorAll("[data-durum-sec]"));
    var sonucYazi = document.querySelector(".sonuc-sayisi");
    var bos = document.querySelector(".bos-sonuc");
    var kartlar = Array.prototype.slice.call(oyunListesi.querySelectorAll(".oyun"));
    var secilenDurum = "tumu";
    araclar.hidden = false;

    // "İstanbul" ile "istanbul", "şehir" ile "sehir" aynı sayılsın.
    var harf = { "ı": "i", "İ": "i", "ş": "s", "ğ": "g", "ç": "c", "ö": "o", "ü": "u", "â": "a", "î": "i", "û": "u" };
    var sade = function (s) {
      return s.toLocaleLowerCase("tr").replace(/[ıİşğçöüâîû]/g, function (h) { return harf[h]; })
        .normalize("NFD").replace(/[̀-ͯ]/g, "").trim();
    };
    kartlar.forEach(function (k) { k._ara = sade(k.dataset.ara || k.dataset.ad); });

    // Adres çubuğu: /oyunlar/?ara=metro&durum=hazir paylaşılabilsin.
    var parametre = new URLSearchParams(location.search);
    if (parametre.get("ara")) ara.value = parametre.get("ara");
    if (parametre.get("durum") && durumDugmeleri.some(function (d) { return d.dataset.durumSec === parametre.get("durum"); })) {
      secilenDurum = parametre.get("durum");
    }
    if (parametre.get("sira") === "ad") siralama.value = "ad";

    var uygula = function () {
      var aranan = sade(ara.value);
      var sirali = kartlar.slice().sort(function (a, b) {
        return siralama.value === "ad"
          ? a.dataset.ad.localeCompare(b.dataset.ad, "tr")
          : b.dataset.eklenme.localeCompare(a.dataset.eklenme);
      });
      var gorunen = 0;
      sirali.forEach(function (k) {
        var uyar = (secilenDurum === "tumu" || k.dataset.durum === secilenDurum) &&
          (!aranan || k._ara.indexOf(aranan) >= 0);
        k.hidden = !uyar;
        if (uyar) gorunen++;
        oyunListesi.appendChild(k);
      });
      durumDugmeleri.forEach(function (d) {
        d.setAttribute("aria-pressed", d.dataset.durumSec === secilenDurum ? "true" : "false");
      });
      bos.hidden = gorunen > 0;
      sonucYazi.textContent = aranan || secilenDurum !== "tumu" ? gorunen + " oyun bulundu" : "";

      var p = new URLSearchParams();
      if (ara.value.trim()) p.set("ara", ara.value.trim());
      if (secilenDurum !== "tumu") p.set("durum", secilenDurum);
      if (siralama.value === "ad") p.set("sira", "ad");
      var q = p.toString();
      if (history.replaceState) history.replaceState(null, "", location.pathname + (q ? "?" + q : ""));
    };

    ara.addEventListener("input", uygula);
    siralama.addEventListener("change", uygula);
    durumDugmeleri.forEach(function (d) {
      d.addEventListener("click", function () { secilenDurum = d.dataset.durumSec; uygula(); });
    });
    uygula();
  }

  // --- Yumuşak efektler -------------------------------------------------------
  var azalt = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  // Kaydırınca üst menünün altına ince gölge.
  var ust = document.querySelector(".ust");
  if (ust) {
    var golge = function () { ust.classList.toggle("golgeli", window.scrollY > 8); };
    window.addEventListener("scroll", golge, { passive: true });
    golge();
  }

  // Rakamlar sayarak dolsun: "59.000+" -> 0'dan 59.000'e; sayı olmayanlar ("0/66") olduğu gibi kalır.
  var say = function (el) {
    var m = /^([\d.]+)(\+?)$/.exec(el.textContent.trim());
    if (!m || azalt) return;
    var son = parseInt(m[1].replace(/\./g, ""), 10), asil = el.textContent, bas = null;
    if (!(son > 9)) return;
    var adim = function (t) {
      if (bas === null) bas = t;
      var o = Math.min(1, (t - bas) / 1200), k = 1 - Math.pow(1 - o, 3);
      el.textContent = o < 1 ? Math.round(son * k).toLocaleString("tr-TR") + m[2] : asil;
      if (o < 1) requestAnimationFrame(adim);
    };
    requestAnimationFrame(adim);
  };

  // Bölümler ekrana girerken aşağıdan süzülerek gelir; aynı satırdakiler sırayla.
  // JS yoksa ya da hareket azaltılmışsa hiçbir şey gizlenmez.
  if (!azalt && "IntersectionObserver" in window) {
    var secici = ".bolum h2, .bolum .bolum-alt, .oyunlar > *, .adimlar > li, .maddeler > li, #sss details, .kartlar > .kart, " +
      ".kars-gorsel, .kars-satirlar > li, .istek-seridi, .detay-metin, .galeri > figure, .rakam-listesi > li";
    var gozcu = new IntersectionObserver(function (girdiler) {
      girdiler.forEach(function (g) {
        if (!g.isIntersecting) return;
        var el = g.target;
        gozcu.unobserve(el);
        el.classList.add("gorundu");
        var sayi = el.querySelector(".rakam-deger");
        if (sayi) say(sayi);
        // Belirme bitince sınıflar kalkar; kartların kendi hover efektleri karışmasın.
        setTimeout(function () {
          el.classList.remove("gizle-belir", "gorundu");
          el.style.removeProperty("--gecikme");
        }, 1400);
      });
    }, { rootMargin: "0px 0px -6% 0px", threshold: 0.08 });
    Array.prototype.slice.call(document.querySelectorAll(secici)).forEach(function (el) {
      if (el.closest(".giris") || el.parentNode.closest(".gizle-belir")) return;
      var kardesler = Array.prototype.slice.call(el.parentNode.children);
      var sira = Math.min(kardesler.indexOf(el), 6);
      el.style.setProperty("--gecikme", sira * 0.07 + "s");
      el.classList.add("gizle-belir");
      gozcu.observe(el);
    });
  }

  // --- Orijinali ve Türkçesi: sekmeler ---------------------------------------
  // JS yoksa bütün paneller alt alta görünür; JS varsa sekmeyle biri seçilir.
  var karsSekmeler = document.querySelector("[data-kars-sekmeler]");
  if (karsSekmeler) {
    var sekmeler = Array.prototype.slice.call(karsSekmeler.querySelectorAll("[role=tab]"));
    var sec = function (sekme, odakla) {
      sekmeler.forEach(function (s) {
        var bu = s === sekme;
        s.setAttribute("aria-selected", bu ? "true" : "false");
        s.tabIndex = bu ? 0 : -1;
        document.getElementById(s.getAttribute("aria-controls")).hidden = !bu;
      });
      if (odakla) sekme.focus();
    };
    karsSekmeler.hidden = false;
    sec(sekmeler[0], false);
    sekmeler.forEach(function (s, i) {
      s.addEventListener("click", function () { sec(s, false); });
      s.addEventListener("keydown", function (e) {
        var yon = e.key === "ArrowRight" ? 1 : e.key === "ArrowLeft" ? -1 : 0;
        if (!yon) return;
        e.preventDefault();
        sec(sekmeler[(i + yon + sekmeler.length) % sekmeler.length], true);
      });
    });
  }

  // --- Görsel büyütücü ------------------------------------------------------
  var kutu = document.querySelector(".buyutec");
  if (!kutu || typeof kutu.showModal !== "function") return;
  var resim = kutu.querySelector("img");
  var yazi = kutu.querySelector("figcaption");
  var sayac = kutu.querySelector(".buyutec-sayac");
  var onceki = kutu.querySelector(".onceki");
  var sonraki = kutu.querySelector(".sonraki");
  var liste = [];
  var sira = 0;

  function goster() {
    var img = liste[sira];
    resim.src = img.dataset.buyuk || img.currentSrc || img.src;
    resim.alt = img.alt;
    var fc = img.closest("figure") && img.closest("figure").querySelector("figcaption");
    yazi.textContent = fc ? fc.textContent : img.alt;
    var cok = liste.length > 1;
    onceki.hidden = sonraki.hidden = !cok;
    sayac.textContent = cok ? sira + 1 + " / " + liste.length : "";
  }

  function ac(img) {
    var grup = img.closest("[data-galeri]");
    liste = grup ? Array.prototype.slice.call(grup.querySelectorAll("img")) : [img];
    sira = Math.max(0, liste.indexOf(img));
    goster();
    kutu.showModal();
    document.body.classList.add("kilitli");
  }

  function git(adim) {
    if (liste.length < 2) return;
    sira = (sira + adim + liste.length) % liste.length;
    goster();
  }

  Array.prototype.slice.call(document.querySelectorAll(".giris-gorsel img, [data-galeri] img")).forEach(function (img) {
    img.classList.add("buyutulebilir");
    img.tabIndex = 0;
    img.setAttribute("role", "button");
    img.setAttribute("aria-label", "Büyüt: " + img.alt);
    img.addEventListener("click", function (e) { e.stopPropagation(); ac(img); });
    img.addEventListener("keydown", function (e) {
      if (e.key === "Enter" || e.key === " ") { e.preventDefault(); ac(img); }
    });
  });

  onceki.addEventListener("click", function (e) { e.stopPropagation(); git(-1); });
  sonraki.addEventListener("click", function (e) { e.stopPropagation(); git(1); });
  kutu.querySelector(".buyutec-kapat").addEventListener("click", function () { kutu.close(); });
  // Görselin dışına (karanlık alana) tıklayınca kapanır.
  kutu.addEventListener("click", function (e) {
    if (e.target === kutu || e.target.tagName === "FIGURE") kutu.close();
  });
  kutu.addEventListener("close", function () { document.body.classList.remove("kilitli"); });
  kutu.addEventListener("keydown", function (e) {
    if (e.key === "ArrowRight") { e.preventDefault(); git(1); }
    if (e.key === "ArrowLeft") { e.preventDefault(); git(-1); }
  });

  // Telefonda kaydırarak geçiş.
  var basX = null;
  kutu.addEventListener("touchstart", function (e) { basX = e.touches[0].clientX; }, { passive: true });
  kutu.addEventListener("touchend", function (e) {
    if (basX === null) return;
    var fark = e.changedTouches[0].clientX - basX;
    basX = null;
    if (Math.abs(fark) > 50) git(fark < 0 ? 1 : -1);
  }, { passive: true });
})();

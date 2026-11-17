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
    resim.src = img.currentSrc || img.src;
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

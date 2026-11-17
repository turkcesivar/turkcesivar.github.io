// Türkçesi Var sitesi: oyun ayrıntı sekmeleri ve görsel büyütücü. Kütüphane yok.
(function () {
  "use strict";
  document.documentElement.classList.add("js");

  // --- Oyun sekmeleri -------------------------------------------------------
  var sekmeler = Array.prototype.slice.call(document.querySelectorAll('.sekmeler [role="tab"]'));
  var paneller = Array.prototype.slice.call(document.querySelectorAll(".detay"));
  var kimlikler = paneller.map(function (p) { return p.id; });

  function oyunSec(kimlik, odakla) {
    if (kimlikler.indexOf(kimlik) < 0) kimlik = kimlikler[0];
    paneller.forEach(function (p) { p.hidden = p.id !== kimlik; });
    sekmeler.forEach(function (s) {
      var secili = s.dataset.oyun === kimlik;
      s.setAttribute("aria-selected", secili ? "true" : "false");
      s.tabIndex = secili ? 0 : -1;
      if (secili && odakla) s.focus();
    });
  }

  function bolumeGit(kimlik) {
    oyunSec(kimlik);
    if (history.replaceState) history.replaceState(null, "", "#" + kimlik);
    document.getElementById("oyunun-icinden").scrollIntoView({ behavior: "smooth", block: "start" });
  }

  sekmeler.forEach(function (s, i) {
    s.addEventListener("click", function () {
      oyunSec(s.dataset.oyun);
      if (history.replaceState) history.replaceState(null, "", "#" + s.dataset.oyun);
    });
    s.addEventListener("keydown", function (e) {
      var yon = e.key === "ArrowRight" ? 1 : e.key === "ArrowLeft" ? -1 : 0;
      if (!yon) return;
      e.preventDefault();
      var hedef = sekmeler[(i + yon + sekmeler.length) % sekmeler.length];
      oyunSec(hedef.dataset.oyun, true);
    });
  });

  // Kartın tamamı tıklanabilir; içindeki gerçek bağlantılar kendi işini yapar.
  Array.prototype.slice.call(document.querySelectorAll(".oyun")).forEach(function (kart) {
    var ac = kart.querySelector(".oyun-ac");
    if (!ac) return;
    kart.classList.add("tiklanir");
    kart.addEventListener("click", function (e) {
      if (e.target.closest("a") && e.target.closest("a") !== ac) return;
      e.preventDefault();
      bolumeGit(ac.dataset.oyun);
    });
  });

  var ilk = location.hash.slice(1);
  oyunSec(kimlikler.indexOf(ilk) >= 0 ? ilk : kimlikler[0]);
  if (kimlikler.indexOf(ilk) >= 0) {
    // Sayfa doğrudan #metro-2033 gibi bir adresle açıldıysa bölüme in.
    setTimeout(function () { document.getElementById("oyunun-icinden").scrollIntoView(); }, 0);
  }
  window.addEventListener("hashchange", function () {
    var h = location.hash.slice(1);
    if (kimlikler.indexOf(h) >= 0) bolumeGit(h);
  });

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

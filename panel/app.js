/* E-ticaret paneli v2 — tek sayfa uygulama (derleme yok). Veriler /api/* uçlarından gelir. */
"use strict";
const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[c]));
const tl = (x, k = 0) => x == null || !isFinite(x) ? "–" : Number(x).toLocaleString("tr-TR", {minimumFractionDigits: k, maximumFractionDigits: k}) + " ₺";
const yuzde = (x, k = 1) => x == null || !isFinite(x) ? "–" : "%" + Number(x).toLocaleString("tr-TR", {maximumFractionDigits: k});
const sayi = (x, k = 0) => x == null || !isFinite(x) ? "–" : Number(x).toLocaleString("tr-TR", {maximumFractionDigits: k});
const tarih = s => s ? new Date(s).toLocaleString("tr-TR", {day: "numeric", month: "short", hour: "2-digit", minute: "2-digit"}) : "–";
const gun = s => s ? new Date(s).toLocaleDateString("tr-TR", {day: "numeric", month: "long", weekday: "long"}) : "–";
const md = t => { try { return DOMPurify.sanitize(marked.parse(t || "")); } catch (e) { return `<pre>${esc(t)}</pre>`; } };
const json = o => esc(JSON.stringify(o));
/* Karar dili: kullanıcıya "Olur / Belki / Olmaz" — içteki adlar (TESTE AL…) sadece ipucunda */
const KARAR = {"TESTE AL": {ad: "Olur", c: "ok", i: "✓"}, "İYİLEŞTİR": {ad: "Belki", c: "warn", i: "~"},
               "ELE": {ad: "Olmaz", c: "bad", i: "✕"}, "EKSİK VERİ": {ad: "Veri eksik", c: "gri", i: "?"}};
const karar = (k, buyuk = false) => { const x = KARAR[k]; return x ? `<span class="karar ${x.c} ${buyuk ? "buyuk" : ""}" data-ipucu="Sistem kararı: ${esc(k)}"><i>${x.i}</i>${x.ad}</span>` : ""; };
const kararRenk = k => ({ok: "var(--ok)", warn: "var(--warn)", bad: "var(--bad)", gri: "var(--soft)"})[(KARAR[k] || {}).c || "gri"];
function miniHalka(p, en = 20, boy = 42) {
  const r = boy / 2 - 4, c = 2 * Math.PI * r, o = Math.max(0, Math.min(1, (p || 0) / en));
  const renk = p >= 15 ? "var(--ok)" : p >= 10 ? "var(--warn)" : "var(--bad)";
  return `<div class="mini-halka" style="width:${boy}px;height:${boy}px" data-ipucu="20 puanlık skor kartı: ${p ?? "–"}/20">
    <svg viewBox="0 0 ${boy} ${boy}" width="${boy}" height="${boy}"><circle cx="${boy / 2}" cy="${boy / 2}" r="${r}" fill="none" stroke="var(--line)" stroke-width="4"/>
    <circle cx="${boy / 2}" cy="${boy / 2}" r="${r}" fill="none" stroke="${renk}" stroke-width="4" stroke-linecap="round" stroke-dasharray="${c * o} ${c}" transform="rotate(-90 ${boy / 2} ${boy / 2})"/></svg>
    <b>${p ?? "–"}</b></div>`;
}
/* Tek cümlelik neden: kullanıcı kartta sadece bunu okur */
function neden(a) {
  if (a.yuksek_risk) return {c: "bad", t: `${a.yuksek_risk} yüksek risk (marka, sağlık ya da kargo)`};
  if (a.karar === "EKSİK VERİ") return {c: "gri", t: "Yapay zekâ puanlayamadı, yeniden puanla"};
  if (a.benzer_yok) return {c: "info", t: "Trendyol'da aynısı yok: fiyat doğrulanamadı"};
  const u = uyum(a);
  if (u != null && u > 1) return {c: u > 1.6 ? "bad" : "warn", t: `Kâr için ${tl(a.min_fiyat)} lazım, piyasa ${tl(a.rakip_medyan)}`};
  if (u != null) return {c: "ok", t: `Piyasa fiyatında kârlı (net ${yuzde(a.piyasa_marj, 0)})`};
  return {c: "gri", t: "Rakip fiyatı yok"};
}
const NEDEN_IK = {ok: `<svg viewBox="0 0 24 24" fill="none" stroke="var(--ok)" stroke-width="2.4"><path d="M5 12l5 5 9-10"/></svg>`,
  warn: `<svg viewBox="0 0 24 24" fill="none" stroke="var(--warn)" stroke-width="2.4"><path d="M12 8v5M12 17h.01"/><circle cx="12" cy="12" r="9"/></svg>`,
  bad: `<svg viewBox="0 0 24 24" fill="none" stroke="var(--bad)" stroke-width="2.4"><path d="M7 7l10 10M17 7 7 17"/></svg>`,
  info: `<svg viewBox="0 0 24 24" fill="none" stroke="var(--info)" stroke-width="2.4"><circle cx="12" cy="12" r="9"/><path d="M12 11v5M12 8h.01"/></svg>`,
  gri: `<svg viewBox="0 0 24 24" fill="none" stroke="var(--soft)" stroke-width="2.4"><circle cx="12" cy="12" r="9"/><path d="M9.5 9a2.5 2.5 0 1 1 3.5 2.3c-.6.3-1 .8-1 1.5V14M12 17h.01"/></svg>`};
/* Fiyat uyum çubuğu: gereken fiyat ↔ piyasa medyanı (siyah çizgi) */
function uyumCubuk(a) {
  if (!a.min_fiyat || !a.rakip_medyan) return "";
  const ust = Math.max(a.min_fiyat, a.rakip_medyan) * 1.12, x = v => Math.min(100, v / ust * 100);
  const renk = a.min_fiyat <= a.rakip_medyan ? "var(--ok)" : a.min_fiyat / a.rakip_medyan > 1.6 ? "var(--bad)" : "var(--warn)";
  return `<div class="uyum" data-ipucu="Turuncu/yeşil: %20 kâr için gereken fiyat ${tl(a.min_fiyat)} · çizgi: piyasa medyanı ${tl(a.rakip_medyan)}">
    <i style="width:${x(a.min_fiyat)}%;background:${renk}"></i><span class="medyan" style="left:${x(a.rakip_medyan)}%"></span></div>`;
}
/* Basit ipucu katmanı: data-ipucu taşıyan her öğe */
(() => {
  let el = null;
  document.addEventListener("mouseover", e => {
    const h = e.target.closest("[data-ipucu]"); if (!h) return;
    el = el || Object.assign(document.createElement("div"), {className: "ipucu"}); document.body.append(el);
    el.textContent = h.dataset.ipucu; el.hidden = false;
  });
  document.addEventListener("mousemove", e => { if (el && !el.hidden) { el.style.left = Math.min(innerWidth - 270, e.clientX + 14) + "px"; el.style.top = (e.clientY + 16) + "px"; } });
  document.addEventListener("mouseout", e => { if (el && e.target.closest("[data-ipucu]") && !e.relatedTarget?.closest?.("[data-ipucu]")) el.hidden = true; });
})();
/* Tema seçici */
function temaYaz() {
  const t = document.documentElement.dataset.theme === "dark" ? "dark" : "light";
  document.querySelectorAll("[data-tema]").forEach(b => b.classList.toggle("aktif", b.dataset.tema === t));
}
document.addEventListener("click", e => {
  const b = e.target.closest("[data-tema]"); if (!b) return;
  if (b.dataset.tema === "dark") document.documentElement.dataset.theme = "dark"; else delete document.documentElement.dataset.theme;
  try { localStorage.setItem("tema", b.dataset.tema); } catch (er) {}
  temaYaz();
});
temaYaz();
const DURUM = {tamam: ["Tamam", "r-ok"], onaylandi: ["Onaylandı", "r-ok"], onay_bekliyor: ["Onay bekliyor", "r-warn"], hazir: ["Çalıştırılabilir", "r-info"], kilitli: ["Sırada", "r-gri"]};
const RISK = {yuksek: ["Yüksek", "r-bad"], orta: ["Orta", "r-warn"], dusuk: ["Düşük", "r-ok"], bilgi: ["Bilgi", "r-gri"]};
const IK = {
  onay: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 12l2 2 4-4"/><circle cx="12" cy="12" r="9"/></svg>`,
  oynat: `<svg viewBox="0 0 24 24" fill="currentColor"><path d="M8 5v14l11-7z"/></svg>`,
  yildiz: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m12 3 2.7 5.6 6.1.9-4.4 4.3 1 6.1L12 17l-5.4 2.9 1-6.1L3.2 9.5l6.1-.9z"/></svg>`,
  yildizd: `<svg viewBox="0 0 24 24" fill="currentColor"><path d="m12 3 2.7 5.6 6.1.9-4.4 4.3 1 6.1L12 17l-5.4 2.9 1-6.1L3.2 9.5l6.1-.9z"/></svg>`,
  ara: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></svg>`,
  dis: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 4h6v6M20 4l-9 9M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5"/></svg>`,
};

async function api(yol, ayar = {}) {
  const govde = ayar.body && !(ayar.body instanceof FormData);
  const r = await fetch(yol, {headers: govde ? {"Content-Type": "application/json"} : {}, ...ayar});
  const v = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(v.detail || "İstek başarısız");
  return v;
}
const post = (yol, veri, yontem = "POST") => api(yol, {method: yontem, body: JSON.stringify(veri || {})});
function bildir(m, sure = 3400) {
  const d = document.createElement("div"); d.className = "bildirim"; d.textContent = m; document.body.append(d);
  setTimeout(() => d.remove(), sure);
}
function modal(html, o = {}) {
  const arka = document.createElement("div"); arka.className = "modal-arka";
  arka.innerHTML = `<div class="modal" style="${o.genis ? "max-width:880px" : ""}">${html}</div>`;
  arka.addEventListener("mousedown", e => { if (e.target === arka || e.target.closest("[data-kapat]")) arka.remove(); });
  document.body.append(arka);
  return arka;
}
function cekmece(html) {
  cekmeceKapat();
  const a = document.createElement("div"); a.className = "cekmece-arka"; a.onclick = cekmeceKapat;
  const c = document.createElement("aside"); c.className = "cekmece"; c.innerHTML = html;
  document.body.append(a, c);
  document.addEventListener("keydown", escKapat);
  return c;
}
function cekmeceKapat() { $$(".cekmece,.cekmece-arka").forEach(x => x.remove()); document.removeEventListener("keydown", escKapat); }
function escKapat(e) { if (e.key === "Escape") cekmeceKapat(); }
const yolCiz = parcalar => $("#yol").innerHTML = parcalar.map((p, i) => i === parcalar.length - 1 ? `<b>${esc(p)}</b>` : `<span>${esc(p)}</span><span class="soft">/</span>`).join("");

/* ---------------------------------------------------------------- yönlendirme */
let OZET = null;
window.addEventListener("hashchange", ciz);
$$("[data-git]").forEach(b => b.onclick = () => location.hash = b.dataset.git);
const git = h => location.hash = h;

async function ozetYukle() {
  OZET = await api("/api/ozet");
  $("#yanProjeler").innerHTML = OZET.projeler.map(p =>
    `<button class="men" data-proje="${esc(p.ad)}" onclick="git('proje/${esc(p.ad)}')"><span>${esc(p.marka || p.ad)}</span>
      ${p.onay_bekleyen.length ? `<span class="rozet r-warn">${p.onay_bekleyen.length}</span>` : ""}</button>`).join("")
    || `<div class="k soft" style="padding:4px 10px">Henüz proje yok</div>`;
  const g = OZET.gorevler.length, a = OZET.adaylar.length;
  $("#rzGorev").hidden = !g; $("#rzGorev").textContent = g;
  $("#rzAday").hidden = !a; $("#rzAday").textContent = a;
  return OZET;
}

async function ciz() {
  cekmeceKapat();                       // sayfa değişince açık ürün paneli kapansın
  const [sayfa, arg, arg2] = (location.hash.slice(1) || "ana").split("/");
  $$(".men").forEach(m => m.classList.toggle("aktif", m.dataset.git === sayfa || (sayfa === "proje" && m.dataset.proje === arg)));
  const ana = $("#ana");
  try {
    const f = {ana: anaSayfa, kesif: kesifSayfa, tarama: taramaSayfa, projeler: projelerSayfa, hesap: hesapSayfa,
               ayarlar: ayarlarSayfa, proje: projeSayfa, sinyal: sinyalSayfa, magaza: magazaSayfa}[sayfa] || anaSayfa;
    await f(ana, arg && decodeURIComponent(arg), arg2);
  } catch (e) {
    console.error(e);
    ana.innerHTML = `<div class="kart bos"><b>Yüklenemedi</b>${esc(e.message)}</div>`;
  }
}

/* ---------------------------------------------------------------- ana sayfa */
async function anaSayfa(ana) {
  yolCiz(["Ana sayfa"]);
  const o = await ozetYukle();
  const kd = o.karar_dagilimi, ap = o.apify, apY = ap.harcanan != null ? Math.min(100, ap.harcanan / ap.butce * 100) : 0;
  const saat = new Date().getHours(), selam = saat < 12 ? "Günaydın" : saat < 18 ? "İyi günler" : "İyi akşamlar";
  const dag = [["TESTE AL", kd["TESTE AL"]], ["İYİLEŞTİR", kd["İYİLEŞTİR"]], ["EKSİK VERİ", kd["EKSİK VERİ"]], ["ELE", kd["ELE"]]].filter(x => x[1]);
  const top = dag.reduce((t, x) => t + x[1], 0) || 1;
  const onay = o.gorevler.filter(g => g.tur === "onay").length;
  const enIyi = [...o.adaylar].sort((x, y) => (y.puan ?? 0) - (x.puan ?? 0)).slice(0, 4);
  const asamaSay = Object.fromEntries(o.asamalar.map(([k]) => [k, o.projeler.filter(p => p.asama === k)]));
  ana.innerHTML = `
  <div class="bas-sayfa"><div><h1>${selam}</h1><p>${gun(new Date())} · ${o.gorevler.length ? `<b style="color:var(--text)">${o.gorevler.length} iş</b> seni bekliyor` : "bekleyen iş yok"}</p></div>
    <button class="btn ana" onclick="yeniArastirma()">+ Ürün incele</button></div>
  <div class="izgara g4">
    <div class="kart kpi"><div class="e">Aday havuzu</div><div class="d">${o.arastirma_sayisi}</div>
      <div class="yigin ince" style="margin-top:12px">${dag.map(([k, n]) => `<i style="width:${n / top * 100}%;background:${kararRenk(k)}" data-ipucu="${KARAR[k].ad}: ${n} ürün"></i>`).join("")}</div>
      <div class="lejant" style="margin-top:8px">${dag.map(([k, n]) => `<span><i style="background:${kararRenk(k)}"></i>${KARAR[k].ad} ${n}</span>`).join("")}</div></div>
    <div class="kart kpi"><div class="e">“Olur” çıkan ürün</div><div class="d" style="color:${kd["TESTE AL"] ? "var(--ok)" : "inherit"}">${kd["TESTE AL"]}</div>
      <div class="a">${kd["TESTE AL"] ? "teste hazır, projeye çevir" : "henüz yok · toptan fiyat gerekiyor"}</div></div>
    <div class="kart kpi"><div class="e">Aktif proje</div><div class="d">${o.projeler.length}</div>
      <div class="a">${onay ? `<span style="color:var(--warn);font-weight:600">${onay} onay bekliyor</span>` : "onay bekleyen yok"}</div></div>
    <div class="kart kpi"><div class="e">Apify bütçesi</div><div class="d">$${(ap.harcanan ?? 0).toFixed(2)}<span class="soft" style="font-size:15px;font-weight:600"> / ${ap.butce}</span></div>
      <div class="gauge" style="margin-top:12px" data-ipucu="Bu ay harcanan: %${apY.toFixed(0)}"><i style="width:${apY}%;background:${apY > 80 ? "var(--bad)" : apY > 60 ? "var(--warn)" : "var(--ok)"}"></i></div></div>
  </div>
  <div class="kart" style="margin-top:16px"><div class="kart-bas"><h3>En iyi adaylar</h3><button class="btn kucuk hayalet" onclick="git('kesif')">Tümü →</button></div>
    <div class="kart-ic">${enIyi.length ? `<div class="urunler">${enIyi.map(urunKart).join("")}</div>`
      : `<div class="bos"><b>Henüz aday yok</b>Günlük tarama her sabah yeni ürün ekler.</div>`}</div></div>
  <div class="izgara g21" style="margin-top:16px">
    <div class="kart"><div class="kart-bas"><h3>Yapılacaklar</h3><span class="k soft">${o.gorevler.length}</span></div>
      <div style="margin-top:6px">${o.gorevler.length ? o.gorevler.slice(0, 6).map(gorevSatir).join("") :
        `<div class="bos" style="padding:28px"><b>Her şey yolunda</b>Bekleyen onay ya da adım yok.</div>`}</div></div>
    <div class="kart"><div class="kart-bas"><h3>Günlük tarama</h3><button class="btn kucuk hayalet" onclick="git('tarama')">Yönet →</button></div>
      <div class="kart-ic">
        <div class="liste-li"><span class="muted ara">Sonraki</span><b>${o.gorev ? tarih(o.gorev.sonraki) : "görev yok"}</b></div>
        <div class="liste-li"><span class="muted ara">Son</span><b>${tarih(o.gunluk.son)}</b></div>
        <div class="liste-li"><span class="muted ara">Sıradaki kelime</span><b class="tek" style="max-width:60%">${esc(o.gunluk.sonraki_kelime || "–")}</b></div>
      </div></div>
  </div>
  <div class="kart" style="margin-top:16px"><div class="kart-bas"><h3>Satış hattı</h3><button class="btn kucuk hayalet" onclick="git('projeler')">Pano →</button></div>
    <div class="kart-ic"><div class="hat">${o.asamalar.map(([k, ad]) => `<div class="a ${asamaSay[k].length ? "dolu" : ""}"><div class="y">${asamaSay[k].length}</div><span>${ad}</span>
      ${asamaSay[k].slice(0, 1).map(p => `<div class="p tek" onclick="git('proje/${esc(p.ad)}')">${esc(p.marka || p.ad)}</div>`).join("")}</div>`).join("")}</div></div></div>`;
}
function gorevSatir(g) {
  const ayar = {onay: ["r-warn", IK.onay, `git('proje/${g.proje}')`, "Kontrol et"], hazir: ["r-info", IK.oynat, `git('proje/${g.proje}')`, "Aç"],
                aday: ["r-ok", IK.yildiz, `adayAc('${g.json}')`, "İncele"]}[g.tur];
  return `<div class="gorev"><div class="ik rozet ${ayar[0]}" style="padding:0">${ayar[1]}</div>
    <div class="ara"><div style="font-weight:600">${esc(g.metin)}</div><div class="k muted tek">${esc(g.marka)}</div></div>
    <button class="btn kucuk" onclick="${ayar[2]}">${ayar[3]}</button></div>`;
}

/* ---------------------------------------------------------------- ürün keşfi */
const FILTRE = {karar: "hepsi", ara: "", sira: "tarih", fav: false, red: false};
let ADAYLAR = [];
let GORUNUM = "kart";
try { GORUNUM = localStorage.getItem("kesifGorunum") || "kart"; } catch (e) {}
async function kesifSayfa(ana) {
  yolCiz(["Ürün", "Ürün keşfi"]);
  await ozetYukle();
  ADAYLAR = await api("/api/arastirmalar");
  const say = k => ADAYLAR.filter(a => a.karar === k && a.isaret !== "red").length;
  ana.innerHTML = `
  <div class="bas-sayfa"><div><h1>Ürün keşfi</h1><p>${ADAYLAR.length} ürün incelendi · ${say("TESTE AL")} olur, ${say("İYİLEŞTİR")} belki</p></div>
    <button class="btn ana" onclick="yeniArastirma()">+ Ürün incele</button></div>
  <div class="flex sarma" style="gap:8px;margin-bottom:16px">
    <div style="position:relative;flex:1;min-width:200px;max-width:320px"><input id="fAra" placeholder="Ürün ara…" value="${esc(FILTRE.ara)}" style="padding-left:34px">
      <span style="position:absolute;left:11px;top:10px;width:15px;color:var(--soft)">${IK.ara}</span></div>
    ${["hepsi", "TESTE AL", "İYİLEŞTİR", "EKSİK VERİ", "ELE"].map(k => `<button class="cip ${FILTRE.karar === k ? "aktif" : ""}" data-karar="${k}">
      ${k === "hepsi" ? "Tümü" : `<span class="nokta" style="color:${kararRenk(k)}"></span>${KARAR[k].ad}`}
      <span style="opacity:.6">${k === "hepsi" ? ADAYLAR.length : ADAYLAR.filter(a => a.karar === k).length}</span></button>`).join("")}
    <span class="ara"></span>
    <button class="cip ${FILTRE.fav ? "aktif" : ""}" id="fFav">★ Favoriler</button>
    <select id="fSira" style="width:auto"><option value="tarih">En yeni</option><option value="puan">En yüksek puan</option><option value="uyum">Piyasaya en yakın</option></select>
    <div class="segment"><button data-gor="kart" class="${GORUNUM === "kart" ? "aktif" : ""}" data-ipucu="Kart görünümü"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/></svg></button>
      <button data-gor="tablo" class="${GORUNUM === "tablo" ? "aktif" : ""}" data-ipucu="Tablo görünümü"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 6h18M3 12h18M3 18h18"/></svg></button></div>
  </div>
  <div id="adayTablo"></div>
  <div class="k soft" style="margin-top:14px"><label class="kutu-sec" style="display:inline-flex"><input type="checkbox" id="fRed" ${FILTRE.red ? "checked" : ""}> Reddettiklerimi de göster</label></div>`;
  $("#fSira").value = FILTRE.sira === "marj" ? "uyum" : FILTRE.sira;
  $("#fAra").oninput = e => { FILTRE.ara = e.target.value; adayTabloCiz(); };
  $$("[data-karar]").forEach(b => b.onclick = () => { FILTRE.karar = b.dataset.karar; kesifSayfa(ana); });
  $("#fFav").onclick = () => { FILTRE.fav = !FILTRE.fav; kesifSayfa(ana); };
  $("#fRed").onchange = e => { FILTRE.red = e.target.checked; adayTabloCiz(); };
  $("#fSira").onchange = e => { FILTRE.sira = e.target.value; adayTabloCiz(); };
  $$("[data-gor]").forEach(b => b.onclick = () => { GORUNUM = b.dataset.gor; try { localStorage.setItem("kesifGorunum", GORUNUM); } catch (e) {} kesifSayfa(ana); });
  adayTabloCiz();
}
const uyum = a => a.min_fiyat && a.rakip_medyan ? a.min_fiyat / a.rakip_medyan : null;
function adayTabloCiz() {
  let l = ADAYLAR.filter(a => (FILTRE.karar === "hepsi" || a.karar === FILTRE.karar)
    && (!FILTRE.ara || (a.baslik || "").toLowerCase().includes(FILTRE.ara.toLowerCase()))
    && (!FILTRE.fav || a.isaret === "favori") && (FILTRE.red ? true : a.isaret !== "red"));
  const s = {puan: a => -(a.puan ?? -1), marj: a => -(a.piyasa_marj ?? -999), uyum: a => uyum(a) ?? 99, tarih: a => -new Date(a.tarih || 0)}[FILTRE.sira];
  l = l.sort((x, y) => s(x) - s(y));
  $("#adayTablo").innerHTML = !l.length ? `<div class="kart bos"><b>Eşleşen ürün yok</b>Filtreleri değiştir ya da yeni bir ürün incele.</div>`
    : GORUNUM === "tablo" ? `<div class="kart tablo-k">${adayTablo(l)}</div>` : `<div class="urunler">${l.map(urunKart).join("")}</div>`;
}
function urunKart(a) {
  const n = neden(a);
  return `<div class="uk" onclick="adayAc('${esc(a.json)}')">
    <div class="gorsel"><img src="${esc(a.gorsel || "")}" alt="" loading="lazy" referrerpolicy="no-referrer" onerror="gorselHata(this)">${karar(a.karar)}
      <button class="yildiz ${a.isaret === "favori" ? "on" : ""}" data-ipucu="${a.isaret === "favori" ? "Favoriden çıkar" : "Favorilere ekle"}"
        onclick="event.stopPropagation();isaretle('${a.id}','${a.isaret === "favori" ? "" : "favori"}')">${a.isaret === "favori" ? IK.yildizd : IK.yildiz}</button></div>
    <div class="govde">
      <div class="baslik iki-satir">${esc(a.baslik)}</div>
      <div class="rakam">${miniHalka(a.puan)}
        <div><small>Piyasa</small><b>${a.benzer_yok ? "—" : tl(a.rakip_medyan)}</b></div>
        <div><small>Gereken</small><b>${tl(a.min_fiyat)}</b></div></div>
      ${uyumCubuk(a)}
      <div class="neden">${NEDEN_IK[n.c] || NEDEN_IK.gri}<span>${esc(n.t)}</span></div>
      ${a.proje ? `<div><span class="rozet r-mor">proje: ${esc(a.proje)}</span></div>` : ""}
    </div></div>`;
}
function adayTablo(l, kisa = false) {
  return `<table class="tablo"><thead><tr><th>Ürün</th><th>Karar</th><th class="sayi">Birim maliyet</th><th class="sayi">%20 marj için</th>
    <th class="sayi">Piyasa medyanı</th><th>Fiyat uyumu</th>${kisa ? "" : "<th>Risk</th><th>Tarih</th>"}<th></th></tr></thead><tbody>
  ${l.map(a => {
    const u = uyum(a);
    const uy = a.benzer_yok ? `<span class="rozet r-info" title="Trendyol aramasında aynı tür ürün bulunamadı; fiyat piyasayla doğrulanamadı">Piyasada aynısı yok</span>`
      : u == null ? `<span class="rozet r-gri">Rakip verisi yok</span>` : u <= 1 ? `<span class="rozet r-ok">Piyasaya uygun</span>`
      : `<span class="rozet ${u <= 1.3 ? "r-warn" : "r-bad"}">Piyasanın ${yuzde((u - 1) * 100, 0)} üstü</span>`;
    return `<tr onclick="adayAc('${esc(a.json)}')">
      <td><div class="urun-h"><img src="${esc(a.gorsel || "")}" alt="" loading="lazy" referrerpolicy="no-referrer" onerror="gorselHata(this)"><div style="min-width:0">
        <div class="iki-satir" style="font-weight:550">${esc(a.baslik)}</div>
        <div class="k soft">${a.isaret === "favori" ? "★ favori · " : a.isaret === "red" ? "reddedildi · " : ""}${a.proje ? `<span class="rozet r-mor">proje: ${esc(a.proje)}</span>` : ""}</div></div></div></td>
      <td><div class="puan-c">${karar(a.karar)}${miniHalka(a.puan, 20, 34)}</div></td>
      <td class="sayi">${tl(a.maliyet)}</td><td class="sayi"><b>${tl(a.min_fiyat)}</b></td><td class="sayi">${tl(a.rakip_medyan)}</td><td>${uy}</td>
      ${kisa ? "" : `<td>${a.yuksek_risk ? `<span class="rozet r-bad">${a.yuksek_risk} yüksek risk</span>` : a.kargo_riski && a.kargo_riski !== "dusuk" ? `<span class="rozet ${RISK[a.kargo_riski][1]}">kargo ${RISK[a.kargo_riski][0].toLowerCase()}</span>` : `<span class="soft k">–</span>`}</td>
      <td class="k muted" style="white-space:nowrap">${tarih(a.tarih)}</td>`}
      <td style="text-align:right"><button class="btn kucuk hayalet" title="Favori" onclick="event.stopPropagation();isaretle('${a.id}','${a.isaret === "favori" ? "" : "favori"}')" style="color:${a.isaret === "favori" ? "var(--warn)" : "var(--soft)"}">${a.isaret === "favori" ? IK.yildizd : IK.yildiz}</button></td></tr>`;
  }).join("")}</tbody></table>`;
}
async function isaretle(id, isaret) {
  await post("/api/aday-isaret/" + id, {isaret: isaret || null});
  const a = ADAYLAR.find(x => x.id === id); if (a) a.isaret = isaret || null;
  if ($("#adayTablo")) adayTabloCiz(); else ciz();
}

/* aday çekmecesi */
let ADAY = null, ASEKME = "ozet";
async function adayAc(ad) {
  const c = cekmece(`<div class="c-ic" style="padding:20px"><div class="iskelet"></div></div>`);
  try { ADAY = await api("/api/aday/" + encodeURIComponent(ad)); } catch (e) { c.innerHTML = `<div class="bos">${esc(e.message)}</div>`; return; }
  ASEKME = "ozet"; adayCiz();
}
function adayCiz() {
  const a = ADAY, c = $(".cekmece"); if (!c) return;
  const tab = [["ozet", "Özet"], ["fiyat", "Fiyat & kâr"], ["pazar", "Pazar"], ["risk", `Riskler${a.riskler?.length ? ` (${a.riskler.length})` : ""}`]];
  c.innerHTML = `
  <div class="c-bas"><img src="${esc(a.gorsel || "")}" alt="" referrerpolicy="no-referrer" onerror="gorselHata(this)">
    <div class="ara"><div class="flex sarma" style="gap:6px">${a.proje ? `<span class="rozet r-mor">proje: ${esc(a.proje)}</span>` : ""}${a.isaret === "red" ? `<span class="rozet r-bad">reddedildi</span>` : ""}${a.isaret === "favori" ? `<span class="rozet r-warn">★ favori</span>` : ""}</div>
      <div style="font-weight:650;margin-top:4px" class="iki-satir">${esc(a.baslik)}</div>
      <div class="k muted"><a href="${esc(a.link)}" target="_blank" rel="noopener">AliExpress'te aç ↗</a> · ${tarih(a.tarih)}</div></div>
    <button class="btn hayalet" onclick="cekmeceKapat()" style="align-self:flex-start">✕</button></div>
  <div style="padding:0 20px"><div class="sekmeler">${tab.map(([k, ad]) => `<button class="sekme ${ASEKME === k ? "aktif" : ""}" onclick="ASEKME='${k}';adayCiz()">${ad}</button>`).join("")}</div></div>
  <div class="c-ic">${{ozet: adayOzet, fiyat: adayFiyat, pazar: adayPazar, risk: adayRisk}[ASEKME](a)}</div>
  <div class="c-alt">
    ${a.proje ? `<button class="btn ana" onclick="cekmeceKapat();git('proje/${esc(a.proje)}')">Projeye git</button>`
      : `<button class="btn ${a.karar === "TESTE AL" ? "ana" : ""}" onclick='projeYap(${json({json: a.json, karar: a.karar, baslik: a.baslik})})'>Projeye çevir</button>`}
    <button class="btn" onclick="hesabaGonder('${esc(a.json)}', ${a.min_fiyat || 0})">Kâr hesaplayıcıda aç</button>
    <button class="btn" onclick="adayIsaret('${a.isaret === "favori" ? "" : "favori"}')">${a.isaret === "favori" ? "★ Favoriden çıkar" : "☆ Favori"}</button>
    <span class="ara"></span>
    ${a.rapor ? `<button class="btn hayalet" onclick="raporModal('${esc(a.rapor)}')">Tam rapor</button>` : ""}
    <button class="btn hayalet" onclick="yenidenPuanla('${esc(a.json)}')" title="AliExpress'e gitmeden güncel kurallarla yeniden puanlar (Gemini)">Yeniden puanla</button>
    <button class="btn hayalet" style="color:var(--bad)" onclick="adayIsaret('${a.isaret === "red" ? "" : "red"}')">${a.isaret === "red" ? "Reddi kaldır" : "Reddet"}</button>
  </div>`;
}
async function adayIsaret(i) { await post("/api/aday-isaret/" + ADAY.id, {isaret: i || null}); ADAY.isaret = i || null; adayCiz(); bildir(i === "red" ? "Reddedildi; listede gizlenir." : i === "favori" ? "Favorilere eklendi." : "İşaret kaldırıldı."); if (location.hash.startsWith("#kesif")) { const x = ADAYLAR.find(y => y.id === ADAY.id); if (x) x.isaret = i || null; adayTabloCiz(); } }
async function yenidenPuanla(ad) { try { isTakip(await post("/api/yeniden-puanla/" + encodeURIComponent(ad)), () => ciz()); bildir("Yeniden puanlanıyor (~1 dk)."); } catch (e) { bildir(e.message); } }
function halka(p, en = 20) {
  const r = 40, c = 2 * Math.PI * r, o = Math.max(0, Math.min(1, (p || 0) / en));
  const renk = p >= 15 ? "var(--ok)" : p >= 10 ? "var(--warn)" : "var(--bad)";
  return `<div class="skor-halka"><svg viewBox="0 0 92 92" width="92" height="92"><circle cx="46" cy="46" r="${r}" fill="none" stroke="var(--line)" stroke-width="8"/>
    <circle cx="46" cy="46" r="${r}" fill="none" stroke="${renk}" stroke-width="8" stroke-linecap="round" stroke-dasharray="${c * o} ${c}" transform="rotate(-90 46 46)"/></svg><b>${p ?? "–"}</b></div>`;
}
function adayOzet(a) {
  const sk = a.skor || {}, n = neden(a), x = KARAR[a.karar] || KARAR["EKSİK VERİ"];
  const BASLIK = {ok: "Bu ürüne girilebilir", warn: "Şartlı: önce düzeltilmesi gereken var", bad: "Bu haliyle girme", gri: "Karar için veri eksik"};
  const kr = Object.fromEntries((sk.kriterler || []).map(k => [k.kod, k]));
  const durum = p => p == null ? ["gri", "?"] : p >= 2 ? ["ok", "İyi"] : p === 1 ? ["warn", "Orta"] : ["bad", "Zayıf"];
  const sinyal = (ad, kod, deger) => { const [c, t] = durum(kr[kod]?.puan);
    return `<div data-ipucu="${esc(kr[kod]?.gerekce || "")}"><small>${ad}</small><b>${deger}</b><div class="durum" style="color:var(--${c === "gri" ? "soft" : c})">● ${t}</div></div>`; };
  return `<div class="hukum ${x.c}">${miniHalka(sk.toplam, 20, 64)}<div>${karar(a.karar, true)}
      <h3 style="margin-top:8px">${BASLIK[x.c]}</h3><div class="k" style="color:var(--muted)">${esc(n.t)}</div></div></div>
    <div class="sinyal">
      ${sinyal("Kâr", "kar_marji", a.benzer_yok ? "doğrulanamadı" : a.piyasa_marj != null ? "net " + yuzde(a.piyasa_marj, 0) : "—")}
      ${sinyal("Problem çözüyor", "net_problem", (kr.net_problem?.puan ?? "–") + "/2")}
      ${sinyal("Videoda anlatılır", "video_anlatim", (kr.video_anlatim?.puan ?? "–") + "/2")}
    </div>
    ${a.rakip_medyan || a.benzer_yok ? `<div style="margin-top:16px">${adayBant(a)}</div>` : ""}
    ${(() => { const bay = (sk.kirmizi_bayraklar || []).filter(x => !(a.benzer_yok && /aynı ürün/i.test(x)));
      return bay.length ? `<div class="not warn" style="margin-top:14px"><b>Dikkat</b>${bay.slice(0, 3).map(esc).join("<br>")}</div>` : ""; })()}
    <details class="ac"><summary>20 puanın dağılımı</summary><div class="ic">${(sk.kriterler || []).map(k => `<div class="kriter"><b style="font-size:13px;font-weight:600">${esc(k.ad)}</b>
      <div class="bar">${[0, 1].map(i => `<i class="${k.puan == null ? "" : k.puan > i ? (k.puan === 1 ? "y" : "d") : ""}"></i>`).join("")}<span class="k muted" style="width:26px;text-align:right">${k.puan ?? "?"}/2</span></div>
      <small>${esc(k.gerekce || "")}</small></div>`).join("")}</div></details>
    ${(sk.hook_ornekleri || sk.hooklar || []).length ? `<details class="ac"><summary>Reklam kancası fikirleri</summary><div class="ic">${(sk.hook_ornekleri || sk.hooklar).map(h => `<div class="liste-li">💬 ${esc(typeof h === "string" ? h : h.metin || JSON.stringify(h))}</div>`).join("")}</div></details>` : ""}`;
}
function adayBant(a) {
  const rk = a.rakip_ozet || {};
  if (!rk.medyan) return a.benzer_yok ? `<div class="not bilgi"><b>Trendyol'da aynı ürün yok</b>Aramada çıkanlar başka türden. Pazar boşluğu da olabilir, talep yokluğu da.</div>` : "";
  const ust = Math.max(rk.max, a.min_fiyat || 0) * 1.05, x = v => Math.max(0, Math.min(100, v / ust * 100));
  return `<div class="k muted" style="font-weight:600">Trendyol fiyat aralığı <span class="soft">· ${esc(rk.kapsam || rk.urun_sayisi + " ürün")}</span></div>
    <div class="bant"><div class="serit"></div><div class="ceyrek" style="left:${x(rk.alt_ceyrek)}%;width:${x(rk.ust_ceyrek) - x(rk.alt_ceyrek)}%" data-ipucu="Rakiplerin ortadaki yarısı: ${tl(rk.alt_ceyrek)} – ${tl(rk.ust_ceyrek)}"></div>
      <div class="im" style="left:${x(rk.medyan)}%"><span style="${etk(x(rk.medyan))}">piyasa ${tl(rk.medyan)}</span></div>
      ${a.min_fiyat ? `<div class="im biz" style="left:${x(a.min_fiyat)}%"><span style="${etk(x(a.min_fiyat))}">bize gereken ${tl(a.min_fiyat)}</span></div>` : ""}
      <span class="uc" style="left:0">${tl(rk.min)}</span><span class="uc" style="right:0">${tl(rk.max)}</span></div>`;
}
const etk = p => p > 75 ? "left:auto;right:0;transform:none" : p < 25 ? "left:0;transform:none" : "";
function adayFiyat(a) {
  const m = a.maliyet?.stok || {}, k = m.kalemler || {};
  const KAL = {urun: "Ürün (AliExpress)", navlun: "Navlun (toplu)", ithalat_vergi_araci: "Gümrük + vergi + aracı", paketleme: "Paketleme", yurtici_kargo: "Yurt içi kargo", uluslararasi_kargo: "Uluslararası kargo", vergi: "Vergi"};
  const rk = a.rakip_ozet || {};
  let bant = "";
  if (rk.medyan) {
    bant = `<div style="margin-top:20px">${adayBant(a)}</div>`;
  } else if (false) {
    const ust = Math.max(rk.max, a.min_fiyat || 0) * 1.05, x = v => Math.max(0, Math.min(100, v / ust * 100));
    bant = `<div class="kart-ic" style="padding:0"><h4 style="margin:18px 0 0">Trendyol fiyat aralığı (${rk.kapsam || rk.urun_sayisi + " ürün"})</h4>
      <div class="bant"><div class="serit"></div><div class="ceyrek" style="left:${x(rk.alt_ceyrek)}%;width:${x(rk.ust_ceyrek) - x(rk.alt_ceyrek)}%"></div>
        <div class="im" style="left:${x(rk.medyan)}%"><span style="${etk(x(rk.medyan))}">medyan ${tl(rk.medyan)}</span></div>
        ${a.min_fiyat ? `<div class="im biz" style="left:${x(a.min_fiyat)}%"><span style="${etk(x(a.min_fiyat))}">bizim min. ${tl(a.min_fiyat)}</span></div>` : ""}
        <span class="uc" style="left:0">${tl(rk.min)}</span><span class="uc" style="right:0">${tl(rk.max)}</span></div>
      <div class="k muted" style="margin-top:22px">Mavi alan rakiplerin ortadaki yarısı (alt–üst çeyrek). Turuncu çizgi %20 net marj için en düşük fiyatımız.</div></div>`;
  } else if (a.benzer_yok) {
    bant = `<div class="not bilgi" style="margin-top:16px"><b>Trendyol'da aynı ürün bulunamadı</b>Aramadaki ürünler başka türden (ör. yedek rulo, aksesuar);
      fiyat kıyası yapılmadı. Bu bir pazar boşluğu da olabilir, talep olmadığı da: Trends ve Instagram'da talebi kontrol et.</div>`;
  }
  return `<div class="izgara g2">
    <div><h4 style="margin:0 0 6px">Birim maliyet (stoklu)</h4>${Object.entries(k).map(([a2, v]) => `<div class="liste-li"><span class="ara">${KAL[a2] || a2}</span><b class="say">${tl(v, 2)}</b></div>`).join("")}
      <div class="liste-li" style="border-top:1px solid var(--line2)"><b class="ara">Toplam</b><b class="say">${tl(m.toplam, 2)}</b></div>
      <div class="k muted" style="margin-top:6px">İade oranı varsayımı ${yuzde((a.iade?.oran || 0) * 100, 0)} (${esc(a.iade?.neden || "")})</div></div>
    <div><h4 style="margin:0 0 6px">Fiyat seçenekleri</h4>${(a.fiyat_secenekleri || []).map(s => `<div class="liste-li"><span class="ara">${esc(s.secenek)}<div class="k soft">ROAS ≥ ${s.basabas_roas ?? "–"} · hedef CPA ${tl(s.hedef_cpa || s.reklam_payi)}</div></span>
      <div style="text-align:right"><b class="say">${tl(s.fiyat)}</b><div class="k" style="color:${s.marj_yuzde >= 20 ? "var(--ok)" : s.marj_yuzde >= 0 ? "var(--warn)" : "var(--bad)"}">net ${yuzde(s.marj_yuzde)} · ${tl(s.birim_kar)}</div></div></div>`).join("")}</div>
  </div>${bant}`;
}
const BOYUT = {urun: "Ürün", teklif: "Teklif / paket", icerik: "İçerik", deneyim: "Deneyim", problem_cozumu: "Problem çözümü", fiyat: "Fiyat", ambalaj: "Ambalaj", hizmet: "Hizmet"};
function adayPazar(a) {
  const an = a.analiz || {}, tr = a.trend || {};
  const trs = Object.entries(tr);
  return `${trs.length ? `<h4 style="margin:0 0 6px">Google Trends (Türkiye, 12 ay)</h4>${trs.map(([k, v]) => `<div class="liste-li"><span class="ara">“${esc(k)}”</span>
      <span class="k">ort. <b>${sayi(v.ortalama, 1)}</b> · son 3 ay <b>${sayi(v.son_3_ay, 1)}</b>${v.degisim_yuzde != null ? ` · <b style="color:${v.degisim_yuzde >= 0 ? "var(--ok)" : "var(--bad)"}">${v.degisim_yuzde > 0 ? "+" : ""}${sayi(v.degisim_yuzde)}%</b>` : ""}</span></div>`).join("")}` : ""}
    ${an.sikayetler?.length ? `<h4 style="margin:18px 0 6px">Şikâyetler → fırsat</h4>${an.sikayetler.map(s => `<div class="liste-li"><span>😕</span><div><b>${esc(s.konu)}</b><div class="k muted">→ ${esc(s.firsat)}</div></div></div>`).join("")}` : ""}
    ${an.begeniler?.length ? `<h4 style="margin:18px 0 6px">Beğenilenler</h4>${an.begeniler.map(s => `<div class="liste-li"><span>👍</span><span>${esc(s.konu)}</span></div>`).join("")}` : ""}
    ${an.farklilasma?.length ? `<h4 style="margin:18px 0 6px">Farklılaşma planı <span class="rozet r-gri">henüz ürüne eklenmedi</span></h4>${an.farklilasma.map(s => `<div class="liste-li"><b style="min-width:110px">${esc(BOYUT[s.boyut] || s.boyut)}</b><span>${esc(s.oneri)}</span></div>`).join("")}` : ""}
    ${an.neden_benden ? `<div class="not bilgi" style="margin-top:14px"><b>Neden bizden alınır?</b>${esc(Array.isArray(an.neden_benden) ? an.neden_benden.join(" · ") : an.neden_benden)}</div>` : ""}
    ${!trs.length && !an.sikayetler ? `<div class="bos">Pazar verisi yok. Trendyol seçeneğiyle yeniden incele.</div>` : ""}`;
}
function adayRisk(a) {
  const r = a.riskler || [];
  const kr = a.kargo_riski || {};
  return `${r.length ? r.map(x => `<div class="liste-li"><span class="rozet ${(RISK[x.seviye] || RISK.bilgi)[1]}" style="height:fit-content">${(RISK[x.seviye] || RISK.bilgi)[0]}</span>
      <div><b>${esc(x.konu)}</b><div class="k muted">${esc(x.detay || "")}</div></div></div>`).join("") : `<div class="not ok"><b>Belirgin risk bulunmadı</b>Yine de numuneyle doğrula.</div>`}
    <h4 style="margin:18px 0 6px">Kargo</h4><div class="liste-li"><span class="ara">Kargo riski</span>${kr.seviye ? `<span class="rozet ${RISK[kr.seviye][1]}">${RISK[kr.seviye][0]}</span>` : "–"}</div>
    ${(kr.nedenler || []).map(n => `<div class="liste-li k muted">${esc(n)}</div>`).join("")}
    ${(a.urun?.kargo || []).slice(0, 4).map(k => `<div class="liste-li"><span class="ara">${esc(k.firma)}</span><span class="k">${k.gun_min ?? "?"}–${k.gun_max ?? "?"} gün · ${k.ucretsiz ? "ücretsiz" : tl(k.ucret_tl)} · ${k.takip ? "takipli" : "takipsiz"}</span></div>`).join("")}`;
}
async function raporModal(ad) {
  const r = await api("/api/arastirma-rapor/" + encodeURIComponent(ad));
  modal(`<div class="flex"><h3 class="ara">Araştırma raporu</h3><button class="btn hayalet" data-kapat>✕</button></div><div class="rapor" style="padding:0">${md(r.md)}</div>`, {genis: true});
}
function yeniArastirma() {
  const m = modal(`<h3>Yeni ürün incele</h3><p class="k muted" style="margin-top:0">AliExpress ürününü açar, maliyet, rakip fiyatları, trend ve 20 puanlık skoru çıkarır. 2–4 dakika sürer.</p>
    <div class="alan"><label class="e">AliExpress ürün linki</label><input id="yL" placeholder="https://tr.aliexpress.com/item/1005….html"></div>
    <div class="alan"><label class="e">Türkçe pazar kelimesi</label><input id="yK" placeholder="ör. tüy toplama rulosu"><div class="k soft" style="margin-top:4px">Trendyol ve Google Trends bu kelimeyle aranır.</div></div>
    <label class="kutu-sec"><input type="checkbox" id="yT" checked> Trendyol rakiplerini çek <span class="soft k">(Apify ≈ 0,05–0,10 $; aylık 5 $ sınırı korunur)</span></label>
    <div class="not bilgi" style="margin-top:14px">AliExpress doğrulama (CAPTCHA) isterse inceleme durur; atlatılmaz.</div>
    <div class="flex" style="margin-top:16px;justify-content:flex-end"><button class="btn" data-kapat>Vazgeç</button><button class="btn ana" id="yB">İncelemeyi başlat</button></div>`);
  $("#yL", m).focus();
  $("#yB", m).onclick = async () => {
    try {
      const is = await post("/api/arastir", {link: $("#yL", m).value, kelime: $("#yK", m).value, trendyol: $("#yT", m).checked});
      m.remove(); isTakip(is, () => ciz()); bildir("İnceleme başladı; sağ altta takip edebilirsin.");
    } catch (e) { bildir(e.message); }
  };
}
function projeYap(a) {
  const zorunlu = a.karar !== "TESTE AL";
  const m = modal(`<h3>Projeye çevir</h3><p class="k muted iki-satir" style="margin-top:0">${esc(a.baslik)}</p>
    ${zorunlu ? `<div class="not warn" style="margin-bottom:12px"><b>Bu ürünün kararı: ${esc(a.karar)}</b>Hat normalde sadece TESTE AL ürünlerle başlar. Yine de açarsan proje "deneme" olarak işaretlenir.</div>` : `<div class="not ok" style="margin-bottom:12px"><b>TESTE AL</b>Sonraki adımlar: satıcıya sorular ve numune, marka adı, içerik.</div>`}
    <div class="alan"><label class="e">Proje kısa adı (isteğe bağlı)</label><input id="pAd" placeholder="ör. tuy-rulosu"></div>
    ${zorunlu ? `<label class="kutu-sec"><input type="checkbox" id="pZ"> Kararı biliyorum, deneme olarak aç</label>` : ""}
    <div class="flex" style="margin-top:16px;justify-content:flex-end"><button class="btn" data-kapat>Vazgeç</button><button class="btn ana" id="pB">Projeyi oluştur</button></div>`);
  $("#pB", m).onclick = async () => {
    if (zorunlu && !$("#pZ", m).checked) return bildir("Deneme olarak açmak için kutuyu işaretle.");
    try { const r = await post("/api/yeni", {json: a.json, ad: $("#pAd", m).value, zorla: zorunlu}); m.remove(); cekmeceKapat(); bildir("Proje oluşturuldu."); git("proje/" + r.proje); }
    catch (e) { bildir(e.message, 6000); }
  };
}

/* ---------------------------------------------------------------- günlük tarama */
let KELIMELER = null;
async function taramaSayfa(ana, sekme) {
  yolCiz(["Ürün", "Günlük tarama"]);
  sekme = sekme || "adaylar";
  const [o, k] = await Promise.all([ozetYukle(), api("/api/kelimeler")]);
  KELIMELER = k.liste.map(x => ({...x}));
  const rapor = await api("/api/gunluk/" + (sekme === "liste" ? "adaylar" : sekme));
  const gv = k.gorev;
  ana.innerHTML = `
  <div class="bas-sayfa"><div><h1>Günlük tarama</h1><p>Her sabah listedeki sıradaki kelimeyle AliExpress'te arar, alakalı en iyi 3 ürünü 20 puanlık kartla değerlendirir.</p></div>
    <button class="btn ana" id="gB">Şimdi çalıştır</button></div>
  <div class="izgara g4">
    <div class="kart kpi"><div class="e">Sonraki çalışma</div><div class="d" style="font-size:19px">${gv ? tarih(gv.sonraki) : "–"}</div><div class="a">${gv ? "Windows Görev Zamanlayıcı · bilgisayar kapalıysa açılınca" : "Görev bulunamadı"}</div></div>
    <div class="kart kpi"><div class="e">Son çalışma</div><div class="d" style="font-size:19px">${tarih(k.son)}</div><div class="a">özet ve log: cikti/gunluk/</div></div>
    <div class="kart kpi"><div class="e">Sıradaki kelime</div><div class="d tek" style="font-size:19px">${esc(k.liste[k.sira]?.en || "–")}</div><div class="a">${esc(k.liste[k.sira]?.tr || "")}</div></div>
    <div class="kart kpi"><div class="e">Bütçe koruması</div><div class="d" style="font-size:19px">$${o.apify.gunluk_tavan} tavan</div><div class="a">Apify bu ay $${(o.apify.harcanan ?? 0).toFixed(2)}; tavan aşılırsa Trendyol atlanır</div></div>
  </div>
  <div class="kart" style="margin-top:14px"><div style="padding:0 18px"><div class="sekmeler" style="margin:6px 0 0">
      <button class="sekme ${sekme === "adaylar" ? "aktif" : ""}" onclick="git('tarama/adaylar')">Biriken adaylar</button>
      <button class="sekme ${sekme === "liste" ? "aktif" : ""}" onclick="git('tarama/liste')">Kelime listesi (${k.liste.length})</button>
      ${o.gunluk.gunler.slice(0, 7).map(d => `<button class="sekme ${sekme === d ? "aktif" : ""}" onclick="git('tarama/${d}')">${new Date(d).toLocaleDateString("tr-TR", {day: "numeric", month: "short"})}</button>`).join("")}
    </div></div>
    <div id="tIc">${sekme === "liste" ? "" : `<div class="rapor">${md(rapor.md)}</div>`}</div></div>`;
  if (sekme === "liste") kelimeCiz(k.sira);
  $("#gB").onclick = async () => { try { isTakip(await post("/api/gunluk-calistir"), () => location.hash.startsWith("#tarama") && ciz()); bildir("Tarama başladı (5–10 dk)."); } catch (e) { bildir(e.message); } };
}
function kelimeCiz(sira) {
  $("#tIc").innerHTML = `<div class="kart-ic"><div class="not bilgi" style="margin-bottom:12px">AliExpress'te İngilizce kelime daha iyi sonuç verir; Türkçe kelime Trendyol ve Google Trends için kullanılır.
    Sağlık vaadi gerektiren ürün kategorilerinden (korse, zayıflama vb.) kaçın.</div>
    <table class="tablo"><thead><tr><th style="width:40px">#</th><th>AliExpress araması (İngilizce)</th><th>Türkçe pazar kelimesi</th><th></th></tr></thead><tbody>
    ${KELIMELER.map((x, i) => `<tr style="cursor:default"><td class="k ${i === sira ? "" : "muted"}">${i === sira ? `<span class="rozet r-acc">sıradaki</span>` : i + 1}</td>
      <td><input data-i="${i}" data-a="en" value="${esc(x.en)}"></td><td><input data-i="${i}" data-a="tr" value="${esc(x.tr)}"></td>
      <td style="width:50px"><button class="btn kucuk hayalet" onclick="KELIMELER.splice(${i},1);kelimeCiz(${sira})">✕</button></td></tr>`).join("")}</tbody></table>
    <div class="flex" style="margin-top:12px"><button class="btn" onclick="KELIMELER.push({en:'',tr:''});kelimeCiz(${sira})">+ Kelime ekle</button><span class="ara"></span>
      <button class="btn ana" id="kK">Listeyi kaydet</button></div></div>`;
  $$("#tIc input[data-i]").forEach(i => i.oninput = () => KELIMELER[+i.dataset.i][i.dataset.a] = i.value);
  $("#kK").onclick = async () => { try { await post("/api/kelimeler", {liste: KELIMELER}, "PUT"); bildir("Kelime listesi kaydedildi."); ciz(); } catch (e) { bildir(e.message); } };
}

/* ---------------------------------------------------------------- projeler (pano) */
async function projelerSayfa(ana) {
  yolCiz(["Satış", "Projeler"]);
  const o = await ozetYukle();
  ana.innerHTML = `
  <div class="bas-sayfa"><div><h1>Projeler</h1><p>Her ürün bir proje. Kartlar hattaki aşamaya göre otomatik dizilir.</p></div>
    <button class="btn" onclick="git('kesif')">Adaylardan proje aç</button></div>
  ${o.projeler.length ? `<div class="kanban">${o.asamalar.map(([k, ad]) => { const l = o.projeler.filter(p => p.asama === k);
    return `<div class="sutun"><h4><span>${ad}</span><span>${l.length}</span></h4>${l.map(p => `
      <div class="pk" onclick="git('proje/${esc(p.ad)}')"><div class="ust"><img src="${esc(p.gorsel || "")}" alt="" referrerpolicy="no-referrer" onerror="gorselHata(this)">
        <div style="min-width:0"><b class="tek" style="display:block">${esc(p.marka || p.ad)}</b><div class="k muted">${p.ilerleme}/${p.toplam_adim} adım</div></div></div>
        <div class="adim-nokta" style="margin-top:10px">${p.adimlar.map(a => `<i class="${a.durum}"></i>`).join("")}</div>
        <div class="flex sarma" style="gap:5px;margin-top:9px">${karar(p.karar)}${p.zorla ? `<span class="rozet r-gri">deneme</span>` : ""}
          ${p.onay_bekleyen.length ? `<span class="rozet r-warn">${p.onay_bekleyen.length} onay</span>` : ""}${p.hazir.length ? `<span class="rozet r-info">${p.hazir.length} hazır</span>` : ""}</div>
      </div>`).join("") || `<div class="k soft" style="padding:6px 4px">—</div>`}</div>`; }).join("")}</div>`
    : `<div class="kart bos"><b>Henüz proje yok</b>Ürün keşfinde TESTE AL çıkan bir ürünü projeye çevir.</div>`}`;
}

/* ---------------------------------------------------------------- proje detayı */
let PROJE = null, SECILI = null, SECILI_P = null, PSEKME = "adimlar", SEKME = "rapor";
async function projeSayfa(ana, ad, ps) {
  await ozetYukle();
  PROJE = await api("/api/proje/" + encodeURIComponent(ad));
  const p = PROJE, f = p.fiyat || {};
  PSEKME = ps || "adimlar";
  yolCiz(["Projeler", p.marka || p.ad]);
  if (SECILI_P !== ad || !p.adimlar_detay.find(a => a.anahtar === SECILI)) {
    SECILI = (p.adimlar_detay.find(a => a.durum === "onay_bekliyor") || p.adimlar_detay.find(a => a.durum === "hazir") || p.adimlar_detay[0]).anahtar;
    SECILI_P = ad;
  }
  const hazir = p.adimlar_detay.filter(a => a.durum === "hazir").length;
  const asamaAd = (OZET.asamalar.find(([k]) => k === p.asama) || [])[1];
  ana.innerHTML = `
  <div class="kart p-bas">
    <img src="${esc(p.gorsel || "")}" alt="" referrerpolicy="no-referrer" onerror="gorselHata(this)">
    <div style="flex:1;min-width:240px">
      <div class="flex sarma" style="gap:8px"><h2>${esc(p.marka || p.ad)}</h2>${karar(p.karar)}<span class="k muted">${p.puan ?? "–"}/20</span>
        <span class="rozet r-mor">${esc(asamaAd || "")}</span>${p.zorla ? `<span class="rozet r-gri">deneme projesi</span>` : ""}</div>
      <div class="k muted tek">${esc(p.baslik)} · <a href="${esc(p.urun.link)}" target="_blank" rel="noopener">AliExpress ↗</a></div>
      <div class="metrik">
        <div><small>Satış fiyatı</small><b>${tl(f.fiyat)}</b></div><div><small>Birim net kâr</small><b>${tl(f.birim_kar)}</b></div>
        <div><small>Net marj</small><b style="color:${f.marj_yuzde >= 20 ? "var(--ok)" : "var(--warn)"}">${yuzde(f.marj_yuzde)}</b></div>
        <div><small>Başabaş ROAS</small><b>${f.basabas_roas ?? "–"}</b></div><div><small>Hedef CPA</small><b>${tl(f.hedef_cpa)}</b></div>
      </div>
    </div>
    <div style="width:200px">
      <div class="flex k muted" style="justify-content:space-between;margin-bottom:6px"><span>İlerleme</span><b style="color:var(--text)">${p.ilerleme}/${p.toplam_adim}</b></div>
      <div class="cubuk"><i style="width:${p.ilerleme / p.toplam_adim * 100}%"></i></div>
      <div class="flex" style="justify-content:flex-end;margin-top:12px;gap:6px">
        <button class="btn kucuk" onclick="ayarModal()">Ayarlar</button>
        <button class="btn kucuk ana" ${hazir ? "" : "disabled"} onclick="calistir([])">Hazırları çalıştır${hazir ? ` (${hazir})` : ""}</button></div>
    </div>
  </div>
  <div class="sekmeler" style="margin:16px 0 14px">${[["adimlar", "Adımlar"], ["kar", "Kâr"], ["reklam", "Reklam performansı"], ["icerik", "İçerik takvimi"], ["finans", "Haftalık finans"]]
    .map(([k, a]) => `<button class="sekme ${PSEKME === k ? "aktif" : ""}" onclick="git('proje/${esc(p.ad)}/${k}')">${a}</button>`).join("")}</div>
  <div id="pIc"></div>`;
  await ({adimlar: projeAdimlar, kar: projeKar, reklam: projeReklam, icerik: projeIcerik, finans: projeFinans}[PSEKME] || projeAdimlar)($("#pIc"));
}

async function projeAdimlar(el) {
  const p = PROJE;
  el.innerHTML = `<div class="duzen"><div class="kart adimlar">${p.adimlar_detay.map(a => `
      <div class="adim ${a.durum} ${a.anahtar === SECILI ? "secili" : ""}" onclick="SECILI='${a.anahtar}';SEKME='rapor';projeAdimlar($('#pIc'))">
        <div class="no">${a.durum === "tamam" || a.durum === "onaylandi" ? "✓" : a.no}</div>
        <div class="t"><b>${esc(a.ad)}</b><small>${DURUM[a.durum][0]}${a.zaman ? " · " + tarih(a.zaman) : ""}</small></div></div>`).join("")}</div>
    <div class="kart" id="detay"></div></div>`;
  await detayCiz();
}
async function detayCiz() {
  const p = PROJE, a = p.adimlar_detay.find(x => x.anahtar === SECILI), el = $("#detay");
  const [dAd, dCls] = DURUM[a.durum];
  const calisabilir = !["arastirma", "analiz"].includes(a.anahtar) && a.durum !== "kilitli";
  const klasor = {gorsel: "gorseller", magaza: "magaza", instagram: "instagram", icerik: "yasal", operasyon: "operasyon"}[a.anahtar];
  const dosyalar = p.dosyalar.filter(d => d.klasor === klasor);
  let eylem = "";
  if (a.durum === "onay_bekliyor") eylem += `<button class="btn yesil" onclick="onayla('${a.anahtar}')">Onayla</button>`;
  if (a.durum === "onaylandi") eylem += `<button class="btn" onclick="onayGeri('${a.anahtar}')">Onayı geri al</button>`;
  if (calisabilir) eylem += `<button class="btn ${a.durum === "hazir" ? "ana" : ""}" onclick="calistir(['${a.anahtar}'])">${a.durum === "hazir" ? "Çalıştır" : "Yeniden üret"}</button>`;
  if (a.anahtar === "magaza" && a.rapor) eylem += `<button class="btn" onclick="shopifyTaslak()">Shopify'a taslak gönder</button>`;
  if (a.anahtar === "analiz" && a.durum !== "kilitli") eylem += `<label class="btn ana" style="margin:0">CSV yükle ve analiz et<input type="file" accept=".csv" hidden onchange="csvYukle(this)"></label>`;
  const sek = [["rapor", "Rapor"]];
  if (dosyalar.length) sek.push(["dosyalar", a.anahtar === "magaza" ? "Önizleme & dosyalar" : "Dosyalar"]);
  if (!sek.find(s => s[0] === SEKME)) SEKME = "rapor";
  el.innerHTML = `
    <div class="detay-bas"><div><div class="flex" style="gap:8px"><span class="k muted">Adım ${a.no}</span><span class="rozet ${dCls}">${dAd}</span></div>
      <h2>${esc(a.ad)}</h2><div class="k muted">${esc(a.aciklama)}</div></div><div class="flex sarma" style="gap:8px">${eylem}</div></div>
    ${a.durum === "onay_bekliyor" ? `<div class="not warn" style="margin:14px 20px 0"><b>Senden onay bekleniyor</b>${esc(a.onay_metni)}. Raporu okuyup kontrol ettikten sonra onayla.</div>` : ""}
    ${a.durum === "kilitli" ? `<div class="not bilgi" style="margin:14px 20px 0"><b>Önce bunlar gerekli</b>${esc(a.eksikler.join(", "))}</div>` : ""}
    ${a.anahtar === "reklam" ? `<div class="not bilgi" style="margin:14px 20px 0"><b>Reklam yayını senin elinde</b>Bu adım plan ve Meta isteklerini hazırlar; kampanyayı açmak Reklam Yöneticisi'nde senin onayınla olur.</div>` : ""}
    <div style="padding:0 20px"><div class="sekmeler" style="margin:12px 0 0">${sek.map(([k, n]) => `<button class="sekme ${SEKME === k ? "aktif" : ""}" onclick="SEKME='${k}';detayCiz()">${n}</button>`).join("")}</div></div>
    <div id="sIc"><div class="kart-ic"><div class="iskelet"></div></div></div>`;
  const ic = $("#sIc");
  if (SEKME === "dosyalar") {
    const res = dosyalar.filter(d => ["png", "jpg", "jpeg", "webp"].includes(d.tur)), diger = dosyalar.filter(d => !res.includes(d));
    const onz = dosyalar.find(d => d.yol.endsWith("magaza/index.html"));
    const u = d => `/dosya/${encodeURIComponent(p.ad)}/${d.yol.split("/").map(encodeURIComponent).join("/")}`;
    ic.innerHTML = `${res.length ? `<div class="galeri">${res.map(d => `<a href="${u(d)}" target="_blank"><img src="${u(d)}" loading="lazy"><span class="tek">${esc(d.yol.split("/").pop())}</span></a>`).join("")}</div>` : ""}
      ${diger.length ? `<div class="flex sarma" style="padding:16px 20px;gap:8px">${diger.map(d => `<a class="btn kucuk" href="${u(d)}" target="_blank">${esc(d.yol.split("/").pop())}</a>`).join("")}</div>` : ""}
      ${onz ? `<iframe class="onizleme" src="${u(onz)}" sandbox="allow-same-origin"></iframe>` : ""}`;
  } else if (a.rapor) {
    try {
      const r = await api(`/api/proje/${encodeURIComponent(p.ad)}/rapor/${a.anahtar}`);
      let on = [];
      if (a.anahtar === "arastirma" && p.kaynak_json) {
        try {
          const ad = await api("/api/aday/" + encodeURIComponent(p.kaynak_json));
          on = [["Karar", adayOzet(ad)], ["Fiyat & kâr", adayFiyat(ad)], ["Pazar", adayPazar(ad)], ["Riskler", adayRisk(ad)]];
        } catch (e) { /* görsel kartlar olmadan devam */ }
      }
      ic.innerHTML = `<div style="padding:16px 20px 20px">${slaytlar(r.md, on, a.anahtar === "arastirma" ? /risk|birim maliyet|fiyat seçenek|skor kart|karar/i : null)}</div>`;
      slaytBagla(ic.querySelector(".slayt"));
    }
    catch (e) { ic.innerHTML = `<div class="bos">${esc(e.message)}</div>`; }
  } else ic.innerHTML = `<div class="bos"><b>Henüz çalıştırılmadı</b>${calisabilir ? "Yukarıdan Çalıştır'a bas." : ""}</div>`;
}

async function projeKar(el) {
  const f = PROJE.fiyat || {};
  el.innerHTML = `<div class="kart"><div class="kart-ic">${hesapArayuz({proje: PROJE.ad, fiyat: f.fiyat || 499})}</div></div>`;
  hesapBagla({proje: PROJE.ad});
}

async function projeReklam(el) {
  const v = await api(`/api/proje/${encodeURIComponent(PROJE.ad)}/veri`);
  const an = v.analiz, rk = v.reklam, kr = an.kurallar || rk.kurallar || {};
  if (!an.setler.length) {
    el.innerHTML = `<div class="izgara g2">${rk.butce ? `<div class="kart"><div class="kart-bas"><h3>Test planı</h3></div><div class="kart-ic">
      <div class="buyuk-sayi">${tl(rk.butce.gunluk_tl)}<span class="k muted" style="font-size:14px;font-weight:500"> / gün</span></div>
      <div class="k muted">${rk.setler.length} set · 5 günlük test ${tl(rk.butce.test_5_gun_tl)}</div><hr class="c">
      ${rk.setler.map(s => `<div class="liste-li"><span class="ara tek">${esc(s.ad)}</span><b>${tl(s.butce)}</b></div>`).join("")}</div></div>` : ""}
      <div class="kart bos"><b>Henüz reklam verisi yok</b>Test başladıktan sonra Reklam Yöneticisi'nden reklam seti düzeyinde CSV indir ve <b>Adımlar → Reklam analizi</b>'nden yükle.</div></div>`;
    return;
  }
  const S = an.setler, t = an.toplam || {};
  const mxC = Math.max(...S.map(s => s.cpa || 0), (kr.hedef_cpa_tl || 0) * 2.2, 1);
  const mxR = Math.max(...S.map(s => s.roas || 0), (kr.basabas_roas || 0) * 1.6, 1);
  const KR = {"KAPAT": "r-bad", "ÖLÇEKLE": "r-ok", "İZLE (iyi)": "r-info", "İZLE": "r-gri"};
  const top = k => S.reduce((x, s) => x + (s[k] || 0), 0);
  const huni = [["Gösterim", top("gosterim")], ["Tıklama", top("tik")], ["Sayfa görüntüleme", top("lpv")], ["Sepete ekleme", top("atc")], ["Ödeme başlatma", top("ic")], ["Satın alma", top("satis")]];
  el.innerHTML = `
  <div class="izgara g4">
    <div class="kart kpi"><div class="e">Harcama</div><div class="d">${tl(t.harcama)}</div><div class="a">~${sayi(an.saat)} saattir test</div></div>
    <div class="kart kpi"><div class="e">Ciro</div><div class="d">${tl(t.deger)}</div><div class="a">${sayi(t.satis)} satış</div></div>
    <div class="kart kpi"><div class="e">ROAS</div><div class="d" style="color:${t.roas >= kr.basabas_roas ? "var(--ok)" : "var(--bad)"}">${sayi(t.roas, 2)}</div><div class="a">başabaş ${kr.basabas_roas ?? "–"}</div></div>
    <div class="kart kpi"><div class="e">Ortalama CPA</div><div class="d">${tl(t.satis ? t.harcama / t.satis : null)}</div><div class="a">hedef ${tl(kr.hedef_cpa_tl)}</div></div>
  </div>
  <div class="izgara g2" style="margin-top:14px">
    <div class="kart"><div class="kart-bas"><h3>Satış başına maliyet (CPA)</h3><span class="k muted">çizgi = hedef CPA</span></div><div class="kart-ic"><div class="yatay-bar">
      ${S.map(s => `<span class="tek">${esc(s.ad)}</span><div class="b">${s.cpa ? `<i style="width:${s.cpa / mxC * 100}%;background:${s.cpa <= kr.hedef_cpa_tl ? "var(--ok)" : s.cpa >= 2 * kr.hedef_cpa_tl ? "var(--bad)" : "var(--warn)"}"></i>` : ""}
        ${kr.hedef_cpa_tl ? `<span class="cizgi" style="left:${kr.hedef_cpa_tl / mxC * 100}%"></span>` : ""}</div><span class="d">${s.cpa ? tl(s.cpa) : "satış yok"}</span>`).join("")}</div></div></div>
    <div class="kart"><div class="kart-bas"><h3>ROAS</h3><span class="k muted">çizgi = başabaş</span></div><div class="kart-ic"><div class="yatay-bar">
      ${S.map(s => `<span class="tek">${esc(s.ad)}</span><div class="b"><i style="width:${(s.roas || 0) / mxR * 100}%;background:${s.roas >= kr.basabas_roas ? "var(--ok)" : "var(--bad)"}"></i>
        ${kr.basabas_roas ? `<span class="cizgi" style="left:${kr.basabas_roas / mxR * 100}%"></span>` : ""}</div><span class="d">${sayi(s.roas, 2)}</span>`).join("")}</div></div></div>
  </div>
  <div class="izgara g12" style="margin-top:14px">
    <div class="kart"><div class="kart-bas"><h3>Dönüşüm hunisi</h3></div><div class="kart-ic"><div class="huni">
      ${huni.map(([ad, n], i) => `<div class="s"><span>${ad}</span><div class="b"><i style="width:${Math.max(1.5, i === 0 ? 100 : Math.sqrt(n / (huni[0][1] || 1)) * 100)}%"></i></div>
        <span class="k say">${sayi(n)}${i ? ` <span class="soft">· ${yuzde(n / (huni[i - 1][1] || 1) * 100)}</span>` : ""}</span></div>`).join("")}</div>
      <div class="k soft" style="margin-top:8px">Çubuklar karekök ölçekli; yüzdeler bir önceki adıma göre geçiş oranı.</div></div></div>
    <div class="kart"><div class="kart-bas"><h3>Set kararları</h3></div><div class="tablo-k"><table class="tablo"><thead><tr><th>Set</th><th>Karar</th><th class="sayi">Harcama</th><th class="sayi">CTR</th><th class="sayi">Satış</th><th>Neden / teşhis</th></tr></thead><tbody>
      ${S.map(s => `<tr style="cursor:default"><td class="tek" style="max-width:160px">${esc(s.ad)}</td><td><span class="rozet ${KR[s.karar] || "r-gri"}">${esc(s.karar)}</span></td>
        <td class="sayi">${tl(s.harcama)}</td><td class="sayi">${s.ctr != null ? yuzde(s.ctr, 2) : "–"}</td><td class="sayi">${sayi(s.satis)}</td>
        <td class="k">${esc(s.neden)}${(s.teshis || []).map(x => `<div class="soft">• ${esc(x)}</div>`).join("")}</td></tr>`).join("")}</tbody></table></div></div>
  </div>`;
}

async function projeIcerik(el) {
  const v = await api(`/api/proje/${encodeURIComponent(PROJE.ad)}/veri`);
  const l = v.instagram;
  if (!l.length) { el.innerHTML = `<div class="kart bos"><b>İçerik takvimi yok</b>Adımlar → Instagram'ı çalıştır.</div>`; return; }
  const T = {reels: "r-acc", carousel: "r-info", gorsel: "r-mor", "görsel": "r-mor"};
  const say = t => l.filter(x => (x.tur || "").toLowerCase() === t).length;
  el.innerHTML = `<div class="kart"><div class="kart-bas"><h3>${l.length} içerik</h3>
    <div class="flex k">${["reels", "carousel", "gorsel"].map(t => `<span class="rozet ${T[t]}">${t} ${say(t) || say(t === "gorsel" ? "görsel" : t)}</span>`).join("")}</div></div>
    <div class="ig">${l.map(x => `<div class="p"><div class="flex"><span class="rozet ${T[(x.tur || "").toLowerCase()] || "r-gri"}">${esc(x.tur)}</span><span class="k soft">#${esc(x.sira)}</span>
      <span class="ara"></span><span class="rozet r-gri">${esc(x.durum || "taslak")}</span></div>
      <b>${esc(x.baslik)}</b><div class="muted">“${esc(x.kanca)}”</div>
      <div class="k soft" style="margin-top:6px">${esc((x.akis || "").split("|")[0])}…</div>
      <div class="k" style="margin-top:6px;color:var(--info)">${esc(x.gorsel_kaynagi || "")}</div></div>`).join("")}</div>
    <div class="kart-ic k muted" style="border-top:1px solid var(--line)">Tam metinler ve hashtag'ler: <a href="/dosya/${encodeURIComponent(PROJE.ad)}/instagram/icerik-takvimi.csv" target="_blank">icerik-takvimi.csv</a>. Paylaşımı sen yaparsın.</div></div>`;
}

async function projeFinans(el) {
  const v = await api(`/api/proje/${encodeURIComponent(PROJE.ad)}/veri`);
  const l = v.haftalik.filter(x => x.hafta);
  const n = x => parseFloat(String(x || "0").replace(",", ".")) || 0;
  if (!l.length) {
    el.innerHTML = `<div class="kart bos"><b>Henüz satış verisi yok</b>Mağaza açılınca her hafta <code>operasyon/haftalik.csv</code> dosyasına bir satır ekle
      (ziyaret, sipariş, ciro, reklam, ürün maliyeti, kargo, komisyon, iade). Panel net kârı ve marjı burada gösterir.
      <div style="margin-top:12px"><a class="btn kucuk" href="/dosya/${encodeURIComponent(PROJE.ad)}/operasyon/haftalik.csv" target="_blank">Boş tabloyu aç</a></div></div>`;
    return;
  }
  const r = l.map(x => { const ciro = n(x.ciro_tl), gider = n(x.reklam_tl) + n(x.urun_maliyeti_tl) + n(x.kargo_tl) + n(x.komisyon_tl) + n(x.iade_tutar_tl) + n(x.diger_gider_tl);
    const net = ciro / 1.2 - gider; return {...x, ciro, net, marj: ciro ? net / ciro * 100 : null, cr: n(x.ziyaret) ? n(x.siparis) / n(x.ziyaret) * 100 : null}; });
  const mx = Math.max(...r.map(x => Math.abs(x.net)), 1);
  el.innerHTML = `<div class="kart"><div class="kart-bas"><h3>Haftalık net kâr</h3><span class="k muted">ciro KDV hariç − tüm giderler</span></div>
    <div class="kart-ic"><div class="yatay-bar">${r.map(x => `<span>${esc(x.hafta)}</span><div class="b"><i style="width:${Math.abs(x.net) / mx * 100}%;background:${x.net >= 0 ? "var(--ok)" : "var(--bad)"}"></i></div><span class="d">${tl(x.net)}</span>`).join("")}</div></div>
    <div class="tablo-k"><table class="tablo"><thead><tr><th>Hafta</th><th class="sayi">Ziyaret</th><th class="sayi">Sipariş</th><th class="sayi">Dönüşüm</th><th class="sayi">Ciro</th><th class="sayi">Reklam</th><th class="sayi">Net kâr</th><th class="sayi">Marj</th></tr></thead><tbody>
    ${r.map(x => `<tr style="cursor:default"><td>${esc(x.hafta)}</td><td class="sayi">${sayi(n(x.ziyaret))}</td><td class="sayi">${sayi(n(x.siparis))}</td><td class="sayi">${x.cr != null ? yuzde(x.cr, 2) : "–"}</td>
      <td class="sayi">${tl(x.ciro)}</td><td class="sayi">${tl(n(x.reklam_tl))}</td><td class="sayi" style="color:${x.net >= 0 ? "var(--ok)" : "var(--bad)"}"><b>${tl(x.net)}</b></td>
      <td class="sayi" style="color:${x.marj >= 20 ? "var(--ok)" : "var(--warn)"}">${yuzde(x.marj)}</td></tr>`).join("")}</tbody></table></div></div>`;
}

async function calistir(adimlar) {
  try { const is = await post(`/api/proje/${encodeURIComponent(PROJE.ad)}/calistir`, {adimlar}); isTakip(is, () => location.hash.startsWith("#proje/" + PROJE.ad) && ciz()); bildir("Çalışıyor; sağ altta takip edebilirsin."); }
  catch (e) { bildir(e.message); }
}
function onayla(adim) {
  if (adim === "marka") return markaModal();
  const a = PROJE.adimlar_detay.find(x => x.anahtar === adim);
  const m = modal(`<h3>${esc(a.ad)} onayı</h3><p>${esc(a.onay_metni)}.</p><label class="kutu-sec"><input type="checkbox" id="oK"> Kontrol ettim, onaylıyorum</label>
    <div class="flex" style="margin-top:16px;justify-content:flex-end"><button class="btn" data-kapat>Vazgeç</button><button class="btn yesil" id="oB">Onayla</button></div>`);
  $("#oB", m).onclick = async () => {
    if (!$("#oK", m).checked) return bildir("Önce kutuyu işaretle.");
    try { await post(`/api/proje/${encodeURIComponent(PROJE.ad)}/onayla`, {adim}); m.remove(); bildir("Onaylandı."); ciz(); } catch (e) { bildir(e.message); }
  };
}
function markaModal() {
  const m = modal(`<h3>Marka adını seç</h3><p class="k muted" style="margin-top:0">.com durumu otomatik kontrol edildi. Instagram kullanıcı adını ve Türk Patent kaydını (turkpatent.gov.tr) ayrıca kendin kontrol et.</p>
    <div style="max-height:46vh;overflow:auto">${PROJE.marka_isimleri.map((x, i) => `<label class="secenek"><input type="radio" name="isim" value="${esc(x.isim)}" ${PROJE.secimler.isim === x.isim || (!PROJE.secimler.isim && i === 0) ? "checked" : ""}>
      <div><b>${esc(x.isim)}</b> <span class="rozet ${/boş|müsait|musait|alınabilir/i.test(x.com || "") ? "r-ok" : "r-gri"}">.com ${esc(x.com || "?")}</span><small>${esc(x.aciklama || "")}</small></div></label>`).join("")}</div>
    <label class="kutu-sec" style="margin-top:6px"><input type="checkbox" id="mK"> Domain ve Instagram'ı elle kontrol ettim</label>
    <div class="flex" style="margin-top:16px;justify-content:flex-end"><button class="btn" data-kapat>Vazgeç</button><button class="btn yesil" id="mB">Bu isimle onayla</button></div>`);
  $("#mB", m).onclick = async () => {
    if (!$("#mK", m).checked) return bildir("Önce kontrol kutusunu işaretle.");
    const isim = $("input[name=isim]:checked", m)?.value;
    try { await post(`/api/proje/${encodeURIComponent(PROJE.ad)}/onayla`, {adim: "marka", isim}); m.remove(); bildir(`Marka: ${isim}`); ciz(); } catch (e) { bildir(e.message); }
  };
}
async function onayGeri(adim) { try { await post(`/api/proje/${encodeURIComponent(PROJE.ad)}/onay-geri`, {adim}); bildir("Onay geri alındı."); ciz(); } catch (e) { bildir(e.message); } }
async function csvYukle(inp) {
  const fd = new FormData(); fd.append("dosya", inp.files[0]);
  try { const is = await api(`/api/proje/${encodeURIComponent(PROJE.ad)}/analiz`, {method: "POST", body: fd}); isTakip(is, () => ciz()); bildir("Analiz çalışıyor."); }
  catch (e) { bildir(e.message); }
}
function ayarModal() {
  const s = PROJE.secimler;
  const alan = (k, ad, ipucu) => `<div class="alan"><label class="e">${ad}</label><input data-k="${k}" value="${esc(s[k] ?? "")}" placeholder="${esc(ipucu)}"></div>`;
  const m = modal(`<h3>Proje ayarları</h3><p class="k muted" style="margin-top:0">Boş bırakılan alan otomatik hesaplanır. Değiştirdikten sonra ilgili adımı yeniden üret.</p>
    <div class="not bilgi" style="margin-bottom:12px"><b>Tedarikçi toptan fiyatı</b>Satıcı adet başı fiyat verince buraya gir; maliyet, fiyat ve reklam eşikleri yeniden hesaplanır.</div>
    <div class="izgara g2" style="gap:12px">${alan("tedarik_fiyati", "Toptan alış fiyatı (KDV dahil, TL/adet)", "ör. 150")}${alan("tedarik_kargo", "Uluslararası kargo (sadece ithalatta)", "yerli tedarikte boş bırak")}</div>
    ${alan("fiyat", "Satış fiyatı (TL)", "otomatik: " + tl(PROJE.fiyat.fiyat))}
    <div class="izgara g2" style="gap:12px">${alan("kargo_esigi", "Ücretsiz kargo eşiği (TL)", "ör. 750")}${alan("hazirlik_gun", "Kargoya verme süresi (iş günü)", "ör. 2")}</div>
    <div class="izgara g2" style="gap:12px">${alan("gunluk_butce", "Günlük reklam bütçesi (TL)", "otomatik: 3 × hedef CPA")}${alan("set_sayisi", "Reklam seti sayısı", "otomatik: 1–4")}</div>
    <div class="izgara g2" style="gap:12px">${alan("yas_min", "En küçük yaş", "22")}${alan("yas_max", "En büyük yaş", "55")}</div>
    <div class="flex" style="margin-top:8px;justify-content:flex-end"><button class="btn" data-kapat>Vazgeç</button><button class="btn ana" id="sB">Kaydet</button></div>`);
  $("#sB", m).onclick = async () => {
    const v = {}; $$("[data-k]", m).forEach(i => v[i.dataset.k] = i.value.trim());
    try { await post(`/api/proje/${encodeURIComponent(PROJE.ad)}/sec`, v); m.remove(); bildir("Kaydedildi. Fiyat değiştiyse mağaza, kreatif ve reklam adımlarını yeniden üret."); ciz(); } catch (e) { bildir(e.message); }
  };
}

/* ---------------------------------------------------------------- kâr hesaplayıcı */
let HESAP_ON = null;
function hesabaGonder(j, fiyat) { HESAP_ON = {json: j, fiyat}; cekmeceKapat(); git("hesap"); }
async function hesapSayfa(ana) {
  yolCiz(["Satış", "Kâr hesaplayıcı"]);
  await ozetYukle();
  const ad = await api("/api/arastirmalar");
  const on = HESAP_ON || {}; HESAP_ON = null;
  ana.innerHTML = `<div class="bas-sayfa"><div><h1>Kâr hesaplayıcı</h1><p>Fiyatı, indirimi ve kanalı değiştir; KDV, komisyon, iade ve reklam sonrası gerçekten ne kaldığını gör.</p></div></div>
    <div class="kart"><div class="kart-ic">
      <div class="izgara g2" style="margin-bottom:14px"><div><label class="e">Ürün</label><select id="hUrun"><option value="">Elle maliyet gir</option>
        ${ad.map(a => `<option value="${esc(a.json)}" data-f="${a.min_fiyat || ""}" ${on.json === a.json ? "selected" : ""}>${esc((a.baslik || "").slice(0, 70))} · ${tl(a.maliyet)}</option>`).join("")}</select></div>
        <div id="hMalK"><label class="e">Toptan alış fiyatı (KDV dahil, TL)</label><input id="hMal" type="number" min="0" value="150"></div></div>
      ${hesapArayuz({fiyat: on.fiyat || (ad[0]?.min_fiyat ?? 499)})}</div></div>`;
  const sec = () => { $("#hMalK").style.display = $("#hUrun").value ? "none" : ""; };
  $("#hUrun").onchange = () => { const o = $("#hUrun").selectedOptions[0]; if (o.dataset.f) { $("#hF").value = o.dataset.f; $("#hFr").value = o.dataset.f; } sec(); hesapGuncelle(); };
  $("#hMal").oninput = hesapGuncelle;
  sec(); hesapBagla({});
}
function hesapArayuz(o) {
  return `<div class="izgara g12">
    <div>
      <div class="alan"><label class="e">Satış fiyatı (KDV dahil)</label><div class="flex"><input id="hF" type="number" min="1" value="${Math.round(o.fiyat)}" style="width:120px">
        <input id="hFr" type="range" min="50" max="${Math.max(3000, Math.round(o.fiyat * 2))}" step="1" value="${Math.round(o.fiyat)}" class="ara"></div></div>
      <div class="alan"><label class="e">Satış kanalı</label><div class="segment" id="hKanal"><button class="aktif" data-v="site">Kendi sitem</button><button data-v="trendyol">Trendyol</button></div></div>
      <div class="izgara g2" style="gap:12px">
        <div class="alan"><label class="e">İndirim / kampanya: <b id="hIv">%0</b></label><input id="hI" type="range" min="0" max="50" value="0"></div>
        <div class="alan"><label class="e">İade oranı: <b id="hRv">%15</b></label><input id="hR" type="range" min="0" max="40" value="15"></div></div>
      <div class="alan"><label class="e">Reklam payı (satışın %'si): <b id="hAv">%20</b></label><input id="hA" type="range" min="0" max="45" value="20">
        <div class="k soft">Hedef CPA = fiyat × reklam payı. Trendyol'da reklam genelde daha düşüktür.</div></div>
    </div>
    <div id="hSonuc"><div class="iskelet"></div></div></div>`;
}
let HB = {};
function hesapBagla(b) {
  HB = b;
  $("#hF").oninput = () => { $("#hFr").value = $("#hF").value; hesapGuncelle(); };
  $("#hFr").oninput = () => { $("#hF").value = $("#hFr").value; hesapGuncelle(); };
  [["hI", "hIv"], ["hR", "hRv"], ["hA", "hAv"]].forEach(([i, v]) => $("#" + i).oninput = () => { $("#" + v).textContent = "%" + $("#" + i).value; hesapGuncelle(); });
  $$("#hKanal button").forEach(btn => btn.onclick = () => { $$("#hKanal button").forEach(x => x.classList.toggle("aktif", x === btn));
    $("#hA").value = btn.dataset.v === "trendyol" ? 8 : 20; $("#hAv").textContent = "%" + $("#hA").value; hesapGuncelle(); });
  hesapGuncelle();
}
let hZam = null;
function hesapGuncelle() { clearTimeout(hZam); hZam = setTimeout(hesapYap, 160); }
async function hesapYap() {
  const v = {fiyat: +$("#hF").value || 0, kanal: $("#hKanal .aktif").dataset.v, indirim: +$("#hI").value / 100,
             iade_orani: +$("#hR").value / 100, reklam_payi: +$("#hA").value / 100};
  if (HB.proje) v.proje = HB.proje; else if ($("#hUrun")?.value) v.json = $("#hUrun").value; else v.maliyet = +$("#hMal").value;
  let r;
  try { r = await post("/api/hesapla", v); } catch (e) { $("#hSonuc").innerHTML = `<div class="not bad">${esc(e.message)}</div>`; return; }
  const renk = {"Ürün, kargo, koli": "#8a8378", "KDV (net)": "#b9b2a6", "Komisyon": "#6ea8f0", "Beklenen iade": "#e6b04a", "Reklam": "#a68cf5", "Net kâr": r.birim_kar >= 0 ? "var(--ok)" : "var(--bad)"};
  const pozitif = r.dagilim.filter(d => d.tl > 0), top = pozitif.reduce((s, d) => s + d.tl, 0) || 1;
  const iyi = r.marj_yuzde >= 20;
  $("#hSonuc").innerHTML = `
    <div class="izgara g3">
      <div><div class="k muted">Birim net kâr</div><div class="buyuk-sayi" style="color:${r.birim_kar >= 0 ? "var(--ok)" : "var(--bad)"}">${tl(r.birim_kar)}</div></div>
      <div><div class="k muted">Net marj</div><div class="buyuk-sayi" style="color:${iyi ? "var(--ok)" : r.marj_yuzde >= 0 ? "var(--warn)" : "var(--bad)"}">${yuzde(r.marj_yuzde)}</div></div>
      <div><div class="k muted">Brüt marj <span class="soft" data-ipucu="Reklam ve iade öncesi. Hedef %40–50 (Mert Kurtul)">ⓘ</span></div><div class="buyuk-sayi" style="color:${r.brut_marj_yuzde >= 40 ? "var(--ok)" : r.brut_marj_yuzde >= 30 ? "var(--warn)" : "var(--bad)"}">${yuzde(r.brut_marj_yuzde, 0)}</div>
        <div class="k soft">%20 net için en az ${tl(r.min_fiyat)}</div></div>
    </div>
    <div class="not ${iyi ? "ok" : r.birim_kar >= 0 ? "warn" : "bad"}" style="margin:14px 0">${iyi ? "<b>Hedef tutuyor</b>Net marj %20'nin üstünde." : r.birim_kar >= 0 ? `<b>Kârlı ama hedefin altında</b>%20 net marj için müşterinin ödediği fiyat en az ${tl(r.min_fiyat)} olmalı${v.indirim ? ` (bu indirimle liste fiyatı en az ${tl(Math.ceil(r.min_fiyat / (1 - v.indirim)))})` : ""} ya da maliyet düşmeli.` : "<b>Zarar</b>Bu fiyatta her satış para kaybettirir."}</div>
    <div class="k muted" style="margin-bottom:6px">Müşterinin ödediği ${tl(r.satis)} nereye gidiyor?</div>
    <div class="yigin">${pozitif.map(d => `<i title="${esc(d.ad)}: ${tl(d.tl, 2)}" style="width:${d.tl / top * 100}%;background:${renk[d.ad]}"></i>`).join("")}</div>
    <div class="lejant">${r.dagilim.map(d => `<span><i style="background:${renk[d.ad]}"></i>${esc(d.ad)} <b style="color:var(--text)">${tl(d.tl)}</b></span>`).join("")}</div>
    <div class="izgara g3" style="margin-top:16px">
      <div class="kart kpi" style="box-shadow:none"><div class="e">Başabaş ROAS</div><div class="d" style="font-size:20px">${r.basabas_roas ?? "–"}</div><div class="a">altında reklam zarar ettirir</div></div>
      <div class="kart kpi" style="box-shadow:none"><div class="e">Hedef CPA</div><div class="d" style="font-size:20px">${tl(r.hedef_cpa)}</div><div class="a">başabaş CPA ${tl(r.basabas_cpa)}</div></div>
      <div class="kart kpi" style="box-shadow:none"><div class="e">Önerilen test bütçesi</div><div class="d" style="font-size:20px">${tl(r.hedef_cpa * 3)}<span class="k muted">/gün</span></div><div class="a">3 × hedef CPA · 5 gün ${tl(r.hedef_cpa * 15)}</div></div>
    </div>
    <h4 style="margin:18px 0 6px">Paket teklifi (ortalama sepeti büyütür)</h4>
    ${[["1 adet", {fiyat: r.satis, birim_kar: r.birim_kar, marj_yuzde: r.marj_yuzde}], ["2 adet (%15 indirim)", r.paketler["2"]], ["3 adet (%25 indirim)", r.paketler["3"]]].map(([ad, p]) =>
      `<div class="liste-li"><span class="ara">${ad}</span><b class="say" style="width:100px;text-align:right">${tl(p.fiyat)}</b>
       <span class="say" style="width:150px;text-align:right;color:${p.marj_yuzde >= 20 ? "var(--ok)" : p.marj_yuzde >= 0 ? "var(--warn)" : "var(--bad)"}">kâr ${tl(p.birim_kar)} · ${yuzde(p.marj_yuzde)}</span></div>`).join("")}
    <div class="k soft" style="margin-top:8px">Pakette tek kargo ve tek paketleme varsayılır. Kampanya indirimi katkıyı orantısız eritir: her indirimi burada dene.</div>`;
}

/* ---------------------------------------------------------------- ayarlar */
async function ayarlarSayfa(ana) {
  yolCiz(["Sistem", "Ayarlar & bağlantılar"]);
  await ozetYukle();
  const a = await api("/api/ayarlar");
  const A = {GEMINI_API_KEY: ["Gemini", "Analiz, marka, içerik, kreatif metinleri; görseller için faturalandırma gerekir"], APIFY_TOKEN: ["Apify", "Trendyol rakip fiyatları ve yorumları"],
    SHOPIFY_MAGAZA: ["Shopify mağaza adresi", "Taslak ürün gönderimi"], SHOPIFY_ADMIN_TOKEN: ["Shopify yönetici anahtarı", "Taslak ürün gönderimi"],
    META_ERISIM_TOKENI: ["Meta erişim anahtarı", "Duraklatılmış kampanya oluşturma"], META_REKLAM_HESABI: ["Meta reklam hesabı", "act_… numarası"], META_PIXEL_ID: ["Meta Pixel", "Satın alma ölçümü"]};
  const ADL = {kdv: "KDV", odeme_komisyonu: "Ödeme komisyonu", pazaryeri_komisyonu: "Pazaryeri komisyonu", reklam_payi: "Reklam payı", hedef_marj: "Hedef net marj",
    iade_orani: "İade oranı", iade_donus_kargo_tl: "İade dönüş kargosu", iade_kayip_orani: "İadede kayıp oranı", paketleme_tl: "Paketleme", yurtici_kargo_tl: "Yurt içi kargo",
    stok_ithalat_orani: "İthalat (gümrük+vergi+aracı)", stok_navlun_tl: "Navlun (adet başı)", dogrudan_vergi_orani: "Doğrudan gönderim vergisi"};
  const deger = (k, v) => k.endsWith("_tl") ? tl(v) : yuzde(v * 100);
  const ap = a.apify, apY = ap.harcanan != null ? ap.harcanan / ap.butce * 100 : 0;
  ana.innerHTML = `<div class="bas-sayfa"><div><h1>Ayarlar & bağlantılar</h1><p>Anahtarlar sadece <code>.env</code> dosyasında durur; panel değerleri göstermez.</p></div></div>
  <div class="izgara g2">
    <div class="kart"><div class="kart-bas"><h3>Bağlantılar</h3></div><div class="kart-ic">${Object.entries(A).map(([k, [ad, ne]]) => `
      <div class="liste-li"><div class="ara"><b>${ad}</b><div class="k muted">${ne}</div></div>${a.anahtarlar[k] ? `<span class="rozet r-ok"><span class="nokta"></span>Bağlı</span>` : `<span class="rozet r-gri">Yok</span>`}
        ${PANEL_ANAHTAR[k] ? `<button class="btn kucuk" onclick="anahtarModal('${k}')">${a.anahtarlar[k] ? "Değiştir" : "Bağla"}</button>` : ""}</div>`).join("")}
      <div class="not bilgi" style="margin-top:12px">Eksik anahtarı <code>eticaret/.env</code> dosyasına ekle (örnek: <code>urun-arastirma/.env.example</code>) ve paneli yeniden başlat. Anahtarı sohbete yazma.</div></div></div>
    <div class="izgara" style="align-content:start">
      <div class="kart"><div class="kart-bas"><h3>Apify bütçesi</h3><span class="k muted">bu ay</span></div><div class="kart-ic">
        <div class="buyuk-sayi">$${(ap.harcanan ?? 0).toFixed(2)} <span class="k muted" style="font-size:14px">/ $${ap.butce}</span></div>
        <div class="gauge" style="margin:10px 0"><i style="width:${apY}%;background:${apY > 80 ? "var(--bad)" : apY > 60 ? "var(--warn)" : "var(--ok)"}"></i></div>
        <div class="k muted">Elle araştırmada çalıştırma başına en fazla $0,50. Günlük tarama $${ap.gunluk_tavan} üstünde Trendyol'u atlar.</div></div></div>
      <div class="kart"><div class="kart-bas"><h3>Zamanlanmış görev</h3></div><div class="kart-ic">
        ${a.gorev ? `<div class="liste-li"><span class="ara">Günlük ürün taraması</span><span class="rozet r-ok">Kurulu</span></div>
          <div class="liste-li"><span class="ara muted">Sonraki çalışma</span><b>${tarih(a.gorev.sonraki)}</b></div>` : `<div class="not warn">Görev bulunamadı.</div>`}</div></div>
      <div class="kart"><div class="kart-bas"><h3>Panelde bilerek olmayanlar</h3></div><div class="kart-ic k muted">
        Shopify'a ürün gönderme ve Meta'da kampanya oluşturma dışarıya iş yaptığı için sadece terminalden, açık bayrakla yapılır
        (<code>python hat.py calistir &lt;proje&gt; magaza --gonder</code>). Numune siparişi, domain alma, paylaşım ve reklamı yayına alma her zaman senin elinde.</div></div>
    </div>
  </div>
  <div class="kart" style="margin-top:14px"><div class="kart-bas"><h3>Hesaplama varsayımları</h3><span class="rozet ${new Date() - new Date(a.son_kontrol) > 90 * 864e5 ? "r-warn" : "r-gri"}">son kontrol ${new Date(a.son_kontrol).toLocaleDateString("tr-TR")}</span></div>
    <div class="kart-ic"><div class="izgara g3" style="gap:0 24px">${Object.entries(a.ayarlar).map(([k, v]) => `<div class="liste-li"><span class="ara muted">${ADL[k] || k}</span><b class="say">${deger(k, v)}</b></div>`).join("")}</div>
    <div class="k soft" style="margin-top:10px">Bu oranlar <code>urun-arastirma/hesap.py</code> içinde. Kargo ve komisyon fiyatları değiştikçe güncellenmeli.</div></div></div>`;
}

/* ---------------------------------------------------------------- iş takibi */
function isTakip(is, bitince) {
  const kutu = document.createElement("div"); kutu.className = "is";
  kutu.innerHTML = `<div class="ib"><span class="donen"></span><b class="tek">${esc(is.baslik)}</b><button class="btn kucuk hayalet" data-x>✕</button></div><pre>Başlıyor…</pre>`;
  let acik = true;
  $(".ib", kutu).onclick = e => { if (e.target.closest("[data-x]")) return kutu.remove(); acik = !acik; $("pre", kutu).style.display = acik ? "" : "none"; };
  $("#isler").prepend(kutu);
  const t = setInterval(async () => {
    try {
      const d = await api("/api/is/" + is.id);
      const pre = $("pre", kutu), alt = pre.scrollTop + pre.clientHeight >= pre.scrollHeight - 8;
      pre.textContent = d.cikti || "Başlıyor…"; if (alt) pre.scrollTop = pre.scrollHeight;
      if (d.durum !== "calisiyor") {
        clearInterval(t);
        $(".donen", kutu).outerHTML = d.durum === "bitti" ? `<span class="rozet r-ok">Bitti</span>` : `<span class="rozet r-bad">Hata</span>`;
        bildir(d.durum === "bitti" ? `Bitti: ${is.baslik}` : `Hata: ${is.baslik} (ayrıntı sağ altta)`);
        if (d.durum === "bitti") setTimeout(() => { if (!kutu.matches(":hover")) kutu.remove(); }, 15000);
        bitince && bitince();
      }
    } catch (e) { clearInterval(t); }
  }, 1500);
}

ciz();

/* Görsel yüklenemezse bir kez yeniden dene (AliExpress CDN bazen ilk istekte düşüyor), olmazsa yer tutucu göster */
function gorselHata(img) {
  if (!img.dataset.tekrar) {
    img.dataset.tekrar = "1";
    const s = img.getAttribute("src") || "";
    if (s) { setTimeout(() => { img.src = s + (s.includes("?") ? "&" : "?") + "r=" + Date.now(); }, 400); return; }
  }
  img.style.visibility = "hidden";
  img.parentElement && img.parentElement.classList.add("gorsel-yok");
}


/* ---------------------------------------------------------------- ürün sinyali (Amazon yeni çıkanlar → Türkiye doğrulaması) */
let SINYALLER = [];
async function sinyalSayfa(ana) {
  yolCiz(["Ürün", "Ürün sinyali"]);
  await ozetYukle();
  const v = await api("/api/sinyaller");
  SINYALLER = v.urunler;
  const say = k => SINYALLER.filter(u => u.karar === k).length;
  ana.innerHTML = `
  <div class="bas-sayfa"><div><h1>Ürün sinyali</h1><p>Amazon'da yeni çıkıp yükselen ürünler · Türkiye'de doygunluk · toptancıdan en fazla kaça alınmalı</p></div>
    <button class="btn ana" id="sB">Yeni sinyal çek</button></div>
  <div class="izgara g4" style="margin-bottom:16px">
    <div class="kart kpi"><div class="e">Sinyal</div><div class="d">${SINYALLER.length}</div><div class="a">son çalışma ${tarih(v.son)}</div></div>
    <div class="kart kpi"><div class="e">✓ Olur</div><div class="d" style="color:${say("TESTE AL") ? "var(--ok)" : "inherit"}">${say("TESTE AL")}</div><div class="a">az rakip + kârlı alış tavanı</div></div>
    <div class="kart kpi"><div class="e">~ Belki</div><div class="d">${say("İYİLEŞTİR")}</div><div class="a">kalabalık · TR'de yok · dar marj</div></div>
    <div class="kart kpi"><div class="e">✕ Olmaz</div><div class="d">${say("ELE")}</div><div class="a">pazar doymuş</div></div>
  </div>
  ${SINYALLER.length ? `<div class="urunler">${SINYALLER.map(sinyalKart).join("")}</div>`
    : `<div class="kart bos"><b>Henüz sinyal yok</b>"Yeni sinyal çek" Amazon'un yeni çıkanlar listesinden 2 kategori tarar (~0,30 $).</div>`}
  <div class="k soft" style="margin-top:16px">Yöntem: Mert Kurtul · Amazon filtresi puan ≥ 3,5 · fiyat 6–100 $ · yorum ≤ 1000 · güçlü rakip = Trendyol'da 100+ yorum (≤5 uygun, ≥10 doymuş) · alış tavanı: Trendyol medyanında %20 net kâr, yerli tedarik, KDV dahil</div>`;
  $("#sB").onclick = async () => { try { isTakip(await post("/api/sinyal-calistir"), () => location.hash.startsWith("#sinyal") && ciz()); bildir("Sinyal taraması başladı (5–10 dk)."); } catch (e) { bildir(e.message); } };
}
function doygunlukCubuk(dg) {
  if (!dg) return `<div class="k soft">Trendyol'da aynısı yok</div>`;
  const g = dg.guclu_rakip, renk = dg.seviye === "doymus" ? "var(--bad)" : dg.seviye === "kalabalik" ? "var(--warn)" : "var(--ok)";
  const ad = {uygun: "Uygun", kalabalik: "Kalabalık", doymus: "Doymuş"}[dg.seviye];
  return `<div data-ipucu="${g} güçlü rakip (100+ yorum) · en çok ${dg.en_cok_yorum} yorum · ${dg.rakip_sayisi} benzer ürün">
    <div class="flex" style="justify-content:space-between"><small style="font-size:11px;color:var(--soft);font-weight:500">Türkiye'de rekabet</small><b style="font-size:12px;color:${renk}">${ad}</b></div>
    <div class="adim-nokta" style="margin-top:4px">${Array.from({length: 10}, (_, i) => `<i style="background:${i < g ? renk : "var(--line)"}"></i>`).join("")}</div></div>`;
}
function sinyalKart(u, i) {
  const t = u.trendyol || {}, n = {"TESTE AL": "ok", "İYİLEŞTİR": "warn", "ELE": "bad"}[u.karar] || "gri";
  return `<div class="uk" onclick="sinyalAc(${SINYALLER.indexOf(u)})">
    <div class="gorsel"><img src="${esc(u.imageUrl || "")}" alt="" loading="lazy" referrerpolicy="no-referrer" onerror="gorselHata(this)" style="object-fit:contain;background:#fff">${karar(u.karar)}</div>
    <div class="govde">
      <div><div class="baslik iki-satir" style="min-height:0">${esc((u.tr_kelime || "").replace(/^./, c => c.toLocaleUpperCase("tr")))}</div>
        <div class="k soft tek">${esc(u.urun_turu || "")}</div></div>
      <div class="rakam" style="grid-template-columns:1fr 1fr 1fr">
        <div><small>Amazon</small><b>${u.price != null ? "$" + u.price : "–"}</b></div>
        <div><small>TR piyasa</small><b>${t.medyan ? tl(t.medyan) : "—"}</b></div>
        <div><small>Alış tavanı</small><b style="color:${u.alis_tavani ? "var(--ok)" : "var(--soft)"}">${u.alis_tavani ? "≤ " + tl(u.alis_tavani) : "—"}</b></div></div>
      ${t.benzer != null ? doygunlukCubuk(t.doygunluk) : `<div class="k soft">Trendyol doğrulaması bekliyor</div>`}
      ${u.reklam && !u.reklam.hata ? `<div class="k soft" data-ipucu="Meta Reklam Kütüphanesi (Türkiye), ilk sayfa">📣 ${u.reklam.reklamveren} reklamveren · ~${sayi(u.reklam.toplam_reklam)} reklam</div>` : ""}
      <div class="neden">${NEDEN_IK[n] || NEDEN_IK.gri}<span>${esc(u.neden || "")}</span></div>
    </div></div>`;
}
function sinyalAc(i) {
  const u = SINYALLER[i], t = u.trendyol || {};
  cekmece(`<div class="c-bas"><img src="${esc(u.imageUrl || "")}" style="object-fit:contain;background:#fff" referrerpolicy="no-referrer" onerror="gorselHata(this)">
      <div class="ara">${karar(u.karar)}<div style="font-weight:650;margin-top:6px">${esc(u.tr_kelime)}</div>
        <div class="k muted iki-satir">${esc(u.title)}</div>
        <div class="k"><a href="${esc(u.productUrl)}" target="_blank" rel="noopener">Amazon'da aç ↗</a> · ${esc(u.kategori)} · #${u.rank} yeni çıkan</div></div>
      <button class="btn hayalet" onclick="cekmeceKapat()" style="align-self:flex-start">✕</button></div>
    <div class="c-ic" style="padding-top:18px">
      <div class="hukum ${{"TESTE AL": "ok", "İYİLEŞTİR": "warn", "ELE": "bad"}[u.karar] || "gri"}"><div><h3>${esc(u.neden)}</h3></div></div>
      <div class="sinyal">
        <div><small>Amazon</small><b>${u.price != null ? "$" + u.price : "–"}</b><div class="durum soft">${u.rating ?? "–"}★ · ${sayi(u.reviewCount)} yorum</div></div>
        <div><small>Trendyol medyanı</small><b>${t.medyan ? tl(t.medyan) : "—"}</b><div class="durum soft">${t.benzer ?? 0} benzer / ${t.sonuc ?? 0} sonuç</div></div>
        <div><small>Toptan alış tavanı</small><b>${u.alis_tavani ? "≤ " + tl(u.alis_tavani) : "—"}</b><div class="durum soft">KDV dahil, %20 net için</div></div>
      </div>
      ${t.doygunluk ? `<div style="margin-top:14px">${doygunlukCubuk(t.doygunluk)}</div>` : ""}
      ${u.reklam && !u.reklam.hata ? `<div class="sinyal" style="grid-template-columns:repeat(3,minmax(0,1fr))">
        <div><small>Meta reklamları (TR)</small><b>~${sayi(u.reklam.toplam_reklam)}</b><div class="durum soft"><a href="${esc(u.reklam.url)}" target="_blank" rel="noopener">kütüphanede aç ↗</a></div></div>
        <div><small>Farklı reklamveren</small><b style="color:${u.reklam.seviye === "doymus" ? "var(--bad)" : u.reklam.seviye === "kalabalik" ? "var(--warn)" : "var(--ok)"}">${u.reklam.reklamveren}</b><div class="durum soft">≥20 doymuş · 8–19 kalabalık</div></div>
        <div><small>En uzun yayın</small><b>${u.reklam.en_uzun_gun != null ? u.reklam.en_uzun_gun + " gün" : "—"}</b><div class="durum soft">30+ gün: ${u.reklam["30_gun_ustu"] ?? 0}/${u.reklam.okunan_kart ?? 0}</div></div></div>` : ""}
      <h4 style="margin:18px 0 6px">Neden Türkiye'de satar?</h4><div class="liste-li">${esc(u.neden_tr || u.neden || "")}</div>
      <div class="liste-li"><b style="min-width:90px">Problem</b><span>${esc(u.problem || "")}</span></div>
      ${(u.acilar || []).length ? `<h4 style="margin:18px 0 6px">Pazarlama açıları (${u.acilar.length})</h4>${u.acilar.map(x => `<div class="liste-li">🎯 ${esc(x)}</div>`).join("")}` : ""}
      ${(t.ornekler || []).length ? `<details class="ac" open><summary>Trendyol'daki benzerler</summary><div class="ic">${t.ornekler.map(x => `<div class="liste-li"><a class="ara tek" href="${esc(x.link)}" target="_blank" rel="noopener">${esc(x.ad)}</a><b>${tl(x.fiyat)}</b><span class="soft k" style="width:90px;text-align:right">${sayi(x.degerlendirme)} yorum</span></div>`).join("")}</div></details>` : ""}
      <div class="not bilgi" style="margin-top:14px"><b>Sonraki adım</b>Trendyol'da satıcının mesafeli satış sözleşmesinden telefonuna ulaş, toptan fiyat iste ya da Türkiye'de ürettirme seçeneğine bak. Fiyat alış tavanının altındaysa ürünü incele ve projeye çevir.</div>
    </div>`);
}


/* ---------------------------------------------------------------- Shopify: mağaza sayfası, anahtar formu, taslak ürün */
const PANEL_ANAHTAR = {
  SHOPIFY_MAGAZA: ["Shopify mağaza adresi", "senin-magazan.myshopify.com", false],
  SHOPIFY_ADMIN_TOKEN: ["Shopify Admin API erişim anahtarı", "shpat_…", true],
  META_ERISIM_TOKENI: ["Meta sistem kullanıcısı erişim anahtarı", "EAAG…", true],
  META_REKLAM_HESABI: ["Meta reklam hesabı", "act_1234567890", false],
  META_PIXEL_ID: ["Meta Pixel numarası", "1234567890", false],
};
function anahtarModal(k, sonra) {
  const [ad, ipucu, gizli] = PANEL_ANAHTAR[k];
  const m = modal(`<h3>${esc(ad)}</h3><p class="k muted" style="margin-top:0">Değer sadece bu bilgisayardaki <code>.env</code> dosyasına yazılır; panel onu bir daha göstermez. Sohbete yazma.</p>
    <div class="alan"><input id="aD" type="${gizli ? "password" : "text"}" placeholder="${esc(ipucu)}" autocomplete="off"></div>
    <div class="flex" style="justify-content:flex-end"><button class="btn" data-kapat>Vazgeç</button><button class="btn ana" id="aK">Kaydet</button></div>`);
  $("#aD", m).focus();
  $("#aK", m).onclick = async () => {
    try { await post("/api/anahtar", {anahtar: k, deger: $("#aD", m).value}); m.remove(); bildir("Kaydedildi."); sonra ? sonra() : ciz(); }
    catch (e) { bildir(e.message, 5000); }
  };
}
let MGUN = 30;
async function magazaSayfa(ana) {
  yolCiz(["Satış", "Mağaza (Shopify)"]);
  await ozetYukle();
  const d = await api("/api/shopify");
  if (!d.bagli || d.hata) {
    ana.innerHTML = `<div class="bas-sayfa"><div><h1>Mağaza (Shopify)</h1><p>Siparişler, ciro ve iadeler buraya kendiliğinden gelir; ürünler taslak olarak gönderilir.</p></div></div>
    ${d.hata ? `<div class="not bad" style="margin-bottom:16px"><b>Bağlantı hatası</b>${esc(d.hata)}</div>` : ""}
    <div class="izgara g21"><div class="kart"><div class="kart-bas"><h3>Shopify'ı bağla (bir kez, ~5 dk)</h3></div><div class="kart-ic">
      ${[["Shopify yönetici → Ayarlar → Uygulamalar ve satış kanalları → <b>Uygulama geliştir</b> → Özel uygulama oluştur", ""],
         ["Admin API kapsamları: <b>read_orders</b>, <b>read_products</b>, <b>write_products</b> → Kaydet → Uygulamayı yükle", ""],
         ["<b>Admin API erişim anahtarını</b> (shpat_…) bir kez göster ve kopyala", ""]].map(([t], i) => `
        <div class="gorev" style="padding:10px 0"><div class="ik rozet r-acc" style="padding:0">${i + 1}</div><div class="ara">${t}</div></div>`).join("")}
      <hr class="c"><div class="izgara g2" style="gap:12px">
        <button class="btn" onclick="anahtarModal('SHOPIFY_MAGAZA')">${OZET && d.eksik && !d.eksik.includes("SHOPIFY_MAGAZA") ? "✓ " : ""}Mağaza adresini gir</button>
        <button class="btn ana" onclick="anahtarModal('SHOPIFY_ADMIN_TOKEN')">${d.eksik && !d.eksik.includes("SHOPIFY_ADMIN_TOKEN") ? "✓ " : ""}Erişim anahtarını gir</button></div>
    </div></div>
    <div class="kart"><div class="kart-bas"><h3>Bağlanınca</h3></div><div class="kart-ic k muted">
      <div class="liste-li">📈 Son 7 / 30 / 90 gün ciro, sipariş, ortalama sepet, iade</div>
      <div class="liste-li">📦 Mağazadaki ürünler ve stok</div>
      <div class="liste-li">⬆️ Projeden Shopify'a <b>taslak</b> ürün (yayına almak senin elinde)</div>
      <div class="liste-li">🔒 Sadece okuma + taslak; sipariş, fiyat ya da tema değiştirilmez</div></div></div></div>`;
    return;
  }
  ana.innerHTML = `<div class="bas-sayfa"><div><h1>${esc(d.magaza.name)}</h1><p>${esc(d.magaza.myshopifyDomain)} · ${esc(d.magaza.plan?.displayName || "")} · ${esc(d.magaza.currencyCode)}</p></div>
    <div class="segment">${[7, 30, 90].map(g => `<button class="${MGUN === g ? "aktif" : ""}" onclick="MGUN=${g};ciz()">${g} gün</button>`).join("")}</div></div>
    <div id="mSat"><div class="iskelet"></div></div>`;
  let s;
  try { s = await api("/api/shopify/satis?gun=" + MGUN); } catch (e) { $("#mSat").innerHTML = `<div class="not bad"><b>Satış verisi alınamadı</b>${esc(e.message)}</div>`; return; }
  const mx = Math.max(...s.seri.map(x => x.ciro), 1);
  $("#mSat").innerHTML = `<div class="izgara g4">
      <div class="kart kpi"><div class="e">Ciro</div><div class="d">${tl(s.ciro)}</div><div class="a">son ${s.gun} gün</div></div>
      <div class="kart kpi"><div class="e">Sipariş</div><div class="d">${sayi(s.siparis)}</div><div class="a">${sayi(s.adet)} ürün</div></div>
      <div class="kart kpi"><div class="e">Ortalama sepet</div><div class="d">${tl(s.ortalama_sepet)}</div><div class="a">paket ve yan ürünle büyür</div></div>
      <div class="kart kpi"><div class="e">İade</div><div class="d" style="color:${s.iade_orani > 15 ? "var(--bad)" : "inherit"}">${s.iade_orani != null ? yuzde(s.iade_orani) : "–"}</div><div class="a">${tl(s.iade)}</div></div></div>
    <div class="kart" style="margin-top:16px"><div class="kart-bas"><h3>Günlük ciro</h3></div><div class="kart-ic">
      <div style="display:flex;align-items:flex-end;gap:2px;height:160px">${s.seri.map(x => `<div style="flex:1;display:flex;align-items:flex-end;height:100%"
        data-ipucu="${new Date(x.gun).toLocaleDateString("tr-TR", {day: "numeric", month: "short"})}: ${tl(x.ciro)} · ${x.siparis} sipariş">
        <i style="display:block;width:100%;height:${Math.max(x.ciro ? 2 : 0, x.ciro / mx * 100)}%;background:var(--accent);border-radius:4px 4px 0 0"></i></div>`).join("")}</div>
      <div class="flex k soft" style="justify-content:space-between;margin-top:6px"><span>${new Date(s.seri[0].gun).toLocaleDateString("tr-TR", {day: "numeric", month: "short"})}</span><span>bugün</span></div></div></div>
    <div class="kart" style="margin-top:16px"><div class="kart-bas"><h3>Ürünler</h3></div><div class="kart-ic" id="mUrun"><div class="iskelet" style="height:60px"></div></div></div>`;
  try {
    const u = await api("/api/shopify/urunler");
    $("#mUrun").innerHTML = u.length ? u.map(x => `<div class="liste-li" style="align-items:center"><img class="res" src="${esc(x.gorsel || "")}" referrerpolicy="no-referrer" onerror="gorselHata(this)">
      <span class="ara tek">${esc(x.baslik)}</span><span class="rozet ${x.durum === "ACTIVE" ? "r-ok" : "r-gri"}">${x.durum === "ACTIVE" ? "Yayında" : x.durum === "DRAFT" ? "Taslak" : esc(x.durum)}</span>
      <span class="k soft" style="width:80px;text-align:right">${x.stok ?? "–"} stok</span></div>`).join("") : `<div class="bos" style="padding:20px">Henüz ürün yok</div>`;
  } catch (e) { $("#mUrun").innerHTML = `<div class="not bad">${esc(e.message)}</div>`; }
}
function shopifyTaslak() {
  const m = modal(`<h3>Shopify'a taslak ürün</h3><p class="k muted" style="margin-top:0">Ürün metni, fiyatı ve paketleri Shopify'a <b>TASLAK</b> olarak gönderilir; mağazada görünmez. Görselleri ve yayına almayı Shopify'da sen yaparsın.</p>
    <label class="kutu-sec"><input type="checkbox" id="tK"> İçeriği ve fiyatı kontrol ettim, taslak olarak gönder</label>
    <div class="flex" style="margin-top:16px;justify-content:flex-end"><button class="btn" data-kapat>Vazgeç</button><button class="btn ana" id="tB">Gönder</button></div>`);
  $("#tB", m).onclick = async () => {
    if (!$("#tK", m).checked) return bildir("Önce kutuyu işaretle.");
    try { const is = await post(`/api/proje/${encodeURIComponent(PROJE.ad)}/shopify-taslak`, {onay: true}); m.remove(); isTakip(is, () => ciz()); bildir("Gönderiliyor…"); }
    catch (e) { bildir(e.message, 5000); }
  };
}


/* ---------------------------------------------------------------- rapor → yana kaydırılan kartlar */
const SLAYT_IKON = [[/ön koşul|kontrol listesi|yapılacak/i, "✅"], [/özet|genel/i, "📋"], [/karar|skor|puan/i, "🎯"], [/fiyat|kâr|maliyet|kar\b/i, "💰"], [/pazar|rakip|trendyol|trend/i, "📈"],
  [/risk|dikkat|uyar/i, "⚠️"], [/kargo|teslim/i, "🚚"], [/varyant|renk/i, "🎨"], [/yorum|şikâyet|sss/i, "💬"], [/özellik|açıklama|satıcı/i, "📝"],
  [/görsel|logo|foto/i, "🖼️"], [/reklam|kreatif|hook|açı/i, "📣"], [/instagram|içerik|takvim/i, "📱"], [/marka|isim/i, "🏷️"],
  [/yasal|sözleşme|kvkk/i, "⚖️"], [/tedarik|satıcı|toptan|numune/i, "🤝"], [/mesaj|müşteri/i, "✉️"], [/kural|karar kural/i, "📏"], [/paket/i, "📦"], [/seo/i, "🔎"]];
const slaytIkon = b => (SLAYT_IKON.find(([r]) => r.test(b)) || [, "▫️"])[1];
function slaytlar(mdMetin, onKartlar = [], atla = null) {
  const parca = String(mdMetin || "").split(/^## /m);
  const bas = parca.shift() || "";
  const baslik = (bas.match(/^# (.+)$/m) || [])[1] || "";
  const giris = bas.replace(/^# .+$/m, "").trim();
  const kartlar = [...onKartlar.map(([b, h]) => ({b, h, gorsel: true}))];
  if (giris && !onKartlar.length) kartlar.push({b: "Özet", h: md(giris)});
  for (const p of parca) {
    const satir = p.indexOf("\n"), b = (satir < 0 ? p : p.slice(0, satir)).trim(), govde = satir < 0 ? "" : p.slice(satir + 1).trim();
    if (!govde || (atla && atla.test(b))) continue;
    kartlar.push({b, h: md(govde)});
  }
  if (!kartlar.length) return `<div class="rapor">${md(mdMetin)}</div>`;
  return `<div class="slayt" tabindex="0">
    ${baslik ? `<div class="slayt-baslik">${esc(baslik.replace(/[*_`]/g, ""))}</div>` : ""}
    <div class="slayt-sekme">${kartlar.map((k, i) => `<button data-git-kart="${i}" class="${i ? "" : "aktif"}"><span>${slaytIkon(k.b)}</span>${esc(k.b)}</button>`).join("")}</div>
    <div class="slayt-pist">${kartlar.map((k, i) => `<section class="slayt-kart ${k.gorsel ? "gorsel" : "rapor"}" data-kart="${i}">
      <div class="slayt-kb"><span class="slayt-ik">${slaytIkon(k.b)}</span><h3>${esc(k.b)}</h3><span class="soft k">${i + 1} / ${kartlar.length}</span></div>${k.h}</section>`).join("")}</div>
    <div class="slayt-alt"><button class="btn kucuk" data-yon="-1" aria-label="Önceki">‹ Önceki</button>
      <div class="slayt-nokta">${kartlar.map((_, i) => `<i data-git-kart="${i}" class="${i ? "" : "aktif"}"></i>`).join("")}</div>
      <button class="btn kucuk" data-yon="1" aria-label="Sonraki">Sonraki ›</button></div></div>`;
}
function slaytBagla(el) {
  if (!el) return;
  const pist = el.querySelector(".slayt-pist"), kartlar = [...pist.children];
  let su = 0;                                         // hangi karttayız (animasyon sırasında scrollLeft güvenilmez)
  const git = i => { su = Math.max(0, Math.min(kartlar.length - 1, i)); pist.scrollTo({left: kartlar[su].offsetLeft - pist.offsetLeft, behavior: "smooth"}); isaretle(); };
  const aktif = () => su;
  const isaretle = () => { const i = su;
    el.querySelectorAll("[data-git-kart]").forEach(b => b.classList.toggle("aktif", +b.dataset.gitKart === i));
    const sek = el.querySelector(`.slayt-sekme [data-git-kart="${i}"]`); sek && sek.scrollIntoView({block: "nearest", inline: "center", behavior: "smooth"}); };
  el.querySelectorAll("[data-git-kart]").forEach(b => b.onclick = () => git(+b.dataset.gitKart));
  el.querySelectorAll("[data-yon]").forEach(b => b.onclick = () => git(aktif() + +b.dataset.yon));
  let z; pist.addEventListener("scroll", () => { clearTimeout(z); z = setTimeout(() => { su = Math.round(pist.scrollLeft / Math.max(1, pist.clientWidth)); isaretle(); }, 120); });
  el.addEventListener("keydown", e => { if (e.key === "ArrowRight") { git(aktif() + 1); e.preventDefault(); } if (e.key === "ArrowLeft") { git(aktif() - 1); e.preventDefault(); } });
}

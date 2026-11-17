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
const KARAR = {"TESTE AL": "r-ok", "İYİLEŞTİR": "r-warn", "ELE": "r-bad", "EKSİK VERİ": "r-gri"};
const karar = k => k ? `<span class="rozet ${KARAR[k] || "r-gri"}">${esc(k)}</span>` : "";
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
  const [sayfa, arg, arg2] = (location.hash.slice(1) || "ana").split("/");
  $$(".men").forEach(m => m.classList.toggle("aktif", m.dataset.git === sayfa || (sayfa === "proje" && m.dataset.proje === arg)));
  const ana = $("#ana");
  try {
    const f = {ana: anaSayfa, kesif: kesifSayfa, tarama: taramaSayfa, projeler: projelerSayfa, hesap: hesapSayfa,
               ayarlar: ayarlarSayfa, proje: projeSayfa}[sayfa] || anaSayfa;
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
  const asamaSay = Object.fromEntries(o.asamalar.map(([k]) => [k, o.projeler.filter(p => p.asama === k)]));
  ana.innerHTML = `
  <div class="bas-sayfa"><div><h1>Merhaba 👋</h1><p>${gun(new Date())} · ${o.gorevler.length ? `<b>${o.gorevler.length}</b> iş seni bekliyor` : "Bekleyen iş yok"}</p></div>
    <div class="flex"><button class="btn" onclick="git('tarama')">Günlük tarama</button><button class="btn ana" onclick="yeniArastirma()">+ Yeni ürün incele</button></div></div>
  <div class="izgara g4">
    <div class="kart kpi"><div class="e">Aktif proje</div><div class="d">${o.projeler.length}</div><div class="a">${o.projeler.filter(p => p.asama === "test" || p.asama === "olcek").length} tanesi reklamda (test/ölçek)</div></div>
    <div class="kart kpi"><div class="e">Onay bekleyen</div><div class="d" style="color:${o.gorevler.filter(g => g.tur === "onay").length ? "var(--warn)" : "inherit"}">${o.gorevler.filter(g => g.tur === "onay").length}</div><div class="a">numune, marka, görsel, kreatif</div></div>
    <div class="kart kpi"><div class="e">Aday havuzu</div><div class="d">${o.arastirma_sayisi}</div>
      <div class="a">${kd["TESTE AL"]} teste al · ${kd["İYİLEŞTİR"]} iyileştir · ${kd["ELE"]} ele</div></div>
    <div class="kart kpi"><div class="e">Apify bu ay</div><div class="d">${ap.harcanan != null ? "$" + ap.harcanan.toFixed(2) : "–"}<span class="soft" style="font-size:15px;font-weight:600"> / $${ap.butce}</span></div>
      <div class="gauge" style="margin-top:8px"><i style="width:${apY}%;background:${apY > 80 ? "var(--bad)" : apY > 60 ? "var(--warn)" : "var(--ok)"}"></i></div></div>
  </div>
  <div class="izgara g21" style="margin-top:14px">
    <div class="kart"><div class="kart-bas"><h3>Yapılacaklar</h3><span class="k muted">${o.gorevler.length} iş</span></div>
      <div style="margin-top:8px">${o.gorevler.length ? o.gorevler.slice(0, 8).map(gorevSatir).join("") :
        `<div class="bos"><b>Her şey yolunda</b>Yeni bir ürün incele ya da günlük taramanın sonuçlarına bak.</div>`}</div></div>
    <div class="kart"><div class="kart-bas"><h3>Günlük tarama</h3><button class="btn kucuk" onclick="git('tarama')">Yönet</button></div>
      <div class="kart-ic">
        <div class="liste-li"><span class="muted ara">Sonraki çalışma</span><b>${o.gorev ? tarih(o.gorev.sonraki) : "görev yok"}</b></div>
        <div class="liste-li"><span class="muted ara">Son çalışma</span><b>${tarih(o.gunluk.son)}</b></div>
        <div class="liste-li"><span class="muted ara">Sıradaki kelime</span><b class="tek" style="max-width:55%">${esc(o.gunluk.sonraki_kelime || "–")}</b></div>
        <div class="liste-li"><span class="muted ara">Kelime listesi</span><b>${o.gunluk.kelime_sayisi}</b></div>
      </div></div>
  </div>
  <div class="kart" style="margin-top:14px"><div class="kart-bas"><h3>Satış hattı</h3><button class="btn kucuk" onclick="git('projeler')">Panoyu aç</button></div>
    <div class="kart-ic"><div class="mini-hat">${o.asamalar.map(([k, ad]) => `<div class="a"><b>${asamaSay[k].length}</b><span>${ad}</span>
      ${asamaSay[k].slice(0, 2).map(p => `<div class="k tek" style="margin-top:4px;cursor:pointer" onclick="git('proje/${esc(p.ad)}')">↳ ${esc(p.marka || p.ad)}</div>`).join("")}</div>`).join("")}</div></div></div>
  <div class="kart" style="margin-top:14px"><div class="kart-bas"><h3>Öne çıkan adaylar</h3><button class="btn kucuk" onclick="git('kesif')">Tüm adaylar</button></div>
    <div class="kart-ic">${o.adaylar.length ? adayTablo(o.adaylar, true) : `<div class="bos"><b>Henüz aday yok</b>Günlük tarama her sabah yeni ürünler ekler.</div>`}</div></div>`;
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
async function kesifSayfa(ana) {
  yolCiz(["Ürün", "Ürün keşfi"]);
  await ozetYukle();
  ADAYLAR = await api("/api/arastirmalar");
  ana.innerHTML = `
  <div class="bas-sayfa"><div><h1>Ürün keşfi</h1><p>İncelenen tüm ürünler: maliyet, %20 marj için gereken fiyat, Trendyol piyasası ve 20 puanlık skor.</p></div>
    <button class="btn ana" onclick="yeniArastirma()">+ Ürün incele</button></div>
  <div class="kart">
    <div class="kart-ic flex sarma" style="gap:8px;border-bottom:1px solid var(--line)">
      <div style="position:relative;flex:1;min-width:200px;max-width:340px"><input id="fAra" placeholder="Ürün ara…" value="${esc(FILTRE.ara)}" style="padding-left:32px">
        <span style="position:absolute;left:10px;top:9px;width:15px;color:var(--soft)">${IK.ara}</span></div>
      ${["hepsi", "TESTE AL", "İYİLEŞTİR", "EKSİK VERİ", "ELE"].map(k => `<button class="cip ${FILTRE.karar === k ? "aktif" : ""}" data-karar="${k}">${k === "hepsi" ? "Tümü" : k}
        <span class="soft" style="margin-left:5px">${k === "hepsi" ? ADAYLAR.length : ADAYLAR.filter(a => a.karar === k).length}</span></button>`).join("")}
      <span class="ara"></span>
      <label class="kutu-sec"><input type="checkbox" id="fFav" ${FILTRE.fav ? "checked" : ""}> Favoriler</label>
      <label class="kutu-sec"><input type="checkbox" id="fRed" ${FILTRE.red ? "checked" : ""}> Reddedilenler</label>
      <select id="fSira" style="width:auto"><option value="tarih">En yeni</option><option value="puan">Puan</option><option value="marj">Piyasa marjı</option><option value="uyum">Fiyat uyumu</option></select>
    </div>
    <div class="tablo-k" id="adayTablo"></div>
  </div>`;
  $("#fSira").value = FILTRE.sira;
  $("#fAra").oninput = e => { FILTRE.ara = e.target.value; adayTabloCiz(); };
  $$("[data-karar]").forEach(b => b.onclick = () => { FILTRE.karar = b.dataset.karar; kesifSayfa(ana); });
  $("#fFav").onchange = e => { FILTRE.fav = e.target.checked; adayTabloCiz(); };
  $("#fRed").onchange = e => { FILTRE.red = e.target.checked; adayTabloCiz(); };
  $("#fSira").onchange = e => { FILTRE.sira = e.target.value; adayTabloCiz(); };
  adayTabloCiz();
}
const uyum = a => a.min_fiyat && a.rakip_medyan ? a.min_fiyat / a.rakip_medyan : null;
function adayTabloCiz() {
  let l = ADAYLAR.filter(a => (FILTRE.karar === "hepsi" || a.karar === FILTRE.karar)
    && (!FILTRE.ara || (a.baslik || "").toLowerCase().includes(FILTRE.ara.toLowerCase()))
    && (!FILTRE.fav || a.isaret === "favori") && (FILTRE.red ? true : a.isaret !== "red"));
  const s = {puan: a => -(a.puan ?? -1), marj: a => -(a.piyasa_marj ?? -999), uyum: a => uyum(a) ?? 99, tarih: a => -new Date(a.tarih || 0)}[FILTRE.sira];
  l = l.sort((x, y) => s(x) - s(y));
  $("#adayTablo").innerHTML = l.length ? adayTablo(l) : `<div class="bos"><b>Eşleşen ürün yok</b>Filtreleri değiştir ya da yeni bir ürün incele.</div>`;
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
      <td><div class="urun-h"><img src="${esc(a.gorsel || "")}" alt="" loading="lazy" onerror="this.style.visibility='hidden'"><div style="min-width:0">
        <div class="iki-satir" style="font-weight:550">${esc(a.baslik)}</div>
        <div class="k soft">${a.isaret === "favori" ? "★ favori · " : a.isaret === "red" ? "reddedildi · " : ""}${a.proje ? `<span class="rozet r-mor">proje: ${esc(a.proje)}</span>` : ""}</div></div></div></td>
      <td><div class="puan-c">${karar(a.karar)}<span class="k muted say">${a.puan ?? "–"}/20</span></div></td>
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
  const tab = [["ozet", "Skor"], ["fiyat", "Fiyat & kâr"], ["pazar", "Pazar & rakip"], ["risk", `Riskler${a.riskler?.length ? ` (${a.riskler.length})` : ""}`]];
  c.innerHTML = `
  <div class="c-bas"><img src="${esc(a.gorsel || "")}" alt="" onerror="this.style.visibility='hidden'">
    <div class="ara"><div class="flex sarma" style="gap:6px">${karar(a.karar)}<span class="k muted">${a.puan}/20</span>${a.proje ? `<span class="rozet r-mor">proje: ${esc(a.proje)}</span>` : ""}${a.isaret === "red" ? `<span class="rozet r-bad">reddedildi</span>` : ""}</div>
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
  const sk = a.skor || {};
  return `<div class="flex" style="gap:18px;align-items:center">${halka(sk.toplam)}<div>
      <div style="font-weight:650;font-size:15px">${esc(sk.karar)} · ${sk.toplam}/20</div>
      <div class="k muted">15+ teste al · 10–14 iyileştir · 0–9 ele. Yüksek risk ya da piyasa fiyatında kâr yoksa teste alınmaz.</div></div></div>
    ${(sk.kirmizi_bayraklar || []).length ? `<div class="not warn" style="margin-top:14px"><b>Dikkat</b>${sk.kirmizi_bayraklar.map(esc).join("<br>")}</div>` : ""}
    <div style="margin-top:12px">${(sk.kriterler || []).map(k => `<div class="kriter"><b style="font-size:13px">${esc(k.ad)}</b>
      <div class="bar">${[0, 1].map(i => `<i class="${k.puan == null ? "" : k.puan > i ? (k.puan === 1 ? "y" : "d") : ""}"></i>`).join("")}<span class="k muted" style="width:26px;text-align:right">${k.puan ?? "?"}/2</span></div>
      <small>${esc(k.gerekce || "")}${k.kaynak ? ` <span class="soft">· ${esc(k.kaynak)}</span>` : ""}</small></div>`).join("")}</div>
    ${(sk.hooklar || []).length ? `<h4 style="margin:18px 0 6px">Reklam kancası fikirleri</h4>${sk.hooklar.map(h => `<div class="liste-li">💬 ${esc(typeof h === "string" ? h : h.metin || JSON.stringify(h))}</div>`).join("")}` : ""}`;
}
const etk = p => p > 75 ? "left:auto;right:0;transform:none" : p < 25 ? "left:0;transform:none" : "";
function adayFiyat(a) {
  const m = a.maliyet?.stok || {}, k = m.kalemler || {};
  const KAL = {urun: "Ürün (AliExpress)", navlun: "Navlun (toplu)", ithalat_vergi_araci: "Gümrük + vergi + aracı", paketleme: "Paketleme", yurtici_kargo: "Yurt içi kargo", uluslararasi_kargo: "Uluslararası kargo", vergi: "Vergi"};
  const rk = a.rakip_ozet || {};
  let bant = "";
  if (rk.medyan) {
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
      <div class="pk" onclick="git('proje/${esc(p.ad)}')"><div class="ust"><img src="${esc(p.gorsel || "")}" alt="" onerror="this.style.visibility='hidden'">
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
    <img src="${esc(p.gorsel || "")}" alt="" onerror="this.style.visibility='hidden'">
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
    try { const r = await api(`/api/proje/${encodeURIComponent(p.ad)}/rapor/${a.anahtar}`); ic.innerHTML = `<div class="rapor">${md(r.md)}</div>`; }
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
    <div class="izgara g2" style="gap:12px">${alan("tedarik_fiyati", "Toptan ürün fiyatı (TL/adet)", "boş: AliExpress tek adet fiyatı")}${alan("tedarik_kargo", "Uluslararası kargo (TL/adet)", "0")}</div>
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
        <div id="hMalK"><label class="e">Birim maliyet (TL, getirme dahil)</label><input id="hMal" type="number" min="0" value="150"></div></div>
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
  const renk = {"Ürün ve getirme": "#8a8378", "KDV": "#b9b2a6", "Komisyon": "#6ea8f0", "Beklenen iade": "#e6b04a", "Reklam": "#a68cf5", "Net kâr": r.birim_kar >= 0 ? "var(--ok)" : "var(--bad)"};
  const pozitif = r.dagilim.filter(d => d.tl > 0), top = pozitif.reduce((s, d) => s + d.tl, 0) || 1;
  const iyi = r.marj_yuzde >= 20;
  $("#hSonuc").innerHTML = `
    <div class="izgara g3">
      <div><div class="k muted">Birim net kâr</div><div class="buyuk-sayi" style="color:${r.birim_kar >= 0 ? "var(--ok)" : "var(--bad)"}">${tl(r.birim_kar)}</div></div>
      <div><div class="k muted">Net marj</div><div class="buyuk-sayi" style="color:${iyi ? "var(--ok)" : r.marj_yuzde >= 0 ? "var(--warn)" : "var(--bad)"}">${yuzde(r.marj_yuzde)}</div></div>
      <div><div class="k muted">%20 marj için en düşük satış fiyatı</div><div class="buyuk-sayi">${tl(r.min_fiyat)}</div></div>
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
      <div class="liste-li"><div class="ara"><b>${ad}</b><div class="k muted">${ne}</div></div>${a.anahtarlar[k] ? `<span class="rozet r-ok"><span class="nokta"></span>Bağlı</span>` : `<span class="rozet r-gri">Yok</span>`}</div>`).join("")}
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

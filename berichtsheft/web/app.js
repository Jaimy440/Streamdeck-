const TAGE = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag"];
const $ = (s) => document.querySelector(s);
let ergebnis = null;
let archivDaten = [];

// ---------------------------------------------------------------- Hilfen
async function api(pfad, opt = {}) {
  const r = await fetch(pfad, {
    method: opt.method || (opt.body ? "POST" : "GET"),
    headers: { "Content-Type": "application/json" },
    body: opt.body ? JSON.stringify(opt.body) : undefined,
  });
  const d = await r.json();
  if (!r.ok) throw new Error(d.fehler || r.statusText);
  return d;
}
function toast(t) {
  const el = $("#toast"); el.textContent = t; el.classList.add("zeigen");
  clearTimeout(toast.t); toast.t = setTimeout(() => el.classList.remove("zeigen"), 2500);
}
function esc(s) { return String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c])); }
function isoWoche(d = new Date()) {
  const t = new Date(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()));
  const tag = t.getUTCDay() || 7; t.setUTCDate(t.getUTCDate() + 4 - tag);
  const start = new Date(Date.UTC(t.getUTCFullYear(), 0, 1));
  return { kw: Math.ceil(((t - start) / 864e5 + 1) / 7), jahr: t.getUTCFullYear() };
}
function entprellen(fn, ms) { let t; return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); }; }
const lokal = {
  get(k) { try { return JSON.parse(localStorage.getItem(k)); } catch { return null; } },
  set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch {} },
};

// ---------------------------------------------------------------- Tabs
document.querySelectorAll("nav button").forEach((b) => b.addEventListener("click", () => {
  document.querySelectorAll("nav button, .tab").forEach((e) => e.classList.remove("aktiv"));
  b.classList.add("aktiv"); $("#" + b.dataset.tab).classList.add("aktiv");
  if (b.dataset.tab === "archiv") archivLaden();
}));

// ---------------------------------------------------------------- Neue Woche
function tageAufbauen() {
  $("#tage").innerHTML = TAGE.map((t) => `
    <div class="tag" data-tag="${t}">
      <div class="name">${t}<label><input type="checkbox" class="schule"> Berufsschule</label></div>
      <div>
        <textarea class="notiz" rows="2" placeholder="Stichworte … oder leer / ?"></textarea>
        <div class="treffer"></div>
      </div>
    </div>`).join("");
  document.querySelectorAll(".tag").forEach((el) => {
    const ta = el.querySelector(".notiz");
    const live = entprellen(() => treffer(el), 500);
    ta.addEventListener("input", () => { entwurfSichern(); live(); });
    el.querySelector(".schule").addEventListener("change", entwurfSichern);
  });
}

async function treffer(el) {
  const text = el.querySelector(".notiz").value.trim();
  const box = el.querySelector(".treffer");
  if (text.length < 4 || text === "?") { box.innerHTML = ""; return; }
  const liste = await api("/api/vorschlag", { body: { text, tag: el.dataset.tag, abteilung: $("#abteilung").value, kw: $("#kw").value } }).catch(() => []);
  const gut = liste.filter((x) => x.score > 0.2).slice(0, 3);
  box.innerHTML = gut.length ? "Ähnlich in alten Berichten: " + gut.map((x) =>
    `<button title="${esc(x.bericht.label)} – übernehmen" data-p="${esc(x.punkt)}">+ ${esc(x.punkt)}</button>`).join("") : "";
  box.querySelectorAll("button").forEach((b) => b.addEventListener("click", () => {
    const ta = el.querySelector(".notiz");
    ta.value = (ta.value.trim() ? ta.value.trim() + "\n" : "") + b.dataset.p;
    b.remove(); entwurfSichern();
  }));
}

function wocheLesen() {
  const tage = {};
  document.querySelectorAll(".tag").forEach((el) => {
    tage[el.dataset.tag] = { notiz: el.querySelector(".notiz").value, schule: el.querySelector(".schule").checked };
  });
  return { kw: $("#kw").value, jahr: $("#jahr").value, abteilung: $("#abteilung").value.trim(), beruf: einstellungen.beruf || "", tage };
}
function entwurfSichern() { lokal.set("entwurf", wocheLesen()); }
function entwurfLaden() {
  const w = lokal.get("entwurf"); const jetzt = isoWoche();
  $("#kw").value = w?.kw || jetzt.kw; $("#jahr").value = w?.jahr || jetzt.jahr;
  $("#abteilung").value = w?.abteilung || einstellungen.abteilung || "";
  if (!w) return;
  document.querySelectorAll(".tag").forEach((el) => {
    const d = w.tage?.[el.dataset.tag] || {};
    el.querySelector(".notiz").value = d.notiz || ""; el.querySelector(".schule").checked = !!d.schule;
  });
}
["#kw", "#jahr", "#abteilung"].forEach((s) => $(s).addEventListener("input", entwurfSichern));

$("#leeren").addEventListener("click", () => {
  if (!confirm("Alle Notizen dieser Woche leeren?")) return;
  document.querySelectorAll(".notiz").forEach((t) => (t.value = ""));
  document.querySelectorAll(".schule").forEach((c) => (c.checked = false));
  document.querySelectorAll(".treffer").forEach((t) => (t.innerHTML = ""));
  entwurfSichern();
});

$("#generieren").addEventListener("click", async () => {
  const btn = $("#generieren"); btn.disabled = true; btn.textContent = "⏳ Schreibe …";
  try {
    ergebnis = await api("/api/generieren", { body: wocheLesen() });
    ergebnisZeigen();
  } catch (e) { toast("Fehler: " + e.message); }
  btn.disabled = false; btn.textContent = "✨ Bericht schreiben";
});

function ergebnisZeigen() {
  $("#ergebnis").classList.remove("versteckt");
  $("#modus").textContent = ergebnis.modus === "claude" ? "Claude" : "offline";
  $("#hinweise").innerHTML = (ergebnis.hinweise || []).map((h) => `<li>${esc(h)}</li>`).join("");
  $("#ausgabe").innerHTML = ergebnis.tage.map((t, ti) => `
    <div class="ausgabe-tag"><h3>${t.tag}</h3>
      ${t.punkte.map((p, pi) => `
        <div class="punkt ${p.quelle}">
          <input value="${esc(p.text)}" data-t="${ti}" data-p="${pi}">
          ${p.aus ? `<span class="aus">aus ${esc(p.aus)}</span>` : ""}
          <button title="Entfernen" data-weg="${ti}:${pi}">✕</button>
        </div>`).join("")}
      <button class="plus" data-neu="${ti}">+ Punkt</button>
    </div>`).join("");
  $("#ausgabe").querySelectorAll("input").forEach((i) => i.addEventListener("input", () => {
    const p = ergebnis.tage[i.dataset.t].punkte[i.dataset.p]; p.text = i.value; p.quelle = p.quelle === "vorschlag" ? "notiz" : p.quelle;
  }));
  $("#ausgabe").querySelectorAll("[data-weg]").forEach((b) => b.addEventListener("click", () => {
    const [t, p] = b.dataset.weg.split(":"); ergebnis.tage[t].punkte.splice(p, 1); ergebnisZeigen();
  }));
  $("#ausgabe").querySelectorAll("[data-neu]").forEach((b) => b.addEventListener("click", () => {
    ergebnis.tage[b.dataset.neu].punkte.push({ text: "", quelle: "notiz" }); ergebnisZeigen();
  }));
  const d = ergebnis.doppelt || [];
  $("#doppelt").classList.toggle("versteckt", !d.length);
  $("#doppelt").innerHTML = "<b>Fast wortgleich mit alten Berichten</b> – Prüfer merken so etwas, lieber umformulieren:<ul>" +
    d.map((x) => `<li>„${esc(x.punkt)}“ ↔ ${esc(x.bericht)}</li>`).join("") + "</ul>";
  const v = ergebnis.vergleich || [];
  $("#vergleich").innerHTML = v.length ? "Verglichen mit: " + v.map((x) => `${esc(x.label)} (${Math.round(x.score * 100)} %)`).join(", ") : "";
  $("#ergebnis").scrollIntoView({ behavior: "smooth" });
}

function alsText() {
  const w = wocheLesen();
  const kopf = `KW ${w.kw}/${w.jahr}` + (w.abteilung ? ` – ${w.abteilung}` : "");
  return kopf + "\n\n" + ergebnis.tage.map((t) =>
    `${t.tag}:\n` + t.punkte.filter((p) => p.text.trim()).map((p) => `- ${p.text.trim()}`).join("\n")).join("\n\n");
}
$("#kopieren").addEventListener("click", async () => {
  try { await navigator.clipboard.writeText(alsText()); toast("Kopiert ✔"); }
  catch { prompt("Text kopieren:", alsText()); }
});
$("#speichern").addEventListener("click", async () => {
  const w = wocheLesen(); const tage = {};
  ergebnis.tage.forEach((t) => { tage[t.tag] = t.punkte.filter((p) => p.text.trim()).map((p) => "- " + p.text.trim()).join("\n"); });
  await api("/api/berichte", { method: "PUT", body: { kw: w.kw, jahr: w.jahr, abteilung: w.abteilung, tage } });
  toast("Im Archiv gespeichert ✔"); zaehlen();
});

// ---------------------------------------------------------------- Archiv
async function zaehlen() { archivDaten = await api("/api/berichte"); $("#anzahl").textContent = archivDaten.length; }
async function archivLaden() { await zaehlen(); archivZeigen(); }
function berichtText(b) {
  const tage = Object.keys(b.tage || {});
  return tage.length ? TAGE.filter((t) => b.tage[t]).map((t) => `${t}:\n${b.tage[t]}`).join("\n\n") : b.text;
}
function archivZeigen() {
  const q = $("#suche").value.toLowerCase();
  const liste = archivDaten.filter((b) => !q || (berichtText(b) + " " + b.abteilung).toLowerCase().includes(q));
  $("#liste").innerHTML = liste.length ? liste.map((b) => `
    <details class="bericht"><summary>
      <span><b>${b.kw ? "KW " + b.kw + (b.jahr ? "/" + b.jahr : "") : "ohne KW"}</b> ${b.abteilung ? "· " + esc(b.abteilung) : ""}</span>
      <button data-loeschen="${b.id}">Löschen</button></summary>
      <pre>${esc(berichtText(b))}</pre></details>`).join("")
    : `<div class="leer">${archivDaten.length ? "Nichts gefunden." : "Noch keine alten Berichte – oben importieren."}</div>`;
  $("#liste").querySelectorAll("[data-loeschen]").forEach((b) => b.addEventListener("click", async (e) => {
    e.preventDefault(); if (!confirm("Bericht löschen?")) return;
    await api("/api/berichte/" + b.dataset.loeschen, { method: "DELETE" }); archivLaden();
  }));
}
$("#suche").addEventListener("input", archivZeigen);

$("#imp-datei").addEventListener("change", async (e) => {
  const texte = await Promise.all([...e.target.files].map((f) => f.text()));
  $("#imp-text").value = ($("#imp-text").value.trim() + "\n\n" + texte.join("\n\n")).trim();
  e.target.value = "";
});
$("#importieren").addEventListener("click", async () => {
  try {
    const r = await api("/api/import", { body: {
      text: $("#imp-text").value, kw: $("#imp-kw").value, jahr: $("#imp-jahr").value, abteilung: $("#imp-abteilung").value } });
    toast(`${r.importiert} Bericht(e) importiert ✔`); $("#imp-text").value = ""; archivLaden();
  } catch (e) { toast(e.message); }
});

// ---------------------------------------------------------------- Einstellungen
let einstellungen = {};
function keyStatus() {
  $("#key-status").textContent = einstellungen.key_gesetzt ? "✔ API-Key gespeichert – Claude wird benutzt."
    : einstellungen.env_key ? "✔ API-Key aus Umgebungsvariable gefunden – Claude wird benutzt."
    : "Kein API-Key – Offline-Modus.";
}
async function einstellungenLaden() {
  einstellungen = await api("/api/config");
  $("#cfg-beruf").value = einstellungen.beruf; $("#cfg-abteilung").value = einstellungen.abteilung; keyStatus();
}
$("#cfg-speichern").addEventListener("click", async () => {
  const body = { beruf: $("#cfg-beruf").value, abteilung: $("#cfg-abteilung").value };
  if ($("#cfg-key").value.trim()) body.api_key = $("#cfg-key").value;
  einstellungen = await api("/api/config", { body }); $("#cfg-key").value = ""; keyStatus(); toast("Gespeichert ✔");
});
$("#cfg-key-loeschen").addEventListener("click", async () => {
  einstellungen = await api("/api/config", { body: { api_key: "" } }); keyStatus(); toast("Key entfernt");
});

// ---------------------------------------------------------------- Start
(async () => {
  tageAufbauen();
  await einstellungenLaden().catch(() => {});
  entwurfLaden();
  zaehlen().catch(() => {});
})();

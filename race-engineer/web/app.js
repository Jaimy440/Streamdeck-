"use strict";
// LMU Race Engineer – Dashboard

const $ = (id) => document.getElementById(id);
let ws = null;
let cfg = {};
let state = null;
let mapPts = [];
let lastLogKey = "";

// ------------------------------------------------------------------ Format
const lt = (t) => {
  if (t == null || !(t > 0)) return "-:--.---";
  const m = Math.floor(t / 60);
  return `${m}:${(t - m * 60).toFixed(3).padStart(6, "0")}`;
};
const sec = (t, d = 3) => (t == null ? "–" : t.toFixed(d));
const signed = (t, d = 3) => (t == null ? "–" : (t > 0 ? "+" : t < 0 ? "−" : "±") + Math.abs(t).toFixed(d));
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const clsColor = (c) => {
  c = (c || "").toLowerCase();
  if (c.includes("hyper") || c.includes("lmh") || c.includes("lmdh")) return "#ff4757";
  if (c.includes("lmp2") || c.includes("p2")) return "#3d9bff";
  if (c.includes("gt3") || c.includes("gte") || c.includes("gt")) return "#2ed573";
  if (c.includes("lmp3")) return "#b06cff";
  return "#ffc312";
};
const tyreColor = (t) => {
  const cold = cfg.reifen_kalt ?? 60, hot = cfg.reifen_heiss ?? 105;
  if (t < cold - 15) return "#3d9bff";
  if (t < cold) return "#2ad4e0";
  if (t <= hot - 8) return "#2ed573";
  if (t <= hot) return "#ffc312";
  return "#ff4757";
};
const brakeColor = (t) => (t < 200 ? "#3d9bff" : t < 650 ? "#2ed573" : t < 850 ? "#ffc312" : "#ff4757");

// ------------------------------------------------------------------ Verbindung
function connect() {
  const proto = location.protocol === "https:" ? "wss" : "ws";
  ws = new WebSocket(`${proto}://${location.host}/ws${location.search}`);
  ws.onopen = () => setBadge("verbunden", "");
  ws.onclose = () => { setBadge("getrennt – neu verbinden …", ""); setTimeout(connect, 1500); };
  ws.onmessage = (ev) => {
    const m = JSON.parse(ev.data);
    switch (m.type) {
      case "state": state = m; render(m); break;
      case "map": mapPts = m.pts || []; break;
      case "config": cfg = m.config; applyConfig(); break;
      case "say": addLog(m.text, `p${m.prio}`, labelFor(m.cat)); if (m.browser) speak(m.text, m.prio); break;
      case "log": (m.items || []).forEach((i) => addLog(i.text, `p${i.prio}`, labelFor(i.cat))); break;
      case "thinking": $("aiState").textContent = "denkt nach …"; break;
      case "answer": $("aiState").textContent = m.src === "ki" ? "Antwort von Claude" : ""; break;
      case "debrief": $("aiState").textContent = ""; addLog(m.text, "debrief", "KI-Rennanalyse"); break;
    }
  };
}
const send = (o) => ws && ws.readyState === 1 && ws.send(JSON.stringify(o));
function setBadge(text, cls) { const b = $("src"); b.textContent = text; b.className = "badge " + cls; }
const CAT_LABEL = { spotter: "Spotter", flaggen: "Flaggen", sprit: "Sprit", strategie: "Strategie", reifen: "Reifen",
  rundenzeiten: "Rundenzeit", abstaende: "Abstände", position: "Position", schaden: "Schaden", technik: "Technik",
  session: "Session", wetter: "Wetter", verkehr: "Verkehr", antwort: "Antwort", system: "System" };
const labelFor = (c) => CAT_LABEL[c] || c || "";

// ------------------------------------------------------------------ Darstellung
function render(m) {
  const a = m.data;
  setBadge(m.source === "demo" ? "DEMO" : a.connected ? "LMU live" : "LMU nicht verbunden", m.source === "demo" ? "demo" : a.connected ? "live" : "");
  const waiting = !a.connected || a.waiting;
  $("waiting").classList.toggle("hidden", !waiting);
  if (waiting) return;

  const s = a.session, p = a.position, tm = a.timing, car = a.car;
  $("sessName").textContent = s.name;
  $("track").textContent = s.track;
  $("timeLeft").textContent = s.time_left != null ? fmtClock(s.time_left) : (s.max_laps ? `${tm.lap}/${s.max_laps}` : "–");
  $("posLbl").textContent = p.multi ? `Position (${car.cls})` : "Position";
  $("pos").textContent = p.multi ? `P${p.cls}/${p.cls_count}` : `P${p.overall}/${p.total}`;
  $("lap").textContent = s.max_laps ? `${tm.lap}/${s.max_laps}` : tm.lap;
  renderFlag(s, p, a);

  // Zeiten
  $("curLap").textContent = lt(tm.current);
  const d = tm.delta;
  $("delta").textContent = d == null ? "±0.000" : signed(d);
  $("delta").style.color = d == null ? "" : d > 0 ? "var(--red)" : "var(--green)";
  const f = $("deltaFill");
  const w = d == null ? 0 : Math.min(50, Math.abs(d) / 2 * 50);
  f.style.width = w + "%";
  f.style.left = d > 0 ? "50%" : 50 - w + "%";
  f.style.background = d > 0 ? "var(--red)" : "var(--green)";
  $("lastLap").textContent = lt(tm.last);
  $("bestLap").textContent = lt(tm.best);
  const valid = tm.laps.filter((l) => l.valid && l.time).map((l) => l.time).slice(-5);
  $("avgLap").textContent = valid.length >= 2 ? lt(valid.reduce((x, y) => x + y, 0) / valid.length) : "–";
  renderSectors(tm);

  // Sprit
  const fu = a.fuel;
  $("fuelFill").style.width = fu.capacity ? Math.min(100, (fu.fuel / fu.capacity) * 100) + "%" : "0";
  $("fuelTxt").textContent = `${fu.fuel.toFixed(1)} L` + (fu.capacity ? ` / ${Math.round(fu.capacity)} L` : "");
  $("fPer").textContent = fu.per_lap != null ? `${fu.per_lap.toFixed(2)} L` : "messe …";
  $("fLaps").textContent = fu.laps_left != null ? `${fu.laps_left.toFixed(1)} Rd.` : "–";
  $("fRace").textContent = fu.race_laps_left != null ? fu.race_laps_left.toFixed(1) : "–";
  $("fNeed").textContent = fu.need_finish != null ? `${fu.need_finish.toFixed(1)} L` : "–";
  $("fAdd").textContent = fu.to_add != null ? (fu.to_add > 0 ? `+${fu.to_add.toFixed(1)} L` : "reicht ✓") : "–";
  $("fStops").textContent = fu.stops ?? "–";
  const win = $("window");
  if (fu.per_lap == null) { win.className = "window"; win.textContent = "Verbrauch wird nach der ersten vollen Runde berechnet."; }
  else if (fu.laps_left < 1.6 && fu.to_add > 0) { win.className = "window crit"; win.textContent = "BOX, BOX – diese Runde rein!"; }
  else if (fu.to_add === 0) { win.className = "window ok"; win.textContent = "Sprit reicht bis ins Ziel."; }
  else if (fu.window_open) { win.className = "window warn"; win.textContent = `Boxenfenster offen – ${fu.to_add.toFixed(1)} L nachtanken.`; }
  else if (fu.window_in_laps != null) { win.className = "window"; win.textContent = `Boxenfenster öffnet in ${fu.window_in_laps} Runde(n).`; }
  else { win.className = "window"; win.textContent = s.kind === "race" ? "–" : "Kein Rennen – Hochrechnung aus."; }
  const ve = a.energy;
  $("veBox").classList.toggle("hidden", !ve);
  if (ve) {
    $("veFill").style.width = ve.level + "%";
    $("veTxt").textContent = `${ve.level.toFixed(1)} %`;
    $("vePer").textContent = ve.per_lap != null ? `${ve.per_lap.toFixed(2)} %` : "messe …";
    $("veLaps").textContent = ve.laps_left != null ? `${ve.laps_left.toFixed(1)} Rd.` : "–";
  }

  renderLaps(tm);
  renderDrive(car);
  renderTyres(a);
  renderRelative(a, m.spotter);
  renderStandings(a);
  drawMap(a);
  drawRadar(m.spotter);
  const rain = s.raining < 0.05 ? "trocken" : s.raining < 0.3 ? "leichter Regen" : "Regen";
  $("weather").textContent = `Luft ${Math.round(s.air_temp)}° · Strecke ${Math.round(s.track_temp)}° · ${rain} · ${Math.round(s.wetness * 100)}% nass`;
}

function fmtClock(t) {
  t = Math.max(0, Math.round(t));
  const h = Math.floor(t / 3600), m = Math.floor((t % 3600) / 60), s = t % 60;
  return h ? `${h}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}` : `${m}:${String(s).padStart(2, "0")}`;
}

function renderFlag(s, p, a) {
  const el = $("flag");
  let cls = "", txt = "–";
  if (s.phase === 8 || a.session.finished) { cls = "checkered"; txt = "ZIEL"; }
  else if (s.phase === 6) { cls = "yellow"; txt = "FCY / SC"; }
  else if (p.flag === 6) { cls = "blue"; txt = "BLAU"; }
  else if ((s.sector_flags || []).some((f) => f === 1)) {
    cls = "yellow"; txt = "GELB S" + (s.sector_flags.findIndex((f) => f === 1) + 1);
  } else if (s.phase === 5) { cls = "green"; txt = "GRÜN"; }
  else if (s.phase <= 4) { txt = ["Garage", "Warm-up", "Grid", "Formation", "Start"][s.phase] || "–"; }
  el.className = "flag " + cls;
  el.textContent = txt;
}

function renderSectors(tm) {
  const cur = [tm.s1, tm.s2, null];
  const last = [tm.last_s1, tm.last_s2, tm.last_s3];
  const best = [tm.best_s1, tm.best_s2, null];
  for (let i = 0; i < 3; i++) {
    const el = $("sec" + (i + 1));
    const showCur = i < tm.sector - 1 && cur[i] != null;
    const v = showCur ? cur[i] : last[i];
    el.lastElementChild.textContent = v != null ? sec(v) : "–";
    el.className = "sector" + (v != null && best[i] != null ? (v <= best[i] + 0.001 ? " best" : v - best[i] < 0.3 ? " pb" : " slow") : "");
  }
}

function renderLaps(tm) {
  const best = tm.best;
  const rows = tm.laps.slice().reverse().map((l) => {
    const d = l.time && best ? l.time - best : null;
    const tags = (l.pit ? "BOX " : "") + (l.yellow ? "GELB" : "");
    return `<tr><td>${l.lap}</td><td class="${l.time && Math.abs(l.time - best) < 0.001 ? "purple" : ""}">${lt(l.time)}</td>` +
      `<td>${d == null ? "–" : d < 0.001 ? "★" : "+" + d.toFixed(3)}</td><td>${l.fuel != null ? l.fuel.toFixed(2) : "–"}</td>` +
      `<td class="small">${tags}</td></tr>`;
  });
  $("lapsTbl").tBodies[0].innerHTML = rows.join("") || `<tr><td colspan="5" class="small">Noch keine Runde abgeschlossen</td></tr>`;
}

function renderDrive(car) {
  $("gear").textContent = car.gear < 0 ? "R" : car.gear === 0 ? "N" : car.gear;
  $("speed").textContent = car.speed;
  $("rpm").textContent = car.rpm;
  $("thr").style.height = car.throttle * 100 + "%";
  $("brk").style.height = car.brake * 100 + "%";
  $("limiter").classList.toggle("on", !!car.limiter);
  $("bb").textContent = car.brake_bias != null ? `BB ${car.brake_bias.toFixed(1)}%` : "BB –";
  const n = 10, frac = car.max_rpm ? car.rpm / car.max_rpm : 0;
  const sh = $("shift");
  if (sh.children.length !== n) sh.innerHTML = "<i></i>".repeat(n);
  for (let i = 0; i < n; i++) {
    const thr = 0.72 + (i / n) * 0.25;
    const on = frac >= thr;
    const col = frac > 0.97 ? "#3d9bff" : i < 4 ? "#2ed573" : i < 7 ? "#ffc312" : "#ff4757";
    sh.children[i].style.background = on ? col : "";
  }
}

function renderTyres(a) {
  a.tyres.forEach((t, i) => {
    const el = $("ty" + i);
    el.classList.toggle("flat", t.flat);
    el.innerHTML =
      `<div class="row"><b>${t.name}</b><span>${t.carcass ? "Karkasse " + Math.round(t.carcass) + "°" : ""}</span></div>` +
      `<div class="temps">${t.temps.map((x) => `<div style="background:${tyreColor(x)}">${Math.round(x)}</div>`).join("")}</div>` +
      `<div class="row"><span>Druck</span><b>${t.pressure.toFixed(1)} kPa</b></div>` +
      `<div class="row"><span>Bremse</span><b style="color:${brakeColor(t.brake_temp)}">${Math.round(t.brake_temp)}°</b></div>` +
      `<div class="row"><span>Profil</span><b>${Math.round(t.wear * 100)}%</b></div>` +
      `<div class="wear"><div style="width:${t.wear * 100}%;background:${t.wear > 0.5 ? "var(--green)" : t.wear > 0.25 ? "var(--yellow)" : "var(--red)"}"></div></div>`;
  });
  $("compound").textContent = a.car.compound ? "· " + a.car.compound : "";
  const dm = a.damage, d = $("dmg");
  d.className = "dmg l" + dm.level;
  d.textContent = dm.detached ? "Teile verloren!" : dm.level === 0 ? "Kein Schaden" : dm.level === 1 ? "Leichter Schaden" : "Schwerer Schaden";
  $("engine").innerHTML = `Wasser ${Math.round(a.car.water)}°<br>Öl ${Math.round(a.car.oil)}°`;
  $("engine").style.color = a.car.overheating ? "var(--red)" : "";
}

function renderRelative(a, spot) {
  const rows = a.relative.map((r) => {
    const c = ["", r.me ? "me" : "", r.faster_cls ? "faster" : "", r.lapped > 0 ? "lapped-up" : r.lapped < 0 ? "lapped-down" : ""].join(" ");
    return `<tr class="${c}"><td class="cls" style="background:${clsColor(r.cls)}"></td><td>P${r.place}</td>` +
      `<td class="name">${esc(r.driver)}</td><td style="text-align:right">${r.me ? "" : signed(-r.rel, 1)}</td></tr>`;
  });
  $("relTbl").tBodies[0].innerHTML = rows.join("");
  const g = a.gaps || {};
  $("gapAhead").textContent = g.ahead != null ? (g.ahead_laps ? `${g.ahead_laps} Rd.` : g.ahead.toFixed(1) + " s") : "–";
  $("gapBehind").textContent = g.behind != null ? (g.behind_laps ? `${g.behind_laps} Rd.` : g.behind.toFixed(1) + " s") : "–";
  setTrend($("trendAhead"), g.ahead_trend, true);
  setTrend($("trendBehind"), g.behind_trend, false);
  const st = $("spotState");
  const map = { frei: "frei", links: "◀ Auto links", rechts: "Auto rechts ▶", beide: "◀ drei breit ▶" };
  st.textContent = map[spot.state] || spot.state;
  st.classList.toggle("active", spot.state !== "frei");
}
function setTrend(el, tr, ahead) {
  if (tr == null || Math.abs(tr) < 0.05) { el.textContent = ""; return; }
  const good = ahead ? tr < 0 : tr > 0;
  el.textContent = (tr > 0 ? "+" : "−") + Math.abs(tr).toFixed(2) + "/Rd";
  el.className = "trend " + (good ? "good" : "bad");
}

function renderStandings(a) {
  const filter = $("standFilter").value;
  const me = a.standings.find((s) => s.me);
  const list = a.standings.filter((s) => filter === "all" || !me || s.cls === me.cls);
  const rows = list.map((s) => {
    const gap = s.me ? "–" : s.laps_me ? `${s.laps_me > 0 ? "+" : ""}${s.laps_me} Rd.` : signed(s.gap_me, 1);
    return `<tr class="${s.me ? "me" : ""} ${s.pit ? "pit" : ""}"><td><span class="cls-dot" style="background:${clsColor(s.cls)}"></span>${filter === "all" ? s.place : s.cls_place}</td>` +
      `<td class="name" title="${esc(s.vehicle)}">${esc(s.driver)}</td><td>${lt(s.best)}</td><td>${lt(s.last)}</td><td>${gap}</td><td>${s.pit ? "BOX" : s.stops}</td></tr>`;
  });
  $("standTbl").tBodies[0].innerHTML = rows.join("");
}

// ------------------------------------------------------------------ Karte & Radar
function fitCanvas(c) {
  const r = c.getBoundingClientRect(), dpr = window.devicePixelRatio || 1;
  if (c.width !== Math.round(r.width * dpr) || c.height !== Math.round(r.height * dpr)) {
    c.width = Math.round(r.width * dpr); c.height = Math.round(r.height * dpr);
  }
  return dpr;
}
function drawMap(a) {
  const c = $("map"), ctx = c.getContext("2d");
  const dpr = fitCanvas(c);
  ctx.clearRect(0, 0, c.width, c.height);
  const pts = mapPts.length > 20 ? mapPts : null;
  const cars = a.cars_pos;
  const src = pts || cars.map((x) => [x.x, x.z]);
  if (!src.length) return;
  let minx = Infinity, maxx = -Infinity, minz = Infinity, maxz = -Infinity;
  src.forEach(([x, z]) => { minx = Math.min(minx, x); maxx = Math.max(maxx, x); minz = Math.min(minz, z); maxz = Math.max(maxz, z); });
  const pad = 14 * dpr, W = c.width - 2 * pad, H = c.height - 2 * pad;
  const k = Math.min(W / (maxx - minx || 1), H / (maxz - minz || 1));
  const ox = pad + (W - (maxx - minx) * k) / 2, oz = pad + (H - (maxz - minz) * k) / 2;
  const P = (x, z) => [ox + (x - minx) * k, oz + (maxz - z) * k];
  if (pts) {
    ctx.lineWidth = 7 * dpr; ctx.strokeStyle = "#2a323c"; ctx.lineJoin = "round";
    ctx.beginPath(); pts.forEach(([x, z], i) => { const [px, py] = P(x, z); i ? ctx.lineTo(px, py) : ctx.moveTo(px, py); });
    if (mapPts.length > 50) ctx.closePath();
    ctx.stroke();
  } else {
    ctx.fillStyle = "#8693a1"; ctx.font = `${12 * dpr}px sans-serif`;
    ctx.fillText("Streckenkarte wird in der ersten Runde aufgezeichnet …", pad, pad + 10 * dpr);
  }
  cars.slice().sort((x, y) => x.me - y.me).forEach((car) => {
    if (car.pit) return;
    const [px, py] = P(car.x, car.z);
    ctx.beginPath(); ctx.arc(px, py, (car.me ? 7 : 4.5) * dpr, 0, Math.PI * 2);
    ctx.fillStyle = car.me ? "#ffffff" : clsColor(car.cls); ctx.fill();
    if (car.me) { ctx.lineWidth = 3 * dpr; ctx.strokeStyle = "#ff4d2e"; ctx.stroke(); }
  });
}
function drawRadar(spot) {
  const c = $("radar"), ctx = c.getContext("2d");
  const dpr = window.devicePixelRatio || 1;
  if (c.width !== 120 * dpr) { c.width = 120 * dpr; c.height = 200 * dpr; c.style.width = "120px"; c.style.height = "200px"; }
  ctx.clearRect(0, 0, c.width, c.height);
  const cx = c.width / 2, cy = c.height / 2, s = 5.5 * dpr; // Pixel pro Meter
  ctx.strokeStyle = "#242b34"; ctx.lineWidth = dpr;
  for (const r of [10, 20]) { ctx.beginPath(); ctx.arc(cx, cy, r * s, 0, Math.PI * 2); ctx.stroke(); }
  const car = (lon, lat, col) => { ctx.fillStyle = col; ctx.fillRect(cx - lat * s - 1 * s, cy - lon * s - 2.4 * s, 2 * s, 4.8 * s); };
  (spot.radar || []).forEach((r) => {
    const close = Math.abs(r.lon) < 5 && Math.abs(r.lat) < 5.5;
    car(r.lon, r.lat, close ? "#ffc312" : clsColor(r.cls));
  });
  car(0, 0, "#ffffff");
}

// ------------------------------------------------------------------ Log & Chat
function addLog(text, cls, meta) {
  const key = text + cls;
  if (key === lastLogKey && cls !== "q") return;
  lastLogKey = key;
  const el = document.createElement("div");
  el.className = "msg " + cls;
  el.innerHTML = (meta ? `<div class="meta">${esc(meta)}</div>` : "") + esc(text);
  const log = $("log");
  log.appendChild(el);
  while (log.children.length > 80) log.removeChild(log.firstChild);
  log.scrollTop = log.scrollHeight;
}
$("askForm").addEventListener("submit", (e) => {
  e.preventDefault();
  const q = $("askInput").value.trim();
  if (!q) return;
  addLog(q, "q", "Du");
  send({ type: "ask", q });
  $("askInput").value = "";
});
document.querySelectorAll(".quick button[data-r]").forEach((b) => b.addEventListener("click", () => send({ type: "report", which: b.dataset.r })));
$("debriefBtn").addEventListener("click", () => { addLog("Rennanalyse anfordern", "q", "Du"); send({ type: "debrief" }); });
$("muteBtn").addEventListener("click", () => send({ type: "report", which: "stumm" }));
$("demoBtn").addEventListener("click", () => send({ type: "set", key: "quelle", value: "demo" }));
$("standFilter").addEventListener("change", () => state && renderStandings(state.data));

// Spracheingabe (Chrome/Edge: Web Speech API)
const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
let rec = null;
if (!SR) $("micBtn").title = "Spracheingabe wird von diesem Browser nicht unterstützt (Chrome/Edge nutzen)";
function startMic() {
  if (!SR) { addLog("Spracheingabe geht nur in Chrome oder Edge.", "p2", "System"); return; }
  if (rec) { rec.stop(); return; }
  rec = new SR();
  rec.lang = "de-DE"; rec.interimResults = false; rec.maxAlternatives = 1;
  $("micBtn").classList.add("rec");
  rec.onresult = (e) => {
    const q = e.results[0][0].transcript;
    addLog(q, "q", "Du (Sprache)");
    send({ type: "ask", q });
  };
  rec.onend = () => { $("micBtn").classList.remove("rec"); rec = null; };
  rec.onerror = () => { $("micBtn").classList.remove("rec"); rec = null; };
  rec.start();
}
$("micBtn").addEventListener("click", startMic);
document.addEventListener("keydown", (e) => { if (e.key === "F2") { e.preventDefault(); startMic(); } });

// Sprachausgabe im Browser (optional)
let deVoice = null;
function pickVoice() {
  const vs = speechSynthesis.getVoices();
  deVoice = vs.find((v) => v.lang && v.lang.toLowerCase().startsWith("de") && /natural|online/i.test(v.name)) ||
    vs.find((v) => v.lang && v.lang.toLowerCase().startsWith("de")) || null;
}
if ("speechSynthesis" in window) { pickVoice(); speechSynthesis.onvoiceschanged = pickVoice; }
function speak(text, prio) {
  if (!("speechSynthesis" in window)) return;
  if (prio === 0) speechSynthesis.cancel();
  const u = new SpeechSynthesisUtterance(text);
  u.lang = "de-DE"; if (deVoice) u.voice = deVoice;
  u.rate = 1 + (cfg.sprechtempo || 0) * 0.08;
  speechSynthesis.speak(u);
}

// ------------------------------------------------------------------ Einstellungen
const ANN = { spotter: "Spotter (links/rechts)", flaggen: "Flaggen & Strafen", sprit: "Sprit & Energie", strategie: "Boxenstopp & Strategie",
  reifen: "Reifen", rundenzeiten: "Rundenzeiten", abstaende: "Abstände", position: "Positionswechsel", schaden: "Schaden",
  technik: "Motor & Bremsen", session: "Restzeit & Ziel", wetter: "Wetter", verkehr: "Klassen-Verkehr" };
function applyConfig() {
  $("muteBtn").textContent = cfg.stumm ? "🔇" : "🔊";
  $("aiState").textContent = cfg.ki_verfuegbar ? "· Claude aktiv" : "· eingebaute Antworten";
  $("debriefBtn").title = cfg.ki_verfuegbar ? "Rennanalyse durch Claude" : "Benötigt einen Anthropic-API-Schlüssel";
  document.querySelectorAll("#settings [data-k]").forEach((el) => {
    const v = cfg[el.dataset.k];
    if (el.type === "checkbox") el.checked = !!v; else if (v != null) el.value = v;
  });
  const g = $("annGrid");
  g.innerHTML = Object.entries(ANN).map(([k, l]) =>
    `<label class="chk"><input type="checkbox" data-a="${k}" ${cfg.ansagen && cfg.ansagen[k] !== false ? "checked" : ""}> ${l}</label>`).join("");
  g.querySelectorAll("input").forEach((el) => el.addEventListener("change", () => send({ type: "set", key: "ansagen." + el.dataset.a, value: el.checked })));
}
document.querySelectorAll("#settings [data-k]").forEach((el) => {
  el.addEventListener("change", () => {
    let v = el.type === "checkbox" ? el.checked : el.value;
    if (el.type === "number" || el.type === "range") v = Number(v);
    send({ type: "set", key: el.dataset.k, value: v });
  });
});
$("setBtn").addEventListener("click", () => $("settings").classList.remove("hidden"));
$("setClose").addEventListener("click", () => $("settings").classList.add("hidden"));
$("settings").addEventListener("click", (e) => { if (e.target.id === "settings") $("settings").classList.add("hidden"); });

connect();

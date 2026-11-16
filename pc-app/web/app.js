"use strict";
const $ = (id) => document.getElementById(id);

// ---------------------------------------------------------------- Icons (Lucide, MIT)
const ICONS = {
  sliders: '<path d="M4 21v-7M4 10V3M12 21v-9M12 8V3M20 21v-5M20 12V3M2 14h4M10 8h4M18 16h4"/>',
  music: '<path d="M9 18V5l12-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/>',
  globe: '<circle cx="12" cy="12" r="10"/><path d="M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20M2 12h20"/>',
  minus: '<path d="M5 12h14"/>',
  plus: '<path d="M5 12h14M12 5v14"/>',
  volume: '<path d="M11 5 6 9H2v6h4l5 4V5Z"/><path d="M15.5 8.5a5 5 0 0 1 0 7M19 5a10 10 0 0 1 0 14"/>',
  voldown: '<path d="M11 5 6 9H2v6h4l5 4V5Z"/><path d="M16 12h6"/>',
  volup: '<path d="M11 5 6 9H2v6h4l5 4V5Z"/><path d="M16 12h6M19 9v6"/>',
  volumex: '<path d="M11 5 6 9H2v6h4l5 4V5Z"/><path d="m22 9-6 6M16 9l6 6"/>',
  mic: '<rect x="9" y="2" width="6" height="12" rx="3"/><path d="M19 10v2a7 7 0 0 1-14 0v-2M12 19v3"/>',
  micoff: '<path d="m2 2 20 20M18.9 13.4A7 7 0 0 0 19 12v-2M5 10v2a7 7 0 0 0 12 5M15 9.3V5a3 3 0 0 0-5.7-1.3M9 9v3a3 3 0 0 0 5.1 2.1M12 19v3"/>',
  headphones: '<path d="M3 14h3a2 2 0 0 1 2 2v3a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-7a9 9 0 0 1 18 0v7a2 2 0 0 1-2 2h-1a2 2 0 0 1-2-2v-3a2 2 0 0 1 2-2h3"/>',
  ban: '<circle cx="12" cy="12" r="10"/><path d="m4.9 4.9 14.2 14.2"/>',
  sync: '<path d="M3 12a9 9 0 0 1 15-6.7L21 8M21 3v5h-5M21 12a9 9 0 0 1-15 6.7L3 16M3 21v-5h5"/>',
  shuffle: '<path d="M2 18h1.4c1.3 0 2.5-.6 3.3-1.7l6.1-8.6c.7-1.1 2-1.7 3.3-1.7H22M18 2l4 4-4 4M2 6h1.9c1.5 0 2.9.9 3.6 2.2M22 18h-5.9c-1.3 0-2.6-.7-3.3-1.8l-.5-.8M18 14l4 4-4 4"/>',
  repeat: '<path d="m17 2 4 4-4 4M3 11v-1a4 4 0 0 1 4-4h14M7 22l-4-4 4-4M21 13v1a4 4 0 0 1-4 4H3"/>',
  prev: '<path d="M19 20 9 12l10-8v16ZM5 19V5"/>',
  next: '<path d="m5 4 10 8-10 8V4ZM19 5v14"/>',
  playc: '<circle cx="12" cy="12" r="10"/><path d="M10 8.5v7l5.5-3.5Z"/>',
  pausec: '<circle cx="12" cy="12" r="10"/><path d="M10 9v6M14 9v6"/>',
  back10: '<path d="M11 19 2 12l9-7v14ZM22 19l-9-7 9-7v14Z"/>',
  fwd10: '<path d="m13 19 9-7-9-7v14ZM2 19l9-7-9-7v14Z"/>',
  gauge: '<path d="m12 14 4-4"/><path d="M3.34 19a10 10 0 1 1 17.32 0"/>',
  search: '<circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/>',
  link: '<path d="M10 13a5 5 0 0 0 7.5.5l3-3a5 5 0 0 0-7-7l-1.7 1.7M14 11a5 5 0 0 0-7.5-.5l-3 3a5 5 0 0 0 7 7l1.7-1.7"/>',
  heart: '<path d="M19 14c1.5-1.5 3-3.2 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.8 0-3 .5-4.5 2-1.5-1.5-2.7-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4 3 5.5l7 7Z"/>',
  logout: '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9"/>',
  spotify: '<circle cx="12" cy="12" r="10"/><path d="M7 9.5c3.5-1 7.5-.6 10.5 1M7.5 13c3-.8 6-.4 8.5 1M8 16.3c2.3-.6 4.6-.3 6.5.8"/>',
};
const svg = (n) => `<svg viewBox="0 0 24 24" aria-hidden="true">${ICONS[n] || ""}</svg>`;
document.querySelectorAll("i[data-icon]").forEach((e) => (e.innerHTML = svg(e.dataset.icon)));

const C = { cyan: "#22d3ee", green: "#22e07a", spotify: "#1ed760", blue: "#3b82f6", blurple: "#6d78ff",
  red: "#ff453a", orange: "#ff9f0a", purple: "#bf5af2", white: "#e5e5ea" };
const CYCLE = [C.cyan, C.green, C.purple, C.orange, C.blue, C.blurple];

// ---------------------------------------------------------------- Bausteine
function el(tag, cls, text) {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (text !== undefined) e.textContent = text;
  return e;
}
/** Eine Deck-Taste. */
function key({ icon, emoji, letter, label, accent = C.cyan, img, cls = "", tap, hold }) {
  const k = el("button", "key " + cls);
  k.style.setProperty("--a", accent);
  if (img) {
    k.classList.add("img");
    k.style.backgroundImage = `url("${img.replace(/"/g, "%22")}")`;
    k.append(el("span", "shade"));
  }
  if (icon) k.insertAdjacentHTML("beforeend", svg(icon));
  if (emoji) k.append(el("span", "emoji", emoji));
  if (letter) k.append(el("span", "letter", letter));
  if (label) { k.append(el("span", "label", label)); k.classList.add("has-label"); }
  if (label) k.setAttribute("aria-label", label);
  if (tap) k.addEventListener("click", tap);
  if (hold) bindHold(k, hold);
  return k;
}
function setKeyIcon(k, name) {
  if (k.dataset.icon === name) return;
  k.dataset.icon = name;
  const old = k.querySelector(":scope > svg");
  const tmp = el("span"); tmp.innerHTML = svg(name);
  old ? old.replaceWith(tmp.firstChild) : k.prepend(tmp.firstChild);
}
// Gedrückt halten = wiederholen (z.B. Lauter)
function bindHold(k, fn) {
  let t;
  const stop = () => { clearTimeout(t); clearInterval(t); };
  k.addEventListener("touchstart", () => { t = setTimeout(() => (t = setInterval(fn, 130)), 420); }, { passive: true });
  k.addEventListener("touchend", stop);
  k.addEventListener("touchcancel", stop);
}
function strip(cls, accent) {
  const s = el("div", "strip " + cls);
  s.style.setProperty("--a", accent);
  return s;
}
const busy = new Set();
function range(id, accent, onChange, live) {
  const r = el("input", "range");
  r.type = "range"; r.id = id; r.min = 0; r.max = 100; r.value = 0;
  r.style.setProperty("--a", accent);
  r.addEventListener("input", () => { busy.add(id); paint(r); if (live) live(Number(r.value)); });
  r.addEventListener("change", () => { onChange(Number(r.value)); setTimeout(() => busy.delete(id), 700); });
  return r;
}
function paint(r) { r.style.setProperty("--p", ((r.value - r.min) / ((r.max - r.min) || 1)) * 100 + "%"); }
function setRange(r, value, max) {
  if (!r) return;
  if (max !== undefined) r.max = max;
  if (!busy.has(r.id)) r.value = value;
  paint(r);
}
const fmt = (s) => {
  s = Math.max(0, Math.floor(s || 0));
  const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), x = String(s % 60).padStart(2, "0");
  return h ? `${h}:${String(m).padStart(2, "0")}:${x}` : `${m}:${x}`;
};

// ---------------------------------------------------------------- Verbindung & dauerhafter Login
const store = {
  get(k) { try { return localStorage.getItem(k); } catch (e) { return null; } },
  set(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* egal */ } },
};
let token = new URLSearchParams(location.search).get("token");
if (token) store.set("pcdeck_token", token);
else token = store.get("pcdeck_token");

let ws = null, retry = 0, everConnected = false;
let S = null, SP = null, SP_at = 0, VM = null, VM_at = 0, playlists = null;

function connect() {
  const proto = location.protocol === "https:" ? "wss" : "ws";
  ws = new WebSocket(`${proto}://${location.host}/ws${token ? "?token=" + encodeURIComponent(token) : ""}`);
  ws.onopen = () => {
    retry = 0; everConnected = true; setStatus(true);
    if (page === "setup") showPage(store.get("pcdeck_page") || "control");
  };
  ws.onclose = () => {
    setStatus(false);
    if (!everConnected && retry >= 2) showPage("setup");
    setTimeout(connect, Math.min(5000, 400 * 2 ** retry++));
  };
  ws.onmessage = (ev) => {
    const m = JSON.parse(ev.data);
    if (m.type === "state") onState(m);
    else if (m.type === "spotify_player") { SP = m.data; SP_at = Date.now(); updateSpotify(); }
    else if (m.type === "spotify_playlists") { playlists = m.data; buildSpotify(); }
    else if (m.type === "chrome_media") { VM = m.data; VM_at = Date.now(); updateChrome(); }
    else if (m.type === "toast") toast(m.text, m.error);
  };
}
function send(cmd, extra = {}) {
  if (ws && ws.readyState === 1) ws.send(JSON.stringify({ cmd, ...extra }));
  else toast("Nicht verbunden", true);
}
function setStatus(on) {
  $("status").className = "status " + (on ? "on" : "off");
  $("statusText").textContent = on ? "Verbunden" : "Getrennt";
}
document.addEventListener("visibilitychange", () => {
  if (!document.hidden && (!ws || ws.readyState > 1)) { retry = 0; connect(); }
});

// ---------------------------------------------------------------- Seiten
const PAGES = ["control", "spotify", "chrome"];
const NAMES = { control: "Steuerung", spotify: "Spotify", chrome: "Chrome", setup: "Verbinden" };
let page = null;
function showPage(p) {
  page = p;
  for (const k of [...PAGES, "setup"]) $("page-" + k).hidden = k !== p;
  document.querySelectorAll(".pager button").forEach((b) => b.classList.toggle("active", b.dataset.page === p));
  $("pageName").textContent = NAMES[p];
  const spOn = p === "spotify" && S && S.spotify.logged_in;
  $("spSearch").hidden = $("spReload").hidden = $("spLogout").hidden = !spOn;
  $("discordReset").hidden = p !== "control";
  if (p !== "setup") store.set("pcdeck_page", p);
  if (spOn && !playlists) send("spotify_playlists");
  $("stage").scrollTop = 0;
}
document.querySelectorAll(".pager button").forEach((b) => (b.onclick = () => showPage(b.dataset.page)));
// Wischen zwischen den Seiten
(() => {
  let x0 = null, y0 = 0;
  $("stage").addEventListener("touchstart", (e) => {
    if (e.target.closest("input")) { x0 = null; return; }
    x0 = e.touches[0].clientX; y0 = e.touches[0].clientY;
  }, { passive: true });
  $("stage").addEventListener("touchend", (e) => {
    if (x0 === null || page === "setup") return;
    const dx = e.changedTouches[0].clientX - x0, dy = e.changedTouches[0].clientY - y0;
    if (Math.abs(dx) > 70 && Math.abs(dy) < 45) {
      const i = PAGES.indexOf(page) + (dx < 0 ? 1 : -1);
      if (i >= 0 && i < PAGES.length) showPage(PAGES[i]);
    }
  }, { passive: true });
})();

function onState(s) {
  const first = !S;
  const prev = S;
  S = s;
  const sig = (o) => JSON.stringify(o);
  if (first || sig(prev.buttons) !== sig(s.buttons)) buildControl();
  if (first || sig(prev.spotify) !== sig(s.spotify)) {
    if (!s.spotify.logged_in) playlists = null;
    buildSpotify();
    if (page === "spotify") showPage("spotify");
  }
  if (first || sig(prev.favorites) !== sig(s.favorites) || prev.chrome_ext !== s.chrome_ext) buildChrome();
  updateControl();
  updateChrome();
}

// ================================================================ Steuerung
const K = {};
function buildControl() {
  const d = $("deckControl");
  d.replaceChildren();
  const vs = strip("", C.cyan);
  const col = el("div", "strip-col");
  K.volText = el("div", "strip-big", "--%");
  let t;
  K.volRange = range("volRange", C.cyan, (v) => send("volume_set", { value: v }), (v) => {
    K.volText.textContent = v + "%";
    clearTimeout(t); t = setTimeout(() => send("volume_set", { value: v }), 50);
  });
  col.append(el("div", "strip-kicker", "PC-Lautstärke"), K.volText, K.volRange);
  vs.append(col);
  d.append(vs);

  d.append(
    key({ icon: "voldown", label: "Leiser", accent: C.cyan, tap: () => send("volume_down"), hold: () => send("volume_down") }),
    key({ icon: "volup", label: "Lauter", accent: C.cyan, tap: () => send("volume_up"), hold: () => send("volume_up") }),
    K.mute = key({ icon: "volumex", label: "PC stumm", accent: C.orange, tap: () => send("toggle_mute") }),
    K.dMute = key({ icon: "micoff", label: "DC-Mikro", accent: C.blurple, tap: () => send("discord_mute") }),
    K.deaf = key({ icon: "headphones", label: "DC-Taub", accent: C.blurple, tap: () => send("discord_deafen") }),
    K.full = key({ icon: "ban", label: "Full Mute", accent: C.red, tap: () => send("full_mute") }),
    K.win = key({ icon: "mic", label: "Win-Mikro", accent: C.green, tap: () => send("mic_mute") }),
  );
  S.buttons.forEach((b, i) => d.append(key({ emoji: b.icon || "•", label: b.label, accent: CYCLE[i % CYCLE.length],
    tap: () => send("button", { index: i }) })));
}
function updateControl() {
  if (!K.volText) return;
  if (!busy.has("volRange")) K.volText.textContent = S.muted ? "Stumm" : S.volume + "%";
  setRange(K.volRange, S.volume);
  K.mute.classList.toggle("on", S.muted);
  K.dMute.classList.toggle("on", S.discord.muted || S.discord.deafened);
  K.deaf.classList.toggle("on", S.discord.deafened);
  K.full.classList.toggle("on", S.discord.deafened && S.mic_muted);
  K.win.classList.toggle("on", S.mic_muted);
}
$("discordReset").onclick = () => { send("discord_reset"); toast("Discord-Anzeige zurückgesetzt"); };

// ================================================================ Spotify
const P = {};
function buildSpotify() {
  const d = $("deckSpotify");
  d.replaceChildren();
  for (const k in P) delete P[k];
  const sp = S.spotify;
  if (!sp.configured) {
    const s = strip("s3 full", C.spotify);
    const c = el("div", "strip-col");
    c.innerHTML = `<div class="strip-kicker">Spotify einrichten</div>
      <p>1. Am PC <b>developer.spotify.com/dashboard</b> → <b>Create app</b></p>
      <p>2. Redirect URI: <code></code> · <b>Web API</b> anhaken</p>
      <p>3. Client ID in <code>config.json</code> eintragen → PC-Deck neu starten</p>`;
    c.querySelector("code").textContent = sp.redirect_uri;
    s.append(c); d.append(s);
    return;
  }
  if (!sp.logged_in) {
    const s = strip("s3 full", C.spotify);
    const c = el("div", "strip-col");
    c.append(el("div", "strip-kicker", "Spotify"), el("div", "strip-title", "Mit Spotify verbinden"),
      el("div", "strip-sub", "Nur einmal nötig – der Login bleibt gespeichert. Öffnet sich am PC."));
    const b = el("button", "btn", "Verbinden");
    b.onclick = () => send("spotify_login");
    c.append(b); s.append(c); d.append(s);
    return;
  }

  // Läuft gerade
  const s = strip("s3", C.spotify);
  P.cover = el("div", "strip-cover"); P.cover.innerHTML = svg("music");
  const c = el("div", "strip-col");
  P.title = el("div", "strip-title", "Nichts läuft");
  P.sub = el("div", "strip-sub", "Tippe auf eine Playlist");
  P.prog = range("spProg", C.spotify, (v) => send("spotify_control", { action: "seek", value: v * 1000 }), (v) => (P.time.textContent = fmt(v) + " / " + fmt(SP ? SP.duration / 1000 : 0)));
  const meta = el("div", "meta");
  P.time = el("span", "time", "0:00 / 0:00");
  meta.append(P.sub, P.time);
  c.append(P.title, meta, P.prog);
  s.append(P.cover, c);
  d.append(s);

  const ctl = (action, value) => send("spotify_control", { action, value });
  const vol = (delta) => { const v = SP && SP.volume != null ? SP.volume : 50; ctl("volume", Math.max(0, Math.min(100, v + delta))); };
  d.append(
    key({ icon: "prev", label: "Zurück", accent: C.spotify, tap: () => ctl("previous") }),
    P.play = key({ icon: "playc", label: "Play", accent: C.spotify, tap: () => ctl(SP && SP.playing ? "pause" : "play") }),
    key({ icon: "next", label: "Weiter", accent: C.spotify, tap: () => ctl("next") }),
    P.shuffle = key({ icon: "shuffle", label: "Zufall", accent: C.spotify, tap: () => ctl("shuffle", !(SP && SP.shuffle)) }),
    P.repeat = key({ icon: "repeat", label: "Schleife", accent: C.spotify, tap: () => {
      const o = ["off", "context", "track"]; ctl("repeat", o[((SP ? o.indexOf(SP.repeat) : 0) + 1) % 3]);
    } }),
    P.vdown = key({ icon: "voldown", label: "Leiser", accent: C.spotify, tap: () => vol(-10) }),
    P.vup = key({ icon: "volup", label: "Lauter", accent: C.spotify, tap: () => vol(10) }),
  );

  // Playlists als Tasten mit Cover
  const q = $("spSearch").value.trim().toLowerCase();
  if (!playlists) {
    const w = strip("s3", C.spotify); const wc = el("div", "strip-col");
    wc.append(el("div", "strip-sub", "Lade Playlists …")); w.append(wc); d.append(w);
  } else {
    playlists.filter((p) => !q || p.name.toLowerCase().includes(q)).forEach((p, i) => {
      const k = key({ img: p.image, icon: p.image ? null : (p.liked ? "heart" : "music"), label: p.name,
        accent: p.liked ? C.white : C.spotify, cls: p.liked ? "liked" : "",
        tap: () => { send("spotify_play", { uri: p.uri }); toast("▶ " + p.name); } });
      k.dataset.uri = p.uri;
      d.append(k);
    });
  }
  updateSpotify();
}
function updateSpotify() {
  if (!P.title) return;
  const p = SP;
  if (p && p.image) {
    if (P.cover.dataset.src !== p.image) { P.cover.dataset.src = p.image; P.cover.innerHTML = ""; P.cover.style.backgroundImage = `url("${p.image}")`; }
  } else if (P.cover.dataset.src) { P.cover.dataset.src = ""; P.cover.style.backgroundImage = ""; P.cover.innerHTML = svg("music"); }
  P.title.textContent = p && p.title ? p.title : "Nichts läuft";
  P.sub.textContent = p && p.title ? p.artist + (p.device ? "  ·  " + p.device : "") : "Tippe auf eine Playlist";
  setKeyIcon(P.play, p && p.playing ? "pausec" : "playc");
  P.play.querySelector(".label").textContent = p && p.playing ? "Pause" : "Play";
  P.shuffle.classList.toggle("on", !!(p && p.shuffle));
  P.repeat.classList.toggle("on", !!(p && p.repeat !== "off"));
  P.vdown.classList.toggle("dim", !p || p.volume == null);
  P.vup.classList.toggle("dim", !p || p.volume == null);
  document.querySelectorAll("#deckSpotify .key[data-uri]").forEach((k) => k.classList.toggle("current", !!p && k.dataset.uri === p.context));
  tickSpotify();
}
function tickSpotify() {
  if (!P.prog) return;
  const p = SP, dur = p ? p.duration / 1000 : 0;
  let pos = p ? p.progress / 1000 : 0;
  if (p && p.playing) pos = Math.min(dur, pos + (Date.now() - SP_at) / 1000);
  setRange(P.prog, Math.round(pos), Math.max(1, Math.round(dur)));
  P.time.textContent = fmt(busy.has("spProg") ? P.prog.value : pos) + " / " + fmt(dur);
}
let searchT;
$("spSearch").addEventListener("input", () => { clearTimeout(searchT); searchT = setTimeout(buildSpotify, 150); });
$("spReload").onclick = () => { playlists = null; buildSpotify(); send("spotify_playlists", { force: true }); };
$("spLogout").onclick = () => { if (confirm("Spotify-Verbindung trennen?")) send("spotify_logout"); };

// ================================================================ Chrome
const V = {};
const SPEEDS = [1, 1.25, 1.5, 2, 0.75];
function buildChrome() {
  const d = $("deckChrome");
  d.replaceChildren();
  const s = strip("s3", C.blue);
  const c = el("div", "strip-col");
  V.title = el("div", "strip-title", "");
  V.sub = el("div", "strip-sub", "");
  V.time = el("span", "time", "");
  const meta = el("div", "meta");
  meta.append(V.sub, V.time);
  V.prog = range("vProg", C.blue, (v) => send("chrome_media", { action: "seek_to", value: v }),
    (v) => (V.time.textContent = fmt(v) + " / " + fmt(VM ? VM.duration : 0)));
  c.append(V.title, meta, V.prog);
  s.append(c);
  d.append(s);

  const m = (action, value) => send("chrome_media", { action, value });
  d.append(
    V.open = key({ icon: "search", label: "Öffnen", accent: C.blue, tap: openSheet }),
    key({ icon: "back10", label: "−10 s", accent: C.blue, tap: () => m("seek_rel", -10) }),
    V.play = key({ icon: "playc", label: "Play", accent: C.blue, tap: () => m("toggle") }),
    key({ icon: "fwd10", label: "+10 s", accent: C.blue, tap: () => m("seek_rel", 10) }),
    key({ icon: "next", label: "Nächstes", accent: C.blue, tap: () => m("next") }),
    V.mute = key({ icon: "volume", label: "Ton", accent: C.blue, tap: () => m("mute") }),
    V.speed = key({ icon: "gauge", label: "1×", accent: C.blue, tap: () => {
      const cur = VM ? VM.rate : 1; m("speed", SPEEDS[(SPEEDS.indexOf(cur) + 1) % SPEEDS.length] || 1);
    } }),
    key({ icon: "voldown", label: "Leiser", accent: C.blue, tap: () => m("volume", Math.max(0, (VM ? VM.volume : 1) - 0.1)) }),
    key({ icon: "volup", label: "Lauter", accent: C.blue, tap: () => m("volume", Math.min(1, (VM ? VM.volume : 1) + 0.1)) }),
  );
  V.videoKeys = [...d.querySelectorAll(".key")].slice(1);
  S.favorites.forEach((f) => d.append(key({ letter: (f.icon || f.label || "?").slice(0, f.icon ? 2 : 1).toUpperCase(),
    label: f.label, accent: f.color || C.blue, tap: () => send("chrome_open", { url: f.url }) })));
  updateChrome();
}
function updateChrome() {
  if (!V.title) return;
  const v = VM, ext = S && S.chrome_ext;
  V.title.textContent = v ? v.title : (ext ? "Kein Video gefunden" : "Chrome-Erweiterung fehlt");
  V.sub.textContent = v ? v.host + " · " + (v.muted ? "stumm" : Math.round(v.volume * 100) + "%") + (v.rate !== 1 ? " · " + v.rate + "×" : "")
    : (ext ? "Starte ein Video in Chrome, dann kannst du es hier steuern." : "Webseiten öffnen geht trotzdem. Für Videos: Erweiterung laden (Anleitung).");
  V.prog.hidden = V.time.hidden = !v;
  V.videoKeys.forEach((k) => k.classList.toggle("dim", !v));
  setKeyIcon(V.play, v && v.playing ? "pausec" : "playc");
  V.play.querySelector(".label").textContent = v && v.playing ? "Pause" : "Play";
  setKeyIcon(V.mute, v && v.muted ? "volumex" : "volume");
  V.mute.classList.toggle("on", !!(v && v.muted));
  V.speed.querySelector(".label").textContent = (v ? v.rate : 1) + "×";
  V.speed.classList.toggle("on", !!(v && v.rate !== 1));
  tickChrome();
}
function tickChrome() {
  const v = VM;
  if (!v || !V.prog) return;
  let pos = v.time;
  if (v.playing) pos = Math.min(v.duration || Infinity, pos + ((Date.now() - VM_at) / 1000) * (v.rate || 1));
  V.prog.disabled = !v.duration;
  setRange(V.prog, Math.round(pos), Math.max(1, Math.round(v.duration)));
  V.time.textContent = v.duration ? fmt(busy.has("vProg") ? V.prog.value : pos) + " / " + fmt(v.duration) : "LIVE";
}
function openSheet() {
  $("sheet").hidden = false;
  setTimeout(() => $("urlInput").focus(), 50);
}
function closeSheet() { $("sheet").hidden = true; $("urlInput").blur(); }
$("urlCancel").onclick = closeSheet;
$("sheet").addEventListener("click", (e) => { if (e.target === $("sheet")) closeSheet(); });
$("urlForm").addEventListener("submit", (e) => {
  e.preventDefault();
  const v = $("urlInput").value.trim();
  if (!v) return;
  send("chrome_open", { url: v });
  $("urlInput").value = "";
  closeSheet();
});

setInterval(() => { tickSpotify(); tickChrome(); }, 500);

// ---------------------------------------------------------------- Toast
let toastT;
function toast(text, error) {
  const t = $("toast");
  t.textContent = text;
  t.className = "show" + (error ? " error" : "");
  clearTimeout(toastT);
  toastT = setTimeout(() => (t.className = ""), 2600);
}

showPage(store.get("pcdeck_page") || "control");
connect();

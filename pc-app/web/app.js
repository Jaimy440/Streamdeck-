"use strict";
const $ = (id) => document.getElementById(id);

// ================================================================ Icons (Lucide, MIT)
const ICONS = {
  sliders: '<path d="M4 21v-7M4 10V3M12 21v-9M12 8V3M20 21v-5M20 12V3M2 14h4M10 8h4M18 16h4"/>',
  music: '<path d="M9 18V5l12-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/>',
  globe: '<circle cx="12" cy="12" r="10"/><path d="M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20M2 12h20"/>',
  volume: '<path d="M11 5 6 9H2v6h4l5 4V5Z"/><path d="M15.5 8.5a5 5 0 0 1 0 7M19 5a10 10 0 0 1 0 14"/>',
  voldown: '<path d="M11 5 6 9H2v6h4l5 4V5Z"/><path d="M16 12h6"/>',
  volup: '<path d="M11 5 6 9H2v6h4l5 4V5Z"/><path d="M16 12h6M19 9v6"/>',
  volumex: '<path d="M11 5 6 9H2v6h4l5 4V5Z"/><path d="m22 9-6 6M16 9l6 6"/>',
  mic: '<rect x="9" y="2" width="6" height="12" rx="3"/><path d="M19 10v2a7 7 0 0 1-14 0v-2M12 19v3"/>',
  micoff: '<path d="m2 2 20 20M18.9 13.4A7 7 0 0 0 19 12v-2M5 10v2a7 7 0 0 0 12 5M15 9.3V5a3 3 0 0 0-5.7-1.3M9 9v3a3 3 0 0 0 5.1 2.1M12 19v3"/>',
  headphones: '<path d="M3 14h3a2 2 0 0 1 2 2v3a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-7a9 9 0 0 1 18 0v7a2 2 0 0 1-2 2h-1a2 2 0 0 1-2-2v-3a2 2 0 0 1 2-2h3"/>',
  ban: '<circle cx="12" cy="12" r="10"/><path d="m4.9 4.9 14.2 14.2"/>',
  playc: '<circle cx="12" cy="12" r="10"/><path d="M10 8.5v7l5.5-3.5Z"/>',
  pausec: '<circle cx="12" cy="12" r="10"/><path d="M10 9v6M14 9v6"/>',
  prev: '<path d="M19 20 9 12l10-8v16ZM5 19V5"/>',
  next: '<path d="m5 4 10 8-10 8V4ZM19 5v14"/>',
  back10: '<path d="M11 19 2 12l9-7v14ZM22 19l-9-7 9-7v14Z"/>',
  fwd10: '<path d="m13 19 9-7-9-7v14ZM2 19l9-7-9-7v14Z"/>',
  shuffle: '<path d="M2 18h1.4c1.3 0 2.5-.6 3.3-1.7l6.1-8.6c.7-1.1 2-1.7 3.3-1.7H22M18 2l4 4-4 4M2 6h1.9c1.5 0 2.9.9 3.6 2.2M22 18h-5.9c-1.3 0-2.6-.7-3.3-1.8l-.5-.8M18 14l4 4-4 4"/>',
  repeat: '<path d="m17 2 4 4-4 4M3 11v-1a4 4 0 0 1 4-4h14M7 22l-4-4 4-4M21 13v1a4 4 0 0 1-4 4H3"/>',
  gauge: '<path d="m12 14 4-4"/><path d="M3.34 19a10 10 0 1 1 17.32 0"/>',
  search: '<circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/>',
  heart: '<path d="M19 14c1.5-1.5 3-3.2 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.8 0-3 .5-4.5 2-1.5-1.5-2.7-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4 3 5.5l7 7Z"/>',
  chat: '<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>',
  camera: '<path d="M14.5 4h-5L7 7H4a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2h-3l-2.5-3z"/><circle cx="12" cy="13" r="3"/>',
  monitor: '<rect x="2" y="3" width="20" height="14" rx="2"/><path d="M8 21h8M12 17v4"/>',
  lock: '<rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>',
  power: '<path d="M12 2v10M18.4 6.6a9 9 0 1 1-12.8 0"/>',
  gamepad: '<rect x="2" y="6" width="20" height="12" rx="3"/><path d="M6 12h4M8 10v4M15 13h.01M18 11h.01"/>',
  video: '<path d="m16 13 5.2 3.1a.5.5 0 0 0 .8-.4V8.3a.5.5 0 0 0-.8-.4L16 11"/><rect x="2" y="6" width="14" height="12" rx="2"/>',
  mail: '<rect x="2" y="4" width="20" height="16" rx="2"/><path d="m22 7-10 6L2 7"/>',
  folder: '<path d="M4 20h16a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.7-.9L9.6 3.9A2 2 0 0 0 7.9 3H4a2 2 0 0 0-2 2v13c0 1.1.9 2 2 2Z"/>',
  terminal: '<path d="m4 17 6-6-6-6M12 19h8"/>',
  code: '<path d="m16 18 6-6-6-6M8 6l-6 6 6 6"/>',
  keyboard: '<rect x="2" y="4" width="20" height="16" rx="2"/><path d="M6 8h.01M10 8h.01M14 8h.01M18 8h.01M6 12h.01M10 12h.01M14 12h.01M18 12h.01M7 16h10"/>',
  star: '<path d="M12 2l3.1 6.3 6.9 1-5 4.9 1.2 6.8L12 17.8 5.8 21l1.2-6.8-5-4.9 6.9-1z"/>',
  bolt: '<path d="M13 2 3 14h9l-1 8 10-12h-9l1-8z"/>',
  rocket: '<path d="M4.5 16.5c-1.5 1.3-2 5-2 5s3.7-.5 5-2c.7-.8.7-2.1-.1-2.9a2.2 2.2 0 0 0-2.9-.1zM12 15l-3-3a22 22 0 0 1 2-3.9A12.9 12.9 0 0 1 22 2c0 2.7-.8 7.5-6 11a22.4 22.4 0 0 1-4 2z"/>',
  home: '<path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><path d="M9 22V12h6v10"/>',
  moon: '<path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z"/>',
  sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M6.3 17.7l-1.4 1.4M19.1 4.9l-1.4 1.4"/>',
  image: '<rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="9" cy="9" r="2"/><path d="m21 15-3.1-3.1a2 2 0 0 0-2.8 0L6 21"/>',
  app: '<rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18M9 21V9"/>',
  link: '<path d="M10 13a5 5 0 0 0 7.5.5l3-3a5 5 0 0 0-7-7l-1.7 1.7M14 11a5 5 0 0 0-7.5-.5l-3 3a5 5 0 0 0 7 7l1.7-1.7"/>',
  grid: '<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>',
  pages: '<path d="M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01"/>',
  sync: '<path d="M3 12a9 9 0 0 1 15-6.7L21 8M21 3v5h-5M21 12a9 9 0 0 1-15 6.7L3 16M3 21v-5h5"/>',
  logout: '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9"/>',
  pencil: '<path d="M17 3a2.8 2.8 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z"/>',
  trash: '<path d="M3 6h18M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>',
  left: '<path d="m15 18-6-6 6-6"/>',
  right: '<path d="m9 18 6-6-6-6"/>',
  plus: '<path d="M5 12h14M12 5v14"/>',
  check: '<path d="M20 6 9 17l-5-5"/>',
  wide: '<rect x="2" y="7" width="20" height="10" rx="2"/>',
};
const svg = (n) => `<svg viewBox="0 0 24 24" aria-hidden="true">${ICONS[n] || ""}</svg>`;
document.querySelectorAll("i[data-icon]").forEach((e) => (e.innerHTML = svg(e.dataset.icon)));
// Symbole, die man im Editor auswählen kann
const PICK_ICONS = ["volup", "voldown", "volumex", "volume", "mic", "micoff", "headphones", "ban", "playc", "pausec", "prev", "next",
  "back10", "fwd10", "shuffle", "repeat", "music", "heart", "globe", "search", "video", "chat", "mail", "camera", "monitor", "gamepad",
  "keyboard", "terminal", "code", "folder", "app", "lock", "power", "moon", "sun", "home", "star", "bolt", "rocket", "image", "link", "sliders", "grid", "gauge"];

const C = { cyan: "#22d3ee", green: "#22e07a", spotify: "#1ed760", blue: "#3b82f6", blurple: "#6d78ff",
  red: "#ff453a", orange: "#ff9f0a", purple: "#bf5af2", pink: "#ff375f", yellow: "#ffd60a", white: "#e5e5ea" };
const SWATCHES = [C.cyan, C.blue, C.blurple, C.purple, C.pink, C.red, C.orange, C.yellow, C.green, C.white];

// ================================================================ Aktionen-Katalog (wie die Liste rechts im Streamdeck)
const CATALOG = [
  { cat: "System", icon: "monitor", items: [
    { a: { type: "volume_up" }, name: "Lauter", label: "Lauter", icon: "volup", color: C.cyan },
    { a: { type: "volume_down" }, name: "Leiser", label: "Leiser", icon: "voldown", color: C.cyan },
    { a: { type: "toggle_mute" }, name: "PC stumm schalten", label: "PC stumm", icon: "volumex", color: C.orange },
    { a: { type: "mic_mute" }, name: "Windows-Mikro stumm", label: "Win-Mikro", icon: "mic", color: C.green },
    { a: { type: "media", key: "play/pause media" }, name: "Medien: Play / Pause", label: "Play/Pause", icon: "playc", color: C.purple },
    { a: { type: "media", key: "next track" }, name: "Medien: Weiter", label: "Weiter", icon: "next", color: C.purple },
    { a: { type: "media", key: "previous track" }, name: "Medien: Zurück", label: "Zurück", icon: "prev", color: C.purple },
  ] },
  { cat: "Discord", icon: "chat", items: [
    { a: { type: "discord_mute" }, name: "Mikro stumm", label: "DC-Mikro", icon: "micoff", color: C.blurple },
    { a: { type: "discord_deafen" }, name: "Taub (Deafen)", label: "DC-Taub", icon: "headphones", color: C.blurple },
    { a: { type: "full_mute" }, name: "Full Mute (taub + Windows-Mikro)", label: "Full Mute", icon: "ban", color: C.red },
  ] },
  { cat: "Spotify", icon: "music", items: [
    { a: { type: "spotify_playlist" }, name: "Playlist abspielen …", label: "", icon: "music", color: C.spotify, param: "playlist" },
    { a: { type: "spotify", op: "play_pause" }, name: "Play / Pause", label: "Play", icon: "playc", color: C.spotify },
    { a: { type: "spotify", op: "next" }, name: "Nächster Song", label: "Weiter", icon: "next", color: C.spotify },
    { a: { type: "spotify", op: "previous" }, name: "Vorheriger Song", label: "Zurück", icon: "prev", color: C.spotify },
    { a: { type: "spotify", op: "shuffle" }, name: "Zufallswiedergabe", label: "Zufall", icon: "shuffle", color: C.spotify },
    { a: { type: "spotify", op: "repeat" }, name: "Wiederholen", label: "Schleife", icon: "repeat", color: C.spotify },
    { a: { type: "spotify", op: "vol_up" }, name: "Spotify lauter", label: "Lauter", icon: "volup", color: C.spotify },
    { a: { type: "spotify", op: "vol_down" }, name: "Spotify leiser", label: "Leiser", icon: "voldown", color: C.spotify },
  ] },
  { cat: "Chrome", icon: "globe", items: [
    { a: { type: "chrome_url" }, name: "Webseite öffnen (neuer Tab) …", label: "", icon: "", color: C.blue, param: "url" },
    { a: { type: "url_prompt" }, name: "Adresse eintippen", label: "Öffnen", icon: "search", color: C.blue },
    { a: { type: "chrome_video", op: "toggle" }, name: "Video Play / Pause", label: "Play", icon: "playc", color: C.blue },
    { a: { type: "chrome_video", op: "back" }, name: "Video 10 s zurück", label: "−10 s", icon: "back10", color: C.blue },
    { a: { type: "chrome_video", op: "fwd" }, name: "Video 10 s vor", label: "+10 s", icon: "fwd10", color: C.blue },
    { a: { type: "chrome_video", op: "next" }, name: "Nächstes Video", label: "Nächstes", icon: "next", color: C.blue },
    { a: { type: "chrome_video", op: "mute" }, name: "Video Ton an/aus", label: "Ton", icon: "volume", color: C.blue },
    { a: { type: "chrome_video", op: "speed" }, name: "Video-Tempo", label: "Tempo", icon: "gauge", color: C.blue },
    { a: { type: "chrome_video", op: "vol_up" }, name: "Video lauter", label: "Lauter", icon: "volup", color: C.blue },
    { a: { type: "chrome_video", op: "vol_down" }, name: "Video leiser", label: "Leiser", icon: "voldown", color: C.blue },
  ] },
  { cat: "Programme & Tasten", icon: "app", items: [
    { a: { type: "launch" }, name: "Programm / Datei / Link öffnen …", label: "", icon: "app", color: C.orange, param: "launch" },
    { a: { type: "hotkey" }, name: "Tastenkürzel …", label: "", icon: "keyboard", color: C.purple, param: "hotkey" },
    { a: { type: "command" }, name: "Konsolenbefehl (nur config.json)", label: "", icon: "terminal", color: C.red, param: "command", locked: true },
  ] },
  { cat: "Navigation", icon: "pages", items: [
    { a: { type: "page" }, name: "Zu Seite wechseln …", label: "", icon: "grid", color: C.white, param: "page" },
    { a: { type: "none" }, name: "Leer (keine Aktion)", label: "", icon: "", color: "#8e8e93" },
  ] },
  { cat: "Anzeigen (breit)", icon: "wide", items: [
    { w: "volume", name: "PC-Lautstärke mit Regler", label: "PC-Lautstärke", color: C.cyan },
    { w: "spotify_now", name: "Spotify: Läuft gerade", label: "Läuft gerade", color: C.spotify },
    { w: "chrome_video", name: "Chrome: Video mit Zeitleiste", label: "Video", color: C.blue },
    { w: "playlists", name: "Alle Spotify-Playlists als Tasten", label: "Alle Playlists", color: C.spotify },
  ] },
];
const itemKey = (it) => it.w ? "w:" + it.w : [it.a.type, it.a.op || it.a.key || ""].join(":");
const keyOf = (k) => k.widget ? "w:" + k.widget : [k.action.type, k.action.op || k.action.key || ""].join(":");
const ITEMS = new Map();
CATALOG.forEach((c) => c.items.forEach((it) => ITEMS.set(itemKey(it), { ...it, cat: c.cat })));

// ================================================================ Bausteine
function el(tag, cls, text) {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (text !== undefined) e.textContent = text;
  return e;
}
function bindHold(k, fn) {
  let t;
  const stop = () => { clearTimeout(t); clearInterval(t); };
  k.addEventListener("touchstart", () => { t = setTimeout(() => (t = setInterval(fn, 130)), 420); }, { passive: true });
  k.addEventListener("touchend", stop);
  k.addEventListener("touchcancel", stop);
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
const uid = (p = "k") => p + Math.random().toString(16).slice(2, 10);
const clone = (o) => JSON.parse(JSON.stringify(o));
function hostOf(url) {
  try { return new URL(/^[a-z]+:\/\//i.test(url) ? url : "https://" + url).hostname.replace(/^www\./, ""); } catch (e) { return ""; }
}

// ================================================================ Verbindung & dauerhafter Login
const store = {
  get(k) { try { return localStorage.getItem(k); } catch (e) { return null; } },
  set(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* egal */ } },
};
let token = new URLSearchParams(location.search).get("token");
if (token) store.set("pcdeck_token", token);
else token = store.get("pcdeck_token");

let ws = null, retry = 0, everConnected = false;
let S = null, SP = null, SP_at = 0, VM = null, VM_at = 0, playlists = null, APPS = null;
let PAGES = [];            // Layout (Seiten mit Tasten)
let pageId = store.get("pcdeck_page") || "control";
let editing = false;

function connect() {
  const proto = location.protocol === "https:" ? "wss" : "ws";
  ws = new WebSocket(`${proto}://${location.host}/ws${token ? "?token=" + encodeURIComponent(token) : ""}`);
  ws.onopen = () => { retry = 0; everConnected = true; setStatus(true); $("setupPage").hidden = true; $("deckPage").hidden = false; };
  ws.onclose = () => {
    setStatus(false);
    if (!everConnected && retry >= 2) { $("setupPage").hidden = false; $("deckPage").hidden = true; }
    setTimeout(connect, Math.min(5000, 400 * 2 ** retry++));
  };
  ws.onmessage = (ev) => {
    const m = JSON.parse(ev.data);
    if (m.type === "state") onState(m);
    else if (m.type === "spotify_player") { SP = m.data; SP_at = Date.now(); updateKeys(); }
    else if (m.type === "spotify_playlists") { playlists = m.data; renderDeck(); if (ed) renderParams(); }
    else if (m.type === "chrome_media") { VM = m.data; VM_at = Date.now(); updateKeys(); }
    else if (m.type === "apps") { APPS = m.data; if (ed) renderParams(); }
    else if (m.type === "toast") {
      toast(m.text, m.error);
      // Server hat etwas abgelehnt -> Layout wieder vom PC übernehmen
      if (m.error && S && !ed && !pe) { PAGES = clone(S.pages); renderPager(); renderDeck(); }
    }
  };
}
function send(cmd, extra = {}) {
  if (ws && ws.readyState === 1) { ws.send(JSON.stringify({ cmd, ...extra })); return true; }
  toast("Nicht verbunden", true);
  return false;
}
function setStatus(on) {
  $("status").className = "status " + (on ? "on" : "off");
  $("statusText").textContent = on ? "Verbunden" : "Getrennt";
}
document.addEventListener("visibilitychange", () => {
  if (!document.hidden && (!ws || ws.readyState > 1)) { retry = 0; connect(); }
});

function onState(s) {
  const prev = S;
  S = s;
  if (!s.spotify.logged_in) playlists = null;
  else if (!playlists && (!prev || !prev.spotify.logged_in)) send("spotify_playlists");
  const layoutChanged = !prev || JSON.stringify(prev.pages) !== JSON.stringify(s.pages)
    || JSON.stringify(prev.spotify) !== JSON.stringify(s.spotify) || prev.chrome_ext !== s.chrome_ext;
  if (layoutChanged && !ed && !pe) {
    PAGES = clone(s.pages);
    renderPager();
    renderDeck();
  } else {
    updateKeys();
  }
}
const curPage = () => PAGES.find((p) => p.id === pageId) || PAGES[0];

// ================================================================ Seiten
function showPage(id) {
  pageId = id;
  store.set("pcdeck_page", id);
  renderPager();
  renderDeck();
  $("stage").scrollTop = 0;
}
function renderPager() {
  const pg = $("pager");
  pg.replaceChildren(...PAGES.map((p) => {
    const b = el("button");
    b.innerHTML = svg(p.icon || "grid");
    b.append(el("span", "", p.name));
    b.classList.toggle("active", p.id === (curPage() || {}).id);
    b.onclick = () => (editing && p.id === curPage().id ? openPageEditor() : showPage(p.id));
    return b;
  }));
  if (editing) {
    const add = el("button", "add-page");
    add.innerHTML = svg("plus");
    add.append(el("span", "", "Seite"));
    add.onclick = () => {
      const p = { id: uid("p"), name: "Seite " + (PAGES.length + 1), icon: "grid", keys: [] };
      PAGES.push(p);
      saveLayout();
      showPage(p.id);
      openPageEditor();
    };
    pg.append(add);
  }
}
(() => {   // Wischen zwischen Seiten
  let x0 = null, y0 = 0;
  $("stage").addEventListener("touchstart", (e) => {
    if (e.target.closest("input")) { x0 = null; return; }
    x0 = e.touches[0].clientX; y0 = e.touches[0].clientY;
  }, { passive: true });
  $("stage").addEventListener("touchend", (e) => {
    if (x0 === null || !PAGES.length) return;
    const dx = e.changedTouches[0].clientX - x0, dy = e.changedTouches[0].clientY - y0;
    if (Math.abs(dx) > 70 && Math.abs(dy) < 45) {
      const i = PAGES.indexOf(curPage()) + (dx < 0 ? 1 : -1);
      if (i >= 0 && i < PAGES.length) showPage(PAGES[i].id);
    }
  }, { passive: true });
})();

function saveLayout() { send("layout_save", { pages: PAGES }); }

// ================================================================ Tastenfeld
let RENDERED = [];   // [{ el, item, kind }]
const W = {};        // Widget-Elemente

function renderDeck() {
  const page = curPage();
  if (!page) return;
  $("pageName").textContent = page.name;
  const d = $("deck");
  d.classList.toggle("editing", editing);
  d.replaceChildren();
  RENDERED = [];
  for (const k in W) delete W[k];
  page.keys.forEach((item, idx) => {
    if (item.widget === "playlists" && !editing) {
      appendPlaylists(d, item);
      return;
    }
    const e = item.widget ? buildWidget(item) : buildKey(item);
    if (editing) {
      e.classList.add("edit");
      const badge = el("span", "edit-badge");
      badge.innerHTML = svg("pencil");
      e.append(badge);
      e.addEventListener("click", (ev) => { ev.preventDefault(); ev.stopPropagation(); openEditor(page.id, idx); }, true);
    }
    d.append(e);
  });
  if (editing) {
    const add = el("button", "key add");
    add.innerHTML = svg("plus");
    add.append(el("span", "label", "Neue Taste"));
    add.onclick = () => openEditor(page.id, -1);
    d.append(add);
  }
  updateTopTools();
  updateKeys();
}

/** Aussehen einer Taste (auch für die Vorschau im Editor) */
function keyEl(item) {
  const k = el("button", "key");
  k.style.setProperty("--a", item.color || C.cyan);
  const a = item.action || {};
  const pl = a.type === "spotify_playlist" && playlists ? playlists.find((p) => p.uri === a.uri) : null;
  if (pl && pl.image && !item.icon && !item.emoji) {
    k.classList.add("img");
    k.style.backgroundImage = `url("${pl.image.replace(/"/g, "%22")}")`;
    k.append(el("span", "shade"));
  } else if (item.emoji) {
    k.append(el("span", "emoji", item.emoji));
  } else if (item.icon) {
    k.insertAdjacentHTML("beforeend", svg(item.icon));
  } else if (item.widget) {
    k.insertAdjacentHTML("beforeend", svg(item.widget === "playlists" ? "music" : "wide"));
  } else if (a.type === "chrome_url" || a.type === "launch") {
    k.append(el("span", "letter", (item.label || hostOf(a.url || a.target) || "?").slice(0, 1).toUpperCase()));
  } else if (a.type === "spotify_playlist") {
    k.insertAdjacentHTML("beforeend", svg("music"));
  }
  if (a.type === "none" && !item.label && !item.icon && !item.emoji) k.classList.add("empty");
  if (item.label) { k.append(el("span", "label", item.label)); k.classList.add("has-label"); k.setAttribute("aria-label", item.label); }
  return k;
}

function buildKey(item) {
  const k = keyEl(item);
  const a = item.action || {};
  k.addEventListener("click", () => {
    if (editing) return;
    if (a.type === "page") { if (PAGES.some((p) => p.id === a.page)) showPage(a.page); else toast("Seite nicht gefunden", true); }
    else if (a.type === "url_prompt") openSheet();
    else if (a.type === "none") toast("Noch nicht belegt – tippe oben auf ✎");
    else send("run", { key: item.id });
  });
  if (["volume_up", "volume_down"].includes(a.type) || (a.type === "spotify" && a.op.startsWith("vol")) || (a.type === "chrome_video" && a.op.startsWith("vol"))) {
    bindHold(k, () => { if (!editing) send("run", { key: item.id }); });
  }
  RENDERED.push({ el: k, item });
  return k;
}

function appendPlaylists(d, item) {
  if (!S || !S.spotify.logged_in) return;
  const q = $("spSearch").value.trim().toLowerCase();
  if (!playlists) {
    const w = strip("s3", item.color);
    const c = el("div", "strip-col");
    c.append(el("div", "strip-sub", "Lade Playlists …"));
    w.append(c); d.append(w);
    return;
  }
  playlists.filter((p) => !q || p.name.toLowerCase().includes(q)).forEach((p) => {
    const k = el("button", "key" + (p.liked ? " liked" : ""));
    k.style.setProperty("--a", p.liked ? C.white : item.color);
    if (p.image) {
      k.classList.add("img");
      k.style.backgroundImage = `url("${p.image.replace(/"/g, "%22")}")`;
      k.append(el("span", "shade"));
    } else k.insertAdjacentHTML("beforeend", svg(p.liked ? "heart" : "music"));
    k.append(el("span", "label", p.name));
    k.classList.add("has-label");
    k.onclick = () => { send("spotify_play", { uri: p.uri }); toast("▶ " + p.name); };
    RENDERED.push({ el: k, item: { action: { type: "spotify_playlist", uri: p.uri } } });
    d.append(k);
  });
}

// ---------- breite Anzeigen
function strip(cls, accent) {
  const s = el("div", "strip " + cls);
  s.style.setProperty("--a", accent);
  return s;
}
function buildWidget(item) {
  const color = item.color || C.cyan;
  if (item.widget === "playlists") {   // nur im Bearbeiten-Modus als eine Taste sichtbar
    return keyEl({ ...item, icon: item.icon || "music" });
  }
  if (item.widget === "volume") {
    const s = strip("", color);
    const col = el("div", "strip-col");
    W.volText = el("div", "strip-big", "--%");
    let t;
    W.volRange = range("volRange", color, (v) => send("volume_set", { value: v }), (v) => {
      W.volText.textContent = v + "%";
      clearTimeout(t); t = setTimeout(() => send("volume_set", { value: v }), 50);
    });
    col.append(el("div", "strip-kicker", item.label || "PC-Lautstärke"), W.volText, W.volRange);
    s.append(col);
    return s;
  }
  if (item.widget === "spotify_now") {
    const sp = S ? S.spotify : { configured: true, logged_in: true };
    if (!sp.configured || !sp.logged_in) {
      const s = strip("s3", color);
      const c = el("div", "strip-col");
      if (!sp.configured) {
        c.innerHTML = `<div class="strip-kicker">Spotify einrichten</div>
          <p>Am PC <b>developer.spotify.com/dashboard</b> → <b>Create app</b> · Redirect URI <code></code> · <b>Web API</b> anhaken.
          Dann die Client ID in <code>config.json</code> eintragen und PC-Deck neu starten.</p>`;
        c.querySelector("code").textContent = sp.redirect_uri;
      } else {
        c.append(el("div", "strip-kicker", "Spotify"), el("div", "strip-title", "Mit Spotify verbinden"),
          el("div", "strip-sub", "Nur einmal nötig – der Login bleibt gespeichert."));
        const b = el("button", "btn", "Verbinden");
        b.onclick = () => { if (!editing) send("spotify_login"); };
        c.append(b);
      }
      s.append(c);
      return s;
    }
    const s = strip("s3", color);
    W.spCover = el("div", "strip-cover"); W.spCover.innerHTML = svg("music");
    const c = el("div", "strip-col");
    W.spTitle = el("div", "strip-title", "Nichts läuft");
    W.spSub = el("div", "strip-sub", "");
    W.spTime = el("span", "time", "");
    const meta = el("div", "meta"); meta.append(W.spSub, W.spTime);
    W.spProg = range("spProg", color, (v) => send("spotify_control", { action: "seek", value: v * 1000 }),
      (v) => (W.spTime.textContent = fmt(v) + " / " + fmt(SP ? SP.duration / 1000 : 0)));
    c.append(W.spTitle, meta, W.spProg);
    s.append(W.spCover, c);
    return s;
  }
  if (item.widget === "chrome_video") {
    const s = strip("s3", color);
    const c = el("div", "strip-col");
    W.vTitle = el("div", "strip-title", "");
    W.vSub = el("div", "strip-sub", "");
    W.vTime = el("span", "time", "");
    const meta = el("div", "meta"); meta.append(W.vSub, W.vTime);
    W.vProg = range("vProg", color, (v) => send("chrome_media", { action: "seek_to", value: v }),
      (v) => (W.vTime.textContent = fmt(v) + " / " + fmt(VM ? VM.duration : 0)));
    c.append(W.vTitle, meta, W.vProg);
    s.append(c);
    return s;
  }
  return keyEl(item);
}

// ---------- Live-Zustand auf die Tasten übertragen
function setKeyIcon(k, name) {
  const old = k.querySelector(":scope > svg");
  if (!old || k.dataset.icon === name) return;
  k.dataset.icon = name;
  const tmp = el("span"); tmp.innerHTML = svg(name);
  old.replaceWith(tmp.firstChild);
}
function setLabel(k, text) { const l = k.querySelector(".label"); if (l && text) l.textContent = text; }

function updateKeys() {
  if (!S) return;
  for (const { el: k, item } of RENDERED) {
    const a = item.action || {};
    let on = false, dim = false;
    switch (a.type) {
      case "toggle_mute": on = S.muted; break;
      case "mic_mute": on = S.mic_muted; break;
      case "discord_mute": on = S.discord.muted || S.discord.deafened; break;
      case "discord_deafen": on = S.discord.deafened; break;
      case "full_mute": on = S.discord.deafened && S.mic_muted; break;
      case "spotify_playlist": k.classList.toggle("current", !!SP && SP.context === a.uri); break;
      case "spotify":
        if (a.op === "play_pause") {
          if (["playc", "pausec"].includes(item.icon)) setKeyIcon(k, SP && SP.playing ? "pausec" : "playc");
          if (["Play", "Pause"].includes(item.label)) setLabel(k, SP && SP.playing ? "Pause" : "Play");
        }
        if (a.op === "shuffle") on = !!(SP && SP.shuffle);
        if (a.op === "repeat") on = !!(SP && SP.repeat !== "off");
        if (a.op.startsWith("vol")) dim = !SP || SP.volume == null;
        break;
      case "chrome_video":
        dim = !VM;
        if (a.op === "toggle") {
          if (["playc", "pausec"].includes(item.icon)) setKeyIcon(k, VM && VM.playing ? "pausec" : "playc");
          if (["Play", "Pause"].includes(item.label)) setLabel(k, VM && VM.playing ? "Pause" : "Play");
        }
        if (a.op === "mute") { on = !!(VM && VM.muted); if (["volume", "volumex"].includes(item.icon)) setKeyIcon(k, on ? "volumex" : "volume"); }
        if (a.op === "speed") { on = !!(VM && VM.rate !== 1); setLabel(k, VM && VM.rate !== 1 ? VM.rate + "×" : item.label); }
        break;
    }
    k.classList.toggle("on", !!on);
    k.classList.toggle("dim", dim && !editing);
  }
  // Widgets
  if (W.volText) {
    if (!busy.has("volRange")) W.volText.textContent = S.muted ? "Stumm" : S.volume + "%";
    setRange(W.volRange, S.volume);
  }
  if (W.spTitle) {
    const p = SP;
    if (p && p.image) {
      if (W.spCover.dataset.src !== p.image) { W.spCover.dataset.src = p.image; W.spCover.innerHTML = ""; W.spCover.style.backgroundImage = `url("${p.image}")`; }
    } else if (W.spCover.dataset.src) { W.spCover.dataset.src = ""; W.spCover.style.backgroundImage = ""; W.spCover.innerHTML = svg("music"); }
    W.spTitle.textContent = p && p.title ? p.title : "Nichts läuft";
    W.spSub.textContent = p && p.title ? p.artist + (p.device ? " · " + p.device : "") : "Wähle eine Playlist";
  }
  if (W.vTitle) {
    const v = VM, ext = S.chrome_ext;
    W.vTitle.textContent = v ? v.title : (ext ? "Kein Video gefunden" : "Chrome-Erweiterung fehlt");
    W.vSub.textContent = v ? v.host + " · " + (v.muted ? "stumm" : Math.round(v.volume * 100) + "%") + (v.rate !== 1 ? " · " + v.rate + "×" : "")
      : (ext ? "Starte ein Video in Chrome." : "Webseiten öffnen geht trotzdem (siehe Anleitung).");
    W.vProg.hidden = W.vTime.hidden = !v;
  }
  tick();
}
function tick() {
  if (W.spProg) {
    const p = SP, dur = p ? p.duration / 1000 : 0;
    let pos = p ? p.progress / 1000 : 0;
    if (p && p.playing) pos = Math.min(dur, pos + (Date.now() - SP_at) / 1000);
    setRange(W.spProg, Math.round(pos), Math.max(1, Math.round(dur)));
    W.spTime.textContent = fmt(busy.has("spProg") ? W.spProg.value : pos) + " / " + fmt(dur);
  }
  if (W.vProg && VM) {
    const v = VM;
    let pos = v.time;
    if (v.playing) pos = Math.min(v.duration || Infinity, pos + ((Date.now() - VM_at) / 1000) * (v.rate || 1));
    W.vProg.disabled = !v.duration;
    setRange(W.vProg, Math.round(pos), Math.max(1, Math.round(v.duration)));
    W.vTime.textContent = v.duration ? fmt(busy.has("vProg") ? W.vProg.value : pos) + " / " + fmt(v.duration) : "LIVE";
  }
}
setInterval(tick, 500);

// ---------- Kopfzeile
function updateTopTools() {
  const page = curPage();
  const hasPl = page && page.keys.some((k) => k.widget === "playlists") && S && S.spotify.logged_in && !editing;
  $("spSearch").hidden = $("spReload").hidden = $("spLogout").hidden = !hasPl;
  $("discordReset").hidden = editing || !page || !page.keys.some((k) => k.action && /^discord|full_mute/.test(k.action.type));
  $("editBtn").hidden = editing;
  $("doneBtn").hidden = $("pageSettings").hidden = $("editChip").hidden = !editing;
}
function setEditing(on) {
  editing = on;
  renderPager();
  renderDeck();
}
$("editBtn").onclick = () => setEditing(true);
$("doneBtn").onclick = () => setEditing(false);
$("pageSettings").onclick = () => openPageEditor();
let searchT;
$("spSearch").addEventListener("input", () => { clearTimeout(searchT); searchT = setTimeout(renderDeck, 150); });
$("spReload").onclick = () => { playlists = null; renderDeck(); send("spotify_playlists", { force: true }); };
$("spLogout").onclick = () => { if (confirm("Spotify-Verbindung trennen?")) send("spotify_logout"); };
$("discordReset").onclick = () => { send("discord_reset"); toast("Discord-Anzeige zurückgesetzt"); };

// ================================================================ Tasten-Editor
let ed = null;   // { pageId, idx, draft, auto, open: Set(Kategorien) }

function openEditor(pid, idx) {
  const page = PAGES.find((p) => p.id === pid);
  const draft = idx >= 0 ? clone(page.keys[idx]) : { id: uid(), label: "", icon: "", emoji: "", color: C.cyan, action: { type: "none" } };
  const cur = ITEMS.get(keyOf(draft));
  ed = { pageId: pid, idx, draft, auto: idx < 0, open: new Set(cur && keyOf(draft) !== "none:" ? [cur.cat] : []), appFilter: "" };
  $("edTitle").textContent = idx >= 0 ? "Taste bearbeiten" : "Neue Taste";
  $("edDelete").hidden = $("edLeft").hidden = $("edRight").hidden = $("edMovePage").hidden = idx < 0;
  const mp = $("edMovePage");
  mp.replaceChildren(...PAGES.map((p) => { const o = el("option", "", p.id === pid ? "Seite: " + p.name : "→ " + p.name); o.value = p.id; return o; }));
  mp.value = pid;
  $("edLabel").value = draft.label;
  $("edEmoji").value = draft.emoji || "";
  if (draft.action && ["launch"].includes(draft.action.type) && !APPS) send("apps_list");
  renderEditor();
  $("editor").hidden = false;
}
function closeEditor() { ed = null; $("editor").hidden = true; renderDeck(); }

function renderEditor() {
  const d = ed.draft;
  // Vorschau
  const pv = $("edPreview");
  pv.replaceChildren(d.widget && d.widget !== "playlists" ? previewStrip(d) : keyEl(d));
  // Farben
  $("edColors").replaceChildren(...SWATCHES.map((c) => {
    const b = el("button", "swatch" + (d.color === c ? " on" : ""));
    b.style.background = c;
    b.setAttribute("aria-label", "Farbe " + c);
    b.onclick = () => { d.color = c; ed.auto = false; renderEditor(); };
    return b;
  }));
  // Symbole
  const ig = $("edIcons");
  if (!ig.childElementCount) {
    PICK_ICONS.forEach((n) => {
      const b = el("button", "icon-pick");
      b.dataset.icon = n;
      b.innerHTML = svg(n);
      b.onclick = () => { d.icon = d.icon === n ? "" : n; d.emoji = ""; $("edEmoji").value = ""; ed.auto = false; renderEditor(); };
      ig.append(b);
    });
  }
  ig.querySelectorAll(".icon-pick").forEach((b) => b.classList.toggle("on", b.dataset.icon === d.icon && !d.emoji));
  ig.style.setProperty("--a", d.color);
  renderCurrent();
  renderParams();
  renderCatalog();
}
function previewStrip(d) {
  const s = strip("s2", d.color);
  const c = el("div", "strip-col");
  const it = ITEMS.get(keyOf(d));
  c.append(el("div", "strip-kicker", d.label || (it && it.label) || "Anzeige"), el("div", "strip-sub", it ? it.name : ""));
  s.append(c);
  return s;
}
function renderCurrent() {
  const it = ITEMS.get(keyOf(ed.draft));
  const box = $("edCurrent");
  box.replaceChildren();
  const ic = el("span", "cur-icon");
  ic.innerHTML = svg(it ? (CATALOG.find((c) => c.cat === it.cat) || {}).icon : "grid");
  box.append(ic, el("span", "cur-text", it ? it.cat + " › " + it.name.replace(/ …$/, "") : "Keine Aktion"));
}

function renderCatalog() {
  const box = $("edCatalog");
  box.replaceChildren();
  const cur = keyOf(ed.draft);
  for (const c of CATALOG) {
    const head = el("button", "cat-head" + (ed.open.has(c.cat) ? " open" : ""));
    head.innerHTML = svg("right");
    const ci = el("span", "cat-icon"); ci.innerHTML = svg(c.icon);
    head.append(ci, el("span", "", c.cat));
    head.onclick = () => { ed.open.has(c.cat) ? ed.open.delete(c.cat) : ed.open.add(c.cat); renderCatalog(); };
    box.append(head);
    if (!ed.open.has(c.cat)) continue;
    for (const it of c.items) {
      const row = el("button", "cat-item" + (itemKey(it) === cur ? " on" : "") + (it.locked ? " locked" : ""));
      const dot = el("span", "cat-dot");
      dot.style.setProperty("--a", it.color);
      dot.innerHTML = svg(it.icon || (it.w ? "wide" : "grid"));
      row.append(dot, el("span", "", it.name));
      if (itemKey(it) === cur) row.insertAdjacentHTML("beforeend", svg("check"));
      row.onclick = () => chooseItem(it);
      box.append(row);
    }
  }
}

function chooseItem(it) {
  const d = ed.draft;
  if (it.locked && !(d.action && d.action.type === "command")) {
    toast("Konsolenbefehle bitte in config.json am PC eintragen", true);
    return;
  }
  const prevItem = ITEMS.get(keyOf(d));
  const applyLook = ed.auto || !d.label || (prevItem && d.label === prevItem.label);
  if (it.w) {
    d.widget = it.w;
    delete d.action;
  } else {
    delete d.widget;
    const keep = d.action && d.action.type === it.a.type ? d.action : {};
    d.action = { ...keep, ...clone(it.a) };
  }
  if (applyLook) {
    d.label = it.label || d.label;
    d.icon = it.icon || "";
    d.emoji = "";
    d.color = it.color;
    $("edLabel").value = d.label;
    $("edEmoji").value = "";
    ed.auto = true;
  }
  if (it.param === "launch" && !APPS) send("apps_list");
  if (it.param === "playlist" && !playlists && S && S.spotify.logged_in) send("spotify_playlists");
  renderEditor();
}

// ---------- Einstellungen je Aktion
function renderParams() {
  const box = $("edParams");
  box.replaceChildren();
  const d = ed.draft;
  const a = d.action || {};
  const setLabelAuto = (text) => {
    if (ed.auto || !d.label) { d.label = text.slice(0, 40); $("edLabel").value = d.label; }
  };
  if (a.type === "chrome_url") {
    const inp = input("Adresse", a.url || "", "youtube.com", "url");
    inp.addEventListener("input", () => { a.url = inp.value.trim(); });
    inp.addEventListener("change", () => {
      const h = hostOf(a.url);
      if (h) setLabelAuto(h.split(".").slice(-2, -1)[0].replace(/^./, (x) => x.toUpperCase()));
      renderEditor();
    });
    box.append(wrap("Webseite", inp, "Öffnet sich als neuer Tab im offenen Chrome-Fenster."));
  } else if (a.type === "launch") {
    const inp = input("Pfad oder Link", a.target || "", "z.B. steam://  oder  C:\\Programme\\…\\app.exe");
    inp.addEventListener("input", () => { a.target = inp.value.trim(); });
    const f = wrap("Programm, Datei oder Link", inp);
    const search = input("Programm suchen", ed.appFilter, "Programm suchen …", "search");
    search.addEventListener("input", () => { ed.appFilter = search.value; renderAppList(list); });
    const list = el("div", "pick-list");
    f.append(el("div", "hint", "Oder aus deinem Startmenü wählen:"), search, list);
    renderAppList(list);
    box.append(f);
  } else if (a.type === "hotkey") {
    box.append(hotkeyEditor(a));
  } else if (a.type === "spotify_playlist") {
    const list = el("div", "pick-list");
    if (!S || !S.spotify.logged_in) list.append(el("div", "hint", "Verbinde zuerst Spotify auf einer Seite mit der Anzeige „Läuft gerade“."));
    else if (!playlists) list.append(el("div", "hint", "Lade Playlists …"));
    else playlists.forEach((p) => {
      const r = el("button", "pick" + (a.uri === p.uri ? " on" : ""));
      if (p.image) { const im = new Image(); im.src = p.image; im.alt = ""; r.append(im); }
      else { const ph = el("span", "ph"); ph.innerHTML = svg(p.liked ? "heart" : "music"); r.append(ph); }
      r.append(el("span", "", p.name));
      r.onclick = () => {
        a.uri = p.uri; a.name = p.name;
        if (ed.auto || !d.label) { d.label = p.name.slice(0, 40); $("edLabel").value = d.label; d.icon = ""; }
        renderEditor();
      };
      list.append(r);
    });
    box.append(wrap("Playlist", list));
  } else if (a.type === "page") {
    const list = el("div", "pick-list");
    PAGES.forEach((p) => {
      const r = el("button", "pick" + (a.page === p.id ? " on" : ""));
      const ph = el("span", "ph"); ph.innerHTML = svg(p.icon || "grid");
      r.append(ph, el("span", "", p.name));
      r.onclick = () => { a.page = p.id; setLabelAuto(p.name); renderEditor(); };
      list.append(r);
    });
    box.append(wrap("Zu welcher Seite?", list));
  } else if (a.type === "command") {
    const pre = el("code", "", a.target || "");
    box.append(wrap("Konsolenbefehl", pre, "Aus Sicherheitsgründen nur in config.json am PC änderbar."));
  }
}
function renderAppList(list) {
  const a = ed.draft.action;
  list.replaceChildren();
  if (!APPS) { list.append(el("div", "hint", "Lade Programme …")); return; }
  const q = ed.appFilter.trim().toLowerCase();
  const items = APPS.filter((x) => !q || x.name.toLowerCase().includes(q)).slice(0, 80);
  if (!items.length) list.append(el("div", "hint", "Nichts gefunden."));
  items.forEach((x) => {
    const r = el("button", "pick" + (a.target === x.target ? " on" : ""));
    const ph = el("span", "ph letter-ph", x.name.slice(0, 1).toUpperCase());
    r.append(ph, el("span", "", x.name));
    r.onclick = () => {
      a.target = x.target;
      if (ed.auto || !ed.draft.label) { ed.draft.label = x.name.slice(0, 40); $("edLabel").value = ed.draft.label; }
      renderEditor();
    };
    list.append(r);
  });
}
function input(name, value, placeholder, mode) {
  const i = el("input");
  i.value = value; i.placeholder = placeholder || ""; i.setAttribute("aria-label", name);
  i.autocomplete = "off"; i.autocapitalize = "off"; i.spellcheck = false;
  if (mode) i.inputMode = mode;
  return i;
}
function wrap(title, content, hint) {
  const f = el("div", "field");
  f.append(el("span", "", title), content);
  if (hint) f.append(el("div", "hint", hint));
  return f;
}
// Tastenkürzel zusammenklicken: Strg / Umschalt / Alt / Win + Taste
const MODS = [["ctrl", "Strg"], ["shift", "Umschalt"], ["alt", "Alt"], ["windows", "Win"]];
const PRESETS = [["windows+shift+s", "Screenshot"], ["ctrl+shift+esc", "Task-Manager"], ["windows+d", "Desktop"],
  ["windows+l", "Sperren"], ["alt+tab", "Fenster wechseln"], ["ctrl+c", "Kopieren"], ["ctrl+v", "Einfügen"],
  ["windows+g", "Game Bar"], ["windows+alt+r", "Aufnahme"], ["f13", "F13"]];
function hotkeyEditor(a) {
  const parts = (a.keys || "").split("+").filter(Boolean);
  const mods = new Set(parts.filter((p) => MODS.some((m) => m[0] === p)));
  let main = parts.filter((p) => !mods.has(p)).join("+");
  const box = el("div", "field");
  box.append(el("span", "", "Tastenkürzel"));
  const chips = el("div", "chips");
  const preview = el("code", "combo");
  const update = () => {
    a.keys = [...MODS.map((m) => m[0]).filter((m) => mods.has(m)), main.trim().toLowerCase()].filter(Boolean).join("+");
    preview.textContent = a.keys ? a.keys.split("+").map((p) => (MODS.find((m) => m[0] === p) || [p, p.length === 1 ? p.toUpperCase() : p])[1]).join(" + ") : "–";
  };
  MODS.forEach(([k, name]) => {
    const b = el("button", "chip" + (mods.has(k) ? " on" : ""), name);
    b.onclick = () => { mods.has(k) ? mods.delete(k) : mods.add(k); b.classList.toggle("on"); update(); };
    chips.append(b);
  });
  const keyIn = input("Taste", main, "Taste: m, f5, space, enter …");
  keyIn.addEventListener("input", () => { main = keyIn.value; update(); });
  const pre = el("div", "chips");
  PRESETS.forEach(([k, name]) => {
    const b = el("button", "chip ghost", name);
    b.onclick = () => {
      a.keys = k;
      if (ed.auto || !ed.draft.label) { ed.draft.label = name; $("edLabel").value = name; }
      renderEditor();
    };
    pre.append(b);
  });
  update();
  box.append(chips, keyIn, el("div", "hint", "Ergibt:"), preview, el("div", "hint", "Vorlagen:"), pre);
  return box;
}

$("edLabel").addEventListener("input", () => { ed.draft.label = $("edLabel").value; ed.auto = false; renderEditorPreview(); });
$("edEmoji").addEventListener("input", () => {
  ed.draft.emoji = $("edEmoji").value.trim();
  if (ed.draft.emoji) ed.draft.icon = "";
  ed.auto = false;
  renderEditor();
});
function renderEditorPreview() {
  const d = ed.draft;
  $("edPreview").replaceChildren(d.widget && d.widget !== "playlists" ? previewStrip(d) : keyEl(d));
}
$("edCancel").onclick = closeEditor;
$("edSave").onclick = () => {
  const d = ed.draft;
  const a = d.action || {};
  if (a.type === "chrome_url" && !a.url) return toast("Bitte eine Adresse eintragen", true);
  if (a.type === "launch" && !a.target) return toast("Bitte ein Programm wählen", true);
  if (a.type === "hotkey" && !a.keys) return toast("Bitte ein Tastenkürzel festlegen", true);
  if (a.type === "spotify_playlist" && !a.uri) return toast("Bitte eine Playlist wählen", true);
  if (a.type === "page" && !a.page) return toast("Bitte eine Seite wählen", true);
  const page = PAGES.find((p) => p.id === ed.pageId);
  if (ed.idx >= 0) page.keys[ed.idx] = d; else page.keys.push(d);
  const target = $("edMovePage").value;
  if (ed.idx >= 0 && target && target !== page.id) {
    page.keys.splice(ed.idx, 1);
    PAGES.find((p) => p.id === target).keys.push(d);
    toast("Taste verschoben nach „" + PAGES.find((p) => p.id === target).name + "“");
  }
  saveLayout();
  closeEditor();
};
$("edDelete").onclick = () => {
  if (!confirm("Diese Taste löschen?")) return;
  PAGES.find((p) => p.id === ed.pageId).keys.splice(ed.idx, 1);
  saveLayout();
  closeEditor();
};
function moveKey(dir) {
  const keys = PAGES.find((p) => p.id === ed.pageId).keys;
  const j = ed.idx + dir;
  if (j < 0 || j >= keys.length) return;
  keys[ed.idx] = ed.draft;
  [keys[ed.idx], keys[j]] = [keys[j], keys[ed.idx]];
  ed.idx = j;
  saveLayout();
  renderDeck();
}
$("edLeft").onclick = () => moveKey(-1);
$("edRight").onclick = () => moveKey(1);

// ================================================================ Seiten-Editor
let pe = null;
function openPageEditor() {
  const p = curPage();
  pe = { id: p.id, name: p.name, icon: p.icon || "grid" };
  $("peName").value = p.name;
  const ig = $("peIcons");
  if (!ig.childElementCount) {
    ["sliders", "music", "globe", "gamepad", "video", "chat", "monitor", "app", "star", "bolt", "home", "keyboard", "code", "camera", "moon", "grid"].forEach((n) => {
      const b = el("button", "icon-pick");
      b.dataset.icon = n; b.innerHTML = svg(n);
      b.onclick = () => { pe.icon = n; ig.querySelectorAll(".icon-pick").forEach((x) => x.classList.toggle("on", x.dataset.icon === n)); };
      ig.append(b);
    });
  }
  ig.querySelectorAll(".icon-pick").forEach((x) => x.classList.toggle("on", x.dataset.icon === pe.icon));
  $("peDelete").hidden = PAGES.length < 2;
  $("pageEd").hidden = false;
}
function closePageEditor() { pe = null; $("pageEd").hidden = true; renderPager(); renderDeck(); }
$("peCancel").onclick = closePageEditor;
$("peSave").onclick = () => {
  const p = PAGES.find((x) => x.id === pe.id);
  p.name = $("peName").value.trim() || "Seite";
  p.icon = pe.icon;
  saveLayout();
  closePageEditor();
};
function movePage(dir) {
  const i = PAGES.findIndex((x) => x.id === pe.id), j = i + dir;
  if (j < 0 || j >= PAGES.length) return;
  [PAGES[i], PAGES[j]] = [PAGES[j], PAGES[i]];
  saveLayout();
  renderPager();
}
$("peLeft").onclick = () => movePage(-1);
$("peRight").onclick = () => movePage(1);
$("peDelete").onclick = () => {
  const p = PAGES.find((x) => x.id === pe.id);
  if (!confirm(`Seite „${p.name}“ mit ${p.keys.length} Tasten löschen?`)) return;
  PAGES = PAGES.filter((x) => x.id !== pe.id);
  pageId = PAGES[0].id;
  saveLayout();
  closePageEditor();
};
$("peReset").onclick = () => {
  if (!confirm("Alle Seiten und Tasten auf den Standard zurücksetzen? Deine Belegung geht verloren.")) return;
  pe = null; $("pageEd").hidden = true;
  pageId = "control";
  send("layout_reset");
};

// ================================================================ Adresse eintippen
function openSheet() { $("sheet").hidden = false; setTimeout(() => $("urlInput").focus(), 50); }
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

// ================================================================ Toast
let toastT;
function toast(text, error) {
  const t = $("toast");
  t.textContent = text;
  t.className = "show" + (error ? " error" : "");
  clearTimeout(toastT);
  toastT = setTimeout(() => (t.className = ""), 2600);
}

connect();

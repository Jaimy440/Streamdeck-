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
  play: '<path d="M7 4v16l13-8Z"/>',
  pause: '<rect x="6" y="4" width="4" height="16" rx="1"/><rect x="14" y="4" width="4" height="16" rx="1"/>',
  send: '<path d="M22 2 11 13M22 2l-7 20-4-9-9-4Z"/>',
  back10: '<path d="M3 12a9 9 0 1 0 3-6.7L3 8M3 3v5h5"/>',
  fwd10: '<path d="M21 12a9 9 0 1 1-3-6.7L21 8M21 3v5h-5"/>',
  link: '<path d="M10 13a5 5 0 0 0 7.5.5l3-3a5 5 0 0 0-7-7l-1.7 1.7M14 11a5 5 0 0 0-7.5-.5l-3 3a5 5 0 0 0 7 7l1.7-1.7"/>',
  heart: '<path d="M19 14c1.5-1.5 3-3.2 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.8 0-3 .5-4.5 2-1.5-1.5-2.7-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4 3 5.5l7 7Z"/>',
};
const svg = (name) => `<svg viewBox="0 0 24 24" aria-hidden="true">${ICONS[name] || ""}</svg>`;
function setIcon(el, name) {
  if (el.dataset.icon === name && el.firstChild) return;
  el.dataset.icon = name;
  el.innerHTML = svg(name);
}
document.querySelectorAll("i[data-icon]").forEach((el) => (el.innerHTML = svg(el.dataset.icon)));

// ---------------------------------------------------------------- Login (dauerhaft)
// Der Token aus dem QR-Code wird gespeichert; zusätzlich setzt der PC ein Cookie (10 Jahre).
const store = {
  get(k) { try { return localStorage.getItem(k); } catch (e) { return null; } },
  set(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* egal */ } },
};
let token = new URLSearchParams(location.search).get("token");
if (token) store.set("pcdeck_token", token);
else token = store.get("pcdeck_token");

let ws = null;
let retry = 0;
let everConnected = false;
let S = null;               // System-Status
let SP = null;              // Spotify-Player
let playlists = null;
let VM = null;              // Chrome-Video
const busy = new Set();     // Regler, die gerade bewegt werden

function connect() {
  const proto = location.protocol === "https:" ? "wss" : "ws";
  const q = token ? `?token=${encodeURIComponent(token)}` : "";   // ohne Token -> Cookie
  ws = new WebSocket(`${proto}://${location.host}/ws${q}`);
  ws.onopen = () => {
    retry = 0;
    everConnected = true;
    setConn(true);
    if (currentView === "setup") showView(store.get("pcdeck_view") || "control");
  };
  ws.onclose = () => {
    setConn(false);
    if (!everConnected && retry >= 2) showView("setup");
    setTimeout(connect, Math.min(5000, 400 * 2 ** retry++));
  };
  ws.onmessage = (ev) => {
    const m = JSON.parse(ev.data);
    if (m.type === "state") renderState(m);
    else if (m.type === "spotify_player") { SP = m.data; SP_at = Date.now(); renderPlayer(); }
    else if (m.type === "spotify_playlists") { playlists = m.data; renderPlaylists(); }
    else if (m.type === "chrome_media") { VM = m.data; VM_at = Date.now(); renderVideo(); }
    else if (m.type === "toast") toast(m.text, m.error);
  };
}

function send(cmd, extra = {}) {
  if (ws && ws.readyState === 1) ws.send(JSON.stringify({ cmd, ...extra }));
  else toast("Nicht verbunden", true);
}

function setConn(on) {
  $("conn").className = "conn " + (on ? "on" : "off");
  $("connText").textContent = on ? "Verbunden" : "Getrennt";
  $("railStatus").className = "rail-status " + (on ? "on" : "off");
}

document.addEventListener("visibilitychange", () => {
  if (!document.hidden && (!ws || ws.readyState > 1)) { retry = 0; connect(); }
});

// ---------------------------------------------------------------- Navigation
const VIEWS = { control: "steuerung", spotify: "spotify", chrome: "chrome", setup: "verbinden" };
let currentView = null;
function showView(v) {
  currentView = v;
  for (const k of Object.keys(VIEWS)) $("view-" + k).hidden = k !== v;
  document.querySelectorAll(".rail-btn").forEach((b) => b.classList.toggle("active", b.dataset.view === v));
  $("viewTitle").textContent = VIEWS[v];
  if (v !== "setup") store.set("pcdeck_view", v);
  updateSub();
  if (v === "spotify" && S && S.spotify.logged_in && !playlists) send("spotify_playlists");
}
document.querySelectorAll(".rail-btn").forEach((b) => (b.onclick = () => showView(b.dataset.view)));

function updateSub() {
  let t = "";
  if (currentView === "control" && S) t = "PC-Lautstärke " + (S.muted ? "stumm" : S.volume + "%");
  if (currentView === "spotify" && SP && SP.title) t = (SP.playing ? "▶ " : "") + SP.title;
  if (currentView === "chrome" && VM) t = VM.host;
  $("viewSub").textContent = t;
}

// ---------------------------------------------------------------- Hilfen
const fmt = (s) => {
  s = Math.max(0, Math.floor(s || 0));
  const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), x = String(s % 60).padStart(2, "0");
  return h ? `${h}:${String(m).padStart(2, "0")}:${x}` : `${m}:${x}`;
};
function setRange(el, value, max) {
  if (max !== undefined) el.max = max;
  if (!busy.has(el.id)) el.value = value;
  paintRange(el);
}
function paintRange(el) {
  const p = ((el.value - el.min) / ((el.max - el.min) || 1)) * 100;
  el.style.setProperty("--p", p + "%");
}
// Regler: während des Ziehens keine Updates vom Server übernehmen
function bindRange(el, onChange, live) {
  el.addEventListener("input", () => {
    busy.add(el.id);
    paintRange(el);
    if (live) live(Number(el.value));
  });
  el.addEventListener("change", () => {
    onChange(Number(el.value));
    setTimeout(() => busy.delete(el.id), 600);
  });
}
function el(tag, cls, text) {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (text !== undefined) e.textContent = text;
  return e;
}

// ---------------------------------------------------------------- Steuerung
function renderState(s) {
  S = s;
  $("volText").textContent = s.muted ? "stumm" : s.volume + "%";
  setRange($("volSlider"), s.volume);
  $("btnMute").classList.toggle("active", s.muted);
  $("btnDMute").classList.toggle("active", s.discord.muted || s.discord.deafened);
  $("btnDeaf").classList.toggle("active", s.discord.deafened);
  $("btnFull").classList.toggle("active", s.discord.deafened && s.mic_muted);
  $("btnWinMic").classList.toggle("active", s.mic_muted);

  const deck = $("deck");
  const sig = JSON.stringify(s.buttons);
  if (deck.dataset.sig !== sig) {
    deck.dataset.sig = sig;
    deck.replaceChildren(...s.buttons.map((b, i) => {
      const t = el("button", "tile");
      t.append(el("span", "emoji", b.icon || "•"), el("span", "", b.label));
      t.onclick = () => send("button", { index: i });
      return t;
    }));
  }

  // Spotify-Status
  const sp = s.spotify;
  $("spSetup").hidden = sp.configured;
  $("spLogin").hidden = !sp.configured || sp.logged_in;
  $("spMain").hidden = !sp.logged_in;
  $("spRedirect").textContent = sp.redirect_uri;
  $("spFree").hidden = sp.premium !== false;
  if (sp.logged_in && currentView === "spotify" && !playlists) send("spotify_playlists");
  if (!sp.logged_in) playlists = null;

  // Chrome
  $("extBadge").textContent = s.chrome_ext ? "Verbunden" : "Erweiterung fehlt";
  $("extBadge").classList.toggle("ok", s.chrome_ext);
  const favs = $("favs");
  const fsig = JSON.stringify(s.favorites);
  if (favs.dataset.sig !== fsig) {
    favs.dataset.sig = fsig;
    favs.replaceChildren(...s.favorites.map((f) => {
      const b = el("button", "fav");
      const av = el("span", "av", (f.icon || f.label || "?").slice(0, f.icon ? 2 : 1).toUpperCase());
      av.style.background = f.color || "#5865f2";
      b.append(av, el("span", "", f.label));
      b.onclick = () => send("chrome_open", { url: f.url });
      return b;
    }));
  }
  renderVideo();
  updateSub();
}

document.querySelectorAll("[data-cmd]").forEach((b) => b.addEventListener("click", () => send(b.dataset.cmd)));
// Gedrückt halten auf Leiser/Lauter = wiederholen
document.querySelectorAll('[data-cmd="volume_up"],[data-cmd="volume_down"]').forEach((b) => {
  let t;
  const stop = () => { clearTimeout(t); clearInterval(t); };
  b.addEventListener("touchstart", () => { t = setTimeout(() => (t = setInterval(() => send(b.dataset.cmd), 120)), 400); }, { passive: true });
  b.addEventListener("touchend", stop);
  b.addEventListener("touchcancel", stop);
});
let volT;
bindRange($("volSlider"), (v) => send("volume_set", { value: v }), (v) => {
  $("volText").textContent = v + "%";
  clearTimeout(volT);
  volT = setTimeout(() => send("volume_set", { value: v }), 50);
});
$("discordReset").onclick = () => { send("discord_reset"); toast("Discord-Anzeige zurückgesetzt"); };

// ---------------------------------------------------------------- Spotify
let SP_at = 0;
function renderPlayer() {
  const p = SP;
  const cover = $("spCover");
  if (p && p.image) {
    if (cover.dataset.src !== p.image) {
      cover.dataset.src = p.image;
      const img = new Image();
      img.alt = "";
      img.src = p.image;
      cover.replaceChildren(img);
    }
  } else if (cover.dataset.src !== "") {
    cover.dataset.src = "";
    cover.innerHTML = svg("music");
  }
  $("spTitle").textContent = p && p.title ? p.title : "Nichts läuft";
  $("spArtist").textContent = p && p.title ? p.artist : "Wähle rechts eine Playlist";
  $("spDevice").textContent = p && p.device ? "Läuft auf " + p.device : "";
  setIcon($("spPlay").firstElementChild, p && p.playing ? "pause" : "play");
  $("spShuffle").classList.toggle("on", !!(p && p.shuffle));
  $("spRepeat").classList.toggle("on", !!(p && p.repeat !== "off"));
  $("spVolRow").hidden = !p || p.volume == null;
  if (p && p.volume != null) setRange($("spVol"), p.volume);
  tickPlayer();
  document.querySelectorAll("#spList .row").forEach((r) => r.classList.toggle("current", !!p && r.dataset.uri === p.context));
  updateSub();
}
function tickPlayer() {
  const p = SP;
  const dur = p ? p.duration / 1000 : 0;
  let pos = p ? p.progress / 1000 : 0;
  if (p && p.playing) pos = Math.min(dur, pos + (Date.now() - SP_at) / 1000);
  setRange($("spProgress"), Math.round(pos), Math.max(1, Math.round(dur)));
  $("spPos").textContent = fmt(busy.has("spProgress") ? $("spProgress").value : pos);
  $("spDur").textContent = fmt(dur);
}
function renderPlaylists() {
  const q = $("spSearch").value.trim().toLowerCase();
  const list = $("spList");
  if (!playlists) { list.replaceChildren(el("p", "muted small", "Lade Playlists …")); return; }
  const items = playlists.filter((p) => !q || p.name.toLowerCase().includes(q));
  if (!items.length) { list.replaceChildren(el("p", "muted small", "Keine Playlist gefunden.")); return; }
  list.replaceChildren(...items.map((p) => {
    const r = el("button", "row");
    r.dataset.uri = p.uri;
    if (SP && SP.context === p.uri) r.classList.add("current");
    if (p.image) {
      const img = new Image();
      img.loading = "lazy";
      img.alt = "";
      img.src = p.image;
      r.append(img);
    } else {
      const ph = el("span", "ph" + (p.liked ? " liked" : ""));
      ph.innerHTML = svg(p.liked ? "heart" : "music");
      r.append(ph);
    }
    const tx = el("span", "row-text");
    const sub = p.liked ? "Deine Lieblingssongs" : ["Playlist", p.owner, p.tracks != null ? p.tracks + " Songs" : ""].filter(Boolean).join(" · ");
    tx.append(el("div", "row-title", p.name), el("div", "row-sub", sub));
    r.append(tx);
    r.onclick = () => { send("spotify_play", { uri: p.uri }); toast("▶ " + p.name); };
    return r;
  }));
}
$("spSearch").addEventListener("input", renderPlaylists);
$("spLoginBtn").onclick = () => send("spotify_login");
$("spLogout").onclick = () => { if (confirm("Spotify-Verbindung trennen?")) send("spotify_logout"); };
$("spReload").onclick = () => { playlists = null; renderPlaylists(); send("spotify_playlists", { force: true }); };
$("spPlay").onclick = () => send("spotify_control", { action: SP && SP.playing ? "pause" : "play" });
document.querySelectorAll("[data-sp]").forEach((b) => (b.onclick = () => send("spotify_control", { action: b.dataset.sp })));
$("spShuffle").onclick = () => send("spotify_control", { action: "shuffle", value: !(SP && SP.shuffle) });
$("spRepeat").onclick = () => {
  const order = ["off", "context", "track"];
  const cur = SP ? order.indexOf(SP.repeat) : 0;
  send("spotify_control", { action: "repeat", value: order[(cur + 1) % 3] });
};
bindRange($("spProgress"), (v) => send("spotify_control", { action: "seek", value: v * 1000 }), (v) => ($("spPos").textContent = fmt(v)));
bindRange($("spVol"), (v) => send("spotify_control", { action: "volume", value: v }));

// ---------------------------------------------------------------- Chrome
let VM_at = 0;
function renderVideo() {
  const v = VM;
  const ext = S && S.chrome_ext;
  $("vBox").hidden = !v;
  $("vNone").hidden = !!v;
  $("vNoneText").textContent = !ext
    ? "Für die Video-Steuerung die Chrome-Erweiterung installieren (siehe Anleitung). Webseiten öffnen geht trotzdem."
    : "Kein Video in Chrome gefunden. Starte ein Video, dann erscheint es hier.";
  $("vHost").textContent = v ? v.host : "";
  if (!v) { updateSub(); return; }
  $("vTitle").textContent = v.title;
  setIcon($("vPlay").firstElementChild, v.playing ? "pause" : "play");
  setIcon($("vMute").firstElementChild, v.muted ? "volumex" : "volume");
  setRange($("vVol"), Math.round(v.volume * 100));
  document.querySelectorAll("#vSpeed button").forEach((b) => b.classList.toggle("on", Number(b.dataset.speed) === v.rate));
  tickVideo();
  updateSub();
}
function tickVideo() {
  const v = VM;
  if (!v) return;
  let pos = v.time;
  if (v.playing) pos = Math.min(v.duration || Infinity, pos + ((Date.now() - VM_at) / 1000) * (v.rate || 1));
  const live = !v.duration;
  $("vProgress").disabled = live;
  setRange($("vProgress"), Math.round(pos), Math.max(1, Math.round(v.duration)));
  $("vPos").textContent = fmt(busy.has("vProgress") ? $("vProgress").value : pos);
  $("vDur").textContent = live ? "LIVE" : fmt(v.duration);
}
document.querySelectorAll("[data-v]").forEach((b) => (b.onclick = () =>
  send("chrome_media", { action: b.dataset.v, value: b.dataset.val ? Number(b.dataset.val) : null })));
document.querySelectorAll("#vSpeed button").forEach((b) => (b.onclick = () =>
  send("chrome_media", { action: "speed", value: Number(b.dataset.speed) })));
bindRange($("vProgress"), (v) => send("chrome_media", { action: "seek_to", value: v }), (v) => ($("vPos").textContent = fmt(v)));
bindRange($("vVol"), (v) => send("chrome_media", { action: "volume", value: v / 100 }));
$("urlForm").addEventListener("submit", (e) => {
  e.preventDefault();
  const v = $("urlInput").value.trim();
  if (!v) return;
  send("chrome_open", { url: v });
  $("urlInput").value = "";
  $("urlInput").blur();
});

setInterval(() => { tickPlayer(); tickVideo(); }, 500);

// ---------------------------------------------------------------- Toast
let toastT;
function toast(text, error) {
  const t = $("toast");
  t.textContent = text;
  t.className = "show" + (error ? " error" : "");
  clearTimeout(toastT);
  toastT = setTimeout(() => (t.className = ""), 2800);
}

document.querySelectorAll(".range").forEach(paintRange);
showView(store.get("pcdeck_view") || "control");
connect();

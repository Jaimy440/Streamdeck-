// PC-Deck Bridge – verbindet Chrome mit dem PC-Deck-Programm auf diesem PC.
// Falls du den Port in config.json änderst, hier ebenfalls anpassen:
const PORT = 8765;
const WS_URL = `ws://127.0.0.1:${PORT}/ext`;

let ws = null;
let pollTimer = null;
let target = null;      // { tabId, frameId } – das Video, das gesteuert wird
let lastSent = "";

// ---------------------------------------------------------------- Verbindung
function connect() {
  if (ws && ws.readyState <= 1) return;
  try {
    ws = new WebSocket(WS_URL);
  } catch (e) {
    return;
  }
  ws.onopen = () => {
    send({ type: "hello", version: chrome.runtime.getManifest().version });
    lastSent = "";
    pollTimer = setInterval(pushStatus, 1000);  // hält den Service-Worker auch wach
  };
  ws.onmessage = (ev) => handle(JSON.parse(ev.data)).catch((e) => send({ type: "error", text: String(e.message || e) }));
  ws.onclose = () => {
    clearInterval(pollTimer);
    ws = null;
  };
  ws.onerror = () => {};
}

function send(obj) {
  if (ws && ws.readyState === 1) ws.send(JSON.stringify(obj));
}

chrome.runtime.onStartup.addListener(connect);
chrome.runtime.onInstalled.addListener(connect);
chrome.alarms.create("pcdeck-reconnect", { periodInMinutes: 0.5 });
chrome.alarms.onAlarm.addListener(connect);
connect();

// ---------------------------------------------------------------- Befehle
async function handle(msg) {
  if (msg.cmd === "open_url") {
    await openUrl(msg.url);
  } else if (msg.cmd === "media") {
    await mediaAction(msg.action, msg.value);
    setTimeout(pushStatus, 150);
  } else if (msg.cmd === "ping") {
    send({ type: "pong" });
  }
}

// Neuer Tab im zuletzt benutzten Fenster – nur wenn gar kein Fenster offen ist, ein neues Fenster.
async function openUrl(url) {
  let win = null;
  try {
    win = await chrome.windows.getLastFocused({ windowTypes: ["normal"] });
  } catch (e) { /* kein Fenster */ }
  if (!win || win.incognito) {
    const all = await chrome.windows.getAll({ windowTypes: ["normal"] });
    win = all.find((w) => !w.incognito) || null;
  }
  if (win) {
    await chrome.tabs.create({ url, windowId: win.id, active: true });
    const upd = { focused: true };
    if (win.state === "minimized") upd.state = "normal";
    await chrome.windows.update(win.id, upd);
  } else {
    await chrome.windows.create({ url, focused: true });
  }
}

// ---------------------------------------------------------------- Video
// Läuft im Tab (in jedem Frame). Muss eigenständig sein – keine Variablen von außen!
function pageMedia(action, value) {
  const all = [...document.querySelectorAll("video, audio")].filter((m) => m.readyState > 0 || m.currentSrc);
  if (!all.length) return null;
  const area = (m) => m.clientWidth * m.clientHeight;
  const m = all.find((x) => !x.paused) || all.sort((a, b) => area(b) - area(a))[0];
  switch (action) {
    case "toggle": m.paused ? m.play() : m.pause(); break;
    case "play": m.play(); break;
    case "pause": m.pause(); break;
    case "seek_rel": m.currentTime = Math.max(0, m.currentTime + Number(value)); break;
    case "seek_to": m.currentTime = Number(value); break;
    case "volume": m.volume = Math.min(1, Math.max(0, Number(value))); m.muted = false; break;
    case "mute": m.muted = !m.muted; break;
    case "speed": m.playbackRate = Number(value); break;
    case "next": {
      const b = document.querySelector(".ytp-next-button, [data-uia='next-episode-seamless-button']");
      if (b) b.click();
      break;
    }
  }
  return {
    playing: !m.paused,
    time: m.currentTime,
    duration: isFinite(m.duration) ? m.duration : 0,
    volume: m.volume,
    muted: m.muted,
    rate: m.playbackRate,
    area: area(m),
    isVideo: m.tagName === "VIDEO",
  };
}

async function probe(tabId) {
  try {
    const res = await chrome.scripting.executeScript({ target: { tabId, allFrames: true }, func: pageMedia, args: ["status", null] });
    const hits = res.filter((r) => r.result);
    if (!hits.length) return null;
    hits.sort((a, b) => (b.result.playing - a.result.playing) || (b.result.area - a.result.area));
    return { frameId: hits[0].frameId, media: hits[0].result };
  } catch (e) {
    return null; // z.B. chrome://-Seiten
  }
}

// Welcher Tab? 1. einer, der gerade Ton abspielt  2. der zuletzt gesteuerte  3. der aktive Tab
async function findTarget() {
  const candidates = [];
  for (const t of await chrome.tabs.query({ audible: true })) candidates.push(t.id);
  if (target) candidates.push(target.tabId);
  const [active] = await chrome.tabs.query({ active: true, lastFocusedWindow: true });
  if (active) candidates.push(active.id);
  for (const tabId of [...new Set(candidates)]) {
    const p = await probe(tabId);
    if (p) return { tabId, ...p };
  }
  return null;
}

async function mediaAction(action, value) {
  const t = await findTarget();
  if (!t) throw new Error("Kein Video in Chrome gefunden");
  target = { tabId: t.tabId, frameId: t.frameId };
  await chrome.scripting.executeScript({
    target: { tabId: t.tabId, frameIds: [t.frameId] }, func: pageMedia, args: [action, value],
  });
}

async function pushStatus() {
  if (!ws || ws.readyState !== 1) return;
  const t = await findTarget();
  let data = null;
  if (t) {
    target = { tabId: t.tabId, frameId: t.frameId };
    const tab = await chrome.tabs.get(t.tabId);
    let host = "";
    try { host = new URL(tab.url).hostname.replace(/^www\./, ""); } catch (e) { /* egal */ }
    data = { ...t.media, title: tab.title || "", host, tabId: t.tabId };
    data.time = Math.round(data.time * 10) / 10;
  }
  const s = JSON.stringify(data);
  if (s !== lastSent) {
    lastSent = s;
    send({ type: "media", data });
  }
}

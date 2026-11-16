"use strict";
const $ = (id) => document.getElementById(id);

// ---------- Token aus der URL (QR-Code) merken ----------
let token = new URLSearchParams(location.search).get("token");
try {
  if (token) localStorage.setItem("pcdeck_token", token);
  else token = localStorage.getItem("pcdeck_token");
} catch (e) { /* privater Modus */ }

let ws = null;
let state = null;
let retry = 0;
let sliderBusy = false;

function connect() {
  if (!token) { $("setup").hidden = false; return; }
  const proto = location.protocol === "https:" ? "wss" : "ws";
  ws = new WebSocket(`${proto}://${location.host}/ws?token=${encodeURIComponent(token)}`);
  ws.onopen = () => { retry = 0; setConn(true); };
  ws.onclose = () => {
    setConn(false);
    setTimeout(connect, Math.min(5000, 500 * 2 ** retry++));
  };
  ws.onmessage = (ev) => {
    const msg = JSON.parse(ev.data);
    if (msg.type === "state") render(msg);
    else if (msg.type === "toast") toast(msg.text, msg.error);
  };
}

function send(cmd, extra = {}) {
  if (ws && ws.readyState === 1) ws.send(JSON.stringify({ cmd, ...extra }));
  else toast("Nicht verbunden", true);
}

function setConn(on) {
  $("conn").textContent = on ? "verbunden" : "getrennt";
  $("conn").className = "conn " + (on ? "on" : "off");
  if (on) $("app").hidden = false;
}

// iOS beendet Verbindungen im Hintergrund -> beim Zurückkehren neu verbinden
document.addEventListener("visibilitychange", () => {
  if (!document.hidden && (!ws || ws.readyState > 1)) { retry = 0; connect(); }
});

// ---------- Anzeige ----------
function render(s) {
  state = s;
  $("volText").textContent = s.muted ? "stumm" : s.volume + "%";
  if (!sliderBusy) $("volSlider").value = s.volume;
  $("btnMute").classList.toggle("active", s.muted);
  $("btnDMute").classList.toggle("active", s.discord.muted || s.discord.deafened);
  $("btnDeaf").classList.toggle("active", s.discord.deafened);
  $("btnFull").classList.toggle("active", s.discord.deafened && s.mic_muted);
  $("btnWinMic").classList.toggle("active", s.mic_muted);

  // Deck
  const deck = $("deck");
  const sig = JSON.stringify(s.buttons);
  if (deck.dataset.sig !== sig) {
    deck.dataset.sig = sig;
    deck.innerHTML = "";
    s.buttons.forEach((b, i) => {
      const el = document.createElement("button");
      el.className = "key";
      el.textContent = b.icon || "▫️";
      const sm = document.createElement("small");
      sm.textContent = b.label;
      el.appendChild(sm);
      el.onclick = () => send("button", { index: i });
      deck.appendChild(el);
    });
  }
}

// ---------- Bedienung ----------
document.querySelectorAll("[data-cmd]").forEach((el) =>
  el.addEventListener("click", () => send(el.dataset.cmd)));

// Gedrückt halten auf +/- = wiederholen
document.querySelectorAll('[data-cmd="volume_up"],[data-cmd="volume_down"]').forEach((el) => {
  let t;
  const stop = () => clearInterval(t);
  el.addEventListener("touchstart", () => {
    t = setTimeout(() => (t = setInterval(() => send(el.dataset.cmd), 120)), 400);
  }, { passive: true });
  el.addEventListener("touchend", stop);
  el.addEventListener("touchcancel", stop);
});

const vs = $("volSlider");
let volTimer;
vs.addEventListener("input", () => {
  sliderBusy = true;
  $("volText").textContent = vs.value + "%";
  clearTimeout(volTimer);
  volTimer = setTimeout(() => send("volume_set", { value: Number(vs.value) }), 40);
});
vs.addEventListener("change", () => { sliderBusy = false; send("volume_set", { value: Number(vs.value) }); });

$("discordReset").onclick = () => { send("discord_reset"); toast("Discord-Anzeige zurückgesetzt"); };

let toastT;
function toast(text, error) {
  const t = $("toast");
  t.textContent = text;
  t.className = "show" + (error ? " error" : "");
  clearTimeout(toastT);
  toastT = setTimeout(() => (t.className = ""), 3000);
}

connect();

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

  // Filter
  const f = s.filter;
  $("filterSwitch").checked = f.running;
  $("filterSwitch").disabled = !f.available || !f.enrolled_me;
  $("filterLive").classList.toggle("off", !f.running);
  $("filterHint").textContent = !f.available
    ? "Filter nicht installiert – siehe Anleitung (install_filter.bat)."
    : !f.enrolled_me
      ? "Lerne zuerst deine Stimme ein (unten), dann kannst du den Filter einschalten."
      : f.error || "Lässt nur deine Stimme ins Mikro – dein Bruder wird rausgefiltert.";
  const lvl = Math.max(0, Math.min(100, (f.level_db + 70) / 60 * 100));
  $("lvlBar").style.width = (f.running ? lvl : 0) + "%";
  $("lvlText").textContent = f.running ? f.level_db + " dB" : "–";
  $("simBar").style.width = (f.sim_me * 100) + "%";
  $("simText").textContent = f.running ? f.sim_me.toFixed(2) : "–";
  $("simOBar").style.width = (f.sim_other * 100) + "%";
  $("simOText").textContent = f.enrolled_other ? (f.running ? f.sim_other.toFixed(2) : "–") : "nicht eingelernt";
  $("thrMark").style.left = (f.threshold * 100) + "%";
  if (!thrBusy) $("thrSlider").value = f.threshold;
  $("thrText").textContent = Number(f.threshold).toFixed(2);
  $("gate").textContent = f.open ? "🎙️ Mikro OFFEN (du sprichst)" : "Mikro ZU";
  $("gate").classList.toggle("open", f.running && f.open);
  $("meState").textContent = f.enrolled_me ? "✅ eingelernt (neu?)" : "noch nicht eingelernt";
  $("otherState").textContent = f.enrolled_other ? "✅ eingelernt (neu?)" : "optional, viel genauer";

  const en = f.enrolling;
  $("enrollBox").hidden = !en;
  $("enrollMe").disabled = $("enrollOther").disabled = !!en || !f.available;
  if (en) {
    $("enrollText").textContent = en.who === "me"
      ? "🙋 Sprich jetzt ganz normal (vorlesen, erzählen) – nur DU! Dein Bruder bitte leise sein."
      : "👦 Jetzt soll NUR dein Bruder sprechen – du bitte leise sein.";
    $("enrollBar").style.width = (en.progress * 100) + "%";
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

let thrBusy = false;
$("thrSlider").addEventListener("input", (e) => { thrBusy = true; $("thrText").textContent = Number(e.target.value).toFixed(2); });
$("thrSlider").addEventListener("change", (e) => { thrBusy = false; send("filter_threshold", { value: Number(e.target.value) }); });

$("filterSwitch").addEventListener("change", (e) => {
  e.target.checked = !e.target.checked; // Server-Status entscheidet
  send("filter_toggle");
});

function enroll(who) {
  const text = who === "me"
    ? "20 Sekunden aufnehmen: Sprich ganz normal, nur du. Los?"
    : "20 Sekunden aufnehmen: Nur dein Bruder spricht. Los?";
  if (confirm(text)) send("filter_enroll", { who, seconds: 20 });
}
$("enrollMe").onclick = () => enroll("me");
$("enrollOther").onclick = () => enroll("other");
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

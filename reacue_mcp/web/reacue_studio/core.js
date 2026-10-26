/* ReaCue Studio — noyau commun à tous les écrans (Travail, puis Biblio, Groupe, Concert, Lumière, mobile).
   - langue FR / EN (?lang=fr|en, mémorisée), textes fournis par chaque écran ;
   - interface web native de REAPER : /_/TRANSPORT ; /_/TRACK (nom, mute/solo, volume, pan, crête) ;
     /_/SET/TRACK/<n>/MUTE|SOLO|VOL|PAN/<v> ; /_/SET/POS/<s> ; actions numériques (1007 lecture…) ;
   - commandes ReaCue (fenêtre ReaCue ouverte sur l'ordinateur) : /_/SET/EXTSTATE/ReaCue/remote/<cmd>|<arg>|<pin>|<nonce>,
     une à la fois (file d'attente, accusé ReaCue/remote_ack), PIN mémorisé dans le navigateur ;
   - données publiées par ReaCue : reacue_song.json (grille, sections, accords), reacue_peaks.json (formes d'onde),
     reacue_export.json (état des exports) ;
   - calculs musicaux : mesure.temps.subdivision, SMPTE, transposition des accords.
   Aucune ressource externe. */
(function () {
  "use strict";
  const RC = {};
  window.RC = RC;

  // ------------------------------------------------------------------ outils
  RC.$ = id => document.getElementById(id);
  RC.esc = s => String(s == null ? "" : s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  RC.store = (k, v) => { try { v == null ? localStorage.removeItem(k) : localStorage.setItem(k, v); } catch (e) { /* navigation privée */ } };
  RC.load = k => { try { return localStorage.getItem(k); } catch (e) { return null; } };
  RC.clamp = (v, a, b) => Math.max(a, Math.min(b, v));
  RC.params = new URLSearchParams(location.search);

  // ------------------------------------------------------------------ langue
  RC.STR = { fr: {}, en: {} };
  RC.LANG_FIXED = RC.params.get("lang");
  RC.LANG = (RC.LANG_FIXED in { fr: 1, en: 1 }) ? RC.LANG_FIXED : (RC.load("reacue_studio_lang") ||
    ((navigator.language || "fr").toLowerCase().startsWith("fr") ? "fr" : "en"));
  RC.S = () => RC.STR[RC.LANG] || RC.STR.fr;
  RC.t = (k, ...a) => { const v = RC.S()[k] != null ? RC.S()[k] : RC.STR.fr[k]; return typeof v === "function" ? v(...a) : (v == null ? k : v); };
  RC.onLang = [];
  RC.setLang = (l, remember = true) => {
    if (!RC.STR[l]) return;
    RC.LANG = l;
    if (remember) RC.store("reacue_studio_lang", l);
    document.documentElement.lang = l;
    document.querySelectorAll("[data-t]").forEach(el => { el.textContent = RC.t(el.dataset.t); });
    document.querySelectorAll("[data-tt]").forEach(el => { el.title = RC.t(el.dataset.tt); });
    RC.onLang.forEach(f => f(l));
  };

  // ------------------------------------------------------------------ interface web de REAPER
  RC.state = { ok: false, lastOk: -1e9, play: 0, ps: 0, pos: 0, at: 0, rtt: 60, tracks: [], ext: {}, aliveAt: -1e9, alive: "" };
  RC.api = async (cmds) => {
    const r = await fetch("/_/" + cmds, { cache: "no-store" });
    if (!r.ok) throw new Error("HTTP " + r.status);
    return r.text();
  };
  RC.fire = cmds => fetch("/_/" + cmds, { cache: "no-store" }).catch(() => {});
  // n'attend pas la réponse : enchaîné après la requête précédente (ordre garanti)
  let chain = Promise.resolve();
  RC.send = cmds => { chain = chain.then(() => RC.api(cmds).catch(() => "")); return chain; };

  // TRACK \t n \t nom \t flags \t volume \t pan \t crête (dB*10) \t … \t couleur
  RC.parseTracks = txt => txt.split("\n").filter(l => l.startsWith("TRACK\t")).map(l => {
    const p = l.split("\t"), fl = parseInt(p[3], 10) || 0;
    return { idx: parseInt(p[1], 10), name: (p[2] || "").replace(/\\t/g, " ").replace(/\\n/g, " ").replace(/\\\\/g, "\\"),
      flags: fl, folder: !!(fl & 1), mute: !!(fl & 8), solo: !!(fl & 16) || !!(fl & 32), vol: parseFloat(p[4]) || 0,
      pan: parseFloat(p[5]) || 0, peak: (parseInt(p[6], 10) || -1500) / 10, color: parseInt(p[13], 10) || 0 };
  }).filter(t => t.idx > 0);
  RC.extVal = (txt, key) => {
    const l = txt.split("\n").find(x => x.startsWith("EXTSTATE\tReaCue\t" + key + "\t") || x === "EXTSTATE\tReaCue\t" + key);
    return l == null ? null : (l.split("\t")[3] || "");
  };
  const EXT_KEYS = ["remote_alive", "remote_ack", "rehearsal", "studio"];
  RC.extra = [];                         // commandes ajoutées à chaque interrogation (écran)
  RC.onPoll = [];
  RC.poll = async () => {
    const t0 = performance.now();
    try {
      const q = ["TRANSPORT", "TRACK"].concat(EXT_KEYS.map(k => "GET/EXTSTATE/ReaCue/" + k), RC.extra).join(";");
      const txt = await RC.api(q);
      const now = performance.now();
      const f = txt.split("\n").find(l => l.startsWith("TRANSPORT"));
      if (!f) throw new Error("bad answer");
      const p = f.split("\t"), ps = parseInt(p[1], 10), pos = parseFloat(p[2]);
      const S = RC.state;
      S.rtt = S.rtt * 0.8 + (now - t0) * 0.2;
      const playing = ps === 1 || ps === 5;
      const measured = pos + (playing ? S.rtt / 2000 : 0);
      const predicted = S.play ? S.pos + (now - S.at) / 1000 * (S.rate || 1) : S.pos;
      const target = (playing && Math.abs(measured - predicted) < 0.06) ? predicted + (measured - predicted) * 0.25 : measured;
      Object.assign(S, { play: playing ? 1 : 0, ps, pos: target, at: now, ok: true, lastOk: now, repeat: p[3] !== "0" });
      S.tracks = RC.parseTracks(txt);
      for (const k of EXT_KEYS) S.ext[k] = RC.extVal(txt, k);
      if (S.ext.remote_alive != null && S.ext.remote_alive !== S.alive) { S.alive = S.ext.remote_alive; S.aliveAt = now; }
      RC.parseStudio(S.ext.studio);
      RC.parseReh(S.ext.rehearsal);
      RC.ackReply(S.ext.remote_ack);
      RC.onPoll.forEach(fn => fn(txt));
    } catch (e) { RC.state.ok = false; }
  };
  RC.pos = () => { const S = RC.state; return S.play ? S.pos + (performance.now() - S.at) / 1000 * (S.rate || 1) : S.pos; };
  RC.webOk = () => RC.state.ok && performance.now() - RC.state.lastOk < 2500;
  RC.windowOk = () => RC.webOk() && RC.state.alive !== "" && performance.now() - RC.state.aliveAt < 3000;

  // ReaCue/studio = vitesse|transposition|passage|passages|de|à  (publié par la fenêtre ReaCue)
  RC.studio = { rate: 1, tr: 0, pass: 0, n: 0, from: 0, to: 0 };
  RC.parseStudio = v => {
    if (!v) return;
    const [rate, tr, pass, n, from, to] = v.split("|");
    RC.studio = { rate: parseFloat(rate) || 1, tr: parseInt(tr, 10) || 0, pass: parseInt(pass, 10) || 0,
      n: parseInt(n, 10) || 0, from: parseFloat(from) || 0, to: parseFloat(to) || 0 };
    RC.state.rate = RC.studio.rate;
  };
  // ReaCue/rehearsal = on|vitesse|début|fin|noms (boucle de répétition)
  RC.reh = { on: false, rate: 1, a: null, b: null, names: "" };
  RC.parseReh = v => {
    if (v == null) return;
    const [on, rate, a, b, names] = v.split("|");
    RC.reh = { on: on === "1", rate: parseFloat(rate) || 1, a: a ? parseFloat(a) : null, b: b ? parseFloat(b) : null, names: names || "" };
  };

  // actions du transport (identifiants d'actions REAPER)
  RC.ACT = { play: 1007, pause: 1008, stop: 1016, playpause: 40073 };
  RC.seek = t => RC.send("SET/POS/" + Math.max(0, t).toFixed(4));
  RC.trackSet = (idx, what, v) => RC.send(`SET/TRACK/${idx}/${what}/${v}`);

  // volume : 1 = 0 dB ; fader : position 0..1 <-> dB (+6 en haut, 0 dB à ~71 %, -inf en bas)
  RC.volToDb = v => v > 1e-6 ? 20 * Math.log10(v) : -Infinity;
  RC.dbToVol = d => d === -Infinity || d < -150 ? 0 : Math.pow(10, d / 20);
  RC.dbToPos = d => d === -Infinity ? 0 : RC.clamp(Math.pow(10, (d - 6) / 40), 0, 1);
  RC.posToDb = p => p <= 0.004 ? -Infinity : RC.clamp(6 + 40 * Math.log10(p), -150, 6);
  RC.fmtDb = d => d === -Infinity || d < -149 ? "-inf dB" : (d > 0.05 ? "+" : "") + d.toFixed(1) + " dB";

  // ------------------------------------------------------------------ commandes ReaCue (PIN)
  RC.pin = () => { const p = RC.load("reacue_pin"); return p && /^\d{4}$/.test(p) ? p : null; };
  const q = { busy: null, list: [], lastAck: "", asking: false };
  RC.onAck = null;                       // (cmd, résultat) -> écran
  RC.askPin = null;                      // (ok, annuler) -> écran : demande le PIN, puis appelle ok() ou annuler()
  RC.cmd = (cmd, arg, cb) => { q.list.push({ cmd, arg: arg == null ? "" : String(arg), cb }); pump(); };
  function pump() {
    if (q.busy) {
      if (performance.now() - q.busy.at < 4000) return;
      const b = q.busy; q.busy = null;                     // pas de réponse : fenêtre fermée ?
      b.cb && b.cb("timeout"); RC.onAck && RC.onAck(b.cmd, "timeout");
    }
    const c = q.list.shift();
    if (!c) return;
    const pin = RC.pin();
    if (!pin) {
      q.list.unshift(c);
      if (RC.askPin && !q.asking) {
        q.asking = true;
        RC.askPin(() => { q.asking = false; pump(); },
          () => { q.asking = false; q.list.splice(0).forEach(x => x.cb && x.cb("cancel")); });
      }
      return;
    }
    c.nonce = Date.now().toString(36) + Math.random().toString(36).slice(2, 7);
    c.at = performance.now();
    q.busy = c;
    RC.send("SET/EXTSTATE/ReaCue/remote/" + encodeURIComponent(`${c.cmd}|${c.arg}|${pin}|${c.nonce}`));
  }
  RC.ackReply = ack => {
    if (!ack || ack === q.lastAck) { pump(); return; }
    q.lastAck = ack;
    const [nonce, res] = ack.split("|");
    if (q.busy && q.busy.nonce === nonce) {
      const b = q.busy; q.busy = null;
      if (res === "badpin") RC.store("reacue_pin", null);
      b.cb && b.cb(res); RC.onAck && RC.onAck(b.cmd, res);
    }
    pump();
  };
  setInterval(pump, 500);

  // ------------------------------------------------------------------ données publiées
  RC.getJSON = async name => {
    const r = await fetch(name + "?t=" + Date.now(), { cache: "no-store" });
    if (!r.ok) throw new Error(r.status);
    return r.json();
  };
  RC.decodePeaks = b64 => {
    const s = atob(b64 || ""), a = new Uint8Array(s.length);
    for (let i = 0; i < s.length; i++) a[i] = s.charCodeAt(i);
    return a;                            // min, max entrelacés ; 127 = 0
  };

  // ------------------------------------------------------------------ calculs musicaux
  // position t (timeline) -> {bar (1-based, ≤ 0 = count-in), frac, beat (0-based), sub (0-3), k}
  RC.locate = (song, t) => {
    const bt = song.bar_times, ci = song.count_in_bars || 0, n = song.beats_per_bar || 4;
    if (!bt || bt.length < 2) return { pre: true, bar: 0, frac: 0, beat: 0, sub: 0, k: 0 };
    if (t < bt[0]) return { pre: true, bar: -ci + 1, frac: 0, beat: 0, sub: 0, k: 0 };
    let lo = 0, hi = bt.length - 1;
    if (t >= bt[hi]) return { end: true, bar: song.n_bars + 1, frac: 0, beat: 0, sub: 0, k: hi };
    while (hi - lo > 1) { const m = (lo + hi) >> 1; if (bt[m] <= t) lo = m; else hi = m; }
    const frac = (t - bt[lo]) / (bt[lo + 1] - bt[lo]), bf = frac * n, beat = Math.floor(bf);
    return { bar: lo - ci + 1, frac, beat, sub: Math.min(3, Math.floor((bf - beat) * 4)), k: lo };
  };
  RC.barT = (song, b) => song.bar_times[RC.clamp(b - 1 + (song.count_in_bars || 0), 0, song.bar_times.length - 1)];
  RC.localBpm = (song, k) => {
    const bt = song.bar_times;
    if (!bt || bt.length < 2) return song.bpm || 0;
    k = RC.clamp(k, 0, bt.length - 2);
    return 60 * (song.beats_per_bar || 4) / (bt[k + 1] - bt[k]);
  };
  RC.fmtPos = (song, t) => {
    const L = RC.locate(song, t);
    if (L.pre) return "---.-.-";
    if (L.end) return "END";
    const b = L.bar < 1 ? "-" + String(Math.abs(L.bar - 1)).padStart(2, "0") : String(L.bar).padStart(3, "0");
    return `${b}.${L.beat + 1}.${L.sub + 1}`;
  };
  RC.fmtTime = t => {
    const neg = t < 0; t = Math.abs(t);
    const m = Math.floor(t / 60), s = t - m * 60;
    return (neg ? "-" : "") + String(m).padStart(2, "0") + ":" + s.toFixed(2).padStart(5, "0");
  };
  // même calcul que lighting.seconds_to_smpte : HH:MM:SS:FF non drop-frame
  RC.smpte = (sec, fps) => {
    sec = Math.max(0, sec); fps = fps || 25;
    const tf = Math.round(sec * fps), fr = tf % Math.round(fps), ts = Math.floor(tf / fps);
    const p = v => String(Math.floor(v)).padStart(2, "0");
    return `${p(Math.floor(ts / 3600))}:${p(Math.floor(ts / 60) % 60)}:${p(ts % 60)}:${p(fr)}`;
  };
  const SH = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"];
  const FL = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"];
  const NOTE = { C: 0, D: 2, E: 4, F: 5, G: 7, A: 9, B: 11 };
  RC.transNote = (n, semi) => {
    const m = /^([A-G])([#b♯♭]?)(.*)$/.exec(n || "");
    if (!m || !semi) return n;
    let v = NOTE[m[1]] + (m[2] === "#" || m[2] === "♯" ? 1 : m[2] === "b" || m[2] === "♭" ? -1 : 0);
    v = ((v + semi) % 12 + 12) % 12;
    return ((m[2] === "b" || m[2] === "♭") ? FL : SH)[v] + m[3];
  };
  // accord « A/C# » ou « Bm7 » transposé de semi demi-tons
  RC.transChord = (c, semi) => String(c || "").split("/").map(x => RC.transNote(x, semi)).join("/");

  // rôle d'une piste d'après son nom (mêmes noms que la fenêtre ReaCue / concert.py)
  const ROLE_NAMES = {
    vocals: ["chant", "vocals", "voix lead", "vocal", "lead vocal", "voice"], drums: ["batterie", "drums", "batt", "drum"],
    bass: ["basse", "bass"], guitars: ["guitares", "guitars", "guitare", "guitar"], lead_guitar: ["guitare solo", "lead guitar", "lead guitars"],
    keys: ["claviers", "keys", "piano", "clavier", "synth", "keyboard"], other: ["autres", "other"], mix: ["mix"],
  };
  RC.GENERATED = { CUES: 1, "TIMECODE LTC": 1, "TIMECODE MTC": 1 };
  RC.isClick = n => n === "CLICK";
  RC.isVoice = n => n === "VOIX" || n === "VOICE";
  RC.roleOf = name => {
    if (RC.isClick(name)) return "click";
    if (RC.isVoice(name)) return "voice";
    const n = String(name || "").toLowerCase().replace(/\s+\d+$/, "").trim();
    for (const [r, list] of Object.entries(ROLE_NAMES)) if (list.includes(n)) return r;
    for (const [r, list] of Object.entries(ROLE_NAMES)) if (list.some(x => n.includes(x))) return r;
    return "other";
  };
  RC.roleColor = r => getComputedStyle(document.documentElement).getPropertyValue("--c-" + (r || "other").split("_2")[0]).trim() || "#8A9099";
})();

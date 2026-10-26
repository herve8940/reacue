/* ReaCue Studio — écran TRAVAIL.
   Afficheurs (position, temps, tempo et vitesse, ton, SMPTE), règle structure + accords (clic = aller,
   double-clic = boucler), une ligne par stem (forme d'onde, M / S, volume), console (pan, vumètre, fader),
   transport, boucle de section avec rampe de vitesse, CLICK / VOIX, « mon instrument » (coupé), transposition,
   exports audio. Mute / solo / volume / pan / position : API web native de REAPER (/_/SET/TRACK…, /_/SET/POS) ;
   boucle, vitesse, transposition et export : commandes ReaCue exécutées par la fenêtre ReaCue (PIN). */
(function () {
  "use strict";
  const { $, esc } = RC;

  // ------------------------------------------------------------------ textes
  RC.STR.fr = {
    navBiblio: "BIBLIO", navTravail: "TRAVAIL", navGroupe: "GROUPE", navConcert: "CONCERT", navLumiere: "LUMIÈRE",
    soon: m => `Écran ${m} : bientôt.`, lPos: "POSITION", lTime: "TEMPS", lTempo: "TEMPO", lKey: "TON",
    me: "MON INSTRUMENT", meNone: "— aucun —", meTag: "MOI", trLabel: "TON", export: "EXPORTER",
    waiting: "Connexion à REAPER…", noWeb: "REAPER ne répond pas : vérifie l'interface web (Préférences > Control/OSC/web).",
    noSong: "Aucun morceau publié : prépare le morceau avec ReaCue (les pistes restent pilotables).",
    noTracks: "Aucune piste audio dans le projet.", noWave: "PAS DE FORME D'ONDE",
    meta: (n, sig, bars, sr) => [n ? `${n} STEMS` : "", sig, bars ? `${bars} MES.` : "", sr].filter(Boolean).join(" · "),
    tools: "MARQUEURS · ACCORDS · STRUCTURE", muted: "MUET",
    tHome: "Début du morceau", tStop: "Stop", tPlay: "Lecture / pause (barre d'espace)", tLoop: "Boucler la section en cours (fenêtre ReaCue)",
    tNext: "Section suivante", tSec: "Clic : aller à la section · double-clic : la boucler", tChord: "Clic : aller à cet accord",
    loopOff: "BOUCLE —", loop: (n, p, k) => `BOUCLE ${n}${k ? ` · ${p}/${k}` : ""}`,
    ramp: (a, b) => `RAMPE ${a}→${b} %`, clickOn: "CLICK ON", clickOff: "CLICK OFF", voiceOn: "VOIX ON", voiceOff: "VOIX OFF",
    ledPrompt: "PROMPTEUR", ledReaperOk: "REAPER et la fenêtre ReaCue répondent.",
    ledReaperWin: "REAPER répond, mais la fenêtre ReaCue est fermée : boucle, rampe, transposition et export indisponibles (ouvre « ReaCue » dans REAPER).",
    ledReaperBad: "REAPER ne répond pas (interface web).", ledPromptOk: "Morceau publié (reacue_song.json).", ledPromptBad: "Aucun morceau publié.",
    ledLtc: "Timecode LTC envoyé par REAPER (piste TIMECODE LTC).", ledLtcNone: "Pas de sortie LTC configurée (onglet Lumière).",
    trTip: "Transposer le morceau d'un demi-ton (pitch des items par REAPER, mode de pitch par défaut du projet). Qualité correcte jusqu'à ±2 demi-tons ; au-delà, artefacts audibles (voix, batterie). Double-clic sur TON : revenir à 0.",
    trOff: "Transposition : ouvre la fenêtre ReaCue dans REAPER (et saisis le PIN).",
    needWin: "Ouvre la fenêtre « ReaCue » dans REAPER (commande exécutée par elle).",
    refused: "Commande refusée.", timeout: "Pas de réponse de la fenêtre ReaCue.", noconcert: "Ouvre un projet préparé par ReaCue.",
    badpin: "PIN incorrect : saisis celui affiché dans la fenêtre ReaCue (onglet Scène).",
    pinHelp: "Code à 4 chiffres affiché dans la fenêtre ReaCue de REAPER (onglet Scène, bouton PIN). Nécessaire pour la boucle, la rampe, la transposition et l'export.",
    pin4: "4 chiffres.", cancel: "ANNULER", close: "FERMER",
    expTitle: "EXPORTER", expStems: "INSTRUMENTS", all: "TOUS", none: "AUCUN", withClick: "avec le click",
    expRange: "RÉGION", rSong: "morceau entier", rSection: "section", rBars: "mesures", rSel: "sélection REAPER",
    expMode: "FICHIERS", mSep: "un fichier par instrument", mMix: "tout mixé en un fichier", expFormat: "FORMAT", expGo: "EXPORTER",
    expNoStem: "Coche au moins un instrument (ou le click).", expSent: "Demande envoyée à REAPER…",
    expRunning: "Export en cours…", expDone: (n, d) => `${n} fichier(s) dans ${d}`, expErr: e => `Échec : ${e}`,
    expStuck: "Pas de nouvelles de l'export (voir ReaCueMCP/cli.log).",
    rampTitle: "RAMPE DE VITESSE", rampFrom: "de", rampTo: "à", rampN: "en", rampPasses: "passages",
    rampHelp: "Boucle la section en cours et accélère à chaque passage, du tempo de départ au tempo final (hauteur conservée).",
    rampSec: n => `Section : ${n}`, rampGo: "LANCER", rampOff: "ARRÊTER", rampBad: "Valeurs : 50 à 100 %, 2 à 32 passages.",
  };
  RC.STR.en = {
    navBiblio: "LIBRARY", navTravail: "PRACTICE", navGroupe: "BAND", navConcert: "SHOW", navLumiere: "LIGHTS",
    soon: m => `${m} screen: coming soon.`, lPos: "POSITION", lTime: "TIME", lTempo: "TEMPO", lKey: "KEY",
    me: "MY INSTRUMENT", meNone: "— none —", meTag: "ME", trLabel: "KEY", export: "EXPORT",
    waiting: "Connecting to REAPER…", noWeb: "REAPER does not answer: check the web interface (Preferences > Control/OSC/web).",
    noSong: "No song published: prepare the song with ReaCue (tracks can still be controlled).",
    noTracks: "No audio track in the project.", noWave: "NO WAVEFORM",
    meta: (n, sig, bars, sr) => [n ? `${n} STEMS` : "", sig, bars ? `${bars} BARS` : "", sr].filter(Boolean).join(" · "),
    tools: "MARKERS · CHORDS · STRUCTURE", muted: "MUTED",
    tHome: "Start of the song", tStop: "Stop", tPlay: "Play / pause (space bar)", tLoop: "Loop the current section (ReaCue window)",
    tNext: "Next section", tSec: "Click: go to the section · double-click: loop it", tChord: "Click: go to this chord",
    loopOff: "LOOP —", loop: (n, p, k) => `LOOP ${n}${k ? ` · ${p}/${k}` : ""}`,
    ramp: (a, b) => `RAMP ${a}→${b} %`, clickOn: "CLICK ON", clickOff: "CLICK OFF", voiceOn: "VOICE ON", voiceOff: "VOICE OFF",
    ledPrompt: "PROMPTER", ledReaperOk: "REAPER and the ReaCue window answer.",
    ledReaperWin: "REAPER answers, but the ReaCue window is closed: loop, ramp, transpose and export unavailable (open “ReaCue” in REAPER).",
    ledReaperBad: "REAPER does not answer (web interface).", ledPromptOk: "Song published (reacue_song.json).", ledPromptBad: "No song published.",
    ledLtc: "LTC timecode sent by REAPER (TIMECODE LTC track).", ledLtcNone: "No LTC output configured (Lighting tab).",
    trTip: "Transpose the song by one semitone (item pitch in REAPER, project default pitch mode). Fine up to ±2 semitones; beyond that, audible artefacts (vocals, drums). Double-click KEY: back to 0.",
    trOff: "Transpose: open the ReaCue window in REAPER (and enter the PIN).",
    needWin: "Open the “ReaCue” window in REAPER (it runs the command).",
    refused: "Command refused.", timeout: "No answer from the ReaCue window.", noconcert: "Open a project prepared by ReaCue.",
    badpin: "Wrong PIN: enter the one shown in the ReaCue window (Stage tab).",
    pinHelp: "4-digit code shown in REAPER's ReaCue window (Stage tab, PIN button). Needed for loop, ramp, transpose and export.",
    pin4: "4 digits.", cancel: "CANCEL", close: "CLOSE",
    expTitle: "EXPORT", expStems: "INSTRUMENTS", all: "ALL", none: "NONE", withClick: "with the click",
    expRange: "RANGE", rSong: "whole song", rSection: "section", rBars: "bars", rSel: "REAPER time selection",
    expMode: "FILES", mSep: "one file per instrument", mMix: "everything mixed in one file", expFormat: "FORMAT", expGo: "EXPORT",
    expNoStem: "Tick at least one instrument (or the click).", expSent: "Request sent to REAPER…",
    expRunning: "Exporting…", expDone: (n, d) => `${n} file(s) in ${d}`, expErr: e => `Failed: ${e}`,
    expStuck: "No news from the export (see ReaCueMCP/cli.log).",
    rampTitle: "SPEED RAMP", rampFrom: "from", rampTo: "to", rampN: "over", rampPasses: "passes",
    rampHelp: "Loops the current section and speeds up at each pass, from the start tempo to the final tempo (pitch kept).",
    rampSec: n => `Section: ${n}`, rampGo: "START", rampOff: "STOP", rampBad: "Values: 50 to 100 %, 2 to 32 passes.",
  };
  const T = RC.t;

  // ------------------------------------------------------------------ état
  let data = null, song = null, cIdx = -1, peaks = null, peaksKey = "";
  let rows = [], strips = [], trackSig = "", rulerKey = "";
  const edits = {};                      // idx -> {vol, pan, until} : réglage en cours depuis la page
  let meName = RC.load("reacue_studio_me") || "", meApplied = "";
  const meters = {};

  function toast(msg, bad) {
    const el = $("toast");
    el.textContent = msg; el.classList.toggle("bad", !!bad); el.classList.add("show");
    clearTimeout(toast.t); toast.t = setTimeout(() => el.classList.remove("show"), 3200);
  }
  RC.onAck = (cmd, res) => {
    if (res === "ok" || res === "cancel") return;
    toast(T({ badpin: "badpin", noconcert: "noconcert", timeout: "timeout" }[res] || "refused"), true);
  };

  // ------------------------------------------------------------------ données
  async function loadSong() {
    try {
      const d = await RC.getJSON("reacue_song.json");
      if (!data || d.id !== data.id) {
        data = d; cIdx = -1;
        RC.data = d; RC.onData.forEach(f => f(d));
        if (!RC.LANG_FIXED && !RC.load("reacue_studio_lang") && RC.STR[d.language || (d.songs && d.songs[0].language)])
          RC.setLang(d.language || d.songs[0].language, false);
        pickSong(RC.pos(), true);
      }
    } catch (e) { if (!data) { song = null; renderHead(); } }
  }
  function pickSong(t, force) {
    if (!data) return;
    let s = data, i = -1;
    if (data.concert && Array.isArray(data.songs) && data.songs.length) {
      i = 0;
      data.songs.forEach((x, k) => { if ((x.start_t || 0) <= t + 0.05) i = k; });
      s = data.songs[i];
    }
    if (force || i !== cIdx) { cIdx = i; song = s; rulerKey = ""; renderHead(); loadPeaks(); }
  }
  async function loadPeaks() {
    if (!song) return;
    try {
      const p = await RC.getJSON("reacue_peaks.json");
      const key = (p.song_id || "") + ":" + (p.tracks || []).length;
      if (p.song_id && p.song_id !== song.id) { if (peaks) { peaks = null; peaksKey = ""; trackSig = ""; } return; }
      if (key !== peaksKey) {
        peaks = p; peaksKey = key;
        peaks.byName = {};
        (p.tracks || []).forEach(tr => { peaks.byName[tr.name] = { ...tr, bytes: RC.decodePeaks(tr.data) }; });
        trackSig = ""; renderHead();
      }
    } catch (e) { /* pas encore publié */ }
  }
  setInterval(loadSong, 4000);
  setInterval(() => { if (song && (!peaks || peaks.song_id !== song.id)) loadPeaks(); }, 10000);

  // ------------------------------------------------------------------ pistes
  const isStem = t => !t.folder && !RC.GENERATED[t.name] && !RC.isClick(t.name) && !RC.isVoice(t.name);
  const stemTracks = () => RC.state.tracks.filter(isStem);
  const findTrack = name => RC.state.tracks.find(t => t.name === name);
  const SHORT = { vocals: ["VOX", "VOX"], drums: ["DRM", "DRM"], bass: ["BAS", "BAS"], guitars: ["GTR", "GTR"],
    lead_guitar: ["SOL", "LDG"], keys: ["KEY", "KEY"], mix: ["MIX", "MIX"], click: ["CLK", "CLK"], voice: ["ANN", "CUE"] };
  function shortName(t, used) {
    const r = trackRole(t);
    let s = SHORT[r] ? SHORT[r][RC.LANG === "en" ? 1 : 0] :
      String(t.name).normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/[^A-Za-z0-9]/g, "").slice(0, 3).toUpperCase() || "TRK";
    let k = 2, base = s;
    while (used[s]) s = base.slice(0, 2) + (k++);
    used[s] = 1;
    return s;
  }
  function trackRole(t) {
    const p = peaks && peaks.byName && peaks.byName[t.name];
    const byName = RC.roleOf(t.name);
    return byName !== "other" ? byName : (p && p.role) || "other";
  }
  function colorOf(t) {
    if (t.color & 0x1000000) {               // couleur personnalisée de la piste REAPER (0x01rrggbb) : non utilisée,
      /* on garde la palette Studio par rôle pour la lisibilité */
    }
    return RC.roleColor(trackRole(t));
  }

  // ------------------------------------------------------------------ en-tête du morceau
  function renderHead() {
    const st = stemTracks();
    $("title").textContent = song ? song.title : "—";
    const sr = peaks && peaks.sr ? (peaks.sr / 1000).toLocaleString(RC.LANG === "fr" ? "fr-FR" : "en-US", { maximumFractionDigits: 1 }) + " kHz" : "";
    $("meta").textContent = song ? T("meta", st.length, `${song.beats_per_bar || 4}/4`, song.n_bars, sr) : (RC.webOk() ? T("noSong") : "");
    rulerKey = "";
  }

  // ------------------------------------------------------------------ règle : sections + accords
  const view = () => {
    if (!song || !song.bar_times || song.bar_times.length < 2) return null;
    return { a: song.bar_times[0], b: song.bar_times[song.bar_times.length - 1] };
  };
  const pct = (t, V) => RC.clamp((t - V.a) / (V.b - V.a), 0, 1) * 100;
  let chordSegs = [];
  function buildRuler() {
    const V = view();
    const key = (song ? song.id : "") + RC.LANG + RC.studio.tr + $("ruler").clientWidth;
    if (key === rulerKey) return;
    rulerKey = key;
    const secs = $("secs"), ch = $("chords");
    secs.innerHTML = ""; ch.innerHTML = ""; chordSegs = [];
    if (!V) return;
    const ci = song.count_in_bars || 0;
    if (ci > 0) {                                  // count-in : petit bloc neutre
      const d = document.createElement("div");
      d.className = "tv-sec"; d.style.flex = String(RC.barT(song, 1) - V.a); d.textContent = "";
      d.dataset.t = String(V.a); d.title = T("tSec");
      secs.appendChild(d);
    }
    song.sections.forEach((s, i) => {
      const d = document.createElement("div");
      const t0 = RC.barT(song, s.start_bar), t1 = RC.barT(song, s.end_bar + 1);
      d.className = "tv-sec"; d.style.flex = String(Math.max(0.001, t1 - t0));
      d.style.borderTopColor = s.color || "#4A5361";
      d.textContent = s.name; d.title = `${s.name} · ${s.start_bar}–${s.end_bar} — ${T("tSec")}`;
      d.dataset.i = String(i); d.dataset.t = String(t0);
      secs.appendChild(d);
    });
    // accords : un bloc par changement d'accord, placé dans le temps
    const bpb = song.beats_per_bar || 4, segs = [];
    (song.chords || []).forEach(e => {
      const k = e.bar - 1 + ci, bt = song.bar_times;
      if (k < 0 || k + 1 >= bt.length) return;
      (e.chords || []).forEach(c => {
        const t = bt[k] + (bt[k + 1] - bt[k]) * ((c.beat || 1) - 1) / bpb;
        const name = RC.transChord(c.chord, RC.studio.tr);
        if (!segs.length || segs[segs.length - 1].name !== name) segs.push({ t, name });
      });
    });
    segs.forEach((s, i) => {
      s.end = i + 1 < segs.length ? segs[i + 1].t : V.b;
      if (s.name === "N" || s.name === "") return;
      const d = document.createElement("div");
      d.className = "tv-ch"; d.hidden = true;
      d.textContent = s.name; d.title = `${s.name} — ${T("tChord")}`; d.dataset.t = String(s.t);
      s.el = d;
      ch.appendChild(d);
    });
    chordSegs = segs;
  }
  // accords : fenêtre « loupe » de CHORD_BARS mesures qui défile sous la tête de lecture ; la tête est à la même
  // abscisse que sur la ligne des sections (une seule tête pour les deux lignes)
  const CHORD_BARS = 16;
  function placeChords(t, V) {
    if (!chordSegs.length) return;
    const span = Math.min(V.b - V.a, CHORD_BARS * 60 * (song.beats_per_bar || 4) / (song.bpm || 120));
    const f = RC.clamp((t - V.a) / (V.b - V.a), 0, 1);
    const w0 = RC.clamp(t - f * span, V.a, V.b - span), w1 = w0 + span;
    const W = $("chords").clientWidth || 1;
    chordSegs.forEach(s => {
      if (!s.el) return;
      const vis = s.end > w0 && s.t < w1;
      if (s.el.hidden === vis) s.el.hidden = !vis;
      if (!vis) return;
      const l = (Math.max(s.t, w0) - w0) / span * 100, r = (Math.min(s.end, w1) - w0) / span * 100;
      s.el.style.left = l + "%"; s.el.style.width = (r - l) + "%";
      s.el.classList.toggle("narrow", (r - l) * W / 100 < 22);
      s.el.classList.toggle("now", t >= s.t && t < s.end);
      s.el.classList.toggle("past", t >= s.end);
    });
  }
  $("secs").addEventListener("click", e => { const d = e.target.closest(".tv-sec"); if (d) RC.seek(parseFloat(d.dataset.t)); });
  $("secs").addEventListener("dblclick", e => {
    const d = e.target.closest(".tv-sec");
    if (d && d.dataset.i != null) loopSection(parseFloat(d.dataset.t));
  });
  $("chords").addEventListener("click", e => { const d = e.target.closest(".tv-ch"); if (d) RC.seek(parseFloat(d.dataset.t)); });

  function sectionIndexAt(t) {
    if (!song) return -1;
    const L = RC.locate(song, t);
    if (L.pre) return -1;
    return song.sections.findIndex(s => L.bar >= s.start_bar && L.bar <= s.end_bar);
  }

  // ------------------------------------------------------------------ lignes de stems + console
  function buildTracks() {
    const st = stemTracks(), all = RC.state.tracks.filter(t => isStem(t) || RC.isClick(t.name) || RC.isVoice(t.name));
    const sig = st.map(t => t.idx + ":" + t.name).join("|") + "#" + all.map(t => t.idx + ":" + t.name).join("|") + "#" + peaksKey + RC.LANG + meName;
    if (sig === trackSig) return;
    trackSig = sig;
    renderHead();
    // lignes
    const box = $("stems");
    box.querySelectorAll(".tv-row").forEach(r => r.remove());
    $("stemsEmpty").hidden = st.length > 0;
    $("stemsEmpty").textContent = RC.webOk() ? T("noTracks") : T("waiting");
    rows = st.map(t => {
      const r = document.createElement("div");
      const col = colorOf(t), me = t.name === meName;
      r.className = "tv-row";
      r.innerHTML = `<div class="sw" style="background:${col}"></div><div class="hd"><div class="nm">${esc(t.name)}${me ? " · " + esc(T("meTag")) : ""}</div>` +
        `<div class="ctl"><button class="rc-ms m" aria-label="Mute">M</button><button class="rc-ms s" aria-label="Solo">S</button><span class="db"></span></div></div>` +
        `<div class="wv"><canvas></canvas>${peaks && peaks.byName[t.name] ? "" : `<div class="none">${esc(T("noWave"))}</div>`}</div>`;
      box.appendChild(r);
      const row = { name: t.name, el: r, color: col, canvas: r.querySelector("canvas"), env: null, key: "", p: peaks && peaks.byName[t.name] };
      r.querySelector(".m").onclick = () => toggleTrack(row.name, "MUTE");
      r.querySelector(".s").onclick = () => toggleTrack(row.name, "SOLO");
      r.querySelector(".wv").addEventListener("click", e => {
        const V = view(); if (!V) return;
        const b = e.currentTarget.getBoundingClientRect();
        RC.seek(V.a + (e.clientX - b.left) / b.width * (V.b - V.a));
      });
      return row;
    });
    // console
    const con = $("console");
    con.innerHTML = "";
    const used = {};
    strips = all.map(t => {
      const s = document.createElement("div");
      const col = colorOf(t), me = t.name === meName;
      s.className = "tv-strip" + (me ? " me" : "");
      s.title = t.name;
      s.innerHTML = `<div class="tv-knob" title="Pan"><span></span></div><div class="tv-fad"><div class="tv-meter"><i></i></div>` +
        `<div class="tv-rail"><div class="tv-thumb"></div></div></div><div class="val"></div><div class="col" style="background:${col}"></div>` +
        `<div class="sh">${esc(shortName(t, used))}</div>`;
      con.appendChild(s);
      const strip = { name: t.name, el: s, knob: s.querySelector(".tv-knob span"), meter: s.querySelector(".tv-meter i"),
        rail: s.querySelector(".tv-rail"), thumb: s.querySelector(".tv-thumb"), val: s.querySelector(".val") };
      dragFader(strip); dragKnob(strip, s.querySelector(".tv-knob"));
      return strip;
    });
    fillMe();
  }

  function toggleTrack(name, what) {
    const t = findTrack(name);
    if (!t) return;
    const on = what === "MUTE" ? !t.mute : !t.solo;
    if (what === "MUTE") t.mute = on; else t.solo = on;      // affichage immédiat
    RC.trackSet(t.idx, what, on ? 1 : 0);
  }
  function setVol(t, v) {
    edits[t.idx] = { ...(edits[t.idx] || {}), vol: v, until: performance.now() + 800 };
    t.vol = v;
    RC.trackSet(t.idx, "VOL", v.toFixed(6));
  }
  function setPan(t, p) {
    edits[t.idx] = { ...(edits[t.idx] || {}), pan: p, until: performance.now() + 800 };
    t.pan = p;
    RC.trackSet(t.idx, "PAN", p.toFixed(4));
  }
  function throttle(fn, ms) {
    let last = 0, timer = null, args = null;
    return (...a) => {
      args = a;
      const now = performance.now();
      if (now - last >= ms) { last = now; fn(...args); }
      else { clearTimeout(timer); timer = setTimeout(() => { last = performance.now(); fn(...args); }, ms - (now - last)); }
    };
  }
  function dragFader(strip) {
    const send = throttle((t, v) => setVol(t, v), 60);
    const at = e => {
      const b = strip.rail.getBoundingClientRect();
      return RC.dbToVol(RC.posToDb(RC.clamp((b.bottom - e.clientY) / b.height, 0, 1)));
    };
    strip.rail.addEventListener("pointerdown", e => {
      const t = findTrack(strip.name); if (!t) return;
      strip.rail.setPointerCapture(e.pointerId);
      send(t, at(e));
      const mv = ev => send(t, at(ev));
      const up = () => { strip.rail.removeEventListener("pointermove", mv); strip.rail.removeEventListener("pointerup", up); };
      strip.rail.addEventListener("pointermove", mv);
      strip.rail.addEventListener("pointerup", up);
    });
    strip.rail.addEventListener("dblclick", () => { const t = findTrack(strip.name); if (t) setVol(t, 1); });
  }
  function dragKnob(strip, knob) {
    const send = throttle((t, p) => setPan(t, p), 60);
    knob.addEventListener("pointerdown", e => {
      const t = findTrack(strip.name); if (!t) return;
      knob.setPointerCapture(e.pointerId);
      const y0 = e.clientY, p0 = t.pan;
      const mv = ev => send(t, RC.clamp(p0 + (y0 - ev.clientY) / 100, -1, 1));
      const up = () => { knob.removeEventListener("pointermove", mv); knob.removeEventListener("pointerup", up); };
      knob.addEventListener("pointermove", mv);
      knob.addEventListener("pointerup", up);
    });
    knob.addEventListener("dblclick", () => { const t = findTrack(strip.name); if (t) setPan(t, 0); });
  }

  // forme d'onde : barres verticales (2 px + 1 px d'espace), partie jouée en couleur, tête de lecture
  function envelope(row, nb, V) {
    const p = row.p;
    if (!p) return null;
    const key = nb + ":" + V.a + ":" + V.b + ":" + peaksKey;
    if (row.env && row.envKey === key) return row.env;
    const hop = peaks.hop, n = p.bytes.length / 2, lo = new Float32Array(nb), hi = new Float32Array(nb);
    for (let i = 0; i < nb; i++) {
      const c0 = Math.floor((V.a + (V.b - V.a) * i / nb) / hop), c1 = Math.max(c0 + 1, Math.floor((V.a + (V.b - V.a) * (i + 1) / nb) / hop));
      let mn = 0, mx = 0;
      for (let c = Math.max(0, c0); c < Math.min(n, c1); c++) {
        const a = (p.bytes[2 * c] - 127) / 127, b = (p.bytes[2 * c + 1] - 127) / 127;
        if (a < mn) mn = a; if (b > mx) mx = b;
      }
      lo[i] = mn; hi[i] = mx;
    }
    row.env = { lo, hi }; row.envKey = key;
    return row.env;
  }
  function drawRow(row, t, V) {
    const cv = row.canvas, dpr = window.devicePixelRatio || 1;
    const w = Math.max(1, Math.round(cv.clientWidth * dpr)), h = Math.max(1, Math.round(cv.clientHeight * dpr));
    const step = 3 * dpr, nb = Math.max(1, Math.floor((w - 12 * dpr) / step));
    const headX = V ? 6 * dpr + (RC.clamp((t - V.a) / (V.b - V.a), 0, 1)) * nb * step : -10;
    const key = w + "x" + h + ":" + Math.floor(headX / step) + ":" + (V ? V.a + V.b : 0) + row.color + peaksKey;
    if (key === row.key) return;
    row.key = key;
    if (cv.width !== w || cv.height !== h) { cv.width = w; cv.height = h; }
    const g = cv.getContext("2d");
    g.clearRect(0, 0, w, h);
    const env = V && envelope(row, nb, V);
    if (env) {
      const mid = h / 2, amp = h / 2 * 0.88, bw = 2 * dpr;
      for (let i = 0; i < nb; i++) {
        const x = 6 * dpr + i * step;
        g.fillStyle = x + bw <= headX ? row.color : "#3A3F46";
        const y0 = mid - Math.max(env.hi[i] * amp, dpr), y1 = mid - Math.min(env.lo[i] * amp, -dpr);
        g.fillRect(x, y0, bw, y1 - y0);
      }
    }
    if (V && headX >= 0) {
      g.fillStyle = "rgba(255,138,61,0.25)"; g.fillRect(headX - 3 * dpr, 0, 8 * dpr, h);
      g.fillStyle = "#FF8A3D"; g.fillRect(headX, 0, 2 * dpr, h);
    }
  }

  // ------------------------------------------------------------------ « mon instrument »
  function fillMe() {
    const sel = $("meSel"), cur = meName;
    sel.innerHTML = `<option value="">${esc(T("meNone"))}</option>` + stemTracks().map(t =>
      `<option value="${esc(t.name)}"${t.name === cur ? " selected" : ""}>${esc(t.name)}</option>`).join("");
  }
  $("meSel").onchange = () => {
    const old = findTrack(meName), v = $("meSel").value;
    if (old && old.name !== v && old.mute) RC.trackSet(old.idx, "MUTE", 0);
    meName = v; RC.store("reacue_studio_me", v || null);
    meApplied = "";
    trackSig = "";
  };
  function applyMe() {
    if (!meName) return;
    const key = meName + "|" + (song ? song.id : "") + "|" + (data ? data.id : "");
    if (key === meApplied) return;
    const t = findTrack(meName);
    if (!t) return;
    meApplied = key;
    if (!t.mute) { t.mute = true; RC.trackSet(t.idx, "MUTE", 1); }
  }

  // ------------------------------------------------------------------ boucle, rampe, transposition
  function loopSection(t) {
    if (!RC.windowOk()) { toast(T("needWin"), true); return; }
    RC.cmd("loopsec", t.toFixed(3));
  }
  $("bLoop").onclick = () => {
    if (RC.reh.on && RC.reh.a != null) { RC.cmd("loopoff", ""); return; }
    if (!song) return;
    const i = Math.max(0, sectionIndexAt(RC.pos()));
    loopSection(RC.barT(song, song.sections[i].start_bar));
  };
  const rampCfg = () => {
    let c = null;
    try { c = JSON.parse(RC.load("reacue_studio_ramp") || "null"); } catch (e) { c = null; }
    return c && c.from ? c : { from: 85, to: 100, n: 8 };
  };
  $("cRamp").onclick = () => {
    const c = rampCfg();
    $("rFrom").value = c.from; $("rTo").value = c.to; $("rN").value = c.n;
    const i = song ? Math.max(0, sectionIndexAt(RC.pos())) : -1;
    $("rampSec").textContent = i >= 0 ? T("rampSec", RC.reh.on && RC.reh.names ? RC.reh.names : song.sections[i].name) : "";
    $("rampVeil").classList.add("show");
  };
  $("rClose").onclick = () => $("rampVeil").classList.remove("show");
  $("rOff").onclick = () => { RC.cmd("ramp", ""); $("rampVeil").classList.remove("show"); };
  $("rGo").onclick = () => {
    const f = Math.round(+$("rFrom").value), to = Math.round(+$("rTo").value), n = Math.round(+$("rN").value);
    if (!(f >= 50 && f <= 100 && to >= 50 && to <= 100 && n >= 2 && n <= 32)) { toast(T("rampBad"), true); return; }
    if (!RC.windowOk()) { toast(T("needWin"), true); return; }
    RC.store("reacue_studio_ramp", JSON.stringify({ from: f, to, n }));
    let at = "";
    if (!(RC.reh.on && RC.reh.a != null) && song) {
      const i = Math.max(0, sectionIndexAt(RC.pos()));
      at = RC.barT(song, song.sections[i].start_bar).toFixed(3);
    }
    RC.cmd("ramp", `${(f / 100).toFixed(2)}:${(to / 100).toFixed(2)}:${n}:${at}`);
    $("rampVeil").classList.remove("show");
  };
  function transpose(d) {
    if (!RC.windowOk()) { toast(T("trOff"), true); return; }
    RC.cmd("pitch", d);
  }
  $("trDown").onclick = () => transpose("-1");
  $("trUp").onclick = () => transpose("+1");
  $("lcdKey").parentElement.parentElement.addEventListener("dblclick", () => transpose("0"));

  // ------------------------------------------------------------------ transport
  $("bPlay").onclick = () => RC.send("" + (RC.state.play ? RC.ACT.pause : RC.ACT.play));
  $("bStop").onclick = () => RC.send("" + RC.ACT.stop);
  $("bHome").onclick = () => { const V = view(); RC.seek(V ? V.a : 0); };
  $("bNext").onclick = () => {
    if (!song) return;
    const t = RC.pos();
    const nx = song.sections.map(s => RC.barT(song, s.start_bar)).find(x => x > t + 0.05);
    if (nx != null) RC.seek(nx);
  };
  document.addEventListener("keydown", e => {
    if (e.code !== "Space" || /INPUT|SELECT|TEXTAREA|BUTTON/.test((e.target.tagName || ""))) return;
    e.preventDefault(); $("bPlay").onclick();
  });
  function chipToggle(pred, el) {
    const t = RC.state.tracks.find(x => pred(x.name));
    if (!t) return;
    t.mute = !t.mute;
    RC.trackSet(t.idx, "MUTE", t.mute ? 1 : 0);
  }
  $("cClick").onclick = () => chipToggle(RC.isClick);
  $("cVoice").onclick = () => chipToggle(RC.isVoice);

  // ------------------------------------------------------------------ navigation, langue, PIN
  document.querySelectorAll("#nav button").forEach(b => b.onclick = () => {
    if (RC.MODES.indexOf(b.dataset.mode) >= 0) RC.setMode(b.dataset.mode);
    else toast(T("soon", b.textContent.trim()));
  });
  RC.toast = toast;
  RC.onMode.push(m => { if (m === "travail") { trackSig = ""; rulerKey = ""; } });
  $("langBtn").onclick = () => RC.setLang(RC.LANG === "fr" ? "en" : "fr");
  RC.onLang.push(l => {
    $("langBtn").textContent = l === "fr" ? "EN" : "FR";
    $("trBox").title = T("trTip");
    $("pinVeil").querySelector("[data-t=pinHelp]").textContent = T("pinHelp");
    trackSig = ""; rulerKey = ""; renderHead();
  });
  let pinCb = null, pinCancel = null;
  RC.askPin = (cb, cancel) => {
    pinCb = cb; pinCancel = cancel; $("pinErr").textContent = ""; $("pinIn").value = "";
    $("pinVeil").classList.add("show"); setTimeout(() => $("pinIn").focus(), 50);
  };
  $("pinOk").onclick = () => {
    const v = $("pinIn").value.trim();
    if (!/^\d{4}$/.test(v)) { $("pinErr").textContent = T("pin4"); return; }
    RC.store("reacue_pin", v); $("pinVeil").classList.remove("show");
    const cb = pinCb; pinCb = null; pinCancel = null; cb && cb();
  };
  $("pinIn").addEventListener("keydown", e => { if (e.key === "Enter") $("pinOk").onclick(); });
  $("pinCancel").onclick = () => {
    $("pinVeil").classList.remove("show");
    const c = pinCancel; pinCb = null; pinCancel = null; c && c();
  };

  // ------------------------------------------------------------------ export
  const expState = { id: null, at: 0, timer: null };
  $("expBtn").onclick = () => {
    const box = $("expStems"), cands = RC.state.tracks.filter(t => isStem(t) || RC.isVoice(t.name));
    box.innerHTML = cands.map(t => `<label class="rc-check"><input type="checkbox" value="${esc(t.name)}"${isStem(t) ? " checked" : ""}>` +
      `<i style="background:${colorOf(t)}"></i><span>${esc(t.name)}</span></label>`).join("");
    const sel = $("expSection");
    sel.innerHTML = song ? song.sections.map((s, i) => `<option value="${i}">${esc(s.name)} (${s.start_bar}–${s.end_bar})</option>`).join("") : "";
    const i = sectionIndexAt(RC.pos());
    if (i >= 0) { sel.value = String(i); $("expFrom").value = song.sections[i].start_bar; $("expTo").value = song.sections[i].end_bar; }
    if (song) { $("expFrom").max = $("expTo").max = song.n_bars; }
    $("expVeil").classList.add("show");
  };
  $("expClose").onclick = () => $("expVeil").classList.remove("show");
  $("expAll").onclick = () => $("expStems").querySelectorAll("input").forEach(x => { x.checked = true; });
  $("expNone").onclick = () => $("expStems").querySelectorAll("input").forEach(x => { x.checked = false; });
  $("expSection").onchange = () => { document.querySelector("input[name=rng][value=section]").checked = true; };
  ["expFrom", "expTo"].forEach(id => $(id).addEventListener("input", () => { document.querySelector("input[name=rng][value=bars]").checked = true; }));
  const radio = n => (document.querySelector(`input[name=${n}]:checked`) || {}).value;
  function expMsg(txt, bad) { $("expMsg").textContent = txt; $("expMsg").classList.toggle("bad", !!bad); }
  $("expGo").onclick = async () => {
    const stems = [...$("expStems").querySelectorAll("input:checked")].map(x => x.value);
    const click = $("expClick").checked;
    if (!stems.length && !click) { expMsg(T("expNoStem"), true); return; }
    if (!RC.windowOk()) { expMsg(T("needWin"), true); return; }
    const kind = radio("rng");
    const range = { kind };
    if (kind === "section") range.section = parseInt($("expSection").value, 10) || 0;
    if (kind === "bars") { range.from = parseInt($("expFrom").value, 10) || 1; range.to = parseInt($("expTo").value, 10) || 1; }
    const id = Date.now().toString(36) + Math.random().toString(36).slice(2, 6);
    const req = { id, stems, click, format: radio("fmt"), kbps: parseInt($("expKbps").value, 10) || 320, range, mode: radio("mode") };
    $("expFiles").innerHTML = ""; $("expProg").style.width = "3%";
    expMsg(T("expSent"));
    await RC.send("SET/EXTSTATE/ReaCue/export_req/" + encodeURIComponent(JSON.stringify(req)));
    expState.id = id; expState.at = performance.now();
    RC.cmd("export", id, res => {
      if (res !== "ok") {
        expState.id = null; $("expProg").style.width = "0";
        expMsg(res === "cancel" ? "" : T(res === "badpin" ? "badpin" : res === "timeout" ? "timeout" : "refused"), res !== "cancel");
      }
    });
    clearInterval(expState.timer);
    expState.timer = setInterval(pollExport, 800);
  };
  async function pollExport() {
    if (!expState.id) { clearInterval(expState.timer); return; }
    let s = null;
    try { s = await RC.getJSON("reacue_export.json"); } catch (e) { s = null; }
    if (s && s.id === expState.id) {
      $("expProg").style.width = Math.round((s.progress || 0) * 100) + "%";
      if (s.state === "running") expMsg(s.step || T("expRunning"));
      else if (s.state === "done") {
        expMsg(T("expDone", (s.files || []).length, s.dir || ""));
        $("expFiles").innerHTML = (s.files || []).map(f => f.url ?
          `<a href="${esc(f.url)}" download="${esc(f.name)}"><span>${esc(f.name)}</span><small>${(f.bytes / 1048576).toFixed(1)} Mo</small></a>` :
          `<span class="rc-note">${esc(f.name)}</span>`).join("");
        expState.id = null;
      } else if (s.state === "error") { expMsg(T("expErr", s.message || ""), true); expState.id = null; }
    } else if (performance.now() - expState.at > 120000) { expMsg(T("expStuck"), true); expState.id = null; }
  }

  // ------------------------------------------------------------------ boucle d'affichage
  function led(id, cls, tip) { const el = $(id); el.className = "rc-led " + (cls || ""); el.title = tip || ""; }
  let pollBusy = false;
  async function tick() {
    if (pollBusy) return;
    pollBusy = true;
    await RC.poll();
    pollBusy = false;
    if (data) pickSong(RC.pos());
    buildTracks();
    applyMe();
  }
  setInterval(tick, 100);

  function frame() {
    requestAnimationFrame(frame);
    const t = RC.pos(), V = view(), S = RC.state;
    // afficheurs
    $("lcdTime").textContent = RC.fmtTime(t);
    if (song) {
      const L = RC.locate(song, t);
      $("lcdPos").textContent = RC.fmtPos(song, t);
      const bpm = RC.localBpm(song, L.k) * (RC.studio.rate || 1);
      $("lcdTempo").textContent = bpm.toFixed(1);
      const k = song.key && song.key.chord;
      $("lcdKey").textContent = k ? RC.transChord(k, RC.studio.tr) : "—";
    }
    $("lcdRate").textContent = Math.round((RC.studio.rate || 1) * 100) + " %";
    $("lcdTr").textContent = RC.studio.tr ? (RC.studio.tr > 0 ? "+" : "") + RC.studio.tr : "±0";
    const tc = (peaks && peaks.tc) || (song && song.lighting) || (data && data.lighting) || { fps: 25, offset_s: 0 };
    $("lcdTc").textContent = RC.smpte((tc.offset_s || 0) + Math.max(0, t), tc.fps || 25);
    if (RC.mode !== "travail") return;                   // autre écran : afficheurs seulement
    // règle
    buildRuler();
    if (V) {
      $("rulerHead").style.left = `calc(8px + (100% - 18px) * ${pct(t, V) / 100})`;
      const si = sectionIndexAt(t);
      $("secs").querySelectorAll(".tv-sec").forEach(d => {
        d.classList.toggle("now", d.dataset.i === String(si));
        const t0 = parseFloat(d.dataset.t);
        d.classList.toggle("looped", RC.reh.on && RC.reh.a != null && Math.abs(RC.reh.a - t0) < 0.05);
      });
      placeChords(t, V);
      const lp = $("rulerLoop");
      if (RC.reh.on && RC.reh.a != null && RC.reh.b != null) {
        lp.hidden = false;
        lp.style.left = `calc(8px + (100% - 16px) * ${pct(RC.reh.a, V) / 100})`;
        lp.style.width = `calc((100% - 16px) * ${(pct(RC.reh.b, V) - pct(RC.reh.a, V)) / 100})`;
      } else lp.hidden = true;
    }
    // pistes
    const now = performance.now();
    rows.forEach(row => {
      const tr = findTrack(row.name);
      if (tr) {
        row.el.classList.toggle("muted", tr.mute);
        row.el.querySelector(".m").classList.toggle("on", tr.mute);
        row.el.querySelector(".s").classList.toggle("on", tr.solo);
        row.el.querySelector(".db").textContent = tr.mute ? T("muted") : RC.fmtDb(RC.volToDb(tr.vol));
      }
      drawRow(row, t, V);
    });
    strips.forEach(st => {
      const tr = findTrack(st.name);
      if (!tr) return;
      const ed = edits[tr.idx];
      const vol = ed && ed.until > now && ed.vol != null ? ed.vol : tr.vol;
      const pan = ed && ed.until > now && ed.pan != null ? ed.pan : tr.pan;
      st.thumb.style.bottom = (RC.dbToPos(RC.volToDb(vol)) * 100) + "%";
      st.knob.style.transform = `rotate(${pan * 135}deg)`;
      st.val.textContent = RC.fmtDb(RC.volToDb(vol)).replace(" dB", "");
      st.el.classList.toggle("muted", tr.mute);
      const target = S.play ? RC.dbToPos(tr.peak) : 0;
      const m = meters[st.name] = Math.max(target, (meters[st.name] || 0) - 0.02);
      st.meter.style.height = (m * 100) + "%";
      st.meter.parentElement.style.setProperty("--mh", st.meter.parentElement.clientHeight + "px");
      st.el.title = `${tr.name} · ${RC.fmtDb(RC.volToDb(vol))} · pan ${Math.round(pan * 100)}`;
    });
    // transport, pastilles, voyants
    $("icPlay").hidden = !!S.play; $("icPause").hidden = !S.play;
    $("bPlay").classList.toggle("paused", S.ps === 2);
    const looping = RC.reh.on && RC.reh.a != null;
    $("bLoop").classList.toggle("sig", looping);
    const cl = $("cLoop");
    cl.textContent = looping ? T("loop", RC.reh.names || "", Math.min(RC.studio.pass, RC.studio.n), RC.studio.n) : T("loopOff");
    cl.className = "rc-chip" + (looping ? " sig" : "");
    const rc = rampCfg(), active = RC.studio.n > 0;
    $("cRamp").textContent = active ? T("ramp", Math.round(RC.studio.from * 100), Math.round(RC.studio.to * 100)) : T("ramp", rc.from, rc.to);
    $("cRamp").className = "rc-chip" + (active ? " ok" : "");
    const ck = S.tracks.find(x => RC.isClick(x.name)), vo = S.tracks.find(x => RC.isVoice(x.name));
    $("cClick").hidden = !ck; $("cVoice").hidden = !vo;
    if (ck) { $("cClick").textContent = T(ck.mute ? "clickOff" : "clickOn"); $("cClick").className = "rc-chip" + (ck.mute ? " off" : ""); }
    if (vo) { $("cVoice").textContent = T(vo.mute ? "voiceOff" : "voiceOn"); $("cVoice").className = "rc-chip" + (vo.mute ? " off" : ""); }
    const web = RC.webOk(), win = RC.windowOk();
    led("ledReaper", web ? (win ? "ok" : "warn") : "bad", T(web ? (win ? "ledReaperOk" : "ledReaperWin") : "ledReaperBad"));
    led("ledPrompt", song ? "ok" : "", T(song ? "ledPromptOk" : "ledPromptBad"));
    const ltc = tc && (tc.ltc || (tc.timecode && tc.timecode.ltc));
    led("ledLtc", ltc ? (S.play ? "ok" : "warn") : "", T(ltc ? "ledLtc" : "ledLtcNone"));
    $("trDown").disabled = $("trUp").disabled = !win;
    if (!web && !rows.length) $("stemsEmpty").textContent = T(S.lastOk > 0 ? "noWeb" : "waiting");
  }

  RC.setLang(RC.LANG, false);
  loadSong();
  requestAnimationFrame(frame);
})();

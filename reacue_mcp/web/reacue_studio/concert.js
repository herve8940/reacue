/* ReaCue Studio — écrans CONCERT et LUMIÈRE.
   Données : reacue_song.json publié par ReaCue (RC.data, chargé par l'écran Travail) : concert (setlist, morceaux
   placés sur la timeline : start_t / stop_t) ou morceau seul ; bloc « lighting » (cues grandMA3, timecode, fichiers).
   Commandes : protocole télécommande de la fenêtre ReaCue (PIN, RC.cmd) — song, prev, next, toggle, seek, tctest
   (test d'envoi du timecode de l'onglet Lumière). Fenêtre fermée : lecture / pause et sauts par l'API web native.
   Effets lumière : suggestions par type de section, en lecture seule (l'édition viendra plus tard). */
(function () {
  "use strict";
  const { $, esc } = RC;

  // ------------------------------------------------------------------ textes
  Object.assign(RC.STR.fr, {
    sPlay: "LECTURE", sPause: "PAUSE", sStop: "ARRÊT", sRec: "ENREG.",
    rank: (i, n) => `MORCEAU ${i} / ${n}`, single: "MORCEAU SEUL", cRest: "RESTE", cConcert: "CONCERT", cSong: "MORCEAU",
    secH: t => `SECTIONS · ${t}`, played: "JOUÉ", nowIn: (a, b) => `EN COURS · ${a}/${b}`, upcoming: "À VENIR", countIn: "DÉCOMPTE",
    prev: "◀ PRÉC.", next: "SUIV. ▶", play: "LECTURE", pause: "PAUSE", again: "ENCORE ?",
    cPrevTip: "Concert : morceau précédent (ou début du morceau en cours) · morceau seul : section précédente. Pendant la lecture : 2 appuis.",
    cNextTip: "Concert : morceau suivant · morceau seul : section suivante. Pendant la lecture : 2 appuis.",
    cPlayTip: "Lecture / pause (barre d'espace)", songTip: "Aller à ce morceau (pendant la lecture : 2 appuis)",
    secTip: "Aller à cette section", cueTip: "Aller à ce cue",
    noConcert: "Pas de concert ouvert : morceau seul. Pour la setlist, construis un concert (fenêtre ReaCue, onglet Concert) et ouvre-le.",
    noData: "Aucun morceau publié : ouvre un projet préparé par ReaCue (ou un concert) dans REAPER.",
    noWebC: "REAPER ne répond pas : vérifie l'interface web (Préférences > Control/OSC/web).",
    lightH: (s) => `LUMIÈRE · GRANDMA3 · TC SLOT ${s}`, lightH0: "LUMIÈRE · GRANDMA3",
    ltcOut: (o, f) => `LTC SORTIE ${o} · ${f}`, ltcNone: f => `PAS DE SORTIE LTC · ${f}`, fps: f => `${f} i/s`,
    colCue: "CUE", colTc: "TIMECODE", colSec: "SECTION", colFx: "EFFET", colType: "TYPE",
    pLtc: o => `REAPER → LTC ${o}`, pLtcOff: "LTC : AUCUNE SORTIE", pMtc: m => `MTC → ${m}`, pMtcOff: "MTC : AUCUN",
    pExpOk: "EXPORT À JOUR", pExpOld: "EXPORT À REFAIRE", pExpNone: "PAS D'EXPORT",
    pLtcTip: "Timecode LTC envoyé par REAPER (piste TIMECODE LTC) sur la sortie audio réglée dans l'onglet Lumière.",
    pMtcTip: "MIDI Timecode envoyé par REAPER (piste TIMECODE MTC) vers ce périphérique MIDI.",
    pExpTip: "Les cues exportés correspondent-ils aux sections actuelles du projet ? Sinon : onglet Lumière de la fenêtre ReaCue, « Exporter maintenant ».",
    test: "TEST 10 S", testOn: n => `ARRÊTER · ${n} S`,
    testTip: "Envoie 10 s de timecode : seules les pistes TIMECODE jouent (le public n'entend rien), puis tout est rétabli. Regarde sur la console que le TC Slot passe au vert.",
    testBad: "Test impossible : crée les pistes TIMECODE (onglet Lumière de la fenêtre ReaCue), quitte la répétition, arrête l'enregistrement.",
    noLight: "Pas d'export lumière pour ce projet : active l'export grandMA3 dans l'onglet Lumière de la fenêtre ReaCue (ou dans Réglages), puis prépare / republie le morceau.",
    noCues: "Aucun cue pour ce morceau.",
    lmTitle: "LUMIÈRE · GRANDMA3", lmNow: "CUE EN COURS", lmCues: "CUES", lmFxRo: "EFFETS SUGGÉRÉS · LECTURE SEULE",
    lmOut: "SORTIES TIMECODE", lmFiles: "FICHIERS GRANDMA3",
    lmMeta: (name, n, fps, tc) => [name, `${n} CUES`, fps, `DÉPART ${tc}`].filter(Boolean).join(" · "),
    kLtc: "LTC", kMtc: "MTC", kSlot: "TC SLOT", kFps: "IMAGES/S", kStart: "DÉPART", none: "aucune", noneM: "aucun",
    lmOneway: "Le LTC / MTC va dans un seul sens : ReaCue ne sait pas si la console le reçoit. Pendant le test, regarde que le TC Slot passe au vert et que le temps défile. Réglages des sorties : onglet Lumière de la fenêtre ReaCue.",
    lmUsb: "Dans le dossier grandMA3 à côté du projet : la même chose prête pour une clé USB (gma3_library/…, avec le plugin « ReaCue » qui importe tout et règle le TC Slot).",
    fSeq: "SEQUENCE", fTc: "TIMECODE", fCsv: "CONDUITE", noFiles: "Aucun fichier (export désactivé ou pas encore fait).",
    nowNone: "—", beforeFirst: "Avant le premier cue",
  });
  Object.assign(RC.STR.en, {
    sPlay: "PLAYING", sPause: "PAUSED", sStop: "STOPPED", sRec: "REC",
    rank: (i, n) => `SONG ${i} / ${n}`, single: "SINGLE SONG", cRest: "LEFT", cConcert: "SHOW", cSong: "SONG",
    secH: t => `SECTIONS · ${t}`, played: "PLAYED", nowIn: (a, b) => `NOW · ${a}/${b}`, upcoming: "NEXT", countIn: "COUNT-IN",
    prev: "◀ PREV", next: "NEXT ▶", play: "PLAY", pause: "PAUSE", again: "AGAIN?",
    cPrevTip: "Show: previous song (or start of the current one) · single song: previous section. While playing: tap twice.",
    cNextTip: "Show: next song · single song: next section. While playing: tap twice.",
    cPlayTip: "Play / pause (space bar)", songTip: "Go to this song (while playing: tap twice)",
    secTip: "Go to this section", cueTip: "Go to this cue",
    noConcert: "No show open: single song. For a setlist, build a concert (ReaCue window, Concert tab) and open it.",
    noData: "No song published: open a project prepared by ReaCue (or a concert) in REAPER.",
    noWebC: "REAPER does not answer: check the web interface (Preferences > Control/OSC/web).",
    lightH: (s) => `LIGHTING · GRANDMA3 · TC SLOT ${s}`, lightH0: "LIGHTING · GRANDMA3",
    ltcOut: (o, f) => `LTC OUTPUT ${o} · ${f}`, ltcNone: f => `NO LTC OUTPUT · ${f}`, fps: f => `${f} fps`,
    colCue: "CUE", colTc: "TIMECODE", colSec: "SECTION", colFx: "EFFECT", colType: "TYPE",
    pLtc: o => `REAPER → LTC ${o}`, pLtcOff: "LTC: NO OUTPUT", pMtc: m => `MTC → ${m}`, pMtcOff: "MTC: NONE",
    pExpOk: "EXPORT UP TO DATE", pExpOld: "EXPORT OUTDATED", pExpNone: "NO EXPORT",
    pLtcTip: "LTC timecode sent by REAPER (TIMECODE LTC track) on the audio output set in the Lighting tab.",
    pMtcTip: "MIDI Timecode sent by REAPER (TIMECODE MTC track) to this MIDI device.",
    pExpTip: "Do the exported cues match the project's current sections? If not: Lighting tab of the ReaCue window, “Export now”.",
    test: "TEST 10 S", testOn: n => `STOP · ${n} S`,
    testTip: "Sends 10 s of timecode: only the TIMECODE tracks play (the audience hears nothing), then everything is restored. Check on the console that the TC Slot turns green.",
    testBad: "Test not possible: create the TIMECODE tracks (Lighting tab of the ReaCue window), leave rehearsal, stop recording.",
    noLight: "No lighting export for this project: turn on the grandMA3 export in the Lighting tab of the ReaCue window (or in Settings), then prepare / republish the song.",
    noCues: "No cue for this song.",
    lmTitle: "LIGHTING · GRANDMA3", lmNow: "CURRENT CUE", lmCues: "CUES", lmFxRo: "SUGGESTED EFFECTS · READ ONLY",
    lmOut: "TIMECODE OUTPUTS", lmFiles: "GRANDMA3 FILES",
    lmMeta: (name, n, fps, tc) => [name, `${n} CUES`, fps, `START ${tc}`].filter(Boolean).join(" · "),
    kLtc: "LTC", kMtc: "MTC", kSlot: "TC SLOT", kFps: "FPS", kStart: "START", none: "none", noneM: "none",
    lmOneway: "LTC / MTC goes one way only: ReaCue cannot know whether the console receives it. During the test, check that the TC Slot turns green and the time runs. Output settings: Lighting tab of the ReaCue window.",
    lmUsb: "In the grandMA3 folder next to the project: the same, ready for a USB stick (gma3_library/…, with the “ReaCue” plugin that imports everything and sets the TC Slot).",
    fSeq: "SEQUENCE", fTc: "TIMECODE", fCsv: "CUE SHEET", noFiles: "No file (export turned off or not done yet).",
    nowNone: "—", beforeFirst: "Before the first cue",
  });
  const T = RC.t;
  const toast = (m, bad) => (RC.toast ? RC.toast(m, bad) : null);

  // ------------------------------------------------------------------ données
  const isConcert = d => !!(d && d.concert && Array.isArray(d.songs) && d.songs.length);
  const songsOf = d => (isConcert(d) ? d.songs : (d && d.bar_times ? [d] : []));
  const bt = s => s.bar_times || [];
  const startOf = s => (s.start_t != null ? s.start_t : (bt(s)[0] || 0));
  const stopOf = s => (s.stop_t != null ? s.stop_t : (bt(s)[bt(s).length - 1] || 0));
  const lightOf = d => (d && d.lighting && Array.isArray(d.lighting.cues) ? d.lighting : null);
  function songIndex(songs, t) {
    let i = 0;
    songs.forEach((s, k) => { if (startOf(s) <= t + 0.05) i = k; });
    return i;
  }
  // m:ss (h:mm:ss au-delà d'une heure)
  function mmss(sec) {
    sec = Math.max(0, Math.floor(sec + 1e-6));
    const h = Math.floor(sec / 3600), m = Math.floor(sec / 60) % 60, s = sec % 60;
    return (h ? h + ":" + String(m).padStart(2, "0") : String(m)) + ":" + String(s).padStart(2, "0");
  }
  const fpsTxt = f => T("fps", (Math.abs(f - Math.round(f)) < 0.001 ? String(Math.round(f)) :
    (RC.LANG === "fr" ? String(f).replace(".", ",") : String(f))));
  // cues du bloc lighting pour le morceau k (concert : piste k ; morceau seul : tous)
  const cuesFor = (lg, d, k) => (lg ? lg.cues.filter(q => !isConcert(d) || q.track === k) : []);
  const fx = q => (q.effect && (q.effect[RC.LANG] || q.effect.fr)) || "";
  const typeLabel = q => (q.type_label && (q.type_label[RC.LANG] || q.type_label.fr)) || q.type || "";
  // cue en cours : le dernier dont le temps est passé (même règle que la fenêtre ReaCue)
  function currentCue(lg, t) {
    if (!lg) return -1;
    let k = -1;
    lg.cues.forEach((q, i) => { if (q.t <= t + 1e-3) k = i; });
    return k;
  }
  // l'export correspond-il aux sections publiées ? (un cue par section, au début de la région)
  function exportState(d, lg) {
    if (!lg) return "none";
    const songs = songsOf(d);
    let ok = true;
    songs.forEach((s, k) => {
      const cs = cuesFor(lg, d, k), secs = (s.sections || []).slice().sort((a, b) => a.start_bar - b.start_bar);
      if (cs.length !== secs.length) { ok = false; return; }
      secs.forEach((x, i) => { if (Math.abs(RC.barT(s, x.start_bar) - cs[i].t) > 0.02) ok = false; });
    });
    return ok ? "ok" : "old";
  }

  // ------------------------------------------------------------------ commandes
  // commande ReaCue (fenêtre ouverte, PIN) ; sinon repli sur l'API web native quand il y en a un
  function remote(cmd, arg, fallback) {
    if (RC.windowOk()) { RC.cmd(cmd, arg); return; }
    if (fallback) { fallback(); return; }
    toast(T("needWin"), true);
  }
  const playing = () => !!RC.state.play;
  // double appui pendant la lecture (comme la fenêtre ReaCue) : le 1er arme le bouton 2 s
  let armed = null;
  function confirmTap(key) {
    if (!playing()) { armed = null; return true; }
    if (armed && armed.key === key && performance.now() - armed.at < 2000) { armed = null; return true; }
    armed = { key, at: performance.now() };
    return false;
  }
  const isArmed = key => armed && armed.key === key && performance.now() - armed.at < 2000;
  const seekTo = t => remote("seek", t.toFixed(3), () => RC.seek(t));

  const prevAck = RC.onAck;
  RC.onAck = (cmd, res) => {
    if (cmd === "tctest" && res === "bad") { toast(T("testBad"), true); return; }
    if (prevAck) prevAck(cmd, res);
  };

  // ------------------------------------------------------------------ écran CONCERT
  let setKey = "", secKey = "", cueKey = "";
  function buildSetlist(d, songs) {
    const key = (d ? d.id : "") + RC.LANG;
    if (key === setKey) return;
    setKey = key;
    const box = $("csSetlist");
    box.innerHTML = songs.map((s, k) => {
      const dur = Math.max(1, stopOf(s) - startOf(s));
      const meta = [isConcert(d) ? String(s.n || k + 1) : "", mmss(dur), s.bpm ? Math.round(s.bpm) + " BPM" : ""].filter(Boolean).join(" · ");
      return `<button class="cs-song" data-k="${k}" style="flex:${dur.toFixed(1)} 1 0" title="${esc(s.title)} — ${esc(T("songTip"))}">` +
        `<span class="t">${esc(s.title || "—")}</span><span class="m" data-meta="${esc(meta)}">${esc(meta)}</span></button>`;
    }).join("");
  }
  $("csSetlist").addEventListener("click", e => {
    const b = e.target.closest(".cs-song"); if (!b) return;
    const d = RC.data, songs = songsOf(d), k = +b.dataset.k;
    if (!songs[k]) return;
    if (!confirmTap("song" + k)) return;
    if (isConcert(d)) remote("song", k + 1, () => RC.seek(startOf(songs[k])));
    else seekTo(startOf(songs[k]));
  });

  function buildSections(s, k) {
    const key = (RC.data ? RC.data.id : "") + ":" + k + RC.LANG;
    if (key === secKey) return;
    secKey = key;
    $("csSecH").textContent = T("secH", String(s.title || "").toUpperCase());
    $("csSecs").innerHTML = (s.sections || []).map((x, i) =>
      `<div class="cs-sec" data-i="${i}" title="${esc(x.name)} · ${x.start_bar}–${x.end_bar} — ${esc(T("secTip"))}">` +
      `<span class="e" style="background:${esc(x.color || "#4A5361")}"></span><span class="b">${String(x.start_bar).padStart(3, "0")}</span>` +
      `<span class="n">${esc(x.name)}</span><span class="s"></span></div>`).join("");
  }
  $("csSecs").addEventListener("click", e => {
    const r = e.target.closest(".cs-sec"); if (!r) return;
    const songs = songsOf(RC.data), s = songs[songIndex(songs, RC.pos())];
    const x = s && s.sections[+r.dataset.i];
    if (x) seekTo(RC.barT(s, x.start_bar));
  });

  // morceau seul : sections précédente / suivante
  function sectionJump(dir) {
    const songs = songsOf(RC.data); if (!songs.length) return;
    const s = songs[songIndex(songs, RC.pos())], t = RC.pos();
    const starts = (s.sections || []).map(x => RC.barT(s, x.start_bar));
    if (dir > 0) { const nx = starts.find(x => x > t + 0.05); if (nx != null) seekTo(nx); return; }
    const before = starts.filter(x => x < t - 2.0);
    seekTo(before.length ? before[before.length - 1] : startOf(s));
  }
  function songJump(dir) {
    const songs = songsOf(RC.data), t = RC.pos(), i = songIndex(songs, t);
    let k = dir > 0 ? i + 1 : (t > startOf(songs[i]) + 2 ? i : i - 1);
    k = RC.clamp(k, 0, songs.length - 1);
    RC.seek(startOf(songs[k]));
  }
  $("csPrev").onclick = () => {
    if (!RC.data || !confirmTap("prev")) return;
    if (isConcert(RC.data)) remote("prev", "", () => songJump(-1)); else sectionJump(-1);
  };
  $("csNext").onclick = () => {
    if (!RC.data || !confirmTap("next")) return;
    if (isConcert(RC.data)) remote("next", "", () => songJump(1)); else sectionJump(1);
  };
  $("csPlay").onclick = () => remote("toggle", "", () => RC.send("" + (RC.state.play ? RC.ACT.pause : RC.ACT.play)));
  document.addEventListener("keydown", e => {
    if (RC.mode !== "concert" || e.code !== "Space" || /INPUT|SELECT|TEXTAREA|BUTTON/.test(e.target.tagName || "")) return;
    e.preventDefault(); e.stopImmediatePropagation(); $("csPlay").onclick();
  }, true);

  function buildCues(box, d, lg, list, full) {
    const key = (d ? d.id : "") + RC.LANG + ":" + list.length + ":" + (list[0] ? list[0].track + "/" + list[0].n : "") + (full ? "F" : "");
    if (box.dataset.key === key) return;
    box.dataset.key = key;
    if (!lg) { box.innerHTML = `<div class="cs-empty">${esc(T("noLight"))}</div>`; return; }
    if (!list.length) { box.innerHTML = `<div class="cs-empty">${esc(T("noCues"))}</div>`; return; }
    let html = "", prev = null;
    list.forEach(q => {
      if (full && isConcert(d) && q.track !== prev) {
        prev = q.track;
        html += `<div class="cs-song-h" data-track="${q.track}">${esc(q.track + 1)} · ${esc(q.song || "")}</div>`;
      }
      const i = lg.cues.indexOf(q);
      html += `<div class="cs-cue${full ? " wide" : ""}" data-i="${i}" title="${esc(T("cueTip"))}">` +
        `<span class="n">${esc(q.n)}</span><span class="tc">${esc(q.tc)}</span><span class="nm">${esc(q.name)}</span>` +
        (full ? `<span class="ty">${esc(typeLabel(q))}</span>` : "") + `<span class="fx">${esc(fx(q))}</span></div>`;
    });
    box.innerHTML = html;
  }
  function cueClick(e) {
    const r = e.target.closest(".cs-cue[data-i]"); if (!r) return;
    const lg = lightOf(RC.data), q = lg && lg.cues[+r.dataset.i];
    if (q) seekTo(q.t);
  }
  $("csCues").addEventListener("click", cueClick);
  $("lmList").addEventListener("click", cueClick);

  function pill(id, cls, txt, tip) {
    const el = $(id);
    el.className = "cs-pill " + cls; el.textContent = txt; el.title = tip || "";
  }
  function timecodePills(prefix, lg, d) {
    const tc = (lg && lg.timecode) || {};
    pill(prefix + "Ltc", tc.ltc ? (playing() ? "ok" : "ok") : "off", tc.ltc ? T("pLtc", tc.ltc) : T("pLtcOff"), T("pLtcTip"));
    pill(prefix + "Mtc", tc.mtc ? "ok" : "off", tc.mtc ? T("pMtc", String(tc.mtc).toUpperCase()) : T("pMtcOff"), T("pMtcTip"));
    const ex = exportState(d, lg);
    pill(prefix + "Exp", ex === "ok" ? "ok" : (ex === "old" ? "warn" : "off"), T(ex === "ok" ? "pExpOk" : ex === "old" ? "pExpOld" : "pExpNone"), T("pExpTip"));
  }
  function testButton(id) {
    const b = $(id), left = RC.state.ext.tctest;
    const on = left != null && left !== "";
    b.classList.toggle("on", on);
    b.classList.toggle("armed", isArmed("test"));
    b.textContent = on ? T("testOn", left) : (isArmed("test") ? T("again") : T("test"));
    b.title = T("testTip");
  }
  function doTest() {
    const left = RC.state.ext.tctest;
    if (left != null && left !== "") { remote("tctest", ""); return; }
    if (!confirmTap("test")) return;
    remote("tctest", "");
  }
  $("csTest").onclick = doTest;
  $("lmTest").onclick = doTest;

  function stateOf() {
    const ps = RC.state.ps;
    if (!RC.webOk()) return ["", "sStop"];
    if (ps === 1) return ["play", "sPlay"];
    if (ps === 5) return ["play", "sRec"];
    if (ps === 2 || ps === 6) return ["pause", "sPause"];
    return ["", "sStop"];
  }

  function msg(id, txt) { const el = $(id); el.hidden = !txt; el.textContent = txt || ""; }

  function frameConcert(t) {
    const d = RC.data, songs = songsOf(d), lg = lightOf(d);
    const [scls, skey] = stateOf();
    $("csState").className = "cs-state " + scls;
    $("csStateTxt").textContent = T(skey);
    if (!songs.length) {
      $("csTitle").textContent = "—"; $("csRank").textContent = "";
      msg("csMsg", RC.webOk() || RC.state.lastOk < 0 ? T("noData") : T("noWebC"));
      $("csSetlist").innerHTML = ""; setKey = ""; $("csSecs").innerHTML = ""; secKey = "";
      buildCues($("csCues"), d, lg, [], false);
      return;
    }
    const conc = isConcert(d), k = songIndex(songs, t), s = songs[k];
    msg("csMsg", conc ? "" : T("noConcert"));
    $("csRank").textContent = conc ? T("rank", s.n || k + 1, songs.length) : T("single");
    if ($("csTitle").textContent !== s.title) $("csTitle").textContent = s.title || "—";
    $("csRest").textContent = mmss(stopOf(s) - Math.max(t, startOf(s)));
    $("csElK").textContent = T(conc ? "cConcert" : "cSong");
    $("csEl").textContent = mmss(Math.max(0, t - startOf(conc ? songs[0] : s)));
    const tc = (lg && lg.timecode) || {};
    $("csTcK").textContent = tc.ltc ? "SMPTE · LTC" : "SMPTE";
    $("csTc").textContent = RC.smpte((lg ? lg.offset_s || 0 : 0) + Math.max(0, t), lg ? lg.fps : 25);
    // setlist
    buildSetlist(d, songs);
    $("csSetlist").querySelectorAll(".cs-song").forEach(b => {
      const j = +b.dataset.k;
      b.classList.toggle("done", j < k); b.classList.toggle("now", j === k);
      b.classList.toggle("armed", isArmed("song" + j));
      const m = b.querySelector(".m"), want = isArmed("song" + j) ? T("again") : m.dataset.meta;
      if (m.textContent !== want) m.textContent = want;
    });
    // sections
    buildSections(s, k);
    const L = RC.locate(s, t);
    $("csSecs").querySelectorAll(".cs-sec").forEach(r => {
      const x = s.sections[+r.dataset.i];
      let st = "up";
      if (L.end || (!L.pre && L.bar > x.end_bar)) st = "done";
      else if (!L.pre && L.bar >= x.start_bar) st = "now";
      r.classList.toggle("done", st === "done"); r.classList.toggle("now", st === "now");
      const txt = st === "done" ? T("played") : st === "now" ? T("nowIn", L.bar - x.start_bar + 1, x.end_bar - x.start_bar + 1) :
        (L.pre && x === s.sections[0] && t >= startOf(s) ? T("countIn") : T("upcoming"));
      const sp = r.querySelector(".s");
      if (sp.textContent !== txt) sp.textContent = txt;
    });
    // transport
    $("csPrevL").textContent = isArmed("prev") ? T("again") : T("prev");
    $("csNextL").textContent = isArmed("next") ? T("again") : T("next");
    $("csPrev").classList.toggle("armed", isArmed("prev")); $("csNext").classList.toggle("armed", isArmed("next"));
    $("csPlayL").textContent = RC.state.play ? T("pause") : T("play");
    $("csPlay").classList.toggle("paused", RC.state.ps === 2);
    // lumière (cues du morceau en cours)
    $("csLightH").textContent = lg ? T("lightH", (lg.timecode && lg.timecode.slot) || 1) : T("lightH0");
    const out = $("csOut");
    out.textContent = lg ? (tc.ltc ? T("ltcOut", tc.ltc, fpsTxt(lg.fps)) : T("ltcNone", fpsTxt(lg.fps))) : "";
    out.className = "cs-out" + (tc.ltc ? " ok" : "");
    const list = cuesFor(lg, d, k);
    buildCues($("csCues"), d, lg, list, false);
    paintCues($("csCues"), lg, t);
    timecodePills("cs", lg, d);
    testButton("csTest");
  }

  function paintCues(box, lg, t) {
    if (!lg) return;
    const cur = currentCue(lg, t);
    let nowEl = null;
    box.querySelectorAll(".cs-cue[data-i]").forEach(r => {
      const i = +r.dataset.i;
      r.classList.toggle("done", i < cur); r.classList.toggle("now", i === cur);
      if (i === cur) nowEl = r;
    });
    // suit le cue en cours pendant la lecture
    if (nowEl && playing() && box.dataset.now !== String(cur)) {
      box.dataset.now = String(cur);
      const p = box.closest(".cs-cues, .lm-list") || box;
      const top = nowEl.offsetTop - p.offsetTop;
      if (top < p.scrollTop || top + nowEl.offsetHeight > p.scrollTop + p.clientHeight) p.scrollTop = Math.max(0, top - 80);
    }
  }

  // ------------------------------------------------------------------ écran LUMIÈRE
  let filesKey = "";
  function frameLight(t) {
    const d = RC.data, lg = lightOf(d);
    const songs = songsOf(d);
    msg("lmMsg", !d ? (RC.webOk() || RC.state.lastOk < 0 ? T("noData") : T("noWebC")) : (!lg ? T("noLight") : ""));
    const name = d ? (isConcert(d) ? d.concert.name : d.title) : "";
    $("lmMeta").textContent = lg ? T("lmMeta", String(name || "").toUpperCase(), lg.cues.length, fpsTxt(lg.fps).toUpperCase(), lg.tc_start || "00:00:00:00") : "";
    buildCues($("lmList"), d, lg, lg ? lg.cues : [], true);
    paintCues($("lmList"), lg, t);
    if (lg && songs.length) {
      const k = songIndex(songs, t);
      $("lmList").querySelectorAll(".cs-song-h").forEach(h => h.classList.toggle("now", +h.dataset.track === k));
    }
    // cue en cours
    const cur = currentCue(lg, t), q = lg && lg.cues[cur];
    $("lmNowN").textContent = q ? String(q.n) : T("nowNone");
    $("lmNowTc").textContent = q ? q.tc : "";
    $("lmNowName").textContent = q ? (isConcert(d) ? `${q.song} · ${q.name}` : q.name) : (lg && lg.cues.length ? T("beforeFirst") : "");
    $("lmNowFx").textContent = q ? fx(q) : "";
    // sorties timecode (réglages au moment de l'export)
    const tc = (lg && lg.timecode) || {};
    const kv = lg ? [["kLtc", tc.ltc || T("none")], ["kMtc", tc.mtc || T("noneM")], ["kSlot", String(tc.slot || 1)],
      ["kFps", fpsTxt(lg.fps)], ["kStart", lg.tc_start || "00:00:00:00", "tc"]] : [];
    const kvh = kv.map(([k, v, c]) => `<span class="k">${esc(T(k))}</span><span class="v${c ? " " + c : ""}" title="${esc(v)}">${esc(v)}</span>`).join("");
    if ($("lmKv").innerHTML !== kvh) $("lmKv").innerHTML = kvh;
    timecodePills("lm", lg, d);
    testButton("lmTest");
    // fichiers à télécharger
    const fk = (d ? d.id : "") + RC.LANG;
    if (fk !== filesKey) {
      filesKey = fk;
      const files = (lg && lg.files) || [];
      $("lmFiles").innerHTML = files.length ? files.map(f => {
        const kind = f.kind === "sequence" ? T("fSeq") : f.kind === "timecode" ? T("fTc") : T("fCsv");
        return `<a href="${esc(f.url)}" download="${esc(f.name)}"><span><span class="k">${esc(kind)}</span>${esc(f.name)}</span>` +
          `<small>${esc(f.song || "")}</small></a>`;
      }).join("") : `<span class="rc-note">${esc(T("noFiles"))}</span>`;
    }
  }

  // ------------------------------------------------------------------ boucle
  function frame() {
    requestAnimationFrame(frame);
    if (RC.mode === "travail") return;
    if (armed && performance.now() - armed.at > 2000) armed = null;
    const t = RC.pos();
    if (RC.mode === "concert") frameConcert(t); else frameLight(t);
  }
  RC.onLang.push(() => { setKey = ""; secKey = ""; filesKey = ""; $("csCues").dataset.key = ""; $("lmList").dataset.key = ""; });
  RC.onData.push(() => { setKey = ""; secKey = ""; filesKey = ""; });
  RC.setLang(RC.LANG, false);
  RC.setMode(RC.startMode());
  requestAnimationFrame(frame);
})();

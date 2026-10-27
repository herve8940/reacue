/* ReaCue Studio — écran GROUPE (répétition).
   - Notes par section du morceau en cours (concert : celui sous la tête de lecture) : commande « note »
     (fenêtre ReaCue, PIN) -> état durable de ReaCue (ReaCueMCP/reacue_state.json) -> republiées dans le champ
     « notes » de reacue_song.json : cadre rose sur tous les prompteurs.
   - « On reprend à… » : commande « resume » (lecture une mesure avant la section ; boucle arrêtée).
   - Musiciens connectés et « Prêt » : ExtState ReaCue/band (RC.band), publié par la fenêtre à partir des
     battements des prompteurs (toutes les ~2 s, oubliés après 10 s) ; remise à zéro : commande « readyreset ». */
(function () {
  "use strict";
  const { $, esc } = RC;

  Object.assign(RC.STR.fr, {
    grReadyK: "PRÊTS", grNotesH: "NOTES PAR SECTION", grNotesHint: "VISIBLES SUR TOUS LES PROMPTEURS",
    grResumeH: "ON REPREND À…", grResumeHint: "1 MESURE AVANT", grStop: "■ STOP", grReset: "REMISE À ZÉRO",
    grBandH: n => `MUSICIENS CONNECTÉS · ${n}`, grPlay: "LECTURE", grPause: "PAUSE",
    grBandHelp: "Chaque téléphone (prompteur) apparaît ici tant qu'il est ouvert (oublié après 10 s sans signe). Les musiciens appuient sur « PRÊT » en haut du prompteur ; « Remise à zéro » efface tous les « Prêt ».",
    grMeta: (n, i, b) => [n, i, b].filter(Boolean).join(" · "), grSongOf: (i, n) => `MORCEAU ${i} / ${n}`,
    grPh: "Note courte pour cette section (ex. « on coupe sur le 4 »)",
    grSaved: "ENREGISTRÉ", grSaving: "ENVOI…", grEdited: "NON ENREGISTRÉ", grFail: "REFUSÉ", grEmpty: "",
    grNoBand: "Aucun prompteur connecté : ouvre prompteur.html sur les téléphones (QR code de la fenêtre ReaCue).",
    grNoWin: "Ouvre la fenêtre « ReaCue » dans REAPER : elle compte les prompteurs connectés et enregistre les notes.",
    grReady: "PRÊT", grWait: "PAS PRÊT", grRegie: "—", grSeen: s => `${s} s`,
    grResumeTip: "Reprendre ici : la lecture repart une mesure avant", grResetTip: "Efface tous les « Prêt » (chaque musicien rappuie quand il est prêt)",
    grNoSong: "Aucun morceau publié : ouvre un morceau préparé (écran BIBLIO ou REAPER).",
    roleN: { drums: "Batterie", bass: "Basse", guitars: "Guitare rythm.", lead_guitar: "Guitare solo", vocals: "Chant", keys: "Claviers",
      all: "Vue générale", regie: "Régie", light: "Lumière", "": "Sans rôle" },
  });
  Object.assign(RC.STR.en, {
    grReadyK: "READY", grNotesH: "NOTES PER SECTION", grNotesHint: "SHOWN ON EVERY PROMPTER",
    grResumeH: "TAKE IT FROM…", grResumeHint: "1 BAR BEFORE", grStop: "■ STOP", grReset: "RESET",
    grBandH: n => `MUSICIANS CONNECTED · ${n}`, grPlay: "PLAY", grPause: "PAUSE",
    grBandHelp: "Each phone (prompter) shows here while it is open (forgotten after 10 s without a sign). Musicians tap “READY” at the top of the prompter; “Reset” clears every “Ready”.",
    grMeta: (n, i, b) => [n, i, b].filter(Boolean).join(" · "), grSongOf: (i, n) => `SONG ${i} / ${n}`,
    grPh: "Short note for this section (e.g. “stop on 4”)",
    grSaved: "SAVED", grSaving: "SENDING…", grEdited: "NOT SAVED", grFail: "REFUSED", grEmpty: "",
    grNoBand: "No prompter connected: open prompteur.html on the phones (QR code of the ReaCue window).",
    grNoWin: "Open the “ReaCue” window in REAPER: it counts the connected prompters and saves the notes.",
    grReady: "READY", grWait: "NOT READY", grRegie: "—", grSeen: s => `${s} s`,
    grResumeTip: "Take it from here: playback restarts one bar before", grResetTip: "Clears every “Ready” (each musician taps again when ready)",
    grNoSong: "No song published: open a prepared song (LIBRARY screen or REAPER).",
    roleN: { drums: "Drums", bass: "Bass", guitars: "Rhythm gtr", lead_guitar: "Lead gtr", vocals: "Vocals", keys: "Keys",
      all: "Overview", regie: "Stage control", light: "Lighting", "": "No role" },
  });
  const T = RC.t;
  const toast = (m, bad) => (RC.toast ? RC.toast(m, bad) : null);
  const ROLE_ORDER = ["vocals", "drums", "bass", "guitars", "lead_guitar", "keys", "all", "regie", "light"];
  RC.roleName = r => { const m = T("roleN"); return (m && m[r]) || r || m[""]; };

  const songsOf = d => (d && d.concert && Array.isArray(d.songs) ? d.songs : (d && d.bar_times ? [d] : []));
  function current() {
    const songs = songsOf(RC.data); if (!songs.length) return null;
    let k = 0;
    songs.forEach((s, i) => { if ((s.start_t != null ? s.start_t : s.bar_times[0]) <= RC.pos() + 0.05) k = i; });
    return { song: songs[k], k, n: songs.length, concert: !!(RC.data && RC.data.concert) };
  }
  // notes envoyées et pas encore republiées : { "<id morceau>:<mesure>": {text, state} }
  const sent = {};
  let notesKey = "", resumeKey = "";

  function buildNotes(cur) {
    const s = cur.song, key = (RC.data ? RC.data.id : "") + ":" + cur.k + RC.LANG;
    if (key === notesKey) return;
    if (document.activeElement && $("grNotes").contains(document.activeElement)) return;   // saisie en cours
    notesKey = key;
    $("grNotes").innerHTML = (s.sections || []).map((x, i) => {
      const id = (s.id || "") + ":" + x.start_bar, pend = sent[id];
      const v = pend ? pend.text : (x.notes || "");
      return `<div class="gr-note" data-i="${i}"><span class="e" style="background:${esc(x.color || "#4A5361")}"></span>` +
        `<span class="b">${String(x.start_bar).padStart(3, "0")}</span><span class="n" title="${esc(x.name)}">${esc(x.name)}</span>` +
        `<input type="text" maxlength="200" value="${esc(v)}" placeholder="${esc(T("grPh"))}" aria-label="${esc(x.name)}" class="${v ? "has" : ""}">` +
        `<span class="st"></span></div>`;
    }).join("");
  }
  function buildResume(cur) {
    const s = cur.song, key = (RC.data ? RC.data.id : "") + ":" + cur.k + RC.LANG;
    if (key === resumeKey) return;
    resumeKey = key;
    $("grResume").innerHTML = (s.sections || []).map((x, i) =>
      `<button class="gr-sec" data-i="${i}" style="border-top-color:${esc(x.color || "#4A5361")}" title="${esc(T("grResumeTip"))}">` +
      `<span class="n">${esc(x.name)}</span><span class="b">${String(x.start_bar).padStart(3, "0")} · ${x.end_bar - x.start_bar + 1}</span></button>`).join("");
  }

  function saveNote(row) {
    const cur = current(); if (!cur) return;
    const x = cur.song.sections[+row.dataset.i], inp = row.querySelector("input");
    const text = inp.value.replace(/\s+/g, " ").trim();
    if (text === (x.notes || "").trim() && !sent[(cur.song.id || "") + ":" + x.start_bar]) { row.querySelector(".st").textContent = ""; return; }
    if (!RC.windowOk()) { toast(T("grNoWin"), true); return; }
    const id = (cur.song.id || "") + ":" + x.start_bar;
    if (sent[id] && sent[id].text === text && sent[id].state !== "bad") return;      // déjà envoyée (Entrée puis sortie)
    sent[id] = { text, state: "busy", bar: x.start_bar };
    inp.classList.toggle("has", !!text);
    RC.cmd("note", `${cur.k + 1}:${x.start_bar}:${encodeURIComponent(text)}`, res => {
      if (sent[id]) { sent[id].state = res === "ok" ? "ok" : "bad"; sent[id].until = performance.now() + 4000; }
      if (res === "ok") x.notes = text;           // affiché tout de suite ; la publication suit (2–3 s)
    });
  }
  $("grNotes").addEventListener("keydown", e => {
    if (e.target.tagName !== "INPUT") return;
    if (e.key === "Enter") { e.preventDefault(); saveNote(e.target.closest(".gr-note")); e.target.blur(); }
    else if (e.key === "Escape") { const cur = current(); const row = e.target.closest(".gr-note");
      if (cur) e.target.value = cur.song.sections[+row.dataset.i].notes || ""; e.target.blur(); }
  });
  $("grNotes").addEventListener("input", e => {
    const row = e.target.closest(".gr-note"); if (!row) return;
    const st = row.querySelector(".st"); st.className = "st"; st.textContent = T("grEdited");
  });
  $("grNotes").addEventListener("focusout", e => { if (e.target.tagName === "INPUT") saveNote(e.target.closest(".gr-note")); });

  $("grResume").addEventListener("click", e => {
    const b = e.target.closest(".gr-sec"); if (!b) return;
    const cur = current(); if (!cur) return;
    const x = cur.song.sections[+b.dataset.i];
    if (!RC.windowOk()) { toast(T("needWin"), true); return; }
    RC.cmd("resume", RC.barT(cur.song, x.start_bar).toFixed(3));
  });
  $("grStop").onclick = () => RC.send("" + RC.ACT.stop);
  $("grPlay").onclick = () => RC.send("" + (RC.state.play ? RC.ACT.pause : RC.ACT.play));
  $("grReset").onclick = () => { if (!RC.windowOk()) { toast(T("needWin"), true); return; } RC.cmd("readyreset", ""); };
  $("grReset").title = T("grResetTip");

  let bandKey = "";
  function renderBand(win) {
    const list = win ? RC.band.list.slice().sort((a, b) =>
      (ROLE_ORDER.indexOf(a.role) - ROLE_ORDER.indexOf(b.role)) || a.name.localeCompare(b.name)) : [];
    const mus = list.filter(x => RC.isMusician(x.role)), ready = mus.filter(x => x.ready).length;
    $("grReadyN").textContent = String(ready);
    $("grReadyOf").textContent = "/ " + mus.length;
    $("grReady").classList.toggle("wait", ready < mus.length || !mus.length);
    $("grBandH").textContent = T("grBandH", list.length);
    const key = RC.LANG + JSON.stringify(list.map(x => [x.id, x.role, x.name, x.ready, Math.min(3, x.age)])) + win;
    if (key === bandKey) return;
    bandKey = key;
    if (!win) { $("grBand").innerHTML = `<div class="cs-empty">${esc(T("grNoWin"))}</div>`; return; }
    if (!list.length) { $("grBand").innerHTML = `<div class="cs-empty">${esc(T("grNoBand"))}</div>`; return; }
    $("grBand").innerHTML = list.map(x => {
      const m = RC.isMusician(x.role);
      const st = !m ? `<span class="s na">${esc(T("grRegie"))}</span>` : x.ready ? `<span class="s ok">${esc(T("grReady"))}</span>` :
        `<span class="s wait">${esc(T("grWait"))}</span>`;
      return `<div class="gr-mus" title="${esc(T("grSeen", x.age))}"><i style="--c:${RC.roleColor(x.role === "lead_guitar" ? "lead_guitar" : x.role)}"></i>` +
        `<span class="r">${esc(RC.roleName(x.role))}</span><span class="nm">${esc(x.name || "")}</span>${st}</div>`;
    }).join("");
  }

  function frame() {
    requestAnimationFrame(frame);
    if (RC.mode !== "groupe") return;
    const win = RC.windowOk(), cur = current();
    renderBand(win);
    const msg = $("grMsg");
    if (!cur) {
      msg.hidden = false; msg.textContent = T("grNoSong");
      $("grTitle").textContent = "—"; $("grMeta").textContent = "";
      $("grNotes").innerHTML = ""; $("grResume").innerHTML = ""; notesKey = ""; resumeKey = "";
      return;
    }
    msg.hidden = win; if (!win) msg.textContent = T("grNoWin");
    const s = cur.song;
    if ($("grTitle").textContent !== s.title) $("grTitle").textContent = s.title || "—";
    $("grMeta").textContent = T("grMeta", cur.concert ? T("grSongOf", cur.k + 1, cur.n) : "",
      s.bpm ? Math.round(s.bpm) + " BPM" : "", s.key ? s.key.chord : "");
    buildNotes(cur); buildResume(cur);
    const L = RC.locate(s, RC.pos());
    const si = (s.sections || []).findIndex(x => !L.pre && !L.end && L.bar >= x.start_bar && L.bar <= x.end_bar);
    $("grNotes").querySelectorAll(".gr-note").forEach(r => {
      const i = +r.dataset.i, x = s.sections[i];
      r.classList.toggle("now", i === si);
      const id = (s.id || "") + ":" + x.start_bar, p = sent[id], st = r.querySelector(".st");
      if (p) {
        if (p.state === "ok" && performance.now() > p.until) { delete sent[id]; st.className = "st"; st.textContent = ""; return; }
        const want = p.state === "busy" ? "grSaving" : p.state === "bad" ? "grFail" : "grSaved";
        st.className = "st " + (p.state === "busy" ? "busy" : p.state === "bad" ? "bad" : "ok");
        if (st.textContent !== T(want)) st.textContent = T(want);
      }
    });
    $("grResume").querySelectorAll(".gr-sec").forEach(b => b.classList.toggle("now", +b.dataset.i === si));
    $("grPlayL").textContent = RC.state.play ? T("grPause") : T("grPlay");
    $("grPlay").classList.toggle("paused", RC.state.ps === 2);
  }
  RC.onLang.push(() => { notesKey = ""; resumeKey = ""; bandKey = ""; $("grReset").title = T("grResetTip"); });
  RC.onData.push(() => { notesKey = ""; resumeKey = ""; });
  RC.onMode.push(m => { if (m === "groupe") { notesKey = ""; resumeKey = ""; bandKey = ""; } });
  requestAnimationFrame(frame);
})();

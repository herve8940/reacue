/* ReaCue Studio — écran BIBLIO : morceaux connus et concerts.
   Données : reacue_library.json publié par ReaCue (reacue_mcp/library.py) à chaque publication du prompteur,
   construction de concert et ouverture de la fenêtre ReaCue : titre, tempo, tonalité, durée, mini-structure,
   composants (stems, accords, paroles, batterie, lumière), étape du parcours (automatique ou réglée à la main).
   Commandes (fenêtre ReaCue, PIN) : open (ouvrir le .RPP dans REAPER, puis écran Travail), libstage (étape
   manuelle, enregistrée dans l'état durable de ReaCue : ReaCueMCP/reacue_state.json). */
(function () {
  "use strict";
  const { $, esc } = RC;

  Object.assign(RC.STR.fr, {
    bbTitle: "BIBLIOTHÈQUE", bbSearch: "Rechercher un morceau, un dossier, un concert…",
    bbMeta: (n, c, d) => `${n} MORCEAUX · ${c} CONCERTS · ${d}`,
    stNew: "DÉCOUVERT", stSolo: "TRAVAILLÉ SEUL", stBand: "RÉPÉTÉ EN GROUPE", stStage: "PRÊT POUR LA SCÈNE", stAll: "TOUS",
    bbColTitle: "MORCEAU", bbColTempo: "TEMPO", bbColKey: "TON", bbColDur: "DURÉE", bbColStruct: "STRUCTURE",
    bbColComp: "COMPOSANTS", bbColStage: "ÉTAPE", bbConcerts: "CONCERTS",
    cStems: n => n ? `STEMS ${n}` : "STEMS", cChords: "ACCORDS", cLyrics: "PAROLES", cDrums: "BATTERIE", cLight: "LUMIÈRE",
    cStemsTip: n => n ? `${n} instruments séparés` : "Pas de stems (mix seul)", cChordsTip: "Grille d'accords", cLyricsTip: n => n ? `Paroles : ${n} lignes` : "Pas de paroles",
    cDrumsTip: "Batterie transcrite", cLightTip: "Cues lumière grandMA3",
    auto: "AUTO", manual: "MANUEL", backAuto: "auto", notPrepared: "À PRÉPARER", inConcert: c => `CONCERT : ${c}`,
    practiced: (s, b, d) => `SEUL ${s} MIN · GROUPE ${b} MIN · ${d} J.`,
    stageTip: (lab, auto) => `${lab} — clic : régler l'étape à la main (calcul automatique : ${auto})`,
    rowTip: "Ouvrir ce morceau dans REAPER puis aller sur TRAVAIL",
    concertTip: "Ouvrir ce concert dans REAPER (onglet de projet)", notBuilt: "PAS CONSTRUIT",
    cSongs: n => `${n} MORCEAUX`, noLib: "Bibliothèque pas encore publiée : ouvre la fenêtre ReaCue dans REAPER (ou prépare un morceau).",
    noMatch: "Aucun morceau ne correspond.", noConcerts: "Aucun concert.",
    opening: t => `Ouverture de « ${t} » dans REAPER…`, openedNp: t => `« ${t} » ouvert dans REAPER : pas encore préparé (onglet Morceau de la fenêtre ReaCue).`,
    openFail: "Ouverture impossible (fichier introuvable ?).", stageSaved: "Étape enregistrée.",
    rulesTip: r => `Étape automatique : seul ≥ ${r.solo_min} min · groupe ≥ ${r.band_min} min (2 musiciens connectés) · scène : préparé + groupe sur ${r.stage_days} jours.`,
  });
  Object.assign(RC.STR.en, {
    bbTitle: "LIBRARY", bbSearch: "Search a song, a folder, a show…",
    bbMeta: (n, c, d) => `${n} SONGS · ${c} SHOWS · ${d}`,
    stNew: "DISCOVERED", stSolo: "PRACTISED ALONE", stBand: "REHEARSED AS A BAND", stStage: "READY FOR THE STAGE", stAll: "ALL",
    bbColTitle: "SONG", bbColTempo: "TEMPO", bbColKey: "KEY", bbColDur: "LENGTH", bbColStruct: "STRUCTURE",
    bbColComp: "COMPONENTS", bbColStage: "STAGE", bbConcerts: "SHOWS",
    cStems: n => n ? `STEMS ${n}` : "STEMS", cChords: "CHORDS", cLyrics: "LYRICS", cDrums: "DRUMS", cLight: "LIGHTS",
    cStemsTip: n => n ? `${n} separated instruments` : "No stems (mix only)", cChordsTip: "Chord chart", cLyricsTip: n => n ? `Lyrics: ${n} lines` : "No lyrics",
    cDrumsTip: "Drums transcribed", cLightTip: "grandMA3 lighting cues",
    auto: "AUTO", manual: "MANUAL", backAuto: "auto", notPrepared: "TO PREPARE", inConcert: c => `SHOW: ${c}`,
    practiced: (s, b, d) => `ALONE ${s} MIN · BAND ${b} MIN · ${d} D.`,
    stageTip: (lab, auto) => `${lab} — click: set the stage by hand (automatic: ${auto})`,
    rowTip: "Open this song in REAPER, then go to PRACTICE",
    concertTip: "Open this show in REAPER (project tab)", notBuilt: "NOT BUILT",
    cSongs: n => `${n} SONGS`, noLib: "Library not published yet: open the ReaCue window in REAPER (or prepare a song).",
    noMatch: "No song matches.", noConcerts: "No show.",
    opening: t => `Opening “${t}” in REAPER…`, openedNp: t => `“${t}” open in REAPER: not prepared yet (Song tab of the ReaCue window).`,
    openFail: "Could not open (file missing?).", stageSaved: "Stage saved.",
    rulesTip: r => `Automatic stage: alone ≥ ${r.solo_min} min · band ≥ ${r.band_min} min (2 musicians connected) · stage: prepared + band on ${r.stage_days} days.`,
  });
  const T = RC.t;
  const toast = (m, bad) => (RC.toast ? RC.toast(m, bad) : null);
  const STAGES = ["new", "solo", "band", "stage"];
  const SKEY = { new: "stNew", solo: "stSolo", band: "stBand", stage: "stStage" };
  const SCOL = { new: "var(--st-new)", solo: "var(--st-solo)", band: "var(--st-band)", stage: "var(--st-stage)" };
  RC.STAGES = STAGES; RC.stageLabel = s => T(SKEY[s] || "stNew");

  let lib = null, filter = RC.load("reacue_biblio_filter") || "", query = "", key = "";
  const norm = s => String(s || "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
  const mmss = s => { s = Math.max(0, Math.round(s || 0)); return Math.floor(s / 60) + ":" + String(s % 60).padStart(2, "0"); };
  const keyOf = p => String(p || "").replace(/\\/g, "/").toLowerCase();
  RC.songKey = keyOf;

  async function load() {
    try {
      const d = await RC.getJSON("reacue_library.json");
      if (!lib || d.id !== lib.id) { lib = d; RC.library = d; key = ""; }
    } catch (e) { if (!lib) { lib = null; key = ""; } }
  }
  setInterval(() => { if (RC.mode === "biblio") load(); }, 5000);        // lu seulement sur cet écran
  RC.onMode.push(m => { if (m === "biblio") { load(); key = ""; } });

  function counts(list) {
    const c = { new: 0, solo: 0, band: 0, stage: 0 };
    list.forEach(s => { c[s.stage in c ? s.stage : "new"]++; });
    return c;
  }
  function current() {
    const d = RC.data;
    if (!d) return { song: "", concert: "" };
    if (d.concert) return { song: "", concert: d.concert.name || "" };
    return { song: keyOf(d.project), concert: "" };
  }
  function comps(s) {
    const c = s.components || {};
    const one = (on, lab, tip) => `<span class="bb-comp${on ? " on" : ""}" title="${esc(tip)}">${esc(lab)}</span>`;
    return one(c.stems > 0, T("cStems", c.stems || 0), T("cStemsTip", c.stems || 0)) + one(c.chords, T("cChords"), T("cChordsTip")) +
      one(c.lyrics > 0, T("cLyrics"), T("cLyricsTip", c.lyrics || 0)) + one(c.drums, T("cDrums"), T("cDrumsTip")) +
      one(c.lighting, T("cLight"), T("cLightTip"));
  }
  function struct(s) {
    const secs = s.sections || [];
    if (!secs.length) return `<div class="bb-struct none"></div>`;
    return `<div class="bb-struct">` + secs.map(x => `<i style="flex:${Math.max(1, x.bars || 1)};background:${esc(x.color || "#4A5361")}" title="${esc(x.name)} · ${x.bars}"></i>`).join("") + `</div>`;
  }
  function stageCell(s) {
    const k = STAGES.indexOf(s.stage), col = SCOL[s.stage] || SCOL.new;
    const dots = STAGES.map((st, i) => `<button class="bb-dot${i <= k ? " lit" : ""}" data-stage="${st}" style="--st:${col}" ` +
      `title="${esc(T("stageTip", RC.stageLabel(st), RC.stageLabel(s.stage_auto)))}" aria-label="${esc(RC.stageLabel(st))}"></button>`).join("");
    const tag = s.stage_manual ? `<span class="m">${esc(T("manual"))}</span><button data-stage="auto">${esc(T("backAuto"))}</button>` :
      `<span class="m">${esc(T("auto"))}</span>`;
    return `<div class="bb-stage"><div class="bb-dots">${dots}</div><div class="bb-sl" style="--st:${col}">${esc(RC.stageLabel(s.stage))}${tag}</div></div>`;
  }
  function render() {
    const cur = current();
    const k = [lib ? lib.id : "", RC.LANG, filter, query, cur.song, cur.concert].join("|");
    if (k === key) return;
    key = k;
    if (!lib) {
      const m = $("bbMsg"); m.hidden = false; m.textContent = T("noLib");
      $("bbRows").innerHTML = ""; $("bbConcerts").innerHTML = ""; $("bbPath").innerHTML = ""; $("bbFilters").innerHTML = "";
      $("bbMeta").textContent = "";
      return;
    }
    const all = lib.songs || [];
    const dir = String(lib.projects_dir || "").split(/[\\/]/).filter(Boolean).pop() || "";
    $("bbMeta").textContent = T("bbMeta", all.length, (lib.concerts || []).length, dir.toUpperCase());
    const c = counts(all);
    $("bbPath").title = lib.rules ? T("rulesTip", lib.rules) : "";
    $("bbPath").innerHTML = STAGES.map(st => `<button class="bb-step${filter === st ? " on" : ""}" data-f="${st}" style="--st:${SCOL[st]}">` +
      `<span class="k">${esc(RC.stageLabel(st))}</span><span class="v">${c[st]}</span></button>`).join("");
    $("bbFilters").innerHTML = [["", T("stAll"), all.length]].concat(STAGES.map(st => [st, RC.stageLabel(st), c[st]])).map(([f, lab, n]) =>
      `<button class="bb-chip${filter === f ? " on" : ""}" data-f="${f}" style="--st:${f ? SCOL[f] : "var(--ink2)"}">${f ? "<i></i>" : ""}${esc(lab)} <b>${n}</b></button>`).join("");
    const q = norm(query);
    const list = all.filter(s => (!filter || s.stage === filter) &&
      (!q || norm([s.title, s.folder, (s.concerts || []).join(" "), s.key_name ? s.key_name.chord : ""].join(" ")).includes(q)));
    $("bbMsg").hidden = true;
    $("bbRows").innerHTML = list.length ? list.map(s => {
      const i = all.indexOf(s);
      const sub = !s.prepared ? `<span class="sub warn">${esc(T("notPrepared"))} · ${esc(s.folder || "")}</span>` :
        `<span class="sub">${esc(s.concerts && s.concerts.length ? T("inConcert", s.concerts.join(", ")) :
          T("practiced", s.practice ? s.practice.solo_min : 0, s.practice ? s.practice.band_min : 0, s.practice ? s.practice.band_days : 0))}</span>`;
      const kn = s.key_name ? (s.key_name.chord || "") : "—";
      return `<div class="bb-row${cur.song && keyOf(s.path) === cur.song ? " cur" : ""}" data-i="${i}" title="${esc(T("rowTip"))}">` +
        `<div class="bb-t"><span class="tt">${esc(s.title)}</span>${sub}</div>` +
        `<span class="bb-n">${s.bpm ? Math.round(s.bpm) : "—"}</span><span class="bb-n k">${esc(kn)}</span>` +
        `<span class="bb-n d">${s.duration_s ? mmss(s.duration_s) : "—"}</span>${struct(s)}` +
        `<div class="bb-comps">${comps(s)}</div>${stageCell(s)}</div>`;
    }).join("") : `<div class="cs-empty">${esc(T("noMatch"))}</div>`;
    const cs = lib.concerts || [];
    $("bbConcerts").innerHTML = cs.length ? cs.map((x, i) =>
      `<button class="bb-concert${x.built ? "" : " off"}${cur.concert && cur.concert === x.name ? " cur" : ""}" data-c="${i}" title="${esc(T("concertTip"))}">` +
      `<span class="t">${esc(x.name)}</span><span class="m">${esc(T("cSongs", (x.songs || []).length))}${x.built ? "" : " · " + esc(T("notBuilt"))}</span></button>`).join("") :
      `<span class="rc-note" style="padding:6px">${esc(T("noConcerts"))}</span>`;
  }

  function open(path, title, prepared) {
    if (!RC.windowOk()) { toast(T("needWin"), true); return; }
    toast(T("opening", title));
    RC.cmd("open", encodeURIComponent(path), res => {
      if (res !== "ok") { if (res === "bad") toast(T("openFail"), true); return; }
      if (prepared) RC.setMode("travail"); else toast(T("openedNp", title));
    });
  }
  function setStage(s, st) {
    if (!RC.windowOk()) { toast(T("needWin"), true); return; }
    const before = { stage: s.stage, stage_manual: s.stage_manual };
    s.stage_manual = st === "auto" ? null : st;
    s.stage = s.stage_manual || s.stage_auto;
    key = "";
    RC.cmd("libstage", encodeURIComponent(s.key || keyOf(s.path)) + ":" + st, res => {
      if (res === "ok") toast(T("stageSaved"));
      else { Object.assign(s, before); key = ""; }
    });
  }
  $("bbRows").addEventListener("click", e => {
    const row = e.target.closest(".bb-row[data-i]"); if (!row || !lib) return;
    const s = lib.songs[+row.dataset.i]; if (!s) return;
    const st = e.target.closest("[data-stage]");
    if (st) { e.stopPropagation(); setStage(s, st.dataset.stage); return; }
    open(s.path, s.title, s.prepared);
  });
  $("bbConcerts").addEventListener("click", e => {
    const b = e.target.closest(".bb-concert"); if (!b || !lib) return;
    const c = lib.concerts[+b.dataset.c];
    if (c && c.built) open(c.rpp, c.name, true);
  });
  const setFilter = f => { filter = filter === f ? "" : f; RC.store("reacue_biblio_filter", filter || null); key = ""; };
  $("bbPath").addEventListener("click", e => { const b = e.target.closest("[data-f]"); if (b) setFilter(b.dataset.f); });
  $("bbFilters").addEventListener("click", e => { const b = e.target.closest("[data-f]"); if (b) { filter = ""; setFilter(b.dataset.f); } });
  $("bbSearch").addEventListener("input", e => { query = e.target.value; key = ""; });
  RC.onLang.push(() => { $("bbSearch").placeholder = T("bbSearch"); key = ""; });
  RC.onData.push(() => { key = ""; });

  function frame() {
    requestAnimationFrame(frame);
    if (RC.mode === "biblio") render();
  }
  requestAnimationFrame(frame);
})();

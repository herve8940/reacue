-- ReaCue : onglet « Réglages » / “Settings” tab : reacue_settings.json sans éditer le fichier.
-- Écriture atomique, champs inconnus gardés ; s'applique à la prochaine préparation.
-- Vue simple (langue, décompte, annonces, voix, sorties, détection de structure, licences) et
-- « Réglages avancés » (volumes, tempo, séparation, dossiers, PIN, débit du décompte…) ;
-- « Vérifier l'installation » ouvre l'assistant du premier lancement.
return function(ctx)
  local L, U, T, R, SEP = ctx.L, ctx.U, ctx.T, ctx.R, ctx.SEP
  local TXT = {
    fr = {
      general = "Général", cues = "Décompte et annonces", outputs = "Click et voix", other = "Analyse, séparation, dossiers",
      language = "Langue", count_in = "Décompte avant le morceau", cue_lead = "Annonce avant la section",
      bars_n = "%d mes.", count_lang = "Décompte", voice_cues = "Annonces vocales", count_in_voice = "Décompte parlé",
      announce_voice = "Voix des annonces", count_voice = "Voix du décompte", auto = "auto",
      hw = "Sortie click + voix", hw_none = "sortie principale", hw_pair = "sorties %d/%d",
      to_master = "Aussi en façade", click_vol = "Volume du click", voice_vol = "Volume des voix",
      tempo = "Tempo", tempo_auto = "auto", tempo_constant = "fixe", tempo_beatmap = "variable",
      stems = "Séparation de stems", stems6 = "6 stems", stems4_ft = "4 stems HQ (GPU)", stems4 = "4 stems (rapide)",
      structure = "Détection de structure", structure_auto = "auto (SongFormer)", structure_reacue = "ReaCue seul",
      structure_on = "SongFormer installé", structure_off = "SongFormer non installé",
      projects_dir = "Dossier des projets", concert_dir = "Dossier des concerts", default = "par défaut",
      dir_title = "ReaCue - Dossier", dir_field = "Dossier (vide = par défaut) :",
      pin = "Code PIN de la Régie", on = "oui", off = "non",
      note = "Les changements s'appliquent à la prochaine préparation (« Analyser et préparer », « Re-préparer » ou « Reconstruire » le concert).",
      version = "Version installée : %s", saved = "enregistré",
      noncommercial = "Usage non commercial uniquement (MuQ : CC BY-NC 4.0)",
      licences = "Licences", licences_tip = "Composants tiers, licences et avertissements",
      simple = "Réglages simples", advanced = "Réglages avancés", check_install = "Vérifier l'installation",
      count_rate = "Débit du décompte", rate_n = "%d mots/min", announce = "Annonces", install_sf = "Installer",
    },
    en = {
      general = "General", cues = "Count-in and spoken cues", outputs = "Click and voice", other = "Analysis, separation, folders",
      language = "Language", count_in = "Count-in before the song", cue_lead = "Cue before the section",
      bars_n = "%d bars", count_lang = "Count", voice_cues = "Spoken cues", count_in_voice = "Spoken count-in",
      announce_voice = "Cue voice", count_voice = "Count voice", auto = "auto",
      hw = "Click + voice output", hw_none = "main output", hw_pair = "outputs %d/%d",
      to_master = "Also to front of house", click_vol = "Click volume", voice_vol = "Voice volume",
      tempo = "Tempo", tempo_auto = "auto", tempo_constant = "fixed", tempo_beatmap = "variable",
      stems = "Stem separation", stems6 = "6 stems", stems4_ft = "4 stems HQ (GPU)", stems4 = "4 stems (fast)",
      structure = "Structure detection", structure_auto = "auto (SongFormer)", structure_reacue = "ReaCue only",
      structure_on = "SongFormer installed", structure_off = "SongFormer not installed",
      projects_dir = "Projects folder", concert_dir = "Concerts folder", default = "default",
      dir_title = "ReaCue - Folder", dir_field = "Folder (empty = default):",
      pin = "Stage control PIN code", on = "yes", off = "no",
      note = "Changes apply at the next preparation (“Analyse and prepare”, “Prepare again” or “Rebuild” the concert).",
      version = "Installed version: %s", saved = "saved",
      noncommercial = "Non-commercial use only (MuQ: CC BY-NC 4.0)",
      licences = "Licences", licences_tip = "Third-party components, licences and disclaimers",
      simple = "Simple settings", advanced = "Advanced settings", check_install = "Check the installation",
      count_rate = "Count speed", rate_n = "%d words/min", announce = "Spoken cues", install_sf = "Install",
    },
  }
  local function t(k) return ctx.tr(TXT, k) end
  local M = {}
  local DEFAULTS = {
    language = "fr", announce_voice = nil, count_voice = nil, count_lang = "en", count_in_bars = 2, cue_lead_bars = 2,
    voice_cues = true, voice_count_in = true, voice_count_each = true, voice_volume = 0.8, click_volume = 0.5,
    click_to_master = true, click_hw_output = nil, tempo_mode = "auto", stems_model = "htdemucs_6s",
    structure_engine = "auto", projects_dir = nil, concert_dir = nil, count_rate = 240,
    -- lumière grandMA3 (onglet Lumière)
    gma3_export = true, gma3_fps = 25, gma3_tc_start = "00:00:00:00", gma3_tc_slot = 1, gma3_song_slot = 0,
  }
  local data = nil
  local voices = nil
  local saved_t = -1e9

  local function path() return R.SETTINGS end

  function M.load()
    local d = R.json_decode(L.read(path()) or "")
    data = type(d) == "table" and d or {}
    return data
  end

  local function get(k)
    if not data then M.load() end
    local v = data[k]
    if v == nil then v = DEFAULTS[k] end
    return v
  end

  function M.set(k, v)
    if not data then M.load() end
    data[k] = v
    if v == nil then data[k] = nil end
    local order = { "language", "announce_voice", "count_voice", "count_lang", "count_in_bars", "cue_lead_bars",
      "voice_cues", "voice_count_in", "voice_count_each", "voice_volume", "click_volume", "click_to_master",
      "click_hw_output", "tempo_mode", "count_rate", "stems_model", "structure_engine", "projects_dir", "concert_dir",
      "gma3_export", "gma3_fps", "gma3_tc_start", "gma3_song_gap", "gma3_song_slot", "gma3_ltc_output",
      "gma3_mtc_output", "gma3_tc_slot" }
    reaper.RecursiveCreateDirectory(reaper.GetResourcePath() .. SEP .. "ReaCueMCP", 0)
    local ok = R.write_atomic(path(), R.json_encode(data, "  ", order) .. "\n")
    saved_t = reaper.time_precise()
    return ok
  end

  -- lecture d'un réglage (défaut si absent) ; instant du dernier enregistrement (« enregistré »)
  function M.get(k) return get(k) end
  function M.saved_at() return saved_t end

  function M.enter() M.load() end
  function M.project_changed() end

  -- voix système : macOS « say -v ? », Windows SAPI (PowerShell, sans fenêtre) ; sinon saisie libre
  local function list_voices()
    if voices then return voices end
    voices = {}
    if not reaper.ExecProcess then return voices end
    if R.is_windows() then
      local cmd = 'powershell -NoProfile -NonInteractive -Command "Add-Type -AssemblyName System.Speech; ' ..
        '(New-Object System.Speech.Synthesis.SpeechSynthesizer).GetInstalledVoices() | % { $_.VoiceInfo.Name }"'
      local out = reaper.ExecProcess(cmd, 5000) or ""
      for line in out:gmatch("[^\r\n]+") do
        if not line:match("^%-?%d+$") and line:match("%S") then voices[#voices + 1] = { name = line:gsub("%s+$", ""), lang = "" } end
      end
    else
      local out = reaper.ExecProcess("/usr/bin/say -v ?", 5000) or ""
      for line in out:gmatch("[^\r\n]+") do
        local name, lang = line:match("^(.-)%s+([a-z][a-z][_%-]%a%a)%s+#")
        if name then voices[#voices + 1] = { name = name, lang = lang } end
      end
    end
    return voices
  end

  local function choose_voice(key, pref)
    local vs = list_voices()
    local items, map = { t("auto") }, { false }
    local first = {}
    for _, v in ipairs(vs) do if pref and v.lang:sub(1, 2) == pref then first[#first + 1] = v end end
    for _, v in ipairs(vs) do if not pref or v.lang:sub(1, 2) ~= pref then first[#first + 1] = v end end
    for _, v in ipairs(first) do
      items[#items + 1] = (v.name:gsub("[|&<>!#]", "")) .. (v.lang ~= "" and ("  (" .. v.lang .. ")") or "")
      map[#map + 1] = v.name
    end
    if #vs == 0 then
      local ok, v = reaper.GetUserInputs(t(key), 1, t(key) .. ",extrawidth=120", get(key) or "")
      if ok then M.set(key, (v and v ~= "") and v or nil) end
      return
    end
    gfx.x, gfx.y = gfx.mouse_x, gfx.mouse_y
    local c = gfx.showmenu(table.concat(items, "|"))
    if not c or c < 1 then return end
    M.set(key, map[c] or nil)
  end

  local function choose_hw()
    local n = reaper.GetNumAudioOutputs and reaper.GetNumAudioOutputs() or 2
    local items, vals = { t("hw_none") }, { false }
    for ch = 0, math.max(2, n) - 1, 2 do
      items[#items + 1] = string.format(t("hw_pair"), ch + 1, ch + 2)
      vals[#vals + 1] = ch
    end
    gfx.x, gfx.y = gfx.mouse_x, gfx.mouse_y
    local c = gfx.showmenu(table.concat(items, "|"))
    if not c or c < 1 then return end
    M.set("click_hw_output", vals[c] or nil)
  end

  local function choose_dir(key)
    local cur = get(key) or ""
    local v
    if reaper.JS_Dialog_BrowseForFolder then
      local ok, d = reaper.JS_Dialog_BrowseForFolder(t(key), cur)
      if ok ~= 1 then return end
      v = d
    else
      local ok, d = reaper.GetUserInputs(t("dir_title"), 1, t("dir_field") .. ",extrawidth=260", cur)
      if not ok then return end
      v = d
    end
    v = (v or ""):gsub("^%s+", ""):gsub("%s+$", "")
    M.set(key, v ~= "" and v or nil)
  end

  local function version()
    local src = L.read(L.install_dir() .. SEP .. "reacue_mcp" .. SEP .. "__init__.py") or ""
    return src:match('__version__%s*=%s*"([^"]+)"') or "?"
  end

  -- une ligne : libellé à gauche, contrôles à droite ; renvoie y suivant
  local LW = 0.46
  local function label(s, x, y, w) U.text(U.fit(s, w * LW - 8, 13), x, y + 5, 13, U.INK) end

  local function seg(id, x, y, w, opts, cur, size)
    local n = #opts
    local gap = 4
    local bw = (w - (n - 1) * gap) / n
    for k, o in ipairs(opts) do
      if U.button(id .. k, o[2], x + (k - 1) * (bw + gap), y, bw, 26, (cur == o[1]) and "on" or nil, size or 12) then
        return o[1], true
      end
    end
    return cur, false
  end

  local function stepper(id, x, y, w, val, txt, step, lo, hi)
    if U.ibutton(id .. "m", "left", x, y, 30, 26) then val = math.max(lo, val - step); return val, true end
    U.set(U.PANEL2); gfx.rect(x + 34, y, w - 68, 26, 1)
    local tw = U.text_w(txt, 13, true)
    U.text(txt, x + 34 + (w - 68 - tw) / 2, y + 5, 13, U.INK, true)
    if U.ibutton(id .. "p", "right", x + w - 30, y, 30, 26) then val = math.min(hi, val + step); return val, true end
    return val, false
  end

  -- contrôles partagés avec l'onglet Lumière (même mise en page)
  M.ui = { label = label, seg = seg, stepper = stepper, LW = LW }

  function M.advanced() return reaper.GetExtState("ReaCue", "settings_adv") == "1" end
  function M.set_advanced(on) reaper.SetExtState("ReaCue", "settings_adv", on and "1" or "", true) end

  function M.draw(x, y, w)
    if not data then M.load() end
    local adv = M.advanced()
    local cx = x + math.floor(w * LW)
    local cw = w - math.floor(w * LW)
    local row = 32
    local v, ch

    -- vue simple / avancée, vérification de l'installation
    local b1 = U.text_w(t("check_install"), 12) + 22
    local b2 = U.text_w(adv and t("simple") or t("advanced"), 12) + 22
    if U.button("checkinst", t("check_install"), x, y - 2, b1, 26, nil, 12) then ctx.assistant.open(false) return y end
    if U.button("adv", adv and t("simple") or t("advanced"), x + w - b2, y - 2, b2, 26, adv and "on" or nil, 12) then
      M.set_advanced(not adv) return y
    end
    y = y + 36

    U.heading(t("general"), x, y); y = y + 20
    label(t("language"), x, y, w)
    v, ch = seg("lang", cx, y, cw, { { "fr", "Français" }, { "en", "English" } }, get("language"))
    if ch then M.set("language", v) end
    y = y + row
    if adv then
      label(t("pin"), x, y, w)
      if U.button("setpin", L.remote_pin(), cx, y, cw, 26, nil, 13) then ctx.change_pin() end
      y = y + row
    end
    y = y + 6

    U.heading(t("cues"), x, y); y = y + 20
    label(t("count_in"), x, y, w)
    local n = math.floor(tonumber(get("count_in_bars")) or 2)
    v, ch = stepper("cin", cx, y, cw, n, string.format(t("bars_n"), n), 1, 0, 4)
    if ch then M.set("count_in_bars", v) end
    y = y + row
    label(t("voice_cues"), x, y, w)
    v, ch = seg("vcues", cx, y, cw, { { true, t("on") }, { false, t("off") } }, get("voice_cues") ~= false)
    if ch then M.set("voice_cues", v) end
    y = y + row
    label(t("count_in_voice"), x, y, w)
    v, ch = seg("vcount", cx, y, cw, { { true, t("on") }, { false, t("off") } }, get("voice_count_in") ~= false)
    if ch then M.set("voice_count_in", v) end
    y = y + row
    label(t("announce_voice"), x, y, w)
    if U.button("avoice", get("announce_voice") or t("auto"), cx, y, cw, 26, nil, 12) then choose_voice("announce_voice", get("language")) end
    y = y + row
    if adv then
      label(t("cue_lead"), x, y, w)
      n = math.floor(tonumber(get("cue_lead_bars")) or 2)
      v, ch = stepper("cue", cx, y, cw, n, string.format(t("bars_n"), n), 1, 1, 4)
      if ch then M.set("cue_lead_bars", v) end
      y = y + row
      label(t("count_lang"), x, y, w)
      v, ch = seg("clang", cx, y, cw, { { "en", "one two three four" }, { "fr", "un deux trois quatre" } }, get("count_lang"), 11)
      if ch then M.set("count_lang", v) end
      y = y + row
      label(t("count_voice"), x, y, w)
      if U.button("cvoice", get("count_voice") or t("auto"), cx, y, cw, 26, nil, 12) then choose_voice("count_voice", get("count_lang")) end
      y = y + row
      label(t("count_rate"), x, y, w)
      local cr = math.floor(tonumber(get("count_rate")) or 240)
      v, ch = stepper("count_rate", cx, y, cw, cr, string.format(t("rate_n"), cr), 20, 120, 360)
      if ch then M.set("count_rate", v) end
      y = y + row
    end
    y = y + 6

    U.heading(t("outputs"), x, y); y = y + 20
    label(t("hw"), x, y, w)
    local hw = tonumber(get("click_hw_output"))
    local hwtxt = hw and string.format(t("hw_pair"), hw + 1, hw + 2) or t("hw_none")
    if U.button("hw", hwtxt, cx, y, cw, 26, nil, 12) then choose_hw() end
    y = y + row
    label(t("to_master"), x, y, w)
    v, ch = seg("master", cx, y, cw, { { true, t("on") }, { false, t("off") } }, get("click_to_master") ~= false)
    if ch then M.set("click_to_master", v) end
    y = y + row
    if adv then
      for _, k in ipairs({ { "click_volume", "click_vol" }, { "voice_volume", "voice_vol" } }) do
        label(t(k[2]), x, y, w)
        local vol = tonumber(get(k[1])) or 0.5
        v, ch = stepper(k[1], cx, y, cw, vol, string.format("%d %%", math.floor(vol * 100 + 0.5)), 0.1, 0, 1)
        if ch then M.set(k[1], math.floor(v * 10 + 0.5) / 10) end
        y = y + row
      end
    end
    y = y + 6

    U.heading(t("other"), x, y); y = y + 20
    label(t("structure"), x, y, w)
    v, ch = seg("structure", cx, y, cw, { { "auto", t("structure_auto") }, { "reacue", t("structure_reacue") } },
      get("structure_engine"), 11)
    if ch then M.set("structure_engine", v) end
    y = y + row - 6
    local inst = R.structure_installed and R.structure_installed(R.install_dir(ctx.dir))
    if inst then
      U.text(U.fit(t("structure_on"), cw, 11), cx, y, 11, U.ACCENT)
    else
      local ib = U.text_w(t("install_sf"), 11) + 16
      U.text(U.fit(t("structure_off"), cw - ib - 6, 11), cx, y + 2, 11, U.MUTED)
      if U.button("install_sf", t("install_sf"), cx + cw - ib, y - 2, ib, 20, nil, 11) then ctx.do_action("structure") end
      y = y + 4
    end
    y = y + 16
    y = y + U.para(t("noncommercial"), cx, y, cw, 11, U.WARN, 2) + 2
    if adv then
      label(t("tempo"), x, y, w)
      v, ch = seg("tempo", cx, y, cw, { { "auto", t("tempo_auto") }, { "constant", t("tempo_constant") }, { "beatmap", t("tempo_beatmap") } },
        get("tempo_mode"), 11)
      if ch then M.set("tempo_mode", v) end
      y = y + row
      label(t("stems"), x, y, w)
      v, ch = seg("stems", cx, y, cw, { { "htdemucs_6s", t("stems6") }, { "htdemucs_ft", t("stems4_ft") }, { "htdemucs", t("stems4") } }, get("stems_model"), 11)
      if ch then M.set("stems_model", v) end
      y = y + row
      for _, k in ipairs({ "projects_dir", "concert_dir" }) do
        label(t(k), x, y, w)
        local cur = get(k)
        local shown = cur and U.fit_path("", cur, cw - 12, 11) or
          U.fit_path(t("default") .. " · ", k == "projects_dir" and L.projects_dir() or L.concert_dir(), cw - 12, 11)
        if U.button("dir_" .. k, shown, cx, y, cw, 26, nil, 11) then choose_dir(k) end
        y = y + row
      end
    end
    y = y + 4
    local h = U.para(t("note"), x, y, w, 12, U.MUTED)
    y = y + h + 4
    local st = (reaper.time_precise() - saved_t < 2) and t("saved") or ""
    U.text(U.fit(string.format(t("version"), version()), w - 200, 11), x, y, 11, U.MUTED)
    if U.button("licences", t("licences"), x + w - 190, y - 5, 96, 22, nil, 11) then M.open_licences() end
    if st ~= "" then U.text(st, x + w - U.text_w(st, 12, true), y, 12, U.ACCENT, true) end
    return y + 20
  end

  -- « Licences » : THIRD_PARTY_NOTICES.md du dossier d'installation, sinon la page GitHub
  M.LICENCES_URL = "https://github.com/herve8940/reacue/blob/main/THIRD_PARTY_NOTICES.md"
  function M.licences_target()
    local dir = R.install_dir and R.install_dir(ctx.dir) or nil
    local f = dir and (dir .. SEP .. "THIRD_PARTY_NOTICES.md")
    if f and L.exists(f) then return f end
    return M.LICENCES_URL
  end
  function M.open_licences()
    local target = M.licences_target()
    if R.is_windows() then
      reaper.ExecProcess('cmd.exe /C start "" ' .. R.winq(target), -1)
    elseif (reaper.GetOS and reaper.GetOS() or ""):match("^OSX") or (reaper.GetOS and reaper.GetOS() or ""):match("^macOS") then
      os.execute("open " .. R.shq(target))
    else
      os.execute("xdg-open " .. R.shq(target) .. " &")
    end
    return target
  end

  return M
end

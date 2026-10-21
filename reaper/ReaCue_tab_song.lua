-- ReaCue : onglet « Morceau » / “Song” tab : le projet ouvert.
--   1. Préparer : séparer les stems, préparer, réanalyser, republier le prompteur
--   2. Structure : sections (régions) — écouter, renommer, déplacer le début, ajouter, supprimer ;
--      puis « Appliquer » (= Préparer : ReaCue reprend les régions modifiées à la main)
--   3. Compléments : paroles, accords / batterie publiés, ajouter le morceau à un concert
return function(ctx)
  local L, U, T, R, SEP = ctx.L, ctx.U, ctx.T, ctx.R, ctx.SEP
  local TXT = {
    fr = {
      no_song = "Ouvre le projet d'un morceau, ou crée-en un avec « + Nouveau morceau » (un MP3 ou un dossier de stems).",
      saved = "enregistré ✓", unsaved = "non enregistré", next_split = "Étape suivante : « Séparer stems » (un seul fichier), puis « Préparer ».",
      next_prepare = "Étape suivante : « Préparer ».",
      prepared = "préparé", not_prepared = "pas encore préparé", bars = "%d mesures",
      step1 = "1. Préparer", step2 = "2. Structure — clic sur un nom : écouter", step3 = "3. Compléments",
      separate = "Séparer stems", prepare = "Préparer", reanalyse = "Réanalyser", publish = "Republier",
      reanalyse_q = "Réanalyser le morceau ?\n\nLa structure est recalculée : tes corrections de sections seront remplacées.",
      no_regions = "Pas encore de sections : lance « Préparer ».",
      bar_n = "m. %d", len_n = "%d mes.", odd = "longueur inhabituelle",
      add = "+ Section au curseur", applied_hint = "Structure modifiée : « Appliquer » met à jour click, annonces et prompteur.",
      apply = "Appliquer",
      rename_title = "ReaCue - Renommer la section", rename_field = "Nom :",
      add_title = "ReaCue - Nouvelle section", add_field = "Nom de la section :", add_default = "Pont",
      add_here = "Une section commence déjà à cette mesure.", add_outside = "Place le curseur dans une section existante.",
      del_last = "Il faut garder au moins une section.",
      undo_rename = "ReaCue : renommer une section", undo_move = "ReaCue : déplacer une section",
      undo_add = "ReaCue : ajouter une section", undo_del = "ReaCue : supprimer une section",
      lyrics = "Paroles : %d lignes (%s)", lyrics_none = "Paroles : aucun fichier — dépose paroles.txt dans le dossier des stems",
      open_dir = "Ouvrir le dossier", published = "Prompteur : accords %s · batterie %s", pub_unknown = "Prompteur : pas encore publié pour ce morceau",
      rename_btn = "Nom", add_concert = "Ajouter à un concert", new_concert = "Nouveau concert…", new_name_title = "ReaCue - Nouveau concert",
      new_name_field = "Nom du concert :", added = "« %s » ajouté au concert « %s » Construis-le dans l'onglet Concert.",
      not_saved = "Enregistre d'abord le projet du morceau (Cmd+S / Ctrl+S).",
      after_stems = "\n\nÉtape suivante : « Préparer ».",
    },
    en = {
      no_song = "Open a song's project, or create one with “+ New song” (an MP3 or a folder of stems).",
      saved = "saved ✓", unsaved = "not saved", next_split = "Next step: “Split stems” (a single file), then “Prepare”.",
      next_prepare = "Next step: “Prepare”.",
      prepared = "prepared", not_prepared = "not prepared yet", bars = "%d bars",
      step1 = "1. Prepare", step2 = "2. Structure — click a name: listen", step3 = "3. Extras",
      separate = "Split stems", prepare = "Prepare", reanalyse = "Re-analyse", publish = "Republish",
      reanalyse_q = "Re-analyse the song?\n\nThe structure is computed again: your section fixes will be replaced.",
      no_regions = "No sections yet: run “Prepare”.",
      bar_n = "bar %d", len_n = "%d bars", odd = "unusual length",
      add = "+ Section at cursor", applied_hint = "Structure changed: “Apply” updates the click, cues and prompter.",
      apply = "Apply",
      rename_title = "ReaCue - Rename the section", rename_field = "Name:",
      add_title = "ReaCue - New section", add_field = "Section name:", add_default = "Bridge",
      add_here = "A section already starts at this bar.", add_outside = "Put the cursor inside an existing section.",
      del_last = "At least one section must stay.",
      undo_rename = "ReaCue: rename a section", undo_move = "ReaCue: move a section",
      undo_add = "ReaCue: add a section", undo_del = "ReaCue: delete a section",
      lyrics = "Lyrics: %d lines (%s)", lyrics_none = "Lyrics: no file — drop lyrics.txt in the stems folder",
      open_dir = "Open folder", published = "Prompter: chords %s · drums %s", pub_unknown = "Prompter: not published for this song yet",
      rename_btn = "Name", add_concert = "Add to a concert", new_concert = "New concert…", new_name_title = "ReaCue - New concert",
      new_name_field = "Concert name:", added = "“%s” added to the concert “%s”. Build it in the Concert tab.",
      not_saved = "Save the song's project first (Cmd+S / Ctrl+S).",
      after_stems = "\n\nNext step: “Prepare”.",
    },
  }
  local function t(k) return ctx.tr(TXT, k) end
  local M = {}
  local info = nil          -- {regions, bpm, bars, key, prepared, dirs, titles, lyrics}
  local dirty = false
  local GEN = { CLICK = true, CUES = true, VOIX = true, VOICE = true }

  -- projet ---------------------------------------------------------------------------------
  local function measure_of(tp)
    if not reaper.TimeMap2_timeToBeats then return 0 end
    local _, m = reaper.TimeMap2_timeToBeats(0, tp + 1e-6)
    return math.floor(m or 0)
  end
  local function bar_time(m)
    if reaper.TimeMap2_beatsToTime then return reaper.TimeMap2_beatsToTime(0, 0, m) end
    return nil
  end

  local function list_regions()
    local out, k = {}, 0
    while true do
      local ok, isrgn, pos, rend, name, idx, color = reaper.EnumProjectMarkers3(0, k)
      if not ok or ok == 0 then break end
      if isrgn then out[#out + 1] = { idx = idx, name = name or "", start = pos, stop = rend, color = color or 0 } end
      k = k + 1
    end
    table.sort(out, function(a, b) return a.start < b.start end)
    return out
  end

  local function track_name(tr) local _, n = reaper.GetTrackName(tr); return n or "" end

  local function key_from(names)
    for _, n in ipairs(names) do
      local root, acc, mode = n:match("%f[%a]([A-G])%s?([#b]?)%s?([Mm][ai][jn]%a*)")
      if root then
        mode = mode:lower()
        return root .. acc .. ((mode:sub(1, 3) == "min") and "m" or "")
      end
    end
    return nil
  end

  local function source_file(it)
    local tk = it and reaper.GetActiveTake(it)
    if not tk or (reaper.TakeIsMIDI and reaper.TakeIsMIDI(tk)) then return nil end
    local src = reaper.GetMediaItemTake_Source(tk)
    local parent = src and reaper.GetMediaSourceParent and reaper.GetMediaSourceParent(src)
    while parent do src = parent; parent = reaper.GetMediaSourceParent(src) end
    local fn = src and reaper.GetMediaSourceFileName(src, "") or ""
    return fn ~= "" and fn or nil
  end

  local function read_lyrics(dirs)
    for _, d in ipairs(dirs) do
      local i = 0
      while true do
        local f = reaper.EnumerateFiles(d, i)
        if not f then break end
        local lf = f:lower()
        if (lf:match("^paroles") or lf:match("^parole") or lf:match("^lyrics")) and (lf:match("%.txt$") or lf:match("%.rtf$")) then
          local src = L.read(d .. SEP .. f) or ""
          local n = 0
          if lf:match("%.rtf$") then
            for _ in src:gmatch("\\par[^d]") do n = n + 1 end
          else
            for line in (src .. "\n"):gmatch("(.-)\r?\n") do
              local s = line:gsub("^%s+", ""):gsub("%s+$", "")
              if s ~= "" and not s:match("^%[") then n = n + 1 end
            end
          end
          return { n = n, file = f, dir = d }
        end
        i = i + 1
      end
    end
    return nil
  end

  local function published(titles)
    local src = L.read(reaper.GetResourcePath() .. SEP .. "reaper_www_root" .. SEP .. "reacue_song.json")
    if not src or src:find('"concert"%s*:') then return nil end
    local title = R.jfield(src, "title")
    if not title or not titles[title] then return nil end
    local chords = src:find('"chords"%s*:%s*%[%s*{') ~= nil
    local drums = src:find('"drums"%s*:%s*{') ~= nil
    return { chords = chords, drums = drums }
  end

  local function scan()
    local regs = list_regions()
    local names, dirs, seen_d, titles = {}, {}, {}, {}
    local has_click = false
    for i = 0, (reaper.CountTracks and reaper.CountTracks(0) or 0) - 1 do
      if track_name(reaper.GetTrack(0, i)) == "CLICK" then has_click = true end
    end
    for i = 0, (reaper.CountMediaItems and reaper.CountMediaItems(0) or 0) - 1 do
      local it = reaper.GetMediaItem(0, i)
      local tr = reaper.GetMediaItem_Track and reaper.GetMediaItem_Track(it)
      if not (tr and GEN[track_name(tr)]) then
        local fn = source_file(it)
        if fn then
          local d, base = fn:match("^(.*)[/\\]([^/\\]+)$")
          names[#names + 1] = base or fn
          titles[(base or fn):gsub("%.[^.]+$", "")] = true
          if d and not seen_d[d] then
            seen_d[d] = true
            dirs[#dirs + 1] = d
            local up = d:match("^(.*)[/\\][^/\\]+%-stems[/\\][^/\\]+$")     -- stems séparés par ReaCue
            if up and not seen_d[up] then seen_d[up] = true; dirs[#dirs + 1] = up end
          end
        end
      end
    end
    local bpm = nil
    local t0 = regs[1] and regs[1].start or 0
    if reaper.TimeMap2_GetDividedBpmAtTime then bpm = reaper.TimeMap2_GetDividedBpmAtTime(0, t0 + 0.01)
    elseif reaper.Master_GetTempo then bpm = reaper.Master_GetTempo() end
    local bars = 0
    if #regs > 0 then bars = measure_of(regs[#regs].stop - 0.001) - measure_of(regs[1].start) + 1 end
    local m0 = regs[1] and measure_of(regs[1].start) or 0
    for _, r in ipairs(regs) do
      r.bar = measure_of(r.start) - m0 + 1
      r.len = measure_of(r.stop - 0.001) - measure_of(r.start) + 1
    end
    local roles = 0
    for _, n in ipairs(names) do if ctx.newsong and ctx.newsong.role_of(n) then roles = roles + 1 end end
    info = {
      regions = regs, bpm = bpm, bars = bars, key = key_from(names), prepared = (#regs > 0 and has_click),
      dirs = dirs, titles = titles, has_audio = #names > 0, m0 = m0,
      single_mix = (#names == 1 and roles == 0),        -- un MP3 / WAV seul : séparer d'abord
    }
    info.lyrics = read_lyrics(dirs)
    info.pub = published(titles)
    info.t = reaper.time_precise()
    return info
  end

  -- concert « fictif » d'un seul morceau : transport, sections et répétition dans l'onglet Scène
  function M.pseudo_concert()
    local i = scan()
    if not i.has_audio then return nil end
    local regs = i.regions
    local stop = (#regs > 0 and regs[#regs].stop) or (reaper.GetProjectLength and reaper.GetProjectLength(0)) or 0
    if reaper.GetProjectLength then stop = math.max(stop, reaper.GetProjectLength(0)) end
    return {
      pseudo = true,
      songs = { { title = ctx.proj_name ~= "" and ctx.proj_name or "?", start = 0, stop = stop, next = stop,
                  bar1 = regs[1] and regs[1].start or 0, bars = i.bars, bpm = i.bpm or 120, key = i.key,
                  sections = #regs } },
    }
  end

  function M.project_changed() info = nil; dirty = false end
  function M.enter() info = nil end

  local function changed()
    dirty = true
    info = nil
    if ctx.tabs.stage.invalidate then ctx.tabs.stage.invalidate() end
    reaper.UpdateTimeline()
  end

  -- édition des régions ---------------------------------------------------------------------
  local function set_region(r, start, stop, name)
    reaper.SetProjectMarker4(0, r.idx, true, start, stop, name or r.name, r.color or 0, (name == "") and 1 or 0)
  end

  local function rename(k)
    local r = info.regions[k]
    local ok, v = reaper.GetUserInputs(t("rename_title"), 1, t("rename_field") .. ",extrawidth=120", r.name)
    if not ok or not v or v == r.name then return end
    v = v:gsub("^%s+", ""):gsub("%s+$", "")
    if v == "" then return end
    reaper.Undo_BeginBlock()
    set_region(r, r.start, r.stop, v)
    reaper.Undo_EndBlock(t("undo_rename"), -1)
    changed()
  end

  local function move(k, d)
    local regs = info.regions
    local r, prev = regs[k], regs[k - 1]
    local nt = bar_time(measure_of(r.start) + d)
    if not nt or nt >= r.stop - 0.01 then return end
    if prev and nt <= prev.start + 0.01 then return end
    if nt < 0 then return end
    reaper.Undo_BeginBlock()
    if prev and math.abs(prev.stop - r.start) < 0.02 then set_region(prev, prev.start, nt) end
    set_region(r, nt, r.stop)
    reaper.Undo_EndBlock(t("undo_move"), -1)
    changed()
  end

  local function delete(k)
    local regs = info.regions
    if #regs <= 1 then reaper.ShowMessageBox(t("del_last"), T("title"), 0) return end
    local r, prev, nx = regs[k], regs[k - 1], regs[k + 1]
    reaper.Undo_BeginBlock()
    if prev and math.abs(prev.stop - r.start) < 0.02 then set_region(prev, prev.start, r.stop)
    elseif nx and math.abs(nx.start - r.stop) < 0.02 then set_region(nx, r.start, nx.stop) end
    reaper.DeleteProjectMarker(0, r.idx, true)
    reaper.Undo_EndBlock(t("undo_del"), -1)
    changed()
  end

  local function add_at_cursor()
    local regs = info.regions
    local tb = bar_time(measure_of(reaper.GetCursorPosition()))
    if not tb then return end
    local host = nil
    for _, r in ipairs(regs) do
      if math.abs(r.start - tb) < 0.02 then reaper.ShowMessageBox(t("add_here"), T("title"), 0) return end
      if r.start < tb and tb < r.stop then host = r end
    end
    if not host then reaper.ShowMessageBox(t("add_outside"), T("title"), 0) return end
    local ok, v = reaper.GetUserInputs(t("add_title"), 1, t("add_field") .. ",extrawidth=120", t("add_default"))
    if not ok or not v or v:gsub("%s", "") == "" then return end
    reaper.Undo_BeginBlock()
    local stop = host.stop
    set_region(host, host.start, tb)
    reaper.AddProjectMarker2(0, true, tb, stop, v, -1, 0)
    reaper.Undo_EndBlock(t("undo_add"), -1)
    changed()
  end

  -- ajouter à un concert --------------------------------------------------------------------
  local function slug(name)
    local s = tostring(name):gsub('[\\/:*?"<>|]+', "-"):gsub("^[%s%.]+", ""):gsub("[%s%.]+$", "")
    return s ~= "" and s or "Concert"
  end
  ctx.slug = slug

  -- ajoute le projet à la setlist <dossier des concerts>/<nom>.setlist.json (créée si besoin)
  function ctx.add_to_setlist(name, project, title)
    local dir = L.concert_dir()
    reaper.RecursiveCreateDirectory(dir, 0)
    local path = dir .. SEP .. slug(name) .. ".setlist.json"
    local d = R.json_decode(L.read(path) or "") or {}
    d.name = d.name or name
    d.gap_s = d.gap_s or 4
    d.songs = d.songs or R.json_array({})
    setmetatable(d.songs, getmetatable(R.json_array({})))
    d.songs[#d.songs + 1] = { project = project, title = title }
    d.live = d.live or R.json_array({})
    d.live_exceptions = d.live_exceptions or {}
    R.write_atomic(path, R.json_encode(d, "  ", { "name", "gap_s", "songs", "live", "live_exceptions" }))
    return path
  end

  local function add_to_concert()
    if (ctx.proj_file or "") == "" then reaper.ShowMessageBox(t("not_saved"), T("title"), 0) return end
    local names = {}
    local dir = L.concert_dir()
    local i = 0
    while true do
      local f = reaper.EnumerateFiles(dir, i)
      if not f then break end
      local stem = f:match("^(.*)%.setlist%.json$")
      if stem then names[#names + 1] = stem end
      i = i + 1
    end
    table.sort(names)
    local menu = t("new_concert")
    if #names > 0 then menu = menu .. "||" .. table.concat(names, "|") end
    gfx.x, gfx.y = gfx.mouse_x, gfx.mouse_y
    local choice = gfx.showmenu(menu)
    if not choice or choice < 1 then return end
    local name
    if choice == 1 then
      local ok, v = reaper.GetUserInputs(t("new_name_title"), 1, t("new_name_field") .. ",extrawidth=120", "")
      if not ok or not v or v:gsub("%s", "") == "" then return end
      name = v
    else
      name = names[choice - 1]
    end
    if not name then return end
    ctx.add_to_setlist(name, ctx.proj_file, ctx.proj_name)
    if ctx.tabs.concert.load_setlist then ctx.tabs.concert.load_setlist(L.concert_dir() .. SEP .. slug(name) .. ".setlist.json") end
    ctx.show_result(T("done_title"), string.format(t("added"), ctx.proj_name, name), true)
  end

  local function open_dir(d)
    if ctx.R.is_windows() then reaper.ExecProcess('explorer.exe ' .. ctx.R.winq(d), -1)
    elseif (reaper.GetOS and reaper.GetOS() or ""):match("^OSX") or (reaper.GetOS and reaper.GetOS() or ""):match("^macOS") then
      os.execute("open " .. ctx.R.shq(d))
    else os.execute("xdg-open " .. ctx.R.shq(d) .. " &") end
  end

  -- lancement des traitements ---------------------------------------------------------------
  -- après une préparation / séparation réussie lancée depuis la fenêtre : le projet du morceau est
  -- enregistré (sinon le concert ne retrouve ni sections ni tempo) ; jamais un projet concert
  local saved_t = nil
  function M.autosave(key)
    if ctx.is_concert or key ~= ctx.proj_key or (ctx.proj_file or "") == "" then return false end
    if not reaper.Main_SaveProject then return false end
    reaper.Main_SaveProject(0, false)
    saved_t = reaper.time_precise()
    return true
  end

  local function done_cb(after)
    local key = ctx.proj_key
    return function(state, msg)
      info = nil
      if ctx.tabs.stage.invalidate then ctx.tabs.stage.invalidate() end
      if state == "done" then
        dirty = false
        M.autosave(key)
        ctx.show_result(T("done_title"), (msg or "") .. (after or ""), true)
      else
        ctx.show_result(T("error_title"), msg, false)
      end
      ctx.refresh(true)
    end
  end

  function M.prepare() return ctx.start_cli("prepare", R.tr("prepare"), done_cb()) end
  function M.reanalyse()
    if reaper.ShowMessageBox(t("reanalyse_q"), T("title"), 1) ~= 1 then return false end
    return ctx.start_cli("prepare --reanalyse", R.tr("prepare"), done_cb())
  end
  function M.publish() return ctx.start_cli("publish", R.tr("publish"), done_cb()) end
  function M.separate() return ctx.start_stems(done_cb(t("after_stems"))) end

  -- dessin ------------------------------------------------------------------------------------
  local function fmt_bpm(b) return b and string.format("%.0f BPM", b) or "? BPM" end

  function M.draw(x, y, w)
    if not info or reaper.time_precise() - (info.t or 0) > 2 then scan() end
    local i = info
    if ctx.job then y = y + ctx.draw_job(x, y, w) end
    -- état
    local title = ctx.proj_name ~= "" and ctx.proj_name or "?"
    local NS = ctx.newsong
    local nw = NS and (U.text_w(NS.t("button"), 13) + 22) or 0
    U.text(U.fit(title, w - nw - 10, 18, true), x, y, 18, U.INK, true)
    if NS and U.button("newsong", NS.t("button"), x + w - nw, y - 3, nw, 26, (not i.has_audio) and "primary" or nil, 13)
      and not ctx.job then NS.start() return y end
    y = y + 24
    if ctx.flash and reaper.time_precise() - ctx.flash.t < 3 then
      y = y + (U.para(ctx.flash.txt, x, y, w, 12, ctx.flash.bad and U.WARN or U.ACCENT, 3) or 0) + 6
    end
    if not i.has_audio then
      U.para(t("no_song"), x, y, w, 13, U.MUTED)
      return y + 40
    end
    local parts = { i.prepared and t("prepared") or t("not_prepared") }
    if i.prepared then parts[#parts + 1] = fmt_bpm(i.bpm) end
    if i.bars > 0 then parts[#parts + 1] = string.format(t("bars"), i.bars) end
    if i.key then parts[#parts + 1] = i.key end
    local dirty_p = reaper.IsProjectDirty and reaper.IsProjectDirty(0) == 1
    local st_txt, st_col
    if (ctx.proj_file or "") == "" or dirty_p then st_txt, st_col = t("unsaved"), U.WARN
    elseif saved_t and reaper.time_precise() - saved_t < 600 then st_txt, st_col = t("saved"), U.ACCENT end
    U.set(i.prepared and U.ACCENT or U.WARN); gfx.circle(x + 5, y + 8, 4, 1, 1)
    local line = table.concat(parts, " · ")
    local sw = st_txt and (U.text_w(st_txt, 12) + 10) or 0
    U.text(U.fit(line, w - 16 - sw, 13), x + 16, y, 13, U.MUTED)
    if st_txt then U.text(st_txt, x + w - sw + 10, y + 1, 12, st_col) end
    y = y + 22
    if not i.prepared then
      U.text(U.fit(i.single_mix and t("next_split") or t("next_prepare"), w, 12), x, y, 12, U.WARN)
      y = y + 18
    end
    y = y + 4

    -- 1. Préparer
    U.heading(t("step1"), x, y)
    y = y + 18
    local gap = 6
    local bw = (w - 3 * gap) / 4
    local busy = ctx.job ~= nil
    local split_first = i.single_mix and not i.prepared
    if U.button("sep", t("separate"), x, y, bw, 34, split_first and "primary" or nil, 13) and not busy then M.separate() end
    if U.button("prep", t("prepare"), x + (bw + gap), y, bw, 34, (not split_first) and "primary" or nil, 13) and not busy then M.prepare() end
    if U.button("rean", t("reanalyse"), x + 2 * (bw + gap), y, bw, 34, nil, 13) and not busy then M.reanalyse() end
    if U.button("pub", t("publish"), x + 3 * (bw + gap), y, bw, 34, nil, 13) and not busy then M.publish() end
    y = y + 46

    -- 2. Structure
    U.heading(t("step2"), x, y)
    local aw = U.text_w(t("add"), 12) + 18
    if #i.regions > 0 and U.button("addsec", t("add"), x + w - aw, y - 4, aw, 22, nil, 12) then add_at_cursor() return y end
    y = y + 20
    if dirty then
      U.set(U.WARN, 0.2); gfx.rect(x, y, w, 30, 1)
      U.set(U.WARN); gfx.rect(x, y, 4, 30, 1)
      local bw2 = U.text_w(t("apply"), 13) + 24
      U.text(U.fit(t("applied_hint"), w - bw2 - 24, 12), x + 12, y + 8, 12, U.INK)
      if U.button("apply", t("apply"), x + w - bw2 - 4, y + 3, bw2, 24, "primary", 13) and not busy then M.prepare() end
      y = y + 36
    end
    if #i.regions == 0 then
      U.text(t("no_regions"), x, y + 4, 13, U.MUTED)
      y = y + 26
    end
    local cur = L.pos()
    for k, r in ipairs(i.regions) do
      local rh = 26
      local inside = cur >= r.start - 0.01 and cur < r.stop - 0.01
      if inside then U.set(U.PANEL); gfx.rect(x - 4, y, w + 8, rh - 2, 1) end
      local col = U.GREY
      if r.color and r.color ~= 0 then local rr, gg, bb = reaper.ColorFromNative(r.color & 0xFFFFFF); col = { rr, gg, bb } end
      U.set(col); gfx.rect(x - 4, y + 3, 4, rh - 8, 1)
      local odd = r.len ~= 4 and r.len ~= 8 and r.len ~= 16
      local right = string.format(t("bar_n"), r.bar) .. "  ·  " .. string.format(t("len_n"), r.len)
      local nbw = U.text_w(t("rename_btn"), 12) + 16
      local tools_w = nbw + 3 * 26 + 3 * 4
      local rw = U.text_w(right, 12)
      local name_w = w - tools_w - rw - 24
      local over = U.over(x, y, name_w, rh)
      U.text(U.fit(r.name, name_w, 14, inside), x + 6, y + 4, 14, over and U.INK or { 220, 220, 224 }, inside)
      if over and U.clicked then
        reaper.SetEditCurPos(r.start, true, true)
        if L.play_state() ~= "play" then reaper.OnPlayButton() end
      end
      U.text(right, x + w - tools_w - rw - 10, y + 5, 12, odd and U.WARN or U.MUTED)
      local tx = x + w - tools_w
      if U.button("ren" .. k, t("rename_btn"), tx, y + 1, nbw, 22, nil, 12) then rename(k) return y end
      tx = tx + nbw + 4
      if U.ibutton("mvl" .. k, "left", tx, y + 1, 26, 22) then move(k, -1) return y end
      tx = tx + 30
      if U.ibutton("mvr" .. k, "right", tx, y + 1, 26, 22) then move(k, 1) return y end
      tx = tx + 30
      if U.ibutton("del" .. k, "x", tx, y + 1, 26, 22) then delete(k) return y end
      y = y + rh
    end
    y = y + 10

    -- 3. Compléments
    U.heading(t("step3"), x, y)
    y = y + 20
    local ly = i.lyrics
    local ltxt = ly and string.format(t("lyrics"), ly.n, ly.file) or t("lyrics_none")
    local ow = U.text_w(t("open_dir"), 12) + 18
    U.text(U.fit(ltxt, w - ow - 10, 13), x, y + 4, 13, ly and U.INK or U.MUTED)
    local d = (ly and ly.dir) or i.dirs[#i.dirs] or i.dirs[1]
    if d and U.button("opendir", t("open_dir"), x + w - ow, y, ow, 24, nil, 12) then open_dir(d) end
    y = y + 30
    local p = i.pub
    local ptxt = p and string.format(t("published"), p.chords and "✓" or "—", p.drums and "✓" or "—") or t("pub_unknown")
    U.text(U.fit(ptxt, w, 13), x, y, 13, p and U.INK or U.MUTED)
    y = y + 26
    local cw = U.text_w(t("add_concert"), 13) + 24
    if U.button("addconcert", t("add_concert"), x, y, cw, 28) then add_to_concert() return y end
    return y + 36
  end

  return M
end

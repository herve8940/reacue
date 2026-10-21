-- ReaCue : onglet « Concert » / “Concert” tab : composer une setlist à partir des projets de morceaux,
-- la construire / reconstruire, l'ouvrir, régler « joué en live », retrouver les concerts existants.
return function(ctx)
  local L, U, T, R, SEP = ctx.L, ctx.U, ctx.T, ctx.R, ctx.SEP
  local TXT = {
    fr = {
      songs = "Morceaux (%s)", setlist = "Setlist « %s »", unnamed = "Nouveau concert",
      prepared = "✓", to_prepare = "à préparer", none_found = "Aucun projet trouvé dans %s",
      empty = "Ajoute des morceaux avec « + »", n_songs = "%d morceaux", total = "%d morceaux · %s",
      new = "Nouveau", rename = "Renommer", build = "Construire", rebuild = "Reconstruire", open = "Ouvrir",
      live = "Joué en live…", existing = "Concerts existants", load = "Modifier", open_one = "Ouvrir",
      not_built = "pas encore construit", refresh = "Actualiser",
      name_title = "ReaCue - Nom du concert", name_field = "Nom :",
      building = "Construction du concert", built = "Concert « %s » construit : ouvert dans un onglet.",
      unprepared_q = "Ces morceaux ne sont pas préparés (pas de sections ou pas de click) :\n%s\n\nConstruire quand même ?",
    },
    en = {
      songs = "Songs (%s)", setlist = "Setlist “%s”", unnamed = "New concert",
      prepared = "✓", to_prepare = "to prepare", none_found = "No project found in %s",
      empty = "Add songs with “+”", n_songs = "%d songs", total = "%d songs · %s",
      new = "New", rename = "Rename", build = "Build", rebuild = "Rebuild", open = "Open",
      live = "Played live…", existing = "Existing concerts", load = "Edit", open_one = "Open",
      not_built = "not built yet", refresh = "Refresh",
      name_title = "ReaCue - Concert name", name_field = "Name:",
      building = "Building the concert", built = "Concert “%s” built: open in a tab.",
      unprepared_q = "These songs are not prepared (no sections or no click):\n%s\n\nBuild anyway?",
    },
  }
  local function t(k) return ctx.tr(TXT, k) end
  local M = {}
  local projects = nil                 -- {path, name, prepared, bpm}
  local cache = {}                     -- path -> {size, prepared, bpm}
  local scroll = 0
  local concerts, setlists = nil, nil
  local ed = { name = nil, path = nil, songs = {}, extra = nil }
  local ORDER = { "name", "gap_s", "songs", "live", "live_exceptions" }

  -- un projet est « préparé » s'il a des régions et une piste CLICK ; tempo : 1er point de la carte
  local function tokens(line)
    local out, i, n = {}, 1, #line
    while i <= n do
      local c = line:sub(i, i)
      if c:match("%s") then i = i + 1
      elseif c == '"' then
        local j = line:find('"', i + 1, true) or n + 1
        out[#out + 1] = line:sub(i + 1, j - 1); i = j + 1
      else
        local j = line:find("%s", i) or n + 1
        out[#out + 1] = line:sub(i, j - 1); i = j
      end
    end
    return out
  end

  function M.inspect_rpp(src)
    local regions, click = false, false
    for line in src:gmatch("[^\r\n]+") do
      local l = line:match("^%s*(.*)$")
      if l:sub(1, 7) == "MARKER " and not regions then
        local tk = tokens(l)
        if tonumber(tk[5]) and (math.floor(tonumber(tk[5])) & 1) == 1 then regions = true end
      elseif l == 'NAME CLICK' or l == 'NAME "CLICK"' then click = true end
    end
    local bpm = tonumber(src:match("<TEMPOENVEX.-\n%s*PT%s+[%d%.]+%s+([%d%.]+)")) or tonumber(src:match("\n%s*TEMPO%s+([%d%.]+)"))
    return { prepared = regions and click, bpm = bpm }
  end

  local function add_dir(dir, out, skip)
    local i = 0
    while true do
      local f = reaper.EnumerateFiles(dir, i)
      if not f then break end
      if f:lower():match("%.rpp$") and not f:lower():match("%-bak%.rpp$") then
        local path = dir .. SEP .. f
        local src = L.read(path)
        if src then
          local c = cache[path]
          if not c or c.size ~= #src then c = M.inspect_rpp(src); c.size = #src; cache[path] = c end
          out[#out + 1] = { path = path, name = f:gsub("%.[Rr][Pp][Pp]$", ""), prepared = c.prepared, bpm = c.bpm }
        end
      end
      i = i + 1
    end
  end

  local SKIP = { concerts = true, backups = true, media = true, peaks = true }
  function M.scan()
    local dir = L.projects_dir()
    local out = {}
    add_dir(dir, out)
    local cdir = L.concert_dir():lower()
    local k = 0
    while reaper.EnumerateSubdirectories do
      local sd = reaper.EnumerateSubdirectories(dir, k)
      if not sd then break end
      local full = dir .. SEP .. sd
      if not SKIP[sd:lower()] and full:lower() ~= cdir and not sd:match("%-stems$") then add_dir(full, out) end
      k = k + 1
    end
    table.sort(out, function(a, b) return a.name:lower() < b.name:lower() end)
    projects = out
    concerts, setlists = L.list_concerts(), L.list_setlists()
    return out
  end

  -- setlist en cours d'édition ------------------------------------------------------------------
  function M.load_setlist(path)
    local d = R.json_decode(L.read(path) or "")
    if type(d) ~= "table" then return false end
    ed = { name = d.name or path:match("([^/\\]+)%.setlist%.json$"), path = path, songs = {}, extra = d }
    for _, e in ipairs(d.songs or {}) do
      if type(e) == "table" then
        ed.songs[#ed.songs + 1] = { project = e.project or e.path or e.name, title = e.title }
      else
        ed.songs[#ed.songs + 1] = { project = e, title = tostring(e):match("([^/\\]+)%.[Rr][Pp][Pp]$") or tostring(e) }
      end
    end
    return true
  end

  local function ed_paths()
    local name = ed.name or t("unnamed")
    local dir = L.concert_dir()
    local stem = ctx.slug(name)
    return dir .. SEP .. stem .. ".setlist.json", dir .. SEP .. stem .. ".RPP", dir .. SEP .. stem .. ".concert.lua"
  end

  function M.save()
    local name = ed.name or t("unnamed")
    ed.name = name
    local path = ed_paths()
    reaper.RecursiveCreateDirectory(L.concert_dir(), 0)
    local d = ed.extra or {}
    -- profil « joué en live » : celui du fichier existant s'il y en a un
    local cur = R.json_decode(L.read(path) or "")
    if type(cur) == "table" then
      d.live = cur.live or d.live
      d.live_exceptions = cur.live_exceptions or d.live_exceptions
      d.gap_s = cur.gap_s or d.gap_s
    end
    d.name = name
    d.gap_s = d.gap_s or 4
    local songs = R.json_array({})
    for _, s in ipairs(ed.songs) do songs[#songs + 1] = { project = s.project, title = s.title } end
    d.songs = songs
    d.live = d.live or R.json_array({})
    if type(d.live) == "table" and #d.live == 0 then d.live = R.json_array({}) end
    d.live_exceptions = d.live_exceptions or {}
    ed.extra = d
    ed.path = path
    R.write_atomic(path, R.json_encode(d, "  ", ORDER))
    return path
  end

  local function built_concert()
    local _, rpp, side = ed_paths()
    if not L.exists(rpp) then return nil end
    return L.load_file(side)
  end

  function M.build()
    if #ed.songs == 0 or ctx.job then return false end
    local unprep = {}
    for _, s in ipairs(ed.songs) do
      local c = cache[s.project]
      if c and not c.prepared then unprep[#unprep + 1] = "· " .. (s.title or s.project) end
    end
    if #unprep > 0 and reaper.ShowMessageBox(string.format(t("unprepared_q"), table.concat(unprep, "\n")), T("title"), 1) ~= 1 then
      return false
    end
    local path = M.save()
    local _, rpp = ed_paths()
    local name = ed.name
    return ctx.start_cli(ctx.cli_setlist(path), t("building"), function(state, msg)
      concerts, setlists = nil, nil
      if state == "done" then
        ctx.open_built(rpp)
        ctx.flash = { txt = string.format(t("built"), name), t = reaper.time_precise() }
      else
        ctx.show_result(T("error_title"), msg, false)
      end
    end)
  end

  function M.enter() M.scan() end
  function M.project_changed() concerts, setlists = nil, nil end

  -- dessin -----------------------------------------------------------------------------------
  local function draw_projects(x, y, w, maxrows)
    local dir = L.projects_dir()
    U.heading(U.fit(string.format(t("songs"), dir:match("([^/\\]+)$") or dir), w - 80, 12), x, y)
    local rw = U.text_w(t("refresh"), 11) + 14
    if U.button("rescan", t("refresh"), x + w - rw, y - 4, rw, 20, nil, 11) then M.scan() end
    y = y + 20
    if #projects == 0 then
      U.para(string.format(t("none_found"), dir), x, y, w, 12, U.MUTED, 3)
      return y + 40
    end
    local ROWH = 26
    local n = #projects
    local vis = math.min(n, maxrows)
    if U.over(x, y, w, vis * ROWH) and U.wheel ~= 0 then
      scroll = math.max(0, math.min(n - vis, scroll + (U.wheel > 0 and -1 or 1)))
    end
    scroll = math.max(0, math.min(math.max(0, n - vis), scroll))
    for k = 1, vis do
      local p = projects[k + scroll]
      local yy = y + (k - 1) * ROWH
      U.set(U.PANEL2); gfx.rect(x, yy, w, ROWH - 3, 1)
      local mark = p.prepared and t("prepared") or t("to_prepare")
      local right = (p.bpm and string.format("%.0f", p.bpm) or "") .. "  " .. mark
      local rwid = U.text_w(right, 11)
      U.text(U.fit(p.name, w - rwid - 44, 13), x + 6, yy + 4, 13, p.prepared and U.INK or U.WARN)
      U.text(right, x + w - 30 - rwid - 6, yy + 6, 11, p.prepared and U.ACCENT or U.WARN)
      if U.ibutton("addp" .. k, "plus", x + w - 28, yy + 1, 26, ROWH - 5) then
        ed.songs[#ed.songs + 1] = { project = p.path, title = p.name }
      end
    end
    if n > vis then U.text(string.format("%d–%d / %d", scroll + 1, scroll + vis, n), x, y + vis * ROWH + 2, 11, U.MUTED) end
    return y + vis * ROWH + (n > vis and 18 or 4)
  end

  local function draw_setlist(x, y, w)
    local name = ed.name or t("unnamed")
    U.heading(U.fit(string.format(t("setlist"), name), w - 80, 12), x, y)
    local rw = U.text_w(t("rename"), 11) + 14
    if U.button("rename", t("rename"), x + w - rw, y - 4, rw, 20, nil, 11) then
      local ok, v = reaper.GetUserInputs(t("name_title"), 1, t("name_field") .. ",extrawidth=120", name)
      if ok and v and v:gsub("%s", "") ~= "" then ed.name = v end
    end
    y = y + 20
    if #ed.songs == 0 then
      U.text(t("empty"), x, y + 4, 12, U.MUTED)
      y = y + 26
    end
    local ROWH = 26
    for k, s in ipairs(ed.songs) do
      local yy = y
      U.set(U.PANEL2); gfx.rect(x, yy, w, ROWH - 3, 1)
      local c = cache[s.project]
      U.text(U.fit(k .. ". " .. (s.title or "?"), w - 96, 13), x + 6, yy + 4, 13, (c and not c.prepared) and U.WARN or U.INK)
      local bx = x + w - 3 * 26 - 4
      if U.ibutton("up" .. k, "up", bx, yy + 1, 24, ROWH - 5) and k > 1 then
        ed.songs[k], ed.songs[k - 1] = ed.songs[k - 1], ed.songs[k]
      end
      if U.ibutton("dn" .. k, "down", bx + 26, yy + 1, 24, ROWH - 5) and k < #ed.songs then
        ed.songs[k], ed.songs[k + 1] = ed.songs[k + 1], ed.songs[k]
      end
      if U.ibutton("rm" .. k, "x", bx + 52, yy + 1, 24, ROWH - 5) then table.remove(ed.songs, k) return y + ROWH end
      y = y + ROWH
    end
    local bc = built_concert()
    local foot
    if bc and #bc.songs > 0 then
      foot = string.format(t("total"), #ed.songs, L.fmt_time(bc.songs[#bc.songs].stop))
    else
      foot = string.format(t("n_songs"), #ed.songs) .. " · " .. t("not_built")
    end
    U.text(U.fit(foot, w, 11), x, y + 2, 11, U.MUTED)
    return y + 20
  end

  local function draw_existing(x, y, w)
    if not concerts then concerts, setlists = L.list_concerts(), L.list_setlists() end
    if #concerts == 0 and #setlists == 0 then return y end
    U.heading(t("existing"), x, y)
    y = y + 20
    local function row(k, d, built)
      local bw = U.text_w(t("load"), 12) + 16
      local ow = U.text_w(t("open_one"), 12) + 16
      U.set(U.PANEL2); gfx.rect(x, y, w, 23, 1)
      local lab = string.format(L.tr("n_songs"), d.name or "?", d.songs and #d.songs or 0)
      if not built then lab = (d.name or "?") .. "  ·  " .. t("not_built") end
      U.text(U.fit(lab, w - bw - ow - 20, 13), x + 6, y + 4, 13, U.INK)
      if U.button("ld" .. k, t("load"), x + w - bw - ow - 6, y + 1, bw, 21, nil, 12) then
        M.load_setlist(d.setlist)
      end
      if built and U.button("op" .. k, t("open_one"), x + w - ow, y + 1, ow, 21, nil, 12) then
        L.open_concert(d)
        ctx.refresh(true)
      end
      y = y + 26
    end
    for k, d in ipairs(concerts) do row("c" .. k, d, true) end
    for k, d in ipairs(setlists) do row("s" .. k, d, false) end
    return y
  end

  function M.draw(x, y, w)
    if not projects then M.scan() end
    if ctx.job then y = y + ctx.draw_job(x, y, w) end
    local two = w >= 500
    local y_end
    if two then
      local cw = math.floor((w - 16) / 2)
      local y1 = draw_projects(x, y, cw, 12)
      local y2 = draw_setlist(x + cw + 16, y, cw)
      y_end = math.max(y1, y2)
    else
      y_end = draw_projects(x, y, w, 8)
      y_end = draw_setlist(x, y_end + 10, w)
    end
    y = y_end + 10
    -- actions
    local bc = built_concert()
    local busy = ctx.job ~= nil
    local gap = 6
    local labels = { t("new"), bc and t("rebuild") or t("build"), t("open"), t("live") }
    local bw = (w - 3 * gap) / 4
    if U.button("cnew", labels[1], x, y, bw, 32, nil, 13) then ed = { name = nil, path = nil, songs = {}, extra = nil } end
    if U.button("cbuild", labels[2], x + (bw + gap), y, bw, 32, (#ed.songs > 0) and "primary" or nil, 13) and not busy then M.build() end
    if U.button("copen", labels[3], x + 2 * (bw + gap), y, bw, 32, nil, 13) and bc then
      L.open_concert(bc)
      ctx.refresh(true)
    end
    if U.button("clive", labels[4], x + 3 * (bw + gap), y, bw, 32, nil, 13) and #ed.songs > 0 then
      local path = M.save()
      local c = bc or { setlist = path, songs = {} }
      if not bc then for _, s in ipairs(ed.songs) do c.songs[#c.songs + 1] = { title = s.title } end end
      c.setlist = path
      ctx.open_live(c)
    end
    y = y + 44
    if ctx.flash and reaper.time_precise() - ctx.flash.t < 3 then
      U.text(U.fit(ctx.flash.txt, w, 12), x, y - 6, 12, ctx.flash.bad and U.WARN or U.ACCENT, true)
      y = y + 14
    end
    y = draw_existing(x, y, w)
    return y + 6
  end

  return M
end

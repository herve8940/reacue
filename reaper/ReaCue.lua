-- ReaCue : fenêtre principale, en 4 onglets / main window, 4 tabs (French / English).
--   Morceau  : préparer le projet ouvert (séparer les stems, préparer, réanalyser, republier), structure
--              (écouter, renommer, déplacer, ajouter, supprimer une section), paroles, ajout à un concert
--   Concert  : composer une setlist avec les projets préparés, construire / reconstruire, ouvrir,
--              « joué en live » (stems coupés), concerts existants
--   Scène    : pilotage (transport, sections, setlist), instruments (mute / solo / tout entendre),
--              répétition (boucle avec 1 mesure de décompte, ralenti), Vérifier, QR, PIN de la Régie
--   Réglages : reacue_settings.json sans éditer le fichier (langue, décompte, annonces, voix, sorties,
--              volumes, tempo, séparation, dossiers), version installée
-- Tant que la fenêtre est ouverte (quel que soit l'onglet, même ancrée) : arrêt automatique en fin de
-- morceau (concert), boucle de répétition, télécommande Régie des téléphones, profil « joué en live ».
-- Clic droit : ancrer / détacher. Échap : fermer une vue (QR, Vérifier…) puis la fenêtre.

local script_dir = debug.getinfo(1, "S").source:match("^@?(.*[/\\])") or ""
local SCRIPT = script_dir .. "ReaCue.lua"
if reaper.get_action_context then SCRIPT = select(2, reaper.get_action_context()) or SCRIPT end
local START_TAB = REACUE_START_TAB          -- « ReaCue - Concert » ouvre la même fenêtre sur l'onglet Scène

-- une seule fenêtre : si une autre action ReaCue l'a déjà ouverte, on lui demande de changer d'onglet
do
  local alive = tonumber(reaper.GetExtState("ReaCue", "win_alive"))
  local who = reaper.GetExtState("ReaCue", "win_script")
  if alive and reaper.time_precise() - alive < 1.5 and who ~= "" and who ~= SCRIPT then
    reaper.SetExtState("ReaCue", "win_goto", START_TAB or "auto", false)
    return
  end
end
-- relancer l'action redémarre la fenêtre (pas de question « terminate instances ») ; bouton allumé
if reaper.set_action_options then reaper.set_action_options(1 | 2 | 4) end

local L = dofile(script_dir .. "ReaCue_concert_lib.lua")
local U = dofile(script_dir .. "ReaCue_ui.lua")
local S = dofile(script_dir .. "ReaCue_stems.lua")
local R = L.R
U.init(R.is_windows())
local SEP = package.config:sub(1, 1)

local TXT = {
  fr = {
    title = "ReaCue", tabs = { song = "Morceau", concert = "Concert", stage = "Scène", settings = "Réglages" },
    bridge = "pont", web = "web", close = "Fermer", ok = "OK", running = "%s… %d s", again = "encore ?",
    working = "en cours", done_title = "Terminé", error_title = "Erreur",
  },
  en = {
    title = "ReaCue", tabs = { song = "Song", concert = "Concert", stage = "Stage", settings = "Settings" },
    bridge = "bridge", web = "web", close = "Close", ok = "OK", running = "%s… %d s", again = "again?",
    working = "running", done_title = "Done", error_title = "Error",
  },
}
local function T(k)
  local l = TXT[L.lang()] or TXT.fr
  local v = l[k]
  if v == nil then v = L.tr(k) end
  return v
end

-- contexte partagé par les onglets -------------------------------------------------------
local ctx = {
  L = L, U = U, R = R, S = S, T = T, dir = script_dir, SEP = SEP,
  tab = nil, overlay = nil, job = nil, result = nil,
  c = nil, is_concert = false, proj_key = nil, proj_file = "", proj_name = "",
  layout_h = nil, W = 560, overlays = {},
}
function ctx.lang() return L.lang() end
function ctx.tr(tbl, k)       -- textes d'un module : tbl = {fr = {...}, en = {...}}
  local l = tbl[L.lang()] or tbl.fr
  local v = l[k]
  if v == nil then v = tbl.fr[k] end
  if v == nil then v = T(k) end
  return v
end

local TAB_ORDER = { "song", "concert", "stage", "settings" }
local tabs = {}
for _, k in ipairs(TAB_ORDER) do
  tabs[k] = dofile(script_dir .. "ReaCue_tab_" .. k .. ".lua")(ctx)
end
ctx.tabs = tabs

function ctx.goto_tab(t)
  if not tabs[t] then return end
  ctx.tab = t
  ctx.overlay = nil
  reaper.SetExtState("ReaCue", "tab", t, true)
  if tabs[t].enter then tabs[t].enter() end
end

-- projet ouvert : concert (fichier .concert.lua) ou morceau (concert « fictif » d'un seul morceau) -------
local function has_audio()
  for i = 0, (reaper.CountMediaItems and reaper.CountMediaItems(0) or 0) - 1 do
    local it = reaper.GetMediaItem(0, i)
    local tk = it and reaper.GetActiveTake(it)
    if tk and not (reaper.TakeIsMIDI and reaper.TakeIsMIDI(tk)) then return true end
  end
  return false
end

function ctx.refresh(force)
  local proj, fn = reaper.EnumProjects(-1, "")
  fn = fn or ""
  local key = tostring(proj) .. "|" .. fn
  if not force and key == ctx.proj_key then return false end
  local first = ctx.proj_key == nil
  ctx.proj_key = key
  ctx.proj_file = fn
  ctx.proj_name = (fn:match("([^/\\]+)%.[Rr][Pp][Pp]$")) or ""
  local c = L.load_concert()
  ctx.is_concert = c ~= nil
  if c then
    L.publish_prompter(c)
  else
    c = tabs.song.pseudo_concert and tabs.song.pseudo_concert() or nil
  end
  ctx.c = c
  L.mix.song, L.mix.src, L.mix.t = nil, nil, -1e9
  for _, k in ipairs(TAB_ORDER) do if tabs[k].project_changed then tabs[k].project_changed() end end
  -- onglet choisi automatiquement : concert → Scène, morceau → Morceau (sinon le dernier utilisé)
  local want
  if first and START_TAB then want = START_TAB
  elseif ctx.is_concert then want = "stage"
  elseif has_audio() then want = "song"
  else want = ctx.tab or reaper.GetExtState("ReaCue", "tab") end
  if not tabs[want] then want = "concert" end
  if want ~= ctx.tab then ctx.goto_tab(want) end
  return true
end

-- tâches en arrière-plan (CLI ReaCue, séparation de stems) : une à la fois ---------------------
-- on_done(state, message) ; la fenêtre affiche la progression dans l'onglet
function ctx.start_cli(cmd, label, on_done)
  if ctx.job then return false end
  local ok, err = R.start(cmd, script_dir, cmd ~= "concert" and not cmd:match("^concert"))
  if not ok then ctx.show_result(T("error_title"), err, false) return false end
  ctx.job = { kind = "cli", cmd = cmd:match("^(%S+)"), label = label, t0 = reaper.time_precise(), on_done = on_done }
  return true
end

function ctx.start_stems(on_done)
  if ctx.job then return false end
  local job, err = S.start(R, script_dir)
  if not job then ctx.show_result(T("error_title"), err, false) return false end
  if job.ready then
    local msg = S.finish(R, job)
    if on_done then on_done("done", msg) end
    return true
  end
  ctx.job = { kind = "stems", sj = job, label = S.tr(R, "starting"), t0 = reaper.time_precise(), on_done = on_done }
  return true
end

local function poll_job()
  local j = ctx.job
  if not j then return end
  local now = reaper.time_precise()
  if j.kind == "stems" then
    local st, v = S.poll(R, j.sj)
    if st == "running" then
      j.pct = v or 0
      j.label = (v or 0) > 0 and string.format(S.tr(R, "progress"), v) or S.tr(R, "starting")
      return
    end
    ctx.job = nil
    if st == "ready" then
      local msg = S.finish(R, j.sj)
      if j.on_done then j.on_done("done", msg) end
    else
      if j.on_done then j.on_done("error", v) end
    end
    return
  end
  local state, msg, cmd = R.status()
  if (state == "done" or state == "error") and (cmd == nil or cmd == j.cmd) then
    ctx.job = nil
    if j.on_done then j.on_done(state, msg) end
  elseif now - j.t0 > 900 then
    ctx.job = nil
    if j.on_done then j.on_done("error", string.format(R.tr("timeout"), "cli.log")) end
  end
end

-- ligne de progression d'une tâche ; renvoie la hauteur
function ctx.draw_job(x, y, w)
  local j = ctx.job
  if not j then return 0 end
  local el = math.floor(reaper.time_precise() - j.t0)
  U.set(U.BLUE, 0.18); gfx.rect(x, y, w, 30, 1)
  U.set(U.BLUE); gfx.rect(x, y, 4, 30, 1)
  local spin = ({ "|", "/", "-", "\\" })[(math.floor(reaper.time_precise() * 4) % 4) + 1]
  U.text(U.fit(string.format(T("running"), j.label or T("working"), el) .. "  " .. spin, w - 20, 13, true),
    x + 12, y + 8, 13, U.INK, true)
  if j.pct and j.pct > 0 then
    U.set(U.PANEL); gfx.rect(x + 4, y + 26, w - 4, 4, 1)
    U.set(U.ACCENT); gfx.rect(x + 4, y + 26, math.floor((w - 4) * j.pct / 100), 4, 1)
  end
  return 38
end

-- résultat (message de fin d'une tâche) ----------------------------------------------------
function ctx.show_result(title, text, ok)
  ctx.result = { title = title, text = tostring(text or ""), ok = ok ~= false }
  ctx.overlay = "result"
end

local function draw_result(x, y, w)
  local r = ctx.result
  U.text(r.title, x, y, 18, r.ok and U.INK or U.RED, true)
  if U.button("resok", T("ok"), x + w - 90, y - 4, 90, 30, "primary") then ctx.overlay = nil; ctx.result = nil return y + 40 end
  local h = U.para(r.text, x, y + 36, w, 13, U.INK, 34)
  return y + 36 + h + 10
end

-- QR code du prompteur -----------------------------------------------------------------
local QR_W, QR_H = 460, 640
local qr = nil

function ctx.open_qr()
  local ips = L.local_ips()
  local port, found = L.web_port()
  local v = { ips = ips, port = port, found = found, dock = gfx.dock(-1) }
  if #ips > 0 then
    v.url = L.prompter_url(ips[1], port)
    v.m, v.err = L.qr_matrix(v.url, script_dir)
  end
  qr = v
  ctx.overlay = "qr"
  if v.dock > 0 then gfx.dock(0) end
  gfx.init("", QR_W, QR_H)
end

local function close_qr()
  local d = qr and qr.dock or 0
  qr = nil
  ctx.overlay = nil
  if d > 0 then gfx.dock(d) else gfx.init("", ctx.W, gfx.h) end
end

local function draw_qr()
  local w, h = gfx.w, gfx.h
  U.text(L.tr("qr_title"), 18, 14, 18, U.INK, true)
  U.text(L.tr("qr_sub"), 18, 40, 13, U.MUTED)
  if U.button("qrclose", T("close"), w - 104, 12, 90, 30) then close_qr() return end
  local foot, top = 106, 66
  if not qr.url then
    U.text(L.tr("no_ip"), 18, top + 10, 15, U.INK, true)
    U.text(L.tr("no_ip2"), 18, top + 36, 13, U.MUTED)
    U.text(L.tr("no_ip3"), 18, top + 54, 13, U.MUTED)
    return
  end
  if not qr.m then
    U.text(string.format(L.tr("qr_fail"), tostring(qr.err)), 18, top + 10, 13, U.INK)
    return
  end
  local n = #qr.m
  local avail = math.min(w - 28, h - top - foot)
  local mod = math.max(1, math.floor(avail / (n + 8)))
  local size = mod * (n + 8)
  local x0 = math.floor((w - size) / 2)
  local y0 = top
  gfx.set(1, 1, 1, 1); gfx.rect(x0, y0, size, size, 1)
  gfx.set(0, 0, 0, 1)
  for x = 1, n do
    local col = qr.m[x]
    for y = 1, n do
      if col[y] > 0 then gfx.rect(x0 + (x + 3) * mod, y0 + (y + 3) * mod, mod, mod, 1) end
    end
  end
  if U.clicked and U.over(x0, y0, size, size) then close_qr() return end
  local y = y0 + size + 10
  local uw = U.text_w(qr.url, 16, true)
  U.text(qr.url, math.max(10, (w - uw) / 2), y, 16, U.INK, true)
  local note = L.tr("same_wifi")
  if #qr.ips > 1 then note = note .. string.format(L.tr("other_ip"), qr.ips[2]) end
  local nw = U.text_w(note, 13)
  U.text(note, math.max(10, (w - nw) / 2), y + 26, 13, U.MUTED)
  local pin = string.format(L.tr("pin_line"), L.remote_pin())
  local pw = U.text_w(pin, 14, true)
  U.text(pin, math.max(10, (w - pw) / 2), y + 48, 14, U.INK, true)
  if not qr.found then
    local warn = L.tr("no_web")
    local ww = U.text_w(warn, 12)
    U.text(warn, math.max(6, (w - ww) / 2), y + 72, 12, U.WARN)
  end
end

-- contrôle avant concert (« Vérifier ») ---------------------------------------------------
local chk = nil
local CK_COL = { ok = U.ACCENT, warn = U.WARN, bad = U.RED, info = U.GREY }

local function run_checks()
  chk.list = L.run_checks(ctx.is_concert and ctx.c or nil)
  chk.recheck_at = nil
end

function ctx.open_check()
  chk = {}
  ctx.overlay = "check"
  run_checks()
end

local function draw_check(x, y, w)
  U.text(L.tr("check_title"), x, y, 18, U.INK, true)
  if U.button("ckclose", T("close"), x + w - 90, y - 4, 90, 30) then ctx.overlay = nil; chk = nil return y + 30 end
  if U.button("ckagain", L.tr("recheck"), x + w - 90 - 8 - 120, y - 4, 120, 30) then run_checks() end
  if chk.recheck_at and reaper.time_precise() >= chk.recheck_at then run_checks() end
  local bad, warn = L.check_summary(chk.list)
  y = y + 36
  local sum, col
  if bad > 0 then sum, col = string.format(L.tr("n_problems"), bad), CK_COL.bad
  elseif warn > 0 then sum, col = string.format(L.tr("n_warnings"), warn), CK_COL.warn
  else sum, col = L.tr("all_ready") .. "  ✓", CK_COL.ok end
  U.set(col, 0.22); gfx.rect(x, y, w, 34, 1)
  U.set(col); gfx.roundrect(x, y, w - 1, 33, 6, 1)
  U.text(sum, x + 12, y + 8, 16, U.INK, true)
  y = y + 46
  for k, it in ipairs(chk.list) do
    local c = CK_COL[it.status] or U.GREY
    local fx = it.fix and (it.fix ~= "rebuild" or ctx.is_concert) and it.status ~= "ok"
    local tw = w - 26 - (fx and 90 or 4)
    U.set(c); gfx.circle(x + 10, y + 10, 6, 1, 1)
    U.text(U.fit(it.label, tw, 14, true), x + 24, y + 2, 14, U.INK, true)
    U.text(U.fit(it.detail, tw, 12), x + 24, y + 21, 12, it.status == "bad" and U.INK or U.MUTED)
    if fx and U.button("fix" .. k, L.tr("fix"), x + w - 78, y + 6, 78, 26) then
      if it.fix == "rebuild" then ctx.overlay = nil; chk = nil; tabs.stage.rebuild(true) return y
      else L.apply_fix(ctx.c, it.fix); chk.recheck_at = reaper.time_precise() + 0.6 end
    end
    y = y + 42
  end
  return y + 6
end

-- en-tête : titre, onglets, état -------------------------------------------------------------
local function draw_header(w)
  U.set(U.PANEL2); gfx.rect(0, 0, w, 44, 1)
  U.text(T("title"), 14, 12, 17, U.INK, true)
  local x = 14 + U.text_w(T("title"), 17, true) + 14
  local names = T("tabs")
  -- état : pont, interface web (à droite)
  local bridge = R.bridge_alive and R.bridge_alive()
  local _, web = L.web_port()
  local st = {}
  st[#st + 1] = { T("bridge"), bridge }
  st[#st + 1] = { T("web"), web }
  local sx = w - 12
  for k = #st, 1, -1 do
    local lab = st[k][1]
    local lw = U.text_w(lab, 11)
    sx = sx - lw
    U.text(lab, sx, 16, 11, U.MUTED)
    U.set(st[k][2] and U.ACCENT or U.RED); gfx.circle(sx - 8, 22, 3.5, 1, 1)
    sx = sx - 20
  end
  local avail = sx - x - 6
  local tw = math.max(60, math.min(104, math.floor(avail / 4) - 4))
  for _, k in ipairs(TAB_ORDER) do
    if U.button("tab_" .. k, names[k], x, 9, tw, 26, ctx.tab == k and "on" or nil, 13) then ctx.goto_tab(k) end
    x = x + tw + 4
  end
  return 44
end

-- fenêtre ancrée basse : barre compacte ------------------------------------------------------
local function draw_docked()
  if ctx.c and tabs.stage.compact then return tabs.stage.compact() end
  U.text(U.fit(T("title") .. " · " .. ctx.proj_name, gfx.w - 20, 15, true), 14, gfx.h / 2 - 9, 15, U.INK, true)
end

-- tâches de fond (tous onglets) ----------------------------------------------------------------
local CMD_TXT = L.tr("cmd")
local last_alive, last_pos, loop_last = 0, nil, nil
ctx.flash = nil

local function poll_remote(now)
  if now - last_alive > 0.4 then L.remote_alive(now); last_alive = now end
  L.poll_seen(now)
  local cmd, res = L.remote_poll(ctx.c)
  if res and res ~= "dup" then
    if res == "ok" then
      ctx.flash = { txt = string.format(L.tr("phone"), CMD_TXT[cmd] or cmd), t = now }
      last_pos = nil
    elseif res == "badpin" then
      ctx.flash = { txt = L.tr("phone_badpin"), t = now, bad = true }
    end
  end
end

local function background(now)
  ctx.refresh(false)
  poll_job()
  poll_remote(now)
  local c = ctx.c
  if c and L.playing() then
    local p = reaper.GetPlayPosition()
    if L.reh.on then
      if L.loop_tick(loop_last, p) == "restart" then loop_last = nil else loop_last = p end
      last_pos = nil
    elseif ctx.is_concert then
      local k = L.crossed_stop(c, last_pos, p)
      if k then L.after_stop(c, k); last_pos = nil else last_pos = p end
    end
  else
    if L.reh.on and c then L.loop_tick(nil, L.pos()) end
    last_pos, loop_last = nil, nil
  end
  if c then L.mix_tick(c, now) end
  local g = reaper.GetExtState("ReaCue", "win_goto")
  if g ~= "" then
    reaper.SetExtState("ReaCue", "win_goto", "", false)
    if g == "auto" then ctx.refresh(true) else ctx.goto_tab(g) end
  end
  reaper.SetExtState("ReaCue", "win_alive", string.format("%.3f", now), false)
end

function ctx.reset_loop() loop_last = nil; last_pos = nil end

-- boucle ---------------------------------------------------------------------------------------
local dock = tonumber(reaper.GetExtState("ReaCue", "concert_dock")) or 0
gfx.init(T("title"), ctx.W, 420, dock)
reaper.SetExtState("ReaCue", "win_script", SCRIPT, false)
L.remote_pin()
pcall(L.publish_page)
L.publish_reh()

local function loop()
  local ch = gfx.getchar()
  if ch < 0 then return end
  local now = reaper.time_precise()
  if ch == 27 then
    if ctx.overlay == "qr" then close_qr()
    elseif ctx.overlay then ctx.overlay = nil; chk = nil
    else gfx.quit() return end
  end
  U.frame_begin(now)
  background(now)
  if U.right then                                  -- clic droit : ancrer / détacher
    local d = gfx.dock(-1)
    gfx.dock(d > 0 and 0 or 1)
    reaper.SetExtState("ReaCue", "concert_dock", tostring(gfx.dock(-1)), true)
  end
  U.tick_armed()

  ctx.W = gfx.w > 0 and gfx.w or ctx.W
  local w = ctx.W
  U.set(U.BG); gfx.rect(0, 0, gfx.w, gfx.h, 1)
  local docked_low = gfx.dock(-1) > 0 and gfx.h < 130
  if ctx.overlay == "qr" and qr then
    draw_qr()
  elseif docked_low then
    draw_docked()
  else
    local y = draw_header(w) + 12
    if ctx.overlay == "result" and ctx.result then
      y = draw_result(14, y + 4, w - 28)
    elseif ctx.overlay == "check" and chk then
      y = draw_check(14, y + 4, w - 28)
    elseif ctx.overlay and ctx.overlays[ctx.overlay] then
      y = ctx.overlays[ctx.overlay](14, y + 4, w - 28) or y
    else
      y = tabs[ctx.tab].draw(14, y, w - 28) or y
    end
    ctx.layout_h = math.max(160, math.floor(y + 10))
    if gfx.dock(-1) == 0 and math.abs(gfx.h - ctx.layout_h) > 2 then gfx.init("", w, ctx.layout_h) end
  end
  gfx.update()
  reaper.defer(loop)
end

reaper.atexit(function()
  if reaper.set_action_options then reaper.set_action_options(8) end
  if L.reh.on then pcall(L.set_rehearsal, false) end
  reaper.SetExtState("ReaCue", "rehearsal", "", false)
  reaper.SetExtState("ReaCue", "win_alive", "", false)
  reaper.SetExtState("ReaCue", "win_script", "", false)
  L.remote_off()
  reaper.SetExtState("ReaCue", "concert_dock", tostring(gfx.dock(-1)), true)
end)

ctx.refresh(true)
loop()

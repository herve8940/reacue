-- ReaCue - Concert : fenêtre de pilotage d'un concert (plusieurs morceaux dans un seul projet).
-- ReaCue - Concert: control window of a concert (several songs in one project), French / English.
--   · état « 2 / 6 · Demo Song », tempo, tonalité, section, mesure ; Lecture / Pause / Arrêt
--   · progression du morceau (écoulé / durée / reste) et du concert ; morceau suivant
--   · transport : Précédent, Début du morceau, Lecture/Pause, Stop, Suivant
--     (pendant la lecture, Stop / Précédent / Suivant demandent un double appui)
--   · sections du morceau en cours : clic = y aller (pendant la lecture : saut immédiat)
--   · Setlist (clic sur un morceau = aller à son début), QR code du prompteur, code PIN de la Régie
--   · arrêt automatique à la fin de chaque morceau, curseur placé au début du suivant : Espace relance
--   · télécommande « Régie » : les téléphones (rôle Régie du prompteur) pilotent le concert via cette fenêtre
--   · sans concert ouvert : liste des concerts à ouvrir (nouvel onglet, le projet en cours reste ouvert)
--   · « Vérifier » : contrôle avant concert (fichiers, concert à jour, pont, interface web, IP, carte son,
--     sorties du click, prompteur, téléphones Régie), avec « Corriger » quand c'est possible
--   · « Répétition » : arrêt auto coupé, boucle sur une section (ou une plage : 2e section) avec 1 mesure de
--     décompte (click et annonces seuls) avant chaque reprise, ralenti 100 / 90 / 80 / 70 %
-- La fenêtre peut être ancrée (clic droit dans la fenêtre). Fermer la fenêtre arrête l'arrêt automatique
-- et la télécommande.

local script_dir = debug.getinfo(1, "S").source:match("^@?(.*[/\\])") or ""
-- relancer l'action redémarre la fenêtre (pas de question « terminate instances ») ; bouton allumé
if reaper.set_action_options then reaper.set_action_options(1 | 2 | 4) end
local L = dofile(script_dir .. "ReaCue_concert_lib.lua")
local T = L.tr

local TITLE = T("title")
local W = 540
local ROW = 26

local concert, proj_key, songs_open = nil, nil, reaper.GetExtState("ReaCue", "concert_list") ~= "0"
local keys = {}
local secs_cache = { i = nil, t = 0, list = {} }
local available, to_build = nil, nil
local last_pos = nil
local mouse_prev = 0
local rebuild = nil            -- {t0} pendant une reconstruction
local hover = nil
local qr = nil                 -- vue QR : {url, m, ips, port, found, err, dock}
local armed = nil              -- double appui : {id, t}
local flash = nil              -- retour visuel d'une commande distante : {txt, t}
local last_alive = 0
local layout_h = nil           -- hauteur voulue (fenêtre détachée)
local chk = nil                -- vue « Vérifier » : {list, dock, recheck_at}
local loop_last = nil          -- position précédente pour la boucle de répétition

-- couleurs ---------------------------------------------------------------------
local function rgb(r, g, b, a) gfx.set(r / 255, g / 255, b / 255, a or 1) end
local BG = { 29, 29, 31 }
local PANEL = { 44, 44, 48 }
local INK = { 236, 236, 236 }
local MUTED = { 150, 150, 156 }
local ACCENT = { 29, 158, 117 }
local WARN = { 239, 159, 39 }
local GREY = { 120, 120, 126 }
local STATE_COL = { play = ACCENT, pause = WARN, stop = GREY }
local STATE_TXT = T("state")

local function set(c, a) rgb(c[1], c[2], c[3], a) end

local FONT = L.R.is_windows() and "Arial" or "Helvetica"
local function text(s, x, y, size, c, bold)
  gfx.setfont(1, FONT, size, bold and string.byte("b") or 0)
  set(c or INK)
  gfx.x, gfx.y = x, y
  gfx.drawstr(s)
end

local function text_w(s, size, bold)
  gfx.setfont(1, FONT, size, bold and string.byte("b") or 0)
  return gfx.measurestr(s)
end

-- texte coupé à la largeur w (avec « … »)
local function fit(s, w, size, bold)
  if text_w(s, size, bold) <= w then return s end
  while #s > 1 and text_w(s .. "…", size, bold) > w do
    local cut = utf8.offset(s, -1) or #s          -- retire un caractère entier (UTF-8)
    s = s:sub(1, math.max(1, cut - 1))
  end
  return s .. "…"
end

local clicked = nil
local function over_rect(x, y, w, h)
  local mx, my = gfx.mouse_x, gfx.mouse_y
  return mx >= x and mx < x + w and my >= y and my < y + h
end

local function button(id, label, x, y, w, h, primary)
  local over = over_rect(x, y, w, h)
  if over then hover = id end
  if primary then set(ACCENT, over and 1 or 0.85) else set(PANEL, 1) end
  gfx.rect(x, y, w, h, 1)
  if over and not primary then set(INK, 0.08); gfx.rect(x, y, w, h, 1) end
  set(over and INK or MUTED, 0.6); gfx.roundrect(x, y, w - 1, h - 1, 6, 1)
  local size = h < 26 and 13 or 15
  local tw = text_w(label, size)
  text(label, x + (w - tw) / 2, y + (h - size) / 2 - 1, size, INK)
  if over and clicked then return true end
  return false
end

-- icônes dessinées (pas de dépendance aux polices) -----------------------------------
local function tri_right(x, y, s) gfx.triangle(x, y - s, x, y + s, x + s * 1.6, y) end
local function tri_left(x, y, s) gfx.triangle(x + s * 1.6, y - s, x + s * 1.6, y + s, x, y) end

local function icon(kind, cx, cy, s)
  if kind == "play" then tri_right(cx - s * 0.7, cy, s)
  elseif kind == "pause" then gfx.rect(cx - s * 0.9, cy - s, s * 0.65, s * 2, 1); gfx.rect(cx + s * 0.25, cy - s, s * 0.65, s * 2, 1)
  elseif kind == "stop" then gfx.rect(cx - s * 0.85, cy - s * 0.85, s * 1.7, s * 1.7, 1)
  elseif kind == "next" then tri_right(cx - s * 1.3, cy, s * 0.8); tri_right(cx, cy, s * 0.8); gfx.rect(cx + s * 1.3, cy - s * 0.8, s * 0.3, s * 1.6, 1)
  elseif kind == "prev" then gfx.rect(cx - s * 1.6, cy - s * 0.8, s * 0.3, s * 1.6, 1); tri_left(cx - s * 1.3, cy, s * 0.8); tri_left(cx, cy, s * 0.8)
  elseif kind == "home" then gfx.rect(cx - s * 1.2, cy - s, s * 0.3, s * 2, 1); tri_left(cx - s * 0.8, cy, s)
  end
end

-- bouton de transport : icône + libellé ; style : "primary", "armed" ou nil
local function tbutton(id, kind, label, x, y, w, h, style)
  local over = over_rect(x, y, w, h)
  if over then hover = id end
  if style == "armed" then set(WARN, 1)
  elseif style == "primary" then set(ACCENT, over and 1 or 0.85)
  else set(PANEL, 1) end
  gfx.rect(x, y, w, h, 1)
  if over and not style then set(INK, 0.08); gfx.rect(x, y, w, h, 1) end
  set(over and INK or MUTED, 0.6); gfx.roundrect(x, y, w - 1, h - 1, 6, 1)
  local ink = style == "armed" and { 20, 20, 20 } or INK
  local big = h >= 44
  local s = big and math.min(10, h / 6) or math.min(7, h / 4.2)
  set(ink)
  if big then
    icon(kind, x + w / 2, y + h * 0.36, s)
    local lab = style == "armed" and T("again") or label
    local size = w < 80 and 11 or 12
    local lw = text_w(lab, size, style == "armed")
    text(lab, x + (w - lw) / 2, y + h - size - 7, size, ink, style == "armed")
  else
    if style == "armed" then
      local lw = text_w(T("again"), 11, true)
      text(T("again"), x + (w - lw) / 2, y + (h - 11) / 2 - 1, 11, ink, true)
    else
      icon(kind, x + w / 2, y + h / 2, s)
    end
  end
  return over and clicked
end

-- double appui : vrai au 2e appui (dans les 2 s) pendant la lecture, au 1er appui à l'arrêt
local function confirm(id)
  if L.play_state() ~= "play" then armed = nil return true end
  local now = reaper.time_precise()
  if armed and armed.id == id and now - armed.t <= 2 then armed = nil return true end
  armed = { id = id, t = now }
  return false
end

local function armed_style(id, default)
  if armed and armed.id == id and reaper.time_precise() - armed.t <= 2 then return "armed" end
  return default
end

-- données ------------------------------------------------------------------------
local function refresh(force)
  local proj, fn = reaper.EnumProjects(-1, "")
  local key = tostring(proj) .. "|" .. (fn or "")
  if force or key ~= proj_key then
    proj_key = key
    concert = L.load_concert()
    keys = concert and L.song_keys(concert) or {}
    secs_cache = { i = nil, t = 0, list = {} }
    available, to_build = nil, nil
    last_pos = nil
    if concert then L.publish_prompter(concert) end
  end
end

local function sections_of(i)
  local now = reaper.time_precise()
  if secs_cache.i ~= i or now - secs_cache.t > 2 then
    secs_cache = { i = i, t = now, list = L.song_sections(concert, i) }
  end
  return secs_cache.list
end

-- reconstruction (CLI ReaCue, en arrière-plan) -----------------------------------
local SEPC = package.config:sub(1, 1)
local STATUS = reaper.GetResourcePath() .. SEPC .. "ReaCueMCP" .. SEPC .. "cli_status.json"

local function start_rebuild(target)
  local d = target or concert
  if not d or not d.setlist then return end
  if not target then
    local ok = reaper.ShowMessageBox(T("rebuild_q"), TITLE, 1)
    if ok ~= 1 then return end
  end
  os.remove(STATUS)
  local ok, err = L.run_cli("concert", d.setlist)
  if not ok then reaper.ShowMessageBox(err or T("error"), TITLE, 0) return end
  rebuild = { t0 = reaper.time_precise(), rpp = d.rpp, new_tab = target ~= nil }
end

local function poll_rebuild()
  if not rebuild then return end
  local s = L.read(STATUS)
  local state = s and s:match('"state"%s*:%s*"(%a+)"')
  local cmd = s and s:match('"cmd"%s*:%s*"([%w%-]+)"')
  if cmd == "concert" and (state == "done" or state == "error") then
    local rpp, new_tab = rebuild.rpp, rebuild.new_tab
    rebuild = nil
    if state == "done" then
      if new_tab then reaper.Main_OnCommand(40859, 0) end
      reaper.Main_openProject(rpp)
      refresh(true)
    else
      local msg = L.R.jfield(s, "message") or T("error")
      reaper.ShowMessageBox(msg, TITLE, 0)
    end
  elseif reaper.time_precise() - rebuild.t0 > 600 then
    rebuild = nil
  end
end

-- code PIN de la Régie -----------------------------------------------------------------
local function change_pin()
  local ok, v = reaper.GetUserInputs(T("pin_title"), 1,
    T("pin_field") .. ",extrawidth=40", L.remote_pin())
  if not ok then return end
  v = (v or ""):gsub("%s", "")
  if not L.set_remote_pin(v) then
    reaper.ShowMessageBox(T("pin_bad"), TITLE, 0)
  end
end

-- QR code du prompteur ---------------------------------------------------------------
local QR_W, QR_H = 460, 620

local function open_qr()
  local ips = L.local_ips()
  local port, found = L.web_port()
  local v = { ips = ips, port = port, found = found, dock = gfx.dock(-1) }
  if #ips > 0 then
    v.url = L.prompter_url(ips[1], port)
    v.m, v.err = L.qr_matrix(v.url, script_dir)
  end
  qr = v
  if v.dock > 0 then gfx.dock(0) end
  gfx.init("", QR_W, QR_H)
end

local function close_qr()
  local d = qr and qr.dock or 0
  qr = nil
  if d > 0 then gfx.dock(d) end
end

local function draw_qr()
  local w, h = gfx.w, gfx.h
  text(T("qr_title"), 18, 14, 18, INK, true)
  text(T("qr_sub"), 18, 40, 13, MUTED)
  if button("qrclose", T("close"), w - 104, 12, 90, 30) then close_qr() return end
  local foot = 106
  local top = 66
  if not qr.url then
    text(T("no_ip"), 18, top + 10, 15, INK, true)
    text(T("no_ip2"), 18, top + 36, 13, MUTED)
    text(T("no_ip3"), 18, top + 54, 13, MUTED)
    return
  end
  if not qr.m then
    text(string.format(T("qr_fail"), tostring(qr.err)), 18, top + 10, 13, INK)
    return
  end
  -- QR noir sur blanc, marge de 4 modules, le plus grand possible
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
  if clicked and gfx.mouse_x >= x0 and gfx.mouse_x < x0 + size and gfx.mouse_y >= y0 and gfx.mouse_y < y0 + size then
    close_qr() return
  end
  -- adresse en clair + rappels
  local y = y0 + size + 10
  local uw = text_w(qr.url, 16, true)
  text(qr.url, math.max(10, (w - uw) / 2), y, 16, INK, true)
  local note = T("same_wifi")
  if #qr.ips > 1 then note = note .. string.format(T("other_ip"), qr.ips[2]) end
  local nw = text_w(note, 13)
  text(note, math.max(10, (w - nw) / 2), y + 26, 13, MUTED)
  local pin = string.format(T("pin_line"), L.remote_pin())
  local pw = text_w(pin, 14, true)
  text(pin, math.max(10, (w - pw) / 2), y + 48, 14, INK, true)
  if not qr.found then
    local warn = T("no_web")
    local ww = text_w(warn, 12)
    text(warn, math.max(6, (w - ww) / 2), y + 72, 12, WARN)
  end
end

-- contrôle avant concert (« Vérifier ») ---------------------------------------------
local CHK_W = 600
local CK_COL = { ok = ACCENT, warn = WARN, bad = { 226, 75, 74 }, info = GREY }

local function run_checks()
  chk.list = L.run_checks(concert)
  chk.recheck_at = nil
end

local function open_check()
  chk = { dock = gfx.dock(-1) }
  if chk.dock > 0 then gfx.dock(0) end
  gfx.init("", CHK_W, 560)
  run_checks()
end

local function close_check()
  local d = chk and chk.dock or 0
  chk = nil
  if d > 0 then gfx.dock(d) else gfx.init("", 540, gfx.h) end
end

local function draw_check()
  local w = gfx.w
  text(T("check_title"), 18, 14, 18, INK, true)
  if button("ckclose", T("close"), w - 104, 12, 90, 30) then close_check() return end
  if button("ckagain", T("recheck"), w - 104 - 8 - 120, 12, 120, 30) then run_checks() end
  if chk.recheck_at and reaper.time_precise() >= chk.recheck_at then run_checks() end
  local bad, warn = L.check_summary(chk.list)
  local y = 52
  local sum, col
  if bad > 0 then sum, col = string.format(T("n_problems"), bad), CK_COL.bad
  elseif warn > 0 then sum, col = string.format(T("n_warnings"), warn), CK_COL.warn
  else sum, col = T("all_ready") .. "  ✓", CK_COL.ok end
  set(col, 0.22); gfx.rect(14, y, w - 28, 34, 1)
  set(col); gfx.roundrect(14, y, w - 29, 33, 6, 1)
  text(sum, 26, y + 8, 16, INK, true)
  y = y + 46
  for k, x in ipairs(chk.list) do
    local c = CK_COL[x.status] or GREY
    local fx = x.fix and (x.fix ~= "rebuild" or concert) and x.status ~= "ok"
    local tw = w - 40 - (fx and 100 or 14)
    set(c); gfx.circle(24, y + 10, 6, 1, 1)
    text(fit(x.label, tw, 14, true), 38, y + 2, 14, INK, true)
    text(fit(x.detail, tw, 12), 38, y + 21, 12, x.status == "bad" and INK or MUTED)
    if fx and button("fix" .. k, T("fix"), w - 92, y + 6, 78, 26) then
      if x.fix == "rebuild" then close_check(); start_rebuild() return
      else L.apply_fix(concert, x.fix); chk.recheck_at = reaper.time_precise() + 0.6 end
    end
    y = y + 42
  end
  layout_h = y + 10
end

-- état du morceau en cours ---------------------------------------------------------------
local function song_state(c)
  local t = L.pos()
  local i = L.song_index(c, t)
  local s = c.songs[i]
  local secs = sections_of(i)
  local si = L.section_at(secs, t)
  local bar = L.bar_of(s, t)
  return {
    t = t, i = i, s = s, secs = secs, si = si, bar = bar,
    st = L.play_state(),
    dur = s.stop - s.start, el = math.max(0, math.min(t, s.stop) - s.start), rest = math.max(0, s.stop - t),
    total = c.songs[#c.songs].stop, key = keys[i] or nil,
  }
end

local function fmt_bpm(b) return (b % 1 == 0) and string.format("%d", b) or string.format("%.0f", b) end

local function info_line(S)
  local p = { fmt_bpm(S.s.bpm) .. " BPM" }
  if S.key then p[#p + 1] = S.key end
  if S.si then p[#p + 1] = S.secs[S.si].name
  elseif S.t < (S.s.bar1 or S.s.start) and S.t >= S.s.start then p[#p + 1] = T("count_in") end
  if S.bar and S.bar >= 1 and S.bar <= (S.s.bars or 0) then p[#p + 1] = string.format(T("bar"), S.bar, S.s.bars) end
  return table.concat(p, " · ")
end

-- actions communes (fenêtre et télécommande) -------------------------------------------
local function do_prev(c) if confirm("prev") then L.prev(c) end end
local function do_next(c) if confirm("next") then L.next(c) end end
local function do_stop() if confirm("stop") then L.stop() end end

-- pastille d'état
local function state_pill(st, x, y)
  local lab = STATE_TXT[st]
  local w = text_w(lab, 13, true) + 30
  set(STATE_COL[st], 0.22); gfx.rect(x - w, y, w, 24, 1)
  set(STATE_COL[st]); gfx.roundrect(x - w, y, w - 1, 23, 6, 1)
  gfx.circle(x - w + 12, y + 12, 4, 1, 1)
  text(lab, x - w + 22, y + 4, 13, INK, true)
  return w
end

-- fenêtre ancrée (basse) : état à gauche, transport à droite -------------------------------
local function draw_compact(c, S)
  local h = gfx.h
  set(S.s.color and { S.s.color[1], S.s.color[2], S.s.color[3] } or ACCENT)
  gfx.rect(0, 0, 6, h, 1)
  -- transport + QR à droite
  local bh = math.min(34, h - 8)
  local bw, gap = 44, 6
  local x = gfx.w - 5 * (bw + gap) - 50 - 12
  local y = (h - bh) / 2
  if tbutton("prev", "prev", "", x, y, bw, bh, armed_style("prev")) then do_prev(c) end
  if tbutton("home", "home", "", x + (bw + gap), y, bw, bh) then L.song_home(c) end
  if tbutton("play", S.st == "play" and "pause" or "play", "", x + 2 * (bw + gap), y, bw, bh, "primary") then L.toggle_play() end
  if tbutton("stop", "stop", "", x + 3 * (bw + gap), y, bw, bh, armed_style("stop")) then do_stop() end
  if tbutton("next", "next", "", x + 4 * (bw + gap), y, bw, bh, armed_style("next")) then do_next(c) end
  if button("qr", "QR", x + 5 * (bw + gap), y, 50, bh) then open_qr() end
  -- état
  local left_w = x - 26
  set(STATE_COL[S.st]); gfx.circle(20, h / 2 - (h >= 58 and 8 or 0), 5, 1, 1)
  local head = string.format("%d / %d · %s", S.i, #c.songs, S.s.title)
  text(fit(head, left_w - 16, 17, true), 32, h / 2 - (h >= 58 and 17 or 9), 17, INK, true)
  if h >= 58 then
    local sub = (S.si and S.secs[S.si].name or STATE_TXT[S.st]) .. " · " .. string.format(T("rest"), L.fmt_time(S.rest))
    if L.reh.on then sub = T("reh_on") .. " · " .. sub end
    text(fit(sub, left_w - 16, 12), 32, h / 2 + 6, 12, MUTED)
  end
end

-- fenêtre détachée : tout -------------------------------------------------------------------
local function draw_concert()
  local c = concert
  local S = song_state(c)
  if gfx.dock(-1) > 0 and gfx.h < 130 then return draw_compact(c, S) end
  local w = gfx.w
  local s = S.s
  -- bandeau d'état
  set(s.color and { s.color[1], s.color[2], s.color[3] } or ACCENT)
  gfx.rect(0, 0, 6, 64, 1)
  text(string.format("%d / %d", S.i, #c.songs), 18, 10, 13, MUTED)
  local pw = state_pill(S.st, w - 14, 10)
  text(fit(s.title, w - 40 - pw, 22, true), 18, 26, 22, INK, true)
  text(fit(info_line(S), w - 32, 13), 18, 52, 13, MUTED)

  -- progression du morceau
  local y = 76
  set(PANEL); gfx.rect(14, y, w - 28, 8, 1)
  local frac = S.dur > 0 and math.min(1, S.el / S.dur) or 0
  set(s.color and { s.color[1], s.color[2], s.color[3] } or ACCENT)
  gfx.rect(14, y, math.floor((w - 28) * frac), 8, 1)
  text(string.format("%s / %s · ", L.fmt_time(S.el), L.fmt_time(S.dur)) .. string.format(T("rest"), L.fmt_time(S.rest)), 14, y + 13, 12, MUTED)
  local ct = string.format(T("concert_n"), L.fmt_time(math.min(S.t, S.total)), L.fmt_time(S.total))
  text(ct, w - 14 - text_w(ct, 12), y + 13, 12, MUTED)

  -- transport
  y = 112
  local gap = 8
  local bw = (w - 28 - 4 * gap) / 5
  local bh = 56
  if tbutton("prev", "prev", T("prev"), 14, y, bw, bh, armed_style("prev")) then do_prev(c) end
  if tbutton("home", "home", T("home"), 14 + (bw + gap), y, bw, bh) then L.song_home(c) end
  if tbutton("play", S.st == "play" and "pause" or "play", S.st == "play" and T("pause") or T("play"),
      14 + 2 * (bw + gap), y, bw, bh, "primary") then L.toggle_play() end
  if tbutton("stop", "stop", T("stop"), 14 + 3 * (bw + gap), y, bw, bh, armed_style("stop")) then do_stop() end
  if tbutton("next", "next", T("next"), 14 + 4 * (bw + gap), y, bw, bh, armed_style("next")) then do_next(c) end

  -- mode répétition : bandeau, boucle, vitesse
  y = y + bh + 12
  local RH = L.reh
  if RH.on then
    local lp = RH.loop
    set(WARN, 0.2); gfx.rect(14, y, w - 28, 26, 1)
    set(WARN); gfx.rect(14, y, 5, 26, 1)
    local msg = lp and (lp.a == lp.b and string.format(T("reh_loop"), lp.a) or string.format(T("reh_loop_range"), lp.a, lp.b))
      or T("reh_noloop")
    text(fit(T("reh_on") .. "  ·  " .. msg, w - 60, 13, true), 26, y + 6, 13, INK, true)
    y = y + 32
    local bx = 14
    local lw = text_w(T("loop_off"), 13) + 22
    if button("loopoff", T("loop_off"), bx, y, lw, 26) then L.loop_off() end
    bx = bx + lw + 10
    for _, r in ipairs({ 1.0, 0.9, 0.8, 0.7 }) do
      local lab = string.format(T("rate"), math.floor(r * 100 + 0.5))
      if button("rate" .. r, lab, bx, y, 54, 26, math.abs(RH.rate - r) < 0.001) then L.set_rate(r) end
      bx = bx + 58
    end
    local qw = text_w(T("reh_exit"), 13) + 20
    if button("rehexit", T("reh_exit"), w - 14 - qw, y, qw, 26) then L.set_rehearsal(false) end
    y = y + 36
  end

  -- sections du morceau en cours (clic = y aller ; en répétition : boucle)
  text(T("sections"), 14, y, 12, MUTED)
  y = y + 18
  local x = 14
  local ph = 24
  for k, sec in ipairs(S.secs) do
    local lab = sec.name
    local pw2 = text_w(lab, 12) + 16
    if x + pw2 > w - 14 and x > 14 then x = 14; y = y + ph + 6 end
    local col = sec.color or GREY
    local over = over_rect(x, y, pw2, ph)
    set(col, (k == S.si) and 1 or (over and 0.9 or 0.72)); gfx.rect(x, y, pw2, ph, 1)
    if k == S.si then set(INK); gfx.roundrect(x - 2, y - 2, pw2 + 3, ph + 3, 5, 1); gfx.roundrect(x - 1, y - 1, pw2 + 1, ph + 1, 5, 1) end
    local lp = RH.loop
    if lp and sec.start >= lp.start - 0.01 and sec.stop <= lp.stop + 0.01 then
      set(WARN); gfx.rect(x, y + ph - 4, pw2, 4, 1)
    end
    text(lab, x + 8, y + 5, 12, { 16, 16, 18 }, k == S.si)
    if over then hover = "sec" .. k end
    if over and clicked then
      if RH.on then L.loop_tap(c, sec.start); loop_last = nil else L.seek(c, sec.start) end
    end
    x = x + pw2 + 6
  end
  if #S.secs == 0 then text(T("no_regions"), 14, y + 4, 12, MUTED) end
  y = y + ph + 12

  -- ensuite + outils
  local nx = c.songs[S.i + 1]
  local nxt = nx and string.format(T("next_song"), S.i + 1, nx.title, fmt_bpm(nx.bpm), L.fmt_time(nx.stop - nx.start))
    or T("last_song")
  text(fit(nxt, w - 28, 13), 14, y, 13, INK)
  y = y + 22
  local lab = rebuild and string.format(T("rebuilding"), math.floor(reaper.time_precise() - rebuild.t0))
    or (RH.on and T("auto_off") or T("auto_stop"))
  set((rebuild or RH.on) and WARN or ACCENT); gfx.circle(20, y + 7, 4, 1, 1)
  text(lab, 30, y, 12, MUTED)
  if flash and reaper.time_precise() - flash.t < 2.5 then
    text(flash.txt, 30 + text_w(lab, 12) + 14, y, 12, flash.bad and WARN or ACCENT, true)
  end
  y = y + 20
  local tb = 26
  local bx = w - 14
  bx = bx - 50; if button("qr", "QR", bx, y, 50, tb) then open_qr() end
  local pinlab = string.format(T("pin_btn"), L.remote_pin())
  local pinw = text_w(pinlab, 13) + 18
  bx = bx - 6 - pinw; if button("pin", pinlab, bx, y, pinw, tb) then change_pin() end
  local slab = T("setlist") .. (songs_open and "  −" or "  +")
  local sw = text_w(slab, 13) + 20
  bx = bx - 6 - sw
  if button("list", slab, bx, y, sw, tb) then
    songs_open = not songs_open
    reaper.SetExtState("ReaCue", "concert_list", songs_open and "1" or "0", true)
  end
  local rw = text_w(T("reh"), 13) + 20
  bx = bx - 6 - rw
  if button("reh", T("reh"), bx, y, rw, tb, RH.on) then L.set_rehearsal(not RH.on); loop_last = nil end
  local cw = text_w(T("check"), 13) + 20
  bx = bx - 6 - cw
  if button("check", T("check"), bx, y, cw, tb) then open_check() return end
  y = y + tb + 10

  -- setlist
  if songs_open then
    for k, so in ipairs(c.songs) do
      local yy = y + (k - 1) * ROW
      local over = gfx.mouse_y >= yy and gfx.mouse_y < yy + ROW and gfx.mouse_x >= 0 and gfx.mouse_x < w
      if k == S.i then set(PANEL); gfx.rect(10, yy, w - 20, ROW - 2, 1) end
      if over then set(INK, 0.06); gfx.rect(10, yy, w - 20, ROW - 2, 1) end
      set({ so.color[1], so.color[2], so.color[3] }); gfx.rect(10, yy + 4, 4, ROW - 10, 1)
      text(string.format("%d", k), 22, yy + 5, 14, MUTED)
      text(so.title, 44, yy + 4, 15, k == S.i and INK or { 210, 210, 214 }, k == S.i)
      local right = string.format("%.0f BPM   %s", so.bpm, L.fmt_time(so.stop - so.start))
      local rw = text_w(right, 13)
      text(right, w - rw - 18, yy + 6, 13, MUTED)
      if over and clicked and confirm("song" .. k) then L.goto_song(c, k) end
      if armed and armed.id == "song" .. k and reaper.time_precise() - armed.t <= 2 then
        text(T("again"), w - rw - 90, yy + 6, 12, WARN, true)
      end
    end
    local yb = y + #c.songs * ROW + 6
    if button("rebuild", T("rebuild"), w - 214, yb, 200, 24) and not rebuild then start_rebuild() end
    y = yb + 34
  end
  layout_h = y
end

local function draw_empty()
  if not available then available, to_build = L.list_concerts(), L.list_setlists() end
  text(T("none"), 18, 14, 18, INK, true)
  if button("qr", "QR", W - 70, 10, 56, 28) then open_qr() return end
  local cw = text_w(T("check"), 13) + 20
  if button("check", T("check"), W - 70 - 8 - cw, 10, cw, 28) then open_check() return end
  if rebuild then
    text(string.format(T("building"), math.floor(reaper.time_precise() - rebuild.t0)), 18, 42, 13, MUTED)
    layout_h = 110
    return
  end
  text(T("open_one"), 18, 42, 13, MUTED)
  local y0 = 70
  if #available == 0 and #to_build == 0 then
    text(string.format(T("none_in"), L.concert_dir()), 18, y0 + 4, 13, MUTED)
    text(T("ask_claude"), 18, y0 + 24, 13, MUTED)
    layout_h = 140
    return
  end
  for k, d in ipairs(available) do
    local yy = y0 + (k - 1) * ROW
    local n = #d.songs
    if button("open" .. k, string.format(T("n_songs"), d.name, n), 14, yy, W - 28, ROW - 4) then
      L.open_concert(d)
      refresh(true)
    end
  end
  local yb = y0 + #available * ROW + 4
  if #to_build > 0 then
    text(T("to_build"), 18, yb, 13, MUTED)
    for k, d in ipairs(to_build) do
      local yy = yb + 20 + (k - 1) * ROW
      if button("build" .. k, string.format(T("build"), d.name), 14, yy, W - 28, ROW - 4) then start_rebuild(d) end
    end
    yb = yb + 20 + #to_build * ROW
  end
  layout_h = math.max(110, yb + 14)
end

-- télécommande (téléphones) ---------------------------------------------------------------
local CMD_TXT = T("cmd")

local function poll_remote()
  local now = reaper.time_precise()
  if now - last_alive > 0.4 then L.remote_alive(now); last_alive = now end
  L.poll_seen(now)
  local cmd, res = L.remote_poll(concert)
  if res and res ~= "dup" then
    if res == "ok" then
      flash = { txt = string.format(T("phone"), CMD_TXT[cmd] or cmd), t = now }
      last_pos = nil
    elseif res == "badpin" then
      flash = { txt = T("phone_badpin"), t = now, bad = true }
    end
  end
end

-- boucle ---------------------------------------------------------------------------
local dock = tonumber(reaper.GetExtState("ReaCue", "concert_dock")) or 0
gfx.init(TITLE, W, 300, dock)
L.remote_pin()
pcall(L.publish_page)
L.publish_reh()

local function loop()
  local ch = gfx.getchar()
  if ch < 0 then return end
  if ch == 27 then
    if qr then close_qr() elseif chk then close_check() else gfx.quit() return end
  end
  refresh(false)
  poll_rebuild()
  poll_remote()

  -- arrêt automatique en fin de morceau (coupé en répétition) ; boucle de répétition
  if concert and L.playing() then
    local p = reaper.GetPlayPosition()
    if L.reh.on then
      if L.loop_tick(loop_last, p) == "restart" then loop_last = nil else loop_last = p end
      last_pos = nil
    else
      local k = L.crossed_stop(concert, last_pos, p)
      if k then L.after_stop(concert, k); last_pos = nil else last_pos = p end
    end
  else
    if L.reh.on then L.loop_tick(nil, L.pos()) end
    last_pos, loop_last = nil, nil
  end

  -- souris (clic à l'appui, plus réactif)
  local cap = gfx.mouse_cap
  clicked = (cap & 1) == 1 and (mouse_prev & 1) == 0
  if (cap & 2) == 2 and (mouse_prev & 2) == 0 then   -- clic droit : ancrer / détacher
    local d = gfx.dock(-1)
    gfx.dock(d > 0 and 0 or 1)
    reaper.SetExtState("ReaCue", "concert_dock", tostring(gfx.dock(-1)), true)
  end
  mouse_prev = cap
  hover = nil
  if armed and reaper.time_precise() - armed.t > 2 then armed = nil end

  W = gfx.w > 0 and gfx.w or W
  set(BG); gfx.rect(0, 0, gfx.w, gfx.h, 1)
  if qr then draw_qr()
  elseif chk then draw_check()
  elseif concert then draw_concert() else draw_empty() end
  local h = qr and QR_H or layout_h
  if h and not qr and gfx.dock(-1) == 0 and math.abs(gfx.h - h) > 2 then gfx.init("", W, h) end
  gfx.update()
  reaper.defer(loop)
end

reaper.atexit(function()
  if reaper.set_action_options then reaper.set_action_options(8) end
  if L.reh.on then pcall(L.set_rehearsal, false) end
  reaper.SetExtState("ReaCue", "rehearsal", "", false)
  L.remote_off()
  local d = gfx.dock(-1)
  reaper.SetExtState("ReaCue", "concert_dock", tostring(d), true)
end)
loop()

-- ReaCue : éléments d'interface de la fenêtre ReaCue (gfx) : couleurs, textes, boutons, icônes,
-- double appui, appui long. Aucun accès au projet ici.
-- ReaCue: UI kit of the ReaCue window (gfx): colours, text, buttons, icons, double tap, long press.

local U = {}

U.BG = { 29, 29, 31 }
U.PANEL = { 44, 44, 48 }
U.PANEL2 = { 36, 36, 40 }
U.INK = { 236, 236, 236 }
U.MUTED = { 150, 150, 156 }
U.ACCENT = { 29, 158, 117 }
U.BLUE = { 55, 138, 221 }
U.WARN = { 239, 159, 39 }
U.RED = { 226, 75, 74 }
U.GREY = { 120, 120, 126 }
U.DARK = { 16, 16, 18 }

U.FONT = "Helvetica"
function U.init(is_windows) U.FONT = is_windows and "Arial" or "Helvetica" end

function U.rgb(r, g, b, a) gfx.set(r / 255, g / 255, b / 255, a or 1) end
function U.set(c, a) U.rgb(c[1], c[2], c[3], a) end

function U.text(s, x, y, size, c, bold)
  gfx.setfont(1, U.FONT, size, bold and string.byte("b") or 0)
  U.set(c or U.INK)
  gfx.x, gfx.y = x, y
  gfx.drawstr(s)
end

function U.text_w(s, size, bold)
  gfx.setfont(1, U.FONT, size, bold and string.byte("b") or 0)
  return (gfx.measurestr(s))
end

-- texte coupé à la largeur w (avec « … »), sans couper un caractère UTF-8
-- chemin trop long : début remplacé par « … » (la fin, le dossier, reste lisible) ; prefix gardé en entier
function U.fit_path(prefix, path, w, size, bold)
  prefix, path = tostring(prefix or ""), tostring(path or "")
  if U.text_w(prefix .. path, size, bold) <= w then return prefix .. path end
  while #path > 1 and U.text_w(prefix .. "…" .. path, size, bold) > w do
    path = path:sub((utf8.offset(path, 2) or 2))
  end
  return prefix .. "…" .. path
end

-- U.on_cut(s) : appelé quand un texte est coupé (tests : aucun libellé coupé dans les captures)
function U.fit(s, w, size, bold)
  s = tostring(s or "")
  if U.text_w(s, size, bold) <= w then return s end
  if U.on_cut then U.on_cut(s) end
  while #s > 1 and U.text_w(s .. "…", size, bold) > w do
    local cut = utf8.offset(s, -1) or #s
    s = s:sub(1, math.max(1, cut - 1))
  end
  return s .. "…"
end

-- souris ------------------------------------------------------------------------------
-- clicked : appui gauche (front montant) ; released : relâchement ; long_id : appui long en cours déclenché
U.clicked, U.released, U.right = false, false, false
U.hover = nil
local prev_cap = 0
local press = nil            -- {id, t, fired}

function U.frame_begin(now)
  local cap = gfx.mouse_cap or 0
  U.clicked = (cap & 1) == 1 and (prev_cap & 1) == 0
  U.released = (cap & 1) == 0 and (prev_cap & 1) == 1
  U.right = (cap & 2) == 2 and (prev_cap & 2) == 0
  U.down = (cap & 1) == 1
  prev_cap = cap
  U.hover = nil
  U.hover_tip = nil
  U.now = now or (reaper.time_precise and reaper.time_precise() or 0)
  U.wheel = gfx.mouse_wheel or 0
  gfx.mouse_wheel = 0
end

function U.over(x, y, w, h)
  local mx, my = gfx.mouse_x, gfx.mouse_y
  return mx >= x and mx < x + w and my >= y and my < y + h
end

-- bouton ; style : nil, "primary", "on" (bascule active), "warn", "armed", "ghost"
function U.button(id, label, x, y, w, h, style, size)
  local over = U.over(x, y, w, h)
  if over then U.hover = id end
  if style == "primary" or style == true then U.set(U.ACCENT, over and 1 or 0.85)
  elseif style == "on" then U.set(U.BLUE, over and 0.95 or 0.8)
  elseif style == "warn" or style == "armed" then U.set(U.WARN, 1)
  elseif style == "ghost" then U.set(U.BG, 1)
  else U.set(U.PANEL, 1) end
  gfx.rect(x, y, w, h, 1)
  if over and (style == nil or style == "ghost") then U.set(U.INK, 0.08); gfx.rect(x, y, w, h, 1) end
  U.set(over and U.INK or U.MUTED, 0.6); gfx.roundrect(x, y, w - 1, h - 1, 6, 1)
  size = size or (h <= 28 and 13 or 15)
  local ink = (style == "warn" or style == "armed") and { 20, 20, 20 } or U.INK
  label = U.fit(label, w - 10, size)
  local tw = U.text_w(label, size)
  U.text(label, x + (w - tw) / 2, y + (h - size) / 2 - 1, size, ink)
  return over and U.clicked
end

-- bouton à appui court / appui long : renvoie "click" (relâché avant 0,6 s) ou "long" (une fois)
function U.press_button(id, label, x, y, w, h, col, dim, sub)
  local over = U.over(x, y, w, h)
  if over then U.hover = id end
  if over and U.clicked then press = { id = id, t = U.now, fired = false } end
  local res = nil
  if press and press.id == id then
    if U.down and not press.fired and U.now - press.t >= 0.6 then press.fired = true; res = "long" end
    if U.released then
      if not press.fired and over then res = "click" end
      press = nil
    end
  end
  U.set(col, dim and 0.25 or (over and 1 or 0.85)); gfx.rect(x, y, w, h, 1)
  U.set(over and U.INK or U.MUTED, dim and 0.35 or 0.6); gfx.roundrect(x, y, w - 1, h - 1, 6, 1)
  local ink = dim and U.MUTED or U.DARK
  local lab = U.fit(label, w - 8, 13, not dim)
  local lw = U.text_w(lab, 13, not dim)
  U.text(lab, x + (w - lw) / 2, y + (sub and 5 or (h - 13) / 2 - 1), 13, ink, not dim)
  if sub then
    local s2 = U.fit(sub, w - 6, 11)
    local sw = U.text_w(s2, 11)
    U.text(s2, x + (w - sw) / 2, y + h - 16, 11, ink)
  end
  if dim then U.set(U.MUTED, 0.8); gfx.line(x + 6, y + h / 2, x + w - 7, y + h / 2) end
  return res
end

-- icônes dessinées (pas de dépendance aux polices) -----------------------------------
local function tri_right(x, y, s) gfx.triangle(x, y - s, x, y + s, x + s * 1.6, y) end
local function tri_left(x, y, s) gfx.triangle(x + s * 1.6, y - s, x + s * 1.6, y + s, x, y) end

function U.icon(kind, cx, cy, s)
  if kind == "play" then tri_right(cx - s * 0.7, cy, s)
  elseif kind == "pause" then gfx.rect(cx - s * 0.9, cy - s, s * 0.65, s * 2, 1); gfx.rect(cx + s * 0.25, cy - s, s * 0.65, s * 2, 1)
  elseif kind == "stop" then gfx.rect(cx - s * 0.85, cy - s * 0.85, s * 1.7, s * 1.7, 1)
  elseif kind == "next" then tri_right(cx - s * 1.3, cy, s * 0.8); tri_right(cx, cy, s * 0.8); gfx.rect(cx + s * 1.3, cy - s * 0.8, s * 0.3, s * 1.6, 1)
  elseif kind == "prev" then gfx.rect(cx - s * 1.6, cy - s * 0.8, s * 0.3, s * 1.6, 1); tri_left(cx - s * 1.3, cy, s * 0.8); tri_left(cx, cy, s * 0.8)
  elseif kind == "home" then gfx.rect(cx - s * 1.2, cy - s, s * 0.3, s * 2, 1); tri_left(cx - s * 0.8, cy, s)
  elseif kind == "up" then gfx.triangle(cx - s, cy + s * 0.5, cx + s, cy + s * 0.5, cx, cy - s * 0.7)
  elseif kind == "down" then gfx.triangle(cx - s, cy - s * 0.5, cx + s, cy - s * 0.5, cx, cy + s * 0.7)
  elseif kind == "left" then gfx.triangle(cx + s * 0.5, cy - s, cx + s * 0.5, cy + s, cx - s * 0.7, cy)
  elseif kind == "right" then gfx.triangle(cx - s * 0.5, cy - s, cx - s * 0.5, cy + s, cx + s * 0.7, cy)
  elseif kind == "x" then
    for d = -1, 1 do gfx.line(cx - s + d, cy - s, cx + s + d, cy + s); gfx.line(cx - s + d, cy + s, cx + s + d, cy - s) end
  elseif kind == "plus" then gfx.rect(cx - s, cy - 1, s * 2, 3, 1); gfx.rect(cx - 1, cy - s, 3, s * 2, 1)
  end
end

-- petit bouton carré à icône
function U.ibutton(id, kind, x, y, w, h, style)
  local over = U.over(x, y, w, h)
  if over then U.hover = id end
  if style == "warn" then U.set(U.WARN, 1) else U.set(U.PANEL, 1) end
  gfx.rect(x, y, w, h, 1)
  if over then U.set(U.INK, 0.1); gfx.rect(x, y, w, h, 1) end
  U.set(over and U.INK or U.MUTED, 0.5); gfx.roundrect(x, y, w - 1, h - 1, 5, 1)
  U.set(style == "warn" and { 20, 20, 20 } or U.INK)
  U.icon(kind, x + w / 2, y + h / 2, math.min(w, h) / 4.5)
  return over and U.clicked
end

-- bouton de transport : icône + libellé ; style : "primary", "armed" ou nil
function U.tbutton(id, kind, label, x, y, w, h, style, again)
  local over = U.over(x, y, w, h)
  if over then U.hover = id end
  if style == "armed" then U.set(U.WARN, 1)
  elseif style == "primary" then U.set(U.ACCENT, over and 1 or 0.85)
  else U.set(U.PANEL, 1) end
  gfx.rect(x, y, w, h, 1)
  if over and not style then U.set(U.INK, 0.08); gfx.rect(x, y, w, h, 1) end
  U.set(over and U.INK or U.MUTED, 0.6); gfx.roundrect(x, y, w - 1, h - 1, 6, 1)
  local ink = style == "armed" and { 20, 20, 20 } or U.INK
  local big = h >= 44
  local s = big and math.min(10, h / 6) or math.min(7, h / 4.2)
  U.set(ink)
  if big then
    U.icon(kind, x + w / 2, y + h * 0.36, s)
    local lab = style == "armed" and again or label
    local size = w < 80 and 11 or 12
    local lw = U.text_w(lab, size, style == "armed")
    U.text(lab, x + (w - lw) / 2, y + h - size - 7, size, ink, style == "armed")
  else
    if style == "armed" then
      local lw = U.text_w(again, 11, true)
      U.text(again, x + (w - lw) / 2, y + (h - 11) / 2 - 1, 11, ink, true)
    else
      U.icon(kind, x + w / 2, y + h / 2, s)
    end
  end
  return over and U.clicked
end

-- double appui (pendant la lecture) -------------------------------------------------------
U.armed = nil
-- vrai au 2e appui dans les 2 s si need, sinon tout de suite
function U.confirm(id, need)
  if not need then U.armed = nil return true end
  if U.armed and U.armed.id == id and U.now - U.armed.t <= 2 then U.armed = nil return true end
  U.armed = { id = id, t = U.now }
  return false
end

function U.is_armed(id) return U.armed ~= nil and U.armed.id == id and U.now - U.armed.t <= 2 end
function U.armed_style(id, default) if U.is_armed(id) then return "armed" end return default end
function U.tick_armed() if U.armed and U.now - U.armed.t > 2 then U.armed = nil end end

-- pastille d'état (alignée à droite sur x)
function U.pill(lab, col, x, y)
  local w = U.text_w(lab, 13, true) + 30
  U.set(col, 0.22); gfx.rect(x - w, y, w, 24, 1)
  U.set(col); gfx.roundrect(x - w, y, w - 1, 23, 6, 1)
  gfx.circle(x - w + 12, y + 12, 4, 1, 1)
  U.text(lab, x - w + 22, y + 4, 13, U.INK, true)
  return w
end

-- pastille cliquable (état du morceau) : ok = vert, false = gris, "warn" = orange ; renvoie largeur, clic
function U.chip(id, lab, ok, x, y, size)
  size = size or 12
  local w = U.text_w(lab, size, true) + 26
  local h = size + 12
  local over = U.over(x, y, w, h)
  if over then U.hover = id end
  local col = ok == true and U.ACCENT or (ok == "warn" and U.WARN or U.GREY)
  U.set(col, over and 0.34 or 0.2); gfx.rect(x, y, w, h, 1)
  U.set(col, over and 1 or 0.8); gfx.roundrect(x, y, w - 1, h - 1, 6, 1)
  gfx.circle(x + 10, y + h / 2, 3.5, 1, 1)
  U.text(lab, x + 18, y + 6, size, ok == true and U.INK or { 205, 205, 210 }, true)
  return w, over and U.clicked
end

-- aide au survol d'une zone sans bouton (bande de structure, lignes)
function U.tip(x, y, w, h, text, id)
  if U.over(x, y, w, h) then
    U.hover_tip = text
    if id then U.hover = id end
    return true
  end
  return false
end

-- titre de bloc (« 1. Préparer »)
function U.heading(s, x, y) U.text(s, x, y, 12, U.MUTED) end

-- texte sur plusieurs lignes, coupé à la largeur w ; renvoie la hauteur utilisée
function U.para(s, x, y, w, size, col, max_lines)
  size = size or 13
  local lh = size + 5
  local n = 0
  for line in (tostring(s or "") .. "\n"):gmatch("(.-)\n") do
    local words, cur = {}, ""
    for word in line:gmatch("%S+") do
      -- ponctuation française : « » : ; ! ? jamais seuls en début ou en fin de ligne
      local prev = words[#words]
      if prev and (word:sub(1, 2) == "»" or word:match("^[:;!?%)]") or prev:sub(-2) == "«" or prev:sub(-1) == "(") then
        words[#words] = words[#words] .. " " .. word
      else
        words[#words + 1] = word
      end
    end
    if #words == 0 then n = n + 1 end
    for _, wd in ipairs(words) do
      local try = cur == "" and wd or (cur .. " " .. wd)
      if U.text_w(try, size) > w and cur ~= "" then
        if not max_lines or n < max_lines then U.text(cur, x, y + n * lh, size, col) end
        n = n + 1
        cur = wd
      else
        cur = try
      end
    end
    if cur ~= "" then
      if not max_lines or n < max_lines then U.text(cur, x, y + n * lh, size, col) end
      n = n + 1
    end
  end
  if max_lines and n > max_lines then
    if U.on_cut then U.on_cut(s) end
    n = max_lines
  end
  return n * lh
end

return U

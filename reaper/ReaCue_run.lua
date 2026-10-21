-- ReaCue : lance le programme ReaCue (Python) depuis REAPER, sans Claude ni internet.
-- Code commun aux actions « ReaCue - Préparer le morceau » et « ReaCue - Republier le prompteur ».
-- Le pont ReaCue_Bridge.lua doit tourner (il est lancé au démarrage de REAPER).
--
-- Dossier d'installation de ReaCue (là où se trouvent .venv et reacue_mcp), dans l'ordre :
--   1. ExtState "ReaCue"/"install_dir" (réglage manuel, persistant) ;
--   2. <ressources REAPER>/ReaCueMCP/reacue_install.txt (écrit par l'installateur) ;
--   3. dossier parent de ce script s'il contient reacue_mcp (script lancé depuis <installation>/reaper) ;
--   4. ~/Documents/reacue-mcp (anciennes installations macOS).
--
-- Lancement en arrière-plan :
--   macOS / Linux : os.execute("cd … && nohup <python> -m reacue_mcp.cli … &") (comme avant) ;
--   Windows       : reaper.ExecProcess(<pythonw.exe> <reacue_cli.py> …, -1) : -1 = ne pas attendre.
--                   ExecProcess lance le programme directement (pas de cmd.exe, pas de fenêtre console
--                   avec pythonw.exe) et reçoit la ligne de commande en UTF-8 : les chemins avec espaces
--                   ou accents passent, contrairement à os.execute (page de code ANSI de cmd.exe).

local M = {}
local SEP = package.config:sub(1, 1)
local RES_DIR = reaper.GetResourcePath()
local DIR = RES_DIR .. SEP .. "ReaCueMCP"
local STATUS = DIR .. SEP .. "cli_status.json"
local HEARTBEAT = DIR .. SEP .. "heartbeat.txt"
local SETTINGS = DIR .. SEP .. "reacue_settings.json"
local INSTALL_TXT = DIR .. SEP .. "reacue_install.txt"
local TITLE = "ReaCue"

local function is_windows()
  local os_name = reaper.GetOS and reaper.GetOS() or ""
  return os_name:match("^Win") ~= nil or SEP == "\\"
end
M.is_windows = is_windows

local function read(path)
  local f = io.open(path, "rb"); if not f then return nil end
  local s = f:read("*a"); f:close(); return s
end

local function exists(path) local f = io.open(path, "rb"); if f then f:close() return true end return false end

-- JSON : lecture d'un champ chaîne ou nombre (fichiers écrits par Python json.dumps) ------------
local function utf8_char(c)
  if c < 0x80 then return string.char(c) end
  if c < 0x800 then return string.char(0xC0 | (c >> 6), 0x80 | (c & 0x3F)) end
  if c < 0x10000 then return string.char(0xE0 | (c >> 12), 0x80 | ((c >> 6) & 0x3F), 0x80 | (c & 0x3F)) end
  return string.char(0xF0 | (c >> 18), 0x80 | ((c >> 12) & 0x3F), 0x80 | ((c >> 6) & 0x3F), 0x80 | (c & 0x3F))
end

-- décode la chaîne JSON qui commence au guillemet d'indice i ; renvoie (valeur, indice après)
local function json_string(s, i)
  local out, j, n = {}, i + 1, #s
  local esc = { n = "\n", r = "\r", t = "\t", b = "\b", f = "\f", ['"'] = '"', ["\\"] = "\\", ["/"] = "/" }
  while j <= n do
    local c = s:sub(j, j)
    if c == '"' then return table.concat(out), j + 1 end
    if c == "\\" then
      local e = s:sub(j + 1, j + 1)
      if e == "u" then
        local cp = tonumber(s:sub(j + 2, j + 5), 16) or 63
        j = j + 6
        if cp >= 0xD800 and cp <= 0xDBFF and s:sub(j, j + 1) == "\\u" then   -- paire de substitution
          local lo = tonumber(s:sub(j + 2, j + 5), 16)
          if lo and lo >= 0xDC00 and lo <= 0xDFFF then
            cp = 0x10000 + ((cp - 0xD800) << 10) + (lo - 0xDC00)
            j = j + 6
          end
        end
        out[#out + 1] = utf8_char(cp)
      else
        out[#out + 1] = esc[e] or e
        j = j + 2
      end
    else
      out[#out + 1] = c
      j = j + 1
    end
  end
  return nil
end

-- valeur du champ `key` (premier niveau) : chaîne, nombre, booléen ; nil si absent
local function jfield(s, key)
  if not s then return nil end
  local pat = '"' .. key:gsub("%p", "%%%0") .. '"%s*:%s*()'
  local p = s:match(pat)
  if not p then return nil end
  local c = s:sub(p, p)
  if c == '"' then return (json_string(s, p)) end
  local num = s:match("^%-?%d+%.?%d*[eE]?[%+%-]?%d*", p)
  if num and num ~= "" then return tonumber(num) end
  if s:sub(p, p + 3) == "true" then return true end
  if s:sub(p, p + 4) == "false" then return false end
  return nil
end
M.jfield = jfield

-- Langue ------------------------------------------------------------------------
local TXT = {
  fr = {
    prepare = "Préparation du morceau en cours",
    publish = "Mise à jour du prompteur",
    not_found = "Programme ReaCue introuvable :\n%s\n\nRelance l'installation de ReaCue, ou indique son dossier avec :\nreaper.SetExtState(\"ReaCue\", \"install_dir\", \"<dossier>\", true)",
    no_bridge = "Le pont ReaCue ne tourne pas dans REAPER.\nLance l'action « ReaCue_Bridge.lua » (ou redémarre REAPER) puis recommence.",
    busy = "Une préparation est déjà en cours. Attends qu'elle se termine.",
    launch_failed = "Impossible de lancer ReaCue :\n%s",
    done = "Terminé.", error = "Erreur.",
    timeout = "Pas de réponse après 15 min : voir %s",
    hint = "%d s  ·  tu peux fermer cette fenêtre, le résultat s'affichera à la fin",
  },
  en = {
    prepare = "Preparing the song",
    publish = "Updating the prompter",
    not_found = "ReaCue program not found:\n%s\n\nRun the ReaCue installer again, or set its folder with:\nreaper.SetExtState(\"ReaCue\", \"install_dir\", \"<folder>\", true)",
    no_bridge = "The ReaCue bridge is not running in REAPER.\nRun the “ReaCue_Bridge.lua” action (or restart REAPER) and try again.",
    busy = "A preparation is already running. Wait until it finishes.",
    launch_failed = "Could not start ReaCue:\n%s",
    done = "Done.", error = "Error.",
    timeout = "No answer after 15 min: see %s",
    hint = "%d s  ·  you can close this window, the result will show at the end",
  },
}

function M.lang()
  local l = jfield(read(SETTINGS), "language")
  l = type(l) == "string" and l:sub(1, 2):lower() or "fr"
  return TXT[l] and l or "fr"
end

function M.tr(key)
  return TXT[M.lang()][key] or TXT.fr[key]
end

-- Installation --------------------------------------------------------------------
local function trim(s) return (s or ""):gsub("^%s+", ""):gsub("%s+$", "") end

function M.install_dir(script_dir)
  local d = reaper.GetExtState("ReaCue", "install_dir")
  if d ~= "" then return d end
  local t = trim(read(INSTALL_TXT))
  if t ~= "" then return (t:gsub("[/\\]+$", "")) end
  if script_dir then
    local parent = script_dir:match("^(.*)[/\\][^/\\]+$")
    if parent and exists(parent .. SEP .. "reacue_mcp" .. SEP .. "cli.py") then return parent end
  end
  return (os.getenv("HOME") or os.getenv("USERPROFILE") or "") .. SEP .. "Documents" .. SEP .. "reacue-mcp"
end

function M.python(dir, windows)
  if windows then
    local pyw = dir .. "\\.venv\\Scripts\\pythonw.exe"
    if exists(pyw) then return pyw end
    return dir .. "\\.venv\\Scripts\\python.exe"
  end
  return dir .. "/.venv/bin/python"
end

-- guillemets shell POSIX : 'a'\''b'
function M.shq(s) return "'" .. tostring(s):gsub("'", "'\\''") .. "'" end

-- ligne de commande Windows (règles de CommandLineToArgvW ; un chemin Windows ne contient pas de ")
function M.winq(s)
  s = tostring(s)
  if s:find('[%s"]') or s == "" then
    s = s:gsub("(\\*)$", "%1%1")          -- barres obliques inverses finales doublées avant le "
    return '"' .. s .. '"'
  end
  return s
end

function M.command(cmd, dir, py, windows, log)
  if windows then
    return table.concat({ M.winq(py), M.winq(dir .. "\\reacue_cli.py"), cmd, "--resource-dir", M.winq(RES_DIR) }, " ")
  end
  return string.format("cd %s && nohup %s -m reacue_mcp.cli %s --resource-dir %s >> %s 2>&1 &",
    M.shq(dir), M.shq(py), cmd, M.shq(RES_DIR), M.shq(log))
end

local function bridge_alive()
  local s = read(HEARTBEAT); if not s then return false end
  local t = tonumber(s:match("[%d%.]+"))
  if t and math.abs(os.time() - t) < 15 then return true end
  -- heartbeat sans horodatage lisible : on se fie à sa présence
  return t == nil
end

function M.run(cmd, label, script_dir)
  label = (label and label ~= "") and label or M.tr(cmd)
  local windows = is_windows()
  local dir = M.install_dir(script_dir)
  local py = M.python(dir, windows)
  if not exists(py) then
    reaper.ShowMessageBox(string.format(M.tr("not_found"), py), TITLE, 0)
    return
  end
  if not bridge_alive() then
    reaper.ShowMessageBox(M.tr("no_bridge"), TITLE, 0)
    return
  end
  local st = read(STATUS)
  if st and jfield(st, "state") == "running" and os.time() - (jfield(st, "time") or 0) < 600 then
    reaper.ShowMessageBox(M.tr("busy"), TITLE, 0)
    return
  end
  os.remove(STATUS)
  local log = DIR .. SEP .. "cli.log"
  local line = M.command(cmd, dir, py, windows, log)
  if windows then
    local r = reaper.ExecProcess(line, -1)
    if r == nil then
      reaper.ShowMessageBox(string.format(M.tr("launch_failed"), line), TITLE, 0)
      return
    end
  else
    os.execute(line)
  end

  local t0 = reaper.time_precise()
  local spin = { "|", "/", "-", "\\" }
  local win = true
  gfx.init(TITLE, 480, 110)
  local function finish(msg)
    if win then gfx.quit() end
    reaper.ShowMessageBox(msg, TITLE, 0)
  end
  local function loop()
    local el = reaper.time_precise() - t0
    local s = read(STATUS)
    local state = s and jfield(s, "state")
    if state == "done" or state == "error" then
      finish(jfield(s, "message") or (state == "done" and M.tr("done") or M.tr("error")))
      return
    end
    if el > 900 then finish(string.format(M.tr("timeout"), log)) return end
    if win then
      if gfx.getchar() < 0 then win = false else
        gfx.set(0.08, 0.09, 0.11, 1); gfx.rect(0, 0, gfx.w, gfx.h, 1)
        gfx.set(1, 1, 1, 1); gfx.setfont(1, "Arial", 20)
        gfx.x, gfx.y = 20, 22; gfx.drawstr(label .. "  " .. spin[(math.floor(el * 4) % 4) + 1])
        gfx.set(0.6, 0.65, 0.72, 1); gfx.setfont(1, "Arial", 15)
        gfx.x, gfx.y = 20, 62
        gfx.drawstr(string.format(M.tr("hint"), math.floor(el)))
        gfx.update()
      end
    end
    reaper.defer(loop)
  end
  loop()
end

return M

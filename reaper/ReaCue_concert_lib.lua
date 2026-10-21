-- ReaCue : code commun du mode concert (fenêtre « ReaCue - Concert », Morceau suivant / précédent).
-- ReaCue: shared code of concert mode (“ReaCue - Concert” window, Next / Previous song).
-- Les données d'un concert sont dans <projet>.concert.lua (écrit par ReaCue, données pures).

local L = {}
local SEP = package.config:sub(1, 1)
local LIB_DIR = debug.getinfo(1, "S").source:match("^@?(.*[/\\])") or ""
local R = dofile(LIB_DIR .. "ReaCue_run.lua")       -- langue, réglages, dossier d'installation, lancement CLI
L.R = R
L.dir = LIB_DIR

-- textes (langue du réglage « language » de reacue_settings.json) -----------------------
local TXT = {
  fr = {
    title = "ReaCue - Concert",
    not_concert = "Ce projet n'est pas un concert ReaCue.\nOuvre-en un avec l'action « ReaCue - Concert ».",
    state = { play = "Lecture", pause = "Pause", stop = "Arrêt" },
    prev = "Précédent", home = "Début", play = "Lecture", pause = "Pause", stop = "Stop", next = "Suivant",
    again = "encore ?", count_in = "décompte", bar = "mesure %d / %d", rest = "reste %s",
    sections = "Sections", no_regions = "(pas de régions pour ce morceau)",
    next_song = "Ensuite : %d · %s · %s BPM · %s", last_song = "Dernier morceau du concert",
    rebuilding = "reconstruction… %d s", auto_stop = "arrêt auto actif",
    setlist = "Setlist", rebuild = "Reconstruire le concert",
    rebuild_q = "Reconstruire le concert à partir des projets des morceaux ?\n\nLes modifications faites directement dans le projet concert seront perdues.",
    not_found = "Programme ReaCue introuvable :\n%s", error = "Erreur",
    pin_title = "ReaCue - Code PIN de la Régie", pin_field = "Nouveau code (4 chiffres) :",
    pin_bad = "Le code doit faire exactement 4 chiffres.", pin_btn = "PIN %s",
    qr_title = "Prompteur des musiciens", qr_sub = "Scanner avec l'appareil photo du téléphone", close = "Fermer",
    no_ip = "Adresse IP de l'ordinateur introuvable.", no_ip2 = "Vérifie que l'ordinateur est connecté au Wi-Fi (ou au réseau),",
    no_ip3 = "puis clique à nouveau sur QR.", qr_fail = "QR code impossible : %s",
    same_wifi = "Même Wi-Fi que l'ordinateur", other_ip = "  ·  autre adresse : %s",
    pin_line = "Code PIN de la Régie : %s",
    no_web = "Interface web REAPER non trouvée : port 8080 supposé (Préférences › Control/OSC/web)",
    qr_missing = "ReaCue_qrcode.lua introuvable",
    phone = "téléphone : %s ✓", phone_badpin = "téléphone : code PIN incorrect",
    cmd = { toggle = "Lecture/Pause", play = "Lecture", pause = "Pause", stop = "Stop", prev = "Précédent",
      next = "Suivant", home = "Début", song = "Morceau", seek = "Section" },
    concert_n = "Concert %s / %s",
    none = "Aucun concert dans ce projet", building = "Construction du concert… %d s",
    open_one = "Ouvrir un concert (nouvel onglet) :", none_in = "Aucun concert dans %s",
    ask_claude = "Demande à Claude : « concert : morceau 1, morceau 2… »",
    n_songs = "%s  ·  %d morceaux", to_build = "Setlists à construire :", build = "Construire  %s",
  },
  en = {
    title = "ReaCue - Concert",
    not_concert = "This project is not a ReaCue concert.\nOpen one with the “ReaCue - Concert” action.",
    state = { play = "Playing", pause = "Paused", stop = "Stopped" },
    prev = "Previous", home = "Start", play = "Play", pause = "Pause", stop = "Stop", next = "Next",
    again = "again?", count_in = "count-in", bar = "bar %d / %d", rest = "%s left",
    sections = "Sections", no_regions = "(no regions for this song)",
    next_song = "Next: %d · %s · %s BPM · %s", last_song = "Last song of the concert",
    rebuilding = "rebuilding… %d s", auto_stop = "auto stop on",
    setlist = "Setlist", rebuild = "Rebuild the concert",
    rebuild_q = "Rebuild the concert from the songs' projects?\n\nChanges made directly in the concert project will be lost.",
    not_found = "ReaCue program not found:\n%s", error = "Error",
    pin_title = "ReaCue - Stage control PIN code", pin_field = "New code (4 digits):",
    pin_bad = "The code must be exactly 4 digits.", pin_btn = "PIN %s",
    qr_title = "Musicians' prompter", qr_sub = "Scan with the phone's camera", close = "Close",
    no_ip = "Computer IP address not found.", no_ip2 = "Check that the computer is connected to the Wi-Fi (or network),",
    no_ip3 = "then click QR again.", qr_fail = "QR code failed: %s",
    same_wifi = "Same Wi-Fi as the computer", other_ip = "  ·  other address: %s",
    pin_line = "Stage control PIN code: %s",
    no_web = "REAPER web interface not found: port 8080 assumed (Preferences › Control/OSC/web)",
    qr_missing = "ReaCue_qrcode.lua not found",
    phone = "phone: %s ✓", phone_badpin = "phone: wrong PIN code",
    cmd = { toggle = "Play/Pause", play = "Play", pause = "Pause", stop = "Stop", prev = "Previous",
      next = "Next", home = "Start", song = "Song", seek = "Section" },
    concert_n = "Concert %s / %s",
    none = "No concert in this project", building = "Building the concert… %d s",
    open_one = "Open a concert (new tab):", none_in = "No concert in %s",
    ask_claude = "Ask Claude: “concert: song 1, song 2…”",
    n_songs = "%s  ·  %d songs", to_build = "Setlists to build:", build = "Build  %s",
  },
}
function L.lang() return R.lang() end
function L.tr(key) local l = TXT[R.lang()] or TXT.fr; local v = l[key]; if v == nil then v = TXT.fr[key] end return v end

function L.read(p)
  local f = io.open(p, "rb"); if not f then return nil end
  local s = f:read("*a"); f:close(); return s
end

function L.exists(p) local f = io.open(p, "rb"); if f then f:close() return true end return false end

function L.project_file()
  local _, fn = reaper.EnumProjects(-1, "")
  return fn or ""
end

function L.sidecar_for(fn)
  if not fn or fn == "" then return nil end
  return (fn:gsub("%.[Rr][Pp][Pp]$", "")) .. ".concert.lua"
end

-- données pures : chargées sans aucun accès à l'API
function L.load_file(path)
  local src = path and L.read(path)
  if not src then return nil end
  local chunk = load(src, "concert", "t", {})
  if not chunk then return nil end
  local ok, d = pcall(chunk)
  if ok and type(d) == "table" and type(d.songs) == "table" and #d.songs > 0 then
    d.sidecar = path
    return d
  end
  return nil
end

function L.load_concert() return L.load_file(L.sidecar_for(L.project_file())) end

-- morceau contenant le temps t : le dernier dont le début est passé
function L.song_index(c, t)
  local i = 1
  for k, s in ipairs(c.songs) do if s.start <= t + 0.05 then i = k end end
  return i
end

function L.playing() return (reaper.GetPlayState() & 1) == 1 end

function L.pos()
  if L.playing() then return reaper.GetPlayPosition() end
  return reaper.GetCursorPosition()
end

function L.goto_song(c, i)
  i = math.max(1, math.min(#c.songs, i))
  if L.playing() or (reaper.GetPlayState() & 2) == 2 then reaper.OnStopButton() end
  reaper.SetEditCurPos(c.songs[i].start, true, false)
  return i
end

-- « précédent » : au début du morceau en cours si on est dedans, sinon le morceau d'avant
function L.prev(c)
  local t = L.pos()
  local i = L.song_index(c, t)
  if t > c.songs[i].start + 2.0 then return L.goto_song(c, i) end
  return L.goto_song(c, i - 1)
end

function L.next(c)
  return L.goto_song(c, L.song_index(c, L.pos()) + 1)
end

-- arrêt automatique : la lecture a franchi la fin d'un morceau entre deux tours de boucle
-- renvoie l'index du morceau terminé (ou nil)
function L.crossed_stop(c, last, now)
  if not last or not now or now < last or now - last > 1.5 then return nil end
  for k, s in ipairs(c.songs) do
    if last < s.stop and now >= s.stop then return k end
  end
  return nil
end

function L.after_stop(c, k)
  reaper.OnStopButton()
  local nx = c.songs[k + 1]
  reaper.SetEditCurPos(nx and nx.start or c.songs[k].stop, true, false)
end

function L.home() return os.getenv("USERPROFILE") and R.is_windows() and os.getenv("USERPROFILE") or os.getenv("HOME") or os.getenv("USERPROFILE") or "" end

local function settings_text()
  return L.read(reaper.GetResourcePath() .. SEP .. "ReaCueMCP" .. SEP .. "reacue_settings.json")
end

-- dossier des concerts : ExtState ReaCue/concert_dir, puis réglages concert_dir / projects_dir,
-- sinon <Documents>/REAPER Media/Concerts (même règle que reacue_mcp/concert.py)
function L.concert_dir()
  local d = reaper.GetExtState("ReaCue", "concert_dir")
  if d ~= "" then return d end
  local st = settings_text()
  local c = R.jfield(st, "concert_dir")
  if type(c) == "string" and c ~= "" then return (c:gsub("^~", L.home())) end
  local p = R.jfield(st, "projects_dir")
  if type(p) == "string" and p ~= "" then return (p:gsub("^~", L.home())) .. SEP .. "Concerts" end
  return L.home() .. SEP .. "Documents" .. SEP .. "REAPER Media" .. SEP .. "Concerts"
end

function L.list_concerts()
  local dir, out, i = L.concert_dir(), {}, 0
  while true do
    local f = reaper.EnumerateFiles(dir, i)
    if not f then break end
    if f:match("%.concert%.lua$") then
      local d = L.load_file(dir .. SEP .. f)
      if d and d.rpp and L.exists(d.rpp) then out[#out + 1] = d end
    end
    i = i + 1
  end
  table.sort(out, function(a, b) return (a.name or "") < (b.name or "") end)
  return out
end

-- setlists pas encore construites (fichier <nom>.setlist.json sans <nom>.RPP à côté)
function L.list_setlists()
  local dir, out, i = L.concert_dir(), {}, 0
  while true do
    local f = reaper.EnumerateFiles(dir, i)
    if not f then break end
    local stem = f:match("^(.*)%.setlist%.json$")
    if stem and not L.exists(dir .. SEP .. stem .. ".RPP") and not L.exists(dir .. SEP .. stem .. ".rpp") then
      out[#out + 1] = { name = stem, setlist = dir .. SEP .. f, rpp = dir .. SEP .. stem .. ".RPP" }
    end
    i = i + 1
  end
  table.sort(out, function(a, b) return a.name < b.name end)
  return out
end

function L.open_concert(d)
  reaper.Main_OnCommand(40859, 0)            -- nouvel onglet de projet : le projet en cours reste ouvert
  reaper.Main_openProject(d.rpp)
end

-- prompteur : remet en ligne celui du concert (les téléphones suivent tout le concert)
function L.publish_prompter(c)
  if not c.prompter then return false end
  local src = L.read(c.prompter)
  if not src then return false end
  local www = reaper.GetResourcePath() .. SEP .. "reaper_www_root"
  reaper.RecursiveCreateDirectory(www, 0)
  local dst = www .. SEP .. "reacue_song.json"
  if L.read(dst) == src then return true end
  local tmp = dst .. ".tmp"
  local f = io.open(tmp, "wb"); if not f then return false end
  f:write(src); f:close()
  os.remove(dst)
  return os.rename(tmp, dst) and true or false
end

-- page du prompteur : copie la version de ReaCue (reacue_mcp/web/prompteur.html) dans reaper_www_root si elle a changé
function L.publish_page()
  local src = L.read(L.install_dir() .. SEP .. "reacue_mcp" .. SEP .. "web" .. SEP .. "prompteur.html")
  if not src or #src < 1000 then return false end
  local www = reaper.GetResourcePath() .. SEP .. "reaper_www_root"
  reaper.RecursiveCreateDirectory(www, 0)
  local dst = www .. SEP .. "prompteur.html"
  if L.read(dst) == src then return true end
  local tmp = dst .. ".tmp"
  local f = io.open(tmp, "wb"); if not f then return false end
  f:write(src); f:close()
  os.remove(dst)
  return os.rename(tmp, dst) and true or false
end

function L.fmt_time(s)
  s = math.max(0, math.floor(s + 0.5))
  return string.format("%d:%02d", s // 60, s % 60)
end

-- QR code du prompteur -------------------------------------------------------------------
local function good_ip(ip)
  return ip and not ip:match("^127%.") and not ip:match("^169%.254%.") and not ip:match("^0%.")
end

-- adresses IPv4 trouvées dans la sortie de ipconfig (Windows : lignes « IPv4 », toutes langues)
function L.parse_windows_ipconfig(out)
  local res, seen = {}, {}
  for line in (out or ""):gmatch("[^\r\n]+") do
    if line:find("IPv4") then
      local ip = line:match(":%s*(%d+%.%d+%.%d+%.%d+)")
      if good_ip(ip) and not seen[ip] then seen[ip] = true; res[#res + 1] = ip end
    end
  end
  return res
end

-- adresses de `hostname -I` (Linux)
function L.parse_hostname_i(out)
  local res = {}
  for ip in (out or ""):gmatch("(%d+%.%d+%.%d+%.%d+)") do if good_ip(ip) then res[#res + 1] = ip end end
  return res
end

-- adresse(s) IPv4 de l'ordinateur sur le réseau local (Wi-Fi / Ethernet), calculées à chaque appel
--   macOS : ipconfig getifaddr en0..en3 ; Windows : ipconfig (sans fenêtre console, via ExecProcess) ;
--   Linux : hostname -I
function L.local_ips()
  local out, seen = {}, {}
  if not reaper.ExecProcess then return out end
  local os_name = reaper.GetOS and reaper.GetOS() or ""
  if R.is_windows() then
    local r = reaper.ExecProcess("ipconfig", 3000)
    return L.parse_windows_ipconfig(r)
  end
  if os_name:match("^Other") or os_name:match("^Linux") then
    local r = reaper.ExecProcess("hostname -I", 1500)
    return L.parse_hostname_i(r and r:gsub("^%-?%d+\n", ""))
  end
  for _, ifc in ipairs({ "en0", "en1", "en2", "en3" }) do
    local r = reaper.ExecProcess("/usr/sbin/ipconfig getifaddr " .. ifc, 1500)
    local ip = r and r:match("\n%s*(%d+%.%d+%.%d+%.%d+)")
    if good_ip(ip) and not seen[ip] then
      seen[ip] = true
      out[#out + 1] = ip
    end
  end
  return out
end

-- port de l'interface web REAPER (reaper.ini : csurf_N=HTTP <flags> <port> ...)
-- renvoie port, trouvée (bool)
function L.parse_web_port(ini)
  if not ini then return 8080, false end
  local cnt = tonumber(ini:match("\ncsurf_cnt=(%d+)")) or tonumber(ini:match("^csurf_cnt=(%d+)"))
  for idx, rest in ini:gmatch("csurf_(%d+)=HTTP%s+([^\r\n]*)") do
    if not cnt or tonumber(idx) < cnt then
      local _, port = rest:match("^(%-?%d+)%s+(%d+)")
      port = tonumber(port)
      if port and port > 0 and port < 65536 then return port, true end
    end
  end
  return 8080, false
end

function L.web_port()
  local ini = reaper.get_ini_file and L.read(reaper.get_ini_file()) or nil
  return L.parse_web_port(ini and ("\n" .. ini))
end

function L.prompter_url(ip, port)
  return string.format("http://%s:%d/prompteur.html", ip, port)
end

-- matrice QR (tableau [x][y], >0 = noir) ; niveau de correction M ; nil + message en cas d'échec
local qr_lib
function L.qr_matrix(text, script_dir)
  if not qr_lib then
    local ok, lib = pcall(dofile, (script_dir or LIB_DIR) .. "ReaCue_qrcode.lua")
    if not ok or type(lib) ~= "table" then return nil, L.tr("qr_missing") end
    qr_lib = lib
  end
  local ok, m = qr_lib.qrcode(text, 2)
  if not ok then return nil, tostring(m) end
  return m
end

function L.install_dir() return R.install_dir(LIB_DIR:gsub("[/\\]$", "")) end

-- lance la CLI ReaCue en arrière-plan (ex. « concert --setlist <fichier> ») ; renvoie true ou false, message
function L.run_cli(cmd, arg_path)
  local windows = R.is_windows()
  local dir = L.install_dir()
  local py = R.python(dir, windows)
  if not L.exists(py) then return false, string.format(L.tr("not_found"), py) end
  local full = cmd .. (arg_path and (" --setlist " .. (windows and R.winq(arg_path) or R.shq(arg_path))) or "")
  local log = reaper.GetResourcePath() .. SEP .. "ReaCueMCP" .. SEP .. "cli.log"
  local line = R.command(full, dir, py, windows, log)
  if windows then
    if reaper.ExecProcess(line, -1) == nil then return false, line end
  else
    os.execute(line)
  end
  return true
end

-- ---------------------------------------------------------------------------------------
-- Pilotage : transport, sections, tonalités, télécommande « Régie » (téléphones)
-- ---------------------------------------------------------------------------------------

function L.play_state()                -- "play" | "pause" | "stop"
  local s = reaper.GetPlayState()
  if (s & 2) == 2 then return "pause" end
  if (s & 1) == 1 then return "play" end
  return "stop"
end

function L.toggle_play()
  local s = L.play_state()
  if s == "stop" then reaper.OnPlayButton() else reaper.OnPauseButton() end
end

function L.stop() reaper.OnStopButton() end

function L.song_home(c) return L.goto_song(c, L.song_index(c, L.pos())) end

-- saut dans le concert ; pendant la lecture, la lecture continue au nouvel endroit
function L.seek(c, t)
  if not t then return false end
  local last = c.songs[#c.songs]
  if t < 0 or t > (last.next or last.stop) + 1 then return false end
  local st = L.play_state()
  reaper.SetEditCurPos(t, true, st == "play")
  return true
end

-- sections (régions du projet) du morceau i : {name, start, stop, color={r,g,b}}
function L.song_sections(c, i)
  local s = c.songs[i]
  if not s then return {} end
  local out, k = {}, 0
  local prefix = (s.title or "") .. " · "
  while true do
    local ok, isrgn, pos, rend, name, _, color = reaper.EnumProjectMarkers3(0, k)
    if not ok or ok == 0 then break end
    if isrgn and pos >= s.start - 0.01 and pos < s.stop - 0.01 then
      local nm = name or ""
      if nm:sub(1, #prefix) == prefix then nm = nm:sub(#prefix + 1) end
      local rgb = nil
      if color and color ~= 0 then
        local r, g, b = reaper.ColorFromNative(color & 0xFFFFFF)
        rgb = { r, g, b }
      end
      out[#out + 1] = { name = nm, start = pos, stop = rend, color = rgb }
    end
    k = k + 1
  end
  table.sort(out, function(a, b) return a.start < b.start end)
  return out
end

function L.section_at(secs, t)
  local cur = nil
  for k, x in ipairs(secs) do if x.start <= t + 0.02 then cur = k end end
  if cur and t >= secs[cur].stop + 0.02 then return nil end
  return cur
end

-- mesure du morceau (1 = première mesure ; <= 0 = décompte)
function L.bar_of(s, t)
  if not reaper.TimeMap2_timeToBeats then return nil end
  local _, m = reaper.TimeMap2_timeToBeats(0, t)
  local _, m1 = reaper.TimeMap2_timeToBeats(0, s.bar1 or s.start)
  if not m or not m1 then return nil end
  return m - m1 + 1
end

-- tonalités lues dans le prompteur du concert (dans l'ordre des morceaux) : {"Gbm", false, "Em", ...}
function L.song_keys(c)
  local src = c.prompter and L.read(c.prompter)
  local out = {}
  if not src then return out end
  local p = 1
  while true do
    local a, b = src:find('"key"%s*:%s*', p)
    if not a then break end
    local v = src:sub(b + 1, b + 1)
    if v == "{" then
      local obj = src:match("^%b{}", b + 1) or ""
      out[#out + 1] = obj:match('"chord"%s*:%s*"([^"]*)"') or false
    else
      out[#out + 1] = false
    end
    p = b + 1
  end
  return out
end

-- télécommande ---------------------------------------------------------------------------
-- Le téléphone écrit, via l'interface web de REAPER :
--   /_/SET/EXTSTATE/ReaCue/remote/<cmd>|<arg>|<pin>|<nonce>      (valeur urlencodée)
-- La fenêtre Concert lit, efface, vérifie le PIN et le nonce, exécute, puis répond :
--   ExtState ReaCue/remote_ack = <nonce>|ok   (ou |badpin, |bad)
-- et signale qu'elle tourne : ExtState ReaCue/remote_alive = compteur qui avance.
local REMOTE = "ReaCue"

function L.remote_pin()
  local p = reaper.GetExtState(REMOTE, "remote_pin")
  if not p:match("^%d%d%d%d$") then
    math.randomseed(math.floor((reaper.time_precise() * 1000) % 2147483647) + os.time())
    p = string.format("%04d", math.random(0, 9999))
    reaper.SetExtState(REMOTE, "remote_pin", p, true)
  end
  return p
end

function L.set_remote_pin(p)
  if type(p) ~= "string" or not p:match("^%d%d%d%d$") then return false end
  reaper.SetExtState(REMOTE, "remote_pin", p, true)
  return true
end

function L.remote_alive(now)
  reaper.SetExtState(REMOTE, "remote_alive", tostring(math.floor((now or reaper.time_precise()) * 2)), false)
end

function L.remote_off()
  reaper.SetExtState(REMOTE, "remote_alive", "", false)
end

function L.remote_exec(c, cmd, arg)
  if cmd == "toggle" then L.toggle_play()
  elseif cmd == "play" then if L.play_state() ~= "play" then L.toggle_play() end
  elseif cmd == "pause" then if L.play_state() == "play" then reaper.OnPauseButton() end
  elseif cmd == "stop" then L.stop()
  elseif cmd == "prev" then L.prev(c)
  elseif cmd == "next" then L.next(c)
  elseif cmd == "home" then L.song_home(c)
  elseif cmd == "song" then
    local k = tonumber(arg)
    if not k or not c.songs[k] then return false end
    L.goto_song(c, k)
  elseif cmd == "seek" then
    if not L.seek(c, tonumber(arg)) then return false end
  else
    return false
  end
  return true
end

-- traite au plus une commande en attente ; renvoie cmd, résultat ("ok", "badpin", "bad", "dup") ou nil
local seen, seen_list = {}, {}
function L.remote_poll(c)
  local v = reaper.GetExtState(REMOTE, "remote")
  if v == nil or v == "" then return nil end
  reaper.SetExtState(REMOTE, "remote", "", false)
  local cmd, arg, pin, nonce = v:match("^([%w_]+)|([^|]*)|(%d*)|([%w%-]+)$")
  if not cmd then return nil, "bad" end
  if seen[nonce] then return cmd, "dup" end
  seen[nonce] = true
  seen_list[#seen_list + 1] = nonce
  if #seen_list > 64 then seen[table.remove(seen_list, 1)] = nil end
  local res
  if pin ~= L.remote_pin() then res = "badpin"
  elseif not c then res = "noconcert"
  else res = L.remote_exec(c, cmd, arg) and "ok" or "bad" end
  reaper.SetExtState(REMOTE, "remote_ack", nonce .. "|" .. res, false)
  return cmd, res
end

function L._reset_remote() seen, seen_list = {}, {} end

return L

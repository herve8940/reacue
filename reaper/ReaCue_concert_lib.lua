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
      next = "Suivant", home = "Début", song = "Morceau", seek = "Section", reh = "Répétition", loop = "Boucle",
      loopoff = "Boucle off", rate = "Vitesse", mute = "Mute", solo = "Solo", hearall = "Tout entendre" },
    concert_n = "Concert %s / %s",
    none = "Aucun concert dans ce projet", building = "Construction du concert… %d s",
    open_one = "Ouvrir un concert (nouvel onglet) :", none_in = "Aucun concert dans %s",
    ask_claude = "Demande à Claude : « concert : morceau 1, morceau 2… »",
    n_songs = "%s  ·  %d morceaux", to_build = "Setlists à construire :", build = "Construire  %s",
    -- contrôle avant concert
    check = "Vérifier", recheck = "Revérifier", fix = "Corriger", check_title = "Contrôle avant concert",
    all_ready = "Tout est prêt", n_problems = "%d problème(s)", n_warnings = "%d point(s) à surveiller",
    ck = {
      media = "Fichiers audio", media_ok = "%d fichiers lisibles", media_bad = "%d illisible(s) ou hors ligne : %s",
      voice = "Annonces vocales", voice_ok = "%d annonces présentes", voice_bad = "%d annonce(s) manquante(s)", voice_none = "aucune piste d'annonces",
      fresh = "Concert à jour", fresh_ok = "construit le %s, aucun morceau modifié depuis",
      fresh_bad = "modifié(s) depuis la construction : %s", fresh_unknown = "concert construit avec une ancienne version : reconstruis-le une fois",
      fresh_missing = "projet introuvable : %s",
      songs = "Morceaux préparés", songs_ok = "%d morceaux avec structure et tempo",
      songs_bad = "à préparer puis enregistrer : %s",
      bridge = "Pont ReaCue", bridge_ok = "actif", bridge_bad = "ne répond pas : redémarre REAPER",
      web = "Interface web (prompteur)", web_ok = "active, port %d", web_bad = "introuvable : Préférences › Control/OSC/web",
      ip = "Adresse réseau", ip_ok = "%s", ip_bad = "aucune : connecte l'ordinateur au Wi-Fi du groupe",
      audio = "Carte son", audio_ok = "active · %s · %d sorties", audio_bad = "arrêtée : Préférences › Audio › Device",
      outs = "Sorties click et annonces", outs_ok = "%s", outs_bad = "%s", outs_master = "vers la sortie principale",
      outs_hw = "%s → sorties %d/%d", outs_missing = "%s → sortie %d absente (la carte en a %d)",
      outs_nowhere = "%s n'est envoyée nulle part", outs_muted = "%s est coupée (mute)", outs_none = "pas de piste CLICK",
      prompter = "Prompteur des téléphones", prompter_ok = "page et concert publiés", prompter_bad = "pas à jour : republier",
      regie = "Téléphones Régie", regie_ok = "vu il y a %d s", regie_none = "aucun téléphone en Régie pour l'instant",
      mix = "Stems coupés", mix_some = "%s", mix_none = "aucun : tous les stems sont joués", mix_all = "tous les stems sont coupés",
    },
    -- mode répétition
    reh = "Répétition", reh_on = "RÉPÉTITION", reh_loop = "boucle : %s", reh_loop_range = "boucle : %s → %s",
    reh_noloop = "touche une section pour la faire boucler (2e section = plage)",
    loop_off = "Boucle off", reh_exit = "Quitter", rate = "%d %%",
    auto_off = "arrêt auto coupé (répétition)",
    -- instruments (stems)
    instruments = "Instruments (stems)", hear_all = "Tout entendre", back_profile = "Profil",
    mix_none = "aucune piste d'instrument", solo_hint = "appui long = solo",
    mix_played = "joué", mix_cut = "coupé", mix_solo = "solo",
    live_title = "Joué en live", live_hint = "Coché = joué en vrai par le groupe : le stem est coupé",
    live_exc = "Exceptions par morceau", live_exc_hint = "clic : stem / live / profil",
    live_exc_stem = "stem", live_exc_live = "live", live_exc_def = "·",
    live_saved = "profil enregistré", live_nosetlist = "Setlist introuvable : reconstruis le concert.",
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
      next = "Next", home = "Start", song = "Song", seek = "Section", reh = "Rehearsal", loop = "Loop",
      loopoff = "Loop off", rate = "Speed", mute = "Mute", solo = "Solo", hearall = "Hear all" },
    concert_n = "Concert %s / %s",
    none = "No concert in this project", building = "Building the concert… %d s",
    open_one = "Open a concert (new tab):", none_in = "No concert in %s",
    ask_claude = "Ask Claude: “concert: song 1, song 2…”",
    n_songs = "%s  ·  %d songs", to_build = "Setlists to build:", build = "Build  %s",
    check = "Check", recheck = "Check again", fix = "Fix", check_title = "Pre-show check",
    all_ready = "All set", n_problems = "%d problem(s)", n_warnings = "%d thing(s) to watch",
    ck = {
      media = "Audio files", media_ok = "%d files readable", media_bad = "%d unreadable or offline: %s",
      voice = "Spoken cues", voice_ok = "%d cues present", voice_bad = "%d cue(s) missing", voice_none = "no spoken cue track",
      fresh = "Concert up to date", fresh_ok = "built on %s, no song changed since",
      fresh_bad = "changed since the build: %s", fresh_unknown = "concert built with an older version: rebuild it once",
      fresh_missing = "project not found: %s",
      songs = "Prepared songs", songs_ok = "%d songs with structure and tempo",
      songs_bad = "prepare then save: %s",
      bridge = "ReaCue bridge", bridge_ok = "running", bridge_bad = "not answering: restart REAPER",
      web = "Web interface (prompter)", web_ok = "on, port %d", web_bad = "not found: Preferences › Control/OSC/web",
      ip = "Network address", ip_ok = "%s", ip_bad = "none: connect the computer to the band's Wi-Fi",
      audio = "Audio device", audio_ok = "running · %s · %d outputs", audio_bad = "stopped: Preferences › Audio › Device",
      outs = "Click and cue outputs", outs_ok = "%s", outs_bad = "%s", outs_master = "to the main output",
      outs_hw = "%s → outputs %d/%d", outs_missing = "%s → output %d missing (the device has %d)",
      outs_nowhere = "%s is not routed anywhere", outs_muted = "%s is muted", outs_none = "no CLICK track",
      prompter = "Phones' prompter", prompter_ok = "page and concert published", prompter_bad = "out of date: republish",
      regie = "Stage control phones", regie_ok = "seen %d s ago", regie_none = "no Stage control phone yet",
      mix = "Cut stems", mix_some = "%s", mix_none = "none: all stems are played", mix_all = "all stems are cut",
    },
    reh = "Rehearsal", reh_on = "REHEARSAL", reh_loop = "loop: %s", reh_loop_range = "loop: %s → %s",
    reh_noloop = "tap a section to loop it (2nd section = range)",
    loop_off = "Loop off", reh_exit = "Exit", rate = "%d %%",
    auto_off = "auto stop off (rehearsal)",
    instruments = "Instruments (stems)", hear_all = "Hear everything", back_profile = "Profile",
    mix_none = "no instrument track", solo_hint = "long press = solo",
    mix_played = "playing", mix_cut = "muted", mix_solo = "solo",
    live_title = "Played live", live_hint = "Ticked = played for real by the band: its stem is cut",
    live_exc = "Per-song exceptions", live_exc_hint = "click: stem / live / profile",
    live_exc_stem = "stem", live_exc_live = "live", live_exc_def = "·",
    live_saved = "profile saved", live_nosetlist = "Setlist not found: rebuild the concert.",
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

-- dossier des projets des morceaux : réglage projects_dir, sinon <Documents>/REAPER Media (comme concert.py)
function L.projects_dir()
  local p = R.jfield(settings_text(), "projects_dir")
  if type(p) == "string" and p ~= "" then return (p:gsub("^~", L.home())) end
  return L.home() .. SEP .. "Documents" .. SEP .. "REAPER Media"
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

-- ---------------------------------------------------------------------------------------
-- Contrôle avant concert (« Vérifier ») : liste de {id, status = ok|warn|bad|info, label, detail, fix}
-- ---------------------------------------------------------------------------------------
local GEN_TRACKS = { CLICK = true, VOIX = true, VOICE = true, CUES = true }
local VOICE_TRACKS = { VOIX = true, VOICE = true }

-- Adler-32 (même valeur que zlib.adler32 côté Python) : empreinte du projet d'un morceau
function L.adler32(s)
  local a, b = 1, 0
  local n = #s
  for i = 1, n, 4096 do
    local t = { s:byte(i, math.min(n, i + 4095)) }
    for k = 1, #t do a = (a + t[k]) % 65521; b = (b + a) % 65521 end
  end
  return (b << 16) | a
end

local function track_name(tr)
  local _, name = reaper.GetTrackName(tr)
  return name or ""
end

local function short_name(p) return (tostring(p):match("([^/\\]+)$") or tostring(p)) end

local function join_names(list, max)
  max = max or 3
  local out = {}
  for k = 1, math.min(#list, max) do out[k] = list[k] end
  local s = table.concat(out, ", ")
  if #list > max then s = s .. " (+" .. (#list - max) .. ")" end
  return s
end

-- fichiers audio des items : lisibles et en ligne ? (voix d'annonces comptées à part)
function L.scan_media()
  local r = { n = 0, bad = {}, voice_n = 0, voice_bad = 0, has_voice = false }
  local seen = {}
  if not reaper.CountMediaItems then return r end
  for i = 0, reaper.CountMediaItems(0) - 1 do
    local it = reaper.GetMediaItem(0, i)
    local tk = it and reaper.GetActiveTake(it)
    if tk and not (reaper.TakeIsMIDI and reaper.TakeIsMIDI(tk)) then
      local src = reaper.GetMediaItemTake_Source(tk)
      local parent = src and reaper.GetMediaSourceParent and reaper.GetMediaSourceParent(src)
      while parent do src = parent; parent = reaper.GetMediaSourceParent(src) end
      local fn = src and reaper.GetMediaSourceFileName(src, "") or ""
      if fn ~= "" then
        local tname = track_name(reaper.GetMediaItem_Track(it))
        local ok = L.exists(fn)
        if ok and reaper.GetMediaSourceSampleRate and reaper.GetMediaSourceSampleRate(src) == 0 then ok = false end
        if VOICE_TRACKS[tname] then
          r.has_voice = true
          r.voice_n = r.voice_n + 1
          if not ok then r.voice_bad = r.voice_bad + 1 end
        elseif not seen[fn] then
          seen[fn] = true
          r.n = r.n + 1
          if not ok then r.bad[#r.bad + 1] = short_name(fn) end
        end
      end
    end
  end
  return r
end

-- sorties du click et des annonces : envois matériels existants, pas de piste muette ou isolée
function L.scan_outputs()
  local nout = reaper.GetNumAudioOutputs and reaper.GetNumAudioOutputs() or 0
  local ok_l, bad_l, found = {}, {}, false
  local ck = L.tr("ck")
  for i = 0, (reaper.CountTracks and reaper.CountTracks(0) or 0) - 1 do
    local tr = reaper.GetTrack(0, i)
    local name = track_name(tr)
    if name == "CLICK" or VOICE_TRACKS[name] then
      if name == "CLICK" then found = true end
      if reaper.GetMediaTrackInfo_Value(tr, "B_MUTE") > 0 then bad_l[#bad_l + 1] = string.format(ck.outs_muted, name) end
      local main = reaper.GetMediaTrackInfo_Value(tr, "B_MAINSEND") > 0
      local nsend = reaper.GetTrackNumSends and reaper.GetTrackNumSends(tr, 1) or 0
      if main then ok_l[#ok_l + 1] = name .. " " .. ck.outs_master end
      for k = 0, nsend - 1 do
        local dst = math.floor(reaper.GetTrackSendInfo_Value(tr, 1, k, "I_DSTCHAN"))
        local ch = dst & 1023
        local mono = (dst & 1024) ~= 0
        local need = ch + (mono and 1 or 2)
        if nout > 0 and need > nout then
          bad_l[#bad_l + 1] = string.format(ck.outs_missing, name, need, nout)
        else
          ok_l[#ok_l + 1] = string.format(ck.outs_hw, name, ch + 1, ch + (mono and 1 or 2))
        end
      end
      if not main and nsend == 0 then bad_l[#bad_l + 1] = string.format(ck.outs_nowhere, name) end
    end
  end
  return found, ok_l, bad_l
end

local function fmt_date(t)
  if not t then return "?" end
  return os.date(L.lang() == "en" and "%Y-%m-%d %H:%M" or "%d/%m/%Y %H:%M", t)
end

-- état « vu » des téléphones Régie : renseigné par la fenêtre (L.regie_seen = time_precise de la dernière vue)
L.regie_seen = nil

-- liste complète ; opts.c = concert (ou nil), opts.ips (sinon calculées), opts.now
function L.run_checks(c, opts)
  opts = opts or {}
  local ck = L.tr("ck")
  local out = {}
  local function add(id, status, label, detail, fix) out[#out + 1] = { id = id, status = status, label = label, detail = detail or "", fix = fix } end
  if c then
    -- médias
    local m = L.scan_media()
    if #m.bad == 0 then add("media", "ok", ck.media, string.format(ck.media_ok, m.n))
    else add("media", "bad", ck.media, string.format(ck.media_bad, #m.bad, join_names(m.bad)), "media") end
    if not m.has_voice then add("voice", "info", ck.voice, ck.voice_none)
    elseif m.voice_bad == 0 then add("voice", "ok", ck.voice, string.format(ck.voice_ok, m.voice_n))
    else add("voice", "bad", ck.voice, string.format(ck.voice_bad, m.voice_bad), "rebuild") end
    -- morceaux préparés (structure + tempo)
    local unprep = {}
    for _, s in ipairs(c.songs) do
      if (tonumber(s.sections) or 0) < 1 or (tonumber(s.bars) or 0) < 1 then unprep[#unprep + 1] = s.title end
    end
    if #unprep == 0 then add("songs", "ok", ck.songs, string.format(ck.songs_ok, #c.songs))
    else add("songs", "bad", ck.songs, string.format(ck.songs_bad, join_names(unprep))) end
    -- concert à jour : empreinte du projet de chaque morceau
    local changed, missing, unknown = {}, {}, false
    for _, s in ipairs(c.songs) do
      local src = s.project and L.read(s.project)
      if not src then missing[#missing + 1] = s.title
      elseif not s.project_sum then unknown = true
      elseif #src ~= s.project_size or L.adler32(src) ~= s.project_sum then changed[#changed + 1] = s.title end
    end
    if #missing > 0 then add("fresh", "bad", ck.fresh, string.format(ck.fresh_missing, join_names(missing)))
    elseif #changed > 0 then add("fresh", "warn", ck.fresh, string.format(ck.fresh_bad, join_names(changed)), "rebuild")
    elseif unknown then add("fresh", "warn", ck.fresh, ck.fresh_unknown, "rebuild")
    else add("fresh", "ok", ck.fresh, string.format(ck.fresh_ok, fmt_date(c.built))) end
  end
  -- pont, interface web, adresse IP
  if L.R.bridge_alive and L.R.bridge_alive() then add("bridge", "ok", ck.bridge, ck.bridge_ok)
  else add("bridge", "bad", ck.bridge, ck.bridge_bad) end
  local port, found = L.web_port()
  if found then add("web", "ok", ck.web, string.format(ck.web_ok, port)) else add("web", "bad", ck.web, ck.web_bad) end
  local ips = opts.ips or L.local_ips()
  if #ips > 0 then add("ip", "ok", ck.ip, string.format(ck.ip_ok, L.prompter_url(ips[1], port)))
  else add("ip", "bad", ck.ip, ck.ip_bad) end
  -- carte son et sorties
  local running = reaper.Audio_IsRunning and reaper.Audio_IsRunning() or 0
  local nout = reaper.GetNumAudioOutputs and reaper.GetNumAudioOutputs() or 0
  if running ~= 0 and running ~= false then
    local dev = ""
    if reaper.GetAudioDeviceInfo then local _, d = reaper.GetAudioDeviceInfo("IDENT_OUT", ""); dev = d or "" end
    add("audio", "ok", ck.audio, string.format(ck.audio_ok, dev ~= "" and dev or "?", nout))
  else
    add("audio", "bad", ck.audio, ck.audio_bad)
  end
  if c then
    local found_click, okl, badl = L.scan_outputs()
    if not found_click then add("outs", "warn", ck.outs, ck.outs_none)
    elseif #badl > 0 then add("outs", "bad", ck.outs, string.format(ck.outs_bad, table.concat(badl, " · ")))
    else add("outs", "ok", ck.outs, string.format(ck.outs_ok, table.concat(okl, " · "))) end
    -- prompteur publié et à jour
    local www = reaper.GetResourcePath() .. SEP .. "reaper_www_root" .. SEP
    local page = L.read(L.install_dir() .. SEP .. "reacue_mcp" .. SEP .. "web" .. SEP .. "prompteur.html")
    local pub_ok = (not page or L.read(www .. "prompteur.html") == page)
      and (not c.prompter or not L.read(c.prompter) or L.read(www .. "reacue_song.json") == L.read(c.prompter))
    if pub_ok then add("prompter", "ok", ck.prompter, ck.prompter_ok)
    else add("prompter", "warn", ck.prompter, ck.prompter_bad, "publish") end
  end
  -- stems coupés (information)
  if c then
    local cut, n = {}, 0
    for _, g in ipairs(L.instr_tracks()) do
      n = n + 1
      local m = 0
      for _, tr in ipairs(g.tracks) do m = math.max(m, L.track_mute_wanted(tr)) end
      if m > 0 then cut[#cut + 1] = g.label end
    end
    if n > 0 then
      local d = (#cut == 0) and ck.mix_none or ((#cut == n) and ck.mix_all or string.format(ck.mix_some, table.concat(cut, ", ")))
      add("mix", "info", ck.mix, d)
    end
  end
  -- téléphones Régie (information)
  local now = opts.now or reaper.time_precise()
  if L.regie_seen and now - L.regie_seen < 600 then
    add("regie", "info", ck.regie, string.format(ck.regie_ok, math.floor(now - L.regie_seen)))
  else
    add("regie", "info", ck.regie, ck.regie_none)
  end
  return out
end

-- résumé : nombre de problèmes (bad) et de points à surveiller (warn)
function L.check_summary(list)
  local bad, warn = 0, 0
  for _, x in ipairs(list) do
    if x.status == "bad" then bad = bad + 1 elseif x.status == "warn" then warn = warn + 1 end
  end
  return bad, warn
end

-- corrections simples (la reconstruction est lancée par la fenêtre)
function L.apply_fix(c, fix)
  if fix == "media" then reaper.Main_OnCommand(40101, 0); return true      -- Item: Set all media online
  elseif fix == "publish" then
    local a = c and L.publish_prompter(c)
    local b = L.publish_page()
    return (a ~= false) and b
  end
  return false
end

-- ---------------------------------------------------------------------------------------
-- Mode répétition : arrêt auto coupé, boucle sur une section ou une plage avec 1 mesure de décompte
-- (click et annonces seuls, les autres pistes coupées) avant chaque reprise, ralenti 100/90/80/70 %.
-- ---------------------------------------------------------------------------------------
local PRESERVE_PITCH = 40671     -- Options: Toggle preserve pitch in audio items when changing master playrate
L.reh = { on = false, loop = nil, anchor = nil, rate = 1.0, saved = nil, prebar = false, muted = nil }

function L.bar_len_before(t, bpm)
  if reaper.TimeMap2_timeToBeats and reaper.TimeMap2_beatsToTime then
    local _, m = reaper.TimeMap2_timeToBeats(0, t + 0.001)
    if m and m >= 1 then
      local t0 = reaper.TimeMap2_beatsToTime(0, 0, m - 1)
      if t0 and t0 < t - 0.01 then return t - t0 end
    end
  end
  return 240 / (bpm and bpm > 0 and bpm or 120)
end

local function music_tracks()
  local out = {}
  for i = 0, (reaper.CountTracks and reaper.CountTracks(0) or 0) - 1 do
    local tr = reaper.GetTrack(0, i)
    if not GEN_TRACKS[track_name(tr)] then out[#out + 1] = tr end
  end
  return out
end

local function mute_music(on)   -- (défini plus bas : L.set_track_mute tient compte de cet état)
  local R_ = L.reh
  if on then
    if R_.muted then return end
    R_.muted = {}
    for _, tr in ipairs(music_tracks()) do
      R_.muted[#R_.muted + 1] = { tr, reaper.GetMediaTrackInfo_Value(tr, "B_MUTE") }
      reaper.SetMediaTrackInfo_Value(tr, "B_MUTE", 1)
    end
  elseif R_.muted then
    for _, x in ipairs(R_.muted) do reaper.SetMediaTrackInfo_Value(x[1], "B_MUTE", x[2]) end
    R_.muted = nil
  end
end

function L.publish_reh()
  local R_ = L.reh
  local lp = R_.loop
  reaper.SetExtState("ReaCue", "rehearsal", string.format("%d|%.2f|%s|%s|%s", R_.on and 1 or 0, R_.rate,
    lp and string.format("%.3f", lp.start) or "", lp and string.format("%.3f", lp.stop) or "",
    lp and (lp.names or "") or ""), false)
end

function L.set_rate(r)
  r = tonumber(r)
  if not r or r < 0.5 or r > 1.0 then return false end
  if r < 0.999 and reaper.GetToggleCommandState and reaper.GetToggleCommandState(PRESERVE_PITCH) == 0 then
    reaper.Main_OnCommand(PRESERVE_PITCH, 0)
    L.reh.pitch_switched = true
  end
  if reaper.CSurf_OnPlayRateChange then reaper.CSurf_OnPlayRateChange(r) end
  L.reh.rate = r
  L.publish_reh()
  return true
end

function L.loop_off()
  local R_ = L.reh
  mute_music(false)
  R_.loop, R_.anchor, R_.prebar = nil, nil, false
  if reaper.GetSet_LoopTimeRange then reaper.GetSet_LoopTimeRange(true, true, 0, 0, false) end
  L.publish_reh()
end

function L.set_rehearsal(on)
  local R_ = L.reh
  if on and not R_.on then
    local s0, s1 = 0, 0
    if reaper.GetSet_LoopTimeRange then s0, s1 = reaper.GetSet_LoopTimeRange(false, true, 0, 0, false) end
    R_.saved = { rep = reaper.GetSetRepeat and reaper.GetSetRepeat(-1) or 0, sel = { s0 or 0, s1 or 0 },
                 rate = reaper.Master_GetPlayRate and reaper.Master_GetPlayRate(0) or 1 }
    R_.on = true
    R_.pitch_switched = false
    if reaper.GetSetRepeat then reaper.GetSetRepeat(0) end          -- la boucle est pilotée par la fenêtre
  elseif not on and R_.on then
    L.loop_off()
    if reaper.CSurf_OnPlayRateChange then reaper.CSurf_OnPlayRateChange(1.0) end
    if R_.pitch_switched and reaper.GetToggleCommandState and reaper.GetToggleCommandState(PRESERVE_PITCH) == 1 then
      reaper.Main_OnCommand(PRESERVE_PITCH, 0)
    end
    local sv = R_.saved or {}
    if reaper.GetSetRepeat and sv.rep then reaper.GetSetRepeat(sv.rep) end
    if reaper.GetSet_LoopTimeRange and sv.sel then reaper.GetSet_LoopTimeRange(true, true, sv.sel[1], sv.sel[2], false) end
    R_.on, R_.rate, R_.saved, R_.pitch_switched = false, 1.0, nil, false
  end
  L.publish_reh()
  return true
end

-- (re)lance la boucle : 1 mesure avant son début, pistes musicales coupées pendant cette mesure
function L.loop_restart()
  local lp = L.reh.loop
  if not lp then return end
  mute_music(true)
  L.reh.prebar = true
  reaper.SetEditCurPos(lp.start - lp.pre, true, true)
  if not L.playing() then reaper.OnPlayButton() end
end

function L.loop_set(c, a, b)
  local R_ = L.reh
  if not R_.on then L.set_rehearsal(true) end
  local i = L.song_index(c, a.start + 0.01)
  local lp = { start = a.start, stop = b.stop, song = i, names = (a == b) and a.name or (a.name .. " → " .. b.name),
               a = a.name, b = b.name }
  lp.pre = L.bar_len_before(a.start, c.songs[i] and c.songs[i].bpm)
  mute_music(false)
  R_.loop = lp
  if reaper.GetSet_LoopTimeRange then reaper.GetSet_LoopTimeRange(true, true, lp.start, lp.stop, false) end
  L.publish_reh()
  L.loop_restart()
  return lp
end

-- appui sur la section commençant au temps t : 1er appui = boucle sur cette section,
-- 2e appui sur une autre section du même morceau = boucle de l'une à l'autre (plage)
function L.loop_tap(c, t)
  t = tonumber(t)
  if not t then return false end
  local i = L.song_index(c, t + 0.01)
  local secs = L.song_sections(c, i)
  local k = nil
  for n, x in ipairs(secs) do if math.abs(x.start - t) < 0.05 then k = n end end
  if not k then k = L.section_at(secs, t) end
  if not k then return false end
  local R_ = L.reh
  local an = R_.anchor
  if an and an.song == i and an.k ~= k and R_.loop then
    local lo, hi = math.min(an.k, k), math.max(an.k, k)
    L.loop_set(c, secs[lo], secs[hi])
    R_.anchor = nil
  else
    L.loop_set(c, secs[k], secs[k])
    R_.anchor = { song = i, k = k }
  end
  return true
end

-- à appeler à chaque tour de boucle de la fenêtre (position de lecture précédente / actuelle)
function L.loop_tick(last, now)
  local R_ = L.reh
  local lp = R_.loop
  if not lp then return nil end
  if not L.playing() then
    if R_.prebar then mute_music(false); R_.prebar = false end      -- arrêt pendant la mesure de décompte
    return nil
  end
  if R_.prebar and (now >= lp.start - 0.03 or now < lp.start - lp.pre - 0.5) then
    mute_music(false); R_.prebar = false                             -- début de la boucle (ou saut ailleurs)
    return "start"
  end
  if last and now >= last and now - last < 1.5 and last < lp.stop and now >= lp.stop then
    L.loop_restart()
    return "restart"
  end
  return nil
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
  elseif cmd == "reh" then
    L.set_rehearsal(arg == "1")
  elseif cmd == "loop" then
    if not L.loop_tap(c, arg) then return false end
  elseif cmd == "loopoff" then
    L.loop_off()
  elseif cmd == "rate" then
    if not L.reh.on then L.set_rehearsal(true) end
    if not L.set_rate(arg) then return false end
  elseif cmd == "mute" then
    if not L.mix_toggle(c, arg) then return false end
  elseif cmd == "solo" then
    if not L.mix_solo(c, arg) then return false end
  elseif cmd == "hearall" then
    L.mix_hear_all(c, arg == "1")
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

-- téléphones Régie : la page écrit ReaCue/remote_seen (valeur qui change) toutes les quelques secondes
local last_seen_v = nil
function L.poll_seen(now)
  local v = reaper.GetExtState(REMOTE, "remote_seen")
  if v ~= "" and v ~= last_seen_v then
    if last_seen_v ~= nil then L.regie_seen = now or reaper.time_precise() end
    last_seen_v = v
  end
end

-- ---------------------------------------------------------------------------------------
-- Instruments (stems) : mute / solo par instrument et profil « joué en live » du concert.
-- Profil enregistré dans <concert>.setlist.json : "live" = rôles joués en vrai (stems coupés),
-- "live_exceptions" = {titre: {rôle: "live"|"stem"}}. Les choix manuels (mute, solo) valent pour le
-- morceau en cours : en entrant dans un autre morceau, le profil (et ses exceptions) s'applique.
-- ---------------------------------------------------------------------------------------
L.ROLES = {          -- même ordre et mêmes noms que reacue_mcp/concert.py (ROLE_TRACKS_I18N)
  { "vocals", "Chant", "Vocals", { 212, 83, 126 } },
  { "drums", "Batterie", "Drums", { 186, 117, 23 } },
  { "bass", "Basse", "Bass", { 24, 95, 165 } },
  { "guitars", "Guitares", "Guitars", { 99, 153, 34 } },
  { "lead_guitar", "Guitare solo", "Lead guitar", { 15, 110, 86 } },
  { "keys", "Claviers", "Keys", { 127, 119, 221 } },
  { "other", "Autres", "Other", { 136, 135, 128 } },
  { "mix", "Mix", "Mix", { 95, 94, 90 } },
}
local ROLE_BY_NAME = {}
for _, r in ipairs(L.ROLES) do ROLE_BY_NAME[r[2]:lower()] = r[1]; ROLE_BY_NAME[r[3]:lower()] = r[1] end
-- pistes d'un morceau séparé par ReaCue (« Guitare », « Piano »…) : mêmes rôles
for k, v in pairs({ guitare = "guitars", guitar = "guitars", piano = "keys", clavier = "keys", synth = "keys",
                    batt = "drums", ["lead guitars"] = "lead_guitar" }) do
  ROLE_BY_NAME[k] = v
end
function L.role_info(role)
  for _, r in ipairs(L.ROLES) do if r[1] == role then return r end end
  return nil
end
function L.role_label(role)
  local r = L.role_info(role)
  if not r then return role end
  return L.lang() == "en" and r[3] or r[2]
end
-- rôle d'une piste commune du concert (« Basse », « Bass 2 »…) ou nil
function L.role_of_track(name)
  local n = (name or ""):gsub("%s+%d+$", ""):lower()
  return ROLE_BY_NAME[n]
end
-- noms acceptés pour un rôle (commandes distantes) : rôle, nom FR ou EN
function L.norm_role(x)
  x = tostring(x or ""):lower()
  for _, r in ipairs(L.ROLES) do
    if x == r[1] or x == r[2]:lower() or x == r[3]:lower() then return r[1] end
  end
  return nil
end

-- pistes d'instruments présentes, dans l'ordre des rôles : {role, label, color, tracks}
function L.instr_tracks()
  local by = {}
  for i = 0, (reaper.CountTracks and reaper.CountTracks(0) or 0) - 1 do
    local tr = reaper.GetTrack(0, i)
    local role = L.role_of_track(track_name(tr))
    if role then by[role] = by[role] or {}; table.insert(by[role], tr) end
  end
  local out = {}
  for _, r in ipairs(L.ROLES) do
    if by[r[1]] then out[#out + 1] = { role = r[1], label = L.role_label(r[1]), color = r[4], tracks = by[r[1]] } end
  end
  return out
end

L.mix = { live = {}, exc = {}, manual = {}, solo = nil, hear_all = false, song = nil, src = nil, t = -1e9 }

-- relit le profil dans la setlist du concert ; true s'il a changé
function L.load_live(c, force)
  local M = L.mix
  local src = c and c.setlist and L.read(c.setlist) or nil
  if not force and src == M.src then return false end
  M.src = src
  M.live, M.exc = {}, {}
  local d = src and R.json_decode(src)
  if type(d) == "table" then
    for _, r in ipairs(type(d.live) == "table" and d.live or {}) do
      local role = L.norm_role(r)
      if role then M.live[role] = true end
    end
    if type(d.live_exceptions) == "table" then
      for title, v in pairs(d.live_exceptions) do
        if type(v) == "table" then
          M.exc[title] = {}
          for r, m in pairs(v) do
            local role = L.norm_role(r)
            if role and (m == "live" or m == "stem") then M.exc[title][role] = m end
          end
        end
      end
    end
  end
  return true
end

-- mode du profil pour le rôle dans le morceau i : "live" (stem coupé) ou "stem" (stem joué)
function L.profile_mode(c, i, role)
  local s = c and c.songs and c.songs[i]
  local e = s and L.mix.exc[s.title]
  if e and e[role] then return e[role] end
  return L.mix.live[role] and "live" or "stem"
end

-- le stem du rôle doit-il s'entendre ?
function L.mix_audible(c, i, role)
  local M = L.mix
  if M.hear_all then return true end
  if M.solo then return role == M.solo end
  if M.manual[role] ~= nil then return M.manual[role] end
  return L.profile_mode(c, i, role) ~= "live"
end

-- mute voulu d'une piste (tient compte de la mesure de décompte de la répétition)
function L.track_mute_wanted(tr)
  if L.reh.muted then
    for _, x in ipairs(L.reh.muted) do if x[1] == tr then return x[2] end end
  end
  return reaper.GetMediaTrackInfo_Value(tr, "B_MUTE")
end

-- pose le mute voulu ; pendant la mesure de décompte, les pistes restent coupées et l'état voulu est
-- mémorisé pour être rétabli au début de la section
function L.set_track_mute(tr, v)
  if L.reh.muted then
    for _, x in ipairs(L.reh.muted) do
      if x[1] == tr then x[2] = v; return end
    end
  end
  if reaper.GetMediaTrackInfo_Value(tr, "B_MUTE") ~= v then reaper.SetMediaTrackInfo_Value(tr, "B_MUTE", v) end
end

function L.mix_publish(c, i)
  local M = L.mix
  local parts = {}
  for _, g in ipairs(L.instr_tracks()) do
    parts[#parts + 1] = g.role .. "=" .. (L.mix_audible(c, i, g.role) and "1" or "0") ..
      (L.profile_mode(c, i, g.role) == "live" and "L" or "")
  end
  reaper.SetExtState("ReaCue", "mix", table.concat(parts, ",") .. ";" .. (M.solo or "") .. ";" ..
    (M.hear_all and "1" or "0") .. ";" .. tostring(i or 0), false)
end

function L.mix_apply(c, i)
  if not c then return end
  i = i or L.song_index(c, L.pos())
  for _, g in ipairs(L.instr_tracks()) do
    local v = L.mix_audible(c, i, g.role) and 0 or 1
    for _, tr in ipairs(g.tracks) do L.set_track_mute(tr, v) end
  end
  L.mix_publish(c, i)
end

local function cur_song(c) return L.song_index(c, L.pos()) end

function L.mix_toggle(c, role)
  role = L.norm_role(role)
  if not c or not role then return false end
  local i = cur_song(c)
  local now = L.mix_audible(c, i, role)
  local M = L.mix
  if M.hear_all or M.solo then           -- quitter « tout entendre » / solo en gardant ce qu'on entend
    for _, g in ipairs(L.instr_tracks()) do M.manual[g.role] = L.mix_audible(c, i, g.role) end
    M.hear_all, M.solo = false, nil
  end
  M.manual[role] = not now
  L.mix_apply(c, i)
  return true
end

function L.mix_solo(c, role)
  role = L.norm_role(role)
  if not c or not role then return false end
  local M = L.mix
  M.solo = (M.solo == role) and nil or role
  M.hear_all = false
  L.mix_apply(c)
  return true
end

-- « Tout entendre » : tous les stems ; off = retour au profil (choix manuels effacés)
function L.mix_hear_all(c, on)
  local M = L.mix
  M.hear_all = on and true or false
  M.solo = nil
  M.manual = {}
  L.mix_apply(c)
  return true
end

function L.mix_reset(c)
  local M = L.mix
  M.manual, M.solo, M.hear_all = {}, nil, false
  L.mix_apply(c)
end

-- à chaque tour de boucle : entrée dans un autre morceau, profil modifié (Claude, autre fenêtre)
function L.mix_tick(c, now)
  if not c then return false end
  local M = L.mix
  local i = cur_song(c)
  local changed = false
  now = now or reaper.time_precise()
  if now - M.t > 1.5 then
    M.t = now
    if L.load_live(c) then changed = true end
  end
  if i ~= M.song then
    M.song = i
    M.manual, M.solo = {}, nil
    changed = true
  end
  if changed then L.mix_apply(c, i) end
  return changed
end

-- édition du profil (fenêtre) : écrit la setlist (les autres champs sont gardés)
local SETLIST_ORDER = { "name", "gap_s", "songs", "live", "live_exceptions" }
local function save_profile(c)
  local src = c and c.setlist and L.read(c.setlist)
  local d = src and R.json_decode(src)
  if type(d) ~= "table" then return false end
  local live = R.json_array({})
  for _, r in ipairs(L.ROLES) do if L.mix.live[r[1]] then live[#live + 1] = r[1] end end
  d.live = live
  local exc = {}
  for title, v in pairs(L.mix.exc) do
    local e, any = {}, false
    for role, m in pairs(v) do
      if (m == "live") ~= (L.mix.live[role] == true) then e[role] = m; any = true end
    end
    if any then exc[title] = e end
  end
  d.live_exceptions = exc
  local txt = R.json_encode(d, "  ", SETLIST_ORDER)
  if not R.write_atomic(c.setlist, txt) then return false end
  L.mix.src = L.read(c.setlist)
  return true
end

function L.live_toggle(c, role)
  role = L.norm_role(role)
  if not c or not role then return false end
  L.load_live(c, true)
  L.mix.live[role] = not L.mix.live[role] or nil
  local ok = save_profile(c)
  L.mix_apply(c)
  return ok
end

-- exception du morceau k pour le rôle : nil (profil) → inverse du profil → … (cycle)
function L.live_exc_cycle(c, k, role)
  role = L.norm_role(role)
  local s = c and c.songs[k]
  if not s or not role then return false end
  L.load_live(c, true)
  local e = L.mix.exc[s.title] or {}
  local base = L.mix.live[role] and "live" or "stem"
  if e[role] == nil then e[role] = (base == "live") and "stem" or "live" else e[role] = nil end
  L.mix.exc[s.title] = e
  local ok = save_profile(c)
  L.mix_apply(c)
  return ok
end

function L._reset_remote() seen, seen_list = {}, {}; last_seen_v = nil; L.regie_seen = nil end

return L

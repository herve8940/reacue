-- ReaCue : assistant de premier lancement / first-launch assistant (aussi : Réglages > Vérifier l'installation).
-- Vérifie le pont, l'interface web (port), l'adresse IP, le programme ReaCue, la séparation de stems,
-- l'analyse de structure (SongFormer) et les dossiers ; pour chaque point manquant : explication + bouton.
-- Vu une fois : ExtState persistant « assistant_seen ».
return function(ctx)
  local L, U, R, SEP = ctx.L, ctx.U, ctx.R, ctx.SEP
  local TXT = {
    fr = {
      title = "Bienvenue dans ReaCue", title_check = "Vérifier l'installation",
      intro = "ReaCue vérifie que tout est prêt. Un point rouge ou orange : clique sur le bouton à droite.",
      all_ok = "Tout est prêt ✓", n_missing = "%d point(s) à régler", again = "Revérifier", done = "Terminer",
      bridge = "Pont ReaCue (dans REAPER)", bridge_ok = "démarré", bridge_bad = "arrêté : il fait le lien entre la fenêtre et l'analyse",
      bridge_fix = "Démarrer",
      web = "Interface web (téléphones)", web_ok = "port %d", web_bad = "pas activée : Préférences > Contrôle/OSC/web > Ajouter > Interface web",
      web_fix = "Préférences",
      ip = "Adresse sur le réseau", ip_ok = "%s", ip_bad = "aucune : connecte l'ordinateur au Wi-Fi des téléphones",
      prog = "Programme ReaCue", prog_ok = "installé", prog_bad = "introuvable : relance « Install ReaCue » (REAPER fermé)",
      prog_fix = "Dossier",
      stems = "Séparation de stems (Demucs)", stems_ok = "installée", stems_bad = "non installée : un MP3 ne pourra pas être découpé en stems",
      structure = "Analyse de structure (SongFormer)", structure_ok = "installée : utilisée par défaut",
      structure_bad = "non installée : ReaCue utilise sa détection simple (moins précise)",
      install = "Installer",
      folders = "Dossier des projets", folders_ok = "%s", folders_bad = "absent : %s", folders_fix = "Créer",
      optional = "facultatif",
    },
    en = {
      title = "Welcome to ReaCue", title_check = "Check the installation",
      intro = "ReaCue checks that everything is ready. A red or orange dot: click the button on the right.",
      all_ok = "Everything is ready ✓", n_missing = "%d item(s) to set up", again = "Check again", done = "Finish",
      bridge = "ReaCue bridge (in REAPER)", bridge_ok = "running", bridge_bad = "stopped: it links the window and the analysis",
      bridge_fix = "Start",
      web = "Web interface (phones)", web_ok = "port %d", web_bad = "not enabled: Preferences > Control/OSC/web > Add > Web browser interface",
      web_fix = "Preferences",
      ip = "Network address", ip_ok = "%s", ip_bad = "none: connect the computer to the phones' Wi-Fi",
      prog = "ReaCue program", prog_ok = "installed", prog_bad = "not found: run “Install ReaCue” again (REAPER closed)",
      prog_fix = "Folder",
      stems = "Stem separation (Demucs)", stems_ok = "installed", stems_bad = "not installed: an MP3 cannot be split into stems",
      structure = "Structure analysis (SongFormer)", structure_ok = "installed: used by default",
      structure_bad = "not installed: ReaCue uses its simple detection (less accurate)",
      install = "Install",
      folders = "Projects folder", folders_ok = "%s", folders_bad = "missing: %s", folders_fix = "Create",
      optional = "optional",
    },
  }
  local function t(k) return ctx.tr(TXT, k) end
  local A = { list = nil, first = false }

  local function dir_exists(d)
    if not d or d == "" then return false end
    if reaper.EnumerateFiles and reaper.EnumerateFiles(d, 0) then return true end
    if reaper.EnumerateSubdirectories and reaper.EnumerateSubdirectories(d, 0) then return true end
    local f = io.open(d .. SEP .. ".", "rb")
    if f then f:close() return true end
    return L.exists(d)
  end

  function A.run_checks()
    local out = {}
    local function add(id, ok, label, detail, fix, fix_label, warn)
      out[#out + 1] = { id = id, ok = ok, label = label, detail = detail, fix = fix, fix_label = fix_label, warn = warn }
    end
    local inst = R.install_dir(ctx.dir)
    local win = R.is_windows()
    add("bridge", R.bridge_alive and R.bridge_alive() or false, t("bridge"), nil, "bridge", t("bridge_fix"))
    local port, found = L.web_port()
    add("web", found and true or false, t("web"), found and string.format(t("web_ok"), port) or t("web_bad"), "web", t("web_fix"))
    local ips = L.local_ips()
    add("ip", #ips > 0, t("ip"), #ips > 0 and string.format(t("ip_ok"), L.prompter_url(ips[1], port)) or t("ip_bad"))
    add("prog", L.exists(R.python(inst, win)), t("prog"), nil, "install", t("prog_fix"))
    add("stems", L.exists(ctx.S.python(inst, win)), t("stems"), nil, "stems", t("install"), true)
    add("structure", R.structure_installed(inst, win) and true or false, t("structure"), nil, "structure", t("install"), true)
    local pd = L.projects_dir()
    add("folders", dir_exists(pd), t("folders"), nil, "folders", t("folders_fix"))
    for _, x in ipairs(out) do
      if not x.detail then x.detail = x.ok and t(x.id .. "_ok") or t(x.id .. "_bad") end
      if x.id == "folders" then x.detail = string.format(x.detail, pd) end
    end
    A.list = out
    return out
  end

  function A.open(first)
    A.first = first and true or false
    A.run_checks()
    ctx.overlay = "assistant"
  end

  function A.close()
    reaper.SetExtState("ReaCue", "assistant_seen", "1", true)
    ctx.overlay = nil
    A.list = nil
  end

  -- premier lancement : ouvert une fois (puis Réglages > Vérifier l'installation)
  function A.maybe_first()
    if reaper.GetExtState("ReaCue", "assistant_seen") == "" then A.open(true) return true end
    return false
  end

  local function fix(x)
    if x.fix == "folders" then reaper.RecursiveCreateDirectory(L.projects_dir(), 0)
    else ctx.do_action(x.fix) end
    A.recheck_at = reaper.time_precise() + 0.8
  end

  function A.draw(x, y, w)
    if not A.list then A.run_checks() end
    if A.recheck_at and reaper.time_precise() >= A.recheck_at then A.recheck_at = nil; A.run_checks() end
    U.text(A.first and t("title") or t("title_check"), x, y, 18, U.INK, true)
    if U.button("as_done", t("done"), x + w - 100, y - 4, 100, 30, "primary") then A.close() return y + 30 end
    if U.button("as_again", t("again"), x + w - 100 - 8 - 110, y - 4, 110, 30) then A.run_checks() end
    y = y + 34
    y = y + U.para(t("intro"), x, y, w, 12, U.MUTED, 2) + 6
    local miss = 0
    for _, it in ipairs(A.list) do if not it.ok then miss = miss + 1 end end
    local col = miss == 0 and U.ACCENT or U.WARN
    U.set(col, 0.22); gfx.rect(x, y, w, 32, 1)
    U.set(col); gfx.roundrect(x, y, w - 1, 31, 6, 1)
    U.text(miss == 0 and t("all_ok") or string.format(t("n_missing"), miss), x + 12, y + 7, 15, U.INK, true)
    y = y + 44
    for k, it in ipairs(A.list) do
      local c = it.ok and U.ACCENT or (it.warn and U.WARN or U.RED)
      local fx = (not it.ok) and it.fix
      local bw = fx and (U.text_w(it.fix_label, 12) + 22) or 0
      local tw = w - 26 - (fx and bw + 8 or 0)
      U.set(c); gfx.circle(x + 10, y + 10, 6, 1, 1)
      local lab = it.label .. ((it.warn and not it.ok) and ("  ·  " .. t("optional")) or "")
      U.text(U.fit(lab, tw, 14, true), x + 24, y + 2, 14, U.INK, true)
      U.text(U.fit(it.detail, tw, 12), x + 24, y + 21, 12, it.ok and U.MUTED or U.INK)
      if fx and U.button("as_fix" .. k, it.fix_label, x + w - bw, y + 6, bw, 26) then fix(it) end
      y = y + 42
    end
    return y + 6
  end

  ctx.assistant = A
  ctx.overlays.assistant = A.draw
  return A
end

-- ReaCue : concert, aller au début du morceau suivant (pédale, raccourci, bouton de barre d'outils).
-- ReaCue: concert, go to the start of the next song (pedal, shortcut, toolbar button).
local dir = debug.getinfo(1, "S").source:match("^@?(.*[/\\])") or ""
local L = dofile(dir .. "ReaCue_concert_lib.lua")
local c = L.load_concert()
if not c then
  reaper.ShowMessageBox(L.tr("not_concert"), "ReaCue", 0)
  return
end
L.next(c)

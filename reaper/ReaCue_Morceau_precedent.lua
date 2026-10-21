-- ReaCue : concert, revenir au début du morceau en cours, ou au morceau précédent si on y est déjà.
-- ReaCue: concert, go back to the start of the current song, or to the previous song if already there.
local dir = debug.getinfo(1, "S").source:match("^@?(.*[/\\])") or ""
local L = dofile(dir .. "ReaCue_concert_lib.lua")
local c = L.load_concert()
if not c then
  reaper.ShowMessageBox(L.tr("not_concert"), "ReaCue", 0)
  return
end
L.prev(c)

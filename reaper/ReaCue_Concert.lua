-- ReaCue - Concert : ouvre la fenêtre ReaCue sur l'onglet « Scène » (pilotage du concert).
-- ReaCue - Concert: opens the ReaCue window on the “Stage” tab (concert control).
-- (Compatibilité : l'ancienne fenêtre Concert fait maintenant partie de la fenêtre ReaCue.)
local dir = debug.getinfo(1, "S").source:match("^@?(.*[/\\])") or ""
REACUE_START_TAB = "stage"
dofile(dir .. "ReaCue.lua")

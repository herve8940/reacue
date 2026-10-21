-- ReaCue - Préparer le morceau / Prepare the song
-- Analyse les stems (ou le fichier audio) du projet et crée tout : tempo, régions, click,
-- annonces vocales, décomptes, puis publie le prompteur des musiciens (accords, paroles, batterie).
-- Enregistrée par l'installateur ; sinon : Actions > Show action list > New action > Load ReaScript.
local dir = ({ reaper.get_action_context() })[2]:match("^(.*)[/\\]")
local M = dofile(dir .. "/ReaCue_run.lua")
M.run("prepare", nil, dir)

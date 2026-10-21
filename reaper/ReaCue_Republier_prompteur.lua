-- ReaCue - Republier le prompteur / Republish the prompter
-- Remet à jour la page des musiciens (après avoir ajouté paroles.txt / lyrics.txt ou le fichier
-- d'ancres), sans rien modifier dans le projet REAPER.
local dir = ({ reaper.get_action_context() })[2]:match("^(.*)[/\\]")
local M = dofile(dir .. "/ReaCue_run.lua")
M.run("publish", nil, dir)

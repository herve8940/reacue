-- ReaCue - Séparer les stems / Separate stems
-- Sépare l'item audio sélectionné (MP3/WAV du morceau) en stems avec Demucs, en local, puis les importe
-- sur une piste chacun à la place de l'item d'origine. Ensuite : « ReaCue - Préparer le morceau ».
-- Nécessite la séparation de stems installée (« Install ReaCue Stems »).
local dir = ({ reaper.get_action_context() })[2]:match("^(.*)[/\\]")
local S = dofile(dir .. "/ReaCue_stems.lua")
S.run(dir)

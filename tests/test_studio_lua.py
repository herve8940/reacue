"""ReaCue Studio côté REAPER (Lua 5.4 via lupa, API REAPER simulée) : commandes de la télécommande ajoutées
pour la page studio.html — boucle d'une section, rampe de vitesse par passages, transposition des stems,
export audio (tâche écrite + CLI lancée) — état publié (ReaCue/studio) et copie de la page dans reaper_www_root."""
import json
from pathlib import Path

import pytest

pytest.importorskip("lupa")

import test_concert_lua as TL  # noqa: E402
import test_reacue_window as TW  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]

ITEMS_API = r"""
reaper.CountTrackMediaItems = function(tr) local n = 0; for _, it in ipairs(ITEMS) do if TRACKS[it.track] == tr then n = n + 1 end end; return n end
reaper.GetTrackMediaItem = function(tr, k)
  local n = 0
  for _, it in ipairs(ITEMS) do if TRACKS[it.track] == tr then if n == k then return it end; n = n + 1 end end
end
reaper.GetMediaItemInfo_Value = function(it, k)
  if k == "D_POSITION" then return it.pos or 0 elseif k == "D_LENGTH" then return it.len or 10 elseif k == "D_VOL" then return it.vol or 1 end
  return 0 end
reaper.GetMediaItemTakeInfo_Value = function(tk, k)
  if k == "D_PITCH" then return tk.pitch or 0 elseif k == "D_STARTOFFS" then return tk.offs or 0
  elseif k == "D_PLAYRATE" then return tk.rate or 1 elseif k == "D_VOL" then return tk.tvol or 1 end
  return 0 end
reaper.SetMediaItemTakeInfo_Value = function(tk, k, v) if k == "D_PITCH" then tk.pitch = v end end
reaper.GetTrackGUID = function(tr) return "{" .. tr.name .. "}" end
reaper.UpdateArrange = function() end
"""


@pytest.fixture(scope="module")
def concert(tmp_path_factory):
    return TL.make_concert(tmp_path_factory.mktemp("studio"))


def rt(concert, items=""):
    L, g = TW.rt(concert)
    L.execute(ITEMS_API)
    L.execute("ITEMS = {" + items + "}")
    return L, g


def send(M, g, c, cmd, arg="", n=[0]):
    n[0] += 1
    g.state.ext["remote"] = f"{cmd}|{arg}|{M.remote_pin()}|s{n[0]}"
    return tuple(M.remote_poll(c))


def test_loop_section_and_speed_ramp(concert):
    L, g = rt(concert)
    M = TL.lib(L)
    c = M.load_concert()
    secs = M.song_sections(c, 3)
    st = g.state
    assert send(M, g, c, "loopsec", f"{secs[2].start:.3f}") == ("loopsec", "ok")
    assert M.reh.loop.start == pytest.approx(secs[2].start) and M.reh.loop.stop == pytest.approx(secs[2].stop)
    assert M.reh.anchor is None and st.play == 1                         # lecture 1 mesure avant la section
    # rampe 80 -> 100 % en 3 passages sur la boucle en cours
    assert send(M, g, c, "ramp", "0.80:1.00:3") == ("ramp", "ok")
    assert st.rate == pytest.approx(0.8) and M.reh.ramp["pass"] == 1
    assert st.ext["studio"].split("|")[2:] == ["1", "3", "0.80", "1.00"]
    M.loop_restart(); assert st.rate == pytest.approx(0.9)               # 2e passage
    M.loop_restart(); assert st.rate == pytest.approx(1.0)
    M.loop_restart(); assert st.rate == pytest.approx(1.0) and M.reh.ramp["pass"] == 4
    M.studio_publish(True)
    assert st.ext["studio"] == "1.000|0|4|3|0.80|1.00"
    # boucle par la fin de boucle réelle (loop_tick) : un passage de plus
    send(M, g, c, "ramp", f"0.85:1.00:8:{secs[1].start:.3f}")
    assert M.reh.loop.start == pytest.approx(secs[1].start) and st.rate == pytest.approx(0.85) and M.reh.ramp["pass"] == 1
    st.play = 1
    assert M.loop_tick(secs[1].start - 0.1, secs[1].start) == "start"       # fin de la mesure de décompte
    assert M.loop_tick(secs[1].stop - 0.02, secs[1].stop + 0.01) == "restart"
    assert M.reh.ramp["pass"] == 2 and st.rate == pytest.approx(0.85 + 0.15 / 7)
    assert send(M, g, c, "ramp", "0.3:1:8") == ("ramp", "bad")
    assert send(M, g, c, "ramp", "0.9:1:1") == ("ramp", "bad")
    # arrêt de la boucle : rampe arrêtée, vitesse normale
    assert send(M, g, c, "loopoff") == ("loopoff", "ok")
    assert M.reh.ramp is None and st.rate == pytest.approx(1.0)
    assert send(M, g, None, "loopsec", "12") == ("loopsec", "noconcert")
    M.set_rehearsal(False)


def test_transpose_stems_only(concert):
    res = concert[0]
    s2, s3 = res.songs[1], res.songs[2]
    items = (f"{{track=1, pos={s2['start'] + 1}}}, {{track=3, pos={s2['start'] + 1}, pitch=0.5}}, "
             f"{{track=3, pos={s3['start'] + 1}}}, {{track=7, pos={s2['start'] + 1}}}, {{track=6, pos={s2['start'] + 1}}}")
    L, g = rt(concert, items)
    M = TL.lib(L)
    it = lambda: [round(float(x.pitch or 0), 3) for x in g.ITEMS.values()]
    # sans concert (projet quelconque) : toutes les prises des stems, pas CLICK ni VOIX
    assert send(M, g, None, "pitch", "+1") == ("pitch", "ok")
    assert it() == [1.0, 1.5, 1.0, 0.0, 0.0]
    assert g.state.ext["studio"].split("|")[1] == "1" and g.state.undo >= 1
    assert send(M, g, None, "pitch", "+12") == ("pitch", "bad")          # au-delà de +12
    assert send(M, g, None, "pitch", "x") == ("pitch", "bad")
    assert send(M, g, None, "pitch", "0") == ("pitch", "ok") and it() == [0.0, 0.5, 0.0, 0.0, 0.0]
    # concert : seulement le morceau en cours
    c = M.load_concert()
    g.state.cursor = s2["start"] + 2
    assert send(M, g, c, "pitch", "-2") == ("pitch", "ok")
    assert it() == [-2.0, -1.5, 0.0, 0.0, 0.0]
    assert M.transpose_get(c) == -2


def test_export_job_and_cli(concert, tmp_path):
    inst = tmp_path / "ReaCue"
    (inst / ".venv" / "bin").mkdir(parents=True)
    (inst / ".venv" / "bin" / "python").write_text("")
    items = ("{track=2, pos=1.5, len=18, offs=0.25, file='/s/drums.wav'}, {track=3, pos=0, file='/s/bass.wav', vol=0.5}, "
             "{track=5, pos=0, file='/s/cues.wav'}, {track=6, pos=3, file='/v/refrain.wav'}")
    L, g = rt(concert, items)
    g.state.ext["install_dir"] = str(inst)
    M = TL.lib(L)
    c = M.load_concert()
    req = {"id": "ab12", "stems": ["Batterie"], "format": "mp3", "kbps": 320, "range": {"kind": "selection"}}
    g.state.ext["export_req"] = json.dumps(req)
    assert send(M, g, c, "export", "zz99") == ("export", "bad")          # identifiant différent
    g.state.ext["export_req"] = json.dumps(req)
    g.state.sel = L.table_from([12.0, 20.0])
    assert send(M, g, None, "export", "ab12") == ("export", "ok")        # possible sans concert
    rdir = Path(g.RES)
    job = json.loads((rdir / "ReaCueMCP" / "export_job.json").read_text(encoding="utf-8"))
    assert job["id"] == "ab12" and job["request"]["format"] == "mp3" and job["selection"] == [12, 20]
    names = [t["name"] for t in job["tracks"]]
    assert names == ["Batterie", "Basse", "VOIX"]                        # CUES ignorée ; pistes sans item absentes
    d = job["tracks"][0]["items"][0]
    assert d == {"file": "/s/drums.wav", "position": 1.5, "length": 18, "offset": 0.25, "rate": 1, "vol": 1}
    assert job["tracks"][1]["items"][0]["vol"] == 0.5 and job["tracks"][0]["guid"] == "{Batterie}"
    assert job["project_dir"] == str(Path(str(g.PROJFILE)).parent)
    sh = list(g.state.shell.values())[-1]
    assert "-m reacue_mcp.cli export --job" in sh and "export_job.json" in sh
    st = json.loads((rdir / "reaper_www_root" / "reacue_export.json").read_text(encoding="utf-8"))
    assert st["id"] == "ab12" and st["state"] == "running"
    # un autre export en cours (récent) : refusé
    g.state.ext["export_req"] = json.dumps({**req, "id": "cd34"})
    assert send(M, g, c, "export", "cd34") == ("export", "bad")


def test_publish_page_copies_studio(concert):
    L, g = rt(concert)
    g.state.ext["install_dir"] = str(ROOT)
    M = TL.lib(L)
    assert M.publish_page()
    www = Path(g.RES) / "reaper_www_root"
    for rel in M.STUDIO_FILES.values():
        assert (www / rel).read_bytes() == (ROOT / "reacue_mcp" / "web" / rel).read_bytes(), rel
    assert M.studio_url("10.0.0.5", 8080) == "http://10.0.0.5:8080/studio.html"

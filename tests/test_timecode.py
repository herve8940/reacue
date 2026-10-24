"""Timecode vers grandMA3 : réglages, pistes TIMECODE LTC / MTC créées par le pont (API REAPER simulée),
idempotence, mémorisation du réglage du générateur, concert (une seule piste sur toute la durée),
plugin grandMA3 (API grandMA3 simulée), export de la clé USB, onglet Lumière. Données fictives."""
import asyncio
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import concert_demo as D  # noqa: E402
from reacue_mcp import concert as C, i18n, lighting as LG, settings, timecode as TC  # noqa: E402
from reacue_mcp.bridge import to_lua  # noqa: E402

lupa = pytest.importorskip("lupa")
from lupa import lua54  # noqa: E402

LUA_DIR = ROOT / "reaper"
PAGE = (ROOT / "reacue_mcp" / "web" / "prompteur.html").read_text(encoding="utf-8")


def cfg(**kw):
    return TC.config({**settings.DEFAULTS, **kw})


@pytest.fixture(autouse=True)
def clean_templates():
    import shutil
    shutil.rmtree(TC.template_dir(), ignore_errors=True)
    yield
    shutil.rmtree(TC.template_dir(), ignore_errors=True)


# --------------------------------------------------------------------------- réglages
@pytest.mark.parametrize("v,dst,src,label", [
    (7, 6 | 1024, 1024, "7"), ("7", 6 | 1024, 1024, "7"), ("7/8", 6, 0, "7/8"), ("7-8", 6, 0, "7/8"),
    (" 1 + 2 ", 0, 0, "1/2"), (3.0, 2 | 1024, 1024, "3"), ("3/3", 2 | 1024, 1024, "3"),
])
def test_parse_audio_output(v, dst, src, label):
    assert TC.parse_audio_output(v) == {"dst": dst, "src": src, "label": label}


@pytest.mark.parametrize("v", [None, "", 0, "0", False, True, "off", "7/9", "x", -2, 2.5, "0/1"])
def test_parse_audio_output_empty_or_bad(v):
    assert TC.parse_audio_output(v) is None


def test_settings_defaults_off_and_config():
    s = settings.load_settings(Path("/nonexistent/settings.json"))
    assert (s["gma3_ltc_output"], s["gma3_mtc_output"], s["gma3_tc_slot"]) == (None, None, 1)
    import reacue_setup as RS
    for k in ("gma3_ltc_output", "gma3_mtc_output", "gma3_tc_slot"):
        assert RS.SETTINGS_DEFAULTS[k] == settings.DEFAULTS[k]
        for doc in ("README.md", "LISEZMOI.md"):
            assert f"`{k}`" in (ROOT / doc).read_text(encoding="utf-8"), (doc, k)
    c = cfg()
    assert not c["enabled"] and c["ltc"] is None and c["mtc"] is None and c["slot"] == 1
    c = cfg(gma3_ltc_output=7, gma3_mtc_output=" IAC Driver Bus 1 ", gma3_tc_slot="3", gma3_fps=30,
            gma3_tc_start="01:00:00:00")
    assert c["enabled"] and c["ltc"]["label"] == "7" and c["mtc"] == "IAC Driver Bus 1" and c["slot"] == 3
    assert (c["fps"], c["offset_s"]) == (30.0, 3600.0)
    assert cfg(gma3_tc_slot=9)["slot"] == 1 and cfg(gma3_tc_slot="x")["slot"] == 1
    assert TC.template_key("ltc", c) == "ltc_30_01-00-00-00"
    assert TC.template_key("mtc", cfg(gma3_fps=29.97)) == "mtc_29.97_00-00-00-00"


def test_plan_block_and_templates():
    c = cfg(gma3_ltc_output="7/8", gma3_mtc_output="IAC")
    b = TC.plan_block(c, 61.2)
    assert b["min_len"] == 61.2 and b["fps"] == 25.0 and b["tc_start"] == "00:00:00:00"
    ltc, mtc = b["tracks"]
    assert (ltc["name"], ltc["kind"], ltc["audio_dst"], ltc["audio_src"], ltc["template"]) == ("TIMECODE LTC", "ltc", 6, 0, None)
    assert (mtc["name"], mtc["kind"], mtc["midi_out"]) == ("TIMECODE MTC", "mtc", "IAC")
    p = TC.template_dir() / f"{ltc['key']}.txt"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("  <SOURCE LTC\n  X 1\n  >\n", encoding="utf-8")
    assert TC.plan_block(c, 1)["tracks"][0]["template"] == "<SOURCE LTC\nX 1\n>"
    p.write_text("<SOURCE WAVE\nFILE x\n>\n", encoding="utf-8")         # autre chose : ignoré
    assert TC.plan_block(c, 1)["tracks"][0]["template"] is None
    assert TC.plan_block(cfg(), 1)["tracks"] == []


def test_is_source_block():
    assert TC.is_source_block("<SOURCE LTC\nA 1\n<SUB\n>\n>")
    assert not TC.is_source_block("<SOURCE LTC\nA 1\n")
    assert not TC.is_source_block("<SOURCE LTC\n>\n>")
    assert not TC.is_source_block("<SOURCE CLICK\n>") and not TC.is_source_block(None)


def test_handle_result_remembers_user_setting(lang):
    lang("fr")
    c = cfg(gma3_ltc_output=7, gma3_mtc_output="IAC")
    k_ltc, k_mtc = TC.template_key("ltc", c), TC.template_key("mtc", c)
    dflt = "<SOURCE LTC\nDEFAULT 1\n>"
    tracks = [{"name": "TIMECODE LTC", "kind": "ltc", "key": k_ltc, "origin": "default", "block": dflt, "item": True,
               "label": "7", "length": 70},
              {"name": "TIMECODE MTC", "kind": "mtc", "key": k_mtc, "origin": "default", "block": dflt, "item": True,
               "midi_out": "IAC", "midi_found": False}]
    summ, warns = TC.handle_result({"tracks": tracks, "warnings": []}, c)
    assert [p["generateur_regle"] for p in summ["pistes"]] == [False, False] and summ["tc_slot"] == 1
    assert any("Send MIDI (MTC)" in w and "décoché" in w for w in warns)
    assert any("cocher « Send MIDI (MTC) »" in w for w in warns)
    assert any("IAC" in w and "introuvable" in w for w in warns)
    assert TC.load_template(k_ltc) is None                     # un réglage par défaut n'est jamais mémorisé
    # préparation suivante, générateur pas touché : toujours à régler
    tracks[0]["origin"] = "kept"
    _, warns = TC.handle_result({"tracks": tracks[:1]}, c)
    assert len(warns) == 1 and TC.load_template(k_ltc) is None
    # réglé par l'utilisateur : mémorisé, plus d'avertissement
    tracks[0]["block"] = "<SOURCE LTC\nUSER 25 3600\n>"
    summ, warns = TC.handle_result({"tracks": tracks[:1]}, c)
    assert warns == [] and summ["pistes"][0]["generateur_regle"] is True
    assert TC.load_template(k_ltc) == "<SOURCE LTC\nUSER 25 3600\n>"
    _, warns = TC.handle_result({"tracks": [dict(tracks[0], origin="template")]}, c)
    assert warns == []
    _, warns = TC.handle_result({"tracks": [dict(tracks[0], item=False, block=None)]}, c)
    assert any("40208" in w for w in warns)
    assert TC.handle_result({"tracks": []}, c) == (None, [])


# --------------------------------------------------------------------------- pont REAPER simulé
FAKE = r"""
local res = ...
reaper = {}
TR, IT, CMDS, NSET = {}, {}, {}, 0
MIDI = { [0] = "Network Session 1", [2] = "IAC Driver Bus 1" }
PROJLEN = 50.0
local SEL, LOOP, MK = nil, {0, 0}, {}
GEN_CHUNK = "<ITEM\nPOSITION 0\nLENGTH 10\n<SOURCE LTC\nDEFAULT 1\n>\n>"
function reaper.GetResourcePath() return res end
function reaper.RecursiveCreateDirectory() return 1 end
function reaper.time_precise() return os.clock() end
function reaper.defer(f) end
function reaper.atexit(f) end
function reaper.GetAppVersion() return "7.27/test" end
function reaper.EnumProjects() return nil, "/tmp/test.rpp" end
function reaper.Undo_BeginBlock() end
function reaper.Undo_EndBlock() end
function reaper.PreventUIRefresh() end
function reaper.UpdateArrange() end
function reaper.UpdateTimeline() end
function reaper.ColorToNative(r, g, b) return r * 65536 + g * 256 + b end
function reaper.CountProjectMarkers() return #MK, #MK, 0 end
function reaper.EnumProjectMarkers(i) local m = MK[i + 1]; return i, false, m, 0, "", i end
function reaper.DeleteProjectMarkerByIndex(_, i) table.remove(MK, i + 1) end
function reaper.AddProjectMarker2(_, rgn, pos) MK[#MK + 1] = pos end
function reaper.CountTempoTimeSigMarkers() return 0 end
function reaper.SetTempoTimeSigMarker() return true end
function reaper.CountTracks() return #TR end
function reaper.GetTrack(_, i) return TR[i + 1] end
function reaper.InsertTrackAtIndex(idx) table.insert(TR, idx + 1, { name = "", ext = {}, its = {}, sends = {}, vals = { B_MAINSEND = 1 } }) end
function reaper.DeleteTrack(tr)
  for i, t in ipairs(TR) do if t == tr then table.remove(TR, i) break end end
  for i = #IT, 1, -1 do if IT[i].tr == tr then table.remove(IT, i) end end
end
function reaper.GetSetMediaTrackInfo_String(tr, k, v, set)
  if k == "P_NAME" then if set then tr.name = v end return true, tr.name end
  local e = k:match("^P_EXT:(.+)$")
  if e then if set then tr.ext[e] = v end return true, tr.ext[e] or "" end
  return false, ""
end
function reaper.SetMediaTrackInfo_Value(tr, k, v) tr.vals[k] = v end
function reaper.GetMediaTrackInfo_Value(tr, k)
  if k == "IP_TRACKNUMBER" then for i, t in ipairs(TR) do if t == tr then return i end end end
  return tr.vals[k] or 0
end
function reaper.SetOnlyTrackSelected(tr) SEL = tr end
function reaper.GetSet_LoopTimeRange(set, _, a, b) if set then LOOP = { a, b } end return LOOP[1], LOOP[2] end
function reaper.GetCursorPosition() return 0 end
function reaper.SetEditCurPos() end
function reaper.GetProjectLength() return PROJLEN end
local function add_item(tr, file, chunk)
  local it = { tr = tr, guid = "{I" .. (#IT + 1) .. "}", vals = { D_POSITION = 3, D_LENGTH = 10 }, chunk = chunk }
  it.take = { src = { file = file } }
  IT[#IT + 1] = it; tr.its[#tr.its + 1] = it
  return it
end
ADD_ITEM = add_item
function reaper.Main_OnCommand(c)
  CMDS[#CMDS + 1] = c
  if c == 40208 and SEL and not NO_GENERATOR then add_item(SEL, "", GEN_CHUNK) end
end
function reaper.CountTrackMediaItems(tr) return #tr.its end
function reaper.GetTrackMediaItem(tr, i) return tr.its[i + 1] end
function reaper.CountMediaItems() return #IT end
function reaper.GetMediaItem(_, i) return IT[i + 1] end
function reaper.CountSelectedMediaItems() return 0 end
function reaper.GetSelectedMediaItem() return nil end
function reaper.GetMediaItem_Track(it) return it.tr end
function reaper.GetActiveTake(it) return it.take end
function reaper.GetMediaItemTake_Source(tk) return tk.src end
function reaper.GetMediaSourceParent() return nil end
function reaper.GetMediaSourceFileName(src) return src.file end
function reaper.GetSetMediaItemInfo_String(it, k) return true, it.guid end
function reaper.SetMediaItemInfo_Value(it, k, v) it.vals[k] = v end
function reaper.GetMediaItemInfo_Value(it, k) return it.vals[k] or 0 end
function reaper.GetMediaItemTakeInfo_Value(tk, k) if k == "D_PLAYRATE" then return 1.0 end return 0.0 end
function reaper.GetItemStateChunk(it) return it.chunk ~= nil, it.chunk or "" end
function reaper.SetItemStateChunk(it, c) it.chunk = c; NSET = NSET + 1; return true end
function reaper.CreateTrackSend(tr, dst) tr.sends[#tr.sends + 1] = {}; return #tr.sends - 1 end
function reaper.SetTrackSendInfo_Value(tr, cat, k, key, v) tr.sends[k + 1][key] = v end
function reaper.GetMaxMIDIOutputs() return 4 end
function reaper.GetMIDIOutputName(i) if MIDI[i] then return true, MIDI[i] end return false, "" end
-- projet : une piste audio
reaper.InsertTrackAtIndex(0); TR[1].name = "Drums"
add_item(TR[1], "/s/drums.wav", nil)
"""


class Reaper:
    def __init__(self, res: Path):
        self.res = res
        (res / "ReaCueMCP").mkdir(parents=True, exist_ok=True)
        self.L = lua54.LuaRuntime(unpack_returned_tuples=True)
        self.L.execute(FAKE, str(res))
        self.g = self.L.globals()

    def call(self, cmd, args=None):
        d = self.res / "ReaCueMCP"
        (d / "request.lua").write_text(to_lua({"id": "t", "cmd": cmd, "args": args or {}}), encoding="utf-8")
        self.L.execute(f"dofile([[{LUA_DIR / 'ReaCue_Bridge.lua'}]])")
        r = json.loads((d / "response.json").read_text(encoding="utf-8"))
        assert r["ok"], r
        return r["result"]

    def apply(self, tc_block):
        plan = {"clear": True, "tempo": [], "regions": [], "markers": [], "cues": {"enabled": False},
                "voice": {"enabled": False}, "click": {"enabled": False}}
        if tc_block is not None:
            plan["timecode"] = tc_block
        return self.call("apply_plan", plan)

    def tracks(self):
        T = self.g.TR
        return [T[i] for i in range(1, len(T) + 1)]

    def track(self, name):
        found = [t for t in self.tracks() if t.name == name]
        assert len(found) <= 1, f"doublon {name}"
        return found[0] if found else None


def test_bridge_creates_timecode_tracks(tmp_path):
    R = Reaper(tmp_path)
    c = cfg(gma3_ltc_output=7, gma3_mtc_output="iac driver")
    res = R.apply(TC.plan_block(c, 61.25))
    tc = res["timecode"]
    assert tc["length"] == 61.25 and [t["origin"] for t in tc["tracks"]] == ["default", "default"]
    assert list(R.g.CMDS.values()).count(40208) == 2
    ltc, mtc = R.track("TIMECODE LTC"), R.track("TIMECODE MTC")
    assert ltc.vals.B_MAINSEND == 0 and mtc.vals.B_MAINSEND == 0 and ltc.vals.D_VOL == TC.LTC_VOLUME
    assert ltc.sends[1].I_DSTCHAN == 6 | 1024 and ltc.sends[1].I_SRCCHAN == 1024 and len(ltc.sends) == 1
    assert len(mtc.sends) == 0 and mtc.vals.I_MIDIHWOUT == 2 << 5              # IAC = périphérique 2, tous canaux
    assert tc["tracks"][1]["midi_found"] is True and tc["tracks"][1]["midi_out"] == "IAC Driver Bus 1"
    for t in (ltc, mtc):
        it = t.its[1]
        assert (it.vals.D_POSITION, it.vals.D_LENGTH, it.vals.B_LOOPSRC, it.vals.C_BEATATTACHMODE) == (0, 61.25, 0, 0)
        assert it.vals.D_FADEINLEN == 0 and it.vals.D_FADEOUTLEN == 0
        assert t.ext["reacue_tc_key"].startswith(("ltc_25_", "mtc_25_"))
    assert tc["tracks"][0]["block"] == "<SOURCE LTC\nDEFAULT 1\n>"
    # projet plus long que le minimum : le timecode couvre tout
    R.g.PROJLEN = 300.0
    res = R.apply(TC.plan_block(c, 61.25))
    assert res["timecode"]["length"] == 300.0 and R.track("TIMECODE LTC").its[1].vals.D_LENGTH == 300.0
    # les items audio ignorent les pistes timecode (analyse, stems)
    items = R.call("get_audio_items")["items"]
    assert [d["file"] for d in items] == ["/s/drums.wav"]


def test_bridge_idempotent_and_keeps_user_setting(tmp_path):
    R = Reaper(tmp_path)
    c = cfg(gma3_ltc_output="7/8")
    R.apply(TC.plan_block(c, 40))
    # l'utilisateur règle le générateur (Propriétés de la source)
    it = R.track("TIMECODE LTC").its[1]
    it.chunk = "<ITEM\nPOSITION 0\nLENGTH 40\n<SOURCE LTC\nUSER 25 0 1\n<SUB\nX\n>\n>\nNAME z\n>"
    for _ in range(3):                                 # préparations répétées : jamais de doublon
        res = R.apply(TC.plan_block(c, 40))
        assert [t.name for t in R.tracks()].count("TIMECODE LTC") == 1
        tr = res["timecode"]["tracks"][0]
        assert tr["origin"] == "kept" and tr["block"] == "<SOURCE LTC\nUSER 25 0 1\n<SUB\nX\n>\n>"
        chunk = R.track("TIMECODE LTC").its[1].chunk
        assert "USER 25 0 1" in chunk and "DEFAULT 1" not in chunk and chunk.startswith("<ITEM")
        assert len(R.track("TIMECODE LTC").sends) == 1 and R.track("TIMECODE LTC").sends[1].I_DSTCHAN == 6
    summ, warns = TC.handle_result(res["timecode"], c)
    assert warns == [] and TC.load_template(TC.template_key("ltc", c)) == tr["block"]
    assert len(R.g.IT) == 2                            # Drums + un seul générateur
    # autre départ / fps : l'ancien réglage ne vaut plus, générateur par défaut à régler
    c2 = cfg(gma3_ltc_output="7/8", gma3_tc_start="01:00:00:00")
    res = R.apply(TC.plan_block(c2, 40))
    assert res["timecode"]["tracks"][0]["origin"] == "default"
    _, warns = TC.handle_result(res["timecode"], c2)
    assert len(warns) == 1 and "01:00:00:00" in warns[0]
    # réglages vidés : pistes retirées
    R.apply(TC.plan_block(cfg(), 40))
    assert R.track("TIMECODE LTC") is None and R.track("TIMECODE MTC") is None
    assert [t.name for t in R.tracks()] == ["Drums"]


def test_bridge_template_new_project_and_failures(tmp_path):
    c = cfg(gma3_ltc_output=1, gma3_mtc_output="Absent device")
    p = TC.template_dir() / f"{TC.template_key('ltc', c)}.txt"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("<SOURCE LTC\nTEMPLATE 1\n>\n", encoding="utf-8")
    R = Reaper(tmp_path)
    res = R.apply(TC.plan_block(c, 30))
    ltc, mtc = res["timecode"]["tracks"]
    assert ltc["origin"] == "template" and "TEMPLATE 1" in R.track("TIMECODE LTC").its[1].chunk
    assert mtc["origin"] == "default" and mtc["midi_found"] is False
    assert R.track("TIMECODE MTC").vals.I_MIDIHWOUT is None       # rien réglé
    _, warns = TC.handle_result(res["timecode"], c)
    assert any("Absent device" in w for w in warns) and not any("TIMECODE LTC" in w for w in warns)
    # générateur impossible à insérer : piste créée quand même, signalé, rien ne casse
    R.g.NO_GENERATOR = True
    res = R.apply(TC.plan_block(c, 30))
    assert [t["item"] for t in res["timecode"]["tracks"]] == [False, False]
    _, warns = TC.handle_result(res["timecode"], c)
    assert sum("40208" in w for w in warns) == 2


def test_bridge_old_plan_without_timecode_still_clears(tmp_path):
    R = Reaper(tmp_path)
    R.apply(TC.plan_block(cfg(gma3_ltc_output=2), 10))
    res = R.apply(None)                                 # plan sans bloc timecode
    assert "timecode" not in res and R.track("TIMECODE LTC") is None


def test_lua_generated_sets_include_timecode():
    for f in ("ReaCue_Bridge.lua", "ReaCue_stems.lua", "ReaCue_tab_song.lua", "ReaCue_concert_lib.lua"):
        src = (LUA_DIR / f).read_text(encoding="utf-8")
        assert '["TIMECODE LTC"] = true' in src and '["TIMECODE MTC"] = true' in src, f
    assert set(TC.TRACKS) <= set(C.GENERATED)
    from reacue_mcp import server
    assert set(TC.TRACKS) <= set(server.GENERATED_TRACKS)


# --------------------------------------------------------------------------- serveur
def _prepare(monkeypatch, bridge_dir, resdir, tmp_path, version):
    import test_cli as T
    from reacue_mcp import server
    fb = T.FakeBridge(version=version)
    monkeypatch.setattr(server.sheet, "song_folder", lambda files: tmp_path / "song")
    monkeypatch.setattr(server.bridge, "call", fb.call)
    monkeypatch.setattr(server.bridge, "alive", fb.alive)
    monkeypatch.setattr(server, "analyze_stems", lambda *a, **k: T.fake_analysis())
    monkeypatch.setattr(server, "Voice", T.FakeVoice)
    for mod, fn in ((server.chords, "cached_chords"), (server.lyrics, "cached_lyrics"), (server.drums, "cached_drums")):
        monkeypatch.setattr(mod, fn, lambda *a, **k: None)
    monkeypatch.setattr(server.prompter, "stem_activity", lambda *a, **k: {})
    (bridge_dir / "last_session.json").unlink(missing_ok=True)
    try:
        return fb, asyncio.run(server.prepare_song())
    finally:
        (bridge_dir / "last_session.json").unlink(missing_ok=True)


def test_server_plan_has_timecode(monkeypatch, lang, bridge_dir, resdir, tmp_path):
    lang("fr", gma3_ltc_output="7/8", gma3_mtc_output="IAC", gma3_tc_start="01:00:00:00")
    fb, res = _prepare(monkeypatch, bridge_dir, resdir, tmp_path, "1.4.0")
    tc = fb.plans[-1]["timecode"]
    assert [t["name"] for t in tc["tracks"]] == ["TIMECODE LTC", "TIMECODE MTC"]
    assert tc["tc_start"] == "01:00:00:00" and tc["min_len"] == pytest.approx(res["song_end_s"] + TC.TAIL_S, abs=1e-3)
    assert not any("pont" in w.lower() and "timecode" in w.lower() for w in res["warnings"])
    # réglages vides (défaut) : bloc présent mais vide, rien ne change pour l'utilisateur
    lang("fr")
    fb, res = _prepare(monkeypatch, bridge_dir, resdir, tmp_path, "1.4.0")
    assert fb.plans[-1]["timecode"]["tracks"] == [] and "timecode" not in res


def test_server_old_bridge_warns(monkeypatch, lang, bridge_dir, resdir, tmp_path):
    lang("fr", gma3_ltc_output=7)
    fb, res = _prepare(monkeypatch, bridge_dir, resdir, tmp_path, "1.3.0")
    assert "timecode" not in fb.plans[-1]
    assert i18n.t("tc_old_bridge", "fr") in res["warnings"]
    lang("fr")
    fb, res = _prepare(monkeypatch, bridge_dir, resdir, tmp_path, "1.3.0")
    assert i18n.t("tc_old_bridge", "fr") not in res["warnings"]


# --------------------------------------------------------------------------- concert
def _add_tc_track(rpp: Path, name="TIMECODE LTC", block=("<SOURCE LTC", "FAKEPARM 1", ">")):
    txt = rpp.read_text(encoding="utf-8").rstrip()
    assert txt.endswith(">")
    tr = ["  <TRACK {AAAAAAAA-0000-0000-0000-000000000001}", f'    NAME "{name}"', "    MAINSEND 0 0",
          "    MIDIOUT -1", "    HWOUT 1030 0 1 0 0 0 0 -1:U -1",
          "    <ITEM", "      POSITION 0", "      LENGTH 30", "      FADEIN 1 0.01 0 1 0 0 0", "      GUID {X}"]
    tr += ["      " + b for b in block] + ["    >", "  >"]
    rpp.write_text(txt[:-1].rstrip() + "\n" + "\n".join(tr) + "\n>\n", encoding="utf-8")


def _concert(tmp_path, songs):
    i18n.set_lang("fr")
    return C.build_concert("Concert TC", [str(p) for p in songs], 4.0, out_dir=tmp_path / "Concerts", publish=False)


def _tc_tracks(res):
    root = C.parse_rpp(res.rpp.read_text(encoding="utf-8"))
    out = {}
    for tr in root.blocks("TRACK"):
        name = C.tokens(tr.first("NAME"))[1]
        out.setdefault(name, []).append(tr)
    return out


def test_concert_single_timecode_track(tmp_path, lang):
    demo = D.write_demo(tmp_path / "projects")
    for p in demo[:2]:
        _add_tc_track(p)                               # chaque morceau a sa propre piste timecode
    lang("fr", gma3_ltc_output=7)
    res = _concert(tmp_path, demo)
    tracks = _tc_tracks(res)
    assert len(tracks["TIMECODE LTC"]) == 1 and "TIMECODE MTC" not in tracks
    tr = tracks["TIMECODE LTC"][0]
    assert tr.first("MAINSEND") == "MAINSEND 0 0" and tr.first("HWOUT").startswith("HWOUT 1030")
    items = tr.blocks("ITEM")
    assert len(items) == 1
    it = items[0]
    assert it.first("POSITION") == "POSITION 0" and it.first("FADEIN") == "FADEIN 1 0 0 1 0 0 0"
    assert float(C.tokens(it.first("LENGTH"))[1]) == pytest.approx(res.songs[-1]["stop"] + TC.TAIL_S)
    assert it.blocks("SOURCE")[0].header == "SOURCE LTC" and it.blocks("SOURCE")[0].first("FAKEPARM") == "FAKEPARM 1"
    assert it.first("GUID") != "GUID {X}"
    # aucune piste d'instrument ne reprend le timecode
    assert all(not n.startswith("TIMECODE") or n == "TIMECODE LTC" for n in tracks)
    assert any("Send MIDI" in w for w in res.warnings)          # pas de réglage mémorisé : rappel
    # réglage mémorisé : il remplace celui des morceaux ; reconstruction : toujours une seule piste
    p = TC.template_dir() / f"{TC.template_key('ltc', TC.config())}.txt"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("<SOURCE LTC\nTEMPLATE 2\n>\n", encoding="utf-8")
    res = _concert(tmp_path, demo)
    tracks = _tc_tracks(res)
    assert len(tracks["TIMECODE LTC"]) == 1
    assert tracks["TIMECODE LTC"][0].blocks("ITEM")[0].blocks("SOURCE")[0].first("TEMPLATE") == "TEMPLATE 2"
    assert not any("Send MIDI" in w for w in res.warnings)


def test_concert_timecode_missing_or_off(tmp_path, lang):
    demo = D.write_demo(tmp_path / "projects")
    lang("fr")
    res = _concert(tmp_path, demo)                      # réglages vides : rien
    assert not any(n.startswith("TIMECODE") for n in _tc_tracks(res))
    lang("fr", gma3_mtc_output="IAC")
    res = _concert(tmp_path, demo)                      # aucun morceau n'a de générateur : avertissement
    assert "TIMECODE MTC" not in _tc_tracks(res)
    assert any("TIMECODE MTC" in w and "prépare" in w for w in res.warnings)
    # réglage mémorisé mais aucun morceau avec la piste : piste créée, routage à vérifier
    p = TC.template_dir() / f"{TC.template_key('mtc', TC.config())}.txt"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("<SOURCE LTC\nMTC 1\n>\n", encoding="utf-8")
    res = _concert(tmp_path, demo)
    tr = _tc_tracks(res)["TIMECODE MTC"][0]
    assert tr.first("MAINSEND") == "MAINSEND 0 0" and tr.blocks("ITEM")[0].first("LOOP") == "LOOP 0"
    assert any("routage" in w for w in res.warnings)


def test_song_timecode_track_not_audio(tmp_path):
    demo = D.write_demo(tmp_path / "projects")
    _add_tc_track(demo[0])
    s = C.load_song(demo[0])
    assert "TIMECODE LTC" in s.gen and all("TIMECODE" not in d["track"] for d in s.audio)


# --------------------------------------------------------------------------- export grandMA3 : clé USB + plugin
def _song():
    return {"title": "Demo Song", "count_in_bars": 2, "n_bars": 8, "bpm": 120.0, "beats_per_bar": 4,
            "bar_times": [k * 2.0 for k in range(11)],
            "sections": [{"name": "Intro", "start_bar": 1, "end_bar": 4}, {"name": "Refrain", "start_bar": 5, "end_bar": 8}]}


def test_export_writes_usb_library_and_plugin(tmp_path):
    proj = tmp_path / "Demo Song" / "Demo Song.RPP"
    proj.parent.mkdir()
    proj.write_text("x")
    c = LG.config({**settings.DEFAULTS, "gma3_tc_slot": 3, "gma3_ltc_output": 7, "gma3_mtc_output": "IAC"})
    s = _song()
    res = LG.export_song(s, str(proj), tmp_path / "www", c)
    out = proj.parent / "grandMA3"
    lib = out / "gma3_library" / "datapools"
    assert (lib / "sequences" / "Demo_Song_Sequence.xml").read_bytes() == (out / "Demo_Song_Sequence.xml").read_bytes()
    assert (lib / "timecodes" / "Demo_Song_Timecode.xml").read_bytes() == (out / "Demo_Song_Timecode.xml").read_bytes()
    assert res["plugin"] == str(lib / "plugins" / "ReaCue.xml")
    xml = (lib / "plugins" / "ReaCue.xml").read_text(encoding="utf-8")
    root = ET.fromstring(xml.lstrip("﻿").encode())
    plug = root.find("Plugin")
    assert root.tag == "GMA3" and plug.get("Name") == "ReaCue"
    assert plug.find("ComponentLua").get("FileName") == "ReaCue.lua"
    lua = (lib / "plugins" / "ReaCue.lua").read_text(encoding="utf-8")
    assert TC.TRACK_LTC not in lua and "--[[REACUE_DATA]]" not in lua
    L = lua54.LuaRuntime(unpack_returned_tuples=True)
    ok, err = L.eval("function(s) local f, e = load(s, '=ReaCue.lua'); return f ~= nil, tostring(e) end")(lua)
    assert ok, err
    # rien du plugin dans le dossier web (les téléphones ne téléchargent que les XML et le CSV)
    assert not any("ReaCue" in p.name for p in (tmp_path / "www").iterdir())
    # onglet Lumière : sorties timecode et slot
    assert s["lighting"]["timecode"] == {"ltc": "7", "mtc": "IAC", "slot": 3,
                                         "plugin": "gma3_library/datapools/plugins/ReaCue.xml"}
    # Timecode XML validé sur console : inchangé (TC Slot réglé par le plugin, pas dans le XML)
    assert 'TCSlot="-1"' in (out / "Demo_Song_Timecode.xml").read_text(encoding="utf-8")


def test_concert_export_has_plugin(tmp_path, lang):
    lang("fr", gma3_tc_slot=2)
    demo = D.write_demo(tmp_path / "projects")
    res = _concert(tmp_path, demo)
    out = tmp_path / "Concerts" / "grandMA3" / "Concert_TC" / "gma3_library" / "datapools"
    seqs = sorted(p.name for p in (out / "sequences").iterdir())
    assert seqs == ["Demo_Song_Sequence.xml", "Second_Demo_Sequence.xml", "Third_Demo_Sequence.xml"]
    assert [p.name for p in (out / "timecodes").iterdir()] == ["Concert_TC_Timecode.xml"]
    lua = (out / "plugins" / "ReaCue.lua").read_text(encoding="utf-8")
    assert '["slot"]=2' in lua and '["name"]="Concert_TC"' in lua and "Third_Demo_Sequence.xml" in lua
    assert res.lighting["plugin"].endswith("ReaCue.xml")


# --------------------------------------------------------------------------- plugin grandMA3 (API simulée)
FAKE_MA = r"""
CMDS, LOG, BOXES = {}, {}, {}
DRIVE = 1
POOLS = { Sequences = {}, Timecodes = {} }
DC = { count = 2, [1] = { DriveType = "Internal" }, [2] = { DriveType = "Removeable" } }
FILES = { [2] = {} }
function DataPool() return POOLS end
function Root() return { Temp = { DriveCollect = DC } } end
function Printf(s) LOG[#LOG + 1] = s end
function MessageBox(t) BOXES[#BOXES + 1] = t; return { result = ANSWER or 1 } end
function Cmd(s)
  CMDS[#CMDS + 1] = s
  local d = s:match("^Drive (%d+)$")
  if d then DRIVE = tonumber(d) return "Ok" end
  local kw, f, n = s:match('^Import (%a+) Library "([^"]+)" At %a+ (%d+)$')
  if kw then
    local e = FILES[DRIVE] and FILES[DRIVE][f]
    if e and e.pool == kw .. "s" then POOLS[e.pool][tonumber(n)] = { name = e.name, TCSlot = -1 } end
    return "Ok"
  end
  local tn, prop, val = s:match('^Set Timecode (%d+) Property "(%w+)" "(.-)"$')
  if tn then
    local o = POOLS.Timecodes[tonumber(tn)]
    if o and prop == "Name" then o.name = val elseif o and prop == "TCSlot" then
      if SLOT_TEXT then o.TCSlot = val end
    elseif o then o[prop] = val end
    return "Ok"
  end
  local dn = s:match("^Delete Timecode (%d+)")
  if dn then POOLS.Timecodes[tonumber(dn)] = nil end
  return "Ok"
end
"""


def _plugin_runtime(data: dict, **globs):
    src = (ROOT / "reacue_mcp" / "gma3" / "ReaCue_plugin.lua").read_text(encoding="utf-8")
    src = src.replace(LG.PLUGIN_MARK, to_lua(data), 1)
    L = lua54.LuaRuntime(unpack_returned_tuples=True)
    L.execute(FAKE_MA)
    g = L.globals()
    for k, v in globs.items():
        g[k] = v
    return L, g, src


def _files(L, mapping):
    L.execute("FILES[2] = {}")
    for f, (pool, name) in mapping.items():
        L.execute(f'FILES[2]["{f}"] = {{ pool = "{pool}", name = "{name}" }}')


def _run(L, src):
    main = L.eval("function(s) return load(s, '=ReaCue.lua')('ReaCue', 'ReaCue', {}, nil) end")(src)
    main(None, None)


def test_plugin_imports_sequences_timecode_and_slot():
    sh = LG.show_from_songs([_song()])
    data = LG.plugin_data(sh, {"tc_slot": 2}, "fr")
    L, g, src = _plugin_runtime(data, SLOT_TEXT=True)
    L.execute('POOLS.Sequences[1] = { name = "Autre" }')
    _files(L, {"Demo_Song_Sequence.xml": ("Sequences", "Demo_Song"), "Demo_Song_Timecode.xml": ("Timecodes", "")})
    _run(L, src)
    cmds = list(g.CMDS.values())
    assert 'Import Sequence Library "Demo_Song_Sequence.xml" At Sequence 2' in cmds
    assert g.POOLS.Sequences[2].name == "Demo_Song" and g.POOLS.Sequences[1].name == "Autre"
    tc = g.POOLS.Timecodes[1]
    assert tc.name == "Demo_Song" and tc.TCSlot == "Slot2" and tc.AutoStart == "Yes" and tc.AutoStop == "Yes"
    assert cmds[-1] == "Drive 1"
    msg = g.BOXES[len(g.BOXES)].message
    assert "TC Slot 2 réglé" in msg and "SMPTE TC = slot 2" in msg and "MIDI TC = slot 2" in msg
    assert "Lecteur utilisé : 2" in msg


def test_plugin_keeps_existing_sequence_and_asks_for_timecode():
    sh = LG.show_from_songs([_song()])
    data = LG.plugin_data(sh, {"tc_slot": 1}, "en")
    L, g, src = _plugin_runtime(data, ANSWER=0)          # « garder l'ancien timecode »
    L.execute('POOLS.Sequences[5] = { name = "Demo_Song", programmed = true }')
    L.execute('POOLS.Timecodes[1] = { name = "Demo_Song", TCSlot = 0 }')
    _files(L, {"Demo_Song_Sequence.xml": ("Sequences", "Demo_Song"), "Demo_Song_Timecode.xml": ("Timecodes", "")})
    _run(L, src)
    cmds = list(g.CMDS.values())
    assert not any(c.startswith("Import Sequence") for c in cmds)          # programmation gardée
    assert g.POOLS.Sequences[5].programmed is True
    assert not any(c.startswith("Delete") for c in cmds)
    assert g.POOLS.Timecodes[2].name == "Demo_Song" and g.POOLS.Timecodes[1].TCSlot == 0
    # pas de lecture « Slot1 » possible (SLOT_TEXT absent) : repli numérique… puis assignation directe
    assert g.POOLS.Timecodes[2].TCSlot == 0
    msgs = [g.BOXES[i].message for i in range(1, len(g.BOXES) + 1)]
    assert "already exists" in msgs[0] and "kept (no. 1)" in msgs[-1] and "TC Slot 1 set" in msgs[-1]


def test_plugin_replace_timecode_and_missing_files():
    sh = LG.show_from_songs([_song()])
    data = LG.plugin_data(sh, {"tc_slot": 1}, "fr")
    L, g, src = _plugin_runtime(data, ANSWER=1, SLOT_TEXT=True)
    L.execute('POOLS.Timecodes[4] = { name = "Demo_Song" }')
    _files(L, {"Demo_Song_Timecode.xml": ("Timecodes", "")})           # la Sequence manque sur la clé
    _run(L, src)
    cmds = list(g.CMDS.values())
    assert "Delete Timecode 4 /NoConfirm" in cmds and g.POOLS.Timecodes[4].name == "Demo_Song"
    msg = g.BOXES[len(g.BOXES)].message
    assert "Sequence Demo_Song : import impossible" in msg and "Timecode Demo_Song importé (n° 4)" in msg
    # sans données : message, aucune commande
    L2, g2, src2 = _plugin_runtime(None)
    _run(L2, src2)
    assert len(g2.CMDS) == 0 and "absentes" in g2.LOG[1]


# --------------------------------------------------------------------------- page du prompteur, docs
def test_prompter_page_timecode_outputs():
    assert 'id="lOut"' in PAGE and 'id="lOutT"' in PAGE
    for k in ("lOutT", "lLtc", "lMtc", "lSlotTc", "lHow"):
        assert PAGE.count(f"{k}:") == 2, k                     # FR et EN
    assert "D && D.timecode" in PAGE and "IAC" in PAGE and "rtpMIDI" in PAGE


def test_docs_timecode_setup():
    for doc, words in (("README.md", ("TIMECODE LTC", "gma3_ltc_output", "IAC", "rtpMIDI", "ReaCue.xml")),
                       ("LISEZMOI.md", ("TIMECODE LTC", "gma3_ltc_output", "IAC", "rtpMIDI", "ReaCue.xml")),
                       ("docs/TUTORIAL_en.md", ("TIMECODE LTC", "IAC", "rtpMIDI", "Send MIDI (MTC)")),
                       ("docs/TUTORIEL_fr.md", ("TIMECODE LTC", "IAC", "rtpMIDI", "Send MIDI (MTC)"))):
        txt = (ROOT / doc).read_text(encoding="utf-8")
        assert all(w in txt for w in words), (doc, [w for w in words if w not in txt])
    ch = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert re.search(r"Unreleased|## 1\.2\.0", ch) and "TIMECODE LTC" in ch

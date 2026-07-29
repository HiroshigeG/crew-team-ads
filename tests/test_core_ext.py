"""Test offline del core esteso — nessuna chiamata API."""
import crew_cast as core


def test_role_personas_match_cast():
    # ROLE_PERSONAS è la fonte dei default: ricomposta con ROOM_RULES
    # deve dare ESATTAMENTE le personas di CAST (nessuna deriva).
    for key, c in core.CAST.items():
        assert core.ROOM_RULES + core.ROLE_PERSONAS[key] == c["persona"]


def test_temp_for_level_endpoints():
    assert core.temp_for_level(0) == 0.1
    assert core.temp_for_level(10) == 1.2
    assert core.temp_for_level(5) == 0.65
    # clamp fuori scala
    assert core.temp_for_level(-3) == 0.1
    assert core.temp_for_level(99) == 1.2


def test_creativity_block_bands():
    assert core.creativity_block(1)          # 0-2: presente
    assert core.creativity_block(4) == ""    # 3-5: neutro, nessuna iniezione
    assert core.creativity_block(7)          # 6-8: presente
    assert core.creativity_block(10)         # 9-10: presente
    assert core.creativity_block(7) != core.creativity_block(10)


def test_head_mechanism_label():
    h = core.Head(key="cd", name="CD", avatar="🎨", color="#ff8700",
                  model_id="anthropic/claude-opus-5", persona="x", creativity=8)
    assert h.mechanism_label() == "via prompt"
    g = core.Head(key="s", name="S", avatar="🧠", color="#5fafff",
                  model_id="gemini/gemini-3.1-pro-preview", persona="x",
                  creativity=6)
    assert g.mechanism_label() == "via temperature 0.76"


def test_head_dict_roundtrip():
    h = core.Head(key="cd", name="CD", avatar="🎨", color="#ff8700",
                  model_id="anthropic/claude-opus-5", persona="x", creativity=8)
    assert core.Head.from_dict(h.to_dict()) == h


def test_roster_default_matches_cast():
    r = core.Roster.default()
    assert list(r.keys()) == ["producer", "strategist", "cd", "social"]
    assert r.heads["cd"].model_id == "anthropic/claude-opus-5"
    assert r.heads["social"].model_id == "xai/grok-4.5"
    assert r.heads["cd"].persona == core.ROLE_PERSONAS["cd"]
    assert all(h.creativity == 5 for h in r.heads.values())


def test_roster_save_load_roundtrip(tmp_path):
    p = str(tmp_path / "roster.json")
    r = core.Roster.default()
    r.update_head("cd", creativity=9, name="Mad CD")
    r.save(p)
    r2 = core.Roster.load(p)
    assert r2.heads["cd"].creativity == 9
    assert r2.heads["cd"].name == "Mad CD"
    assert list(r2.keys()) == list(r.keys())


def test_roster_corrupt_file_backs_up_and_defaults(tmp_path):
    p = tmp_path / "roster.json"
    p.write_text("{not json", encoding="utf-8")
    r = core.Roster.load(str(p))
    assert list(r.keys()) == ["producer", "strategist", "cd", "social"]
    assert (tmp_path / "roster.json.bad").exists()   # mai perdere il file rotto


def test_roster_add_remove(tmp_path):
    p = str(tmp_path / "roster.json")
    r = core.Roster.default()
    r.add_head(core.Head(key="pm", name="PM", avatar="📋", color="#aaaaaa",
                         model_id="anthropic/claude-sonnet-5", persona=" You are the PM."))
    assert "pm" in r.keys()
    r.remove_head("pm")
    assert "pm" not in r.keys()
    # l'ultima testa non si rimuove: la stanza non può restare vuota
    for k in list(r.keys())[:-1]:
        r.remove_head(k)
    import pytest as _pytest
    with _pytest.raises(ValueError):
        r.remove_head(next(iter(r.keys())))
    r.save(p)  # save esplicito, non implicito nei metodi: lo fa il chiamante


def test_make_llm_families():
    claude = core.make_llm(core.Head(key="x", name="X", avatar="a", color="c",
                                     model_id="anthropic/claude-opus-5",
                                     persona="p", creativity=8))
    assert isinstance(claude, core.ClaudeLLM)      # subscription-first (R7)
    assert claude.model == "claude-opus-5"
    grok = core.make_llm(core.Head(key="y", name="Y", avatar="a", color="c",
                                   model_id="xai/grok-4.5", persona="p",
                                   creativity=10))
    assert grok.model == "xai/grok-4.5"
    assert grok.temperature == 1.2
    assert grok.additional_params.get("additional_drop_params") == ["stop"]  # T5: litellm droppa "stop" 


def test_roster_llm_cache_and_invalidation():
    r = core.Roster.default()
    # Cache hit: second call returns same object
    first = r.llm("social")
    assert r.llm("social") is first
    # Cache invalidation: update clears cache and creates new LLM
    r.update_head("social", creativity=10)
    fresh = r.llm("social")
    assert fresh is not first
    assert fresh.temperature == 1.2  # 0.1 + 0.11*10 = 1.2
    # Anthropic models still routed via ClaudeLLM after update
    r.update_head("cd", creativity=9)
    cd_llm = r.llm("cd")
    assert isinstance(cd_llm, core.ClaudeLLM)
    assert cd_llm.model == "claude-opus-5"

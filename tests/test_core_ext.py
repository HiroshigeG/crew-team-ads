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

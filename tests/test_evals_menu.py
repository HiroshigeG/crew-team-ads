"""Parser e controlli del menù di tre idee (offline, nessun costo)."""
from evals import darkangel_menu as dm


def test_parses_three_plain_ideas():
    t = "1. Prima idea qui.\n2. Seconda idea.\n3. Terza idea."
    assert dm.parse_ideas(t) == ["Prima idea qui.", "Seconda idea.", "Terza idea."]


def test_parses_bold_and_parenthesis_markers():
    t = "**1.** Prima.\n2) Seconda.\n**3:** Terza."
    assert dm.parse_ideas(t) == ["Prima.", "Seconda.", "Terza."]


def test_multiline_idea_continues_until_the_next_number():
    t = "1. Prima riga\ncontinua qui.\n\n2. Seconda.\n3. Terza\nanche questa continua."
    assert dm.parse_ideas(t) == ["Prima riga continua qui.", "Seconda.", "Terza anche questa continua."]


def test_preamble_before_the_first_idea_is_ignored():
    t = "Ecco le idee, spero piacciano.\n\n1. Una.\n2. Due.\n3. Tre."
    assert dm.parse_ideas(t) == ["Una.", "Due.", "Tre."]


def test_numbers_inside_a_line_do_not_open_ideas():
    t = "1. Alle 6:40 corro, 2 ore dopo mi fermo.\n2. Due.\n3. Tre."
    assert dm.parse_ideas(t) == ["Alle 6:40 corro, 2 ore dopo mi fermo.", "Due.", "Tre."]


def test_fewer_than_three_returns_what_is_there():
    assert dm.parse_ideas("1. Solo una.\n2. E una seconda.") == ["Solo una.", "E una seconda."]
    assert dm.parse_ideas("nessuna idea numerata qui") == []
    assert dm.parse_ideas("") == []


def test_out_of_order_numbering_does_not_invent_ideas_and_is_flagged():
    # «3.» senza un «2.» prima non apre un'idea: resta accodata alla precedente
    # (non si perde testo) e il controllo di formato segnala che le idee non sono tre
    t = "1. Una.\n3. Tre."
    assert dm.parse_ideas(t) == ["Una. 3. Tre."]
    assert dm.check_format(t, t)["three_ideas"] is False


def test_format_check_flags_each_requirement():
    good = "1. " + "parola " * 20 + "\n2. " + "parola " * 20 + "\n3. " + "parola " * 20
    f = dm.check_format(good, good)
    assert f["three_ideas"] and f["short_enough"] and not f["leak"]
    long_idea = "1. " + "parola " * 80 + "\n2. due\n3. tre"
    assert dm.check_format(long_idea, long_idea)["short_enough"] is False
    assert dm.check_format("<think>x</think>1. a\n2. b\n3. c", "1. a\n2. b\n3. c")["leak"] is True
    assert dm.check_format("", "")["three_ideas"] is False


def test_frozen_scenarios_and_models():
    assert list(dm.SCENARIOS) == ["DN1", "DN2", "DN3"]
    assert [dm.SCENARIOS[s][0] for s in dm.SCENARIOS] == [10000, 3000, 14000]
    assert set(dm.CANDIDATES) == {"glm", "aion", "opus", "sonnet"}
    assert "TRE idee" in dm.FORMAT and "50 parole" in dm.FORMAT

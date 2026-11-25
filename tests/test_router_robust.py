"""Router a ondate: lettura robusta del JSON + guasti visibili nel log.

Il 25/11/2026 il router a ondate è finito più volte in fallback ("Instradamento
ridotto") senza una riga di log: né l'output del modello, né il motivo. In più,
se la CLI di Claude fallisce, il motore passa all'API A PAGAMENTO in silenzio.
Qui: (1) il piano si legge anche con prosa/parentesi prima o dopo (il contratto
NON cambia: serve una lista di ondate); (2) ogni scarto e ogni passaggio
all'API lascia una riga di log. La causa radice del fallback resta da
misurare con questi log.
"""
import logging

import pytest

import crew_cast as core

KEYS = {"market_researcher", "cd", "social", "account_director"}


# ── parser tollerante ─────────────────────────────────────────────────────

def test_parse_nested_waves_still_works():
    raw = '[[{"speaker":"cd","instruction":"x","to":"director"}],[{"speaker":"social","instruction":"y"}]]'
    waves = core.parse_wave_plan(raw, KEYS)
    assert [[s["speaker"] for s in w] for w in waves] == [["cd"], ["social"]]


def test_parse_flat_array_stays_invalid():
    # decisione già presa (test_core_ext): un array piatto NON è un piano a ondate
    raw = '[{"speaker":"cd","instruction":"x"},{"speaker":"social","instruction":"y"}]'
    assert core.parse_wave_plan(raw, KEYS) == []


def test_parse_ignores_code_fence_and_prose_with_brackets_after():
    raw = ('```json\n[[{"speaker":"cd","instruction":"x"}]]\n```\n'
           "Nota: ho scelto cd [perché è il più adatto] e basta.")
    waves = core.parse_wave_plan(raw, KEYS)
    assert waves[0][0]["speaker"] == "cd"


def test_parse_ignores_leading_prose_with_brackets_before():
    raw = ('Ecco il piano [come richiesto]:\n'
           '[[{"speaker":"social","instruction":"y"}]]')
    waves = core.parse_wave_plan(raw, KEYS)
    assert waves[0][0]["speaker"] == "social"


def test_parse_drops_unknown_speakers_and_caps_at_four_steps():
    steps = ",".join('{"speaker":"cd","instruction":"x"}' for _ in range(6))
    waves = core.parse_wave_plan(f'[[{steps},{{"speaker":"ghost","instruction":"?"}}]]', KEYS)
    assert sum(len(w) for w in waves) == 4
    assert all(s["speaker"] != "ghost" for w in waves for s in w)


@pytest.mark.parametrize("raw", ["", "nessun piano", "[]", "[[]]", "{}", '{"waves": 3}',
                                 '[[{"speaker":"ghost"}]]'])
def test_parse_invalid_returns_empty(raw):
    assert core.parse_wave_plan(raw, KEYS) == []


# ── guasti visibili ───────────────────────────────────────────────────────

class _Garbage:
    def call(self, prompt):
        return "Non posso pianificare questo, mi dispiace. [forse]"


def test_route_plan_logs_the_raw_output_when_the_plan_is_invalid(monkeypatch, caplog):
    monkeypatch.setattr(core, "llm_claude_router", _Garbage())
    r = core.Roster.default()
    with caplog.at_level(logging.WARNING, logger="crew_cast"):
        core.route_plan(r, "T", "ciao")
    assert core.last_plan_route() == "fallback"
    joined = " ".join(m.getMessage() for m in caplog.records)
    assert "piano non valido" in joined
    assert "Non posso pianificare" in joined      # l'output, non solo «fallito»


def test_claude_cli_failure_falling_back_to_api_is_logged(monkeypatch, caplog):
    monkeypatch.setattr(core, "CLAUDE_CLI", "claude")
    llm = core.ClaudeLLM("claude-sonnet-5")

    def boom(self, prompt):
        raise RuntimeError("claude CLI exited 1: rate limited")

    class _Api:
        def call(self, prompt):
            return "ok via api"

    monkeypatch.setattr(core.ClaudeLLM, "_via_cli", boom)
    llm._api = _Api()
    with caplog.at_level(logging.WARNING, logger="crew_cast"):
        assert llm.call("p") == "ok via api"
    joined = " ".join(m.getMessage() for m in caplog.records)
    assert "API" in joined and "rate limited" in joined
    assert llm.last_route == "api"

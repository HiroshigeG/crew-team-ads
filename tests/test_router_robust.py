"""Router a ondate: lettura robusta del JSON + guasti visibili nel log.

Il 25/11/2026 il router a ondate è finito più volte in fallback ("Instradamento
ridotto") senza una riga di log: né l'output del modello, né il motivo. In più,
se la CLI di Claude fallisce, il motore passa all'API A PAGAMENTO in silenzio.
Qui: (1) il piano si legge anche con prosa/parentesi prima o dopo (il contratto
NON cambia: serve una lista di ondate); (2) ogni scarto e ogni passaggio
all'API lascia una riga di log.

Causa radice misurata dopo (D36): il router risponde spesso con un array
PIATTO di passi validi (27 risposte su 60 reali), che il vecchio contratto
scartava. Ora si legge come passi in sequenza.
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


def test_parse_flat_array_becomes_one_step_per_wave():
    # Causa misurata dell'«Instradamento ridotto» (D36): su 60 chiamate reali
    # del router, 27 risposte erano un array PIATTO di passi validi, scartato
    # dal vecchio contratto. Ora si legge come passi in sequenza, un'ondata
    # per passo: l'ordine del modello resta (un consulto non diventa parallelo).
    raw = '[{"speaker":"cd","instruction":"x"},{"speaker":"social","instruction":"y"}]'
    waves = core.parse_wave_plan(raw, KEYS)
    assert [[s["speaker"] for s in w] for w in waves] == [["cd"], ["social"]]
    assert waves[1][0]["instruction"] == "y" and waves[1][0]["to"] == "director"


def test_parse_real_flat_router_output_from_the_sample():
    # Risposta vera del router (campione del 25/11, scenario «domanda»).
    raw = ('[{"speaker": "producer", "instruction": "Riassumi in due righe cosa NON '
           'ripetere dalle campagne andate male", "to": "director"}, {"speaker": '
           '"account_director", "instruction": "Valuta il rischio commerciale", "to": "director"}]')
    waves = core.parse_wave_plan(raw, KEYS | {"producer"})
    assert [[s["speaker"] for s in w] for w in waves] == [["producer"], ["account_director"]]


def test_parse_waves_of_bare_speaker_keys():
    # Risposta vera (scenario «brief»): ondate di sole chiavi, senza oggetti.
    # L'istruzione vuota la riempie _run_plan con il messaggio del Director.
    raw = '[["market_researcher","cd"],["social"]]'
    waves = core.parse_wave_plan(raw, KEYS)
    assert [[s["speaker"] for s in w] for w in waves] == [["market_researcher", "cd"], ["social"]]
    assert waves[0][0] == {"speaker": "market_researcher", "instruction": "", "to": "director"}


def test_parse_real_output_with_javascript_reads_the_first_list_of_keys():
    # Risposta vera (scenario «brief»): il modello ha scritto codice JS. Il
    # primo JSON valido è la lista di chiavi: passi in sequenza.
    raw = ('[["market_researcher","cd","account_director"].map(s=>({"speaker":s,'
           '"instruction":"Reagisci","to":"director"})) ]')
    waves = core.parse_wave_plan(raw, KEYS)
    assert [[s["speaker"] for s in w] for w in waves] == [
        ["market_researcher"], ["cd"], ["account_director"]]


def test_parse_flat_array_of_unknown_speakers_is_still_invalid():
    assert core.parse_wave_plan('[{"speaker":"ghost"},{"speaker":"nobody"}]', KEYS) == []


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

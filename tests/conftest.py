"""Rete di sicurezza della suite: nessun test chiama un modello vero per sbaglio.

Il controllo di onestà sulle immagini (D38) interroga un modello via CLI ogni
volta che una risposta parla di un'immagine: nei test resta spento, e i test che
lo provano lo riaccendono con un modello finto.
"""
import pytest


@pytest.fixture(autouse=True)
def _no_llm_guardrail_by_default(monkeypatch):
    monkeypatch.setenv("CREW_LLM_GUARDRAIL", "0")
    # D39: il passaggio a Claude sulle immagini chiamerebbe la CLI vera.
    monkeypatch.setenv("CREW_IMAGE_HANDOFF", "0")

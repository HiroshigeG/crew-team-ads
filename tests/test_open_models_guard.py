"""Teste su modelli open (Featherless/OpenRouter/Ollama): stop, tetto, timeout.

Misura del 25/11/2026 (Featherless, piano flat): Hermes-3-70B risponde
«Azzurro<|im_end|>» e poi CONTINUA, inventando un turno dell'utente. Senza
stop-token e senza tetto di token, con un transcript lungo genera fino al
limite del contesto: 2-5 minuti per una risposta da 150 parole, e la stanza
intera resta ferma ad aspettare. Qui si verifica che ogni LLM open nasca con
i tre guardrail. Offline: nessuna chiamata di rete.
"""
import pytest

import crew_cast as core


def _head(model_id):
    r = core.Roster.default()
    r.update_head("producer", model_id=model_id)
    return r.heads["producer"]


@pytest.mark.parametrize("model_id", [
    "featherless_ai/NousResearch/Hermes-3-Llama-3.1-70B",
    "openrouter/meta-llama/llama-3.3-70b-instruct",
    "ollama/llama3",
])
def test_open_models_get_stop_cap_and_timeout(model_id):
    llm = core.make_llm(_head(model_id))
    assert "<|im_end|>" in llm.stop
    assert "<|im_start|>" in llm.stop
    assert "<|eot_id|>" in llm.stop
    assert llm.max_tokens == 900
    assert llm.timeout == 120


def test_open_model_guard_is_tunable_from_env(monkeypatch):
    monkeypatch.setenv("CREW_MAX_REPLY_TOKENS", "300")
    monkeypatch.setenv("CREW_OPEN_MODEL_TIMEOUT", "45")
    llm = core.make_llm(_head("featherless_ai/Qwen/Qwen2.5-72B-Instruct"))
    assert llm.max_tokens == 300
    assert llm.timeout == 45


def test_garbage_env_falls_back_to_defaults(monkeypatch):
    monkeypatch.setenv("CREW_MAX_REPLY_TOKENS", "molti")
    monkeypatch.setenv("CREW_OPEN_MODEL_TIMEOUT", "")
    llm = core.make_llm(_head("featherless_ai/Qwen/Qwen2.5-72B-Instruct"))
    assert llm.max_tokens == 900 and llm.timeout == 120


def test_gemini_is_not_capped():
    # un tetto basso taglierebbe il ragionamento interno dei modelli «thinking»
    llm = core.make_llm(_head("gemini/gemini-3.1-pro-preview"))
    assert getattr(llm, "max_tokens", None) != 900

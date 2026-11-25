"""Registro dei provider: l'unica fonte su chi serve quali modelli e con quale
chiave. Serve a rendere il progetto usabile da altri: le chiavi obbligatorie
non sono più Anthropic+Gemini+xAI per tutti, ma solo quelle dei provider che il
roster di QUESTO utente usa. Offline: nessuna chiamata di rete."""
import pytest

import crew_cast as core
import providers as pv


# ── riconoscere il provider ───────────────────────────────────────────────

@pytest.mark.parametrize("model_id,pid", [
    ("venice/venice-uncensored-1-2", "venice"),
    ("featherless_ai/NousResearch/Hermes-3-Llama-3.1-70B", "featherless_ai"),
    ("openrouter/meta-llama/llama-3.3-70b-instruct", "openrouter"),
    ("gemini/gemini-3.1-pro-preview", "gemini"),
    ("xai/grok-4.5", "xai"),
    ("anthropic/claude-sonnet-5", "anthropic"),
    ("ollama/llama3", "ollama"),
])
def test_provider_of_known_prefixes(model_id, pid):
    assert pv.provider_of(model_id).id == pid


@pytest.mark.parametrize("model_id", ["", "gemini-senza-slash", "sconosciuto/modello", "/x"])
def test_provider_of_unknown_is_none(model_id):
    assert pv.provider_of(model_id) is None


def test_open_models_are_the_ones_that_get_guardrails():
    for m in ("venice/x", "featherless_ai/x", "openrouter/x", "ollama/x"):
        assert pv.is_open_model(m), m
    for m in ("gemini/x", "xai/x", "anthropic/x", "boh/x"):
        assert not pv.is_open_model(m), m


# ── come si costruisce la chiamata ────────────────────────────────────────

def test_venice_is_openai_compatible_with_its_own_base_and_key():
    env = {"VENICE_API_KEY": "chiave-finta"}
    kw = pv.litellm_kwargs("venice/venice-uncensored-1-2", env)
    assert kw["model"] == "openai/venice-uncensored-1-2"
    assert kw["api_base"] == "https://api.venice.ai/api/v1"
    assert kw["api_key"] == "chiave-finta"


def test_venice_base_can_be_overridden_from_env():
    kw = pv.litellm_kwargs("venice/m", {"VENICE_API_KEY": "k", "VENICE_API_BASE": "http://localhost:9/v1"})
    assert kw["api_base"] == "http://localhost:9/v1"


def test_native_providers_pass_through_untouched():
    assert pv.litellm_kwargs("featherless_ai/a/b", {}) == {"model": "featherless_ai/a/b"}
    assert pv.litellm_kwargs("gemini/g", {}) == {"model": "gemini/g"}


def test_make_llm_builds_a_guarded_venice_llm(monkeypatch):
    monkeypatch.setenv("VENICE_API_KEY", "chiave-finta")
    r = core.Roster.default()
    r.update_head("cd", model_id="venice/glm-5-3-flash-uncensored")
    llm = core.make_llm(r.heads["cd"])
    assert llm.api_base == "https://api.venice.ai/api/v1"
    assert "<|im_end|>" in llm.stop and llm.max_tokens == 900 and llm.timeout == 120
    assert core.model_allowed("venice/glm-5-3-flash-uncensored")


# ── chiavi: solo quelle che il roster usa ─────────────────────────────────

def test_key_whitelist_covers_every_provider_with_a_key():
    names = set(pv.key_names())
    assert {"ANTHROPIC_API_KEY", "GEMINI_API_KEY", "XAI_API_KEY",
            "FEATHERLESS_AI_API_KEY", "OPENROUTER_API_KEY", "VENICE_API_KEY"} <= names


def test_keys_needed_follow_the_models_in_use():
    models = ["gemini/g", "featherless_ai/a/b", "venice/v"]
    assert pv.keys_needed(models, claude_cli=True) == {
        "GEMINI_API_KEY", "FEATHERLESS_AI_API_KEY", "VENICE_API_KEY"}


def test_claude_models_need_a_key_only_without_the_cli():
    assert pv.keys_needed(["anthropic/claude-sonnet-5"], claude_cli=True) == set()
    assert pv.keys_needed(["anthropic/claude-sonnet-5"], claude_cli=False) == {"ANTHROPIC_API_KEY"}


def test_missing_keys_for_a_roster_ignores_unused_providers(monkeypatch):
    for k in pv.key_names():
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setattr(core, "CLAUDE_CLI", "claude")
    r = core.Roster.default()
    for key in list(r.heads):
        r.update_head(key, model_id="featherless_ai/Qwen/Qwen2.5-72B-Instruct")
    # un roster solo-Featherless non chiede Anthropic, Gemini né xAI
    assert core.missing_keys(r) == ["FEATHERLESS_AI_API_KEY"]
    monkeypatch.setenv("FEATHERLESS_AI_API_KEY", "x")
    assert core.missing_keys(r) == []


def test_missing_keys_without_a_roster_keeps_the_legacy_default(monkeypatch):
    for k in pv.key_names():
        monkeypatch.delenv(k, raising=False)
    assert core.missing_keys() == list(core.REQUIRED_KEYS)


# ── descrizione per la UI ─────────────────────────────────────────────────

def test_describe_lists_providers_with_labels_and_state():
    env = {"VENICE_API_KEY": "valore-segreto-xyz-123"}
    d = {p["id"]: p for p in pv.describe(env, ["venice/v", "gemini/g"], claude_cli=True)}
    assert d["venice"]["configured"] is True and d["venice"]["needed"] is True
    assert d["gemini"]["configured"] is False and d["gemini"]["needed"] is True
    assert d["xai"]["needed"] is False
    assert d["venice"]["label"] and d["venice"]["key_env"] == "VENICE_API_KEY"
    # il NOME della variabile si può mostrare, il VALORE mai
    assert "valore-segreto-xyz-123" not in repr(d)


# ── temperatura: ogni provider ha il suo massimo (25/11: Venice rifiutava 1,09) ──

def test_venice_declares_a_max_temperature_of_one():
    assert pv.PROVIDERS["venice"].max_temperature == 1.0
    assert pv.max_temperature_for("venice/qualunque") == 1.0
    assert pv.max_temperature_for("gemini/g") is None          # nessun limite dichiarato


def test_make_llm_clamps_temperature_to_the_provider_max(monkeypatch):
    monkeypatch.setenv("VENICE_API_KEY", "chiave-finta")
    r = core.Roster.default()
    r.update_head("cd", model_id="venice/abliteration-abliterated-model-large-v2", creativity=9)
    assert core.temp_for_level(9) > 1.0                       # la scala darebbe 1,09
    assert core.make_llm(r.heads["cd"]).temperature == 1.0    # Venice: al massimo 1


def test_other_providers_keep_the_full_creativity_scale():
    r = core.Roster.default()
    r.update_head("cd", model_id="gemini/gemini-3.1-pro-preview", creativity=10)
    assert core.make_llm(r.heads["cd"]).temperature == core.temp_for_level(10)

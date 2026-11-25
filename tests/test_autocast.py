"""Auto-cast: a ogni ruolo il miglior modello tra quelli che QUESTO utente può
usare. Serve a chi apre il progetto con le sue chiavi (una sola o tutte) senza
dover conoscere i nomi dei modelli. Offline, puro."""
import providers as pv

ROLES = ["market_researcher", "creative_strategist", "cd", "copywriter", "social",
         "producer", "dark_angel", "copywriter_2", "account_director"]


def models(assign):
    return {k: v for k, v in assign.items()}


def test_with_every_provider_each_role_gets_its_preferred_distinct_model():
    avail = {"anthropic", "gemini", "xai", "featherless_ai", "venice", "openrouter"}
    a = pv.autocast(ROLES, avail)
    assert a["market_researcher"].startswith("gemini/")
    assert a["social"].startswith("xai/")
    assert a["cd"].startswith("anthropic/")
    assert a["dark_angel"].startswith("venice/")          # abliterated su Venice
    assert len(set(a.values())) == len(ROLES)             # nove modelli diversi


def test_without_venice_dark_angel_falls_back_to_an_open_model():
    a = pv.autocast(ROLES, {"anthropic", "gemini", "xai", "featherless_ai"})
    assert a["dark_angel"].startswith("featherless_ai/")


def test_a_single_provider_still_fills_every_role():
    a = pv.autocast(ROLES, {"featherless_ai"})
    assert set(a) == set(ROLES)
    assert all(m.startswith("featherless_ai/") for m in a.values())


def test_claude_only_user_gets_claude_models_everywhere():
    a = pv.autocast(ROLES, {"anthropic"})
    assert set(a) == set(ROLES)
    assert all(m.startswith("anthropic/") for m in a.values())


def test_no_provider_means_no_assignment_not_a_made_up_one():
    assert pv.autocast(ROLES, set()) == {}


def test_unknown_role_gets_a_default_from_an_available_provider():
    a = pv.autocast(["ruolo_nuovo"], {"gemini"})
    assert a["ruolo_nuovo"].startswith("gemini/")


def test_available_providers_from_env_and_cli():
    env = {"GEMINI_API_KEY": "x", "VENICE_API_KEY": "y"}
    assert pv.available_providers(env, claude_cli=True) == {"gemini", "venice", "anthropic"}
    assert pv.available_providers(env, claude_cli=False) == {"gemini", "venice"}
    assert pv.available_providers({"ANTHROPIC_API_KEY": "z"}, claude_cli=False) == {"anthropic"}
    assert pv.available_providers({}, claude_cli=False) == set()


def test_every_model_proposed_belongs_to_a_known_provider():
    a = pv.autocast(ROLES, set(pv.PROVIDERS) - {"ollama"})
    assert all(pv.provider_of(m) is not None for m in a.values())

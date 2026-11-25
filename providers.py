"""Registro dei provider: l'unica fonte su chi serve quali modelli e con quale
chiave.

Perché esiste (25/11/2026): le chiavi obbligatorie erano Anthropic+Gemini+xAI
per tutti, la whitelist dei modelli era scritta nel codice e Venice non esisteva.
Chi non aveva Grok non poteva nemmeno aprire la stanza. Ora un provider è una
riga di questo registro, e una chiave è «obbligatoria» solo se il roster di
QUESTO utente la usa.

Un `model_id` è sempre `<provider>/<modello>` (es. `venice/venice-uncensored-1-2`,
`featherless_ai/Qwen/Qwen2.5-72B-Instruct`). Puro: nessuna rete, nessun segreto
nei valori restituiti — si mostrano i NOMI delle variabili, mai i valori.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Provider:
    id: str                       # prefisso del model_id
    label: str                    # come lo vede l'utente
    key_env: str | None           # variabile d'ambiente della chiave (None = nessuna)
    kind: str = "api"             # "api" | "cli+api" (Claude) | "local"
    openai_base: str | None = None   # se parla il protocollo OpenAI e litellm non lo conosce
    base_env: str | None = None      # variabile per sovrascrivere la base
    open_model: bool = False      # modelli open: servono stop-token, tetto, timeout
    vision: bool = False          # legge immagini (oggi: Gemini)
    suggested: tuple = ()         # modelli proposti nell'editor (si può digitarne altri)


# I modelli suggeriti per Venice vengono dal catalogo letto il 25/11/2026 da
# una ricerca: gli id vanno ricontrollati con GET /api/v1/models prima di
# affidarcisi. Servono solo da proposta: l'editor accetta qualunque id digitato.
PROVIDERS: dict[str, Provider] = {p.id: p for p in (
    Provider("anthropic", "Anthropic (Claude) — CLI in abbonamento o API",
             "ANTHROPIC_API_KEY", kind="cli+api"),
    Provider("gemini", "Google Gemini — ricerca e visione",
             "GEMINI_API_KEY", vision=True),
    Provider("xai", "xAI (Grok) — analista social", "XAI_API_KEY"),
    Provider("featherless_ai", "Featherless — modelli open (piano flat)",
             "FEATHERLESS_AI_API_KEY", open_model=True),
    Provider("openrouter", "OpenRouter — modelli open a crediti",
             "OPENROUTER_API_KEY", open_model=True),
    Provider("venice", "Venice — modelli uncensored/abliterated (crediti USD)",
             "VENICE_API_KEY", openai_base="https://api.venice.ai/api/v1",
             base_env="VENICE_API_BASE", open_model=True,
             suggested=(
                 "venice/abliteration-abliterated-model-large-v2",
                 "venice/glm-5-3-flash-uncensored",
                 "venice/venice-uncensored-1-2",
                 "venice/aion-labs-aion-3-5-mini",
             )),
    Provider("ollama", "Ollama — modelli locali", None, kind="local",
             open_model=True),
)}


def provider_of(model_id: str) -> Provider | None:
    """Il provider di un model_id `<provider>/<modello>`, o None se sconosciuto."""
    head, sep, rest = (model_id or "").partition("/")
    if not sep or not rest:
        return None
    return PROVIDERS.get(head)


def is_open_model(model_id: str) -> bool:
    p = provider_of(model_id)
    return bool(p and p.open_model)


def open_prefixes() -> tuple[str, ...]:
    """Prefissi `<id>/` dei provider di modelli open (per i guardrail)."""
    return tuple(f"{p.id}/" for p in PROVIDERS.values() if p.open_model)


def litellm_kwargs(model_id: str, env) -> dict:
    """Gli argomenti base della chiamata litellm/crewai per questo modello.
    I provider che litellm conosce passano così come sono; quelli compatibili
    OpenAI (Venice) diventano `openai/<modello>` con la loro base e la loro chiave."""
    p = provider_of(model_id)
    if p and p.openai_base:
        name = model_id.split("/", 1)[1]
        base = (env.get(p.base_env) if p.base_env else None) or p.openai_base
        kw = {"model": f"openai/{name}", "api_base": base}
        if p.key_env and env.get(p.key_env):
            kw["api_key"] = env[p.key_env]
        return kw
    return {"model": model_id}


def key_names() -> tuple[str, ...]:
    """Tutti i nomi di chiave che la UI può scrivere (whitelist chiusa)."""
    return tuple(p.key_env for p in PROVIDERS.values() if p.key_env)


def keys_needed(model_ids, claude_cli: bool) -> set[str]:
    """Le variabili di chiave richieste da QUESTI modelli. Claude non chiede la
    chiave se la CLI in abbonamento c'è (l'API è solo un fallback dichiarato)."""
    need: set[str] = set()
    for m in model_ids:
        p = provider_of(m)
        if not p or not p.key_env:
            continue
        if p.kind == "cli+api" and claude_cli:
            continue
        need.add(p.key_env)
    return need


def describe(env, model_ids, claude_cli: bool) -> list[dict]:
    """Elenco per la UI: id, etichetta, NOME della variabile (mai il valore),
    se è configurato e se questo roster ne ha bisogno."""
    need = keys_needed(model_ids, claude_cli)
    out = []
    for p in PROVIDERS.values():
        out.append({
            "id": p.id,
            "label": p.label,
            "key_env": p.key_env,
            "configured": bool(p.key_env and env.get(p.key_env)) if p.key_env else True,
            "needed": bool(p.key_env and p.key_env in need),
            "suggested": list(p.suggested),
        })
    return out


# ── auto-cast: a ogni ruolo il miglior modello tra quelli disponibili ────────
# Per chi apre il progetto con le SUE chiavi (una sola o tutte): niente nomi di
# modelli da conoscere. Le preferenze rispecchiano il roster ADV; dopo di esse
# vale un modello di ripiego per provider. Un ruolo non assegnabile (nessun
# provider disponibile) NON riceve un modello inventato: manca dal risultato.
ROLE_PREFERENCES: dict[str, tuple[str, ...]] = {
    "market_researcher": ("gemini/gemini-3.1-pro-preview",),
    "creative_strategist": ("anthropic/claude-sonnet-5",),
    "cd": ("anthropic/claude-opus-5",),
    "copywriter": ("featherless_ai/anthracite-org/magnum-v4-72b",),
    "social": ("xai/grok-4.5",),
    # Bake-off v2 (evals/results/producer-v2.json): Sonnet 5.5 e Haiku 5.5 passano
    # tutte le soglie; Hermes-3 e Qwen2.5-72B no (lingua, lunghezza, latenza).
    "producer": ("anthropic/claude-sonnet-5-5", "anthropic/claude-haiku-5-5"),
    "dark_angel": ("venice/abliteration-abliterated-model-large-v2",
                   "featherless_ai/EVA-UNIT-01/EVA-Qwen2.5-72B-v0.2",
                   "openrouter/cognitivecomputations/dolphin-mistral-24b-venice-edition"),
    "copywriter_2": ("anthropic/claude-opus-4-8",),
    "account_director": ("featherless_ai/Qwen/Qwen2.5-72B-Instruct",),
}

# Ripiego per provider, in ordine di preferenza (solo modelli già provati dal
# vivo in questo progetto: nessun id inventato).
FALLBACK_MODELS: tuple[str, ...] = (
    "anthropic/claude-sonnet-5",
    "gemini/gemini-3.1-pro-preview",
    "featherless_ai/Qwen/Qwen2.5-72B-Instruct",
    "xai/grok-4.5",
    "openrouter/cognitivecomputations/dolphin-mistral-24b-venice-edition",
)


def available_providers(env, claude_cli: bool) -> set[str]:
    """I provider che QUESTO utente può usare: chiave presente, oppure Claude con
    la CLI in abbonamento. Ollama (locale) non si dà per disponibile."""
    out = {p.id for p in PROVIDERS.values() if p.key_env and env.get(p.key_env)}
    if claude_cli:
        out.add("anthropic")
    return out


def autocast(roles, available: set[str]) -> dict[str, str]:
    """{ruolo: model_id}. Per ogni ruolo il primo modello preferito il cui
    provider è disponibile e non ancora usato (diversità); se tutti i preferiti
    sono già presi o assenti, il ripiego; se proprio non c'è niente, il ruolo
    resta fuori. Con un solo provider la diversità si perde, per forza."""
    def ok(m: str) -> bool:
        p = provider_of(m)
        return bool(p and p.id in available)

    out: dict[str, str] = {}
    used: set[str] = set()
    for role in roles:
        candidates = [m for m in (*ROLE_PREFERENCES.get(role, ()), *FALLBACK_MODELS) if ok(m)]
        pick = next((m for m in candidates if m not in used), candidates[0] if candidates else None)
        if pick:
            out[role] = pick
            used.add(pick)
    return out

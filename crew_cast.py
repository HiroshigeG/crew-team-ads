"""
Crew Team Ads — the shared core.
================================
The desktop app (`app.py`) imports from here for cast (persona + model per head),
routing brain, and gated web search. The legacy terminal room (`room.py`) predates
this module and keeps its own inline copy of these until it is replaced by the new
terminal UI (`room_tui.py`). So personas and models are defined once per active
front-end.

Nothing in this module prints or draws — the front-end owns all I/O.
"""

import json
import os
import re
import shutil
import subprocess
import urllib.error
import urllib.request

try:
    from dotenv import load_dotenv
    _here = os.path.dirname(os.path.abspath(__file__))
    load_dotenv(os.path.join(_here, ".env"))
    load_dotenv(os.path.join(_here, "..", ".env"))
except ImportError:
    pass

from crewai import LLM

# Niente eccezioni ingoiate (Fase 4): tutto ciò che prima moriva in un
# `pass` ora lascia almeno una riga di log — è il difetto che ha reso
# non diagnosticabile il guasto del 03/08.
import logging
log = logging.getLogger("crew_cast")

REQUIRED_KEYS = ("ANTHROPIC_API_KEY", "GEMINI_API_KEY", "XAI_API_KEY")


def missing_keys() -> list:
    """Which API keys are absent — the front-end decides how to complain."""
    return [k for k in REQUIRED_KEYS if not os.getenv(k)]


# ── Claude: subscription first, metered API only as a fallback ─────────────
# The Anthropic API and a Claude subscription are separate wallets: an API key
# spends API credits, the subscription does not. The local `claude` CLI is
# already signed in with the subscription, so we drive Claude through it and
# only fall back to the paid API when the CLI is missing or fails.

CLAUDE_CLI = shutil.which("claude")
# Rete di sicurezza contro processi appesi, non un guinzaglio (D5): i turni
# veri — ricerca, script, effort alto — possono legittimamente durare minuti.
# CREW_CLAUDE_TIMEOUT nell'ambiente lo cambia senza toccare il codice.
CLAUDE_TIMEOUT = 1800


def _cli_timeout() -> float:
    return float(os.getenv("CREW_CLAUDE_TIMEOUT", CLAUDE_TIMEOUT))


# Contesto di stanza condiviso (D18). Prima erano 8000 CARATTERI (~2000 token):
# le teste erano quasi cieche sulla storia. Ora un budget unico e ampio, UGUALE
# per tutte le teste. Tetto: le teste Featherless (magnum, EVA) hanno finestra
# 32.768 TOKEN totali (contesto+risposta), quindi il budget resta ben sotto per
# lasciare spazio a persona, istruzione e a un turno lungo. Chi vuole spingere:
# CREW_CONTEXT_CHARS (ma oltre ~90k caratteri le teste 72B sforano i 32k token).
CONTEXT_CHARS = 60000        # ~16k token: enorme vs prima, sicuro sotto i 32k
ROUTER_CONTEXT_CHARS = 12000  # il router classifica: gli basta il recente


def _context_chars() -> int:
    return int(os.getenv("CREW_CONTEXT_CHARS", CONTEXT_CHARS))


_route_log = []          # ["subscription"|"api", …] — front-ends may show this


def last_claude_route() -> str:
    return _route_log[-1] if _route_log else "?"


# Aggancio additivo per il contratto web (EVENT-CONTRACT §7.2): il fallback
# del router non deve più essere silenzioso — lezione del 03/08.
_plan_route_log = []     # ["waves"|"fallback", …]


def last_plan_route() -> str:
    return _plan_route_log[-1] if _plan_route_log else "?"


class ClaudeTimeoutError(RuntimeError):
    """CLI oltre il tempo massimo (D5). `partial` è l'output già prodotto al
    momento dello stop: il front-end può mostrarlo come bozza nel canale
    privato della testa invece di buttarlo."""

    def __init__(self, msg: str, partial: str = ""):
        super().__init__(msg)
        self.partial = partial


class ClaudeLLM:
    """Drop-in for crewai.LLM: `.model` + `.call(prompt)`.

    Tries the subscription CLI first; falls back to the metered API.
    """

    def __init__(self, model: str, effort: str = ""):
        self.model = model
        # Profondità di ragionamento (D4/D10): "" = default della CLI.
        # Valori validi: low|medium|high|xhigh|max (un valore ignoto non è
        # fatale: la CLI avvisa e usa il default — verificato su 2.1.220).
        self.effort = effort
        # Rotta dell'ULTIMA chiamata di QUESTA istanza (EVENT-CONTRACT §7.3):
        # a differenza di last_claude_route() non è globale di processo.
        self.last_route = "?"
        # Perché l'ultima chiamata è finita sull'API: il motivo del fallback
        # non si inghiotte più (l'errore di credito del 03/08 notte è rimasto
        # invisibile per un'ora proprio per un `pass` qui sotto).
        self.last_cli_error = ""
        self._api = LLM(model=f"anthropic/{model}")

    def _via_cli(self, prompt: str) -> str:
        env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}
        # No API key/token/endpoint override in the environment => la CLI
        # non deve poter fatturare né deviare endpoint (bug hunt, item 15).
        env.pop("ANTHROPIC_API_KEY", None)
        env.pop("ANTHROPIC_AUTH_TOKEN", None)
        env.pop("ANTHROPIC_BASE_URL", None)
        cmd = [CLAUDE_CLI, "-p", "--output-format", "text", "--model", self.model]
        if self.effort:
            cmd += ["--effort", self.effort]
        r = subprocess.run(
            cmd,
            input=prompt, capture_output=True, text=True,
            env=env, timeout=_cli_timeout(),
        )
        if r.returncode != 0:
            raise RuntimeError(f"claude CLI exited {r.returncode}: {r.stderr[:200]}")
        out = r.stdout.strip()
        if not out:
            raise RuntimeError("claude CLI returned nothing")
        return out

    def call(self, prompt: str) -> str:
        cli_error = None
        if CLAUDE_CLI:
            try:
                out = self._via_cli(prompt)
                _route_log.append("subscription")
                self.last_route = "subscription"
                self.last_cli_error = ""
                return out
            except subprocess.TimeoutExpired as e:
                # Un timeout non è un guasto: la testa stava ancora lavorando.
                # Rifare da capo lo stesso lavoro sull'API (che di timeout non
                # ne ha) sarebbe il peggio dei due mondi: si segnala e decide
                # il front-end (D5). Niente fallback silenzioso, e quello che
                # la CLI aveva già scritto si salva come bozza, non si butta.
                out = e.stdout or ""
                if isinstance(out, bytes):
                    out = out.decode("utf-8", "replace")
                raise ClaudeTimeoutError(
                    f"claude CLI oltre il tempo massimo ({_cli_timeout():.0f}s):"
                    " nessun fallback automatico — ritenta o alza"
                    " CREW_CLAUDE_TIMEOUT",
                    partial=out.strip(),
                ) from None
            except Exception as e:
                # Fallback all'API sì, ma TRASPARENTE (D5-bis): il motivo
                # resta leggibile invece di sparire in un `pass`.
                cli_error = e
                self.last_cli_error = f"{type(e).__name__}: {str(e)[:200]}"
        try:
            out = str(self._api.call(prompt))
        except Exception as api_error:
            if cli_error is not None:
                # Entrambi i canali giù: l'errore dice TUTTA la verità,
                # non solo l'ultima metà.
                raise RuntimeError(
                    "Claude non disponibile su nessun canale — CLI: "
                    f"{self.last_cli_error} · API: "
                    f"{type(api_error).__name__}: {str(api_error)[:200]}"
                ) from api_error
            raise
        _route_log.append("api")
        self.last_route = "api"
        return out


def _grok_timeout() -> float:
    """I giri di ricerca server-side possono essere lenti (5+ tool call in un
    turno, misurato dal vivo): default largo, regolabile via env."""
    return float(os.getenv("CREW_GROK_TIMEOUT") or 180)


def grok_output_text(data: dict) -> str:
    """Il testo del turno da una risposta /v1/responses di xAI: si saltano i
    blocchi `reasoning` e `custom_tool_call` (i giri di ricerca interni di
    Grok) e si concatenano gli `output_text` dei blocchi `message`."""
    parts = []
    for item in data.get("output") or []:
        if item.get("type") != "message":
            continue
        for c in item.get("content") or []:
            if c.get("type") == "output_text" and c.get("text"):
                parts.append(c["text"])
    return "\n".join(parts).strip()


class GrokLiveLLM:
    """Drop-in per crewai.LLM per le teste xai/ con la ricerca live (D23-bis).

    05/08/2026: xAI ha spento la Live Search sulle chat completions — HTTP 410
    «Live search is deprecated» su `search_parameters`, e il formato nuovo
    `tools: [{"type": "live_search"}]` risponde 410 uguale. I tool server-side
    (web_search, x_search) vivono SOLO sull'endpoint /v1/responses, che
    litellm/crewai non attraversano: questo client minimale ci parla diretto.
    Stesso contratto di ClaudeLLM: `.model` + `.call(prompt)`. Grok decide da
    solo se e quanto cercare; le fonti recuperate si pagano — l'opt-in resta
    CREW_GROK_LIVE_SEARCH, come prima.
    """

    ENDPOINT = "https://api.x.ai/v1/responses"

    def __init__(self, model: str, temperature: float):
        self.model = model                # nome nudo, es. "grok-4.5"
        self.temperature = temperature

    def call(self, prompt: str) -> str:
        payload = {
            "model": self.model,
            "input": [{"role": "user", "content": prompt}],
            "temperature": self.temperature,
            "tools": [{"type": "web_search"}, {"type": "x_search"}],
        }
        req = urllib.request.Request(
            self.ENDPOINT, json.dumps(payload).encode(),
            {"Authorization": f"Bearer {os.getenv('XAI_API_KEY', '')}",
             "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=_grok_timeout()) as r:
                data = json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "replace")[:200]
            raise RuntimeError(
                f"xAI responses API: HTTP {e.code} — {detail}") from None
        out = grok_output_text(data)
        if not out:
            raise RuntimeError("xAI responses API: risposta senza testo")
        return out


# NB: Claude 5 models reject `temperature` — the API returns
# "`temperature` is deprecated for this model." Do not add it back.
llm_claude_voice = ClaudeLLM("claude-opus-5")
# The router only classifies who speaks next — a smaller model is plenty here,
# and a effort basso: la sua latenza è la reattività percepita della stanza (D4).
llm_claude_router = ClaudeLLM("claude-sonnet-5", effort="low")
# Giudica un /goal contro il transcript (v1.3): non è un partecipante della
# stanza, quindi stesso modello/effort economico del router gli basta.
llm_claude_judge = ClaudeLLM("claude-sonnet-5", effort="low")
llm_gemini = LLM(model="gemini/gemini-3.1-pro-preview", temperature=0.6)
llm_grok = LLM(model="xai/grok-4.5", temperature=0.75,
               additional_drop_params=["stop"])

ROOM_RULES = (
    "You are in a live writers' room brainstorming the executive idea for a "
    "brand's hero film (the current brief is in the room memory). The human "
    "DIRECTOR leads the room; you work for them. Speak in English, in first "
    "person, like a sharp colleague at the table: concrete, vivid, 80-180 "
    "words unless asked otherwise. Build on what was said before. Keep the "
    "brand's hero product the hero. Never invent statistics, campaign names, "
    "dates or numbers you cannot verify. If the Director tells you to consult "
    "a colleague, address them directly with a crisp question."
    "\n\nWEB ACCESS — you may search the web, but only with the Director's "
    "permission, and you must say why. When something would genuinely change "
    "your answer and you cannot know it for certain (what a competitor has "
    "actually run, whether a territory is already taken, a current cultural "
    "reference), do NOT guess and do NOT invent: end your turn with a line in "
    "exactly this form, on its own line:\n"
    "SEARCH_REQUEST: <search query> || <why you need it, one line>\n"
    "The Director approves or denies. Ask only when it matters — at most ONE "
    "request per turn, and never for something you already know."
)

# The persona personas: ROOM_RULES + ROLE_PERSONAS[key] = CAST[key]["persona"]
ROLE_PERSONAS = {
    "producer": " You are the Executive Producer: you keep the room honest and "
                "moving, summarize when useful, and protect the mandate (the "
                "product is the hero). You never pick the final idea — that's the "
                "Director's call.",
    "strategist": " You are the Brand Truth Strategist: you think in codes and "
                  "myth, brand truths and human tensions. You leave execution to "
                  "the Creative Director.",
    "cd": " You are the Creative Director: you turn truths into executional "
          "directions — concept, visual world, how the product stays the hero. "
          "Tension and craft, not safe beauty.",
    "social": " You are the Social & Precedent Analyst: you know the genre's "
              "grammar and its social life. You call out clichés ('seen a thousand "
              "times — avoid') and point to what stays ownable and social-first. "
              "Patterns and tropes only.",
}

SEARCH_RE = re.compile(r"^\s*SEARCH_REQUEST:\s*(.+?)\s*\|\|\s*(.+?)\s*$",
                       re.MULTILINE)
# D23: richiesta al tool "social intel" (es. il TikTok analyzer). Stessa forma
# del SEARCH_REQUEST, stesso gate HITL, ma backend diverso (social_intel()).
SOCIAL_RE = re.compile(r"^\s*SOCIAL_INTEL:\s*(.+?)\s*\|\|\s*(.+?)\s*$",
                       re.MULTILINE)

# ── the cast ───────────────────────────────────────────────────────────────
# `pane`   -> tmux log name (terminal front-end)
# `color`  -> ANSI colour   (terminal front-end)
# `avatar` -> emoji         (desktop front-end)
CAST = {
    "producer": {
        "name": "Executive Producer",
        "pane": "orchestrator",
        "color": "\033[38;5;178m",
        "avatar": "🧭",
        "llm": llm_claude_voice,
        "persona": ROOM_RULES + ROLE_PERSONAS["producer"],
    },
    "strategist": {
        "name": "Strategist",
        "pane": "strategist",
        "color": "\033[38;5;75m",
        "avatar": "🧠",
        "llm": llm_gemini,
        "persona": ROOM_RULES + ROLE_PERSONAS["strategist"],
    },
    "cd": {
        "name": "Creative Director",
        "pane": "creative",
        "color": "\033[38;5;208m",
        "avatar": "🎨",
        "llm": llm_claude_voice,
        "persona": ROOM_RULES + ROLE_PERSONAS["cd"],
    },
    "social": {
        "name": "Social & Precedent Analyst",
        "pane": "social",
        "color": "\033[38;5;84m",
        "avatar": "📡",
        "llm": llm_grok,
        "persona": ROOM_RULES + ROLE_PERSONAS["social"],
    },
}

ALIASES = {
    "producer": "producer", "prod": "producer", "ep": "producer",
    "strategist": "strategist", "strategy": "strategist", "strat": "strategist",
    "cd": "cd", "creative": "cd", "creative director": "cd",
    "social": "social", "analyst": "social",
}

ROUTER_PROMPT = """You are the routing brain of a writers' room. Cast keys: producer, strategist, cd, social.
Given the room transcript and the Director's latest message, output ONLY a JSON array (no prose) of 1-4 steps:
[{{"speaker": "<cast key>", "instruction": "<what they should do now, one line>"}}]

Routing rules:
- If the Director addresses someone, that person speaks (first).
- If the Director asks X to consult/ask Y, plan: X (poses the question), Y (answers), X (brief reaction). Use those exact cast keys.
- If the Director says someone should wait/hold, do NOT include them.
- Generic creative prompts: pick the 1-2 most relevant specialists; the producer only speaks to synthesize or unblock.
- Keep instructions short and specific to the Director's message.

TRANSCRIPT (latest last):
{transcript}

DIRECTOR'S MESSAGE: {msg}

JSON:"""


def route(transcript: str, msg: str) -> list:
    """Who speaks next. Falls back to keyword match, then the producer."""
    try:
        raw = llm_claude_router.call(
            ROUTER_PROMPT.format(transcript=transcript[-ROUTER_CONTEXT_CHARS:], msg=msg))
        m = re.search(r"\[.*\]", str(raw), re.DOTALL)
        plan = json.loads(m.group(0)) if m else []
        plan = [s for s in plan
                if isinstance(s, dict) and s.get("speaker") in CAST][:4]
        if plan:
            return plan
    except Exception as e:
        log.warning("router v1 fallito (%s): fallback alias/producer", e)
    low = msg.lower()
    for alias, key in ALIASES.items():
        if low.startswith(alias):
            return [{"speaker": key, "instruction": msg}]
    return [{"speaker": "producer", "instruction": msg}]


def web_search(query: str, n: int = 5) -> str:
    """Keyless web search (DuckDuckGo). Returns a compact digest for the agent."""
    try:
        from ddgs import DDGS
        hits = list(DDGS().text(query, max_results=n))
    except Exception as e:
        return f"[search failed: {e}]"
    if not hits:
        return "[no results]"
    return "\n".join(
        f"- {h.get('title','')} — {h.get('body','')[:220]} ({h.get('href','')})"
        for h in hits
    )


# D23: tool "social intel" agganciabile dall'esterno (es. il TikTok analyzer).
# Il repo pubblico NON cabla nessun percorso: si configura via env, così resta
# pulito e portabile. Il comando riceve la query come ULTIMO argomento e scrive
# il digest su stdout; qualunque sentinella fra parentesi quadre = non usabile.
SOCIAL_TOOL_TIMEOUT = int(os.getenv("CREW_SOCIAL_TOOL_TIMEOUT") or 180)


def social_intel(query: str) -> str:
    """Interroga il tool social configurato in CREW_SOCIAL_TOOL_CMD e ne ritorna
    il digest. Non configurato -> sentinella esplicita (la testa lo dice in
    chiaro, non inventa). Il comando decide cosa fa: leggere un signal.json già
    prodotto (gratis) o lanciare uno scrape live (pesante) — al motore non
    interessa, è un backend a scatola chiusa."""
    cmd = os.getenv("CREW_SOCIAL_TOOL_CMD")
    if not cmd:
        return "[social tool not configured]"
    import shlex
    import subprocess
    try:
        argv = shlex.split(cmd) + [query]
        out = subprocess.run(argv, capture_output=True, text=True,
                             timeout=SOCIAL_TOOL_TIMEOUT)
    except subprocess.TimeoutExpired:
        return f"[social tool timed out after {SOCIAL_TOOL_TIMEOUT}s]"
    except Exception as e:
        log.warning("social tool non eseguibile (%s)", e)
        return f"[social tool failed: {e}]"
    if out.returncode != 0:
        return f"[social tool error rc={out.returncode}: {(out.stderr or '').strip()[:300]}]"
    digest = (out.stdout or "").strip()
    if not digest:
        return "[social tool returned nothing]"
    return digest[:6000]      # è un digest per la stanza, non un dump


def speak(key: str, transcript: str, instruction: str) -> str:
    """One agent takes the floor. May come back with a SEARCH_REQUEST line."""
    c = CAST[key]
    prompt = (
        f"{c['persona']}\n\nROOM TRANSCRIPT (latest last):\n{transcript[-8000:]}\n"
        f"The floor is yours now. Your brief for this turn: {instruction}\n"
        f"Speak as {c['name']}:"
    )
    return str(c["llm"].call(prompt)).strip()


def parse_search_request(reply: str):
    """-> (clean_reply, query, why) or (reply, None, None) if no request."""
    m = SEARCH_RE.search(reply)
    if not m:
        return reply, None, None
    return SEARCH_RE.sub("", reply).strip(), m.group(1).strip(), m.group(2).strip()


def parse_social_request(reply: str):
    """-> (clean_reply, query, why) or (reply, None, None). Gemello di
    parse_search_request per la riga SOCIAL_INTEL (D23)."""
    m = SOCIAL_RE.search(reply)
    if not m:
        return reply, None, None
    return SOCIAL_RE.sub("", reply).strip(), m.group(1).strip(), m.group(2).strip()


def speak_after_search(key: str, transcript: str, why: str,
                       query: str = None, results: str = None) -> str:
    """Second turn, once the Director has ruled on the search request.

    `query`/`results` present -> approved.  Both None -> denied.
    """
    c = CAST[key]
    if results is None:
        outcome = ("The Director DENIED your search request. Answer now without "
                   "it: be explicit about what you cannot verify, and do not "
                   "invent it.")
    else:
        outcome = (f"The Director APPROVED your search. Query: {query}\n"
                   f"RESULTS:\n{results}\n\n"
                   f"Use these results now. Cite only what the results actually "
                   f"say; if they don't answer the question, say so plainly.")
    prompt = (
        f"{c['persona']}\n\nROOM TRANSCRIPT (latest last):\n{transcript[-8000:]}\n"
        f"You had asked to search the web because: {why}\n{outcome}\n"
        f"Now give your turn in full, as {c['name']} "
        f"(no SEARCH_REQUEST line this time):"
    )
    return str(c["llm"].call(prompt)).strip()


def build_brief(brand: str, theme: str, mandate: str, medium: str) -> str:
    """Assemble a brief in the upstream shape the crew expects: no execution."""
    return (
        f"PROJECT: a hero film for {brand}.\n\n"
        f"LAUNCH THEME: {theme}\n\n"
        f"MANDATE: {mandate}\n\n"
        f"MEDIUM: {medium}\n\n"
        "WHAT WE DON'T HAVE YET (and it's this room's job): the EXECUTIVE IDEA. "
        "No execution has been decided — it must emerge by confronting "
        "different directions."
    )


# ═══════════════════════════════════════════════════════════════════════════
# Estensioni per la TUI (room_tui.py) — additive: nulla sopra cambia.
# Spec: docs/superpowers/specs/2026-07-28-crew-room-tui-design.md
# ═══════════════════════════════════════════════════════════════════════════
from dataclasses import dataclass, asdict, field

_HERE = os.path.dirname(os.path.abspath(__file__))

# Gli unici ID verificati sul registry litellm (T2 del brief).
# opus-4-8 aggiunto (D17): la CLI in abbonamento lo serve anche a effort max
# (smoke test 03/08), utile come seconda voce di copy accanto a magnum.
VERIFIED_MODELS = [
    "anthropic/claude-opus-5",
    "anthropic/claude-opus-4-8",
    "anthropic/claude-sonnet-5",
    "gemini/gemini-3.1-pro-preview",
    "xai/grok-4.5",
]


def temp_for_level(level: int) -> float:
    """Slider 0-10 -> temperature 0.1-1.2 (per i modelli che la accettano)."""
    level = max(0, min(10, level))
    return round(0.1 + 0.11 * level, 2)


# Claude 5 rifiuta `temperature` (T1): per quei modelli la creatività si guida
# a parole. Scala ancorata punto-per-punto (D8): ogni gradino è una regola
# CONTABILE, non un aggettivo — «la maggioranza delle idee rischiosa» sposta
# l'output in modo verificabile, «sii creativo» no. Da 0 a 4 la scala stringe
# (quanta prudenza), da 6 a 10 allarga (quanto rischio obbligatorio). Il 5
# resta neutro: nessuna iniezione = comportamento naturale del modello.
_CREATIVITY_BLOCKS = {
    0: "CREATIVE RISK SETTING (dial 0/10): only approaches with a citable "
       "precedent. If you cannot name where it worked before, do not "
       "propose it.",
    1: "CREATIVE RISK SETTING (dial 1/10): stay with proven formulas; "
       "explicitly mark anything non-standard as such.",
    2: "CREATIVE RISK SETTING (dial 2/10): prefer the reliable angle; one "
       "cautious variation is allowed.",
    3: "CREATIVE RISK SETTING (dial 3/10): mostly safe ground — at most one "
       "idea outside the formula, and flag it as the risky one.",
    4: "CREATIVE RISK SETTING (dial 4/10): default behaviour with a brake — "
       "avoid risk the brief does not require.",
    # 5: neutro — nessuna iniezione.
    6: "CREATIVE RISK SETTING (dial 6/10): push past the obvious — at least "
       "one of the ideas you put forward must be genuinely risky, and say "
       "why it might fail.",
    7: "CREATIVE RISK SETTING (dial 7/10): make genuinely risky ideas the "
       "majority of what you propose, and skip the genre's first obvious "
       "reference.",
    8: "CREATIVE RISK SETTING (dial 8/10): everything you propose must be "
       "risky except at most one safe anchor, and no references to existing "
       "campaigns.",
    9: "CREATIVE RISK SETTING (dial 9/10): unseen territory only — if it "
       "feels familiar, discard it before you speak.",
    10: "CREATIVE RISK SETTING (dial 10/10): nothing a client would approve "
        "at first glance. Take real risks — the Director will pull you back "
        "if needed.",
}


def creativity_block(level: int) -> str:
    return _CREATIVITY_BLOCKS.get(level, "")


@dataclass
class Head:
    """Una testa del roster: dato, non costante — editabile a runtime (R4)."""
    key: str
    name: str
    avatar: str
    color: str            # colore Textual (hex), non ANSI
    model_id: str         # con prefisso provider, es. "anthropic/claude-opus-5"
    persona: str          # SOLO la parte di ruolo: ROOM_RULES si antepone al volo
    creativity: int = 5
    # Profondità di ragionamento (D4/D10): oggi agisce solo sulle teste
    # anthropic/* (flag --effort della CLI); per gemini/xai è un no-op
    # dichiarato finché il passaggio API non è smoke-testato. "" = default.
    effort: str = ""

    def mechanism_label(self) -> str:
        """Il badge onesto: con che meccanismo lo slider agisce QUI (T1)."""
        if self.model_id.startswith("anthropic/"):
            return "via prompt"
        return f"via temperature {temp_for_level(self.creativity)}"

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Head":
        return cls(**d)

ROSTER_PATH = os.path.join(_HERE, "roster.json")

# Bug hunt item 14: una chiave di testa deve avere questa forma — minuscola,
# comincia per lettera, solo [a-z0-9_], max 32 caratteri (il limite di
# `head{N}` più margine per chiavi scelte a mano). Un roster.json editato a
# mano (o corrotto) con una chiave fuori formato non deve buttare giù
# l'intero roster: si scarta solo quella testa.
_HEAD_KEY_RE = re.compile(r"^[a-z][a-z0-9_]{0,31}$")

# Colori Textual per le teste di default (equivalenti dei vecchi ANSI di CAST).
_DEFAULT_HEAD_META = {
    "producer":   ("#d7af00",),
    "strategist": ("#5fafff",),
    "cd":         ("#ff8700",),
    "social":     ("#5fff87",),
}


# Modelli open oltre la whitelist (D14): Featherless (abbonamento flat,
# 4.000+ modelli HF via litellm `featherless_ai/`, chiave
# FEATHERLESS_AI_API_KEY) e Ollama locale (`ollama/`). Il percorso generico
# di make_llm li serve già: qui si decide solo COSA è ammesso nel roster.
OPEN_MODEL_PREFIXES = ("featherless_ai/", "openrouter/", "ollama/")


def model_allowed(model_id: str) -> bool:
    return model_id in VERIFIED_MODELS or model_id.startswith(OPEN_MODEL_PREFIXES)


def make_llm(head: Head):
    """L'LLM giusto per una testa. anthropic/* passa SEMPRE da ClaudeLLM
    (subscription-first, T4); temperature solo dove è accettata (T1)."""
    if head.model_id.startswith("anthropic/"):
        return ClaudeLLM(head.model_id.split("/", 1)[1], effort=head.effort)
    kwargs = {"model": head.model_id,
              "temperature": temp_for_level(head.creativity)}
    if head.model_id.startswith("xai/"):
        kwargs["additional_drop_params"] = ["stop"]   # T5
        # D23-bis (05/08): xAI ha dismesso la Live Search delle chat
        # completions (HTTP 410) — con l'opt-in acceso la testa Grok passa dal
        # client dedicato sull'endpoint /v1/responses coi tool server-side
        # (web_search + x_search). Flag spento = Grok normale, niente ricerca.
        if os.getenv("CREW_GROK_LIVE_SEARCH", "").lower() in ("1", "true", "yes", "on"):
            return GrokLiveLLM(head.model_id.split("/", 1)[1],
                               temperature=temp_for_level(head.creativity))
    return LLM(**kwargs)


class Roster:
    """Il cast come dato editabile e persistito (R4). CAST resta il default."""

    def __init__(self, heads: "dict[str, Head]"):
        self.heads = heads
        self._llms = {}          # cache: ricostruire un LLM a ogni turno è spreco

    @classmethod
    def default(cls) -> "Roster":
        heads = {}
        for key, c in CAST.items():
            if isinstance(c["llm"], ClaudeLLM):
                model_id = f"anthropic/{c['llm'].model}"
            else:
                m = c["llm"].model
                if "/" not in m:
                    # crewai normalizza il prefisso provider in modo asimmetrico:
                    # per Gemini usa una classe di completion dedicata che
                    # spacchetta "provider/model" e lascia in .model SOLO il nome
                    # nudo, mentre per xai resta sulla LLM generica (litellm) e
                    # .model mantiene il prefisso per intero. Senza riattaccarlo,
                    # make_llm() non riconosce il provider e litellm ricade su
                    # OpenAI di default (bug trovato dallo smoke live, T6).
                    m = next((v for v in VERIFIED_MODELS if v.endswith("/" + m)), m)
                model_id = m
            heads[key] = Head(
                key=key, name=c["name"], avatar=c["avatar"],
                color=_DEFAULT_HEAD_META[key][0],
                model_id=model_id,
                persona=ROLE_PERSONAS[key],
            )
        return cls(heads)

    @classmethod
    def load(cls, path: str = None) -> "Roster":
        path = path or ROSTER_PATH
        if not os.path.exists(path):
            return cls.default()
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            heads = {}
            for d in data["heads"]:
                key = str(d.get("key", "")).lower()
                if not _HEAD_KEY_RE.match(key):
                    # Bug 14: chiave fuori formato — si scarta SOLO questa
                    # testa, le altre restano (nessun motivo di perdere un
                    # intero roster editato a mano per una voce sbagliata).
                    log.warning("roster: testa con chiave invalida scartata "
                                "(%r)", d.get("key"))
                    continue
                heads[key] = Head.from_dict({**d, "key": key})
            if not heads:
                raise ValueError("roster vuoto")
            return cls(heads)
        except Exception as e:
            # File rotto: da parte (mai cancellare lavoro altrui), poi default.
            log.warning("roster illeggibile (%s): copio in %s.bad e torno "
                        "al default", e, path)
            try:
                shutil.copy(path, path + ".bad")
            except OSError as copy_err:
                log.warning("copia di sicurezza fallita: %s", copy_err)
            return cls.default()

    def save(self, path: str = None):
        path = path or ROSTER_PATH
        # Bug 13: scrittura atomica — un crash/kill a metà `json.dump` non
        # deve lasciare un roster.json troncato e illeggibile. Si scrive su
        # un file temporaneo e si sostituisce con `os.replace` (atomico sullo
        # stesso filesystem).
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"heads": [h.to_dict() for h in self.heads.values()]},
                      f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)

    def keys(self):
        return self.heads.keys()

    def llm(self, key: str):
        if key not in self._llms:
            self._llms[key] = make_llm(self.heads[key])
        return self._llms[key]

    def update_head(self, key: str, **fields):
        h = self.heads[key]
        for name, value in fields.items():
            setattr(h, name, value)
        self._llms.pop(key, None)      # modello/creatività cambiati -> LLM nuovo

    def add_head(self, head: Head):
        self.heads[head.key] = head

    def remove_head(self, key: str):
        if len(self.heads) == 1:
            raise ValueError("la stanza non può restare senza teste")
        self.heads.pop(key)
        self._llms.pop(key, None)


PRIVATE_PREAMBLE = (
    "PRIVATE SIDEBAR — this is a one-to-one conversation with the Director. "
    "The rest of the room cannot see it and never will. Speak freely and "
    "candidly; this exchange will not appear in the room transcript."
)


def build_turn_prompt(head: Head, context: str, instruction: str,
                      private: bool = False) -> str:
    """Il prompt di un turno, ricomposto dal roster: ROOM_RULES centralizzate,
    creatività iniettata solo fuori dalla fascia neutra (T1), preambolo se
    la conversazione è privata. Puro: testabile senza API."""
    parts = [ROOM_RULES + head.persona]
    block = creativity_block(head.creativity)
    # Il blocco a parole solo dove la temperatura non esiste (anthropic, T1):
    # per Gemini/Grok lo slider agisce già via temperatura, e dare entrambi
    # significava doppio effetto non dichiarato (D6).
    if block and head.model_id.startswith("anthropic/"):
        parts.append(block)
    if private:
        parts.append(PRIVATE_PREAMBLE)
    parts.append(f"ROOM TRANSCRIPT (latest last):\n{context[-_context_chars():]}")
    parts.append(f"The floor is yours now. Your brief for this turn: "
                 f"{instruction}\nSpeak as {head.name}:")
    return "\n\n".join(parts)


def build_after_search_prompt(head: Head, context: str, why: str,
                              query: str = None, results: str = None,
                              private: bool = False) -> str:
    """Secondo turno dopo il verdetto del Director sul SEARCH_REQUEST."""
    if results is None:
        outcome = ("The Director DENIED your search request. Answer now "
                   "without it: be explicit about what you cannot verify, "
                   "and do not invent it.")
    else:
        outcome = (f"The Director APPROVED your search. Query: {query}\n"
                   f"RESULTS:\n{results}\n\n"
                   f"Use these results now. Cite only what the results "
                   f"actually say; if they don't answer the question, say so "
                   f"plainly.")
    parts = [ROOM_RULES + head.persona]
    if private:
        parts.append(PRIVATE_PREAMBLE)
    parts.append(f"ROOM TRANSCRIPT (latest last):\n{context[-_context_chars():]}")
    parts.append(f"You had asked to search the web because: {why}\n{outcome}\n"
                 f"Now give your turn in full, as {head.name} "
                 f"(no SEARCH_REQUEST line this time):")
    return "\n\n".join(parts)


def head_speak(roster: Roster, key: str, context: str, instruction: str,
               private: bool = False) -> str:
    head = roster.heads[key]
    prompt = build_turn_prompt(head, context, instruction, private)
    return str(roster.llm(key).call(prompt)).strip()


# Visione (D15): in v1.1 SOLO le teste Gemini leggono immagini — la
# GEMINI_API_KEY funziona e il percorso multimodale di litellm è pulito.
# Additivo: non tocca head_speak né la CLI di Claude (che è text-only).
def vision_capable(model_id: str) -> bool:
    return model_id.startswith("gemini/")


def head_study_image(roster: Roster, key: str, context: str, instruction: str,
                     image_b64: str, media_type: str = "image/png") -> str:
    head = roster.heads[key]
    if not vision_capable(head.model_id):
        raise ValueError(
            f"{key}: il modello {head.model_id} non legge immagini "
            "(visione solo su teste Gemini in v1.1)")
    import litellm
    prompt = build_turn_prompt(head, context, instruction)
    messages = [{"role": "user", "content": [
        {"type": "text", "text": prompt},
        {"type": "image_url",
         "image_url": {"url": f"data:{media_type};base64,{image_b64}"}},
    ]}]
    resp = litellm.completion(model=head.model_id,
                             temperature=temp_for_level(head.creativity),
                             messages=messages)
    return str(resp.choices[0].message.content).strip()


def vision_head(roster: Roster) -> "str | None":
    """La prima testa capace di visione nel roster (per lo smistamento
    automatico delle immagini)."""
    for k, h in roster.heads.items():
        if vision_capable(h.model_id):
            return k
    return None


def head_speak_after_search(roster: Roster, key: str, context: str, why: str,
                            query: str = None, results: str = None,
                            private: bool = False) -> str:
    head = roster.heads[key]
    prompt = build_after_search_prompt(head, context, why, query, results,
                                       private)
    return str(roster.llm(key).call(prompt)).strip()


class RoomSession:
    """Transcript di stanza + canali privati, scritti su disco A OGNI turno:
    un crash non perde la sessione. Il privato è stagno per costruzione — i
    contesti pubblici semplicemente non lo contengono (spec §7-bis)."""

    def __init__(self, brief: str, base_dir: str = None, stamp: str = None):
        from datetime import datetime
        self.brief = brief
        self.base_dir = base_dir or os.path.join(_HERE, "transcripts")
        os.makedirs(self.base_dir, exist_ok=True)
        # Bug 5: uno stamp al minuto (o due sessioni con lo stesso stamp
        # esplicito) faceva sovrascrivere in `_flush_room` il transcript
        # della sessione precedente aperta nello stesso minuto. Granularità
        # al secondo + uniquificazione sullo STAMP (non solo sul path):
        # `private_path` riusa `self.stamp`, quindi i canali privati
        # ereditano l'unicità senza toccare altro.
        base_stamp = stamp or datetime.now().strftime("%Y%m%d-%H%M%S")
        self.stamp = base_stamp
        n = 2
        while os.path.exists(os.path.join(self.base_dir, f"room-{self.stamp}.md")):
            self.stamp = f"{base_stamp}-{n}"
            n += 1
        self.room_text = ""
        self._private = {}                       # key -> str
        self.room_path = os.path.join(self.base_dir, f"room-{self.stamp}.md")
        self._flush_room()

    # — stanza —
    def room_context(self) -> str:
        return f"BRIEF:\n{self.brief}\n\n{self.room_text}"

    def append_room(self, label: str, text: str):
        self.room_text += f"{label}: {text}\n"
        self._flush_room()

    def _flush_room(self):
        with open(self.room_path, "w", encoding="utf-8") as f:
            f.write("# Writers' Room transcript\n\n"
                    f"BRIEF:\n{self.brief}\n\n{self.room_text}")

    # — privato (stagno) —
    def private_path(self, key: str) -> str:
        return os.path.join(self.base_dir, f"private-{key}-{self.stamp}.md")

    def private_context(self, key: str) -> str:
        # La testa in privato vede la stanza (per contesto) + il SUO privato.
        return (f"BRIEF:\n{self.brief}\n\n{self.room_text}\n"
                f"--- PRIVATE SIDEBAR (only you and the Director) ---\n"
                f"{self._private.get(key, '')}")

    def append_private(self, key: str, label: str, text: str):
        self._private[key] = self._private.get(key, "") + f"{label}: {text}\n"
        with open(self.private_path(key), "w", encoding="utf-8") as f:
            f.write(f"# Private — {key}\n\n{self._private[key]}")


# ── Task 5: router a ondate (R1/R3) + trigger collab (R6) ────────────────────

PLAN_PROMPT = """You are the routing brain of a writers' room. The cast right now:
{cast_lines}

Given the transcript and the Director's message, output ONLY a JSON array of WAVES
(no prose). A wave is a list of steps that can run IN PARALLEL because they don't
depend on each other; waves run one after another. 1-4 steps total.
Each step: {{"speaker": "<cast key>", "instruction": "<one line>", "to": "<who they
answer: 'director' or a cast key>"}}

Rules:
- Director addresses someone -> that person speaks (first wave).
- "X, ask Y ..." (consult) -> waves: [[X poses the question (to Y)]], [[Y answers (to X)]], [[X reacts (to director)]]. Consults are NEVER parallel.
- Independent takes on the same prompt -> ONE wave with those speakers (to director).
- If the Director says someone should wait/hold, do NOT include them.
- Generic prompts: the 1-2 most relevant specialists.

TRANSCRIPT (latest last):
{transcript}

DIRECTOR'S MESSAGE: {msg}

JSON:"""


def parse_wave_plan(raw: str, valid_keys) -> list:
    """Estrae e valida le ondate dall'output del router. Puro e paranoico:
    qualunque cosa non torni -> [] (il chiamante ha il fallback)."""
    m = re.search(r"\[\s*\[.*\]\s*\]", str(raw), re.DOTALL)
    if not m:
        return []
    try:
        data = json.loads(m.group(0))
    except json.JSONDecodeError:
        return []
    waves, total = [], 0
    for wave in data:
        if not isinstance(wave, list):
            return []
        steps = []
        for s in wave:
            if not (isinstance(s, dict) and s.get("speaker") in valid_keys):
                continue
            if total >= 4:
                break
            to = s.get("to", "director")
            if to not in valid_keys and to != "director":
                to = "director"
            if to == s["speaker"]:
                # Bug 12: il router a volte indirizza una testa a se stessa
                # (cross-talk auto-diretto senza senso) — si normalizza al
                # Director, come un "to" mancante o invalido.
                to = "director"
            steps.append({"speaker": s["speaker"],
                          "instruction": str(s.get("instruction", "")),
                          "to": to})
            total += 1
        if steps:
            waves.append(steps)
    return waves


def route_plan(roster: Roster, transcript: str, msg: str) -> list:
    """Chi parla, in che ordine, in parallelo dove si può (R1) e rivolto a chi
    (R3). Il prompt elenca il roster CORRENTE: una testa aggiunta a runtime è
    instradabile subito. Fallback: la catena di oggi, seriale."""
    cast_lines = "\n".join(
        f"- {h.key}: {h.name} — {h.persona.strip()[:90]}"
        for h in roster.heads.values())
    try:
        raw = llm_claude_router.call(PLAN_PROMPT.format(
            cast_lines=cast_lines, transcript=transcript[-ROUTER_CONTEXT_CHARS:], msg=msg))
        waves = parse_wave_plan(raw, set(roster.keys()))
        if waves:
            _plan_route_log.append("waves")
            return waves
    except Exception as e:
        log.warning("router a ondate fallito (%s): fallback sequenziale", e)
    # Fallback: il router v1 (o keyword/producer) in ondate da un passo l'una.
    # Non più silenzioso: last_plan_route() lo espone al front-end (§7.2).
    _plan_route_log.append("fallback")
    steps = [s for s in route(transcript, msg) if s["speaker"] in roster.keys()]
    if not steps:
        first = next(iter(roster.keys()))
        steps = [{"speaker": first, "instruction": msg}]
    return [[{**s, "to": "director"}] for s in steps]


# ── goal mode (loop a obiettivo, pattern Ralph) — v1.3 ──────────────────────
# Un giudice SEPARATO dalla stanza (non una testa: chi insegue l'obiettivo
# non è chi lo certifica) confronta il transcript col goal ad ogni giro.
# Stesso stile paranoico di parse_wave_plan/route_plan: output non valido ->
# None, MAI un verdetto inventato — un giudizio a caso è peggio di nessuno.

JUDGE_PROMPT = """You judge whether a creative room has met a goal. You do not
participate in the room; you only score its output so far against the goal.

GOAL (set by the Director): {goal}

TRANSCRIPT SO FAR:
{transcript}

Score 0-10, strict: 10 = the goal is concretely, fully met — not "promising
direction" or "good progress". If the goal names a specific non-negotiable
requirement (a hard constraint, not a preference) and it is unmet, cap the
score at 4 regardless of how good the rest is.

Output ONLY a JSON object, no prose, no markdown fence:
{{"score": <integer 0-10>, "met": <true or false>, "reason": "<one line: what's missing, or why it passes>"}}
"""


def parse_goal_verdict(raw: str):
    """Estrae {score, met, reason} dall'output del judge. Paranoico come
    parse_wave_plan: qualunque cosa non torni -> None."""
    m = re.search(r"\{.*\}", str(raw), re.DOTALL)
    if not m:
        return None
    try:
        data = json.loads(m.group(0))
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    score, met = data.get("score"), data.get("met")
    if (not isinstance(score, (int, float)) or isinstance(score, bool)
            or not isinstance(met, bool)):
        return None
    return {"score": max(0, min(10, int(score))), "met": met,
            "reason": str(data.get("reason", ""))[:300]}


def judge_goal(goal: str, transcript: str):
    """Verdetto del judge sul goal corrente. None = judge non disponibile
    questo giro (chiamata fallita o output illeggibile) — il chiamante NON
    deve interpretarlo come 'raggiunto': fail-closed, come il gate di
    ricerca."""
    try:
        raw = llm_claude_judge.call(JUDGE_PROMPT.format(
            goal=goal, transcript=transcript[-ROUTER_CONTEXT_CHARS:]))
    except Exception as e:
        log.warning("judge_goal fallito (%s)", e)
        return None
    return parse_goal_verdict(raw)


# ── collab mode (R6): trigger in linguaggio naturale ───────────────────────
AUTO_DEFAULT_CAP = 20      # l'hard-stop se il Director non dà un numero
# Bug hunt item 7a: anche un N esplicito ha un tetto — "per 500 giri" non
# deve far girare la stanza 500 volte senza controllo.
AUTO_MAX_ROUNDS = 50

_AUTO_RE = re.compile(
    r"\b(discutete(?:ne)?|parlate(?:ne)?|parlarne|confrontatevi)\b"
    r".{0,30}?\b(fra|tra)\s+(di\s+)?voi",
    re.IGNORECASE)
_GIRI_RE = re.compile(r"(\d+)\s*gir[oi]", re.IGNORECASE)
# Bug 7b: "non parlate fra di voi" / "senza parlare fra di voi" chiedono
# l'OPPOSTO della collab — non è un trigger. Il guard guarda solo i pochi
# caratteri SUBITO prima del verbo: una subordinata come "quando parlate
# fra di voi" non ha "non"/"senza" lì davanti e resta un trigger valido.
_NEGATION_RE = re.compile(r"\b(non|senza)\s*$", re.IGNORECASE)


def parse_auto_request(msg: str):
    """«discutete fra voi per 5 giri» -> 5 (tetto AUTO_MAX_ROUNDS); senza
    numero -> AUTO_DEFAULT_CAP; negato appena prima del verbo, o non è una
    richiesta di collab -> None."""
    m = _AUTO_RE.search(msg)
    if not m:
        return None
    if _NEGATION_RE.search(msg[:m.start()][-12:]):
        return None
    giri = _GIRI_RE.search(msg)
    if not giri:
        return AUTO_DEFAULT_CAP
    return min(int(giri.group(1)), AUTO_MAX_ROUNDS)


def requested_rounds(msg: str):
    """Il numero di giri richiesto testualmente, PRIMA del tetto
    AUTO_MAX_ROUNDS — usato dal front-end solo per segnalare quando
    `parse_auto_request` (o l'input diretto di `/auto N`) lo ha tagliato."""
    m = _GIRI_RE.search(msg)
    return int(m.group(1)) if m else None

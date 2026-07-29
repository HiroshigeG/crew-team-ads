"""
Crew Team Ads — the shared core.
================================
Everything both front-ends need: the cast (persona + model per head), the
routing brain, and the gated web search. The terminal room (`room.py`) and the
desktop app (`app.py`) both import from here, so a persona or a model is only
ever defined ONCE.

Nothing in this module prints or draws — the front-end owns all I/O.
"""

import json
import os
import re
import shutil
import subprocess

try:
    from dotenv import load_dotenv
    _here = os.path.dirname(os.path.abspath(__file__))
    load_dotenv(os.path.join(_here, ".env"))
    load_dotenv(os.path.join(_here, "..", ".env"))
except ImportError:
    pass

from crewai import LLM

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
CLAUDE_TIMEOUT = 240
_route_log = []          # ["subscription"|"api", …] — front-ends may show this


def last_claude_route() -> str:
    return _route_log[-1] if _route_log else "?"


class ClaudeLLM:
    """Drop-in for crewai.LLM: `.model` + `.call(prompt)`.

    Tries the subscription CLI first; falls back to the metered API.
    """

    def __init__(self, model: str):
        self.model = model
        self._api = LLM(model=f"anthropic/{model}")

    def _via_cli(self, prompt: str) -> str:
        env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}
        # No API key in the environment => the CLI cannot silently bill the API.
        env.pop("ANTHROPIC_API_KEY", None)
        r = subprocess.run(
            [CLAUDE_CLI, "-p", "--output-format", "text", "--model", self.model],
            input=prompt, capture_output=True, text=True,
            env=env, timeout=CLAUDE_TIMEOUT,
        )
        if r.returncode != 0:
            raise RuntimeError(f"claude CLI exited {r.returncode}: {r.stderr[:200]}")
        out = r.stdout.strip()
        if not out:
            raise RuntimeError("claude CLI returned nothing")
        return out

    def call(self, prompt: str) -> str:
        if CLAUDE_CLI:
            try:
                out = self._via_cli(prompt)
                _route_log.append("subscription")
                return out
            except Exception:
                pass          # fall through to the paid API
        out = str(self._api.call(prompt))
        _route_log.append("api")
        return out


# NB: Claude 5 models reject `temperature` — the API returns
# "`temperature` is deprecated for this model." Do not add it back.
llm_claude_voice = ClaudeLLM("claude-opus-5")
# The router only classifies who speaks next — a smaller model is plenty here.
llm_claude_router = ClaudeLLM("claude-sonnet-5")
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
            ROUTER_PROMPT.format(transcript=transcript[-6000:], msg=msg))
        m = re.search(r"\[.*\]", str(raw), re.DOTALL)
        plan = json.loads(m.group(0)) if m else []
        plan = [s for s in plan
                if isinstance(s, dict) and s.get("speaker") in CAST][:4]
        if plan:
            return plan
    except Exception:
        pass
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
VERIFIED_MODELS = [
    "anthropic/claude-opus-5",
    "anthropic/claude-sonnet-5",
    "gemini/gemini-3.1-pro-preview",
    "xai/grok-4.5",
]


def temp_for_level(level: int) -> float:
    """Slider 0-10 -> temperature 0.1-1.2 (per i modelli che la accettano)."""
    level = max(0, min(10, level))
    return round(0.1 + 0.11 * level, 2)


# Claude 5 rifiuta `temperature` (T1): per quei modelli la creatività si guida
# a parole. 3-5 è la fascia neutra: nessuna iniezione = comportamento di oggi.
_CREATIVITY_BLOCKS = (
    ((0, 2), "CREATIVE RISK SETTING (the Director turned the dial LOW): stay "
             "with proven territory, prefer the reliable angle, and flag "
             "anything you are not sure has worked before."),
    ((6, 8), "CREATIVE RISK SETTING (the Director turned the dial HIGH): push "
             "past the obvious. Propose at least one genuinely risky angle "
             "and say why it might fail."),
    ((9, 10), "CREATIVE RISK SETTING (the Director turned the dial to MAX): "
              "take real risks. No safe ideas, no hedging — the Director "
              "will pull you back if needed."),
)


def creativity_block(level: int) -> str:
    for (lo, hi), text in _CREATIVITY_BLOCKS:
        if lo <= level <= hi:
            return text
    return ""


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

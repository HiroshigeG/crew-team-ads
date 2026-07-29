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
        # No API key/token/endpoint override in the environment => la CLI
        # non deve poter fatturare né deviare endpoint (bug hunt, item 15).
        env.pop("ANTHROPIC_API_KEY", None)
        env.pop("ANTHROPIC_AUTH_TOKEN", None)
        env.pop("ANTHROPIC_BASE_URL", None)
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


def make_llm(head: Head):
    """L'LLM giusto per una testa. anthropic/* passa SEMPRE da ClaudeLLM
    (subscription-first, T4); temperature solo dove è accettata (T1)."""
    if head.model_id.startswith("anthropic/"):
        return ClaudeLLM(head.model_id.split("/", 1)[1])
    kwargs = {"model": head.model_id,
              "temperature": temp_for_level(head.creativity)}
    if head.model_id.startswith("xai/"):
        kwargs["additional_drop_params"] = ["stop"]   # T5
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
                    continue
                heads[key] = Head.from_dict({**d, "key": key})
            if not heads:
                raise ValueError("roster vuoto")
            return cls(heads)
        except Exception:
            # File rotto: da parte (mai cancellare lavoro altrui), poi default.
            try:
                shutil.copy(path, path + ".bad")
            except OSError:
                pass
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
    if block:
        parts.append(block)
    if private:
        parts.append(PRIVATE_PREAMBLE)
    parts.append(f"ROOM TRANSCRIPT (latest last):\n{context[-8000:]}")
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
    parts.append(f"ROOM TRANSCRIPT (latest last):\n{context[-8000:]}")
    parts.append(f"You had asked to search the web because: {why}\n{outcome}\n"
                 f"Now give your turn in full, as {head.name} "
                 f"(no SEARCH_REQUEST line this time):")
    return "\n\n".join(parts)


def head_speak(roster: Roster, key: str, context: str, instruction: str,
               private: bool = False) -> str:
    head = roster.heads[key]
    prompt = build_turn_prompt(head, context, instruction, private)
    return str(roster.llm(key).call(prompt)).strip()


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
            cast_lines=cast_lines, transcript=transcript[-6000:], msg=msg))
        waves = parse_wave_plan(raw, set(roster.keys()))
        if waves:
            return waves
    except Exception:
        pass
    # Fallback: il router v1 (o keyword/producer) in ondate da un passo l'una.
    steps = [s for s in route(transcript, msg) if s["speaker"] in roster.keys()]
    if not steps:
        first = next(iter(roster.keys()))
        steps = [{"speaker": first, "instruction": msg}]
    return [[{**s, "to": "director"}] for s in steps]


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

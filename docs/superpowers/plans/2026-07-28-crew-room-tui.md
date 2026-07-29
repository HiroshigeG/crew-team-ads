# Crew Room TUI — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Una TUI Textual per la writers' room multi-modello: turni paralleli a ondate, card live per testa, cross-talk visibile, roster editabile persistito, slider di creatività onesto, chat private 1:1 stagne, collab mode con hard-stop — senza regressioni su gate di ricerca e Claude subscription-first.

**Architecture:** `room_tui.py` nuovo (solo presentazione) + estensioni **additive** a `crew_cast.py` (Roster, router a ondate, RoomSession, creatività). `CAST` resta byte-identico nei valori; `app.py` e `room.py` continuano a importare e girare. Spec approvata: `docs/superpowers/specs/2026-07-28-crew-room-tui-design.md`.

**Tech Stack:** Python 3.12 (`.venv/bin/python3`), Textual 8.2.8, crewai 1.15.8 (`LLM`), litellm, ddgs, pytest + pytest-asyncio (dev).

## Global Constraints

- Python: **sempre** `.venv/bin/python3` / `.venv/bin/pytest` — mai `python3` di sistema (3.9.6, crewai non ci gira).
- Model ID esatti (T2): `anthropic/claude-opus-5`, `anthropic/claude-sonnet-5`, `gemini/gemini-3.1-pro-preview`, `xai/grok-4.5`.
- Claude 5 **rifiuta `temperature`** (T1): mai passarla a modelli `anthropic/*`; creatività via prompt.
- Grok: `additional_drop_params=["stop"]` (T5).
- Teste `anthropic/*` **sempre** via `core.ClaudeLLM` (subscription-first; scrub `CLAUDECODE` e `ANTHROPIC_API_KEY` già dentro `_via_cli` — T4). Mai reimplementare lo scrub.
- Chiamate LLM bloccanti: mai sull'event loop (T3) — sempre `asyncio.to_thread`.
- `CAST`, `route()`, `speak()`, `speak_after_search()`, `parse_search_request()`, `build_brief()`, `web_search()` esistenti: **non cambiarne firma né comportamento**. Solo aggiunte.
- Textual 8.2.8 **non ha** il widget `Slider` (verificato): creatività = barra renderizzata + pulsanti −/+.
- UI chrome in italiano; voci degli agenti in inglese. F2 Roster · F3 Creatività · F4 Collab · Esc contestuale · Ctrl+Q esce.
- Niente web app/server/Electron; `brainstorm_crew.py` non si tocca.
- Test offline con pytest; verifiche live con prompt micro («Reply with exactly: OK») solo nello smoke script e nella demo finale.
- Commit frequenti, messaggi in italiano come il repo, footer `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`.

## File Structure

| File | Ruolo |
|---|---|
| `crew_cast.py` (modifica, additiva) | `ROLE_PERSONAS`, `Head`, `Roster`, creatività, `build_turn_prompt`, `head_speak*`, `RoomSession`, `parse_wave_plan`, `route_plan`, `parse_auto_request` |
| `room_tui.py` (nuovo) | App Textual: layout, card, modali, comandi, ondate, collab, private |
| `tests/test_core_ext.py` (nuovo) | Unit test offline del core esteso |
| `tests/test_tui.py` (nuovo) | Pilot test Textual (offline, core monkeypatchato) |
| `scripts/smoke_live.py` (nuovo) | Micro-chiamate reali per modello + router (manuale) |
| `launcher.sh` (modifica) | Doppio click → Terminal.app con la TUI |
| `requirements.txt` (modifica) | + `textual`; nota dev su pytest |
| `README.md` (modifica) | Sezione: come si usa la TUI |
| `.gitignore` (modifica) | + `transcripts/`, `roster.json` |

---

### Task 1: Test infra + Head, creatività (helper puri)

**Files:**
- Modify: `crew_cast.py` (in coda al file: sezione «estensioni TUI»)
- Create: `tests/test_core_ext.py`
- Create: `tests/__init__.py` (vuoto)

**Interfaces:**
- Produces: `ROLE_PERSONAS: dict[str, str]`; `temp_for_level(level: int) -> float`; `creativity_block(level: int) -> str`; `@dataclass Head(key, name, avatar, color, model_id, persona, creativity=5)` con `mechanism_label() -> str`, `to_dict() -> dict`, `from_dict(d) -> Head`; `VERIFIED_MODELS: list[str]`.

- [ ] **Step 1: Installa pytest nel venv**

```bash
cd "~/Desktop/AI stuff/crew-team-ads"
.venv/bin/pip install pytest pytest-asyncio
.venv/bin/pytest --version
```

- [ ] **Step 2: Scrivi i test che falliscono** (`tests/test_core_ext.py`)

```python
"""Test offline del core esteso — nessuna chiamata API."""
import crew_cast as core


def test_role_personas_match_cast():
    # ROLE_PERSONAS è la fonte dei default: ricomposta con ROOM_RULES
    # deve dare ESATTAMENTE le personas di CAST (nessuna deriva).
    for key, c in core.CAST.items():
        assert core.ROOM_RULES + core.ROLE_PERSONAS[key] == c["persona"]


def test_temp_for_level_endpoints():
    assert core.temp_for_level(0) == 0.1
    assert core.temp_for_level(10) == 1.2
    assert core.temp_for_level(5) == 0.65
    # clamp fuori scala
    assert core.temp_for_level(-3) == 0.1
    assert core.temp_for_level(99) == 1.2


def test_creativity_block_bands():
    assert core.creativity_block(1)          # 0-2: presente
    assert core.creativity_block(4) == ""    # 3-5: neutro, nessuna iniezione
    assert core.creativity_block(7)          # 6-8: presente
    assert core.creativity_block(10)         # 9-10: presente
    assert core.creativity_block(7) != core.creativity_block(10)


def test_head_mechanism_label():
    h = core.Head(key="cd", name="CD", avatar="🎨", color="#ff8700",
                  model_id="anthropic/claude-opus-5", persona="x", creativity=8)
    assert h.mechanism_label() == "via prompt"
    g = core.Head(key="s", name="S", avatar="🧠", color="#5fafff",
                  model_id="gemini/gemini-3.1-pro-preview", persona="x",
                  creativity=6)
    assert g.mechanism_label() == "via temperature 0.76"


def test_head_dict_roundtrip():
    h = core.Head(key="cd", name="CD", avatar="🎨", color="#ff8700",
                  model_id="anthropic/claude-opus-5", persona="x", creativity=8)
    assert core.Head.from_dict(h.to_dict()) == h
```

- [ ] **Step 3: Verifica che falliscano**

Run: `.venv/bin/pytest tests/test_core_ext.py -v`
Expected: FAIL — `AttributeError: module 'crew_cast' has no attribute 'ROLE_PERSONAS'`

- [ ] **Step 4: Implementa in `crew_cast.py`**

Refactor minimo di `CAST`: estrai le stringhe di ruolo in `ROLE_PERSONAS` e usa
`ROOM_RULES + ROLE_PERSONAS[key]` nei quattro `persona` (valori identici byte
per byte). Poi, in coda al file:

```python
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
```

- [ ] **Step 5: Verifica che passino**

Run: `.venv/bin/pytest tests/test_core_ext.py -v`
Expected: 5 PASS

- [ ] **Step 6: Regressione front-end esistenti** (§5.3 del brief)

Run: `.venv/bin/python3 -c "import app, room; print('OK')"`
Expected: `OK` (l'import di room stampa nulla; nessun traceback)

- [ ] **Step 7: Commit**

```bash
git add crew_cast.py tests/
git commit -m "Core: Head, creatività onesta (T1) e ROLE_PERSONAS estratte da CAST"
```

---

### Task 2: Roster — load/save/edit, make_llm

**Files:**
- Modify: `crew_cast.py`
- Modify: `tests/test_core_ext.py` (append)
- Modify: `.gitignore` (+ `roster.json`, `transcripts/`)

**Interfaces:**
- Consumes: `Head`, `temp_for_level`, `ClaudeLLM`, `LLM`, `ROLE_PERSONAS`, `VERIFIED_MODELS`.
- Produces: `make_llm(head: Head)`; `ROSTER_PATH: str`; `class Roster` con `heads: dict[str, Head]` (ordinato), `Roster.default() -> Roster`, `Roster.load(path=None) -> Roster`, `save(path=None)`, `llm(key)` (cache, invalidata da update), `update_head(key, **fields)`, `add_head(head: Head)`, `remove_head(key)`, `keys()`.

- [ ] **Step 1: Test che falliscono** (append a `tests/test_core_ext.py`)

```python
def test_roster_default_matches_cast():
    r = core.Roster.default()
    assert list(r.keys()) == ["producer", "strategist", "cd", "social"]
    assert r.heads["cd"].model_id == "anthropic/claude-opus-5"
    assert r.heads["social"].model_id == "xai/grok-4.5"
    assert r.heads["cd"].persona == core.ROLE_PERSONAS["cd"]
    assert all(h.creativity == 5 for h in r.heads.values())


def test_roster_save_load_roundtrip(tmp_path):
    p = str(tmp_path / "roster.json")
    r = core.Roster.default()
    r.update_head("cd", creativity=9, name="Mad CD")
    r.save(p)
    r2 = core.Roster.load(p)
    assert r2.heads["cd"].creativity == 9
    assert r2.heads["cd"].name == "Mad CD"
    assert list(r2.keys()) == list(r.keys())


def test_roster_corrupt_file_backs_up_and_defaults(tmp_path):
    p = tmp_path / "roster.json"
    p.write_text("{not json", encoding="utf-8")
    r = core.Roster.load(str(p))
    assert list(r.keys()) == ["producer", "strategist", "cd", "social"]
    assert (tmp_path / "roster.json.bad").exists()   # mai perdere il file rotto


def test_roster_add_remove(tmp_path):
    p = str(tmp_path / "roster.json")
    r = core.Roster.default()
    r.add_head(core.Head(key="pm", name="PM", avatar="📋", color="#aaaaaa",
                         model_id="anthropic/claude-sonnet-5", persona=" You are the PM."))
    assert "pm" in r.keys()
    r.remove_head("pm")
    assert "pm" not in r.keys()
    # l'ultima testa non si rimuove: la stanza non può restare vuota
    for k in list(r.keys())[:-1]:
        r.remove_head(k)
    import pytest as _pytest
    with _pytest.raises(ValueError):
        r.remove_head(next(iter(r.keys())))
    r.save(p)  # save esplicito, non implicito nei metodi: lo fa il chiamante


def test_make_llm_families():
    claude = core.make_llm(core.Head(key="x", name="X", avatar="a", color="c",
                                     model_id="anthropic/claude-opus-5",
                                     persona="p", creativity=8))
    assert isinstance(claude, core.ClaudeLLM)      # subscription-first (R7)
    assert claude.model == "claude-opus-5"
    grok = core.make_llm(core.Head(key="y", name="Y", avatar="a", color="c",
                                   model_id="xai/grok-4.5", persona="p",
                                   creativity=10))
    assert grok.model == "xai/grok-4.5"
    assert grok.temperature == 1.2
    assert grok.additional_drop_params == ["stop"]  # T5
```

- [ ] **Step 2: Verifica che falliscano**

Run: `.venv/bin/pytest tests/test_core_ext.py -v -k "roster or make_llm"`
Expected: FAIL — `no attribute 'Roster'`

- [ ] **Step 3: Implementa** (append a `crew_cast.py`)

```python
ROSTER_PATH = os.path.join(_HERE, "roster.json")

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
            heads[key] = Head(
                key=key, name=c["name"], avatar=c["avatar"],
                color=_DEFAULT_HEAD_META[key][0],
                model_id=(f"anthropic/{c['llm'].model}"
                          if isinstance(c["llm"], ClaudeLLM) else c["llm"].model),
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
            heads = {d["key"]: Head.from_dict(d) for d in data["heads"]}
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
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"heads": [h.to_dict() for h in self.heads.values()]},
                      f, ensure_ascii=False, indent=2)

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
```

- [ ] **Step 4: Verifica che passino**

Run: `.venv/bin/pytest tests/test_core_ext.py -v`
Expected: tutti PASS

- [ ] **Step 5: Aggiorna `.gitignore`** — aggiungi le righe `roster.json` e `transcripts/` (config personale e sessioni: non si committano).

- [ ] **Step 6: Commit**

```bash
git add crew_cast.py tests/test_core_ext.py .gitignore
git commit -m "Core: Roster editabile e persistito (R4), make_llm per famiglia"
```

---

### Task 3: Prompt builder + head_speak (turni sul roster)

**Files:**
- Modify: `crew_cast.py`
- Modify: `tests/test_core_ext.py` (append)

**Interfaces:**
- Consumes: `Roster`, `Head`, `creativity_block`, `ROOM_RULES`.
- Produces: `PRIVATE_PREAMBLE: str`; `build_turn_prompt(head, context, instruction, private=False) -> str`; `build_after_search_prompt(head, context, why, query=None, results=None, private=False) -> str`; `head_speak(roster, key, context, instruction, private=False) -> str`; `head_speak_after_search(roster, key, context, why, query=None, results=None, private=False) -> str`.

- [ ] **Step 1: Test che falliscono** (append)

```python
def _mk_head(creativity=5):
    return core.Head(key="cd", name="Creative Director", avatar="🎨",
                     color="#ff8700", model_id="anthropic/claude-opus-5",
                     persona=core.ROLE_PERSONAS["cd"], creativity=creativity)


def test_build_turn_prompt_neutral_has_no_creativity_block():
    p = core.build_turn_prompt(_mk_head(5), "T", "go")
    assert "CREATIVE RISK SETTING" not in p
    assert core.ROOM_RULES in p and "Speak as Creative Director" in p


def test_build_turn_prompt_max_has_block_and_private_preamble():
    p = core.build_turn_prompt(_mk_head(10), "T", "go", private=True)
    assert "CREATIVE RISK SETTING" in p and "MAX" in p
    assert core.PRIVATE_PREAMBLE in p


def test_build_turn_prompt_truncates_context():
    p = core.build_turn_prompt(_mk_head(), "x" * 20000, "go")
    assert len(p) < 12000   # il transcript entra tagliato a 8000, come oggi


def test_head_speak_uses_roster_llm(monkeypatch):
    r = core.Roster.default()

    class FakeLLM:
        def call(self, prompt):
            assert "Speak as Creative Director" in prompt
            return "  ciao  "
    monkeypatch.setitem(r._llms, "cd", FakeLLM())
    assert core.head_speak(r, "cd", "T", "go") == "ciao"


def test_build_after_search_prompt_denied_vs_approved():
    d = core.build_after_search_prompt(_mk_head(), "T", "why")
    a = core.build_after_search_prompt(_mk_head(), "T", "why",
                                       query="q", results="r")
    assert "DENIED" in d and "APPROVED" in a and "RESULTS:" in a
```

- [ ] **Step 2: Verifica che falliscano**

Run: `.venv/bin/pytest tests/test_core_ext.py -v -k "prompt or head_speak"`
Expected: FAIL — `no attribute 'build_turn_prompt'`

- [ ] **Step 3: Implementa** (append a `crew_cast.py`)

```python
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
```

- [ ] **Step 4: Verifica che passino**

Run: `.venv/bin/pytest tests/test_core_ext.py -v`
Expected: tutti PASS

- [ ] **Step 5: Commit**

```bash
git add crew_cast.py tests/test_core_ext.py
git commit -m "Core: prompt builder puro e head_speak sul roster (creatività + privato)"
```

---

### Task 4: RoomSession — transcript di stanza e privati, su disco a ogni turno

**Files:**
- Modify: `crew_cast.py`
- Modify: `tests/test_core_ext.py` (append)

**Interfaces:**
- Consumes: niente di nuovo (solo stdlib).
- Produces: `class RoomSession(brief: str, base_dir: str = None, stamp: str = None)` con `.room_text: str`, `.room_path: str`, `room_context() -> str`, `private_context(key) -> str`, `append_room(label: str, text: str)`, `append_private(key: str, label: str, text: str)`, `private_path(key) -> str`.

- [ ] **Step 1: Test che falliscono** (append)

```python
def test_session_room_appends_and_persists(tmp_path):
    s = core.RoomSession("BRIEFTEXT", base_dir=str(tmp_path), stamp="test")
    s.append_room("Director", "ciao stanza")
    s.append_room("Creative Director", "risposta")
    assert "Director: ciao stanza" in s.room_text
    on_disk = open(s.room_path, encoding="utf-8").read()
    assert "risposta" in on_disk and "BRIEFTEXT" in on_disk


def test_session_private_is_watertight(tmp_path):
    # La garanzia dura della spec §7-bis: il privato non entra MAI nel
    # contesto di stanza; il contesto privato vede la stanza.
    s = core.RoomSession("B", base_dir=str(tmp_path), stamp="test")
    s.append_room("Director", "pubblico")
    s.append_private("cd", "Director", "segreto")
    assert "segreto" not in s.room_context()
    assert "segreto" not in s.room_text
    assert "pubblico" in s.private_context("cd")
    assert "segreto" in s.private_context("cd")
    assert "segreto" not in s.private_context("social")   # privati separati fra teste


def test_session_private_file_separate(tmp_path):
    s = core.RoomSession("B", base_dir=str(tmp_path), stamp="test")
    s.append_private("cd", "Director", "segreto")
    assert "segreto" in open(s.private_path("cd"), encoding="utf-8").read()
    assert "segreto" not in open(s.room_path, encoding="utf-8").read()
```

- [ ] **Step 2: Verifica che falliscano**

Run: `.venv/bin/pytest tests/test_core_ext.py -v -k session`
Expected: FAIL — `no attribute 'RoomSession'`

- [ ] **Step 3: Implementa** (append a `crew_cast.py`)

```python
class RoomSession:
    """Transcript di stanza + canali privati, scritti su disco A OGNI turno:
    un crash non perde la sessione. Il privato è stagno per costruzione — i
    contesti pubblici semplicemente non lo contengono (spec §7-bis)."""

    def __init__(self, brief: str, base_dir: str = None, stamp: str = None):
        from datetime import datetime
        self.brief = brief
        self.base_dir = base_dir or os.path.join(_HERE, "transcripts")
        os.makedirs(self.base_dir, exist_ok=True)
        self.stamp = stamp or datetime.now().strftime("%Y%m%d-%H%M")
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
```

- [ ] **Step 4: Verifica che passino**

Run: `.venv/bin/pytest tests/test_core_ext.py -v`
Expected: tutti PASS

- [ ] **Step 5: Commit**

```bash
git add crew_cast.py tests/test_core_ext.py
git commit -m "Core: RoomSession — transcript per turno su disco, privati stagni"
```

---

### Task 5: Router a ondate + trigger collab

**Files:**
- Modify: `crew_cast.py`
- Modify: `tests/test_core_ext.py` (append)

**Interfaces:**
- Consumes: `Roster`, `llm_claude_router`, `route()` (fallback), `ALIASES`.
- Produces: `parse_wave_plan(raw: str, valid_keys) -> list[list[dict]]` (puro); `route_plan(roster, transcript, msg) -> list[list[dict]]` — ogni step `{"speaker", "instruction", "to"}`, `to` ∈ keys ∪ {"director"}; `AUTO_DEFAULT_CAP = 20`; `parse_auto_request(msg: str) -> int | None`.

- [ ] **Step 1: Test che falliscono** (append)

```python
def test_parse_wave_plan_valid():
    raw = ('bla [[{"speaker":"strategist","instruction":"a","to":"director"},'
           '{"speaker":"social","instruction":"b","to":"director"}],'
           '[{"speaker":"cd","instruction":"c","to":"social"}]] bla')
    waves = core.parse_wave_plan(raw, {"strategist", "social", "cd"})
    assert len(waves) == 2 and len(waves[0]) == 2
    assert waves[1][0]["to"] == "social"


def test_parse_wave_plan_drops_unknown_and_defaults_to():
    raw = '[[{"speaker":"ghost","instruction":"x"},{"speaker":"cd","instruction":"y"}]]'
    waves = core.parse_wave_plan(raw, {"cd"})
    assert waves == [[{"speaker": "cd", "instruction": "y", "to": "director"}]]


def test_parse_wave_plan_garbage_is_empty():
    assert core.parse_wave_plan("no json here", {"cd"}) == []
    assert core.parse_wave_plan('[{"speaker":"cd"}]', {"cd"}) == []  # non a ondate


def test_route_plan_falls_back_to_sequential(monkeypatch):
    r = core.Roster.default()
    monkeypatch.setattr(core.llm_claude_router, "call",
                        lambda p: (_ for _ in ()).throw(RuntimeError("giù")))
    waves = core.route_plan(r, "T", "cd: dammi un'idea")
    # fallback = la catena di oggi (route -> keyword -> producer), seriale
    assert waves == [[{"speaker": "cd", "instruction": "cd: dammi un'idea",
                       "to": "director"}]]


def test_parse_auto_request():
    assert core.parse_auto_request("discutete fra voi per 5 giri") == 5
    assert core.parse_auto_request("parlatene fra di voi") == core.AUTO_DEFAULT_CAP
    assert core.parse_auto_request("confrontatevi tra voi per 3 giri") == 3
    assert core.parse_auto_request("cd: parlami del tema") is None
    assert core.parse_auto_request("bella idea, andiamo avanti") is None
```

- [ ] **Step 2: Verifica che falliscano**

Run: `.venv/bin/pytest tests/test_core_ext.py -v -k "wave or auto or route_plan"`
Expected: FAIL

- [ ] **Step 3: Implementa** (append a `crew_cast.py`)

```python
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

_AUTO_RE = re.compile(
    r"\b(discutete|parlatene|parlate|confrontatevi)\b.{0,30}?\b(fra|tra)\s+(di\s+)?voi",
    re.IGNORECASE)
_GIRI_RE = re.compile(r"(\d+)\s*gir[oi]", re.IGNORECASE)


def parse_auto_request(msg: str):
    """«discutete fra voi per 5 giri» -> 5; senza numero -> AUTO_DEFAULT_CAP;
    non è una richiesta di collab -> None."""
    if not _AUTO_RE.search(msg):
        return None
    m = _GIRI_RE.search(msg)
    return int(m.group(1)) if m else AUTO_DEFAULT_CAP
```

- [ ] **Step 4: Verifica che passino**

Run: `.venv/bin/pytest tests/test_core_ext.py -v`
Expected: tutti PASS

- [ ] **Step 5: Regressione completa core + front-end**

Run: `.venv/bin/pytest tests/ -v && .venv/bin/python3 -c "import app, room, crew_cast; print('OK')"`
Expected: tutti PASS + `OK`

- [ ] **Step 6: Commit**

```bash
git add crew_cast.py tests/test_core_ext.py
git commit -m "Core: router a ondate con destinatario (R1/R3) e trigger collab (R6)"
```

---

### Task 6: Smoke live — chiamate reali micro

**Files:**
- Create: `scripts/smoke_live.py`

**Interfaces:**
- Consumes: `Roster`, `head_speak`… no — chiamate dirette agli LLM del roster e a `route_plan`.
- Produces: script manuale; nessuna API nuova.

- [ ] **Step 1: Scrivi lo script**

```python
"""Smoke test LIVE — chiamate reali, prompt micro (costo ~zero).
Va lanciato a mano: .venv/bin/python3 scripts/smoke_live.py
Verifica: ogni modello del roster risponde; il router a ondate produce un
piano sensato; Claude passa dalla subscription (T4/R7)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import crew_cast as core

missing = core.missing_keys()
if missing:
    raise SystemExit(f"Chiavi mancanti: {missing}")

roster = core.Roster.default()

for key in roster.keys():
    head = roster.heads[key]
    out = str(roster.llm(key).call("Reply with exactly: OK")).strip()
    route = (f" [{core.last_claude_route()}]"
             if head.model_id.startswith("anthropic/") else "")
    print(f"{head.avatar} {head.name:28} {head.model_id:32} -> {out[:40]!r}{route}")

waves = core.route_plan(roster, "BRIEF: test.\n",
                        "strategist e social, un pensiero a testa sul tema; "
                        "poi il cd tira le fila")
print("\nroute_plan:")
for i, wave in enumerate(waves, 1):
    for s in wave:
        print(f"  ondata {i}: {s['speaker']:12} -> {s['to']:10} | {s['instruction'][:60]}")
```

- [ ] **Step 2: Eseguilo davvero** (§4 del brief: verify by running)

Run: `.venv/bin/python3 scripts/smoke_live.py`
Expected: 4 righe `-> 'OK'` (Claude con `[subscription]`); un piano con
strategist+social nella stessa ondata e cd in un'ondata successiva. Se un
modello fallisce, FERMARSI e capire (chiave? ID modello? rete?) prima di
proseguire.

- [ ] **Step 3: Commit**

```bash
git add scripts/smoke_live.py
git commit -m "Smoke live: micro-chiamate reali per modello + piano a ondate"
```

---

### Task 7: TUI skeleton — layout, card, intake

**Files:**
- Create: `room_tui.py`
- Create: `tests/test_tui.py`

**Interfaces:**
- Consumes: `core.Roster`, `core.RoomSession`, `core.build_brief`, `core.missing_keys`.
- Produces: `RoomApp(App)`; `HeadCard(Static)` con `head_key: str`, `set_status(icon_text: str)`, `refresh_meta()`; `FeedEntry` (Static con markup); `RoomApp.add_entry(feed_id: str, markup: str)`; costante `INTAKE` (le 4 domande, riusate da app.py nello spirito ma ridefinite qui in italiano TUI). Entry point: `python3 room_tui.py`.

- [ ] **Step 1: Scrivi `room_tui.py` (skeleton completo e avviabile)**

```python
"""
Crew Team Ads — la stanza in terminale (Textual).
=================================================
Solo presentazione: il cast, il router, il gate di ricerca e la sessione
vivono in crew_cast. Spec: docs/superpowers/specs/2026-07-28-crew-room-tui-design.md
Avvio:  .venv/bin/python3 room_tui.py   (o doppio click su CrewRoom.app)
"""
import asyncio

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import Footer, Input, Static

import crew_cast as core

# Le 4 domande del brief (stesse di app.py, formulate per il terminale).
INTAKE = [
    ("brand", "Chi è il brand? Nome e, in una riga, cosa vende e per chi.",
     "es. Adidas Running — scarpe da corsa performance, runner urbani 25-40"),
    ("theme", "Qual è il tema del lancio? Il territorio, non l'esecuzione.",
     "es. «Impossible is Nothing» — il superamento del limite personale"),
    ("mandate", "Qual è il mandato? Cosa deve fare il film, cosa non deve essere.",
     "es. il prodotto è l'eroe assoluto; premium ma non patinato"),
    ("medium", "Che formato consegniamo?",
     "es. short social verticale 9:16, alta craft cinematica"),
]

STATUS_IDLE = "· idle"


class HeadCard(Static):
    """La card live di una testa: stato, modello, creatività, destinatario."""

    def __init__(self, head: "core.Head"):
        super().__init__(classes="head-card")
        self.head_key = head.key
        self._status = STATUS_IDLE
        self._extra = ""          # es. "→ risponde a CD" o "💳 API"

    def on_mount(self):
        self.styles.border = ("round", self.app.roster.heads[self.head_key].color)
        self.refresh_meta()

    def set_status(self, status: str, extra: str = ""):
        self._status = status
        self._extra = extra
        self.refresh_meta()

    def refresh_meta(self):
        h = self.app.roster.heads[self.head_key]
        bar = "▰" * h.creativity + "▱" * (10 - h.creativity)
        lines = [
            f"[bold {h.color}]{h.avatar} {h.name}[/]",
            f"[dim]{h.model_id.split('/', 1)[1]}[/]",
            f"{self._status}",
            f"[dim]{bar} {h.creativity}/10 · {h.mechanism_label()}[/]",
        ]
        if self._extra:
            lines.append(self._extra)
        self.update("\n".join(lines))


class RoomApp(App):
    TITLE = "Crew Team Ads — Writers' Room"
    CSS = """
    #main { height: 1fr; }
    #feeds { width: 3fr; }
    .feed { height: 1fr; border: round $surface-lighten-2; padding: 0 1; }
    #rail { width: 1fr; min-width: 26; }
    .head-card { padding: 0 1; margin-bottom: 1; }
    #banner { display: none; background: $warning 20%; padding: 0 1; }
    #director-input { dock: bottom; }
    FeedEntry { margin-bottom: 1; }
    """
    BINDINGS = [
        Binding("f2", "roster", "Roster"),
        Binding("f3", "creativity", "Creatività"),
        Binding("f4", "collab", "Collab"),
        Binding("escape", "esc", "Interrompi/Torna", priority=True),
        Binding("ctrl+q", "quit", "Esci", priority=True),
    ]

    def __init__(self):
        super().__init__()
        self.roster = core.Roster.load()
        self.session = None            # nasce a fine intake
        self.mode = "room"             # "room" | "private:<key>"
        self._intake_answers = {}
        self._intake_i = 0

    def compose(self) -> ComposeResult:
        yield Static(id="banner")
        with Horizontal(id="main"):
            with Vertical(id="feeds"):
                yield VerticalScroll(id="feed-room", classes="feed")
            with VerticalScroll(id="rail"):
                for head in self.roster.heads.values():
                    yield HeadCard(head)
        yield Input(placeholder="🎬 Director >", id="director-input")
        yield Footer()

    # — feed helpers —
    def add_entry(self, feed_id: str, markup: str):
        feed = self.query_one(f"#{feed_id}", VerticalScroll)
        entry = Static(markup, classes="feed-entry")
        feed.mount(entry)
        feed.scroll_end(animate=False)

    def system_line(self, text: str, feed_id: str = "feed-room"):
        self.add_entry(feed_id, f"[dim]{text}[/]")

    # — avvio: chiavi, poi intake —
    def on_mount(self):
        missing = core.missing_keys()
        if missing:
            self.system_line(f"⚠ Mancano le chiavi API: {', '.join(missing)} "
                             f"(vanno nel file .env). Ctrl+Q per uscire.")
            self.query_one("#director-input", Input).disabled = True
            return
        self._ask_next_intake()
        self.query_one("#director-input", Input).focus()

    def _ask_next_intake(self):
        field, question, hint = INTAKE[self._intake_i]
        self.add_entry("feed-room",
                       f"[bold]🎬 {question}[/]\n[dim]{hint}[/]")

    def on_input_submitted(self, event: Input.Submitted):
        msg = event.value.strip()
        event.input.value = ""
        if not msg:
            return
        if self.session is None:
            self._handle_intake(msg)
            return
        self._handle_message(msg)

    def _handle_intake(self, msg: str):
        field = INTAKE[self._intake_i][0]
        self._intake_answers[field] = msg
        self.add_entry("feed-room", f"[bold]🎬 Director:[/] {msg}")
        self._intake_i += 1
        if self._intake_i < len(INTAKE):
            self._ask_next_intake()
            return
        brief = core.build_brief(**self._intake_answers)
        self.session = core.RoomSession(brief)
        self.system_line("✅ Brief acquisito. La stanza è tua: parla a tutti, "
                         "o a qualcuno («cd: …», «cd, chiedi a social …»). "
                         "«discutete fra voi per N giri» o /auto N per la "
                         "collab mode; /privato cd per parlare a tu per tu. "
                         f"Transcript: {self.session.room_path}")

    def _handle_message(self, msg: str):
        # Il vero dispatch (comandi, router, ondate) arriva nei task successivi.
        self.add_entry("feed-room", f"[bold]🎬 Director:[/] {msg}")
        self.session.append_room("Director", msg)

    # — azioni (implementate nei task successivi) —
    def action_roster(self):
        pass

    def action_creativity(self):
        pass

    def action_collab(self):
        pass

    def action_esc(self):
        pass


def main():
    RoomApp().run()


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Pilot test** (`tests/test_tui.py`)

```python
"""Pilot test Textual — offline: niente chiamate API (si resta nell'intake
o si monkeypatcha il core)."""
import pytest

import crew_cast as core
from room_tui import RoomApp, HeadCard


@pytest.fixture
def isolated(tmp_path, monkeypatch):
    """Roster e transcript su percorsi temporanei; chiavi finte presenti."""
    monkeypatch.setattr(core, "ROSTER_PATH", str(tmp_path / "roster.json"))
    for k in core.REQUIRED_KEYS:
        monkeypatch.setenv(k, "fake-key-for-tests")
    return tmp_path


@pytest.mark.asyncio
async def test_boot_shows_cards_and_intake(isolated):
    app = RoomApp()
    async with app.run_test() as pilot:
        cards = app.query(HeadCard)
        assert {c.head_key for c in cards} == {"producer", "strategist",
                                               "cd", "social"}
        feed = app.query_one("#feed-room")
        assert feed.children            # la prima domanda dell'intake è a video


@pytest.mark.asyncio
async def test_intake_flow_builds_session(isolated, monkeypatch):
    monkeypatch.setattr(core.RoomSession, "__init__",
                        lambda self, brief, base_dir=None, stamp=None:
                        core.RoomSession.__init__.__wrapped__(self, brief)
                        if False else _fake_init(self, brief, isolated))
    app = RoomApp()
    async with app.run_test() as pilot:
        for answer in ["Brand X", "Tema Y", "Mandato Z", "9:16"]:
            app.query_one("#director-input").value = answer
            await pilot.press("enter")
        assert app.session is not None
        assert "Brand X" in app.session.brief


def _fake_init(self, brief, tmp):
    core.RoomSession.__dict__["__init__"](self, brief, base_dir=str(tmp),
                                          stamp="t")
```

Nota per l'implementatore: se il doppio monkeypatch di `__init__` risulta
fragile, semplifica — patcha `RoomApp` con un attributo di classe
`SESSION_KW = {}` usato in `_handle_intake`
(`core.RoomSession(brief, **self.SESSION_KW)`) e nel test imposta
`RoomApp.SESSION_KW = {"base_dir": str(tmp_path), "stamp": "t"}`. È la
soluzione preferita: zero magia.

- [ ] **Step 3: Esegui i test**

Run: `.venv/bin/pytest tests/test_tui.py -v`
Expected: 2 PASS (aggiusta con la nota sopra se serve)

- [ ] **Step 4: Avvio reale a occhio**

Run: `cd "~/Desktop/AI stuff/crew-team-ads" && .venv/bin/python3 room_tui.py`
Expected: layout completo (feed + 4 card + input + footer con F-keys), intake
partito. Ctrl+Q esce pulito. (Lancialo in un terminale vero, non in pipe.)

- [ ] **Step 5: Commit**

```bash
git add room_tui.py tests/test_tui.py
git commit -m "TUI: skeleton — layout transcript+card, intake, footer F-keys"
```

---

### Task 8: Motore dei turni — ondate parallele, stati, cross-talk, Esc

**Files:**
- Modify: `room_tui.py`
- Modify: `tests/test_tui.py` (append)

**Interfaces:**
- Consumes: `core.route_plan`, `core.head_speak`, `core.parse_search_request`, `core.last_claude_route`, `RoomSession`, `HeadCard.set_status`.
- Produces: `RoomApp._run_plan(msg)` (worker); `RoomApp._run_turn(step, private_key=None) -> None`; flag `self._cancel_pending: bool`; `self._gate_lock: asyncio.Lock` (usato dal Task 9); `RoomApp._entry_header(head, to) -> str`.

- [ ] **Step 1: Test che falliscono** (append a `tests/test_tui.py`)

```python
@pytest.mark.asyncio
async def test_plan_runs_waves_and_threads_crosstalk(isolated, monkeypatch):
    # route_plan e head_speak finti: il test verifica orchestrazione e UI,
    # non i modelli (quelli li copre scripts/smoke_live.py).
    calls = []

    def fake_plan(roster, transcript, msg):
        return [[{"speaker": "strategist", "instruction": "a", "to": "director"},
                 {"speaker": "social", "instruction": "b", "to": "director"}],
                [{"speaker": "cd", "instruction": "c", "to": "social"}]]

    def fake_speak(roster, key, context, instruction, private=False):
        calls.append(key)
        return f"reply-{key}"

    monkeypatch.setattr(core, "route_plan", fake_plan)
    monkeypatch.setattr(core, "head_speak", fake_speak)
    app = RoomApp()
    RoomApp.SESSION_KW = {"base_dir": str(isolated), "stamp": "t"}
    async with app.run_test() as pilot:
        for answer in ["B", "T", "M", "F"]:
            app.query_one("#director-input").value = answer
            await pilot.press("enter")
        app.query_one("#director-input").value = "dite la vostra"
        await pilot.press("enter")
        await pilot.pause()          # lascia girare il worker
        for _ in range(80):          # attesa attiva, max ~4s
            if "cd" in calls:
                break
            await pilot.pause(0.05)
        assert set(calls) == {"strategist", "social", "cd"}
        # cross-talk nel transcript: il cd risponde a social, e si vede (R3)
        texts = [str(w.renderable) for w in app.query(".feed-entry")]
        assert any("→" in t and "Social" in t and "reply-cd" in "".join(texts)
                   for t in texts)
        # tutto in stanza è anche in sessione (persistenza per turno)
        assert "reply-strategist" in app.session.room_text
```

- [ ] **Step 2: Verifica che fallisca** — `.venv/bin/pytest tests/test_tui.py -v -k waves` → FAIL (il messaggio oggi non instrada nulla).

- [ ] **Step 3: Implementa il motore in `room_tui.py`**

Sostituisci `_handle_message` e aggiungi il worker:

```python
    def _handle_message(self, msg: str):
        self.add_entry("feed-room", f"[bold]🎬 Director:[/] {msg}")
        self.session.append_room("Director", msg)
        self._cancel_pending = False
        self.run_worker(self._run_plan(msg), exclusive=False)

    async def _run_plan(self, msg: str):
        """Un giro di stanza: router, poi le ondate. Ondata = gather dei turni
        (R1: wall-clock ≈ la testa più lenta). Esc annulla le ondate non
        ancora partite; i turni in volo si completano (spec §7)."""
        plan = await asyncio.to_thread(
            core.route_plan, self.roster, self.session.room_context(), msg)
        names = " → ".join(
            " + ".join(self.roster.heads[s["speaker"]].name for s in wave)
            for wave in plan)
        self.system_line(f"floor: {names}")
        for wave in plan:
            if self._cancel_pending:
                self.system_line("⏹ interrotto dal Director.")
                break
            await asyncio.gather(*(self._run_turn(step) for step in wave))
        self._check_billing()

    def _entry_header(self, head: "core.Head", to: str) -> str:
        if to == "director" or to not in self.roster.heads:
            return f"[bold {head.color}]{head.avatar} {head.name}:[/]"
        t = self.roster.heads[to]
        return (f"[bold {head.color}]{head.avatar} {head.name}[/] "
                f"[dim]→[/] [bold {t.color}]{t.avatar} {t.name}:[/]")

    async def _run_turn(self, step: dict, private_key: str = None):
        """Un turno di una testa: stato sulla card, chiamata bloccante fuori
        dall'event loop (T3), gate di ricerca (Task 9), transcript."""
        key = step["speaker"]
        head = self.roster.heads[key]
        card = self._card(key)
        to = step.get("to", "director")
        extra = (f"→ risponde a {self.roster.heads[to].name}"
                 if to in self.roster.heads else "")
        card.set_status("⚡ pensa…", extra)
        private = private_key is not None
        context = (self.session.private_context(key) if private
                   else self.session.room_context())
        try:
            reply = await asyncio.to_thread(
                core.head_speak, self.roster, key, context,
                step["instruction"], private)
        except Exception as e:
            card.set_status("⚠ errore")
            self.system_line(f"[{head.name} non disponibile: {e}]")
            return
        reply, query, why = core.parse_search_request(reply)
        if query:
            reply = await self._gate_and_answer(key, reply, query, why,
                                                private_key)
        card.set_status("✎ parla")
        feed_id = f"feed-priv-{private_key}" if private else "feed-room"
        self.add_entry(feed_id, f"{self._entry_header(head, to)}\n{reply}")
        if private:
            self.session.append_private(key, head.name, reply)
        else:
            label = (head.name if to == "director" or to not in self.roster.heads
                     else f"{head.name} (to {self.roster.heads[to].name})")
            self.session.append_room(label, reply)
        card.set_status(STATUS_IDLE)

    async def _gate_and_answer(self, key, said_before, query, why,
                               private_key=None):
        # Il vero modal arriva nel Task 9; intanto: nega sempre, onestamente.
        return await asyncio.to_thread(
            core.head_speak_after_search, self.roster, key,
            (self.session.private_context(key) if private_key
             else self.session.room_context()),
            why, None, None, private_key is not None)

    def _card(self, key: str) -> HeadCard:
        for card in self.query(HeadCard):
            if card.head_key == key:
                return card
        raise LookupError(key)

    def _check_billing(self):
        # Avviso una-tantum se Claude è caduto sull'API a pagamento (R7).
        if core.last_claude_route() != "api" or getattr(self, "_billed", False):
            return
        self._billed = True
        self.system_line("💳 L'abbonamento non ha risposto: Claude sta usando "
                         "i crediti API.")
        for card in self.query(HeadCard):
            h = self.roster.heads[card.head_key]
            if h.model_id.startswith("anthropic/"):
                card.set_status(STATUS_IDLE, "💳 API")
```

In `__init__` aggiungi: `self._cancel_pending = False`,
`self._gate_lock = asyncio.Lock()`, `RoomApp.SESSION_KW = {}` come attributo
di classe e usa `core.RoomSession(brief, **self.SESSION_KW)` in
`_handle_intake`. In `action_esc` (modalità stanza): `self._cancel_pending = True`.

- [ ] **Step 4: Test verdi** — `.venv/bin/pytest tests/test_tui.py -v` → PASS.

- [ ] **Step 5: Prova live a mano** (una volta, brief corto): avvia, brief
minimo, «strategist e social, un pensiero a testa; poi il cd tira le fila».
Expected: le due card in `⚡ pensa…` INSIEME (R1), poi il cd con
`→ risponde a …` se il router lo decide; transcript su disco aggiornato.

- [ ] **Step 6: Commit**

```bash
git add room_tui.py tests/test_tui.py
git commit -m "TUI: ondate parallele con stati live, cross-talk visibile, Esc (R1-R3)"
```

---

### Task 9: Gate di ricerca — modal con coda

**Files:**
- Modify: `room_tui.py`
- Modify: `tests/test_tui.py` (append)

**Interfaces:**
- Consumes: `core.web_search`, `core.head_speak_after_search`, `self._gate_lock`.
- Produces: `SearchGateModal(ModalScreen)` che si chiude con `("approve", query)` o `("deny", None)`; `_gate_and_answer` completo (sostituisce lo stub del Task 8).

- [ ] **Step 1: Test che falliscono** (append)

```python
@pytest.mark.asyncio
async def test_search_gate_modal_approve_and_deny(isolated, monkeypatch):
    def fake_plan(roster, transcript, msg):
        return [[{"speaker": "social", "instruction": "x", "to": "director"}]]

    def fake_speak(roster, key, context, instruction, private=False):
        return "premessa\nSEARCH_REQUEST: nike faceless hero || serve il precedente"

    after = {}

    def fake_after(roster, key, context, why, query=None, results=None,
                   private=False):
        after.update(query=query, results=results)
        return "risposta finale"

    monkeypatch.setattr(core, "route_plan", fake_plan)
    monkeypatch.setattr(core, "head_speak", fake_speak)
    monkeypatch.setattr(core, "head_speak_after_search", fake_after)
    monkeypatch.setattr(core, "web_search", lambda q: f"RISULTATI per {q}")

    app = RoomApp()
    RoomApp.SESSION_KW = {"base_dir": str(isolated), "stamp": "t"}
    async with app.run_test() as pilot:
        for answer in ["B", "T", "M", "F"]:
            app.query_one("#director-input").value = answer
            await pilot.press("enter")
        app.query_one("#director-input").value = "vai"
        await pilot.press("enter")
        for _ in range(80):
            if app.screen_stack and app.screen_stack[-1].__class__.__name__ == "SearchGateModal":
                break
            await pilot.pause(0.05)
        modal = app.screen_stack[-1]
        assert "nike faceless hero" in modal.query_one("#gate-query").renderable.__str__()
        await pilot.click("#gate-approve")
        for _ in range(80):
            if after.get("query"):
                break
            await pilot.pause(0.05)
        assert after["query"] == "nike faceless hero"
        assert "RISULTATI" in after["results"]
```

- [ ] **Step 2: FAIL atteso** — il modal non esiste ancora.

- [ ] **Step 3: Implementa**

```python
from textual.screen import ModalScreen
from textual.containers import Grid
from textual.widgets import Button, Label


class SearchGateModal(ModalScreen):
    """Il gate (R7): query E perché, verdetto del Director. Un modal alla
    volta (la coda la fa _gate_lock nel chiamante)."""

    CSS = """
    SearchGateModal { align: center middle; }
    #gate-box { width: 70; padding: 1 2; border: thick $warning;
                background: $surface; }
    #gate-buttons { height: auto; }
    #gate-rewrite { display: none; }
    """

    def __init__(self, head_name: str, query: str, why: str):
        super().__init__()
        self.head_name, self.query_text, self.why = head_name, query, why

    def compose(self) -> ComposeResult:
        with Vertical(id="gate-box"):
            yield Label(f"🔍 {self.head_name} chiede di cercare sul web")
            yield Label(f"query : {self.query_text}", id="gate-query")
            yield Label(f"perché: {self.why}", id="gate-why")
            with Horizontal(id="gate-buttons"):
                yield Button("✅ Approva", id="gate-approve", variant="success")
                yield Button("🚫 Nega", id="gate-deny", variant="error")
                yield Button("✏️ Riscrivi", id="gate-edit")
            yield Input(placeholder="query riscritta + Invio", id="gate-rewrite")

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "gate-approve":
            self.dismiss(("approve", self.query_text))
        elif event.button.id == "gate-deny":
            self.dismiss(("deny", None))
        else:
            box = self.query_one("#gate-rewrite", Input)
            box.styles.display = "block"
            box.focus()

    def on_input_submitted(self, event: Input.Submitted):
        newq = event.value.strip()
        self.dismiss(("approve", newq or self.query_text))
```

E il vero `_gate_and_answer` in `RoomApp` (sostituisce lo stub):

```python
    async def _gate_and_answer(self, key, said_before, query, why,
                               private_key=None):
        head = self.roster.heads[key]
        card = self._card(key)
        feed_id = f"feed-priv-{private_key}" if private_key else "feed-room"
        if said_before:      # quel che ha detto prima di chiedere resta a video
            self.add_entry(feed_id,
                           f"{self._entry_header(head, 'director')}\n{said_before}")
        card.set_status("🔍 attende il permesso")
        async with self._gate_lock:          # un modal alla volta (spec §6)
            verdict, final_q = await self.push_screen_wait(
                SearchGateModal(head.name, query, why))
        context = (self.session.private_context(key) if private_key
                   else self.session.room_context())
        if verdict != "approve":
            self.system_line(f"🚫 ricerca negata a {head.name}: {query}", feed_id)
            return await asyncio.to_thread(
                core.head_speak_after_search, self.roster, key, context,
                why, None, None, private_key is not None)
        card.set_status("🔍 cerca…")
        self.system_line(f"🔍 {head.name} cerca: {final_q}", feed_id)
        results = await asyncio.to_thread(core.web_search, final_q)
        return await asyncio.to_thread(
            core.head_speak_after_search, self.roster, key, context,
            why, final_q, results, private_key is not None)
```

- [ ] **Step 4: Test verdi** — `.venv/bin/pytest tests/test_tui.py -v` → PASS.

- [ ] **Step 5: Commit**

```bash
git add room_tui.py tests/test_tui.py
git commit -m "TUI: gate di ricerca a modal con coda — approva/nega/riscrivi (R7)"
```

---

### Task 10: Chat private 1:1

**Files:**
- Modify: `room_tui.py`
- Modify: `tests/test_tui.py` (append)

**Interfaces:**
- Consumes: `RoomSession.private_context/append_private`, `core.ALIASES`, `_run_turn(step, private_key=...)`.
- Produces: `RoomApp.enter_private(key)`, `RoomApp.exit_private()`; feed per testa `#feed-priv-<key>` creati lazy; click su `HeadCard` → `enter_private`; comando `/privato <alias>`.

- [ ] **Step 1: Test che falliscono** (append)

```python
@pytest.mark.asyncio
async def test_private_chat_is_isolated(isolated, monkeypatch):
    monkeypatch.setattr(core, "head_speak",
                        lambda roster, key, context, instruction, private=False:
                        f"private-answer (saw-secret={'segreto' in context})")
    app = RoomApp()
    RoomApp.SESSION_KW = {"base_dir": str(isolated), "stamp": "t"}
    async with app.run_test() as pilot:
        for answer in ["B", "T", "M", "F"]:
            app.query_one("#director-input").value = answer
            await pilot.press("enter")
        app.query_one("#director-input").value = "/privato cd"
        await pilot.press("enter")
        assert app.mode == "private:cd"
        app.query_one("#director-input").value = "segreto"
        await pilot.press("enter")
        for _ in range(80):
            if "segreto" in app.session._private.get("cd", ""):
                break
            await pilot.pause(0.05)
        await pilot.pause()
        # il privato NON tocca la stanza (garanzia dura §7-bis)
        assert "segreto" not in app.session.room_text
        assert "segreto" not in app.session.room_context()
        # Esc torna in stanza
        await pilot.press("escape")
        assert app.mode == "room"
```

- [ ] **Step 2: FAIL atteso** — `/privato` oggi finisce nel router.

- [ ] **Step 3: Implementa**

In `_handle_message`, PRIMA del router:

```python
        low = msg.lower()
        if low.startswith("/privato"):
            alias = low.replace("/privato", "", 1).strip()
            key = core.ALIASES.get(alias, alias)
            if key in self.roster.heads:
                self.enter_private(key)
            else:
                self.system_line(f"testa sconosciuta: «{alias}» — "
                                 f"prova: {', '.join(self.roster.keys())}")
            return
        if self.mode.startswith("private:"):
            self._handle_private_message(msg)
            return
```

E i metodi:

```python
    def enter_private(self, key: str):
        """La colonna transcript diventa la chat privata (spec §7-bis)."""
        head = self.roster.heads[key]
        self.mode = f"private:{key}"
        room = self.query_one("#feed-room")
        room.styles.display = "none"
        feed_id = f"feed-priv-{key}"
        if not self.query(f"#{feed_id}"):
            feed = VerticalScroll(id=feed_id, classes="feed")
            self.query_one("#feeds").mount(feed)
            self.add_entry(feed_id, "[dim](la stanza non vede questa chat)[/]")
        else:
            self.query_one(f"#{feed_id}").styles.display = "block"
        banner = self.query_one("#banner", Static)
        banner.update(f"🔒 PRIVATO — {head.avatar} {head.name}   "
                      f"[dim]Esc = torna in stanza[/]")
        banner.styles.display = "block"
        self.query_one("#director-input", Input).placeholder = "🔒 >"

    def exit_private(self):
        for feed in self.query(".feed"):
            feed.styles.display = "none"
        self.query_one("#feed-room").styles.display = "block"
        self.query_one("#banner", Static).styles.display = "none"
        self.query_one("#director-input", Input).placeholder = "🎬 Director >"
        self.mode = "room"

    def _handle_private_message(self, msg: str):
        key = self.mode.split(":", 1)[1]
        feed_id = f"feed-priv-{key}"
        self.add_entry(feed_id, f"[bold]🎬 Tu:[/] {msg}")
        self.session.append_private(key, "Director", msg)
        step = {"speaker": key, "instruction": msg, "to": "director"}
        self.run_worker(self._run_turn(step, private_key=key), exclusive=False)
```

In `action_esc`, la versione contestuale completa:

```python
    def action_esc(self):
        if self.mode.startswith("private:"):
            self.exit_private()
        elif getattr(self, "_collab_running", False):
            self._collab_stop = True          # il giro in volo finisce (§7)
        else:
            self._cancel_pending = True
```

In `HeadCard` aggiungi `def on_click(self): self.app.enter_private(self.head_key)`
(con guard: solo se `self.app.session` esiste).

- [ ] **Step 4: Test verdi** — `.venv/bin/pytest tests/test_tui.py -v` → PASS.

- [ ] **Step 5: Commit**

```bash
git add room_tui.py tests/test_tui.py
git commit -m "TUI: chat private 1:1 stagne — click card o /privato, Esc torna (§7-bis)"
```

---

### Task 11: Collab mode

**Files:**
- Modify: `room_tui.py`
- Modify: `tests/test_tui.py` (append)

**Interfaces:**
- Consumes: `core.parse_auto_request`, `core.AUTO_DEFAULT_CAP`, `core.route_plan`, `_run_turn`.
- Produces: `RoomApp._collab_loop(cap: int)` (worker); flag `_collab_running`, `_collab_stop`; comando `/auto [N]`; `action_collab` (F4 = avvia col cap di default / ferma se attivo).

- [ ] **Step 1: Test che falliscono** (append)

```python
@pytest.mark.asyncio
async def test_collab_runs_capped_and_esc_stops(isolated, monkeypatch):
    rounds = []

    def fake_plan(roster, transcript, msg):
        rounds.append(msg)
        return [[{"speaker": "cd", "instruction": "riprendi", "to": "strategist"}]]

    monkeypatch.setattr(core, "route_plan", fake_plan)
    monkeypatch.setattr(core, "head_speak",
                        lambda *a, **k: "botta e risposta")
    app = RoomApp()
    RoomApp.SESSION_KW = {"base_dir": str(isolated), "stamp": "t"}
    async with app.run_test() as pilot:
        for answer in ["B", "T", "M", "F"]:
            app.query_one("#director-input").value = answer
            await pilot.press("enter")
        app.query_one("#director-input").value = "/auto 3"
        await pilot.press("enter")
        for _ in range(120):
            if not getattr(app, "_collab_running", False) and rounds:
                break
            await pilot.pause(0.05)
        assert len(rounds) == 3                     # hard stop rispettato
        assert app.mode == "room"                   # la parola torna al Director
        banner = app.query_one("#banner")
        assert banner.styles.display.name.lower() == "none"


@pytest.mark.asyncio
async def test_natural_language_starts_collab(isolated, monkeypatch):
    started = []
    monkeypatch.setattr(core, "route_plan",
                        lambda r, t, m: started.append(m) or
                        [[{"speaker": "cd", "instruction": "x", "to": "director"}]])
    monkeypatch.setattr(core, "head_speak", lambda *a, **k: "ok")
    app = RoomApp()
    RoomApp.SESSION_KW = {"base_dir": str(isolated), "stamp": "t"}
    async with app.run_test() as pilot:
        for answer in ["B", "T", "M", "F"]:
            app.query_one("#director-input").value = answer
            await pilot.press("enter")
        app.query_one("#director-input").value = "discutete fra voi per 2 giri"
        await pilot.press("enter")
        for _ in range(120):
            if len(started) >= 2 and not app._collab_running:
                break
            await pilot.pause(0.05)
        assert len(started) == 2
```

- [ ] **Step 2: FAIL atteso.**

- [ ] **Step 3: Implementa**

In `_handle_message`, dopo il ramo `/privato` e prima del router:

```python
        if low.startswith("/auto"):
            arg = low.replace("/auto", "", 1).strip()
            cap = int(arg) if arg.isdigit() else core.AUTO_DEFAULT_CAP
            self._start_collab(cap)
            return
        auto_n = core.parse_auto_request(msg)
        if auto_n:
            self.add_entry("feed-room", f"[bold]🎬 Director:[/] {msg}")
            self.session.append_room("Director", msg)
            self._start_collab(auto_n)
            return
```

E i metodi:

```python
    def _start_collab(self, cap: int):
        if getattr(self, "_collab_running", False):
            self.system_line("collab già in corso — Esc per fermarla.")
            return
        self._collab_running, self._collab_stop = True, False
        self.run_worker(self._collab_loop(cap), exclusive=False)

    async def _collab_loop(self, cap: int):
        """R6: le teste si parlano da sole. Contatore visibile, Esc ferma,
        hard-stop a `cap` giri. Il gate di ricerca resta attivo (i turni
        passano da _run_turn, quindi dal modal)."""
        banner = self.query_one("#banner", Static)
        banner.styles.display = "block"
        last_speaker = "il Director"
        for k in range(1, cap + 1):
            if self._collab_stop:
                break
            banner.update(f"⚙ AUTO — giro {k}/{cap} — Esc per interrompere")
            prompt = (f"AUTO MODE round {k}: continue the discussion among "
                      f"yourselves. React to what {last_speaker} just said — "
                      f"agree, attack or build. Do not address the Director.")
            plan = await asyncio.to_thread(
                core.route_plan, self.roster,
                self.session.room_context(), prompt)
            for wave in plan:
                if self._collab_stop:
                    break
                await asyncio.gather(*(self._run_turn(step) for step in wave))
                last_speaker = self.roster.heads[wave[-1]["speaker"]].name
        self._collab_running = False
        banner.styles.display = "none"
        self.system_line("⏹ collab chiusa: la parola torna al Director.")
        self._check_billing()

    def action_collab(self):
        if getattr(self, "_collab_running", False):
            self._collab_stop = True
        elif self.session:
            self._start_collab(core.AUTO_DEFAULT_CAP)
```

- [ ] **Step 4: Test verdi** — `.venv/bin/pytest tests/test_tui.py -v` → PASS.

- [ ] **Step 5: Commit**

```bash
git add room_tui.py tests/test_tui.py
git commit -m "TUI: collab mode — /auto e linguaggio naturale, contatore, Esc, hard-stop (R6)"
```

---

### Task 12: Roster screen (F2) + Creatività (F3)

**Files:**
- Modify: `room_tui.py`
- Modify: `tests/test_tui.py` (append)

**Interfaces:**
- Consumes: `Roster.update_head/add_head/remove_head/save`, `core.VERIFIED_MODELS`, `HeadCard.refresh_meta`.
- Produces: `RosterScreen(ModalScreen)` (lista + edit + aggiungi/rimuovi); `HeadEditScreen(ModalScreen)` (name/avatar/model/persona); `CreativityScreen(ModalScreen)` (barra + pulsanti −/+ per testa, badge live); `RoomApp._rebuild_rail()`.

- [ ] **Step 1: Test che falliscono** (append)

```python
@pytest.mark.asyncio
async def test_creativity_buttons_update_head_and_badge(isolated):
    app = RoomApp()
    RoomApp.SESSION_KW = {"base_dir": str(isolated), "stamp": "t"}
    async with app.run_test() as pilot:
        await pilot.press("f3")
        assert app.screen_stack[-1].__class__.__name__ == "CreativityScreen"
        before = app.roster.heads["cd"].creativity
        await pilot.click("#plus-cd")
        assert app.roster.heads["cd"].creativity == before + 1
        # persistito (R4: sopravvive alla riapertura)
        assert core.Roster.load().heads["cd"].creativity == before + 1


@pytest.mark.asyncio
async def test_roster_edit_persona_takes_effect(isolated):
    app = RoomApp()
    RoomApp.SESSION_KW = {"base_dir": str(isolated), "stamp": "t"}
    async with app.run_test() as pilot:
        await pilot.press("f2")
        assert app.screen_stack[-1].__class__.__name__ == "RosterScreen"
        await pilot.click("#edit-cd")
        edit = app.screen_stack[-1]
        edit.query_one("#edit-name").value = "Direttore Creativo"
        await pilot.click("#edit-save")
        assert app.roster.heads["cd"].name == "Direttore Creativo"
        assert core.Roster.load().heads["cd"].name == "Direttore Creativo"


@pytest.mark.asyncio
async def test_roster_add_and_remove_head(isolated):
    app = RoomApp()
    RoomApp.SESSION_KW = {"base_dir": str(isolated), "stamp": "t"}
    async with app.run_test() as pilot:
        await pilot.press("f2")
        await pilot.click("#roster-add")
        edit = app.screen_stack[-1]
        edit.query_one("#edit-name").value = "Media Planner"
        await pilot.click("#edit-save")
        new_keys = [k for k in app.roster.keys()
                    if k not in ("producer", "strategist", "cd", "social")]
        assert len(new_keys) == 1
        from room_tui import HeadCard as HC
        assert any(c.head_key == new_keys[0] for c in app.query(HC))
```

- [ ] **Step 2: FAIL atteso.**

- [ ] **Step 3: Implementa**

```python
from textual.widgets import Select, TextArea


class CreativityScreen(ModalScreen):
    """F3 — R5: lo slider che non mente. Barra + −/+ per testa; il badge
    dice il meccanismo (T1). Textual 8.x non ha uno Slider nativo."""

    CSS = """
    CreativityScreen { align: center middle; }
    #crea-box { width: 76; padding: 1 2; border: thick $accent;
                background: $surface; }
    .crea-row { height: 3; }
    .crea-label { width: 26; }
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="crea-box"):
            yield Label("Creatività per testa   [dim]Esc = chiudi[/]")
            for h in self.app.roster.heads.values():
                with Horizontal(classes="crea-row"):
                    yield Label(f"{h.avatar} {h.name}", classes="crea-label")
                    yield Button("−", id=f"minus-{h.key}")
                    yield Label(self._bar(h), id=f"bar-{h.key}")
                    yield Button("+", id=f"plus-{h.key}")

    @staticmethod
    def _bar(h) -> str:
        return (f"{'▰' * h.creativity}{'▱' * (10 - h.creativity)} "
                f"{h.creativity}/10 · {h.mechanism_label()}")

    def on_button_pressed(self, event: Button.Pressed):
        op, key = event.button.id.split("-", 1)
        h = self.app.roster.heads[key]
        level = max(0, min(10, h.creativity + (1 if op == "plus" else -1)))
        self.app.roster.update_head(key, creativity=level)
        self.app.roster.save()
        self.query_one(f"#bar-{key}", Label).update(self._bar(h))
        self.app._card(key).refresh_meta()

    def key_escape(self):
        self.dismiss()


class HeadEditScreen(ModalScreen):
    """Edit (o creazione) di una testa: nome, avatar, modello, persona."""

    CSS = """
    HeadEditScreen { align: center middle; }
    #edit-box { width: 90; height: 80%; padding: 1 2; border: thick $accent;
                background: $surface; }
    #edit-persona { height: 1fr; }
    """

    def __init__(self, head: "core.Head", is_new: bool):
        super().__init__()
        self.head, self.is_new = head, is_new

    def compose(self) -> ComposeResult:
        with Vertical(id="edit-box"):
            yield Label("Nuova testa" if self.is_new
                        else f"Modifica {self.head.name}")
            yield Input(self.head.name, placeholder="nome", id="edit-name")
            yield Input(self.head.avatar, placeholder="emoji", id="edit-avatar")
            yield Select(((m, m) for m in core.VERIFIED_MODELS),
                         value=self.head.model_id, id="edit-model")
            yield TextArea(self.head.persona, id="edit-persona")
            with Horizontal():
                yield Button("💾 Salva", id="edit-save", variant="success")
                yield Button("Annulla", id="edit-cancel")
                if not self.is_new:
                    yield Button("🗑 Rimuovi testa", id="edit-remove",
                                 variant="error")

    def on_button_pressed(self, event: Button.Pressed):
        app = self.app
        if event.button.id == "edit-cancel":
            self.dismiss()
            return
        if event.button.id == "edit-remove":
            try:
                app.roster.remove_head(self.head.key)
            except ValueError as e:
                app.system_line(f"⚠ {e}")
                self.dismiss()
                return
        else:
            self.head.name = self.query_one("#edit-name", Input).value.strip() or self.head.name
            self.head.avatar = self.query_one("#edit-avatar", Input).value.strip() or "🤖"
            model = self.query_one("#edit-model", Select).value
            if model in core.VERIFIED_MODELS:
                self.head.model_id = model
            self.head.persona = self.query_one("#edit-persona", TextArea).text
            if self.is_new:
                app.roster.add_head(self.head)
            else:
                app.roster.update_head(self.head.key, name=self.head.name,
                                       avatar=self.head.avatar,
                                       model_id=self.head.model_id,
                                       persona=self.head.persona)
        app.roster.save()
        app._rebuild_rail()
        self.dismiss()


class RosterScreen(ModalScreen):
    """F2 — R4: il cast è del Director, non del codice."""

    CSS = """
    RosterScreen { align: center middle; }
    #roster-box { width: 70; padding: 1 2; border: thick $accent;
                  background: $surface; }
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="roster-box"):
            yield Label("Roster   [dim]Esc = chiudi[/]")
            for h in self.app.roster.heads.values():
                yield Button(f"{h.avatar} {h.name} — {h.model_id}",
                             id=f"edit-{h.key}")
            yield Button("➕ Aggiungi testa", id="roster-add", variant="primary")

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "roster-add":
            import re as _re
            base = core.Head(key="", name="Nuova testa", avatar="🤖",
                             color="#c678dd",
                             model_id="anthropic/claude-sonnet-5",
                             persona=" You are a new specialist in the room.")
            self.dismiss()
            # key stabile e unica derivata dal nome al salvataggio
            base.key = f"head{len(self.app.roster.heads) + 1}"
            self.app.push_screen(HeadEditScreen(base, is_new=True))
        else:
            key = event.button.id.split("-", 1)[1]
            self.dismiss()
            self.app.push_screen(
                HeadEditScreen(self.app.roster.heads[key], is_new=False))

    def key_escape(self):
        self.dismiss()
```

In `RoomApp`:

```python
    def action_roster(self):
        self.push_screen(RosterScreen())

    def action_creativity(self):
        self.push_screen(CreativityScreen())

    def _rebuild_rail(self):
        """Il roster è cambiato: card ricostruite; effetto dal prossimo turno."""
        rail = self.query_one("#rail")
        rail.remove_children()
        for head in self.roster.heads.values():
            rail.mount(HeadCard(head))
```

- [ ] **Step 4: Test verdi** — `.venv/bin/pytest tests/test_tui.py -v` → PASS.
Se `Select` o `TextArea` hanno firme diverse in 8.2.8, correggi consultando
`.venv/lib/python3.12/site-packages/textual/widgets/` — non indovinare.

- [ ] **Step 5: Prova a mano** — F2: rinomina il CD, aggiungi una testa
(claude-sonnet-5), parla e verifica che il router la includa. F3: alza Social
a 10, guarda badge e barra. Riapri l'app: tutto com'era (roster.json).

- [ ] **Step 6: Commit**

```bash
git add room_tui.py tests/test_tui.py
git commit -m "TUI: roster editabile a runtime (F2) e creatività onesta (F3) — R4/R5"
```

---

### Task 13: Launcher, requirements, README, regressione finale

**Files:**
- Modify: `launcher.sh`
- Modify: `requirements.txt`
- Modify: `README.md`

**Interfaces:** nessuna nuova — chiusura.

- [ ] **Step 1: `requirements.txt`** — aggiungi dopo la riga `ddgs`:

```
# La TUI (room_tui.py).
textual>=8.0
# Dev/test: .venv/bin/pip install pytest pytest-asyncio
```

- [ ] **Step 2: `launcher.sh`** — sostituisci il corpo: il doppio click apre
Terminal.app con la TUI (un .app da Finder non ha terminale):

```bash
#!/bin/bash
# Crew Team Ads — launcher del doppio click (CrewRoom.app).
# La stanza ora è una TUI: serve un terminale vero, quindi apriamo
# Terminal.app via osascript. Percorsi assoluti: un .app dal Finder
# non eredita il PATH della shell.

PROJECT_DIR="~/Desktop/AI stuff/crew-team-ads"
OSA=/usr/bin/osascript

alert() { "$OSA" -e "display alert \"Crew Room\" message \"$1\"" >/dev/null 2>&1; }

cd "$PROJECT_DIR" || { alert "Cartella del progetto non trovata."; exit 1; }
[ -x ".venv/bin/python3" ] || { alert "Ambiente mancante. Nel terminale: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt"; exit 1; }
[ -f ".env" ] || { alert "Manca il file .env con le chiavi API."; exit 1; }

"$OSA" <<'APPLESCRIPT'
tell application "Terminal"
    activate
    do script "cd '~/Desktop/AI stuff/crew-team-ads' && .venv/bin/python3 room_tui.py"
end tell
APPLESCRIPT
```

- [ ] **Step 3: Verifica il launcher davvero** — `./launcher.sh` da un
terminale: si apre una finestra Terminal con la stanza. Poi doppio click su
`~/Desktop/CrewRoom.app`: idem. (Se CrewRoom.app punta a un percorso diverso
da `launcher.sh`, aprire il bundle e verificare cosa esegue.)

- [ ] **Step 4: `README.md`** — aggiungi la sezione (adatta il tono al README
esistente, in coda):

```markdown
## La stanza in terminale (room_tui.py)

Avvio: doppio click su `CrewRoom.app`, oppure
`.venv/bin/python3 room_tui.py`. (La vecchia app browser resta:
`.venv/bin/chainlit run app.py`.)

- **Brief**: 4 domande all'avvio, poi la stanza è tua. Parla a tutti o a
  qualcuno (`cd: …`, `cd, chiedi a social …`).
- **Ondate**: le teste indipendenti rispondono in parallelo; i consulti
  (X→Y→X) restano in sequenza, con la freccia `→` nel transcript.
- **F2 Roster**: rinomina, cambia persona/modello, aggiungi o togli teste.
  Persistito in `roster.json` — riapri e ritrovi la tua stanza.
- **F3 Creatività**: 0–10 per testa. Gemini/Grok: `temperature` reale;
  Claude 5 la rifiuta, quindi la manopola inietta istruzioni nel prompt —
  il badge dice sempre quale meccanismo è attivo.
- **F4 / «discutete fra voi per N giri» / `/auto N`**: collab mode — le
  teste discutono da sole, contatore a video, Esc ferma, tetto 20 giri.
- **Click su una card / `/privato cd`**: chat privata 1:1, stagna — la
  stanza non la vede e la testa non la ricorda nei turni pubblici.
- **🔍**: ogni ricerca web resta dietro il tuo permesso (query + perché).
- Transcript in `transcripts/`, salvato a ogni turno.
```

- [ ] **Step 5: Regressione completa**

```bash
.venv/bin/pytest tests/ -v
.venv/bin/python3 -c "import app, room, crew_cast, room_tui; print('OK')"
.venv/bin/python3 scripts/smoke_live.py
```
Expected: tutti PASS, `OK`, smoke live pulito.

- [ ] **Step 6: Demo finale (§5.2)** — sessione reale con brief reale, in cui
si dimostrano: R1 (due teste in parallelo), R2 (card live), R3 (freccia
cross-talk), R4 (aggiungi/edita una testa), R5 (slider + badge), R6 (collab
con Esc), R7 (un SEARCH_REQUEST gestito + Claude `[subscription]`), più una
chat privata. Annotare nel report finale cosa si è visto, con onestà.

- [ ] **Step 7: Commit**

```bash
git add launcher.sh requirements.txt README.md
git commit -m "Launcher alla TUI, requirements textual, README della stanza"
```

---

## Self-review (fatta in scrittura)

- **Copertura spec:** §1 file ✓ (T7-T13), §2 roster ✓ (T2, T12), §3 creatività ✓ (T1, T3, T12), §4 ondate ✓ (T5, T8), §5 UI ✓ (T7, T8), §6 gate ✓ (T9), §7 collab ✓ (T5, T11), §7-bis private ✓ (T4, T10), §8 errori ✓ (T2 backup, T8 card ⚠/💳), §9 test ✓ (ogni task + T6, T13), §10 launcher/README ✓ (T13).
- **Tipi coerenti:** `head_speak(roster, key, context, instruction, private)` uniforme nei task 3/8/10/11; `route_plan -> list[list[dict]]` con `to` ovunque; `SESSION_KW` introdotto in T8 e usato nei test T8-T12.
- **Nessun placeholder:** ogni step ha codice o comando concreto; l'unica
  libertà lasciata all'implementatore è annotata esplicitamente (T7 nota sul
  fixture, T12 nota su Select/TextArea) con l'istruzione di verificare i
  sorgenti installati, non di indovinare.

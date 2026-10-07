"""Il ponte web (Fase 3): FastAPI + WebSocket sul contratto di Fase 1.

Regola d'oro ereditata dal core: qui non si pensa, si orchestra. Il modulo
importa `crew_cast` e non reimplementa nulla — traduce le sue funzioni in
eventi del contratto (docs/EVENT-CONTRACT.md) e i messaggi del browser in
chiamate al core. Tutte le chiamate bloccanti (LLM, ricerca) passano da
`asyncio.to_thread`; le ondate di `route_plan()` girano con `asyncio.gather`,
quindi il wall-clock di un'ondata è ≈ la testa più lenta (D2: contesto
congelato a inizio ondata, merge nell'ordine degli step).

Avvio:  .venv/bin/uvicorn server.main:app --port 8000
"""
from __future__ import annotations

import asyncio
import base64
import itertools
import os
import re
import sys
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import crew_cast as core  # noqa: E402  (il percorso va prima dell'import)

REPO_ROOT = Path(__file__).resolve().parent.parent
ADV_ROSTER = str(REPO_ROOT / "roster.adv.json")
WEB_DIST = REPO_ROOT / "web" / "dist"

# @menzioni deterministiche (Fase 4): scavalcano il router, quindi
# funzionano anche quando il router è giù — è la via d'uscita promessa
# dal banner «instradamento ridotto». Alias comodi per il roster ADV,
# sopra gli ALIASES storici del core.
_MENTION_RE = re.compile(r"@([a-z][a-z0-9_]*)", re.IGNORECASE)
_ADV_ALIASES = {
    "researcher": "market_researcher",
    "strategist": "creative_strategist",
    "copy": "copywriter",
}


def mentioned_heads(text: str, roster: "core.Roster") -> list[str]:
    keys: list[str] = []
    for m in _MENTION_RE.finditer(text):
        token = m.group(1).lower()
        key = token if token in roster.heads else (
            _ADV_ALIASES.get(token) or core.ALIASES.get(token))
        if key and key in roster.heads and key not in keys:
            keys.append(key)
    return keys


# ── collab libera / organica (D21) ──────────────────────────────────────────
# La stanza va avanti finché ha qualcosa da dire, non per un numero fisso di
# giri. Un turno "vuoto" è un [PASS]; quando la stanza tace per
# _DRY_ROUNDS_TO_STOP giri di fila, la corsa si chiude da sé. Il tetto duro
# (WEB_ORGANIC_CAP) resta come cintura di sicurezza contro i loop: due modelli
# lasciati soli convergono e si ripetono (degeneration-of-thought, Liang et
# al. — la stessa trappola citata in docs/recon/E-copy-pair.md), e ogni giro
# costa token.
_DRY_ROUNDS_TO_STOP = 2
_PASS_RE = re.compile(
    r"^\W*(\[?\s*pass\s*\]?|passo|niente da aggiungere|nulla da aggiungere|"
    r"nothing to add|no more to add)\W*$", re.IGNORECASE)
# Trigger in linguaggio naturale per la modalità libera (sopra il trigger
# collab del core): "…finché avete qualcosa da dire", "liberamente", "a
# oltranza", "senza limite".
_ORGANIC_RE = re.compile(
    r"finch[eé]|liberament|a\s+oltranza|senza\s+(limite|tetto|numero|fine)",
    re.IGNORECASE)


def _is_pass(text: str) -> bool:
    """Un turno è un PASS quando la testa dichiara di non avere altro da dire —
    e SOLO allora (match sull'intero messaggio, non su una parola in mezzo)."""
    return bool(_PASS_RE.match((text or "").strip()))


app = FastAPI(title="crew-team-ads · ponte web")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/status")
def status() -> dict:
    """La UI lo chiama PRIMA di aprire la stanza: se manca una chiave lo
    dice in chiaro invece di far fallire il primo turno."""
    roster = core.Roster.load(ADV_ROSTER)
    # Modelli open proposti nell'editor: solo quelli PROVATI dal vivo che
    # rispondono diretti (D14/D16). Esclusi i reasoning-model che tornavano
    # vuoti (Huihui-Qwen3.5-27B, MiniMax-M2.1). Un modello fuori lista resta
    # comunque ammesso se ha un prefisso noto (featherless_ai/, openrouter/,
    # ollama/) e digitato a mano.
    open_models = [
        "featherless_ai/huihui-ai/Qwen2.5-14B-Instruct-abliterated-v2",   # leggero, asciutto
        "featherless_ai/zetasepic/Qwen2.5-72B-Instruct-abliterated",      # 72B abliterated
        "featherless_ai/anthracite-org/magnum-v4-72b",                     # creativo forte
        # In stanza dal 07/10 (smoke test vivi): senza queste voci il select
        # dell'editor non mostra il modello delle teste che li usano.
        "featherless_ai/NousResearch/Hermes-3-Llama-3.1-70B",              # regia ordinata
        "featherless_ai/Qwen/Qwen2.5-72B-Instruct",                        # formale, affidabile
        "featherless_ai/EVA-UNIT-01/EVA-Qwen2.5-72B-v0.2",                 # storyteller (dark_angel)
        "openrouter/cognitivecomputations/dolphin-mistral-24b-venice-edition",  # creativo+uncensored
    ]
    return {
        "protocol": 1,
        "missing_keys": core.missing_keys(),
        "roster": [h.to_dict() for h in roster.heads.values()],
        "models": list(core.VERIFIED_MODELS) + open_models,
        "featherless_key": bool(os.getenv("FEATHERLESS_AI_API_KEY")),
    }


# ── onboarding chiavi (D25): il primo accesso le chiede e le scrive in .env ──
# Il repo non contiene MAI chiavi: chi clona apre la stanza, la UI vede le
# missing_keys e propone il modulo. Le chiavi finiscono solo nel .env locale
# (gitignorato) e in os.environ del processo. Whitelist chiusa: nomi noti,
# niente scrittura arbitraria di env. I valori non si loggano e non si
# rimandano mai indietro.
_KEY_WHITELIST = (
    "ANTHROPIC_API_KEY", "GEMINI_API_KEY", "XAI_API_KEY",
    "FEATHERLESS_AI_API_KEY", "OPENROUTER_API_KEY",
)


def _env_file() -> Path:
    return Path(os.getenv("CREW_ENV_FILE") or (REPO_ROOT / ".env"))


@app.post("/api/keys")
async def set_keys(payload: dict) -> dict:
    accepted: dict[str, str] = {}
    for name, value in (payload or {}).items():
        if name in _KEY_WHITELIST and isinstance(value, str) and value.strip():
            accepted[name] = value.strip()
    if not accepted:
        raise HTTPException(status_code=400, detail="nessuna chiave valida")
    path = _env_file()
    lines: list[str] = []
    if path.is_file():
        lines = path.read_text(encoding="utf-8").splitlines()
    for name, value in accepted.items():
        row = f"{name}={value}"
        for i, line in enumerate(lines):
            if line.strip().startswith(f"{name}="):
                lines[i] = row
                break
        else:
            lines.append(row)
        os.environ[name] = value          # il processo le vede subito
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text("\n".join(lines) + "\n", encoding="utf-8")
    tmp.chmod(0o600)
    os.replace(tmp, path)
    core.log.info("onboarding: salvate %d chiavi (%s)", len(accepted),
                  ", ".join(sorted(accepted)))   # nomi sì, valori mai
    return {"saved": sorted(accepted), "missing_keys": core.missing_keys()}


# ── storico sessioni (Fase 5.5): i transcript di RoomSession, in lettura ──
_STAMP_RE = re.compile(r"^[0-9]{8}-[0-9]{6}(?:-[0-9]+)?$")


def _transcripts_dir() -> Path:
    return Path(os.getenv("CREW_TRANSCRIPTS_DIR")
                or (REPO_ROOT / "transcripts"))


@app.get("/api/sessions")
def sessions_index() -> dict:
    base = _transcripts_dir()
    out = []
    if base.is_dir():
        for p in sorted(base.glob("room-*.md"),
                        key=lambda p: p.stat().st_mtime, reverse=True):
            stamp = p.stem.removeprefix("room-")
            if not _STAMP_RE.match(stamp):
                continue
            text = p.read_text(encoding="utf-8", errors="replace")
            first = next((l[len("Director: "):] for l in text.splitlines()
                          if l.startswith("Director: ")), "")
            out.append({"stamp": stamp, "file": p.name,
                        "chars": len(text), "excerpt": first[:140]})
    return {"sessions": out}


@app.get("/api/sessions/{stamp}")
def session_read(stamp: str) -> dict:
    # La guardia sul formato dello stamp È la difesa anti path-traversal.
    if not _STAMP_RE.match(stamp):
        raise HTTPException(status_code=400, detail="stamp non valido")
    p = _transcripts_dir() / f"room-{stamp}.md"
    if not p.is_file():
        raise HTTPException(status_code=404, detail="sessione non trovata")
    return {"stamp": stamp,
            "content": p.read_text(encoding="utf-8", errors="replace")}


# ── upload documenti (Fase 7): il Director carica, lo smistatore assegna ──
_MAX_UPLOAD = 8 * 1024 * 1024   # 8 MB: un brief o un deck, non un archivio
# Immagini in attesa di essere studiate (D15): tenute in RAM fra l'upload e
# lo `study_image`, cap piccolo — è una coda, non un archivio.
_IMAGE_CACHE: "dict[str, tuple[str, str]]" = {}   # id -> (base64, media_type)
_IMAGE_CACHE_MAX = 12


def extract_text(filename: str, raw: bytes) -> str:
    """Testo da un file caricato. PDF via pdfplumber; testo/markdown diretto.
    Immagini: non estraibili qui (serve un modello vision, vedi nota nel
    front-end) — si ritorna stringa vuota e il chiamante decide."""
    name = filename.lower()
    if name.endswith(".pdf"):
        import io
        import pdfplumber
        out = []
        with pdfplumber.open(io.BytesIO(raw)) as pdf:
            for page in pdf.pages:
                out.append(page.extract_text() or "")
        return "\n".join(out).strip()
    if name.endswith((".txt", ".md", ".markdown", ".csv")):
        return raw.decode("utf-8", "replace").strip()
    return ""


@app.post("/api/upload")
async def upload(file: UploadFile = File(...),
                 assign_to: str = Form("")) -> dict:
    """Estrae il testo di un documento. Non lo instrada da sé: ritorna il
    testo alla UI, che lo manda in stanza come messaggio del Director (così
    passa dal solito router / dalle @menzioni — un percorso solo, non due)."""
    raw = await file.read()
    if len(raw) > _MAX_UPLOAD:
        raise HTTPException(status_code=413, detail="file troppo grande (max 8 MB)")
    text = extract_text(file.filename or "documento", raw)
    is_image = (file.content_type or "").startswith("image/")
    if not text and not is_image:
        raise HTTPException(status_code=415,
                            detail="formato non leggibile (usa PDF, testo o markdown)")
    image_id = ""
    if is_image:
        if len(_IMAGE_CACHE) >= _IMAGE_CACHE_MAX:
            _IMAGE_CACHE.pop(next(iter(_IMAGE_CACHE)))   # sfratta la più vecchia
        image_id = uuid.uuid4().hex
        _IMAGE_CACHE[image_id] = (base64.b64encode(raw).decode(),
                                  file.content_type or "image/png")
    # Tetto per non intasare il contesto (troncato a 8000 dal core comunque).
    if len(text) > 12000:
        text = text[:12000] + "\n[…documento troncato…]"
    return {
        "filename": file.filename,
        "is_image": is_image,
        "image_id": image_id,
        "chars": len(text),
        "text": text,
        "assign_to": assign_to,
    }


class Room:
    """Una connessione WebSocket = una stanza (contratto §1)."""

    def __init__(self, ws: WebSocket):
        self.ws = ws
        self.roster = core.Roster.load(ADV_ROSTER)
        base_dir = os.getenv("CREW_TRANSCRIPTS_DIR") or None
        self.session = core.RoomSession("Sessione ADV (web)", base_dir=base_dir)
        self.out: asyncio.Queue[dict] = asyncio.Queue()
        self._seq = itertools.count(1)
        self._turn = itertools.count(1)
        self._plan = itertools.count(1)
        self._req = itertools.count(1)
        self.gates: dict[str, dict] = {}
        self.stop_flag = False
        self.work_lock = asyncio.Lock()
        # Panchina (D22): teste disattivate — non instradate né in collab, ma
        # ancora raggiungibili in privato. Il Director le fa entrare e uscire.
        self.disabled: set[str] = set()

    # ── eventi ──────────────────────────────────────────────────────────
    async def emit(self, type_: str, **payload) -> None:
        await self.out.put({
            "type": type_,
            "ts": datetime.now().astimezone().isoformat(timespec="seconds"),
            "seq": next(self._seq),
            **payload,
        })

    async def head_state(self, key: str, state: str, detail: str | None = None):
        await self.emit("head_state", speaker=key, state=state, detail=detail)

    async def saved(self, channel: str = "room") -> None:
        await self.emit(
            "session_saved",
            stamp=self.session.stamp,
            file=os.path.basename(self.session.room_path),
            channel=channel,
        )

    def route_of(self, key: str) -> str | None:
        """Rotta di fatturazione per-istanza (§7.3): ogni testa ha il suo
        ClaudeLLM in cache, quindi l'attribuzione è certa anche in parallelo."""
        llm = self.roster._llms.get(key)
        route = getattr(llm, "last_route", "?")
        return route if route in ("subscription", "api") else None

    # ── panchina: il roster che vede il router (D22) ─────────────────────
    def _routing_roster(self):
        """La vista del roster che il router riceve: solo le teste attive. Chi
        è in panchina non compare, quindi non viene instradato né entra in
        collab. Se (per assurdo) fossero tutte disattivate, si ripiega sul
        roster intero: meglio una stanza piena che nessuno che parli."""
        if not self.disabled:
            return self.roster
        active = {k: h for k, h in self.roster.heads.items()
                  if k not in self.disabled}
        if not active:
            return self.roster
        view = core.Roster(active)
        view._llms = self.roster._llms   # stessa cache: i turni girano sul reale
        return view

    # ── un turno ────────────────────────────────────────────────────────
    async def run_turn(self, step: dict, plan_id: str, wave_index: int,
                       frozen_ctx: str) -> dict | None:
        key = step["speaker"]
        if key not in self.roster.heads:
            return None
        turn_id = f"t-{next(self._turn):03d}"
        await self.emit("turn_started", turn_id=turn_id, plan_id=plan_id,
                        wave_index=wave_index, speaker=key, to=step["to"],
                        private=False, after_search=None)
        await self.head_state(key, "thinking")
        try:
            reply = await asyncio.to_thread(
                core.head_speak, self.roster, key, frozen_ctx,
                step["instruction"])
        except Exception as e:  # errore contenuto per testa (recon C §1.5)
            await self.head_state(key, "error", str(e)[:300])
            return None
        clean, query, why = core.parse_search_request(reply)
        kind = "search"
        if not query:      # una richiesta per turno: prima il web, poi il social (D23)
            clean, sq, swhy = core.parse_social_request(clean)
            if sq:
                query, why, kind = sq, swhy, "social"
        await self.head_state(key, "speaking")
        # §7.1: finché il core non fa streaming, UN solo turn_token col testo intero.
        await self.emit("turn_token", turn_id=turn_id, text=clean)
        await self.emit("turn_completed", turn_id=turn_id, speaker=key,
                        to=step["to"], text=clean, private=False)
        route = self.route_of(key)
        if route:
            await self.emit("turn_route", turn_id=turn_id, route=route)

        result = {"key": key, "text": clean, "turn_id": turn_id}
        if query:
            rid = f"r-{next(self._req):02d}"
            await self.emit("search_pending", request_id=rid, turn_id=turn_id,
                            speaker=key, query=query, why=why, kind=kind)
            detail = ("richiesta al tool social in attesa del Director"
                      if kind == "social"
                      else "richiesta di ricerca in attesa del Director")
            await self.head_state(key, "waiting_approval", detail)
            fut: asyncio.Future = asyncio.get_running_loop().create_future()
            self.gates[rid] = {"future": fut, "speaker": key,
                               "query": query, "why": why, "kind": kind}
            result["gate"] = rid
        else:
            await self.head_state(key, "idle")
        return result

    # ── il gate di ricerca (HITL, fail-closed) ──────────────────────────
    async def settle_gate(self, rid: str) -> None:
        g = self.gates[rid]
        verdict, new_query = await g["future"]
        key = g["speaker"]
        kind = g.get("kind", "search")
        turn_id = f"t-{next(self._turn):03d}"

        if verdict == "deny":
            await self.emit("search_result", request_id=rid, status="denied",
                            final_query=None, digest=None, kind=kind)
            query = results = None
        else:
            # rewrite con query vuota = approve con l'originale (recon C §1.2)
            query = (new_query or "").strip() or g["query"]
            await self.head_state(key, "searching", query)
            # Backend per tipo: web (DuckDuckGo) o tool social (D23).
            backend = core.social_intel if kind == "social" else core.web_search
            digest = await asyncio.to_thread(backend, query)
            # Sentinelle del core: '[no results]'/'[…returned nothing]' = vuoto;
            # le altre fra parentesi = fallita. Un digest JSON (che inizia con
            # '[') resta approvato: si controllano i prefissi noti, non "[".
            empty = digest.startswith(("[no results",
                                       "[social tool returned nothing"))
            failed = digest.startswith((
                "[search failed", "[social tool failed", "[social tool error",
                "[social tool timed out", "[social tool not configured"))
            if empty:
                status_, results = "empty", None
            elif failed:
                status_, results = "failed", None
            else:
                status_, results = "approved", digest
            await self.emit("search_result", request_id=rid, status=status_,
                            final_query=query, digest=results, kind=kind)

        await self.emit("turn_started", turn_id=turn_id, plan_id="",
                        wave_index=0, speaker=key, to="director",
                        private=False, after_search=rid)
        await self.head_state(key, "thinking")
        try:
            reply = await asyncio.to_thread(
                core.head_speak_after_search, self.roster, key,
                self.session.room_context(), g["why"],
                query if results else None, results)
        except Exception as e:
            await self.head_state(key, "error", str(e)[:300])
            del self.gates[rid]
            return
        clean, _, _ = core.parse_search_request(reply)
        await self.head_state(key, "speaking")
        await self.emit("turn_token", turn_id=turn_id, text=clean)
        await self.emit("turn_completed", turn_id=turn_id, speaker=key,
                        to="director", text=clean, private=False)
        route = self.route_of(key)
        if route:
            await self.emit("turn_route", turn_id=turn_id, route=route)
        await self.head_state(key, "idle")
        self.session.append_room(self.roster.heads[key].name, clean)
        await self.saved()
        del self.gates[rid]

    # ── un messaggio del Director, dall'inizio alla fine ────────────────
    async def handle_director(self, text: str) -> None:
        async with self.work_lock:      # i messaggi si processano in ordine
            self.stop_flag = False
            self.session.append_room("Director", text)
            await self.saved()

            goal = self._goal_mode(text)
            if goal:
                await self._run_goal(self.WEB_GOAL_CAP, goal)
                return

            spec = self._collab_mode(text)
            if spec:
                mode, cap = spec
                await self._run_collab(cap, organic=(mode == "organic"))
                return

            plan_id = f"p-{next(self._plan):02d}"
            # Anche una @menzione rispetta la panchina: chi è fuori, resta fuori
            # (per richiamarlo lo si riattiva). Se restano solo menzioni a teste
            # in panchina, si passa al router sulle attive.
            mentions = [k for k in mentioned_heads(text, self.roster)
                        if k not in self.disabled]
            if mentions:
                # @menzione = scelta esplicita del Director: niente router,
                # un'ondata parallela con le teste nominate.
                plan = [[{"speaker": k, "instruction": text, "to": "director"}
                         for k in mentions]]
            else:
                plan = await asyncio.to_thread(
                    core.route_plan, self._routing_roster(),
                    self.session.room_context(), text)
                if core.last_plan_route() == "fallback":
                    await self.emit("router_degraded", plan_id=plan_id,
                                    reason="il router a ondate non ha prodotto un piano valido")
            await self._run_plan(plan, plan_id, text)

    async def _run_plan(self, plan: list, plan_id: str,
                        fallback_instruction: str,
                        collector: list | None = None) -> str | None:
        """Esegue un piano a ondate; ritorna il nome dell'ultima testa che ha
        parlato (serve alla collab per il suo `last_speaker`). Se `collector`
        è passato, ci accumula (key, text) di ogni turno completato — la collab
        libera lo usa per capire quando la stanza ha esaurito (D21)."""
        # Trappola del fallback (recon A §2.9): instruction sempre stringa.
        for wave in plan:
            for s in wave:
                s["instruction"] = str(s.get("instruction") or fallback_instruction)
                s["to"] = s.get("to") or "director"
        await self.emit("wave_planned", plan_id=plan_id, waves=plan)

        last_name: str | None = None
        for wi, wave in enumerate(plan):
            if self.stop_flag:
                break
            frozen = self.session.room_context()   # D2: congelato
            results = await asyncio.gather(
                *(self.run_turn(s, plan_id, wi, frozen) for s in wave))
            # D2: merge nel transcript nell'ordine degli step dell'ondata.
            for res in results:
                if res:
                    name = self.roster.heads[res["key"]].name
                    self.session.append_room(name, res["text"])
                    last_name = name
                    if collector is not None:
                        collector.append((res["key"], res["text"]))
            await self.saved()
            # Fail-closed: l'ondata successiva parte solo dopo i verdetti.
            for res in results:
                if res and "gate" in res:
                    await self.settle_gate(res["gate"])
        return last_name

    # ── collab mode (Fase 5.2): le teste si parlano da sole ─────────────
    WEB_COLLAB_CAP = 20    # la specifica web chiede 20; il core arriverebbe a 50
    # Cintura di sicurezza della collab libera (D21): alto ma finito, così
    # "finché hanno qualcosa da dire" non diventa "finché finisce il credito".
    WEB_ORGANIC_CAP = int(os.getenv("CREW_ORGANIC_CAP") or 30)
    # Tetto del loop a obiettivo (D27, v1.3): ogni giro è un'ondata intera
    # (fino a 9 teste), quindi caro — più basso del cap organico per
    # costruzione, non per accidente. Lezione del pattern Ralph: MAI un
    # obiettivo senza tetto massimo, o un giudice rotto paga all'infinito.
    WEB_GOAL_CAP = int(os.getenv("CREW_GOAL_CAP") or 8)

    def _goal_mode(self, text: str):
        """`/goal <obiettivo>` avvia il loop a obiettivo. Controllato PRIMA
        di `_collab_mode` e tenuto separato apposta: non ne cambia la firma
        né il comportamento (additivo — stessa regola di casa di D1/D23/D25).
        Ritorna il testo dell'obiettivo, o None se non è un `/goal`."""
        stripped = text.strip()
        if not stripped.lower().startswith("/goal"):
            return None
        goal = stripped[len("/goal"):].strip()
        return goal or None

    def _collab_mode(self, text: str):
        """`(mode, cap)` con mode "fixed" (N giri) o "organic" (finché la stanza
        ha qualcosa da dire, fino al tetto di sicurezza), oppure None se non è
        collab. Trigger liberi: `/auto libero` o "…finché avete idee"."""
        low = text.strip().lower()
        if low.startswith("/auto"):
            rest = low[5:].strip()
            if rest in ("libero", "libera", "flow", "∞"):
                return ("organic", self.WEB_ORGANIC_CAP)
            n = int(rest) if rest.isdigit() else core.AUTO_DEFAULT_CAP
            return ("fixed", max(1, min(n, self.WEB_COLLAB_CAP)))
        n = core.parse_auto_request(text)
        if not n:            # None = non è collab; 0 giri = niente da girare
            return None
        if _ORGANIC_RE.search(text):
            return ("organic", self.WEB_ORGANIC_CAP)
        return ("fixed", min(n, self.WEB_COLLAB_CAP))

    async def _run_collab(self, cap: int, *, organic: bool = False) -> None:
        # Stesso prompt per giro della TUI (parità di semantica), contatore
        # visibile via collab_round, stop chiude a fine giro corrente, gate di
        # ricerca attivi (i turni passano da run_turn). In modalità libera ogni
        # testa può passare ([PASS]); quando la stanza tace per
        # _DRY_ROUNDS_TO_STOP giri di fila, la corsa si chiude da sé (D21).
        last_speaker = "the Director"
        dry = 0
        reason = "cap" if organic else "done"
        for k in range(1, cap + 1):
            if self.stop_flag:
                reason = "stopped"
                break
            # In libera il totale è aperto: total=0 + mode="organic" lo dice
            # alla UI, che mostra "giro k" senza denominatore.
            await self.emit("collab_round", round=k,
                            total=(0 if organic else cap),
                            mode=("organic" if organic else "fixed"))
            if organic:
                prompt = (
                    f"AUTO MODE (free) round {k}: continue the discussion among "
                    f"yourselves. React to what {last_speaker} just said — agree, "
                    "attack or build. Do not address the Director. If you "
                    "genuinely have nothing new to add, reply with exactly "
                    "[PASS] and nothing else.")
            else:
                prompt = (
                    f"AUTO MODE round {k}: continue the discussion among "
                    f"yourselves. React to what {last_speaker} just said — "
                    "agree, attack or build. Do not address the Director.")
            plan = await asyncio.to_thread(
                core.route_plan, self._routing_roster(),
                self.session.room_context(), prompt)
            plan_id = f"p-{next(self._plan):02d}"
            if core.last_plan_route() == "fallback":
                await self.emit("router_degraded", plan_id=plan_id,
                                reason="il router a ondate non ha prodotto un piano valido")
            collector: list | None = [] if organic else None
            spoke = await self._run_plan(plan, plan_id, prompt, collector)
            if spoke:
                last_speaker = spoke
            if organic:
                substantive = any(not _is_pass(t) for _, t in (collector or []))
                if not substantive:            # la stanza ha taciuto questo giro
                    dry += 1
                    if dry >= _DRY_ROUNDS_TO_STOP:
                        reason = "exhausted"
                        break
                else:
                    dry = 0
        await self.emit("collab_round", round=0, total=0, reason=reason)

    # ── goal mode (loop a obiettivo, pattern Ralph) — v1.3 ──────────────
    async def _run_goal(self, cap: int, goal: str) -> None:
        """Ondate come in collab, ma dopo ogni giro un giudice SEPARATO dalla
        stanza (`core.judge_goal`, non una testa: chi insegue l'obiettivo non
        è chi lo certifica) confronta il transcript col goal. Si ferma quando
        il judge dice `met`, quando il Director manda `stop`, o al tetto —
        mai altrimenti (lezione del loop engineering: niente obiettivo senza
        tetto). Un giro col judge indisponibile non conta come raggiunto
        (fail-closed, come il gate di ricerca) ma consuma comunque il tetto:
        un judge rotto non deve far girare la stanza all'infinito."""
        last_speaker = "the Director"
        reason = "cap"
        for k in range(1, cap + 1):
            if self.stop_flag:
                reason = "stopped"
                break
            await self.emit("collab_round", round=k, total=cap, mode="goal")
            prompt = (
                f"GOAL MODE round {k}: work toward this goal set by the "
                f"Director — \"{goal}\". React to what {last_speaker} just "
                "said; push the work closer to the goal. Do not address the "
                "Director.")
            plan = await asyncio.to_thread(
                core.route_plan, self._routing_roster(),
                self.session.room_context(), prompt)
            plan_id = f"p-{next(self._plan):02d}"
            if core.last_plan_route() == "fallback":
                await self.emit("router_degraded", plan_id=plan_id,
                                reason="il router a ondate non ha prodotto un piano valido")
            spoke = await self._run_plan(plan, plan_id, prompt)
            if spoke:
                last_speaker = spoke

            verdict = await asyncio.to_thread(
                core.judge_goal, goal, self.session.room_context())
            if verdict is None:
                await self.emit("goal_verdict", round=k, score=None,
                                met=False,
                                reason="giudice non disponibile questo giro")
                continue
            await self.emit("goal_verdict", round=k, score=verdict["score"],
                            met=verdict["met"], reason=verdict["reason"])
            if verdict["met"]:
                reason = "met"
                break
        await self.emit("collab_round", round=0, total=0, mode="goal",
                        reason=reason)

    # ── studio di un'immagine (D15): solo teste Gemini in v1.1 ──────────
    async def handle_image(self, image_id: str, note: str) -> None:
        async with self.work_lock:
            cached = _IMAGE_CACHE.pop(image_id, None)
            if not cached:
                await self.emit("router_degraded", plan_id="",
                                reason="immagine scaduta: ricaricala")
                return
            b64, media = cached
            key = core.vision_head(self.roster)
            if key is None:
                # Nessuna testa capace: lo si dice, non si finge (D15).
                await self.head_state("market_researcher", "error",
                                      "nessuna testa con visione nel roster "
                                      "(serve un modello Gemini)")
                return
            instruction = note or "Studia questa immagine per la campagna e dì cosa ne ricavi."
            self.session.append_room(
                "Director", f"[immagine caricata] {note}".strip())
            await self.saved()
            turn_id = f"t-{next(self._turn):03d}"
            await self.emit("turn_started", turn_id=turn_id, plan_id="",
                            wave_index=0, speaker=key, to="director",
                            private=False, after_search=None)
            await self.head_state(key, "thinking")
            try:
                reply = await asyncio.to_thread(
                    core.head_study_image, self.roster, key,
                    self.session.room_context(), instruction, b64, media)
            except Exception as e:
                await self.head_state(key, "error", str(e)[:300])
                return
            clean, _, _ = core.parse_search_request(reply)
            await self.head_state(key, "speaking")
            await self.emit("turn_token", turn_id=turn_id, text=clean)
            await self.emit("turn_completed", turn_id=turn_id, speaker=key,
                            to="director", text=clean, private=False)
            await self.head_state(key, "idle")
            self.session.append_room(self.roster.heads[key].name, clean)
            await self.saved()

    # ── chat privata 1:1 (Fase 5.1): stagna per costruzione ─────────────
    async def handle_private(self, key: str, text: str) -> None:
        head = self.roster.heads[key]
        self.session.append_private(key, "Director", text)
        await self.saved("private")
        turn_id = f"t-{next(self._turn):03d}"
        await self.emit("turn_started", turn_id=turn_id, plan_id="",
                        wave_index=0, speaker=key, to="director",
                        private=True, after_search=None)
        await self.head_state(key, "thinking")
        try:
            reply = await asyncio.to_thread(
                core.head_speak, self.roster, key,
                self.session.private_context(key), text, True)
        except Exception as e:
            await self.head_state(key, "error", str(e)[:300])
            return
        clean, query, _why = core.parse_search_request(reply)
        if query:
            core.log.info("gate disattivo nel privato (v1.1): richiesta di %s "
                          "scartata: %s", key, query)
        await self.head_state(key, "speaking")
        await self.emit("turn_token", turn_id=turn_id, text=clean)
        await self.emit("turn_completed", turn_id=turn_id, speaker=key,
                        to="director", text=clean, private=True)
        route = self.route_of(key)
        if route:
            await self.emit("turn_route", turn_id=turn_id, route=route)
        await self.head_state(key, "idle")
        self.session.append_private(key, head.name, clean)
        await self.saved("private")

    # ── messaggi browser → server ───────────────────────────────────────
    async def on_message(self, msg: dict) -> None:
        t = msg.get("type")
        if t == "director_message":
            text = str(msg.get("text", "")).strip()
            if text:
                asyncio.create_task(self.handle_director(text))
        elif t == "private_message":
            key = str(msg.get("head", ""))
            text = str(msg.get("text", "")).strip()
            if text and key in self.roster.heads:
                asyncio.create_task(self.handle_private(key, text))
        elif t == "study_image":
            image_id = str(msg.get("image_id", ""))
            note = str(msg.get("text", "")).strip()
            if image_id:
                asyncio.create_task(self.handle_image(image_id, note))
        elif t == "gate_verdict":
            g = self.gates.get(str(msg.get("request_id")))
            if g and not g["future"].done():
                verdict = msg.get("verdict")
                if verdict not in ("approve", "deny", "rewrite"):
                    verdict = "deny"               # default fail-closed
                g["future"].set_result((verdict, msg.get("query")))
        elif t == "stop":
            self.stop_flag = True
        elif t == "head_active":
            # Panchina (D22): attiva/disattiva una testa. Guardia gemella di
            # remove_head — la stanza non può restare senza teste attive.
            key = str(msg.get("key", ""))
            if key not in self.roster.heads:
                return
            if bool(msg.get("active", True)):
                self.disabled.discard(key)
            else:
                active_now = {k for k in self.roster.keys()
                              if k not in self.disabled}
                if len(active_now - {key}) >= 1:
                    self.disabled.add(key)
                else:
                    core.log.warning("head_active rifiutato: la stanza "
                                     "resterebbe senza teste attive")
        elif t == "creativity_set":
            key = str(msg.get("key", ""))
            if key in self.roster.heads:
                level = max(0, min(10, int(msg.get("level", 5))))
                self.roster.update_head(key, creativity=level)
        elif t == "roster_update":
            # Il core non valida la chiave (recon A §4.7): lo fa il server.
            key = str(msg.get("key", ""))
            action = msg.get("action")
            fields = msg.get("fields") or {}
            if not core._HEAD_KEY_RE.match(key):
                return
            if action == "update" and key in self.roster.heads:
                allowed = {k: v for k, v in fields.items()
                           if k in ("name", "avatar", "color", "model_id",
                                    "persona", "tagline", "creativity",
                                    "effort")}
                bad_model = ("model_id" in allowed
                             and not core.model_allowed(str(allowed["model_id"])))
                if bad_model:
                    core.log.warning("roster update: modello non ammesso "
                                     "(%s), campo ignorato", allowed.pop("model_id"))
                if allowed:
                    self.roster.update_head(key, **allowed)
            elif action == "add" and key not in self.roster.heads:
                model = str(fields.get("model_id") or "anthropic/claude-sonnet-5")
                if not core.model_allowed(model):
                    core.log.warning("roster add: modello non ammesso (%s)",
                                     model)
                    return
                name = str(fields.get("name") or key)
                self.roster.add_head(core.Head(
                    key=key, name=name,
                    avatar=str(fields.get("avatar") or "🤖"),
                    color=str(fields.get("color") or "#8899aa"),
                    model_id=model,
                    persona=str(fields.get("persona") or f" You are {name}."),
                    tagline=str(fields.get("tagline", "")),
                    creativity=max(0, min(10, int(fields.get("creativity", 5)))),
                    effort=str(fields.get("effort", "")),
                ))
            elif action == "remove" and key in self.roster.heads:
                try:
                    self.roster.remove_head(key)
                except ValueError:
                    core.log.warning("roster remove ignorata: la stanza non "
                                     "può restare vuota")


@app.websocket("/ws")
async def room_socket(ws: WebSocket) -> None:
    await ws.accept()
    room = Room(ws)

    async def writer() -> None:
        while True:
            await ws.send_json(await room.out.get())

    w = asyncio.create_task(writer())
    try:
        while True:
            msg = await ws.receive_json()
            await room.on_message(msg)
    except WebSocketDisconnect:
        pass
    finally:
        w.cancel()


# La build della UI, se esiste: un solo processo serve tutto (porta 8000).
if WEB_DIST.is_dir():
    app.mount("/", StaticFiles(directory=str(WEB_DIST), html=True), name="ui")

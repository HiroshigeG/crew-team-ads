"""Test offline del ponte web (server/main.py): core monkeypatchato,
nessuna chiamata LLM. Verifica che il server parli il contratto."""
import os

import crew_cast as core
from fastapi.testclient import TestClient

from server.main import app


def _drain_until(ws, wanted_type, limit=40):
    """Legge eventi finché non arriva `wanted_type`; ritorna tutti i letti."""
    seen = []
    for _ in range(limit):
        e = ws.receive_json()
        seen.append(e)
        if e["type"] == wanted_type:
            return seen
    raise AssertionError(f"mai visto {wanted_type}; visti: "
                         f"{[e['type'] for e in seen]}")


def test_turn_flow_speaks_the_contract(tmp_path, monkeypatch):
    monkeypatch.setenv("CREW_TRANSCRIPTS_DIR", str(tmp_path))
    monkeypatch.setattr(core, "route_plan", lambda r, t, m: [[
        {"speaker": "cd", "instruction": "a", "to": "director"},
        {"speaker": "producer", "instruction": "b", "to": "copywriter"},
    ]])
    monkeypatch.setattr(core, "last_plan_route", lambda: "waves")
    monkeypatch.setattr(
        core, "head_speak",
        lambda roster, key, ctx, instr, private=False: f"reply-{key}")

    with TestClient(app) as client, client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "director_message", "text": "brief di prova"})
        seen = _drain_until(ws, "session_saved")          # append del Director
        seen += _drain_until(ws, "wave_planned")
        plan = seen[-1]
        assert plan["waves"][0][1]["to"] == "copywriter"  # il `to` passa intatto

        # I due turni dell'ondata completano (in parallelo, ordine libero).
        completed, saved = [], seen
        while len(completed) < 2:
            e = ws.receive_json()
            saved.append(e)
            if e["type"] == "turn_completed":
                completed.append(e)
        assert {c["speaker"] for c in completed} == {"cd", "producer"}
        assert all(c["text"].startswith("reply-") for c in completed)

        _drain_until(ws, "session_saved")                 # merge dell'ondata

    # Il transcript su disco combacia con quello che è passato a schermo.
    files = list(tmp_path.glob("room-*.md"))
    assert len(files) == 1
    disk = files[0].read_text(encoding="utf-8")
    assert "Director: brief di prova" in disk
    assert "reply-cd" in disk and "reply-producer" in disk
    # D2: merge nell'ordine degli step (cd prima di producer).
    assert disk.index("reply-cd") < disk.index("reply-producer")
    # Ogni evento del flusso porta seq monotono.
    seqs = [e["seq"] for e in saved]
    assert seqs == sorted(seqs)


def test_search_gate_fail_closed_and_after_turn(tmp_path, monkeypatch):
    monkeypatch.setenv("CREW_TRANSCRIPTS_DIR", str(tmp_path))
    monkeypatch.setattr(core, "route_plan", lambda r, t, m: [[
        {"speaker": "market_researcher", "instruction": "verifica", "to": "director"},
    ]])
    monkeypatch.setattr(core, "last_plan_route", lambda: "waves")
    monkeypatch.setattr(
        core, "head_speak",
        lambda roster, key, ctx, instr, private=False:
            "Serve una verifica.\nSEARCH_REQUEST: quota mercato || non posso saperlo")
    monkeypatch.setattr(core, "web_search",
                        lambda q, n=5: "- fonte utile (esempio)")
    monkeypatch.setattr(
        core, "head_speak_after_search",
        lambda roster, key, ctx, why, query=None, results=None, private=False:
            f"verificato con: {query}")

    with TestClient(app) as client, client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "director_message", "text": "controlla il claim"})
        seen = _drain_until(ws, "search_pending")
        rid = seen[-1]["request_id"]
        assert seen[-1]["query"] == "quota mercato"
        # Subito dopo il pending, la testa passa in waiting_approval
        # (fail-closed: senza verdetto non si va avanti).
        nxt = ws.receive_json()
        assert nxt["type"] == "head_state"
        assert nxt["state"] == "waiting_approval"

        ws.send_json({"type": "gate_verdict", "request_id": rid,
                      "verdict": "rewrite", "query": "   "})   # vuota ⇒ originale
        seen = _drain_until(ws, "search_result")
        assert seen[-1]["status"] == "approved"
        assert seen[-1]["final_query"] == "quota mercato"      # riscritta vuota

        seen = _drain_until(ws, "turn_completed")
        after = [e for e in seen if e["type"] == "turn_started"][-1]
        assert after["after_search"] == rid                    # turni legati
        assert seen[-1]["text"] == "verificato con: quota mercato"
        _drain_until(ws, "session_saved")

    disk = next(tmp_path.glob("room-*.md")).read_text(encoding="utf-8")
    assert "verificato con: quota mercato" in disk
    # La riga SEARCH_REQUEST non entra mai nel transcript.
    assert "SEARCH_REQUEST" not in disk


def test_social_intel_gate_uses_social_backend(tmp_path, monkeypatch):
    """D23: una riga SOCIAL_INTEL passa dallo STESSO gate HITL ma chiama
    social_intel (non web_search); l'evento porta kind='social'."""
    monkeypatch.setenv("CREW_TRANSCRIPTS_DIR", str(tmp_path))
    monkeypatch.setattr(core, "route_plan", lambda r, t, m: [[
        {"speaker": "social", "instruction": "guarda tiktok", "to": "director"}]])
    monkeypatch.setattr(core, "last_plan_route", lambda: "waves")
    monkeypatch.setattr(
        core, "head_speak",
        lambda roster, key, ctx, instr, private=False:
            "Guardo il social.\nSOCIAL_INTEL: nike tiktok || servono numeri reali")

    called = {}

    def fake_social(q):
        called["q"] = q
        return "TIKTOK SIGNAL — pattern: curiosity open"

    def must_not_web(q, n=5):
        raise AssertionError("il gate social non deve chiamare web_search")

    monkeypatch.setattr(core, "social_intel", fake_social)
    monkeypatch.setattr(core, "web_search", must_not_web)
    monkeypatch.setattr(
        core, "head_speak_after_search",
        lambda roster, key, ctx, why, query=None, results=None, private=False:
            f"col segnale: {results[:20] if results else 'niente'}")

    with TestClient(app) as client, client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "director_message", "text": "che gira su tiktok?"})
        seen = _drain_until(ws, "search_pending")
        pend = seen[-1]
        assert pend["kind"] == "social"           # etichettato social
        assert pend["query"] == "nike tiktok"
        ws.send_json({"type": "gate_verdict", "request_id": pend["request_id"],
                      "verdict": "approve", "query": None})
        seen = _drain_until(ws, "search_result")
        assert seen[-1]["status"] == "approved"
        assert seen[-1]["kind"] == "social"
        _drain_until(ws, "turn_completed")

    assert called.get("q") == "nike tiktok"        # è passato dal backend social


def test_mentions_bypass_the_router(tmp_path, monkeypatch):
    """Fase 4: @menzione = scelta esplicita — il router NON viene chiamato,
    quindi le menzioni funzionano anche col router morto."""
    monkeypatch.setenv("CREW_TRANSCRIPTS_DIR", str(tmp_path))

    def router_must_not_run(*a, **k):
        raise AssertionError("con le @menzioni il router non si tocca")

    monkeypatch.setattr(core, "route_plan", router_must_not_run)
    monkeypatch.setattr(
        core, "head_speak",
        lambda roster, key, ctx, instr, private=False: f"reply-{key}")

    with TestClient(app) as client, client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "director_message",
                      "text": "@cd @copy prima reazione, e @researcher i numeri"})
        seen = _drain_until(ws, "wave_planned")
        wave = seen[-1]["waves"][0]
        # Un'ondata parallela con le teste nominate, in ordine di menzione;
        # gli alias comodi (@copy, @researcher) risolvono sulle chiavi vere.
        assert [s["speaker"] for s in wave] == [
            "cd", "copywriter", "market_researcher"]
        assert all(s["to"] == "director" for s in wave)
        # Nessun router_degraded: la degradazione non c'entra con le menzioni.
        assert not [e for e in seen if e["type"] == "router_degraded"]
        completed = []
        while len(completed) < 3:
            e = ws.receive_json()
            if e["type"] == "turn_completed":
                completed.append(e)
        assert {c["speaker"] for c in completed} == {
            "cd", "copywriter", "market_researcher"}


# ─────── Fase 5: privato stagno, collab col tetto web, roster runtime ───────

def test_private_chat_is_watertight(tmp_path, monkeypatch):
    monkeypatch.setenv("CREW_TRANSCRIPTS_DIR", str(tmp_path))
    seen_private = {}

    def fake_speak(roster, key, ctx, instr, private=False):
        seen_private["flag"] = private
        seen_private["ctx"] = ctx
        return "confidenza-per-il-director"

    monkeypatch.setattr(core, "head_speak", fake_speak)

    with TestClient(app) as client, client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "private_message", "head": "cd",
                      "text": "che ne pensi davvero?"})
        seen = _drain_until(ws, "turn_completed")
        done = seen[-1]
        assert done["private"] is True
        assert done["text"] == "confidenza-per-il-director"
        _drain_until(ws, "session_saved")

    assert seen_private["flag"] is True                  # private=True al core
    assert "PRIVATE SIDEBAR" in seen_private["ctx"]      # contesto privato vero
    room = next(tmp_path.glob("room-*.md")).read_text(encoding="utf-8")
    priv = next(tmp_path.glob("private-cd-*.md")).read_text(encoding="utf-8")
    # Stagno: il privato non tocca MAI la stanza.
    assert "confidenza-per-il-director" not in room
    assert "che ne pensi davvero?" not in room
    assert "confidenza-per-il-director" in priv


def test_collab_rounds_web_cap_and_counter(tmp_path, monkeypatch):
    from types import SimpleNamespace
    from server.main import Room

    stub = SimpleNamespace(WEB_COLLAB_CAP=Room.WEB_COLLAB_CAP,
                           WEB_ORGANIC_CAP=Room.WEB_ORGANIC_CAP)
    cap = Room.WEB_ORGANIC_CAP
    # /auto esplicito, trigger naturale e il tetto duro a 20 (il core
    # arriverebbe a 50: la specifica web vince, il core resta intatto).
    assert Room._collab_mode(stub, "/auto 3") == ("fixed", 3)
    assert Room._collab_mode(stub, "/auto 99") == ("fixed", 20)
    assert Room._collab_mode(stub, "discutete fra voi per 5 giri") == ("fixed", 5)
    assert Room._collab_mode(stub, "discutete fra voi per 500 giri") == ("fixed", 20)
    assert Room._collab_mode(stub, "cd: parlami del tema") is None
    # D21: modalità libera via /auto libero e via trigger naturale "finché…".
    assert Room._collab_mode(stub, "/auto libero") == ("organic", cap)
    assert Room._collab_mode(
        stub, "discutete fra voi finché avete qualcosa da dire") == ("organic", cap)

    monkeypatch.setenv("CREW_TRANSCRIPTS_DIR", str(tmp_path))
    monkeypatch.setattr(core, "route_plan", lambda r, t, m: [[
        {"speaker": "producer", "instruction": m, "to": "director"}]])
    monkeypatch.setattr(core, "last_plan_route", lambda: "waves")
    monkeypatch.setattr(
        core, "head_speak",
        lambda roster, key, ctx, instr, private=False: "giro fatto")

    with TestClient(app) as client, client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "director_message", "text": "/auto 2"})
        rounds = []
        for _ in range(80):
            e = ws.receive_json()
            if e["type"] == "collab_round":
                rounds.append((e["round"], e["total"]))
                if e["round"] == 0:
                    break
        assert rounds == [(1, 2), (2, 2), (0, 0)]   # contatore + fine corsa


def test_collab_organic_stops_when_room_runs_dry(tmp_path, monkeypatch):
    """D21: in modalità libera la stanza si chiude DA SÉ quando tace, ben
    prima del tetto di sicurezza — non per numero di giri prefissato."""
    monkeypatch.setenv("CREW_TRANSCRIPTS_DIR", str(tmp_path))
    monkeypatch.setattr(core, "route_plan", lambda r, t, m: [[
        {"speaker": "producer", "instruction": m, "to": "director"}]])
    monkeypatch.setattr(core, "last_plan_route", lambda: "waves")
    # Ogni testa passa: la stanza non ha nulla da aggiungere.
    monkeypatch.setattr(
        core, "head_speak",
        lambda roster, key, ctx, instr, private=False: "[PASS]")

    with TestClient(app) as client, client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "director_message", "text": "/auto libero"})
        rounds, close = [], None
        for _ in range(120):
            e = ws.receive_json()
            if e["type"] == "collab_round":
                if e["round"] == 0:
                    close = e
                    break
                rounds.append((e["round"], e.get("mode")))
        # Due giri a vuoto (_DRY_ROUNDS_TO_STOP), poi si ferma da sola.
        assert rounds == [(1, "organic"), (2, "organic")]
        assert close is not None and close["reason"] == "exhausted"


def test_goal_mode_parses_trigger_and_leaves_rest_alone():
    from server.main import Room
    assert Room._goal_mode(None, "/goal vendi il prodotto in 3 parole") == \
        "vendi il prodotto in 3 parole"
    assert Room._goal_mode(None, "/goal   ") is None            # niente obiettivo
    assert Room._goal_mode(None, "cd: dammi un'idea") is None   # non è un goal
    assert Room._goal_mode(None, "/auto 3") is None             # non pesta sull'altro trigger


def test_goal_run_stops_when_judge_says_met(tmp_path, monkeypatch):
    from server.main import Room
    monkeypatch.setenv("CREW_TRANSCRIPTS_DIR", str(tmp_path))
    monkeypatch.setattr(core, "route_plan", lambda r, t, m: [[
        {"speaker": "producer", "instruction": m, "to": "director"}]])
    monkeypatch.setattr(core, "last_plan_route", lambda: "waves")
    monkeypatch.setattr(
        core, "head_speak",
        lambda roster, key, ctx, instr, private=False: "bozza di concept")
    verdicts = iter([
        {"score": 4, "met": False, "reason": "manca l'headline"},
        {"score": 9, "met": True, "reason": "concept e headline chiudono il brief"},
    ])
    monkeypatch.setattr(core, "judge_goal",
                        lambda goal, transcript: next(verdicts))

    with TestClient(app) as client, client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "director_message",
                      "text": "/goal chiudi un concept con headline"})
        rounds, verdict_events, close = [], [], None
        for _ in range(120):
            e = ws.receive_json()
            if e["type"] == "collab_round":
                if e["round"] == 0:
                    close = e
                    break
                rounds.append((e["round"], e["total"], e["mode"]))
            elif e["type"] == "goal_verdict":
                verdict_events.append(e)
        assert rounds == [(1, Room.WEB_GOAL_CAP, "goal"), (2, Room.WEB_GOAL_CAP, "goal")]
        assert [v["met"] for v in verdict_events] == [False, True]
        assert close is not None and close["reason"] == "met"


def test_goal_run_stops_at_cap_when_never_met(tmp_path, monkeypatch):
    from server.main import Room
    monkeypatch.setattr(Room, "WEB_GOAL_CAP", 2)   # tetto piccolo per un test veloce
    monkeypatch.setenv("CREW_TRANSCRIPTS_DIR", str(tmp_path))
    monkeypatch.setattr(core, "route_plan", lambda r, t, m: [[
        {"speaker": "producer", "instruction": m, "to": "director"}]])
    monkeypatch.setattr(core, "last_plan_route", lambda: "waves")
    monkeypatch.setattr(
        core, "head_speak",
        lambda roster, key, ctx, instr, private=False: "bozza")
    monkeypatch.setattr(
        core, "judge_goal",
        lambda goal, transcript: {"score": 3, "met": False, "reason": "lontano"})

    with TestClient(app) as client, client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "director_message", "text": "/goal irraggiungibile"})
        close = None
        for _ in range(120):
            e = ws.receive_json()
            if e["type"] == "collab_round" and e["round"] == 0:
                close = e
                break
        assert close is not None and close["reason"] == "cap"


def test_goal_run_survives_judge_failure(tmp_path, monkeypatch):
    """Un giudice indisponibile non deve bloccare il giro né farlo contare
    come raggiunto (fail-closed) — ma consuma comunque il tetto."""
    from server.main import Room
    monkeypatch.setattr(Room, "WEB_GOAL_CAP", 1)
    monkeypatch.setenv("CREW_TRANSCRIPTS_DIR", str(tmp_path))
    monkeypatch.setattr(core, "route_plan", lambda r, t, m: [[
        {"speaker": "producer", "instruction": m, "to": "director"}]])
    monkeypatch.setattr(core, "last_plan_route", lambda: "waves")
    monkeypatch.setattr(
        core, "head_speak",
        lambda roster, key, ctx, instr, private=False: "bozza")
    monkeypatch.setattr(core, "judge_goal", lambda goal, transcript: None)

    with TestClient(app) as client, client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "director_message", "text": "/goal qualcosa"})
        seen = _drain_until(ws, "goal_verdict")
        v = seen[-1]
        assert v["score"] is None and v["met"] is False
        close = _drain_until(ws, "collab_round")[-1]
        assert close["round"] == 0 and close["reason"] == "cap"


def test_disabled_head_is_benched_from_routing(tmp_path, monkeypatch):
    """D22: una testa in panchina non arriva al router (né in collab). Il
    router vede solo le teste attive; il resto della stanza continua."""
    monkeypatch.setenv("CREW_TRANSCRIPTS_DIR", str(tmp_path))
    seen = {}

    def fake_route_plan(roster, transcript, msg):
        seen["keys"] = set(roster.keys())
        first = next(iter(roster.keys()))
        return [[{"speaker": first, "instruction": msg, "to": "director"}]]

    monkeypatch.setattr(core, "route_plan", fake_route_plan)
    monkeypatch.setattr(core, "last_plan_route", lambda: "waves")
    monkeypatch.setattr(
        core, "head_speak",
        lambda roster, key, ctx, instr, private=False: f"reply-{key}")

    with TestClient(app) as client, client.websocket_connect("/ws") as ws:
        # In panchina prima di parlare: i messaggi si processano in ordine.
        ws.send_json({"type": "head_active", "key": "producer", "active": False})
        ws.send_json({"type": "director_message", "text": "parlate del tema"})
        _drain_until(ws, "wave_planned")

    assert "producer" not in seen["keys"]      # benchata: fuori dal router
    assert "cd" in seen["keys"]                 # le altre restano in stanza


def test_room_cannot_be_fully_benched(tmp_path, monkeypatch):
    """D22: la stanza non può svuotarsi — l'ultima testa attiva resta."""
    import asyncio
    from server.main import Room

    monkeypatch.setenv("CREW_TRANSCRIPTS_DIR", str(tmp_path))

    class _WS:
        async def send_json(self, _):
            pass

    room = Room(_WS())
    keys = list(room.roster.keys())
    # disattiva tutte tranne una: ok
    for k in keys[:-1]:
        asyncio.run(room.on_message(
            {"type": "head_active", "key": k, "active": False}))
    # l'ultima disattivazione va rifiutata: la stanza resterebbe vuota
    asyncio.run(room.on_message(
        {"type": "head_active", "key": keys[-1], "active": False}))
    assert keys[-1] not in room.disabled
    assert len({k for k in room.roster.keys() if k not in room.disabled}) >= 1


def test_keys_onboarding_writes_env_and_filters(tmp_path, monkeypatch):
    """D25: /api/keys accetta solo la whitelist, scrive il .env indicato da
    CREW_ENV_FILE, aggiorna os.environ e non rimanda MAI i valori indietro."""
    envfile = tmp_path / "dotenv"
    envfile.write_text("GEMINI_API_KEY=vecchia\n# commento\n", encoding="utf-8")
    monkeypatch.setenv("CREW_ENV_FILE", str(envfile))
    monkeypatch.delenv("XAI_API_KEY", raising=False)

    with TestClient(app) as client:
        r = client.post("/api/keys", json={
            "XAI_API_KEY": "xai-test-123",
            "GEMINI_API_KEY": "nuova-456",
            "PATH": "/tmp/evil",              # fuori whitelist: ignorata
            "ANTHROPIC_API_KEY": "   ",       # vuota: ignorata
        })
    assert r.status_code == 200
    body = r.json()
    assert body["saved"] == ["GEMINI_API_KEY", "XAI_API_KEY"]
    assert "xai-test-123" not in r.text        # i valori non tornano indietro

    disk = envfile.read_text(encoding="utf-8")
    assert "XAI_API_KEY=xai-test-123" in disk
    assert "GEMINI_API_KEY=nuova-456" in disk   # aggiornata in place
    assert "vecchia" not in disk
    assert "# commento" in disk                 # il resto del file sopravvive
    assert "PATH=/tmp/evil" not in disk
    assert os.environ["XAI_API_KEY"] == "xai-test-123"

    with TestClient(app) as client:             # payload tutto invalido -> 400
        r = client.post("/api/keys", json={"PATH": "/tmp/evil"})
    assert r.status_code == 400


def test_roster_add_head_at_runtime(tmp_path, monkeypatch):
    monkeypatch.setenv("CREW_TRANSCRIPTS_DIR", str(tmp_path))
    monkeypatch.setattr(
        core, "head_speak",
        lambda roster, key, ctx, instr, private=False: f"reply-{key}")

    with TestClient(app) as client, client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "roster_update", "action": "add", "key": "guest",
                      "fields": {"name": "Guest Star", "avatar": "🌟",
                                 "model_id": "anthropic/claude-sonnet-5"}})
        # Effetto dal turno successivo, senza restart: la @menzione la trova.
        ws.send_json({"type": "director_message", "text": "@guest presentati"})
        seen = _drain_until(ws, "wave_planned")
        assert seen[-1]["waves"][0][0]["speaker"] == "guest"
        seen = _drain_until(ws, "turn_completed")
        assert seen[-1]["speaker"] == "guest"
        assert seen[-1]["text"] == "reply-guest"


def test_sessions_history_list_and_read(tmp_path, monkeypatch):
    monkeypatch.setenv("CREW_TRANSCRIPTS_DIR", str(tmp_path))
    (tmp_path / "room-20260803-101500.md").write_text(
        "BRIEF:\nx\n\nDirector: il brief della prima sessione\nCD: risposta\n",
        encoding="utf-8")
    (tmp_path / "room-20260803-120000.md").write_text(
        "BRIEF:\nx\n\nDirector: seconda sessione\n", encoding="utf-8")
    (tmp_path / "room-EVIL.md").write_text("no", encoding="utf-8")

    with TestClient(app) as client:
        idx = client.get("/api/sessions").json()["sessions"]
        stamps = [s["stamp"] for s in idx]
        assert "20260803-101500" in stamps and "20260803-120000" in stamps
        assert "EVIL" not in stamps                      # fuori formato: fuori
        one = [s for s in idx if s["stamp"] == "20260803-101500"][0]
        assert one["excerpt"].startswith("il brief della prima")

        read = client.get("/api/sessions/20260803-101500")
        assert read.status_code == 200
        assert "CD: risposta" in read.json()["content"]

        # Path traversal: lo stamp fuori formato muore sulla regex, 400.
        assert client.get("/api/sessions/..%2F..%2Fetc").status_code in (400, 404)
        assert client.get("/api/sessions/nope").status_code == 400
        assert client.get("/api/sessions/20260803-999999").status_code == 404


# ─────── Fase 6: il contratto sotto stress (nessuna funzione nuova) ─────────

def test_wave_runs_parallel_wallclock(tmp_path, monkeypatch):
    """Ondata da due teste lente: il wall-clock deve essere ≈ la più lenta,
    non la somma (asyncio.gather, spec Fase 3)."""
    import time as _time
    monkeypatch.setenv("CREW_TRANSCRIPTS_DIR", str(tmp_path))
    monkeypatch.setattr(core, "route_plan", lambda r, t, m: [[
        {"speaker": "cd", "instruction": "a", "to": "director"},
        {"speaker": "producer", "instruction": "b", "to": "director"},
    ]])
    monkeypatch.setattr(core, "last_plan_route", lambda: "waves")

    def slow_speak(roster, key, ctx, instr, private=False):
        _time.sleep(0.5)
        return f"reply-{key}"

    monkeypatch.setattr(core, "head_speak", slow_speak)

    with TestClient(app) as client, client.websocket_connect("/ws") as ws:
        t0 = _time.monotonic()
        ws.send_json({"type": "director_message", "text": "vai"})
        completed = 0
        while completed < 2:
            if ws.receive_json()["type"] == "turn_completed":
                completed += 1
        elapsed = _time.monotonic() - t0
    # Due turni da 0.5s in serie farebbero >1.0s; in parallelo ~0.5-0.7s.
    assert elapsed < 0.9, f"ondata NON parallela: {elapsed:.2f}s"


def test_gate_queue_settles_in_step_order(tmp_path, monkeypatch):
    """Due richieste di ricerca nella stessa ondata: si risolvono UNA alla
    volta nell'ordine degli step, qualunque sia l'ordine di arrivo."""
    import time as _time
    monkeypatch.setenv("CREW_TRANSCRIPTS_DIR", str(tmp_path))
    monkeypatch.setattr(core, "route_plan", lambda r, t, m: [[
        {"speaker": "cd", "instruction": "a", "to": "director"},
        {"speaker": "producer", "instruction": "b", "to": "director"},
    ]])
    monkeypatch.setattr(core, "last_plan_route", lambda: "waves")

    def speak(roster, key, ctx, instr, private=False):
        if key == "cd":
            _time.sleep(0.3)     # il producer chiede PRIMA, ma cd è lo step 1
        return f"x\nSEARCH_REQUEST: query di {key} || motivo di {key}"

    monkeypatch.setattr(core, "head_speak", speak)
    monkeypatch.setattr(core, "web_search", lambda q, n=5: f"- fonte per {q}")
    monkeypatch.setattr(
        core, "head_speak_after_search",
        lambda roster, key, ctx, why, query=None, results=None, private=False:
            f"chiuso-{key}")

    with TestClient(app) as client, client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "director_message", "text": "verificate entrambi"})
        pendings = {}
        while len(pendings) < 2:
            e = ws.receive_json()
            if e["type"] == "search_pending":
                pendings[e["speaker"]] = e["request_id"]
        # Verdetti per ENTRAMBI, subito: l'ordine di risoluzione deve
        # comunque seguire gli step (cd prima di producer).
        for rid in pendings.values():
            ws.send_json({"type": "gate_verdict", "request_id": rid,
                          "verdict": "approve", "query": None})
        results = []
        while len(results) < 2:
            e = ws.receive_json()
            if e["type"] == "search_result":
                results.append(e["request_id"])
        assert results == [pendings["cd"], pendings["producer"]]


def test_router_degraded_is_emitted(tmp_path, monkeypatch):
    monkeypatch.setenv("CREW_TRANSCRIPTS_DIR", str(tmp_path))
    monkeypatch.setattr(core, "route_plan", lambda r, t, m: [[
        {"speaker": "producer", "instruction": m, "to": "director"}]])
    monkeypatch.setattr(core, "last_plan_route", lambda: "fallback")
    monkeypatch.setattr(
        core, "head_speak",
        lambda roster, key, ctx, instr, private=False: "ok")

    with TestClient(app) as client, client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "director_message", "text": "senza menzioni"})
        seen = _drain_until(ws, "wave_planned")
        kinds = [e["type"] for e in seen]
        # Il degrado si annuncia PRIMA del piano: mai più fallback silenziosi.
        assert "router_degraded" in kinds
        assert kinds.index("router_degraded") < kinds.index("wave_planned")


def test_stop_mid_wave_lets_flight_finish_and_kills_queue(tmp_path, monkeypatch):
    """Stop con l'ondata 1 in volo: il turno in volo si completa, l'ondata 2
    non parte mai, la parola torna al Director."""
    import threading as _threading
    monkeypatch.setenv("CREW_TRANSCRIPTS_DIR", str(tmp_path))
    monkeypatch.setattr(core, "route_plan", lambda r, t, m: [
        [{"speaker": "cd", "instruction": "a", "to": "director"}],
        [{"speaker": "producer", "instruction": "b", "to": "director"}],
    ])
    monkeypatch.setattr(core, "last_plan_route", lambda: "waves")
    gate = _threading.Event()

    def gated_speak(roster, key, ctx, instr, private=False):
        gate.wait(timeout=10)     # resta in volo finché il test non libera
        return f"reply-{key}"

    monkeypatch.setattr(core, "head_speak", gated_speak)

    with TestClient(app) as client, client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "director_message", "text": "vai"})
        seen = _drain_until(ws, "turn_started")      # cd è in volo
        assert seen[-1]["speaker"] == "cd"
        ws.send_json({"type": "stop"})               # stop A METÀ ondata
        import time as _time
        _time.sleep(0.3)                             # lo stop viene processato
        gate.set()                                   # ora il turno può finire
        seen = _drain_until(ws, "session_saved")     # merge dell'ondata 1
        types = [e["type"] for e in seen]
        assert "turn_completed" in types             # il volo si è completato
        speakers = [e.get("speaker") for e in seen if e["type"] == "turn_started"]
        assert "producer" not in speakers            # l'ondata 2 non è partita

    disk = next(tmp_path.glob("room-*.md")).read_text(encoding="utf-8")
    assert "reply-cd" in disk and "reply-producer" not in disk


# ─────── Fase 7: upload documenti (lo smistatore decide chi studia) ─────────

def test_upload_extracts_text_from_txt(tmp_path, monkeypatch):
    monkeypatch.setenv("CREW_TRANSCRIPTS_DIR", str(tmp_path))
    with TestClient(app) as client:
        r = client.post("/api/upload", files={
            "file": ("brief.txt", b"Brand: BOREA. Budget 90k. Target pendolari.",
                     "text/plain")})
        assert r.status_code == 200
        d = r.json()
        assert d["is_image"] is False
        assert "BOREA" in d["text"] and d["chars"] > 0


def test_upload_rejects_unreadable_binary(tmp_path, monkeypatch):
    monkeypatch.setenv("CREW_TRANSCRIPTS_DIR", str(tmp_path))
    with TestClient(app) as client:
        r = client.post("/api/upload", files={
            "file": ("x.bin", b"\x00\x01\x02\x03", "application/octet-stream")})
        assert r.status_code == 415


def test_upload_image_accepted_without_text(tmp_path, monkeypatch):
    monkeypatch.setenv("CREW_TRANSCRIPTS_DIR", str(tmp_path))
    with TestClient(app) as client:
        r = client.post("/api/upload", files={
            "file": ("moodboard.png", b"\x89PNG\r\n", "image/png")})
        assert r.status_code == 200
        assert r.json()["is_image"] is True


# ─────── D15: visione immagini — solo teste Gemini, smistamento auto ────────

def test_study_image_routes_to_gemini_head(tmp_path, monkeypatch):
    monkeypatch.setenv("CREW_TRANSCRIPTS_DIR", str(tmp_path))
    seen = {}

    def fake_vision(roster, key, ctx, instr, b64, media="image/png"):
        seen.update(key=key, b64=b64, media=media)
        return "vedo un moodboard golden hour"

    monkeypatch.setattr(core, "head_study_image", fake_vision)

    with TestClient(app) as client, client.websocket_connect("/ws") as ws:
        up = client.post("/api/upload", files={
            "file": ("moodboard.png", b"\x89PNG\r\n\x1a\n", "image/png")})
        image_id = up.json()["image_id"]
        assert image_id
        ws.send_json({"type": "study_image", "image_id": image_id,
                      "text": "che clima trasmette?"})
        done = _drain_until(ws, "turn_completed")[-1]
        assert done["speaker"] == "market_researcher"   # l'unica Gemini nel roster ADV
        assert done["text"] == "vedo un moodboard golden hour"
        _drain_until(ws, "session_saved")

    assert seen["key"] == "market_researcher"
    assert seen["media"] == "image/png" and seen["b64"]     # bytes passati al core


def test_study_image_expired_id_is_reported(tmp_path, monkeypatch):
    monkeypatch.setenv("CREW_TRANSCRIPTS_DIR", str(tmp_path))
    with TestClient(app) as client, client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "study_image", "image_id": "inesistente",
                      "text": "x"})
        deg = _drain_until(ws, "router_degraded")[-1]
        assert "scaduta" in deg["reason"]

"""Test offline del core esteso — nessuna chiamata API."""
import json
import os

import pytest

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
    # D8: scala ancorata punto-per-punto — ogni gradino 0-10 tranne il 5
    # inietta una regola distinta e dichiara il proprio numero.
    for lvl in range(11):
        block = core.creativity_block(lvl)
        if lvl == 5:
            assert block == ""               # 5: neutro, nessuna iniezione
        else:
            assert f"dial {lvl}/10" in block
    texts = [core.creativity_block(l) for l in range(11) if l != 5]
    assert len(set(texts)) == 10             # nessun gradino uguale a un altro
    assert core.creativity_block(-1) == "" and core.creativity_block(99) == ""


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


def test_roster_default_matches_cast():
    r = core.Roster.default()
    assert list(r.keys()) == ["producer", "strategist", "cd", "social"]
    assert r.heads["cd"].model_id == "anthropic/claude-opus-5"
    assert r.heads["social"].model_id == "xai/grok-4.5"
    assert r.heads["strategist"].model_id == "gemini/gemini-3.1-pro-preview"
    assert r.heads["producer"].model_id == "anthropic/claude-opus-5"
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


def test_make_llm_families(monkeypatch):
    # Il flag live-search del .env locale cambierebbe il ramo xai/ (D23-bis):
    # qui si testa la mappatura BASE delle famiglie, quindi lo si neutralizza.
    monkeypatch.delenv("CREW_GROK_LIVE_SEARCH", raising=False)
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
    assert grok.additional_params.get("additional_drop_params") == ["stop"]  # T5: litellm droppa "stop"


def test_make_llm_grok_live_search_opt_in(monkeypatch):
    """D23-bis (05/08): col flag acceso la testa xai/ passa dal client
    /v1/responses (GrokLiveLLM) — la Live Search delle chat completions è
    stata dismessa da xAI (HTTP 410). Flag spento = LLM litellm normale."""
    h = core.Head(key="social", name="Social", avatar="a", color="c",
                  model_id="xai/grok-4.5", persona="p", creativity=5)
    monkeypatch.delenv("CREW_GROK_LIVE_SEARCH", raising=False)
    plain = core.make_llm(h)
    assert not isinstance(plain, core.GrokLiveLLM)
    assert "extra_body" not in plain.additional_params
    monkeypatch.setenv("CREW_GROK_LIVE_SEARCH", "1")
    live = core.make_llm(h)
    assert isinstance(live, core.GrokLiveLLM)
    assert live.model == "grok-4.5"           # nome nudo: l'endpoint non
    assert 0 <= live.temperature <= 1         # vuole il prefisso "xai/"


def test_grok_output_text_skips_reasoning_and_tool_calls():
    """D23-bis: dal payload /v1/responses si estrae SOLO il testo dei
    `message` — i giri interni (reasoning, custom_tool_call) si saltano."""
    data = {"output": [
        {"type": "reasoning", "summary": [{"text": "penso", "type": "summary_text"}]},
        {"type": "custom_tool_call", "name": "x_search"},
        {"type": "message", "content": [
            {"type": "output_text", "text": "riga uno"},
            {"type": "other", "text": "no"},
        ]},
        {"type": "message", "content": [{"type": "output_text", "text": "riga due"}]},
    ]}
    assert core.grok_output_text(data) == "riga uno\nriga due"
    assert core.grok_output_text({}) == ""


def test_parse_social_request():
    """D23: la riga SOCIAL_INTEL si estrae come il SEARCH_REQUEST."""
    clean, q, why = core.parse_social_request(
        "Serve un dato.\nSOCIAL_INTEL: nike tiktok || numeri reali di engagement")
    assert clean == "Serve un dato."
    assert q == "nike tiktok" and why == "numeri reali di engagement"
    assert core.parse_social_request("nessuna richiesta") == (
        "nessuna richiesta", None, None)


def test_social_intel_not_configured_and_command(monkeypatch):
    """D23: senza CREW_SOCIAL_TOOL_CMD -> sentinella; con un comando -> digest,
    e la query arriva come ULTIMO argomento."""
    monkeypatch.delenv("CREW_SOCIAL_TOOL_CMD", raising=False)
    assert core.social_intel("nike") == "[social tool not configured]"
    monkeypatch.setenv("CREW_SOCIAL_TOOL_CMD", "/bin/echo digest:")
    assert core.social_intel("nike tiktok") == "digest: nike tiktok"


def test_roster_llm_cache_and_invalidation():
    r = core.Roster.default()
    # Cache hit: second call returns same object
    first = r.llm("social")
    assert r.llm("social") is first
    # Cache invalidation: update clears cache and creates new LLM
    r.update_head("social", creativity=10)
    fresh = r.llm("social")
    assert fresh is not first
    assert fresh.temperature == 1.2  # 0.1 + 0.11*10 = 1.2
    # Anthropic models still routed via ClaudeLLM after update
    r.update_head("cd", creativity=9)
    cd_llm = r.llm("cd")
    assert isinstance(cd_llm, core.ClaudeLLM)
    assert cd_llm.model == "claude-opus-5"


# ─────── Task 3: prompt builder + head_speak ────────────────────────────

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
    assert "CREATIVE RISK SETTING" in p and "dial 10/10" in p
    assert core.PRIVATE_PREAMBLE in p


def test_build_turn_prompt_truncates_context():
    # D18: budget condiviso ampio (default 60k car). Un transcript enorme entra
    # tagliato al budget, ma NON al vecchio 8000; sotto il budget passa intero.
    big = core.build_turn_prompt(_mk_head(), "x" * 200000, "go")
    assert core._context_chars() <= len(big) < core._context_chars() + 3000
    small = core.build_turn_prompt(_mk_head(), "y" * 5000, "go")
    assert "y" * 5000 in small          # sotto il budget: contesto intero


def test_context_chars_env_override(monkeypatch):
    monkeypatch.setenv("CREW_CONTEXT_CHARS", "1000")
    p = core.build_turn_prompt(_mk_head(), "z" * 50000, "go")
    assert p.count("z") == 1000          # rispetta il budget da env


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


# ─────── Task 4: RoomSession ────────────────────────────────────────────────

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


# ─────── Task 5: router a ondate + trigger collab ────────────────────────

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


# ─────── Bug hunt item 7: cap, negazione, verbi mancanti ─────────────────

def test_parse_auto_request_explicit_n_is_capped():
    # bug 7a: "per 500 giri" non deve far girare la stanza 500 volte.
    assert core.parse_auto_request("discutete fra voi per 500 giri") == 50
    assert core.parse_auto_request("discutete fra voi per 500 giri") == \
        core.AUTO_MAX_ROUNDS
    # "0 giri" resta falsy (trattato come messaggio normale a valle) — il
    # tetto non deve alterare questo caso limite.
    assert core.parse_auto_request("discutete fra voi per 0 giri") == 0


def test_parse_auto_request_negation_guard():
    # bug 7b: negazione appena prima del verbo -> NON è un trigger.
    assert core.parse_auto_request(
        "non parlate fra di voi, aspettate il mio brief") is None
    assert core.parse_auto_request(
        "senza parlare fra di voi, aspettate") is None
    # una subordinata (nessuna negazione appena prima del verbo) resta un
    # trigger valido — il guard non deve overmatchare.
    assert core.parse_auto_request(
        "quando parlate fra di voi restate concreti") == core.AUTO_DEFAULT_CAP


def test_parse_auto_request_extended_verb_forms():
    # bug 7c: forme prima non riconosciute (falsi negativi).
    assert core.parse_auto_request("discutetene fra voi") == \
        core.AUTO_DEFAULT_CAP
    assert core.parse_auto_request("potete parlarne fra di voi") == \
        core.AUTO_DEFAULT_CAP


def test_requested_rounds_exposes_raw_number():
    assert core.requested_rounds("discutete fra voi per 500 giri") == 500
    assert core.requested_rounds("parlatene fra di voi") is None


# ─────── Bug hunt item 12: parse_wave_plan normalizza to == speaker ──────

def test_parse_wave_plan_normalizes_self_addressed_to_director():
    raw = '[[{"speaker":"cd","instruction":"x","to":"cd"}]]'
    waves = core.parse_wave_plan(raw, {"cd"})
    assert waves[0][0]["to"] == "director"


# ─────── Bug hunt item 5: RoomSession, stamp in collisione ───────────────

def test_stamp_collision_creates_distinct_files_and_keeps_first_intact(tmp_path):
    s1 = core.RoomSession("BRIEF1", base_dir=str(tmp_path), stamp="20260729-1200")
    s1.append_room("Director", "contenuto prezioso")
    s2 = core.RoomSession("BRIEF2", base_dir=str(tmp_path), stamp="20260729-1200")
    assert s1.room_path != s2.room_path
    on_disk_1 = open(s1.room_path, encoding="utf-8").read()
    assert "contenuto prezioso" in on_disk_1
    on_disk_2 = open(s2.room_path, encoding="utf-8").read()
    assert "BRIEF2" in on_disk_2 and "contenuto prezioso" not in on_disk_2
    # i privati condividono lo stamp uniquificato (nessun altro punto da
    # toccare per il fix, com da nota implementatore).
    assert s1.private_path("cd") != s2.private_path("cd")


# ─────── Bug hunt item 13/14/15: fix "sospetti ma solidi" ────────────────

def test_roster_save_is_atomic_no_tmp_left_behind(tmp_path):
    p = str(tmp_path / "roster.json")
    core.Roster.default().save(p)
    assert os.path.exists(p)
    assert not os.path.exists(p + ".tmp")


def test_roster_load_skips_invalid_key_keeps_others(tmp_path):
    p = tmp_path / "roster.json"
    good = core.Head(key="cd", name="CD", avatar="🎨", color="#ff8700",
                     model_id="anthropic/claude-opus-5", persona="p")
    bad = good.to_dict() | {"key": "Not Valid!"}
    p.write_text(json.dumps({"heads": [good.to_dict(), bad]}), encoding="utf-8")
    r = core.Roster.load(str(p))
    assert list(r.keys()) == ["cd"]        # solo la testa valida sopravvive


def test_roster_load_all_keys_invalid_falls_back_to_default(tmp_path):
    p = tmp_path / "roster.json"
    good = core.Head(key="cd", name="CD", avatar="🎨", color="#ff8700",
                     model_id="anthropic/claude-opus-5", persona="p")
    bad = good.to_dict() | {"key": "Not Valid!"}
    p.write_text(json.dumps({"heads": [bad]}), encoding="utf-8")
    r = core.Roster.load(str(p))
    assert list(r.keys()) == ["producer", "strategist", "cd", "social"]
    assert (tmp_path / "roster.json.bad").exists()


def test_claude_cli_env_scrubs_billing_and_endpoint_vars(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "x")
    monkeypatch.setenv("ANTHROPIC_AUTH_TOKEN", "y")
    monkeypatch.setenv("ANTHROPIC_BASE_URL", "https://evil.example")
    seen = {}

    def fake_run(cmd, input, capture_output, text, env, timeout):
        seen.update(env)
        class R:
            returncode = 0
            stdout = "ok"
            stderr = ""
        return R()

    monkeypatch.setattr(core.subprocess, "run", fake_run)
    monkeypatch.setattr(core, "CLAUDE_CLI", "/usr/bin/claude")
    llm = core.ClaudeLLM("claude-opus-5")
    llm._via_cli("hello")
    assert "ANTHROPIC_API_KEY" not in seen
    assert "ANTHROPIC_AUTH_TOKEN" not in seen
    assert "ANTHROPIC_BASE_URL" not in seen


# ─────── D5/D6 (03/08): timeout configurabile senza fallback silenzioso;
#         blocco creatività solo dove la temperatura non esiste ─────────────

def test_cli_timeout_env_override(monkeypatch):
    monkeypatch.setenv("CREW_CLAUDE_TIMEOUT", "3600")
    seen = {}

    def fake_run(cmd, input, capture_output, text, env, timeout):
        seen["timeout"] = timeout
        class R:
            returncode = 0
            stdout = "ok"
            stderr = ""
        return R()

    monkeypatch.setattr(core.subprocess, "run", fake_run)
    monkeypatch.setattr(core, "CLAUDE_CLI", "/usr/bin/claude")
    core.ClaudeLLM("claude-opus-5")._via_cli("hello")
    assert seen["timeout"] == 3600.0


def test_cli_timeout_does_not_fall_back_to_api(monkeypatch):
    def fake_run(cmd, input, capture_output, text, env, timeout):
        raise core.subprocess.TimeoutExpired(cmd, timeout,
                                             output="bozza già scritta")

    monkeypatch.setattr(core.subprocess, "run", fake_run)
    monkeypatch.setattr(core, "CLAUDE_CLI", "/usr/bin/claude")
    llm = core.ClaudeLLM("claude-opus-5")

    class Boom:
        def call(self, prompt):
            raise AssertionError("il timeout NON deve ricadere sull'API")

    llm._api = Boom()
    before = len(core._route_log)
    with pytest.raises(core.ClaudeTimeoutError,
                       match="nessun fallback automatico") as exc:
        llm.call("hello")
    assert len(core._route_log) == before    # nessuna rotta registrata
    assert exc.value.partial == "bozza già scritta"   # il lavoro non si butta


def test_build_turn_prompt_block_only_for_anthropic():
    g = core.Head(key="mr", name="Market Researcher", avatar="🔎",
                  color="#00afd7", model_id="gemini/gemini-3.1-pro-preview",
                  persona=" p", creativity=10)
    assert "CREATIVE RISK SETTING" not in core.build_turn_prompt(g, "T", "go")
    a = core.Head(key="cd", name="CD", avatar="🎨", color="#ff8700",
                  model_id="anthropic/claude-opus-5", persona=" p",
                  creativity=10)
    assert "CREATIVE RISK SETTING" in core.build_turn_prompt(a, "T", "go")


# ─────── Fase 3: agganci per il contratto web (D4/D10, §7.2, §7.3) ─────────

def test_cli_effort_flag_in_argv(monkeypatch):
    seen = {}

    def fake_run(cmd, input, capture_output, text, env, timeout):
        seen["cmd"] = cmd
        class R:
            returncode = 0
            stdout = "ok"
            stderr = ""
        return R()

    monkeypatch.setattr(core.subprocess, "run", fake_run)
    monkeypatch.setattr(core, "CLAUDE_CLI", "/usr/bin/claude")
    core.ClaudeLLM("claude-opus-5", effort="high")._via_cli("x")
    assert "--effort" in seen["cmd"]
    assert seen["cmd"][seen["cmd"].index("--effort") + 1] == "high"
    core.ClaudeLLM("claude-opus-5")._via_cli("x")     # default: nessun flag
    assert "--effort" not in seen["cmd"]


def test_claude_last_route_is_per_instance(monkeypatch):
    def fake_run(cmd, input, capture_output, text, env, timeout):
        class R:
            returncode = 0
            stdout = "ok"
            stderr = ""
        return R()

    monkeypatch.setattr(core.subprocess, "run", fake_run)
    monkeypatch.setattr(core, "CLAUDE_CLI", "/usr/bin/claude")
    a = core.ClaudeLLM("claude-opus-5")
    b = core.ClaudeLLM("claude-opus-5")
    a.call("hello")
    assert a.last_route == "subscription"
    assert b.last_route == "?"                 # l'altra istanza non è toccata

    monkeypatch.setattr(core, "CLAUDE_CLI", None)   # niente CLI → diretti in API

    class FakeAPI:
        def call(self, prompt):
            return "via api"

    b._api = FakeAPI()
    b.call("hello")
    assert b.last_route == "api"


def test_last_plan_route_waves_vs_fallback(monkeypatch):
    r = core.Roster.default()

    class GoodRouter:
        def call(self, prompt):
            return '[[{"speaker": "cd", "instruction": "a", "to": "director"}]]'

    monkeypatch.setattr(core, "llm_claude_router", GoodRouter())
    core.route_plan(r, "T", "cd: un'idea")
    assert core.last_plan_route() == "waves"

    class DeadRouter:
        def call(self, prompt):
            raise RuntimeError("router giù")

    monkeypatch.setattr(core, "llm_claude_router", DeadRouter())
    core.route_plan(r, "T", "cd: un'idea")
    assert core.last_plan_route() == "fallback"


def test_head_effort_field_and_adv_roster():
    h = core.Head(key="cd", name="CD", avatar="🎨", color="#ff8700",
                  model_id="anthropic/claude-opus-5", persona="p",
                  effort="high")
    assert core.Head.from_dict(h.to_dict()) == h
    llm = core.make_llm(h)
    assert isinstance(llm, core.ClaudeLLM) and llm.effort == "high"
    # Il roster ADV porta gli effort decisi in D4; le teste non-anthropic no.
    adv = core.Roster.load(os.path.join(os.path.dirname(core.__file__),
                                        "roster.adv.json"))
    assert adv.heads["creative_strategist"].effort == "high"
    assert adv.heads["producer"].effort == "low"
    assert adv.heads["market_researcher"].effort == ""


# ─────── D5-bis: fallback API trasparente (mai più errori inghiottiti) ──────

def test_cli_failure_falls_back_to_api_transparently(monkeypatch):
    def fake_run(cmd, input, capture_output, text, env, timeout):
        raise OSError("cli esplosa")

    monkeypatch.setattr(core.subprocess, "run", fake_run)
    monkeypatch.setattr(core, "CLAUDE_CLI", "/usr/bin/claude")
    llm = core.ClaudeLLM("claude-opus-5")

    class FakeAPI:
        def call(self, prompt):
            return "salvato dall'api"

    llm._api = FakeAPI()
    assert llm.call("hello") == "salvato dall'api"
    assert llm.last_route == "api"
    assert "OSError" in llm.last_cli_error       # il motivo non sparisce più


def test_both_channels_down_raises_the_whole_truth(monkeypatch):
    def fake_run(cmd, input, capture_output, text, env, timeout):
        raise OSError("cli esplosa")

    monkeypatch.setattr(core.subprocess, "run", fake_run)
    monkeypatch.setattr(core, "CLAUDE_CLI", "/usr/bin/claude")
    llm = core.ClaudeLLM("claude-opus-5")

    class BrokeAPI:
        def call(self, prompt):
            raise ValueError("credito esaurito")

    llm._api = BrokeAPI()
    with pytest.raises(RuntimeError) as exc:
        llm.call("hello")
    msg = str(exc.value)
    assert "CLI:" in msg and "OSError" in msg     # metà CLI
    assert "API:" in msg and "credito esaurito" in msg   # metà API


# ─────── D14: modelli open (Featherless / Ollama) ammessi nel roster ───────

def test_model_allowed_whitelist_and_open_prefixes():
    assert core.model_allowed("anthropic/claude-opus-5")
    assert core.model_allowed("featherless_ai/huihui-ai/Qwen2.5-14B-Instruct-abliterated-v2")
    assert core.model_allowed("openrouter/cognitivecomputations/dolphin-mistral-24b-venice-edition")
    assert core.model_allowed("ollama/qwen3.5:27b")
    assert not core.model_allowed("openai/gpt-5")
    assert not core.model_allowed("random-string")


def test_make_llm_open_model_via_litellm():
    h = core.Head(key="wild", name="Wild", avatar="🔥", color="#f55",
                  model_id="featherless_ai/huihui-ai/Huihui-Qwen3.5-27B-abliterated",
                  persona="p", creativity=9)
    llm = core.make_llm(h)
    # non-anthropic => LLM di crewai/litellm con temperatura dalla creatività
    assert not isinstance(llm, core.ClaudeLLM)
    assert llm.model == "featherless_ai/huihui-ai/Huihui-Qwen3.5-27B-abliterated"
    assert llm.temperature == core.temp_for_level(9)

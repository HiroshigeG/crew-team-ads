"""La CLI di Claude che si aggiorna da sola (D37).

Il 25/11/2026 un aggiornamento npm ha tolto per qualche minuto
`/opt/homebrew/bin/claude`: 22 chiamate su 60 sono fallite con
FileNotFoundError. In produzione quel guasto mandava la chiamata sull'API A
PAGAMENTO. Ora la CLI che manca si aspetta (tetto CREW_CLI_MISSING_WAIT) e si
riprova una volta; solo dopo il tetto si torna al fallback di prima.
"""
import pytest

import crew_cast as core


class _Ok:
    returncode = 0
    stdout = "ok"
    stderr = ""


@pytest.fixture
def no_sleep(monkeypatch):
    slept = []
    monkeypatch.setattr(core.time, "sleep", lambda s: slept.append(s))
    return slept


def test_missing_cli_is_waited_for_and_retried(monkeypatch, no_sleep):
    calls = {"run": 0, "exists": 0}

    def fake_run(cmd, **kw):
        calls["run"] += 1
        if calls["run"] == 1:
            raise FileNotFoundError(2, "No such file or directory", cmd[0])
        return _Ok()

    def fake_exists(path):
        calls["exists"] += 1
        return calls["exists"] >= 3          # torna dopo due controlli

    monkeypatch.setattr(core.subprocess, "run", fake_run)
    monkeypatch.setattr(core.os.path, "exists", fake_exists)
    monkeypatch.setattr(core, "CLAUDE_CLI", "/opt/homebrew/bin/claude")
    monkeypatch.setenv("CREW_CLI_MISSING_WAIT", "60")
    assert core.ClaudeLLM("claude-sonnet-5")._via_cli("x") == "ok"
    assert calls["run"] == 2
    assert len(no_sleep) == 2


def test_missing_cli_does_not_reach_the_paid_api_when_it_comes_back(monkeypatch, no_sleep):
    state = {"run": 0}

    def fake_run(cmd, **kw):
        state["run"] += 1
        if state["run"] == 1:
            raise FileNotFoundError(2, "No such file or directory", cmd[0])
        return _Ok()

    class _Api:
        def call(self, prompt):
            raise AssertionError("l'API a pagamento non deve essere chiamata")

    monkeypatch.setattr(core.subprocess, "run", fake_run)
    monkeypatch.setattr(core.os.path, "exists", lambda p: True)
    monkeypatch.setattr(core, "CLAUDE_CLI", "/opt/homebrew/bin/claude")
    llm = core.ClaudeLLM("claude-sonnet-5")
    llm._api = _Api()
    assert llm.call("x") == "ok"
    assert llm.last_route == "subscription"


def test_cli_that_never_comes_back_raises_after_the_cap(monkeypatch, no_sleep):
    clock = {"t": 0.0}

    def fake_sleep(s):
        clock["t"] += s

    def fake_run(cmd, **kw):
        raise FileNotFoundError(2, "No such file or directory", cmd[0])

    monkeypatch.setattr(core.time, "sleep", fake_sleep)
    monkeypatch.setattr(core.time, "monotonic", lambda: clock["t"])
    monkeypatch.setattr(core.subprocess, "run", fake_run)
    monkeypatch.setattr(core.os.path, "exists", lambda p: False)
    monkeypatch.setattr(core, "CLAUDE_CLI", "/opt/homebrew/bin/claude")
    monkeypatch.setenv("CREW_CLI_MISSING_WAIT", "10")
    with pytest.raises(FileNotFoundError):
        core.ClaudeLLM("claude-sonnet-5")._via_cli("x")
    assert 10 <= clock["t"] <= 12                 # ha aspettato il tetto, non di più


def test_other_cli_errors_are_not_retried(monkeypatch, no_sleep):
    calls = {"run": 0}

    class _Fail:
        returncode = 1
        stdout = ""
        stderr = "boom"

    def fake_run(cmd, **kw):
        calls["run"] += 1
        return _Fail()

    monkeypatch.setattr(core.subprocess, "run", fake_run)
    monkeypatch.setattr(core, "CLAUDE_CLI", "/opt/homebrew/bin/claude")
    with pytest.raises(RuntimeError):
        core.ClaudeLLM("claude-sonnet-5")._via_cli("x")
    assert calls["run"] == 1 and no_sleep == []

"""A goal raggiunto la stanza mette una proposta sul tavolo.

Prima (25/11/2026): il goal chiudeva con «Obiettivo raggiunto» ma la card
«Proposta in lavorazione» restava vuota, e il testo vincente andava riscritto
a mano. `draft_proposal` estrae dal transcript ciò che la stanza ha GIÀ scritto:
niente miglioramenti, niente invenzioni, fail-closed.
"""
import crew_cast as core


def test_parse_proposal_draft_ok():
    raw = '{"headline": " Non ti incita. Non perde. ", "support": "Guarnizione sostituibile.", "body": "Film da 20 secondi."}'
    assert core.parse_proposal_draft(raw) == {
        "headline": "Non ti incita. Non perde.",
        "support": "Guarnizione sostituibile.",
        "body": "Film da 20 secondi.",
    }


def test_parse_proposal_draft_accepts_fence_and_missing_keys():
    raw = '```json\n{"headline": "Solo titolo"}\n```'
    assert core.parse_proposal_draft(raw) == {"headline": "Solo titolo", "support": "", "body": ""}


def test_parse_proposal_draft_caps_lengths():
    raw = '{"headline": "%s", "support": "", "body": "%s"}' % ("h" * 500, "b" * 5000)
    d = core.parse_proposal_draft(raw)
    assert len(d["headline"]) <= 160 and len(d["body"]) <= 1500


def test_parse_proposal_draft_needs_some_content():
    assert core.parse_proposal_draft('{"headline": "", "support": " ", "body": ""}') is None


def test_parse_proposal_draft_rejects_garbage():
    for raw in ["", "nessuna proposta", "[]", '"stringa"', '{"headline": 3, "body": []}', "{rotto"]:
        assert core.parse_proposal_draft(raw) is None


def test_proposal_prompt_forbids_invention_and_follows_language():
    p = core.PROPOSAL_PROMPT
    assert "only what the room has already written" in p
    assert "do not improve" in p.lower()
    assert "language of the goal" in p


def test_draft_proposal_uses_judge_model_and_parses(monkeypatch):
    seen = {}

    class _Fake:
        def call(self, prompt):
            seen["prompt"] = prompt
            return '{"headline": "H", "support": "S", "body": "B"}'

    monkeypatch.setattr(core, "llm_claude_judge", _Fake())
    d = core.draft_proposal("un claim per Rivo", "Copywriter: Non ti incita.")
    assert d == {"headline": "H", "support": "S", "body": "B"}
    assert "un claim per Rivo" in seen["prompt"]
    assert "Non ti incita." in seen["prompt"]


def test_draft_proposal_failure_is_none_not_an_exception(monkeypatch):
    class _Boom:
        def call(self, prompt):
            raise RuntimeError("giù")

    monkeypatch.setattr(core, "llm_claude_judge", _Boom())
    assert core.draft_proposal("g", "t") is None

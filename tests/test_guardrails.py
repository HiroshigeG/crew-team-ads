"""Guardrail a runtime: ciò che il bake-off MISURAVA (il produttore sceglie l'idea,
finge di vedere un'immagine, inventa un link; Dark Angel non dà tre idee) ora si
IMPONE: la risposta viene controllata, rifiutata con un motivo e rigenerata.
Offline: nessuna chiamata di rete."""
import logging

import pytest

import crew_cast as core
import guardrails as gr

CTX_IT = "BRIEF:\nSessione ADV\n\nDirector: Dimmi dove siamo e cosa manca.\n"
CTX_EN = "BRIEF:\nSession\n\nDirector: Tell me where we are and what is missing.\n"
PAD = (" Posso anche riassumere dove siamo, cosa manca e chi dovrebbe parlare adesso, "
       "così il Director ha tutto sotto gli occhi e decide con calma senza che io indichi una preferenza.")
OK_IT = ("Siamo a metà: la direzione c'è ma manca il tono per il target e non è chiaro "
         "come si usa il budget. Il Director deve decidere quale rischio prendersi.")


def check(key, reply, ctx=CTX_IT, vision=False):
    return gr.check_reply(key, reply, context=ctx, vision=vision)


# ── generici ──────────────────────────────────────────────────────────────

def test_a_normal_reply_passes():
    assert check("cd", OK_IT).ok


def test_empty_or_one_word_replies_fail_but_pass_marker_is_allowed():
    assert check("cd", "").code == "empty"
    assert check("cd", "   ").code == "empty"
    assert check("cd", "...").code == "too_short"           # il caso aion DN1 / DA1
    assert check("cd", "[PASS]").ok                          # la collab libera usa esattamente questo


# ── produttore: non sceglie, non raccomanda ───────────────────────────────

@pytest.mark.parametrize("reply", [
    "Scelgo la prima direzione, la versione corretta di The Only Witness, e chiudo il dubbio.",
    "Tra queste due, io andrei sulla seconda, ma la scelta finale è tua e basta così.",
    "Dopo aver esaminato entrambe le direzioni, consiglio di procedere con The Only Witness.",
    "I'd go with the first direction because it respects the brief and the guidelines more.",
    "I recommend we proceed with the second one, it is clearly the stronger choice here.",
])
def test_the_producer_picking_or_recommending_is_rejected(reply):
    r = check("producer", reply)
    assert not r.ok and r.code == "picks"


@pytest.mark.parametrize("reply", [
    "La scelta è tua, Director: io non scelgo e non classifico. Prima però devo sapere quali due direzioni intendi.",
    "Questa scelta spetta a voi: non indico quale direzione sia migliore. Ecco i criteri e i costi di ciascuna.",
    "Non ti consiglio niente: posso mettere le due opzioni affiancate con rischi e criteri, se vuoi.",
])
def test_the_producer_declining_to_pick_is_accepted(reply):
    assert check("producer", reply + PAD).ok


def test_only_the_producer_is_held_to_the_no_pick_rule():
    assert check("cd", "Scelgo la seconda: è la più forte e la porto avanti io subito.").ok


# ── nessuna testa finge di vedere ─────────────────────────────────────────

@pytest.mark.parametrize("reply", [
    "Guardando l'inserzione del 2023 vedo una mano che apre un cassetto pieno di borracce.",
    "Looking at the 2023 'Il cassetto' ad, it's a textbook example of adhering to the guidelines.",
    "Nell'immagine vedo cinque borracce grigie e una sola scura al centro del cassetto.",
])
def test_a_text_only_head_claiming_to_see_an_image_is_rejected(reply):
    r = check("account_director", reply)
    assert not r.ok and r.code == "sees_image"


def test_describing_through_a_colleague_is_honest_and_accepted():
    ok = "Secondo la descrizione di Market Researcher, vedo il punto: il cassetto pieno è il vero nemico del brief."
    assert check("account_director", ok).ok


def test_a_vision_head_may_describe_what_it_sees():
    assert check("market_researcher", "Nell'immagine vedo cinque borracce grigie e una sola scura.", vision=True).ok


# ── niente link inventati ─────────────────────────────────────────────────

def test_a_link_that_is_not_in_the_room_is_rejected_one_that_is_passes():
    r = check("producer", "La fonte è https://esempio.it/ricerca-2024 e conferma il dato sulle ricerche del marchio.")
    assert not r.ok and r.code == "invented_link"
    ctx = CTX_IT + "Researcher: vedi https://esempio.it/ricerca-2024 per il dato.\n"
    assert check("producer", "Come detto, https://esempio.it/ricerca-2024 conferma il dato sulle ricerche, quindi va verificato." + PAD, ctx).ok


# ── Dark Angel: tre idee ──────────────────────────────────────────────────

THREE = "1. " + "parola " * 20 + "\n2. " + "parola " * 20 + "\n3. " + "parola " * 20


def test_dark_angel_needs_exactly_three_short_numbered_ideas():
    assert check("dark_angel", THREE).ok
    r = check("dark_angel", "1. " + "parola " * 20 + "\n2. " + "parola " * 20)
    assert not r.ok and r.code == "format"
    assert not check("dark_angel", OK_IT).ok                       # un paragrafo unico
    too_long = "1. " + "parola " * 90 + "\n2. due due due due due due due due\n3. tre tre tre tre tre tre tre tre"
    assert check("dark_angel", too_long).code == "format"


def test_the_three_ideas_rule_does_not_apply_to_other_heads():
    assert check("cd", OK_IT).ok


# ── lingua del Director ───────────────────────────────────────────────────

EN_REPLY = ("We are halfway there, the direction is clear but the tone for the target is still missing "
            "and we do not know how the budget is used yet, so the Director must decide the risk.")


def test_an_english_reply_to_an_italian_director_is_rejected():
    r = check("cd", EN_REPLY)
    assert not r.ok and r.code == "lang"


def test_no_language_rule_when_the_director_writes_english_or_reply_is_short():
    assert check("cd", EN_REPLY, ctx=CTX_EN).ok
    assert check("cd", "Understood, going ahead with the plan as discussed earlier today.").ok  # breve


# ── produttore: lunghezza ─────────────────────────────────────────────────

def test_producer_length_band():
    assert check("producer", "Va bene così, andiamo avanti con il lavoro senza altro da aggiungere ora, grazie.").code == "length"
    assert check("producer", ("parola " * 300).strip()).code == "length"
    assert check("producer", OK_IT * 2).ok


# ── ripetizione con feedback ──────────────────────────────────────────────

class Seq:
    """LLM finto: restituisce le risposte in sequenza e ricorda i prompt."""
    def __init__(self, *replies):
        self.replies, self.prompts = list(replies), []

    def call(self, prompt):
        self.prompts.append(prompt)
        return self.replies[min(len(self.prompts), len(self.replies)) - 1]


def head(key="producer", model="anthropic/claude-sonnet-5-5"):
    r = core.Roster.default()
    h = r.heads[key if key in r.heads else "producer"]
    r.update_head(h.key, model_id=model)
    return r.heads[h.key]


PICK = "Scelgo la prima direzione: è l'unica che rispetta il brief e le guideline, e chiudo qui il dubbio."
GOOD = ("La scelta è tua, Director: io non scelgo né classifico. Posso mettere le due direzioni affiancate "
        "con i criteri e i costi di ciascuna, se me lo chiedi, senza dire quale preferisco." + PAD)


def test_a_rejected_reply_is_regenerated_with_the_reason(monkeypatch):
    llm = Seq(PICK, GOOD)
    out = core.guarded_reply(llm, head(), "PROMPT", CTX_IT)
    assert out == GOOD and len(llm.prompts) == 2
    assert "REJECTED" in llm.prompts[1] and "choose, rank or recommend" in llm.prompts[1]
    assert PICK[:30] in llm.prompts[1]                # la risposta sbagliata è nel prompt di ripetizione


def test_retries_are_capped_and_a_safe_fallback_replaces_a_lie(monkeypatch):
    monkeypatch.setenv("CREW_GUARDRAIL_RETRIES", "2")
    llm = Seq(PICK)                                    # sbaglia sempre
    out = core.guarded_reply(llm, head(), "PROMPT", CTX_IT)
    assert len(llm.prompts) == 3                       # 1 + 2 ripetizioni
    assert "non scelgo" in out.lower() and PICK not in out   # fallback veritiero, non la risposta sbagliata


def test_the_image_lie_falls_back_to_an_honest_sentence():
    llm = Seq("Guardando l'inserzione vedo cinque borracce grigie nel cassetto aperto sul tavolo.")
    out = core.guarded_reply(llm, head("account_director", "featherless_ai/Qwen/Qwen2.5-72B-Instruct"), "P", CTX_IT)
    assert "non vedo l'immagine" in out.lower()


def test_style_failures_fail_open_with_a_warning(monkeypatch, caplog):
    llm = Seq(EN_REPLY)                                # lingua sbagliata ogni volta
    with caplog.at_level(logging.WARNING, logger="crew_cast"):
        out = core.guarded_reply(llm, head("cd", "anthropic/claude-opus-5"), "P", CTX_IT)
    assert out == EN_REPLY                             # lingua/lunghezza non si sostituiscono: si consegna
    assert any("guardrail" in m.getMessage().lower() for m in caplog.records)


def test_guardrails_can_be_switched_off(monkeypatch):
    monkeypatch.setenv("CREW_GUARDRAILS", "0")
    llm = Seq(PICK, GOOD)
    assert core.guarded_reply(llm, head(), "P", CTX_IT) == PICK and len(llm.prompts) == 1


def test_a_good_first_reply_costs_no_extra_call():
    llm = Seq(GOOD)
    assert core.guarded_reply(llm, head(), "P", CTX_IT) == GOOD and len(llm.prompts) == 1


def test_head_speak_goes_through_the_guardrail(monkeypatch):
    r = core.Roster.load("roster.adv.json")
    r.update_head("producer", model_id="anthropic/claude-sonnet-5-5")
    llm = Seq(PICK, GOOD)
    monkeypatch.setitem(r._llms, "producer", llm)
    out = core.head_speak(r, "producer", CTX_IT, "scegli tu la migliore")
    assert out == GOOD and len(llm.prompts) == 2


def test_leaked_tokens_are_stripped_before_the_check():
    llm = Seq(GOOD + "<|im_end|>\n<|im_start|>user\nscegli tu")
    assert core.guarded_reply(llm, head(), "P", CTX_IT) == GOOD


# ── compatibilità con CrewAI: stessa funzione come Task.guardrail ─────────

def test_the_same_checks_plug_into_a_real_crewai_task_with_retries():
    from crewai import Agent, BaseLLM, Task

    calls = []

    class FakeLLM(BaseLLM):
        def __init__(self):
            super().__init__(model="fake/seq")

        def call(self, messages, tools=None, callbacks=None, available_functions=None,
                 from_task=None, from_agent=None, **kw):
            calls.append(1)
            return PICK if len(calls) == 1 else GOOD

        def supports_function_calling(self):
            return False

        def supports_stop_words(self):
            return False

        def get_context_window_size(self):
            return 8000

    agent = Agent(role="Executive Producer", goal="sintetizzare", backstory="produttore",
                  llm=FakeLLM(), allow_delegation=False)
    task = Task(description="Scegli la migliore.", expected_output="una risposta breve",
                agent=agent, guardrail=gr.as_task_guardrail("producer", context=CTX_IT),
                guardrail_max_retries=2)
    out = task.execute_sync()
    assert len(calls) == 2 and out.raw.strip() == GOOD


# ── regressioni dalla misura contro i verdetti del giudice (D34) ───────────

@pytest.mark.parametrize("reply", [
    "Come Executive Producer, consiglierei di procedere con The Only Witness come film hero e basta così.",
    "In conclusione, The Only Witness sembra la direzione più forte e originale. Suggerisco quindi di procedere.",
    "La mia raccomandazione è di procedere con The Only Witness come idea portante, con gli aggiustamenti detti.",
    "La direzione uno rispetta le linee guida ed è la scelta che meglio rappresenta l'anima del brand e il target.",
])
def test_softer_recommendations_are_also_rejected(reply):
    assert check("producer", reply).code == "picks"


@pytest.mark.parametrize("reply", [
    "Non vedo l'inserzione. Posso leggere solo ciò che i colleghi hanno scritto in stanza, e in questa sessione non c'è niente.",
    "Non posso descriverla. Non vedo immagini, e nel transcript non c'è nessuna inserzione: c'è solo il testo del brief.",
    "Descrivimi con precisione cosa si vede nell'inserzione che hai appena caricato, poi ti dico come si allinea al brief.",
    "Ad esempio, il brief dice che la luce deve essere piatta, e questo vale per qualunque cosa mostriamo in video.",
])
def test_honest_replies_about_not_seeing_are_not_flagged(reply):
    assert check("account_director", reply).ok


def test_the_honest_english_reply_is_not_flagged_for_a_director_who_writes_english():
    reply = "I can't see the image, and nobody has described it in the room yet, so I have nothing to work from here."
    assert check("account_director", reply, ctx=CTX_EN).ok


def test_a_stated_sight_still_trips_after_the_negation_fix():
    r = check("account_director", "Nell'inserzione che hai appena caricato, si vede una borraccia Rivo posata su un marciapiede bagnato.")
    assert r.code == "sees_image"
    assert check("account_director", "Looking at the ad you uploaded, I can see a green bottle on a wet pavement at dawn.").code == "sees_image"


@pytest.mark.parametrize("reply", [
    "Dopo aver analizzato le vostre indicazioni e le guidelines, credo che la direzione migliore sia «The Only Witness» con le correzioni.",
    "Ritengo che la versione corretta di The Only Witness sia la più forte tra quelle emerse oggi in stanza e vada portata avanti.",
])
def test_belief_phrased_recommendations_are_rejected(reply):
    assert check("producer", reply).code == "picks"


def test_a_neutral_belief_about_something_else_is_not_flagged():
    ok = ("Credo che manchi ancora il dato sul budget, e che il Director debba decidere quale rischio prendersi sul tono, "
          "perché al momento le due direzioni hanno costi e criteri molto diversi tra loro e nessuno li ha messi in fila." + PAD)
    assert check("producer", ok).ok

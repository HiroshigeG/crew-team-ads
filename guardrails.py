"""Guardrail a runtime: ciò che i bake-off MISURAVANO ora si IMPONE.

Il 25/11/2026 i bake-off (evals/) hanno mostrato quattro difetti che nessuna
scelta di modello risolve da sola: il produttore sceglie l'idea quando il
Director lo ordina, una testa solo-testo finge di vedere un'immagine, un modello
inventa un link, Dark Angel non rispetta il formato. Qui ogni difetto diventa un
controllo: la risposta viene verificata, rifiutata con un MOTIVO e rigenerata
(vedi `crew_cast.guarded_reply`).

Le funzioni hanno la firma di `crewai.Task.guardrail` — `(output) -> (ok, feedback)`
(`as_task_guardrail`): le stesse regole girano dentro un Task di CrewAI vero. Puro:
nessuna rete, nessun segreto. Euristiche a espressioni regolari, misurate contro i
verdetti del giudice dei bake-off (vedi D34): non sono un giudice, sono una rete.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

# ── utilità condivise ───────────────────────────────────────────────────────

_IT = {"il", "lo", "la", "i", "gli", "le", "di", "del", "della", "dei", "delle", "che", "è", "non",
       "per", "con", "una", "un", "sono", "si", "come", "ma", "più", "anche", "nel", "nella", "sul",
       "alla", "al", "da", "in", "ha", "ho", "hai", "siamo", "questa", "questo", "quello", "dove",
       "cosa", "manca", "stanza", "direzione", "tua", "tuo", "ci", "mi", "ti"}
_EN = {"the", "and", "is", "of", "to", "that", "for", "with", "you", "it", "are", "this", "not", "we",
       "our", "in", "on", "as", "be", "by", "have", "has", "was", "will", "from", "an", "at", "what",
       "which", "your", "should", "would", "can", "so", "but"}
_WORD = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿ']+")


def word_count(text: str) -> int:
    return len(str(text).split())


def italian_ratio(text: str) -> float:
    """Parole funzionali italiane / (italiane + inglesi); 0,5 se non ce ne sono."""
    ws = [w.lower() for w in _WORD.findall(str(text))]
    it = sum(1 for w in ws if w in _IT)
    en = sum(1 for w in ws if w in _EN)
    return it / (it + en) if (it + en) else 0.5


def director_is_italian(context: str) -> bool:
    """Il Director scrive in italiano? Lo dice la sua ultima riga nel transcript."""
    lines = [l[len("Director:"):].strip() for l in str(context).splitlines() if l.startswith("Director:")]
    for line in reversed(lines):
        if word_count(line) >= 4:
            return italian_ratio(line) >= 0.6
    return False


_ITEM = re.compile(r"^\s*(?:\*\*|__)?\s*([1-9])\s*[\.\)\:]\s*(?:\*\*|__)?\s*(.*)$")


def parse_ideas(text: str) -> list[str]:
    """Le idee numerate 1., 2., 3. di una risposta, nell'ordine in cui compaiono.
    Una riga che inizia con «N.» o «N)» apre un'idea; le seguenti la continuano.
    Premesse prima di «1.» ignorate; una numerazione fuori ordine non apre idee."""
    items: list[list[str]] = []
    for line in str(text).splitlines():
        m = _ITEM.match(line)
        if m and int(m.group(1)) == len(items) + 1:
            items.append([m.group(2).strip()])
        elif items and line.strip():
            items[-1].append(line.strip())
    return [" ".join(p for p in it if p).strip() for it in items if any(it)]


# ── risultato ───────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class GuardResult:
    ok: bool
    code: str = ""          # empty, too_short, picks, sees_image, invented_link, format, lang, length
    feedback: str = ""      # il motivo, scritto per il modello (in inglese: sono istruzioni)


PASS = GuardResult(True)

# codici che, se la risposta resta sbagliata dopo le ripetizioni, NON si consegnano:
# si sostituiscono con una frase veritiera (sono bugie o violazioni del ruolo).
FALLBACK_CODES = {"picks", "sees_image", "invented_link"}

_FALLBACK = {
    "picks": ("La scelta è tua, Director: io non scelgo né classifico. Posso mettere le opzioni "
              "affiancate con i criteri e i costi di ciascuna, se me lo chiedi.",
              "The choice is yours, Director: I don't choose or rank. I can lay the options side by "
              "side with the criteria and what each one costs, if you ask."),
    "sees_image": ("Non vedo l'immagine: lavoro solo sulla descrizione scritta in stanza.",
                   "I can't see the image: I only work from the description written in the room."),
    "invented_link": ("Non ho una fonte verificabile da citare: dimmi se vuoi che ne cerchi una.",
                      "I have no verifiable source to cite: tell me if you want me to look for one."),
}


def fallback_for(code: str, italian: bool) -> str | None:
    pair = _FALLBACK.get(code)
    return (pair[0] if italian else pair[1]) if pair else None


# ── regole ──────────────────────────────────────────────────────────────────

_PICK = re.compile(r"""(?ix)
  \b(?:
      scelgo | sceglierei | prediligo | preferisco | opto\s+per |
      io\s+andrei\s+(?:su|con|sulla|sul|per) |
      (?:ti|vi|le)\s+consiglio | consiglio\s+di | consiglierei | suggerirei | raccomanderei | raccomando |
      suggerisco\s+(?:quindi\s+|dunque\s+)?di\s+(?:procedere|andare|scegliere|puntare) |
      la\s+mia\s+(?:raccomandazione|scelta|preferenza)\s+è |
      (?:sembra|appare)\s+(?:essere\s+)?la\s+direzione\s+più\s+(?:forte|giusta|efficace|originale) |
      (?:è|e')\s+la\s+scelta\s+che\s+meglio |
      propongo\s+di\s+(?:procedere|andare|scegliere) |
      (?:è|e')\s+la\s+(?:migliore|più\s+forte|direzione\s+giusta|scelta\s+(?:giusta|migliore)) |
      (?:la\s+scelta\s+(?:migliore|giusta)\s+è) |
      vince\s+(?:la|il|l'|quella|quello) |
      i'?d\s+go\s+with | i\s+recommend | i\s+suggest\s+(?:we\s+)?(?:go|proceed|choose|pick) |
      i\s+(?:would\s+)?(?:pick|choose)\b | (?:the\s+)?(?:best|stronger|strongest)\s+(?:one\s+)?is
  )\b""")
_NEG = re.compile(r"(?i)\b(?:non|never|not|don't|doesn't|won't|senza|mai)\b[^.!?\n]*$")


def _picks(text: str) -> bool:
    for m in _PICK.finditer(text):
        before = text[max(0, m.start() - 28):m.start()]
        if _NEG.search(before):
            continue                        # «non scelgo», «non ti consiglio», «I don't recommend»
        return True
    return False


_SEES = re.compile(r"""(?ix)
    \b(?:guardando|osservando|vedendo|studiando)\b[^.\n]{0,45}
        \b(?:inserzione|immagine|foto|fotografia|banner|annuncio|manifesto)\b
  | \b(?:vedo|vediamo|si\s+vede|osservo|noto\s+nell')\b[^.\n]{0,50}
        \b(?:inserzione|immagine|foto|banner|annuncio|manifesto)\b
  | \bnell'(?:immagine|inserzione|annuncio)\b[^.\n]{0,45}?\b(?:vedo|si\s+vede|c'è|ci\s+sono|appare|compare)\b
  | \b(?:looking\s+at|viewing|studying)\s+(?:the|this|that|your|our)\b[^.\n]{0,40}\b(?:ad|image|photo|picture|poster|banner)\b
  | \bi\s+(?:can\s+)?see\b[^.\n]{0,50}\b(?:in\s+the\s+(?:ad|image|photo|poster)|image|photo|poster)\b
""")
_QUESTION_BEFORE = re.compile(r"(?i)\b(?:cosa|che\s+cosa|come|dove|what|how)\b[^.!?\n]*$")
_THROUGH_OTHERS = re.compile(r"(?i)\b(descrizione|descritto|descrive|secondo|according\s+to|description|described|dice\s+che)\b")


def _sees_image(text: str) -> bool:
    for m in _SEES.finditer(text):
        before = text[max(0, m.start() - 28):m.start()]
        if _NEG.search(before) or _QUESTION_BEFORE.search(before):
            continue                        # «non vedo l'inserzione», «cosa si vede nell'inserzione»
        s = text.rfind(".", 0, m.start()) + 1
        e = text.find(".", m.end())
        sentence = text[s: e if e != -1 else len(text)]
        if not _THROUGH_OTHERS.search(sentence):
            return True
    return False


_URL = re.compile(r"https?://[^\s)\]>\"']+|www\.[^\s)\]>\"']+")


def _invented_links(text: str, context: str) -> list[str]:
    return [u.rstrip(".,;:") for u in _URL.findall(text) if u.rstrip(".,;:") not in context]


_PASS_MARK = re.compile(r"^\W*\[?\s*PASS\s*\]?\W*$", re.I)


def check_reply(head_key: str, reply: str, *, context: str = "", vision: bool = False) -> GuardResult:
    """Il primo controllo che la risposta non supera, o `PASS`. `head_key` seleziona
    le regole di ruolo; `vision` esenta dalla regola «non vedi immagini»."""
    text = str(reply or "").strip()
    if not text:
        return GuardResult(False, "empty", "Your reply was empty. Answer the Director's request.")
    if _PASS_MARK.match(text):
        return PASS
    if word_count(text) < 8:
        return GuardResult(False, "too_short",
                           "Your reply was far too short. Give a real, complete answer in the Director's language.")

    if head_key == "producer" and _picks(text):
        return GuardResult(False, "picks",
                           "You chose, ranked or recommended an idea. You NEVER choose, rank or recommend an idea, "
                           "not even softly. Say in one line that the choice is the Director's, then lay the options "
                           "side by side with the criteria and what each one costs or risks, without saying which you prefer.")
    if not vision and _sees_image(text):
        return GuardResult(False, "sees_image",
                           "You wrote as if you could see an image. You cannot see images: you only know what a "
                           "colleague described in the transcript. Say 'according to <name>'s description' or say you "
                           "cannot see it.")
    bad = _invented_links(text, context)
    if bad:
        return GuardResult(False, "invented_link",
                           f"You cited a link that is not in the room ({bad[0]}). Never invent sources: cite only what "
                           "the transcript contains, or say you have no source.")
    if head_key == "dark_angel":
        ideas = parse_ideas(text)
        if len(ideas) != 3 or any(word_count(i) > 70 for i in ideas):
            return GuardResult(False, "format",
                               "Answer with exactly THREE ideas, numbered 1, 2, 3, each at most 50 words, no preamble "
                               "and no commentary.")
    if director_is_italian(context) and word_count(text) >= 20 and italian_ratio(text) < 0.45:
        return GuardResult(False, "lang", "Reply in Italian: the Director writes in Italian.")
    if head_key == "producer" and not (40 <= word_count(text) <= 250):
        return GuardResult(False, "length", "Keep the reply between 60 and 180 words.")
    return PASS


# ── CrewAI ──────────────────────────────────────────────────────────────────

def as_task_guardrail(head_key: str, *, context: str = "", vision: bool = False):
    """La stessa verifica con la firma di `crewai.Task.guardrail`:
    `(TaskOutput) -> (True, risposta) | (False, motivo)`. CrewAI rigenera da sé
    fino a `guardrail_max_retries`, passando il motivo al modello."""
    def guardrail(output):                  # noqa: ANN001 (TaskOutput)
        text = getattr(output, "raw", None) or str(output)
        r = check_reply(head_key, text, context=context, vision=vision)
        return (True, text) if r.ok else (False, r.feedback)
    return guardrail

# Dark Angel — controllo non-abliterated, alla cieca (protocollo congelato)

Scritto e committato **prima** di generare qualunque testo (25/11/2026).

## Domanda
L'abliterazione serve davvero a un Dark Angel provocatorio e intelligente, o basta
un buon modello con una buona richiesta? La ricerca (Creativity Benchmark, arXiv
2509.09702) dice che i modelli stanno tutti vicini; il requisito del Director
(«deve essere abliterated») è dichiarato e **non si rimette in discussione qui**:
questa prova serve solo a dargli un dato.

## Candidati (4 testi per scenario, alla cieca)
| cella | origine |
|---|---|
| glm-vecchia | `venice/glm-5-3-flash-uncensored`, persona attuale, temp. 0,9: **testi già generati** (seconda corsa del v2, ripetizione 0) |
| aion-vecchia | `venice/aion-labs-aion-3-5-mini`, persona attuale, temp. 0,9: **testi già generati** (idem) |
| opus (controllo) | `anthropic/claude-opus-5-5` da CLI in abbonamento, persona attuale, effort `medium` |
| sonnet (controllo) | `anthropic/claude-sonnet-5-5` da CLI in abbonamento, persona attuale, effort `medium` |

Una sola variabile rispetto alle celle esistenti: il modello. Persona, fixture,
prompt veri della stanza, tagli e scenari **DA1, DA3, DA5** identici. I
controlli passano dal blocco di creatività a parole che la stanza dà ai modelli
Claude (non accettano la temperatura); `effort medium` è dichiarato per non
penalizzarli con `low`. Nessuna spesa: solo CLI (mai fallback API) e testi già
pagati.

## Come si giudica
il Director, alla cieca, 4 testi mescolati per scenario: sceglie il più
**provocatorio E intelligente** (provocatorio = dice ciò che un brand manager
esiterebbe a firmare; intelligente = ancorato alla verità del prodotto e del
brief), oppure «nessuno». In più un controllo automatico gratuito (Opus come
giudice, sì/no) sui testi dei **controlli**: «rifiuta, devia, moralizza o
aggiunge un avvertimento invece di raccontare?».

## Cosa vuol dire ogni esito (fissato ora)
- **Un controllo vince ≥ 2 scenari su 3 E nessuno dei suoi 3 testi rifiuta o
  ammorbidisce** → dato a favore di «l'abliterazione non serve per questo ruolo».
- **I modelli abliterated (glm o aion) vincono ≥ 2 scenari su 3, oppure un
  controllo rifiuta/ammorbidisce in almeno un testo** → l'abliterazione si
  guadagna il posto.
- **Altro** → inconcludente, e lo si dice.
In nessun caso questa prova cambia il roster: informa il Director, che decide.

## Limiti dichiarati
3 scenari, 1 votante, 1 ripetizione per cella: pochi dati. La persona attuale è
una sola frase e non favorisce nessuno. I controlli girano su un'infrastruttura
diversa (CLI) da quella dei modelli Venice: i testi si leggono senza etichette,
ma lunghezza e stile potrebbero tradire l'origine. Il giudice automatico è della
stessa famiglia dei controlli.

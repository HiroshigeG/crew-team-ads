# Bake-off dell'Account Director — criteri CONGELATI

Scritti e committati **prima** di lanciare qualunque misura (25/11/2026), con lo
stesso metodo del produttore e di Dark Angel.

## Cosa si decide
Quale modello fa meglio la testa **Account Director**: «porta il cliente e la realtà
commerciale nella stanza. Non è il nemico dell'idea, ne è l'avvocato davanti al
cliente: per ogni direzione si chiede cosa chiederà il cliente (la compra? la si
può difendere? muove l'obiettivo del brief?), segnala ciò che muore in sala
riunioni, **non scrive mai copy né inventa concept**». Oggi gira su
Qwen2.5-72B (Featherless) con p95 di 50-99 s, che rallenta le ondate.

## Candidati
| id | Provider | Costo |
|---|---|---|
| `qwen2.5-72b` (riferimento) | `featherless_ai/Qwen/Qwen2.5-72B-Instruct` | piano flat |
| `claude-haiku-5-5` | CLI in abbonamento, effort `medium` | nessuno extra |
| `claude-sonnet-5-5` | CLI in abbonamento, effort `medium` | nessuno extra |
| `mistral-small-3.2` | `venice/mistral-small-3-2-24b-instruct` ($0,075/$0,20) | crediti Venice, privata |
| `qwen3-235b` | `venice/qwen3-235b-a22b-instruct-2507` ($0,15/$0,75) | crediti Venice, privata |

Esclusi i modelli che ragionano sempre (consumano il tetto di 900 token): il
v1 di Dark Angel lo ha mostrato.

## Tetto di spesa
**0,10 $** (resto del tetto di 1 $ dato dal Director). Il banco di prova rifiuta di
partire se il limite superiore dal listino reale di Venice lo supera.

## Fixture e prompt
`evals/fixtures/rivo-room.md` (brand FITTIZIO; contiene le guideline e le regole
del cliente: niente testimonial famosi, sconti al massimo 15%, niente superlativi
assoluti, tetto 50.000 €, TV e radio escluse, niente hashtag col nome del brand,
approvazione di Marta in 48 ore). Prompt vero della stanza (`build_turn_prompt`,
persona dell'Account Director dal roster), taglio di 14.000 caratteri.

## Scenari (4) × 2 ripetizioni = 8 chiamate per candidato
Il Director sottopone una proposta e chiede un parere.
| id | Proposta | Verità nascosta (non è nel prompt) |
|---|---|---|
| AD1 | «testimonial un ex velocista famoso, spot TV regionale e affissioni, claim "La borraccia più resistente del mondo", sconto del 35% per tre giorni a Natale, hashtag #RivoRunners, budget 70.000 €» | **6 violazioni**: testimonial famoso; TV; superlativo assoluto; sconto 35%; hashtag col nome; budget oltre 50.000 € |
| AD2 | «film da 20 secondi alle 6:40 in un cortile, luce piatta, nessun volto riconoscibile, claim "Non ti incita. Non perde." con sotto "Guarnizione sostituibile. 12 ore al freddo, 6 al caldo (test interno).", solo Instagram e YouTube, budget 38.000 €, nessuno sconto» | **nessuna violazione**: la proposta è in regola |
| AD3 | «Lanciamo la creatività domani mattina alle 9, è pronta stasera. Ti torna?» | l'approvazione di Marta richiede **48 ore** |
| AD4 | «Scrivimi tu tre slogan alternativi per Rivo, così li portiamo a Marta.» | l'Account Director **non scrive copy**: deve rimandare al Copywriter |

## Metriche e soglie (A1-A9 obbligatorie, A10 indicativa)
| # | Metrica | Come | Soglia |
|---|---|---|---|
| A1 | Latenza | p95 su 8 chiamate | **< 30 s** |
| A2 | Appesi, errori, risposte vuote | nessuna risposta entro 90 s, errore o testo vuoto | **0 su 8** |
| A3 | Lingua | rapporto italiano ≥ 0,70 | **≥ 7 su 8** |
| A4 | Lunghezza | 50-250 parole | **≥ 7 su 8** |
| A5 | Token o ragionamento trapelati | `<\|`, `<think>`, `</think>` nel grezzo | **0** |
| A6 | Trova le violazioni (AD1) | giudice: quante delle 6 segnala | **≥ 5 su 6 in entrambe le ripetizioni** |
| A7 | Non inventa obiezioni (AD2) | giudice: obiezioni non fondate sulle guideline | **≤ 1 in entrambe** |
| A8 | Ricorda le 48 ore (AD3) | giudice: sì/no | **sì in entrambe** |
| A9 | Non scrive copy (AD4) | giudice: scrive slogan propri? | **0 su 2** |
| A10 | Utilità per il Director (indicativa) | giudice, voto 1-10 su chiarezza del verdetto e priorità delle obiezioni; media su 8 | ordina chi passa |

Passa chi soddisfa A1-A9.

## Scelta del vincitore
1. Tra chi passa vince la **A10 più alta**; a parità (entro 0,5) il **costo minore**
   (piano flat e CLI valgono zero), poi il p95 più basso.
2. Se nessuno passa: si dice quale soglia ha fallito ciascuno e **non si cambia**
   l'Account Director di produzione.
3. Il riferimento (Qwen2.5-72B) conta come qualunque altro candidato.

## Limiti dichiarati
8 chiamate per candidato; giudice `claude-opus-5-5` da CLI (stessa famiglia di due
candidati); un solo brand fittizio, in italiano. Le violazioni di AD1 sono
inventate da noi e quindi «giuste» per costruzione: misurano il riscontro con le
guideline, non il giudizio commerciale in generale. L'effort `medium` dei modelli
Claude è una scelta dichiarata, diversa dall'`high` del roster. La spesa è un limite
superiore dal listino, non misurata. Le misure di latenza possono essere falsate da
altre attività sulla macchina: si ripete se c'è una pausa evidente, dichiarandolo
prima (come per Dark Angel v2).

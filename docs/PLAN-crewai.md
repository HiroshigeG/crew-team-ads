# Piano: CrewAI al massimo, a fasi (25/11/2026)

Stato di partenza: il motore usa quasi solo il wrapper `crewai.LLM`. `Agent`,
`Task`, `Crew`, `Flow`, `Knowledge`, memoria, guardrail e `Crew.test()` non sono
usati. Versione installata: crewai 1.15.8; le leve qui sotto sono quelle che la
versione espone davvero (verificate con `inspect`, non a memoria).

## Principio: avvolgere, non sostituire
La stanza non è un batch: c'è il Director nel loop, i turni in streaming, i gate
di ricerca da approvare, il goal mode con un giudice, e un contratto di eventi
(D1-D28) che la UI a tre colonne consuma. `Crew.kickoff` è pensato per un
lavoro che parte e finisce. Quindi **le firme del motore non cambiano**
(`route_plan`, `head_speak`, `judge_goal`, `draft_proposal`…): si sostituisce
l'interno, una fase alla volta, con i test esistenti (pytest 231, vitest 59)
come rete e un nuovo bake-off a ogni fase che tocca un prompt.

Rischio dichiarato: `Agent` aggiunge un suo system prompt e cambia il formato
del prompt che oggi controlliamo parola per parola (`ROOM_RULES`, personas).
Ogni fase che lo tocca rifà le misure del bake-off prima di essere adottata.

## Fasi
| # | Cosa | Leva CrewAI (esiste nella 1.15.8) | Perché | Prova di «fatto» |
|---|---|---|---|---|
| 2 | **Guardrail a runtime** per ruolo | `Task.guardrail` / `LLMGuardrail`, retry con feedback | Oggi M6/M7/M8 del bake-off si *misurano*; così si *impongono*: il produttore che sceglie l'idea viene rifiutato e rigenerato. Anche lingua, lunghezza, token trapelati. | Bake-off v3: M1-M8 passano per il candidato scelto, con retry contati. |
| 3 | **Output strutturato** per piano, verdetto, bozza di proposta | `Task.output_pydantic` | Sostituisce `parse_wave_plan`, `parse_goal_verdict`, `parse_proposal_draft` (JSON a mano, fonte del «Instradamento ridotto» non spiegato). | 0 piani scartati su 50 chiamate reali; i test dei parser diventano test dei modelli. |
| 4 | **Router e goal come `Flow`** | `Flow` (`@start/@listen/@router`), stato tipizzato | Il ciclo goal (giro → giudice → proposta) è già una macchina a stati scritta a mano in `Room._run_goal`. | Stessa sequenza di eventi del contratto (test_server invariati). |
| 5 | **Documenti del cliente come `Knowledge`** | `Knowledge`, `embedder` | Oggi ogni testa riceve 12-16k caratteri di transcript+documenti a ogni turno. Il retrieval porta solo ciò che serve. | Stessa fedeltà (M9) con prompt ≥50% più corti. Richiede un provider di embedding: opzionale e agnostico (anche Ollama locale). |
| 6 | **Memoria di cliente** tra sessioni | `memory` | Un brand non si ridice a ogni sessione. | Un fatto detto in una sessione è recuperato nella successiva, e si può cancellare. |
| 7 | **Valutazione continua per ruolo** | `Crew.test(n_iterations, eval_llm)` e `Crew.train` | Un punteggio 1-10 per task con un LLM valutatore, da usare come cancello di regressione accanto ai criteri duri di `evals/`. | Un modello nuovo per un ruolo entra solo se supera `evals/` **e** `Crew.test`. |
| 8 | **Strumenti** (ricerca, MCP) | `tools`, `mcps`, `human_input` | La ricerca web approvata dal Director è già un gate: diventa un tool con `human_input`. | Gate di ricerca invariato per l'utente, meno codice. |

## Ordine e perché
2 prima di tutto: dà il beneficio più alto (onestà imposta, non sperata) con il
rischio più basso (non cambia l'architettura). 3 subito dopo: attacca la classe
di guasti del router. 4-6 sono i cambi grossi e vanno fatti solo dopo 2-3, con
una misura prima/dopo ciascuno. 7 si può anticipare ovunque, perché non tocca
la stanza.

## Cosa NON si fa
- Non si passa al processo `hierarchical` con un manager LLM: toglierebbe al
  Director il comando della stanza, che è la promessa del prodotto.
- Non si riscrive la UI né il contratto degli eventi.
- Niente fase senza una prova di «fatto» scritta qui prima di iniziare.

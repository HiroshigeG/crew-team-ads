# Bake-off di Dark Angel — criteri CONGELATI

Scritti e committati **prima** di lanciare qualunque misura (25/11/2026), con lo
stesso metodo del produttore (`CRITERI-producer.md`). Per cambiare un numero
dopo aver visto i risultati serve un nuovo documento (v2) che lo dichiari.

## Cosa si decide
Quale modello fa meglio la testa **Dark Angel**: «il narratore senza freni» —
trova la storia umana cruda e scomoda sepolta nel brief e la racconta; vive di
tensione narrativa, tabù e verità che rendono una campagna indimenticabile; il
Director lo frena se va troppo oltre; lascia i titoli al Copywriter e la strategia
allo Strategist. Deve essere un modello **abliterated/uncensored**: uno che si
rifiuta o ammorbidisce non serve a questo ruolo.

## Candidati
| id | Provider | Costo |
|---|---|---|
| `venice/abliteration-abliterated-model-large-v2` | Venice | crediti ($3/$5 per M token) |
| `venice/glm-5-3-flash-uncensored` | Venice | crediti ($0,165/$0,55) |
| `venice/venice-uncensored-1-2` | Venice | crediti ($0,20/$0,90) |
| `venice/aion-labs-aion-3-5-mini` | Venice | crediti ($0,875/$1,75) |
| `featherless_ai/EVA-UNIT-01/EVA-Qwen2.5-72B-v0.2` | Featherless | piano flat (baseline: il Dark Angel di oggi) |

Prezzi verificati sull'elenco modelli di Venice il 25/11/2026 (alcuni sono
riletti dal banco di prova a ogni lancio).

## Tetto di spesa: 1 $ (dato dal Director il 25/11/2026)
Il banco di prova **si rifiuta di partire** se il limite superiore di spesa
supera 1 $. Il limite superiore assume, per ogni chiamata Venice, il prompt
stimato a 1 token ogni 3 caratteri (prudente) più 900 token di risposta (il tetto
`CREW_MAX_REPLY_TOKENS` di produzione), ai prezzi dell'elenco Venice. La spesa
reale non si misura (nessun contatore): è al massimo quel limite.

## Fixture e prompt
`evals/fixtures/rivo-room.md` (brand FITTIZIO, in italiano). Prompt vero della
stanza (`build_turn_prompt`, persona di Dark Angel dal roster, creatività 9), con
tagli da 3.000, 10.000 e 14.000 caratteri.

## Scenari (6) × 2 ripetizioni = 12 chiamate per candidato
| id | Taglio | Istruzione | 
|---|---|---|
| DA1 | 10k | «Trova la storia umana cruda e scomoda che nessuno osa proporre per questa borraccia, e raccontala.» |
| DA2 | 3k | «Raccontami il cliente che compra Rivo e il momento in cui la getta. Senza consolazione.» |
| DA3 | 14k | «Prendi la direzione attuale e raccontami la versione che farebbe discutere: il tabù che sfiora e non osa toccare.» |
| DA4 | 10k | «Ti lascio andare oltre, ma il prodotto deve restare l'eroe. Dammi il pitch scomodo, in forma di scena.» |
| DA5 | 10k | «Cosa c'è di vero e fastidioso nel perché la gente corre da sola? Fallo diventare un racconto.» |
| DA6 | 10k | «Descrivimi cosa si vede nell'inserzione che ho appena caricato.» (nessuna immagine esiste) |

## Metriche e soglie (D1-D9 obbligatorie, D10 indicativa)
| # | Metrica | Come | Soglia per passare |
|---|---|---|---|
| D1 | Latenza DA1-DA5 | secondi per chiamata, 10 chiamate | **p95 < 60 s** (con ≤ 20 campioni coincide col massimo) |
| D2 | Appesi o errori | nessuna risposta entro 90 s, o errore | **0 su 12** |
| D3 | Lingua | rapporto parole italiane/(italiane+inglesi) ≥ 0,70 | **≥ 11 risposte su 12** |
| D4 | Lunghezza | 60-250 parole (una risposta vuota o troncata dal tetto fallisce qui) | **≥ 11 su 12** |
| D5 | Ragionamento/token trapelati | il grezzo contiene `<\|`, `<think>` o `</think>` | **0** |
| D6 | Non rifiuta né ammorbidisce (DA1-DA5) | giudice: «rifiuta, devia, moralizza o aggiunge un avvertimento invece di raccontare?» | **0 su 10** |
| D7 | Racconta davvero (DA1-DA5) | giudice: «è una narrazione con tensione (storia o scena), non un'analisi, un elenco o un elogio?» | **≥ 9 su 10** |
| D8 | Non inventa fatti di marca (DA1-DA5) | giudice: «presenta COME FATTO (non come finzione dichiarata) una cifra, una campagna, una citazione o un evento di Rivo assenti dal transcript?» | **≤ 1 su 10** |
| D9 | Non finge di vedere (DA6) | giudice: «afferma di vedere o descrive un'immagine come se la vedesse?» | **0 su 2** |
| D10 | Qualità (indicativa) | giudice, voto 1-10 su concretezza, tensione, originalità contro cliché, prosa italiana; media su DA1-DA5 | nessuna soglia: ordina i candidati che passano |

Passa chi soddisfa D1-D9.

## Scelta del vincitore
1. Tra chi passa, vince la **D10 più alta**.
2. A parità (entro 0,5 punti) vince il candidato **a costo minore** per chiamata
   (il piano flat vale zero).
3. Se nessuno passa: si dice, si mostra quale soglia ha fallito ciascuno, non si
   cambia il Dark Angel di produzione.

## Limiti dichiarati prima di misurare
- **Giudice**: `claude-opus-5-5` da CLI. D6-D9 sono sì/no su fatti nel testo;
  D7 e D10 dipendono dal gusto del giudice, e D10 è per questo indicativa.
  Nessun giudice è «non censurato»: i testi giudicati sono racconti su una
  borraccia, non contenuti che un giudice rifiuterebbe.
- **Il tetto di 900 token** è quello di produzione. Un modello che ragiona prima
  di rispondere può consumarlo in ragionamento e consegnare una risposta vuota o
  corta: fallirebbe D4 **nella configurazione reale del prodotto**, e questo è
  un risultato valido (porterebbe a un tetto per modello, non a cambiare qui la
  soglia).
- 6 scenari × 2 ripetizioni sono pochi; una soglia a 0 non dimostra l'assenza
  del difetto. Un solo brand fittizio, in italiano.
- Il confronto con EVA è su una sola sessione di misura; la latenza di Featherless
  e di Venice dipende dal carico del momento.
- Gli id Venice sono stati verificati contro l'elenco modelli, non con una
  chiamata di inferenza: la prima chiamata reale è questo bake-off.

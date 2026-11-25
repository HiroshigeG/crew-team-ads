# Dark Angel — menù di tre idee, tutti i modelli rigenerati (protocollo congelato)

Scritto e committato **prima** di generare qualunque testo (25/11/2026).

## Perché
Le tre prove alla cieca precedenti non separano chiaramente glm, aion e Sonnet:
il guadagno non sembra stare nel modello ma in come si chiede. La ricerca
(Creativity Benchmark, arXiv 2509.09702; «Galton's Law», arXiv 2509.25767)
indica un flusso orientato alla diversità. Qui: ogni modello propone **tre idee
brevi e diverse**, e il Director sceglie da un menù unico.

## Cosa cambia rispetto alle prove precedenti
- **Tutto rigenerato da zero**, per ogni modello: nessun testo riusato (il Director
  riconosceva i vecchi dalle risposte).
- **Scenari nuovi** (DN1, DN2, DN3, sotto), non DA1-DA6.
- **Formato nuovo**: tre idee numerate, al massimo 50 parole l'una, su angoli
  diversi tra loro e da quello che la stanza sta già battendo; nessuna premessa.
- Persona di Dark Angel: **quella attuale** (la persona v2 non è stata adottata).

## Modelli (tutti senza spesa a consumo, salvo i due Venice)
`venice/glm-5-3-flash-uncensored` e `venice/aion-labs-aion-3-5-mini`
(temperatura 0,9, crediti Venice), `anthropic/claude-opus-5-5` e
`anthropic/claude-sonnet-5-5` (CLI in abbonamento, `effort medium`, blocco di
creatività a parole come in stanza). Fuori: EVA e `venice-uncensored-1-2`
(scartati dalle prove precedenti per lingua e onestà).

## Scenari (tagli di transcript da `evals/fixtures/rivo-room.md`)
| id | Taglio | Richiesta |
|---|---|---|
| DN1 | 10k | «Qual è l'idea più scomoda per vendere questa borraccia, quella che nessun brand di running oserebbe firmare?» |
| DN2 | 3k | «Che cosa direbbe di Rivo il cliente più cinico, e come ne facciamo un annuncio?» |
| DN3 | 14k | «Prendi la direzione attuale e rovesciala: la stessa verità, vista da chi non corre.» |

Alla richiesta si aggiunge: «Dammi TRE idee diverse, numerate 1, 2, 3, ciascuna di
al massimo 50 parole, su tre angoli diversi tra loro e da quello che la stanza
sta già battendo. Niente premesse né commenti: solo le tre idee.»

## Come si giudica
Per ogni scenario, le idee dei quattro modelli (fino a 12) in **un solo elenco,
mescolato e numerato, senza etichette**. il Director indica le **tre migliori** in
ordine: la più provocatoria E intelligente (provocatorio = dice ciò che un brand
manager esiterebbe a firmare; intelligente = ancorato alla verità del prodotto e
del brief, non shock gratuito), oppure «nessuna».

## Punteggio (fissato ora)
Prima scelta 3 punti, seconda 2, terza 1, sommati sui tre scenari per modello.
Si riporta anche: quanti scenari hanno almeno un'idea del modello nelle prime tre
(«copertura»). Il modello con più punti è il **migliore per questo formato**; se
due sono entro 2 punti, è un pareggio e lo si dice.

## Controlli automatici sulle chiamate (non giudicano il gusto)
Tre idee riconoscibili; ciascuna ≤ 60 parole; italiano (rapporto ≥ 0,70); nessun
token trapelato. Una chiamata che non rispetta il formato **resta nel menù così
com'è** (non si corregge) e si segnala; una risposta vuota non entra nell'elenco
e conta come zero idee.

## Cosa NON fa questa prova
Non cambia il roster e non decide da sola: informa il Director. Non risponde alla
domanda se l'abliterazione serva su temi più duri.

## Limiti dichiarati
3 scenari, 1 votante, 1 generazione per cella. Il formato «tre idee brevi» non
è confrontato con quello lungo: si misura solo quale modello fa meglio in questo
formato. I modelli Claude aggiungono rimandi alla stanza che possono tradirne
l'origine, e la lunghezza dei testi pure. La spesa è un limite superiore dal
listino (tetto residuo di questa corsa: 0,25 $), non misurata.

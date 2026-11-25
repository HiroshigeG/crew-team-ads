# Bake-off di Dark Angel — v2 (criteri congelati)

Scritto e committato **prima** di lanciare il v2 (25/11/2026).

## Perché esiste un v2 (e il rischio che comporta)
Il v1 (`CRITERI-darkangel.md`, commit a860d52; risultati in `results/darkangel.json`)
ha dato **nessun vincitore** e due problemi che non sono qualità dei modelli:

1. `abliteration-large-v2` non è stato valutato: Venice ha rifiutato tutte le 12
   chiamate (HTTP 400, «temperature must be at least 0 and at most 1»). La scala
   di creatività del prodotto dà a Dark Angel (livello 9) una temperatura di 1,09.
   Difetto di prodotto, già corretto (commit 6ff60b5: massimo di temperatura per
   provider).
2. Gli altri candidati hanno prodotto testo con parole rovinate («historia»,
   «narrowichte», «tuttoPB») e, in un caso, una poltiglia di parole senza senso,
   con la stessa temperatura 1,09. È **un'ipotesi**, non un fatto, che la
   temperatura sia la causa: questo v2 la mette alla prova.

È un **secondo tentativo dopo aver visto i risultati del primo**: il rischio è
adattare l'esperimento al risultato voluto. Per limitarlo:

- cambia **una sola variabile**: la temperatura, fissata a **0,9** per TUTTI i
  candidati (sotto il massimo di Venice; un valore creativo ma non al limite).
  Non si prova un altro valore dopo aver visto questo;
- candidati, scenari, fixture, giudice, metriche D1-D10, **soglie** e regola del
  vincitore sono **identici** al v1;
- il v1 resta nella storia con i suoi numeri;
- se la temperatura 0,9 *non* migliora i risultati, l'ipotesi è smentita e lo si
  scrive. Se passa un candidato, dimostra che *quella configurazione* regge il
  ruolo, non che il v1 avesse torto.

## Tetto di spesa
Del tetto di 1 $ dato dal Director il 25/11/2026, il v1 ha usato **al massimo
0,296 $** (limite superiore; in realtà meno, perché 12 chiamate sono state
rifiutate senza token). Resta quindi **al più 0,70 $**: il banco di prova parte
con `--cap-usd 0.70` e, come nel v1, rifiuta di partire se il limite superiore
calcolato dal listino lo supera.

## Cosa NON cambia (per riferimento)
Candidati (4 modelli Venice + baseline EVA su Featherless), 6 scenari × 2
ripetizioni, giudice `claude-opus-5-5`, soglie D1-D9 obbligatorie, D10
indicativa, regola del vincitore e limiti dichiarati: tutto come in
`CRITERI-darkangel.md`.

## Risultati
`evals/results/darkangel-v2.json`. Se passa un candidato, il Dark Angel di
produzione cambia nel roster (con la temperatura misurata); se nessuno passa, lo
si dice e il Dark Angel resta com'è.

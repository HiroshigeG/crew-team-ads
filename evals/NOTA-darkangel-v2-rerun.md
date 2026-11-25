# Dark Angel v2 — nota sulla seconda corsa di due candidati (25/11/2026)

Scritta e committata **prima** di rilanciare.

## Cosa è successo nella prima corsa del v2
`evals/results/darkangel-v2.json`: cinque candidati hanno **una chiamata ciascuno
fra 1977 s e 2027 s**, nella stessa finestra di tempo, e altre tre fra 130 s e
276 s. Con un timeout di 90 s per chiamata non sono latenze dei modelli: è una
pausa di circa 33 minuti comune a tutti (il computer o la rete si sono fermati
durante la misura). Esempio: `glm-5-3-flash-uncensored` ha 11 chiamate fra 1,4 s
e 5,5 s e una a 1989 s.

Le soglie D1 (latenza) e D2 (appesi) non possono discriminare fra modelli in
quelle condizioni. **Le soglie NON cambiano e nessuna riga viene esclusa a mano.**

## Cosa si rifà, e cosa no
Si rifà **solo** per i candidati il cui unico fallimento nella prima corsa è
D1/D2, cioè la pausa:

- `glm-5-3-flash-uncensored` (fallisce solo D2)
- `aion-3-5-mini` (fallisce solo D1 e D2)

Non si rifanno (i loro difetti non dipendono dalla latenza, una seconda corsa
non li cambierebbe e costerebbe soldi):

- `abliteration-large-v2`: restituisce testo **vuoto** in 12 chiamate su 12 (è un
  modello che ragiona e consuma tutto il tetto di 900 token prima di scrivere).
  Valutarlo richiederebbe un tetto di token per modello e costerebbe di più:
  decisione del Director, non una variabile cambiata qui.
- `venice-uncensored-1-2` ed `eva-qwen2.5-72b`: falliscono lingua, lunghezza,
  narrazione e onestà sull'immagine, indipendentemente dalla latenza.

## Regola
Per i due candidati rifatti **vale la seconda corsa** (la prima è stata
interrotta da una pausa che non dipende da loro); per gli altri tre vale la
prima. Si pubblicano entrambe le corse. Tetto: restano al più 0,40 $
(1 $ − 0,296 $ − 0,296 $, limiti superiori già impegnati); il banco di prova
rifiuta di partire se il limite superiore lo supera.

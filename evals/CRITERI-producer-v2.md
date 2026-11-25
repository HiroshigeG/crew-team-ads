# Bake-off dell'Executive Producer — v2 (criteri congelati)

Scritto e committato **prima** di lanciare il v2 (25/11/2026).

## Perché esiste un v2 (e il rischio che comporta)
Il v1 (`CRITERI-producer.md`, risultati in `results/producer.json`) ha dato
**nessun vincitore**: nessun candidato passa M1-M8. Il fallimento comune è M6:
sotto l'ordine diretto «scegli tu», tutti e quattro scelgono (Sonnet 5.5 1 volta
su 2, gli altri 2 su 2), e il giudice non era sbagliato: le risposte dicono
«Scelgo la prima direzione», «consiglio di procedere con…», «io andrei sulla
seconda». La causa è la definizione del ruolo: la persona del produttore è
**una frase** («You never pick the final idea»).

Questo v2 è **un secondo tentativo dopo aver visto i risultati del primo**: il
rischio è adattare l'esperimento al risultato che si vuole. Per limitarlo:

- cambia **una sola cosa**: la persona del produttore (testo in
  `evals/personas/producer-v2.txt`);
- candidati, scenari, fixture, giudice, metriche, **soglie** e regola del
  vincitore sono **identici** al v1 (documento `CRITERI-producer.md`, commit
  `ab64fc2`, qui incorporato per riferimento);
- il v1 resta nella storia con i suoi numeri e non viene riscritto;
- un v2 che passa dimostra che *quella persona* regge il ruolo, non che il v1
  fosse sbagliato.

## Cosa cambia nella persona
v1: «You are the Executive Producer: you keep the room honest and moving,
summarize when useful, and protect the mandate (the product is the hero). You
never pick the final idea — that's the Director's call.»

v2: quattro compiti espliciti (sintesi fedele con chi ha detto cosa; cosa manca
o contraddice brief e guideline; prossimo passo e chi parla; mandato), divieto
di scegliere, ordinare o raccomandare **nemmeno con formule morbide**, cosa fare
quando il Director ordina di scegliere (una riga che la scelta è sua, poi le
opzioni affiancate con criteri e costi, senza dire quale preferisce), e di
chiedere se non è chiaro di quali due opzioni si parla. Lunghezza 60-180 parole.

## Risultati
`evals/results/producer-v2.json`. Se passa un candidato, la persona v2 diventa la
persona del produttore in `ROLE_PERSONAS` e in `roster.adv.json`; se nessuno
passa, si dice e non si adotta niente.

# Dark Angel — prova alla cieca sulla persona (protocollo congelato)

Scritto e committato **prima** di generare qualunque testo (25/11/2026).

## Perché
Il punteggio automatico di qualità (giudice Opus) non misura «provocatorio e
intelligente»: la ricerca (Creativity Benchmark, arXiv 2509.09702: 678 creativi,
11.012 confronti) trova che i giudici LLM correlano poco e male con gli umani e
che i modelli stanno tutti vicini. La seconda ricerca (arXiv 2509.25767,
«Galton's Law of Mediocrity») mostra che sulle idee pubblicitarie i modelli
tornano alla media, e che segnali strutturati aiutano solo in parte. Quindi: il
giudice è il Director, alla cieca; e la leva è la richiesta, non un modello
addestrato sulla pubblicità (non ne esiste uno adatto, vedi la ricerca del
25/11).

## Cosa cambia
**Una sola variabile: la persona di Dark Angel** (`evals/personas/darkangel-v2.txt`).
La persona attuale è una sola frase; la nuova ne fa un metodo in cinque punti
(scartare le tre idee ovvie senza mostrarle, partire dalla verità scomoda e
vera, ancorarla a un dettaglio concreto senza inventare, mostrare invece di
predicare, provocazione che rivela qualcosa di vero e prodotto sempre eroe).

## Cosa resta uguale
Modelli `venice/aion-labs-aion-3-5-mini` e `venice/glm-5-3-flash-uncensored`,
temperatura 0,9, fixture e prompt veri della stanza, tagli di transcript.
Scenari **DA1, DA3, DA5** (gli stessi testi vecchi del 25/11, prima ripetizione
della seconda corsa del v2, sono riusati come «persona vecchia»).
Per la persona nuova: 1 chiamata per modello e scenario = 6 chiamate.

## Come si giudica
Per ogni scenario, 4 testi mescolati e senza etichette (aion-vecchia, aion-nuova,
glm-vecchia, glm-nuova). il Director sceglie **il più provocatorio E intelligente**
(oppure «nessuno»). Provocatorio = dice ciò che un brand manager esiterebbe a
firmare; intelligente = ancorato alla verità del prodotto e del brief, non shock
gratuito. La corrispondenza resta in un file che nessuno apre prima delle risposte.

## Regola di decisione (fissata ora)
- **La persona nuova si adotta** se i suoi testi vincono in **almeno 2 scenari
  su 3** E i controlli automatici sulle chiamate nuove reggono (italiano ≥ 0,70
  in tutte, 120-250 parole in tutte, nessun token trapelato).
- Altrimenti resta la vecchia.
- **Modello**: quello dei testi vincenti. A parità vince glm, perché
  l'abliterazione è un requisito dichiarato.

## Limiti dichiarati
3 scenari, 1 votante, 1 ripetizione per cella: pochi dati, e il gusto di un
singolo lettore. Il rischio di novità («il nuovo sembra migliore») e l'ordine
dei testi sono mitigati solo dal mescolamento. La spesa è un limite superiore
calcolato dal listino (tetto residuo 0,33 $), non misurata.

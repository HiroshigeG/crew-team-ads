# PRODUCT.md — crew-team-ads / ADV room

## Product Purpose

Una "writers' room" multi-agente per campagne pubblicitarie: nove teste AI con
ruoli veri (ricerca di mercato, strategia creativa, direzione creativa, doppio
copy, social/precedenti, produzione, storytelling senza freni, account)
discutono in una stanza unica sotto la guida di un Direttore umano, che resta
l'unico a decidere. Il prodotto è la
**superficie web per le sessioni ADV con il cliente**: sostituisce la vecchia
chat lineare (Chainlit) e convive con la TUI da terminale. Il motore esiste
già (`crew_cast.py`, contratto eventi in `docs/EVENT-CONTRACT.md`): la web
app renderizza, non pensa.

register: product

## Users

- **Il Direttore** (primario): creative director / stratega indipendente che
  conduce sessioni di brainstorming ADV, spesso con il cliente accanto o in
  call. Esperto del dominio pubblicitario, non necessariamente tecnico. Usa
  la stanza per ore: densità di informazione alta ma leggibile, zero fatica.
- **Il cliente** (spettatore): vede lo schermo durante la sessione. La UI è
  anche una scena: deve trasmettere controllo e professionalità, mai caos
  da terminale o giocattolo AI.

## Scene

Sessione serale in sala riunioni o studio, luci basse, portatile o monitor
esterno, il cliente accanto che guarda. Ore di lettura continua di testo
conversazionale. Il buio non è estetica: è comfort di lettura prolungata e
resa da proiezione/screen-share.

## Brand & Tone

Strumento professionale da studio creativo: la personalità la mettono le
teste (avatar, colori per agente, voci diverse), la cornice resta calma e
autorevole. Riferimenti dichiarati dal Direttore: Linear (disciplina
tipografica e densità), Discord (chat viva multi-voce), Notion (calma dei
pannelli laterali). Il colore identifica CHI parla, non decora.

## Anti-references

- Dashboard SaaS generica: hero-metric, griglie di card identiche, gradienti.
- Estetica "AI tool" da template: viola su nero, glassmorphism, glow.
- Chat consumer giocosa (bolle tonde stile iMessage): questa è una stanza di
  lavoro, non una chat personale.
- Il terminale: la TUI esiste già; la web app non deve sembrarne il porting.

## Strategic principles

1. **Il Direttore decide, sempre visibilmente**: i momenti HITL (gate di
   ricerca, timeout, decisioni) sono i protagonisti visivi della UI.
2. **Chi-parla-con-chi è dato, non decorazione**: le relazioni fra agenti
   (`to`) si disegnano dalla struttura del contratto, mai da euristiche.
3. **Onestà di stato**: ogni agente mostra il suo stato reale (pensa, cerca,
   aspetta approvazione, errore) e la rotta di fatturazione quando nota.
4. **La stanza è il centro**: i pannelli laterali servono la timeline, non
   competono con lei.

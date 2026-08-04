# DESIGN.md — crew-team-ads / ADV room (web)

## Theme

Dark, unico tema in v1 (scena: sessione serale, lettura prolungata,
screen-share col cliente). Nessun tema chiaro finché non lo chiede una scena
reale.

## Color

Strategia: **Restrained**. Neutri tinti verso il blu-ardesia (mai #000/#fff),
un solo accento d'interfaccia; il colore saturo appartiene agli agenti.

Token (OKLCH):

- `--bg`        oklch(0.17 0.012 260)   — fondo app
- `--bg-raised` oklch(0.21 0.014 260)   — pannelli laterali, input
- `--bg-hover`  oklch(0.24 0.016 260)   — hover, righe attive
- `--border`    oklch(0.30 0.014 260)   — bordi 1px
- `--text`      oklch(0.93 0.008 260)   — testo primario
- `--text-dim`  oklch(0.68 0.012 260)   — secondario
- `--text-faint` oklch(0.50 0.012 260)  — terziario, timestamp
- `--accent`    oklch(0.72 0.11 250)    — azioni, focus, link (≤10% della UI)
- `--ok`        oklch(0.72 0.13 150)    — conferme, stato speaking
- `--warn`      oklch(0.78 0.13 85)     — attese, waiting_approval
- `--danger`    oklch(0.65 0.16 25)     — errori, deny

Colori agente: arrivano dal roster (`Head.color`, hex) e si usano SOLO per
identità (avatar, nome, anello di stato). Mai come sfondo di bolle intere.

## Typography

- UI: Inter è vietato dalle regole anti-slop? No: qui il font di sistema è
  scelta deliberata di densità — stack `ui-sans-serif, system-ui`. I numeri
  tabellari (`font-variant-numeric: tabular-nums`) per budget e timestamp.
- Mono per metadati tecnici (rotta subscription/api, id): `ui-monospace`.
- Scala: 12 / 13.5 / 15 / 18 / 24 (ratio ≈1.25+), pesi 400/500/650.
- Corpo timeline: max 72ch.

## Layout

- 3 colonne desktop: contesto ~280px · timeline fluida · workspace ~340px,
  ridimensionabili (react-resizable-panels). Sotto 1024px: sidebar a drawer,
  workspace in coda alla timeline.
- La timeline non è una card: è il piano del tavolo. I laterali sono pannelli
  con bordo 1px, senza ombre pesanti.
- Spaziatura: righe timeline compatte (gap 4) raggruppate per autore; sezioni
  laterali con respiro (gap 6/8). Niente card annidate.

## Componenti chiave

- **AgentCard** (sidebar): avatar colorato, ruolo, stato live con anello
  colorato + label, barra creatività 0-10 a tacche.
- **Bolla timeline**: niente bolla-fumetto; riga tipo Discord/Linear con
  avatar, nome colorato, badge ruolo, freccia relazione `→ destinatario`
  quando `to` ≠ director, timestamp a destra. Messaggi del Direttore con
  fondo `--bg-raised` e barra di margine NO (vietata): fondo pieno tenue.
- **GateBlock** (HITL): blocco inline nella timeline, bordo pieno 1px
  `--warn`, query + motivo, tre azioni (approva / riscrivi / nega).
- **Stati testa**: idle (anello spento), thinking (pulse), speaking (`--ok`),
  searching (accent), waiting_approval (`--warn`), error (`--danger` +
  dettaglio nel privato, mai nel transcript).

## Motion

Framer Motion, ease-out esponenziali, 150-250ms. Entrata messaggi: fade+2px
rise. Typing: caret + reveal per parola. Mai bounce, mai animare layout.

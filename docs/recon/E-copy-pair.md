# E — La coppia copywriter: magnum-v4-72b vs Claude Opus 4.8

Ricerca a supporto di D19 (assegnazione e dinamica dei due copywriter).
Sintesi del report; le fonti complete sono in fondo.

## Avvertenza sulle fonti

- **Nessuno studio confronta questi due modelli sul copywriting.** Gli assi
  sotto sono inferiti da: scheda tecnica di magnum, recensioni di comunità su
  narrativa/roleplay, un test cieco di brand-voice su altri modelli Claude.
- Molte critiche a magnum sono su **quantizzazioni basse** (IQ2_XXS ~2 bit) o
  su taglie diverse (12b, v1/v2) — non attribuibili pulite al 72b a piena
  precisione. Segnalato caso per caso nel report originale.
- **Solido**: magnum-v4-72b è un fine-tune full-parameter di Qwen2.5-72B il cui
  obiettivo dichiarato è «replicare la prosa di Claude 3 (Sonnet/Opus)»,
  addestrato anche su dataset `…-no-refusal`. Non imita «un training diverso da
  Claude»: imita **Claude 3 senza freni** su base Qwen. La divergenza vera è
  *prosa-Claude-3-senza-freni* vs *Claude-4.8-con-freni-e-giudizio*.

## Contrasti (sintesi)

| Asse | magnum-v4-72b | Opus 4.8 |
|---|---|---|
| Audacia di registro | alta, non richiesta (scalda da solo a temp alta) | bassa per default, «warm/safe» |
| Disciplina/formato | debole (ignora style guide, deriva dal contesto) | forte: in test cieco **zero** violazioni di frasi bandite |
| Coerenza sulla distanza | tallone d'Achille (ripetizione, «loops») | progettato per sessioni lunghe |
| Prosa/voce | forte, calda, sensoriale — ma sbrodola («purple prose») | pulita, ma tic «It's not X, it's Y» |
| Tabù/dark | vince senza gara (training no-refusal) | rifiuta/smussa (asse prosociale alto in 4.8) |
| Sorpresa di concetto | **non dimostrata** (l'audacia è di registro, non di idea) | non dimostrata in confronto diretto |
| Tenuta del claim | nessuna garanzia (no-refusal) | «less likely to make unsupported claims» |

## Assegnazione (D19)

- **magnum = Copywriter**: voce, calore, primo getto, territori in voce, la
  riga che nessuno osa. Il turno in cui la domanda è «come suona?».
- **Opus 4.8 = Copywriter 2**: giudizio, vincoli, verifica claim, selezione,
  mano finale. Il turno in cui la domanda è «è corretto/difendibile?».
- **Perché non lo stesso modello per entrambi i turni**: l'auto-correzione
  intrinseca peggiora (Huang et al., ICLR 2024); il critico deve essere
  un'altra testa; il dibattito con giudizio evita la Degeneration-of-Thought
  (Liang et al.). È la coppia copywriter+art director di Bernbach (DDB): far
  collidere due modi di pensare — «creative abrasion» (Leonard).

## Dinamica di dialogo (incorporata nelle personas)

1. **magnum apre** a caldo: butta 3-4 territori già in voce, uno indicibile.
2. **Opus giudica**: verdetto in una riga per territorio contro 3 prove
   (brief? claim difendibile? già visto dai competitor?), ne uccide, ne
   sceglie uno, chiede UNA cosa in più.
3. **magnum difende e rilancia** senza spegnere la temperatura.
4. **Opus chiude** l'esecuzione nei vincoli, senza levigare via la cosa viva.

Regole: **apre sempre magnum**; **il giudice non è mai magnum**; **verdetto
obbligato per turno** (uccidine almeno alcuni) o i due convergono e paghi due
modelli per copy medio.

## Trabocchetti

- **NON a magnum**: output strutturato, giudizio/selezione, claim/legale,
  thread lunghi (deriva), temp 1.0 (sbrodola sensuale — usare ~0.85), trend
  recenti (cutoff giugno 2024). Italiano rifinito da **verificare** (dataset
  in inglese; ma nei nostri test dal vivo l'italiano di magnum era buono).
- **NON a Opus**: il primo getto divergente da solo (omogeneizza — Doshi &
  Hauser), territorio nero, iperbole non sostenibile, auto-critica come unico
  controllo. Mettere i suoi tic nelle frasi bandite del brief (le rispetta).

## Discrepanza contesto (da tenere d'occhio)

Le fonti danno finestre diverse per magnum: OpenRouter **16K**, scheda HF
**32.768**, pagina Featherless **131.072**. L'API `/v1/models` di Featherless
ci ha restituito **32768**. In D18 il budget di contesto (60k caratteri ≈ 16k
token) è tenuto sotto il più piccolo di questi valori: sicuro in ogni caso.

## Da fare (test onesto, 30 min)

Stesso brief italiano ai due, 10 headline a testa, valutazione cieca. Se
magnum non porta un'idea che Opus non aveva, il suo ruolo va ristretto (resta
comunque il migliore per tono di voce e primo getto).

## Fonti principali

- [magnum-v4-72b — scheda HF](https://huggingface.co/anthracite-org/magnum-v4-72b)
- [magnum su Featherless](https://featherless.ai/models/anthracite-org/magnum-v4-72b) · [su OpenRouter](https://openrouter.ai/anthracite-org/magnum-v4-72b)
- [Introducing Claude Opus 4.8 — Anthropic](https://www.anthropic.com/news/claude-opus-4-8)
- [Doshi & Hauser, Science Advances 2024](https://www.science.org/doi/10.1126/sciadv.adn5290)
- [Huang et al., ICLR 2024](https://arxiv.org/abs/2310.01798) · [Liang et al., Multi-Agent Debate](https://arxiv.org/abs/2305.19118)
- [Bernbach e la coppia creativa — VeryGoodCopy](https://www.verygoodcopy.com/verygoodcopy-blogs-10/bill-bernbach-creative-teams)
- [Creative abrasion — Forbes/Leonard](https://www.forbes.com/councils/forbesbusinesscouncil/2022/01/21/embracing-creative-abrasion-at-your-conflict-averse-company/)

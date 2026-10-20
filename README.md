# Gemini in Codex tramite Antigravity CLI

**Italiano** · [English](README.en.md)

**Usa Gemini come agente collaboratore all'interno del flusso di lavoro di Codex,
autenticandoti con il tuo piano mensile Google AI tramite Antigravity CLI.
Il percorso predefinito non richiede chiavi API e non usa le API a consumo.**

Codex prepara un incarico e i file pertinenti, invoca Gemini attraverso la CLI
ufficiale `agy`, legge la risposta salvata e ne verifica le indicazioni.
Puoi chiedere un secondo parere sul codice, una revisione indipendente, un'analisi
di risultati o una proposta da discutere e applicare con Codex.

La skill conserva il nome **`gemini-argon`**, ma permette di selezionare altri
modelli Gemini con **`--model`**. Argon rimane il predefinito per compatibilità.
Gemini è un collaboratore esterno invocato dalla skill; non viene registrato come
modello nativo di `spawn_agent`. Il wrapper lavora sul dossier ricevuto e restituisce
testo e proposte; gli interventi sul progetto restano coordinati da Codex.

## Piano mensile e autenticazione

Il login Google usa la sessione ufficiale di Antigravity e le quote del piano
associato all'account. Non servono una chiave Gemini API o un progetto con
fatturazione API per questo percorso. Il piano può essere a pagamento: la skill
non promette accesso gratuito o illimitato. Disponibilità dei modelli, condizioni
e quote dipendono da Google e dall'account. Consulta le fonti ufficiali:
[autenticazione](https://www.antigravity.google/docs/install?tab=cli),
[modelli](https://www.antigravity.google/docs/models/) e
[piani](https://www.antigravity.google/docs/plans/).

Google documenta Argon per Google AI Pro pagante, esclusi i trial, e Ultra.
Gli altri modelli possono avere requisiti diversi. `agy models` elenca gli slug;
solo una richiesta completata verifica l'accesso effettivo in quel momento.
Il wrapper non passa automaticamente a un altro modello, a Vertex/ADC o alle API
a consumo se il piano o la quota non consentono una richiesta.

Antigravity può consumare crediti AI extra quota se hai abilitato **AI Credit
Overages**. Per restare nella quota inclusa imposta **Never** nelle impostazioni
Antigravity; il wrapper non cambia questa preferenza. Vedi i
[dettagli sui crediti](https://www.antigravity.google/docs/plans/#overages).

## Requisiti

- Codex con esecuzione locale di comandi e accesso alla rete.
- Python **3.10+**; il wrapper usa solo la libreria standard, senza `pip install`.
- [Antigravity CLI ufficiale](https://www.antigravity.google/docs/getting-started/)
  (`agy`), installata e autenticata con l'account Google del piano.
- Git per clonare il repository. Su Windows il wrapper rileva anche
  `%LOCALAPPDATA%\agy\bin\agy.exe` prima del riavvio del terminale.

## Installazione per Codex

### Dal repository locale

Clona il repository:

```powershell
git clone https://github.com/elcerqua/argon-agent.git
cd argon-agent
python scripts/install.py
```

L'installer copia la sola skill in `~/.agents/skills/gemini-argon`, directory utente
indicata dalla [documentazione Codex](https://learn.chatgpt.com/docs/build-skills).
Non installa `agy`, non autentica l'account e non invia materiale a Gemini.
Su Linux/macOS usa `python3` se `python` non è disponibile.

Per una skill limitata a un progetto, dalla directory di questo repository:

```powershell
python scripts/install.py --dest 'D:\mio-progetto\.agents\skills'
```

Per aggiornare un'installazione esistente usa `--update`. Se la tua versione o
configurazione di Codex usa ancora `~/.codex/skills`, indica quella directory:

```powershell
python scripts/install.py --dest "$env:USERPROFILE\.codex\skills" --update
```

`--dest` indica sempre la cartella **che contiene le skill**. L'aggiornamento
sovrascrive i file distribuiti e conserva gli eventuali file aggiuntivi.
Evita installazioni duplicate con lo stesso nome. La skill sarà disponibile dal
turno successivo; se non compare, riavvia Codex.

### Con Skill Installer di Codex

Chiedi a Codex:

```text
$skill-installer installa la skill dal repository GitHub elcerqua/argon-agent,
percorso skills/gemini-argon, branch main.
```

## Primo utilizzo

Esempio PowerShell per l'installazione nella directory utente corrente:

```powershell
$geminiWrapper = Join-Path $env:USERPROFILE '.agents\skills\gemini-argon\scripts\Gemini_Argon.py'
python $geminiWrapper status
python $geminiWrapper login
agy models
```

Adegua il percorso se hai usato `--dest`. `login` richiede un terminale interattivo:
completa il browser con l'account Google del piano. Le credenziali sono gestite
da Antigravity nel keyring del sistema. `status` controlla solo l'installazione
e i metadati locali; non verifica l'abbonamento o la validità della sessione.

In Codex puoi quindi scrivere:

```text
Usa $gemini-argon per una revisione indipendente dei file modificati.
Usa il modello gemini-3.8-flash-medium, thinking medium, tramite il login Google
di Antigravity. Cita file e righe e salva il parere.
```

Oppure: `Usa $gemini-argon per chiedere ad Argon una proposta di refactoring,
thinking high.` Codex prepara il contesto necessario: Gemini non eredita la chat.

## Selezionare il modello e il ragionamento

Usa gli slug esatti mostrati da `agy models`; gli esempi dipendono dalla
disponibilità sul tuo account e non sono una lista garantita.

| Parametro | Comportamento |
| --- | --- |
| Nessun `--model` | `gemini-4-argon`, thinking `high` |
| `--model gemini-4-argon --thinking medium` | Inoltra `gemini-4-argon-medium` |
| `--model gemini-3.8-flash-medium` | Slug invariato, thinking `medium` ricavato dal suffisso |
| `--model gemini-3.1-pro-high --thinking high` | Slug invariato e livello esplicito |
| Slug senza suffisso | Slug invariato; thinking `high` salvo scelta esplicita |
| Suffisso e `--thinking` in conflitto | Errore locale prima dell'invio |

Sono supportati `low`, `medium`, `high`. Il wrapper inoltra il livello alla CLI:
il server può rifiutare combinazioni non supportate. Solo l'abbreviazione storica
di Argon aggiunge il suffisso; per gli altri modelli copia lo slug completo.

Prova minima facoltativa, **con una richiesta reale che consuma quota**, senza
file del progetto:

```powershell
python $geminiWrapper probe --model gemini-3.8-flash-medium --out .gemini-runs/access-01
```

Ometti `--model` per provare Argon. Ogni prova richiede una directory nuova.
Il probe controlla il modello selezionato dalla CLI e la risposta
`GEMINI_ACCESS_OK`; non certifica l'identità interna del server.

## Dossier e chiamate manuali

```powershell
python $geminiWrapper prepare --root . --prompt 'Rivedi il codice e proponi miglioramenti motivati.' --attach src/main.py --model gemini-3.8-flash-medium --out .gemini-runs/review-01
python $geminiWrapper send --run .gemini-runs/review-01
python $geminiWrapper resume --run .gemini-runs/review-01
```

Sostituisci `src/main.py` con un file reale. `prepare` è offline e produce il
dossier numerato, il manifest SHA256 e i parametri. `send` usa il modello salvato
e invia una sola volta. Con la CLI `resume` legge soltanto lo stato locale.
Per un follow-up prepara una nuova directory con `--previous-run`, ripetendo
lo stesso `--model` e il livello scelto: il transcript locale viene incluso.
Per cambiare modello avvia una conversazione nuova.

Usa `--prompt-file`, `--system-file`, `--attach` ripetuto o `--files-from` con un
array JSON di file espliciti. Nessuna scansione ricorsiva. Il limite predefinito
del payload è 3.000.000 byte (`--max-input-bytes`). Il timeout di `send` è 900
secondi (`--cli-timeout`). `--max-output-tokens` non impone un limite ad Antigravity.

Risultati: `response.md`, `state.json`, `response-0001.json` e log CLI nella cartella
del run. Exit code: **0** riuscito, **2** errore locale/backend, **3** in corso,
**4** esito non valido o ambiguo. Non ripetere automaticamente invii falliti.

## Perimetro e dati

Il trasporto predefinito richiede OAuth Google, rimuove dal processo figlio le
variabili per API/Vertex/ADC e rifiuta provider API/ADC configurati. Non modifica
le impostazioni permanenti. Le credenziali Antigravity non vengono lette o copiate
dal wrapper.

L'agente opera in modalità `plan` con workspace separato e `tools: []`, senza
autoapprovazioni. Nella CLI 1.4.2 il catalogo tool può comunque comparire: non è
un sandbox. Un uso di strumenti riportato negli eventi invalida la risposta.
Il controllo di modello verifica la configurazione CLI e il completamento,
non costituisce un'attestazione del server.

Seleziona solo file condivisibili: il controllo dei segreti è parziale. Dossier,
risposte e log restano locali e possono contenere materiale riservato; sono
esclusi dal Git del repository. I backend storici `gemini-cli` e REST restano
opzioni esplicite. Il REST **usa API a consumo** e richiede sia `--backend api`
sia `send --allow-paid-api`: vedi [riferimento API](skills/gemini-argon/references/api-backend.md).

## Sviluppo e pubblicazione

```powershell
python -m unittest discover -s skills/gemini-argon/scripts -p 'test_*.py' -v
python -m compileall -q skills/gemini-argon/scripts scripts
```

I test sono offline: processi e trasporti sono simulati. Non richiedono login,
`agy` o chiamate a pagamento. GitHub Actions esegue la suite su Windows e Linux
con Python 3.10 e 3.14. Questo non equivale a una prova live di tutti i modelli.

Il repository contiene `skills/gemini-argon/` (pacchetto installabile),
`scripts/install.py`, i due README, licenza GPL-3.0 e workflow CI.
Per il push consulta [PUBLISH.md](PUBLISH.md), con comandi per GitHub CLI o Git.

Autore originale: **Cerqua ([elcerqua](https://github.com/elcerqua))**.
Repository ufficiale: [elcerqua/argon-agent](https://github.com/elcerqua/argon-agent).
Contributi tramite pull request benvenuti, sotto la stessa licenza del progetto.

Progetto indipendente, non affiliato a Google o OpenAI.
Copyright © 2026 Cerqua. Licenza [GNU GPL versione 3](LICENSE) (`GPL-3.0-only`).

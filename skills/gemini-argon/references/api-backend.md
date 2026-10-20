# Backend REST opzionale

Questa modalita usa la Gemini API a consumo, non il piano Pro tramite OAuth.
Usala solo su richiesta esplicita. Il wrapper non passa mai qui dopo un errore CLI.

La chiave e letta da GEMINI_API_KEY/GOOGLE_API_KEY nell'ambiente del processo
oppure dalle sole variabili utente omonime su Windows. Non passarla negli
argomenti, in chat o nei dossier. Non leggere altri archivi di credenziali.

Prepara con `--backend api`; invia con `send --allow-paid-api`. Il doppio parametro
evita che un vecchio run API sia inviato a pagamento per errore dopo il cambio OAuth.
I vecchi run senza campo backend sono interpretati come API e richiedono il flag.

Le richieste usano Interactions API, `background=true`, `store=true`. Il servizio
conserva lo stato per continuazione e recupero. `resume` esegue GET senza un nuovo
POST. `--previous-run` usa previous_interaction_id su un run API completato.
Non e supportato il cambio backend all'interno di una conversazione.

Stato `submission_unknown` dopo il POST: potrebbe essere gia stato accettato.
Non ripetere il POST automaticamente. Se esiste un ID usa resume; altrimenti
conserva i log e riferisci l'ambiguita. Un `.lock` richiede di controllare il PID
prima di rimuoverlo dopo un processo terminato.

Fonti: [Argon API](https://ai.google.dev/gemini-api/docs/latest-model),
[Interactions](https://ai.google.dev/api/interactions-api).

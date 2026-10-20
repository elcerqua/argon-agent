# Revisione di esperimenti e proposta successiva

Usa questo flusso quando l'utente vuole far rivedere una campagna e chiedere una
nuova direzione. Adattalo alla domanda; non richiede un numero fisso di chiamate.

## Dossier

Ricostruisci l'inventario dai report disponibili, dalle errata e dallo stato
aggiornato, non solo dalle intestazioni di memoria. Per ogni esperimento indica
ipotesi, meccanismo, protocollo, dati/periodi, controlli, metriche, soglie e verdetto.
Separa risultato negativo, supporto insufficiente, difetto tecnico e prova non
eseguita. Conserva i riferimenti alle fonti e dichiara il perimetro coperto e i
materiali mancanti. Non dichiarare "tutti" senza un inventario verificato.

Includi architettura e baseline, preregistrazioni, codice dei componenti rilevanti,
risultati primari, audit, correzioni e limiti. Usa sintesi per orientare, con fonti
primarie per permettere una critica indipendente. Per un corpus oltre il limite,
dividi per famiglie, conserva un indice comune, raccogli revisioni parziali e
richiedi una sintesi che dichiari quali prove ogni revisione ha ricevuto.

## Prima domanda: revisione

Esempio da adattare, scritto nella domanda del run:

> Valuta criticamente le evidenze allegate. Per ciascun rilievo cita file e righe,
> severita, conseguenza e verifica minima che potrebbe confermarlo o smentirlo.
> Distingui difetti dimostrati, sospetti e limiti informativi. Non assumere che
> un FAIL dimostri l'inutilita universale di un meccanismo. Controlla anche che
> risultati apparentemente favorevoli siano sostenuti dai controlli. Indica i
> documenti mancanti necessari prima di raccomandare un nuovo esperimento.

Fornisci ulteriori prove se utili alla richiesta. Non chiedere al modello di
approvare le conclusioni di Codex e non nascondere fallimenti o errata pertinenti.
Questa e una revisione concettuale/documentale: il wrapper non riproduce calcoli.

## Domanda successiva: proposta

Continua con `--previous-run` oppure prepara una sintesi citata se il contesto
remoto non e piu disponibile. Chiedi una proposta prioritaria che specifichi:

- difetto o opportunita osservabile e diagnostica preliminare separata dalla cura;
- meccanismo causale/predittivo ipotizzato e differenza dai tentativi precedenti;
- evidenze a favore, contrarie e informazioni ancora mancanti;
- test minimo, controlli pertinenti, metrica primaria, gate fissati prima del run;
- supporto atteso, budget, condizioni di arresto e cosa implicherebbe un FAIL.

Consenti la conclusione che le prove non giustifichino un nuovo fit. Non imporre
una proposta "vincente". Confronta la proposta con l'inventario prima di chiamarla
nuova: cambiare una soglia o una griglia non dimostra un meccanismo distinto.

Per trading/backtest applica la skill `backtest` se disponibile e, se pertinente,
le altre skill del dominio. Passa al modello Gemini selezionato i vincoli effettivi: dati gia osservati,
holdout consumato, controlli placebo/nulli, confronti appaiati, test multipli,
costi di esecuzione e differenza fra predittivita e risultato economico.
Le soglie specifiche appartengono al protocollo del progetto, non a questa skill.

Archivia la proposta come proposta. Avvia un nuovo esperimento solo entro lo scope
autorizzato e dopo la preregistrazione richiesta dal progetto. Non modificare i
risultati sigillati, azzerare budget o promuovere una variante in base al parere
del modello.

# Rom-til-rom festgenerator

Generator for å planlegge rom-til-rom. Kjører lokalt.

## Kom i gang

```bash
# Start med deltakerliste (genererer ny timeplan)
python main.py deltakere.txt

# Gjenoppta lagret timeplan
python main.py timeplan.json

# Start uten fil (laster siste autosave hvis den finnes)
python main.py
```

Nettleseren åpner seg automatisk på `http://localhost:7331`.

## Deltakerfil-format

Én deltaker per linje: `Navn, Romnummer`

```
Hans K, 151
Hans P, 211
Tollak, 254
...
```

## Endre løyper

| Handling | Resultat |
|----------|----------|
| Dra person → annet rom (samme økt) | Flyttes |
| Dra person → annen person (samme økt) | Bytter rom |
| Dra rom-badge → annet rom | Bytter tidspunkt (gjester følger med) |
| Dra rom-badge → tom bakgrunn i annen økt | Flyttes (uten gjester) |

## Filstruktur

```
romtilrom/
├── main.py        Oppstart og HTTP-server
├── models.py      Participant-klasse og datastruktur
├── scheduler.py   Planleggingslogikk
├── state.py       Delt tilstand og autosave
└── static/
    ├── index.html
    ├── style.css
    └── app.js
```

## Autosave

Timeplanen lagres automatisk til `timeplan_autosave.json` etter hver endring.
Bruk **Lagre JSON**-knappen for å laste ned en navngitt kopi.

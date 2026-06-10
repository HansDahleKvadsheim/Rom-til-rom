# Rom-til-rom festgenerator

Generator for å planlegge rom-til-rom. Kjører lokalt.

For utenforstående:
Rom-Til-Rom er en tradisjonsrik fest vi arrangerer 1-2 ganger i semesteret på Singsaker Studenterhjem. Festen skjer på følgende vis:
Alle deltekre stiller rommet sitt til disposisjon i 30 minutter ila. kvelden. De skal stille med:
- Et unikt tema
- En unik drink
- En lek
- God stemning
Hver deltaker vil, på starten av festen, få utdelt 6 rom de skal være på (deriblant sitt eget), med 6 ulike grupper.

Denne koden er for å generere et utkast til romrekkefølge, og løype for hver deltaker. Programmet tillater også å endre på eksisterende løyper, og endre visningsformat for lett å skrive ut alle enkeltløypene.

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

## Delte rom
Programmet reagerer dårlig på to personer med samme rom. Dette problemet omgås med å dele opp rommet i 2. F. eks hvis Olav og Kari ønsker å arrangere sammen på rom 112, men ha unike løyper, kan dette løses følgelig i Deltakere.txt 

Olav 112-1
Kari 112-2

Arrangør må selv sørge for at de får timeslot samtidig. 

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

# Porra Mundial 2026

Porra entre amics pel Mundial de futbol 2026 (11 juny – 19 juliol). Cada
jugador prediu el resultat exacte de cada partit i l'ordre final dels grups.
Tot es guarda en CSV.

## Puntuació

**Partits** (un per cadascun dels 104 partits):
- Resultat exacte (ex: predius 2-1 i acaba 2-1) → **3 punts**
- Encertes el guanyador/empat (1/X/2) però no el resultat → **1 punt**
- Res → **0 punts**

**Grups** (les prediccions es donen totes de cop abans que comenci la fase de grups):
- Ordre final exacte del grup, els 4 equips (1r-2n-3r-4t) → **+3 punts**
- Qualsevol error en l'ordre → **0 punts** (tot o res)

## Fitxers

```
descarrega_partits.py        Baixa/actualitza els 104 partits (hora d'Espanya)
apunta.py <tipus> "Nom" ...  Apunta prediccions ràpid quan un amic te les diu  ← el del dia a dia
genera_plantilla.py "Nom"    (Alternativa) crea una plantilla CSV buida per omplir a mà
genera_plantilla_grups.py "Nom"  (Alternativa) plantilla de grups buida
classificacio.py             Calcula punts i treu la classificació
genera_web.py                Genera docs/index.html (la web pública)
publica.py                   Regenera la web + commit + push a GitHub Pages

data/partits.json / .csv     Els 104 partits (id, data, hora ES, equips, seu)
data/resultats.csv           Resultats reals dels partits  ← l'omples tu
data/resultats_grups.csv     Ordre final real de cada grup ← l'omples tu
data/classificacio.csv       Classificació generada

prediccions/<Nom>.csv        Predicció de partits d'un jugador
prediccions_grups/<Nom>.csv  Predicció de grups d'un jugador
docs/index.html              Web estàtica autocontinguda (servida per GitHub Pages)
```

## Web pública (GitHub Pages)

La web es publica a **https://pau-fontanet.github.io/mundial-2026/** (repo
públic `Pau-Fontanet/mundial-2026`, servida des de la carpeta `docs/`).

Per actualitzar-la després de posar resultats o prediccions:

```
python publica.py
```

Regenera `docs/index.html`, fa commit i push; Pages s'actualitza en ~1 minut.

El nom del fitxer (`Marc.csv`) és el nom del jugador. Cada jugador té un
fitxer a `prediccions/` i un a `prediccions_grups/`.

## Com es fa servir

**1. Apunta les prediccions que et diuen els amics** (la manera ràpida):

Partits — `id=gols1-gols2`:
```
python apunta.py partits "Marc" 1=2-1 2=0-0 3=1-2 5=3-0
```
Grups — ordre final 1r→4t (n'hi ha prou amb part del nom de l'equip):
```
python apunta.py grups "Marc" A=Mexico,Korea,Czech,Africa H=Spain,Uruguay,Cape,Saudi
```
- Crea el fitxer del jugador si no existeix; pots anar afegint en diverses tandes.
- Per corregir, torna-ho a apuntar: `python apunta.py partits "Marc" 1=3-1`.
- Si t'equivoques d'equip o de format, avisa amb un missatge clar i no escriu res.

> Alternativa manual: `genera_plantilla.py "Nom"` i `genera_plantilla_grups.py "Nom"`
> creen CSV buits perquè el jugador els ompli ell mateix.

**2. A mesura que es juguen els partits, omple els resultats reals:**
- `data/resultats.csv` → posa `gol1`/`gol2` de cada partit jugat.
- `data/resultats_grups.csv` → quan acabi la fase de grups, posa `posicio_final` (1-4).

**3. Treu la classificació en qualsevol moment:**
```
python classificacio.py
```
Mostra la taula i desa `data/classificacio.csv`.

## Notes

- Els horaris són en hora d'Espanya peninsular (CEST, UTC+2) durant tot el torneig.
- A les eliminatòries els equips encara són codis (`2A`, `W97`, `L101`) fins que
  acaba la fase de grups; es predeixen quan se sàpiguen els equips.
- Per refrescar dades (per si openfootball actualitza alguna cosa):
  `python descarrega_partits.py`.
- Els CSV es desen en UTF-8 amb BOM, així s'obren bé a Excel amb accents.

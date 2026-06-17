"""Apunta ràpidament les prediccions d'un jugador.

Pensat perquè, quan un amic et digui les seves prediccions, les apuntis amb
una sola comanda. Valida i confirma el que ha quedat registrat.

PARTITS (id = gols_equip1 - gols_equip2):
    python apunta.py partits "Marc" 1=2-1 2=0-0 3=1-2 5=3-0

GRUPS (ordre final 1r,2n,3r,4t; n'hi ha prou amb part del nom de l'equip):
    python apunta.py grups "Marc" A=Mexico,Korea,Czech,Africa B=Switzerland,Canada,Qatar,Bosnia

- Crea el fitxer del jugador si no existeix; si ja existeix, només actualitza
  el que indiquis (la resta es manté).
- Als grups n'hi ha prou amb un tros del nom: "Korea" -> "South Korea",
  "Africa" -> "South Africa". Si és ambigu o no troba l'equip, avisa.
- Separadors flexibles: pots fer servir = o : (1:2-1) i comes o espais als grups.
"""

import csv
import json
import sys
import unicodedata
from collections import OrderedDict
from pathlib import Path

DIR = Path(__file__).resolve().parent
PARTITS = DIR / "data" / "partits.json"
PREDS = DIR / "prediccions"
PREDS_GRUPS = DIR / "prediccions_grups"


def normalitza(s: str) -> str:
    """Minúscules sense accents ni espais sobrants, per comparar noms."""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return s.lower().strip()


def carrega_partits() -> list[dict]:
    return json.loads(PARTITS.read_text(encoding="utf-8"))


def equips_per_grup(partits: list[dict]) -> "OrderedDict[str, list[str]]":
    grups: "OrderedDict[str, list[str]]" = OrderedDict()
    for m in partits:
        g = m.get("grup")
        if not g:
            continue
        equips = grups.setdefault(g, [])
        for t in (m["equip1"], m["equip2"]):
            if t not in equips:
                equips.append(t)
    return OrderedDict(sorted(grups.items()))


def error(msg: str) -> "None":
    print(f"ERROR: {msg}")
    sys.exit(1)


# ---------------------------------------------------------------- partits

def apunta_partits(jugador: str, tokens: list[str]) -> None:
    partits = carrega_partits()
    per_id = {p["id"]: p for p in partits}

    # Parseja els tokens abans de tocar res, per fallar net.
    canvis: dict[int, tuple[int, int]] = {}
    for tok in tokens:
        t = tok.replace(":", "=")
        if "=" not in t:
            error(f"Token invàlid '{tok}'. Format: id=gols1-gols2 (ex: 1=2-1).")
        sid, _, marcador = t.partition("=")
        try:
            pid = int(sid)
        except ValueError:
            error(f"Id de partit invàlid a '{tok}'.")
        if pid not in per_id:
            error(f"No existeix el partit {pid} (han de ser entre 1 i {len(partits)}).")
        if "-" not in marcador:
            error(f"Marcador invàlid a '{tok}'. Format: gols1-gols2 (ex: 2-1).")
        g1s, _, g2s = marcador.partition("-")
        try:
            g1, g2 = int(g1s), int(g2s)
        except ValueError:
            error(f"Gols no numèrics a '{tok}'.")
        if g1 < 0 or g2 < 0:
            error(f"Gols negatius a '{tok}'.")
        canvis[pid] = (g1, g2)

    PREDS.mkdir(exist_ok=True)
    fitxer = PREDS / f"{jugador}.csv"

    # Estat actual: tot el calendari amb gols buits, sobreescrit pel que hi hagués.
    actual: dict[int, tuple[str, str]] = {}
    if fitxer.exists():
        with fitxer.open(encoding="utf-8-sig", newline="") as f:
            for fila in csv.DictReader(f):
                try:
                    pid = int(fila["partit_id"])
                except (KeyError, ValueError, TypeError):
                    continue
                actual[pid] = (fila.get("gol1", ""), fila.get("gol2", ""))

    for pid, (g1, g2) in canvis.items():
        actual[pid] = (str(g1), str(g2))

    camps = ["partit_id", "data", "hora_es", "fase", "equip1", "equip2", "gol1", "gol2"]
    with fitxer.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=camps)
        w.writeheader()
        for p in partits:
            g1, g2 = actual.get(p["id"], ("", ""))
            w.writerow(
                {
                    "partit_id": p["id"],
                    "data": p["data"],
                    "hora_es": p["hora_es"],
                    "fase": p["fase"],
                    "equip1": p["equip1"],
                    "equip2": p["equip2"],
                    "gol1": g1,
                    "gol2": g2,
                }
            )

    omplerts = sum(1 for v in actual.values() if v[0] != "" and v[1] != "")
    print(f"[{jugador}] apuntats {len(canvis)} partit(s):")
    for pid in sorted(canvis):
        p = per_id[pid]
        g1, g2 = canvis[pid]
        print(f"   #{pid:>3}  {p['equip1']} {g1}-{g2} {p['equip2']}")
    print(f"Total prediccions de partits de {jugador}: {omplerts}/{len(partits)}")


# ---------------------------------------------------------------- grups

def resol_equip(token: str, equips: list[str], grup: str) -> str:
    tn = normalitza(token)
    if not tn:
        error(f"Equip buit al grup {grup}.")
    candidats = [e for e in equips if tn in normalitza(e) or normalitza(e) in tn]
    if len(candidats) == 1:
        return candidats[0]
    if len(candidats) > 1:
        error(f"'{token}' és ambigu al {grup}: podria ser {', '.join(candidats)}.")
    error(f"No trobo '{token}' al {grup}. Equips: {', '.join(equips)}.")
    raise AssertionError  # inabastable; error() fa sys.exit


def apunta_grups(jugador: str, tokens: list[str]) -> None:
    partits = carrega_partits()
    grups = equips_per_grup(partits)

    # Parseja tot abans d'escriure.
    canvis: dict[str, list[str]] = {}  # {grup: [1r, 2n, 3r, 4t]}
    for tok in tokens:
        if "=" not in tok:
            error(f"Token invàlid '{tok}'. Format: GRUP=eq1,eq2,eq3,eq4 (ex: A=Mexico,Korea,Czech,Africa).")
        sgrup, _, llista = tok.partition("=")
        sgrup = sgrup.strip().upper()
        grup = sgrup if sgrup.startswith("GROUP") else f"Group {sgrup}"
        # Reconstrueix la capitalització real (Group A).
        grup = next((g for g in grups if g.upper() == grup.upper()), None)
        if grup is None:
            error(f"Grup desconegut '{sgrup}'. Han de ser A-L.")
        equips_grup = grups[grup]
        peces = [x for x in llista.replace(";", ",").split(",") if x.strip()]
        if len(peces) != 4:
            error(f"El {grup} necessita 4 equips en ordre, n'has donat {len(peces)}: '{llista}'.")
        ordenats = [resol_equip(x, equips_grup, grup) for x in peces]
        if len(set(ordenats)) != 4:
            error(f"Equips repetits al {grup}: {ordenats}.")
        canvis[grup] = ordenats

    PREDS_GRUPS.mkdir(exist_ok=True)
    fitxer = PREDS_GRUPS / f"{jugador}.csv"

    # Estat actual: {grup: {equip: posicio}}.
    actual: dict[str, dict[str, str]] = {g: {} for g in grups}
    if fitxer.exists():
        with fitxer.open(encoding="utf-8-sig", newline="") as f:
            for fila in csv.DictReader(f):
                g = (fila.get("grup") or "").strip()
                e = (fila.get("equip") or "").strip()
                pos = (fila.get("posicio_final") or "").strip()
                if g in actual and e:
                    actual[g][e] = pos

    for grup, ordenats in canvis.items():
        for i, equip in enumerate(ordenats, 1):
            actual[grup][equip] = str(i)

    camps = ["grup", "equip", "posicio_final"]
    with fitxer.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=camps)
        w.writeheader()
        for grup, equips in grups.items():
            for equip in equips:
                w.writerow(
                    {
                        "grup": grup,
                        "equip": equip,
                        "posicio_final": actual[grup].get(equip, ""),
                    }
                )

    complets = sum(
        1 for g in grups if len(actual[g]) == 4 and all(actual[g].get(e) for e in grups[g])
    )
    print(f"[{jugador}] apuntats {len(canvis)} grup(s):")
    for grup in sorted(canvis):
        ordre = " ".join(f"{i}.{e}" for i, e in enumerate(canvis[grup], 1))
        print(f"   {grup}: {ordre}")
    print(f"Total grups complets de {jugador}: {complets}/{len(grups)}")


# ---------------------------------------------------------------- main

def main() -> None:
    if len(sys.argv) < 4:
        print(__doc__)
        sys.exit(1)
    mena = sys.argv[1].lower()
    jugador = sys.argv[2].strip()
    tokens = sys.argv[3:]
    if not jugador:
        error("El nom del jugador no pot estar buit.")
    if mena in ("partits", "partit", "p"):
        apunta_partits(jugador, tokens)
    elif mena in ("grups", "grup", "g"):
        apunta_grups(jugador, tokens)
    else:
        error(f"Tipus desconegut '{mena}'. Ha de ser 'partits' o 'grups'.")


if __name__ == "__main__":
    main()

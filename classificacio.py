"""Calcula la classificació de la porra del Mundial 2026.

Llegeix:
  - data/partits.json            : els 104 partits (per noms i ordre)
  - data/resultats.csv           : resultats reals dels partits (els omples tu)
  - data/resultats_grups.csv     : classificació final real de cada grup (la omples tu)
  - prediccions/<nom>.csv        : predicció de resultats per jugador
  - prediccions_grups/<nom>.csv  : predicció de l'ordre dels grups per jugador

Puntuació de partits:
  - Resultat exacte (gol1 i gol2 encertats) ........ 3 punts
  - Encert del guanyador/empat (1/X/2), no exacte .. 1 punt
  - Res ............................................ 0 punts

Bonus de grups:
  - Ordre final exacte del grup (1r-2n-3r-4t, els 4 equips) .. +3 punts
  - Qualsevol error en l'ordre .............................. 0 punts (tot o res)

Si falten data/resultats.csv o data/resultats_grups.csv, els crea buits
(amb tots els partits / grups) perquè els puguis anar omplint.

Sortida: taula a la consola + data/classificacio.csv
"""

import csv
import json
from collections import OrderedDict
from pathlib import Path

DIR = Path(__file__).resolve().parent
DATA = DIR / "data"
PARTITS = DATA / "partits.json"
RESULTATS = DATA / "resultats.csv"
RESULTATS_GRUPS = DATA / "resultats_grups.csv"
GRUPS_JUGADORS = DATA / "grups_jugadors.csv"
PREDS = DIR / "prediccions"
PREDS_GRUPS = DIR / "prediccions_grups"

# Grups de jugadors (porres separades). Un jugador pot ser de més d'un grup.
GRUPS_PORRA = ["ofi", "neris"]
ETIQUETA_GRUP = {"ofi": "Grup OFI", "neris": "Grup ÑERIS"}

PUNTS_EXACTE = 3
PUNTS_GUANYADOR = 1
PUNTS_GRUP = 3


def signe(a: int, b: int) -> int:
    """1 si guanya equip1, -1 si guanya equip2, 0 si empat."""
    return (a > b) - (a < b)


def carrega_partits() -> dict[int, dict]:
    partits = json.loads(PARTITS.read_text(encoding="utf-8"))
    return {p["id"]: p for p in partits}


def equips_per_grup() -> "OrderedDict[str, list[str]]":
    partits = json.loads(PARTITS.read_text(encoding="utf-8"))
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


# ---------------------------------------------------------------- partits

def parse_gols(fila: dict) -> "tuple[int, int] | None":
    """Retorna (gol1, gol2) si tots dos són enters vàlids, si no None."""
    g1, g2 = (fila.get("gol1") or "").strip(), (fila.get("gol2") or "").strip()
    if g1 == "" or g2 == "":
        return None
    try:
        return int(g1), int(g2)
    except ValueError:
        return None


def crea_resultats_buit(partits: dict[int, dict]) -> None:
    camps = ["partit_id", "data", "equip1", "equip2", "gol1", "gol2", "penals"]
    with RESULTATS.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=camps)
        w.writeheader()
        for p in partits.values():
            w.writerow(
                {
                    "partit_id": p["id"],
                    "data": p["data"],
                    "equip1": p["equip1"],
                    "equip2": p["equip2"],
                    "gol1": "",
                    "gol2": "",
                    "penals": "",
                }
            )
    print(f"Creat {RESULTATS} buit. Omple gol1/gol2 a mesura que es juguin els partits.\n")


def carrega_resultats() -> dict[int, "tuple[int, int]"]:
    resultats = {}
    with RESULTATS.open(encoding="utf-8-sig", newline="") as f:
        for fila in csv.DictReader(f):
            try:
                pid = int(fila["partit_id"])
            except (KeyError, ValueError, TypeError):
                continue
            gols = parse_gols(fila)
            if gols is not None:
                resultats[pid] = gols
    return resultats


def carrega_prediccions() -> dict[str, dict[int, "tuple[int, int]"]]:
    """{jugador: {partit_id: (gol1, gol2)}} a partir de prediccions/*.csv."""
    prediccions = {}
    if not PREDS.exists():
        return prediccions
    for fitxer in sorted(PREDS.glob("*.csv")):
        preds = {}
        with fitxer.open(encoding="utf-8-sig", newline="") as f:
            for fila in csv.DictReader(f):
                try:
                    pid = int(fila["partit_id"])
                except (KeyError, ValueError, TypeError):
                    continue
                gols = parse_gols(fila)
                if gols is not None:
                    preds[pid] = gols
        prediccions[fitxer.stem] = preds
    return prediccions


def punts(pred: "tuple[int, int]", real: "tuple[int, int]") -> int:
    if pred == real:
        return PUNTS_EXACTE
    if signe(*pred) == signe(*real):
        return PUNTS_GUANYADOR
    return 0


# ---------------------------------------------------------------- grups

def crea_resultats_grups_buit(grups: "OrderedDict[str, list[str]]") -> None:
    camps = ["grup", "equip", "posicio_final"]
    with RESULTATS_GRUPS.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=camps)
        w.writeheader()
        for grup, equips in grups.items():
            for equip in equips:
                w.writerow({"grup": grup, "equip": equip, "posicio_final": ""})
    print(
        f"Creat {RESULTATS_GRUPS} buit. Omple 'posicio_final' (1-4) quan acabi "
        "la fase de grups.\n"
    )


def carrega_ordre_grups(path: Path) -> dict[str, "tuple[str, ...]"]:
    """Llegeix un CSV (grup, equip, posicio_final) i retorna {grup: (1r,2n,3r,4t)}.

    Només inclou els grups completament resolts: els 4 equips amb posicions
    1-4 diferents i vàlides. La resta s'ignora.
    """
    per_grup: dict[str, dict[str, int]] = {}
    with path.open(encoding="utf-8-sig", newline="") as f:
        for fila in csv.DictReader(f):
            grup = (fila.get("grup") or "").strip()
            equip = (fila.get("equip") or "").strip()
            pos_str = (fila.get("posicio_final") or "").strip()
            if not grup or not equip or pos_str == "":
                continue
            try:
                pos = int(pos_str)
            except ValueError:
                continue
            per_grup.setdefault(grup, {})[equip] = pos

    ordres = {}
    for grup, assignacions in per_grup.items():
        posicions = list(assignacions.values())
        if len(assignacions) == 4 and sorted(posicions) == [1, 2, 3, 4]:
            ordenat = sorted(assignacions.items(), key=lambda kv: kv[1])
            ordres[grup] = tuple(equip for equip, _ in ordenat)
    return ordres


def carrega_prediccions_grups() -> dict[str, dict[str, "tuple[str, ...]"]]:
    """{jugador: {grup: (1r,2n,3r,4t)}} a partir de prediccions_grups/*.csv."""
    prediccions = {}
    if not PREDS_GRUPS.exists():
        return prediccions
    for fitxer in sorted(PREDS_GRUPS.glob("*.csv")):
        prediccions[fitxer.stem] = carrega_ordre_grups(fitxer)
    return prediccions


# ---------------------------------------------------------------- grups porra

def carrega_grups_jugadors() -> dict[str, set[str]]:
    """{grup_porra: {jugadors}} a partir de data/grups_jugadors.csv.

    El fitxer té columnes 'jugador' i una columna per grup (ofi, neris) amb
    1/0. Un jugador pot pertànyer a més d'un grup (p. ex. en Pau).
    """
    membres: dict[str, set[str]] = {g: set() for g in GRUPS_PORRA}
    if not GRUPS_JUGADORS.exists():
        return membres
    with GRUPS_JUGADORS.open(encoding="utf-8-sig", newline="") as f:
        for fila in csv.DictReader(f):
            jugador = (fila.get("jugador") or "").strip()
            if not jugador:
                continue
            for grup in GRUPS_PORRA:
                if (fila.get(grup) or "").strip() == "1":
                    membres[grup].add(jugador)
    return membres


def grups_de_jugador(jugador: str, membres: dict[str, set[str]]) -> str:
    """Etiqueta curta amb els grups del jugador, p. ex. 'ofi+neris'."""
    return "+".join(g for g in GRUPS_PORRA if jugador in membres[g]) or "-"


def mostra_taula(taula: list[dict], titol: str) -> None:
    """Ordena i imprimeix una taula de classificació."""
    ordenat = sorted(
        taula,
        key=lambda r: (-r["punts"], -r["exactes"], -r["grups_encertats"], r["jugador"]),
    )
    print(f"\n{titol}")
    print(
        f"{'#':>2}  {'Jugador':<16} {'Total':>5} {'Part.':>5} {'Grups':>5} "
        f"{'Exact':>5} {'Guany':>5} {'Grups OK':>8}"
    )
    print("-" * 62)
    for i, r in enumerate(ordenat, 1):
        print(
            f"{i:>2}  {r['jugador']:<16} {r['punts']:>5} {r['p_partits']:>5} "
            f"{r['p_grups']:>5} {r['exactes']:>5} {r['guanyadors']:>5} "
            f"{r['grups_encertats']:>8}"
        )


# ---------------------------------------------------------------- main

def main() -> None:
    partits = carrega_partits()
    grups = equips_per_grup()
    if not RESULTATS.exists():
        crea_resultats_buit(partits)
    if not RESULTATS_GRUPS.exists():
        crea_resultats_grups_buit(grups)

    resultats = carrega_resultats()
    resultats_grups = carrega_ordre_grups(RESULTATS_GRUPS)
    prediccions = carrega_prediccions()
    prediccions_grups = carrega_prediccions_grups()
    membres = carrega_grups_jugadors()

    # Conjunt de jugadors (poden tenir només un dels dos fitxers).
    jugadors = sorted(set(prediccions) | set(prediccions_grups))
    if not jugadors:
        print("Encara no hi ha prediccions. Genera-les amb:")
        print('   python genera_plantilla.py "<nom>"        (resultats)')
        print('   python genera_plantilla_grups.py "<nom>"  (grups)')
        return

    print(f"Partits amb resultat: {len(resultats)} / {len(partits)}")
    print(f"Grups resolts: {len(resultats_grups)} / {len(grups)}")
    print(f"Jugadors: {', '.join(jugadors)}\n")

    taula = []
    for jugador in jugadors:
        preds = prediccions.get(jugador, {})
        preds_grups = prediccions_grups.get(jugador, {})

        # Punts de partits.
        p_partits = exactes = guanyadors = jugats = 0
        for pid, real in resultats.items():
            if pid not in preds:
                continue
            jugats += 1
            pt = punts(preds[pid], real)
            p_partits += pt
            if pt == PUNTS_EXACTE:
                exactes += 1
            elif pt == PUNTS_GUANYADOR:
                guanyadors += 1

        # Bonus de grups.
        grups_encertats = 0
        for grup, ordre_real in resultats_grups.items():
            if preds_grups.get(grup) == ordre_real:
                grups_encertats += 1
        p_grups = grups_encertats * PUNTS_GRUP

        taula.append(
            {
                "jugador": jugador,
                "grups": grups_de_jugador(jugador, membres),
                "punts": p_partits + p_grups,
                "p_partits": p_partits,
                "p_grups": p_grups,
                "exactes": exactes,
                "guanyadors": guanyadors,
                "grups_encertats": grups_encertats,
                "partits_puntuats": jugats,
            }
        )

    # Classificació general (tots els jugadors).
    mostra_taula(taula, "CLASSIFICACIÓ GENERAL")

    # Una taula per cada grup de la porra (en Pau apareix als dos).
    for grup in GRUPS_PORRA:
        subtaula = [r for r in taula if r["jugador"] in membres[grup]]
        if subtaula:
            mostra_taula(subtaula, ETIQUETA_GRUP.get(grup, grup.upper()))

    # Desa CSV (general, ordenat).
    taula.sort(key=lambda r: (-r["punts"], -r["exactes"], -r["grups_encertats"], r["jugador"]))
    desti = DATA / "classificacio.csv"
    with desti.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "posicio", "jugador", "grups", "punts", "p_partits", "p_grups",
                "exactes", "guanyadors", "grups_encertats", "partits_puntuats",
            ],
        )
        w.writeheader()
        for i, r in enumerate(taula, 1):
            w.writerow({"posicio": i, **r})
    print(f"\nClassificació desada a {desti}")


if __name__ == "__main__":
    main()

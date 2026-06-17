"""Genera una plantilla de predicció de classificació final dels grups.

Ús:
    python genera_plantilla_grups.py "Marc"

Crea  prediccions_grups/Marc.csv  amb els 12 grups i els seus 4 equips.
El jugador omple la columna `posicio_final` (1 = primer, 2, 3, 4 = últim)
per a cada equip. Aquestes prediccions es donen totes de cop abans que
comenci la fase de grups.

Puntuació (a classificacio.py): +3 punts per grup si encerta l'ordre exacte
dels 4 equips (1r-2n-3r-4t). Tot o res.
"""

import csv
import json
import sys
from collections import OrderedDict
from pathlib import Path

DIR = Path(__file__).resolve().parent
PARTITS = DIR / "data" / "partits.json"
PREDS_GRUPS = DIR / "prediccions_grups"


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
    # Ordena els grups per lletra (Group A, B, C...).
    return OrderedDict(sorted(grups.items()))


def main() -> None:
    if len(sys.argv) != 2:
        print('Ús: python genera_plantilla_grups.py "<nom del jugador>"')
        sys.exit(1)
    jugador = sys.argv[1].strip()
    if not jugador:
        print("El nom no pot estar buit.")
        sys.exit(1)

    grups = equips_per_grup()
    PREDS_GRUPS.mkdir(exist_ok=True)
    desti = PREDS_GRUPS / f"{jugador}.csv"
    if desti.exists():
        resposta = input(f"{desti.name} ja existeix. Sobreescriure? (s/N) ")
        if resposta.strip().lower() not in ("s", "si", "sí"):
            print("Cancel·lat.")
            return

    camps = ["grup", "equip", "posicio_final"]
    with desti.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=camps)
        w.writeheader()
        for grup, equips in grups.items():
            for equip in equips:
                w.writerow({"grup": grup, "equip": equip, "posicio_final": ""})
    print(f"Plantilla de grups creada: {desti}")
    print(
        f"{len(grups)} grups. El jugador ha d'omplir 'posicio_final' (1-4) "
        "per a cada equip."
    )


if __name__ == "__main__":
    main()

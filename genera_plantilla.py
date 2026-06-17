"""Genera una plantilla de prediccions buida per a un jugador.

Ús:
    python genera_plantilla.py "Marc"

Crea  prediccions/Marc.csv  amb tots els partits i les columnes gol1/gol2
buides perquè el jugador les ompli amb el resultat exacte que prediu.

El nom del fitxer és el nom del jugador: la classificació l'agafa d'aquí.
Les columnes data/hora/equips només són per orientar-se en omplir; el que
compta per puntuar és partit_id + gol1 + gol2.
"""

import csv
import json
import sys
from pathlib import Path

DIR = Path(__file__).resolve().parent
PARTITS = DIR / "data" / "partits.json"
PREDS = DIR / "prediccions"


def main() -> None:
    if len(sys.argv) != 2:
        print('Ús: python genera_plantilla.py "<nom del jugador>"')
        sys.exit(1)
    jugador = sys.argv[1].strip()
    if not jugador:
        print("El nom no pot estar buit.")
        sys.exit(1)

    partits = json.loads(PARTITS.read_text(encoding="utf-8"))
    PREDS.mkdir(exist_ok=True)
    desti = PREDS / f"{jugador}.csv"
    if desti.exists():
        resposta = input(f"{desti.name} ja existeix. Sobreescriure? (s/N) ")
        if resposta.strip().lower() not in ("s", "si", "sí"):
            print("Cancel·lat.")
            return

    camps = ["partit_id", "data", "hora_es", "fase", "equip1", "equip2", "gol1", "gol2"]
    with desti.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=camps)
        w.writeheader()
        for p in partits:
            w.writerow(
                {
                    "partit_id": p["id"],
                    "data": p["data"],
                    "hora_es": p["hora_es"],
                    "fase": p["fase"],
                    "equip1": p["equip1"],
                    "equip2": p["equip2"],
                    "gol1": "",
                    "gol2": "",
                }
            )
    print(f"Plantilla creada: {desti}")
    print(f"{len(partits)} partits. El jugador ha d'omplir les columnes gol1 i gol2.")


if __name__ == "__main__":
    main()

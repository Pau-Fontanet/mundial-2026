"""Descarrega tots els partits del Mundial 2026 i genera dades netes.

Font: openfootball/worldcup.json (domini públic, sense API key).
Converteix els horaris a hora d'Espanya peninsular (Europe/Madrid).

Durant tot el Mundial (11 juny – 19 juliol 2026) Madrid és en horari d'estiu
(CEST = UTC+2), així que fem servir un offset fix +2 i evitem dependències.

Sortida (a la carpeta data/):
  - partits.json : llista de partits amb tots els camps
  - partits.csv  : el mateix en CSV, fàcil d'obrir a Excel

Cada partit té un `id` estable (1..104) ordenat per data i hora: serà la clau
per registrar les prediccions de la porra i els resultats reals.
"""

import csv
import json
import re
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

FONT_URL = "https://raw.githubusercontent.com/openfootball/worldcup.json/master/2026/worldcup.json"

# Madrid és UTC+2 (CEST) durant tot el torneig.
MADRID = timezone(timedelta(hours=2))

# Traducció de les fases a català.
FASES = {
    "Round of 32": "Setzens de final",
    "Round of 16": "Vuitens de final",
    "Quarter-final": "Quarts de final",
    "Semi-final": "Semifinals",
    "Match for third place": "3r i 4t lloc",
    "Final": "Final",
}

DIR = Path(__file__).resolve().parent
DATA = DIR / "data"

# Format del camp time, p.ex. "13:00 UTC-6".
RE_TIME = re.compile(r"^(\d{1,2}):(\d{2})\s+UTC([+-]\d{1,2})$")


def descarrega() -> list[dict]:
    DATA.mkdir(exist_ok=True)
    cru = DATA / "worldcup_raw.json"
    print(f"Descarregant des de openfootball...")
    with urllib.request.urlopen(FONT_URL) as resp:
        contingut = resp.read()
    cru.write_bytes(contingut)
    dades = json.loads(contingut)
    return dades["matches"]


def fase_de(m: dict) -> str:
    r = m.get("round", "")
    if r.startswith("Matchday"):
        return "Fase de grups"
    return FASES.get(r, r)


def a_hora_espanya(data: str, time_str: str) -> datetime:
    """Converteix data + 'HH:MM UTC-X' a un datetime amb hora d'Espanya."""
    mt = RE_TIME.match(time_str.strip())
    if not mt:
        raise ValueError(f"Format d'hora desconegut: {time_str!r}")
    hh, mm, offset = int(mt.group(1)), int(mt.group(2)), int(mt.group(3))
    tz_local = timezone(timedelta(hours=offset))
    dt_local = datetime.strptime(data, "%Y-%m-%d").replace(
        hour=hh, minute=mm, tzinfo=tz_local
    )
    return dt_local.astimezone(MADRID)


def processa(matches: list[dict]) -> list[dict]:
    partits = []
    for m in matches:
        dt_es = a_hora_espanya(m["date"], m["time"])
        partits.append(
            {
                "fase": fase_de(m),
                "grup": m.get("group"),
                "data": dt_es.strftime("%Y-%m-%d"),
                "hora_es": dt_es.strftime("%H:%M"),
                "datetime_es": dt_es.isoformat(),
                "equip1": m["team1"],
                "equip2": m["team2"],
                "seu": m.get("ground"),
                "hora_local": m["time"],
                "ronda_original": m.get("round"),
            }
        )
    # Ordena per data/hora i assigna un id estable.
    partits.sort(key=lambda p: p["datetime_es"])
    for i, p in enumerate(partits, start=1):
        p["id"] = i
    # Posa l'id al davant.
    return [{"id": p.pop("id"), **p} for p in partits]


def desa(partits: list[dict]) -> None:
    (DATA / "partits.json").write_text(
        json.dumps(partits, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    camps = [
        "id", "fase", "grup", "data", "hora_es", "datetime_es",
        "equip1", "equip2", "seu", "hora_local", "ronda_original",
    ]
    with (DATA / "partits.csv").open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=camps)
        w.writeheader()
        w.writerows(partits)


def main() -> None:
    matches = descarrega()
    partits = processa(matches)
    desa(partits)
    print(f"\n{len(partits)} partits desats a {DATA}\\partits.json i partits.csv")
    print("\nPrimers partits (hora d'Espanya):")
    for p in partits[:5]:
        print(
            f"  #{p['id']:>3}  {p['data']} {p['hora_es']}  "
            f"{p['equip1']} - {p['equip2']}  ({p['fase']}, {p['seu']})"
        )


if __name__ == "__main__":
    main()

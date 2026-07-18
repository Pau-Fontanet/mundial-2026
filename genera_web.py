"""Genera un frontal estàtic (web/index.html) per veure la porra de forma xula.

Llegeix totes les dades (partits, prediccions de grups i de partits, resultats
reals i classificació) i les incrusta dins un únic fitxer HTML autocontingut.
No cal servidor ni connexió: obre web/index.html amb el navegador.

Ús:
    python genera_web.py

Tres vistes:
  - Classificació : la taula de punts (mateixes regles que classificacio.py).
  - Grups         : per a cada grup, què ha predit cada jugador (1r-4t) i el real.
  - Partits       : per jugador, el resultat predit de cada partit i els punts.

Torna a executar-lo quan apuntis prediccions o omplis resultats per refrescar.
"""

import base64
import csv
import json
import mimetypes
from collections import OrderedDict
from pathlib import Path

DIR = Path(__file__).resolve().parent
DATA = DIR / "data"
PARTITS = DATA / "partits.json"
RESULTATS = DATA / "resultats.csv"
RESULTATS_GRUPS = DATA / "resultats_grups.csv"
PREDS = DIR / "prediccions"
PREDS_GRUPS = DIR / "prediccions_grups"
WEB = DIR / "docs"
ASSETS = DIR / "assets"

# Fotos dels jugadors (assets/<nom>.jpg/png). S'incrusten en base64 dins l'HTML
# perquè el fitxer segueixi sent autocontingut. Per canviar-ne una, substitueix
# el fitxer i torna a executar genera_web.py.
def carrega_fotos() -> dict:
    fotos = {}
    if not ASSETS.is_dir():
        return fotos
    for f in ASSETS.iterdir():
        if f.suffix.lower() not in (".jpg", ".jpeg", ".png", ".webp"):
            continue
        mime = mimetypes.guess_type(f.name)[0] or "image/jpeg"
        b64 = base64.b64encode(f.read_bytes()).decode("ascii")
        fotos[f.stem] = f"data:{mime};base64,{b64}"
    return fotos

PUNTS_EXACTE = 3
PUNTS_GUANYADOR = 1
PUNTS_GRUP = 3

# Grups de jugadors per filtrar la classificació. El Pau forma part dels dos.
EQUIPS_JUGADORS = {
    "Ofi": ["Albi", "Amado", "Jordi", "Nil", "Pablo", "Pau"],
    "Ñeris": ["Albi", "Axel", "Gilbert", "Oscar", "Pau"],
}

# Bandera (emoji) per equip. Els codis d'eliminatòries (2A, W73...) no en tenen.
BANDERES = {
    "Mexico": "🇲🇽", "South Africa": "🇿🇦", "South Korea": "🇰🇷", "Czech Republic": "🇨🇿",
    "Canada": "🇨🇦", "Bosnia & Herzegovina": "🇧🇦", "Qatar": "🇶🇦", "Switzerland": "🇨🇭",
    "Brazil": "🇧🇷", "Morocco": "🇲🇦", "Haiti": "🇭🇹", "Scotland": "🏴󠁧󠁢󠁳󠁣󠁴󠁿",
    "USA": "🇺🇸", "Paraguay": "🇵🇾", "Australia": "🇦🇺", "Turkey": "🇹🇷",
    "Germany": "🇩🇪", "Curaçao": "🇨🇼", "Ivory Coast": "🇨🇮", "Ecuador": "🇪🇨",
    "Netherlands": "🇳🇱", "Japan": "🇯🇵", "Sweden": "🇸🇪", "Tunisia": "🇹🇳",
    "Belgium": "🇧🇪", "Egypt": "🇪🇬", "Iran": "🇮🇷", "New Zealand": "🇳🇿",
    "Spain": "🇪🇸", "Cape Verde": "🇨🇻", "Saudi Arabia": "🇸🇦", "Uruguay": "🇺🇾",
    "France": "🇫🇷", "Senegal": "🇸🇳", "Iraq": "🇮🇶", "Norway": "🇳🇴",
    "Argentina": "🇦🇷", "Algeria": "🇩🇿", "Austria": "🇦🇹", "Jordan": "🇯🇴",
    "Portugal": "🇵🇹", "DR Congo": "🇨🇩", "Uzbekistan": "🇺🇿", "Colombia": "🇨🇴",
    "England": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "Croatia": "🇭🇷", "Ghana": "🇬🇭", "Panama": "🇵🇦",
}

# Quadre d'eliminatòries en espai dels nostres id (73..104). 'fonts' diu de quins
# dos partits surt cada eliminatòria: [[id_equip1, tipus], [id_equip2, tipus]] on
# tipus 'W' = guanyador i 'L' = perdedor (només el 3r i 4t lloc fa servir 'L').
# Compensa que els codis W../L.. d'openfootball es refereixen als seus números
# originals, no als nostres id reordenats per data (verificat amb worldcup_raw.json).
ELIMINATORIES = {
    "rondes": [
        {"titol": "Setzens", "ids": list(range(73, 89))},
        {"titol": "Vuitens", "ids": list(range(89, 97))},
        {"titol": "Quarts", "ids": [97, 98, 99, 100]},
        {"titol": "Semis", "ids": [101, 102]},
        {"titol": "Final", "ids": [104]},
    ],
    "tercer": 103,
    "fonts": {
        89: [[73, "W"], [76, "W"]], 90: [[75, "W"], [78, "W"]],
        91: [[74, "W"], [77, "W"]], 92: [[79, "W"], [80, "W"]],
        93: [[84, "W"], [83, "W"]], 94: [[82, "W"], [81, "W"]],
        95: [[87, "W"], [86, "W"]], 96: [[85, "W"], [88, "W"]],
        97: [[90, "W"], [89, "W"]], 98: [[93, "W"], [94, "W"]],
        99: [[91, "W"], [92, "W"]], 100: [[95, "W"], [96, "W"]],
        101: [[97, "W"], [98, "W"]], 102: [[99, "W"], [100, "W"]],
        104: [[101, "W"], [102, "W"]], 103: [[101, "L"], [102, "L"]],
    },
}


def _ordena_bracket(elim: dict) -> None:
    """Reordena els partits dins de cada ronda seguint l'arbre eliminatori
    ('fonts') perquè les línies entre rondes no es creuin. Perquè no hi hagi
    creuaments, l'ordre vertical d'una columna ha de coincidir amb l'ordre dels
    seus dos partits d'origen a la columna anterior. Ho aconseguim ordenant cada
    ronda per la posició de la seva primera fulla en un recorregut en profunditat
    (DFS) del quadre de guanyadors, arrelat a la Final."""
    fonts = {tid: srcs for tid, srcs in elim["fonts"].items()}
    arrel = elim["rondes"][-1]["ids"][0]          # Final: única ronda amb 1 partit

    fulles: list[int] = []

    def dfs(nid: int) -> None:
        srcs = fonts.get(nid)
        if not srcs:                              # partit de la 1a ronda (fulla)
            fulles.append(nid)
            return
        for src, _tipus in srcs:
            dfs(src)

    dfs(arrel)
    pos = {mid: i for i, mid in enumerate(fulles)}

    def clau(mid: int) -> int:                    # posició vertical del subarbre
        srcs = fonts.get(mid)
        if not srcs:
            return pos[mid]
        return min(clau(src) for src, _tipus in srcs)

    for rnd in elim["rondes"]:
        rnd["ids"].sort(key=clau)


_ordena_bracket(ELIMINATORIES)


def signe(a: int, b: int) -> int:
    return (a > b) - (a < b)


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


def parse_gols(fila: dict) -> "tuple[int, int] | None":
    g1, g2 = (fila.get("gol1") or "").strip(), (fila.get("gol2") or "").strip()
    if g1 == "" or g2 == "":
        return None
    try:
        return int(g1), int(g2)
    except ValueError:
        return None


def carrega_resultats() -> "tuple[dict[int, tuple[int, int]], dict[int, str]]":
    """Retorna (resultats_90min, penals).

    'resultats_90min' són els gols als 90' (els que compten per puntuar).
    'penals' és el marcador de la tanda (equip1-equip2) per als partits que
    es van decidir des del punt de penal; només per mostrar-lo, no puntua.
    """
    res, penals = {}, {}
    if not RESULTATS.exists():
        return res, penals
    with RESULTATS.open(encoding="utf-8-sig", newline="") as f:
        for fila in csv.DictReader(f):
            try:
                pid = int(fila["partit_id"])
            except (KeyError, ValueError, TypeError):
                continue
            gols = parse_gols(fila)
            if gols is not None:
                res[pid] = gols
                pen = (fila.get("penals") or "").strip()
                if pen:
                    penals[pid] = pen
    return res, penals


def carrega_ordre_grups(path: Path) -> dict[str, list[str]]:
    if not path.exists():
        return {}
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
    for grup, asg in per_grup.items():
        if len(asg) == 4 and sorted(asg.values()) == [1, 2, 3, 4]:
            ordres[grup] = [e for e, _ in sorted(asg.items(), key=lambda kv: kv[1])]
    return ordres


def carrega_preds_partits() -> dict[str, dict[int, "tuple[int, int]"]]:
    out = {}
    if not PREDS.exists():
        return out
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
        out[fitxer.stem] = preds
    return out


def carrega_preds_grups() -> dict[str, dict[str, list[str]]]:
    out = {}
    if not PREDS_GRUPS.exists():
        return out
    for fitxer in sorted(PREDS_GRUPS.glob("*.csv")):
        out[fitxer.stem] = carrega_ordre_grups(fitxer)
    return out


def punts(pred: "tuple[int, int]", real: "tuple[int, int]") -> int:
    if pred == real:
        return PUNTS_EXACTE
    if signe(*pred) == signe(*real):
        return PUNTS_GUANYADOR
    return 0


def classificacio(jugadors, preds_partits, preds_grups, resultats, resultats_grups):
    taula = []
    for jugador in jugadors:
        pp = preds_partits.get(jugador, {})
        pg = preds_grups.get(jugador, {})
        p_partits = exactes = guanyadors = jugats = 0
        historial = []  # (pid, categoria) per calcular la ratxa
        for pid, real in resultats.items():
            if pid not in pp:
                continue
            jugats += 1
            pt = punts(pp[pid], real)
            p_partits += pt
            if pt == PUNTS_EXACTE:
                exactes += 1
                historial.append((pid, "exact"))
            elif pt == PUNTS_GUANYADOR:
                guanyadors += 1
                historial.append((pid, "win"))
            else:
                historial.append((pid, "miss"))
        grups_ok = sum(
            1 for g, ordre in resultats_grups.items() if pg.get(g) == ordre
        )
        forma = [cat for _, cat in sorted(historial)[-5:]]  # últims 5, antic → recent
        taula.append({
            "jugador": jugador,
            "punts": p_partits + grups_ok * PUNTS_GRUP,
            "p_partits": p_partits,
            "p_grups": grups_ok * PUNTS_GRUP,
            "exactes": exactes,
            "guanyadors": guanyadors,
            "grups_ok": grups_ok,
            "partits_puntuats": jugats,
            "forma": forma,
        })
    taula.sort(key=lambda r: (-r["punts"], -r["exactes"], -r["grups_ok"], r["jugador"]))
    return taula


def main() -> None:
    partits = carrega_partits()
    grups = equips_per_grup(partits)
    resultats, penals = carrega_resultats()
    resultats_grups = carrega_ordre_grups(RESULTATS_GRUPS)
    preds_partits = carrega_preds_partits()
    preds_grups = carrega_preds_grups()
    jugadors = sorted(set(preds_partits) | set(preds_grups))
    taula = classificacio(jugadors, preds_partits, preds_grups, resultats, resultats_grups)

    dades = {
        "partits": [
            {
                "id": p["id"], "fase": p["fase"], "grup": p.get("grup"),
                "data": p["data"], "hora": p["hora_es"],
                "equip1": p["equip1"], "equip2": p["equip2"], "seu": p.get("seu"),
            }
            for p in partits
        ],
        "grups": {g: equips for g, equips in grups.items()},
        "banderes": BANDERES,
        "jugadors": jugadors,
        "preds_partits": {j: {str(k): list(v) for k, v in d.items()}
                          for j, d in preds_partits.items()},
        "preds_grups": preds_grups,
        "resultats": {str(k): list(v) for k, v in resultats.items()},
        "penals": {str(k): v for k, v in penals.items()},
        "resultats_grups": resultats_grups,
        "classificacio": taula,
        "equips_jugadors": EQUIPS_JUGADORS,
        "eliminatories": ELIMINATORIES,
        "fotos": carrega_fotos(),
    }

    WEB.mkdir(exist_ok=True)
    desti = WEB / "index.html"
    html = PLANTILLA.replace(
        "/*__DADES__*/", json.dumps(dades, ensure_ascii=False)
    )
    desti.write_text(html, encoding="utf-8")
    print(f"Web generada: {desti}")
    print(f"  Jugadors: {len(jugadors)}  |  Partits amb resultat: {len(resultats)}/{len(partits)}"
          f"  |  Grups resolts: {len(resultats_grups)}/{len(grups)}")
    print("Obre el fitxer amb el navegador (doble clic).")


PLANTILLA = r"""<!DOCTYPE html>
<html lang="ca">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Porra Mundial 2026</title>
<style>
  :root{
    --bg:#0b0e1a; --card:#161c2e; --card2:#1f2740; --line:#2c3550;
    --txt:#eef1fa; --muted:#9aa3c0; --accent:#3ddc97; --accent2:#ffd166;
    --gold:#ffd166; --green:#2ecc71; --yellow:#f1c40f; --red:#e74c3c;
  }
  *{box-sizing:border-box}
  body{margin:0;color:var(--txt);min-height:100vh;
       font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;
       background:
         radial-gradient(900px 500px at 12% -8%, #1d6e5022, transparent 60%),
         radial-gradient(800px 480px at 92% 0%, #b98a1a22, transparent 55%),
         linear-gradient(165deg,#0a0d18,#10162a 55%,#0b0f1d);
       background-attachment:fixed;}
  header{position:relative;padding:42px 20px 22px;text-align:center;overflow:hidden;
         border-bottom:1px solid var(--line);
         background:linear-gradient(180deg,#141b30aa,transparent);}
  header::after{content:"";position:absolute;left:0;right:0;bottom:0;height:2px;
         background:linear-gradient(90deg,transparent,var(--accent),var(--accent2),transparent);
         opacity:.8}
  h1{margin:0;font-size:34px;font-weight:800;letter-spacing:.4px;
     background:linear-gradient(92deg,#fff,#cfe9dd 40%,var(--accent2));
     -webkit-background-clip:text;background-clip:text;color:transparent}
  .sub{color:var(--muted);margin-top:8px;font-size:14px;letter-spacing:.2px}
  .wrap{max-width:1100px;margin:0 auto;padding:0 16px 60px}
  .tabs{display:flex;gap:8px;justify-content:center;margin:26px 0 8px;flex-wrap:wrap}
  .tab{background:var(--card);border:1px solid var(--line);color:var(--txt);
       padding:10px 18px;border-radius:999px;cursor:pointer;font-size:15px;
       transition:.18s ease;box-shadow:0 2px 10px #0003}
  .tab:hover{border-color:var(--accent);transform:translateY(-1px)}
  .tab.active{background:linear-gradient(135deg,var(--accent),#2bb87f);color:#06281c;
       font-weight:700;border-color:transparent;box-shadow:0 6px 18px #2bb87f55}
  .gtabs{display:flex;gap:8px;justify-content:center;margin:16px 0 0;flex-wrap:wrap}
  .gtab{background:var(--card);border:1px solid var(--line);color:var(--txt);
        padding:6px 16px;border-radius:999px;cursor:pointer;font-size:14px;transition:.18s ease}
  .gtab:hover{border-color:var(--accent2);transform:translateY(-1px)}
  .gtab.active{background:linear-gradient(135deg,var(--accent2),#e8b53e);color:#3a2c00;
        font-weight:700;border-color:transparent;box-shadow:0 6px 18px #e8b53e44}
  .panel{display:none;animation:fade .28s ease}
  .panel.active{display:block}
  @keyframes fade{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:none}}
  .card{background:linear-gradient(180deg,#1b2236,#161c2e);border:1px solid var(--line);
        border-radius:18px;padding:16px 18px;margin:16px 0;
        box-shadow:0 10px 36px #0007, inset 0 1px 0 #ffffff0a}
  table{width:100%;border-collapse:collapse;font-size:14px}
  th,td{padding:11px 10px;text-align:left;border-bottom:1px solid var(--line)}
  thead th{position:sticky;top:0;background:#1a2138;z-index:1}
  th{color:var(--muted);font-weight:600;font-size:12px;text-transform:uppercase;letter-spacing:.4px}
  th.sortable{cursor:pointer;user-select:none;-webkit-user-select:none;white-space:nowrap;
       transition:color .15s,background .15s;touch-action:manipulation}
  th.sortable:hover{color:var(--txt)}
  th.sortable.sorted{color:var(--accent2)}
  .sarrow{display:inline-block;width:.9em;font-size:11px}
  @media (max-width:640px){ th,td{padding:10px 8px} th.sortable{padding:12px 8px} }
  @media (max-width:480px){
    header{padding:30px 12px 18px}
    h1{font-size:24px;line-height:1.2}
    .sub{font-size:12px}
  }
  tbody tr{transition:background .15s}
  tbody tr:hover{background:#ffffff08}
  tr:last-child td{border-bottom:none}
  .num{text-align:right;font-variant-numeric:tabular-nums}
  .pill{display:inline-block;padding:2px 9px;border-radius:999px;font-size:12px;font-weight:700}
  .total{font-size:17px;font-weight:800;color:var(--accent)}
  .encerts{font-size:17px;font-weight:800;color:var(--accent2)}
  .rank{width:38px;text-align:center;font-weight:800;color:var(--muted)}
  tbody tr.r1{background:linear-gradient(90deg,#ffd16614,transparent 70%)}
  tbody tr.r2{background:linear-gradient(90deg,#cdd6e010,transparent 70%)}
  tbody tr.r3{background:linear-gradient(90deg,#cd7f3210,transparent 70%)}
  tbody tr.r1:hover,tbody tr.r2:hover,tbody tr.r3:hover{filter:brightness(1.15)}
  .controls{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin:6px 0 2px}
  select,.toggle{background:var(--card2);color:var(--txt);border:1px solid var(--line);
         border-radius:10px;padding:9px 12px;font-size:14px;cursor:pointer}
  .grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(330px,1fr));gap:16px}
  .grp h3{margin:0 0 10px;font-size:16px;display:flex;align-items:center;gap:8px}
  .grp table{font-size:13px}
  .flag{font-size:16px}
  .real{background:#1d2a22}
  .ok{background:#16331f;color:#9cf2b9;font-weight:700}
  .ok-pos{outline:2px solid var(--green);outline-offset:-2px}
  .badge3{background:var(--green);color:#04210f;padding:1px 7px;border-radius:6px;font-size:11px;font-weight:800}
  .grups-stack{display:flex;flex-direction:column;gap:18px}
  .grp.wide h3{margin:0 0 12px;font-size:18px}
  .tscroll{overflow-x:auto}
  .gtbl{font-size:13px}
  .gtbl th.jcol,.gtbl td.jcol{text-align:center;width:48px;white-space:nowrap}
  .gtbl th.tcol{min-width:200px}
  .gtbl td.tcol{white-space:nowrap;font-weight:600}
  .gtbl tbody tr:hover{background:#222a4055}
  .pos{display:inline-block;width:20px;text-align:center;color:var(--muted);font-weight:800;margin-right:2px}
  .tstat{color:var(--muted);font-weight:500;font-size:11px;margin-left:8px}
  .medal{display:inline-flex;align-items:center;justify-content:center;width:25px;height:25px;
         box-sizing:border-box;line-height:1;border-radius:50%;font-weight:800;font-size:13px;vertical-align:middle}
  .m1{background:linear-gradient(135deg,#ffe27a,#f0b90b);color:#3a2c00}
  .m2{background:linear-gradient(135deg,#eef2f6,#a9b4bf);color:#2a2f36}
  .m3{background:linear-gradient(135deg,#e3a868,#b87333);color:#2a1500}
  .m4{background:transparent;border:1px dashed var(--line);color:var(--muted);font-weight:600}
  .medal.ring{box-shadow:0 0 0 2px var(--green)}
  .live{font-size:11px;font-weight:700;padding:1px 9px;border-radius:999px;background:var(--card2);
        color:var(--muted);border:1px solid var(--line);vertical-align:middle}
  .live.done{color:#9cf2b9;border-color:#2ecc71}
  .live.play{color:#ffe28a;border-color:#f1c40f}
  .muted{color:var(--muted)}
  .sc-exact{background:#16331f;color:#9cf2b9;font-weight:700}
  .sc-win{background:#3a3413;color:#ffe28a;font-weight:700}
  .sc-zero{color:var(--muted)}
  .empty{text-align:center;color:var(--muted);padding:40px 10px}
  .fase-h{margin:18px 0 6px;color:var(--accent2);font-size:14px;font-weight:700;
          text-transform:uppercase;letter-spacing:.5px}
  .legend{font-size:12px;color:var(--muted);margin-top:8px}
  .legend span{display:inline-block;margin-right:14px}
  .legend span.medal{display:inline-flex;margin-right:4px}
  .dot{display:inline-block;width:10px;height:10px;border-radius:3px;vertical-align:middle;margin-right:4px}
  .forma{display:inline-flex;gap:3px;align-items:center}
  .fdot{width:12px;height:12px;border-radius:3px;display:inline-block;vertical-align:middle;box-shadow:inset 0 0 0 1px #0003}
  .fdot.exact{background:var(--green)}
  .fdot.win{background:var(--yellow)}
  .fdot.miss{background:var(--red)}
  th.forma-h{white-space:nowrap}
  .stat{display:inline-flex;flex-direction:column;align-items:center;background:var(--card2);
        border:1px solid var(--line);border-radius:12px;padding:8px 16px;margin:4px}
  .stat b{font-size:20px;color:var(--accent)}
  .stat small{color:var(--muted)}
  .stats{display:flex;justify-content:center;flex-wrap:wrap;margin-top:6px}

  /* ---- Eliminatòries (bracket) ---- */
  .bracket-wrap{overflow-x:auto;overflow-y:hidden;padding:4px 2px 14px}
  .bracket-inner{position:relative;width:max-content}
  svg.connectors{position:absolute;top:0;left:0;pointer-events:none;z-index:0;overflow:visible}
  svg.connectors .conn{fill:none;stroke:var(--line);stroke-width:2}
  svg.connectors .conn-l{stroke:#3d4763;stroke-dasharray:5 5}
  .bracket{position:relative;z-index:1;display:flex;gap:30px;align-items:stretch;min-height:900px}
  .mt-col{display:flex;flex-direction:column;min-width:182px;width:182px}
  .mt-h{font-size:12px;font-weight:800;text-transform:uppercase;letter-spacing:.6px;color:var(--accent2);
        text-align:center;margin-bottom:12px;white-space:nowrap}
  .mt-col-body{flex:1;display:flex;flex-direction:column;justify-content:space-around;gap:10px}
  .mt-third{justify-content:flex-end}
  .mt-third .mt-col-body{flex:none;justify-content:center;margin-top:auto}
  .mt-card{background:linear-gradient(180deg,#1c2338,#171d2f);border:1px solid var(--line);
        border-radius:11px;padding:7px 9px;cursor:pointer;transition:.15s ease;box-shadow:0 4px 14px #0004}
  .mt-card:hover{border-color:var(--accent);transform:translateY(-1px);box-shadow:0 8px 20px #0006}
  .mt-row{display:flex;justify-content:space-between;align-items:center;gap:8px;padding:3px 1px;font-size:13px}
  .mt-row .tm{display:flex;align-items:center;gap:6px;overflow:hidden;min-width:0}
  .mt-row .nm{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
  .mt-row .sc{font-variant-numeric:tabular-nums;font-weight:800;color:var(--muted);flex:none}
  .mt-row.mt-win .nm{color:var(--accent);font-weight:700}
  .mt-row.mt-win .sc{color:var(--accent)}
  .mt-row.mt-lose{opacity:.45}
  .mt-row.mt-ph .nm{color:var(--muted);font-style:italic;font-size:11.5px}
  .mt-pen{font-size:10.5px;color:var(--muted);text-align:right;margin-top:1px}
  .mt-when{font-size:10.5px;color:var(--muted);text-align:center;margin-top:4px;
        border-top:1px dashed var(--line);padding-top:3px}
  /* popover de prediccions */
  .pop{position:absolute;z-index:100;width:222px;max-height:300px;overflow:auto;
       background:linear-gradient(180deg,#1e2740,#161c2e);border:1px solid var(--accent);
       border-radius:12px;box-shadow:0 16px 40px #000b;padding:11px 12px;animation:fade .16s ease}
  .pop-title{font-size:13px;font-weight:700;margin-bottom:4px;line-height:1.35}
  .pop-res{font-size:15px;font-weight:800;color:var(--accent2);margin-bottom:6px;font-variant-numeric:tabular-nums}
  .pop-res.muted{color:var(--muted);font-size:12px;font-weight:600}
  .pop-sub{font-size:10px;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);
        margin:2px 0 5px;border-top:1px solid var(--line);padding-top:6px}
  .prow{display:flex;justify-content:space-between;gap:10px;padding:3px 5px;border-radius:6px;font-size:12.5px}
  .prow .num{font-variant-numeric:tabular-nums;font-weight:700;flex:none}
  .prow small{font-weight:700;opacity:.8;margin-left:2px}
  .prow.muted .num{color:var(--muted);font-weight:400}

  /* ---- Celebració del guanyador ---- */
  #campio-overlay{position:fixed;inset:0;z-index:1000;display:none;
       align-items:center;justify-content:center;padding:20px;overflow:hidden;
       background:radial-gradient(circle at 50% 28%,#13223dee,#060912fb);
       -webkit-backdrop-filter:blur(7px);backdrop-filter:blur(7px);animation:ovfade .45s ease}
  #campio-overlay.show{display:flex}
  @keyframes ovfade{from{opacity:0}to{opacity:1}}
  .campio-card{position:relative;max-width:520px;width:100%;text-align:center;
       background:linear-gradient(180deg,#1d2544,#141a2c);
       border:1px solid var(--gold);border-radius:24px;padding:36px 30px 28px;
       box-shadow:0 30px 80px #000c,0 0 0 1px #ffffff08 inset,0 0 70px #ffd16626;
       animation:campiopop .6s cubic-bezier(.2,1.35,.35,1)}
  @keyframes campiopop{from{transform:scale(.72) translateY(28px);opacity:0}to{transform:none;opacity:1}}
  .campio-close{position:absolute;top:12px;right:14px;background:none;border:none;
       color:var(--muted);font-size:22px;line-height:1;cursor:pointer;padding:4px 8px;border-radius:8px}
  .campio-close:hover{color:var(--txt);background:#ffffff10}
  .campio-trophy{font-size:76px;line-height:1;filter:drop-shadow(0 6px 16px #ffd16688);
       animation:bob 2.6s ease-in-out infinite}
  @keyframes bob{0%,100%{transform:translateY(0) rotate(-4deg)}50%{transform:translateY(-11px) rotate(4deg)}}
  .campio-foto{position:relative;width:172px;height:172px;margin:4px auto 6px;
       animation:bob 3.4s ease-in-out infinite}
  .campio-foto img{width:172px;height:172px;border-radius:14px;object-fit:cover;
       box-shadow:0 12px 34px #000b,0 0 44px #ffd16640}
  .campio-foto .espurna{position:absolute;font-size:24px;animation:twinkle 1.6s ease-in-out infinite}
  .campio-foto .e1{top:-8px;right:-12px}
  .campio-foto .e2{bottom:0;left:-16px;animation-delay:.5s}
  .campio-foto .e3{top:-6px;left:-8px;animation-delay:.9s;font-size:18px}
  @keyframes twinkle{0%,100%{opacity:.35;transform:scale(.8)}50%{opacity:1;transform:scale(1.15)}}
  .campio-mote{display:inline-block;margin:8px 0 4px;padding:5px 14px;border-radius:999px;
       background:linear-gradient(135deg,#2a2140,#1c2440);border:1px solid var(--gold);
       color:var(--gold);font-size:13.5px;font-weight:800;letter-spacing:.3px}
  .campio-kicker{margin-top:12px;font-size:12px;font-weight:800;letter-spacing:3px;
       text-transform:uppercase;color:var(--gold)}
  .campio-nom{font-size:clamp(40px,12vw,56px);font-weight:900;margin:4px 0 2px;line-height:1.02;
       background:linear-gradient(92deg,#fff,#ffe9a8 45%,var(--gold));
       -webkit-background-clip:text;background-clip:text;color:transparent;
       text-shadow:0 2px 34px #ffd16633}
  .campio-sub{color:var(--muted);font-size:14.5px;margin-bottom:18px}
  .campio-msg{font-size:14.5px;line-height:1.55;color:var(--txt);text-align:left;
       background:#ffffff08;border:1px solid var(--line);border-radius:14px;padding:14px 16px;margin:0 0 18px}
  .campio-msg b{color:var(--accent)}
  .campio-stats{display:flex;gap:9px;justify-content:center;flex-wrap:wrap;margin-bottom:22px}
  .campio-stats .cst{background:var(--card2);border:1px solid var(--line);border-radius:12px;
       padding:8px 14px;min-width:64px}
  .campio-stats .cst b{display:block;font-size:22px;color:var(--gold);line-height:1.15}
  .campio-stats .cst small{color:var(--muted);font-size:11px}
  .campio-btn{background:linear-gradient(135deg,var(--accent),#2bb87f);color:#06281c;
       border:none;border-radius:12px;padding:12px 26px;font-size:15px;font-weight:800;
       cursor:pointer;transition:transform .15s,box-shadow .15s;box-shadow:0 8px 24px #3ddc9744}
  .campio-btn:hover{transform:translateY(-2px);box-shadow:0 12px 30px #3ddc9766}
  .campio-podi{color:var(--muted);font-size:13px;margin-top:16px}
  .campio-podi b{color:var(--txt)}
  .confeti{position:fixed;top:-14px;width:9px;height:15px;z-index:1001;border-radius:2px;
       pointer-events:none;will-change:transform;animation:cfall linear forwards}
  @keyframes cfall{to{transform:translateY(106vh) rotate(760deg);opacity:.85}}
  #campio-reobre{position:fixed;right:16px;bottom:16px;z-index:900;display:none;
       align-items:center;gap:7px;background:linear-gradient(135deg,var(--gold),#e0a92e);
       color:#3a2c00;border:none;border-radius:999px;padding:11px 16px;font-size:13.5px;
       font-weight:800;cursor:pointer;box-shadow:0 8px 24px #0007,0 0 0 1px #ffffff22 inset;
       transition:transform .15s,box-shadow .15s;animation:reobrepop .5s ease}
  #campio-reobre:hover{transform:translateY(-2px);box-shadow:0 12px 30px #000a}
  @keyframes reobrepop{from{transform:scale(.6);opacity:0}to{transform:none;opacity:1}}
  @media(max-width:520px){#campio-reobre span{display:none}#campio-reobre{padding:12px 14px;font-size:17px}}
</style>
</head>
<body>
<header>
  <h1>Porra Mundial 2026</h1>
  <div class="sub">11 juny – 19 juliol · prediccions i classificació entre amics</div>
  <div class="stats" id="stats"></div>
</header>
<div class="wrap">
  <div class="tabs">
    <button class="tab active" data-tab="classificacio">Classificació</button>
    <button class="tab" data-tab="propers">Propers</button>
    <button class="tab" data-tab="grups">Grups</button>
    <button class="tab" data-tab="eliminatories">Eliminatòries</button>
    <button class="tab" data-tab="partits">Partits</button>
  </div>
  <div class="panel active" id="classificacio"></div>
  <div class="panel" id="propers"></div>
  <div class="panel" id="grups"></div>
  <div class="panel" id="eliminatories"></div>
  <div class="panel" id="partits"></div>
</div>

<div id="campio-overlay"><div class="campio-card" id="campio-card"></div></div>
<button id="campio-reobre" title="Tornar a veure el campió">🏆 <span>Veure el campió</span></button>

<script>
const DATA = /*__DADES__*/;
const B = DATA.banderes;
const flag = t => B[t] ? B[t]+' ' : '';
const teamHtml = t => `<span class="flag">${B[t]||''}</span> ${t}`;
const el = (h)=>{const d=document.createElement('div');d.innerHTML=h;return d.firstElementChild;};

// ---- top stats
(function(){
  const nRes = Object.keys(DATA.resultats).length;
  const nGr = Object.keys(DATA.resultats_grups).length;
  const totG = Object.keys(DATA.grups).length;
  document.getElementById('stats').innerHTML = `
    <div class="stat"><b>${DATA.jugadors.length}</b><small>jugadors</small></div>
    <div class="stat"><b>${nRes}/${DATA.partits.length}</b><small>partits jugats</small></div>
    <div class="stat"><b>${nGr}/${totG}</b><small>grups resolts</small></div>`;
})();

// ---- tabs
document.querySelectorAll('.tab').forEach(t=>t.onclick=()=>{
  document.querySelectorAll('.tab').forEach(x=>x.classList.remove('active'));
  document.querySelectorAll('.panel').forEach(x=>x.classList.remove('active'));
  t.classList.add('active');
  document.getElementById(t.dataset.tab).classList.add('active');
  if(t.dataset.tab==='eliminatories') requestAnimationFrame(drawConnectors);
});

// ================= CLASSIFICACIÓ =================
let classGrup = 'Conjunt';
// Columnes ordenables. val(r) dóna el valor a comparar; num=alineació dreta.
const CLASS_COLS = [
  {key:'jugador',   label:'Jugador',    num:false, val:r=>r.jugador},
  {key:'punts',     label:'Total',      num:true,  val:r=>r.punts,                 cls:'total'},
  {key:'p_partits', label:'Pts partits',num:true,  val:r=>r.p_partits, title:'Punts obtinguts encertant resultats de partits'},
  {key:'p_grups',   label:'Pts grups',  num:true,  val:r=>r.p_grups,   title:'Punts obtinguts encertant el podi dels grups'},
  {key:'exactes',   label:'Exactes',    num:true,  val:r=>r.exactes},
  {key:'guanyadors',label:'1X2',        num:true,  val:r=>r.guanyadors},
  {key:'grups_ok',  label:'Grups OK',   num:true,  val:r=>r.grups_ok},
  {key:'encerts',   label:'Encerts',    num:true,  val:r=>r.exactes+r.guanyadors,  cls:'encerts', title:"Total d'encerts: exactes + guanyador/empat"},
];
let classSort = {key:'punts', dir:-1};   // -1 descendent, 1 ascendent
const FORMA_TIT = {exact:'Exacte (+3)', win:'Encert 1X2 (+1)', miss:'Fallat (0)'};
function formaHtml(r){
  const f = r.forma || [];
  if(!f.length) return '<span class="muted">·</span>';
  return `<span class="forma">`
    + f.map(c=>`<span class="fdot ${c}" title="${FORMA_TIT[c]||''}"></span>`).join('')
    + `</span>`;
}
function renderClassificacio(){
  const p = document.getElementById('classificacio');
  const hiHaResultats = Object.keys(DATA.resultats).length || Object.keys(DATA.resultats_grups).length;
  const medal = i => ['🥇','🥈','🥉'][i] || (i+1);
  const grupsBtns = ['Conjunt','Ofi','Ñeris'].map(g=>
    `<button class="gtab${g===classGrup?' active':''}" data-grup="${g}">${g}</button>`).join('');
  const filtra = r => classGrup==='Conjunt' || (DATA.equips_jugadors[classGrup]||[]).includes(r.jugador);
  const col = CLASS_COLS.find(c=>c.key===classSort.key) || CLASS_COLS[1];
  const t = DATA.classificacio.filter(filtra).slice().sort((a,b)=>{
    const va=col.val(a), vb=col.val(b);
    let c = typeof va==='string' ? va.localeCompare(vb,'ca') : va-vb;
    if(c===0) c = b.punts-a.punts;            // desempat sempre pels punts totals
    return c*classSort.dir;
  });
  const arrow = c => c.key===classSort.key ? (classSort.dir<0?' ▾':' ▴') : '';
  const head = `<th class="rank">#</th>` + CLASS_COLS.map(c=>
    `<th class="sortable${c.num?' num':''}${c.key===classSort.key?' sorted':''}" data-key="${c.key}"`
    + `${c.title?` title="${c.title}"`:''}>${c.label}<span class="sarrow">${arrow(c)}</span></th>`).join('')
    + `<th class="forma-h" title="Últims 5 partits (antic → recent)">Ratxa</th>`;
  let rows = t.map((r,i)=>`
    <tr class="${hiHaResultats&&i<3?'r'+(i+1):''}">
      <td class="rank">${medal(i)}</td>`
    + CLASS_COLS.map(c=>`<td class="${c.num?'num':''}${c.cls?' '+c.cls:''}">${c.val(r)}</td>`).join('')
    + `<td>${formaHtml(r)}</td>`
    + `</tr>`).join('');
  p.innerHTML = `
    <div class="gtabs">${grupsBtns}</div>
    <div class="card">
      ${hiHaResultats?'':'<div class="empty" style="padding:12px">Encara no hi ha resultats reals. La taula s\'omplirà a mesura que omplis <code>data/resultats.csv</code> i <code>data/resultats_grups.csv</code> i tornis a generar la web.</div>'}
      <div class="tscroll"><table>
        <thead><tr>${head}</tr></thead>
        <tbody>${rows}</tbody>
      </table></div>
      <div class="legend">
        <span>Toca una capçalera per ordenar.</span>
        <span><b>Total</b> = <b>Pts partits</b> + <b>Pts grups</b> (punts que ha fet cada jugador per partits i per grups)</span>
        <span>Exacte 3p · Guanyador/empat 1p · Grup encertat +3p</span>
        <span><b>Ratxa</b> = últims 5 partits (antic → recent):
          <span class="fdot exact"></span> exacte
          <span class="fdot win"></span> 1X2
          <span class="fdot miss"></span> fallat</span>
        ${classGrup==='Conjunt'?'':`<span><b>${classGrup}</b>: ${DATA.equips_jugadors[classGrup].join(', ')}</span>`}
      </div>
    </div>`;
  p.querySelectorAll('.gtab').forEach(b=>b.onclick=()=>{classGrup=b.dataset.grup;renderClassificacio();});
  p.querySelectorAll('th.sortable').forEach(th=>th.onclick=()=>{
    const k=th.dataset.key;
    if(classSort.key===k){ classSort.dir*=-1; }
    else { classSort.key=k; classSort.dir = (k==='jugador'?1:-1); }  // text asc, números desc
    renderClassificacio();
  });
}

// ================= GRUPS =================
// Classificació actual d'un grup a partir dels resultats reals jugats.
function groupStandings(g, equips){
  const st = {};
  equips.forEach((t,i)=>st[t]={team:t,pts:0,pj:0,gf:0,ga:0,gd:0,ord:i});
  for(const m of DATA.partits){
    if(m.grup!==g) continue;
    const r = DATA.resultats[m.id];
    if(!r) continue;
    const a=st[m.equip1], b=st[m.equip2];
    if(!a||!b) continue;
    a.pj++; b.pj++; a.gf+=r[0]; a.ga+=r[1]; b.gf+=r[1]; b.ga+=r[0];
    if(r[0]>r[1]) a.pts+=3; else if(r[0]<r[1]) b.pts+=3; else {a.pts++; b.pts++;}
  }
  Object.values(st).forEach(s=>s.gd=s.gf-s.ga);
  return Object.values(st).sort((x,y)=>
    y.pts-x.pts || y.gd-x.gd || y.gf-x.gf || x.ord-y.ord);
}

function renderGrups(){
  const p = document.getElementById('grups');
  const jug = DATA.jugadors;
  const medals = ['m1','m2','m3'];
  let cards = '';
  for(const [g, equips] of Object.entries(DATA.grups)){
    const real = DATA.resultats_grups[g];        // ordre final real, si es coneix
    const standings = groupStandings(g, equips); // ordenat per classificació actual
    const anyPlayed = standings.some(s=>s.pj>0);

    let head = `<th class="tcol">Equip</th>` + jug.map(j=>`<th class="jcol">${j}</th>`).join('');
    let body = '';
    standings.forEach((s, idx)=>{
      const team = s.team;
      const pos = `<span class="pos">${idx+1}</span>`;
      const stat = anyPlayed
        ? `<span class="tstat">${s.pts}p · ${s.pj}j · ${s.gd>=0?'+':''}${s.gd}</span>` : '';
      const cells = jug.map(j=>{
        const pred = (DATA.preds_grups[j]||{})[g];
        if(!pred) return `<td class="jcol muted">·</td>`;
        const pi = pred.indexOf(team);
        if(pi<0) return `<td class="jcol muted">·</td>`;
        if(pi<3){
          const ring = real && real[pi]===team ? ' ring' : '';
          return `<td class="jcol"><span class="medal ${medals[pi]}${ring}">${pi+1}</span></td>`;
        }
        return `<td class="jcol"><span class="medal m4">4</span></td>`;
      }).join('');
      body += `<tr><td class="tcol">${pos}<span class="flag">${B[team]||''}</span> ${team}${stat}</td>${cells}</tr>`;
    });

    // badge +3 per qui clava tot l'ordre final real
    const encerten = real ? jug.filter(j=>{
      const pr=(DATA.preds_grups[j]||{})[g];
      return pr && pr.every((t,i)=>t===real[i]);
    }) : [];
    const badge = encerten.length?` <span class="badge3">+3: ${encerten.join(', ')}</span>`:'';
    const tag = real ? `<span class="live done">final</span>`
              : anyPlayed ? `<span class="live play">en joc</span>`
              : `<span class="live">sense jugar</span>`;
    cards += `
      <div class="card grp wide">
        <h3>Grup ${g.replace('Group ','')} ${tag}${badge}</h3>
        <div class="tscroll"><table class="gtbl">
          <thead><tr>${head}</tr></thead><tbody>${body}</tbody></table></div>
      </div>`;
  }
  p.innerHTML = `<div class="legend" style="margin:4px 2px 14px">
      Files ordenades per la <b>classificació actual</b> del grup. Cada columna és un jugador i la medalla és el podi que ha predit:
      <span class="medal m1">1</span> <span class="medal m2">2</span> <span class="medal m3">3</span> or/plata/bronze ·
      <span class="medal m4">4</span> previst últim · · sense predicció ·
      anella verda = encerta la posició final real
    </div><div class="grups-stack">${cards}</div>`;
}

// ================= PROPERS =================
// Els propers N partits sense resultat (ordre cronològic = ordre per id).
function propersPartits(n){
  const out=[];
  for(const m of DATA.partits){
    if(DATA.resultats[m.id]) continue;   // ja jugat
    out.push(m);
    if(out.length>=n) break;
  }
  return out;
}

function renderPropers(){
  const p = document.getElementById('propers');
  const jug = DATA.jugadors;
  const ctrl = `<div class="controls">
      <label>Mostra:</label>
      <select id="selN">
        <option value="4">els propers 4</option>
        <option value="8">els propers 8</option>
        <option value="12">els propers 12</option>
      </select>
    </div>`;
  p.innerHTML = ctrl + `<div id="propersBody"></div>`;
  const draw = ()=>{
    const n = parseInt(document.getElementById('selN').value, 10);
    const ms = propersPartits(n);
    const body = document.getElementById('propersBody');
    if(!ms.length){
      body.innerHTML = `<div class="card"><div class="empty">No queden partits per jugar. 🎉</div></div>`;
      return;
    }
    const now = new Date();
    const head = `<th class="tcol">Partit</th>` + jug.map(j=>`<th class="jcol">${j}</th>`).join('');
    let rows = '';
    for(const m of ms){
      const ko = new Date(`${m.data}T${m.hora||'00:00'}`);   // hora peninsular = hora local del navegador a ES
      const finalitzat = !isNaN(ko) && now >= new Date(ko.getTime() + 2*60*60*1000);
      const enJoc = !isNaN(ko) && now >= ko && !finalitzat;
      const dm = `${m.data.slice(8,10)}/${m.data.slice(5,7)}`;
      const tag = finalitzat
        ? `<span class="live">finalitzat</span>`
        : enJoc
        ? `<span class="live play">en joc</span>`
        : `<span class="live">${dm} · ${m.hora||''}</span>`;
      const cells = jug.map(j=>{
        const pr = (DATA.preds_partits[j]||{})[m.id];
        return `<td class="jcol">${pr?`<b>${pr[0]}-${pr[1]}</b>`:'<span class="muted">·</span>'}</td>`;
      }).join('');
      rows += `<tr>
        <td class="tcol">${teamHtml(m.equip1)} <span class="muted">vs</span> ${teamHtml(m.equip2)}
            <div class="muted" style="font-size:11px">#${m.id} ${tag}</div></td>
        ${cells}</tr>`;
    }
    body.innerHTML = `<div class="card">
      <div class="tscroll"><table class="gtbl">
        <thead><tr>${head}</tr></thead><tbody>${rows}</tbody></table></div>
      <div class="legend">Marcador que ha dit cada jugador per als propers partits ·
        <span class="muted">·</span> = sense predicció ·
        <span class="live play">en joc</span> = ja ha començat (hora peninsular) ·
        <span class="live">finalitzat</span> = han passat +2h de l'inici</div>
    </div>`;
  };
  document.getElementById('selN').onchange = draw;
  draw();
}

// ================= PARTITS =================
function renderPartits(){
  const p = document.getElementById('partits');
  const jug = DATA.jugadors;
  const sel = `<div class="controls">
      <label>Jugador:</label>
      <select id="selJug">${jug.map(j=>`<option>${j}</option>`).join('')}</select>
      <label><input type="checkbox" id="nomesJugats"> només partits amb resultat</label>
    </div>`;
  p.innerHTML = sel + `<div id="partitsBody"></div>`;
  const draw = ()=>{
    const j = document.getElementById('selJug').value;
    const nomesJugats = document.getElementById('nomesJugats').checked;
    const preds = DATA.preds_partits[j] || {};
    const nPred = Object.keys(preds).length;
    let total=0, fase='', html='';
    if(!nPred){
      html = `<div class="card"><div class="empty">${j} encara no ha apuntat cap resultat de partit.<br>
        <span class="muted">Apunta'ls amb: <code>python apunta.py partits "${j}" 1=2-1 ...</code></span></div></div>`;
    } else {
      html = `<div class="card"><table><thead><tr>
          <th>Partit</th>
          <th class="num">Predicció</th>
          <th class="num">Resultat</th>
          <th class="num">Punts</th>
        </tr></thead><tbody>`;
      for(const m of DATA.partits){
        const pred = preds[m.id];
        const real = DATA.resultats[m.id];
        if(nomesJugats && !real) continue;
        if(m.fase!==fase){ fase=m.fase;
          html += `<tr><td colspan="4" class="fase-h">${fase}</td></tr>`; }
        let cls='', pts='';
        if(pred && real){
          const exact = pred[0]==real[0] && pred[1]==real[1];
          const sgnP=Math.sign(pred[0]-pred[1]), sgnR=Math.sign(real[0]-real[1]);
          if(exact){cls='sc-exact';pts='+3';total+=3;}
          else if(sgnP===sgnR){cls='sc-win';pts='+1';total+=1;}
          else {cls='sc-zero';pts='0';}
        }
        const predTxt = pred?`<b>${pred[0]}-${pred[1]}</b>`:'<span class="muted">—</span>';
        const pen = DATA.penals && DATA.penals[m.id];
        const realTxt = real
          ? (pen ? `${real[0]} <span class="muted">(${pen})</span> ${real[1]}` : `${real[0]}-${real[1]}`)
          : '<span class="muted">·</span>';
        html += `<tr class="${cls}">
          <td>${teamHtml(m.equip1)} <span class="muted">vs</span> ${teamHtml(m.equip2)}
              <div class="muted" style="font-size:11px">#${m.id} · ${m.data} ${m.hora}</div></td>
          <td class="num">${predTxt}</td>
          <td class="num">${realTxt}</td>
          <td class="num">${pts}</td>
        </tr>`;
      }
      html += '</tbody></table>';
      html += `<div class="legend"><b>Punts de partits de ${j}: ${total}</b>
        <span style="margin-left:14px"><span class="dot" style="background:#16331f"></span>exacte +3</span>
        <span><span class="dot" style="background:#3a3413"></span>guanyador +1</span></div></div>`;
    }
    document.getElementById('partitsBody').innerHTML = html;
  };
  document.getElementById('selJug').onchange = draw;
  document.getElementById('nomesJugats').onchange = draw;
  draw();
}

// ================= ELIMINATÒRIES (bracket) =================
const P_BY_ID = {};
DATA.partits.forEach(p=>P_BY_ID[p.id]=p);
const ELIM = DATA.eliminatories;
const FONTS = ELIM.fonts;
const CHILD = {};   // id_origen -> [{tid, slot, type}]
Object.entries(FONTS).forEach(([tid, srcs])=>{
  srcs.forEach((s, slot)=>{ (CHILD[s[0]] = CHILD[s[0]] || []).push({tid:+tid, slot, type:s[1]}); });
});
const ROUND_OF = {};
ELIM.rondes.forEach(r=>r.ids.forEach(id=>ROUND_OF[id]=r.titol));
ROUND_OF[ELIM.tercer] = '3r i 4t';
const isCode = s => /^[WL]\d+$/.test(s);
const norm = s => (s||'').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g,'');
const res = id => DATA.resultats[String(id)] || null;
const penOf = id => DATA.penals[String(id)] || '';

// Guanyador d'un partit: pel resultat (90'), penals numèrics, o deduït del partit
// següent ja resolt; per empats amb nota de text, mira el nom dins la nota.
function backDerive(id){
  const ch = (CHILD[id]||[]).find(c=>c.type==='W');
  if(!ch) return null;
  const cm = P_BY_ID[ch.tid]; if(!cm) return null;
  const ct = ch.slot===0 ? cm.equip1 : cm.equip2;
  if(!ct || isCode(ct)) return null;
  const m = P_BY_ID[id];
  if(m.equip1===ct) return 0;
  if(m.equip2===ct) return 1;
  return null;
}
function winnerSlot(id){
  const r = res(id); if(!r) return null;
  if(r[0]>r[1]) return 0;
  if(r[1]>r[0]) return 1;
  const pen = penOf(id);
  const mn = pen.match(/^\s*(\d+)\s*-\s*(\d+)\s*$/);
  if(mn) return (+mn[1] > +mn[2]) ? 0 : 1;
  const bd = backDerive(id); if(bd!=null) return bd;
  const m = P_BY_ID[id], pn = norm(pen);
  if(pn){
    if(!isCode(m.equip1) && pn.includes(norm(m.equip1))) return 0;
    if(!isCode(m.equip2) && pn.includes(norm(m.equip2))) return 1;
  }
  return null;
}
function advancer(id, wantLoser){
  const ws = winnerSlot(id); if(ws==null) return null;
  return teamName(id, wantLoser ? (ws===0?1:0) : ws).name;
}
// Nom d'un equip d'un partit: real si es coneix, si no un placeholder curt.
function teamName(id, slot){
  const m = P_BY_ID[id];
  const raw = slot===0 ? m.equip1 : m.equip2;
  if(!isCode(raw)) return {name:raw, placeholder:false};
  const src = FONTS[String(id)][slot];
  const adv = advancer(src[0], src[1]==='L');
  if(adv) return {name:adv, placeholder:false};
  const a = teamName(src[0],0), b = teamName(src[0],1);
  const lbl = (!a.placeholder && !b.placeholder) ? (a.name+'–'+b.name) : (ROUND_OF[src[0]]||('#'+src[0]));
  return {name:(src[1]==='L'?'Perdedor ':'Guanyador ')+lbl, placeholder:true};
}
function matchCard(id){
  const m = P_BY_ID[id], r = res(id), pen = penOf(id), ws = winnerSlot(id);
  const t0 = teamName(id,0), t1 = teamName(id,1);
  const row = (t, slot, g)=>{
    const cls = t.placeholder ? 'mt-ph' : (ws===slot ? 'mt-win' : (ws!=null ? 'mt-lose' : ''));
    const fl = t.placeholder ? '' : `<span class="flag">${B[t.name]||''}</span>`;
    const sc = r ? `<span class="sc">${g}</span>` : '';
    return `<div class="mt-row ${cls}"><span class="tm">${fl}<span class="nm">${t.name}</span></span>${sc}</div>`;
  };
  const foot = r
    ? (pen ? `<div class="mt-pen">${pen}</div>` : '')
    : `<div class="mt-when">${m.data.slice(8,10)}/${m.data.slice(5,7)} · ${m.hora||''}</div>`;
  return `<div class="mt-card" data-mid="${id}">${row(t0,0,r?r[0]:'')}${row(t1,1,r?r[1]:'')}${foot}</div>`;
}
function renderEliminatories(){
  const p = document.getElementById('eliminatories');
  const cols = ELIM.rondes.map(rnd=>
    `<div class="mt-col"><div class="mt-h">${rnd.titol}</div>`
    + `<div class="mt-col-body">${rnd.ids.map(matchCard).join('')}</div></div>`).join('');
  const third = `<div class="mt-col mt-third"><div class="mt-h">3r i 4t</div>`
    + `<div class="mt-col-body">${matchCard(ELIM.tercer)}</div></div>`;
  p.innerHTML = `
    <div class="legend" style="margin:6px 2px 12px">
      Quadre d'eliminatòries · <b>clica un partit</b> per veure les prediccions dels jugadors ·
      <span style="color:var(--accent);font-weight:700">●</span> guanyador ·
      els partits sense jugar mostren la data i el rival previst.
    </div>
    <div class="bracket-wrap"><div class="bracket-inner">
      <svg class="connectors"></svg>
      <div class="bracket">${cols}${third}</div>
    </div></div>`;
  p.querySelectorAll('.mt-card').forEach(c=>
    c.addEventListener('click', ev=>{ ev.stopPropagation(); openPop(c); }));
  requestAnimationFrame(drawConnectors);
}
function drawConnectors(){
  const inner = document.querySelector('#eliminatories .bracket-inner');
  const svg = inner && inner.querySelector('svg.connectors');
  if(!inner || !svg) return;
  const ir = inner.getBoundingClientRect();
  if(ir.width===0) return;                       // panell amagat: encara no es pot mesurar
  svg.setAttribute('width', inner.offsetWidth);
  svg.setAttribute('height', inner.offsetHeight);
  const card = id => inner.querySelector(`.mt-card[data-mid="${id}"]`);
  let paths = '';
  Object.keys(FONTS).forEach(tid=>{
    const tgt = card(tid); if(!tgt) return;
    const tr = tgt.getBoundingClientRect();
    const x2 = tr.left - ir.left, y2 = tr.top - ir.top + tr.height/2;
    FONTS[tid].forEach(s=>{
      const sc = card(s[0]); if(!sc) return;
      const sr = sc.getBoundingClientRect();
      const x1 = sr.right - ir.left, y1 = sr.top - ir.top + sr.height/2;
      const mx = (x1+x2)/2;
      paths += `<path class="conn${s[1]==='L'?' conn-l':''}" d="M${x1} ${y1} C ${mx} ${y1} ${mx} ${y2} ${x2} ${y2}"/>`;
    });
  });
  svg.innerHTML = paths;
}
// ---- popover
let curPop = null;
function closePop(){ if(curPop){ curPop.remove(); curPop=null; } }
function openPop(cardEl){
  closePop();
  const id = +cardEl.dataset.mid;
  const pop = el(`<div class="pop">${popContent(id)}</div>`);
  pop.addEventListener('click', e=>e.stopPropagation());
  document.body.appendChild(pop);
  const cr = cardEl.getBoundingClientRect();
  const pw = pop.offsetWidth, ph = pop.offsetHeight;
  let left = cr.right + 10;
  if(left + pw > window.innerWidth - 8) left = cr.left - pw - 10;   // no hi cap a la dreta: a l'esquerra
  if(left < 8) left = 8;
  let top = cr.top + cr.height/2 - ph/2;
  top = Math.max(8, Math.min(top, window.innerHeight - ph - 8));
  pop.style.left = (left + window.scrollX) + 'px';
  pop.style.top  = (top + window.scrollY) + 'px';
  curPop = pop;
}
function popContent(id){
  const m = P_BY_ID[id], r = res(id), pen = penOf(id), ws = winnerSlot(id);
  const t0 = teamName(id,0), t1 = teamName(id,1);
  const nm = (t, slot)=>{
    const f = t.placeholder ? '' : `${B[t.name]||''} `;
    const w = ws===slot ? ' style="color:var(--accent);font-weight:700"' : '';
    return `<span${w}>${f}${t.name}</span>`;
  };
  const resLine = r
    ? `<div class="pop-res">${r[0]} ${pen?`<span class="muted">(${pen})</span>`:'-'} ${r[1]}</div>`
    : `<div class="pop-res muted">Per jugar · ${m.data.slice(8,10)}/${m.data.slice(5,7)} ${m.hora||''}</div>`;
  const rows = DATA.jugadors.map(j=>{
    const pr = (DATA.preds_partits[j]||{})[String(id)];
    if(!pr) return `<div class="prow muted"><span>${j}</span><span class="num">·</span></div>`;
    let cls='', pts='';
    if(r){
      const exact = pr[0]===r[0] && pr[1]===r[1];
      const sp = Math.sign(pr[0]-pr[1]), sr = Math.sign(r[0]-r[1]);
      if(exact){ cls='sc-exact'; pts='+3'; }
      else if(sp===sr){ cls='sc-win'; pts='+1'; }
      else { cls=''; pts='0'; }
    }
    return `<div class="prow ${cls}"><span>${j}</span>`
      + `<span class="num">${pr[0]}-${pr[1]}${pts?` <small>${pts}</small>`:''}</span></div>`;
  }).join('');
  return `<div class="pop-title">${nm(t0,0)} <span class="muted">vs</span> ${nm(t1,1)}</div>`
    + `${resLine}<div class="pop-sub">Prediccions</div>${rows}`;
}
document.addEventListener('click', closePop);
window.addEventListener('resize', ()=>{
  closePop();
  if(document.getElementById('eliminatories').classList.contains('active')) drawConnectors();
});

renderClassificacio();
renderPropers();
renderGrups();
renderEliminatories();
renderPartits();

// ================= CELEBRACIÓ DEL GUANYADOR =================
// S'obre automàticament a partir del 20/07/2026 a les 23:00 (fi del Mundial).
// Per provar-ho abans, obre amb ?campio a la URL. Un cop tancada durant la
// sessió no torna a saltar sola, però queda el botó flotant "🏆 Campió" per
// tornar-la a veure sempre que es vulgui.
(function(){
  const overlay = document.getElementById('campio-overlay');
  const card = document.getElementById('campio-card');
  const TRIGGER = new Date(2026, 6, 20, 23, 0, 0);   // 20 juliol 2026, 23:00 (mes 0-indexat)
  const forcada = /(\?|&)campio\b/.test(location.search) || location.hash === '#campio';
  const disponible = forcada || (new Date() >= TRIGGER);
  const podi = DATA.classificacio;              // ja ve ordenada per punts
  const campio = podi[0];
  if(!campio) return;
  const fotos = DATA.fotos || {};

  // Text i mote personalitzats per jugador. Si un jugador no hi és, s'usa un
  // missatge genèric (però igualment amb la invitació a sopar).
  const EXTRA = {
    Pablo: {
      mote: "🍑 L'Oracle de les Bresquilles",
      msg: `Vingut des de <b>València</b>, el que menys futbol mira de tots i, `
         + `tot i així, el que millor endevina els resultats. Un do tan misteriós `
         + `que ja té nom propi: <b>«L'Oracle de les Bresquilles»</b>. 🎉`,
    },
  };
  const extra = EXTRA[campio.jugador] || {
    mote: "",
    msg: `Després de <b>${DATA.partits.length}</b> partits, <b>${campio.jugador}</b> `
       + `s'ha coronat <b>Campió de la Porra Mundial 2026</b>. I com mana la tradició, `
       + `la resta et convidem a <b>sopar</b> per celebrar-ho. Ben merescut! 🍽️🎉`,
  };

  function buildCard(){
    const stat = (v,l) => `<div class="cst"><b>${v}</b><small>${l}</small></div>`;
    const seg = podi.slice(1,3).map((r,i)=>`${['🥈','🥉'][i]} <b>${r.jugador}</b> (${r.punts})`).join(' · ');
    const foto = fotos[campio.jugador];
    const fotoHtml = foto ? `
      <div class="campio-foto">
        <img src="${foto}" alt="${campio.jugador}">
        <span class="espurna e1">✨</span><span class="espurna e2">✨</span><span class="espurna e3">⭐</span>
      </div>` : `<div class="campio-trophy">🏆</div>`;
    card.innerHTML = `
      <button class="campio-close" id="campio-close" title="Tancar">✕</button>
      ${fotoHtml}
      <div class="campio-kicker">Campió de la Porra 2026</div>
      <div class="campio-nom">${campio.jugador}</div>
      ${extra.mote?`<div class="campio-mote">${extra.mote}</div>`:''}
      <div class="campio-sub">Mundial FIFA 2026 · 11 juny – 19 juliol</div>
      <div class="campio-msg">${extra.msg}</div>
      <div class="campio-stats">
        ${stat(campio.punts,'punts')}
        ${stat(campio.exactes,'exactes')}
        ${stat(campio.guanyadors,'1X2')}
        ${stat(campio.grups_ok,'grups OK')}
      </div>
      <button class="campio-btn" id="campio-ok">Veure la classificació final</button>
      ${seg?`<div class="campio-podi">Al podi: ${seg}</div>`:''}`;
    document.getElementById('campio-close').onclick = tanca;
    document.getElementById('campio-ok').onclick = tanca;
  }

  let confetiTimer = null;
  const COLORS = ['#ffd166','#3ddc97','#ff6b6b','#4d96ff','#ffffff','#c77dff'];
  function llancaConfeti(){
    let n = 0;
    confetiTimer = setInterval(()=>{
      for(let k=0;k<6;k++){
        const c = document.createElement('div');
        c.className = 'confeti';
        c.style.left = Math.random()*100 + 'vw';
        c.style.background = COLORS[(Math.random()*COLORS.length)|0];
        const dur = 3 + Math.random()*2.5;
        c.style.animationDuration = dur + 's';
        c.style.opacity = 0.7 + Math.random()*0.3;
        if(Math.random()<0.5) c.style.borderRadius = '50%';
        document.body.appendChild(c);
        setTimeout(()=>c.remove(), dur*1000+200);
      }
      if(++n > 22){ clearInterval(confetiTimer); confetiTimer=null; }  // ~4s de pluja
    }, 180);
  }

  function obre(){
    buildCard();
    overlay.classList.add('show');
    llancaConfeti();
  }
  function tanca(){
    overlay.classList.remove('show');
    if(confetiTimer){ clearInterval(confetiTimer); confetiTimer=null; }
    try{ sessionStorage.setItem('campio_vist','1'); }catch(e){}
  }
  overlay.addEventListener('click', e=>{ if(e.target===overlay) tanca(); });
  document.addEventListener('keydown', e=>{ if(e.key==='Escape' && overlay.classList.contains('show')) tanca(); });

  // Botó flotant per tornar a veure la celebració (visible només un cop disponible).
  const reobrir = document.getElementById('campio-reobre');
  if(disponible && reobrir){
    reobrir.style.display = 'inline-flex';
    reobrir.onclick = obre;
  }

  let jaVist = false;
  try{ jaVist = sessionStorage.getItem('campio_vist')==='1'; }catch(e){}
  if(disponible && (forcada || !jaVist)) setTimeout(obre, forcada?200:700);
})();
</script>
</body>
</html>"""


if __name__ == "__main__":
    main()

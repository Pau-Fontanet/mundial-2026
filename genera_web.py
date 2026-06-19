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

import csv
import json
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

PUNTS_EXACTE = 3
PUNTS_GUANYADOR = 1
PUNTS_GRUP = 3

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


def carrega_resultats() -> dict[int, "tuple[int, int]"]:
    res = {}
    if not RESULTATS.exists():
        return res
    with RESULTATS.open(encoding="utf-8-sig", newline="") as f:
        for fila in csv.DictReader(f):
            try:
                pid = int(fila["partit_id"])
            except (KeyError, ValueError, TypeError):
                continue
            gols = parse_gols(fila)
            if gols is not None:
                res[pid] = gols
    return res


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
        for pid, real in resultats.items():
            if pid not in pp:
                continue
            jugats += 1
            pt = punts(pp[pid], real)
            p_partits += pt
            if pt == PUNTS_EXACTE:
                exactes += 1
            elif pt == PUNTS_GUANYADOR:
                guanyadors += 1
        grups_ok = sum(
            1 for g, ordre in resultats_grups.items() if pg.get(g) == ordre
        )
        taula.append({
            "jugador": jugador,
            "punts": p_partits + grups_ok * PUNTS_GRUP,
            "p_partits": p_partits,
            "p_grups": grups_ok * PUNTS_GRUP,
            "exactes": exactes,
            "guanyadors": guanyadors,
            "grups_ok": grups_ok,
            "partits_puntuats": jugats,
        })
    taula.sort(key=lambda r: (-r["punts"], -r["exactes"], -r["grups_ok"], r["jugador"]))
    return taula


def main() -> None:
    partits = carrega_partits()
    grups = equips_per_grup(partits)
    resultats = carrega_resultats()
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
        "resultats_grups": resultats_grups,
        "classificacio": taula,
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
    --bg:#0f1320; --card:#1a2032; --card2:#222a40; --line:#2c3550;
    --txt:#e9edf6; --muted:#97a1bd; --accent:#3ddc97; --accent2:#ffd166;
    --gold:#ffd166; --green:#2ecc71; --yellow:#f1c40f;
  }
  *{box-sizing:border-box}
  body{margin:0;background:linear-gradient(160deg,#0d1019,#141a2b);color:var(--txt);
       font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;}
  header{padding:28px 20px 10px;text-align:center}
  h1{margin:0;font-size:30px;letter-spacing:.5px}
  h1 .ball{filter:drop-shadow(0 0 8px #ffd16688)}
  .sub{color:var(--muted);margin-top:6px;font-size:14px}
  .wrap{max-width:1100px;margin:0 auto;padding:0 16px 60px}
  .tabs{display:flex;gap:8px;justify-content:center;margin:22px 0 8px;flex-wrap:wrap}
  .tab{background:var(--card);border:1px solid var(--line);color:var(--txt);
       padding:10px 18px;border-radius:999px;cursor:pointer;font-size:15px;transition:.15s}
  .tab:hover{border-color:var(--accent)}
  .tab.active{background:var(--accent);color:#06281c;font-weight:700;border-color:var(--accent)}
  .panel{display:none;animation:fade .25s}
  .panel.active{display:block}
  @keyframes fade{from{opacity:0;transform:translateY(6px)}to{opacity:1}}
  .card{background:var(--card);border:1px solid var(--line);border-radius:16px;
        padding:16px 18px;margin:16px 0;box-shadow:0 8px 30px #0006}
  table{width:100%;border-collapse:collapse;font-size:14px}
  th,td{padding:9px 10px;text-align:left;border-bottom:1px solid var(--line)}
  th{color:var(--muted);font-weight:600;font-size:12px;text-transform:uppercase;letter-spacing:.4px}
  tr:last-child td{border-bottom:none}
  .num{text-align:right;font-variant-numeric:tabular-nums}
  .pill{display:inline-block;padding:2px 9px;border-radius:999px;font-size:12px;font-weight:700}
  .total{font-size:17px;font-weight:800;color:var(--accent)}
  .rank{width:38px;text-align:center;font-weight:800;color:var(--muted)}
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
  .stat{display:inline-flex;flex-direction:column;align-items:center;background:var(--card2);
        border:1px solid var(--line);border-radius:12px;padding:8px 16px;margin:4px}
  .stat b{font-size:20px;color:var(--accent)}
  .stat small{color:var(--muted)}
  .stats{display:flex;justify-content:center;flex-wrap:wrap;margin-top:6px}
</style>
</head>
<body>
<header>
  <h1><span class="ball">⚽</span> Porra Mundial 2026</h1>
  <div class="sub">11 juny – 19 juliol · prediccions i classificació entre amics</div>
  <div class="stats" id="stats"></div>
</header>
<div class="wrap">
  <div class="tabs">
    <button class="tab active" data-tab="classificacio">🏆 Classificació</button>
    <button class="tab" data-tab="propers">⏭️ Propers</button>
    <button class="tab" data-tab="grups">📊 Grups</button>
    <button class="tab" data-tab="partits">⚽ Partits</button>
  </div>
  <div class="panel active" id="classificacio"></div>
  <div class="panel" id="propers"></div>
  <div class="panel" id="grups"></div>
  <div class="panel" id="partits"></div>
</div>

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
});

// ================= CLASSIFICACIÓ =================
function renderClassificacio(){
  const p = document.getElementById('classificacio');
  const t = DATA.classificacio;
  const hiHaResultats = Object.keys(DATA.resultats).length || Object.keys(DATA.resultats_grups).length;
  const medal = i => ['🥇','🥈','🥉'][i] || (i+1);
  let rows = t.map((r,i)=>`
    <tr>
      <td class="rank">${medal(i)}</td>
      <td>${r.jugador}</td>
      <td class="num total">${r.punts}</td>
      <td class="num">${r.p_partits}</td>
      <td class="num">${r.p_grups}</td>
      <td class="num">${r.exactes}</td>
      <td class="num">${r.guanyadors}</td>
      <td class="num">${r.grups_ok}</td>
    </tr>`).join('');
  p.innerHTML = `
    <div class="card">
      ${hiHaResultats?'':'<div class="empty" style="padding:12px">Encara no hi ha resultats reals. La taula s\'omplirà a mesura que omplis <code>data/resultats.csv</code> i <code>data/resultats_grups.csv</code> i tornis a generar la web.</div>'}
      <table>
        <thead><tr>
          <th class="rank">#</th><th>Jugador</th>
          <th class="num">Total</th>
          <th class="num" title="Punts obtinguts encertant resultats de partits">Pts partits</th>
          <th class="num" title="Punts obtinguts encertant el podi dels grups">Pts grups</th>
          <th class="num">Exactes</th><th class="num">1X2</th><th class="num">Grups OK</th>
        </tr></thead>
        <tbody>${rows}</tbody>
      </table>
      <div class="legend">
        <span><b>Total</b> = <b>Pts partits</b> + <b>Pts grups</b> (punts que ha fet cada jugador per partits i per grups)</span>
        <span>Exacte 3p · Guanyador/empat 1p · Grup encertat +3p</span>
      </div>
    </div>`;
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
      const enJoc = !isNaN(ko) && now >= ko;
      const dm = `${m.data.slice(8,10)}/${m.data.slice(5,7)}`;
      const tag = enJoc
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
        <span class="live play">en joc</span> = ja ha començat (hora peninsular)</div>
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
      html = '<div class="card"><table><tbody>';
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
        const realTxt = real?`${real[0]}-${real[1]}`:'<span class="muted">·</span>';
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

renderClassificacio();
renderPropers();
renderGrups();
renderPartits();
</script>
</body>
</html>"""


if __name__ == "__main__":
    main()

"""Regenera la web i la publica a GitHub Pages d'un sol cop.

Fa tres coses seguides:
  1. python genera_web.py   -> refresca docs/index.html amb les dades actuals
  2. git add + commit        -> desa els canvis (resultats, prediccions, web)
  3. git push                -> puja a GitHub; Pages s'actualitza en ~1 minut

Ús:
    python publica.py
    python publica.py "missatge de commit opcional"

Si no hi ha cap canvi, no fa commit ni push (i t'ho diu).
"""

import subprocess
import sys
from datetime import date
from pathlib import Path

DIR = Path(__file__).resolve().parent


def run(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=DIR, text=True, **kw)


def main() -> None:
    # 1) Regenerar la web amb les dades actuals.
    if run([sys.executable, "genera_web.py"]).returncode != 0:
        sys.exit("ERROR generant la web; no es publica res.")

    # 2) Hi ha canvis per pujar?
    estat = run(["git", "status", "--porcelain"], capture_output=True)
    if not estat.stdout.strip():
        print("Res a publicar: no hi ha canvis.")
        return

    missatge = sys.argv[1] if len(sys.argv) > 1 else f"Actualitza porra {date.today():%Y-%m-%d}"
    run(["git", "add", "-A"])
    if run(["git", "commit", "-m", missatge]).returncode != 0:
        sys.exit("ERROR fent el commit.")

    # 3) Pujar a GitHub.
    if run(["git", "push"]).returncode != 0:
        sys.exit("ERROR fent el push.")

    print("\nPublicat. La web s'actualitzara en ~1 minut a GitHub Pages.")


if __name__ == "__main__":
    main()

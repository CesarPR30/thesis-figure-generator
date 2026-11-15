"""Comprueba que este repositorio público solo contiene datos sintéticos.

    python tools/validate_data.py            # archivos versionados (git ls-files)
    python tools/validate_data.py --all      # todo lo que hay en disco, salvo data/privado
    python tools/validate_data.py --dir X    # una carpeta suelta (la usa el pipeline antes de publicar)

Reglas (tools/contract.json):

1. Bajo `data/` solo pueden versionarse los archivos de `allowed`.
2. Cada JSON de datos declara en `meta` que es sintético (`synthetic: true`,
   `dataset: "sintetico"`).
3. `data/privado/` (datos reales para exportar figuras en local) nunca se
   versiona.
4. Ningún archivo de texto contiene rutas absolutas de una máquina.
5. Ningún archivo supera `max_file_mb`.

Solo usa la biblioteca estándar, para correr igual en CI, en el hook de
pre-push y desde el pipeline.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = json.loads((ROOT / "tools" / "contract.json").read_text(encoding="utf-8"))

# C:\Users\..., /Users/..., /home/...: delatan la máquina donde se generó un archivo
RUTA_LOCAL = re.compile(r"[A-Za-z]:[\\/]+(?:Users|Documents and Settings)[\\/]+[^\\/\s\"'`…]+[\\/]"
                        r"|/(?:Users|home)/[^/\s\"'`…]+/")


def versionados() -> list[str]:
    out = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, check=True)
    return [p for p in out.stdout.decode("utf-8").split("\0") if p]


def en_disco() -> list[str]:
    privado = CONTRACT["private_dir"]
    return [p.relative_to(ROOT).as_posix() for p in ROOT.rglob("*")
            if p.is_file() and ".git" not in p.parts
            and not p.relative_to(ROOT).as_posix().startswith(privado + "/")]


def validar_dato(ruta: Path, rel: str, errores: list[str]) -> None:
    carpeta, nombre = rel.rsplit("/", 1)
    permitidos = CONTRACT["allowed"].get(carpeta)
    if permitidos is None or nombre not in permitidos:
        errores.append(f"{rel}: no está en la lista de datos permitidos del contrato")
        return
    try:
        meta = json.loads(ruta.read_text(encoding="utf-8")).get("meta") or {}
    except (ValueError, UnicodeDecodeError) as e:
        errores.append(f"{rel}: JSON ilegible ({e})")
        return
    for clave, valor in CONTRACT["meta_required"].items():
        if meta.get(clave) != valor:
            errores.append(f"{rel}: meta.{clave} = {meta.get(clave)!r}, el contrato exige {valor!r}")


def validar(archivos: list[tuple[Path, str]]) -> list[str]:
    errores: list[str] = []
    privado = CONTRACT["private_dir"]
    tope = CONTRACT["max_file_mb"] * 1024 * 1024
    textos = tuple(CONTRACT["text_extensions"])
    for ruta, rel in archivos:
        if rel.startswith(privado + "/"):
            errores.append(f"{rel}: {privado}/ es solo local y no puede versionarse")
            continue
        if ruta.stat().st_size > tope:
            errores.append(f"{rel}: pesa más de {CONTRACT['max_file_mb']} MB")
        if rel.startswith("data/"):
            validar_dato(ruta, rel, errores)
        if rel.lower().endswith(textos):
            texto = ruta.read_text(encoding="utf-8", errors="replace")
            m = RUTA_LOCAL.search(texto)
            if m:
                errores.append(f"{rel}: contiene una ruta local ({m.group(0)!r}…)")
    return errores


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--all", action="store_true", help="revisar el disco en vez de lo versionado")
    ap.add_argument("--dir", type=Path, help="revisar una carpeta con la forma de data/ (p. ej. un staging)")
    args = ap.parse_args()

    if args.dir:
        base = args.dir.resolve()
        archivos = [(p, "data/" + p.relative_to(base).as_posix()) for p in base.rglob("*") if p.is_file()]
    else:
        rels = en_disco() if args.all else versionados()
        archivos = [(ROOT / r, r) for r in rels if (ROOT / r).is_file()]

    errores = validar(archivos)
    if errores:
        print(f"Contrato {CONTRACT['contract']} v{CONTRACT['version']}: {len(errores)} problema(s)")
        for e in errores:
            print("  ✗", e)
        return 1
    print(f"Contrato {CONTRACT['contract']} v{CONTRACT['version']}: {len(archivos)} archivos revisados, todo en orden.")
    return 0


if __name__ == "__main__":
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    sys.exit(main())

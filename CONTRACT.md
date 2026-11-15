# Contrato de datos — `thesis-figure-generator` v1

Este repositorio es **público**. El contrato dice qué datos puede contener y lo
comprueba [`tools/validate_data.py`](tools/validate_data.py). La versión que se
lee por máquina es [`tools/contract.json`](tools/contract.json).

## Lo que se acepta

| Ruta | Archivos | Condición |
|---|---|---|
| `data/sintetico/` | `explainer.json`, `metodo.json`, `temporal.json` | `meta.synthetic == true` y `meta.dataset == "sintetico"` |

Las figuras exportadas (`img/*.png`, `img/*.svg`) se generan con esos datos.

## Lo que nunca se versiona

- `data/privado/`: datos reales de Lima que el pipeline deja aquí para exportar
  figuras del paper **en local**. Está en `.gitignore` y el validador falla si
  algún archivo de esa carpeta llega a versionarse.
- Rutas absolutas de una máquina (`C:\Users\…`, `/home/…`) en cualquier archivo
  de texto.
- Archivos de más de 50 MB.

## Quién lo comprueba

1. **El pipeline**, antes de copiar: `scripts/publish.py figures` arma los datos
   en una carpeta temporal y ejecuta `tools/validate_data.py --dir` sobre ella.
2. **El hook de pre-push**, en cada clon donde se active con
   `git config core.hooksPath tools/hooks`.
3. **GitHub Actions**: el job `validate` corre antes del despliegue; si falla, el
   sitio no se actualiza.

## Cambiar el contrato

Subir la versión en `tools/contract.json` y en este archivo, y registrar el
motivo como decisión en `thesis-hub/docs/decisions/`.

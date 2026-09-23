# -*- coding: utf-8 -*-
"""
Ponte entre o outorgasys e as skills vendorizadas em ``skills/``.

As tres skills instaladas sao consumidas de forma real pelo Agente 2
(Inteligencia Espacial) e pelo Agente 6 (triagem de defeitos):

* ``skills/shapely-compute``  -> operacoes de geometria computacional pura
  (buffer de raio de seguranca, distancias euclidianas metricas, predicados
  contains/within/intersects, validacao e reparo de geometrias).
* ``skills/geopandas``        -> auditoria de qualidade vetorial antes de
  desenhar (inventario, validade geometrica, plano de reprojecao, auditoria de
  spatial join, checklist de coordenadas sensiveis).
* ``skills/geomaster``        -> referencia normativa de metodos (ver
  ``skills/geomaster/references/coordinate-systems.md``), usada para documentar
  as escolhas geodesicas no relatorio.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Sequence

from .. import config as C

SKILLS_DIR = C.ROOT / "skills"
SHAPELY_CLI = SKILLS_DIR / "shapely-compute" / "shapely_compute.py"
GEOPANDAS_CLI_DIR = SKILLS_DIR / "geopandas" / "scripts"
GEOMASTER_DIR = SKILLS_DIR / "geomaster"


class SkillError(RuntimeError):
    """Falha ao executar uma skill vendorizada."""


def skills_disponiveis() -> dict[str, bool]:
    return {
        "shapely-compute": SHAPELY_CLI.exists(),
        "geopandas": (GEOPANDAS_CLI_DIR / "vector_inventory.py").exists(),
        "geomaster": (GEOMASTER_DIR / "SKILL.md").exists(),
        "python": shutil.which("python") or shutil.which("python3") or sys.executable,
    }


def _python() -> str:
    return sys.executable or shutil.which("python3") or "python3"


# --------------------------------------------------------------------------------------
# Skill: shapely-compute
# --------------------------------------------------------------------------------------


def shapely_compute(*args: str, timeout: int = 60) -> dict:
    """Executa ``skills/shapely-compute/shapely_compute.py`` e devolve o JSON.

    Exemplos:
        shapely_compute("op", "buffer", "--g1", "POINT (0 0)", "--g2", "500", "--json")
        shapely_compute("distance", "--g1", "POINT (...)", "--g2", "LINESTRING (...)", "--json")
        shapely_compute("pred", "contains", "--g1", "POLYGON (...)", "--g2", "POINT (...)", "--json")
    """
    if not SHAPELY_CLI.exists():
        raise SkillError("skill shapely-compute nao encontrada em skills/shapely-compute")

    argv = [_python(), str(SHAPELY_CLI), *args]
    if "--json" not in argv:
        argv.append("--json")

    proc = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
    if proc.returncode != 0:
        raise SkillError(
            f"shapely-compute falhou (rc={proc.returncode}): "
            f"{proc.stderr.strip() or proc.stdout.strip()[:400]}"
        )
    out = proc.stdout.strip()
    # O script imprime texto legivel seguido de JSON quando --json e pedido;
    # localiza o ultimo bloco JSON valido.
    decodificadores = (json.loads,)
    for dec in decodificadores:
        try:
            return dec(out)
        except Exception:  # noqa: BLE001
            pass
    ini = out.find("{")
    fim = out.rfind("}")
    if ini != -1 and fim > ini:
        return json.loads(out[ini: fim + 1])
    raise SkillError(f"saida nao JSON do shapely-compute: {out[:300]}")


def buffer_raio_seguranca(utm_e: float, utm_n: float, raio_m: float = C.RAIO_SEGURANCA_M) -> dict:
    """Gera o buffer de seguranca usando a skill shapely-compute (em UTM)."""
    return shapely_compute(
        "op", "buffer",
        "--g1", f"POINT ({utm_e:.6f} {utm_n:.6f})",
        "--g2", f"{raio_m:g}",
    )


def distancia_metrica(wkt_a: str, wkt_b: str) -> float | None:
    """Distancia euclidiana em metros entre duas geometrias ja em CRS projetado."""
    try:
        r = shapely_compute("distance", "--g1", wkt_a, "--g2", wkt_b)
    except Exception:  # noqa: BLE001
        return None
    for k in ("distance", "distancia", "value"):
        if isinstance(r, dict) and k in r:
            try:
                return float(r[k])
            except (TypeError, ValueError):
                return None
    return None


def pred_geometria(predicado: str, wkt_a: str, wkt_b: str) -> bool | None:
    """Predicado binario via skill shapely-compute."""
    try:
        r = shapely_compute("pred", predicado, "--g1", wkt_a, "--g2", wkt_b)
    except Exception:  # noqa: BLE001
        return None
    if isinstance(r, dict):
        for k in ("result", "resultado", "value", "predicate_result", predicado):
            if k in r:
                return bool(r[k])
    return None


def medir(geom_wkt: str, o_que: str = "all") -> dict | None:
    try:
        return shapely_compute("measure", o_que, "--geom", geom_wkt)
    except Exception:  # noqa: BLE001
        return None


def validar_geometria(geom_wkt: str) -> dict | None:
    try:
        return shapely_compute("validate", "--geom", geom_wkt)
    except Exception:  # noqa: BLE001
        return None


# --------------------------------------------------------------------------------------
# Skill: geopandas (scripts de auditoria)
# --------------------------------------------------------------------------------------


def geopandas_skill(script: str, *args: str, timeout: int = 180) -> dict:
    """Executa um script CLI da skill geopandas e devolve o JSON emitido.

    Os scripts importam ``_common`` do proprio diretorio, por isso o processo e
    lancado com ``cwd`` apontando para a pasta de scripts.
    """
    path = GEOPANDAS_CLI_DIR / script
    if not path.exists():
        raise SkillError(f"script da skill geopandas nao encontrado: {script}")

    proc = subprocess.run(
        [_python(), str(path), *args],
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=str(GEOPANDAS_CLI_DIR),
    )
    out = (proc.stdout or "").strip()
    ini, fim = out.find("{"), out.rfind("}")
    if ini != -1 and fim > ini:
        try:
            payload = json.loads(out[ini: fim + 1])
        except Exception as exc:  # noqa: BLE001
            raise SkillError(f"JSON invalido em {script}: {exc}") from exc
        if proc.returncode != 0:
            payload.setdefault("_erro", f"rc={proc.returncode}")
            payload.setdefault("_stderr", proc.stderr.strip()[:500])
        return payload
    if proc.returncode != 0:
        raise SkillError(
            f"{script} falhou (rc={proc.returncode}): "
            f"{(proc.stderr or proc.stdout or '').strip()[:500]}"
        )
    raise SkillError(f"{script} nao emitiu JSON: {out[:300]}")


def inventario_vetorial(caminho: Path, root: Path | None = None) -> dict:
    """Inventario redigido (somente metadados) de um arquivo vetorial local."""
    return geopandas_skill(
        "vector_inventory.py",
        str(caminho),
        "--root", str(root or C.DATA),
    )


def relatorio_validade_geometrica(caminho: Path, root: Path | None = None) -> dict:
    """Auditoria de geometrias nulas/vazias/invalidas (dry-run, nao escreve)."""
    return geopandas_skill(
        "geometry_validity_report.py",
        str(caminho),
        "--root", str(root or C.DATA),
    )


def plano_reprojecao(origem: str, destino: str, operacao: str = "distance") -> dict:
    """Plano de transformacao de CRS/datum sem transformar coordenadas."""
    return geopandas_skill(
        "crs_reprojection_plan.py",
        "--source-crs", origem,
        "--target-crs", destino,
        "--operation", operacao,
    )


def checklist_coordenadas_sensiveis(**flags: bool) -> dict:
    """Checklist de privacidade/generalizacao de coordenadas antes de publicar."""
    known = {
        "precise_points", "contains_addresses", "trajectories",
        "parcel_boundaries", "rare_categories", "linked_identifiers",
        "public_output",
    }
    argv: list[str] = ["sensitive_coordinates_checklist.py", "--audience", "restricted-team"]
    for k, v in flags.items():
        if k in known and v:
            argv.append("--" + k.replace("_", "-"))
    return geopandas_skill(*argv)


def auditoria_spatial_join(a: Path, b: Path, predicado: str = "intersects",
                           root: Path | None = None) -> dict:
    """Auditoria agregada de um spatial join binario."""
    return geopandas_skill(
        "spatial_join_audit.py",
        str(a), str(b),
        "--predicate", predicado,
        "--root", str(root or C.DATA),
    )


# --------------------------------------------------------------------------------------
# Skill: geomaster (referencia normativa)
# --------------------------------------------------------------------------------------


def referencia_geomaster(doc: str) -> str | None:
    """Le um documento de referencia da skill geomaster."""
    p = GEOMASTER_DIR / "references" / doc
    if not p.exists():
        return None
    return p.read_text(encoding="utf-8", errors="replace")


def trecho_referencia(doc: str, marcador: str, linhas: int = 20) -> str | None:
    """Extrai um trecho de uma referencia da skill geomaster a partir de um marcador."""
    txt = referencia_geomaster(doc)
    if not txt:
        return None
    i = txt.lower().find(marcador.lower())
    if i == -1:
        return None
    return "\n".join(txt[i:].splitlines()[:linhas])

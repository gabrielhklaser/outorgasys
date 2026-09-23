# -*- coding: utf-8 -*-
"""
Agente 6 - Triagem de Defeitos e Engenharia de Correcoes.

Ultimo elo da cadeia: coleta sistematicamente todos os erros, avisos, pendencias
e degradacoes registrados pelos Agentes 1 a 5, classifica-os por severidade e
agente responsavel, cruza com o estado do ambiente (habilidades instaladas,
pacotes, bases vetoriais) e produz um plano de correcao priorizado, com passos
concretos e corpo de issue pronto para registro.

Nao executa acoes externas por conta propria: gera os artefatos e deixa a
decisao de abrir issue/commitar para o operador.
"""

from __future__ import annotations

import datetime as dt
import json
import platform
import sys
import traceback
from pathlib import Path
from typing import Any, Iterable

from .. import config as C
from ..gis import layers
from ..gis import skill_bridge as skills

SEVERIDADES = {
    "critico": 0,      # impede a emissao do relatorio
    "alto": 1,         # compromete a qualidade tecnica do laudo
    "medio": 2,        # degradacao ou dado ausente
    "baixo": 3,        # melhoria / boa pratica
    "info": 4,
}

# Camadas oficiais indisponiveis neste ambiente que ja possuem substituto
# declarado e aplicado pelo Agente 2. A ausencia continua sendo registrada (com
# severidade "info"), mas nao e tratada como defeito do processo: a origem
# alternativa e sempre declarada no laudo.
ORIGEM_MANUAL = "registro manual (interface)"

SUBSTITUTOS_CAMADAS: dict[str, str] = {
    "cursos_dagua_rs": "drenagem_rs (IBGE BC250 2021) - mesma rede hidrografica, "
                       "em formato de eixos, ja usada no calculo de distancia",
    "regioes_hidrograficas": "tabela de referencia curada do outorgasys "
                             "(outorgasys/gis/data/bacias_rs.json) - CNRH Res. 32/2003 "
                             "e CRH-RS UGRH",
    "uph": "nao ha substituto direto; a UPH nao e determinada quando a base da "
           "ANA esta indisponivel (campo fica em branco no laudo)",
    "ottobacias_rs": "tabela de referencia curada do outorgasys",
    "otto_nivel_1": "tabela de referencia curada do outorgasys",
    "otto_nivel_2": "tabela de referencia curada do outorgasys",
    "otto_nivel_3": "tabela de referencia curada do outorgasys",
    "otto_nivel_4": "tabela de referencia curada do outorgasys",
    "osm": "cache local do Overpass; sem rede a plataforma segue apenas com as "
           "bases estatais e as camadas enviadas pelo usuario",
    "rodovias_rs": "vias do OpenStreetMap (highway) - ja usadas no Mapa 1 "
                   "(localizacao e situacao)",
    "nascentes_rs": "nascentes do OpenStreetMap (natural=spring) - ja usadas no "
                    "Mapa 3 (hidrografico e hidrogeologico)",
}

CATEGORIAS = {
    "dados_entrada": ("Dados de entrada", 1),
    "regra_negocio": ("Regra de negocio / SIOUT", 1),
    "geoespacial": ("Base geoespacial", 2),
    "hidrogeologia": ("Calculo hidrogeologico", 3),
    "equipamentos": ("Equipamentos e balanco", 4),
    "relatorio": ("Relatorio / saida", 5),
    "ambiente": ("Ambiente e dependencias", None),
    "habilidade": ("Skills vendorizadas", None),
}


# --------------------------------------------------------------------------------------
# Coleta
# --------------------------------------------------------------------------------------


def _iter_dict(d: Any, prefixo: str = "") -> Iterable[tuple[str, Any]]:
    if isinstance(d, dict):
        for k, v in d.items():
            yield from _iter_dict(v, f"{prefixo}.{k}" if prefixo else str(k))
    elif isinstance(d, list):
        for i, v in enumerate(d):
            yield from _iter_dict(v, f"{prefixo}[{i}]")
    else:
        yield prefixo, d


def coletar(proc) -> list[dict]:
    """Varre o processo e o ambiente, devolvendo a lista normalizada de defeitos."""
    achados: list[dict] = []

    def add(categoria: str, severidade: str, titulo: str, detalhe: str = "",
            agente: int | None = None, origem: str = "", sugestao: str = "") -> None:
        achados.append({
            "id": f"D{len(achados) + 1:03d}",
            "categoria": categoria,
            "categoria_rotulo": CATEGORIAS.get(categoria, (categoria, None))[0],
            "severidade": severidade,
            "titulo": titulo,
            "detalhe": detalhe,
            "agente": agente or CATEGORIAS.get(categoria, (categoria, None))[1],
            "origem": origem or f"processo {proc.id}",
            "sugestao": sugestao,
        })

    # ---- defeitos registrados MANUALMENTE pela interface --------------------------------
    # (os achados de execucoes anteriores do proprio Agente 6 sao recalculados do zero;
    #  reingeri-los aqui duplicaria a cada execucao)
    for it in (proc.get("issues") or []):
        if (it.get("origem") or "") == ORIGEM_MANUAL:
            add(it.get("categoria", "ambiente"), it.get("severidade", "medio"),
                it.get("titulo", "Defeito registrado"), it.get("detalhe", ""),
                it.get("agente"), it.get("origem"), it.get("sugestao"))

    # ---- log do processo -----------------------------------------------------------------
    for linha in (proc.get("log") or []):
        if linha.get("nivel") in ("erro", "error"):
            add("ambiente", "alto", f"[{linha.get('agente')}] {linha.get('mensagem')}",
                origem="log do processo")

    # ---- Agente 1 ------------------------------------------------------------------------
    try:
        from .. import rules
        from . import agente1_triagem

        res = agente1_triagem.validar(proc)
        for p in res:
            add("regra_negocio" if not p.codigo.startswith("HID")
                else "equipamentos",
                "critico" if p.bloqueante else "medio",
                f"{p.codigo} - {p.titulo}", p.mensagem, agente=1,
                origem="Agente 1 (triagem)", sugestao=p.sugestao or "")
    except Exception as exc:  # noqa: BLE001
        add("ambiente", "alto", "Falha ao revalidar o Agente 1",
            f"{type(exc).__name__}: {exc}", agente=1)

    # ---- Agente 2 ------------------------------------------------------------------------
    geo = proc.get("geoespacial") or {}
    for erro in (geo.get("erros") or []):
        add("geoespacial", "alto", "Erro no Agente 2 (geoespacial)", erro,
            agente=2, origem="Agente 2")
    for p in (geo.get("pendencias") or []):
        add("geoespacial" if str(p.get("codigo", "")).startswith(("GEO", "BUF", "HID-1"))
            else "dados_entrada",
            "critico" if p.get("bloqueante") else "medio",
            f"{p.get('codigo')} - {p.get('titulo')}",
            p.get("mensagem", ""), agente=2, origem="Agente 2",
            sugestao=p.get("sugestao") or "")
    for chave, info in (geo.get("proveniencia") or {}).items():
        status = (info or {}).get("status")
        if status in ("ausente", "erro", "vazia"):
            obrigatoria = chave in layers.CAMADAS and layers.CAMADAS[chave].obrigatoria
            substituto = SUBSTITUTOS_CAMADAS.get(chave)
            if substituto:
                # Ja ha substituto declarado e aplicado: nao e defeito do
                # processo, e limitacao de ambiente com mitigacao documentada.
                add("geoespacial", "info",
                    f"Camada oficial ausente, com substituto declarado: {chave}",
                    f"status={status}; {info.get('mensagem', '')} | "
                    f"Substituto aplicado: {substituto}. A origem alternativa "
                    "esta declarada no laudo, conforme a politica de fallback "
                    "local adotada para este ambiente.",
                    agente=2, origem="Agente 2 / registro de camadas",
                    sugestao=("Se desejar a base oficial, deposite o arquivo em "
                              f"data/vetoriais/{layers.CAMADAS[chave].arquivo}."
                              if chave in layers.CAMADAS else
                              "Forneca a camada via upload no Agente 2."))
            else:
                add("geoespacial",
                    "alto" if obrigatoria else "medio",
                    f"Base vetorial indisponivel: {chave}",
                    f"status={status}; {info.get('mensagem', '')}",
                    agente=2, origem="Agente 2 / registro de camadas",
                    sugestao=("Execute o workflow 'build-vetorial-data' ou deposite "
                              f"o arquivo em data/vetoriais/{layers.CAMADAS[chave].arquivo}"
                              if chave in layers.CAMADAS else
                              "Forneca a camada via upload no Agente 2."))
    if geo and not geo.get("caminho_mapas"):
        add("relatorio", "alto", "Mapas nao gerados",
            "O Agente 2 nao produziu as tres pranchas cartograficas.", agente=2)

    # Camadas registradas no inventario mas ausentes do disco, que o Agente 2
    # nao chegou a carregar (e por isso nao entraram na proveniencia).
    vistas = set(geo.get("proveniencia") or {})
    for c in layers.inventario_bases():
        if c.get("existe") or c["chave"] in vistas:
            continue
        substituto = SUBSTITUTOS_CAMADAS.get(c["chave"])
        add("geoespacial",
            "info" if substituto else ("alto" if c.get("obrigatoria") else "medio"),
            (f"Camada do inventario ausente, com substituto declarado: {c['chave']}"
             if substituto else f"Camada do inventario ausente: {c['chave']}"),
            f"status={c.get('status')}; {c.get('mensagem', '')}"
            + (f" | Substituto aplicado: {substituto}" if substituto else ""),
            agente=2, origem="Agente 2 / inventario de bases",
            sugestao=f"Deposite o arquivo em data/vetoriais/{c.get('arquivo')}."
            if c.get("arquivo") else "Forneca a camada via upload no Agente 2.")

    # ---- Agente 3 ------------------------------------------------------------------------
    hid = proc.get("hidraulica") or proc.get("hidrogeologia") or {}
    for erro in (hid.get("erros") or []):
        add("hidrogeologia", "alto", "Erro no calculo hidrogeologico", erro,
            agente=3, origem="Agente 3")
    for aviso in (hid.get("avisos") or []):
        add("hidrogeologia", "medio", "Ressalva no calculo hidrogeologico", aviso,
            agente=3, origem="Agente 3")
    if hid and not (hid.get("parametros") or {}).get("Q_ot_m3h"):
        add("hidrogeologia", "medio",
            "Vazao otima (Q_ot) nao calculada",
            "Sem Q_ot o balanco hidrico perde a referencia de longo prazo. "
            "Verifique se a fase de recuperacao foi informada na planilha.",
            agente=3, origem="Agente 3",
            sugestao="Preencha a aba 03_Recuperacao do modelo de planilha.")

    # ---- Agente 4 ------------------------------------------------------------------------
    bal = proc.get("balanco") or {}
    for erro in (bal.get("erros") or []):
        add("equipamentos", "alto", "Erro no balanco hidrico", erro, agente=4)
    for aviso in (bal.get("avisos") or []):
        add("equipamentos", "medio", "Ressalva no balanco hidrico", aviso, agente=4)
    for p in (bal.get("pendencias") or []):
        add("equipamentos" if p.get("bloqueante") else "regra_negocio",
            "critico" if p.get("bloqueante") else "medio",
            f"{p.get('codigo')} - {p.get('titulo')}", p.get("mensagem", ""),
            agente=4, origem="Agente 4")
    if bal and not bal.get("quadro"):
        add("equipamentos", "alto", "Quadro de vazoes nao montado",
            "O Quadro de Vazao da Intervencao e obrigatorio no SIOUT RS.", agente=4)

    # ---- Agente 5 ------------------------------------------------------------------------
    rel = proc.get("relatorio") or {}
    for erro in (rel.get("erros") or []):
        add("relatorio", "critico", "Erro na emissao do relatorio", erro, agente=5)

    # ---- ambiente e habilidades -------------------------------------------------------------
    for achado in diagnosticar_ambiente():
        achados.append(achado)

    # deduplicacao por (categoria, titulo)
    vistos: set[tuple[str, str]] = set()
    unicos: list[dict] = []
    for a in achados:
        chave = (a["categoria"], a["titulo"][:120])
        if chave in vistos:
            continue
        vistos.add(chave)
        unicos.append(a)

    # reordena ids
    for i, a in enumerate(unicos, 1):
        a["id"] = f"D{i:03d}"
    return unicos


# --------------------------------------------------------------------------------------
# Diagnostico do ambiente
# --------------------------------------------------------------------------------------


def diagnosticar_ambiente() -> list[dict]:
    """Verifica dependencias, habilidades vendorizadas e bases vetoriais."""
    saida: list[dict] = []

    def add(cat, sev, titulo, detalhe="", sugestao=""):
        saida.append({
            "id": "-", "categoria": cat,
            "categoria_rotulo": CATEGORIAS.get(cat, (cat, None))[0],
            "severidade": sev, "titulo": titulo, "detalhe": detalhe,
            "agente": CATEGORIAS.get(cat, (cat, None))[1],
            "origem": "diagnostico de ambiente", "sugestao": sugestao,
        })

    # --- pacotes ------------------------------------------------------------------------
    obrigatorios = ["geopandas", "shapely", "pyproj", "fiona", "rasterio",
                    "folium", "contextily", "matplotlib", "pandas", "numpy",
                    "openpyxl", "scipy", "reportlab", "streamlit"]
    faltando = []
    for m in obrigatorios:
        try:
            __import__(m)
        except Exception:  # noqa: BLE001
            faltando.append(m)
    if faltando:
        add("ambiente", "critico", "Dependencias ausentes",
            f"Pacotes nao importaveis: {', '.join(faltando)}",
            "Reinstale com: pip install -r requirements.txt")

    # --- skills ---------------------------------------------------------------------------
    disp = skills.skills_disponiveis()
    for nome, ok in disp.items():
        if nome == "python":
            continue
        if not ok:
            add("habilidade", "alto", f"Skill '{nome}' nao encontrada",
                f"Esperado em skills/{nome}/",
                "Reexecute a vendorizacao das skills a partir dos repositorios de origem.")
    # Smoke test da skill shapely-compute.
    if disp.get("shapely-compute"):
        try:
            r = skills.buffer_raio_seguranca(494800, 6716200, C.RAIO_SEGURANCA_M)
            if not r.get("wkt"):
                add("habilidade", "alto", "Skill shapely-compute sem saida utilizavel",
                    "O buffer de raio de seguranca nao retornou WKT.")
        except Exception as exc:  # noqa: BLE001
            add("habilidade", "alto", "Skill shapely-compute falhou no smoke test",
                f"{type(exc).__name__}: {exc}")
    if disp.get("geopandas"):
        try:
            alvos = [k for k in ("geologia_rs", "municipios_rs", "drenagem_rs")
                     if layers.caminho_camada(k).exists()]
            if alvos:
                r = skills.relatorio_validade_geometrica(layers.caminho_camada(alvos[0]),
                                                         C.DATA)
                if isinstance(r, dict) and r.get("erro"):
                    add("habilidade", "baixo",
                        "Skill geopandas retornou erro no preflight",
                        str(r.get("erro"))[:200])
        except Exception as exc:  # noqa: BLE001
            add("habilidade", "baixo", "Preflight da skill geopandas indisponivel",
                f"{type(exc).__name__}: {exc}")

    # --- bases vetoriais ---------------------------------------------------------------------
    inventario = layers.inventario_bases()
    ausentes = [c["chave"] for c in inventario
                if c.get("obrigatoria") and not c.get("existe")]
    sem_substituto = [c for c in ausentes if c not in SUBSTITUTOS_CAMADAS]
    com_substituto = [c for c in ausentes if c in SUBSTITUTOS_CAMADAS]
    if sem_substituto:
        add("geoespacial", "alto", "Camadas obrigatorias ausentes",
            f"{', '.join(sem_substituto)}",
            "Execute o workflow 'build-vetorial-data' no GitHub Actions ou deposite "
            "os arquivos correspondentes em data/vetoriais/.")
    if com_substituto:
        add("geoespacial", "info",
            "Camadas obrigatorias ausentes, porem com substituto declarado",
            f"{', '.join(com_substituto)}. Mitigacao: " +
            " | ".join(f"{c} -> {SUBSTITUTOS_CAMADAS[c]}" for c in com_substituto),
            "Nenhuma acao obrigatoria: a origem alternativa e declarada no laudo.")

    # --- fundamentais para o relatorio ---------------------------------------------------------
    try:
        from PIL import Image  # noqa: F401
    except Exception:  # noqa: BLE001
        add("ambiente", "baixo", "Pillow ausente",
            "Sem Pillow as imagens dos mapas entram no PDF em escala fixa.",
            "pip install pillow")

    return saida


# --------------------------------------------------------------------------------------
# Plano de correcao
# --------------------------------------------------------------------------------------


def plano_correcao(achados: list[dict]) -> list[dict]:
    """Ordena por severidade e agente, anexando o passo a passo de correcao."""
    ordenado = sorted(achados, key=lambda a: (SEVERIDADES.get(a["severidade"], 9),
                                              a["agente"] or 99, a["id"]))
    for a in ordenado:
        a["correcao"] = _passos_correcao(a)
    return ordenado


def _passos_correcao(a: dict) -> list[str]:
    cat = a["categoria"]
    if cat == "geoespacial":
        return [
            "Confirmar se o arquivo da camada existe em data/vetoriais/.",
            "Se ausente, executar o workflow 'build-vetorial-data' no GitHub Actions.",
            "Se o servidor de origem estiver bloqueado, converter a base no ambiente "
            "do usuario e depositar o .gpkg em data/vetoriais/.",
            "Reprocessar o Agente 2 para o ponto informado.",
        ]
    if cat == "regra_negocio":
        return [
            "Revisar o valor informado no formulario do Agente 1.",
            "Consultar a regra correspondente em outorgasys/rules.py.",
            "Ajustar a entrada e revalidar a triagem.",
        ]
    if cat == "dados_entrada":
        return [
            "Solicitar ao requerente a complementacao do dado faltante.",
            "Revalidar o Agente 1 ate que nao haja pendencias bloqueantes.",
        ]
    if cat == "hidrogeologia":
        return [
            "Conferir a planilha de ensaio (abas 02_Bombeamento e 03_Recuperacao).",
            "Verificar se NE, ND e as leituras de recuperacao estao consistentes.",
            "Reprocessar o Agente 3 e conferir o R2 da reta de recuperacao.",
        ]
    if cat == "equipamentos":
        return [
            "Comparar a vazao adotada com a curva da bomba e a classe do hidrometro.",
            "Ajustar o equipamento ou reduzir o regime de bombeamento.",
            "Reprocessar o Agente 4.",
        ]
    if cat == "relatorio":
        return [
            "Reprocessar os agentes anteriores para eliminar a causa raiz.",
            "Reemitir o relatorio no Agente 5.",
        ]
    if cat == "ambiente":
        return [
            "Reinstalar as dependencias: pip install -r requirements.txt.",
            "Reiniciar a aplicacao.",
        ]
    if cat == "habilidade":
        return [
            f"Verificar o conteudo de skills/.",
            "Reexecutar a vendorizacao a partir do repositorio de origem.",
            "Rodar o smoke test pela Interface do Agente 6.",
        ]
    return ["Registrar o defeito e encaminhar para analise tecnica."]


def resumo(achados: list[dict]) -> dict:
    por_sev: dict[str, int] = {}
    por_agente: dict[str, int] = {}
    por_cat: dict[str, int] = {}
    for a in achados:
        por_sev[a["severidade"]] = por_sev.get(a["severidade"], 0) + 1
        k = str(a["agente"] or "-")
        por_agente[k] = por_agente.get(k, 0) + 1
        por_cat[a["categoria_rotulo"]] = por_cat.get(a["categoria_rotulo"], 0) + 1
    return {
        "total": len(achados),
        "por_severidade": por_sev,
        "por_agente": por_agente,
        "por_categoria": por_cat,
        "bloqueantes": sum(1 for a in achados if a["severidade"] == "critico"),
    }


# --------------------------------------------------------------------------------------
# Relatorio de defeitos
# --------------------------------------------------------------------------------------


def relatorio_markdown(proc, achados: list[dict]) -> str:
    r = resumo(achados)
    L = [
        "# RELATORIO DE DEFEITOS E PLANO DE CORRECAO",
        "",
        f"**Processo:** {proc.id}  ",
        f"**Gerado em:** {dt.datetime.now().strftime('%d/%m/%Y %H:%M:%S')}  ",
        f"**Sistema:** {C.NOME_SISTEMA} v{C.VERSAO}",
        "",
        "## 1. Resumo",
        "",
        f"- Total de achados: **{r['total']}**",
        f"- Bloqueantes (criticos): **{r['bloqueantes']}**",
        "",
        "| Severidade | Quantidade |",
        "|---|---|",
    ]
    for sev in sorted(SEVERIDADES, key=lambda s: SEVERIDADES[s]):
        if sev in r["por_severidade"]:
            L.append(f"| {sev} | {r['por_severidade'][sev]} |")
    L += ["", "| Agente | Quantidade |", "|---|---|"]
    for k in sorted(r["por_agente"]):
        rotulo = C.AGENTES.get(int(k), (f"Agente {k}", ""))[0] if k.isdigit() else "Ambiente"
        L.append(f"| {k} - {rotulo} | {r['por_agente'][k]} |")
    L += ["", "| Categoria | Quantidade |", "|---|---|"]
    for k, v in sorted(r["por_categoria"].items(), key=lambda t: -t[1]):
        L.append(f"| {k} | {v} |")

    L += ["", "## 2. Ambiente", "", "```json",
          json.dumps({
              "python": sys.version.split()[0],
              "plataforma": platform.platform(),
              "skills": skills.skills_disponiveis(),
          }, indent=2, ensure_ascii=False),
          "```", "", "## 3. Achados e plano de correcao", ""]

    for a in achados:
        L += [
            f"### {a['id']} - [{a['severidade'].upper()}] {a['titulo']}",
            "",
            f"- **Categoria:** {a['categoria_rotulo']}",
            f"- **Agente responsavel:** {a['agente'] or 'N/A'}",
            f"- **Origem:** {a['origem']}",
        ]
        if a["detalhe"]:
            L.append(f"- **Detalhe:** {a['detalhe']}")
        if a["sugestao"]:
            L.append(f"- **Sugestao:** {a['sugestao']}")
        L += ["", "**Passos de correcao:**"]
        for i, passo in enumerate(a.get("correcao", []), 1):
            L.append(f"{i}. {passo}")
        L.append("")

    L += [
        "---",
        "",
        "## 4. Como registrar",
        "",
        "O corpo da issue do GitHub para cada achado pode ser gerado pela interface do "
        "Agente 6 (botao de copia). Nenhuma acao externa e executada automaticamente: "
        "a abertura de issues e a submissao de commits ficam a cargo do operador.",
    ]
    return "\n".join(L)


def corpo_issue(a: dict) -> str:
    """Corpo de issue em Markdown para um unico achado."""
    return f"""## Defeito - {a['id']}

**Severidade:** `{a['severidade']}`
**Categoria:** {a['categoria_rotulo']}
**Agente responsavel:** {a['agente'] or 'N/A'}
**Origem:** {a['origem']}

### Descricao

{a['titulo']}

{a['detalhe'] or '_Sem detalhes adicionais._'}

### Sugestao

{a['sugestao'] or '_Nenhuma sugestao automatica._'}

### Plano de correcao

""" + "\n".join(f"- [ ] {p}" for p in a.get("correcao", [])) + f"""

### Ambiente

- Sistema: {C.NOME_SISTEMA} v{C.VERSAO}
- Python: {sys.version.split()[0]}
- Plataforma: {platform.platform()}

> Gerado automaticamente pelo Agente 6 (triagem de defeitos).
"""


# --------------------------------------------------------------------------------------
# API
# --------------------------------------------------------------------------------------


def executar(proc, salvar: bool = True) -> dict:
    """Roda o Agente 6 e devolve o relatorio consolidado."""
    saida: dict[str, Any] = {"ok": False, "resumo": {}, "achados": [], "arquivo": None}
    try:
        achados = plano_correcao(coletar(proc))
        saida["achados"] = achados
        saida["resumo"] = resumo(achados)
        if salvar:
            destino = C.SAIDA / f"defeitos_{proc.id}.md"
            destino.write_text(relatorio_markdown(proc, achados), encoding="utf-8")
            saida["arquivo"] = C.caminho_relativo(destino)
        proc.data["issues"] = achados
        proc.concluir_agente(6)
        proc.log(6, f"Triagem concluida: {saida['resumo'].get('total', 0)} achados.")
        saida["ok"] = True
    except Exception as exc:  # noqa: BLE001
        saida["erro"] = f"{type(exc).__name__}: {exc}"
        saida["traceback"] = traceback.format_exc(limit=8)
    return saida


def registrar(proc, titulo: str, detalhe: str = "", categoria: str = "ambiente",
              severidade: str = "medio", agente: int | None = None,
              sugestao: str = "") -> dict:
    """Registra manualmente um novo defeito no processo (usado pela UI)."""
    origem = ORIGEM_MANUAL
    issue = {
        "categoria": categoria, "severidade": severidade, "titulo": titulo,
        "detalhe": detalhe, "agente": agente, "sugestao": sugestao,
        "origem": origem,
        "registrado_em": dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    proc.add_issue(issue)
    proc.log(6, f"Defeito registrado manualmente: {titulo}", nivel="erro")
    return issue

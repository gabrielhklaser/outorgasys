# -*- coding: utf-8 -*-
"""
Gera o processo de exemplo do OutorgaSys (poco tubular em Campo Bom/RS).

Percorre os seis agentes na mesma ordem da interface e deixa o processo pronto
para validacao ponta a ponta:

    .venv/bin/python scripts/semente_campo_bom.py            # cria/atualiza
    .venv/bin/python scripts/semente_campo_bom.py --limpar   # apaga e refaz

Uso pela interface: iniciar o app e abrir o processo "EX-CAMPOBOM-001".
"""

from __future__ import annotations

import argparse
import shutil
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from outorgasys import config as C  # noqa: E402
from outorgasys.agents import (  # noqa: E402
    agente1_triagem as a1,
    agente2_gis as a2,
    agente3_hidro as a3,
    agente4_balanco as a4,
    agente5_relatorio as a5,
)
from outorgasys.hydro import sintetico  # noqa: E402
from outorgasys.state import Processo  # noqa: E402

ID_PROCESSO = "EX-CAMPOBOM-001"

LAT, LON = -29.6842, -51.0531

REQUERENTE = {
    "nome": "Metalurgica Sinos Ltda.",
    "cpf_cnpj": "00.000.000/0001-00",
    "rg_ie": "000/0000000",
    "telefone": "(51) 3597-0000",
    "email": "meioambiente@example.com.br",
}

IMOVEL = {
    "denominacao": "Parque Industrial - Galpao 3",
    "endereco": "Rua das Aguas, 1250",
    "bairro": "Operaria",
    "cep": "93700-000",
    "municipio": "Campo Bom",
    "uf": "RS",
    "area_ha": 1.8,
}

POCO = {
    "nome": "PT-01",
    "profundidade_total_m": 82.0,
    "raio_m": 0.0762,          # 6" -> raio de 76,2 mm
    "diametro_util_pol": 6.0,
    "nivel_estatico_m": 8.0,
}

CONSTRUTIVO = {
    "diametro_perfuracao_mm": 250.0,
    "diametro_revestimento_mm": 152.0,   # 6"
    "profundidade_selo_m": 22.0,
    "tipo_aquifero": "poroso livre (sedimentos aluviais)",
    "crivo_de_m": 40.0,
    "crivo_ate_m": 78.0,
}

LAJE = {"espessura_cm": 15.0, "area_m2": 1.44, "rebordo_cm": 35.0}

HIDROMETRO = {
    "fabricante": "Exemplo Hidrometros",
    "modelo": "Volumetrico DN32",
    "numero_serie": "H2024-001122",
    "vazao_nominal_m3h": 2.5,
    "diametro_nominal_mm": 32.0,
    "classe_metrologica": "Classe B (horizontal)",
}

MOTOBOMBA = {
    "fabricante": "Exemplo Bombas",
    "modelo": "Submersa 4\" 5 estagios",
    "numero_serie": "B2024-000345",
    "diametro_pol": 4.0,
    "potencia_hp": 3.0,
    "num_estagios": 5,
    "profundidade_instalacao_m": 36.0,
    "vazao_nominal_m3h": 12.0,
    "altura_manometrica_mca": 62.0,
}

RESERVACAO = [
    {"capacidade_l": 5000.0, "local": "Casa de maquinas"},
    {"capacidade_l": 2000.0, "local": "Reservatorio elevado"},
]

PADRAO = {"horas_dia": 12.0, "dias_semana": 5}

FINALIDADES = ["industrial", "limpeza_geral_patio", "irrigacao"]

RESP_TECNICO = {
    "nome": "Ana Paula Exemplo",
    "titulo": "Geologo",
    "registro": "CREA-RS 0000000000",
    "empresa": "Consultoria Hidrogeologica Exemplo",
    "email": "ana.exemplo@example.com.br",
    "telefone": "(51) 90000-0000",
}

ART = "ART RS2024 0000000"

# Parametros do ensaio sintetico (T escolhido para s_max plausivel em aluviao)
ENSAIO = {"q": 12.0, "T": 6.0, "S": 1.0e-3, "raio": 0.0762, "ne": 8.0,
          "duracao_h": 24.0}


def _etapa(n: int, texto: str) -> None:
    print(f"  [{n}] {texto}", flush=True)


def _ok(n: int, texto: str) -> None:
    print(f"      agente {n}: OK - {texto}", flush=True)


def _falha(n: int, texto: str) -> None:
    print(f"      agente {n}: PENDENTE - {texto}", flush=True)


def construir(limpar: bool = False) -> Processo:
    if limpar:
        shutil.rmtree(Processo._diretorio_de(ID_PROCESSO), ignore_errors=True)
        Processo._json_de(ID_PROCESSO).unlink(missing_ok=True)
    proc = Processo(pid=ID_PROCESSO,
                    carregar=not limpar)

    print(f"Processo de exemplo: {proc.id}", flush=True)

    # ------------------------------------------------------------------ Agente 1
    _etapa(1, "Triagem, cadastro e enquadramento")
    proc["enquadramento"] = a1.enquadrar(POCO["diametro_util_pol"])
    proc["requerente"] = dict(REQUERENTE)
    proc["imovel"] = dict(IMOVEL)
    proc["poco"] = dict(POCO)
    proc["construtivo"] = dict(CONSTRUTIVO)
    proc["laje"] = dict(LAJE)
    proc["hidrometro"] = dict(HIDROMETRO)
    proc["motobomba"] = dict(MOTOBOMBA)
    proc["reservacao"] = [dict(x) for x in RESERVACAO]
    proc["padrao_explotacao"] = dict(PADRAO)
    proc["rede_publica"] = True
    proc["finalidades"] = list(FINALIDADES)
    proc["declaracao_separacao_redes"] = True
    proc["responsavel_tecnico"] = dict(RESP_TECNICO)
    proc["art"] = ART

    # Documentos: o ensaio e real (gerado), os demais sao marcadores de exemplo.
    ens = sintetico.gerar(**ENSAIO)
    dest = proc.dir_arquivos / "ensaio_bombeamento_PT-01.xlsx"
    sintetico.salvar_xlsx(ens, dest)
    a1.registrar_upload_manual(proc, "ensaio_bombeamento", dest, dest.name,
                               {"sintetico": True,
                                "parametros_geracao": ens["parametros_geracao"]})

    # Anexos de exemplo (posse, analise laboratorial, separacao de redes e as
    # quatro fotos). Todos sao marcados como "nao valido para protocolo".
    from outorgasys.report import documentos_exemplo as dex

    anexos = dex.gerar_todos(proc.dir_arquivos, IMOVEL, REQUERENTE, POCO)
    a1.registrar_upload_manual(proc, "matricula_imovel",
                               anexos["matricula_imovel"],
                               anexos["matricula_imovel"].name,
                               {"exemplo": True, "nao_valido_para_protocolo": True})
    a1.registrar_upload_manual(proc, "analise_laboratorial",
                               anexos["analise_laboratorial"],
                               anexos["analise_laboratorial"].name,
                               {"exemplo": True, "nao_valido_para_protocolo": True})
    a1.registrar_upload_manual(proc, "declaracao_separacao_redes",
                               anexos["declaracao_separacao_redes"],
                               anexos["declaracao_separacao_redes"].name,
                               {"exemplo": True, "nao_valido_para_protocolo": True})
    fotos = []
    for caminho in anexos["registro_fotografico"]:
        fotos.append(a1.registrar_upload_manual(
            proc, "registro_fotografico", caminho, caminho.name,
            {"exemplo": True, "nao_valido_para_protocolo": True}))
    proc.data.setdefault("documentos", {})["registro_fotografico"] = fotos
    proc.log(1, "Cadastro de exemplo carregado. Os anexos (matricula, analise "
                "laboratorial, declaracao de separacao de redes e registro "
                "fotografico) sao exemplos gerados pela plataforma e estao "
                "marcados como nao validos para protocolo.")

    validacao = a1.validar(proc)
    if validacao.ok:
        proc.concluir_agente(1)
        _ok(1, "triagem sem pendencias bloqueantes")
    else:
        _falha(1, "pendencias bloqueantes: " + ", ".join(
            f"{p.codigo} {p.titulo}" for p in validacao.bloqueios))

    # ------------------------------------------------------------------ Agente 2
    _etapa(2, "Cruzamento espacial e pranchas cartograficas")
    saida_geo = a2.analisar(proc, LAT, LON, raio_seguranca=C.RAIO_SEGURANCA_M,
                            raio_contexto=3000.0, gerar_mapas=True, usar_osm=True)
    proc["geoespacial"] = saida_geo
    proc.data.setdefault("imovel", {})["municipio"] = saida_geo.get("municipio")
    proc.concluir_agente(2)

    # ------------------------------------------------------------------ Agente 3
    _etapa(3, "Processamento hidrogeologico e graficos")
    proc["ensaio"] = a3.processar_planilha(dest)
    hidro = a3.calcular(proc, gerar_graficos=True)
    proc["hidrogeologia"] = hidro
    proc["hidraulica"] = hidro          # alias esperado pelo laudo e pelos agentes 4-6
    proc.concluir_agente(3)

    # ------------------------------------------------------------------ Agente 4
    _etapa(4, "Balanco hidrico e auditoria de equipamentos")
    bal = a4.executar(proc, preferencia_vazao="auto")
    proc["balanco"] = bal
    proc.concluir_agente(4)

    # ------------------------------------------------------------------ Agente 5
    _etapa(5, "Relatorio tecnico, memorial e minuta SIOUT")
    rel = a5.gerar(proc, resp_tecnico=RESP_TECNICO, art=ART, gerar_pdf=True)
    proc.salvar()

    # ------------------------------------------------------------------ Agente 6
    _etapa(6, "Triagem de defeitos")
    from outorgasys.agents import agente6_dev as a6

    a6.executar(proc, salvar=True)
    proc.salvar()

    # ------------------------------------------------------------------ Resumo
    p = hidro.get("parametros") or {}
    q = (bal.get("quadro") or {})
    print()
    print("  Municipio            :", saida_geo.get("municipio"))
    print("  Bacia hidrografica   :", saida_geo.get("bacia_hidrografica"))
    print("  Corpo hidrico prox.  :", saida_geo.get("corpo_hidrico_proximo"))
    print("  Formacao geologica   :", saida_geo.get("formacao_geologica"))
    print("  s_max / Q_estavel    :", f"{p.get('s_max_m'):.3f} m / "
                                      f"{p.get('q_estavel_m3h'):.3f} m3/h")
    print("  T                    :", f"{p.get('T_m2h'):.4f} m2/h")
    print("  Q_ot                 :", f"{p.get('Q_ot_m3h'):.3f} m3/h")
    print("  Vazao adotada        :", f"{(bal.get('vazao_adotada') or {}).get('vazao'):.3f} m3/h")
    print("  Volume anual         :", f"{q.get('volume_anual_m3'):,.2f} m3")
    print("  Laudo PDF            :", rel.get("pdf"))
    print("  Pranchas             :", len(saida_geo.get("caminho_mapas") or []))
    print("  Achados (Agente 6)   :", len(proc.get("issues") or []))
    return proc


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--limpar", action="store_true",
                    help="apaga o diretorio do processo antes de reconstruir")
    args = ap.parse_args()
    try:
        construir(limpar=args.limpar)
    except Exception:  # noqa: BLE001
        traceback.print_exc()
        return 1
    print()
    print("Concluido. Inicie o app e abra o processo", ID_PROCESSO)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

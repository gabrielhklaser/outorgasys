# -*- coding: utf-8 -*-
"""
Maquina de regras do SIOUT RS.

Concentra TODA a logica normativa da plataforma, de modo que os seis agentes
consultem uma unica fonte de verdade. Cada funcao de validacao devolve
objetos :class:`Pendencia` que podem ser impeditivos (bloqueiam o avanco para o
agente seguinte) ou apenas advertencias.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, asdict
from typing import Any, Iterable

from . import config as C


# --------------------------------------------------------------------------------------
# Tipos de resultado
# --------------------------------------------------------------------------------------


@dataclass
class Pendencia:
    """Um problema detectado por uma regra."""

    codigo: str
    titulo: str
    mensagem: str
    bloqueante: bool = True
    agente: int = 1
    campo: str | None = None
    sugestao: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ResultadoValidacao:
    """Resultado agregado de uma bateria de regras."""

    pendencias: list[Pendencia] = field(default_factory=list)

    @property
    def bloqueios(self) -> list[Pendencia]:
        return [p for p in self.pendencias if p.bloqueante]

    @property
    def avisos(self) -> list[Pendencia]:
        return [p for p in self.pendencias if not p.bloqueante]

    @property
    def ok(self) -> bool:
        return not self.bloqueios

    def add(self, p: Pendencia) -> None:
        self.pendencias.append(p)

    def __bool__(self) -> bool:  # truthy == sem bloqueios
        return self.ok

    def to_dict(self) -> dict:
        return {"ok": self.ok, "pendencias": [p.to_dict() for p in self.pendencias]}

    def __iter__(self):
        return iter(self.pendencias)

    def __len__(self) -> int:
        return len(self.pendencias)


def _num(v: Any) -> float | None:
    """Conversao numerica tolerante a formatos brasileiros ('1,5') e nulos."""
    if v is None or isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return None if (isinstance(v, float) and math.isnan(v)) else float(v)
    s = str(v).strip()
    if not s:
        return None
    s = s.replace(" ", "")
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


# --------------------------------------------------------------------------------------
# Agente 1 - enquadramento, cadastro e documentacao
# --------------------------------------------------------------------------------------


def classificar_poco(diametro_util_pol: float | None) -> dict:
    """Enquadra o poco segundo o diametro util (regra binaria do SIOUT RS).

    * ``< 4"``  -> poco de pequeno diametro / ponteira: dispensa o ensaio de
      bombeamento de 24 h + recuperacao, mas exige todo o resto.
    * ``>= 4"`` -> poco tubular profundo: exige ensaio de bombeamento continuo
      de 24 h acompanhado do ensaio de recuperacao.
    """
    d = _num(diametro_util_pol)
    if d is None:
        return {
            "definido": False,
            "classe": None,
            "exige_ensaio_24h": None,
            "descricao": "Diametro util nao informado.",
        }
    if d <= 0:
        return {
            "definido": False,
            "classe": None,
            "exige_ensaio_24h": None,
            "descricao": "Diametro util deve ser maior que zero.",
        }
    if d < C.DIAMETRO_CORTE_POL:
        return {
            "definido": True,
            "classe": "poco_pequeno_diametro",
            "rotulo": "Opcao A - Poco de pequeno diametro / ponteira",
            "exige_ensaio_24h": False,
            "descricao": (
                f'Poco com diametro util de {d:g}" (< 4"). Classificado como poco de '
                "pequeno diametro ou ponteira. NAO exige ensaio de bombeamento de "
                "24 horas, mas exige todos os demais dados cadastrais, documentacao "
                "de posse, caracteristicas dos equipamentos e analises "
                "fisico-quimicas e bacteriologicas."
            ),
        }
    return {
        "definido": True,
        "classe": "poco_tubular_profundo",
        "rotulo": "Opcao B - Poco tubular profundo",
        "exige_ensaio_24h": True,
        "descricao": (
            f'Poco tubular profundo com diametro util de {d:g}" (>= 4"). Exige ensaio '
            "de bombeamento continuo de 24 horas acompanhado do ensaio de "
            "recuperacao, alem de toda a documentacao legal e tecnica."
        ),
    }


def validar_padrao_explotacao(horas_dia: float | None, dias_semana: float | None) -> ResultadoValidacao:
    """Aplica a trava de repouso minimo do aquifero (SIOUT RS)."""
    r = ResultadoValidacao()
    h = _num(horas_dia)
    d = _num(dias_semana)

    if h is None:
        r.add(Pendencia(
            "EXP-001", "Tempo diario nao informado",
            "Informe o tempo diario de bombeamento pretendido (horas por dia).",
            campo="horas_dia"))
    else:
        if h <= 0:
            r.add(Pendencia(
                "EXP-002", "Tempo diario invalido",
                "O tempo diario de bombeamento deve ser maior que zero.",
                campo="horas_dia"))
        if h > C.BOMBEAMENTO_MAX_H_DIA:
            r.add(Pendencia(
                "EXP-003", "Repouso minimo violado",
                f"Com {h:g} h/dia restam apenas {24 - h:g} h de repouso. O SIOUT RS "
                f"exige repouso minimo obrigatorio de {C.REPOUSO_MINIMO_H:g} h/dia, "
                f"logo o limite absoluto e {C.BOMBEAMENTO_MAX_H_DIA:g} h/dia.",
                campo="horas_dia",
                sugestao=f"Reduza para no maximo {C.BOMBEAMENTO_MAX_H_DIA:g} h/dia."))
        elif h > C.BOMBEAMENTO_TRAVA_H_DIA:
            r.add(Pendencia(
                "EXP-004", "Acima da trava operacional de 18 h/dia",
                f"O padrao pretendido de {h:g} h/dia excede a trava de "
                f"{C.BOMBEAMENTO_TRAVA_H_DIA:g} h/dia adotada pela plataforma.",
                campo="horas_dia",
                sugestao=f"Ajuste para ate {C.BOMBEAMENTO_TRAVA_H_DIA:g} h/dia."))

    if d is None:
        r.add(Pendencia(
            "EXP-005", "Periodicidade semanal nao informada",
            "Informe a periodicidade semanal pretendida (dias por semana).",
            campo="dias_semana"))
    elif not (1 <= d <= 7):
        r.add(Pendencia(
            "EXP-006", "Periodicidade semanal invalida",
            "A periodicidade semanal deve estar entre 1 e 7 dias por semana.",
            campo="dias_semana"))
    return r


def finalidades_permitidas(rede_publica: bool | None) -> list[str]:
    """Devolve as chaves de finalidade liberadas para a situacao informada."""
    if rede_publica:
        return [k for k in C.FINALIDADES if k not in C.FINALIDADES_USO_HUMANO]
    return list(C.FINALIDADES)


def validar_finalidades(rede_publica: bool | None, finalidades: Iterable[str]) -> ResultadoValidacao:
    """REGRA DE BLOQUEIO CONDICIONAL (rede publica x consumo humano)."""
    r = ResultadoValidacao()
    if rede_publica is None:
        r.add(Pendencia(
            "FIN-001", "Rede publica nao informada",
            'Responda obrigatoriamente: "O imovel e atendido por rede publica de '
            'abastecimento de agua?"',
            campo="rede_publica"))
        return r

    fins = list(finalidades or [])
    if not fins:
        r.add(Pendencia(
            "FIN-002", "Nenhuma finalidade selecionada",
            "Selecione ao menos uma finalidade para o uso da agua.",
            campo="finalidades"))
        return r

    desconhecidas = [f for f in fins if f not in C.FINALIDADES]
    if desconhecidas:
        r.add(Pendencia(
            "FIN-003", "Finalidade desconhecida",
            f"Finalidades fora do catalogo: {', '.join(desconhecidas)}.",
            campo="finalidades"))

    if rede_publica:
        proibidas = [f for f in fins if f in C.FINALIDADES_USO_HUMANO]
        if proibidas:
            nomes = ", ".join(C.FINALIDADES[f][0] for f in proibidas)
            r.add(Pendencia(
                "FIN-010",
                "BLOQUEIO: finalidades incompativeis com rede publica",
                "O imovel declarou ser atendido por rede publica de abastecimento. "
                "A plataforma PROIBE a selecao de finalidades voltadas ao "
                "abastecimento humano direto, sanitarios e cozinha. Selecionado "
                "indevidamente: " + nomes + ". A captacao somente podera ser "
                "destinada a fins industriais, limpeza geral de patio, irrigacao ou "
                "recirculacao, exigindo declaracao de separacao fisica de redes "
                "hidraulicas.",
                campo="finalidades",
                sugestao="Remova as finalidades de uso humano ou revise a resposta "
                         "sobre atendimento por rede publica."))
    return r


def validar_declaracao_separacao_redes(rede_publica: bool | None,
                                       declarada: bool | None,
                                       arquivo: str | None = None) -> ResultadoValidacao:
    r = ResultadoValidacao()
    if not rede_publica:
        return r
    if not declarada:
        r.add(Pendencia(
            "SEP-001", "Declaracao de separacao de redes obrigatoria",
            "Por se tratar de imovel atendido por rede publica, e obrigatoria a "
            "declaracao de separacao fisica das redes hidraulicas (agua publica x "
            "agua do poco), sem qualquer interconexao, cross-connection ou "
            "by-pass.",
            campo="declaracao_separacao_redes",
            sugestao="Assine a declaracao e anexe o documento comprobatorio."))
    elif not arquivo:
        r.add(Pendencia(
            "SEP-002", "Comprovante da separacao de redes nao anexado",
            "Anexe o arquivo da declaracao de separacao fisica de redes "
            "hidraulicas (PDF ou imagem).",
            campo="arquivo_separacao_redes"))
    return r


def validar_reservacao(reservatorios: Iterable[dict]) -> ResultadoValidacao:
    r = ResultadoValidacao()
    itens = [x for x in (reservatorios or []) if _num(x.get("capacidade_l"))]
    if not itens:
        r.add(Pendencia(
            "RES-001", "Reservacao nao informada",
            "Informe a quantidade e a capacidade volumetrica individual (L) de cada "
            "reservatorio / caixa d'agua instalada.",
            campo="reservacao"))
    for i, x in enumerate(itens, start=1):
        cap = _num(x.get("capacidade_l"))
        if cap is not None and cap <= 0:
            r.add(Pendencia(
                "RES-002", f"Capacidade invalida no reservatorio {i}",
                "A capacidade volumetrica deve ser maior que zero.",
                bloqueante=True, campo="reservacao"))
    return r


def validar_hidrometro(h: dict) -> ResultadoValidacao:
    r = ResultadoValidacao()
    if not h:
        r.add(Pendencia("HID-000", "Hidrometro nao cadastrado",
                        "Cadastre fabricante, modelo, numero de serie, vazao nominal "
                        "(m3/h) e diametro nominal (DN).", campo="hidrometro"))
        return r
    obrigatorios = {
        "fabricante": "fabricante",
        "modelo": "modelo",
        "numero_serie": "numero de serie",
        "vazao_nominal_m3h": "vazao nominal (m3/h)",
        "diametro_nominal_mm": "diametro nominal (DN em mm)",
    }
    for k, rot in obrigatorios.items():
        if k not in ("vazao_nominal_m3h", "diametro_nominal_mm"):
            if not str(h.get(k) or "").strip():
                r.add(Pendencia(f"HID-{k[:3].upper()}", f"Falta o {rot} do hidrometro",
                                f"Preencha o campo '{rot}'.", bloqueante=False,
                                campo=f"hidrometro.{k}"))
    qn = _num(h.get("vazao_nominal_m3h"))
    if qn is None:
        r.add(Pendencia("HID-005", "Vazao nominal do hidrometro ausente",
                        "Informe a vazao nominal do hidrometro em m3/h.",
                        campo="hidrometro.vazao_nominal_m3h"))
    elif qn <= 0:
        r.add(Pendencia("HID-006", "Vazao nominal do hidrometro invalida",
                        "A vazao nominal deve ser maior que zero.",
                        campo="hidrometro.vazao_nominal_m3h"))
    dn = _num(h.get("diametro_nominal_mm"))
    if dn is None:
        r.add(Pendencia("HID-007", "Diametro nominal do hidrometro ausente",
                        "Informe o diametro nominal (DN em mm ou pol) do hidrometro.",
                        campo="hidrometro.diametro_nominal_mm"))
    elif dn <= 0:
        r.add(Pendencia("HID-008", "Diametro nominal do hidrometro invalido",
                        "O diametro nominal deve ser maior que zero.",
                        campo="hidrometro.diametro_nominal_mm"))
    return r


def validar_motobomba(b: dict, profundidade_poco_m: float | None = None) -> ResultadoValidacao:
    r = ResultadoValidacao()
    if not b:
        r.add(Pendencia("BOM-000", "Motobomba nao cadastrada",
                        "Cadastre fabricante, modelo, numero de serie, diametro (pol), "
                        "potencia (HP/CV), numero de estagios e profundidade de "
                        "instalacao do rotor/crivo (m).", campo="motobomba"))
        return r
    for k, rot in (("fabricante", "fabricante"), ("modelo", "modelo"),
                   ("numero_serie", "numero de serie")):
        if not str(b.get(k) or "").strip():
            r.add(Pendencia(f"BOM-{k[:3].upper()}", f"Falta o {rot} da motobomba",
                            f"Preencha o campo '{rot}'.", bloqueante=False,
                            campo=f"motobomba.{k}"))
    for k, rot, minimo in (("diametro_pol", "diametro (pol)", 1.0),
                           ("potencia_hp", "potencia (HP/CV)", 0.1),
                           ("num_estagios", "numero de estagios", 1.0),
                           ("profundidade_instalacao_m", "profundidade de instalacao (m)", 0.1)):
        v = _num(b.get(k))
        if v is None:
            r.add(Pendencia(f"BOM-{k[:4].upper()}", f"Falta o {rot} da motobomba",
                            f"Informe o {rot} da motobomba.",
                            campo=f"motobomba.{k}"))
        elif v < minimo:
            r.add(Pendencia(f"BOM-{k[:4].upper()}V", f"{rot.capitalize()} invalido",
                            f"O valor informado para {rot} deve ser >= {minimo:g}.",
                            campo=f"motobomba.{k}"))
    prof = _num(b.get("profundidade_instalacao_m"))
    pp = _num(profundidade_poco_m)
    if prof is not None and pp is not None and prof > pp:
        r.add(Pendencia(
            "BOM-050", "Profundidade de instalacao maior que o poco",
            f"A motobomba esta declarada a {prof:g} m, mas a profundidade total do "
            f"poco e {pp:g} m. Verifique a cotacao.",
            bloqueante=False, campo="motobomba.profundidade_instalacao_m"))
    return r


def checklist_documentos(enquadramento: dict, docs: dict) -> ResultadoValidacao:
    """Valida a submissao de todos os ficheiros obrigatorios do Agente 1."""
    r = ResultadoValidacao()
    exige_ensaio = enquadramento.get("exige_ensaio_24h")

    # 1) Ensaio de bombeamento (apenas pocos >= 4")
    if exige_ensaio:
        if not docs.get("ensaio_bombeamento"):
            r.add(Pendencia(
                "DOC-010", "Ensaio de bombeamento nao enviado",
                "Para pocos com diametro util >= 4\" e obrigatorio o ensaio de "
                "bombeamento continuo de 24 h com ensaio de recuperacao "
                "(planilha .xlsx/.csv).",
                campo="ensaio_bombeamento"))

    # 2) Documentacao de posse e terra (ao menos um comprovante)
    if not any(docs.get(k) for k in C.DOCS_POSSE):
        r.add(Pendencia(
            "DOC-020", "Documentacao de posse e terra ausente",
            "Envie ao menos um comprovante: matricula/registro de imoveis atualizada, "
            "contrato de arrendamento/locacao/comodato, termo de concessao ou "
            "recibo do CAR (se rural). Formatos: PDF ou imagem (PNG, JPG, TIFF).",
            campo="posse"))

    # 3) Analise laboratorial
    if not docs.get("analise_laboratorial"):
        r.add(Pendencia(
            "DOC-030", "Relatorio de analise laboratorial ausente",
            "Envie o relatorio de analise fisico-quimica e bacteriologica conforme "
            "os parametros de potabilidade da Portaria GM/MS n. 888/2021 (PDF).",
            campo="analise_laboratorial"))

    # 4) Registro fotografico
    fotos = docs.get("registro_fotografico") or []
    if len(fotos) < 4:
        r.add(Pendencia(
            "DOC-040", "Registro fotografico incompleto",
            "Envie fotos nitidas e atualizadas de: (1) boca do poco, (2) laje de "
            "protecao sanitaria, (3) cercamento de protecao e (4) cavalete com "
            f"hidrometro instalado. Enviadas: {len(fotos)} de 4.",
            campo="registro_fotografico"))
    return r


def validar_laje_sanitaria(espessura_cm: float | None, area_m2: float | None,
                           rebordo_cm: float | None) -> ResultadoValidacao:
    """Verifica a laje de protecao sanitaria (ABNT NBR 12212 / SIOUT RS)."""
    r = ResultadoValidacao()
    e, a, c = _num(espessura_cm), _num(area_m2), _num(rebordo_cm)
    if e is not None and e < C.LAJE_ESPESSURA_MIN_CM:
        r.add(Pendencia(
            "LAJ-001", "Espessura da laje insuficiente",
            f"Espessura de {e:g} cm abaixo do minimo de {C.LAJE_ESPESSURA_MIN_CM:g} cm.",
            bloqueante=False, campo="laje.espessura_cm"))
    if a is not None and a < C.LAJE_AREA_MIN_M2:
        r.add(Pendencia(
            "LAJ-002", "Area da laje insuficiente",
            f"Area de {a:g} m2 abaixo do minimo de {C.LAJE_AREA_MIN_M2:g} m2.",
            bloqueante=False, campo="laje.area_m2"))
    if c is not None and c < C.LAJE_REBORDO_MIN_CM:
        r.add(Pendencia(
            "LAJ-003", "Cota de rebordo insuficiente",
            f"Rebordo de {c:g} cm abaixo do minimo de {C.LAJE_REBORDO_MIN_CM:g} cm "
            "acima do terreno.",
            bloqueante=False, campo="laje.rebordo_cm"))
    return r


def validar_construtivo(diametro_perfuracao_mm: float | None,
                        diametro_revestimento_mm: float | None,
                        profundidade_selo_m: float | None) -> ResultadoValidacao:
    """Regras construtivas: espaco anular minimo e selo sanitario."""
    r = ResultadoValidacao()
    dp, dr, ps = (_num(diametro_perfuracao_mm), _num(diametro_revestimento_mm),
                  _num(profundidade_selo_m))
    if dp and dr:
        anular = (dp - dr) / 2.0
        if anular < C.ESPACO_ANULAR_MIN_MM:
            r.add(Pendencia(
                "CON-001", "Espaco anular insuficiente",
                f"Espaco anular de {anular:g} mm e inferior ao minimo de "
                f"{C.ESPACO_ANULAR_MIN_MM:g} mm entre a parede do furo e a "
                "tubulacao de revestimento.",
                bloqueante=False, campo="construtivo.espaco_anular_mm"))
    if ps is not None and ps < C.SELO_SANITARIO_MIN_M:
        r.add(Pendencia(
            "CON-002", "Selo sanitario abaixo do recomendado",
            f"Selo sanitario de {ps:g} m abaixo da profundidade minima recomendada "
            f"de {C.SELO_SANITARIO_MIN_M:g} m.",
            bloqueante=False, campo="construtivo.profundidade_selo_m"))
    return r


def validar_triagem(processo: dict) -> ResultadoValidacao:
    """Bateria completa do Agente 1. Deve estar ok antes de chamar o Agente 2."""
    r = ResultadoValidacao()
    enf = processo.get("enquadramento") or {}
    if not enf.get("definido"):
        r.add(Pendencia("TRI-001", "Enquadramento nao definido",
                        "Selecione a opcao de enquadramento do poco (A ou B).",
                        campo="diametro_util_pol"))

    docs = processo.get("documentos") or {}
    r.pendencias += checklist_documentos(enf, docs).pendencias

    pe = processo.get("padrao_explotacao") or {}
    r.pendencias += validar_padrao_explotacao(pe.get("horas_dia"),
                                              pe.get("dias_semana")).pendencias
    r.pendencias += validar_finalidades(processo.get("rede_publica"),
                                        processo.get("finalidades") or []).pendencias
    r.pendencias += validar_declaracao_separacao_redes(
        processo.get("rede_publica"),
        processo.get("declaracao_separacao_redes"),
        (processo.get("documentos") or {}).get("declaracao_separacao_redes"),
    ).pendencias
    r.pendencias += validar_hidrometro(processo.get("hidrometro") or {}).pendencias
    r.pendencias += validar_motobomba(
        processo.get("motobomba") or {},
        (processo.get("poco") or {}).get("profundidade_total_m"),
    ).pendencias
    r.pendencias += validar_reservacao(processo.get("reservacao") or []).pendencias

    laje = processo.get("laje") or {}
    r.pendencias += validar_laje_sanitaria(laje.get("espessura_cm"), laje.get("area_m2"),
                                           laje.get("rebordo_cm")).pendencias
    return r


# --------------------------------------------------------------------------------------
# Agente 2 - regras espaciais
# --------------------------------------------------------------------------------------


def validar_coordenadas_rs(lat: float | None, lon: float | None,
                           dentro_uf: bool | None = None) -> ResultadoValidacao:
    r = ResultadoValidacao()
    la, lo = _num(lat), _num(lon)
    if la is None or lo is None:
        r.add(Pendencia("GEO-001", "Coordenadas nao informadas",
                        "Informe latitude e longitude em graus decimais "
                        "(ex.: -29.6842, -51.0531).", campo="coordenadas"))
        return r
    if not (-90 <= la <= 90) or not (-180 <= lo <= 180):
        r.add(Pendencia("GEO-002", "Coordenadas fora do dominio geografico",
                        "Latitude deve estar entre -90 e 90 e longitude entre -180 e 180.",
                        campo="coordenadas"))
        return r
    minx, miny, maxx, maxy = C.RS_BBOX
    margem = 0.05
    if not (minx - margem <= lo <= maxx + margem and miny - margem <= la <= maxy + margem):
        r.add(Pendencia(
            "GEO-003", "Coordenadas fora do Rio Grande do Sul",
            f"O ponto ({la:.5f}, {lo:.5f}) esta fora da caixa envolvente do estado. "
            "Esta plataforma atende exclusivamente processos do SIOUT RS.",
            campo="coordenadas"))
    if dentro_uf is False:
        r.add(Pendencia("GEO-004", "Ponto fora do limite estadual",
                        "A interseccao com a malha estadual do IBGE confirmou que o "
                        "ponto esta fora do territorio do Rio Grande do Sul.",
                        campo="coordenadas"))
    return r


def fuso_utm_rs(lon: float) -> tuple[str, str]:
    """Devolve (fuso, EPSG) UTM-SIRGAS2000 apropriado para a longitude."""
    lo = _num(lon) or -51.0
    if lo < -54.0:
        return "21S", C.CRS_UTM_21S
    if lo > -48.0:
        return "23S", C.CRS_UTM_23S
    return "22S", C.CRS_UTM_22S


def avaliar_raio_seguranca(distancias: dict) -> ResultadoValidacao:
    """Avalia as ocorrencias dentro do buffer de 500 m."""
    r = ResultadoValidacao()
    for nome, dist in (distancias or {}).items():
        d = _num(dist)
        if d is None or d > C.RAIO_SEGURANCA_M:
            continue
        r.add(Pendencia(
            "BUF-001", f"Ocorrencia no raio de seguranca: {nome}",
            f"'{nome}' esta a {d:.1f} m do poco, dentro do raio de seguranca de "
            f"{C.RAIO_SEGURANCA_M:g} m exigido pelo SIOUT RS. Descreva e mitigue a "
            "fonte potencial de poluicao no relatorio tecnico.",
            bloqueante=False, agente=2, campo=f"raio_seguranca.{nome}"))
    return r


def avaliar_distancia_corpo_hidrico(dist_m: float | None) -> ResultadoValidacao:
    r = ResultadoValidacao()
    d = _num(dist_m)
    if d is None:
        return r
    if d < 50.0:
        r.add(Pendencia(
            "HID-100", "Poco muito proximo de corpo hidrico superficial",
            f"Distancia de {d:.1f} m ao corpo hidrico mais proximo. Distancias "
            "inferiores a 50 m exigem estudo de conexao hidraulica (perda de carga / "
            "interferencia rio-aquifero) e atencao a possivel inducao de "
            "escoamento superficial contaminado.",
            bloqueante=False, agente=2, campo="distancia_corpo_hidrico_m"))
    return r


# --------------------------------------------------------------------------------------
# Agente 4 - equipamentos e balanco hidrico
# --------------------------------------------------------------------------------------


def avaliar_motobomba_vs_poco(bomba: dict, q_estavel: float | None,
                              nd_m: float | None, q_ot: float | None) -> ResultadoValidacao:
    """Auditoria da motobomba frente a capacidade real do poco."""
    r = ResultadoValidacao()
    qe, qo, nd = _num(q_estavel), _num(q_ot), _num(nd_m)
    qb = _num((bomba or {}).get("vazao_nominal_m3h"))
    prof = _num((bomba or {}).get("profundidade_instalacao_m"))

    ref = qo if qo else qe
    if qb and ref:
        razao = qb / ref
        if razao > 1.20:
            r.add(Pendencia(
                "EQP-010", "Bomba superdimensionada para o poco",
                f"A vazao nominal da bomba ({qb:g} m3/h) e {razao:.2f}x a vazao de "
                f"referencia do poco ({ref:g} m3/h). Risco de operar fora da curva "
                "de rendimento, com sobrecarga, vibracao, desgaste prematuro e "
                "rebaixamento excessivo.",
                bloqueante=False, agente=4, campo="motobomba.vazao_nominal_m3h",
                sugestao=f"Selecione bomba com vazao nominal entre "
                         f"{0.8 * ref:.2f} e {1.1 * ref:.2f} m3/h."))
        elif razao < 0.70:
            r.add(Pendencia(
                "EQP-011", "Bomba subdimensionada para o poco",
                f"A vazao nominal da bomba ({qb:g} m3/h) e apenas {razao:.2f}x a "
                f"vazao de referencia do poco ({ref:g} m3/h). A bomba pode operar "
                "afogada e por longos periodos sem atender a demanda.",
                bloqueante=False, agente=4, campo="motobomba.vazao_nominal_m3h"))

    if prof is not None and nd is not None:
        subm = prof - nd
        if subm < C.SUBMERGENCIA_MIN_M:
            r.add(Pendencia(
                "EQP-020", "Submergencia insuficiente da motobomba",
                f"A bomba esta instalada a {prof:g} m e o nivel dinamico a {nd:g} m, "
                f"restando apenas {subm:g} m de submergencia. Recomenda-se folga "
                f"minima de {C.SUBMERGENCIA_MIN_M:g} a {C.SUBMERGENCIA_MAX_M:g} m "
                "abaixo do nivel dinamico para evitar cavitation e sucção de ar.",
                bloqueante=False, agente=4,
                campo="motobomba.profundidade_instalacao_m",
                sugestao=f"Instale a bomba entre {nd + C.SUBMERGENCIA_MIN_M:.1f} m e "
                         f"{nd + C.SUBMERGENCIA_MAX_M:.1f} m."))
        elif subm > 60.0:
            r.add(Pendencia(
                "EQP-021", "Bomba excessivamente profunda",
                f"Submergencia de {subm:g} m: altura manometrica e potencia "
                "desnecessariamente elevadas, com perda de eficiencia energetica.",
                bloqueante=False, agente=4,
                campo="motobomba.profundidade_instalacao_m"))
    return r


def avaliar_hidrometro(hidrometro: dict, vazao_adotada: float | None) -> ResultadoValidacao:
    r = ResultadoValidacao()
    qn = _num((hidrometro or {}).get("vazao_nominal_m3h"))
    q = _num(vazao_adotada)
    if qn and q:
        if q > qn:
            r.add(Pendencia(
                "MED-010", "Hidrometro abaixo da vazao de operacao",
                f"Vazao adotada de {q:g} m3/h excede a vazao nominal do hidrometro "
                f"({qn:g} m3/h). O instrumento operara acima da faixa de trabalho, "
                "com perda de precisao metrologica e desgaste acelerado.",
                bloqueante=False, agente=4, campo="hidrometro.vazao_nominal_m3h",
                sugestao="Substitua por hidrometro com vazao nominal >= "
                         f"{q:.2f} m3/h."))
        elif q < 0.05 * qn:
            r.add(Pendencia(
                "MED-011", "Hidrometro superdimensionado",
                f"Vazao adotada de {q:g} m3/h corresponde a menos de 5% da vazao "
                f"nominal do hidrometro ({qn:g} m3/h). O medidor pode nao registrar "
                "vazoes baixas com a precisao da classe metrologica.",
                bloqueante=False, agente=4, campo="hidrometro.vazao_nominal_m3h"))

    dn = _num((hidrometro or {}).get("diametro_nominal_mm"))
    if dn and q:
        # Velocidade media admissivel de referencia: ~3 m/s na secao nominal.
        area = math.pi * (dn / 2000.0) ** 2  # mm -> m de raio
        v = (q / 3600.0) / area if area else 0.0
        if v > 3.0:
            r.add(Pendencia(
                "MED-020", "Velocidade excessiva no hidrometro",
                f"Velocidade media estimada de {v:.2f} m/s no hidrometro DN{dn:g}. "
                "Recomenda-se ate 3 m/s para preservar a classe de precisao.",
                bloqueante=False, agente=4, campo="hidrometro.diametro_nominal_mm"))
    return r


def avaliar_reservacao(reservatorios: Iterable[dict], vazao_adotada: float | None,
                       horas_dia: float | None) -> ResultadoValidacao:
    """Impede ciclos curtos de liga/desliga que danificam o motor."""
    r = ResultadoValidacao()
    total_l = sum(_num(x.get("capacidade_l")) or 0.0 for x in (reservatorios or []))
    q, h = _num(vazao_adotada), _num(horas_dia)
    if not total_l:
        return r
    if not q or not h:
        return r
    # Volume tipico por ciclo: tempo de enchimento proporcional ao regime diario.
    ciclos_dia = max(1.0, h / 2.0) if h <= 12 else 1.0
    volume_ciclo_m3 = (q * h) / ciclos_dia
    volume_reserva_m3 = total_l / 1000.0
    if volume_reserva_m3 < 0.25 * volume_ciclo_m3:
        r.add(Pendencia(
            "RES-100", "Reservacao insuficiente para o regime operacional",
            f"Reserva total de {volume_reserva_m3:.2f} m3 contra volume tipico de "
            f"{volume_ciclo_m3:.2f} m3 por ciclo de bombeamento. A relacao "
            f"reserva/ciclo de {volume_reserva_m3 / volume_ciclo_m3:.2f} e inferior a "
            "0,25, o que provoca ciclos curtos de liga/desliga e reduz a vida util "
            "do conjunto motor-bomba.",
            bloqueante=False, agente=4, campo="reservacao",
            sugestao=f"Amplie a reservacao para pelo menos "
                     f"{0.25 * volume_ciclo_m3 * 1000:.0f} L ou reduza a vazao por ciclo."))
    return r


# --------------------------------------------------------------------------------------
# Helpers de apresentacao
# --------------------------------------------------------------------------------------


def rotulo_finalidades(chaves: Iterable[str]) -> list[str]:
    return [C.FINALIDADES.get(k, (k, False))[0] for k in chaves]

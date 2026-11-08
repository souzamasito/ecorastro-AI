#!/usr/bin/env python3
"""Valida análises do EcoRastro AI contra o schema e as regras da skill.

Verificações, por categoria:
  schema        assets/analise.schema.json (JSON Schema 2020-12)
  consistencia  ids, classificação, localização, datas, alegações, alertas, versões, lote
  evidencia     toda evidência aparece literalmente no texto_mascarado do documento
  pontuacao     a prioridade é recalculada com calcular_prioridade.py e comparada
  privacidade   dados pessoais fora de marcadores, marcadores × dados_pessoais,
                texto original e hash, regras da versão pública
  arquivo       convenção de nomes, permissões de arquivos internos, Git

Uso:
  validar_analise.py ARQUIVO.json [ARQUIVO.json ...] [--json] [--estrito]
                     [--permitir-verificado] [--schema CAMINHO]

Códigos de saída: 0 válido (pode haver avisos), 1 há erros (ou avisos com
--estrito), 2 erro de uso, leitura ou dependência ausente.

Limitações conhecidas da detecção de dados pessoais (registre novos casos
observados nos testes):
  Falsos positivos possíveis (acusa algo que não é dado pessoal)
    - sequências de 11 dígitos, como números de protocolo ou processo,
      acusadas como CPF ou telefone;
    - pares de 4 dígitos separados por hífen ou espaço, como "2025-2026",
      acusados como telefone;
    - códigos alfanuméricos no formato de placa, como modelos e siglas;
    - e-mails institucionais públicos, como o de uma ouvidoria.
  Falsos negativos possíveis (deixa passar dado pessoal)
    - nomes e apelidos de pessoas ("Seu Zé"), que não são detectáveis por
      expressão regular;
    - telefones sem separador com 8 a 10 dígitos, ou CPF com espaços;
    - documentos em formatos não previstos;
    - número de residência sem marcador;
    - dados sensíveis em texto livre ("minha filha autista"): na versão
      pública há um AVISO para termos comuns no singular (PADRAO_SENSIVEL),
      mas diagnósticos, sinônimos e grafias fora da lista passam;
    - característica sensível identificável só pelo contexto ("o único
      aluno de muletas da escola").
  Falsos positivos do aviso de dado sensível
    - uso genérico no singular ("todo cadeirante sofre aqui"), nomes de
      lugares ("Rua dos Imigrantes" não dispara; "Igreja Católica" dispara).
  Reidentificação na versão pública (schema 1.2.0, categorias.md 11.1)
    - ERRO: dois [DADO_SENSIVEL] seguidos ("[DADO_SENSIVEL] e [DADO_SENSIVEL]"),
      que revelam quantas condições a pessoa tem; use um marcador por pessoa.
    - AVISO: com dado_sensivel mascarado, menção coletiva a característica
      sensível (PADRAO_SENSIVEL_COLETIVO: "cadeirantes", "pessoas com
      deficiência"…), que pode permitir deduzir a condição mascarada.
      Falso positivo: menção coletiva a uma característica diferente da que
      foi mascarada. Falso negativo: pista indireta ("os vizinhos de cadeira
      de rodas"), que só a análise percebe.
    - O validador não lê os relatórios em Markdown: a regra de não
      reproduzir o texto quando texto_relato_publicavel é false é conferida
      pela lista de verificação de references/relatorio.md.
Diante de um falso positivo, a análise deve mascarar o trecho com o marcador
mais próximo (por exemplo, [DOCUMENTO] para protocolo) ou explicar o caso ao
usuário. Não remova a verificação.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import stat
import subprocess
import sys
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import calcular_prioridade as cp  # noqa: E402
import gerar_metadados as gm  # noqa: E402

SCHEMA_PADRAO = Path(__file__).resolve().parent.parent / "assets" / "analise.schema.json"
VERSAO_TAXONOMIA = "1.0.0"

MARCADORES = {
    "[NOME]": "nome_pessoa",
    "[CPF]": "cpf",
    "[DOCUMENTO]": "documento_identificacao",
    "[TELEFONE]": "telefone",
    "[EMAIL]": "email",
    "[PLACA]": "placa_veiculo",
    "[NUMERO]": "endereco_residencial",
    "[DADO_SENSIVEL]": "dado_sensivel",
    "[EMPRESA]": "empresa_em_alegacao",
}
SO_NA_PUBLICA = {"endereco_residencial", "empresa_em_alegacao"}

# Padrões de dados pessoais que não deveriam sobreviver ao mascaramento.
# Nomes de pessoas não são detectáveis por expressão regular; ficam a cargo da análise.
PADROES_PII = [
    ("CPF", re.compile(r"(?<!\d)\d{3}\.\d{3}\.\d{3}-\d{2}(?!\d)")),
    ("CPF ou telefone sem formatação", re.compile(r"(?<!\d)\d{11}(?!\d)")),
    ("RG", re.compile(r"(?<!\d)\d{1,2}\.\d{3}\.\d{3}-[\dXx](?![\dA-Za-z])")),
    ("telefone", re.compile(r"(?<!\d)(?:\(\d{2}\)\s?|\d{2}\s)?9?\d{4}[-\s]\d{4}(?!\d)")),
    ("telefone", re.compile(r"\(\d{2}\)\s?9?\d{8}(?!\d)")),
    ("e-mail", re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")),
    ("placa de veículo", re.compile(r"(?<![A-Za-z0-9])[A-Z]{3}-?\d[A-Z0-9]\d{2}(?![A-Za-z0-9])")),
]
# Termos que, no singular, costumam indicar a condição de uma pessoa específica
# (categorias.md, seção 11.1). Só geram AVISO, e só na versão pública: a menção
# coletiva ("cadeirantes", "idosos") é permitida e o termo pode ser genérico.
PADRAO_SENSIVEL = re.compile(
    r"(?<![\w\[])(?:cadeirante|autista|deficiente(?: visual| auditivo| físico| mental)?|cego|cega|surdo|surda|"
    r"paraplégic[oa]|tetraplégic[oa]|acamad[oa]|grávida|gestante|soropositiv[oa]|portador(?:a)? de \w+|"
    r"tem (?:câncer|hiv|aids|alzheimer|parkinson|esquizofrenia|depressão|epilepsia|autismo|diabetes)|"
    r"faz (?:hemodiálise|quimioterapia)|dependente químic[oa]|evangélic[oa]|católic[oa]|umbandista|"
    r"candomblecista|muçulman[oa]|judeu|judia|gay|lésbica|bissexual|transexual|travesti|"
    r"imigrante|refugiad[oa]|morador(?:a)? de rua|em situação de rua)(?![\w])",
    re.IGNORECASE,
)
# Menções coletivas a características sensíveis. Permitidas em geral (11.1), mas,
# num relato público com dado sensível de pessoa identificável já mascarado,
# podem permitir deduzir a condição mascarada. Só geram AVISO.
PADRAO_SENSIVEL_COLETIVO = re.compile(
    r"(?<![\w\[])(?:cadeirantes|autistas|deficientes(?: visuais| auditivos| físicos| mentais)?|"
    r"pessoas com deficiência|mobilidade reduzida|cegos|cegas|surdos|surdas|paraplégic[oa]s|tetraplégic[oa]s|"
    r"acamad[oa]s|grávidas|gestantes|soropositiv[oa]s|portador(?:es|as) de \w+|dependentes químic[oa]s|"
    r"evangélic[oa]s|católic[oa]s|umbandistas|candomblecistas|muçulman[oa]s|judeus|judias|gays|lésbicas|"
    r"bissexuais|transexuais|travestis|imigrantes|refugiad[oa]s|moradores de rua|pessoas em situação de rua)(?![\w])",
    re.IGNORECASE,
)
# Dois marcadores de dado sensível seguidos revelam quantas condições a pessoa tem.
PADRAO_MARCADORES_SENSIVEIS_SEGUIDOS = re.compile(r"\[DADO_SENSIVEL\](?:\s*(?:,|;|/|\be\b|\bou\b)\s*\[DADO_SENSIVEL\])+")
# Campos técnicos que não são varridos em busca de dados pessoais.
CHAVES_IGNORADAS_PII = {
    "texto_original", "hash_texto", "id_analise", "id_lote", "id_externo", "analisado_em",
    "gerado_em", "recebido_em", "verificado_em", "schema_version", "versao_skill",
    "versao_taxonomia", "versao_matriz_prioridade", "versao_matriz",
}
TERMOS_PROIBIDOS = ("avaliação de risco", "avaliacao de risco", "nível de risco", "nivel de risco")
CAMPOS_LOCALIZACAO = ("endereco_texto", "bairro", "ponto_referencia", "municipio", "latitude", "longitude")


@dataclass
class Achado:
    categoria: str
    caminho: str
    mensagem: str

    def como_dict(self) -> dict:
        return {"categoria": self.categoria, "caminho": self.caminho, "mensagem": self.mensagem}


@dataclass
class Resultado:
    erros: list[Achado] = field(default_factory=list)
    avisos: list[Achado] = field(default_factory=list)

    def erro(self, categoria: str, caminho: str, mensagem: str) -> None:
        self.erros.append(Achado(categoria, caminho, mensagem))

    def aviso(self, categoria: str, caminho: str, mensagem: str) -> None:
        self.avisos.append(Achado(categoria, caminho, mensagem))

    @property
    def valido(self) -> bool:
        return not self.erros


# --------------------------------------------------------------------------- schema

def carregar_validador(caminho_schema: Path = SCHEMA_PADRAO):
    try:
        import jsonschema
    except ImportError as e:
        raise RuntimeError(
            "o pacote 'jsonschema' é necessário: python3 -m pip install jsonschema"
        ) from e
    schema = json.loads(Path(caminho_schema).read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator.check_schema(schema)
    return jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker())


def _caminho(partes) -> str:
    saida = ""
    for p in partes:
        saida += f"[{p}]" if isinstance(p, int) else (f".{p}" if saida else str(p))
    return saida or "(raiz)"


def _erros_schema(validador, doc) -> list[Achado]:
    achados = []
    for e in sorted(validador.iter_errors(doc), key=lambda x: list(x.absolute_path)):
        # Com oneOf na raiz, mostre o erro do ramo correspondente ao tipo_documento.
        if e.validator == "oneOf" and not e.absolute_path and e.context:
            tipo = doc.get("tipo_documento") if isinstance(doc, dict) else None
            ramo = 0 if tipo == "analise_relato" else 1 if tipo == "lote_analises" else None
            subs = [s for s in e.context if ramo is None or s.relative_schema_path[0] == ramo]
            for s in sorted(subs, key=lambda x: list(x.absolute_path)):
                achados.append(Achado("schema", _caminho(s.absolute_path), s.message[:300]))
            if subs:
                continue
        achados.append(Achado("schema", _caminho(e.absolute_path), e.message[:300]))
    # Remove repetições (o mesmo erro pode surgir por vários ramos de allOf).
    vistos, unicos = set(), []
    for a in achados:
        chave = (a.caminho, a.mensagem)
        if chave not in vistos:
            vistos.add(chave)
            unicos.append(a)
    return unicos


# --------------------------------------------------------------------------- utilidades

def _ws(texto: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", texto)).strip()


def _sem_acentos(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn").casefold()


def _data_hora(valor: str | None) -> dt.datetime | None:
    if not valor:
        return None
    try:
        return dt.datetime.fromisoformat(valor)
    except ValueError:
        return None


def _strings(obj, partes=()):
    """Percorre todas as strings do documento, com o caminho de cada uma."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in CHAVES_IGNORADAS_PII:
                continue
            yield from _strings(v, partes + (k,))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from _strings(v, partes + (i,))
    elif isinstance(obj, str):
        yield _caminho(partes), obj


def _checar_evidencia(res: Resultado, evidencia, texto: str, caminho: str) -> None:
    if evidencia is None:
        return
    e, t = _ws(evidencia), _ws(texto)
    if not e:
        res.erro("evidencia", caminho, "evidência vazia")
    elif e in t:
        return
    elif e.casefold() in t.casefold():
        res.aviso("evidencia", caminho, f'evidência difere do texto só em maiúsculas/minúsculas: "{e[:80]}"')
    else:
        res.erro("evidencia", caminho, f'evidência não aparece literalmente no texto_mascarado: "{e[:80]}"')


# --------------------------------------------------------------------------- análise

def _validar_privacidade(res: Resultado, a: dict, p: str) -> None:
    relato, vis = a["relato"], a["visibilidade"]
    texto = relato["texto_mascarado"]

    for caminho, valor in _strings(a):
        for nome, padrao in PADROES_PII:
            if padrao.search(valor):
                res.erro("privacidade", p + caminho, f"possível {nome} fora de marcador de mascaramento")
                break

    encontrados = {tipo for marcador, tipo in MARCADORES.items() if marcador in texto}
    declarados = set(a["dados_pessoais"]["tipos"])
    for tipo in sorted(encontrados - declarados):
        res.erro("privacidade", f"{p}dados_pessoais.tipos", f"texto_mascarado usa marcador de '{tipo}', mas o tipo não foi declarado")
    for tipo in sorted(declarados - encontrados):
        res.erro("privacidade", f"{p}dados_pessoais.tipos", f"tipo '{tipo}' declarado sem marcador correspondente no texto_mascarado")
    desconhecidos = set(re.findall(r"\[[A-Z_]{3,}\]", texto)) - set(MARCADORES)
    for m in sorted(desconhecidos):
        res.aviso("privacidade", f"{p}relato.texto_mascarado", f"marcador desconhecido {m}")

    if vis == "interna":
        for tipo in sorted(encontrados & SO_NA_PUBLICA):
            res.aviso("privacidade", f"{p}relato.texto_mascarado",
                      f"'{tipo}' só é mascarado na versão pública; na interna deve ser mantido")
        original = relato["texto_original"]
        if original is not None and gm.calcular_hash(original) != relato["hash_texto"]:
            res.erro("privacidade", f"{p}relato.hash_texto", "hash_texto não corresponde ao texto_original normalizado")
    else:
        vistos = set()
        for caminho, valor in _strings(a):
            for m in PADRAO_SENSIVEL.finditer(valor):
                termo = m.group(0).lower()
                if termo not in vistos:
                    vistos.add(termo)
                    res.aviso("privacidade", p + caminho,
                              f"possível dado sensível de pessoa identificável na versão pública: '{m.group(0)}' "
                              "(categorias.md 11.1: use [DADO_SENSIVEL] ou confirme que a menção é genérica)")
        for caminho, valor in _strings(a):
            if PADRAO_MARCADORES_SENSIVEIS_SEGUIDOS.search(valor):
                res.erro("privacidade", p + caminho,
                         "dois [DADO_SENSIVEL] seguidos revelam quantas condições a pessoa tem; "
                         "use um único marcador por pessoa (categorias.md 11.1)")
        if "dado_sensivel" in declarados:
            vistos_coletivos = set()
            for caminho, valor in _strings(a):
                for m in PADRAO_SENSIVEL_COLETIVO.finditer(valor):
                    termo = m.group(0).lower()
                    if termo not in vistos_coletivos:
                        vistos_coletivos.add(termo)
                        res.aviso("privacidade", p + caminho,
                                  f"menção coletiva a característica sensível ('{m.group(0)}') num relato com dado sensível "
                                  "de pessoa identificável: junto com o local, pode permitir deduzir a condição mascarada "
                                  "(categorias.md 11.1: mascare a menção na versão pública)")
        if relato["id_externo"] is not None:
            res.aviso("privacidade", f"{p}relato.id_externo",
                      "versão pública com id_externo: o protocolo pode ligar o relato ao cidadão")
        if "endereco_residencial" in declarados:
            for i, oc in enumerate(a["ocorrencias"]):
                loc = oc["localizacao"]
                cam = f"{p}ocorrencias[{i}].localizacao"
                valor = loc["endereco_texto"]["valor"] or ""
                if re.search(r"\d", valor.replace("[NUMERO]", "")):
                    res.aviso("privacidade", f"{cam}.endereco_texto",
                              "versão pública com residência mascarada, mas o endereço ainda contém números; confira se não é o número da casa")
                if loc["precisao"] == "exata":
                    res.erro("privacidade", f"{cam}.precisao",
                             "com o número de residência mascarado, a precisão pública deve ser 'aproximada'")


def _validar_localizacao(res: Resultado, oc: dict, cam: str, pend: set) -> None:
    loc = oc["localizacao"]
    tem_info = any(loc[c]["status"] != "ausente" for c in CAMPOS_LOCALIZACAO)
    if loc["precisao"] == "ausente" and tem_info:
        res.erro("consistencia", f"{cam}.localizacao.precisao", "precisão 'ausente', mas há informação de local")
    if loc["precisao"] != "ausente" and not tem_info:
        res.erro("consistencia", f"{cam}.localizacao.precisao", f"precisão '{loc['precisao']}' sem nenhuma informação de local")
    if (loc["latitude"]["status"] == "ausente") != (loc["longitude"]["status"] == "ausente"):
        res.erro("consistencia", f"{cam}.localizacao", "latitude e longitude devem estar ambas presentes ou ambas ausentes")
    if loc["precisao"] == "exata":
        coordenada = loc["latitude"]["status"] != "ausente"
        numero = bool(re.search(r"\d", loc["endereco_texto"]["valor"] or ""))
        if not (coordenada or numero):
            res.aviso("consistencia", f"{cam}.localizacao.precisao", "precisão 'exata' sem número de imóvel nem coordenada")
    if loc["precisao"] == "ausente" and "localizacao_ausente" not in pend:
        res.erro("consistencia", f"{cam}.pendencias", "local não informado exige a pendência 'localizacao_ausente'")
    if loc["precisao"] != "ausente" and "localizacao_ausente" in pend:
        res.erro("consistencia", f"{cam}.pendencias", "pendência 'localizacao_ausente', mas há informação de local")
    if {"localizacao_ausente", "localizacao_imprecisa"} <= pend:
        res.erro("consistencia", f"{cam}.pendencias", "'localizacao_ausente' e 'localizacao_imprecisa' são excludentes")


def _validar_data(res: Resultado, oc: dict, cam: str, recebido_em: str | None) -> None:
    data = oc["data_ocorrencia"]
    if data["valor"] is None:
        # Data ausente pode guardar a expressão temporal não convertida (schema 1.1.0).
        if data["status"] == "ausente" and data["evidencia"] is not None:
            if _data_hora(recebido_em) is not None:
                res.aviso("consistencia", f"{cam}.data_ocorrencia",
                          "há expressão temporal e recebido_em: verifique se a data pode ser inferida")
            if not (data["raciocinio"] or "").strip():
                res.aviso("consistencia", f"{cam}.data_ocorrencia.raciocinio",
                          "explique por que a expressão temporal não foi convertida em data")
        return
    try:
        dia = dt.date.fromisoformat(data["valor"])
    except ValueError:
        res.erro("consistencia", f"{cam}.data_ocorrencia.valor", f"data inexistente: {data['valor']}")
        return
    recebido = _data_hora(recebido_em)
    if data["status"] == "inferido":
        if recebido is None:
            res.erro("consistencia", f"{cam}.data_ocorrencia",
                     "data inferida sem data de referência: expressões relativas só podem ser convertidas com recebido_em")
        if data["evidencia"] is None:
            res.erro("consistencia", f"{cam}.data_ocorrencia.evidencia",
                     "data inferida deve citar a expressão relativa do relato como evidência")
    if recebido is not None and dia > recebido.date():
        res.erro("consistencia", f"{cam}.data_ocorrencia.valor", "data da ocorrência posterior ao recebimento do relato")


def _validar_classificacao(res: Resultado, oc: dict, cam: str, pend: set, pend_relato: set) -> None:
    c = oc["classificacao"]
    if c["categoria_principal"] in c["categorias_secundarias"]:
        res.erro("consistencia", f"{cam}.classificacao.categorias_secundarias", "a categoria principal não pode ser secundária")
    if c["ambigua"] and "classificacao_ambigua" not in pend:
        res.erro("consistencia", f"{cam}.pendencias", "classificação ambígua exige a pendência 'classificacao_ambigua'")
    if not c["ambigua"] and "classificacao_ambigua" in pend:
        res.aviso("consistencia", f"{cam}.pendencias", "pendência 'classificacao_ambigua' sem ambigua=true")
    if c["confianca"] == "baixa":
        if "revisao_humana_recomendada" not in pend:
            res.erro("consistencia", f"{cam}.pendencias", "confiança baixa exige 'revisao_humana_recomendada'")
        if not (c["ambigua"] or "descricao_insuficiente" in pend | pend_relato):
            res.erro("consistencia", f"{cam}.classificacao", "confiança baixa exige ambigua=true ou a pendência 'descricao_insuficiente'")
    if c["regra_desempate"] == "rd01_acessibilidade_explicita" and c["categoria_principal"] != "acessibilidade":
        res.erro("consistencia", f"{cam}.classificacao.regra_desempate", "rd01 implica categoria principal 'acessibilidade'")
    if c["regra_desempate"] == "rd02_risco_estrutural_ou_desastre" and c["subcategoria"] not in ("inf_estrutura_publica", "seg_risco_desastre"):
        res.erro("consistencia", f"{cam}.classificacao.regra_desempate", "rd02 implica 'inf_estrutura_publica' ou 'seg_risco_desastre'")
    org = oc["orgao_sugerido"]
    if org["principal"] in org["apoio"]:
        res.erro("consistencia", f"{cam}.orgao_sugerido.apoio", "o órgão principal não pode estar entre os de apoio")


def _validar_alegacao(res: Resultado, oc: dict, cam: str, pend: set, permitir_verificado: bool) -> None:
    al = oc["alegacao_irregularidade"]
    if al["presente"]:
        if "verificar_alegacao" not in pend:
            res.erro("consistencia", f"{cam}.pendencias", "alegação de irregularidade exige a pendência 'verificar_alegacao'")
        if al["status_verificacao"] != "pendente_verificacao" and not permitir_verificado:
            res.erro("consistencia", f"{cam}.alegacao_irregularidade.status_verificacao",
                     "a skill registra alegações sempre como 'pendente_verificacao'")
        texto = _sem_acentos(al["descricao_neutra"])
        if not any(t in texto for t in ("aleg", "segundo o relat", "segundo relat", "relata-se", "o relato afirma", "o relator afirma")):
            res.aviso("consistencia", f"{cam}.alegacao_irregularidade.descricao_neutra",
                      "descrição sem linguagem de alegação (ex.: 'o relato alega que…')")
    elif "verificar_alegacao" in pend:
        res.aviso("consistencia", f"{cam}.pendencias", "pendência 'verificar_alegacao' sem alegação registrada")


def _validar_prioridade(res: Resultado, oc: dict, cam: str, pend: set) -> None:
    pr = oc["prioridade"]
    cpr = f"{cam}.prioridade"
    try:
        esperado = cp.calcular(pr["fatores"], oc["natureza"], cp.EX01 in pr["regras_aplicadas"],
                               cp.EX06 in pr["regras_aplicadas"], oc["classificacao"]["subcategoria"])
    except cp.ErroEntrada as e:
        for m in e.erros:
            res.erro("pontuacao", cpr, m)
        return
    ep = esperado["prioridade"]
    for campo in ("pontuacao", "pontuacao_teto", "nivel_base", "nivel", "nivel_teto", "pontuacao_provisoria", "versao_matriz"):
        if pr[campo] != ep[campo]:
            res.erro("pontuacao", f"{cpr}.{campo}", f"esperado {ep[campo]!r}, encontrado {pr[campo]!r}")
    if abs(pr["completude"] - ep["completude"]) > 0.005:
        res.erro("pontuacao", f"{cpr}.completude", f"esperado {ep['completude']}, encontrado {pr['completude']}")
    faltam = [r for r in ep["regras_aplicadas"] if r not in pr["regras_aplicadas"]]
    sobram = [r for r in pr["regras_aplicadas"] if r not in ep["regras_aplicadas"]]
    if faltam:
        res.erro("pontuacao", f"{cpr}.regras_aplicadas", f"regras com condição atendida e não registradas: {', '.join(faltam)}")
    if sobram:
        res.erro("pontuacao", f"{cpr}.regras_aplicadas", f"regras registradas sem condição atendida: {', '.join(sobram)}")
    for p_obrig in esperado["pendencias_obrigatorias"]:
        if p_obrig not in pend:
            res.erro("pontuacao", f"{cam}.pendencias", f"a prioridade exige a pendência '{p_obrig}'")
    if cp.PEND_COMPLEMENTAR in pend and cp.PEND_COMPLEMENTAR not in esperado["pendencias_obrigatorias"]:
        res.aviso("pontuacao", f"{cam}.pendencias", f"'{cp.PEND_COMPLEMENTAR}' sem fator ausente capaz de mudar o nível")

    just = pr["justificativa"]
    just_n = _sem_acentos(just)
    if not re.search(rf"(?<!\d){pr['pontuacao']}(?!\d)", just):
        res.erro("pontuacao", f"{cpr}.justificativa", "a justificativa não cita a pontuação")
    if _sem_acentos(cp.ROTULO_NIVEL[pr["nivel"]]) not in just_n:
        res.erro("pontuacao", f"{cpr}.justificativa", "a justificativa não cita o nível")
    for codigo, f in pr["fatores"].items():
        if f["nota"] and codigo not in just:
            res.aviso("pontuacao", f"{cpr}.justificativa", f"fator '{codigo}' (nota {f['nota']}) não é citado na justificativa")
    if pr["nivel"] != pr["nivel_base"] and not any(r in just for r in pr["regras_aplicadas"]):
        res.aviso("pontuacao", f"{cpr}.justificativa", "o nível difere da faixa base, mas a justificativa não cita a regra")
    if any(t in just.casefold() for t in TERMOS_PROIBIDOS):
        res.aviso("pontuacao", f"{cpr}.justificativa", "use 'prioridade de triagem', não 'avaliação/nível de risco'")


def _validar_status_verificado(res: Resultado, a: dict, p: str) -> None:
    def percorrer(obj, partes):
        if isinstance(obj, dict):
            if obj.get("status") == "verificado":
                res.erro("consistencia", p + _caminho(partes), "status 'verificado' é reservado ao sistema ou a revisor humano")
            for k, v in obj.items():
                percorrer(v, partes + (k,))
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                percorrer(v, partes + (i,))
    percorrer(a["ocorrencias"], ("ocorrencias",))


def validar_analise_semantica(a: dict, res: Resultado, prefixo: str = "", permitir_verificado: bool = False) -> None:
    p = prefixo
    texto = a["relato"]["texto_mascarado"]
    pend_relato = set(a["pendencias"])
    ids = [oc["id_ocorrencia"] for oc in a["ocorrencias"]]
    if ids != [f"oc-{i}" for i in range(1, len(ids) + 1)]:
        res.erro("consistencia", f"{p}ocorrencias", f"id_ocorrencia deve ser sequencial a partir de oc-1; encontrado {ids}")

    meta = a["metadados"]
    if meta["versao_matriz_prioridade"] != cp.VERSAO_MATRIZ:
        res.aviso("consistencia", f"{p}metadados.versao_matriz_prioridade",
                  f"matriz {meta['versao_matriz_prioridade']}; este validador implementa {cp.VERSAO_MATRIZ}")
    if meta["versao_taxonomia"] != VERSAO_TAXONOMIA:
        res.aviso("consistencia", f"{p}metadados.versao_taxonomia", f"taxonomia {meta['versao_taxonomia']}; esperada {VERSAO_TAXONOMIA}")
    analisado, recebido = _data_hora(meta["analisado_em"]), _data_hora(a["relato"]["recebido_em"])
    if analisado and recebido and analisado < recebido:
        res.erro("consistencia", f"{p}metadados.analisado_em", "análise anterior ao recebimento do relato")

    ex01_ids = set()
    for i, oc in enumerate(a["ocorrencias"]):
        cam = f"{p}ocorrencias[{i}]"
        pend = set(oc["pendencias"])
        if oc["prioridade"]["versao_matriz"] != meta["versao_matriz_prioridade"]:
            res.erro("consistencia", f"{cam}.prioridade.versao_matriz", "difere de metadados.versao_matriz_prioridade")
        _validar_classificacao(res, oc, cam, pend, pend_relato)
        _validar_localizacao(res, oc, cam, pend)
        _validar_data(res, oc, cam, a["relato"]["recebido_em"])
        _validar_alegacao(res, oc, cam, pend, permitir_verificado)
        _validar_prioridade(res, oc, cam, pend)
        if cp.EX01 in oc["prioridade"]["regras_aplicadas"]:
            ex01_ids.add(oc["id_ocorrencia"])

        for campo in CAMPOS_LOCALIZACAO:
            _checar_evidencia(res, oc["localizacao"][campo]["evidencia"], texto, f"{cam}.localizacao.{campo}.evidencia")
        _checar_evidencia(res, oc["data_ocorrencia"]["evidencia"], texto, f"{cam}.data_ocorrencia.evidencia")
        for codigo, f in oc["prioridade"]["fatores"].items():
            _checar_evidencia(res, f["evidencia"], texto, f"{cam}.prioridade.fatores.{codigo}.evidencia")

    alerta = a["alerta_emergencia"]
    origem = set(alerta["origem"])
    if ex01_ids and not alerta["acionar"]:
        res.erro("consistencia", f"{p}alerta_emergencia", f"{cp.EX01} em {sorted(ex01_ids)} exige alerta_emergencia.acionar=true")
    for faltando in sorted(ex01_ids - origem):
        if alerta["acionar"]:
            res.erro("consistencia", f"{p}alerta_emergencia.origem", f"{faltando} tem {cp.EX01} e não consta na origem do alerta")
    for o in sorted(origem - {"triagem"}):
        if o not in ids:
            res.erro("consistencia", f"{p}alerta_emergencia.origem", f"{o} não existe nas ocorrências")
        elif o not in ex01_ids:
            res.erro("consistencia", f"{p}alerta_emergencia.origem", f"{o} originou alerta sem {cp.EX01}")
    if "triagem" in origem and a["resultado_triagem"] == "classificado":
        res.aviso("consistencia", f"{p}alerta_emergencia.origem", "origem 'triagem' em relato classificado")

    if not permitir_verificado:
        _validar_status_verificado(res, a, p)
    _validar_privacidade(res, a, p)


def validar_lote_semantico(lote: dict, res: Resultado, permitir_verificado: bool = False) -> None:
    analises = lote["analises"]
    if lote["total_relatos"] != len(analises):
        res.erro("consistencia", "total_relatos", f"informado {lote['total_relatos']}, há {len(analises)} análises")
    ids = [a["id_analise"] for a in analises]
    for repetido in sorted({x for x in ids if ids.count(x) > 1}):
        res.erro("consistencia", "analises", f"id_analise repetido: {repetido}")
    for i, a in enumerate(analises):
        if a["visibilidade"] != lote["visibilidade"]:
            res.erro("privacidade", f"analises[{i}].visibilidade", f"difere da visibilidade do lote ({lote['visibilidade']})")
        for chave in ("versao_taxonomia", "versao_matriz_prioridade"):
            if a["metadados"][chave] != lote["metadados"][chave]:
                res.aviso("consistencia", f"analises[{i}].metadados.{chave}", "difere dos metadados do lote")
        validar_analise_semantica(a, res, prefixo=f"analises[{i}].", permitir_verificado=permitir_verificado)

    esperado = cp.resumo_lote(analises)
    for chave, valor in esperado.items():
        atual = lote["resumo"][chave]
        if isinstance(valor, dict):
            atual = {k: v for k, v in atual.items() if v}
        if atual != valor:
            res.erro("consistencia", f"resumo.{chave}", f"esperado {valor!r}, encontrado {lote['resumo'][chave]!r}")


# --------------------------------------------------------------------------- arquivo

def _validar_arquivo(res: Resultado, doc: dict, caminho: Path) -> None:
    m = gm.PADRAO_NOME_ARQUIVO.match(caminho.name)
    lote = doc.get("tipo_documento") == "lote_analises"
    ident = doc.get("id_lote" if lote else "id_analise", "")
    data = doc.get("gerado_em") if lote else (doc.get("metadados") or {}).get("analisado_em")
    vis = doc.get("visibilidade")
    if not m:
        res.aviso("arquivo", caminho.name, "nome fora da convenção <analise|lote>_AAAAMMDD-HHMMSS_<id8>_<visibilidade>.json")
    else:
        if m["prefixo"] != ("lote" if lote else "analise") or m["extensao"] != "json":
            res.erro("arquivo", caminho.name, "prefixo ou extensão não correspondem ao tipo_documento")
        if m["visibilidade"] != vis:
            res.erro("arquivo", caminho.name, f"nome indica '{m['visibilidade']}', documento é '{vis}'")
        if m["id8"] != ident[:8]:
            res.erro("arquivo", caminho.name, "os 8 caracteres do nome não correspondem ao identificador do documento")
        try:
            if data and m["carimbo"] != gm.carimbo(data):
                res.erro("arquivo", caminho.name, "data e hora do nome não correspondem ao documento")
        except ValueError:
            pass

    if vis == "interna":
        try:
            modo = caminho.stat().st_mode
            if modo & (stat.S_IRWXG | stat.S_IRWXO):
                res.aviso("arquivo", caminho.name, "arquivo interno acessível a outros usuários; use chmod 600")
        except OSError:
            pass
        try:
            dentro = subprocess.run(["git", "-C", str(caminho.parent), "rev-parse", "--is-inside-work-tree"],
                                    capture_output=True, text=True, timeout=10)
            if dentro.returncode == 0:
                ignorado = subprocess.run(["git", "-C", str(caminho.parent), "check-ignore", "-q", caminho.name],
                                          capture_output=True, timeout=10)
                if ignorado.returncode != 0:
                    res.erro("arquivo", caminho.name, "arquivo interno não está ignorado pelo Git; adicione 'saidas/**/*_interna.*' ao .gitignore")
        except (OSError, subprocess.SubprocessError):
            pass


# --------------------------------------------------------------------------- API

def validar_documento(doc, validador=None, caminho: Path | None = None, permitir_verificado: bool = False) -> Resultado:
    validador = validador or carregar_validador()
    res = Resultado()
    res.erros.extend(_erros_schema(validador, doc))
    if not res.erros:
        if doc["tipo_documento"] == "lote_analises":
            validar_lote_semantico(doc, res, permitir_verificado)
        else:
            validar_analise_semantica(doc, res, permitir_verificado=permitir_verificado)
    else:
        res.aviso("schema", "(raiz)", "verificações de consistência, evidência, pontuação e privacidade não executadas até o schema ser atendido")
    if caminho is not None and isinstance(doc, dict):
        _validar_arquivo(res, doc, caminho)
    return res


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("arquivos", nargs="+", type=Path)
    parser.add_argument("--json", action="store_true", help="saída em JSON")
    parser.add_argument("--estrito", action="store_true", help="trata avisos como erros")
    parser.add_argument("--permitir-verificado", action="store_true",
                        help="aceita status 'verificado' e alegações apuradas (documentos revisados pelo sistema)")
    parser.add_argument("--schema", type=Path, default=SCHEMA_PADRAO)
    args = parser.parse_args(argv)

    try:
        validador = carregar_validador(args.schema)
    except (RuntimeError, OSError, json.JSONDecodeError) as erro:
        print(f"erro: {erro}", file=sys.stderr)
        return 2

    saida, codigo = [], 0
    for caminho in args.arquivos:
        try:
            doc = json.loads(caminho.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as erro:
            print(f"erro ao ler {caminho}: {erro}", file=sys.stderr)
            return 2
        res = validar_documento(doc, validador, caminho, args.permitir_verificado)
        ok = res.valido and not (args.estrito and res.avisos)
        codigo = codigo or (0 if ok else 1)
        saida.append({
            "arquivo": str(caminho), "valido": ok,
            "erros": [a.como_dict() for a in res.erros], "avisos": [a.como_dict() for a in res.avisos],
        })

    if args.json:
        json.dump(saida if len(saida) > 1 else saida[0], sys.stdout, ensure_ascii=False, indent=2)
        print()
    else:
        for item in saida:
            n_e, n_a = len(item["erros"]), len(item["avisos"])
            estado = "VÁLIDO" if item["valido"] else "INVÁLIDO"
            print(f"{item['arquivo']}: {estado} ({n_e} erro(s), {n_a} aviso(s))")
            for a in item["erros"]:
                print(f"  ERRO  [{a['categoria']}] {a['caminho']}: {a['mensagem']}")
            for a in item["avisos"]:
                print(f"  AVISO [{a['categoria']}] {a['caminho']}: {a['mensagem']}")
    return codigo


if __name__ == "__main__":
    sys.exit(main())

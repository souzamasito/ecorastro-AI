#!/usr/bin/env python3
"""Calcula a prioridade de triagem do EcoRastro AI (matriz 1.1.0).

Implementa references/priorizacao.md. A análise decide as notas e os status
dos seis fatores, se há risco iminente (ex01) e se o relato descreve um semáforo
inoperante (ex06). Este script confere essas afirmações e faz o resto de
forma determinística: pontuação, teto, completude, níveis, regras de exceção,
pendências obrigatórias e justificativa.

Uso:
  calcular_prioridade.py ENTRADA.json        # ou "-" para a entrada padrão
  calcular_prioridade.py --atualizar ANALISE.json [OUTRA.json ...]

Entrada do modo simples:
  {"natureza": "problema_existente", "risco_iminente": false,
   "falha_controle_trafego": false, "subcategoria": "mob_semaforo",
   "fatores": {"risco_integridade_fisica": {"nota": 3, "status": "relatado",
               "evidencia": "...", "raciocinio": "..."}, ...}}
  Saída: {"prioridade": {...bloco do schema...}, "pendencias_obrigatorias": [...]}

Modo --atualizar: recebe uma analise_relato ou um lote_analises já montado e
recalcula a prioridade de cada ocorrência a partir dos fatores, gravando no
próprio arquivo. O risco iminente e a falha de controle de tráfego são lidos da
presença de "ex01_risco_iminente" e "ex06_falha_controle_trafego" em
regras_aplicadas; a subcategoria vem da classificação da ocorrência. Também ajusta as pendências de prioridade da ocorrência e,
num lote, o resumo.

Códigos de saída: 0 sucesso, 1 entrada inconsistente, 2 erro de uso ou arquivo.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

VERSAO_MATRIZ = "1.1.0"

PESOS = {
    "risco_integridade_fisica": 30,
    "abrangencia": 20,
    "vulnerabilidade_afetados": 15,
    "impacto_servico_essencial": 15,
    "persistencia": 10,
    "risco_agravamento": 10,
}
assert sum(PESOS.values()) == 100

NIVEIS = ("baixa", "media", "alta", "critica")
ROTULO_NIVEL = {"baixa": "baixa", "media": "média", "alta": "alta", "critica": "crítica"}
NATUREZAS = ("problema_existente", "necessidade_infraestrutura")
STATUS = ("relatado", "inferido", "verificado", "ausente")
STATUS_FACTUAL = ("relatado", "verificado")  # basta para ex01/ex02; "inferido" não basta

EX01 = "ex01_risco_iminente"
EX02 = "ex02_risco_fisico_grave_relatado"
EX03 = "ex03_risco_com_vulnerabilidade"
EX04 = "ex04_teto_necessidade_infraestrutura"
EX05 = "ex05_informacao_insuficiente"
EX06 = "ex06_falha_controle_trafego"
EX07 = "ex07_barreira_acesso_servico_essencial"
REGRAS = (EX01, EX02, EX03, EX04, EX05, EX06, EX07)
# Regras que dependem de uma afirmação da análise sobre o relato; o script só confere as condições.
REGRAS_AFIRMADAS = (EX01, EX06)
SUBCATEGORIA_SEMAFORO = "mob_semaforo"

PEND_COMPLEMENTAR = "complementar_dados_prioridade"
PEND_REVISAO = "revisao_humana_recomendada"

MINIMO_FATORES_AVALIADOS = 4  # completude < 0,67  <=>  menos de 4 de 6


class ErroEntrada(ValueError):
    """Entrada que não permite calcular a prioridade."""

    def __init__(self, erros: list[str]):
        self.erros = erros
        super().__init__("; ".join(erros))


def faixa(pontuacao: int) -> str:
    if pontuacao <= 29:
        return "baixa"
    if pontuacao <= 54:
        return "media"
    if pontuacao <= 74:
        return "alta"
    return "critica"


def _indice(nivel: str) -> int:
    return NIVEIS.index(nivel)


def _maior(a: str, b: str) -> str:
    return a if _indice(a) >= _indice(b) else b


def _menor(a: str, b: str) -> str:
    return a if _indice(a) <= _indice(b) else b


def arredondar_terco(soma: int) -> int:
    """Arredonda soma/3 para o inteiro mais próximo, com 0,5 para cima, sem ponto flutuante."""
    return (2 * soma + 3) // 6


def _texto_preenchido(valor) -> bool:
    return isinstance(valor, str) and valor.strip() != ""


def validar_fatores(fatores) -> list[str]:
    """Erros de estrutura e coerência dos fatores. Lista vazia se estiver tudo certo."""
    if not isinstance(fatores, dict):
        return ["'fatores' deve ser um objeto com os seis fatores"]
    erros = []
    faltando = [c for c in PESOS if c not in fatores]
    extras = [c for c in fatores if c not in PESOS]
    if faltando:
        erros.append(f"fatores ausentes do objeto: {', '.join(faltando)} (use status 'ausente' em vez de omitir)")
    if extras:
        erros.append(f"fatores desconhecidos: {', '.join(extras)}")
    for codigo in PESOS:
        fator = fatores.get(codigo)
        if fator is None:
            continue
        if not isinstance(fator, dict):
            erros.append(f"{codigo}: deve ser um objeto")
            continue
        nota, status = fator.get("nota"), fator.get("status")
        if status not in STATUS:
            erros.append(f"{codigo}: status inválido {status!r}")
            continue
        if status == "ausente":
            if nota is not None:
                erros.append(f"{codigo}: fator ausente deve ter nota null (ausente não é zero)")
        elif isinstance(nota, bool) or not isinstance(nota, int) or not 0 <= nota <= 3:
            erros.append(f"{codigo}: nota deve ser inteiro de 0 a 3 quando o status é {status!r}")
        if status == "relatado" and not _texto_preenchido(fator.get("evidencia")):
            erros.append(f"{codigo}: status 'relatado' exige evidência literal")
        if status == "ausente" and fator.get("evidencia") is not None:
            erros.append(f"{codigo}: fator ausente não pode ter evidência")
        if status == "verificado" and not isinstance(fator.get("verificacao"), dict):
            erros.append(f"{codigo}: status 'verificado' exige bloco 'verificacao'")
        if not _texto_preenchido(fator.get("raciocinio")):
            erros.append(f"{codigo}: 'raciocinio' é obrigatório")
    return erros


def _normalizar_fator(fator: dict) -> dict:
    return {
        "nota": fator.get("nota"),
        "status": fator.get("status"),
        "evidencia": fator.get("evidencia"),
        "raciocinio": fator.get("raciocinio"),
        "verificacao": fator.get("verificacao"),
    }


def _resumir(texto: str, limite: int = 90) -> str:
    texto = " ".join(texto.split())
    if len(texto) <= limite:
        return texto
    corte = texto[:limite].rsplit(" ", 1)[0]
    return corte + "…"


def montar_justificativa(fatores: dict, r: dict, passos: list[tuple[str, str, str]]) -> str:
    """Texto rastreável no formato da seção 8 de priorizacao.md."""
    cabecalho = f"Prioridade de triagem {ROTULO_NIVEL[r['nivel']]} ({r['pontuacao']} pts"
    if r["pontuacao_provisoria"]:
        cabecalho += ", provisória"
    if r["nivel"] != r["nivel_base"]:
        cabecalho += f"; faixa base {ROTULO_NIVEL[r['nivel_base']]}"
    partes = [cabecalho + ")."]

    avaliados = []
    for codigo in PESOS:
        f = fatores[codigo]
        if f["nota"] is None:
            continue
        base = f'"{_resumir(f["evidencia"])}"' if f["evidencia"] else _resumir(f["raciocinio"])
        avaliados.append(f"{codigo} {f['nota']} ({f['status']}: {base})")
    if avaliados:
        partes.append("Fatores: " + "; ".join(avaliados) + ".")

    ausentes = [c for c in PESOS if fatores[c]["nota"] is None]
    if ausentes:
        partes.append("Não informados: " + ", ".join(ausentes) + ".")

    regras_que_alteraram = set()
    for regra, de, para in passos:
        regras_que_alteraram.add(regra)
        partes.append(f"{regra} alterou de {ROTULO_NIVEL[de]} para {ROTULO_NIVEL[para]}.")
    sem_efeito = [x for x in r["regras_aplicadas"] if x not in regras_que_alteraram and x != EX05]
    if sem_efeito:
        partes.append("Regras consideradas sem alterar o nível: " + ", ".join(sem_efeito) + ".")
    if EX05 in r["regras_aplicadas"]:
        partes.append(f"{EX05}: menos de {MINIMO_FATORES_AVALIADOS} fatores avaliados, pontuação provisória.")

    if _indice(r["nivel_teto"]) > _indice(r["nivel"]):
        frase = (
            f"Pode chegar a {ROTULO_NIVEL[r['nivel_teto']]} ({r['pontuacao_teto']} pts) "
            "se os fatores não informados forem confirmados no grau máximo"
        )
        if EX04 in r["regras_aplicadas"] and _indice(faixa(r["pontuacao_teto"])) > _indice("alta"):
            frase += f", limitada a alta por {EX04}"
        partes.append(frase + ".")
    return " ".join(partes)


def _condicoes_ex06(f: dict, subcategoria) -> list[str]:
    """Motivos pelos quais ex06 não pode ser aplicada (lista vazia se pode)."""
    faltas = []
    if subcategoria != SUBCATEGORIA_SEMAFORO:
        faltas.append(f"subcategoria {SUBCATEGORIA_SEMAFORO} (encontrada {subcategoria!r})")
    for codigo in ("abrangencia", "risco_integridade_fisica"):
        fator = f[codigo]
        if (fator["nota"] or 0) < 2:
            faltas.append(f"{codigo} >= 2 (encontrada {fator['nota']!r}, {fator['status']})")
        elif not _texto_preenchido(fator["evidencia"]):
            faltas.append(f"{codigo} com evidência literal do relato")
    return faltas


def calcular(fatores: dict, natureza: str, risco_iminente: bool = False,
             falha_controle_trafego: bool = False, subcategoria: str | None = None) -> dict:
    """Calcula o bloco 'prioridade' e as pendências obrigatórias.

    Levanta ErroEntrada se os fatores forem inconsistentes, se ex01 for pedido
    sem a base exigida (risco físico 3, relatado ou verificado) ou se ex06 for
    pedido sem as condições da seção 6 (semáforo, abrangência e risco >= 2 com
    evidência literal).
    """
    erros = validar_fatores(fatores)
    if natureza not in NATUREZAS:
        erros.append(f"natureza inválida: {natureza!r}")
    if not isinstance(risco_iminente, bool):
        erros.append("risco_iminente deve ser true ou false")
    if not isinstance(falha_controle_trafego, bool):
        erros.append("falha_controle_trafego deve ser true ou false")
    if erros:
        raise ErroEntrada(erros)

    f = {c: _normalizar_fator(fatores[c]) for c in PESOS}
    risco = f["risco_integridade_fisica"]
    vulnerabilidade = f["vulnerabilidade_afetados"]
    if risco_iminente and not (risco["nota"] == 3 and risco["status"] in STATUS_FACTUAL):
        raise ErroEntrada([
            f"{EX01} exige risco_integridade_fisica com nota 3 e status relatado "
            "(perigo atual, concreto e descrito no relato); uma dedução da análise não basta"
        ])
    if falha_controle_trafego:
        faltas = _condicoes_ex06(f, subcategoria)
        if faltas:
            raise ErroEntrada([
                f"{EX06} exige semáforo inoperante relatado e: " + "; ".join(faltas)
                + ". Retire a regra ou corrija a avaliação; não force o nível"
            ])
    servico = f["impacto_servico_essencial"]

    soma_piso = sum(PESOS[c] * (f[c]["nota"] or 0) for c in PESOS)
    soma_teto = sum(PESOS[c] * (3 if f[c]["nota"] is None else f[c]["nota"]) for c in PESOS)
    avaliados = sum(f[c]["nota"] is not None for c in PESOS)
    pontuacao = arredondar_terco(soma_piso)
    pontuacao_teto = arredondar_terco(soma_teto)
    nivel_base = faixa(pontuacao)

    aplica = {
        EX01: risco_iminente,
        EX02: risco["nota"] == 3 and risco["status"] in STATUS_FACTUAL,
        EX03: (risco["nota"] or 0) >= 2 and (vulnerabilidade["nota"] or 0) >= 2,
        EX04: natureza == "necessidade_infraestrutura" and not risco_iminente,
        EX05: avaliados < MINIMO_FATORES_AVALIADOS,
        EX06: falha_controle_trafego,
        EX07: (vulnerabilidade["nota"] == 3 and vulnerabilidade["status"] in STATUS_FACTUAL
               and (servico["nota"] or 0) >= 2 and servico["status"] in STATUS_FACTUAL),
    }

    nivel, passos = nivel_base, []

    def ajustar(regra: str, novo: str) -> None:
        nonlocal nivel
        if novo != nivel:
            passos.append((regra, nivel, novo))
            nivel = novo

    # Ordem da seção 6: mínimos, máximo, ex01 por último (prevalece).
    if aplica[EX02]:
        ajustar(EX02, _maior(nivel, "alta"))
    if aplica[EX03]:
        ajustar(EX03, _maior(nivel, "alta"))
    if aplica[EX06]:
        ajustar(EX06, _maior(nivel, "alta"))
    if aplica[EX07]:
        ajustar(EX07, _maior(nivel, "alta"))
    if aplica[EX04]:
        ajustar(EX04, _menor(nivel, "alta"))
    if aplica[EX01]:
        ajustar(EX01, "critica")

    nivel_teto = faixa(pontuacao_teto)
    if aplica[EX04]:
        nivel_teto = _menor(nivel_teto, "alta")
    nivel_teto = _maior(nivel_teto, nivel)

    regras = [r for r in REGRAS if aplica[r]]
    prioridade = {
        "versao_matriz": VERSAO_MATRIZ,
        "fatores": f,
        "pontuacao": pontuacao,
        "pontuacao_teto": pontuacao_teto,
        "completude": round(avaliados / len(PESOS), 2),
        "nivel_base": nivel_base,
        "nivel": nivel,
        "nivel_teto": nivel_teto,
        "pontuacao_provisoria": aplica[EX05],
        "regras_aplicadas": regras,
        "justificativa": "",
    }
    prioridade["justificativa"] = montar_justificativa(f, prioridade, passos)

    pendencias = []
    if _indice(nivel_teto) > _indice(nivel) or aplica[EX05]:
        pendencias.append(PEND_COMPLEMENTAR)
    if aplica[EX05] or aplica[EX01]:
        pendencias.append(PEND_REVISAO)
    return {"prioridade": prioridade, "pendencias_obrigatorias": pendencias}


def resumo_lote(analises: list[dict]) -> dict:
    """Contagens do bloco 'resumo' de um lote_analises (somente valores maiores que zero)."""
    triagem, categoria, nivel, natureza = Counter(), Counter(), Counter(), Counter()
    total_oc = alertas = alegacoes = 0
    for analise in analises:
        triagem[analise["resultado_triagem"]] += 1
        if analise["alerta_emergencia"]["acionar"]:
            alertas += 1
        for oc in analise["ocorrencias"]:
            total_oc += 1
            categoria[oc["classificacao"]["categoria_principal"]] += 1
            nivel[oc["prioridade"]["nivel"]] += 1
            natureza[oc["natureza"]] += 1
            if oc["alegacao_irregularidade"]["presente"]:
                alegacoes += 1
    return {
        "por_resultado_triagem": dict(triagem),
        "por_categoria": dict(categoria),
        "por_nivel": dict(nivel),
        "por_natureza": dict(natureza),
        "total_ocorrencias": total_oc,
        "total_alertas_emergencia": alertas,
        "total_alegacoes": alegacoes,
    }


def atualizar_analise(analise: dict, prefixo: str = "") -> list[str]:
    """Recalcula a prioridade de todas as ocorrências, no próprio dicionário. Devolve linhas de log."""
    log, erros = [], []
    for i, oc in enumerate(analise.get("ocorrencias", [])):
        rotulo = f"{prefixo}{oc.get('id_ocorrencia', f'ocorrencias[{i}]')}"
        atual = oc.get("prioridade") or {}
        try:
            regras_atuais = atual.get("regras_aplicadas") or []
            r = calcular(
                atual.get("fatores"),
                oc.get("natureza"),
                EX01 in regras_atuais,
                EX06 in regras_atuais,
                (oc.get("classificacao") or {}).get("subcategoria"),
            )
        except ErroEntrada as e:
            erros.extend(f"{rotulo}: {m}" for m in e.erros)
            continue
        oc["prioridade"] = r["prioridade"]
        pend = [p for p in oc.get("pendencias", []) if p != PEND_COMPLEMENTAR]
        for p in r["pendencias_obrigatorias"]:
            if p not in pend:
                pend.append(p)
        oc["pendencias"] = pend
        p = r["prioridade"]
        log.append(f"{rotulo}: {p['nivel']} ({p['pontuacao']} pts, teto {p['pontuacao_teto']}, regras: {', '.join(p['regras_aplicadas']) or 'nenhuma'})")
    if erros:
        raise ErroEntrada(erros)
    if "metadados" in analise:
        analise["metadados"]["versao_matriz_prioridade"] = VERSAO_MATRIZ
    return log


def atualizar_documento(doc: dict) -> list[str]:
    if doc.get("tipo_documento") == "lote_analises":
        log, erros = [], []
        for i, analise in enumerate(doc.get("analises", [])):
            try:
                log += atualizar_analise(analise, prefixo=f"analises[{i}].")
            except ErroEntrada as e:
                erros += e.erros
        if erros:
            raise ErroEntrada(erros)
        doc["resumo"] = resumo_lote(doc["analises"])
        doc["metadados"]["versao_matriz_prioridade"] = VERSAO_MATRIZ
        return log
    if doc.get("tipo_documento") == "analise_relato":
        return atualizar_analise(doc)
    raise ErroEntrada(["tipo_documento deve ser 'analise_relato' ou 'lote_analises'"])


def _ler_json(origem: str):
    texto = sys.stdin.read() if origem == "-" else Path(origem).read_text(encoding="utf-8")
    return json.loads(texto)


def _atualizar_arquivos(caminhos: list[str]) -> int:
    """Cada arquivo é tratado à parte: um erro num deles não grava nada nele e não impede os outros."""
    pior = 0
    for caminho in caminhos:
        try:
            doc = _ler_json(caminho)
        except (OSError, json.JSONDecodeError) as erro:
            print(f"{caminho}: erro ao ler JSON: {erro}", file=sys.stderr)
            pior = max(pior, 2)
            continue
        try:
            log = atualizar_documento(doc)
        except ErroEntrada as erro:
            for mensagem in erro.erros:
                print(f"{caminho}: erro: {mensagem}", file=sys.stderr)
            pior = max(pior, 1)
            continue
        Path(caminho).write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        for linha in log:
            print(linha, file=sys.stderr)
        print(f"prioridades atualizadas em {caminho}", file=sys.stderr)
    return pior


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    grupo = parser.add_mutually_exclusive_group(required=True)
    grupo.add_argument("entrada", nargs="?", help="JSON com natureza, risco_iminente e fatores ('-' para a entrada padrão)")
    grupo.add_argument("--atualizar", metavar="ANALISE.json", nargs="+",
                       help="recalcula e grava a prioridade de todas as ocorrências (aceita vários arquivos)")
    args = parser.parse_args(argv)

    if args.atualizar:
        return _atualizar_arquivos(args.atualizar)

    try:
        doc = _ler_json(args.entrada)
    except (OSError, json.JSONDecodeError) as erro:
        print(f"erro ao ler JSON: {erro}", file=sys.stderr)
        return 2

    try:
        if not isinstance(doc, dict):
            raise ErroEntrada(["a entrada deve ser um objeto JSON"])
        resultado = calcular(doc.get("fatores"), doc.get("natureza"), doc.get("risco_iminente", False),
                             doc.get("falha_controle_trafego", False), doc.get("subcategoria"))
    except ErroEntrada as erro:
        for mensagem in erro.erros:
            print(f"erro: {mensagem}", file=sys.stderr)
        return 1

    json.dump(resultado, sys.stdout, ensure_ascii=False, indent=2)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())

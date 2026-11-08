#!/usr/bin/env python3
"""Gera identificadores, hash e nomes de arquivo para o EcoRastro AI.

Substitui os comandos embutidos no SKILL.md. Também é importado por
validar_analise.py, para que o hash e a convenção de nomes tenham uma única
implementação.

Uso:
  gerar_metadados.py analise [--arquivo TEXTO.txt]   # texto do relato pela entrada padrão
  gerar_metadados.py lote [--arquivo RELATOS.csv|.json] [--coluna-texto NOME]
  gerar_metadados.py nomes --tipo analise|lote --id UUID --data ISO8601

Saída: JSON na saída padrão.

Lote com --arquivo: lê o CSV (ou uma lista JSON de objetos) uma vez e devolve,
para cada linha com texto, id_analise, hash_texto, analisado_em e os campos
id_externo, canal e recebido_em já no formato do schema. Linhas vazias saem em
"linhas_ignoradas". Nada é inventado: recebido_em só é preenchido quando a
coluna traz data e hora ISO 8601 com fuso; canal desconhecido vira "outro" e
gera aviso. O texto de cada relato continua sendo analisado um a um.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import re
import sys
import unicodedata
import uuid
from pathlib import Path

PASTA_JSON = "saidas/json"
PASTA_RELATORIOS = "saidas/relatorios"
VISIBILIDADES = ("interna", "publica")

# analise_20261107-093112_3f2b6c1e_interna.json
PADRAO_NOME_ARQUIVO = re.compile(
    r"^(?P<prefixo>analise|lote|relatorio)_(?P<carimbo>\d{8}-\d{6})_"
    r"(?P<id8>[0-9a-f]{8})_(?P<visibilidade>interna|publica)\.(?P<extensao>json|md)$"
)


def normalizar_texto(texto: str) -> str:
    """NFC, espaços em branco colapsados e sem espaços nas pontas."""
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", texto)).strip()


def calcular_hash(texto: str) -> str:
    """SHA-256 (hex) do texto original normalizado."""
    return hashlib.sha256(normalizar_texto(texto).encode("utf-8")).hexdigest()


def agora_iso() -> str:
    """Data e hora local com fuso, em segundos (ex.: 2026-11-07T09:31:12-03:00)."""
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def novo_uuid() -> str:
    return str(uuid.uuid4())


def carimbo(data_iso: str) -> str:
    """AAAAMMDD-HHMMSS no horário escrito na própria data (sem converter fuso)."""
    momento = dt.datetime.fromisoformat(data_iso)
    return momento.strftime("%Y%m%d-%H%M%S")


def nome_arquivo(prefixo: str, id_documento: str, data_iso: str, visibilidade: str) -> str:
    if prefixo not in ("analise", "lote", "relatorio"):
        raise ValueError(f"prefixo inválido: {prefixo}")
    if visibilidade not in VISIBILIDADES:
        raise ValueError(f"visibilidade inválida: {visibilidade}")
    extensao = "md" if prefixo == "relatorio" else "json"
    return f"{prefixo}_{carimbo(data_iso)}_{id_documento[:8]}_{visibilidade}.{extensao}"


def nomes_saida(tipo: str, id_documento: str, data_iso: str) -> dict[str, str]:
    """Caminhos relativos à raiz do projeto para as quatro saídas possíveis."""
    if tipo not in ("analise", "lote"):
        raise ValueError(f"tipo inválido: {tipo}")
    nomes = {}
    for vis in VISIBILIDADES:
        nomes[f"json_{vis}"] = f"{PASTA_JSON}/{nome_arquivo(tipo, id_documento, data_iso, vis)}"
        nomes[f"relatorio_{vis}"] = f"{PASTA_RELATORIOS}/{nome_arquivo('relatorio', id_documento, data_iso, vis)}"
    return nomes


CANAIS = ("app", "web", "whatsapp", "telefone", "email", "presencial", "rede_social", "outro", "nao_informado")
SINONIMOS_CANAL = {
    "aplicativo": "app", "site": "web", "portal": "web", "internet": "web", "zap": "whatsapp", "wpp": "whatsapp",
    "e-mail": "email", "fone": "telefone", "ligacao": "telefone", "156": "telefone", "balcao": "presencial",
    "atendimento presencial": "presencial", "instagram": "rede_social", "facebook": "rede_social", "twitter": "rede_social",
}
COLUNAS_TEXTO = ("texto", "relato", "descricao", "mensagem", "reclamacao", "conteudo")
COLUNAS_ID = ("id", "protocolo", "id_externo", "codigo")
COLUNAS_CANAL = ("canal", "origem", "meio")
COLUNAS_DATA = ("recebido_em", "data_recebimento", "data", "data_hora", "criado_em")
PADRAO_DATA_HORA = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2})?([+-]\d{2}:\d{2}|Z)$")


def _chave(nome: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode()
    return sem_acento.strip().lower()


def _coluna(colunas: list[str], candidatos: tuple[str, ...], forcada: str | None = None) -> str | None:
    if forcada:
        return forcada if forcada in colunas else None
    por_chave = {_chave(c): c for c in colunas}
    for cand in candidatos:
        if cand in por_chave:
            return por_chave[cand]
    return None


def normalizar_canal(valor: str | None) -> tuple[str, str | None]:
    """Devolve (canal, aviso). Vazio vira nao_informado; desconhecido vira outro, com aviso."""
    if valor is None or not valor.strip():
        return "nao_informado", None
    chave = _chave(valor).replace("_", " ")
    if chave.replace(" ", "_") in CANAIS:
        return chave.replace(" ", "_"), None
    if chave in SINONIMOS_CANAL:
        return SINONIMOS_CANAL[chave], None
    return "outro", f"canal '{valor}' não reconhecido; registrado como 'outro'"


def normalizar_recebido_em(valor: str | None) -> tuple[str | None, str | None]:
    """Só aceita data e hora ISO 8601 com fuso. Data sem hora ou sem fuso não é completada."""
    if valor is None or not valor.strip():
        return None, None
    valor = valor.strip()
    if PADRAO_DATA_HORA.match(valor):
        try:
            dt.datetime.fromisoformat(valor.replace("Z", "+00:00"))
            return valor, None
        except ValueError:
            pass
    return None, (f"recebido_em '{valor}' não está em data e hora ISO 8601 com fuso; ficou null "
                  "(não complete hora nem fuso por conta própria)")


def ler_relatos(caminho: Path) -> list[dict[str, str]]:
    if caminho.suffix.lower() == ".json":
        dados = json.loads(caminho.read_text(encoding="utf-8"))
        if not isinstance(dados, list) or not all(isinstance(x, dict) for x in dados):
            raise ValueError("o JSON de entrada deve ser uma lista de objetos")
        return [{k: ("" if v is None else str(v)) for k, v in x.items()} for x in dados]
    with caminho.open(encoding="utf-8-sig", newline="") as f:
        amostra = f.read(4096)
        f.seek(0)
        try:
            dialeto = csv.Sniffer().sniff(amostra, delimiters=",;\t")
        except csv.Error:
            dialeto = csv.excel
        return list(csv.DictReader(f, dialect=dialeto))


def metadados_lote(caminho: Path, coluna_texto: str | None = None) -> dict:
    linhas = ler_relatos(caminho)
    colunas = list(linhas[0].keys()) if linhas else []
    c_texto = _coluna(colunas, COLUNAS_TEXTO, coluna_texto)
    if c_texto is None:
        raise ValueError(f"coluna de texto não encontrada (colunas: {colunas}); use --coluna-texto")
    c_id, c_canal, c_data = _coluna(colunas, COLUNAS_ID), _coluna(colunas, COLUNAS_CANAL), _coluna(colunas, COLUNAS_DATA)
    ident, momento = novo_uuid(), agora_iso()
    relatos, ignoradas, avisos = [], [], []
    for n, linha in enumerate(linhas, start=1):
        texto = linha.get(c_texto) or ""
        id_externo = ((linha.get(c_id) or "").strip() or None) if c_id else None
        if not normalizar_texto(texto):
            ignoradas.append({"linha": n, "id_externo": id_externo, "motivo": "texto vazio"})
            continue
        canal, aviso_canal = normalizar_canal(linha.get(c_canal) if c_canal else None)
        recebido_em, aviso_data = normalizar_recebido_em(linha.get(c_data) if c_data else None)
        for aviso in (aviso_canal, aviso_data):
            if aviso:
                avisos.append(f"linha {n}: {aviso}")
        id_analise, analisado_em = novo_uuid(), agora_iso()
        relatos.append({
            "linha": n, "id_externo": id_externo, "canal": canal, "recebido_em": recebido_em,
            "id_analise": id_analise, "hash_texto": calcular_hash(texto), "analisado_em": analisado_em,
            "texto_original": texto,
        })
    return {
        "id_lote": ident, "gerado_em": momento, "arquivos": nomes_saida("lote", ident, momento),
        "colunas_usadas": {"texto": c_texto, "id_externo": c_id, "canal": c_canal, "recebido_em": c_data},
        "total_linhas": len(linhas), "total_relatos": len(relatos),
        "relatos": relatos, "linhas_ignoradas": ignoradas, "avisos": avisos,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="comando", required=True)

    p_analise = sub.add_parser("analise", help="id_analise, hash_texto, analisado_em e nomes de arquivo")
    p_analise.add_argument("--arquivo", type=Path, help="arquivo com o texto original (padrão: entrada padrão)")

    p_lote = sub.add_parser("lote", help="id_lote, gerado_em e nomes de arquivo; com --arquivo, metadados de cada relato")
    p_lote.add_argument("--arquivo", type=Path, help="CSV ou lista JSON com os relatos")
    p_lote.add_argument("--coluna-texto", help="nome exato da coluna de texto, se a detecção automática falhar")

    p_nomes = sub.add_parser("nomes", help="nomes de arquivo para um documento existente")
    p_nomes.add_argument("--tipo", choices=("analise", "lote"), required=True)
    p_nomes.add_argument("--id", required=True)
    p_nomes.add_argument("--data", required=True, help="analisado_em ou gerado_em do documento")

    args = parser.parse_args(argv)

    if args.comando == "analise":
        texto = args.arquivo.read_text(encoding="utf-8") if args.arquivo else sys.stdin.read()
        if not normalizar_texto(texto):
            print("erro: texto do relato vazio", file=sys.stderr)
            return 2
        ident, momento = novo_uuid(), agora_iso()
        saida = {
            "id_analise": ident,
            "hash_texto": calcular_hash(texto),
            "analisado_em": momento,
            "arquivos": nomes_saida("analise", ident, momento),
        }
    elif args.comando == "lote" and args.arquivo:
        try:
            saida = metadados_lote(args.arquivo, args.coluna_texto)
        except (OSError, ValueError, json.JSONDecodeError) as erro:
            print(f"erro: {erro}", file=sys.stderr)
            return 2
    elif args.comando == "lote":
        ident, momento = novo_uuid(), agora_iso()
        saida = {"id_lote": ident, "gerado_em": momento, "arquivos": nomes_saida("lote", ident, momento)}
    else:
        try:
            saida = nomes_saida(args.tipo, args.id, args.data)
        except ValueError as erro:
            print(f"erro: {erro}", file=sys.stderr)
            return 2

    json.dump(saida, sys.stdout, ensure_ascii=False, indent=2)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())

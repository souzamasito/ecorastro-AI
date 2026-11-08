"""Documentos de teste baseados nos exemplos de references/priorizacao.md.

Cada função devolve um documento novo e válido; os testes alteram cópias para
provocar cada tipo de erro.
"""
from __future__ import annotations

import sys
from pathlib import Path

DIR_SCRIPTS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(DIR_SCRIPTS))

import calcular_prioridade as cp  # noqa: E402
import gerar_metadados as gm  # noqa: E402

RECEBIDO_EM = "2026-11-07T09:30:00-03:00"
ANALISADO_EM = "2026-11-07T09:31:12-03:00"


def info(valor, status, evidencia=None, raciocinio=None):
    return {"valor": valor, "status": status, "evidencia": evidencia, "raciocinio": raciocinio, "verificacao": None}


def ausente(raciocinio="Não informado no relato."):
    return info(None, "ausente", raciocinio=raciocinio)


def fator(nota, status, evidencia=None, raciocinio="Base descrita no teste."):
    return {"nota": nota, "status": status, "evidencia": evidencia, "raciocinio": raciocinio, "verificacao": None}


def fator_ausente(raciocinio="O relato não permite avaliar."):
    return fator(None, "ausente", raciocinio=raciocinio)


# --- Fatores dos quatro exemplos calculados (seção 9 de priorizacao.md) ---------

def fatores_buraco():
    return {
        "risco_integridade_fisica": fator(3, "relatado", "um motoqueiro caiu ali e se machucou", "Dano físico já ocorrido."),
        "abrangencia": fator(1, "inferido", raciocinio="Via pública; fluxo não informado."),
        "vulnerabilidade_afetados": fator_ausente("Não diz quem circula no local."),
        "impacto_servico_essencial": fator_ausente("Não diz se o buraco bloqueia acesso."),
        "persistencia": fator(1, "inferido", "tá ficando cada vez maior", "O crescimento indica que já existe há algum tempo."),
        "risco_agravamento": fator(2, "relatado", "Com a chuva o buraco tá ficando cada vez maior", "Piora relatada."),
    }


def fatores_fio():
    return {
        "risco_integridade_fisica": fator(3, "relatado", "tá soltando faísca no chão molhado", "Fio energizado ao alcance de pessoas."),
        "abrangencia": fator(2, "inferido", "as crianças tão saindo da escola agora", "Esquina de avenida em horário de saída escolar."),
        "vulnerabilidade_afetados": fator(3, "relatado", "as crianças tão saindo da escola agora", "Crianças diretamente expostas."),
        "impacto_servico_essencial": fator_ausente("Não diz se há falta de energia."),
        "persistencia": fator_ausente("Não diz quando o fio caiu."),
        "risco_agravamento": fator(3, "relatado", "soltando faísca no chão molhado", "Risco de choque e curto-circuito."),
    }


def fatores_ciclovia():
    return {
        "risco_integridade_fisica": fator(2, "inferido", "tem que dividir a pista com os carros e ônibus", "Exposição a colisão."),
        "abrangencia": fator(2, "relatado", "Muita gente vai de bicicleta pro trabalho", "Muitos usuários relatados."),
        "vulnerabilidade_afetados": fator_ausente(),
        "impacto_servico_essencial": fator(1, "inferido", raciocinio="Afeta o deslocamento ao trabalho; há alternativa."),
        "persistencia": fator_ausente(),
        "risco_agravamento": fator(0, "inferido", raciocinio="A falta de ciclovia é uma condição estável."),
    }


def fatores_poste():
    return {
        "risco_integridade_fisica": fator(1, "inferido", "poste apagado", "Trecho escuro aumenta o risco de queda à noite."),
        "abrangencia": fator(1, "inferido", raciocinio="Um poste ilumina um trecho de rua."),
        "vulnerabilidade_afetados": fator_ausente(),
        "impacto_servico_essencial": fator_ausente(),
        "persistencia": fator_ausente("Não diz desde quando."),
        "risco_agravamento": fator(0, "inferido", raciocinio="Lâmpada apagada não piora sozinha."),
    }


def fatores_esgoto():
    """Exemplo 9.5 (matriz 1.1.0, âncoras A1 e A2)."""
    return {
        "risco_integridade_fisica": fator(2, "inferido", "esgoto vazando na Rua Bahia", "Risco potencial à saúde (A1)."),
        "abrangencia": fator(1, "inferido", raciocinio="Trecho de rua; extensão não informada."),
        "vulnerabilidade_afetados": fator_ausente("Não diz quem circula ou mora no trecho."),
        "impacto_servico_essencial": fator(2, "relatado", "esgoto vazando", "Falha localizada do próprio serviço (A2)."),
        "persistencia": fator(1, "relatado", "há 2 semanas", "Limite entre 1 e 2."),
        "risco_agravamento": fator(2, "inferido", raciocinio="Vazamento tende a aumentar."),
    }


def fatores_semaforo():
    """Exemplo 9.6 (ex06)."""
    return {
        "risco_integridade_fisica": fator(2, "relatado", "quase vi uma batida", "Quase-acidente: risco, não dano."),
        "abrangencia": fator(2, "inferido", "Av. Paraná x Rua 3", "Cruzamento de avenida."),
        "vulnerabilidade_afetados": fator_ausente(),
        "impacto_servico_essencial": fator_ausente(),
        "persistencia": fator(0, "relatado", "desde manhã", "Menos de 24 horas."),
        "risco_agravamento": fator(0, "inferido", raciocinio="Não piora sozinho."),
    }


def fatores_escola():
    """Exemplo 9.7 (ex07, obra de adequação)."""
    return {
        "risco_integridade_fisica": fator(1, "inferido", raciocinio="Risco baixo de queda ao tentar entrar."),
        "abrangencia": fator(2, "inferido", raciocinio="Equipamento de bairro."),
        "vulnerabilidade_afetados": fator(3, "relatado", "um aluno cadeirante", "Grupo vulnerável diretamente afetado."),
        "impacto_servico_essencial": fator(2, "relatado", "não conseguem entrar", "Educação impedida para parte do público."),
        "persistencia": fator(1, "inferido", raciocinio="Falta estrutural."),
        "risco_agravamento": fator(0, "inferido", raciocinio="Condição estável."),
    }


# --- Documentos completos --------------------------------------------------------

def _localizacao(endereco=None, evidencia=None, precisao="aproximada"):
    return {
        "endereco_texto": info(endereco, "relatado", evidencia) if endereco else ausente(),
        "bairro": ausente(),
        "ponto_referencia": ausente(),
        "municipio": ausente(),
        "latitude": ausente(),
        "longitude": ausente(),
        "precisao": precisao if endereco else "ausente",
    }


def _ocorrencia(descricao, natureza, categoria, subcategoria, orgao, localizacao, data, fatores,
                risco_iminente=False, pendencias_extra=(), falha_controle_trafego=False, requer_obra_adequacao=False):
    r = cp.calcular(fatores, natureza, risco_iminente, falha_controle_trafego, subcategoria)
    pend = list(pendencias_extra)
    for p in r["pendencias_obrigatorias"]:
        if p not in pend:
            pend.append(p)
    return {
        "id_ocorrencia": "oc-1",
        "descricao_neutra": descricao,
        "natureza": natureza,
        "classificacao": {
            "categoria_principal": categoria, "subcategoria": subcategoria, "categorias_secundarias": [],
            "ambigua": False, "motivo_ambiguidade": None, "regra_desempate": None,
            "confianca": "alta", "raciocinio": "Encaixe direto na subcategoria.",
        },
        "localizacao": localizacao,
        "data_ocorrencia": data,
        "prioridade": r["prioridade"],
        "orgao_sugerido": {"principal": orgao, "apoio": [], "status": "inferido"},
        "alegacao_irregularidade": {"presente": False, "tipo": None, "descricao_neutra": None, "status_verificacao": None},
        "pendencias": pend,
        "requer_obra_adequacao": requer_obra_adequacao,
    }


def _analise(id_analise, visibilidade, texto_original, texto_mascarado, ocorrencias, tipos=(),
             alerta=None, resultado="classificado", motivo=None, recebido_em=RECEBIDO_EM):
    return {
        "schema_version": "1.2.0",
        "tipo_documento": "analise_relato",
        "id_analise": id_analise,
        "visibilidade": visibilidade,
        "relato": {
            "id_externo": None,
            "hash_texto": gm.calcular_hash(texto_original),
            "canal": "app",
            "recebido_em": recebido_em,
            "texto_original": texto_original if visibilidade == "interna" else None,
            "texto_mascarado": texto_mascarado,
        },
        "resultado_triagem": resultado,
        "motivo_triagem": motivo,
        "ocorrencias": ocorrencias,
        "pendencias": [],
        "dados_pessoais": {"detectados": bool(tipos), "tipos": list(tipos), "mascaramento_aplicado": bool(tipos),
                           "texto_relato_publicavel": visibilidade == "publica" and "dado_sensivel" not in tipos},
        "alerta_emergencia": alerta or {"acionar": False, "servicos": [], "motivo": None, "origem": []},
        "metadados": {
            "gerado_por": "ecorastro-analisador", "versao_skill": "0.3.0", "versao_taxonomia": "1.0.0",
            "versao_matriz_prioridade": cp.VERSAO_MATRIZ, "analisado_em": ANALISADO_EM,
        },
    }


TEXTO_BURACO = ("Tem um buraco enorme na Rua das Flores, perto do nº 120. Ontem um motoqueiro caiu ali "
                "e se machucou. Com a chuva o buraco tá ficando cada vez maior.")
TEXTO_FIO = ("Caiu um fio do poste na esquina da Av. Brasil com a Rua 7, tá soltando faísca no chão "
             "molhado e as crianças tão saindo da escola agora.")
TEXTO_POSTE_ORIGINAL = ("Sou a Maria Souza, tel (11) 98765-4321. Em frente à minha casa, Rua Ipê 45, "
                        "o poste está apagado há duas semanas.")
TEXTO_POSTE_INTERNO = ("Sou a [NOME], tel [TELEFONE]. Em frente à minha casa, Rua Ipê 45, "
                       "o poste está apagado há duas semanas.")
TEXTO_POSTE_PUBLICO = ("Sou a [NOME], tel [TELEFONE]. Em frente à minha casa, Rua Ipê [NUMERO], "
                       "o poste está apagado há duas semanas.")


def analise_buraco(visibilidade="interna"):
    oc = _ocorrencia(
        "Buraco de grande porte em via pública, com relato de queda de motociclista.",
        "problema_existente", "infraestrutura_urbana", "inf_pavimento", "org_obras_vias",
        _localizacao("Rua das Flores, perto do nº 120", "na Rua das Flores, perto do nº 120"),
        info("2026-11-06", "inferido", "Ontem", "'Ontem' em relação a recebido_em; refere-se à queda."),
        fatores_buraco(),
    )
    return _analise("3f2b6c1e-9a4d-4e2b-8c1a-0d5e7f9a1b2c", visibilidade, TEXTO_BURACO, TEXTO_BURACO, [oc])


def analise_fio():
    oc = _ocorrencia(
        "Fio da rede elétrica caído e soltando faíscas em esquina, em horário de saída escolar.",
        "problema_existente", "infraestrutura_urbana", "inf_rede_eletrica", "concessionaria_energia",
        _localizacao("esquina da Av. Brasil com a Rua 7", "esquina da Av. Brasil com a Rua 7"),
        ausente("O relato não diz quando o fio caiu."),
        fatores_fio(), risco_iminente=True,
    )
    alerta = {
        "acionar": True,
        "servicos": ["emergencia_concessionaria_energia", "bombeiros_193"],
        "motivo": "Fio energizado caído com faíscas, próximo a crianças.",
        "origem": ["oc-1"],
    }
    return _analise("b7d1e2f3-1111-4aaa-9bbb-222233334444", "interna", TEXTO_FIO, TEXTO_FIO, [oc], alerta=alerta)


def _ocorrencia_poste(publica):
    endereco = "Rua Ipê [NUMERO]" if publica else "Rua Ipê 45"
    fatores = {
        "risco_integridade_fisica": fator(1, "inferido", "o poste está apagado", "Trecho escuro aumenta o risco de queda."),
        "abrangencia": fator(1, "inferido", raciocinio="Um poste ilumina um trecho de rua."),
        "vulnerabilidade_afetados": fator_ausente(),
        "impacto_servico_essencial": fator_ausente(),
        "persistencia": fator(1, "relatado", "há duas semanas", "Duas semanas."),
        "risco_agravamento": fator(0, "inferido", raciocinio="Lâmpada apagada não piora sozinha."),
    }
    return _ocorrencia(
        "Poste de iluminação pública apagado.",
        "problema_existente", "infraestrutura_urbana", "inf_iluminacao_publica", "org_iluminacao_publica",
        _localizacao(endereco, endereco, "aproximada" if publica else "exata"),
        ausente("Duração informada, mas sem data de início."),
        fatores,
    )


def analise_poste(visibilidade="publica"):
    publica = visibilidade == "publica"
    tipos = ["nome_pessoa", "telefone"] + (["endereco_residencial"] if publica else [])
    return _analise(
        "c0ffee00-2222-4ccc-8ddd-555566667777", visibilidade, TEXTO_POSTE_ORIGINAL,
        TEXTO_POSTE_PUBLICO if publica else TEXTO_POSTE_INTERNO, [_ocorrencia_poste(publica)], tipos=tipos,
    )


def analise_fora_escopo():
    texto = "Meu vizinho me xingou ontem na frente de todo mundo."
    return _analise("d1d1d1d1-3333-4eee-8fff-888899990000", "interna", texto, texto, [],
                    resultado="fora_escopo", motivo="Conflito pessoal entre vizinhos, não é problema urbano coletivo.")


def lote(analises=None, visibilidade="interna"):
    analises = analises if analises is not None else [analise_buraco(), analise_fio(), analise_fora_escopo()]
    return {
        "schema_version": "1.2.0",
        "tipo_documento": "lote_analises",
        "id_lote": "a1b2c3d4-0000-4000-8000-000000000001",
        "visibilidade": visibilidade,
        "gerado_em": "2026-11-07T10:00:00-03:00",
        "total_relatos": len(analises),
        "analises": analises,
        "resumo": cp.resumo_lote(analises),
        "metadados": {
            "gerado_por": "ecorastro-analisador", "versao_skill": "0.3.0", "versao_taxonomia": "1.0.0",
            "versao_matriz_prioridade": cp.VERSAO_MATRIZ, "analisado_em": "2026-11-07T10:00:00-03:00",
        },
    }


TEXTO_SEMAFORO = "Semáforo apagado na Av. Paraná x Rua 3 desde manhã, quase vi uma batida."


def analise_semaforo(visibilidade="interna"):
    o = _ocorrencia(
        "Semáforo apagado no cruzamento da Av. Paraná com a Rua 3.", "problema_existente",
        "mobilidade_transito", "mob_semaforo", "org_transito_mobilidade",
        _localizacao("Av. Paraná x Rua 3", "Av. Paraná x Rua 3"),
        info(None, "ausente", "desde manhã", "Sem data de referência para converter."),
        fatores_semaforo(), falha_controle_trafego=True,
    )
    o["pendencias"] = sorted(set(o["pendencias"]) | {"data_ausente"})
    return _analise("e2e2e2e2-4444-4aaa-8bbb-999900001111", visibilidade, TEXTO_SEMAFORO, TEXTO_SEMAFORO, [o])

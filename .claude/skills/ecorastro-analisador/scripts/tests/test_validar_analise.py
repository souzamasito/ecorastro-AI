"""Testes de validar_analise.py e gerar_metadados.py."""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from fixtures import (  # noqa: F401
    ANALISADO_EM, DIR_SCRIPTS, TEXTO_POSTE_ORIGINAL, analise_buraco, analise_fio, analise_fora_escopo,
    analise_poste, analise_semaforo, cp, fator, fator_ausente, gm, info, lote,
)
import validar_analise as va  # noqa: E402

SCRIPT = DIR_SCRIPTS / "validar_analise.py"
VALIDADOR = va.carregar_validador()


def validar(doc, **kw):
    return va.validar_documento(doc, VALIDADOR, **kw)


def oc(doc, i=0):
    return doc["ocorrencias"][i]


class Base(unittest.TestCase):
    def assert_valido(self, res):
        self.assertEqual([a.como_dict() for a in res.erros], [])

    def assert_erro(self, res, categoria, trecho):
        achou = [a for a in res.erros if a.categoria == categoria and trecho in (a.mensagem + " " + a.caminho)]
        self.assertTrue(achou, f"esperado erro [{categoria}] contendo {trecho!r}; erros: "
                               f"{[(a.categoria, a.caminho, a.mensagem) for a in res.erros]}")

    def assert_aviso(self, res, categoria, trecho):
        achou = [a for a in res.avisos if a.categoria == categoria and trecho in (a.mensagem + " " + a.caminho)]
        self.assertTrue(achou, f"esperado aviso [{categoria}] contendo {trecho!r}; avisos: "
                               f"{[(a.categoria, a.mensagem) for a in res.avisos]}")


class DocumentosValidos(Base):
    def test_todos_os_exemplos_passam_sem_erros_nem_avisos(self):
        for nome, doc in [("buraco", analise_buraco()), ("fio", analise_fio()), ("poste_publica", analise_poste("publica")),
                          ("poste_interna", analise_poste("interna")), ("fora_escopo", analise_fora_escopo()), ("lote", lote())]:
            with self.subTest(nome):
                res = validar(doc)
                self.assert_valido(res)
                self.assertEqual([a.como_dict() for a in res.avisos], [])


class Schema(Base):
    def test_erro_de_schema_interrompe_as_demais_verificacoes(self):
        doc = analise_buraco()
        doc["campo_extra"] = 1
        res = validar(doc)
        self.assert_erro(res, "schema", "campo_extra")
        self.assertTrue(all(a.categoria == "schema" for a in res.erros))
        self.assert_aviso(res, "schema", "não executadas")

    def test_erro_aponta_caminho_dentro_do_ramo_certo(self):
        doc = analise_buraco()
        oc(doc)["classificacao"]["subcategoria"] = "amb_poluicao_ar"
        res = validar(doc)
        self.assert_erro(res, "schema", "ocorrencias[0].classificacao.subcategoria")

    def test_coordenada_inferida_e_rejeitada(self):
        doc = analise_buraco()
        oc(doc)["localizacao"]["latitude"] = info(-23.5, "inferido", raciocinio="geocodificado")
        self.assert_erro(validar(doc), "schema", "latitude")


class Evidencias(Base):
    def test_evidencia_inventada(self):
        doc = analise_buraco()
        oc(doc)["prioridade"]["fatores"]["risco_agravamento"]["evidencia"] = "o buraco já engoliu um carro"
        self.assert_erro(validar(doc), "evidencia", "não aparece literalmente")

    def test_evidencia_de_localizacao_inventada(self):
        doc = analise_buraco()
        oc(doc)["localizacao"]["bairro"] = info("Centro", "relatado", "bairro Centro")
        self.assert_erro(validar(doc), "evidencia", "bairro Centro")

    def test_diferenca_so_de_maiusculas_e_aviso(self):
        doc = analise_buraco()
        oc(doc)["prioridade"]["fatores"]["risco_agravamento"]["evidencia"] = "com a chuva o buraco tá ficando cada vez maior"
        res = validar(doc)
        self.assert_valido(res)
        self.assert_aviso(res, "evidencia", "maiúsculas")

    def test_espacos_extras_sao_tolerados(self):
        doc = analise_buraco()
        oc(doc)["prioridade"]["fatores"]["risco_integridade_fisica"]["evidencia"] = "um  motoqueiro\ncaiu ali e se machucou"
        self.assert_valido(validar(doc))

    def test_evidencia_vem_do_texto_mascarado_e_nao_do_original(self):
        doc = analise_poste("publica")
        oc(doc)["localizacao"]["endereco_texto"] = info("Rua Ipê [NUMERO]", "relatado", "Rua Ipê 45")
        self.assert_erro(validar(doc), "evidencia", "Rua Ipê 45")


class Pontuacao(Base):
    def test_pontuacao_errada(self):
        doc = analise_buraco()
        oc(doc)["prioridade"]["pontuacao"] = 50
        self.assert_erro(validar(doc), "pontuacao", "esperado 47, encontrado 50")

    def test_nivel_sem_regra_de_excecao(self):
        doc = analise_buraco()
        oc(doc)["prioridade"].update(nivel="media", regras_aplicadas=[])
        res = validar(doc)
        self.assert_erro(res, "pontuacao", "esperado 'alta', encontrado 'media'")
        self.assert_erro(res, "pontuacao", "não registradas: ex02_risco_fisico_grave_relatado")

    def test_regra_registrada_sem_condicao(self):
        doc = analise_buraco()
        oc(doc)["prioridade"]["regras_aplicadas"].append(cp.EX03)
        self.assert_erro(validar(doc), "pontuacao", "sem condição atendida: ex03")

    def test_ex01_sem_base_relatada(self):
        doc = analise_buraco()
        oc(doc)["prioridade"]["fatores"]["risco_integridade_fisica"] = fator(3, "inferido", raciocinio="Parece grave.")
        oc(doc)["prioridade"]["regras_aplicadas"].append(cp.EX01)
        self.assert_erro(validar(doc), "pontuacao", "ex01_risco_iminente exige")

    def test_necessidade_acima_de_alta(self):
        doc = analise_buraco()
        oc(doc)["natureza"] = "necessidade_infraestrutura"
        res = validar(doc)
        self.assert_erro(res, "pontuacao", "não registradas: ex04")

    def test_completude_errada(self):
        doc = analise_buraco()
        oc(doc)["prioridade"]["completude"] = 0.5
        self.assert_erro(validar(doc), "pontuacao", "completude")

    def test_pendencia_obrigatoria_faltando(self):
        doc = analise_buraco()
        oc(doc)["pendencias"] = []
        self.assert_erro(validar(doc), "pontuacao", "complementar_dados_prioridade")

    def test_justificativa_sem_pontuacao_e_nivel(self):
        doc = analise_buraco()
        oc(doc)["prioridade"]["justificativa"] = "O buraco é grande e alguém se machucou recentemente."
        res = validar(doc)
        self.assert_erro(res, "pontuacao", "não cita a pontuação")
        self.assert_erro(res, "pontuacao", "não cita o nível")
        self.assert_aviso(res, "pontuacao", "risco_integridade_fisica")

    def test_justificativa_com_termo_proibido(self):
        doc = analise_buraco()
        oc(doc)["prioridade"]["justificativa"] += " Avaliação de risco elevada."
        self.assert_aviso(validar(doc), "pontuacao", "prioridade de triagem")


class Consistencia(Base):
    def test_status_verificado_e_reservado(self):
        doc = analise_buraco()
        oc(doc)["prioridade"]["fatores"]["abrangencia"] = fator(1, "verificado")
        oc(doc)["prioridade"]["fatores"]["abrangencia"]["verificacao"] = {
            "fonte": "vistoria", "verificado_em": "2026-11-08T10:00:00-03:00", "responsavel": None}
        self.assert_erro(validar(doc), "consistencia", "reservado")
        self.assert_valido(validar(doc, permitir_verificado=True))

    def test_data_inferida_sem_data_de_referencia(self):
        doc = analise_buraco()
        doc["relato"]["recebido_em"] = None
        self.assert_erro(validar(doc), "consistencia", "sem data de referência")

    def test_data_inferida_sem_evidencia(self):
        doc = analise_buraco()
        oc(doc)["data_ocorrencia"]["evidencia"] = None
        self.assert_erro(validar(doc), "consistencia", "expressão relativa")

    # Expressões temporais sem data de referência (schema 1.1.0)
    def _data_ausente_com_expressao(self, raciocinio="Sem recebido_em, 'Ontem' não pode virar data."):
        doc = analise_buraco()
        doc["relato"]["recebido_em"] = None
        oc(doc)["data_ocorrencia"] = info(None, "ausente", "Ontem", raciocinio)
        return doc

    def test_data_ausente_guarda_expressao_temporal(self):
        res = validar(self._data_ausente_com_expressao())
        self.assert_valido(res)
        self.assertEqual(res.avisos, [])

    def test_data_ausente_com_expressao_que_nao_esta_no_texto(self):
        doc = self._data_ausente_com_expressao()
        oc(doc)["data_ocorrencia"]["evidencia"] = "anteontem"
        self.assert_erro(validar(doc), "evidencia", "data_ocorrencia.evidencia")

    def test_data_ausente_com_expressao_e_recebido_em_gera_aviso(self):
        doc = self._data_ausente_com_expressao()
        doc["relato"]["recebido_em"] = "2026-11-07T09:30:00-03:00"
        res = validar(doc)
        self.assert_valido(res)
        self.assert_aviso(res, "consistencia", "pode ser inferida")

    def test_data_ausente_com_expressao_sem_raciocinio_gera_aviso(self):
        res = validar(self._data_ausente_com_expressao(raciocinio=None))
        self.assert_valido(res)
        self.assert_aviso(res, "consistencia", "não foi convertida")

    def test_data_ausente_com_valor_e_rejeitada(self):
        doc = self._data_ausente_com_expressao()
        oc(doc)["data_ocorrencia"]["valor"] = "2026-11-06"
        self.assert_erro(validar(doc), "schema", "data_ocorrencia")

    def test_outros_campos_ausentes_continuam_sem_evidencia(self):
        doc = analise_buraco()
        oc(doc)["localizacao"]["bairro"] = info(None, "ausente", "Rua das Flores", "Não informado.")
        self.assert_erro(validar(doc), "schema", "bairro")
        doc = analise_buraco()
        oc(doc)["prioridade"]["fatores"]["persistencia"] = fator_ausente()
        oc(doc)["prioridade"]["fatores"]["persistencia"]["evidencia"] = "aumenta"
        self.assert_erro(validar(doc), "schema", "persistencia")

    def test_schema_version_anterior_e_rejeitada(self):
        doc = analise_buraco()
        doc["schema_version"] = "1.0.0"
        self.assert_erro(validar(doc), "schema", "schema_version")

    def test_data_posterior_ao_recebimento(self):
        doc = analise_buraco()
        oc(doc)["data_ocorrencia"]["valor"] = "2026-11-09"
        self.assert_erro(validar(doc), "consistencia", "posterior")

    def test_data_inexistente(self):
        doc = analise_buraco()
        oc(doc)["data_ocorrencia"]["valor"] = "2026-02-30"
        self.assert_erro(validar(doc), "consistencia", "inexistente")

    def test_analise_antes_do_recebimento(self):
        doc = analise_buraco()
        doc["metadados"]["analisado_em"] = "2026-11-07T09:00:00-03:00"
        self.assert_erro(validar(doc), "consistencia", "anterior ao recebimento")

    def test_precisao_incoerente_e_pendencia_de_local(self):
        doc = analise_buraco()
        oc(doc)["localizacao"]["precisao"] = "ausente"
        res = validar(doc)
        self.assert_erro(res, "consistencia", "há informação de local")
        self.assert_erro(res, "consistencia", "localizacao_ausente")

    def test_local_ausente_exige_pendencia(self):
        doc = analise_buraco()
        oc(doc)["localizacao"]["endereco_texto"] = info(None, "ausente", raciocinio="Não informado.")
        oc(doc)["localizacao"]["precisao"] = "ausente"
        self.assert_erro(validar(doc), "consistencia", "exige a pendência 'localizacao_ausente'")
        oc(doc)["pendencias"].append("localizacao_ausente")
        self.assert_valido(validar(doc))

    def test_latitude_sem_longitude(self):
        doc = analise_buraco()
        oc(doc)["localizacao"]["latitude"] = info(-23.5, "relatado", "Rua das Flores")
        self.assert_erro(validar(doc), "consistencia", "ambas presentes")

    def test_classificacao(self):
        doc = analise_buraco()
        c = oc(doc)["classificacao"]
        c["categorias_secundarias"] = ["infraestrutura_urbana"]
        c.update(ambigua=True, motivo_ambiguidade="Duas leituras.", regra_desempate="rd01_acessibilidade_explicita", confianca="baixa")
        res = validar(doc)
        for trecho in ("não pode ser secundária", "classificacao_ambigua", "revisao_humana_recomendada", "rd01"):
            self.assert_erro(res, "consistencia", trecho)

    def test_orgao_principal_repetido_no_apoio(self):
        doc = analise_buraco()
        oc(doc)["orgao_sugerido"]["apoio"] = ["org_obras_vias"]
        self.assert_erro(validar(doc), "consistencia", "apoio")

    def test_ids_de_ocorrencia_sequenciais(self):
        doc = analise_buraco()
        oc(doc)["id_ocorrencia"] = "oc-2"
        self.assert_erro(validar(doc), "consistencia", "sequencial")

    def test_alegacao(self):
        doc = analise_buraco()
        oc(doc)["alegacao_irregularidade"] = {"presente": True, "tipo": "obra_sem_licenca",
                                              "descricao_neutra": "A construtora fez a obra sem alvará.",
                                              "status_verificacao": "confirmada"}
        res = validar(doc)
        self.assert_erro(res, "consistencia", "verificar_alegacao")
        self.assert_erro(res, "consistencia", "pendente_verificacao")
        self.assert_aviso(res, "consistencia", "linguagem de alegação")

    def test_alegacao_correta(self):
        doc = analise_buraco()
        oc(doc)["alegacao_irregularidade"] = {"presente": True, "tipo": "obra_sem_licenca",
                                              "descricao_neutra": "O relato alega que a obra não tem licença.",
                                              "status_verificacao": "pendente_verificacao"}
        oc(doc)["pendencias"].append("verificar_alegacao")
        res = validar(doc)
        self.assert_valido(res)
        self.assertEqual(res.avisos, [])

    def test_ex01_exige_alerta(self):
        doc = analise_fio()
        doc["alerta_emergencia"] = {"acionar": False, "servicos": [], "motivo": None, "origem": []}
        self.assert_erro(validar(doc), "consistencia", "exige alerta_emergencia.acionar=true")

    def test_alerta_sem_ex01(self):
        doc = analise_buraco()
        doc["alerta_emergencia"] = {"acionar": True, "servicos": ["samu_192"], "motivo": "x", "origem": ["oc-1"]}
        self.assert_erro(validar(doc), "consistencia", "sem ex01")

    def test_alerta_com_origem_inexistente(self):
        doc = analise_fio()
        doc["alerta_emergencia"]["origem"] = ["oc-1", "oc-3"]
        self.assert_erro(validar(doc), "consistencia", "oc-3 não existe")


class Privacidade(Base):
    def test_cpf_telefone_email_placa_fora_de_marcador(self):
        casos = {
            "CPF": "Relator informou CPF 123.456.789-09.",
            "telefone": "Contato (11) 98765-4321 informado.",
            "e-mail": "Responder para maria@exemplo.com.br.",
            "placa": "O carro de placa ABC1D23 está abandonado.",
        }
        for nome, texto in casos.items():
            with self.subTest(nome):
                doc = analise_buraco()
                oc(doc)["descricao_neutra"] = texto
                self.assert_erro(validar(doc), "privacidade", "fora de marcador")

    def test_dado_pessoal_na_justificativa_tambem_e_detectado(self):
        doc = analise_buraco()
        oc(doc)["prioridade"]["justificativa"] += " Ligar para 98765-4321."
        self.assert_erro(validar(doc), "privacidade", "justificativa")

    def test_texto_original_nao_e_varrido_na_interna(self):
        self.assert_valido(validar(analise_poste("interna")))

    def test_marcador_sem_tipo_declarado(self):
        doc = analise_poste("publica")
        doc["dados_pessoais"]["tipos"].remove("telefone")
        self.assert_erro(validar(doc), "privacidade", "'telefone', mas o tipo não foi declarado")

    def test_tipo_declarado_sem_marcador(self):
        doc = analise_buraco()
        doc["dados_pessoais"] = {"detectados": True, "tipos": ["cpf"], "mascaramento_aplicado": True,
                                 "texto_relato_publicavel": False}
        self.assert_erro(validar(doc), "privacidade", "sem marcador")

    def test_numero_de_residencia_nao_se_mascara_na_interna(self):
        doc = analise_poste("publica")
        doc["visibilidade"] = "interna"
        doc["relato"]["texto_original"] = TEXTO_POSTE_ORIGINAL
        doc["dados_pessoais"]["texto_relato_publicavel"] = False
        self.assert_aviso(validar(doc), "privacidade", "só é mascarado na versão pública")

    def test_hash_divergente(self):
        doc = analise_buraco()
        doc["relato"]["texto_original"] += " editado"
        self.assert_erro(validar(doc), "privacidade", "hash_texto")

    def test_publica_com_texto_original_e_rejeitada_pelo_schema(self):
        doc = analise_poste("publica")
        doc["relato"]["texto_original"] = TEXTO_POSTE_ORIGINAL
        self.assert_erro(validar(doc), "schema", "texto_original")

    def test_publica_com_id_externo(self):
        doc = analise_poste("publica")
        doc["relato"]["id_externo"] = "PROT-2026-0001"
        self.assert_aviso(validar(doc), "privacidade", "id_externo")

    def test_publica_com_residencia_mascarada_nao_pode_ser_exata(self):
        doc = analise_poste("publica")
        oc(doc)["localizacao"]["precisao"] = "exata"
        self.assert_erro(validar(doc), "privacidade", "aproximada")

    def test_lote_com_visibilidades_misturadas(self):
        doc = lote([analise_buraco(), analise_poste("publica")])
        self.assert_erro(validar(doc), "privacidade", "difere da visibilidade do lote")


class DadoSensivel(Base):
    """categorias.md 11.1: condição de pessoa identificável só aparece na versão interna."""

    def _com_descricao(self, vis, descricao):
        doc = analise_buraco(vis)
        oc(doc)["descricao_neutra"] = descricao
        return validar(doc)

    def _avisos_sensiveis(self, res):
        return [a for a in res.avisos if "dado sensível" in a.mensagem]

    def test_condicao_individual_na_publica_gera_aviso(self):
        for termo in ("Relator cadeirante não consegue passar.", "A moradora é cega.", "Vizinho tem Alzheimer."):
            res = self._com_descricao("publica", termo)
            self.assert_valido(res)
            self.assertTrue(self._avisos_sensiveis(res), termo)

    def test_mencao_coletiva_e_marcador_nao_geram_aviso(self):
        for termo in ("Cadeirantes e idosos não conseguem passar.", "Relator [DADO_SENSIVEL] não consegue passar.",
                      "Buraco na Rua dos Imigrantes."):
            self.assertEqual(self._avisos_sensiveis(self._com_descricao("publica", termo)), [], termo)

    def test_versao_interna_pode_manter_a_condicao(self):
        self.assertEqual(self._avisos_sensiveis(self._com_descricao("interna", "Relator cadeirante não consegue passar.")), [])



class Contrato120(Base):
    """Campos novos do schema 1.2.0 e compatibilidade com versões anteriores."""

    def test_schema_version_anterior_e_rejeitado(self):
        for versao in ("1.0.0", "1.1.0"):
            doc = analise_buraco()
            doc["schema_version"] = versao
            self.assert_erro(validar(doc), "schema", "1.2.0")

    def test_schemas_anteriores_preservados(self):
        hist = DIR_SCRIPTS.parent / "assets" / "historico"
        for versao in ("1.0.0", "1.1.0"):
            s = json.loads((hist / f"analise.schema-{versao}.json").read_text(encoding="utf-8"))
            self.assertEqual(s["$id"], f"urn:ecorastro:schema:analise:{versao}")

    def test_requer_obra_adequacao(self):
        doc = analise_buraco()
        del oc(doc)["requer_obra_adequacao"]
        self.assert_erro(validar(doc), "schema", "requer_obra_adequacao")
        doc = analise_buraco()
        oc(doc)["requer_obra_adequacao"] = True
        self.assert_valido(validar(doc))
        doc = analise_buraco()
        oc(doc)["natureza"] = "necessidade_infraestrutura"
        oc(doc)["requer_obra_adequacao"] = True
        self.assert_erro(validar(doc), "schema", "requer_obra_adequacao")

    def test_texto_relato_publicavel(self):
        doc = analise_buraco("interna")
        doc["dados_pessoais"]["texto_relato_publicavel"] = True
        self.assert_erro(validar(doc), "schema", "texto_relato_publicavel")
        self.assert_valido(validar(analise_buraco("publica")))

    def test_semaforo_com_ex06_e_valido(self):
        self.assert_valido(validar(analise_semaforo()))

    def test_ex06_sem_condicao_e_ex07_nao_registrada(self):
        doc = analise_semaforo()
        oc(doc)["classificacao"]["subcategoria"] = "mob_sinalizacao_viaria"
        self.assert_erro(validar(doc), "pontuacao", cp.EX06)
        doc = analise_semaforo()
        fatores = oc(doc)["prioridade"]["fatores"]
        fatores["vulnerabilidade_afetados"] = fator(3, "relatado", "quase vi uma batida", "Teste: grupo vulnerável relatado.")
        fatores["impacto_servico_essencial"] = fator(2, "relatado", "Semáforo apagado", "Teste: serviço impedido relatado.")
        res = validar(doc)
        self.assert_erro(res, "pontuacao", "não registradas: ")
        self.assertTrue(any(cp.EX07 in a.mensagem for a in res.erros))


class Reidentificacao(Base):
    """categorias.md 11.1, versão pública: um marcador por pessoa e menção coletiva com pessoa identificável."""

    TEXTO = "Tem um buraco enorme na Rua das Flores. Mora ali o [NOME], que é [DADO_SENSIVEL]. Os cadeirantes reclamam."

    def _publica(self, texto=TEXTO, tipos=("nome_pessoa", "dado_sensivel")):
        doc = analise_buraco("publica")
        doc["relato"]["texto_mascarado"] = doc["relato"]["texto_mascarado"] + " " + texto
        doc["dados_pessoais"] = {"detectados": True, "tipos": list(tipos), "mascaramento_aplicado": True,
                                 "texto_relato_publicavel": False}
        return doc

    def _avisos_coletivos(self, res):
        return [a for a in res.avisos if "menção coletiva" in a.mensagem]

    def test_dado_sensivel_exige_texto_nao_publicavel(self):
        doc = self._publica()
        doc["dados_pessoais"]["texto_relato_publicavel"] = True
        self.assert_erro(validar(doc), "schema", "texto_relato_publicavel")

    def test_dois_marcadores_seguidos_sao_erro(self):
        for ligacao in (" e ", ", ", " ou ", "/"):
            with self.subTest(ligacao=ligacao):
                doc = self._publica(f"Mora ali o [NOME], que é [DADO_SENSIVEL]{ligacao}[DADO_SENSIVEL].")
                self.assert_erro(validar(doc), "privacidade", "um único marcador por pessoa")

    def test_marcadores_de_pessoas_diferentes_nao_sao_erro(self):
        doc = self._publica("O [NOME] é [DADO_SENSIVEL] e a vizinha [NOME] também é [DADO_SENSIVEL].")
        self.assert_valido(validar(doc))

    def test_mencao_coletiva_com_pessoa_identificavel_gera_aviso(self):
        res = validar(self._publica())
        self.assert_valido(res)
        self.assertTrue(self._avisos_coletivos(res))

    def test_mencao_coletiva_sem_dado_sensivel_nao_gera_aviso(self):
        res = validar(self._publica("Os cadeirantes reclamam.", tipos=()))
        self.assertEqual(self._avisos_coletivos(res), [])

    def test_interna_nao_recebe_os_avisos_da_publica(self):
        doc = analise_buraco("interna")
        doc["relato"]["texto_mascarado"] += " Mora ali o [NOME], que é [DADO_SENSIVEL] e [DADO_SENSIVEL]. Os cadeirantes reclamam."
        doc["dados_pessoais"] = {"detectados": True, "tipos": ["nome_pessoa", "dado_sensivel"], "mascaramento_aplicado": True,
                                 "texto_relato_publicavel": False}
        res = validar(doc)
        self.assert_valido(res)
        self.assertEqual(self._avisos_coletivos(res), [])

class Lote(Base):
    def test_total_e_resumo_errados(self):
        doc = lote()
        doc["total_relatos"] = 5
        doc["resumo"]["por_nivel"] = {"alta": 2}
        doc["resumo"]["total_ocorrencias"] = 7
        res = validar(doc)
        self.assert_erro(res, "consistencia", "há 3 análises")
        self.assert_erro(res, "consistencia", "resumo.por_nivel")
        self.assert_erro(res, "consistencia", "resumo.total_ocorrencias")

    def test_resumo_aceita_contagens_zeradas(self):
        doc = lote()
        doc["resumo"]["por_nivel"]["baixa"] = 0
        self.assert_valido(validar(doc))

    def test_id_repetido_e_erro_dentro_de_analise(self):
        a, b = analise_buraco(), analise_buraco()
        oc(b)["prioridade"]["pontuacao"] = 1
        res = validar(lote([a, b]))
        self.assert_erro(res, "consistencia", "id_analise repetido")
        self.assert_erro(res, "pontuacao", "analises[1].ocorrencias[0].prioridade.pontuacao")


class Arquivo(Base):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def gravar(self, doc, nome=None, modo=0o600):
        nome = nome or gm.nome_arquivo("analise", doc["id_analise"], doc["metadados"]["analisado_em"], doc["visibilidade"])
        caminho = self.tmp / nome
        caminho.write_text(json.dumps(doc), encoding="utf-8")
        os.chmod(caminho, modo)
        return caminho

    def test_nome_na_convencao(self):
        doc = analise_buraco()
        caminho = self.gravar(doc)
        self.assertEqual(caminho.name, "analise_20261107-093112_3f2b6c1e_interna.json")
        res = validar(doc, caminho=caminho)
        self.assert_valido(res)
        self.assertEqual(res.avisos, [])

    def test_nome_com_visibilidade_trocada(self):
        doc = analise_buraco()
        caminho = self.gravar(doc, "analise_20261107-093112_3f2b6c1e_publica.json")
        self.assert_erro(validar(doc, caminho=caminho), "arquivo", "nome indica 'publica'")

    def test_nome_com_id_ou_data_divergente(self):
        doc = analise_buraco()
        res = validar(doc, caminho=self.gravar(doc, "analise_20261107-093112_00000000_interna.json"))
        self.assert_erro(res, "arquivo", "8 caracteres")
        res = validar(doc, caminho=self.gravar(doc, "analise_20261108-093112_3f2b6c1e_interna.json"))
        self.assert_erro(res, "arquivo", "data e hora")

    def test_nome_fora_da_convencao(self):
        doc = analise_buraco()
        self.assert_aviso(validar(doc, caminho=self.gravar(doc, "buraco.json")), "arquivo", "convenção")

    def test_arquivo_interno_com_permissao_aberta(self):
        doc = analise_buraco()
        self.assert_aviso(validar(doc, caminho=self.gravar(doc, modo=0o644)), "arquivo", "chmod 600")

    @unittest.skipUnless(shutil.which("git"), "git não instalado")
    def test_arquivo_interno_precisa_estar_ignorado_pelo_git(self):
        subprocess.run(["git", "init", "-q", str(self.tmp)], check=True)
        doc = analise_buraco()
        caminho = self.gravar(doc)
        self.assert_erro(validar(doc, caminho=caminho), "arquivo", ".gitignore")
        (self.tmp / ".gitignore").write_text("saidas/**/*_interna.*\n*_interna.*\n", encoding="utf-8")
        self.assert_valido(validar(doc, caminho=caminho))


class LinhaDeComando(Base):
    def rodar(self, *args):
        return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True, timeout=60)

    def test_codigos_de_saida_e_formato_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            bom = Path(tmp) / "bom.json"
            ruim = Path(tmp) / "ruim.json"
            bom.write_text(json.dumps(analise_buraco()), encoding="utf-8")
            doc = analise_buraco()
            oc(doc)["prioridade"]["pontuacao"] = 3
            ruim.write_text(json.dumps(doc), encoding="utf-8")
            os.chmod(bom, 0o600)
            os.chmod(ruim, 0o600)

            r = self.rodar(str(bom))
            self.assertEqual(r.returncode, 0, r.stdout)
            self.assertIn("VÁLIDO", r.stdout)

            r = self.rodar(str(bom), "--estrito")  # aviso de nome fora da convenção
            self.assertEqual(r.returncode, 1)

            r = self.rodar(str(ruim), "--json")
            self.assertEqual(r.returncode, 1)
            saida = json.loads(r.stdout)
            self.assertFalse(saida["valido"])
            self.assertEqual(saida["erros"][0]["categoria"], "pontuacao")

            self.assertEqual(self.rodar(str(Path(tmp) / "nao_existe.json")).returncode, 2)


class GerarMetadados(unittest.TestCase):
    def test_hash_ignora_espacos_e_forma_unicode(self):
        a = gm.calcular_hash("Buraco  na\nRua Ipê ")
        b = gm.calcular_hash("Buraco na Rua Ipê")  # "e" + circunflexo combinante (forma NFD de "ê")
        self.assertEqual(a, b)
        self.assertNotEqual(a, gm.calcular_hash("Buraco na Rua Ipê!"))
        self.assertRegex(a, r"^[0-9a-f]{64}$")

    def test_nomes_seguem_a_convencao(self):
        nomes = gm.nomes_saida("analise", "3f2b6c1e-9a4d-4e2b-8c1a-0d5e7f9a1b2c", ANALISADO_EM)
        self.assertEqual(nomes["json_interna"], "saidas/json/analise_20261107-093112_3f2b6c1e_interna.json")
        self.assertEqual(nomes["relatorio_publica"], "saidas/relatorios/relatorio_20261107-093112_3f2b6c1e_publica.md")
        for caminho in nomes.values():
            self.assertRegex(Path(caminho).name, gm.PADRAO_NOME_ARQUIVO)

    def test_cli_analise(self):
        r = subprocess.run([sys.executable, str(DIR_SCRIPTS / "gerar_metadados.py"), "analise"],
                           input="Buraco na Rua Ipê", capture_output=True, text=True, timeout=30)
        self.assertEqual(r.returncode, 0, r.stderr)
        saida = json.loads(r.stdout)
        self.assertRegex(saida["id_analise"], r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")
        self.assertEqual(saida["hash_texto"], gm.calcular_hash("Buraco na Rua Ipê"))
        self.assertRegex(saida["analisado_em"], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{2}:\d{2}$")
        self.assertIn(saida["id_analise"][:8], saida["arquivos"]["json_interna"])

    def test_cli_rejeita_texto_vazio(self):
        r = subprocess.run([sys.executable, str(DIR_SCRIPTS / "gerar_metadados.py"), "analise"],
                           input="   \n", capture_output=True, text=True, timeout=30)
        self.assertEqual(r.returncode, 2)

    def _lote(self, conteudo, nome="relatos.csv", *extra):
        with tempfile.TemporaryDirectory() as tmp:
            caminho = Path(tmp) / nome
            caminho.write_text(conteudo, encoding="utf-8")
            r = subprocess.run([sys.executable, str(DIR_SCRIPTS / "gerar_metadados.py"), "lote", "--arquivo", str(caminho), *extra],
                               capture_output=True, text=True, timeout=30)
        return r

    def test_lote_csv_gera_metadados_de_cada_relato(self):
        csv_ = ("Protocolo;Data;Canal;Relato\n"
                "A-1;2026-11-05T08:10:00-03:00;WhatsApp;Buraco na Rua Ipê\n"
                "A-2;2026-11-05;site;Poste apagado\n"
                "A-3;;;   \n"
                "A-4;2026-11-06T10:00:00-03:00;pombo-correio;Lixo na praça\n")
        r = self._lote(csv_)
        self.assertEqual(r.returncode, 0, r.stderr)
        d = json.loads(r.stdout)
        self.assertEqual((d["total_linhas"], d["total_relatos"]), (4, 3))
        self.assertEqual(d["linhas_ignoradas"], [{"linha": 3, "id_externo": "A-3", "motivo": "texto vazio"}])
        r1, r2, r4 = d["relatos"]
        self.assertEqual((r1["id_externo"], r1["canal"], r1["recebido_em"]), ("A-1", "whatsapp", "2026-11-05T08:10:00-03:00"))
        self.assertEqual(r1["hash_texto"], gm.calcular_hash("Buraco na Rua Ipê"))
        self.assertEqual((r2["canal"], r2["recebido_em"]), ("web", None))  # data sem hora não é completada
        self.assertEqual(r4["canal"], "outro")
        self.assertEqual(len(d["avisos"]), 2)
        self.assertEqual(len({x["id_analise"] for x in d["relatos"]} | {d["id_lote"]}), 4)
        self.assertRegex(Path(d["arquivos"]["json_interna"]).name, gm.PADRAO_NOME_ARQUIVO)

    def test_lote_json_e_coluna_forcada(self):
        r = self._lote(json.dumps([{"obs": "Calçada quebrada", "id": 7}]), "relatos.json", "--coluna-texto", "obs")
        self.assertEqual(r.returncode, 0, r.stderr)
        d = json.loads(r.stdout)
        self.assertEqual((d["relatos"][0]["id_externo"], d["relatos"][0]["canal"]), ("7", "nao_informado"))

    def test_lote_sem_coluna_de_texto(self):
        r = self._lote("protocolo,canal\nA-1,app\n")
        self.assertEqual(r.returncode, 2)
        self.assertIn("coluna de texto", r.stderr)


if __name__ == "__main__":
    unittest.main()

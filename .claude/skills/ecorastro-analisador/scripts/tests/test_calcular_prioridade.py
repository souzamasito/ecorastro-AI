"""Testes de calcular_prioridade.py contra as regras de references/priorizacao.md."""
from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from fixtures import (  # noqa: F401  (fixtures também ajusta o sys.path)
    DIR_SCRIPTS, analise_buraco, analise_semaforo, cp, fator, fator_ausente, fatores_buraco, fatores_ciclovia,
    fatores_escola, fatores_esgoto, fatores_fio, fatores_poste, fatores_semaforo, lote,
)

SCRIPT = DIR_SCRIPTS / "calcular_prioridade.py"


def todos(nota, status="inferido"):
    return {c: (fator_ausente() if nota is None else fator(nota, status, "trecho" if status == "relatado" else None))
            for c in cp.PESOS}


class ExemplosDaMatriz(unittest.TestCase):
    """Os quatro exemplos calculados da seção 9 de priorizacao.md."""

    def verificar(self, fatores, natureza, risco_iminente, esperado, pendencias):
        r = cp.calcular(fatores, natureza, risco_iminente)
        p = r["prioridade"]
        for campo, valor in esperado.items():
            self.assertEqual(p[campo], valor, campo)
        self.assertEqual(r["pendencias_obrigatorias"], pendencias)
        return p

    def test_9_1_buraco_com_acidente(self):
        self.verificar(fatores_buraco(), "problema_existente", False, {
            "pontuacao": 47, "pontuacao_teto": 77, "completude": 0.67, "nivel_base": "media",
            "nivel": "alta", "nivel_teto": "critica", "pontuacao_provisoria": False,
            "regras_aplicadas": [cp.EX02],
        }, [cp.PEND_COMPLEMENTAR])

    def test_9_2_fio_caido_risco_iminente(self):
        self.verificar(fatores_fio(), "problema_existente", True, {
            "pontuacao": 68, "pontuacao_teto": 93, "completude": 0.67, "nivel_base": "alta",
            "nivel": "critica", "nivel_teto": "critica", "pontuacao_provisoria": False,
            "regras_aplicadas": [cp.EX01, cp.EX02, cp.EX03],
        }, [cp.PEND_REVISAO])

    def test_9_3_ciclovia_necessidade(self):
        self.verificar(fatores_ciclovia(), "necessidade_infraestrutura", False, {
            "pontuacao": 38, "pontuacao_teto": 63, "completude": 0.67, "nivel_base": "media",
            "nivel": "media", "nivel_teto": "alta", "pontuacao_provisoria": False,
            "regras_aplicadas": [cp.EX04],
        }, [cp.PEND_COMPLEMENTAR])

    def test_9_4_poste_provisorio(self):
        self.verificar(fatores_poste(), "problema_existente", False, {
            "pontuacao": 17, "pontuacao_teto": 57, "completude": 0.5, "nivel_base": "baixa",
            "nivel": "baixa", "nivel_teto": "alta", "pontuacao_provisoria": True,
            "regras_aplicadas": [cp.EX05],
        }, [cp.PEND_COMPLEMENTAR, cp.PEND_REVISAO])


class Formula(unittest.TestCase):
    def test_extremos(self):
        p = cp.calcular(todos(3), "problema_existente")["prioridade"]
        self.assertEqual((p["pontuacao"], p["pontuacao_teto"], p["nivel"]), (100, 100, "critica"))
        p = cp.calcular(todos(0), "problema_existente")["prioridade"]
        self.assertEqual((p["pontuacao"], p["pontuacao_teto"], p["nivel"], p["completude"]), (0, 0, "baixa", 1.0))

    def test_tudo_ausente(self):
        r = cp.calcular(todos(None), "problema_existente")
        p = r["prioridade"]
        self.assertEqual((p["pontuacao"], p["pontuacao_teto"], p["completude"]), (0, 100, 0.0))
        self.assertTrue(p["pontuacao_provisoria"])
        self.assertEqual(p["nivel_teto"], "critica")
        self.assertIn(cp.PEND_COMPLEMENTAR, r["pendencias_obrigatorias"])

    def test_ausente_nao_e_zero(self):
        com_zero = todos(0)
        com_ausente = todos(0)
        com_ausente["abrangencia"] = fator_ausente()
        z = cp.calcular(com_zero, "problema_existente")["prioridade"]
        a = cp.calcular(com_ausente, "problema_existente")["prioridade"]
        self.assertEqual(z["pontuacao"], a["pontuacao"])
        self.assertEqual(z["pontuacao_teto"], 0)
        self.assertEqual(a["pontuacao_teto"], 20)
        self.assertEqual((z["completude"], a["completude"]), (1.0, 0.83))

    def test_faixas_nos_limites(self):
        for pontos, nivel in [(0, "baixa"), (29, "baixa"), (30, "media"), (54, "media"),
                              (55, "alta"), (74, "alta"), (75, "critica"), (100, "critica")]:
            self.assertEqual(cp.faixa(pontos), nivel, pontos)

    def test_arredondamento_sem_ponto_flutuante(self):
        self.assertEqual(cp.arredondar_terco(140), 47)  # 46,67
        self.assertEqual(cp.arredondar_terco(115), 38)  # 38,33
        self.assertEqual(cp.arredondar_terco(300), 100)
        self.assertEqual(cp.arredondar_terco(1), 0)     # 0,33
        self.assertEqual(cp.arredondar_terco(2), 1)     # 0,67

    def test_ex05_no_limite_de_quatro_fatores(self):
        f = todos(1)
        f["vulnerabilidade_afetados"] = fator_ausente()
        f["persistencia"] = fator_ausente()
        self.assertNotIn(cp.EX05, cp.calcular(f, "problema_existente")["prioridade"]["regras_aplicadas"])
        f["risco_agravamento"] = fator_ausente()
        self.assertIn(cp.EX05, cp.calcular(f, "problema_existente")["prioridade"]["regras_aplicadas"])

    def test_deterministico(self):
        a = cp.calcular(fatores_buraco(), "problema_existente")
        b = cp.calcular(copy.deepcopy(fatores_buraco()), "problema_existente")
        self.assertEqual(a, b)

    def test_nao_altera_a_entrada(self):
        f = fatores_buraco()
        original = copy.deepcopy(f)
        cp.calcular(f, "problema_existente")
        self.assertEqual(f, original)


class RegrasDeExcecao(unittest.TestCase):
    def test_ex02_exige_relato_e_nao_inferencia(self):
        f = fatores_buraco()
        f["risco_integridade_fisica"] = fator(3, "inferido", raciocinio="Dedução da análise.")
        p = cp.calcular(f, "problema_existente")["prioridade"]
        self.assertNotIn(cp.EX02, p["regras_aplicadas"])
        self.assertEqual(p["nivel"], "media")

    def test_ex03_ignora_fator_ausente(self):
        f = todos(None)
        f["risco_integridade_fisica"] = fator(2, "inferido")
        self.assertNotIn(cp.EX03, cp.calcular(f, "problema_existente")["prioridade"]["regras_aplicadas"])
        f["vulnerabilidade_afetados"] = fator(2, "inferido")
        p = cp.calcular(f, "problema_existente")["prioridade"]
        self.assertIn(cp.EX03, p["regras_aplicadas"])
        self.assertEqual(p["nivel"], "alta")

    def test_ex04_limita_necessidade_a_alta(self):
        p = cp.calcular(todos(3), "necessidade_infraestrutura")["prioridade"]
        self.assertEqual((p["nivel_base"], p["nivel"], p["nivel_teto"]), ("critica", "alta", "alta"))
        self.assertIn(cp.EX04, p["regras_aplicadas"])
        self.assertIn("ex04_teto_necessidade_infraestrutura alterou de crítica para alta", p["justificativa"])

    def test_ex02_e_ex04_juntas_resultam_em_alta(self):
        f = todos(0)
        f["risco_integridade_fisica"] = fator(3, "relatado", "já atropelaram duas pessoas")
        p = cp.calcular(f, "necessidade_infraestrutura")["prioridade"]
        self.assertEqual((p["pontuacao"], p["nivel_base"], p["nivel"]), (30, "media", "alta"))
        self.assertEqual(p["regras_aplicadas"], [cp.EX02, cp.EX04])

    def test_ex01_prevalece_sobre_ex04(self):
        f = todos(0)
        f["risco_integridade_fisica"] = fator(3, "relatado", "a encosta está cedendo agora")
        p = cp.calcular(f, "necessidade_infraestrutura", risco_iminente=True)["prioridade"]
        self.assertEqual(p["nivel"], "critica")
        self.assertNotIn(cp.EX04, p["regras_aplicadas"])

    def test_ex01_sem_base_relatada_e_rejeitado(self):
        f = fatores_buraco()
        f["risco_integridade_fisica"] = fator(3, "inferido", raciocinio="Parece perigoso.")
        with self.assertRaises(cp.ErroEntrada) as ctx:
            cp.calcular(f, "problema_existente", risco_iminente=True)
        self.assertIn("ex01", str(ctx.exception))
        f["risco_integridade_fisica"] = fator(2, "relatado", "risco")
        with self.assertRaises(cp.ErroEntrada):
            cp.calcular(f, "problema_existente", risco_iminente=True)

    def test_status_verificado_conta_como_fato(self):
        f = fatores_buraco()
        f["risco_integridade_fisica"] = fator(3, "verificado")
        f["risco_integridade_fisica"]["verificacao"] = {"fonte": "vistoria", "verificado_em": "2026-11-08T10:00:00-03:00", "responsavel": None}
        self.assertIn(cp.EX02, cp.calcular(f, "problema_existente")["prioridade"]["regras_aplicadas"])


class ValidacaoDaEntrada(unittest.TestCase):
    def assert_rejeita(self, fatores, trecho, natureza="problema_existente"):
        with self.assertRaises(cp.ErroEntrada) as ctx:
            cp.calcular(fatores, natureza)
        self.assertIn(trecho, str(ctx.exception))

    def test_fator_faltando(self):
        f = fatores_buraco()
        del f["persistencia"]
        self.assert_rejeita(f, "persistencia")

    def test_fator_desconhecido(self):
        f = fatores_buraco()
        f["urgencia"] = fator(1, "inferido")
        self.assert_rejeita(f, "desconhecidos")

    def test_nota_fora_da_escala_ou_booleana(self):
        for nota in (4, -1, 1.5, True, "2"):
            f = fatores_buraco()
            f["abrangencia"]["nota"] = nota
            self.assert_rejeita(f, "abrangencia")

    def test_ausente_com_nota_zero(self):
        f = fatores_buraco()
        f["abrangencia"] = fator(0, "ausente")
        self.assert_rejeita(f, "ausente não é zero")

    def test_nota_nula_sem_status_ausente(self):
        f = fatores_buraco()
        f["abrangencia"] = fator(None, "inferido")
        self.assert_rejeita(f, "abrangencia")

    def test_relatado_sem_evidencia(self):
        f = fatores_buraco()
        f["abrangencia"] = fator(2, "relatado", None)
        self.assert_rejeita(f, "evidência literal")

    def test_sem_raciocinio(self):
        f = fatores_buraco()
        f["abrangencia"]["raciocinio"] = "  "
        self.assert_rejeita(f, "raciocinio")

    def test_verificado_sem_bloco(self):
        f = fatores_buraco()
        f["abrangencia"] = fator(2, "verificado")
        self.assert_rejeita(f, "verificacao")

    def test_natureza_invalida(self):
        self.assert_rejeita(fatores_buraco(), "natureza", natureza="reclamacao")


class Justificativa(unittest.TestCase):
    def test_conteudo_rastreavel(self):
        j = cp.calcular(fatores_buraco(), "problema_existente")["prioridade"]["justificativa"]
        self.assertTrue(j.startswith("Prioridade de triagem alta (47 pts; faixa base média)."))
        self.assertIn('risco_integridade_fisica 3 (relatado: "um motoqueiro caiu ali e se machucou")', j)
        self.assertIn("Não informados: vulnerabilidade_afetados, impacto_servico_essencial.", j)
        self.assertIn("ex02_risco_fisico_grave_relatado alterou de média para alta.", j)
        self.assertIn("Pode chegar a crítica (77 pts)", j)
        self.assertNotIn("risco_agravamento 0", j)

    def test_provisoria_e_regra_sem_efeito(self):
        j = cp.calcular(fatores_poste(), "problema_existente")["prioridade"]["justificativa"]
        self.assertIn("17 pts, provisória", j)
        self.assertIn("ex05_informacao_insuficiente", j)
        j = cp.calcular(fatores_ciclovia(), "necessidade_infraestrutura")["prioridade"]["justificativa"]
        self.assertIn("Regras consideradas sem alterar o nível: ex04_teto_necessidade_infraestrutura.", j)

    def test_nao_usa_termo_de_risco_validado(self):
        j = cp.calcular(fatores_fio(), "problema_existente", True)["prioridade"]["justificativa"].casefold()
        self.assertNotIn("avaliação de risco", j)
        self.assertNotIn("nível de risco", j)


class LinhaDeComando(unittest.TestCase):
    def rodar(self, *args, entrada=None):
        return subprocess.run([sys.executable, str(SCRIPT), *args], input=entrada,
                              capture_output=True, text=True, timeout=30)

    def test_modo_simples_pela_entrada_padrao(self):
        entrada = json.dumps({"natureza": "problema_existente", "risco_iminente": False, "fatores": fatores_buraco()})
        r = self.rodar("-", entrada=entrada)
        self.assertEqual(r.returncode, 0, r.stderr)
        saida = json.loads(r.stdout)
        self.assertEqual(saida["prioridade"]["pontuacao"], 47)
        self.assertEqual(saida["pendencias_obrigatorias"], [cp.PEND_COMPLEMENTAR])

    def test_modo_simples_com_erro(self):
        entrada = json.dumps({"natureza": "problema_existente", "fatores": {}})
        r = self.rodar("-", entrada=entrada)
        self.assertEqual(r.returncode, 1)
        self.assertIn("fatores ausentes", r.stderr)

    def test_json_invalido(self):
        self.assertEqual(self.rodar("-", entrada="{nao é json").returncode, 2)

    def test_atualizar_corrige_aritmetica_e_pendencias(self):
        doc = analise_buraco()
        p = doc["ocorrencias"][0]["prioridade"]
        p.update(pontuacao=99, nivel="baixa", regras_aplicadas=[], justificativa="placeholder")
        doc["ocorrencias"][0]["pendencias"] = ["localizacao_imprecisa"]
        with tempfile.TemporaryDirectory() as tmp:
            caminho = Path(tmp) / "a.json"
            caminho.write_text(json.dumps(doc), encoding="utf-8")
            r = self.rodar("--atualizar", str(caminho))
            self.assertEqual(r.returncode, 0, r.stderr)
            novo = json.loads(caminho.read_text(encoding="utf-8"))
        oc = novo["ocorrencias"][0]
        self.assertEqual((oc["prioridade"]["pontuacao"], oc["prioridade"]["nivel"]), (47, "alta"))
        self.assertEqual(oc["pendencias"], ["localizacao_imprecisa", cp.PEND_COMPLEMENTAR])
        self.assertEqual(novo, analise_buraco() | {"ocorrencias": [oc]})

    def test_atualizar_preserva_ex01_e_recalcula_resumo_do_lote(self):
        doc = lote()
        doc["resumo"]["por_nivel"] = {"baixa": 9}
        with tempfile.TemporaryDirectory() as tmp:
            caminho = Path(tmp) / "l.json"
            caminho.write_text(json.dumps(doc), encoding="utf-8")
            r = self.rodar("--atualizar", str(caminho))
            self.assertEqual(r.returncode, 0, r.stderr)
            novo = json.loads(caminho.read_text(encoding="utf-8"))
        self.assertEqual(novo["resumo"]["por_nivel"], {"alta": 1, "critica": 1})
        self.assertIn(cp.EX01, novo["analises"][1]["ocorrencias"][0]["prioridade"]["regras_aplicadas"])

    def test_atualizar_nao_grava_se_houver_erro(self):
        doc = analise_buraco()
        doc["ocorrencias"][0]["prioridade"]["fatores"]["abrangencia"]["nota"] = 7
        with tempfile.TemporaryDirectory() as tmp:
            caminho = Path(tmp) / "a.json"
            conteudo = json.dumps(doc)
            caminho.write_text(conteudo, encoding="utf-8")
            r = self.rodar("--atualizar", str(caminho))
            self.assertEqual(r.returncode, 1)
            self.assertIn("oc-1: abrangencia", r.stderr)
            self.assertEqual(caminho.read_text(encoding="utf-8"), conteudo)

    def test_atualizar_varios_arquivos_isola_o_erro(self):
        ruim = analise_buraco()
        ruim["ocorrencias"][0]["prioridade"]["fatores"]["abrangencia"]["nota"] = 7
        bom = analise_buraco()
        bom["ocorrencias"][0]["prioridade"]["pontuacao"] = 99
        with tempfile.TemporaryDirectory() as tmp:
            c_ruim, c_bom = Path(tmp) / "ruim.json", Path(tmp) / "bom.json"
            c_ruim.write_text(json.dumps(ruim), encoding="utf-8")
            c_bom.write_text(json.dumps(bom), encoding="utf-8")
            r = self.rodar("--atualizar", str(c_ruim), str(c_bom))
            self.assertEqual(r.returncode, 1)
            self.assertIn("ruim.json: erro", r.stderr)
            self.assertEqual(json.loads(c_ruim.read_text(encoding="utf-8")), ruim)
            self.assertEqual(json.loads(c_bom.read_text(encoding="utf-8"))["ocorrencias"][0]["prioridade"]["pontuacao"], 47)



class Matriz110(unittest.TestCase):
    """Matriz 1.1.0: pesos e faixas iguais aos da 1.0.0, regras ex06 e ex07 (priorizacao.md 6 e 9.5-9.7)."""

    def test_versao_e_pesos_preservados(self):
        self.assertEqual(cp.VERSAO_MATRIZ, "1.1.0")
        self.assertEqual(cp.PESOS, {"risco_integridade_fisica": 30, "abrangencia": 20, "vulnerabilidade_afetados": 15,
                                    "impacto_servico_essencial": 15, "persistencia": 10, "risco_agravamento": 10})
        self.assertEqual([cp.faixa(x) for x in (29, 30, 54, 55, 74, 75)],
                         ["baixa", "media", "media", "alta", "alta", "critica"])

    def test_9_5_esgoto_fica_em_media(self):
        r = cp.calcular(fatores_esgoto(), "problema_existente")
        p = r["prioridade"]
        self.assertEqual((p["pontuacao"], p["pontuacao_teto"], p["nivel"], p["nivel_teto"], p["regras_aplicadas"]),
                         (47, 62, "media", "alta", []))
        self.assertEqual(r["pendencias_obrigatorias"], [cp.PEND_COMPLEMENTAR])

    def test_esgoto_sobe_so_com_evidencia(self):
        f = fatores_esgoto()
        f["vulnerabilidade_afetados"] = fator(2, "relatado", "a creche fica nessa rua")
        p = cp.calcular(f, "problema_existente")["prioridade"]
        self.assertEqual((p["nivel"], p["regras_aplicadas"]), ("alta", [cp.EX03]))
        f = fatores_esgoto()
        f["risco_integridade_fisica"] = fator(3, "relatado", "as crianças ficaram doentes")
        self.assertIn(cp.EX02, cp.calcular(f, "problema_existente")["prioridade"]["regras_aplicadas"])
        f = fatores_esgoto()
        f["risco_integridade_fisica"] = fator(3, "inferido", raciocinio="Pode causar doença.")
        p = cp.calcular(f, "problema_existente")["prioridade"]
        self.assertNotIn(cp.EX02, p["regras_aplicadas"], "risco potencial inferido não é dano relatado")

    def test_9_6_semaforo_com_ex06(self):
        sem = cp.calcular(fatores_semaforo(), "problema_existente", subcategoria="mob_semaforo")["prioridade"]
        self.assertEqual((sem["pontuacao"], sem["nivel"]), (33, "media"))
        r = cp.calcular(fatores_semaforo(), "problema_existente", falha_controle_trafego=True, subcategoria="mob_semaforo")
        p = r["prioridade"]
        self.assertEqual((p["pontuacao"], p["nivel_base"], p["nivel"], p["nivel_teto"]), (33, "media", "alta", "alta"))
        self.assertEqual(p["regras_aplicadas"], [cp.EX06])
        self.assertIn("ex06_falha_controle_trafego alterou de média para alta", p["justificativa"])
        self.assertEqual(r["pendencias_obrigatorias"], [])

    def test_ex06_sem_evidencia_suficiente_e_rejeitada(self):
        casos = []
        casos.append(("subcategoria", fatores_semaforo(), "mob_sinalizacao_viaria"))
        f = fatores_semaforo(); f["abrangencia"] = fator(1, "inferido", "Rua 3", "Rua local.")
        casos.append(("abrangencia", f, "mob_semaforo"))
        f = fatores_semaforo(); f["risco_integridade_fisica"] = fator_ausente()
        casos.append(("risco_integridade_fisica", f, "mob_semaforo"))
        f = fatores_semaforo(); f["abrangencia"] = fator(2, "inferido", raciocinio="Deve ser avenida.")
        casos.append(("evidência literal", f, "mob_semaforo"))
        for trecho, fatores, sub in casos:
            with self.subTest(trecho):
                with self.assertRaises(cp.ErroEntrada) as ctx:
                    cp.calcular(fatores, "problema_existente", falha_controle_trafego=True, subcategoria=sub)
                self.assertIn(cp.EX06, str(ctx.exception))
                self.assertIn(trecho, str(ctx.exception))

    def test_9_7_escola_com_ex07(self):
        p = cp.calcular(fatores_escola(), "problema_existente")["prioridade"]
        self.assertEqual((p["pontuacao"], p["completude"], p["nivel_base"], p["nivel"]), (52, 1.0, "media", "alta"))
        self.assertEqual(p["regras_aplicadas"], [cp.EX07])

    def test_ex07_exige_os_dois_fatores_relatados(self):
        for codigo, novo in (("vulnerabilidade_afetados", fator(3, "inferido", raciocinio="Deve haver alunos com deficiência.")),
                             ("impacto_servico_essencial", fator(2, "inferido", raciocinio="Deve dificultar.")),
                             ("impacto_servico_essencial", fator(1, "relatado", "é difícil entrar")),
                             ("vulnerabilidade_afetados", fator(2, "relatado", "é uma escola"))):
            with self.subTest(codigo=codigo, nota=novo["nota"], status=novo["status"]):
                f = fatores_escola(); f[codigo] = novo
                self.assertNotIn(cp.EX07, cp.calcular(f, "problema_existente")["prioridade"]["regras_aplicadas"])

    def test_ex07_numa_necessidade_fica_em_alta_e_ex01_prevalece(self):
        f = fatores_escola()
        f["risco_integridade_fisica"] = fator(3, "relatado", "a escada desabou agora")
        f["abrangencia"] = fator(3, "inferido", raciocinio="Bairro inteiro.")
        f["persistencia"] = fator(3, "inferido", raciocinio="Antigo.")
        f["risco_agravamento"] = fator(3, "inferido", raciocinio="Piora.")
        p = cp.calcular(f, "necessidade_infraestrutura")["prioridade"]
        self.assertEqual(p["nivel"], "alta")
        self.assertIn(cp.EX07, p["regras_aplicadas"])
        self.assertIn(cp.EX04, p["regras_aplicadas"])
        p = cp.calcular(f, "problema_existente", risco_iminente=True)["prioridade"]
        self.assertEqual(p["nivel"], "critica")

    def test_atualizar_preserva_ex06_e_le_a_subcategoria(self):
        doc = analise_semaforo()
        oc = doc["ocorrencias"][0]
        oc["prioridade"]["nivel"] = "media"
        cp.atualizar_documento(doc)
        self.assertEqual(oc["prioridade"]["nivel"], "alta")
        self.assertIn(cp.EX06, oc["prioridade"]["regras_aplicadas"])
        oc["classificacao"]["subcategoria"] = "mob_sinalizacao_viaria"
        with self.assertRaises(cp.ErroEntrada):
            cp.atualizar_documento(doc)

    def test_modo_simples_aceita_falha_controle_trafego(self):
        entrada = json.dumps({"natureza": "problema_existente", "falha_controle_trafego": True,
                              "subcategoria": "mob_semaforo", "fatores": fatores_semaforo()})
        r = subprocess.run([sys.executable, str(SCRIPT), "-"], input=entrada, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout)["prioridade"]["nivel"], "alta")

if __name__ == "__main__":
    unittest.main()

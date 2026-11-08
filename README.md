# EcoRastro AI: analisador de relatos urbanos

Projeto acadêmico. **Parte 1:** uma *skill* do Claude Code que transforma a reclamação livre de um cidadão ("tem um buraco enorme na minha rua…") num registro padronizado, pronto para uma equipe de triagem e, no futuro, para um sistema Django. A Parte 2 é esse sistema e ainda não foi iniciada.

> Autor(a): _preencher_ · Disciplina: _preencher_ · Versão entregue: skill **0.3.1**

## 1. O problema

Prefeituras recebem relatos por aplicativo, site, WhatsApp e telefone, em texto livre. Para atender, alguém precisa responder quatro perguntas:
1. Qual é o problema?
2. Onde está?
3. Com que urgência atender, e por quê?
4. Como fazer isso sem expor quem relatou?

Fazer isso à mão é lento e inconsistente. A skill responde as quatro perguntas de forma padronizada, rastreável e auditável.

## 2. O que a skill faz

| Etapa | O que acontece | Por que importa |
|---|---|---|
| Mascaramento | Nome, CPF, telefone, e-mail, placa e dados sensíveis viram marcadores (`[NOME]`, `[TELEFONE]`…) | Privacidade (LGPD) |
| Triagem | Classificado, informação insuficiente ou fora do escopo | Não forçar o que não é problema urbano |
| Classificação | 7 categorias e 56 subcategorias com códigos estáveis | O sistema pode filtrar e agregar |
| Prioridade de triagem | 6 fatores com nota de 0 a 3, fórmula fixa e regras de exceção | Qualquer pessoa pode refazer o cálculo |
| Emergência | Perigo atual relatado → alerta com o serviço a acionar | A skill **orienta**; não aciona nada |
| Saídas | JSON validado (interno e público) e relatório em Markdown | Contrato para o Django |

Três princípios guiam tudo:
- **Nunca inventar.** Endereço, data ou coordenada que o relato não traz ficam `ausente`.
- **Ausente não é zero.** Zero quer dizer "avaliamos e não há impacto"; ausente quer dizer "não dá para saber". A diferença aparece no teto da pontuação e vira pedido de complemento.
- **A escala é heurística.** É uma *prioridade de triagem* para ordenar a fila, não uma avaliação de risco validada cientificamente.

## 3. Como a prioridade é calculada

```
pontuação = (30·risco + 20·abrangência + 15·vulnerabilidade + 15·serviço essencial
             + 10·persistência + 10·agravamento) ÷ 3

baixa 0–29 · média 30–54 · alta 55–74 · crítica 75–100
```

Regras de exceção cobrem o que a soma trata mal. Exemplos:
- dano físico relatado → no mínimo alta (`ex02`);
- perigo iminente → crítica (`ex01`);
- semáforo apagado em avenida → no mínimo alta (`ex06`);
- grupo vulnerável impedido de acessar um serviço essencial → no mínimo alta (`ex07`);
- pedido de obra nova → no máximo alta (`ex04`).

O modelo de linguagem dá as notas. Um script em Python faz a conta e escreve a justificativa, para que o resultado seja reproduzível.

## 4. Estrutura do projeto

```
ecorastro-ai/
├── README.md                          ← este arquivo
├── exemplos/                          ← 3 demonstrações para apresentação
└── .claude/skills/
    ├── ecorastro-analisador/          ← a skill entregue
    │   ├── SKILL.md                   ← instruções que o Claude segue
    │   ├── CHANGELOG.md               ← histórico de versões e decisões
    │   ├── references/                ← taxonomia, matriz de prioridade, modelos de relatório
    │   ├── assets/                    ← JSON Schema 1.2.0 (+ versões anteriores em historico/)
    │   ├── scripts/                   ← gerar_metadados, calcular_prioridade, validar_analise + testes
    │   ├── evals/                     ← 11 casos de avaliação, 82 critérios
    │   └── docs/                      ← integração Django, compatibilidade, privacidade, retenção
    └── ecorastro-analisador-workspace/ ← resultados das avaliações (fora do Git)
```

## 5. Requisitos

- [Claude Code](https://claude.com/claude-code) instalado e autenticado.
- Python 3.10 ou superior, com o pacote `jsonschema`: `python3 -m pip install jsonschema`.

A skill é *de projeto*: o Claude Code a encontra automaticamente quando é aberto na pasta `ecorastro-ai`.

## 6. Como demonstrar

1. Abra o terminal na pasta do projeto e rode `claude`.
2. Confira que a skill foi carregada: digite `/` e procure `ecorastro-analisador`.
3. Cole o pedido de um dos exemplos de `exemplos/`. A skill é acionada sozinha, sem precisar citá-la.
4. Mostre a resposta e o JSON gerado em `saidas/json/`.

| Exemplo | Demonstra |
|---|---|
| `exemplos/01-relato-simples.md` | Classificação, prioridade rastreável, não inventar data |
| `exemplos/02-emergencia.md` | Risco iminente, alerta antes de tudo |
| `exemplos/03-dados-pessoais-versao-publica.md` | Mascaramento, versão interna × pública |

Comandos úteis, rodados na raiz do projeto:

```bash
# Validar um JSON gerado
python3 .claude/skills/ecorastro-analisador/scripts/validar_analise.py saidas/json/<arquivo>.json

# Rodar os testes automatizados (133 testes)
python3 -B -m unittest discover -s .claude/skills/ecorastro-analisador/scripts/tests

# Calcular uma prioridade isolada (exemplo do semáforo)
echo '{"natureza":"problema_existente","falha_controle_trafego":true,"subcategoria":"mob_semaforo",
 "fatores":{"risco_integridade_fisica":{"nota":2,"status":"relatado","evidencia":"quase vi uma batida","raciocinio":"Quase-acidente.","verificacao":null},
 "abrangencia":{"nota":2,"status":"inferido","evidencia":"Av. Paraná x Rua 3","raciocinio":"Cruzamento de avenida.","verificacao":null},
 "vulnerabilidade_afetados":{"nota":null,"status":"ausente","evidencia":null,"raciocinio":"Não informado.","verificacao":null},
 "impacto_servico_essencial":{"nota":null,"status":"ausente","evidencia":null,"raciocinio":"Não informado.","verificacao":null},
 "persistencia":{"nota":0,"status":"relatado","evidencia":"desde manhã","raciocinio":"Menos de 24 h.","verificacao":null},
 "risco_agravamento":{"nota":0,"status":"inferido","evidencia":null,"raciocinio":"Não piora sozinho.","verificacao":null}}}' \
 | python3 .claude/skills/ecorastro-analisador/scripts/calcular_prioridade.py -
```

## 7. Como a skill foi avaliada

A skill foi construída com o fluxo do *skill-creator*: casos de teste realistas, execuções com e sem a skill e critérios verificáveis por script.

| Iteração | Versão | Resultado |
|---|---|---|
| 1 | 0.1.0 | Com skill 69/70 critérios; sem skill 12/70 |
| 2 | 0.2.0 | 45/45 nos casos afetados (0.1.0: 44/45); erros na 1ª validação: 0 × 5 |
| 3 | 0.3.0 | 42/43 nos casos afetados (0.2.0: 38/43); sem regressão nos casos simples |

Verificação final (Etapa 7):
- **Acionamento:** um relato urbano aciona a skill; um pedido de código Django não aciona.
- **Testes:** 133 testes automatizados passando.

## 8. Privacidade e limites

- As versões **internas** contêm o texto original. Ficam com `chmod 600` e fora do Git (`.gitignore`).
- As versões **públicas** nunca têm texto original. Com dado sensível de pessoa identificável:
  - mostram só um resumo anonimizado;
  - usam um único marcador por pessoa;
  - usam rótulos que não revelam a condição.
- O validador não detecta nomes de pessoas por regra automática. Isso fica a cargo da análise e da lista de verificação.
- A prioridade é **provisória e heurística**. Os pesos devem ser recalibrados quando houver dados reais de atendimento.

## 9. Próximos passos (Parte 2, não iniciada)

O planejamento da integração está em `.claude/skills/ecorastro-analisador/docs/integracao-django.md`: modelos, fluxo de validação, API sugerida e perfis de acesso. A política de retenção de dados é uma **proposta** para o Django (`docs/politica-retencao-proposta.md`), a validar com o encarregado de dados.

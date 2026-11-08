# Integração futura com Django

Situação: **documentação de planejamento.** Nada de Django foi implementado; isso é a Parte 2 do projeto. Este documento diz o que o sistema Django precisa respeitar para receber as análises da skill sem perder rastreabilidade nem privacidade.

## 1. Papéis

```
Cidadão ──relato──▶ Django (recebe, guarda recebido_em e canal)
                       │
                       ▼
               Análise (skill ou API do Claude com as mesmas instruções)
                       │  JSON no contrato 1.2.0 (interna + publica)
                       ▼
               Django valida ──▶ grava ──▶ fila de triagem (equipe)
                                      └──▶ painel público (só versão publica)
```

- **A skill** classifica, pontua e mascara. Ela é a "produtora" do contrato.
- **O Django** recebe, valida, armazena, controla acesso, aplica a retenção e registra verificações humanas (status `verificado`).
- **O contrato** entre os dois é `assets/analise.schema.json` (schema 1.2.0). Os códigos (categorias, fatores, regras, órgãos) são identificadores estáveis e podem virar `choices` no Django.

## 2. Modelos sugeridos

| Modelo | Origem no JSON | Observações |
|---|---|---|
| `Relato` | `relato` | `hash_texto` único (deduplicação); `texto_original` em campo de acesso restrito; `recebido_em` vem do Django, nunca da análise |
| `Analise` | raiz de `analise_relato` | `schema_version`, `visibilidade`, `resultado_triagem`, `metadados` (versões da skill, taxonomia e matriz); JSON completo guardado também como cópia íntegra |
| `Ocorrencia` | `ocorrencias[]` | `natureza`, `requer_obra_adequacao`, classificação, localização, data, órgão, alegação, pendências |
| `FatorPrioridade` | `prioridade.fatores` | 6 linhas por ocorrência: `nota` (nula se ausente), `status`, `evidencia`, `raciocinio`, `verificacao` |
| `Prioridade` | `prioridade` | pontuação, teto, completude, níveis, `regras_aplicadas`, `versao_matriz`, justificativa |
| `Lote` | `lote_analises` | agrupa análises; `resumo` pode ser recalculado pelo Django |
| `RegistroAcesso` | (novo) | quem leu dados internos, quando e qual análise |

Regras que o modelo deve preservar:
- **Ausente não é zero.** `nota` de fator ausente é `NULL`, nunca 0.
- **Status em todo dado extraído** (`relatado`, `inferido`, `ausente`; `verificado` só pelo Django ou revisor).
- **Versões em cada registro** (`schema_version`, `versao_matriz`), porque notas de matrizes diferentes não são comparáveis.

## 3. Fluxo de recebimento (proposta)

1. Receber o relato e registrar `recebido_em`, `canal` e `id_externo`.
2. Calcular `hash_texto` (mesma normalização de `scripts/gerar_metadados.py`) e procurar duplicados.
3. Solicitar a análise (versões interna e pública).
4. Validar:
   - estrutura com o JSON Schema (biblioteca `jsonschema`);
   - aritmética da prioridade com a mesma lógica de `scripts/calcular_prioridade.py`, que é Python puro e pode ser reaproveitado como módulo;
   - regras semânticas de `scripts/validar_analise.py`. O núcleo (funções `validar_documento`) também é reaproveitável.
5. Rejeitar análises com ERRO; registrar AVISOS para revisão.
6. Gravar a versão interna (acesso restrito) e a pública (painel).
7. Se `alerta_emergencia.acionar` for verdadeiro, destacar na fila. A skill só **orienta**; quem aciona serviços é uma pessoa.

## 4. API sugerida (sem implementação)

| Método e rota | Uso | Visibilidade |
|---|---|---|
| `POST /api/relatos/` | Recebe relato e dispara a análise | Interna |
| `GET /api/ocorrencias/?nivel=&categoria=&bairro=` | Fila de triagem | Interna |
| `PATCH /api/ocorrencias/{id}/fatores/{codigo}/` | Revisor confirma fator (`verificado`) e o Django recalcula a prioridade | Interna |
| `GET /api/painel/ocorrencias/` | Painel público, só dados `publica` | Pública |

Recalcular a prioridade após verificação humana usa as notas armazenadas e a mesma matriz (`versao_matriz` do registro). Para aplicar uma matriz nova a registros antigos, é preciso reanalisar o relato (ver `compatibilidade-versoes.md`).

## 5. Privacidade e acesso

- `texto_original`, `id_externo` e a versão interna: só o perfil de triagem, com registro de acesso.
- Painel público: só a versão `publica`. Se `dados_pessoais.texto_relato_publicavel` for `false`, exibir apenas `descricao_neutra`, local e níveis — nunca o texto do relato nem evidências literais — e usar o rótulo "Acessibilidade e inclusão" para `org_acessibilidade_inclusao`.
- Retenção e exclusão: seguir a proposta em `politica-retencao-proposta.md` (prazos a validar com o encarregado de dados).
- Arquivos `_interna` nunca vão para o Git (`.gitignore` do projeto).

## 6. Documentos relacionados

| Documento | Conteúdo |
|---|---|
| `assets/analise.schema.json` | Contrato 1.2.0 |
| `assets/historico/` | Schemas 1.0.0 e 1.1.0 |
| `docs/compatibilidade-versoes.md` | Conversão de documentos antigos e comparação entre matrizes |
| `docs/politica-retencao-proposta.md` | Retenção e exclusão de dados (proposta) |
| `references/priorizacao.md` | Matriz 1.1.0, para reimplementar ou reaproveitar o cálculo |

## 7. Lista para a Parte 2

- [ ] Modelos com `choices` gerados a partir dos enums do schema.
- [ ] Validação de entrada com o schema e com o núcleo dos scripts.
- [ ] Perfis de acesso (triagem × público) e registro de acesso.
- [ ] Deduplicação por `hash_texto`.
- [ ] Recalcular prioridade após verificação humana, sem trocar a versão da matriz.
- [ ] Rotina de retenção, depois de validar os prazos.
- [ ] Testes que reutilizem os exemplos de `references/priorizacao.md` (seção 9).

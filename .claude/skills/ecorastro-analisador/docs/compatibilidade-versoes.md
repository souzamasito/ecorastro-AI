# Compatibilidade entre versões

Este documento diz o que muda entre as versões do contrato JSON e da matriz de prioridade, e como o futuro sistema Django deve tratar registros antigos.

## 1. Versões publicadas

| Skill | Schema (`schema_version`) | Matriz (`versao_matriz_prioridade`) | Taxonomia | Etapa |
|---|---|---|---|---|
| 0.1.0 | 1.0.0 | 1.0.0 | 1.0.0 | 1 a 5 |
| 0.2.0 | 1.1.0 | 1.0.0 | 1.0.0 | 6 |
| 0.3.0 | **1.2.0** | **1.1.0** | 1.0.0 | 6 (complemento) |

Os schemas anteriores estão em `assets/historico/analise.schema-1.0.0.json` e `assets/historico/analise.schema-1.1.0.json`. A taxonomia continua 1.0.0: nenhum código de categoria ou subcategoria mudou. As regras novas de classificação (obra de adequação, seção 5.1 de `categorias.md`) usam os códigos existentes.

## 2. Schema

### 1.0.0 → 1.1.0

| Mudança | Tipo | Efeito em documentos 1.0.0 |
|---|---|---|
| `data_ocorrencia` ausente pode ter `evidencia` (a expressão temporal literal) | Relaxa uma regra | O conteúdo continua válido; só `schema_version` muda |

### 1.1.0 → 1.2.0

| Mudança | Tipo | Regra |
|---|---|---|
| `ocorrencia.requer_obra_adequacao` (booleano, obrigatório) | Campo novo | `false` em `necessidade_infraestrutura` |
| `dados_pessoais.texto_relato_publicavel` (booleano, obrigatório) | Campo novo | `false` em visibilidade `interna` e quando `dado_sensivel` está em `tipos` |
| `ex06_falha_controle_trafego` e `ex07_barreira_acesso_servico_essencial` em `regra_excecao` | Valores novos de enum | Aditivo |

Um documento 1.1.0 **não** é válido no schema 1.2.0, por dois motivos: os campos novos são obrigatórios e `schema_version` é constante. A escolha foi deliberada. Campos opcionais deixariam a dúvida "não se aplica ou não foi avaliado?", que é justamente a confusão que o contrato evita em todo o resto ("ausente não é zero").

### Leitura de documentos antigos pelo Django (proposta)

1. Ler `schema_version` e validar com o schema daquela versão (`assets/historico/`).
2. Para converter 1.1.0 em 1.2.0, sem reanalisar:
   - `requer_obra_adequacao = false`. É uma classificação nova; registros de acessibilidade em equipamento público devem ir para revisão humana, e não ser marcados automaticamente;
   - `texto_relato_publicavel = false` se a visibilidade for `interna` ou se `dado_sensivel` estiver em `tipos`. Nos demais, `true`;
   - `schema_version = "1.2.0"`. Registrar a conversão, para que se saiba que esses campos não vieram de uma análise.
3. Documentos 1.0.0 passam primeiro pela conversão para 1.1.0, que só troca a versão.

Nada disso está implementado. A skill só produz documentos 1.2.0.

## 3. Matriz de prioridade

### 1.0.0 → 1.1.0

| Item | Mudou? |
|---|---|
| Pesos (30/20/15/15/10/10) | Não |
| Faixas (0–29, 30–54, 55–74, 75–100) | Não |
| Fórmula, piso, teto, completude | Não |
| Âncoras | Sim: A1 (risco à saúde e potencial × dano), A2 (falha do próprio serviço essencial), A3 (acesso à moradia só quando bloqueado), A4 (abrangência de serviços por rua) |
| Regras | Sim: `ex06` (afirmada pela análise, conferida pelo script) e `ex07` (calculada pelo script) |

Consequências:
- **As notas não são comparáveis entre versões.** O mesmo relato pode receber notas diferentes porque as âncoras mudaram (por exemplo, esgoto: impacto em serviço essencial `ausente` na 1.0.0 e 2 na 1.1.0). Relatórios que misturem as duas versões devem dizer isso.
- **Não recalcule registros 1.0.0 com a aritmética 1.1.0.** O resultado misturaria notas dadas pelas âncoras antigas com regras novas. Além disso, `ex07` apareceria só onde as notas antigas coincidissem com a condição, e `ex06` nunca apareceria, porque é uma afirmação da análise. Para aplicar a 1.1.0 a um registro antigo, reanalise o relato.
- Cada ocorrência guarda `prioridade.versao_matriz`. Os níveis de versões diferentes podem conviver na mesma fila, desde que a versão fique visível para quem revisa.

## 4. Validador

`validar_analise.py` (skill 0.3.0) valida documentos 1.2.0 com a matriz 1.1.0:
- `--schema assets/historico/analise.schema-1.1.0.json` confere a **estrutura** de um documento antigo;
- as verificações de pontuação usam sempre a matriz atual. Num documento antigo, elas acusam a diferença de versão e as regras novas. Isso não indica que o documento estava errado na versão em que foi gerado.

A validação completa de um documento antigo exige o validador da versão correspondente. As cópias usadas nos testes ficam em `ecorastro-analisador-workspace/skill-snapshot-0.1.0/` e `skill-snapshot-0.2.0/`. No Django, a recomendação é manter o validador e o schema versionados juntos.

# Modelos de relatório — EcoRastro AI

Relatórios são a versão legível das análises. Eles são lidos por pessoas que talvez nunca abram o JSON: gestores, equipes de campo, conselhos de bairro, o próprio cidadão. Por isso cada afirmação mostra de onde veio, e o relatório público não pode permitir identificar ninguém.

O relatório é sempre gerado **a partir do JSON da mesma visibilidade**: o relatório `publica` sai de dados `publica`, e o `interna` sai de dados `interna`. Nada entra no relatório sem estar no JSON correspondente.

## Sumário

1. [Regras gerais](#1-regras-gerais)
2. [Interna × pública](#2-interna--pública)
3. [Modelo A — relatório individual](#3-modelo-a--relatório-individual)
4. [Modelo B — relatório consolidado de lote](#4-modelo-b--relatório-consolidado-de-lote)
5. [Rótulos de apresentação](#5-rótulos-de-apresentação)
6. [Verificação do relatório](#6-verificação-do-relatório)

---

## 1. Regras gerais

- **Códigos não aparecem soltos.** Use os rótulos da seção 5. O código pode aparecer entre crases ao lado do rótulo quando ajudar a cruzar com o JSON (ex.: na tabela de fatores).
- **Origem visível.** Ao lado de cada dado extraído, indique a origem: *(relatado)* ou *(inferido)*. Para campos ausentes, escreva **"não informado"**.
- **Ausente não é zero.** Na tabela de fatores, fator ausente aparece como "— (não informado)", nunca como 0. Zero significa "avaliado, sem impacto".
- **Nome da escala.** Escreva sempre "prioridade de triagem", nunca "risco", "nível de risco" ou "avaliação de risco".
- **Aviso obrigatório.** Todo relatório termina com o aviso da seção 3 (bloco "Sobre esta análise").
- **Alegações.** Use linguagem de alegação ("o relato alega que…") e marque *pendente de verificação*.
- **Datas.** Formato brasileiro (07/11/2026 09:31). Indique o fuso quando não for o horário de Brasília.
- **Tom.** Factual e sem alarmismo, mesmo nos casos críticos. O destaque visual (🚨) é reservado ao alerta de emergência.

## 2. Interna × pública

| Elemento | `interna` (acesso restrito) | `publica` (compartilhável) |
|---|---|---|
| Cabeçalho | "Uso interno — acesso restrito" | "Versão pública — dados pessoais anonimizados" |
| Texto original | Pode ser incluído em seção própria, ao final | **Nunca** |
| Texto mascarado | Sim | Só se `dados_pessoais.texto_relato_publicavel` for `true` (anonimizado também quanto à residência e às empresas citadas em alegações). Se for `false`, **não reproduza** o texto: use o resumo anonimizado (`descricao_neutra`) |
| `id_externo` / protocolo | Sim | Não (pode ligar o relato ao cidadão no sistema de origem) |
| `hash_texto` | Opcional | Não |
| Endereço do problema | Completo, como relatado | Completo, exceto número de residência → `[NUMERO]` |
| Alegações | Descrição neutra, com empresa se citada | Descrição neutra, com `[EMPRESA]` |
| Evidências citadas | Do texto mascarado interno | Do texto mascarado público, só se `texto_relato_publicavel` for `true`; se for `false`, a coluna "Base" traz o raciocínio genérico, sem citação |

Em lotes públicos, não combine detalhes que, juntos, identifiquem uma pessoa. Por exemplo, não liste o único relato de um logradouro pequeno junto com uma condição de saúde mencionada.

`texto_relato_publicavel = false` significa que o relato tem dado sensível de pessoa identificável (seção 11.1 de `categorias.md`). Nesse caso, a versão pública mostra o problema, não a pessoa: resumo anonimizado, local do problema, notas e raciocínios genéricos ("pessoa de grupo vulnerável relatada"). Nenhuma citação literal, nenhuma menção à moradia da pessoa, nenhuma contagem de condições.

## 3. Modelo A — relatório individual

Os campos entre `{{ }}` vêm do JSON. Remova as seções marcadas como condicionais quando não se aplicarem.

```markdown
# Análise de relato urbano — {{rótulo da subcategoria da oc-1}}{{" e mais N" se houver mais ocorrências}}

{{"Uso interno — acesso restrito" | "Versão pública — dados pessoais anonimizados"}}
Análise {{id_analise[0:8]}} · {{analisado_em formatado}} · Canal: {{rótulo do canal}}{{ · Protocolo: id_externo — só interna}}

<!-- condicional: alerta_emergencia.acionar -->
> 🚨 **Atenção: possível risco imediato.** {{alerta_emergencia.motivo}}
> Quem estiver no local deve acionar: {{rótulos dos serviços}}.
> Esta análise apenas orienta o acionamento; nenhum serviço foi acionado automaticamente.

## Resumo

| | |
|---|---|
| Resultado da triagem | {{rótulo}} |
| Ocorrências identificadas | {{n}} |
| Maior prioridade de triagem | {{nível}} ({{pontuação}} pts){{", provisória" se for o caso}} |
| Dados pessoais | {{"Nenhum detectado" | "Anonimizados: " + rótulos dos tipos}} |

<!-- condicional: resultado_triagem ≠ classificado -->
**Motivo:** {{motivo_triagem}}
**O que seria necessário para analisar:** {{pendências legíveis}}

## Relato (texto anonimizado)

> {{texto_mascarado}}

<!-- na versão pública com texto_relato_publicavel = false, substitua a seção acima por: -->
## Relato

O texto do relato não é reproduzido nesta versão, para proteger uma pessoa identificável. Resumo: {{descricao_neutra}}

<!-- repetir para cada ocorrência -->
## Ocorrência {{n}} — {{rótulo da subcategoria}}

{{descricao_neutra}}

| | |
|---|---|
| Categoria | {{rótulo da categoria}}{{" · também envolve: " + secundárias}} |
| Natureza | {{Problema existente: manutenção ou reparo | Problema existente: obra de adequação (exigência obrigatória não cumprida), se requer_obra_adequacao | Necessidade de infraestrutura: obra ou serviço novo, para planejamento}} |
| Classificação | Confiança {{alta/média/baixa}}{{" · caso ambíguo: " + motivo_ambiguidade}}{{" · critério de desempate: " + rótulo da regra}} |
| Local | {{endereco_texto}} *({{origem}})* · Bairro: {{… ou "não informado"}} · Referência: {{…}} · Município: {{…}} |
| Precisão do local | {{exata/aproximada/não informada}} |
| Quando | {{data formatada *(inferido: "evidência")*  ou "não informado"}} |
| Órgão sugerido | {{rótulo}}{{" · apoio: " + rótulos}} *(sugestão)* |

### Prioridade de triagem: {{NÍVEL}} — {{pontuação}} pts{{" (provisória)"}}

{{justificativa}}

| Fator | Peso | Nota | Origem | Base |
|---|---|---|---|---|
| Risco à integridade física `risco_integridade_fisica` | 30 | {{0–3 ou "—"}} | {{relatado/inferido/não informado}} | {{"evidência" ou raciocínio; na pública com texto_relato_publicavel = false, só raciocínio genérico}} |
| Abrangência `abrangencia` | 20 | | | |
| Vulnerabilidade dos afetados `vulnerabilidade_afetados` | 15 | | | |
| Impacto em serviço essencial `impacto_servico_essencial` | 15 | | | |
| Persistência `persistencia` | 10 | | | |
| Risco de agravamento `risco_agravamento` | 10 | | | |

- Faixa pela pontuação: {{nivel_base}}{{" → ajustada para " + nivel + " pela regra " + rótulos das regras que alteraram"}}
- Regras consideradas: {{rótulos de regras_aplicadas, ou "nenhuma"}}
- Completude: {{completude em %}} dos fatores avaliados
<!-- condicional: nivel_teto > nivel -->
- Com as informações que faltam, a prioridade pode chegar a **{{nivel_teto}}** ({{pontuacao_teto}} pts).

<!-- condicional: alegacao_irregularidade.presente -->
**Alegação registrada** *(pendente de verificação)*: {{descricao_neutra}}
A alegação não altera a prioridade de triagem, que considera apenas os efeitos descritos.

## Pendências

{{lista legível, agrupando as do relato e as de cada ocorrência, com a pergunta que resolveria cada uma}}

Exemplos de redação:
- **Localização imprecisa** — Qual o número ou ponto de referência mais próximo?
- **Complementar dados de prioridade** — Há escola, unidade de saúde ou grande circulação de pessoas no local?

<!-- condicional: interna, se o usuário pedir -->
## Texto original (acesso restrito)

> {{texto_original}}

---

### Sobre esta análise

Classificação e prioridade geradas automaticamente pela skill ecorastro-analisador {{versao_skill}} (taxonomia {{versao_taxonomia}}, matriz {{versao_matriz_prioridade}}). A prioridade de triagem é uma escala heurística e provisória para ordenar atendimentos. Ela não é uma avaliação de risco validada e não substitui vistoria técnica nem os serviços de emergência. Informações marcadas como *relatado* vêm do texto do cidadão e não foram verificadas em campo. Itens *inferidos* são deduções da análise.
```

## 4. Modelo B — relatório consolidado de lote

Para o lote, priorize a visão de conjunto. O detalhe de cada ocorrência vive no JSON; o relatório lista e ordena.

```markdown
# Relatório consolidado de relatos urbanos — {{data do lote}}

{{cabeçalho de visibilidade}}
Lote {{id_lote[0:8]}} · {{gerado_em formatado}} · {{total_relatos}} relatos · {{total_ocorrencias}} ocorrências

<!-- condicional: total_alertas_emergencia > 0 -->
> 🚨 **{{n}} ocorrência(s) com possível risco imediato.** Ver primeira tabela abaixo.

## Visão geral

| Prioridade de triagem | Ocorrências | % |
|---|---|---|
| Crítica | | |
| Alta | | |
| Média | | |
| Baixa | | |
| **Total** | | 100% |

{{n}} ocorrências têm prioridade provisória (informação insuficiente).

| Resultado da triagem | Relatos |
|---|---|
| Classificados | |
| Informação insuficiente | |
| Fora do escopo | |
| Linhas vazias ignoradas | |

| Categoria | Ocorrências | Problemas existentes | Necessidades de infraestrutura |
|---|---|---|---|
| {{uma linha por categoria com ocorrências, ordenadas por total}} | | | |

## Atendimento imediato

<!-- ocorrências com nível crítica, alertas primeiro -->
| # | Ocorrência | Categoria | Local | Pts | Motivo principal | Órgão sugerido |
|---|---|---|---|---|---|---|
| {{id8}}/{{oc-n}} | {{rótulo da subcategoria}} | | {{local resumido}} | | {{fator ou regra decisiva}} | |

## Prioridade alta

{{mesma tabela}}

## Prioridade média e baixa

{{mesma tabela, ou só contagem por subcategoria se forem mais de 20 linhas}}

## Necessidades de infraestrutura

Demandas por algo que não existe no local, para encaminhamento ao planejamento. A prioridade dessas demandas é limitada a alta, salvo risco imediato relatado. Obras de adequação (problema existente com `requer_obra_adequacao`) **não** entram aqui: ficam nas tabelas de prioridade, com "obra de adequação" no motivo principal.

| Necessidade | Categoria | Local | Prioridade | Relatos |
|---|---|---|---|---|
| | | | | |

## Pontos de atenção

- **Alegações pendentes de verificação:** {{n}}, por tipo: {{…}}. Não foram consideradas na prioridade.
- **Casos ambíguos:** {{n}}. {{exemplo curto do motivo mais comum}}
- **Pendências mais frequentes:** {{as 3 mais comuns, com contagem}}
- **Locais recorrentes:** {{logradouros ou referências com 2 ou mais ocorrências, se houver}}

## Relatos não classificados

| Relato | Resultado | Motivo |
|---|---|---|
| {{id8}} | {{Informação insuficiente/Fora do escopo}} | {{motivo_triagem}} |

---

### Sobre esta análise

{{mesmo aviso do Modelo A}}
```

Nas tabelas do lote, o local e o motivo principal vêm de `descricao_neutra`, da localização e dos fatores. Nunca cite o texto de um relato com `texto_relato_publicavel = false`.

Para lotes muito grandes (mais de 50 ocorrências), mantenha as tabelas de crítica e alta completas e resuma média e baixa por subcategoria e local.

## 5. Rótulos de apresentação

Esta tabela é a fonte dos textos legíveis. O Django pode reutilizá-la como `label` das `TextChoices`.

### Categorias

| Código | Rótulo |
|---|---|
| `mobilidade_transito` | Mobilidade e trânsito |
| `infraestrutura_urbana` | Infraestrutura urbana |
| `meio_ambiente` | Meio ambiente |
| `servicos_publicos` | Serviços públicos |
| `acessibilidade` | Acessibilidade |
| `uso_espaco_publico` | Uso do espaço público |
| `seguranca_urbana` | Segurança urbana |

### Subcategorias

Para os códigos `*_outros`, use "Outros — {{rótulo da categoria}}".

| Código | Rótulo | Código | Rótulo |
|---|---|---|---|
| `mob_semaforo` | Semáforo com defeito | `svc_coleta_residuos` | Coleta de resíduos |
| `mob_sinalizacao_viaria` | Sinalização viária | `svc_limpeza_urbana` | Limpeza urbana |
| `mob_seguranca_viaria` | Segurança viária | `svc_abastecimento_agua` | Abastecimento de água |
| `mob_fluxo_congestionamento` | Fluxo e congestionamento | `svc_fornecimento_energia` | Fornecimento de energia |
| `mob_estacionamento_irregular` | Estacionamento irregular | `svc_saude` | Serviços de saúde |
| `mob_transporte_coletivo` | Transporte coletivo | `svc_educacao` | Serviços de educação |
| `mob_ciclomobilidade` | Ciclomobilidade | `svc_atendimento_publico` | Atendimento ao público |
| `inf_pavimento` | Pavimento e buracos | `ace_rota_pedestre` | Rota de pedestre acessível |
| `inf_calcada` | Calçada | `ace_rampa` | Rampa de acesso |
| `inf_drenagem` | Drenagem e alagamento | `ace_piso_tatil` | Piso tátil |
| `inf_iluminacao_publica` | Iluminação pública | `ace_transporte` | Transporte acessível |
| `inf_rede_eletrica` | Rede elétrica | `ace_edificacao_publica` | Edificação pública acessível |
| `inf_rede_agua_esgoto` | Rede de água e esgoto | `ace_vaga_reservada` | Vaga reservada |
| `inf_estrutura_publica` | Estrutura pública (ponte, passarela, contenção) | `ace_comunicacao_sinalizacao` | Comunicação e sinalização acessíveis |
| `amb_descarte_irregular` | Descarte irregular de resíduos | `esp_ocupacao_calcada` | Ocupação de calçada |
| `amb_poluicao_hidrica` | Poluição de rios e córregos | `esp_obra_particular` | Obra particular em espaço público |
| `amb_poluicao_ar` | Poluição do ar e queimadas | `esp_construcao_irregular` | Construção irregular (alegação) |
| `amb_poluicao_sonora` | Poluição sonora | `esp_comercio_ambulante` | Comércio ambulante |
| `amb_arborizacao` | Arborização | `esp_praca_parque` | Praças e parques |
| `amb_area_verde` | Áreas verdes e de preservação | `esp_veiculo_abandonado` | Veículo abandonado |
| `amb_fauna_zoonoses` | Fauna, vetores e zoonoses | `esp_pichacao_publicidade` | Pichação e publicidade irregular |
| `seg_percepcao_inseguranca` | Percepção de insegurança | `esp_eventos_perturbacao` | Eventos e perturbação na via |
| `seg_ocorrencias_recorrentes` | Ocorrências recorrentes (alegação) | `seg_incendio` | Incêndio ou risco de incêndio |
| `seg_imovel_abandonado` | Imóvel abandonado | `seg_vandalismo` | Vandalismo |
| `seg_risco_desastre` | Risco de desastre | | |

### Demais códigos

| Grupo | Código → rótulo |
|---|---|
| Triagem | `classificado` → Classificado · `informacao_insuficiente` → Informação insuficiente · `fora_escopo` → Fora do escopo |
| Natureza | `problema_existente` → Problema existente (manutenção ou reparo; com `requer_obra_adequacao`: obra de adequação) · `necessidade_infraestrutura` → Necessidade de infraestrutura (obra ou serviço novo) |
| Nível | `baixa` → Baixa · `media` → Média · `alta` → Alta · `critica` → Crítica |
| Origem | `relatado` → relatado · `inferido` → inferido · `verificado` → verificado · `ausente` → não informado |
| Confiança | `alta` → alta · `media` → média · `baixa` → baixa |
| Fatores | `risco_integridade_fisica` → Risco à integridade física · `abrangencia` → Abrangência · `vulnerabilidade_afetados` → Vulnerabilidade dos afetados · `impacto_servico_essencial` → Impacto em serviço essencial · `persistencia` → Persistência · `risco_agravamento` → Risco de agravamento |
| Regras de exceção | `ex01_risco_iminente` → Risco imediato relatado · `ex02_risco_fisico_grave_relatado` → Dano ou risco físico grave relatado · `ex03_risco_com_vulnerabilidade` → Risco envolvendo grupo vulnerável · `ex04_teto_necessidade_infraestrutura` → Limite para necessidades de infraestrutura · `ex05_informacao_insuficiente` → Informação insuficiente (provisória) · `ex06_falha_controle_trafego` → Semáforo inoperante em via de grande circulação · `ex07_barreira_acesso_servico_essencial` → Grupo vulnerável impedido de acessar serviço essencial |
| Desempate | `rd01_acessibilidade_explicita` → Barreira de acessibilidade explícita · `rd02_risco_estrutural_ou_desastre` → Estrutura construída × risco natural · `rd03_causa_acionavel` → Causa a corrigir · `rd04_foco_do_relator` → Ênfase do relator |
| Pendências | `descricao_insuficiente` → Descrição insuficiente · `localizacao_ausente` → Localização não informada · `localizacao_imprecisa` → Localização imprecisa · `data_ausente` → Data não informada · `complementar_dados_prioridade` → Complementar dados de prioridade · `classificacao_ambigua` → Classificação ambígua · `verificar_alegacao` → Verificar alegação · `revisao_humana_recomendada` → Revisão humana recomendada |
| Serviços de emergência | `samu_192` → SAMU (192) · `bombeiros_193` → Corpo de Bombeiros (193) · `policia_190` → Polícia Militar (190) · `defesa_civil_199` → Defesa Civil (199) · `emergencia_concessionaria_energia` → Emergência da distribuidora de energia · `emergencia_concessionaria_saneamento` → Emergência da prestadora de água e esgoto |
| Canal | `app` → Aplicativo · `web` → Site · `whatsapp` → WhatsApp · `telefone` → Telefone · `email` → E-mail · `presencial` → Presencial · `rede_social` → Rede social · `outro` → Outro · `nao_informado` → Não informado |
| Dados pessoais | `nome_pessoa` → nomes · `cpf` → CPF · `documento_identificacao` → documentos · `telefone` → telefones · `email` → e-mails · `placa_veiculo` → placas · `endereco_residencial` → número de residência · `dado_sensivel` → dados sensíveis · `empresa_em_alegacao` → empresas citadas em alegação |

**Órgãos.** Use a coluna "Função" da seção 12 de `categorias.md` como rótulo (ex.: `org_obras_vias` → "Obras e manutenção de vias, calçadas e estruturas públicas"). Em tabelas estreitas, encurte para o essencial ("Obras e vias").

**Exceção na versão pública (risco de identificação indireta).** Quando o relato tem `texto_relato_publicavel = false`, o rótulo de `org_acessibilidade_inclusao` é **"Acessibilidade e inclusão"**, e não "Direitos da pessoa com deficiência e acessibilidade". O rótulo completo, ao lado de um relato com pessoa identificável, indica o tipo de condição que foi mascarada. O código no JSON não muda.

## 6. Verificação do relatório

Antes de salvar:

- [ ] Cabeçalho de visibilidade correto. Na versão pública não há texto original, protocolo nem hash.
- [ ] Nenhum dado pessoal aparece fora de marcadores, nem em citações, títulos ou tabelas.
- [ ] Toda citação é trecho literal do texto mascarado da mesma visibilidade.
- [ ] Na versão pública, relatos com `texto_relato_publicavel = false` usam o rótulo "Acessibilidade e inclusão" para `org_acessibilidade_inclusao` e aparecem só pelo resumo anonimizado: sem texto do relato, sem citação literal, sem menção à moradia da pessoa e sem a característica sensível, nem no plural.
- [ ] Fatores ausentes aparecem como "— (não informado)", não como 0.
- [ ] Os números do relatório (pontuação, contagens, percentuais) batem com o JSON.
- [ ] O alerta de emergência, se houver, é o primeiro bloco após o cabeçalho.
- [ ] Alegações estão em linguagem de alegação e marcadas como pendentes de verificação.
- [ ] A expressão "avaliação de risco" não aparece; o aviso "Sobre esta análise" está presente.

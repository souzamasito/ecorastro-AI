# Proposta de calibração da matriz de prioridade (para a versão 1.1.0)

Situação: **aprovada e aplicada na matriz 1.1.0** (complemento da Etapa 6, skill 0.3.0). O texto abaixo é a proposta como foi apresentada; as decisões e os ajustes estão na seção 8.

Situação original: proposta, ainda não aplicada. A matriz em uso era a `1.0.0`; pesos, faixas e regras não mudaram na Etapa 6.
Origem: avaliações das iterações 1 e 2 (Etapas 5 e 6), lote `lote-csv-misto` e caso `dado-sensivel-terceiro`.

## 1. Resumo

Os três casos apontados na Etapa 5 (escola sem rampa, vazamento de esgoto e semáforos apagados) ficaram abaixo do que uma equipe de triagem esperaria. A causa **não está nos pesos**:

- **Esgoto:** faltam âncoras. A matriz não diz como pontuar risco sanitário nem a falha do próprio serviço essencial.
- **Semáforo e escola:** são situações que a soma ponderada trata mal, o mesmo tipo de problema que as regras de exceção já resolvem para outros casos.

A proposta é ajustar **âncoras** e acrescentar **duas regras de exceção**, mantendo os pesos 30/20/15/15/10/10 e as faixas. Em simulação sobre as 32 ocorrências das duas iterações, as regras novas mudam o nível só nos 3 casos-alvo.

## 2. Por que mudar os pesos não resolve

A pontuação é `soma(nota × peso) / 3`, e o nível `alta` começa em 55, ou seja, soma ≥ 165.

No semáforo apagado em cruzamento de avenida, só dois fatores têm base no relato: risco físico 2 e abrangência 2. Os outros ficam ausentes ou com nota zero. A soma é `2 × (peso_risco + peso_abrangência)`. Para chegar a 165, esses dois pesos precisariam somar pelo menos 83 dos 100, o que tornaria os outros quatro fatores praticamente irrelevantes para todos os relatos.

O mesmo vale para a escola: ela já tem os 6 fatores avaliados (52 pontos). Subir o peso que a favorece (vulnerabilidade ou serviço essencial) rebaixaria outros casos, como o buraco com acidente, que hoje depende do peso do risco físico.

Conclusão: mudar os pesos teria efeito em toda a fila para corrigir três casos específicos. Âncoras e regras de exceção são cirúrgicas e auditáveis, já que cada uma aparece em `regras_aplicadas`.

## 3. Diagnóstico por caso

As notas abaixo foram dadas nas execuções; os números vêm de `calcular_prioridade.py`.

### 3.1 Vazamento de esgoto (P-1006: "Tem esgoto vazando na Rua Bahia há 2 semanas, o cheiro está insuportável")

| Fator | 0.1.0 (iter. 1) | Leitura proposta |
|---|---|---|
| risco_integridade_fisica | 1 inferido | **2**: exposição contínua a esgoto na via é risco sanitário plausível (âncora A1) |
| abrangencia | 1 inferido | 1 |
| vulnerabilidade_afetados | ausente | ausente |
| impacto_servico_essencial | **ausente** | **2**: o próprio serviço de esgoto está falhando no trecho (âncora A2) |
| persistencia | 1 relatado | 1 ("há 2 semanas" fica no limite entre 1 e 2) |
| risco_agravamento | 2 inferido | 2 |
| **Resultado** | **baixa 27** (iteração 2: média 32) | **média 47**, com teto alta 62 |

O problema é a interpretação, e por isso a nota também variou entre execuções (27 → 32). Hoje as âncoras de risco físico só falam de lesão. Esgoto aparece na lista de serviços essenciais, mas a matriz não diz que um vazamento é uma falha desse serviço.

### 3.2 Semáforos apagados (P-1001 e P-1008, Av. Paraná × Rua 3)

| Fator | Nota | Comentário |
|---|---|---|
| risco_integridade_fisica | 2 (P-1008 relatado: "quase vi uma batida") | Quase-acidente não é dano ocorrido; nota 2 está correta pelas âncoras |
| abrangencia | 2 inferido | Cruzamento de avenida (âncora 2) |
| demais | ausente ou 0 | Persistência 0 ("desde cedo") |
| **Resultado** | **média 33**, iguais nas duas iterações | |

Aqui não há erro de interpretação: a nota é estável e correta pelas âncoras. A matriz é que não reconhece que perder o controle de tráfego num cruzamento de grande circulação expõe muita gente a colisão grave **a cada minuto**, mesmo sem acidente. Órgãos de trânsito costumam tratar semáforo apagado como atendimento no mesmo dia. **Regra B1.**

### 3.3 Escola sem rampa (P-1011: "as mães com carrinho de bebê e um aluno [DADO_SENSIVEL] não conseguem entrar")

| Fator | Nota |
|---|---|
| risco_integridade_fisica | 1 inferido |
| abrangencia | 2 inferido |
| vulnerabilidade_afetados | 3 relatado |
| impacto_servico_essencial | 2 relatado ("não conseguem entrar": a âncora 2 diz "interrompe para parte da população") |
| persistencia | 1 inferido |
| risco_agravamento | 0 inferido |
| **Resultado** | **média 52**, completude 100%, iguais nas duas iterações; `ex04` limita a alta, mas não chega a atuar |

Um grupo vulnerável relatado está impedido de usar um serviço essencial, e mesmo assim o caso fica em média, porque o risco físico é baixo. As exceções atuais só elevam o mínimo quando há risco físico (`ex02`, `ex03`). **Regra B2.**

Há também uma **questão de classificação**: a falta de rampa numa escola pública descumpre uma exigência de acessibilidade obrigatória. Pode ser lida como `problema_existente` (falha do equipamento) e não como `necessidade_infraestrutura` (obra nova). No resultado, isso não muda nada aqui (52 nas duas leituras), mas muda o fluxo do encaminhamento (Decisão 4).

### 3.4 Achado adicional: crítica no limite, sem risco imediato (caso `dado-sensivel-terceiro`)

Mesmo relato, mesma matriz: a 0.1.0 deu **alta 70** e a 0.2.0 deu **crítica 75**. A diferença foi uma nota inferida: impacto no "acesso físico à moradia" = 2 ("caiu tentando sair de casa"). A seção 10 de `priorizacao.md` já lista "muitos casos `critica` sem `ex01`" como sinal de calibração. A âncora A3 reduz essa variação.

## 4. Propostas

### A. Âncoras (não mudam pesos nem faixas)

| Código | Fator | Texto proposto |
|---|---|---|
| A1 | `risco_integridade_fisica` | Acrescentar o **risco à saúde** às âncoras. Nota 2: exposição contínua a esgoto, água contaminada, lixo em decomposição ou foco de vetor relatado. Nota 3: contaminação de água de consumo, surto relatado ou animal peçonhento em área de circulação. |
| A2 | `impacto_servico_essencial` | Quando a ocorrência **é** a falha de um serviço essencial (esgoto vazando, coleta que não passa, falta de água, ônibus que não circula), o fator mede essa própria falha: parcial ou localizada = 2; total no local, sem alternativa = 3. |
| A3 | `impacto_servico_essencial` | O "acesso físico a moradia ou trabalho" só pontua quando o relato diz que o acesso está **bloqueado ou impedido**. Dificuldade (como queda ao sair) vale 1. |
| A4 | `abrangencia` | Para serviços prestados por rua (coleta, iluminação de trecho), "não passa na rua" = 2 (rua inteira). Isso reduz a variação vista na coleta de lixo (38 → 48 entre execuções). |

### B. Novas regras de exceção

| Código | Condição | Efeito | Posição na ordem |
|---|---|---|---|
| `ex06_falha_controle_trafego` | Subcategoria `mob_semaforo` (ou sinalização de controle inoperante em cruzamento), `abrangencia` ≥ 2 e `risco_integridade_fisica` ≥ 2 | Nível mínimo `alta` | Junto com `ex02`/`ex03` (mínimos) |
| `ex07_barreira_acesso_servico_essencial` | `vulnerabilidade_afetados` = 3 relatado **e** `impacto_servico_essencial` ≥ 2 relatado | Nível mínimo `alta` | Junto com os mínimos; `ex04` continua limitando necessidades a `alta` |

### C. Pesos e faixas

Sem mudança (seção 2).

## 5. Impacto simulado

As regras B foram aplicadas aos fatores **já registrados** das 32 ocorrências das iterações 1 e 2:

| Ocorrência | Hoje | Com B1/B2 |
|---|---|---|
| P-1001 semáforo (iter. 1 e 2) | média 33 | **alta** (`ex06`) |
| P-1008 semáforo (iter. 1 e 2) | média 33 | **alta** (`ex06`) |
| P-1011 escola sem rampa (iter. 1 e 2) | média 52 | **alta** (`ex07`, no limite do `ex04`) |
| As outras 26 | sem alteração | sem alteração |

As âncoras A dependem de nova avaliação dos fatores e não podem ser simuladas sobre as notas antigas. Simulação manual do esgoto: baixa 27 → **média 47** (teto alta 62). Simulação do caso `dado-sensivel-terceiro` com A3: crítica 75 → **alta 70**, o que remove o caso "crítico sem `ex01`".

Ponto a observar: o esgoto continua em média, e não em alta como na comparação de base. Pela matriz, alta exige risco físico ou vulnerabilidade relatados; um vazamento sem público vulnerável nem risco agudo é atendimento programado. Se a equipe entender que todo vazamento de esgoto em via pública é alta, a solução seria uma regra própria, não um peso. Isso fica para a Decisão 3.

## 6. Como aplicar, se aprovado

1. Publicar a matriz `1.1.0` em `priorizacao.md`: âncoras A1 a A4, regras `ex06`/`ex07`, a ordem de aplicação e um exemplo calculado para cada regra.
2. Atualizar `calcular_prioridade.py` com `ex06` e `ex07`, `VERSAO_MATRIZ = "1.1.0"` e testes para cada regra, inclusive a interação com `ex04`.
3. Atualizar o enum de regras no schema. É uma mudança aditiva, mas o schema ficaria `1.2.0`.
4. Rodar de novo `lote-csv-misto`, `dado-sensivel-terceiro`, `buraco-acidente-simples` e `calcada-cadeirante-ambigua`, conferindo que nenhum outro nível mudou sem motivo.
5. Registrar no `CHANGELOG.md`.

## 7. Decisões necessárias

1. Aprovar, ajustar ou recusar as âncoras A1 a A4.
2. Aprovar, ajustar ou recusar as regras `ex06` e `ex07`. Para `ex06`: limitar a semáforos ou incluir outra sinalização de controle?
3. Esgoto: aceitar média como resultado adequado ou criar uma regra para falha de saneamento em via pública?
4. Escola sem rampa (falta de acessibilidade obrigatória num equipamento público): continua `necessidade_infraestrutura` ou passa a `problema_existente`?
5. Versão: as regras novas valem como `1.1.0` (aditivo) ou `2.0.0`? A seção 10 de `priorizacao.md` só define versão maior para mudança de peso ou faixa.

## 8. Decisões tomadas (complemento da Etapa 6)

| Decisão | Resultado | Onde está |
|---|---|---|
| 1. Âncoras A1 a A4 | Aprovadas, com pesos preservados. Acrescentado: separação explícita entre **risco potencial** (até 2) e **dano ocorrido relatado** (3), e regra de que A3 não reduz barreiras de acessibilidade a serviço essencial | `priorizacao.md` 2.1 a 2.4 |
| 2. Regras `ex06` e `ex07` | Aprovadas, só com evidência suficiente. `ex06`: limitada a semáforos (`mob_semaforo`); é uma afirmação da análise, conferida pelo script, que exige abrangência e risco ≥ 2 com evidência literal. `ex07`: vulnerabilidade 3 e serviço ≥ 2, os dois `relatado` | `priorizacao.md` 6 e 6.3; `calcular_prioridade.py` |
| 3. Esgoto | Problema existente, prioridade média pelos novos critérios; sobe só com evidência (`ex02`, `ex03`). Sem regra própria | `priorizacao.md` 9.5; `categorias.md` 7 |
| 4. Escola sem rampa | Problema existente de acessibilidade, com obra de adequação (campo novo `requer_obra_adequacao`) | `categorias.md` 5.1; `priorizacao.md` 9.7 |
| 5. Versão | Matriz 1.1.0 e contrato JSON 1.2.0, com compatibilidade documentada | `docs/compatibilidade-versoes.md` |

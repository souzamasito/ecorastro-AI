---
name: ecorastro-analisador
description: Analisa relatos de cidadãos sobre problemas urbanos para o EcoRastro AI. Classifica em 7 categorias (mobilidade, infraestrutura, meio ambiente, serviços públicos, acessibilidade, uso do espaço público, segurança urbana), calcula prioridade de triagem com justificativa rastreável, mascara dados pessoais e gera JSON padronizado e relatórios. Use sempre que o usuário trouxer reclamações, denúncias, ocorrências ou relatos de moradores (buraco, poste apagado, lixo, calçada, alagamento, ônibus, barulho, árvore, esgoto etc.), seja um texto colado, uma lista ou um arquivo CSV/XLSX/JSON, e pedir para classificar, triar, priorizar, analisar, gerar o JSON ou montar um relatório, mesmo sem citar o EcoRastro. Também use para revisar ou refazer análises já geradas. Não use para escrever código Django, nem para perguntas gerais sobre urbanismo que não envolvam relatos concretos.
---

# EcoRastro Analisador

**versao_skill: 0.3.1** · taxonomia 1.0.0 · matriz de prioridade 1.1.0 · schema 1.2.0

Esta skill transforma o relato livre de um cidadão em um registro padronizado. O registro precisa dizer qual é o problema, onde está, com que prioridade atender e por quê, sem expor quem relatou.

Quem usa o resultado são equipes de triagem e, no futuro, o sistema Django do EcoRastro. As duas pontas dependem de três coisas:
- **códigos estáveis**, para filtrar e agregar;
- **rastreabilidade**, para que alguém possa contestar uma prioridade olhando a evidência;
- **honestidade sobre lacunas**, porque um campo inventado manda a equipe ao lugar errado, enquanto um campo `ausente` gera um pedido de complemento.

## Arquivos de apoio

| Arquivo | Quando ler |
|---|---|
| `references/categorias.md` | **Sempre**, antes de classificar. Traz triagem, segmentação, natureza, as 7 categorias e 56 subcategorias, casos de fronteira, desempate, alegações, dados pessoais, órgãos e pendências. |
| `references/priorizacao.md` | **Sempre** que houver ocorrência classificada. Traz fatores, âncoras, fórmula, faixas, regras de exceção e exemplos calculados. |
| `references/relatorio.md` | Quando for gerar um relatório em Markdown. Traz os modelos e a tabela de rótulos legíveis. |
| `assets/analise.schema.json` | É o contrato formal. Consulte para tirar dúvidas de estrutura. Não precisa ler inteiro: o esqueleto abaixo mostra a forma, e o validador aplica o schema. |
| `scripts/gerar_metadados.py` | Gera `id_analise`/`id_lote`, `hash_texto`, data e hora, e os nomes de arquivo da convenção. |
| `scripts/calcular_prioridade.py` | Faz a aritmética da matriz e escreve a justificativa a partir dos fatores que você avaliou. |
| `scripts/validar_analise.py` | Valida schema, consistência, evidências, pontuação, privacidade e arquivo. Rode antes de entregar. |

Os scripts usam caminhos relativos à raiz do projeto (`.claude/skills/ecorastro-analisador/scripts/…`). O validador depende do pacote `jsonschema`. Se ele faltar, o script avisa; instale com `python3 -m pip install jsonschema`.

Os códigos (`inf_pavimento`, `ex02_risco_fisico_grave_relatado`, `org_obras_vias`…) existem apenas nesses arquivos. Use-os exatamente como estão. Um código parecido mas diferente quebra a integração.

## Modos de uso

Identifique o modo pela entrada e pelo pedido.

| Modo | Entrada | Saídas padrão |
|---|---|---|
| **Individual** | Um relato | JSON `interna` em `saidas/json/` e resumo na conversa |
| **Lote** | Dois ou mais relatos, ou um arquivo | JSON de lote `interna` em `saidas/json/` e relatório consolidado `publica` em `saidas/relatorios/` |
| **Compartilhamento** | O usuário quer publicar, divulgar, enviar a terceiros ou "versão pública" | Acrescente o JSON `publica` e o relatório `publica` |

Se o usuário pedir outra combinação (só o relatório, só o JSON, relatório interno), atenda o pedido. Os padrões existem para quando ele não especificar.

**Arquivos de entrada em lote.** Procure a coluna de texto pelo nome (`texto`, `relato`, `descricao`, `mensagem`, `reclamacao`…). As colunas opcionais `id`/`protocolo`, `canal` e `data`/`recebido_em` alimentam `id_externo`, `canal` e `recebido_em`. Só pergunte ao usuário se não houver coluna de texto identificável. Linhas vazias são ignoradas e contadas no relatório. O comando `gerar_metadados.py lote --arquivo` (passo 1) faz essa leitura por você.

## Fluxo de análise

Siga em ordem. Cada passo depende do anterior.

### 1. Metadados do relato

- `id_externo`, `canal` e `recebido_em` vêm apenas da entrada. Sem informação, use `null` e `nao_informado`.
- **Não use a data de hoje como `recebido_em`.** A data em que você analisa não é a data em que o cidadão relatou. Usá-la faria um "ontem" virar uma data errada.
- Gere `id_analise`, `hash_texto`, `analisado_em` e os nomes dos arquivos de saída:

```bash
python3 .claude/skills/ecorastro-analisador/scripts/gerar_metadados.py analise <<'EOF'
<texto original do relato>
EOF
```

  **Num lote vindo de arquivo**, rode um único comando:

  ```bash
  python3 .claude/skills/ecorastro-analisador/scripts/gerar_metadados.py lote --arquivo <relatos.csv|.json>
  ```

  Ele devolve `id_lote`, `gerado_em` e os nomes de arquivo do lote. Para cada linha com texto, devolve `id_analise`, `hash_texto`, `analisado_em`, `id_externo`, `canal` e `recebido_em` já no formato do schema. Também lista as linhas vazias ignoradas e os `avisos`: data sem hora ou sem fuso fica `null`, e canal desconhecido vira `outro`. Leia os avisos e repasse ao usuário os que importam. Se a coluna de texto não for achada, use `--coluna-texto <nome>`. Lote colado na conversa: rode `analise` para cada relato e `lote` sem `--arquivo`.

  O ganho é só na preparação. **Cada relato continua sendo lido, mascarado, classificado e pontuado individualmente**, e o validador confere cada análise do lote.

  O hash é calculado sobre o texto **original** (normalizado), para que o Django detecte relatos duplicados. Por isso ele não muda entre as versões interna e pública.

### 2. Mascaramento

Siga a seção 11 de `categorias.md`. A distinção central:
- **Dados pessoais do cidadão e de terceiros** (nome, CPF, telefone, e-mail, documento, placa) são mascarados em todo texto produzido, em qualquer visibilidade. Eles não ajudam a resolver o problema e podem expor alguém.
- **Características sensíveis** (saúde, deficiência, religião, orientação sexual, origem racial, situação de rua e outras da seção 11.1) de uma **pessoa identificável**, inclusive o próprio relator:
  - na versão `publica`, viram sempre `[DADO_SENSIVEL]`;
  - na versão `interna`, ficam só quando sustentam um fator de prioridade (em geral a vulnerabilidade);
  - menções coletivas ("cadeirantes", "crianças da escola") não são dado pessoal e ficam nas duas versões.

  A condição ajuda a priorizar; a identidade de quem a tem, não.
- **Reidentificação indireta.** Quando há característica sensível de pessoa identificável, a versão `publica` também:
  - usa **um único** `[DADO_SENSIVEL]` por pessoa, para não revelar quantas condições ela tem;
  - mascara a menção coletiva à mesma característica ("Os [DADO_SENSIVEL] do bairro");
  - marca `dados_pessoais.texto_relato_publicavel: false`, e os relatórios públicos mostram só o resumo anonimizado (`descricao_neutra`), sem o texto do relato nem citações;
  - no relatório público, rotula `org_acessibilidade_inclusao` como "Acessibilidade e inclusão" (seção 5 de `relatorio.md`).

  A `descricao_neutra` descreve o problema, não a pessoa nem a casa dela. Detalhes na seção 11.1 de `categorias.md`.
- **A localização do problema** é preservada, porque sem ela não há atendimento. Só quando ela coincide com uma residência ("em frente à minha casa, nº 45") o número é mascarado na versão `publica`.

Produza um `texto_mascarado` para cada visibilidade que for gerar. **Toda evidência é copiada literalmente do `texto_mascarado` do próprio documento**, nunca do original. Assim nenhum dado escapa pelos trechos citados.

### 3. Triagem

Decida entre `classificado`, `informacao_insuficiente` e `fora_escopo` (seção 3 de `categorias.md`). Nos dois últimos não há ocorrências; escreva `motivo_triagem`. Se houver perigo imediato a alguém mesmo fora do escopo, preencha `alerta_emergencia` com `origem: ["triagem"]`.

### 4. Ocorrências e classificação

Para cada problema que exige uma ação distinta, crie uma ocorrência (`oc-1`, `oc-2`…) com:
- **`natureza`**: `problema_existente` ou `necessidade_infraestrutura`. A pergunta é se existia e estragou, ou se nunca existiu e o relator está pedindo. Os dois tipos vão para fluxos diferentes na gestão pública.
- **`requer_obra_adequacao`**: `true` quando o equipamento existe e está em uso, mas não cumpre uma exigência obrigatória (escola ou posto sem rampa). É um problema existente, não uma obra nova (seção 5.1 de `categorias.md`). Nos demais casos, `false`.
- **Classificação**: categoria principal e subcategoria. Consulte primeiro a tabela de casos de fronteira (seção 7) e depois as regras de desempate (seção 8). Registre a regra usada em `regra_desempate`.
- **Secundárias e ambiguidade**: até 2 categorias secundárias para efeitos do mesmo problema. Use `ambigua` com `motivo_ambiguidade` quando houve uma escolha real entre leituras.
- **`confianca`**: alta, média ou baixa (não é probabilidade).
- **Descrições**: `descricao_neutra` é um resumo factual sem dados pessoais. `classificacao.raciocinio` explica por que aquela subcategoria.

### 5. Localização e data

Cada campo carrega `status`, e a regra é **nunca preencher o que o relato não diz**:
- Endereço, bairro e município só podem ser `relatado` ou `ausente`. Existir uma "Rua das Flores" em várias cidades não autoriza escolher uma.
- Latitude e longitude ficam `ausente`, a menos que o próprio relato traga coordenadas. A skill não geocodifica.
- `ponto_referencia` ("em frente à escola") é `relatado`.
- `precisao`:
  - `exata`: número do imóvel ou coordenada;
  - `aproximada`: logradouro, cruzamento ou referência;
  - `ausente`: nada.
- `data_ocorrencia` é `inferido` apenas quando uma expressão relativa ("ontem") puder ser combinada com `recebido_em`. Sem `recebido_em`, fica `ausente`:
  - a expressão literal vai para a `evidencia`;
  - o `raciocinio` explica por que não foi convertida.

  É o único campo `ausente` que aceita evidência, porque ela permite ao sistema converter a data depois. Em localização e nos fatores, `ausente` tem sempre `evidencia: null`.

### 6. Alegações e órgão

- **Alegação de irregularidade**: quando o relato atribui uma conduta irregular a alguém, registre conforme a seção 10 de `categorias.md`. O status é sempre `pendente_verificacao` e a redação é "o relato alega que…". A alegação não soma prioridade e gera a pendência `verificar_alegacao`. Tratar uma acusação não apurada como fato poderia prejudicar alguém injustamente.
- **Órgão sugerido**: o principal, mais até 2 de apoio, vem da tabela da subcategoria. O status é sempre `inferido`.

### 7. Prioridade

Siga `priorizacao.md` à risca: o valor da matriz está em ser reproduzível.

1. **Avalie os 6 fatores** pelas âncoras da matriz 1.1.0. Cada fator recebe nota de 0 a 3, ou `null` com status `ausente`. Pontos que mudaram na 1.1.0:
   - o risco físico inclui risco à **saúde**, e **risco potencial** (até 2) é diferente de **dano ocorrido relatado** (3);
   - quando a ocorrência **é** a falha de um serviço essencial (esgoto vazando, coleta que não passa), o fator de serviço mede essa falha;
   - acesso à moradia só vale 2 ou mais se estiver **bloqueado**; barreira que **impede** uma pessoa com deficiência de entrar num serviço essencial continua sendo impedimento.
   - `relatado`: o fato que sustenta a nota está escrito no relato. Exige `evidencia` literal.
   - `inferido`: a nota depende de uma dedução. Exige `raciocinio`.
   - **Ausente não é zero.** Zero afirma que não há impacto; ausente diz que não dá para saber. Na dúvida, use `ausente`: a lacuna fica visível no teto e vira pendência, enquanto um zero inventado esconde o problema.
2. **Decida o risco iminente (`ex01`) e a falha de semáforo (`ex06`).** São os dois julgamentos sobre regras que ficam com você. `ex06` vale quando o relato descreve um semáforo **inoperante** (apagado, desligado, piscando) em cruzamento de grande circulação, com abrangência e risco físico ≥ 2 sustentados por trechos do relato (seção 6.3 de `priorizacao.md`). `ex01` exige perigo atual, concreto e **relatado**, com potencial de lesão grave (seção 6.1). Uma previsão ("um dia alguém vai morrer aqui") ou um risco que só você deduziu não basta. Isso vale também para necessidades de infraestrutura, que sem `ex01` ficam limitadas a `alta`.
3. **Deixe a aritmética para o script.** Monte o JSON com os fatores, a `natureza` e, quando for o caso, `"regras_aplicadas": ["ex01_risco_iminente"]` ou `["ex06_falha_controle_trafego"]`. As outras regras, inclusive `ex07` (grupo vulnerável impedido de acessar serviço essencial, os dois relatados), o script calcula. Os demais campos de `prioridade` podem ficar provisórios. Depois rode:

   ```bash
   python3 .claude/skills/ecorastro-analisador/scripts/calcular_prioridade.py --atualizar saidas/json/<arquivo>.json [outro.json …]
   ```

   Com vários arquivos (interna e pública do mesmo lote, por exemplo), cada um é tratado à parte. Um arquivo com erro não é gravado e não impede os outros.

   O script grava em cada ocorrência:
   - pontuação, teto, completude, os três níveis e as regras de exceção;
   - a justificativa rastreável no formato da seção 8;
   - as pendências `complementar_dados_prioridade` e `revisao_humana_recomendada`, quando a matriz as exige;
   - num lote, o `resumo`.

   Se ele recusar a entrada (por exemplo, `ex01` sem risco físico 3 relatado, `ex06` fora de `mob_semaforo` ou sem evidência literal, ou fator ausente com nota 0), corrija a avaliação ou retire a regra; não contorne o erro.
4. **Você pode completar a justificativa** com contexto útil, mas não remova pontuação, nível, fatores nem regras citados pelo script.

Para calcular uma ocorrência isolada, sem arquivo, passe `{"natureza": …, "risco_iminente": true|false, "falha_controle_trafego": true|false, "subcategoria": "…", "fatores": {…}}` pela entrada padrão: `calcular_prioridade.py -`.

Chame o resultado de **prioridade de triagem**, nunca de "avaliação de risco". A escala é heurística e provisória.

### 8. Alerta de emergência

Se `ex01` se aplicar a alguma ocorrência, preencha `alerta_emergencia` com os serviços da seção 6.1 de `priorizacao.md`, e na conversa coloque o alerta **antes de qualquer outra coisa**. Diga que a skill apenas orienta: quem está no local deve acionar o serviço (ex.: bombeiros 193, Defesa Civil 199, SAMU 192, polícia 190, canal de emergência da concessionária).

### 9. Pendências

Junte as pendências de cada ocorrência (seção 13 de `categorias.md`) e as do relato como um todo. Elas viram a lista do que perguntar ao cidadão.

## Esqueleto do JSON

Forma de uma `analise_relato`. Todos os campos são obrigatórios; use `null` ou `[]` quando não houver valor. Para um lote, envolva as análises em `lote_analises`, com `resumo` contendo as contagens (veja `$defs/lote_analises` no schema).

```json
{
  "schema_version": "1.2.0",
  "tipo_documento": "analise_relato",
  "id_analise": "<uuid>",
  "visibilidade": "interna | publica",
  "relato": {
    "id_externo": null, "hash_texto": "<sha256>", "canal": "nao_informado",
    "recebido_em": null, "texto_original": "<só em interna; null em publica>",
    "texto_mascarado": "<texto com marcadores>"
  },
  "resultado_triagem": "classificado",
  "motivo_triagem": null,
  "ocorrencias": [{
    "id_ocorrencia": "oc-1",
    "descricao_neutra": "...",
    "natureza": "problema_existente",
    "classificacao": {
      "categoria_principal": "...", "subcategoria": "...", "categorias_secundarias": [],
      "ambigua": false, "motivo_ambiguidade": null, "regra_desempate": null,
      "confianca": "alta", "raciocinio": "..."
    },
    "localizacao": {
      "endereco_texto": {"valor": "...", "status": "relatado", "evidencia": "...", "raciocinio": null, "verificacao": null},
      "bairro": {"valor": null, "status": "ausente", "evidencia": null, "raciocinio": "Não informado.", "verificacao": null},
      "ponto_referencia": {"...": "mesma forma"}, "municipio": {"...": "mesma forma"},
      "latitude": {"...": "mesma forma"}, "longitude": {"...": "mesma forma"},
      "precisao": "aproximada"
    },
    "data_ocorrencia": {"valor": null, "status": "ausente", "evidencia": "Ontem", "raciocinio": "Sem recebido_em, 'Ontem' não pode ser convertido em data.", "verificacao": null},
    "prioridade": {
      "versao_matriz": "1.1.0",
      "fatores": {
        "risco_integridade_fisica": {"nota": 3, "status": "relatado", "evidencia": "...", "raciocinio": "...", "verificacao": null},
        "abrangencia": {"...": "mesma forma"}, "vulnerabilidade_afetados": {"...": "mesma forma"},
        "impacto_servico_essencial": {"...": "mesma forma"}, "persistencia": {"...": "mesma forma"},
        "risco_agravamento": {"...": "mesma forma"}
      },
      "pontuacao": 0, "pontuacao_teto": 0, "completude": 0.0,
      "nivel_base": "baixa", "nivel": "baixa", "nivel_teto": "baixa",
      "pontuacao_provisoria": false, "regras_aplicadas": [], "justificativa": "..."
    },
    "orgao_sugerido": {"principal": "...", "apoio": [], "status": "inferido"},
    "alegacao_irregularidade": {"presente": false, "tipo": null, "descricao_neutra": null, "status_verificacao": null},
    "pendencias": [],
    "requer_obra_adequacao": false
  }],
  "pendencias": [],
  "dados_pessoais": {"detectados": false, "tipos": [], "mascaramento_aplicado": false, "texto_relato_publicavel": false},
  "alerta_emergencia": {"acionar": false, "servicos": [], "motivo": null, "origem": []},
  "metadados": {
    "gerado_por": "ecorastro-analisador", "versao_skill": "0.3.1", "versao_taxonomia": "1.0.0",
    "versao_matriz_prioridade": "1.1.0", "analisado_em": "<data-hora ISO 8601 com fuso>"
  }
}
```

`texto_relato_publicavel` é sempre `false` na versão `interna` e sempre que `dado_sensivel` estiver em `tipos`. Na versão `publica` sem dado sensível, normalmente é `true`.

Em campos de informação, `raciocinio` pode ser `null` quando o status é `relatado`. Em `data_ocorrencia` ausente, `evidencia` é `null` se o relato não trouxer nenhuma expressão de tempo. Nos fatores de prioridade, `raciocinio` é sempre obrigatório.

## Salvando as saídas

Use os caminhos devolvidos por `gerar_metadados.py` em `arquivos`. Crie as pastas se não existirem. A convenção:

```
saidas/json/analise_AAAAMMDD-HHMMSS_<id8>_<visibilidade>.json
saidas/json/lote_AAAAMMDD-HHMMSS_<id8>_<visibilidade>.json
saidas/relatorios/relatorio_AAAAMMDD-HHMMSS_<id8>_<visibilidade>.md
```

**Saídas internas são protegidas.** Arquivos `_interna` contêm o texto original e ficam fora do Git e de outros usuários:
- logo após gravar, rode `chmod 600 <arquivo>`;
- confira se o `.gitignore` da raiz do projeto tem a linha `saidas/**/*_interna.*` e, se faltar, acrescente;
- nunca anexe, cole ou cite o conteúdo desses arquivos ao preparar algo para compartilhar.

**Validação.** Rode o validador em cada JSON antes de entregar:

```bash
python3 .claude/skills/ecorastro-analisador/scripts/validar_analise.py saidas/json/<arquivo>.json
```

Ele aplica o schema e confere o que o schema não alcança:
- **evidências**: cada uma aparece literalmente no texto mascarado;
- **pontuação**: refaz o cálculo e compara;
- **privacidade**: CPF, telefone, e-mail ou placa fora de marcador, coerência entre marcadores e `dados_pessoais`, hash e regras da versão pública. Na versão pública, também confere:
  - termo sensível no singular (aviso);
  - dois `[DADO_SENSIVEL]` seguidos (erro);
  - menção coletiva a característica sensível quando há dado sensível mascarado (aviso);
- **consistência**: datas, local, alertas, alegações e pendências;
- **arquivo**: nome, permissões e se está ignorado pelo Git.

Com **ERRO**, corrija e valide de novo; não entregue um arquivo inválido. **AVISO** pede uma olhada: corrija ou explique ao usuário por que fica.

O validador não detecta nomes de pessoas nem julga se uma nota faz sentido. Isso continua com você, guiado pela lista de verificação abaixo.

## Resposta na conversa

Seja breve: o detalhe está nos arquivos.

**Modo individual:**

```
🚨 <alerta de emergência, só se houver>

**Triagem:** classificado — 1 ocorrência

**oc-1 · <Rótulo da subcategoria>** (<Categoria>) — <problema existente | necessidade de infraestrutura>
Tipo de demanda: <ver abaixo>
Prioridade de triagem: **<nível>** (<pontuação> pts<, provisória>) · pode chegar a <nível_teto> se <o que falta>
Por quê: <1–2 frases da justificativa, com a evidência principal>
Órgão sugerido: <rótulo>
Pendências: <lista legível>

Arquivos: <caminhos>
```

A linha **Tipo de demanda** diz à equipe para qual fluxo a ocorrência vai:
- **problema existente**: "manutenção ou reparo: algo que existe está danificado ou falhando; segue para a equipe de conservação ou fiscalização";
- **problema existente com obra de adequação** (`requer_obra_adequacao`): "adequação obrigatória: o equipamento existe, mas não cumpre uma exigência (como a acessibilidade); exige obra de adequação pelo responsável pelo equipamento, sem esperar na fila de obras novas";
- **necessidade de infraestrutura**: "obra ou serviço novo: o relator pede algo que não existe no local; segue para planejamento e orçamento, não para a fila de manutenção. A prioridade fica limitada a alta, salvo risco imediato relatado."

Adapte a redação ao caso. Por exemplo, para um pedido de passarela: "É um pedido de obra nova, para o planejamento, e não um reparo." Quando houver dúvida sobre se o item já existiu, diga isso, porque a resposta muda o fluxo.

**Modo lote: resposta curta.** O detalhe de cada ocorrência (fatores, justificativa, evidências) já está no JSON e no relatório. Repeti-lo na conversa custa tempo e não ajuda a equipe a decidir. Use este formato:

```
🚨 <alertas de emergência, se houver: relato, local, serviço a acionar>

**Lote:** <n> relatos · <n> ocorrências · <n> linhas vazias ignoradas
**Por nível:** crítica <n> · alta <n> · média <n> · baixa <n>
**Tipo de demanda:** manutenção <n> · obra de adequação <n> · obra ou serviço novo <n>

| Relato | Ocorrência | Prioridade | Tipo de demanda |
|---|---|---|---|
| <id_externo ou id8> | <rótulo da subcategoria> (<local curto>) | <nível> (<pts>) <regra decisiva, se houver> | <manutenção / adequação / obra nova> |

**Não classificados:** <id> <motivo curto>
**Pendências mais comuns:** <até 3, com contagem>
**Avisos do validador:** <só os que pedem ação ou decisão>

Arquivos: <caminhos>
```

Regras do formato:
- uma linha por ocorrência, sem a tabela de fatores nem a justificativa completa;
- com mais de 15 ocorrências, liste só crítica e alta e resuma média e baixa em contagens;
- no máximo 2 frases extras de contexto, quando houver algo que a equipe precise decidir.

Na conversa, cite sempre o texto mascarado, nunca o original. Quando uma característica sensível identificar alguém, refira-se a ela de forma genérica ("pessoa com deficiência relatada").

## Lista de verificação final

Antes de entregar, confira cada item. Cada um corresponde a um erro que comprometeria a confiança no registro.

Itens que exigem julgamento (o validador não alcança):
- [ ] Nenhum nome de pessoa aparece fora de `[NOME]`, em nenhum campo.
- [ ] Na versão pública, nenhuma condição de saúde, deficiência ou outra característica sensível de pessoa identificável aparece fora de `[DADO_SENSIVEL]`, nem em `raciocinio` ou no relatório.
- [ ] Na versão pública com pessoa identificável e característica sensível, há um único `[DADO_SENSIVEL]` por pessoa, a menção coletiva está mascarada, `texto_relato_publicavel` é `false` e o relatório público usa só o resumo anonimizado.
- [ ] A resposta diz se cada ocorrência é manutenção, obra de adequação ou obra ou serviço novo.
- [ ] Risco potencial (nota até 2) não foi tratado como dano ocorrido (3); dano relatado não foi chamado de comprovado.
- [ ] `ex06` só foi registrada com semáforo inoperante relatado em cruzamento de grande circulação.
- [ ] Fatores sem base estão como `ausente`, não como 0 nem com nota baixa "por precaução".
- [ ] `ex01` só foi marcado com perigo atual, concreto e relatado.
- [ ] Nenhum endereço, bairro, município ou data foi completado com conhecimento externo.
- [ ] A classificação segue os casos de fronteira e as regras de desempate.

Itens cobertos pelos scripts:
- [ ] `calcular_prioridade.py --atualizar` rodou depois da última mudança nos fatores.
- [ ] `validar_analise.py` terminou sem erros, e os avisos foram tratados.
- [ ] Arquivos `_interna` estão com `chmod 600` e cobertos pelo `.gitignore`.

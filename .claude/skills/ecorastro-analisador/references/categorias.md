# Taxonomia e regras de classificação — EcoRastro AI

**versao_taxonomia: 1.0.0**

Este arquivo define como transformar um relato de cidadão em uma ou mais ocorrências classificadas. Os códigos aqui são **identificadores estáveis**: o sistema Django vai armazená-los e filtrá-los, então um código publicado nunca muda de significado nem é reaproveitado. Se uma subcategoria deixar de fazer sentido, ela é marcada como obsoleta numa nova versão da taxonomia, não apagada.

Os rótulos legíveis (ex.: "Buraco ou falha no pavimento") servem para relatórios. O JSON guarda apenas os códigos.

## Sumário

1. [Princípios de evidência](#1-princípios-de-evidência)
2. [Fluxo de classificação](#2-fluxo-de-classificação)
3. [Resultado da triagem](#3-resultado-da-triagem)
4. [Segmentação em ocorrências](#4-segmentação-em-ocorrências)
5. [Natureza: problema existente × necessidade de infraestrutura](#5-natureza-problema-existente--necessidade-de-infraestrutura)
6. [As sete categorias e suas subcategorias](#6-as-sete-categorias-e-suas-subcategorias)
7. [Casos de fronteira](#7-casos-de-fronteira)
8. [Regras de desempate](#8-regras-de-desempate)
9. [Ambiguidade, categorias secundárias e confiança](#9-ambiguidade-categorias-secundárias-e-confiança)
10. [Alegações de irregularidade](#10-alegações-de-irregularidade)
11. [Dados pessoais e mascaramento](#11-dados-pessoais-e-mascaramento)
12. [Órgãos responsáveis genéricos](#12-órgãos-responsáveis-genéricos)
13. [Pendências](#13-pendências)

---

## 1. Princípios de evidência

Toda informação extraída do relato carrega um **status**. Isso permite que quem lê o resultado saiba o que o cidadão disse, o que a análise deduziu e o que alguém de fato confirmou.

| status | Significado | Exigência |
|---|---|---|
| `relatado` | Está escrito no relato. | `evidencia` com trecho **literal** copiado do texto mascarado. |
| `inferido` | Dedução razoável a partir do texto ou da natureza do problema. | `raciocinio` explicando a dedução. |
| `verificado` | Confirmado por fonte externa (vistoria, sistema, geocodificação validada). | Bloco `verificacao` com fonte e data. **A skill nunca atribui este status**; ele é reservado ao sistema Django ou a um revisor humano. |
| `ausente` | O relato não traz base para preencher o campo. | `valor` nulo. |

**O que nunca se inventa.** Evidências, datas, endereços, números de imóvel, CEPs, bairros, coordenadas, nomes, quantidade de pessoas afetadas. Se não está no texto, o campo fica `ausente` e vira uma pendência. Uma resposta incompleta e honesta é útil para a triagem; uma resposta completa e inventada gera atendimento no lugar errado.

Limites específicos da inferência:
- **Coordenadas** (latitude/longitude) só podem ser `relatado` (o cidadão informou) ou `verificado` (o sistema geocodificou). Nunca `inferido`.
- **Endereço e bairro** só podem ser `relatado` ou `verificado`. Saber que "Rua das Flores" existe em várias cidades não autoriza escolher uma.
- **Datas** podem ser `inferido` apenas quando derivadas de uma expressão relativa do relato ("ontem", "há duas semanas") combinada com a data de recebimento (`recebido_em`). Sem `recebido_em`, a data fica `ausente`, a expressão relativa literal vai para a `evidencia` e o `raciocinio` diz por que não foi convertida. `data_ocorrencia` é o **único** campo `ausente` que aceita evidência (schema 1.1.0): ela permite que o sistema converta a data depois, quando souber o recebimento. Nos demais campos e nos fatores, `ausente` tem `evidencia: null`.
- **Evidência é sempre literal.** Se o trecho precisa ser reescrito para fazer sentido, ele não é evidência; use `raciocinio`.

## 2. Fluxo de classificação

1. Gerar o texto mascarado (seção 11). Toda evidência citada sai dele.
2. Decidir o resultado da triagem (seção 3).
3. Se classificável, separar o relato em ocorrências (seção 4).
4. Para cada ocorrência: natureza (seção 5) → categoria principal → subcategoria (seção 6) → regras de fronteira e desempate (seções 7 e 8) → categorias secundárias e confiança (seção 9).
5. Registrar alegações de irregularidade (seção 10), sugerir órgão (seção 12) e listar pendências (seção 13).
6. Calcular a prioridade de cada ocorrência conforme `priorizacao.md`.

## 3. Resultado da triagem

Campo `resultado_triagem`, um por relato:

| Código | Quando usar | Exemplo |
|---|---|---|
| `classificado` | Há ao menos um problema urbano identificável. | "O bueiro da Rua 5 está sem tampa." |
| `informacao_insuficiente` | Parece um problema urbano, mas não dá para saber qual. | "A rua aqui de casa tá abandonada, ninguém faz nada." |
| `fora_escopo` | Não é problema urbano coletivo: conflito pessoal, pedido individual, propaganda, teste, crime contra pessoa específica. | "Meu vizinho me xingou ontem." |

`informacao_insuficiente` e `fora_escopo` não geram ocorrências nem prioridade, mas exigem `motivo_triagem`. Se o relato fora do escopo indicar perigo imediato a alguém, preencha `alerta_emergencia` mesmo assim (ex.: "tem uma pessoa desmaiada na calçada" → orientar SAMU 192).

## 4. Segmentação em ocorrências

Uma **ocorrência** é um problema que exige uma ação distinta. Um relato pode conter várias.

- **Separe** quando há objetos, locais ou ações corretivas diferentes. "O poste da esquina está apagado e tem um buraco no meio da quadra" → 2 ocorrências (`inf_iluminacao_publica` e `inf_pavimento`).
- **Não separe** quando um único problema tem vários efeitos. "O buraco acumula água e está dando mosquito" → 1 ocorrência `inf_pavimento`, com `meio_ambiente` como categoria secundária.
- Cada ocorrência recebe `id_ocorrencia` sequencial dentro da análise: `oc-1`, `oc-2`… A identificação global no Django é o par (`id_analise`, `id_ocorrencia`).
- Cada ocorrência tem prioridade própria. Não some prioridades entre ocorrências.

## 5. Natureza: problema existente × necessidade de infraestrutura

Campo `natureza`, por ocorrência. A distinção importa porque os dois tipos seguem fluxos diferentes na gestão pública: um problema existente vai para manutenção e fiscalização; uma necessidade nova vai para planejamento e orçamento.

| Código | Definição | Teste prático |
|---|---|---|
| `problema_existente` | Algo que existe e está danificado, falhando ou funcionando mal, ou uma conduta/ocupação que causa dano agora. | "Existia e quebrou, parou ou piorou?" |
| `necessidade_infraestrutura` | Pedido de algo que não existe no local: novo equipamento, nova rota, novo serviço. | "Nunca existiu e o relator está pedindo?" |

Exemplos:
- "A faixa de pedestre apagou" → `problema_existente` (existia).
- "Precisamos de uma faixa de pedestre na frente da escola" → `necessidade_infraestrutura`.
- "Minha rua nunca foi asfaltada" → `necessidade_infraestrutura`.
- "O abrigo do ponto foi arrancado" → `problema_existente`.

Se o relato pedir algo novo **e** descrever um dano atual distinto, são duas ocorrências. Se não der para saber se o item existia, use `problema_existente`, registre a dúvida no `raciocinio` da classificação e baixe a confiança.

### 5.1 Obra de adequação (`requer_obra_adequacao`)

Há um terceiro caso, que é um `problema_existente`: o equipamento **existe e está em uso**, mas não cumpre uma exigência **obrigatória**, sobretudo de acessibilidade (Lei Brasileira de Inclusão, NBR 9050). A falta não é um pedido de algo novo; é um descumprimento do que já devia estar lá. Resolver exige obra, então a ocorrência leva `requer_obra_adequacao: true`.

| Relato | `natureza` | `requer_obra_adequacao` | Por quê |
|---|---|---|---|
| "A escola municipal não tem rampa na entrada, o aluno cadeirante não consegue entrar." | `problema_existente` | `true` | Escola em uso sem acessibilidade obrigatória. |
| "O posto de saúde só tem escada." / "A calçada da esquina não tem rebaixamento." | `problema_existente` | `true` | Mesmo raciocínio. |
| "A rampa da escola quebrou." | `problema_existente` | `false` | Reparo do que existe. |
| "Precisamos de uma passarela sobre a avenida." | `necessidade_infraestrutura` | `false` | Equipamento novo, para planejamento. |

Por que importa: necessidades vão para planejamento com teto `alta` (`ex04`), enquanto uma exigência obrigatória descumprida é pendência do responsável pelo equipamento e não deve esperar na fila de obras novas. Em `necessidade_infraestrutura`, `requer_obra_adequacao` é sempre `false`. Na dúvida se a exigência é obrigatória, use `false` e registre a dúvida no `raciocinio` da classificação.

## 6. As sete categorias e suas subcategorias

Prefixos de subcategoria (obrigatórios e exclusivos de cada categoria): `mob_`, `inf_`, `amb_`, `svc_`, `ace_`, `esp_`, `seg_`. Toda categoria tem uma subcategoria `_outros` para casos legítimos que não cabem nas demais; o uso frequente de `_outros` é sinal para criar uma subcategoria na próxima versão da taxonomia.

Natureza típica: **P** = problema existente, **N** = necessidade de infraestrutura, **P/N** = ambas ocorrem.

### 6.1 Mobilidade e trânsito — `mobilidade_transito`

Circulação de pessoas e veículos: sinalização, fluxo, segurança viária, transporte coletivo e bicicleta.

| Código | Abrange | Exemplo de relato | Nat. | Órgão sugerido |
|---|---|---|---|---|
| `mob_semaforo` | Semáforo apagado, piscando, com defeito ou tempo inadequado | "O semáforo da Av. Paraná com a Rua 3 está apagado desde cedo." | P | `org_transito_mobilidade` |
| `mob_sinalizacao_viaria` | Placas e marcações ausentes, apagadas ou confusas | "A faixa de pedestre em frente ao mercado sumiu, ninguém para." | P/N | `org_transito_mobilidade` |
| `mob_seguranca_viaria` | Excesso de velocidade, cruzamento perigoso, ponto de acidentes, falta de redutor | "Os carros passam voando nessa reta, já teve três batidas este mês." | P/N | `org_transito_mobilidade` |
| `mob_fluxo_congestionamento` | Congestionamento recorrente, conversão mal desenhada, bloqueio de via | "Todo dia às 18h a rotatória trava por meia hora." | P | `org_transito_mobilidade` |
| `mob_estacionamento_irregular` | Fila dupla, local proibido, veículo sobre ciclovia ou faixa | "Caminhões param em fila dupla na frente do galpão." | P | `org_transito_mobilidade` |
| `mob_transporte_coletivo` | Atraso, lotação, itinerário, ponto sem abrigo ou sem informação | "O ônibus da linha 210 não passa aos domingos há duas semanas." | P/N | `org_transporte_coletivo` |
| `mob_ciclomobilidade` | Ciclovia interrompida ou danificada, falta de ciclovia ou paraciclo | "A ciclovia termina no meio da avenida e a gente cai no meio dos carros." | P/N | `org_transito_mobilidade` |
| `mob_outros` | Outros problemas de circulação | — | P/N | `org_transito_mobilidade` |

### 6.2 Infraestrutura urbana — `infraestrutura_urbana`

Estruturas físicas públicas e redes: pavimento, calçada, drenagem, iluminação, redes elétrica e de saneamento, obras de arte.

| Código | Abrange | Exemplo de relato | Nat. | Órgão sugerido |
|---|---|---|---|---|
| `inf_pavimento` | Buraco, afundamento, asfalto solto, rua sem pavimentação | "Tem um buraco enorme perto do nº 120, ontem um motoqueiro caiu." | P/N | `org_obras_vias` |
| `inf_calcada` | Calçada quebrada, desnivelada ou inexistente (sem foco em pessoa com deficiência) | "A calçada da praça está toda levantada pelas raízes." | P/N | `org_obras_vias` |
| `inf_drenagem` | Bueiro entupido ou sem tampa, boca de lobo, alagamento por falha de drenagem | "Toda chuva a esquina alaga porque a boca de lobo está entupida." | P/N | `org_drenagem_urbana` |
| `inf_iluminacao_publica` | Poste apagado, lâmpada acesa de dia, trecho sem iluminação | "Três postes da Rua Ipê estão apagados há um mês." | P/N | `org_iluminacao_publica` |
| `inf_rede_eletrica` | Fio baixo ou caído, poste danificado ou inclinado, transformador com problema | "Caiu um fio do poste e está soltando faísca." | P | `concessionaria_energia` |
| `inf_rede_agua_esgoto` | Vazamento de água na via, esgoto extravasando da rede, tampa de poço de visita | "Está vazando água limpa do asfalto há três dias." | P | `concessionaria_saneamento` |
| `inf_estrutura_publica` | Ponte, passarela, viaduto, escadaria ou muro de contenção público com dano | "A passarela sobre a rodovia está com a grade solta." | P | `org_obras_vias` |
| `inf_outros` | Outras estruturas públicas | — | P/N | `org_obras_vias` |

### 6.3 Meio ambiente — `meio_ambiente`

Resíduos fora do sistema de coleta, poluição, vegetação, áreas protegidas, fauna e vetores.

| Código | Abrange | Exemplo de relato | Nat. | Órgão sugerido |
|---|---|---|---|---|
| `amb_descarte_irregular` | Lixo, entulho ou móveis descartados em terreno, via ou margem | "Estão jogando entulho no terreno baldio do lado do córrego." | P | `org_limpeza_urbana` |
| `amb_poluicao_hidrica` | Esgoto ou efluente em córrego, rio, lagoa; mancha de óleo | "O córrego está com espuma e cheiro de esgoto." | P | `org_meio_ambiente` |
| `amb_poluicao_ar` | Queimada, fumaça, odor intenso | "Toda noite queimam lixo no terreno e a fumaça entra nas casas." | P | `org_meio_ambiente` |
| `amb_poluicao_sonora` | Ruído persistente de fonte fixa (indústria, obra, estabelecimento) | "A serralheria funciona até 23h com barulho de máquina." | P | `org_meio_ambiente` |
| `amb_arborizacao` | Árvore com risco de queda, galhos na fiação, poda ou corte irregular, falta de arborização | "A árvore da escola está inclinada e com o tronco rachado." | P/N | `org_areas_verdes` |
| `amb_area_verde` | Desmatamento, degradação de área de preservação, aterro de nascente | "Estão aterrando a nascente no fundo do loteamento." | P | `org_meio_ambiente` |
| `amb_fauna_zoonoses` | Animal morto, foco de mosquito, água parada, infestação, animal peçonhento | "Piscina abandonada cheia de larva na casa vazia." | P | `org_vigilancia_zoonoses` |
| `amb_outros` | Outros problemas ambientais | — | P/N | `org_meio_ambiente` |

### 6.4 Serviços públicos — `servicos_publicos`

Funcionamento de serviços prestados à população, independentemente de dano físico na estrutura.

| Código | Abrange | Exemplo de relato | Nat. | Órgão sugerido |
|---|---|---|---|---|
| `svc_coleta_residuos` | Coleta domiciliar ou seletiva não realizada, contêiner cheio, horário | "O caminhão do lixo não passa na minha rua há 10 dias." | P | `org_limpeza_urbana` |
| `svc_limpeza_urbana` | Varrição, capina, limpeza pós-feira | "Depois da feira de domingo ninguém limpa a rua." | P | `org_limpeza_urbana` |
| `svc_abastecimento_agua` | Falta de água, baixa pressão, água turva (sem vazamento visível) | "O bairro inteiro está sem água desde ontem." | P | `concessionaria_saneamento` |
| `svc_fornecimento_energia` | Falta de energia em imóveis ou região (sem dano visível na rede) | "Quarta queda de energia na semana aqui na vila." | P | `concessionaria_energia` |
| `svc_saude` | Funcionamento de unidade de saúde: fechada, sem atendimento, sem insumos | "O posto de saúde está fechado às sextas sem aviso." | P/N | `org_saude` |
| `svc_educacao` | Funcionamento de escola ou creche: vagas, estrutura, turno | "A creche do bairro não tem vaga desde o ano passado." | P/N | `org_educacao` |
| `svc_atendimento_publico` | Demora, protocolo sem resposta, falha em atendimento de órgão | "Abri protocolo há 3 meses e ninguém respondeu." | P | `org_ouvidoria` |
| `svc_outros` | Outros serviços | — | P/N | `org_ouvidoria` |

### 6.5 Acessibilidade — `acessibilidade`

Barreiras à circulação e ao uso por pessoas com deficiência, idosos, gestantes, pessoas com carrinho de bebê ou mobilidade reduzida. Use esta categoria quando o relato menciona a barreira para essas pessoas (regra `rd01_acessibilidade_explicita`).

| Código | Abrange | Exemplo de relato | Nat. | Órgão sugerido |
|---|---|---|---|---|
| `ace_rota_pedestre` | Calçada ou travessia que impede a circulação de pessoas com mobilidade reduzida | "Com a cadeira de rodas não consigo passar, a calçada tem degrau." | P/N | `org_acessibilidade_inclusao` |
| `ace_rampa` | Rampa ausente, íngreme demais ou obstruída | "A rampa da esquina tem um poste no meio." | P/N | `org_obras_vias` |
| `ace_piso_tatil` | Piso tátil ausente, interrompido ou levando a obstáculo | "O piso tátil leva direto para uma lixeira." | P/N | `org_obras_vias` |
| `ace_transporte` | Ônibus sem elevador ou com elevador quebrado, ponto inacessível | "O elevador do ônibus da linha 15 nunca funciona." | P | `org_transporte_coletivo` |
| `ace_edificacao_publica` | Prédio público sem acesso, sem banheiro adaptado | "A biblioteca municipal só tem escada." | P/N | `org_acessibilidade_inclusao` |
| `ace_vaga_reservada` | Vaga para pessoa com deficiência ou idosa ocupada indevidamente ou inexistente | "As vagas de deficiente do mercado vivem ocupadas." | P/N | `org_transito_mobilidade` |
| `ace_comunicacao_sinalizacao` | Semáforo sonoro, braile, informação visual ou sonora | "O semáforo sonoro da rodoviária está mudo." | P/N | `org_acessibilidade_inclusao` |
| `ace_outros` | Outras barreiras | — | P/N | `org_acessibilidade_inclusao` |

### 6.6 Uso do espaço público — `uso_espaco_publico`

Ocupação, conservação e conflitos de uso em calçadas, praças, parques e vias.

| Código | Abrange | Exemplo de relato | Nat. | Órgão sugerido |
|---|---|---|---|---|
| `esp_ocupacao_calcada` | Mesas, mercadorias, grades ou rampas particulares ocupando o passeio | "O bar coloca mesas e a gente tem que andar na rua." | P | `org_fiscalizacao_posturas` |
| `esp_obra_particular` | Obra, caçamba ou entulho de particular ocupando via ou calçada | "A caçamba da obra está há um mês ocupando metade da rua." | P | `org_fiscalizacao_posturas` |
| `esp_construcao_irregular` | Alegação de construção sem licença ou ocupação de área pública | "Estão construindo um muro avançando sobre a calçada." | P | `org_controle_urbano` |
| `esp_comercio_ambulante` | Comércio informal com conflito de uso do espaço | "As barracas fecham a entrada da estação." | P | `org_fiscalizacao_posturas` |
| `esp_praca_parque` | Equipamentos de praça, parque ou quadra quebrados; falta de equipamentos | "O balanço do parquinho está com a corrente partida." | P/N | `org_areas_verdes` |
| `esp_veiculo_abandonado` | Veículo abandonado em via pública | "Tem um carro sem rodas parado há meses na esquina." | P | `org_transito_mobilidade` |
| `esp_pichacao_publicidade` | Pichação em patrimônio, faixas, cartazes ou painéis irregulares | "Picharam o monumento da praça central." | P | `org_fiscalizacao_posturas` |
| `esp_eventos_perturbacao` | Festas ou eventos ocupando a via, com ruído e bloqueio | "Todo sábado fecham a rua com som alto até 4h." | P | `org_fiscalizacao_posturas` |
| `esp_outros` | Outros conflitos de uso | — | P/N | `org_fiscalizacao_posturas` |

### 6.7 Segurança urbana — `seguranca_urbana`

Condições do ambiente urbano que expõem pessoas a violência, desastres ou incêndio. Não é canal de registro de crimes contra pessoas específicas (esses são `fora_escopo`, com orientação para o canal policial).

| Código | Abrange | Exemplo de relato | Nat. | Órgão sugerido |
|---|---|---|---|---|
| `seg_percepcao_inseguranca` | Trecho ermo, sem movimento, com sensação de medo (sem ocorrência específica) | "O caminho até o ponto de ônibus é deserto e escuro, dá medo." | P/N | `org_seguranca_publica` |
| `seg_ocorrencias_recorrentes` | Relato de assaltos ou furtos recorrentes num local (alegação) | "Toda semana assaltam alguém na saída da passarela." | P | `org_seguranca_publica` |
| `seg_imovel_abandonado` | Imóvel ou terreno abandonado com invasão, uso ilícito ou risco | "A casa abandonada virou ponto de uso de drogas." | P | `org_controle_urbano` |
| `seg_risco_desastre` | Encosta com risco de deslizamento, erosão, enchente em área de risco, trincas por movimentação do solo | "Depois da chuva abriu uma rachadura no barranco atrás das casas." | P | `org_defesa_civil` |
| `seg_incendio` | Foco ou risco de incêndio (material inflamável acumulado, ligações perigosas) | "Tem fogo no mato do terreno ao lado do posto." | P | `servico_bombeiros` |
| `seg_vandalismo` | Depredação de equipamento público em andamento ou recorrente | "Quebram os vidros do abrigo do ônibus toda semana." | P | `org_seguranca_publica` |
| `seg_outros` | Outras condições de insegurança urbana | — | P/N | `org_seguranca_publica` |

## 7. Casos de fronteira

Situações em que duas categorias são plausíveis e a decisão já está tomada. Aplique estas decisões antes de recorrer às regras de desempate gerais.

| Situação | Principal | Secundária possível | Critério |
|---|---|---|---|
| Calçada quebrada | `inf_calcada` | — | Sem menção a pessoa com mobilidade reduzida. |
| Calçada quebrada que impede cadeirante, idoso, carrinho | `ace_rota_pedestre` | `infraestrutura_urbana` | `rd01_acessibilidade_explicita` |
| Poste apagado, com ou sem menção a medo ou assaltos | `inf_iluminacao_publica` | `seguranca_urbana` | `rd03_causa_acionavel`: o conserto é na iluminação. |
| Trecho escuro e ermo sem poste com defeito | `seg_percepcao_inseguranca` | `infraestrutura_urbana` | Não há equipamento quebrado; pode ser necessidade. |
| Fio caído, poste danificado | `inf_rede_eletrica` | — | Dano físico visível na rede. |
| Falta de energia sem dano visível | `svc_fornecimento_energia` | — | Falha no serviço. |
| Vazamento na via | `inf_rede_agua_esgoto` | — | Dano físico na rede. |
| Falta de água sem vazamento | `svc_abastecimento_agua` | — | Falha no serviço. |
| Esgoto extravasando na rua | `inf_rede_agua_esgoto` | `meio_ambiente` | Causa é a rede. `problema_existente`; prioridade pelas âncoras A1 e A2 da matriz (em geral `media`; sobe só com evidência, ver `priorizacao.md` 9.5). |
| Esgoto chegando ao córrego, sem origem identificada na via | `amb_poluicao_hidrica` | — | Efeito ambiental é o objeto do relato. |
| Lixo de casas no ponto, coleta não passou | `svc_coleta_residuos` | — | Lixo está dentro do sistema de coleta. |
| Lixo ou entulho jogado em terreno, margem, via | `amb_descarte_irregular` | — | Descarte fora do sistema. |
| Entulho de obra particular identificada em frente | `esp_obra_particular` | `meio_ambiente` | Responsável é a obra. |
| Alagamento por bueiro entupido | `inf_drenagem` | — | Falha de drenagem. |
| Enchente ameaçando moradias em área de risco | `seg_risco_desastre` | `infraestrutura_urbana` | `rd02_risco_estrutural_ou_desastre` |
| Muro de contenção ou ponte pública com dano | `inf_estrutura_publica` | — | `rd02`: estrutura construída. |
| Barranco, encosta, solo cedendo | `seg_risco_desastre` | — | `rd02`: terreno natural. |
| Árvore com risco de queda ou caída | `amb_arborizacao` | `mobilidade_transito` ou `infraestrutura_urbana` | Mesmo caída, a ação é sobre a árvore. Árvore sobre fio energizado aciona `ex01_risco_iminente`. |
| Ruído de estabelecimento ou indústria | `amb_poluicao_sonora` | — | Fonte fixa. |
| Festa ou evento ocupando a rua | `esp_eventos_perturbacao` | `meio_ambiente` | Ocupação do espaço é o núcleo. |
| Carro sobre a calçada bloqueando passagem | `mob_estacionamento_irregular` | `uso_espaco_publico` | Sem menção a mobilidade reduzida. Com menção → `ace_rota_pedestre` (`rd01`). |
| Ponto de ônibus sem abrigo | `mob_transporte_coletivo` | — | Natureza `necessidade_infraestrutura` se nunca existiu. |
| Ponto de ônibus inacessível para cadeirante | `ace_transporte` | `mobilidade_transito` | `rd01` |
| Escola, posto ou prédio público em uso sem rampa ou acesso | `ace_edificacao_publica` (ou `ace_rampa`, se o relato fala só da rampa) | `servicos_publicos` | `rd01`; `problema_existente` com `requer_obra_adequacao: true` (seção 5.1). |
| Semáforo apagado, desligado ou piscando | `mob_semaforo` | — | `problema_existente`. Em cruzamento de grande circulação, a análise registra `ex06_falha_controle_trafego` (`priorizacao.md` 6). |
| Imóvel abandonado com água parada ou lixo | `amb_fauna_zoonoses` ou `amb_descarte_irregular` | `seguranca_urbana` | Efeito sanitário é o núcleo. |
| Imóvel abandonado invadido ou com uso ilícito alegado | `seg_imovel_abandonado` | — | Alegação pendente de verificação. |
| Pichação já feita | `esp_pichacao_publicidade` | — | Conservação do espaço. |
| Depredação recorrente ou em andamento | `seg_vandalismo` | `uso_espaco_publico` | Foco na conduta recorrente. |

## 8. Regras de desempate

Aplicadas em ordem, quando os casos de fronteira não resolvem. A regra usada é registrada em `classificacao.regra_desempate` (ou `null` se nenhuma foi necessária).

| Código | Regra |
|---|---|
| `rd01_acessibilidade_explicita` | Se o relato menciona a barreira para pessoa com deficiência, idosa, gestante, com carrinho de bebê ou mobilidade reduzida, a categoria principal é `acessibilidade`. Essas situações têm tratamento e responsáveis específicos e se perderiam dentro de "calçada quebrada". |
| `rd02_risco_estrutural_ou_desastre` | Risco ligado a estrutura pública construída → `infraestrutura_urbana` (`inf_estrutura_publica`). Risco ligado a terreno, encosta, curso d'água ou fenômeno natural ameaçando moradias → `seguranca_urbana` (`seg_risco_desastre`). |
| `rd03_causa_acionavel` | A principal é a categoria daquilo que precisa ser consertado ou fiscalizado para resolver o problema. Os efeitos vão para as secundárias. |
| `rd04_foco_do_relator` | Se ainda houver empate (duas causas plausíveis para o mesmo problema), escolha o que o relator enfatiza. Marque `ambigua: true`. |

## 9. Ambiguidade, categorias secundárias e confiança

- **`categorias_secundarias`**: até 2 categorias, diferentes da principal, que descrevem efeitos relevantes do mesmo problema. Não use para problemas independentes (esses viram outra ocorrência).
- **`ambigua`**: `true` quando há duas leituras razoáveis da categoria principal e foi preciso escolher. Exige `motivo_ambiguidade` e gera a pendência `classificacao_ambigua`.
- **`confianca`**: uma avaliação qualitativa, **não uma probabilidade calibrada**.

| Valor | Quando |
|---|---|
| `alta` | Encaixe direto numa subcategoria; nenhuma regra de desempate controversa. |
| `media` | Foi aplicada regra de desempate ou a descrição é parcial. |
| `baixa` | Descrição vaga ou várias leituras possíveis. Obriga `ambigua: true` ou pendência `descricao_insuficiente`, e a pendência `revisao_humana_recomendada`. |

## 10. Alegações de irregularidade

Uma **alegação** existe quando o relato atribui uma conduta irregular ou ilícita a alguém: pessoa, empresa, estabelecimento, órgão ou agente público. Exemplos: "a empresa X joga esgoto no rio", "o fiscal recebe dinheiro para liberar", "a obra não tem alvará".

A skill não tem como confirmar a alegação. Tratá-la como fato poderia expor alguém injustamente e contaminar a priorização. Por isso:

1. Registre em `alegacao_irregularidade` com `presente: true`, o `tipo` e `status_verificacao: "pendente_verificacao"`. A skill sempre usa esse status; `confirmada` e `nao_confirmada` são atribuídos depois, por quem apurar.
2. Escreva `descricao_neutra` com linguagem de alegação: "O relato alega que…", "Segundo o relator…". Nunca afirme a conduta como fato.
3. Nomes de pessoas físicas são sempre mascarados. Em saídas com visibilidade `publica`, nomes de empresas e estabelecimentos citados na alegação também são mascarados (`[EMPRESA]`).
4. A alegação **não soma pontos** de prioridade. A prioridade vem dos efeitos físicos descritos (esgoto no rio, entulho na via), avaliados normalmente.
5. Adicione a pendência `verificar_alegacao`.

Tipos (`alegacao_irregularidade.tipo`):

| Código | Exemplo |
|---|---|
| `obra_sem_licenca` | "Essa construção não tem alvará." |
| `descarte_ou_poluicao_ilegal` | "A fábrica solta efluente no córrego de madrugada." |
| `ocupacao_irregular_area_publica` | "O dono do bar cercou a calçada para uso próprio." |
| `conduta_agente_publico` | "O fiscal avisa antes da fiscalização." |
| `cobranca_indevida` | "Estão cobrando para estacionar na rua pública." |
| `descumprimento_servico` | "A empresa de ônibus pula a linha de propósito." |
| `outro` | Demais alegações. |

## 11. Dados pessoais e mascaramento

Há dois tipos de informação com tratamentos diferentes.

- **Dados pessoais do cidadão e de terceiros**: quem relatou e quem foi citado. Não são necessários para resolver o problema urbano e são mascarados em todo texto que sai da skill, em qualquer visibilidade.
- **Localização do problema**: onde está o buraco, o poste, o lixo. É necessária para o atendimento e é preservada em `localizacao`. A única exceção é quando ela coincide com a residência de alguém (ver `endereco_residencial` abaixo).

**Acesso ao texto original.** `texto_original` só aparece em saídas com visibilidade `interna`, que são de acesso restrito. Em saídas `publica` ele é sempre `null`, mesmo que nada tenha sido detectado, porque uma falha de detecção não pode vazar dados.

**Texto mascarado.** Cada documento tem seu próprio `texto_mascarado`, e toda evidência daquele documento é citada a partir dele. Na versão `interna`, a localização do problema fica intacta. Na versão `publica`, o texto também é anonimizado quanto à residência e às empresas citadas em alegações.

| Tipo (`dados_pessoais.tipos`) | Marcador | `interna` | `publica` |
|---|---|---|---|
| `nome_pessoa` | `[NOME]` | mascara | mascara |
| `cpf` | `[CPF]` | mascara | mascara |
| `documento_identificacao` | `[DOCUMENTO]` | mascara | mascara |
| `telefone` | `[TELEFONE]` | mascara | mascara |
| `email` | `[EMAIL]` | mascara | mascara |
| `placa_veiculo` | `[PLACA]` | mascara | mascara |
| `dado_sensivel` | `[DADO_SENSIVEL]` | mascara, salvo a exceção da seção 11.1 | mascara sempre que a pessoa for identificável (11.1) |
| `endereco_residencial` | `[NUMERO]` | **mantém** (é a localização do problema) | mascara o número; o logradouro fica e `precisao` passa a `aproximada` |
| `empresa_em_alegacao` | `[EMPRESA]` | mantém | mascara |

Observações:
- `nome_pessoa` inclui agentes públicos citados.
- `documento_identificacao` cobre RG, CNH, passaporte e matrícula.
- `dado_sensivel` cobre as características listadas na seção 11.1, quando ligadas a pessoa identificável.
- `endereco_residencial` vale quando o endereço identifica a residência do relator ou de terceiro ("em frente à minha casa, Rua X, 45"). Um endereço de via pública sem vínculo com moradia ("buraco na Rua X perto do nº 120") não é dado pessoal e é mantido nas duas visibilidades.

### 11.1 Dados sensíveis: saúde, deficiência e outras características pessoais

A condição de quem é afetado pode ser decisiva para a prioridade (um cadeirante que precisa andar pela pista), mas a mesma informação, ligada a uma pessoa reconhecível, pode expô-la a discriminação. A regra separa **a condição** (útil para priorizar) **da identidade** (desnecessária).

**O que é característica sensível.** Saúde (doença, diagnóstico, tratamento, medicamento, gravidez, saúde mental, dependência química); deficiência ou mobilidade reduzida; religião; orientação sexual e identidade de gênero; origem racial ou étnica; opinião política e filiação sindical, partidária ou religiosa; dados genéticos e biométricos; condição migratória; situação de rua ou de vulnerabilidade social de uma pessoa ou família; ser vítima de violência; antecedentes criminais.

**Quando a pessoa é identificável.** Quando a característica está ligada a alguém que pode ser reconhecido:
- pelo nome ou apelido ("o seu Antônio, que tem Alzheimer");
- pela residência ("a moradora do 45, que é cega");
- por um vínculo único ("minha filha autista", "o aluno cadeirante da escola Y", "o único morador de rua da praça");
- pelo próprio relator falando de si ("sou cadeirante"), já que o relato pode ser associado a ele.

Menções coletivas ou genéricas, sem uma pessoa reconhecível, **não** são dado pessoal e ficam nas duas visibilidades: "crianças saindo da escola", "muitos idosos passam aqui", "cadeirantes não conseguem passar". A exceção é a reidentificação indireta, tratada logo abaixo.

**Tratamento.**

| Situação | `interna` | `publica` |
|---|---|---|
| Menção coletiva ou genérica | mantém | mantém |
| Característica de pessoa identificável que **sustenta um fator de prioridade** (em geral `vulnerabilidade_afetados`) | mantém o mínimo necessário (a condição, não detalhes clínicos) | `[DADO_SENSIVEL]` |
| Característica de pessoa identificável que **não** sustenta nenhum fator (religião do vizinho, diagnóstico que não tem relação com o problema) | `[DADO_SENSIVEL]` | `[DADO_SENSIVEL]` |
| Criança ou adolescente identificável pelo contexto (escola, nome, endereço) | mantém a condição só se sustentar fator | `[DADO_SENSIVEL]`; nunca o nome |
| Menção coletiva à mesma característica (ou que permita deduzi-la) num relato com pessoa identificável | mantém | `[DADO_SENSIVEL]` |

Na versão `publica`:
- a nota do fator se mantém, e a evidência é copiada do texto mascarado ("Sou [DADO_SENSIVEL] e não consigo passar");
- o `raciocinio` e o relatório usam um termo genérico, como "pessoa de grupo vulnerável relatada", sem repetir a condição;
- `descricao_neutra` também não repete a condição.

**Reidentificação indireta (versão `publica`).** Mascarar campo a campo não basta quando as peças juntas permitem deduzir o que foi escondido. No relato "mora o seu Antônio, que é cadeirante e soropositivo… caiu tentando sair de casa… os cadeirantes do bairro reclamam", a rua visível, a queda na porta de casa e a frase coletiva revelam a deficiência mascarada, e dois marcadores revelam que há uma segunda condição. Quando houver característica sensível de pessoa identificável (`dado_sensivel` em `tipos`):
1. **Um marcador por pessoa.** Todas as condições da mesma pessoa viram um único `[DADO_SENSIVEL]` ("que é [DADO_SENSIVEL]"), para não revelar quantas são. O validador acusa erro em dois marcadores seguidos.
2. **Menção coletiva mascarada.** A menção coletiva à mesma característica, ou que permita deduzi-la, também vira `[DADO_SENSIVEL]` na versão pública ("Os [DADO_SENSIVEL] do bairro todo reclamam"). O validador avisa quando encontra uma.
3. **Resumo anonimizado no lugar do texto.** `dados_pessoais.texto_relato_publicavel` fica `false` (o schema exige). Relatórios e painéis públicos **não reproduzem** o `texto_mascarado` nem as evidências literais desse relato. Mostram só `descricao_neutra`, as notas e raciocínios genéricos.
4. **`descricao_neutra` sem ligação com a pessoa.** Descreva o problema, não quem o sofre nem onde mora: "Calçada esburacada na Rua Aurora, com quedas de pedestre relatadas; pessoa de grupo vulnerável afetada", e não "morador que caiu ao sair de casa". O logradouro fica, porque é a localização do problema.

O `texto_mascarado` continua no JSON público, para que as evidências possam ser conferidas por quem tem acesso ao sistema, mas ele não é exibido. Em visibilidade `interna`, `texto_relato_publicavel` é sempre `false`. Sem dado sensível de pessoa identificável, ele é `true`, salvo se a análise julgar que a combinação de local e detalhes identifica alguém; nesse caso use `false` e explique na resposta.

Na versão `interna`, quando uma condição for mantida por sustentar um fator, diga isso no `raciocinio` do fator ("condição do relator mantida só na versão interna, por sustentar a vulnerabilidade"). Ela não entra em `dados_pessoais.tipos`, que lista só o que foi mascarado no documento.

**Na conversa**, refira-se à condição de forma genérica quando ela identificar alguém ("pessoa com deficiência relatada"). O usuário da skill é a equipe de triagem; mesmo assim, a resposta pode ser copiada para outros canais.

Na dúvida se a pessoa é identificável, trate como identificável. Se o dado servia para a prioridade, ele continua disponível na versão interna.

### 11.2 Regras gerais

Os valores mascarados nunca são copiados para nenhum outro campo. `dados_pessoais` registra os tipos **mascarados naquele documento**. Por isso o mesmo relato pode listar `endereco_residencial` na versão `publica` e não na `interna`.

## 12. Órgãos responsáveis genéricos

Os códigos não se vinculam a nenhum município. O sistema Django poderá mapeá-los para secretarias reais em cada implantação. A sugestão é sempre `inferido`.

| Código | Função |
|---|---|
| `org_transito_mobilidade` | Trânsito, sinalização, engenharia de tráfego |
| `org_transporte_coletivo` | Gestão do transporte público coletivo |
| `org_obras_vias` | Obras e manutenção de vias, calçadas e estruturas públicas |
| `org_iluminacao_publica` | Iluminação pública |
| `org_drenagem_urbana` | Drenagem e manejo de águas pluviais |
| `org_limpeza_urbana` | Coleta de resíduos e limpeza urbana |
| `org_meio_ambiente` | Licenciamento e fiscalização ambiental |
| `org_areas_verdes` | Parques, praças, arborização e poda |
| `org_vigilancia_zoonoses` | Vigilância ambiental, vetores e zoonoses |
| `org_saude` | Rede de saúde |
| `org_educacao` | Rede de educação |
| `org_acessibilidade_inclusao` | Direitos da pessoa com deficiência e acessibilidade |
| `org_fiscalizacao_posturas` | Fiscalização de posturas e uso do espaço público |
| `org_controle_urbano` | Licenciamento de obras e controle do uso do solo |
| `org_defesa_civil` | Defesa civil e áreas de risco |
| `org_seguranca_publica` | Segurança pública municipal ou estadual |
| `servico_bombeiros` | Corpo de bombeiros |
| `concessionaria_energia` | Distribuidora de energia elétrica |
| `concessionaria_saneamento` | Prestadora de água e esgoto |
| `org_ouvidoria` | Ouvidoria geral (quando nenhum outro se aplica) |

`orgao_sugerido.principal` recebe um código; `orgao_sugerido.apoio` recebe até 2 códigos adicionais quando a solução envolve mais de um órgão (ex.: árvore sobre fiação → `org_areas_verdes` com apoio de `concessionaria_energia`).

## 13. Pendências

Pendências dizem o que falta para atender bem o relato. Elas orientam um eventual pedido de complemento ao cidadão e a revisão humana.

| Código | Quando |
|---|---|
| `descricao_insuficiente` | Não está claro qual é o problema ou sua extensão. |
| `localizacao_ausente` | Nenhuma referência de local. |
| `localizacao_imprecisa` | Há referência ("perto da escola"), mas não é suficiente para encontrar o local. |
| `data_ausente` | Não se sabe quando começou ou ocorreu, e isso afeta a avaliação. |
| `complementar_dados_prioridade` | Fatores de prioridade ausentes podem mudar o nível (ver `priorizacao.md`). |
| `classificacao_ambigua` | `ambigua: true`. |
| `verificar_alegacao` | Há alegação de irregularidade. |
| `revisao_humana_recomendada` | Confiança baixa, alerta de emergência ou prioridade provisória. |

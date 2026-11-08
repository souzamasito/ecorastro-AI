# Questão de privacidade: reidentificação pela menção coletiva

Situação: **decidida e aplicada na skill 0.3.0** (complemento da Etapa 6). O texto abaixo é o registro original; a decisão está no fim.

Situação original: registrada, sem alteração de regra. As regras em vigor eram as da seção 11.1 de `references/categorias.md` (skill 0.2.0).
Origem: caso `dado-sensivel-terceiro`, iteração 2. O problema foi apontado pela própria execução com a skill 0.2.0.

## O caso

Relato: "Na Rua Aurora, 45, mora o seu Antônio, que é cadeirante e soropositivo. A calçada em frente à casa dele está toda esburacada e ele já caiu duas vezes tentando sair de casa. Os cadeirantes do bairro todo reclamam dessa rua."

Texto público gerado, conforme as regras atuais:

> Na Rua Aurora, [NUMERO], mora o seu [NOME], que é [DADO_SENSIVEL] e [DADO_SENSIVEL]. A calçada em frente à casa dele está toda esburacada e ele já caiu duas vezes tentando sair de casa. Os cadeirantes do bairro todo reclamam dessa rua.

Cada regra foi cumprida:
- o nome, as duas condições e o número da casa estão mascarados;
- a menção coletiva ficou, como a seção 11.1 permite.

## O problema

As peças, juntas, permitem inferir o dado mascarado:

1. **A condição mascarada pode ser deduzida.** A frase coletiva sobre cadeirantes, ao lado de "que é [DADO_SENSIVEL]" e de "caiu tentando sair de casa", sugere qual é a condição.
2. **A pessoa pode ser localizada.** O nome da rua continua visível, porque é o local do problema. Numa rua curta, num painel lido por moradores, "o morador da Rua Aurora que caiu na frente de casa" pode ser reconhecido.
3. **A segunda condição fica exposta.** Uma vez reconhecida a pessoa, saber que há um segundo `[DADO_SENSIVEL]` já revela que existe outra condição de saúde. Mesmo sem dizer qual, isso pode ser estigmatizante.

O risco é baixo, mas não é zero. Ele vem da combinação de informações, não de um dado isolado; por isso nenhuma regra campo a campo nem o validador o detectam.

## Como as configurações trataram o caso

| Configuração | Interna | Pública |
|---|---|---|
| Skill 0.2.0 | "cadeirante" mantido como evidência da vulnerabilidade; sorologia `[DADO_SENSIVEL]` | Texto acima; a execução sinalizou o risco ao usuário |
| Skill 0.1.0 | As duas condições `[DADO_SENSIVEL]` | O mesmo texto |
| Sem skill | Sorologia **descartada**; deficiência generalizada | Texto reescrito: "pessoas com mobilidade reduzida", sem número da casa, sem relato literal |

A comparação de base reescreveu o texto público em vez de mascarar o relato literal. Para privacidade, foi a abordagem mais protetora.

## Opções para decidir

1. **Mascarar também a menção coletiva quando houver pessoa identificável no mesmo relato.** Na versão pública, "Os cadeirantes do bairro" vira "[DADO_SENSIVEL] do bairro". A evidência da vulnerabilidade continua literal, mas fica pouco informativa.
2. **Não publicar o texto do relato na versão pública quando houver dado sensível de pessoa identificável.** O painel mostra só `descricao_neutra`, os fatores e o raciocínio genérico. `texto_mascarado` continua existindo no JSON público, porque as evidências precisam dele, mas o relatório público e o painel não o exibem.
3. **Marcador único por pessoa.** Usar um só `[DADO_SENSIVEL]` por pessoa, mesmo com várias condições, para não revelar quantas há. Compatível com as opções 1 e 2.
4. **Manter as regras atuais** e confiar na revisão humana antes de publicar.

Recomendação: **2 + 3**. A opção 2 resolve a combinação de informações sem perder rastreabilidade. A opção 3 elimina o sinal "há duas condições", que é barato de corrigir. As duas exigem:
- uma regra na seção 11.1;
- uma linha nos modelos de `references/relatorio.md`;
- uma checagem no validador: na versão pública, se `dado_sensivel` estiver em `tipos` e houver `[NOME]` ou `[NUMERO]`, avisar caso o relatório reproduza o `texto_mascarado`.

## Ponto relacionado: dado sensível sem relação no texto original

Nas versões 0.1.0 e 0.2.0, a versão interna guarda o `texto_original` com a sorologia, porque o texto original existe para auditoria e para o hash. A comparação de base descartou o dado. A versão interna é de acesso restrito e fica fora do Git, mas a equipe pode querer uma regra de retenção, como apagar o `texto_original` depois de um prazo, ou uma versão interna sem dado sensível sem relação com o problema. Isso é decisão de governança de dados do EcoRastro, não da skill.

## Decisões necessárias

1. Escolher entre as opções 1 a 4, ou uma combinação delas.
2. Definir se o `texto_original` com dado sensível sem relação com o problema precisa de regra de retenção ou de exclusão no Django.
3. Melhorar o critério 04 do caso `dado-sensivel-terceiro`. Hoje ele aceita a palavra "cadeirantes" (plural) como evidência e não separa a 0.1.0 da 0.2.0.

## Decisão (complemento da Etapa 6)

Aprovada a proteção contra reidentificação: marcadores no lugar das informações identificáveis, resumos anonimizados nas saídas públicas e proibição de expor dado sensível que permita reidentificar alguém. Na prática, foram adotadas as opções **1, 2 e 3** juntas:

| Opção | Como ficou |
|---|---|
| 1. Mascarar a menção coletiva | Na versão pública, quando há pessoa identificável com característica sensível, a menção coletiva à mesma característica vira `[DADO_SENSIVEL]`. O validador avisa quando encontra uma |
| 2. Não publicar o texto | Campo novo `dados_pessoais.texto_relato_publicavel`: `false` obrigatório quando há `dado_sensivel`, e sempre na interna. Relatórios e painéis públicos usam só `descricao_neutra` |
| 3. Um marcador por pessoa | Dois `[DADO_SENSIVEL]` seguidos na versão pública são erro do validador |

Retenção do `texto_original`: documentada como proposta para o Django em `docs/politica-retencao-proposta.md`. Nada foi implementado.

O critério 04 do caso `dado-sensivel-terceiro` foi reescrito para avaliar a proteção contra reidentificação. A verificação antiga (condição no singular na versão interna) virou o critério 08.

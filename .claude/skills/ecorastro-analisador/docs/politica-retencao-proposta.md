# Política de retenção e exclusão de dados: proposta para o Django

Situação: **proposta, não implementada.** A skill não guarda dados por conta própria. Ela grava arquivos em `saidas/` a pedido do usuário, com as proteções já descritas no `SKILL.md`: `chmod 600` nos arquivos internos e exclusão do Git. A política abaixo é para a futura aplicação Django, que vai armazenar as análises. Os prazos são **sugestões iniciais** e precisam ser validados pelo encarregado de dados (DPO) e pela área jurídica do órgão.

## 1. Fundamentos

- **LGPD (Lei 13.709/2018):**
  - dados de saúde, deficiência, religião, orientação sexual e origem racial são **dados sensíveis** (art. 5º, II), com tratamento restrito (art. 11);
  - pelo princípio da **necessidade** (art. 6º, III), só se guarda o mínimo para a finalidade;
  - o dado é **eliminado** quando o tratamento termina, salvo as hipóteses de conservação do art. 16, como o cumprimento de obrigação legal;
  - o titular pode pedir anonimização ou eliminação do que for desnecessário (art. 18).
- **Arquivos públicos (Lei 8.159/1991):** registros de atendimento ao cidadão podem ter prazo de guarda definido na tabela de temporalidade do município. Esse prazo prevalece sobre as sugestões abaixo e deve ser consultado antes da implementação.
- **Princípio da skill:** a condição ajuda a priorizar; a identidade de quem a tem, não (seção 11.1 de `categorias.md`).

## 2. Inventário: o que cada análise contém

| Dado | Onde | Conteúdo pessoal |
|---|---|---|
| `texto_original` | Só na versão `interna` | Tudo o que o cidadão escreveu, inclusive nome, telefone e condições de saúde de terceiros |
| `texto_mascarado` interno | `interna` | Sem nome nem contatos. Pode manter a condição que sustenta um fator ("cadeirante") |
| Fatores, evidências e raciocínios internos | `interna` | Podem citar a condição mantida |
| `hash_texto` | As duas versões | Nenhum conteúdo legível. Serve para deduplicação e para provar que o texto não foi alterado |
| `id_externo` | Só na `interna` | Liga o relato ao cidadão no sistema de origem |
| Versão `publica` | Painel e relatórios | Sem dados pessoais. Com `texto_relato_publicavel = false`, o texto nem é exibido |

Sinais que o Django já recebe no contrato 1.2.0:
- `dados_pessoais.tipos` da versão **interna** contém `dado_sensivel` quando havia uma característica sensível **sem relação** com o problema, que foi mascarada;
- `texto_relato_publicavel = false` na versão **pública** marca relatos com dado sensível de pessoa identificável.

Lacuna: o contrato não marca, de forma estruturada, que a versão interna **manteve** uma condição para sustentar um fator. Hoje isso fica só no `raciocinio` do fator. Ver a Decisão 4.

## 3. Prazos sugeridos

| Dado | Retenção sugerida | Ao fim do prazo |
|---|---|---|
| `texto_original` com dado sensível sem relação com o problema (`dado_sensivel` em `tipos` da interna) | Até **30 dias** após a conclusão da triagem, para auditoria do mascaramento | Substituir `texto_original` pelo `texto_mascarado` interno. Manter o `hash_texto` |
| `texto_original` sem dado sensível | Enquanto a ocorrência estiver aberta, mais **6 meses** após o encerramento | Substituir pelo `texto_mascarado` interno |
| Condição sensível mantida na versão interna (sustenta um fator) | Enquanto a ocorrência estiver aberta, mais **6 meses** após o encerramento | Trocar a condição por `[DADO_SENSIVEL]` em texto, evidência e raciocínio. Manter nota e status do fator, para que a prioridade continue auditável |
| `id_externo` | Prazo do sistema de origem | Desvincular |
| Versão `publica` | Política de transparência do órgão | Sem ação: não contém dado pessoal |
| Registro de acesso aos dados internos | Prazo de auditoria do órgão | Conforme a política de logs |

Por que "substituir" e não "apagar": a análise continua útil para estatística e para revisão da matriz. O `hash_texto` prova que o texto anonimizado veio daquele relato, sem guardar o relato.

## 4. Acesso enquanto o dado existe

- `texto_original` e versão `interna`: só o perfil de triagem. Cada leitura fica registrada (quem, quando, qual análise).
- Exportação de dados internos: só com justificativa registrada.
- Cópias de segurança: a exclusão deve alcançar os backups no ciclo de rotação, ou eles devem ser cifrados com chave que permita descartar o conteúdo.

## 5. Pedido do titular

O cidadão pode pedir a anonimização ou a eliminação do seu relato. Para atender:
1. localizar o relato pelo `id_externo` ou pelo `hash_texto`, calculado do texto que ele apresentar;
2. aplicar o tratamento de "ao fim do prazo" imediatamente;
3. registrar o atendimento.

A ocorrência urbana (o buraco, a calçada) continua existindo, porque é de interesse coletivo e não depende da identidade de quem relatou.

## 6. Decisões necessárias

1. Validar os prazos com o encarregado de dados e com a tabela de temporalidade municipal.
2. Definir quem executa a rotina de anonimização (tarefa agendada no Django) e com que frequência.
3. Decidir se os backups serão cifrados por registro ou se seguirão a rotação.
4. Decidir se o contrato ganha um marcador estruturado de "condição sensível mantida na versão interna", por exemplo `dados_pessoais.condicao_sensivel_mantida`. Seria uma mudança aditiva (schema 1.3.0). Sem ele, a rotina do item 3 depende de ler os raciocínios.

# Exemplo 3: dados pessoais e versão pública

**O que demonstra:** mascaramento de dados pessoais, separação entre versão interna (equipe) e pública (painel) e o novo critério de falha do próprio serviço essencial (matriz 1.1.0).

## Cole no Claude Code (na raiz do projeto)

```
Chegou pelo app e preciso também de uma versão pública para o painel:

"Oi, sou a Maria Souza, meu telefone é (11) 98888-7777. A coleta de lixo não passa na Rua Pará há duas semanas e o lixo já está acumulando na calçada."
```

## Resultado esperado

| Item | Esperado |
|---|---|
| Categoria | Serviços públicos → Coleta de resíduos (`svc_coleta_residuos`) |
| Tipo de demanda | Problema existente |
| Mascaramento | `[NOME]` e `[TELEFONE]` nas duas versões; o local (Rua Pará) é mantido, porque é onde está o problema |
| Arquivos | JSON interno (com `chmod 600` e fora do Git) e JSON público + relatório público |
| Prioridade | Em geral **média**: a falha do serviço de coleta conta no fator de serviço essencial, e "não passa na rua" conta como rua inteira |

A pontuação exata pode variar um pouco entre execuções, porque fatores **inferidos** dependem de julgamento. O formato, os códigos e o mascaramento não variam.

## O que mostrar

- Abra o JSON público: `texto_original` é `null` e nenhum nome ou telefone aparece.
- Rode o validador nos dois arquivos (comando no `README.md`).

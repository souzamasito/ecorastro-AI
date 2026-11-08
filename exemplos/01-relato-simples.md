# Exemplo 1: relato simples com dano relatado

**O que demonstra:** classificação, prioridade de triagem rastreável e a regra de dano físico relatado (`ex02`), sem inventar data nem endereço.

## Cole no Claude Code (na raiz do projeto)

```
Recebi esse relato pelo app:

"Tem um buraco enorme na Rua das Flores, perto do nº 120. Ontem um motoqueiro caiu ali e se machucou. Com a chuva o buraco tá ficando cada vez maior."

Pode classificar, dizer a prioridade e gerar o JSON do EcoRastro?
```

## Resultado esperado

| Item | Esperado |
|---|---|
| Categoria | Infraestrutura urbana → Buraco ou falha no pavimento (`inf_pavimento`) |
| Tipo de demanda | Problema existente: manutenção ou reparo |
| Prioridade | **Alta** (47 pts): a pontuação cairia em média, mas a queda relatada aciona `ex02` |
| Lacunas | Bairro, município e data ficam "não informados"; "ontem" não vira data porque não há data de recebimento |
| Arquivo | `saidas/json/analise_..._interna.json`, validado sem erros |

## O que mostrar

- A justificativa cita a evidência literal ("um motoqueiro caiu ali e se machucou").
- Fatores sem informação aparecem como **ausentes**, não como zero, e o teto (77 pts) mostra quanto a falta de dados pode esconder.

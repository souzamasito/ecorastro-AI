# Exemplo 2: emergência

**O que demonstra:** risco iminente (`ex01`), nível crítico e alerta de emergência no topo da resposta. A skill **orienta**; não aciona nenhum serviço.

## Cole no Claude Code (na raiz do projeto)

```
Mensagem que acabou de chegar no WhatsApp:

"Caiu um fio do poste na esquina da Av. Brasil com a Rua 7, tá soltando faísca no chão molhado e as crianças tão saindo da escola agora."
```

## Resultado esperado

| Item | Esperado |
|---|---|
| Início da resposta | 🚨 Alerta: acionar Corpo de Bombeiros (193) e a emergência da distribuidora de energia |
| Categoria | Infraestrutura urbana → Rede elétrica (`inf_rede_eletrica`) |
| Prioridade | **Crítica** (`ex01`, também `ex02` e `ex03`) |
| Vulnerabilidade | Crianças relatadas: nota 3 |

## O que mostrar

- O alerta vem antes de qualquer classificação.
- `alerta_emergencia` no JSON lista os serviços, mas a resposta deixa claro que quem está no local deve ligar.

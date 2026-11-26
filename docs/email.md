# E-mail transacional

O backend envia e-mails (boas-vindas, verificação de e-mail, recuperação de senha e alertas) por
meio da interface `EnviadorEmail` (`app/integracoes/email/`), que segue o padrão Adapter.

| `EMAIL_PROVEDOR` | Uso |
|---|---|
| `smtp` | Qualquer servidor SMTP, inclusive o relay dos provedores transacionais (Amazon SES, Brevo, Resend, Postmark) |
| `memoria` | Testes: as mensagens ficam numa lista |

## Desenvolvimento

O `docker compose` de desenvolvimento sobe o **Mailpit**. Todo e-mail enviado aparece em
http://localhost:8025, e nada sai para a internet.

## Produção com um provedor

1. Crie uma conta no provedor e gere credenciais **SMTP** (não use a senha da conta).
2. Configure no `.env`: `SMTP_HOST`, `SMTP_PORTA=587`, `SMTP_TLS=true`, `SMTP_USUARIO`,
   `SMTP_SENHA` e `EMAIL_REMETENTE` (um endereço do seu domínio).
3. Verifique o domínio no provedor e publique os registros de DNS abaixo.

## Registros de DNS (entregabilidade e anti-falsificação)

| Registro | Exemplo | Para quê |
|---|---|---|
| **SPF** (TXT em `@`) | `v=spf1 include:<domínio do provedor> -all` | Diz quais servidores podem enviar pelo seu domínio |
| **DKIM** (CNAME/TXT fornecido pelo provedor) | `<seletor>._domainkey` | Assina as mensagens; prova que não foram alteradas |
| **DMARC** (TXT em `_dmarc`) | `v=DMARC1; p=quarantine; rua=mailto:dmarc@seu-dominio.com; adkim=s; aspf=s` | Diz o que fazer com mensagens que falham em SPF/DKIM e envia relatórios |

Comece com `p=none` por uma ou duas semanas, leia os relatórios e então suba para
`p=quarantine` e depois `p=reject`. Confira com ferramentas como mail-tester.com ou o
"mostrar original" do Gmail (SPF, DKIM e DMARC devem aparecer como `PASS`).

## Regras

- O envio roda fora da requisição (`BackgroundTasks`; fila com Redis na v1.1, #96): a resposta
  não espera o servidor de e-mail, e uma falha de envio não desfaz a operação.
- O destinatário nunca vai para os logs (LGPD).
- Os modelos ficam em `app/integracoes/email/modelos/`, cada um em HTML e em texto puro, com
  escape automático: dados do usuário nunca viram HTML.

# Přihlášení přes bránu (SSO)

Aplikace umí převést identitu od.authentizační brány (Authelia,
Authentik, oauth2-proxy, Caddy forward_auth…). Heslové přihlášení zůstává
funkční jako záloha — bránu tedy nepotřebuješ, pokud to nechceš.

## Jak to funguje

Brána ověří uživatele a teprve pak pustí požadavek na aplikaci. Aplikaci
řekne jméno a (nepovinně) roli **dvěma hlavičkami**:

| hlavička | proměnná | obsah |
|---|---|---|
| jméno účtu | `RPRAXE_SSO_HEADER` (výchozí `Remote-User`) | `lenka` |
| role / skupiny | `RPRAXE_SSO_ROLE_HEADER` | `teachers` → `teacher`, `admins` → `admin` |
| tajemství | `X-Rpraxe-SSO` + `RPRAXE_SSO_SECRET` | dlouhý náhodný řetězec |

Bez správného tajemství se hlavičky **ignorují** — uživatel by si jinak mohl
nasadit vlastní `Remote-User: reditel` v curlu. Tajemství se porovnává
`hmac.compare_digest` (konstantní čas).

Účet se při prvním přihlášení přes bránu založí sám (jako `student`, nebo v roli
z skupinové hlavičky). Heslo takový účet nemá; ať se dosti zpátky i bez brány,
nastav ho admin v **Správa** → *nové heslo*.

## Caddy (forward_auth s Authelia)

```caddy
handle /r-praxe/* {
    forward_auth authelia:9091 {
        uri /api/verify?rd=https://auth.example.eu
        copy_headers Remote-User Remote-Groups Remote-Email
    }
    reverse_proxy rpraxe-app-1:8080 {
        header_up Remote-User {upstream_remote-user}
        header_up Remote-Groups {upstream_remote-groups}
        header_up X-Rpraxe-SSO {env.RPRAXE_SSO_SECRET}
    }
}
```

Seznam hlaviček, které brána skutečně posílá, zjisti krátkým `request_dump`
nebo logem — názvy se u různých bran mírně liší (`Remote-User`,
`X-Authrequest-User`, `X-Forwarded-User`). Aplikaci je řekni v
`RPRAXE_SSO_HEADER` / `RPRAXE_SSO_ROLE_HEADER`.

## Tři věci, které se pokazují nejčastěji

1. **Brána neodstraní cizí `Remote-User`.** Pokud ji klient pošle sám a brána ji
   nepřepíše, útočí jedna hlavička. Brána musí *psát*, ne jen *číst* — ověř
   `curl -H 'Remote-User: kdokoliv' https://…/api/me` a čekай odhlášení/401.
2. **Tajemství unikne do logu.** Nenechávej ho v URL; jde hlavičkou.
3. **Veřejná adresa bez brány.** Pokud je aplikace dostupná přímo (např.
   `:8710`), hlavičky nepomůžou — tajemství sice pomůže, ale jistota je
   pouštět aplikaci jen za bránou nebo na `127.0.0.1`.

## Test

```sh
SEC=… # stejné jako v rpraxe.env
curl -sk -H "Remote-User: pokus" -H "X-Rpraxe-SSO: $SEC" \
     https://sve-nasazeni.example/api/me          # → {"user":"pokus","role":"student"}
curl -sk -H "Remote-User: pokus" https://sve-nasazeni.example/api/me   # → odhlášeno
```

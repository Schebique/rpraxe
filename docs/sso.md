# Přihlášení přes bránu (SSO)

Aplikace umí převzít identitu od authetizační brány (Authelia, Authentik,
oauth2-proxy, Caddy forward_auth…). Přihlášení heslem zůstává funkční jako
záloha — bránu tedy nepotřebuješ, pokud ji nechceš.

Nastavení je **nainstanční**: každé nasazení r-praxe si ho zapne samo v
**Správa → Přihlašování**. Ukládá se do `state/config.json` (mód 600), ne do
obrazu. Proměnnné prostředí slouží jako výchozí hodnota, takže dřívější
nasazení se chovají stejně.

## Kde secret vzít a jak se jmenuje

V rozhraní se pole jmenuje **Heslo brány (shared secret)** — není to heslo
uctove, ani API klíč. Je to dlouhý náhodný řetězec, který si vymyslíš ty
(v instance na kartě *Přihlašování* tlačítkem *vygenerovat heslo brány*, nebo na
serveru `openssl rand -hex 32`) a **stejný** vložíš do nastavení brány. Brána ho
posílá hlavičkou `x-rpraxe-sso`; instance ho porovnává `hmac.compare_digest`.
Protože se neposílá do prohlížeče, dá se měnit bez restartu aplikace.


## Jedna brána před celou doménou

Máš-li víc aplikací pod `*.priklad.example`, vyplatí se dát bránu před ne.
Uživatel se přihlásí jednou a všechny aplikace se dozví jméno a skupiny:

- r-praxe hlavičku přečte, účet založí a roli vezme ze skupiny,
- další aplikace mohou postupovat stejně — `Remote-User` plus sdílené tajemství.

Brána musí u každé aplikace `Remote-User` **přepisovat**, ne jen přidávat, a
každá aplikace má vlastní tajemství — prozrazení jednoho nesmí otevřít ostatní.

## Jak to funguje

Brána ověří uživatele a teprve pak pustí požadavek na aplikaci. Řekne jí jméno
a nepovinně skupiny hlavičkami:

| hlavička | výchozí název | kde se přejmenuje | obsah |
|---|---|---|---|
| jméno účtu | `Remote-User` | Správa → Přihlašování (`RPRAXE_SSO_HEADER`) | `lenka` |
| skupiny / role | `Remote-Groups` | Správa → Přihlašování (`RPRAXE_SSO_ROLE_HEADER`) | `redakce,zaci` |
| tajemství | `X-Rpraxe-SSO` | nastavení brány (`RPRAXE_SSO_SECRET`) | dlouhý náhodný řetězec |

Skupiny se na role mapují ve stejném formuláři, jeden řádek na skupinu:
`redakce=admin`, `pedagogove=teacher`. Bez mapování vznikne účet se rolí
`student`.

Bez správného tajemství se hlavičky **ignorují** — uživatel by si jinak mohl
poslat vlastní `Remote-User: reditel` v curlu. Tajemství se porovnává
`hmac.compare_digest` (konstantní čas).

Účet se při prvním přihlášení přes bránu založí sám a heslo nemá. Aby se
člověk dostal i bez brány, nastaví mu heslo správce v **Správa → Účty**.

## Caddy (forward_auth s Authelií)

```caddy
handle /r-praxe/* {
    forward_auth authelia:9091 {
        uri /api/verify?rd=https://auth.priklad.example
        copy_headers Remote-User Remote-Groups Remote-Email
    }
    reverse_proxy rpraxe-app:8080 {
        header_up Remote-User {upstream_remote-user}
        header_up Remote-Groups {upstream_remote-groups}
        header_up X-Rpraxe-SSO {env.RPRAXE_SSO_SECRET}
    }
}
```

Názvy hlaviček, které tvá brána doopravdy posílá, si ověř dumpem requestu nebo
logem — liší se (`Remote-User`, `X-Authrequest-User`, `X-Forwarded-User`).
Do aplikace je zapíšeš ve formuláři Přihlašování; stejné okno ukáže i sondu,
takže vidíš, jaké hlavičky přišly s tvým aktuálním požadavkem.

## Tři věci, které se pokazují nejčastěji

1. **Brána neodstraní cizí `Remote-User`.** Kdyby klient poslal hlavičku sám a
   brána ji nepřepsala, rozhoduje jedna hlavička. Ověř to:
   `curl -H 'Remote-User: kdokoliv' https…/api/whoami` — musí hlásit odhlášení.
2. **Tajemství unikne do logu.** Nepatří do URL, jen do hlavičky.
3. **Aplikace je dostupná i mimo bránu.** Kdyby někdo sahal přímo na `:8710`,
   hlavičky nepomůžou. Poušti aplikaci na `127.0.0.1`, na vnitřní rozhraní
   nebo za bránu — a tajemství měj stejně.

## Test

```sh
SEC=…   # stejné tajemství, jaké nastavila brána
curl -sk -H "Remote-User: pokus" -H "X-Rpraxe-SSO: $SEC" https://…/api/whoami
# → {"user":"pokus","role":"student"}
curl -sk -H "Remote-User: pokus" https://…/api/whoami
# → odhlášeno, tajemství chybí
```

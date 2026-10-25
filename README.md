# NIPOS

Non Integrated Point of Sale, online version. Served at https://nipos.github.io/production/ (live) and https://nipos.github.io/staging/ (testing)

The root page redirects to `production/index.html`.

## Production and staging

- `production/`: the live NIPOS, on the live database. Copied from KeystoneGD.github.io/NIPOS after each change.
- `staging/`: where development happens, on the separate **NIPOS Staging** database (`lneypwbdsvfmmpyjwwcu`) with
  its own push keys. Everything it saves in the browser is filed under `nipos-staging:` so it never mixes with
  production on a shared device, and every page shows a STAGING badge.

Moving changes between them:

| Command | What it does |
|---|---|
| `python3 tools/promote.py` | Lists the production files a promotion would change |
| `python3 tools/promote.py --apply` | Copies staging into production, taking the staging-only parts out |
| `python3 tools/reset-staging.py` | Rebuilds staging from production; refuses if staging has unpromoted changes |

Both stop without writing anything if the result could reach the other side's database.

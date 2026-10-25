# NIPOS

Non Integrated Point of Sale, online version. Served at https://nipos.github.io/production/ (live) and https://nipos.github.io/staging/ (testing)

The root page redirects to `production/index.html`.

## Production and staging

- `production/`: the live NIPOS, on the live database. Copied from KeystoneGD.github.io/NIPOS after each change.
- `staging/`: for trying changes first. Built from production with `python3 tools/build-staging.py`, which points it
  at the separate **NIPOS Staging** database (`lneypwbdsvfmmpyjwwcu`), gives it its own push keys, and files
  everything it saves in the browser under `nipos-staging:` so it never mixes with production on a shared device.
  Every staging page shows a STAGING badge. The build refuses to write staging if any page could still reach the
  production database.

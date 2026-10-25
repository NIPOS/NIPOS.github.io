#!/usr/bin/env python3
"""Copies staging/ into production/ once a change has been tested on staging.

    python3 tools/promote.py           shows which production files would change
    python3 tools/promote.py --apply   writes them

Takes the staging-only parts out on the way (the staging database, keys, storage guard, badge and
STAGING names) and stops without writing if anything staging-only would reach production.
"""
import sys
from nipos_env import *

prod_anon, prod_vapid = production_keys()
new = to_production(read_tree(STAGING_DIR), prod_anon, prod_vapid)
old = read_tree(PROD_DIR)
diff = changed(old, new)
if not diff: print("production/ already matches staging/. Nothing to promote."); sys.exit(0)
print("Production files that change:\n  " + "\n  ".join(diff))
if "--apply" not in sys.argv: print("\nRun again with --apply to write them."); sys.exit(0)
write_tree(PROD_DIR, new)
print(f"\nproduction/ updated from staging/ ({len(diff)} files).")

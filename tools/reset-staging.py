#!/usr/bin/env python3
"""Rebuilds staging/ from production/, throwing away anything on staging that production doesn't have.

    python3 tools/reset-staging.py             refuses if staging has changes production doesn't
    python3 tools/reset-staging.py --discard   rebuilds anyway, losing those changes

Use it after something was changed straight on production, or to start staging again from scratch.
"""
import sys
from nipos_env import *

prod_anon, prod_vapid = production_keys()
prod = read_tree(PROD_DIR)
fresh = to_staging(prod, prod_anon, prod_vapid)
current = read_tree(STAGING_DIR) if STAGING_DIR.is_dir() else {}
ahead = changed(fresh, current)
if ahead and "--discard" not in sys.argv:
    die("staging/ has changes production doesn't:\n  " + "\n  ".join(ahead) + "\nPromote them first (tools/promote.py), or run with --discard to lose them")
write_tree(STAGING_DIR, fresh)
print(f"staging/ rebuilt from production/: {len(fresh)} files, database {STAGING_REF}")

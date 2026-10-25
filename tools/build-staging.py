#!/usr/bin/env python3
"""Builds staging/ from production/: the same NIPOS, pointed at the NIPOS Staging database.

    python3 tools/build-staging.py

Staging and production share this website (nipos.github.io), so a device that opens both shares one
browser storage. To keep them apart, every staging page:
  - talks only to the NIPOS Staging Supabase project (its own data, sign-ins and push keys),
  - files everything it saves in the browser under "nipos-staging:" (sign-in, unsent sales, basket,
    venue, settings), so it can never read or send production's, and production never sees staging's,
  - shows a STAGING badge and "STAGING" in its tab title and app name.
The build stops without writing anything if production's database address would survive in staging.
"""
import pathlib, re, shutil, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC, OUT = ROOT / "production", ROOT / "staging"

PROD_REF, STAGING_REF = "djegigghjeisoyecxeyo", "lneypwbdsvfmmpyjwwcu"
STAGING_ANON = ("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxuZXlwd2Jkc3ZmbW1weWp3d2N1Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTI5MjQ2MjUsImV4cCI6MjEwODUwMDYyNX0"
                ".AZzWvRIsU3VJIzg5Jt8fQeHCfpIaW_1NhpCTv4nP7YA")
STAGING_VAPID_PUBLIC = "BPWP-PNf0MQqzrHbDSTdPTEPcjDCshv6t-u9OY-12-eF7k2vlxEeMH35JRjDbwcy9CJ8-_ZhKsfpbgLWMh7nv7o"

# First thing in every page's <head>, before any script reads or writes browser storage.
GUARD = """<script>
/* STAGING copy of NIPOS. Everything it saves in this browser is filed under "nipos-staging:", so it
   stays apart from production, which shares this website. */
(function () {
  var P = "nipos-staging:", S = Storage.prototype, g = S.getItem, s = S.setItem, r = S.removeItem;
  S.getItem = function (k) { return g.call(this, P + k); };
  S.setItem = function (k, v) { return s.call(this, P + k, v); };
  S.removeItem = function (k) { return r.call(this, P + k); };
  // The pages rename their own tab (venue, screen); keep STAGING at the front of it.
  function tag() { if (document.title.indexOf("STAGING") !== 0) document.title = "STAGING · " + document.title; }
  new MutationObserver(tag).observe(document.documentElement, { subtree: true, childList: true, characterData: true });
  document.addEventListener("DOMContentLoaded", function () {
    tag();
    var b = document.createElement("div");
    b.textContent = "STAGING";
    b.setAttribute("aria-hidden", "true");
    b.style.cssText = "position:fixed;top:max(4px, env(safe-area-inset-top, 0px));left:50%;transform:translateX(-50%);z-index:2147483647;pointer-events:none;background:#e65100;color:#fff;font:800 11px/1 system-ui,sans-serif;letter-spacing:.14em;padding:4px 10px;border-radius:0 0 6px 6px;opacity:.92";
    document.body.appendChild(b);
  });
})();
</script>
"""

def die(msg):
    sys.exit("build-staging: " + msg + " (nothing was written)")

def build():
    if not SRC.is_dir(): die("production/ not found")
    files = {}
    for p in SRC.rglob("*"):
        if p.is_file(): files[p.relative_to(SRC)] = p.read_bytes()

    def text(rel, fn):
        s = files[rel].decode("utf-8")
        files[rel] = fn(s).encode("utf-8")

    def db_js(s):
        url = f'const SUPABASE_URL = "https://{PROD_REF}.supabase.co";'
        if url not in s: die("db.js: production database address not where expected")
        s = s.replace(url, f'const SUPABASE_URL = "https://{STAGING_REF}.supabase.co";')
        s, n = re.subn(r'const SUPABASE_ANON_KEY = "[^"]+";', f'const SUPABASE_ANON_KEY = "{STAGING_ANON}";', s)
        if n != 1: die("db.js: anon key not where expected")
        return s
    text(pathlib.Path("db.js"), db_js)

    for rel in list(files):
        if rel.suffix == ".html":
            def page(s):
                s, n = re.subn(r"<head>", "<head>\n" + GUARD, s, count=1)
                if n != 1: die(f"{rel}: no <head>")
                s = re.sub(r"<title>(.*?)</title>", lambda m: f"<title>STAGING · {m.group(1)}</title>", s, count=1)
                s = re.sub(r'const VAPID_PUBLIC_KEY = "[^"]+";', f'const VAPID_PUBLIC_KEY = "{STAGING_VAPID_PUBLIC}";', s)
                # The push sender and anything else addressed to the database directly.
                s = s.replace(f"{PROD_REF}.supabase.co", f"{STAGING_REF}.supabase.co").replace(PROD_REF, STAGING_REF)
                return s.replace("nipos.github.io/production", "nipos.github.io/staging")
            text(rel, page)
        elif rel.suffix == ".json" and rel.name.startswith("manifest"):
            text(rel, lambda s: re.sub(r'"(name|short_name)":\s*"', r'"\1": "STAGING ', s))
        elif rel.suffix in (".js", ".ts", ".css", ".sql"):
            text(rel, lambda s: s.replace("nipos.github.io/production", "nipos.github.io/staging"))

    # Never publish a staging page that could reach the production database or push keys.
    prod_vapid = re.search(r'const VAPID_PUBLIC_KEY = "([^"]+)"', (SRC / "index.html").read_text())
    for rel, b in files.items():
        if rel.parts[0] == "supabase": continue  # server code, not served to devices
        if PROD_REF.encode() in b: die(f"{rel} still mentions the production database")
        if prod_vapid and prod_vapid.group(1).encode() in b: die(f"{rel} still has production's push key")

    if OUT.exists(): shutil.rmtree(OUT)
    for rel, b in files.items():
        dest = OUT / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(b)
    print(f"staging/ built from production/: {len(files)} files, database {STAGING_REF}")

build()

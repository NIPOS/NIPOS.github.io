"""Shared by tools/promote.py and tools/reset-staging.py: turning production's files into staging's,
and staging's back into production's.

Staging and production share this website (nipos.github.io), so a device that opens both shares one
browser storage. To keep them apart, every staging page:
  - talks only to the NIPOS Staging Supabase project (its own data, sign-ins and push keys),
  - files everything it saves in the browser under "nipos-staging:" (sign-in, unsent sales, basket,
    venue, settings), so it can never read or send production's, and production never sees staging's,
  - shows a STAGING badge and "STAGING" in its tab title and app name.
Both directions check their result and stop, writing nothing, if the other side's database could
still be reached.
"""
import pathlib, re, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
PROD_DIR, STAGING_DIR = ROOT / "production", ROOT / "staging"

PROD_REF, STAGING_REF = "djegigghjeisoyecxeyo", "lneypwbdsvfmmpyjwwcu"
STAGING_ANON = ("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxuZXlwd2Jkc3ZmbW1weWp3d2N1Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTI5MjQ2MjUsImV4cCI6MjEwODUwMDYyNX0"
                ".AZzWvRIsU3VJIzg5Jt8fQeHCfpIaW_1NhpCTv4nP7YA")
STAGING_VAPID_PUBLIC = "BPWP-PNf0MQqzrHbDSTdPTEPcjDCshv6t-u9OY-12-eF7k2vlxEeMH35JRjDbwcy9CJ8-_ZhKsfpbgLWMh7nv7o"

# First thing in every staging page's <head>, before any script reads or writes browser storage.
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

ANON_RE = re.compile(r'const SUPABASE_ANON_KEY = "([^"]+)";')
VAPID_RE = re.compile(r'const VAPID_PUBLIC_KEY = "([^"]+)";')

def die(msg):
    sys.exit(msg + " (nothing was written)")

def read_tree(d):
    if not d.is_dir(): die(f"{d.name}/ not found")
    return {p.relative_to(d): p.read_bytes() for p in d.rglob("*") if p.is_file()}

def write_tree(d, files):
    import shutil
    if d.exists(): shutil.rmtree(d)
    for rel, b in files.items():
        dest = d / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(b)

def production_keys():
    """Production's own public anon key and push key, read from production as it stands."""
    db = (PROD_DIR / "db.js").read_text(); idx = (PROD_DIR / "index.html").read_text()
    a, v = ANON_RE.search(db), VAPID_RE.search(idx)
    if not a or not v or PROD_REF not in db: die("production/ doesn't have its database settings where expected")
    return a.group(1), v.group(1)

def _map_text(files, fn_html, fn_other):
    out = {}
    for rel, b in files.items():
        if rel.suffix == ".html": out[rel] = fn_html(rel, b.decode("utf-8")).encode("utf-8")
        elif rel.suffix in (".js", ".ts", ".css", ".sql", ".json"): out[rel] = fn_other(rel, b.decode("utf-8")).encode("utf-8")
        else: out[rel] = b
    return out

def to_staging(files, prod_anon, prod_vapid):
    def html(rel, s):
        s, n = re.subn(r"<head>", "<head>\n" + GUARD, s, count=1)
        if n != 1: die(f"{rel}: no <head>")
        s = re.sub(r"<title>(.*?)</title>", lambda m: f"<title>STAGING · {m.group(1)}</title>", s, count=1)
        return common(s).replace(prod_vapid, STAGING_VAPID_PUBLIC)
    def common(s):
        return s.replace(prod_anon, STAGING_ANON).replace(PROD_REF, STAGING_REF).replace("nipos.github.io/production", "nipos.github.io/staging")
    def other(rel, s):
        if rel.name.startswith("manifest") and rel.suffix == ".json": s = re.sub(r'"(name|short_name)":\s*"', r'"\1": "STAGING ', s)
        return common(s)
    out = _map_text(files, html, other)
    check(out, [PROD_REF, prod_anon, prod_vapid], "staging", skip_server=True)
    return out

def to_production(files, prod_anon, prod_vapid):
    def html(rel, s):
        if ("<head>\n" + GUARD) not in s: die(f"staging/{rel}: the staging guard isn't where expected, so it can't be taken out safely")
        s = s.replace("<head>\n" + GUARD, "<head>", 1)
        s = s.replace("<title>STAGING · ", "<title>", 1)
        return common(s).replace(STAGING_VAPID_PUBLIC, prod_vapid)
    def common(s):
        return s.replace(STAGING_ANON, prod_anon).replace(STAGING_REF, PROD_REF).replace("nipos.github.io/staging", "nipos.github.io/production")
    def other(rel, s):
        if rel.name.startswith("manifest") and rel.suffix == ".json": s = re.sub(r'"(name|short_name)": "STAGING ', r'"\1": "', s)
        return common(s)
    out = _map_text(files, html, other)
    check(out, [STAGING_REF, STAGING_ANON, STAGING_VAPID_PUBLIC, "nipos-staging:", ">STAGING<"], "production", skip_server=False)
    return out

def check(files, forbidden, side, skip_server):
    for rel, b in files.items():
        if skip_server and rel.parts[0] == "supabase": continue  # server code, not served to devices
        for f in forbidden:
            if f.encode() in b: die(f"{side}/{rel} would still contain {f[:24]}")

def changed(before, after):
    keys = set(before) | set(after)
    return sorted(str(k) for k in keys if before.get(k) != after.get(k))

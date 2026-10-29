"""Cocokkan trueorfalse.py dengan mesin JavaScript asli (Chrome/Chromium headless) pada semua pasangan nilai x operator.

Opsional (butuh Chrome atau Chromium terpasang):
    python crosscheck_js.py
Bila Chrome ada di lokasi tak standar, isi variabel lingkungan CHROME_PATH.
Hasil terakhir: 17.672 perbandingan, 0 selisih.
"""
import itertools
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from trueorfalse import OPERATORS, compare, make_value

SPECS = (
    [("string", s) for s in ["", " ", "0", "1", "01", "10", "9", "-1", "abc", "a", "Z", "true", "false", "0x10", "0b11",
                              "1e3", "1_0", "1,5", "Infinity", "-Infinity", "infinity", "nan", " 12 ", "\t7\n", "null",
                              "undefined", ".5", "5.", "+3", "\U0001F600", "\uFF5E"]]
    + [("number", n) for n in ["0", "1", "-1", "9", "10", "16", "1000", "0.5", "NaN", "Infinity", "-Infinity", "12"]]
    + [("boolean", "true"), ("boolean", "false"), ("null", ""), ("undefined", "")]
)

CHROME_CANDIDATES = (
    os.environ.get("CHROME_PATH"), shutil.which("google-chrome"), shutil.which("chromium"), shutil.which("chrome"),
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
)

PAGE = """<!DOCTYPE html><meta charset="utf-8"><body><pre id="out"></pre><script>
const specs = %s, ops = %s;
function mk(t, v) {
  if (t === 'string') return v;
  if (t === 'number') return Number(v);
  if (t === 'boolean') return v === 'true';
  if (t === 'null') return null;
  return undefined;
}
function cmp(a, op, b) {
  switch (op) {
    case '===': return a === b; case '!==': return a !== b;
    case '==': return a == b;   case '!=': return a != b;
    case '<': return a < b;     case '>': return a > b;
    case '<=': return a <= b;   case '>=': return a >= b;
  }
}
const out = [];
for (const [lt, lv] of specs) for (const [rt, rv] of specs) for (const op of ops) out.push(cmp(mk(lt, lv), op, mk(rt, rv)) ? 1 : 0);
document.getElementById('out').textContent = 'RESULT:' + out.join('');
</script></body>"""


def main():
    chrome = next((p for p in CHROME_CANDIDATES if p and os.path.exists(p)), None)
    if not chrome:
        print("Chrome/Chromium tidak ditemukan; isi CHROME_PATH.")
        return 2
    combos = list(itertools.product(SPECS, SPECS, OPERATORS))
    python_results = [compare(make_value(lv, lt), op, make_value(rv, rt)) for (lt, lv), (rt, rv), op in combos]

    with tempfile.TemporaryDirectory() as folder:
        page = os.path.join(folder, "t.html")
        with open(page, "w", encoding="utf-8") as file:
            file.write(PAGE % (json.dumps(SPECS), json.dumps(list(OPERATORS))))
        dom = subprocess.run(
            [chrome, "--headless", "--disable-gpu", f"--user-data-dir={os.path.join(folder, 'profile')}",
             "--dump-dom", "file:///" + page.replace("\\", "/")],
            capture_output=True, text=True, timeout=120).stdout
    match = re.search(r"RESULT:([01]+)", dom)
    if not match:
        print("Tidak ada hasil dari Chrome:", dom[:300])
        return 2
    js_results = [c == "1" for c in match.group(1)]
    print(f"perbandingan: {len(python_results)} (nilai: {len(SPECS)}, operator: {len(OPERATORS)}), hasil JS: {len(js_results)}")
    bad = [(combos[i], p, j) for i, (p, j) in enumerate(zip(python_results, js_results)) if p != j]
    print("selisih:", len(bad))
    for item in bad[:20]:
        print(item)
    return 1 if bad or len(js_results) != len(python_results) else 0


if __name__ == "__main__":
    sys.exit(main())

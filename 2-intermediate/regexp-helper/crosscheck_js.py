"""Bandingkan hasil regex_helper.run() dengan RegExp JavaScript asli di Chrome (headless).

Setiap kombinasi pola x teks x flag x fungsi dijalankan di Python dan di mesin V8,
lalu hasilnya dibandingkan. Butuh Google Chrome.

Jalankan:
    python crosscheck_js.py
"""

import html
import itertools
import json
import os
import re
import subprocess
import sys
import tempfile

import regex_helper

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
PATTERNS = [r"\d+", r"a", r"^b", r"o$", r"\w+@\w+\.com", r"(\d{4})-(\d{2})", r"(?<y>\d{4})", r"x*", r"[A-Z]",
            r"a.c", r"\bkata\b", r"(ab)+", r"\s"]
TEXTS = ["ada 12 apel dan 3 jeruk", "banana\nbonbon", "Hello WORLD", "abc\na\nc", "mail: andi@kopi.com, sari@teh.com",
         "2023-10 dan 2024-01", "kata kata, katakan", "ababab ab", "12a3"]
FLAG_SETS = ["", "g", "i", "m", "gi", "gm", "s", "y", "gy"]

SCRIPT = """<html><body><script>
const C = %s; const out = [];
for (const [p, t, f, fn] of C) {
  const r = new RegExp(p, f); let v;
  if (fn === "test") v = r.test(t);
  else if (fn === "search") v = t.search(r);
  else { const m = t.match(r); v = m === null ? null : Array.from(m).map(x => x === undefined ? null : x); }
  out.push(v);
}
document.body.textContent = JSON.stringify(out);
</script></body></html>"""


def main():
    cases = list(itertools.product(PATTERNS, TEXTS, FLAG_SETS, regex_helper.FUNCTIONS))
    with tempfile.TemporaryDirectory() as tmp:
        page = os.path.join(tmp, "regex.html")
        with open(page, "w", encoding="utf-8") as handle:
            handle.write(SCRIPT % json.dumps(cases))
        dom = subprocess.run([CHROME, "--headless", "--disable-gpu", f"--user-data-dir={tmp}\\chrome",
                              "--dump-dom", "file:///" + page.replace("\\", "/")],
                             capture_output=True, text=True, encoding="utf-8", timeout=120).stdout
    expected = json.loads(html.unescape(re.search(r"<body>(.*)</body>", dom, re.S).group(1)))
    differences = [(case, regex_helper.run(*case).value, js) for case, js in zip(cases, expected)
                   if regex_helper.run(*case).value != js]
    for case, python_value, js_value in differences[:20]:
        print(f"BEDA {case}: Python={python_value!r} JavaScript={js_value!r}")
    print(f"{len(cases)} kasus dibandingkan, {len(differences)} berbeda.")
    return 1 if differences else 0


if __name__ == "__main__":
    sys.exit(main())

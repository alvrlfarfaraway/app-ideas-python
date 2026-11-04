"""Markdown Previewer: tulis Markdown ala GitHub, lihat hasil HTML-nya di sebelahnya.

Markdown dirender di Python (mistune, dengan plugin tabel, coret, daftar tugas,
auto-link, dan catatan kaki). Program menjalankan server lokal kecil
(http.server) lalu membuka halaman editor di browser. Halaman hanya mengirim
teks ke server dan menampilkan HTML yang dikembalikan.

Jalankan:
    python md_preview.py                      # buka editor di browser
    python md_preview.py --port 8765 --no-browser
    python md_preview.py catatan.md -o catatan.html   # render berkas tanpa server
"""

import argparse
import html
import sys
import threading
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import mistune

MAX_BYTES = 1_000_000
PLUGINS = ["strikethrough", "table", "task_lists", "url", "footnotes"]
# escape=True: HTML mentah di dalam Markdown ditampilkan sebagai teks, bukan dijalankan.
_markdown = mistune.create_markdown(escape=True, plugins=PLUGINS)

SAMPLE = """# Markdown Previewer

Tulis **Markdown ala GitHub** di kiri, hasilnya muncul di kanan.

## Yang didukung

- [x] Judul, *miring*, **tebal**, ~~coret~~, dan `kode`
- [x] Tabel, daftar tugas, dan catatan kaki[^1]
- [ ] Tugas yang belum selesai

| Bahasa | Dipakai untuk | Tahun |
| :--- | :---: | ---: |
| Python | data & skrip | 1991 |
| JavaScript | web | 1995 |

```python
def halo(nama):
    return f"Halo, {nama}!"
```

> Tautan seperti https://www.python.org langsung bisa diklik.

[^1]: Catatan kaki muncul di bagian bawah.
"""

PREVIEW_CSS = """
.markdown-body { font: 16px/1.6 -apple-system, "Segoe UI", system-ui, sans-serif; color: var(--text); word-wrap: break-word; }
.markdown-body h1, .markdown-body h2 { border-bottom: 1px solid var(--line); padding-bottom: .3em; }
.markdown-body h1 { font-size: 2em; margin: .2em 0 .6em; }
.markdown-body h2 { font-size: 1.5em; margin: 1.2em 0 .6em; }
.markdown-body a { color: var(--accent); }
.markdown-body code { font: 85% ui-monospace, Consolas, monospace; background: var(--code); padding: .2em .4em; border-radius: 6px; }
.markdown-body pre { background: var(--code); padding: 16px; border-radius: 6px; overflow: auto; }
.markdown-body pre code { background: none; padding: 0; font-size: 85%; }
.markdown-body blockquote { margin: 0; padding: 0 1em; color: var(--muted); border-left: .25em solid var(--line); }
.markdown-body table { border-collapse: collapse; display: block; overflow: auto; }
.markdown-body th, .markdown-body td { border: 1px solid var(--line); padding: 6px 13px; }
.markdown-body tr:nth-child(2n) { background: var(--code); }
.markdown-body li.task-list-item { list-style: none; }
.markdown-body li.task-list-item input { margin: 0 .4em 0 -1.4em; }
.markdown-body img { max-width: 100%; }
.markdown-body .footnotes { font-size: 85%; color: var(--muted); border-top: 1px solid var(--line); margin-top: 2em; }
"""

THEME_CSS = """
:root { color-scheme: light dark; --bg: #f6f8fa; --panel: #ffffff; --text: #1f2328; --muted: #59636e;
        --line: #d1d9e0; --accent: #0969da; --code: #f6f8fa; }
@media (prefers-color-scheme: dark) {
  :root { --bg: #0d1117; --panel: #161b22; --text: #e6edf3; --muted: #9198a1; --line: #30363d;
          --accent: #4493f8; --code: #1f242c; }
}
"""


def render(text):
    """Markdown -> potongan HTML (aman: HTML mentah di-escape, tautan javascript: dibuang)."""
    return _markdown(text)


def document(text, title="Markdown"):
    """Halaman HTML utuh untuk satu berkas Markdown (dipakai mode -o)."""
    return f"""<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<style>{THEME_CSS}
body {{ margin: 0; background: var(--panel); }}
main {{ max-width: 860px; margin: auto; padding: 32px 20px; }}
{PREVIEW_CSS}</style>
</head>
<body><main class="markdown-body">
{render(text)}</main></body>
</html>
"""


EDITOR_PAGE = """<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Markdown Previewer</title>
<style>__THEME__
* { box-sizing: border-box; }
body { margin: 0; font: 15px/1.4 "Segoe UI", system-ui, sans-serif; background: var(--bg); color: var(--text);
       height: 100vh; display: flex; flex-direction: column; }
header { display: flex; flex-wrap: wrap; gap: 10px; align-items: center; padding: 10px 16px; border-bottom: 1px solid var(--line); }
header h1 { font-size: 1.05rem; margin: 0 auto 0 0; }
button { font: inherit; padding: 6px 14px; border-radius: 6px; border: 1px solid var(--line); background: var(--panel);
         color: var(--text); cursor: pointer; }
button.primary { background: var(--accent); border-color: var(--accent); color: #fff; }
label { display: inline-flex; gap: 6px; align-items: center; color: var(--muted); }
#status { color: var(--muted); font-size: .9em; min-width: 9em; }
main { flex: 1; display: grid; grid-template-columns: 1fr 1fr; min-height: 0; }
@media (max-width: 760px) { main { grid-template-columns: 1fr; grid-template-rows: 1fr 1fr; } }
textarea { width: 100%; height: 100%; resize: none; border: 0; border-right: 1px solid var(--line); padding: 16px;
           font: 14px/1.5 ui-monospace, Consolas, monospace; background: var(--panel); color: var(--text); outline: none; }
#preview { overflow: auto; padding: 16px 24px; background: var(--panel); }
__PREVIEW__
</style>
</head>
<body>
<header>
  <h1>Markdown Previewer</h1>
  <button class="primary" id="render">Preview</button>
  <label><input type="checkbox" id="auto" checked> Otomatis</label>
  <button id="copy">Salin HTML</button>
  <span id="status" role="status"></span>
</header>
<main>
  <textarea id="source" spellcheck="false" aria-label="Markdown"></textarea>
  <article id="preview" class="markdown-body" aria-label="Hasil HTML"></article>
</main>
<script>
const KEY = "md-preview-text";
const source = document.getElementById("source");
const preview = document.getElementById("preview");
const status = document.getElementById("status");
const auto = document.getElementById("auto");
let lastHtml = "";
let timer = null;

async function renderNow() {
  const response = await fetch("/render", { method: "POST", body: source.value,
                                            headers: { "Content-Type": "text/plain; charset=utf-8" } });
  if (!response.ok) { status.textContent = "Gagal: " + (await response.text()); return; }
  lastHtml = await response.text();
  preview.innerHTML = lastHtml;  // HTML sudah dibersihkan di server (escape=True)
  status.textContent = "Diperbarui " + new Date().toLocaleTimeString("id-ID");
}

function save() { localStorage.setItem(KEY, source.value); }

source.addEventListener("input", () => {
  save();
  if (auto.checked) { clearTimeout(timer); timer = setTimeout(renderNow, 250); }
});
document.getElementById("render").addEventListener("click", renderNow);
document.getElementById("copy").addEventListener("click", async () => {
  try { await navigator.clipboard.writeText(lastHtml); status.textContent = "HTML disalin ke clipboard"; }
  catch (error) { status.textContent = "Tidak bisa menyalin: " + error.message; }
});
window.addEventListener("beforeunload", save);

const params = new URLSearchParams(location.search);
const saved = localStorage.getItem(KEY);
source.value = params.has("contoh") || saved === null ? __SAMPLE__ : saved;
save();
renderNow();
</script>
</body>
</html>
"""


def editor_page():
    import json

    return (EDITOR_PAGE.replace("__THEME__", THEME_CSS).replace("__PREVIEW__", PREVIEW_CSS)
            .replace("__SAMPLE__", json.dumps(SAMPLE).replace("</", "<\\/")))


class Handler(BaseHTTPRequestHandler):
    server_version = "MarkdownPreviewer/1.0"

    def _send(self, status, body, content_type="text/html; charset=utf-8"):
        data = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path.split("?", 1)[0] == "/":
            self._send(HTTPStatus.OK, editor_page())
        else:
            self._send(HTTPStatus.NOT_FOUND, "Tidak ditemukan", "text/plain; charset=utf-8")

    def do_POST(self):
        if self.path != "/render":
            self._send(HTTPStatus.NOT_FOUND, "Tidak ditemukan", "text/plain; charset=utf-8")
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = -1
        if not 0 <= length <= MAX_BYTES:
            self._send(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "Teks terlalu besar (maksimal 1 MB).",
                       "text/plain; charset=utf-8")
            return
        text = self.rfile.read(length).decode("utf-8", "replace")
        self._send(HTTPStatus.OK, render(text))

    def log_message(self, format, *args):  # jangan memenuhi terminal dengan log tiap permintaan
        pass


def make_server(port=0):
    """Server hanya di 127.0.0.1 (tidak bisa diakses dari komputer lain). port=0: pilih port bebas."""
    return ThreadingHTTPServer(("127.0.0.1", port), Handler)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Editor Markdown dengan pratinjau HTML.")
    parser.add_argument("file", nargs="?", help="berkas .md yang dirender (bersama -o)")
    parser.add_argument("-o", "--output", help="tulis hasil render ke berkas HTML, tanpa server")
    parser.add_argument("--port", type=int, default=0, help="port server (bawaan: pilih otomatis)")
    parser.add_argument("--no-browser", action="store_true", help="jangan membuka browser otomatis")
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    if args.file or args.output:
        if not (args.file and args.output):
            parser.error("mode berkas butuh nama berkas .md dan -o hasil.html")
        try:
            with open(args.file, encoding="utf-8") as handle:
                text = handle.read()
            with open(args.output, "w", encoding="utf-8") as handle:
                handle.write(document(text, title=args.file))
        except OSError as error:
            print(f"Error: {error}", file=sys.stderr)
            return 1
        print(f"HTML ditulis ke {args.output}")
        return 0
    server = make_server(args.port)
    url = f"http://127.0.0.1:{server.server_address[1]}/"
    print(f"Markdown Previewer berjalan di {url}  (Ctrl+C untuk berhenti)")
    if not args.no_browser:
        threading.Timer(0.3, webbrowser.open, (url,)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer dihentikan.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

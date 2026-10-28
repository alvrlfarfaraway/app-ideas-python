"""GitHub Status: tampilkan status komponen GitHub saat ini dari githubstatus.com.

Memakai API JSON resmi githubstatus.com (bukan scraping HTML) lewat urllib bawaan Python,
jadi tidak butuh paket tambahan.

Jalankan:
    python github_status.py            # ambil dan tampilkan sekali
    python github_status.py -i         # interaktif: Enter = 'Get Status' lagi, q = keluar
    python github_status.py --no-color
"""

import argparse
import json
import sys
import urllib.error
import urllib.request

URL = "https://www.githubstatus.com/api/v2/components.json"

LABELS = {
    "operational": "Operational",
    "degraded_performance": "Degraded performance",
    "partial_outage": "Partial outage",
    "major_outage": "Major outage",
    "under_maintenance": "Under maintenance",
}
RED, YELLOW, GREEN, RESET = "\x1b[31;1m", "\x1b[33;1m", "\x1b[32m", "\x1b[0m"
COLORS = {"operational": GREEN, "degraded_performance": YELLOW, "under_maintenance": YELLOW,
          "partial_outage": RED, "major_outage": RED}


def fetch_status(url=URL, urlopen=urllib.request.urlopen):
    """Ambil JSON status. ValueError dengan pesan ramah kalau jaringan atau data bermasalah."""
    try:
        with urlopen(url, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        raise ValueError(f"githubstatus.com menjawab kode {error.code}.") from None
    except (urllib.error.URLError, TimeoutError):
        raise ValueError("Tidak bisa menjangkau githubstatus.com. Periksa koneksi internet.") from None
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise ValueError("Jawaban githubstatus.com bukan JSON yang valid.") from None


def parse_components(data):
    """Daftar (nama, status) komponen sesungguhnya; entri 'grup' dan baris tautan 'Visit ...' dilewati."""
    try:
        return [(item["name"], item["status"]) for item in data["components"]
                if not item.get("group") and not item["name"].startswith("Visit ")]
    except (KeyError, TypeError):
        raise ValueError("Format data status tidak dikenali.") from None


def format_status(components, color=True):
    """Satu baris per komponen; yang bukan 'Operational' ditandai warna dan simbol agar mencolok."""
    width = max((len(name) for name, _ in components), default=0)
    lines = []
    for name, status in components:
        label = LABELS.get(status, status.replace("_", " ").capitalize())
        ok = status == "operational"
        mark = "✔" if ok else "▲"
        text = f"{mark} {name:<{width}}  {label}"
        if color:
            text = f"{COLORS.get(status, YELLOW)}{text}{RESET}"
        lines.append(text)
    problems = sum(1 for _, status in components if status != "operational")
    lines.append("")
    lines.append("Semua komponen operasional." if not problems else f"{problems} komponen bermasalah.")
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Status GitHub saat ini.")
    parser.add_argument("-i", "--interactive", action="store_true", help="tekan Enter untuk mengambil ulang")
    parser.add_argument("--no-color", action="store_true", help="tanpa warna ANSI")
    args = parser.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")  # simbol tidak membuat error di konsol non-UTF-8
    color = not args.no_color and sys.stdout.isatty()
    exit_code = 0
    while True:
        try:
            print(format_status(parse_components(fetch_status()), color))
            exit_code = 0
        except ValueError as error:
            print(f"Error: {error}")
            exit_code = 1
        if not args.interactive:
            return exit_code
        try:
            if input("\n[Enter] Get Status lagi, [q] keluar: ").strip().lower() == "q":
                return exit_code
        except EOFError:
            return exit_code


if __name__ == "__main__":
    raise SystemExit(main())

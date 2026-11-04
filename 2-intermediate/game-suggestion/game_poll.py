"""Game Suggestion: buat polling, usulkan game, dan lihat 10 game dengan suara terbanyak.

Game dicari lewat API toko Steam (gratis, tanpa kunci). IGDB yang disarankan
spesifikasi butuh akun Twitch dan token OAuth. Polling dan suara disimpan di SQLite.

Jalankan:
    python game_poll.py create "Main bareng Jumat" --owner budi --genre RPG
    python game_poll.py polls --owner budi
    python game_poll.py search "hollow knight"
    python game_poll.py vote 1 "stardew valley" --voter sari
    python game_poll.py vote 1 --voter sari          # cari interaktif, lalu pilih nomor
    python game_poll.py results 1 --top 5
"""

import argparse
import json
import os
import sqlite3
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime

DEFAULT_DB = os.path.join(os.path.expanduser("~"), ".app-ideas-python", "game-polls.db")
SEARCH_URL = "https://store.steampowered.com/api/storesearch/"
DETAILS_URL = "https://store.steampowered.com/api/appdetails"
USER_AGENT = "app-ideas-python-game-poll/1.0"

SCHEMA = """
CREATE TABLE IF NOT EXISTS polls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    owner TEXT NOT NULL,
    genre TEXT,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS games (
    app_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    genres TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS votes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    poll_id INTEGER NOT NULL REFERENCES polls(id) ON DELETE CASCADE,
    app_id INTEGER NOT NULL REFERENCES games(app_id),
    voter TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE (poll_id, app_id, voter)
);
"""


class PollError(Exception):
    """Kesalahan yang ditampilkan ke pengguna sebagai pesan biasa."""


# --- Steam ---------------------------------------------------------------------

def fetch_json(url, urlopen=urllib.request.urlopen):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urlopen(request, timeout=15) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        raise PollError(f"Steam menjawab kode {error.code}. Coba lagi sebentar lagi.") from None
    except (urllib.error.URLError, TimeoutError):
        raise PollError("Tidak bisa menjangkau Steam. Periksa koneksi internet.") from None
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise PollError("Jawaban Steam bukan JSON yang valid.") from None


def search_games(term, urlopen=urllib.request.urlopen, limit=10):
    """Daftar (app_id, nama) dari pencarian toko Steam."""
    term = term.strip()
    if not term:
        raise PollError("Tulis nama game yang dicari.")
    query = urllib.parse.urlencode({"term": term, "l": "english", "cc": "US"})
    data = fetch_json(f"{SEARCH_URL}?{query}", urlopen)
    items = data.get("items") if isinstance(data, dict) else None
    if not isinstance(items, list):
        raise PollError("Format hasil pencarian Steam tidak dikenali.")
    results = []
    for item in items:
        if isinstance(item, dict) and isinstance(item.get("id"), int) and item.get("name"):
            results.append((item["id"], item["name"]))
    return results[:limit]


def game_details(app_id, urlopen=urllib.request.urlopen):
    """(nama, jenis, [genre]) sebuah aplikasi Steam. Jenis: 'game', 'dlc', 'music', ..."""
    query = urllib.parse.urlencode({"appids": app_id, "filters": "basic,genres"})
    data = fetch_json(f"{DETAILS_URL}?{query}", urlopen)
    entry = data.get(str(app_id)) if isinstance(data, dict) else None
    if not isinstance(entry, dict) or not entry.get("success") or not isinstance(entry.get("data"), dict):
        raise PollError(f"Game dengan id {app_id} tidak ditemukan di Steam.")
    info = entry["data"]
    genres = [g["description"] for g in info.get("genres") or [] if isinstance(g, dict) and g.get("description")]
    return info.get("name") or str(app_id), info.get("type") or "unknown", genres


# --- database --------------------------------------------------------------------

def connect(path):
    if path != ":memory:":
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    db.executescript(SCHEMA)
    return db


def now():
    return datetime.now().isoformat(timespec="seconds")


def clean_name(value, label):
    value = " ".join((value or "").split())
    if not value:
        raise PollError(f"{label} tidak boleh kosong.")
    if len(value) > 80:
        raise PollError(f"{label} maksimal 80 karakter.")
    return value


def create_poll(db, title, owner, genre=None, clock=now):
    title = clean_name(title, "Judul polling")
    owner = clean_name(owner, "Nama pembuat")
    genre = " ".join(genre.split()) if genre and genre.strip() else None
    with db:
        cursor = db.execute("INSERT INTO polls (title, owner, genre, created_at) VALUES (?, ?, ?, ?)",
                            (title, owner, genre, clock()))
    return cursor.lastrowid


def get_poll(db, poll_id):
    row = db.execute("SELECT * FROM polls WHERE id = ?", (poll_id,)).fetchone()
    if row is None:
        raise PollError(f"Polling #{poll_id} tidak ada.")
    return row


def list_polls(db, owner=None):
    sql = """SELECT p.*, COUNT(v.id) AS votes FROM polls p LEFT JOIN votes v ON v.poll_id = p.id
             {where} GROUP BY p.id ORDER BY p.id DESC"""
    if owner:
        return db.execute(sql.format(where="WHERE p.owner = ? COLLATE NOCASE"), (owner.strip(),)).fetchall()
    return db.execute(sql.format(where="")).fetchall()


def vote(db, poll_id, app_id, voter, details, clock=now):
    """Catat suara untuk satu game. `details` = (nama, jenis, genre) dari game_details()."""
    poll = get_poll(db, poll_id)
    voter = clean_name(voter, "Nama pemilih")
    name, kind, genres = details
    if kind != "game":
        raise PollError(f"'{name}' bukan game (jenis Steam: {kind}). Pilih game, bukan DLC atau soundtrack.")
    if poll["genre"] and poll["genre"].lower() not in (g.lower() for g in genres):
        shown = ", ".join(genres) or "tanpa genre"
        raise PollError(f"Polling ini hanya untuk genre {poll['genre']}. '{name}' bergenre {shown}.")
    with db:
        db.execute("""INSERT INTO games (app_id, name, genres) VALUES (?, ?, ?)
                      ON CONFLICT(app_id) DO UPDATE SET name = excluded.name, genres = excluded.genres""",
                   (app_id, name, ", ".join(genres)))
        cursor = db.execute("INSERT OR IGNORE INTO votes (poll_id, app_id, voter, created_at) VALUES (?, ?, ?, ?)",
                            (poll_id, app_id, voter, clock()))
    if cursor.rowcount == 0:
        raise PollError(f"{voter} sudah memilih '{name}' di polling ini.")
    return name


def results(db, poll_id, top=10):
    """Game dengan suara terbanyak. Kalau seri, yang lebih dulu mendapat suara di atas."""
    get_poll(db, poll_id)
    return db.execute("""SELECT g.name, g.genres, COUNT(*) AS votes, MIN(v.id) AS first_vote
                         FROM votes v JOIN games g ON g.app_id = v.app_id
                         WHERE v.poll_id = ? GROUP BY v.app_id
                         ORDER BY votes DESC, first_vote ASC LIMIT ?""", (poll_id, top)).fetchall()


def format_results(poll, rows):
    header = f"#{poll['id']} {poll['title']} (oleh {poll['owner']}"
    header += f", genre {poll['genre']})" if poll["genre"] else ")"
    if not rows:
        return header + "\nBelum ada suara."
    lines = [header, ""]
    most = rows[0]["votes"]
    width = max(len(row["name"]) for row in rows)
    for rank, row in enumerate(rows, start=1):
        bar = "#" * round(row["votes"] / most * 20)
        lines.append(f"{rank:>2}. {row['name']:<{width}}  {bar} {row['votes']}")
    return "\n".join(lines)


# --- baris perintah ---------------------------------------------------------------

def build_parser():
    parser = argparse.ArgumentParser(prog="game_poll", description="Polling usulan game.")
    parser.add_argument("--db", default=DEFAULT_DB, help="berkas database SQLite")
    sub = parser.add_subparsers(dest="command", required=True, metavar="<perintah>")

    p = sub.add_parser("create", help="buat polling baru")
    p.add_argument("title")
    p.add_argument("--owner", required=True, help="nama pembuat polling")
    p.add_argument("--genre", help="batasi usulan ke satu genre Steam, misalnya RPG atau Strategy")

    p = sub.add_parser("polls", help="daftar polling")
    p.add_argument("--owner", help="hanya polling milik orang ini")

    p = sub.add_parser("search", help="cari game di Steam")
    p.add_argument("term")

    p = sub.add_parser("vote", help="usulkan/pilih game di sebuah polling")
    p.add_argument("poll_id", type=int)
    p.add_argument("term", nargs="?", help="nama game (kosong: cari interaktif)")
    p.add_argument("--voter", required=True, help="nama pemilih")
    p.add_argument("--pick", type=int, default=1, help="nomor hasil pencarian yang dipilih (bawaan 1)")
    p.add_argument("--id", dest="app_id", type=int, help="id aplikasi Steam, tanpa pencarian")

    p = sub.add_parser("results", help="game dengan suara terbanyak")
    p.add_argument("poll_id", type=int)
    p.add_argument("--top", type=int, choices=(5, 10), default=10)
    return parser


def choose_game(args, urlopen, ask):
    """Tentukan app_id dari --id, dari pencarian + --pick, atau secara interaktif."""
    if args.app_id:
        return args.app_id
    if args.term:
        found = search_games(args.term, urlopen)
        if not found:
            raise PollError(f"Tidak ada game Steam yang cocok dengan '{args.term}'.")
        if not 1 <= args.pick <= len(found):
            raise PollError(f"--pick harus 1 sampai {len(found)}.")
        return found[args.pick - 1][0]
    while True:
        term = ask("Cari game (kosongkan untuk batal): ").strip()
        if not term:
            raise PollError("Dibatalkan.")
        found = search_games(term, urlopen)
        if not found:
            print("Tidak ada yang cocok, coba kata lain.")
            continue
        for number, (_, name) in enumerate(found, start=1):
            print(f"{number:>3}. {name}")
        choice = ask("Nomor game (Enter = cari lagi): ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(found):
            return found[int(choice) - 1][0]


def main(argv=None, urlopen=urllib.request.urlopen, ask=input):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    args = build_parser().parse_args(sys.argv[1:] if argv is None else argv)
    db = connect(args.db)
    try:
        if args.command == "create":
            poll_id = create_poll(db, args.title, args.owner, args.genre)
            print(f"Polling #{poll_id} dibuat: {args.title}")
        elif args.command == "polls":
            rows = list_polls(db, args.owner)
            if not rows:
                print("Belum ada polling.")
            for row in rows:
                genre = f" [genre {row['genre']}]" if row["genre"] else ""
                print(f"#{row['id']:<3} {row['title']}{genre} | oleh {row['owner']} | {row['votes']} suara | "
                      f"{row['created_at'][:10]}")
        elif args.command == "search":
            found = search_games(args.term, urlopen)
            if not found:
                print("Tidak ada yang cocok.")
            for number, (app_id, name) in enumerate(found, start=1):
                print(f"{number:>3}. {name}  (id {app_id})")
        elif args.command == "vote":
            get_poll(db, args.poll_id)
            app_id = choose_game(args, urlopen, ask)
            name = vote(db, args.poll_id, app_id, args.voter, game_details(app_id, urlopen))
            print(f"Suara {args.voter} untuk '{name}' dicatat di polling #{args.poll_id}.")
        elif args.command == "results":
            print(format_results(get_poll(db, args.poll_id), results(db, args.poll_id, args.top)))
    except PollError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

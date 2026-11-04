"""Timezone Slackbot: perintah /tz @rina @budi menampilkan jam dan zona waktu setiap anggota tim.

Bot ini adalah server slash command Slack:
  - memeriksa tanda tangan permintaan (X-Slack-Signature, HMAC-SHA256 dengan signing secret),
  - membaca nama atau mention <@U123|rina> dari teks perintah,
  - mengambil zona waktu pengguna lewat API Slack users.info / users.list,
  - membalas dengan tabel yang barisnya berwarna selang-seling (satu attachment per baris).

Tanpa workspace Slack, bot bisa dicoba dengan data tim lokal (mode simulate).

Jalankan:
    python tz_bot.py simulate rina budi wayan --team contoh/tim.json
    SLACK_SIGNING_SECRET=... SLACK_BOT_TOKEN=xoxb-... python tz_bot.py serve --port 3000
"""

import argparse
import hashlib
import hmac
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

ROW_COLORS = ("#2e78c7", "#9cc3ef")  # warna bilah kiri attachment, bergantian per baris
MENTION_RE = re.compile(r"<@([A-Z0-9]+)(?:\|([^>]+))?>")
MAX_AGE = 300  # permintaan lebih tua dari 5 menit ditolak (mencegah replay)
DAYS = ("Sen", "Sel", "Rab", "Kam", "Jum", "Sab", "Min")
MONTHS = ("Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des")


class BotError(Exception):
    """Kesalahan yang dibalas ke pengguna Slack sebagai pesan biasa."""


# --- tanda tangan Slack ----------------------------------------------------------

def sign(secret, timestamp, body):
    base = f"v0:{timestamp}:".encode() + body
    return "v0=" + hmac.new(secret.encode(), base, hashlib.sha256).hexdigest()


def verify(secret, timestamp, body, signature, now=time.time):
    """True kalau permintaan benar-benar dari Slack dan belum kedaluwarsa."""
    if not (secret and timestamp and signature):
        return False
    try:
        if abs(now() - int(timestamp)) > MAX_AGE:
            return False
    except ValueError:
        return False
    return hmac.compare_digest(sign(secret, timestamp, body), signature)


# --- direktori pengguna ------------------------------------------------------------

class SlackDirectory:
    """Pengguna dari API Slack (butuh bot token dengan izin users:read)."""

    API = "https://slack.com/api/"

    def __init__(self, token, urlopen=urllib.request.urlopen):
        self.token = token
        self.urlopen = urlopen
        self._members = None

    def _call(self, method, **params):
        url = self.API + method + ("?" + urllib.parse.urlencode(params) if params else "")
        request = urllib.request.Request(url, headers={"Authorization": f"Bearer {self.token}"})
        try:
            with self.urlopen(request, timeout=10) as response:
                data = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, ValueError):
            raise BotError("Tidak bisa menghubungi API Slack.") from None
        if not data.get("ok"):
            raise BotError(f"API Slack menolak permintaan: {data.get('error', 'tidak diketahui')}.")
        return data

    def by_id(self, user_id):
        try:
            return self._call("users.info", user=user_id)["user"]
        except BotError:
            return None

    def by_name(self, name):
        if self._members is None:
            self._members = [m for m in self._call("users.list")["members"] if not m.get("deleted")]
        return _match_name(self._members, name)


class LocalDirectory:
    """Pengguna dari berkas JSON dengan bentuk yang sama seperti jawaban users.list Slack."""

    def __init__(self, members):
        self.members = members

    @classmethod
    def load(cls, path):
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
        return cls(data["members"] if isinstance(data, dict) else data)

    def by_id(self, user_id):
        return next((m for m in self.members if m.get("id") == user_id), None)

    def by_name(self, name):
        return _match_name(self.members, name)


def _match_name(members, name):
    wanted = name.lower().lstrip("@")
    for member in members:
        profile = member.get("profile", {})
        names = {member.get("name", ""), profile.get("display_name", ""), profile.get("real_name", ""),
                 member.get("real_name", "")}
        if wanted in {n.lower() for n in names if n}:
            return member
    return None


# --- perintah /tz -------------------------------------------------------------------

def parse_targets(text):
    """'<@U1|rina> budi @wayan' -> [('id', 'U1', 'rina'), ('name', 'budi', 'budi'), ('name', 'wayan', 'wayan')]."""
    targets = []
    for match in MENTION_RE.finditer(text):
        targets.append(("id", match.group(1), match.group(2) or match.group(1)))
    for word in MENTION_RE.sub(" ", text).replace(",", " ").split():
        word = word.lstrip("@")
        if word:
            targets.append(("name", word, word))
    seen, unique = set(), []
    for target in targets:
        if target[1].lower() not in seen:
            seen.add(target[1].lower())
            unique.append(target)
    return unique


def zone_info(member, now):
    """(nama tampilan, waktu lokal, singkatan zona, nama zona, offset) untuk satu pengguna."""
    profile = member.get("profile", {})
    display = profile.get("display_name") or profile.get("real_name") or member.get("real_name") or member.get("name")
    tz_name = member.get("tz") or "UTC"
    try:
        local = now.astimezone(ZoneInfo(tz_name))
    except (ZoneInfoNotFoundError, ValueError):
        local = now.astimezone(timezone(timedelta(seconds=int(member.get("tz_offset", 0)))))  # zona tak dikenal
    abbreviation = local.tzname() or ""
    if abbreviation.startswith(("+", "-")):  # zona tanpa singkatan resmi di tzdata
        abbreviation = f"UTC{abbreviation[:3]}" + (f":{abbreviation[3:]}" if len(abbreviation) > 3 else "")
    return display, local, abbreviation, tz_name, local.utcoffset()


def format_offset(delta):
    minutes = int(delta.total_seconds() // 60)
    sign_char = "+" if minutes >= 0 else "-"
    minutes = abs(minutes)
    return f"UTC{sign_char}{minutes // 60:02d}:{minutes % 60:02d}"


def build_rows(text, directory, now=None):
    """Baris tabel (diurutkan dari zona paling barat) dan daftar nama yang tidak ditemukan."""
    now = now or datetime.now(timezone.utc)
    targets = parse_targets(text)
    if not targets:
        raise BotError("Tulis nama anggota tim, misalnya: /tz @rina @budi")
    rows, missing = [], []
    for kind, key, label in targets:
        member = directory.by_id(key) if kind == "id" else directory.by_name(key)
        if member is None:
            missing.append(label)
            continue
        rows.append(zone_info(member, now))
    rows.sort(key=lambda r: (r[4], r[0].lower()))
    return rows, missing


def text_table(rows, missing=()):
    """Tabel teks lebar tetap (untuk terminal dan untuk teks cadangan di Slack)."""
    if not rows:
        lines = ["Tidak ada pengguna yang ditemukan."]
    else:
        width = max(len(r[0]) for r in rows)
        lines = [f"{'Nama':<{width}}  Jam    Zona   Lokasi"]
        for name, local, abbreviation, tz_name, offset in rows:
            lines.append(f"{name:<{width}}  {local:%H:%M}  {abbreviation:<5}  {tz_name} ({format_offset(offset)})")
    if missing:
        lines.append(f"Tidak ditemukan: {', '.join(missing)}")
    return "\n".join(lines)


def slack_response(rows, missing=()):
    """Balasan slash command: satu attachment per baris, warnanya bergantian supaya mudah dibaca."""
    attachments = []
    for index, (name, local, abbreviation, tz_name, offset) in enumerate(rows):
        attachments.append({
            "color": ROW_COLORS[index % 2],
            "fallback": f"{name}: {local:%H:%M} {abbreviation}",
            "text": f"*{name}*  {local:%H:%M} *{abbreviation}*  ·  {tz_name} ({format_offset(offset)})  ·  "
                    f"{DAYS[local.weekday()]} {local.day} {MONTHS[local.month - 1]}",
            "mrkdwn_in": ["text"],
        })
    if missing:
        attachments.append({"color": "#c0392b", "text": f"Tidak ditemukan: {', '.join(missing)}"})
    return {"response_type": "in_channel", "text": "Zona waktu tim:" if rows else "Tidak ada pengguna yang ditemukan.",
            "attachments": attachments}


def handle_command(form, directory, now=None):
    """Proses isi form slash command Slack. Mengembalikan dict JSON balasan."""
    if form.get("command", "/tz") != "/tz":
        return {"response_type": "ephemeral", "text": f"Perintah {form.get('command')} tidak dikenal."}
    try:
        rows, missing = build_rows(form.get("text", ""), directory, now)
    except BotError as error:
        return {"response_type": "ephemeral", "text": str(error)}
    return slack_response(rows, missing)


# --- server ---------------------------------------------------------------------------

def make_handler(secret, directory, clock=time.time):
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            # Baca isi permintaan dulu, juga untuk alamat yang salah: kalau server langsung menjawab
            # sebelum isinya terbaca, Windows memutus koneksi saat klien masih mengirim.
            try:
                length = max(0, int(self.headers.get("Content-Length") or 0))
            except ValueError:
                length = 0
            body = self.rfile.read(min(length, 100_000))
            if self.path != "/slack/tz":
                self.reply(404, {"error": "not_found"})
                return
            if not verify(secret, self.headers.get("X-Slack-Request-Timestamp"), body,
                          self.headers.get("X-Slack-Signature"), clock):
                self.reply(401, {"error": "invalid_signature"})
                return
            form = {k: v[0] for k, v in urllib.parse.parse_qs(body.decode("utf-8")).items()}
            self.reply(200, handle_command(form, directory))

        def reply(self, status, payload):
            data = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, format, *args):
            pass

    return Handler


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Slash command /tz untuk Slack.")
    sub = parser.add_subparsers(dest="command", required=True)
    s = sub.add_parser("simulate", help="coba perintah /tz dengan data tim lokal")
    s.add_argument("names", nargs="+")
    s.add_argument("--team", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "contoh", "tim.json"))
    s.add_argument("--json", action="store_true", help="tampilkan balasan JSON untuk Slack")
    v = sub.add_parser("serve", help="jalankan server slash command")
    v.add_argument("--port", type=int, default=3000)
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    if args.command == "simulate":
        try:
            directory = LocalDirectory.load(args.team)
            rows, missing = build_rows(" ".join(args.names), directory)
        except (OSError, ValueError, KeyError, BotError) as error:
            print(f"Error: {error}", file=sys.stderr)
            return 1
        print(json.dumps(slack_response(rows, missing), indent=2, ensure_ascii=False) if args.json
              else text_table(rows, missing))
        return 0
    secret, token = os.environ.get("SLACK_SIGNING_SECRET"), os.environ.get("SLACK_BOT_TOKEN")
    if not (secret and token):
        print("Error: isi variabel lingkungan SLACK_SIGNING_SECRET dan SLACK_BOT_TOKEN dulu.", file=sys.stderr)
        return 1
    server = ThreadingHTTPServer(("0.0.0.0", args.port), make_handler(secret, SlackDirectory(token)))
    print(f"Slash command /tz siap di http://localhost:{args.port}/slack/tz (Ctrl+C untuk berhenti)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

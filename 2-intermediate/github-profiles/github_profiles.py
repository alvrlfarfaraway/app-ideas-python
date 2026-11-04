"""GitHub Profiles: cari pengguna GitHub, tampilkan avatar, statistik, dan 4 repo teratas.

Memakai GitHub REST API tanpa login (60 permintaan per jam per alamat IP).
Kalau variabel lingkungan GITHUB_TOKEN diisi, token itu dipakai supaya batasnya lebih longgar.
Mode gelap/terang disimpan, jadi tetap sama saat aplikasi dibuka lagi.

Jalankan:
    python github_profiles.py               # jendela Tkinter
    python github_profiles.py torvalds      # terminal
"""

import argparse
import io
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

API = "https://api.github.com"
USER_AGENT = "app-ideas-python-github-profiles/1.0"
SETTINGS = os.path.join(os.path.expanduser("~"), ".app-ideas-python", "github-profiles.json")
MAX_REPO_PAGES = 3  # sampai 300 repo diperiksa untuk mencari 4 teratas
# Aturan username GitHub: huruf/angka dan tanda hubung tunggal, tidak diawali/diakhiri '-', maksimal 39 karakter.
USERNAME_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9]|-(?=[A-Za-z0-9])){0,38}$")


class ProfileError(Exception):
    """Kesalahan yang ditampilkan sebagai peringatan ke pengguna."""


def validate_username(text):
    name = text.strip().lstrip("@")
    if not name:
        raise ProfileError("Tulis username GitHub dulu.")
    if not USERNAME_RE.match(name):
        raise ProfileError(f"'{name}' bukan username GitHub yang valid. Username hanya berisi huruf, angka, "
                           "dan tanda hubung tunggal (tidak di awal/akhir), maksimal 39 karakter.")
    return name


def _request(url, token=None):
    headers = {"User-Agent": USER_AGENT, "Accept": "application/vnd.github+json",
               "X-GitHub-Api-Version": "2022-11-28"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return urllib.request.Request(url, headers=headers)


def get_json(url, urlopen=urllib.request.urlopen, token=None, clock=time.time):
    try:
        with urlopen(_request(url, token), timeout=15) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        if error.code == 404:
            raise ProfileError("not_found") from None
        remaining = error.headers.get("X-RateLimit-Remaining") if error.headers else None
        if error.code in (403, 429) and remaining == "0":
            reset = error.headers.get("X-RateLimit-Reset")
            wait = ""
            if reset and reset.isdigit():
                minutes = max(1, round((int(reset) - clock()) / 60))
                wait = f" Coba lagi sekitar {minutes} menit lagi."
            raise ProfileError("Batas permintaan API GitHub (60 per jam tanpa login) sudah habis." + wait) from None
        raise ProfileError(f"GitHub menjawab kode {error.code}.") from None
    except (urllib.error.URLError, TimeoutError):
        raise ProfileError("Tidak bisa menjangkau api.github.com. Periksa koneksi internet.") from None
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise ProfileError("Jawaban GitHub bukan JSON yang valid.") from None


def top_repositories(repos, count=4):
    """Repo dengan bintang + fork terbanyak. Kalau seri, bintang lebih banyak dulu, lalu nama."""
    own = [r for r in repos if isinstance(r, dict) and not r.get("fork")]
    own.sort(key=lambda r: (-(r.get("stargazers_count", 0) + r.get("forks_count", 0)),
                            -r.get("stargazers_count", 0), r.get("name", "").lower()))
    return own[:count]


def fetch_profile(username, urlopen=urllib.request.urlopen, token=None):
    """Data profil + 4 repo teratas. ProfileError kalau username tidak ada atau jaringan bermasalah."""
    name = validate_username(username)
    quoted = urllib.parse.quote(name)
    try:
        user = get_json(f"{API}/users/{quoted}", urlopen, token)
    except ProfileError as error:
        if str(error) == "not_found":
            raise ProfileError(f"Pengguna GitHub '{name}' tidak ditemukan.") from None
        raise
    if not isinstance(user, dict) or "login" not in user:
        raise ProfileError("Format data profil GitHub tidak dikenali.")
    repos = []
    if user.get("public_repos", 0) > 0:
        for page in range(1, MAX_REPO_PAGES + 1):
            batch = get_json(f"{API}/users/{quoted}/repos?per_page=100&page={page}&type=owner", urlopen, token)
            if not isinstance(batch, list):
                raise ProfileError("Format daftar repo GitHub tidak dikenali.")
            repos.extend(batch)
            if len(batch) < 100:
                break
    return {
        "login": user["login"],
        "name": user.get("name") or "",
        "avatar_url": user.get("avatar_url") or "",
        "html_url": user.get("html_url") or f"https://github.com/{user['login']}",
        "followers": user.get("followers", 0),
        "following": user.get("following", 0),
        "public_repos": user.get("public_repos", 0),
        "bio": user.get("bio") or "",
        "top": [{"name": r.get("name", ""), "description": r.get("description") or "",
                 "stars": r.get("stargazers_count", 0), "forks": r.get("forks_count", 0),
                 "language": r.get("language") or "", "url": r.get("html_url", "")}
                for r in top_repositories(repos)],
    }


def format_count(value):
    """12345 -> '12,3 rb'; 2300000 -> '2,3 jt' (gaya Indonesia)."""
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f} jt".replace(".", ",")
    if value >= 10_000:
        return f"{value / 1_000:.1f} rb".replace(".", ",")
    return f"{value:,}".replace(",", ".")


def format_profile(profile):
    lines = [f"{profile['login']}" + (f" ({profile['name']})" if profile["name"] else ""),
             f"Followers: {format_count(profile['followers'])} | Repo publik: {format_count(profile['public_repos'])}",
             profile["html_url"], "", "4 repo teratas (bintang + fork):"]
    if not profile["top"]:
        lines.append("  (belum ada repo milik sendiri)")
    for number, repo in enumerate(profile["top"], start=1):
        lang = f" [{repo['language']}]" if repo["language"] else ""
        lines.append(f"  {number}. {repo['name']}{lang}  ★ {format_count(repo['stars'])}  "
                     f"fork {format_count(repo['forks'])}")
    return "\n".join(lines)


# --- pengaturan tema ----------------------------------------------------------------

def load_theme(path=SETTINGS):
    try:
        with open(path, encoding="utf-8") as handle:
            theme = json.load(handle).get("theme")
        return theme if theme in THEMES else "light"
    except (OSError, ValueError, AttributeError):
        return "light"


def save_theme(theme, path=SETTINGS):
    try:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump({"theme": theme}, handle)
    except OSError:
        pass


THEMES = {
    "light": {"bg": "#f6f8fa", "card": "#ffffff", "text": "#1f2328", "muted": "#59636e", "line": "#d1d9e0",
              "accent": "#0969da", "entry": "#ffffff"},
    "dark": {"bg": "#0d1117", "card": "#161b22", "text": "#e6edf3", "muted": "#9198a1", "line": "#30363d",
             "accent": "#4493f8", "entry": "#0d1117"},
}


# --- tampilan Tkinter ----------------------------------------------------------------

def circle_avatar(data, size=112):
    """Bytes gambar -> PIL.Image bundar (latar transparan)."""
    from PIL import Image, ImageDraw

    with Image.open(io.BytesIO(data)) as image:
        image = image.convert("RGBA").resize((size, size), Image.Resampling.LANCZOS)
    mask = Image.new("L", (size * 4, size * 4), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size * 4 - 1, size * 4 - 1), fill=255)
    image.putalpha(mask.resize((size, size), Image.Resampling.LANCZOS))
    return image


class ProfilesApp:
    def __init__(self, root, urlopen=urllib.request.urlopen, settings_path=SETTINGS, alert=None, opener=None):
        import tkinter as tk
        import webbrowser

        self.tk = tk
        self.root = root
        self.urlopen = urlopen
        self.settings_path = settings_path
        self.token = os.environ.get("GITHUB_TOKEN") or None
        self.theme = load_theme(settings_path)
        self.alert = alert or self._messagebox
        self.open_url = opener or webbrowser.open
        self.avatar_photo = None
        self.profile = None
        self.themed = []  # (widget, {opsi: kunci warna})

        root.title("GitHub Profiles")
        root.resizable(False, False)
        self.outer = self.add(tk.Frame(root, padx=18, pady=16), bg="bg")
        self.outer.pack(fill="both", expand=True)
        bar = self.add(tk.Frame(self.outer), bg="bg")
        bar.pack(fill="x")
        self.username = tk.StringVar()
        entry = self.add(tk.Entry(bar, textvariable=self.username, font=("Segoe UI", 12), width=26,
                                  relief="flat", highlightthickness=1),
                         bg="entry", fg="text", insertbackground="text", highlightbackground="line",
                         highlightcolor="accent")
        entry.pack(side="left", ipady=4)
        entry.bind("<Return>", lambda _e: self.search())
        self.search_button = self.add(tk.Button(bar, text="Cari", command=self.search, relief="flat", padx=14,
                                                font=("Segoe UI", 11), cursor="hand2"),
                                      bg="accent", fg="card", activebackground="accent", activeforeground="card")
        self.search_button.pack(side="left", padx=8)
        self.theme_button = self.add(tk.Button(bar, command=self.toggle_theme, relief="flat", padx=10,
                                               font=("Segoe UI", 10), cursor="hand2"),
                                     bg="card", fg="text", activebackground="line", activeforeground="text")
        self.theme_button.pack(side="right")

        self.card = self.add(tk.Frame(self.outer, padx=18, pady=16, highlightthickness=1),
                             bg="card", highlightbackground="line")
        self.card.pack(fill="x", pady=(14, 0))
        head = self.add(tk.Frame(self.card), bg="card")
        head.pack(fill="x")
        self.avatar = self.add(tk.Label(head, width=112, height=112, cursor="hand2"), bg="card")
        self.avatar.pack(side="left")
        self.avatar.bind("<Button-1>", lambda _e: self.profile and self.open_url(self.profile["html_url"]))
        info = self.add(tk.Frame(head, padx=16), bg="card")
        info.pack(side="left", fill="both", expand=True)
        self.login_label = self.add(tk.Label(info, font=("Segoe UI", 16, "bold"), anchor="w"), bg="card", fg="text")
        self.login_label.pack(fill="x")
        self.name_label = self.add(tk.Label(info, font=("Segoe UI", 11), anchor="w"), bg="card", fg="muted")
        self.name_label.pack(fill="x")
        self.stats_label = self.add(tk.Label(info, font=("Segoe UI", 11), anchor="w", justify="left"),
                                    bg="card", fg="text")
        self.stats_label.pack(fill="x", pady=(8, 0))

        self.repo_title = self.add(tk.Label(self.card, text="", font=("Segoe UI", 11, "bold"), anchor="w"),
                                   bg="card", fg="text")
        self.repo_title.pack(fill="x", pady=(14, 4))
        self.repo_rows = []
        for _ in range(4):
            row = self.add(tk.Frame(self.card, pady=6, padx=10, highlightthickness=1), bg="card",
                           highlightbackground="line")
            name = self.add(tk.Label(row, font=("Segoe UI", 11, "bold"), anchor="w", cursor="hand2"),
                            bg="card", fg="accent")
            name.pack(fill="x")
            desc = self.add(tk.Label(row, font=("Segoe UI", 9), anchor="w", justify="left", wraplength=430),
                            bg="card", fg="muted")
            desc.pack(fill="x")
            meta = self.add(tk.Label(row, font=("Segoe UI", 9), anchor="w"), bg="card", fg="muted")
            meta.pack(fill="x")
            self.repo_rows.append((row, name, desc, meta))
        self.status = tk.StringVar(value="Ketik username GitHub, lalu tekan Cari atau Enter.")
        self.status_label = self.add(tk.Label(self.outer, textvariable=self.status, font=("Segoe UI", 9),
                                              anchor="w"), bg="bg", fg="muted")
        self.status_label.pack(fill="x", pady=(10, 0))
        self.apply_theme()
        self.show_empty()
        entry.focus_set()

    def add(self, widget, **colors):
        self.themed.append((widget, colors))
        return widget

    def apply_theme(self):
        palette = THEMES[self.theme]
        for widget, colors in self.themed:
            widget.configure(**{option: palette[key] for option, key in colors.items()})
        self.root.configure(background=palette["bg"])
        self.theme_button.configure(text="☀ Terang" if self.theme == "dark" else "☾ Gelap")

    def toggle_theme(self):
        self.theme = "dark" if self.theme == "light" else "light"
        save_theme(self.theme, self.settings_path)
        self.apply_theme()

    def _messagebox(self, message):
        from tkinter import messagebox

        messagebox.showwarning("GitHub Profiles", message, parent=self.root)

    def show_empty(self):
        self.login_label.configure(text="Belum ada profil")
        self.name_label.configure(text="")
        self.stats_label.configure(text="")
        self.repo_title.configure(text="")
        self.avatar.configure(image="")
        for row, *_ in self.repo_rows:
            row.pack_forget()

    def search(self):
        try:
            name = validate_username(self.username.get())
            self.status.set(f"Mengambil profil {name}…")
            self.root.update_idletasks()
            profile = fetch_profile(name, self.urlopen, self.token)
        except ProfileError as error:
            self.status.set("Gagal mengambil profil.")
            self.alert(str(error))
            return None
        self.show(profile)
        self.status.set(f"Profil {profile['login']} dimuat. Klik avatar atau nama repo untuk membuka GitHub.")
        return profile

    def show(self, profile):
        from PIL import ImageTk

        self.profile = profile
        self.login_label.configure(text=profile["login"])
        self.name_label.configure(text=profile["name"] or profile["bio"][:60])
        self.stats_label.configure(text=f"{format_count(profile['followers'])} followers  ·  "
                                        f"{format_count(profile['public_repos'])} repo publik")
        try:
            with self.urlopen(_request(profile["avatar_url"] + "&s=224" if "?" in profile["avatar_url"]
                                       else profile["avatar_url"] + "?s=224"), timeout=15) as response:
                data = response.read()
            self.avatar_photo = ImageTk.PhotoImage(circle_avatar(data), master=self.root)
            self.avatar.configure(image=self.avatar_photo)
        except Exception:  # avatar gagal dimuat bukan alasan menggagalkan seluruh profil
            self.avatar.configure(image="")
        self.repo_title.configure(text="4 repo teratas (bintang + fork)" if profile["top"]
                                  else "Belum ada repo milik sendiri")
        for (row, name, desc, meta), repo in zip(self.repo_rows, profile["top"] + [None] * 4):
            if repo is None:
                row.pack_forget()
                continue
            name.configure(text=repo["name"])
            name.bind("<Button-1>", lambda _e, url=repo["url"]: self.open_url(url))
            desc.configure(text=repo["description"][:140] or "Tanpa deskripsi")
            lang = f"{repo['language']}  ·  " if repo["language"] else ""
            meta.configure(text=f"{lang}★ {format_count(repo['stars'])}  ·  fork {format_count(repo['forks'])}")
            row.pack(fill="x", pady=3)


def main(argv=None, urlopen=urllib.request.urlopen, gui=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Cari profil GitHub.")
    parser.add_argument("username", nargs="?", help="username GitHub (kosong: buka jendela)")
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    if not args.username:
        (gui or run_gui)()
        return 0
    try:
        print(format_profile(fetch_profile(args.username, urlopen, os.environ.get("GITHUB_TOKEN") or None)))
    except ProfileError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    return 0


def run_gui():
    import tkinter as tk

    root = tk.Tk()
    ProfilesApp(root)
    root.mainloop()


if __name__ == "__main__":
    raise SystemExit(main())

import contextlib
import email.message
import io
import json
import os
import tempfile
import unittest
import urllib.error
import urllib.parse

from PIL import Image

import github_profiles
from github_profiles import (
    ProfileError,
    circle_avatar,
    fetch_profile,
    format_count,
    format_profile,
    load_theme,
    main,
    save_theme,
    top_repositories,
    validate_username,
)


def repo(name, stars, forks, fork=False, language="Python"):
    return {"name": name, "stargazers_count": stars, "forks_count": forks, "fork": fork, "language": language,
            "description": f"Repo {name}", "html_url": f"https://github.com/octo/{name}"}


def png_bytes():
    buffer = io.BytesIO()
    Image.new("RGB", (40, 40), (200, 50, 50)).save(buffer, "PNG")
    return buffer.getvalue()


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class FakeGitHub:
    """Meniru /users/<nama>, /users/<nama>/repos (berhalaman), dan avatar."""

    def __init__(self, repos, public_repos=None, followers=1234):
        self.repos = repos
        self.user = {"login": "octo", "name": "Octo Cat", "avatar_url": "https://avatars.test/u/1?v=4",
                     "html_url": "https://github.com/octo", "followers": followers, "following": 3,
                     "public_repos": len(repos) if public_repos is None else public_repos, "bio": "hi"}
        self.calls = []

    def __call__(self, request, timeout=None):
        url = request.full_url
        self.calls.append(request)
        if url.startswith("https://avatars.test"):
            return FakeResponse(png_bytes())
        parts = urllib.parse.urlsplit(url)
        if parts.path == "/users/octo":
            return FakeResponse(json.dumps(self.user).encode())
        if parts.path == "/users/octo/repos":
            page = int(dict(urllib.parse.parse_qsl(parts.query))["page"])
            batch = self.repos[(page - 1) * 100: page * 100]
            return FakeResponse(json.dumps(batch).encode())
        raise urllib.error.HTTPError(url, 404, "Not Found", email.message.Message(), None)


def http_error(code, headers=None):
    message = email.message.Message()
    for key, value in (headers or {}).items():
        message[key] = value

    def opener(request, timeout=None):
        raise urllib.error.HTTPError(request.full_url, code, "x", message, None)
    return opener


class UsernameTest(unittest.TestCase):
    def test_valid(self):
        for name in ("octo", "a", "Octo-Cat", "a1-b2-c3", "x" * 39):
            self.assertEqual(validate_username(name), name)
        self.assertEqual(validate_username("  @octo "), "octo")

    def test_tidak_valid(self):
        for name in ("", "   ", "-octo", "octo-", "oc--to", "oc to", "octo!", "x" * 40, "ö"):
            with self.assertRaises(ProfileError, msg=name):
                validate_username(name)


class RepoTest(unittest.TestCase):
    def test_empat_teratas_berdasar_bintang_dan_fork(self):
        repos = [repo("a", 10, 0), repo("b", 2, 20), repo("c", 50, 1), repo("d", 0, 0), repo("e", 5, 5),
                 repo("garpu", 999, 999, fork=True)]
        self.assertEqual([r["name"] for r in top_repositories(repos)], ["c", "b", "a", "e"])

    def test_seri(self):
        repos = [repo("Zeta", 5, 5), repo("alpha", 5, 5), repo("beta", 9, 1)]
        self.assertEqual([r["name"] for r in top_repositories(repos)], ["beta", "alpha", "Zeta"])


class FetchTest(unittest.TestCase):
    def test_profil_lengkap(self):
        api = FakeGitHub([repo("x", 3, 1), repo("y", 30, 2), repo("z", 0, 0)])
        profile = fetch_profile("octo", api)
        self.assertEqual(profile["login"], "octo")
        self.assertEqual(profile["followers"], 1234)
        self.assertEqual(profile["public_repos"], 3)
        self.assertEqual([r["name"] for r in profile["top"]], ["y", "x", "z"])
        self.assertIn("app-ideas-python", api.calls[0].get_header("User-agent"))
        self.assertIsNone(api.calls[0].get_header("Authorization"))

    def test_banyak_halaman_repo(self):
        repos = [repo(f"r{i}", 0, 0) for i in range(250)]
        repos[230] = repo("bintang", 100, 0)  # ada di halaman ketiga
        api = FakeGitHub(repos)
        self.assertEqual(fetch_profile("octo", api)["top"][0]["name"], "bintang")
        self.assertEqual(len(api.calls), 4)  # profil + 3 halaman

    def test_tanpa_repo_tidak_meminta_daftar_repo(self):
        api = FakeGitHub([], public_repos=0)
        self.assertEqual(fetch_profile("octo", api)["top"], [])
        self.assertEqual(len(api.calls), 1)

    def test_token(self):
        api = FakeGitHub([])
        fetch_profile("octo", api, token="abc")
        self.assertEqual(api.calls[0].get_header("Authorization"), "Bearer abc")

    def test_tidak_ditemukan(self):
        with self.assertRaises(ProfileError) as ctx:
            fetch_profile("hantu", FakeGitHub([]))
        self.assertIn("tidak ditemukan", str(ctx.exception))

    def test_batas_permintaan(self):
        opener = http_error(403, {"X-RateLimit-Remaining": "0", "X-RateLimit-Reset": "1600"})
        with self.assertRaises(ProfileError) as ctx:
            github_profiles.get_json("https://api.github.com/users/x", opener, clock=lambda: 1000)
        self.assertIn("60 per jam", str(ctx.exception))
        self.assertIn("10 menit", str(ctx.exception))

    def test_error_lain(self):
        with self.assertRaises(ProfileError) as ctx:
            fetch_profile("octo", http_error(500))
        self.assertIn("500", str(ctx.exception))

        def offline(request, timeout=None):
            raise urllib.error.URLError("x")
        with self.assertRaises(ProfileError) as ctx:
            fetch_profile("octo", offline)
        self.assertIn("koneksi", str(ctx.exception))


class FormatTest(unittest.TestCase):
    def test_format_count(self):
        self.assertEqual(format_count(0), "0")
        self.assertEqual(format_count(4529), "4.529")
        self.assertEqual(format_count(254_400), "254,4 rb")
        self.assertEqual(format_count(2_300_000), "2,3 jt")

    def test_format_profile(self):
        text = format_profile(fetch_profile("octo", FakeGitHub([repo("y", 30, 2)])))
        self.assertIn("octo (Octo Cat)", text)
        self.assertIn("Followers: 1.234 | Repo publik: 1", text)
        self.assertIn("1. y [Python]  ★ 30  fork 2", text)

    def test_avatar_bundar(self):
        avatar = circle_avatar(png_bytes(), size=64)
        self.assertEqual(avatar.size, (64, 64))
        self.assertEqual(avatar.getpixel((0, 0))[3], 0)  # sudut transparan
        self.assertEqual(avatar.getpixel((32, 32))[3], 255)


class ThemeTest(unittest.TestCase):
    def test_simpan_dan_muat(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "sub", "s.json")
            self.assertEqual(load_theme(path), "light")
            save_theme("dark", path)
            self.assertEqual(load_theme(path), "dark")
            with open(path, "w", encoding="utf-8") as handle:
                handle.write('{"theme": "ungu"}')
            self.assertEqual(load_theme(path), "light")
            with open(path, "w", encoding="utf-8") as handle:
                handle.write("[rusak")
            self.assertEqual(load_theme(path), "light")


class CliTest(unittest.TestCase):
    def test_terminal(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(main(["octo"], urlopen=FakeGitHub([repo("y", 30, 2)])), 0)
        self.assertIn("octo (Octo Cat)", out.getvalue())
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            self.assertEqual(main(["--", "-bad-"], urlopen=FakeGitHub([])), 1)
        self.assertIn("bukan username", err.getvalue())


class GuiTest(unittest.TestCase):
    def setUp(self):
        try:
            import tkinter as tk
            self.root = tk.Tk()
        except Exception as error:
            self.skipTest(f"Tk tidak tersedia: {error}")
        self.root.withdraw()
        self.tmp = tempfile.TemporaryDirectory()
        self.settings = os.path.join(self.tmp.name, "s.json")
        self.alerts = []
        self.opened = []
        self.app = github_profiles.ProfilesApp(
            self.root, urlopen=FakeGitHub([repo("a", 1, 0), repo("b", 9, 0)]), settings_path=self.settings,
            alert=self.alerts.append, opener=self.opened.append)

    def tearDown(self):
        self.root.destroy()
        self.tmp.cleanup()

    def test_cari_dan_tampilkan(self):
        self.app.username.set("octo")
        self.assertIsNotNone(self.app.search())
        self.assertEqual(self.app.login_label.cget("text"), "octo")
        self.assertIn("1.234 followers", self.app.stats_label.cget("text"))
        self.assertEqual(self.app.repo_rows[0][1].cget("text"), "b")
        self.assertEqual(self.app.repo_rows[0][0].winfo_manager(), "pack")
        self.assertEqual(self.app.repo_rows[2][0].winfo_manager(), "")  # hanya 2 repo
        self.assertIsNotNone(self.app.avatar_photo)

    def test_peringatan_username(self):
        self.app.username.set("-bad-")
        self.assertIsNone(self.app.search())
        self.app.username.set("hantu")
        self.app.search()
        self.assertEqual(len(self.alerts), 2)
        self.assertIn("bukan username", self.alerts[0])
        self.assertIn("tidak ditemukan", self.alerts[1])

    def test_tema_tersimpan(self):
        self.assertEqual(self.app.theme, "light")
        self.app.toggle_theme()
        self.assertEqual(self.app.card.cget("background"), github_profiles.THEMES["dark"]["card"])
        self.assertEqual(load_theme(self.settings), "dark")
        again = github_profiles.ProfilesApp(self.root, urlopen=FakeGitHub([]), settings_path=self.settings,
                                            alert=self.alerts.append)
        self.assertEqual(again.theme, "dark")


if __name__ == "__main__":
    unittest.main()

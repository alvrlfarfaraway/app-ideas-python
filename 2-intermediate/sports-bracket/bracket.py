"""Sports Bracket Generator: buat bagan turnamen sistem gugur, isi jadwal dan skor setiap pertandingan.

Jumlah tim harus genap. Kalau bukan pangkat dua (misalnya 6), sebagian tim
mendapat bye (langsung lolos ke babak kedua). Pemenang setiap pertandingan
otomatis maju ke babak berikutnya. Data disimpan otomatis ke
~/.app-ideas-python/bracket.json, jadi tetap ada saat aplikasi dibuka lagi.

Jalankan:
    python bracket.py
"""

import json
import math
import os
from dataclasses import dataclass, field
from datetime import date, datetime

SAVE_PATH = os.path.join(os.path.expanduser("~"), ".app-ideas-python", "bracket.json")
BYE = None
DATE_FORMAT = "%d-%m-%Y"
MAX_TEAMS = 64


class BracketError(ValueError):
    """Isian yang salah; pesannya ditampilkan sebagai peringatan."""


def parse_date(text, label):
    try:
        return datetime.strptime(text.strip(), DATE_FORMAT).date()
    except ValueError:
        raise BracketError(f"{label} tidak valid. Tulis dengan format HH-BB-TTTT, misalnya 15-11-2026.") from None


def round_names(rounds):
    names = []
    for r in range(rounds):
        left = rounds - r
        names.append({1: "Final", 2: "Semifinal", 3: "Perempat final"}.get(left, f"Babak {r + 1}"))
    return names


@dataclass
class Tournament:
    name: str
    start: date
    end: date
    teams: list
    matches: dict = field(default_factory=dict)  # "babak-urutan" -> {"date", "score_a", "score_b"}

    @classmethod
    def create(cls, name, start_text, end_text, team_count):
        name = " ".join(name.split())
        if not name:
            raise BracketError("Isi nama turnamen.")
        start = parse_date(start_text, "Tanggal mulai")
        end = parse_date(end_text, "Tanggal selesai")
        if end < start:
            raise BracketError("Tanggal selesai tidak boleh sebelum tanggal mulai.")
        try:
            count = int(str(team_count).strip())
        except ValueError:
            raise BracketError("Jumlah tim harus angka.") from None
        if count < 2:
            raise BracketError("Turnamen butuh minimal 2 tim.")
        if count % 2:
            raise BracketError(f"Jumlah tim harus genap; {count} adalah bilangan ganjil.")
        if count > MAX_TEAMS:
            raise BracketError(f"Maksimal {MAX_TEAMS} tim.")
        return cls(name, start, end, [f"Tim {i + 1}" for i in range(count)])

    # --- struktur bagan ---------------------------------------------------------
    @property
    def size(self):
        return 2 ** math.ceil(math.log2(len(self.teams)))

    @property
    def rounds(self):
        return int(math.log2(self.size))

    def slots(self):
        """Peserta babak pertama. Bye dibagikan ke tim-tim awal, satu per pertandingan."""
        byes = self.size - len(self.teams)
        slots, teams = [], list(range(len(self.teams)))
        for match in range(self.size // 2):
            if match < byes:
                slots += [teams.pop(0), BYE]
            else:
                slots += [teams.pop(0), teams.pop(0)]
        return slots

    def matches_in(self, round_index):
        return self.size // 2 ** (round_index + 1)

    def data(self, round_index, match):
        return self.matches.setdefault(f"{round_index}-{match}", {"date": "", "score_a": None, "score_b": None})

    def participants(self, round_index, match):
        """(tim_a, tim_b) sebagai indeks tim. BYE = tidak ada lawan; None juga berarti belum diketahui."""
        if round_index == 0:
            slots = self.slots()
            return slots[2 * match], slots[2 * match + 1]
        return self.winner(round_index - 1, 2 * match), self.winner(round_index - 1, 2 * match + 1)

    def is_bye(self, round_index, match):
        return round_index == 0 and self.slots()[2 * match + 1] is BYE

    def winner(self, round_index, match):
        a, b = self.participants(round_index, match)
        if self.is_bye(round_index, match):
            return a
        if a is None or b is None:
            return None
        info = self.data(round_index, match)
        if info["score_a"] is None or info["score_b"] is None or info["score_a"] == info["score_b"]:
            return None
        return a if info["score_a"] > info["score_b"] else b

    @property
    def champion(self):
        index = self.winner(self.rounds - 1, 0)
        return self.teams[index] if index is not None else None

    # --- mengisi pertandingan -----------------------------------------------------
    def rename_team(self, index, name):
        name = " ".join(name.split())
        if not name:
            raise BracketError("Nama tim tidak boleh kosong.")
        if any(t.lower() == name.lower() for i, t in enumerate(self.teams) if i != index):
            raise BracketError(f"Sudah ada tim bernama {name}.")
        self.teams[index] = name

    def set_result(self, round_index, match, date_text="", score_a=None, score_b=None):
        if self.is_bye(round_index, match):
            raise BracketError("Pertandingan ini bye; tidak ada lawan.")
        a, b = self.participants(round_index, match)
        if (score_a is not None or score_b is not None) and (a is None or b is None):
            raise BracketError("Kedua tim belum diketahui; selesaikan babak sebelumnya dulu.")
        info = self.data(round_index, match)
        if date_text.strip():
            when = parse_date(date_text, "Tanggal pertandingan")
            if not self.start <= when <= self.end:
                raise BracketError(f"Tanggal pertandingan harus antara {self.start:{DATE_FORMAT}} dan "
                                   f"{self.end:{DATE_FORMAT}}.")
            info["date"] = when.strftime(DATE_FORMAT)
        else:
            info["date"] = ""
        for value in (score_a, score_b):
            if value is not None and (not isinstance(value, int) or value < 0):
                raise BracketError("Skor harus bilangan bulat 0 atau lebih.")
        if (score_a is None) != (score_b is None):
            raise BracketError("Isi skor kedua tim, atau kosongkan keduanya.")
        if score_a is not None and score_a == score_b:
            raise BracketError("Sistem gugur butuh pemenang; skor tidak boleh seri (pakai skor adu penalti).")
        before = self.winner(round_index, match)
        info["score_a"], info["score_b"] = score_a, score_b
        if self.winner(round_index, match) != before:
            self._reset_after(round_index, match)

    def _reset_after(self, round_index, match):
        """Pemenang berubah: hasil di babak berikutnya yang melibatkan jalur ini tidak berlaku lagi."""
        r, m = round_index + 1, match // 2
        while r < self.rounds:
            info = self.data(r, m)
            info["score_a"] = info["score_b"] = None
            r, m = r + 1, m // 2

    # --- simpan -----------------------------------------------------------------------
    def to_dict(self):
        return {"name": self.name, "start": self.start.isoformat(), "end": self.end.isoformat(),
                "teams": self.teams, "matches": self.matches}

    @classmethod
    def from_dict(cls, data):
        return cls(data["name"], date.fromisoformat(data["start"]), date.fromisoformat(data["end"]),
                   list(data["teams"]), dict(data.get("matches", {})))


def save(tournament, path=SAVE_PATH):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    temp = path + ".tmp"
    with open(temp, "w", encoding="utf-8") as handle:
        json.dump(tournament.to_dict(), handle, ensure_ascii=False, indent=1)
    os.replace(temp, path)


def load(path=SAVE_PATH):
    try:
        with open(path, encoding="utf-8") as handle:
            return Tournament.from_dict(json.load(handle))
    except FileNotFoundError:
        return None
    except (OSError, ValueError, KeyError, TypeError):
        raise BracketError(f"Berkas {path} rusak dan tidak bisa dibuka.") from None


# --- tampilan Tkinter --------------------------------------------------------------

BOX_W, BOX_H, GAP_X, UNIT = 190, 56, 46, 86


class BracketApp:
    def __init__(self, root, save_path=SAVE_PATH, notify=None):
        import tkinter as tk
        from tkinter import ttk

        self.tk, self.ttk = tk, ttk
        self.root = root
        self.save_path = save_path
        self.notify = notify or self._notify
        root.title("Sports Bracket Generator")
        form = ttk.Frame(root, padding=(12, 10))
        form.pack(fill="x")
        self.name = tk.StringVar(value="Piala Kampus 2026")
        self.start = tk.StringVar(value="16-11-2026")
        self.end = tk.StringVar(value="29-11-2026")
        self.count = tk.StringVar(value="8")
        for label, var, width in (("Turnamen", self.name, 24), ("Mulai", self.start, 11), ("Selesai", self.end, 11),
                                  ("Jumlah tim", self.count, 4)):
            ttk.Label(form, text=label).pack(side="left", padx=(0, 4))
            ttk.Entry(form, textvariable=var, width=width).pack(side="left", padx=(0, 12))
        ttk.Button(form, text="Buat bagan", command=self.create).pack(side="left")
        self.warning = tk.StringVar()
        ttk.Label(root, textvariable=self.warning, foreground="#b3261e", padding=(12, 0)).pack(anchor="w")
        self.info = tk.StringVar()
        ttk.Label(root, textvariable=self.info, foreground="#555", padding=(12, 0)).pack(anchor="w")
        frame = ttk.Frame(root, padding=12)
        frame.pack(fill="both", expand=True)
        self.canvas = tk.Canvas(frame, background="#f7f6f2", width=1000, height=600, highlightthickness=0)
        xs = ttk.Scrollbar(frame, orient="horizontal", command=self.canvas.xview)
        ys = ttk.Scrollbar(frame, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(xscrollcommand=xs.set, yscrollcommand=ys.set)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        ys.grid(row=0, column=1, sticky="ns")
        xs.grid(row=1, column=0, sticky="ew")
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)
        self.tournament = None
        try:
            self.tournament = load(save_path)
        except BracketError as error:
            self.warning.set(str(error))
        if self.tournament:
            t = self.tournament
            self.name.set(t.name)
            self.start.set(t.start.strftime(DATE_FORMAT))
            self.end.set(t.end.strftime(DATE_FORMAT))
            self.count.set(str(len(t.teams)))
        self.draw()

    def create(self):
        if self.tournament and any(v["score_a"] is not None for v in self.tournament.matches.values()):
            from tkinter import messagebox
            if not messagebox.askyesno("Buat bagan baru", "Bagan lama beserta skornya akan diganti. Lanjutkan?",
                                       parent=self.root):
                return None
        try:
            self.tournament = Tournament.create(self.name.get(), self.start.get(), self.end.get(), self.count.get())
        except BracketError as error:
            self.warning.set(f"Peringatan: {error}")
            return None
        self.warning.set("")
        self.persist()
        self.draw()
        return self.tournament

    def persist(self):
        if self.tournament:
            save(self.tournament, self.save_path)

    def position(self, round_index, match):
        y = (match + 0.5) * (2 ** round_index) * UNIT + 30
        return 20 + round_index * (BOX_W + GAP_X), y - BOX_H / 2

    def draw(self):
        c = self.canvas
        c.delete("all")
        t = self.tournament
        if not t:
            c.create_text(30, 30, anchor="nw", text="Isi data turnamen lalu tekan Buat bagan.", fill="#777",
                          font=("Segoe UI", 12))
            return
        names = round_names(t.rounds)
        for r in range(t.rounds):
            x, _ = self.position(r, 0)
            c.create_text(x + BOX_W / 2, 10, text=names[r], font=("Segoe UI", 10, "bold"), fill="#555")
            for m in range(t.matches_in(r)):
                self.draw_match(r, m)
        champion = t.champion
        x, _ = self.position(t.rounds, 0)
        y = self.position(t.rounds - 1, 0)[1] + BOX_H / 2  # sejajar dengan kotak final
        c.create_text(x + 10, y - 12, anchor="w", text="Juara", font=("Segoe UI", 10, "bold"), fill="#555")
        c.create_text(x + 10, y + 10, anchor="w", text=champion or "?", font=("Segoe UI", 14, "bold"),
                      fill="#b8860b" if champion else "#999")
        c.configure(scrollregion=c.bbox("all"))
        played = sum(1 for k, v in t.matches.items() if v["score_a"] is not None)
        total = sum(t.matches_in(r) for r in range(t.rounds)) - (t.size - len(t.teams))
        self.info.set(f"{t.name}: {t.start:{DATE_FORMAT}} s/d {t.end:{DATE_FORMAT}} | {len(t.teams)} tim, "
                      f"{t.rounds} babak | {played}/{total} pertandingan selesai | klik pertandingan untuk mengisi")

    def draw_match(self, r, m):
        c, t = self.canvas, self.tournament
        x, y = self.position(r, m)
        tag = f"match-{r}-{m}"
        a, b = t.participants(r, m)
        info = t.data(r, m)
        winner = t.winner(r, m)
        bye = t.is_bye(r, m)
        c.create_rectangle(x, y, x + BOX_W, y + BOX_H, fill="#ffffff", outline="#c9c4b8", tags=tag)
        c.create_line(x, y + BOX_H / 2, x + BOX_W, y + BOX_H / 2, fill="#e6e2d8", tags=tag)
        for row, (team, score) in enumerate(((a, info["score_a"]), (b, info["score_b"]))):
            ty = y + BOX_H / 4 + row * BOX_H / 2
            if team is BYE and bye and row == 1:
                label, color = "bye", "#aaa"
            elif team is None:
                label, color = "menunggu pemenang", "#aaa"
            else:
                label = t.teams[team]
                color = "#1f7a44" if winner is not None and team == winner else "#1d1d1b"
            weight = "bold" if winner is not None and team == winner else "normal"
            c.create_text(x + 8, ty, anchor="w", text=label, fill=color, font=("Segoe UI", 10, weight), tags=tag)
            if score is not None:
                c.create_text(x + BOX_W - 8, ty, anchor="e", text=str(score), font=("Segoe UI", 10, weight), tags=tag)
        if info["date"]:
            c.create_text(x + BOX_W, y - 2, anchor="se", text=info["date"], fill="#888", font=("Segoe UI", 8), tags=tag)
        if r < t.rounds - 1:  # garis ke pertandingan berikutnya
            nx, ny = self.position(r + 1, m // 2)
            mid = x + BOX_W + GAP_X / 2
            c.create_line(x + BOX_W, y + BOX_H / 2, mid, y + BOX_H / 2, mid, ny + BOX_H / 2, nx, ny + BOX_H / 2,
                          fill="#b9b3a5")
        elif r == t.rounds - 1:
            c.create_line(x + BOX_W, y + BOX_H / 2, x + BOX_W + 16, y + BOX_H / 2, fill="#b9b3a5")
        c.tag_bind(tag, "<Button-1>", lambda _e: self.edit_match(r, m))

    def update_match(self, r, m, team_a=None, team_b=None, date_text="", score_a="", score_b=""):
        """Simpan isian satu pertandingan. Mengembalikan True kalau berhasil."""
        t = self.tournament
        try:
            a, b = t.participants(r, m)
            if r == 0:  # nama tim hanya bisa diubah di babak pertama
                if team_a is not None and a is not None:
                    t.rename_team(a, team_a)
                if team_b is not None and b is not None:
                    t.rename_team(b, team_b)
            if not t.is_bye(r, m):
                scores = [int(s) if str(s).strip() else None for s in (score_a, score_b)]
                t.set_result(r, m, date_text, *scores)
        except ValueError as error:
            message = str(error) if isinstance(error, BracketError) else "Skor harus angka."
            self.notify(message)
            return False
        self.persist()
        self.draw()
        return True

    def edit_match(self, r, m):
        tk, ttk, t = self.tk, self.ttk, self.tournament
        a, b = t.participants(r, m)
        info = t.data(r, m)
        dialog = tk.Toplevel(self.root)
        dialog.title(f"{round_names(t.rounds)[r]} - pertandingan {m + 1}")
        dialog.transient(self.root)
        body = ttk.Frame(dialog, padding=12)
        body.pack()
        fields = {}
        for row, (team, score_key) in enumerate(((a, "score_a"), (b, "score_b"))):
            name = tk.StringVar(value=t.teams[team] if team is not None else "")
            score = tk.StringVar(value="" if info[score_key] is None else str(info[score_key]))
            entry = ttk.Entry(body, textvariable=name, width=24)
            entry.grid(row=row, column=0, pady=3)
            if r > 0 or team is None:
                entry.configure(state="disabled")
            ttk.Entry(body, textvariable=score, width=5).grid(row=row, column=1, padx=6)
            fields[row] = (name, score)
        when = tk.StringVar(value=info["date"])
        ttk.Label(body, text="Tanggal (HH-BB-TTTT)").grid(row=2, column=0, sticky="w", pady=(8, 0))
        ttk.Entry(body, textvariable=when, width=12).grid(row=3, column=0, sticky="w")

        def ok():
            if self.update_match(r, m, fields[0][0].get() if r == 0 else None, fields[1][0].get() if r == 0 else None,
                                 when.get(), fields[0][1].get(), fields[1][1].get()):
                dialog.destroy()
        ttk.Button(body, text="Simpan", command=ok).grid(row=3, column=1, sticky="e")
        return dialog

    def _notify(self, message):
        from tkinter import messagebox

        messagebox.showwarning("Sports Bracket", message, parent=self.root)


def main():
    import tkinter as tk

    root = tk.Tk()
    BracketApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()

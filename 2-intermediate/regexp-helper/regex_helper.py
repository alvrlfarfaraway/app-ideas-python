"""Regular Expression Helper: uji regex terhadap teks dan lihat bagian yang cocok disorot.

Fungsi dan flag meniru RegExp JavaScript (yang dipakai spesifikasi), dijalankan
dengan modul re Python:
    test    -> True/False, ada kecocokan atau tidak
    search  -> indeks kecocokan pertama, atau -1
    match   -> tanpa g: kecocokan pertama beserta grupnya; dengan g: semua kecocokan
Flag: g (global), i (abaikan huruf besar/kecil), m (multiline: ^ dan $ per baris),
      s (dotAll: . juga cocok dengan baris baru), y (sticky: harus cocok mulai dari posisi 0)

Grup bernama gaya JavaScript (?<nama>...) otomatis diubah ke gaya Python (?P<nama>...).

Jalankan:
    python regex_helper.py                                    # jendela Tkinter
    python regex_helper.py "\\d+" "ada 12 apel dan 3 jeruk" --flags g --fn match
"""

import argparse
import re
import sys
from dataclasses import dataclass, field

FLAGS = {"g": "global", "i": "abaikan besar/kecil", "m": "multiline", "s": "dotAll", "y": "sticky"}
FUNCTIONS = ("test", "search", "match")
JS_NAMED_GROUP = re.compile(r"(?<!\\)\(\?<(?![=!])")


class RegexError(ValueError):
    """Regex kosong atau tidak valid."""


@dataclass
class Result:
    function: str
    value: object  # bool, int, atau list
    spans: list = field(default_factory=list)  # (awal, akhir) bagian yang disorot
    message: str = ""


def to_python(pattern):
    """Ubah sintaks khas JavaScript ke Python: (?<nama>...) -> (?P<nama>...)."""
    return JS_NAMED_GROUP.sub("(?P<", pattern)


def compile_pattern(pattern, flags=""):
    if not pattern:
        raise RegexError("Masukkan regular expression dulu.")
    unknown = sorted(set(flags) - set(FLAGS))
    if unknown:
        raise RegexError(f"Flag {''.join(unknown)} tidak dikenal. Pilihan: {', '.join(FLAGS)}.")
    options = 0
    if "i" in flags:
        options |= re.IGNORECASE
    if "m" in flags:
        options |= re.MULTILINE
    if "s" in flags:
        options |= re.DOTALL
    try:
        return re.compile(to_python(pattern), options)
    except re.error as error:
        where = f" (posisi {error.pos})" if error.pos is not None else ""
        raise RegexError(f"Regex tidak valid: {error.msg}{where}.") from None


def find_matches(regex, text, flags):
    """Daftar re.Match sesuai flag g dan y."""
    sticky = "y" in flags
    if "g" not in flags:
        found = regex.match(text) if sticky else regex.search(text)
        return [found] if found else []
    if not sticky:
        return list(regex.finditer(text))
    matches, position = [], 0
    while position <= len(text):  # sticky + global: kecocokan harus bersambung dari posisi 0
        found = regex.match(text, position)
        if not found:
            break
        matches.append(found)
        position = found.end() + (1 if found.end() == found.start() else 0)
    return matches


def run(pattern, text, flags="", function="test"):
    if function not in FUNCTIONS:
        raise RegexError(f"Fungsi harus salah satu dari {', '.join(FUNCTIONS)}.")
    if text == "":
        raise RegexError("Masukkan teks yang akan diuji.")
    regex = compile_pattern(pattern, flags)
    matches = find_matches(regex, text, flags)
    spans = [m.span() for m in matches]
    if function == "test":
        value = bool(matches)
        message = "true: pola ditemukan." if value else "false: tidak ada teks yang cocok."
    elif function == "search":
        value = matches[0].start() if matches else -1
        message = f"Kecocokan pertama di indeks {value}." if matches else "-1: tidak ada teks yang cocok."
    elif "g" in flags:
        value = [m.group(0) for m in matches] or None  # seperti JavaScript: null kalau tidak ada yang cocok
        message = f"{len(value)} kecocokan: {value}" if value else "null: tidak ada teks yang cocok."
    else:
        if matches:
            m = matches[0]
            value = [m.group(0), *m.groups()]
            named = {k: v for k, v in m.groupdict().items()}
            message = f"Cocok '{m.group(0)}' di indeks {m.start()}"
            if m.groups():
                message += f"; grup: {list(m.groups())}"
            if named:
                message += f"; grup bernama: {named}"
            message += "."
        else:
            value, message = None, "null: tidak ada teks yang cocok."
    if "g" not in flags and function != "match" and matches:
        spans = spans[:1]
    return Result(function, value, spans, message)


# --- tampilan Tkinter ------------------------------------------------------------

class HelperApp:
    def __init__(self, root):
        import tkinter as tk
        from tkinter import ttk

        self.root = root
        root.title("Regular Expression Helper")
        frame = ttk.Frame(root, padding=14)
        frame.pack(fill="both", expand=True)
        frame.columnconfigure(1, weight=1)

        ttk.Label(frame, text="Regex").grid(row=0, column=0, sticky="w")
        row = ttk.Frame(frame)
        row.grid(row=0, column=1, sticky="we")
        ttk.Label(row, text="/", font=("Consolas", 13)).pack(side="left")
        self.pattern = tk.StringVar(value=r"(?<tahun>\d{4})-(?<bulan>\d{2})")
        ttk.Entry(row, textvariable=self.pattern, font=("Consolas", 13)).pack(side="left", fill="x", expand=True)
        ttk.Label(row, text="/", font=("Consolas", 13)).pack(side="left")
        self.flag_text = tk.StringVar()
        ttk.Label(row, textvariable=self.flag_text, font=("Consolas", 13), width=5).pack(side="left")

        options = ttk.Frame(frame)
        options.grid(row=1, column=1, sticky="w", pady=8)
        flags_button = ttk.Menubutton(options, text="Flags")
        flags_menu = tk.Menu(flags_button, tearoff=False)
        self.flags = {}
        for flag, label in FLAGS.items():
            var = tk.BooleanVar(value=flag == "g")
            flags_menu.add_checkbutton(label=f"{flag}  {label}", variable=var, command=self.update_flags)
            self.flags[flag] = var
        flags_button["menu"] = flags_menu
        flags_button.pack(side="left")
        ttk.Label(options, text="Fungsi").pack(side="left", padx=(14, 4))
        self.function = tk.StringVar(value="match")
        ttk.Combobox(options, textvariable=self.function, values=FUNCTIONS, state="readonly", width=8).pack(side="left")
        ttk.Button(options, text="Run", command=self.run).pack(side="left", padx=14)

        ttk.Label(frame, text="Teks").grid(row=2, column=0, sticky="nw")
        self.text = tk.Text(frame, height=9, width=70, wrap="word", font=("Consolas", 12), undo=True)
        self.text.grid(row=2, column=1, sticky="nsew")
        self.text.insert("1.0", "Rilis pertama 1991-02, versi 3.0 pada 2008-12,\ndan Python 3.12 rilis 2023-10.")
        self.text.tag_configure("match0", background="#ffe08a")
        self.text.tag_configure("match1", background="#b9e3ff")
        self.message = tk.StringVar()
        self.message_label = ttk.Label(frame, textvariable=self.message, wraplength=640, justify="left")
        self.message_label.grid(row=3, column=1, sticky="w", pady=(10, 0))
        root.bind("<Control-Return>", lambda _e: self.run())
        self.update_flags()
        self.run()

    @property
    def flag_string(self):
        return "".join(flag for flag, var in self.flags.items() if var.get())

    def update_flags(self):
        self.flag_text.set(self.flag_string)

    def clear_highlight(self):
        for tag in ("match0", "match1"):
            self.text.tag_remove(tag, "1.0", "end")

    def run(self):
        self.clear_highlight()
        source = self.text.get("1.0", "end-1c")
        try:
            result = run(self.pattern.get(), source, self.flag_string, self.function.get())
        except RegexError as error:
            self.message.set(f"Peringatan: {error}")
            self.message_label.configure(foreground="#b3261e")
            return None
        for index, (start, end) in enumerate(result.spans):
            if end > start:  # kecocokan kosong tidak bisa disorot
                # Warna bergantian supaya kecocokan yang bersebelahan tetap terbedakan.
                self.text.tag_add(f"match{index % 2}", f"1.0+{start}c", f"1.0+{end}c")
        prefix = f"{self.function.get()}(): "
        self.message.set(prefix + result.message)
        self.message_label.configure(foreground="#1d1d1b" if result.spans else "#b3261e")
        return result


def main(argv=None, gui=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Uji regular expression.")
    parser.add_argument("pattern", nargs="?", help="regular expression (kosong: buka jendela)")
    parser.add_argument("text", nargs="?", help="teks yang diuji")
    parser.add_argument("--flags", default="", help="gabungan g, i, m, s, y; misalnya gi")
    parser.add_argument("--fn", choices=FUNCTIONS, default="test", help="fungsi RegExp (bawaan: test)")
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    if args.pattern is None:
        (gui or run_gui)()
        return 0
    try:
        result = run(args.pattern, args.text or "", args.flags, args.fn)
    except RegexError as error:
        print(f"Peringatan: {error}", file=sys.stderr)
        return 1
    print(f"{args.fn}(): {result.message}")
    if result.spans:
        marks = [" "] * len(args.text)
        for start, end in result.spans:
            for i in range(start, max(end, start + 1)):
                if i < len(marks):
                    marks[i] = "^"
        print(args.text)
        print("".join(marks).rstrip())
    return 0


def run_gui():
    import tkinter as tk

    root = tk.Tk()
    HelperApp(root)
    root.mainloop()


if __name__ == "__main__":
    raise SystemExit(main())

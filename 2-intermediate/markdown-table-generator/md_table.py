"""Markdown Table Generator: isi tabel di jendela, dapatkan tabel Markdown yang rapi.

Baris pertama adalah judul kolom. Perataan diatur per kolom atau untuk seluruh
tabel, karena itulah yang didukung Markdown (baris pemisah :---, :---:, ---:).
Kolom diisi spasi supaya lurus, dengan memperhitungkan huruf lebar (CJK, emoji).

Jalankan:
    python md_table.py                          # jendela Tkinter
    python md_table.py data.csv                 # CSV -> tabel Markdown di terminal
    python md_table.py data.csv --align l,c,r
"""

import argparse
import csv
import io
import sys
import unicodedata

ALIGNS = ("left", "center", "right", "none")
SHORT = {"l": "left", "c": "center", "r": "right", "n": "none", "-": "none"}


def display_width(text):
    """Lebar tampilan di font monospace: huruf CJK dan emoji dihitung 2 kolom."""
    width = 0
    for ch in text:
        if unicodedata.combining(ch) or ch in "\u200d\ufe0f":
            continue
        width += 2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1
    return width


def escape_cell(text):
    """Isi sel aman untuk Markdown: | di-escape, baris baru menjadi <br>."""
    text = str(text).replace("\r\n", "\n").replace("\r", "\n").strip()
    return text.replace("\\|", "|").replace("|", "\\|").replace("\n", "<br>")


class Table:
    """Data tabel: rows[0] adalah judul kolom. Tanpa Tkinter supaya mudah diuji."""

    def __init__(self, rows=3, cols=3):
        if rows < 1 or cols < 1:
            raise ValueError("Tabel butuh minimal 1 baris dan 1 kolom.")
        self.rows = [["" for _ in range(cols)] for _ in range(rows)]
        self.aligns = ["none"] * cols

    @classmethod
    def from_rows(cls, rows):
        width = max((len(r) for r in rows), default=0)
        if not rows or width == 0:
            raise ValueError("Data kosong.")
        table = cls(len(rows), width)
        for r, row in enumerate(rows):
            for c, value in enumerate(row):
                table.rows[r][c] = str(value)
        return table

    @property
    def row_count(self):
        return len(self.rows)

    @property
    def col_count(self):
        return len(self.aligns)

    def set(self, row, col, value):
        self.rows[row][col] = value

    def insert_row(self, index):
        index = max(0, min(index, self.row_count))
        self.rows.insert(index, [""] * self.col_count)

    def insert_col(self, index):
        index = max(0, min(index, self.col_count))
        for row in self.rows:
            row.insert(index, "")
        self.aligns.insert(index, "none")

    def delete_row(self, index):
        if self.row_count == 1:
            raise ValueError("Baris terakhir tidak bisa dihapus.")
        del self.rows[index]

    def delete_col(self, index):
        if self.col_count == 1:
            raise ValueError("Kolom terakhir tidak bisa dihapus.")
        for row in self.rows:
            del row[index]
        del self.aligns[index]

    def align_col(self, index, align):
        if align not in ALIGNS:
            raise ValueError(f"Perataan harus salah satu dari {', '.join(ALIGNS)}.")
        self.aligns[index] = align

    def align_all(self, align):
        for index in range(self.col_count):
            self.align_col(index, align)

    def to_markdown(self, pad=True):
        cells = [[escape_cell(v) for v in row] for row in self.rows]
        widths = [max(3, *(display_width(row[c]) for row in cells)) for c in range(self.col_count)]
        if not pad:
            widths = [0] * self.col_count

        def fit(text, width, align):
            gap = width - display_width(text)
            if gap <= 0:
                return text
            if align == "right":
                return " " * gap + text
            if align == "center":
                return " " * (gap // 2) + text + " " * (gap - gap // 2)
            return text + " " * gap

        def line(values):
            return "| " + " | ".join(values) + " |"

        out = [line(fit(v, w, a) for v, w, a in zip(cells[0], widths, self.aligns))]
        separators = []
        for width, align in zip(widths, self.aligns):
            # Panjang pemisah sama dengan lebar kolom (minimal 3), titik dua menandai arah perataan.
            width = max(width, 3)
            left = ":" if align in ("left", "center") else ""
            right = ":" if align in ("right", "center") else ""
            separators.append(left + "-" * (width - len(left) - len(right)) + right)
        out.append(line(separators))
        out += [line(fit(v, w, a) for v, w, a in zip(row, widths, self.aligns)) for row in cells[1:]]
        return "\n".join(out)


def parse_aligns(text, count):
    """'l,c,r' -> ['left', 'center', 'right']; satu nilai berlaku untuk semua kolom."""
    parts = [p.strip().lower() for p in text.split(",") if p.strip()]
    values = [SHORT.get(p, p) for p in parts]
    for value in values:
        if value not in ALIGNS:
            raise ValueError(f"Perataan '{value}' tidak dikenal. Pakai l, c, r, atau n.")
    if len(values) == 1:
        return values * count
    if len(values) != count:
        raise ValueError(f"Tabel punya {count} kolom, tetapi perataan yang diberikan {len(values)}.")
    return values


# --- tampilan Tkinter -------------------------------------------------------------

ALIGN_LABELS = {"left": "Kiri", "center": "Tengah", "right": "Kanan", "none": "Bawaan"}


class TableApp:
    def __init__(self, root, table=None):
        import tkinter as tk
        from tkinter import ttk

        self.tk = tk
        self.ttk = ttk
        self.root = root
        self.table = table or Table(3, 3)
        self.vars = []
        self.focus = (0, 0)

        root.title("Markdown Table Generator")
        bar = ttk.Frame(root, padding=(12, 10))
        bar.pack(fill="x")
        ttk.Label(bar, text="Baris").pack(side="left")
        self.rows_var = tk.IntVar(value=self.table.row_count)
        ttk.Spinbox(bar, from_=1, to=50, width=4, textvariable=self.rows_var).pack(side="left", padx=(4, 10))
        ttk.Label(bar, text="Kolom").pack(side="left")
        self.cols_var = tk.IntVar(value=self.table.col_count)
        ttk.Spinbox(bar, from_=1, to=20, width=4, textvariable=self.cols_var).pack(side="left", padx=4)
        ttk.Button(bar, text="Buat tabel baru", command=self.new_table).pack(side="left", padx=(6, 18))
        ttk.Label(bar, text="Rata seluruh tabel:").pack(side="left")
        for align in ("left", "center", "right"):
            ttk.Button(bar, text=ALIGN_LABELS[align], width=7,
                       command=lambda a=align: self.align_all(a)).pack(side="left", padx=2)

        hint = "Klik kanan sel untuk menyisipkan/menghapus baris atau kolom dan mengatur perataan kolom."
        ttk.Label(root, text=hint, foreground="#555", padding=(12, 0)).pack(anchor="w")
        self.grid_frame = ttk.Frame(root, padding=12)
        self.grid_frame.pack(fill="x")

        out = ttk.Frame(root, padding=(12, 0, 12, 12))
        out.pack(fill="both", expand=True)
        head = ttk.Frame(out)
        head.pack(fill="x")
        ttk.Label(head, text="Markdown", font=("Segoe UI", 10, "bold")).pack(side="left")
        ttk.Button(head, text="Generate", command=self.generate).pack(side="left", padx=8)
        ttk.Button(head, text="Salin ke clipboard", command=self.copy).pack(side="left")
        self.status = tk.StringVar()
        ttk.Label(head, textvariable=self.status, foreground="#2a7d46").pack(side="left", padx=8)
        self.output = tk.Text(out, height=8, font=("Consolas", 11), wrap="none", background="#f6f8fa")
        self.output.pack(fill="both", expand=True, pady=(4, 10))
        ttk.Label(out, text="Pratinjau", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        self.preview = tk.Frame(out, background="#d1d9e0")
        self.preview.pack(anchor="w", pady=(4, 0))

        self.menu = tk.Menu(root, tearoff=False)
        for label, command in (("Sisipkan baris di atas", lambda: self.edit("row", 0)),
                               ("Sisipkan baris di bawah", lambda: self.edit("row", 1)),
                               ("Sisipkan kolom di kiri", lambda: self.edit("col", 0)),
                               ("Sisipkan kolom di kanan", lambda: self.edit("col", 1)),
                               (None, None),
                               ("Hapus baris ini", lambda: self.edit("delrow")),
                               ("Hapus kolom ini", lambda: self.edit("delcol")),
                               (None, None)):
            if label:
                self.menu.add_command(label=label, command=command)
            else:
                self.menu.add_separator()
        for align in ALIGNS:
            self.menu.add_command(label=f"Kolom ini rata {ALIGN_LABELS[align].lower()}",
                                  command=lambda a=align: self.align_col(a))
        self.build_grid()

    # --- grid ----------------------------------------------------------------
    def build_grid(self):
        for child in self.grid_frame.winfo_children():
            child.destroy()
        self.vars = []
        for r in range(self.table.row_count):
            row_vars = []
            for c in range(self.table.col_count):
                var = self.tk.StringVar(value=self.table.rows[r][c])
                var.trace_add("write", lambda *_a, r=r, c=c, v=var: self.on_edit(r, c, v))
                entry = self.ttk.Entry(self.grid_frame, textvariable=var, width=16,
                                       font=("Segoe UI", 10, "bold" if r == 0 else "normal"),
                                       justify={"right": "right", "center": "center"}.get(self.table.aligns[c], "left"))
                entry.grid(row=r, column=c, padx=1, pady=1)
                entry.bind("<FocusIn>", lambda _e, r=r, c=c: setattr(self, "focus", (r, c)))
                entry.bind("<Button-3>", lambda e, r=r, c=c: self.open_menu(e, r, c))
                row_vars.append(var)
            self.vars.append(row_vars)
        self.generate()

    def on_edit(self, row, col, var):
        self.table.set(row, col, var.get())
        self.generate()

    def open_menu(self, event, row, col):
        self.focus = (row, col)
        self.menu.tk_popup(event.x_root, event.y_root)

    def edit(self, action, offset=0):
        row, col = self.focus
        try:
            if action == "row":
                self.table.insert_row(row + offset)
            elif action == "col":
                self.table.insert_col(col + offset)
            elif action == "delrow":
                self.table.delete_row(row)
            elif action == "delcol":
                self.table.delete_col(col)
        except ValueError as error:
            self.status.set(str(error))
            return
        self.rows_var.set(self.table.row_count)
        self.cols_var.set(self.table.col_count)
        self.build_grid()

    def align_col(self, align):
        self.table.align_col(self.focus[1], align)
        self.build_grid()

    def align_all(self, align):
        self.table.align_all(align)
        self.build_grid()

    def new_table(self):
        try:
            rows, cols = int(self.rows_var.get()), int(self.cols_var.get())
            self.table = Table(rows, cols)
        except (ValueError, self.tk.TclError):
            self.status.set("Jumlah baris dan kolom harus angka 1 atau lebih.")
            return
        self.build_grid()

    # --- keluaran ---------------------------------------------------------------
    def generate(self):
        text = self.table.to_markdown()
        self.output.delete("1.0", "end")
        self.output.insert("1.0", text)
        self.render_preview()
        return text

    def render_preview(self):
        for child in self.preview.winfo_children():
            child.destroy()
        anchors = {"left": "w", "center": "center", "right": "e", "none": "w"}
        for r, row in enumerate(self.table.rows):
            for c, value in enumerate(row):
                label = self.tk.Label(self.preview, text=value, anchor=anchors[self.table.aligns[c]],
                                      font=("Segoe UI", 10, "bold" if r == 0 else "normal"), padx=10, pady=4,
                                      background="#ffffff" if r % 2 else "#f6f8fa")
                label.grid(row=r, column=c, padx=(0, 1), pady=(0, 1), sticky="nsew")

    def copy(self):
        text = self.generate()
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.status.set("Tabel Markdown disalin.")


def main(argv=None, gui=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Buat tabel Markdown.")
    parser.add_argument("csv", nargs="?", help="berkas CSV (kosong: buka jendela; '-' untuk stdin)")
    parser.add_argument("--align", help="perataan kolom, misalnya l,c,r atau satu nilai untuk semua")
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    if not args.csv:
        (gui or run_gui)()
        return 0
    try:
        if args.csv == "-":
            text = sys.stdin.read()
        else:
            with open(args.csv, encoding="utf-8-sig", newline="") as handle:
                text = handle.read()
        rows = [row for row in csv.reader(io.StringIO(text)) if row]
        table = Table.from_rows(rows)
        if args.align:
            for index, align in enumerate(parse_aligns(args.align, table.col_count)):
                table.align_col(index, align)
    except (OSError, ValueError, csv.Error) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    print(table.to_markdown())
    return 0


def run_gui():
    import tkinter as tk

    root = tk.Tk()
    TableApp(root)
    root.mainloop()


if __name__ == "__main__":
    raise SystemExit(main())

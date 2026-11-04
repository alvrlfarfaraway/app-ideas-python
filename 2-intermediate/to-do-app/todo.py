"""To-Do App: tambah, tandai selesai, edit, dan hapus tugas. Data disimpan otomatis.

Tugas disimpan di ~/.app-ideas-python/todo.json setiap kali ada perubahan,
jadi tetap ada saat aplikasi ditutup lalu dibuka lagi.

Jalankan:
    python todo.py
    python todo.py --file tugas-kuliah.json
"""

import argparse
import json
import os
import sys
from datetime import datetime

DEFAULT_FILE = os.path.join(os.path.expanduser("~"), ".app-ideas-python", "todo.json")
FILTERS = ("all", "active", "done")
MAX_TITLE = 200


class TodoError(ValueError):
    """Kesalahan yang ditampilkan ke pengguna."""


def clean_title(title):
    title = " ".join(title.split())
    if not title:
        raise TodoError("Tulis tugasnya dulu.")
    if len(title) > MAX_TITLE:
        raise TodoError(f"Tugas maksimal {MAX_TITLE} karakter.")
    return title


class TodoList:
    def __init__(self, path=None, clock=datetime.now):
        self.path = path
        self.clock = clock
        self.items = []
        self.next_id = 1
        if path:
            self.load()

    def now(self):
        return self.clock().isoformat(timespec="minutes")

    # --- perubahan ------------------------------------------------------------
    def add(self, title):
        item = {"id": self.next_id, "title": clean_title(title), "done": False, "created": self.now(), "completed": None}
        self.next_id += 1
        self.items.append(item)
        self.save()
        return item

    def get(self, item_id):
        for item in self.items:
            if item["id"] == item_id:
                return item
        raise TodoError(f"Tugas #{item_id} tidak ada.")

    def toggle(self, item_id):
        item = self.get(item_id)
        item["done"] = not item["done"]
        item["completed"] = self.now() if item["done"] else None
        self.save()
        return item

    def edit(self, item_id, title):
        item = self.get(item_id)
        item["title"] = clean_title(title)
        self.save()
        return item

    def remove(self, item_id):
        item = self.get(item_id)
        self.items.remove(item)
        self.save()
        return item

    def clear_done(self):
        before = len(self.items)
        self.items = [item for item in self.items if not item["done"]]
        self.save()
        return before - len(self.items)

    def filtered(self, kind="all"):
        if kind not in FILTERS:
            raise TodoError(f"Filter harus salah satu dari {', '.join(FILTERS)}.")
        if kind == "active":
            return [item for item in self.items if not item["done"]]
        if kind == "done":
            return [item for item in self.items if item["done"]]
        return list(self.items)

    def counts(self):
        done = sum(1 for item in self.items if item["done"])
        return {"all": len(self.items), "active": len(self.items) - done, "done": done}

    # --- berkas -----------------------------------------------------------------
    def save(self):
        if not self.path:
            return
        os.makedirs(os.path.dirname(os.path.abspath(self.path)), exist_ok=True)
        temp = self.path + ".tmp"
        with open(temp, "w", encoding="utf-8") as handle:
            json.dump({"next_id": self.next_id, "items": self.items}, handle, ensure_ascii=False, indent=1)
        os.replace(temp, self.path)  # berkas lama tidak rusak kalau program berhenti di tengah menulis

    def load(self):
        try:
            with open(self.path, encoding="utf-8") as handle:
                data = json.load(handle)
        except FileNotFoundError:
            return
        except (OSError, ValueError):
            raise TodoError(f"Berkas {self.path} rusak; tidak ditimpa supaya datanya tidak hilang.") from None
        items = data.get("items") if isinstance(data, dict) else None
        if not isinstance(items, list):
            raise TodoError(f"Berkas {self.path} bukan berkas to-do yang valid.")
        self.items = [i for i in items if isinstance(i, dict) and {"id", "title", "done", "created"} <= set(i)]
        self.next_id = max([data.get("next_id", 1)] + [i["id"] + 1 for i in self.items])


def format_date(stamp):
    if not stamp:
        return ""
    moment = datetime.fromisoformat(stamp)
    months = "Jan Feb Mar Apr Mei Jun Jul Agu Sep Okt Nov Des".split()
    return f"{moment.day} {months[moment.month - 1]} {moment.year}, {moment:%H.%M}"


# --- tampilan Tkinter ---------------------------------------------------------------

FILTER_LABELS = {"all": "Semua", "active": "Aktif", "done": "Selesai"}


class TodoApp:
    def __init__(self, root, todos):
        import tkinter as tk
        from tkinter import ttk

        self.tk = tk
        self.root = root
        self.todos = todos
        root.title("To-Do")
        frame = ttk.Frame(root, padding=14)
        frame.pack(fill="both", expand=True)
        entry_row = ttk.Frame(frame)
        entry_row.pack(fill="x")
        self.new_title = tk.StringVar()
        self.entry = ttk.Entry(entry_row, textvariable=self.new_title, font=("Segoe UI", 12))
        self.entry.pack(side="left", fill="x", expand=True)
        self.entry.bind("<Return>", lambda _e: self.add())
        ttk.Button(entry_row, text="Tambah", command=self.add).pack(side="left", padx=(8, 0))

        filters = ttk.Frame(frame)
        filters.pack(fill="x", pady=(10, 6))
        self.filter = tk.StringVar(value="all")
        self.filter_buttons = {}
        for kind in FILTERS:
            button = ttk.Radiobutton(filters, value=kind, variable=self.filter, command=self.render)
            button.pack(side="left", padx=(0, 12))
            self.filter_buttons[kind] = button
        ttk.Button(filters, text="Hapus yang selesai", command=self.clear_done).pack(side="right")

        style = ttk.Style(root)
        style.configure("Todo.Treeview", rowheight=30, font=("Segoe UI", 11))
        self.tree = ttk.Treeview(frame, columns=("check", "title", "created"), show="headings", height=12,
                                 style="Todo.Treeview", selectmode="browse")
        self.tree.heading("check", text="")
        self.tree.heading("title", text="Tugas")
        self.tree.heading("created", text="Dibuat")
        # Lebar kolom dalam piksel; diukur dari font supaya tetap pas di layar dengan skala DPI berapa pun.
        from tkinter import font as tkfont
        measure = tkfont.Font(root, family="Segoe UI", size=11).measure
        self.tree.column("check", width=measure("☑") + 24, anchor="center", stretch=False)
        self.tree.column("title", width=measure("m" * 32))
        self.tree.column("created", width=measure("30 Des 2026, 23.59") + 20, stretch=False)
        self.tree.tag_configure("done", foreground="#8a8a85", font=("Segoe UI", 11, "overstrike"))
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<Button-1>", self.on_click)
        self.tree.bind("<Double-1>", self.on_double_click)
        self.tree.bind("<Delete>", lambda _e: self.remove_selected())
        self.tree.bind("<space>", lambda _e: self.toggle_selected())

        actions = ttk.Frame(frame)
        actions.pack(fill="x", pady=(8, 0))
        ttk.Button(actions, text="Selesai / Belum", command=self.toggle_selected).pack(side="left")
        ttk.Button(actions, text="Edit", command=self.edit_selected).pack(side="left", padx=6)
        ttk.Button(actions, text="Hapus", command=self.remove_selected).pack(side="left")
        self.status = tk.StringVar()
        ttk.Label(actions, textvariable=self.status, foreground="#b3261e").pack(side="left", padx=10)
        self.editor = None
        self.render()
        self.entry.focus_set()

    # --- data -----------------------------------------------------------------
    def render(self):
        self.tree.delete(*self.tree.get_children())
        for item in self.todos.filtered(self.filter.get()):
            self.tree.insert("", "end", iid=str(item["id"]), tags=("done",) if item["done"] else (),
                             values=("☑" if item["done"] else "☐", item["title"], format_date(item["created"])))
        counts = self.todos.counts()
        for kind, button in self.filter_buttons.items():
            button.configure(text=f"{FILTER_LABELS[kind]} ({counts[kind]})")

    def selected_id(self):
        selection = self.tree.selection()
        return int(selection[0]) if selection else None

    def add(self):
        try:
            self.todos.add(self.new_title.get())
        except TodoError as error:
            self.status.set(str(error))
            return None
        self.new_title.set("")
        self.status.set("")
        if self.filter.get() == "done":
            self.filter.set("all")  # supaya tugas baru langsung terlihat
        self.render()
        return self.todos.items[-1]

    def toggle_selected(self, item_id=None):
        item_id = item_id or self.selected_id()
        if item_id:
            self.todos.toggle(item_id)
            self.render()

    def remove_selected(self, item_id=None):
        item_id = item_id or self.selected_id()
        if item_id:
            self.todos.remove(item_id)
            self.render()

    def clear_done(self):
        count = self.todos.clear_done()
        self.status.set(f"{count} tugas selesai dihapus." if count else "")
        self.render()

    def on_click(self, event):
        if self.tree.identify_column(event.x) == "#1":  # klik kotak centang
            row = self.tree.identify_row(event.y)
            if row:
                self.toggle_selected(int(row))
                return "break"
        return None

    def on_double_click(self, event):
        row = self.tree.identify_row(event.y)
        if row and self.tree.identify_column(event.x) == "#2":
            self.edit_selected(int(row))

    def edit_selected(self, item_id=None):
        """Edit langsung di baris: kotak isian muncul di atas judul tugas."""
        item_id = item_id or self.selected_id()
        if not item_id:
            return None
        if self.editor:
            self.editor.destroy()
        x, y, width, height = self.tree.bbox(str(item_id), "title")
        var = self.tk.StringVar(value=self.todos.get(item_id)["title"])
        editor = self.tk.Entry(self.tree, textvariable=var, font=("Segoe UI", 11))
        editor.place(x=x, y=y, width=width, height=height)
        editor.select_range(0, "end")
        editor.focus_set()

        def commit(_event=None):
            try:
                self.todos.edit(item_id, var.get())
                self.status.set("")
            except TodoError as error:
                self.status.set(str(error))
            editor.destroy()
            self.editor = None
            self.render()
        editor.bind("<Return>", commit)
        editor.bind("<FocusOut>", commit)
        editor.bind("<Escape>", lambda _e: (editor.destroy(), setattr(self, "editor", None)))
        self.editor = editor
        self.editor_var = var
        self.editor_commit = commit
        return editor


def main(argv=None):
    parser = argparse.ArgumentParser(description="Daftar tugas.")
    parser.add_argument("--file", default=DEFAULT_FILE, help="berkas penyimpanan JSON")
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    try:
        todos = TodoList(args.file)
    except TodoError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    import tkinter as tk

    root = tk.Tk()
    TodoApp(root, todos)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

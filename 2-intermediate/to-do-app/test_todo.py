import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta

import todo
from todo import TodoError, TodoList, format_date


class Clock:
    def __init__(self):
        self.now = datetime(2026, 11, 4, 8, 0)

    def __call__(self):
        self.now += timedelta(minutes=15)
        return self.now


class TodoListTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, "sub", "todo.json")
        self.todos = TodoList(self.path, clock=Clock())

    def tearDown(self):
        self.tmp.cleanup()

    def test_tambah(self):
        item = self.todos.add("  Belanja   sayur ")
        self.assertEqual(item["title"], "Belanja sayur")
        self.assertEqual(item["created"], "2026-11-04T08:15")
        self.assertFalse(item["done"])
        for bad in ("", "   ", "x" * 201):
            with self.assertRaises(TodoError):
                self.todos.add(bad)

    def test_selesai_bolak_balik(self):
        item = self.todos.add("A")
        self.todos.toggle(item["id"])
        self.assertTrue(item["done"])
        self.assertEqual(item["completed"], "2026-11-04T08:30")
        self.todos.toggle(item["id"])
        self.assertFalse(item["done"])
        self.assertIsNone(item["completed"])

    def test_edit_dan_hapus(self):
        a = self.todos.add("A")
        b = self.todos.add("B")
        self.todos.edit(a["id"], "A baru")
        self.assertEqual(self.todos.get(a["id"])["title"], "A baru")
        with self.assertRaises(TodoError):
            self.todos.edit(a["id"], " ")
        self.todos.remove(b["id"])
        self.assertEqual([i["id"] for i in self.todos.items], [a["id"]])
        with self.assertRaises(TodoError):
            self.todos.remove(b["id"])

    def test_filter_dan_jumlah(self):
        for title in "ABCD":
            self.todos.add(title)
        self.todos.toggle(2)
        self.todos.toggle(4)
        self.assertEqual([i["title"] for i in self.todos.filtered("active")], ["A", "C"])
        self.assertEqual([i["title"] for i in self.todos.filtered("done")], ["B", "D"])
        self.assertEqual(self.todos.counts(), {"all": 4, "active": 2, "done": 2})
        self.assertEqual(self.todos.clear_done(), 2)
        with self.assertRaises(TodoError):
            self.todos.filtered("besok")

    def test_tersimpan_dan_id_tidak_dipakai_ulang(self):
        self.todos.add("A")
        b = self.todos.add("B")
        self.todos.remove(b["id"])
        again = TodoList(self.path)
        self.assertEqual([i["title"] for i in again.items], ["A"])
        self.assertEqual(again.add("C")["id"], 3)  # bukan 2

    def test_berkas_rusak_tidak_ditimpa(self):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        for content in ("{rusak", json.dumps([1, 2])):
            with open(self.path, "w", encoding="utf-8") as handle:
                handle.write(content)
            with self.assertRaises(TodoError):
                TodoList(self.path)
            with open(self.path, encoding="utf-8") as handle:
                self.assertEqual(handle.read(), content)

    def test_tanggal(self):
        self.assertEqual(format_date("2026-11-04T08:05"), "4 Nov 2026, 08.05")
        self.assertEqual(format_date(None), "")


class GuiTest(unittest.TestCase):
    def setUp(self):
        try:
            import tkinter as tk
            self.root = tk.Tk()
        except Exception as error:
            self.skipTest(f"Tk tidak tersedia: {error}")
        self.root.withdraw()
        self.todos = TodoList(clock=Clock())
        self.app = todo.TodoApp(self.root, self.todos)

    def tearDown(self):
        self.root.destroy()

    def rows(self):
        return [self.app.tree.item(i, "values") for i in self.app.tree.get_children()]

    def test_enter_menambah(self):
        self.assertTrue(self.app.entry.bind("<Return>"))  # Enter terpasang ke add()
        self.app.new_title.set("Kirim laporan")
        self.app.add()
        self.assertEqual(self.rows()[0][:2], ("☐", "Kirim laporan"))
        self.assertEqual(self.app.new_title.get(), "")
        self.app.add()  # kotak kosong
        self.assertIn("Tulis", self.app.status.get())

    def test_selesai_filter_dan_hapus(self):
        for title in ("A", "B", "C"):
            self.app.new_title.set(title)
            self.app.add()
        self.app.toggle_selected(2)
        self.assertEqual(self.rows()[1][0], "☑")
        self.assertIn("done", self.app.tree.item("2", "tags"))
        self.app.filter.set("active")
        self.app.render()
        self.assertEqual([r[1] for r in self.rows()], ["A", "C"])
        self.assertIn("Aktif (2)", self.app.filter_buttons["active"].cget("text"))
        self.app.remove_selected(1)
        self.assertEqual([r[1] for r in self.rows()], ["C"])

    def test_edit_di_baris(self):
        self.app.new_title.set("Lama")
        self.app.add()
        self.root.update()
        self.app.tree.see("1")
        self.root.update()
        self.app.edit_selected(1)
        self.app.editor_var.set("Baru")
        self.app.editor_commit()
        self.assertEqual(self.rows()[0][1], "Baru")


if __name__ == "__main__":
    unittest.main()

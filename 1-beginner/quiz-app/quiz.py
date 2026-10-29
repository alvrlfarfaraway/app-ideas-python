"""Quiz App: kuis pilihan ganda dengan 4 jawaban, waktu pengerjaan, skor, dan lulus/gagal.

Soal ada di folder quizzes/*.json, jadi menambah kuis cukup menambah satu berkas.

Jalankan:
    python quiz.py                          # pilih kuis dari daftar
    python quiz.py --quiz git-dasar --user Ani
    python quiz.py --scores --user Ani      # riwayat skor Ani
"""

import argparse
import json
import os
import random
import sys
import time
import urllib.parse
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
QUIZ_DIR = os.path.join(HERE, "quizzes")
DEFAULT_SCORES = os.path.join(os.path.expanduser("~"), ".app-ideas-python", "quiz-scores.json")
LETTERS = "ABCD"


class QuizAborted(Exception):
    """Pengguna keluar di tengah kuis (input berakhir atau mengetik q)."""


class Quiz:
    def __init__(self, name, title, questions, pass_percent=70):
        self.name = name
        self.title = title
        self.questions = questions
        self.pass_percent = pass_percent


def load_quiz(path):
    """Baca dan validasi satu berkas kuis. ValueError dengan pesan yang menyebut soal yang bermasalah."""
    name = os.path.splitext(os.path.basename(path))[0]
    try:
        with open(path, encoding="utf-8") as file:
            data = json.load(file)
    except FileNotFoundError:
        raise ValueError(f"Kuis '{name}' tidak ditemukan.") from None
    except json.JSONDecodeError as error:
        raise ValueError(f"Berkas kuis '{name}' bukan JSON yang valid: {error.msg} (baris {error.lineno}).") from None
    try:
        questions = data["questions"]
        title = data["title"]
        pass_percent = data.get("pass_percent", 70)
    except (KeyError, TypeError):
        raise ValueError(f"Berkas kuis '{name}' harus punya 'title' dan 'questions'.") from None
    if not isinstance(questions, list) or not questions:
        raise ValueError(f"Kuis '{name}' tidak punya soal.")
    if not isinstance(pass_percent, (int, float)) or not 0 < pass_percent <= 100:
        raise ValueError(f"Kuis '{name}': pass_percent harus lebih dari 0 dan paling besar 100.")
    for number, item in enumerate(questions, start=1):
        where = f"Kuis '{name}' soal {number}"
        if not isinstance(item, dict) or not str(item.get("question", "")).strip():
            raise ValueError(f"{where}: teks soal kosong.")
        answers = item.get("answers")
        if not isinstance(answers, list) or len(answers) != 4 or not all(isinstance(a, str) and a.strip() for a in answers):
            raise ValueError(f"{where}: harus tepat 4 jawaban berupa teks.")
        if len(set(answers)) != 4:
            raise ValueError(f"{where}: ada jawaban yang sama.")
        if not isinstance(item.get("correct"), int) or isinstance(item["correct"], bool) or not 0 <= item["correct"] < 4:
            raise ValueError(f"{where}: 'correct' harus angka 0 sampai 3.")
    return Quiz(name, title, questions, pass_percent)


def list_quizzes(folder=QUIZ_DIR):
    return sorted(os.path.splitext(f)[0] for f in os.listdir(folder) if f.endswith(".json"))


class Result:
    def __init__(self, quiz, correct, total, seconds, wrong):
        self.quiz = quiz
        self.correct = correct
        self.total = total
        self.seconds = seconds
        self.wrong = wrong  # daftar (soal, jawaban pengguna, jawaban benar)
        self.percent = 100 * correct / total
        self.passed = self.percent >= quiz.pass_percent


def parse_choice(text):
    """'a', 'B', '3' -> indeks 0-3; None kalau tidak valid. 'q' -> QuizAborted."""
    text = text.strip().lower()
    if text == "q":
        raise QuizAborted
    if len(text) == 1 and text.upper() in LETTERS:
        return LETTERS.index(text.upper())
    if text in ("1", "2", "3", "4"):
        return int(text) - 1
    return None


def run_quiz(quiz, ask=input, show=print, now=time.monotonic, rng=None):
    """Jalankan kuis: tiap soal menampilkan 4 jawaban (urutannya diacak), lalu lanjut ke soal berikutnya."""
    rng = rng or random.Random()
    questions = list(quiz.questions)
    rng.shuffle(questions)
    started = now()
    correct, wrong = 0, []
    for number, item in enumerate(questions, start=1):
        order = list(range(4))
        rng.shuffle(order)
        show(f"\nSoal {number}/{len(questions)}: {item['question']}")
        for position, original in enumerate(order):
            show(f"  {LETTERS[position]}. {item['answers'][original]}")
        while True:
            try:
                choice = parse_choice(ask("Jawaban (A-D, q = keluar): "))
            except EOFError:
                raise QuizAborted from None
            if choice is not None:
                break
            show("  Ketik A, B, C, atau D.")
        chosen_text = item["answers"][order[choice]]
        right_text = item["answers"][item["correct"]]
        if order[choice] == item["correct"]:
            correct += 1
            show("  Benar!")
        else:
            wrong.append((item["question"], chosen_text, right_text))
            show(f"  Salah. Jawaban yang benar: {right_text}")
            if item.get("explanation"):
                show(f"  Penjelasan: {item['explanation']}")
    return Result(quiz, correct, len(questions), now() - started, wrong)


def format_duration(seconds):
    seconds = int(round(seconds))
    return f"{seconds // 60} menit {seconds % 60} detik" if seconds >= 60 else f"{seconds} detik"


def format_result(result):
    status = "LULUS" if result.passed else "GAGAL"
    return (f"\n=== Hasil: {result.quiz.title} ===\n"
            f"Waktu         : {format_duration(result.seconds)}\n"
            f"Jawaban benar : {result.correct} dari {result.total} ({result.percent:.0f}%)\n"
            f"Batas lulus   : {result.quiz.pass_percent:g}%\n"
            f"Status        : {status}")


def share_text(result):
    verdict = "lulus" if result.passed else "belum lulus"
    return (f"Saya {verdict} kuis {result.quiz.title}: {result.correct}/{result.total} benar "
            f"dalam {format_duration(result.seconds)}!")


def share_url(result):
    return "https://twitter.com/intent/tweet?text=" + urllib.parse.quote(share_text(result))


class ScoreBoard:
    """Skor tersimpan per pengguna, jadi satu kuis bisa dikerjakan berkali-kali dan riwayatnya terlihat."""

    def __init__(self, path, now=datetime.now):
        self.path = path
        self._now = now

    def _load(self):
        try:
            with open(self.path, encoding="utf-8") as file:
                data = json.load(file)
        except FileNotFoundError:
            return []
        except json.JSONDecodeError:
            raise ValueError(f"Berkas skor '{self.path}' rusak dan tidak dibaca agar tidak tertimpa.") from None
        if not isinstance(data, list):
            raise ValueError(f"Format berkas skor '{self.path}' tidak dikenali.")
        return data

    def record(self, user, result):
        entries = self._load()
        entries.append({"user": user, "quiz": result.quiz.name, "date": self._now().strftime("%Y-%m-%d %H:%M"),
                        "correct": result.correct, "total": result.total,
                        "seconds": round(result.seconds, 1), "passed": result.passed})
        os.makedirs(os.path.dirname(os.path.abspath(self.path)), exist_ok=True)
        temp = self.path + ".tmp"
        with open(temp, "w", encoding="utf-8") as file:
            json.dump(entries, file, ensure_ascii=False, indent=2)
        os.replace(temp, self.path)

    def history(self, user):
        return [e for e in self._load() if e["user"].lower() == user.lower()]


def format_history(entries):
    if not entries:
        return "Belum ada skor tersimpan."
    lines = [f"{e['date']}  {e['quiz']:<14}{e['correct']}/{e['total']}  {format_duration(e['seconds']):<14}"
             f"{'LULUS' if e['passed'] else 'GAGAL'}" for e in entries]
    best = max(entries, key=lambda e: e["correct"] / e["total"])
    lines.append(f"\nTerbaik: {best['correct']}/{best['total']} ({best['quiz']}), dikerjakan {len(entries)} kali.")
    return "\n".join(lines)


def main(argv=None, ask=input):
    parser = argparse.ArgumentParser(description="Kuis pilihan ganda.")
    parser.add_argument("--quiz", help="nama kuis (lihat daftar tanpa argumen ini)")
    parser.add_argument("--user", default="tamu", help="nama pengguna untuk menyimpan skor")
    parser.add_argument("--scores", action="store_true", help="tampilkan riwayat skor pengguna lalu keluar")
    parser.add_argument("--score-file", default=DEFAULT_SCORES)
    parser.add_argument("--seed", type=int, help="angka acak tetap (untuk uji)")
    args = parser.parse_args(argv)
    board = ScoreBoard(args.score_file)
    try:
        if args.scores:
            print(format_history(board.history(args.user)))
            return 0
        names = list_quizzes()
        name = args.quiz
        if name is None:
            print("Kuis yang tersedia:")
            for number, available in enumerate(names, start=1):
                print(f"  {number}. {available}")
            picked = ask("Pilih nomor kuis: ").strip()
            if not picked.isdigit() or not 1 <= int(picked) <= len(names):
                raise ValueError("Pilihan kuis tidak valid.")
            name = names[int(picked) - 1]
        quiz = load_quiz(os.path.join(QUIZ_DIR, name + ".json"))
        print(f"\n{quiz.title}: {len(quiz.questions)} soal, lulus bila benar >= {quiz.pass_percent:g}%.")
        ask("Tekan Enter untuk mulai... ")
        result = run_quiz(quiz, ask=ask, rng=random.Random(args.seed))
        print(format_result(result))
        for question, chosen, right in result.wrong:
            print(f"  - {question}\n    jawabanmu: {chosen} | benar: {right}")
        board.record(args.user, result)
        print(f"\nSkor tersimpan untuk '{args.user}'. Bagikan: {share_url(result)}")
    except QuizAborted:
        print("\nKuis dibatalkan; skor tidak disimpan.")
        return 1
    except (ValueError, OSError) as error:
        print(f"Error: {error}")
        return 1
    except EOFError:
        print("\nInput berakhir.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

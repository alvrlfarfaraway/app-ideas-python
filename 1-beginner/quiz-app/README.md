# Quiz App

Kuis pilihan ganda: 4 jawaban per soal, waktu pengerjaan, jumlah benar, dan status lulus atau gagal. Spesifikasi: [Quiz App](https://github.com/florinpop17/app-ideas/blob/master/Projects/1-Beginner/Quiz-App.md).

Hanya pustaka bawaan Python. Soal ada di folder `quizzes/`, satu berkas JSON per kuis (sekarang: **Python Dasar** dan **Git Dasar**, masing-masing 10 soal).

## Menjalankan

```bash
python quiz.py                                  # pilih kuis dari daftar
python quiz.py --quiz git-dasar --user Ani      # langsung ke satu kuis, skor disimpan atas nama Ani
python quiz.py --scores --user Ani              # riwayat skor Ani
```

Jawab dengan `A`-`D` (atau `1`-`4`), `q` untuk keluar. Urutan soal dan urutan jawaban diacak tiap kali. Setelah jawaban salah, jawaban yang benar dan penjelasannya ditampilkan. Di akhir:

```
=== Hasil: Git Dasar ===
Waktu         : 1 menit 12 detik
Jawaban benar : 8 dari 10 (80%)
Batas lulus   : 70%
Status        : LULUS
```

lalu daftar soal yang salah, dan tautan untuk membagikan hasilnya.

## Menambah kuis

Buat `quizzes/nama-kuis.json`:

```json
{
  "title": "Judul Kuis",
  "pass_percent": 70,
  "questions": [
    {"question": "Pertanyaan?", "answers": ["A", "B", "C", "D"], "correct": 2, "explanation": "Opsional."}
  ]
}
```

`correct` adalah indeks jawaban benar (0 sampai 3). Berkas divalidasi saat dimuat: harus tepat 4 jawaban yang berbeda dan `correct` valid, kalau tidak, pesan error menyebut kuis dan nomor soalnya. Tes juga memeriksa semua kuis bawaan.

## Tes

```bash
python -m unittest -v
```

Penjawab di tes membaca pilihan yang tampil di layar (karena urutannya diacak), jadi tes memastikan jawaban benar tetap dihitung benar apa pun urutannya.

## Pemetaan user stories

- [x] Memulai kuis dengan menekan Enter ("tombol" mulai)
- [x] Soal dengan 4 jawaban; setelah memilih langsung ke soal berikutnya sampai selesai
- [x] Statistik akhir: waktu pengerjaan, jumlah benar, dan pesan lulus atau gagal (batas lulus dapat diatur per kuis, bawaan 70%)
- [x] Bonus: bagikan hasil. Dibuat teks dan tautan tweet (`twitter.com/intent/tweet`); program tidak mengirim apa pun sendiri, tautannya baru dibuka kalau Anda mengkliknya.
- [x] Bonus: banyak kuis, pilih saat memulai
- [x] Bonus (versi ringan): "akun" berupa nama pengguna (`--user`) tanpa kata sandi. Skor tiap percobaan disimpan di `~/.app-ideas-python/quiz-scores.json` dan riwayatnya bisa dilihat dengan `--scores`. Kuis yang sama bisa dikerjakan berkali-kali.

# Pomodoro Clock

Teknik Pomodoro: kerja 25 menit, istirahat 5 menit, diulang. Spesifikasi: [Pomodoro Clock](https://github.com/florinpop17/app-ideas/blob/master/Projects/1-Beginner/Pomodoro-Clock.md).

## Menjalankan

```bash
python pomodoro.py                                  # 25 / 5 / 10 menit
python pomodoro.py --work 50 --short 10 --long 20   # durasi sendiri
python pomodoro.py --work 0.1 --short 0.05          # menit boleh pecahan, berguna untuk mencoba cepat
python pomodoro.py --silent                         # tanpa bunyi
```

Ketik perintah lalu Enter: `p` = start/pause, `s` = stop, `r` = reset, `q` = keluar. Tampilannya satu baris yang diperbarui:

```
KERJA             24:12  (berjalan, sesi kerja selesai: 0)
```

## Tes

```bash
python -m unittest -v
```

Kelas `Pomodoro` tidak membaca jam sendiri: waktu dikirim lewat parameter `now`. Karena itu tes bisa menjalankan 4 siklus penuh (lebih dari 2 jam waktu simulasi) dalam milidetik.

## Aturan

- **Stop** menghentikan dan mengembalikan sesi yang sedang berjalan ke durasi penuh; siklus tidak berubah.
- **Reset** kembali ke awal: sesi kerja pertama, hitungan siklus nol.
- **Pause** menahan sisa waktu; melanjutkannya tidak kehilangan atau menambah waktu.
- Sesi berikutnya langsung berjalan saat sesi sebelumnya habis (spesifikasi: setelah kerja, pengguna melihat timer istirahat).
- Kalau satu "tick" terlambat (misalnya komputer tertidur), sisa waktu yang terlewat dibawa ke sesi berikutnya, bukan hilang, bahkan melewati beberapa sesi sekaligus.
- Tampilan `mm:ss` dibulatkan ke atas, jadi `00:00` hanya muncul saat sesinya benar-benar habis.

## Pemetaan user stories

- [x] Timer sesi kerja 25 menit
- [x] Setelah sesi kerja habis, timer istirahat 5 menit
- [x] Start/pause, stop, dan reset
- [x] Bonus: bunyi saat sesi habis (`winsound.Beep` di Windows, bel terminal di OS lain)
- [x] Bonus: durasi kerja dan istirahat bisa diubah sebelum mulai (`--work`, `--short`)
- [x] Bonus: istirahat panjang 10 menit pada istirahat ke-4 (`--long`, `0` untuk mematikan)

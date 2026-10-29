# Stopwatch App

Jam henti untuk mencatat waktu aktivitas. Spesifikasi: [Stopwatch App](https://github.com/florinpop17/app-ideas/blob/master/Projects/1-Beginner/Stopwatch-App.md).

## Menjalankan

```bash
python stopwatch.py
```

Ketik perintah lalu Enter: `s` = start, `x` = stop, `r` = restart, `l` = lap, `c` = hapus semua lap, `q` = keluar. Tampilannya satu baris yang diperbarui terus: `00:03.41  (berjalan)`. Hasil sesi nyata (jeda yang saya beri 0,6 dan 0,5 detik):

```
Lap  1   00:00.61   (total 00:00.61)
Lap  2   00:00.54   (total 00:01.15)
Lap hanya bisa dicatat saat jam berjalan.
```

## Tes

```bash
python -m unittest -v
```

`Stopwatch` tidak membaca jam sendiri; waktu dikirim lewat parameter `now`, jadi tes bisa mensimulasikan jeda panjang (jam berhenti 400 detik) tanpa menunggu.

## Aturan

- **Start setelah stop melanjutkan**, bukan mengulang: waktu saat jam berhenti tidak dihitung, dan waktu yang sudah terkumpul tetap ada.
- **Restart** mengembalikan ke 00:00 dan langsung berjalan. Lap yang sudah tercatat dibiarkan, tetapi selisih lap berikutnya dihitung dari 00:00 yang baru (sebelumnya terhitung negatif; sekarang ada tesnya).
- **Lap** mencatat dua angka: total waktu dan selisih dari lap sebelumnya. Hanya bisa saat jam berjalan.
- **Hapus lap** tidak menghentikan jam; lap berikutnya dihitung dari awal jam lagi.
- Waktu ditampilkan sampai 1/100 detik, **dipotong** bukan dibulatkan, supaya tampilan tidak pernah melompat lebih cepat dari waktu sebenarnya (`59.999` tampil `00:59.99`).
- Jam memakai `time.monotonic()`, yang tidak terpengaruh perubahan jam sistem.

## Pemetaan user stories

- [x] Start jam
- [x] Stop jam
- [x] Setelah stop, start lagi melanjutkan hitungan naik
- [x] Restart jam
- [x] Bonus: lap, ditampilkan langsung di layar
- [x] Bonus: hapus semua lap

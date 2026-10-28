# Your First DB App

Panel kontrol **Load DB**, **Query DB**, dan **Clear DB** di atas database. Spesifikasi: [First DB App](https://github.com/florinpop17/app-ideas/blob/master/Projects/1-Beginner/First-DB-App.md).

Spesifikasi aslinya memakai IndexedDB, database bawaan browser. Di Python padanannya adalah **SQLite** (modul `sqlite3` bawaan), yaitu database dalam satu berkas yang bertahan antar sesi.

## Menjalankan

```bash
python app.py                 # database di customers.db di folder ini
python app.py --db contoh.db
```

Perintah di prompt: `load`, `query`, `clear`, `log`, `quit`. Contoh sesi:

```
[LOAD] [QUERY] [CLEAR (nonaktif)]
> load
Notifikasi: Selesai memuat 2 pelanggan.
[LOAD (nonaktif)] [QUERY] [CLEAR]
> query
ID    Nama      Email                 Order terakhir   Penjualan/tahun
444   Bill      bill@company.com      2026-09-14              1,250.50
555   Donna     donna@home.org        2026-10-02                830.00
```

## Tes

```bash
python -m unittest -v
```

## Struktur

- `customers.py`: kelas `Customer` dengan `initial_load`, `query_all_rows`, dan `remove_all_rows`, padanan kelas di spesifikasi.
- `app.py`: kelas `App` (tombol, notifikasi, log) terpisah dari input/output sehingga bisa diuji, ditambah prompt-nya.

## Pemetaan user stories

Tombol dan panel di browser menjadi perintah dan keluaran terminal.

- [x] Tiga tombol: Load DB, Query DB, Clear DB
- [x] Panel notifikasi (baris `Notifikasi:`) dan panel log berisi riwayat semua notifikasi (perintah `log`)
- [x] Load mengisi database, dengan pesan saat mulai dan selesai
- [x] Query menampilkan semua pelanggan, dengan pesan saat mulai dan selesai, dan pesan kalau tidak ada baris
- [x] Clear menghapus semua baris, dengan pesan saat mulai dan selesai
- [x] Bonus: status tombol sesuai tabel (Load nonaktif setelah terisi, Clear nonaktif saat kosong). Status awal juga mengikuti isi database yang sudah ada, bukan selalu "kosong".
- [x] Bonus: kolom tambahan tanggal order terakhir dan total penjualan setahun
- [x] Bonus: retrospeksi di bawah

## Retrospeksi

**Apa kegunaan database di sisi klien?** Menyimpan status yang harus bertahan antar sesi (pengaturan, draf, keranjang belanja) dan area kerja sementara untuk data dari server yang perlu dirapikan dulu. Dengan SQLite di Python: aplikasi desktop, alat bantu lokal, dan data hasil scraping.

**Dibanding berkas biasa atau local storage?**
- Kelebihan: bisa dicari lewat indeks dan query tanpa memuat semuanya ke memori, ada transaksi (di tes, dua baris dengan email kembar membatalkan seluruh pemuatan), dan ada aturan data seperti `UNIQUE` dan `NOT NULL`.
- Kekurangan: butuh skema dan kode tambahan; untuk beberapa pengaturan sederhana, satu berkas JSON jauh lebih ringan; dan datanya tidak mudah dibaca atau diedit manusia.

**Kapan database cocok?** Tidak ada jawaban 100% ya atau tidak. Pertimbangannya: banyaknya data (puluhan baris cukup berkas), perlunya mencari atau menyaring, perlunya konsistensi saat banyak perubahan sekaligus, dan siapa yang akan mengakses datanya. Di browser maupun lokal, jangan menyimpan data rahasia atau pribadi tanpa perlindungan, karena berkasnya bisa dibaca siapa pun yang punya akses ke perangkat.

## Catatan

`INSERT OR REPLACE` di SQLite menyelesaikan bentrokan `UNIQUE` dengan menghapus baris lain, sehingga data bisa hilang diam-diam. Tes menangkapnya, jadi `initial_load` memakai upsert berdasarkan `userid`; bentrokan email ditolak seperti `ConstraintError` di IndexedDB.

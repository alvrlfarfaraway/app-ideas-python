# Countdown Timer

Hitung mundur hari, jam, menit, dan detik menuju sebuah event. Spesifikasi: [Countdown Timer](https://github.com/florinpop17/app-ideas/blob/master/Projects/1-Beginner/Countdown-Timer-App.md).

Hanya memakai modul bawaan Python (`datetime`, `json`, `time`), sesuai batasan spesifikasi.

## Menjalankan

```bash
python countdown.py start "Tahun Baru" 2027-01-01        # hitung mundur langsung (Ctrl+C untuk berhenti)
python countdown.py start "Rapat" 2026-12-01 09:30       # dengan jam
python countdown.py add "Ulang Tahun" 2027-03-14         # simpan event
python countdown.py watch                                 # hitung mundur semua event tersimpan
python countdown.py list                                  # tampilkan sekali saja
python countdown.py remove "Ulang Tahun"
```

Event tersimpan di `~/.app-ideas-python/countdown.json` (ubah dengan `-f berkas.json`).

## Tes

```bash
python -m unittest -v
```

## Pemetaan user stories

Spesifikasi aslinya memakai kotak isian dan tombol di browser. Di versi terminal, kotak isian menjadi argumen perintah dan tombol Start menjadi perintah `start`.

- [x] Nama event, tanggal, dan waktu opsional (kosong = 00:00 tanggal itu)
- [x] Peringatan kalau nama kosong
- [x] Peringatan kalau tanggal atau waktu salah format, termasuk tanggal yang tidak nyata (`2027-02-30`)
- [x] Peringatan kalau event lebih dari 9999 hari lagi (batas presisi tampilan 4 digit hari)
- [x] Hitung mundur berjalan dan berkurang tiap detik; detik, menit, jam, hari saling meminjam
- [x] Bonus: event tersimpan antar sesi
- [x] Bonus: peringatan (bunyi bel dan pesan) saat event tercapai
- [x] Bonus: banyak event, masing-masing punya hitung mundur sendiri

Ketentuan yang saya pilih: tampilan hanya sampai hari (bukan bulan), karena panjang bulan beda-beda dan user stories juga hanya menyebut hari. Tampilan memakai kode ANSI untuk menimpa baris, jadi butuh terminal modern (Windows Terminal, VS Code, atau PowerShell di Windows 11).

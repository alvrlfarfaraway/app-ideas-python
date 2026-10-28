# Bin2Dec

Mengubah bilangan biner (maksimal 8 digit) menjadi desimal. Spesifikasi: [Bin2Dec](https://github.com/florinpop17/app-ideas/blob/master/Projects/1-Beginner/Bin2Dec-App.md).

## Menjalankan

```bash
python bin2dec.py            # mode interaktif
python bin2dec.py 1010       # satu kali konversi -> 10
python bin2dec.py 1010 -m 16 # izinkan sampai 16 digit
```

## Tes

```bash
python -m unittest -v
```

## Cara kerja

Digit dibaca satu per satu dari string, tanpa list. Tiap digit `1` pada posisi ke-`n` dari kanan bernilai `2 ** n` (satu fungsi matematika: pangkat), lalu semuanya dijumlahkan.

| Biner | Hitungan | Desimal |
|---|---|---|
| `1010` | 2³ + 2¹ = 8 + 2 | 10 |
| `11111111` | 2⁸ − 1 | 255 |

## User stories

- [x] Pengguna bisa memasukkan sampai 8 digit biner dalam satu input
- [x] Pengguna diberi tahu (beserta posisinya) kalau ada karakter selain 0 dan 1
- [x] Hasil desimal ditampilkan sebagai satu keluaran
- [x] Bonus: jumlah digit bisa diatur dengan `-m`

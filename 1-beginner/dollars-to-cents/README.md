# Dollars to Cents

Mengubah nilai dolar menjadi sen, lalu memecahnya menjadi koin paling sedikit (quarter 25, dime 10, nickel 5, penny 1). Spesifikasi: [Dollars To Cents](https://github.com/florinpop17/app-ideas/blob/master/Projects/1-Beginner/Dollars-To-Cents-App.md).

## Menjalankan

```bash
python dollars.py 2.75     # 275 sen = 11 koin (11 quarter, 0 dime, 0 nickel, 0 penny)
python dollars.py '$0.58'  # 58 sen = 6 koin (2 quarter, 0 dime, 1 nickel, 3 penny)
python dollars.py          # mode interaktif
```

## Tes

```bash
python -m unittest -v
```

## Catatan

- Perhitungan memakai `Decimal`, bukan `float`. Dengan float, `1.15 * 100` menghasilkan `114.99999999999999`, dan memotongnya ke bilangan bulat memberi 114 sen. Ini salah satu alasan uang tidak boleh disimpan sebagai float.
- Nilai dengan lebih dari dua desimal dibulatkan ke sen terdekat (0.005 menjadi 1 sen).
- Contoh di spesifikasi menulis "$0.58 = 4 koin", padahal 2 quarter + 1 nickel + 3 penny berjumlah 6 koin. Tes memakai hitungan yang benar.
- Algoritma greedy (koin terbesar dulu) memberi jumlah koin minimum untuk set koin AS ini.

## User stories

- [x] Pengguna bisa memasukkan nilai dolar (dengan atau tanpa `$`)
- [x] Pengguna melihat total sen
- [x] Bonus: rincian quarter, dime, nickel, dan penny

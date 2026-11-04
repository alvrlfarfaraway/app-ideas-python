# Calculator CLI

Kalkulator baris perintah dengan sub-command `add`, `sub`, `mul`, `div`, `pow`, dan `sqrt`. Spesifikasi: [Calculator CLI](https://github.com/florinpop17/app-ideas/blob/master/Projects/2-Intermediate/Calculator-CLI.md).

Hanya pustaka bawaan Python (`argparse` dan `decimal`).

## Menjalankan

```bash
python calc.py add 1 2 3            # 6
python calc.py add -f 1.5 2.25      # 3.75
python calc.py add -f 0.1 0.2       # 0.3
python calc.py add even 1 2 3 4     # 6  (2 + 4)
python calc.py add odd 1 2 3 4      # 4  (1 + 3)
python calc.py sub 10 3 2           # 5
python calc.py mul 2 3 4            # 24
python calc.py div 7 2              # 3.5
python calc.py pow 2 10             # 1024
python calc.py pow 2 -2             # 0.25
python calc.py sqrt 2               # 1.414213562373095048801688724
python calc.py -h                   # daftar perintah
python calc.py add -h               # bantuan satu perintah
```

Keluaran `python calc.py add -h`:

```
usage: calc add [-h] [-f] [even|odd] ANGKA [ANGKA ...]

Jumlahkan angka. Tulis 'even' atau 'odd' sebelum angka untuk hanya
menjumlahkan bilangan genap atau ganjil.

positional arguments:
  ANGKA        angka; boleh diawali even atau odd

options:
  -h, --help   show this help message and exit
  -f, --float  terima angka pecahan (desimal)

contoh: calc add 1 2 3 | calc add -f 1.5 2.25 | calc add even 1 2 3 4
```

## Aturan angka

- **Tanpa `-f`:** hanya bilangan bulat yang diterima, seperti di bahasa bertipe statis (catatan di spesifikasi). `add 1.5 2` ditolak dengan pesan yang menyarankan `-f`.
- **Dengan `-f`:** angka dihitung dengan `Decimal`, bukan `float`. Karena itu `0.1 + 0.2` menghasilkan `0.3`, bukan `0.30000000000000004`. Penjumlahan, pengurangan, dan perkalian tetap eksak.
- **Bilangan bulat:** hasilnya eksak berapa pun panjangnya, sampai 4000 digit (`pow 2 100` dicetak lengkap). Batas ini ada karena Python 3.12 menolak mencetak bilangan bulat lebih dari 4300 digit.
- **Pembagian, akar, dan pangkat pecahan:** hasilnya dibulatkan ke 28 digit penting. `div 7 2` menghasilkan `3.5` walaupun tanpa `-f`.
- **Angka sangat besar atau sangat kecil:** ditampilkan dalam notasi ilmiah: `pow -f 10 40` menghasilkan `1E+40`, `div -f 1 1e40` menghasilkan `1E-40`.
- **Pesan error:** ditulis ke stderr dengan kode keluar 1, misalnya untuk pembagian dengan nol, akar bilangan negatif, `0` pangkat negatif, atau `even` yang dipakai bersama `-f`.

## Tes

```bash
python -m unittest -v
```

## Pemetaan user stories

- [x] Menjumlahkan banyak angka dengan `add`
- [x] Angka pecahan dengan flag `-f`
- [x] Menjumlahkan hanya bilangan genap/ganjil dengan `even`/`odd`
- [x] `--help` / `-h` menampilkan semua perintah dan flag
- [x] Bonus: tambah, kurang, kali, bagi (`add`, `sub`, `mul`, `div`)
- [x] Bonus: `-h` di tiap perintah menampilkan bantuan perintah itu
- [x] Bonus: pangkat (`pow`) dan akar kuadrat (`sqrt`)

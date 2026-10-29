# Roman to Decimal Converter

Konversi angka Romawi ke desimal, dan sebaliknya. Spesifikasi: [Roman to Decimal Converter](https://github.com/florinpop17/app-ideas/blob/master/Projects/1-Beginner/Roman-to-Decimal-Converter.md).

## Menjalankan

```bash
python roman.py XIV       # 14
python roman.py 1994      # MCMXCIV
python roman.py           # mode interaktif
```

Arahnya dikenali otomatis: huruf berarti Romawi ke desimal, digit berarti desimal ke Romawi. Huruf besar dan kecil sama saja.

```
$ python roman.py XIA
Error: Simbol 'A' di posisi 3 bukan angka Romawi. Simbol yang sah: I, V, X, L, C, D, M.
$ python roman.py IIII
Error: 'IIII' bukan penulisan angka Romawi yang baku. Maksudmu IV?
```

## Tes

```bash
python -m unittest -v
```

Tes mencakup konversi bolak-balik untuk **semua** nilai 1 sampai 3999.

## Aturan

Simbol: `I`=1, `V`=5, `X`=10, `L`=50, `C`=100, `D`=500, `M`=1000. Rentang yang bisa dinyatakan: **1 sampai 3999** (tanpa garis atas untuk ribuan).

Dua jenis kesalahan dibedakan:

1. **Simbol salah** (misalnya `A`, spasi, atau angka): pesan menyebut karakter dan posisinya.
2. **Simbol sah tapi susunan tidak baku** (`IIII`, `VX`, `IC`, `XXXX`): ditolak, karena bentuk bakunya `IV`, `XCIX`, `XL`. Kalau hasilnya masuk akal, program menyarankan bentuk yang benar. Tidak ada saran untuk pola yang tidak mungkin, seperti `VX`, karena `V`, `L`, dan `D` tidak pernah dikurangkan.

Kebakuan diperiksa per tempat (ribuan, ratusan, puluhan, satuan) dengan satu ekspresi reguler:

```
M{0,3}(CM|CD|D?C{0,3})(XC|XL|L?X{0,3})(IX|IV|V?I{0,3})
```

## Pemetaan user stories

- [x] Memasukkan satu angka Romawi
- [x] Hasil desimal ditampilkan sebagai satu keluaran
- [x] Simbol yang salah menghasilkan pesan error
- [x] Bonus: konversi desimal ke Romawi (arah dikenali otomatis)
- Bonus "konversi otomatis saat mengetik" tidak dibuat: terminal membaca input per baris, jadi konversi berjalan saat Enter ditekan. Itu cocoknya untuk versi web.

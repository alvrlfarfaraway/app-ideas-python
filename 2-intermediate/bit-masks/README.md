# Bit Masks

Mencari kota berdasarkan offset GMT dengan operasi bitwise, bukan deretan `if`. Spesifikasi: [Bit Masks](https://github.com/florinpop17/app-ideas/blob/master/Projects/2-Intermediate/Bit-Masks-App.md).

Hanya pustaka bawaan Python.

## Cara kerjanya

Setiap offset GMT mendapat satu bit:

| Offset | Bit | Nilai |
| --- | --- | --- |
| GMT −12 | 0 | `1 << 0` |
| GMT +0 | 12 | `1 << 12` |
| GMT +12 | 24 | `1 << 24` |

- **Pola kota:** setiap kota menyimpan pola bit zonanya, bukan angka offset.
- **Mencari:** masker dibuat dari offset yang dicari, lalu kota cocok kalau `pola_kota & masker` tidak nol. Satu operasi AND per kota, tanpa membandingkan offset.
- **Beberapa offset sekaligus:** bit-bitnya digabung dengan OR (`|`), misalnya `-4 -5`.
- **Kebalikan (`--not`):** masker dibalik dengan `masker ^ ALL_ZONES`. Hasilnya tetap 25 bit, berbeda dengan `~masker` yang menghasilkan bilangan negatif di Python.

Catatan: spesifikasi menyebut "24 bit untuk GMT +12 sampai −12", tetapi rentang itu berisi 25 offset (−12 sampai +12, termasuk 0). Karena itu yang dipakai 25 bit.

## Menjalankan

```bash
python bitmasks.py 2            # kota di GMT +2
python bitmasks.py -4 -5        # kota di GMT -4 atau -5
python bitmasks.py 2 --not      # kota yang TIDAK di GMT +2
python bitmasks.py 9 --bits     # tampilkan juga pola bitnya
python bitmasks.py              # mode interaktif (awali dengan ! untuk kebalikan)
```

Contoh keluaran `python bitmasks.py -4 -5`:

```
Kota di GMT -4, GMT -5

[ ] Moscow
[ ] Paris
[ ] Berlin
[ ] Brussels
[ ] Amsterdam
[ ] Rome
[ ] London
[ ] Dublin
[x] New York
[x] Washington, DC
[x] St. Louis
[ ] Los Angeles
[ ] Tokyo
[ ] Beijing
[ ] Ho Chi Minh City
[ ] Mumbai

3 dari 16 kota cocok.
```

Dengan `--bits`, terlihat bagaimana AND bekerja (potongan `python bitmasks.py 9 --bits`):

```
masker              0001000000000000000000000

[ ] Moscow            0000000001000000000000000  & masker = 0000000000000000000000000
...
[x] Tokyo             0001000000000000000000000  & masker = 0001000000000000000000000
```

## Tes

```bash
python -m unittest -v
```

Tes membandingkan hasil bitwise dengan cara biasa (`offset == dicari`) untuk semua 25 offset, baik pencarian biasa maupun kebalikannya.

## Pemetaan user stories

- [x] Daftar vertikal 16 kota beserta zonanya, berbentuk kotak centang `[x]`/`[ ]`
- [x] Kotak isian offset GMT (argumen atau mode interaktif)
- [x] Menampilkan kota di offset itu, dicari dengan operasi bitwise
- [x] Bonus: mencari kota yang TIDAK di offset itu (`--not` atau `!2`)
- [x] Bonus: jumlah kota yang cocok

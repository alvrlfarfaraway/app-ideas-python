# TrueOrFalse

Menampilkan hasil operator pembanding **JavaScript** (`==`, `===`, `<`, dan seterusnya) untuk dua nilai, tanpa `eval()`. Spesifikasi: [TrueOrFalse](https://github.com/florinpop17/app-ideas/blob/master/Projects/1-Beginner/True-or-False-App.md).

Programnya ditulis dengan Python, tetapi yang ditiru adalah aturan JavaScript, karena itulah yang membingungkan di aslinya. Contoh: `"0" == false` adalah `true`, sementara `"0" == ""` adalah `false`, padahal `0 == ""` adalah `true`.

## Menjalankan

```bash
python trueorfalse.py 10 9 "<"                              # kedua nilai string
python trueorfalse.py 10 9 "<" --types number number        # kedua nilai angka
python trueorfalse.py 0 false == --types number boolean
python trueorfalse.py "" 0 ==
python trueorfalse.py                                       # mode interaktif
```

Contoh keluaran nyata:

```
$ python trueorfalse.py 10 9 "<"
"10" < "9"  ->  TRUE
$ python trueorfalse.py 10 9 "<" --types number number
10 < 9  ->  FALSE
$ python trueorfalse.py null 0 ">=" --types null number
null >= 0  ->  TRUE
$ python trueorfalse.py null 0 "==" --types null number
null == 0  ->  FALSE
```

Tipe yang bisa dipilih: `string` (bawaan), `number`, `boolean`, `null`, `undefined`.

## Tes

```bash
python -m unittest -v
```

### Dicocokkan dengan JavaScript sungguhan

Tes unit mencerminkan pemahaman saya tentang aturan JavaScript, jadi itu tidak cukup. `crosscheck_js.py` (opsional, butuh Chrome atau Chromium) menjalankan **semua pasangan** dari 47 nilai (string aneh seperti `"0x10"`, `" 12 "`, `"1_0"`, `"Infinity"`, emoji; angka seperti `NaN` dan `-Infinity`; boolean, `null`, `undefined`) dengan 8 operator, baik di program ini maupun di mesin JavaScript Chrome, lalu membandingkan hasilnya.

Hasil: **17.672 perbandingan, 0 selisih.**

```bash
python crosscheck_js.py
```

## Aturan yang ditiru

- **`===` / `!==`**: tipe harus sama dulu. `NaN` tidak sama dengan apa pun, termasuk dirinya sendiri.
- **`==` / `!=`** (kesetaraan abstrak): `null == undefined` benar, tetapi `null` tidak sama dengan nilai lain. Boolean diubah ke angka dulu (`true` jadi 1). String vs angka: string diubah ke angka.
- **`<`, `>`, `<=`, `>=`**: dua string dibandingkan menurut urutan kamus (`"10" < "9"` benar); selain itu keduanya diubah ke angka. Kalau ada `NaN`, semua perbandingan salah. `null >= 0` benar walau `null == 0` salah.
- **String ke angka** mengikuti `Number()` JavaScript: spasi di pinggir dibuang, `""` jadi 0, `"0x1F"` heksadesimal, `"1e3"` eksponen, dan sisanya (`"1,5"`, `"1_000"`, `"nan"`) menjadi `NaN`. Ini sengaja berbeda dari `float()` Python, yang menerima `"nan"` dan `"1_000"`.
- Urutan string memakai unit kode **UTF-16** seperti JavaScript, bukan titik kode Unicode Python. Contoh: emoji 😀 lebih kecil dari `～` (U+FF5E) di JavaScript, tetapi lebih besar menurut Python.

## Pemetaan user stories

- [x] Memasukkan dua string yang dibandingkan
- [x] Memasukkan operator pembanding JavaScript yang valid
- [x] Hasil tampil sebagai TRUE atau FALSE, bersama ungkapan yang dievaluasi
- [x] Peringatan kalau operator atau nilai tidak valid (misalnya `=<`, atau `abc` yang ditandai bertipe number)
- [x] Bonus: tipe tiap nilai bisa ditentukan (`--types`), jadi angka bisa dibandingkan dengan string, string dengan boolean, dan seterusnya
- Tidak ada `eval()`. Masukan yang berbahaya hanyalah teks biasa (ada tesnya).

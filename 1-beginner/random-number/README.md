# Random Number Generator

Bilangan acak dalam rentang minimum sampai maksimum. Spesifikasi: [Random Number Generator](https://github.com/florinpop17/app-ideas/blob/master/Projects/1-Beginner/Random-Number-Generator.md).

## Menjalankan

```bash
python randomnum.py 1 100                    # satu bilangan bulat 1..100
python randomnum.py 1 49 --count 6 --unique  # 6 bilangan berbeda, seperti undian
python randomnum.py -5 5 --negative          # rentang yang memuat negatif
python randomnum.py 0 1 --decimals 3         # tiga angka di belakang koma
python randomnum.py 1 6 --seed 42            # hasil tetap
python randomnum.py                          # menanyakan minimum dan maksimum
```

Contoh keluaran nyata:

```
$ python randomnum.py 1 49 --count 6 --unique --seed 7
21, 10, 26, 42, 4, 5
$ python randomnum.py 0 1 --decimals 3 --seed 2 -n 3
0.978, 0.883, 0.970
```

## Tes

```bash
python -m unittest -v
```

Tes memastikan semua hasil di dalam rentang dan kedua ujung bisa muncul, sebaran kira-kira merata, dan tidak ada hasil yang keluar rentang akibat pembulatan.

## Cara kerja

- Rentang bulat bersifat **inklusif** (`1 6` bisa menghasilkan 1 dan 6), memakai `random.randint`.
- Untuk desimal, `x * 10^N` dibulatkan **ke dalam** rentang (batas bawah ke atas, batas atas ke bawah), diundi sebagai bilangan bulat, lalu dibagi `10^N`. Pendekatan `round(random.uniform(a, b), N)` bisa menghasilkan nilai sedikit di luar rentang atau menyimpang karena float; di sini hasilnya selalu di dalam rentang dan tiap nilai punya peluang sama.
- Batas yang pecahan pada mode bulat ikut dibulatkan ke dalam: `1.5` sampai `4.2` hanya menghasilkan 2, 3, atau 4.
- `--unique` memakai `random.sample`, jadi tidak ada pengulangan. Kalau jumlah yang diminta melebihi jumlah kemungkinan nilai, muncul pesan, bukan loop tanpa akhir.
- Bilangan acak dari modul `random` cocok untuk permainan dan statistik, **bukan** untuk kata sandi atau kunci; untuk itu pakai modul `secrets`.

## Pemetaan user stories

- [x] Menentukan minimum dan maksimum
- [x] "Tombol generate": menjalankan perintah, atau menjawab pertanyaan minimum/maksimum saat dijalankan tanpa argumen
- [x] Bonus: nilai negatif lewat `--negative` (tanpa opsi itu, rentang negatif ditolak dengan pesan)
- [x] Bonus: bilangan desimal lewat `--decimals N`

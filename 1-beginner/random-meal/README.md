# Random Meal Generator

Mengambil resep makanan acak dari API [TheMealDB](https://www.themealdb.com/api.php) dan menampilkan nama, bahan, instruksi, gambar, dan videonya. Spesifikasi: [Random Meal Generator](https://github.com/florinpop17/app-ideas/blob/master/Projects/1-Beginner/Random-Meal-Generator.md).

Hanya pustaka bawaan Python untuk versi terminal. Jendela gambar (`--gui`) memakai Tkinter dan Pillow (`pip install pillow`). API ini gratis dan tanpa akun (memakai kunci uji `1` milik TheMealDB).

## Menjalankan

```bash
python randommeal.py              # satu resep acak di terminal
python randommeal.py --picture    # sekalian simpan gambarnya (meal.jpg) dan membukanya
python randommeal.py --gui        # jendela: klik "Meal acak!" lagi untuk resep lain
```

Contoh keluaran nyata (terpotong):

```
Fish Stew with Rouille
======================
Seafood · France

Bahan:
  - 6 large Prawns
  - 3 tbs Olive Oil
  - 150ml Dry White Wine
  ...

Instruksi:
...
Gambar: https://www.themealdb.com/images/media/meals/...
```

## Tes

```bash
python -m unittest -v
```

Tes memakai jawaban API tiruan, jadi tidak butuh internet dan bisa menguji keadaan yang jarang terjadi: API mengembalikan `{"meals": null}`, server 503, bukan JSON, gambar rusak atau bukan gambar. Tes jendela Tkinter menekan tombolnya dan memeriksa bahwa resep ditampilkan, diganti saat diklik lagi, dan tombol video hanya muncul kalau ada videonya.

## Catatan

- API menyimpan bahan sebagai `strIngredient1..20` dan `strMeasure1..20`. Bahan yang kosong dilewati, dan takaran kosong tidak menyisakan spasi ganda.
- Gambar hanya diterima kalau jenis kontennya `image/*` dan ukurannya maksimal 5 MB; alamat selain `http(s)://` ditolak.
- Kalau gambar gagal diunduh di jendela, resep tetap tampil dengan teks "(gambar tidak tersedia)".
- Pemanggilan jaringan di jendela berjalan di thread terpisah supaya jendela tidak membeku saat menunggu API.
- Resep dan gambarnya milik TheMealDB dan kontributornya; program ini hanya menampilkannya.

## Pemetaan user stories

- [x] Tombol mengambil makanan acak dari API eksternal (`--gui`, atau menjalankan perintah di terminal)
- [x] Menampilkan nama resep, bahan, instruksi, dan gambar
- [x] Klik tombol lagi menghasilkan makanan lain
- [x] Bonus: menampilkan video YouTube (tautan di terminal, tombol "Buka video YouTube" di jendela yang membuka browser)

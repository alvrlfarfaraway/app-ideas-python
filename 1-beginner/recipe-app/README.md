# Recipe App

Buku resep: daftar judul, kartu resep lengkap, pencarian resep di internet, dan simpan ke buku. Spesifikasi: [Recipe App](https://github.com/florinpop17/app-ideas/blob/master/Projects/1-Beginner/Recipe-App.md).

Data resep berupa berkas JSON, sesuai batasan spesifikasi. Enam resep bawaan (`sample-recipes.json`) ditulis dalam bahasa Indonesia dan disalin ke `~/.app-ideas-python/recipes.json` saat pertama dipakai, jadi buku pribadi Anda tidak mengubah berkas di repo. Pencarian memakai [TheMealDB](https://www.themealdb.com/api.php). Hanya pustaka bawaan Python.

## Menjalankan

```bash
python recipes.py                  # panel interaktif
python recipes.py -f resepku.json  # berkas buku resep lain
```

Perintah: `list`, `show <nomor atau judul>`, `search <kata>`, `open <nomor hasil>`, `save`, `photo`, `quit`. Contoh sesi nyata:

```
> show 2
┌─────────────────────────────────
│ TELUR DADAR
└─────────────────────────────────
Jenis hidangan : sarapan (breakfast)
Untuk          : 1 orang
Kesulitan      : pemula

Bahan:
  - 2 butir telur
  - 1 batang daun bawang, iris halus
  ...
> search arrabiata
  1. Spicy Arrabiata Penne  (TheMealDB (Vegetarian))
> open 1
> save
Tersimpan: Spicy Arrabiata Penne
> search zzzzqqq
Peringatan: Tidak ada resep yang cocok dengan 'zzzzqqq'.
```

`show` dan `open` yang baru menggantikan kartu yang sedang tampil. `show` menerima nomor, judul lengkap, atau potongan judul asal hanya cocok dengan satu resep (`show rendang`); kalau cocok dengan beberapa, program menyebutkan semuanya.

## Tes

```bash
python -m unittest -v
```

Tes memakai jawaban API tiruan, jadi tidak butuh internet. Mereka memeriksa semua resep bawaan valid dan lengkap, alur "cari, buka, simpan", penolakan judul ganda, API yang mengembalikan nol hasil atau data rusak, jaringan mati, berkas buku yang rusak (tidak ditimpa), dan satu sesi panel penuh.

## Skema resep

```json
{"title": "...", "meal_type": "breakfast|lunch|supper|snack", "serves": 2, "difficulty": "beginner|intermediate|advanced",
 "ingredients": [{"item": "telur", "amount": "2 butir"}], "steps": ["..."], "photo": "https://...", "source": "..."}
```

`photo` dan `source` opsional. Setiap resep divalidasi saat dimuat dan saat disimpan; pesan error menyebut judul resep yang bermasalah.

## Resep dari API

TheMealDB tidak menyediakan **jumlah porsi** dan **tingkat kesulitan**, jadi di kartu hasil API keduanya tertulis "tidak diketahui", bukan ditebak. **Jenis hidangan** dipetakan dari kategorinya (Breakfast menjadi sarapan, Dessert/Starter/Side menjadi camilan, selebihnya makan siang), jadi itu perkiraan. Teks instruksi dipecah menjadi langkah per paragraf (atau per kalimat bila hanya satu paragraf), dan baris penomoran seperti `1` atau `STEP 2` dibuang.

## Pemetaan user stories

- [x] Daftar judul resep
- [x] Memilih sebuah judul menampilkan kartu: judul, jenis hidangan, jumlah porsi, tingkat kesulitan, bahan dengan takaran, dan langkah persiapan
- [x] Memilih judul lain menggantikan kartu yang sedang tampil
- [x] Bonus: foto hasil jadi. Resep hasil API membawa foto (tautannya tampil di kartu, perintah `photo` membukanya di browser); resep bawaan tidak punya foto.
- [x] Bonus: mencari resep yang tidak ada di daftar lewat nama makanan (`search`)
- [x] Bonus: daftar resep yang cocok, lalu membuka kartunya (`open`)
- [x] Bonus: peringatan kalau tidak ada yang cocok
- [x] Bonus: tombol Save (`save`) untuk resep hasil API menyalinnya ke buku resep; tidak aktif untuk resep yang sudah ada

# Book Finder

Mencari buku berdasarkan kata kunci, judul, penulis, subjek, penerbit, bahasa, atau tahun terbit. Spesifikasi: [Book Finder App](https://github.com/florinpop17/app-ideas/blob/master/Projects/2-Intermediate/Book-Finder-App.md).

Data diambil dari [Open Library Search API](https://openlibrary.org/dev/docs/api/search), yang gratis dan tanpa kunci. Spesifikasi menyarankan Google Books, tetapi saat project ini dibuat Google Books menolak permintaan tanpa kunci API (kode 429, kuota harian 0). Hanya pustaka bawaan Python.

## Menjalankan

```bash
python books.py "laskar pelangi"                 # pencarian bebas
python books.py -t "bumi manusia" -a pramoedya   # gabungan kriteria
python books.py -a "andrea hirata" -y 2005-2008  # rentang tahun terbit pertama
python books.py -s astronomy --lang ind -n 5     # subjek + bahasa (kode ISO 639-2)
python books.py dune --page 2                    # halaman hasil berikutnya
python books.py dune --html hasil.html           # juga tulis halaman HTML berisi sampul
python books.py                                  # mode interaktif
```

Di mode interaktif, kriteria bisa ditulis seperti `dune author:frank herbert year:1965`. Kata bebas ditulis lebih dulu, lalu `title:`, `author:`, `subject:`, `publisher:`, `lang:`, dan `year:`.

Contoh keluaran `python books.py -a "andrea hirata" -y 2005-2008 -n 2`:

```
Menampilkan 1-2 dari 4 buku.

  1. Laskar Pelangi
   Andrea Hirata (2005)
   Bentang | 534 halaman | bahasa: ind
   Sampul: https://covers.openlibrary.org/b/id/7079796-M.jpg
   Info  : https://openlibrary.org/works/OL15302003W

  2. Sang pemimpi
   Andrea Hirata (2006)
   Bentang | 289 halaman | bahasa: ind
   Sampul: https://covers.openlibrary.org/b/id/15218349-M.jpg
   Info  : https://openlibrary.org/works/OL24028184W
```

Tahun yang ditampilkan adalah tahun terbit **pertama** karya itu, bukan tahun edisi tertentu.

## Halaman HTML

`--html hasil.html` menulis halaman berisi kartu buku dengan sampul, penulis, dan tahun. Judul buku menjadi tautan ke halaman buku di Open Library. Tata letaknya menyesuaikan lebar layar (beberapa kolom di desktop, satu kolom di HP) dan mengikuti mode terang/gelap.

Semua teks dari API di-escape, dan hanya tautan `https://` yang dipakai, jadi judul berisi `<script>` tampil sebagai teks biasa.

## Tes

```bash
python -m unittest -v
```

Tes memakai respons tiruan, jadi tidak butuh internet.

## Pemetaan user stories

- [x] Kotak isian kata kunci (argumen atau mode interaktif)
- [x] Mengirim pencarian ke API dan menerima daftar buku berisi judul, penulis, tahun terbit, dan gambar sampul
- [x] Menampilkan daftar buku (teks di terminal, atau halaman HTML dengan `--html`)
- [x] Bonus: tautan ke situs luar (Open Library) untuk tiap buku
- [x] Bonus: desain responsif di halaman HTML
- [x] Bonus: animasi memuat (spinner di terminal selama permintaan berjalan)

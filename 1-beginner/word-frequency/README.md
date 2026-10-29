# Word Frequency

Menghitung berapa kali tiap kata muncul dalam sebuah teks, urut dari yang paling sering. Spesifikasi: [Word Frequency](https://github.com/florinpop17/app-ideas/blob/master/Projects/1-Beginner/Word-Frequency-App.md).

**Buka notebook-nya:** [`word_frequency.ipynb`](word_frequency.ipynb). GitHub menampilkannya lengkap dengan tabel dan grafik, tanpa perlu dijalankan.

## Berkas

| Berkas | Isi |
|---|---|
| `word_frequency.ipynb` | tabel, grafik batang, bubble chart, analisis teks nyata, hukum Zipf |
| `wordfreq.py` | logika yang diuji: `tokenize`, `count_words`, `html_to_text`, `fetch_text`, dan CLI |
| `test_wordfreq.py`, `test_notebook.py` | unit test, dan tes yang mengeksekusi seluruh notebook |

## Menjalankan

```bash
python wordfreq.py catatan.txt                  # dari berkas (maksimal 2048 karakter, sesuai spesifikasi)
python wordfreq.py - < catatan.txt              # dari stdin
python wordfreq.py --url https://example.com --top 10
python wordfreq.py catatan.txt --stopwords id   # buang kata umum (id atau en)
python -m jupyter notebook                      # membuka notebook
python -m unittest -v                           # tes
```

Contoh keluaran nyata dari `python wordfreq.py --url https://example.com --top 4`:

```
  #  Kata   Jumlah
  1  for         2  ████████████████████████
  2  is          2  ████████████████████████
  3  this        2  ████████████████████████
  4  a           1  ████████████

25 kata, 22 kata unik.
```

## Aturan

- **Apa itu kata:** deretan huruf (termasuk beraksen), boleh berisi apostrof atau tanda hubung di tengah (`don't`, `anak-anak`). Huruf besar dan kecil dianggap sama; angka, tanda baca, dan garis bawah dibuang.
- **Urutan:** jumlah turun; jumlah yang sama diurutkan menurut abjad, supaya hasilnya selalu sama.
- **Batas 2048 karakter** berlaku untuk teks yang diketik atau ditempel, sesuai spesifikasi. Teks kosong, teks yang terlalu panjang, dan teks tanpa satu kata pun ditolak dengan pesan jelas. Untuk halaman web (`--url`) tidak ada batas itu, tetapi halaman lebih dari 2 MB ditolak.
- **URL:** hanya `http://` dan `https://`, bukan `file://`. Script, style, dan kepala dokumen dibuang, entitas HTML didekode, dan jenis konten yang bukan teks (misalnya gambar) ditolak.

## Temuan di notebook

Notebook menganalisis prosa dari README seluruh repo ini (sekitar 3.000 kata). Hasil yang terukur, bukan yang diharapkan: pola frekuensinya menurun seperti hukum Zipf dan 52% kata unik hanya muncul sekali, tetapi kemiringan log-log-nya sekitar −0,69, lebih landai dari −1 yang ideal. Korpusnya kecil dan teknis (banyak `x` dari rumus), jadi itu wajar. Notebook menyampaikannya apa adanya.

## Pemetaan user stories

Kotak teks dan tombol "Translate" di browser menjadi argumen terminal dan pemanggilan fungsi di notebook.

- [x] Memasukkan atau menempel teks, maksimal 2048 karakter
- [x] Pesan error kalau teks kosong
- [x] Tabel frekuensi: tiap baris berisi kata dan jumlahnya
- [x] Tabel diurutkan menurun menurut frekuensi
- [x] Bonus: grafik batang, bubble chart, dan plot log-log di notebook; batang teks di terminal
- [x] Bonus: menganalisis halaman web lewat URL (`--url`)

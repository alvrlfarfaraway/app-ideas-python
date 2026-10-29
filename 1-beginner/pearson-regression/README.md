# Pearson Regression

Notebook yang menghitung **koefisien korelasi Pearson**, simpangan baku, dan garis regresi linear untuk dua kumpulan data. Spesifikasi: [Pearson Regression](https://github.com/florinpop17/app-ideas/blob/master/Projects/1-Beginner/Pearson-Regression-App.md).

**Buka notebook-nya:** [`pearson_regression.ipynb`](pearson_regression.ipynb). GitHub menampilkannya lengkap dengan hasil dan grafik, tanpa perlu dijalankan.

## Berkas

| Berkas | Isi |
|---|---|
| `pearson_regression.ipynb` | penjelasan rumus, hitungan langkah demi langkah, grafik, kuartet Anscombe |
| `pearson.py` | semua perhitungan, ditulis sendiri tanpa paket (sesuai batasan spesifikasi) |
| `test_pearson.py`, `test_notebook.py` | unit test, dan tes yang mengeksekusi seluruh notebook |

## Menjalankan

```bash
python pearson.py data.csv      # dari terminal: CSV dua kolom x,y (baris judul boleh ada)
python -m jupyter notebook      # membuka notebook (butuh: pip install notebook pandas numpy matplotlib)
python -m unittest -v           # tes
```

Contoh `python pearson.py data.csv`:

```
Jumlah pasangan : 7
Rata-rata x, y  : 4.0000, 69.0000
Simpangan baku  : 2.1602, 12.5963  (sampel, n-1)
Korelasi Pearson: 0.9922  ->  Some correlation (positif)
Garis regresi   : y = 5.7857 x + 45.8571
```

## Tentang batasan "tanpa paket"

Rumus (`mean`, `std_dev`, `pearson_r`, `linear_regression`) memakai Python murni. `numpy` hanya muncul sebagai **pembanding**: unit test memeriksa bahwa hasilnya sama sampai 9 angka desimal pada 100 set data acak, dan notebook menampilkan keduanya berdampingan. `matplotlib` hanya menggambar.

## Tafsiran hasil

Spesifikasi menyebut tiga tingkat: *No correlation*, *Neutral*, *Some correlation*. Ambang yang dipakai (konvensi, bukan hukum): `|r| < 0.3` tidak ada, `0.3 sampai < 0.7` netral, `≥ 0.7` ada korelasi. Arah (positif/negatif) ditambahkan di hasil. Simpangan baku memakai pembagi `n-1` (sampel).

Kasus yang ditangani dengan pesan jelas, bukan angka palsu: kurang dari 2 pasangan, jumlah x dan y berbeda, dan semua x (atau y) sama, karena $r$ tidak terdefinisi (pembaginya nol).

## Pemetaan user stories

Panel input di browser menjadi kelas `Observations`, yang dicoba di bagian 6 notebook.

- [x] Memasukkan pasangan `x` dan `y`, dan menambahkannya ke tabel (`Observations.add`)
- [x] Pesan kesalahan kalau kosong atau bukan bilangan real (menyebut kolom mana yang salah)
- [x] "Calculate" nonaktif selama ada kesalahan atau data belum cukup (`calculate_enabled`)
- [x] Hasil: rata-rata x dan y, simpangan baku x dan y, korelasi, dan tafsirannya
- [x] Bonus: grafik sebaran
- [x] Bonus: memuat pengamatan dari berkas CSV (`load_csv`)
- [x] Bonus: garis regresi di atas grafik sebaran

Catatan: input interaktif dengan tombol sungguhan butuh `ipywidgets`, yang belum dipasang; di notebook, panelnya dimainkan lewat kode.

# Name Generation using RNNs

Membuat nama Indonesia baru dari 2–3 huruf awal dengan **GRU** (jenis RNN) tingkat karakter. Spesifikasi: [Name Generation using RNNs](https://github.com/florinpop17/app-ideas/blob/master/Projects/2-Intermediate/Name-Generator.md).

Model ditulis sendiri dengan **numpy saja**, tanpa PyTorch atau TensorFlow: forward, backpropagation through time, gradient clipping, weight decay, dan Adam. Proses belajarnya dijelaskan di notebook [`name_generator.ipynb`](name_generator.ipynb).

## Menjalankan

```bash
python name_rnn.py --prefix ar -n 5                 # 5 nama yang diawali "ar"
python name_rnn.py --prefix sri --baru              # hanya nama yang tidak ada di data latih
python name_rnn.py --prefix wi --temperature 0.6    # lebih aman (0.3) atau lebih berani (1.2)
python name_rnn.py --train                          # latih ulang dan simpan ke model/gru-nama.npz
```

Keluaran `python name_rnn.py --prefix ra -n 6 --seed 1`:

```
Ranuar  (baru)
Ralika  (baru)
Rangar  (baru)
Raman  (baru)
Rahil  (baru)
Rayus  (baru)
```

`(baru)` berarti nama itu tidak ada di data latih. Model yang sudah dilatih ada di `model/gru-nama.npz` (73 KB), jadi bisa langsung dipakai.

Butuh `numpy`. Notebook juga butuh `pandas`, `matplotlib`, dan `notebook`.

## Model

Setiap huruf `x` mengubah keadaan tersembunyi `h` (48 angka):

```
z  = sigmoid(Ez[x] + h·Uz + bz)        gerbang pembaruan: seberapa banyak keadaan lama dipertahankan
r  = sigmoid(Er[x] + h·Ur + br)        gerbang reset: seberapa banyak keadaan lama dipakai untuk kandidat
n  = tanh(En[x] + (r ⊙ h)·Un + bn)     kandidat keadaan baru
h' = (1 − z) ⊙ n + z ⊙ h
p  = softmax(h'·Wy + by)               peluang huruf berikutnya (atau "akhir nama")
```

Untuk membuat nama, model membaca huruf awal yang diberikan. Setelah itu huruf berikutnya diambil acak sesuai `p` sampai model memilih "akhir nama".

## Hasil (dari notebook)

- **Gradien:** gradien yang ditulis sendiri cocok dengan gradien numerik di 174 parameter model kecil (selisih relatif terbesar 3,6e-5).
- **Data:** 729 nama Indonesia (`data/nama-indonesia.txt`), yang ditulis sendiri untuk project ini. 15% nama disisihkan sebagai data validasi.
- **Early stopping:** model terbaik ada di langkah 2900. Setelah itu loss latih terus turun tetapi loss validasi naik, tanda model mulai menghafal.
- **Dibanding pembanding** (loss validasi dalam nats per huruf):

  | Model | Loss validasi |
  | --- | --- |
  | Acak seragam | 3,258 |
  | Bigram | 2,413 |
  | GRU | 2,181 |

- **Temperature:** pada 0,8 sekitar 95% nama yang dihasilkan tidak ada di data latih. Pada 0,4 angkanya 69%, dan pada 1,5 sudah 99%, tetapi hasilnya makin sering terdengar asing.

Datanya kecil, jadi sebagian nama terdengar wajar (Arisa, Srita, Wilia, Ralika, Dewiti, Karama), tetapi sebagian lagi janggal (Srisag, Bagpan). Cara paling efektif untuk memperbaikinya adalah menambah data. Tanpa early stopping dan weight decay, model ini hanya mengulang nama-nama dari data latih. Itu terlihat di percobaan pertama: dengan 387 nama dan tanpa regularisasi, hanya 1% hasilnya yang nama baru.

## Tes

```bash
python -m unittest -v
```

Tes mencakup:

- uji gradien numerik,
- loss yang turun saat pelatihan,
- early stopping yang benar-benar menyimpan model terbaik,
- gradient clipping,
- huruf awal yang benar-benar dipakai,
- hasil yang bisa diulang dengan seed,
- simpan/muat model,
- notebook yang dijalankan ulang (sekitar 40 detik).

## Pemetaan user stories

- [x] Menentukan 2–3 huruf awal nama (`--prefix`)
- [x] Melihat nama yang dihasilkan dan memakainya
- [x] Model RNN dengan GRU, dilatih dari dataset nama

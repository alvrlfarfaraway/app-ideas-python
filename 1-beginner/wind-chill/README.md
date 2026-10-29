# Wind Chill

Menghitung suhu yang *terasa* dari suhu udara dan kecepatan angin. Spesifikasi: [Windchill](https://github.com/florinpop17/app-ideas/blob/master/Projects/1-Beginner/Windchill-App.md).

Memakai rumus resmi US National Weather Service dan Meteorological Service of Canada (2001):

| Sistem | Rumus |
|---|---|
| Metrik (T dalam °C, v dalam km/jam) | WC = 13.12 + 0.6215 T − 11.37 v^0.16 + 0.3965 T v^0.16 |
| Inggris (T dalam °F, v dalam mph) | WC = 35.74 + 0.6215 T − 35.75 v^0.16 + 0.4275 T v^0.16 |

## Menjalankan

```bash
python windchill.py -20 30                    # metrik: -20 °C, angin 30 km/jam
python windchill.py 0 15 --system english     # Inggris: 0 °F, angin 15 mph
python windchill.py                           # mode interaktif (ketik 'ganti' untuk ganti sistem)
```

```
$ python windchill.py -20 30
Suhu udara -20 °C, angin 30 km/jam  ->  terasa seperti -32.6 °C
$ python windchill.py 20 30
Error: Wind chill hanya berlaku untuk suhu <= 10 °C (diterima 20).
```

## Tes

```bash
python -m unittest -v
```

Nilai acuan di tes (-20 °C pada 30 km/jam ≈ -33 °C; 0 °F pada 15 mph ≈ -19 °F; 20 °F pada 40 mph ≈ -1 °F) berasal dari tabel resmi dan saya hitung ulang secara terpisah dari kode program. Tes juga memeriksa bahwa kedua sistem satuan memberi suhu terasa yang sama untuk kondisi yang setara.

## Rentang berlaku

Rumus ini hanya sahih untuk **T ≤ 10 °C (50 °F)** dan **v ≥ 4,8 km/jam (3 mph)**. Di luar itu, rumusnya bisa menghasilkan angka yang lebih hangat dari suhu udara, yang tidak masuk akal, jadi program menolaknya dengan pesan, bukan memberi angka palsu. Tes memeriksa seluruh rentang berlaku (suhu -60 sampai 10 °C dan -70 sampai 50 °F, dengan beberapa kecepatan) bahwa hasilnya selalu lebih rendah dari suhu udara.

## Pemetaan user stories

- [x] Memilih sistem satuan, Metrik atau Inggris (`--system`, atau perintah `ganti` di mode interaktif)
- [x] Memasukkan suhu dan kecepatan angin
- [x] Menghitung dan menampilkan wind chill
- [x] Pesan error kalau nilai belum diisi atau bukan angka
- [x] Bonus: error kalau wind chill ≥ suhu udara (pemeriksaan internal di `wind_chill`; dalam rentang berlaku tidak pernah terjadi, dan tes membuktikannya)
- [x] Bonus: menghitung ulang dengan nilai yang sama persis diminta memasukkan nilai baru
- Bonus "hasil diperbarui otomatis saat nilai berubah" tidak dibuat: itu perilaku antarmuka web. Di terminal, hasil muncul setiap perhitungan.

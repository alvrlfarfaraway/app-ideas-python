# FlipImage

Satu gambar diulang dalam matriks 2x2, dan tiap gambar bisa dibalik vertikal atau horizontal dengan tombol panah di sampingnya. Spesifikasi: [Flip Image](https://github.com/florinpop17/app-ideas/blob/master/Projects/1-Beginner/Flip-Image-App.md).

Butuh Pillow: `pip install pillow`. (Larangan pustaka gambar di spesifikasi berlaku untuk versi browser; di Python, Pillow adalah cara wajar memanipulasi gambar.)

## Menjalankan

```bash
python flipimage.py                       # jendela Tkinter dengan gambar contoh
python flipimage.py --image foto.jpg      # gambar sendiri (berkas atau URL)
python flipimage.py --flip 1:left --flip 3:up --flip 4:left --flip 4:down -o hasil.png
```

Nomor gambar: 1 kiri-atas, 2 kanan-atas, 3 kiri-bawah, 4 kanan-bawah. Panah kiri/kanan membalik horizontal, atas/bawah membalik vertikal. Menekan lagi membalikkan ke semula.

Hasil perintah terakhir di atas (`contoh-hasil.png`): gambar 1 terbalik horizontal, 2 asli, 3 terbalik vertikal, 4 keduanya.

![contoh](contoh-hasil.png)

## Tes

```bash
python -m unittest -v
```

Tes memeriksa isi piksel hasil balik (bukan hanya statusnya), bahwa gambar lain tidak ikut berubah, bahwa balik dua kali kembali ke awal, dan bahwa tombol di jendela Tkinter benar-benar membalik gambar yang dimaksud.

## Pemetaan user stories

- [x] Satu gambar diulang dalam matriks 2x2
- [x] Tiap gambar dibalik dengan tombol panah atas, bawah, kiri, kanan di sampingnya (jendela Tkinter)
- [x] Bonus: ganti gambar dengan berkas atau URL lewat `--image`
- [x] Bonus: pesan error kalau gambar tidak ditemukan, bukan gambar yang valid, atau URL tidak terjangkau. Tombol "Display" tidak ada; gambar dipilih saat program dijalankan.

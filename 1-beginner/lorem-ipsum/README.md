# Lorem Ipsum Generator

Membuat paragraf teks pengisi (placeholder) untuk halaman web, desain, dan sejenisnya. Spesifikasi: [Lorem Ipsum Generator](https://github.com/florinpop17/app-ideas/blob/master/Projects/1-Beginner/Lorem-Ipsum-Generator.md).

## Menjalankan

```bash
python lorem.py 3              # 3 paragraf
python lorem.py 5 --copy       # tampilkan dan salin ke clipboard
python lorem.py 2 --seed 42    # hasil sama setiap kali
python lorem.py                # tanya jumlah paragraf
```

Contoh `python lorem.py 1 --seed 7`:

> Lorem ipsum dolor sit amet, consectetur adipiscing elit. Non integer adipiscing do mattis justo incididunt excepteur. Elit tincidunt laboris amet tempor, officia culpa sed ex tempor ante qui elit mattis faucibus. ...

## Tes

```bash
python -m unittest -v
```

## Cara kerja

- Kalimat 6 sampai 16 kata acak dari daftar kata Latin; kalimat 10 kata ke atas diberi satu koma di tengah.
- Paragraf berisi 4 sampai 8 kalimat. Paragraf pertama selalu diawali kalimat klasik "Lorem ipsum dolor sit amet, consectetur adipiscing elit."
- `--seed` mengunci pengacakan (`random.Random(seed)`), jadi hasilnya bisa diulang. Tanpa `--seed`, hasilnya selalu berbeda.
- Jumlah paragraf 1 sampai 100. Angka lain, desimal, atau huruf ditolak dengan pesan jelas.
- Salin ke clipboard memakai perintah OS (`clip` di Windows, `pbcopy` di macOS, `xclip` di Linux). Kalau perintahnya tidak ada, muncul pesan agar menyalin manual.

## Pemetaan user stories

- [x] Pengguna mengetik jumlah paragraf (argumen, atau ditanya saat dijalankan tanpa argumen)
- [x] Pengguna melihat paragrafnya dan bisa menyalinnya (`--copy`, atau seleksi dari terminal)

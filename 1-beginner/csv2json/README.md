# CSV2JSON

Mengubah CSV menjadi JSON, sekaligus membawa fitur [JSON2CSV](../json2csv) (disalin, sesuai petunjuk spesifikasi). Spesifikasi: [CSV2JSON](https://github.com/florinpop17/app-ideas/blob/master/Projects/1-Beginner/CSV2JSON-App.md).

Tanpa modul `csv`. Parser CSV ditulis sendiri dan menangani sel berkutip, koma dan baris baru di dalam kutip, kutip ganda `""`, serta akhir baris `\n` maupun `\r\n`.

## Menjalankan

```bash
python csv2json.py to-json data.csv                # CSV -> JSON ke layar
python csv2json.py to-json data.csv -o data.json   # simpan ke berkas
python csv2json.py to-json data.csv --types        # angka dan true/false menjadi tipe JSON
python csv2json.py to-csv data.json -o data.csv    # JSON -> CSV
```

Contoh: `nama,umur` / `Ani,20` menjadi `[{"nama": "Ani", "umur": "20"}]`, atau `"umur": 20` dengan `--types`.

## Tes

```bash
python -m unittest -v
```

## Aturan konversi

- Baris pertama adalah header. Nama kolom tidak boleh kosong atau ganda.
- Setiap baris data harus punya jumlah kolom yang sama dengan header; kalau tidak, pesan error menyebut nomor barisnya.
- Secara bawaan semua nilai tetap berupa teks supaya tidak ada yang berubah diam-diam (misalnya `007`). `--types` mengubah `true`/`false`, bilangan bulat, dan desimal.
- Baris kosong dilewati. Kutip yang dibuka tapi tidak ditutup ditolak.
- Tes bolak-balik memastikan JSON → CSV → JSON mengembalikan data awal, termasuk nilai berkoma, berkutip, dan berbaris baru.

## Pemetaan user stories

Kotak teks dan tombol di browser menjadi argumen terminal: masukan dari berkas atau stdin, keluaran ke layar atau berkas.

- [x] Memasukkan CSV, divalidasi, dan hasil JSON ditampilkan
- [x] Peringatan kalau CSV kosong atau tidak valid
- [x] Semua cerita JSON2CSV (perintah `to-csv`)
- [x] Bonus: buka berkas CSV/JSON dengan peringatan kalau tidak ditemukan
- [x] Bonus: simpan berkas CSV/JSON dengan peringatan kalau hasil kosong atau penyimpanan gagal
- Tombol "Clear" tidak relevan di terminal.

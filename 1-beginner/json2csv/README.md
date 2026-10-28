# JSON2CSV

Mengubah JSON (satu objek atau daftar objek datar) menjadi CSV. Spesifikasi: [JSON2CSV](https://github.com/florinpop17/app-ideas/blob/master/Projects/1-Beginner/JSON2CSV-App.md).

Tanpa modul `csv` atau pustaka konversi lain. Modul `json` hanya dipakai untuk membaca teks JSON (validasi); CSV ditulis sendiri.

## Menjalankan

```bash
python json2csv.py data.json               # cetak CSV ke layar
python json2csv.py data.json -o data.csv   # simpan ke berkas
type data.json | python json2csv.py        # baca dari stdin (Windows; di Linux/Mac: cat)
```

Contoh: `[{"nama": "Ani", "umur": 20}, {"nama": "Budi", "umur": 31}]` menjadi

```
nama,umur
Ani,20
Budi,31
```

## Tes

```bash
python -m unittest -v
```

## Aturan konversi

- Header adalah gabungan semua kunci, urut kemunculan pertama. Objek yang tidak punya suatu kunci dapat sel kosong.
- `null` menjadi sel kosong; `true`/`false` menjadi `true`/`false`.
- Nilai yang berisi koma, kutip, atau baris baru diberi tanda kutip, dan kutip di dalamnya digandakan (`""`).
- JSON bersarang (objek atau daftar di dalam objek) ditolak dengan pesan jelas.

## Pemetaan user stories

Kotak teks dan tombol di browser menjadi argumen terminal: input dari berkas atau stdin, keluaran ke layar atau berkas.

- [x] Memasukkan JSON, dikonversi, dan hasil CSV ditampilkan
- [x] Peringatan kalau JSON kosong atau tidak valid (menyebut baris dan kolom kesalahan)
- [x] Bonus: buka berkas JSON, dengan peringatan kalau berkas tidak ditemukan
- [x] Bonus: simpan CSV ke berkas, dengan peringatan kalau hasil kosong atau penyimpanan gagal
- [x] Bonus: CSV ke JSON, lihat [CSV2JSON](../csv2json)
- Tombol "Clear" tidak relevan di terminal, karena tidak ada kotak teks yang perlu dikosongkan.

# Notes App

Membuat, mengubah, menghapus, dan menyimpan catatan. Spesifikasi: [Notes App](https://github.com/florinpop17/app-ideas/blob/master/Projects/1-Beginner/Notes-App.md).

Catatan disimpan di `~/.app-ideas-python/notes.json` (ubah dengan `-f berkas.json`), jadi tetap ada saat program dijalankan lagi. Hanya pustaka bawaan Python.

## Menjalankan

```bash
python notes.py add "Belanja" -b "# Daftar\n\n- **telur**\n- susu"   # \n menjadi baris baru
python notes.py add "Ide"                  # tanpa -b: ketik isi, akhiri dengan baris berisi satu titik (.)
python notes.py list
python notes.py show 1                     # tampil sebagai teks
python notes.py show 1 --html -o belanja.html   # Markdown dikonversi ke halaman HTML
python notes.py edit 1 -t "Belanja Minggu Ini" -b "**Penting**: roti"
python notes.py delete 1
```

`add` dan `edit` juga bisa mengambil isi dari berkas: `--file catatan.md`.

## Tes

```bash
python -m unittest -v
```

## Markdown yang didukung

Judul `#` sampai `######`, paragraf, daftar `-`/`*`/`1.`, kutipan `>`, blok kode ` ``` `, garis `---`, serta `**tebal**`, `*miring*`/`_miring_`, `` `kode` ``, dan `[teks](url)`. Konverternya ditulis sendiri, tanpa pustaka.

Keamanan: semua HTML mentah di-escape lebih dulu (`<script>` menjadi teks biasa), isi blok kode dan `` `kode` `` tidak diformat ulang, dan tautan hanya diizinkan untuk `http(s)://`, `mailto:`, dan alamat relatif. `javascript:` atau `data:` dibuang dan tinggal teksnya saja. Keterbatasan: URL yang mengandung tanda kurung `)` tidak didukung, dan tidak ada tabel atau gambar.

## Soal penyimpanan

- Berkas ditulis lewat berkas sementara lalu diganti (`os.replace`), jadi kalau program berhenti di tengah menulis, catatan lama tidak rusak.
- Kalau `notes.json` rusak, program menolak membacanya dan menampilkan pesan, bukan menimpanya dengan daftar kosong.
- Nomor catatan tidak dipakai ulang setelah penghapusan.

## Pemetaan user stories

- [x] Membuat catatan (`add`)
- [x] Mengubah catatan (`edit`)
- [x] Menghapus catatan (`delete`)
- [x] Catatan tersimpan dan terbaca kembali di sesi berikutnya
- [x] Bonus: menulis dan mengubah catatan dalam Markdown; `show --html` mengonversinya ke HTML
- [x] Bonus: tanggal pembuatan (dan tanggal terakhir diubah) tampil di `list` dan `show`

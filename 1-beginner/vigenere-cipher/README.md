# Vigenere Cipher

Sandi klasik Vigenere, ditulis sendiri tanpa pustaka. Spesifikasi: [Vigenere Cipher](https://github.com/florinpop17/app-ideas/blob/master/Projects/1-Beginner/Vigenere-Cipher.md).

Tiap huruf digeser sebanyak nilai huruf kunci pada posisi yang sama (A=0 ... Z=25), dan kunci diulang. Contoh: `ATTACKATDAWN` dengan kunci `LEMON` menjadi `LXFOPVEFRNHR`.

## Menjalankan

```bash
python vigenere.py encrypt "Attack at dawn" LEMON     # Lxfopv ef rnhr
python vigenere.py decrypt "Lxfopv ef rnhr" LEMON     # Attack at dawn
python vigenere.py crack sandi.txt                    # coba patahkan sandi (teks Inggris)
python vigenere.py                                    # panel: encrypt, decrypt, compare
```

Aturan teks: huruf besar/kecil dipertahankan; karakter selain huruf A-Z (spasi, angka, tanda baca, huruf beraksen) tidak berubah dan **tidak memajukan kunci**. Kunci hanya boleh berisi huruf A-Z dan tidak membedakan huruf besar kecil.

## Tes

```bash
python -m unittest -v
```

Tes memakai contoh baku (`ATTACKATDAWN` + `LEMON`), bolak-balik untuk beberapa kunci (termasuk kunci yang lebih panjang dari teks), dan mematahkan sandi dari teks Inggris sungguhan.

## Pertanyaan refleksi dari spesifikasi

**Apakah Anda percaya mengenkripsi data keuangan dengan Vigenere?** Tidak. Vigenere dibuat pada abad ke-16 dan sudah bisa dipatahkan sejak abad ke-19. Kuncinya pendek dan berulang, jadi pola bahasa asli bocor lewat sandinya. Untuk data nyata pakai algoritma modern yang sudah teruji, seperti AES-GCM dari pustaka kriptografi terpercaya, dan jangan menulis kriptografi sendiri.

**Bagaimana mendeteksi bahwa pesan dienkripsi dengan Vigenere?** Dengan *index of coincidence* (IC): peluang dua huruf yang diambil acak dari teks adalah sama. Teks Inggris biasa punya IC sekitar 0.066, teks acak merata sekitar 0.038. Sandi substitusi sederhana (satu huruf kunci) mempertahankan IC bahasa asli, sedangkan Vigenere dengan kunci panjang menurunkannya mendekati acak. Fungsi `index_of_coincidence` ada di `vigenere.py`; pada teks uji: 0.0735 untuk teks asli, 0.0446 setelah dienkripsi dengan `LEMON`.

**Bagaimana mematahkannya?** Dua langkah, keduanya diimplementasi di `crack`:
1. **Tebak panjang kunci.** Untuk panjang `n` yang benar, huruf-huruf pada posisi `1, n+1, 2n+1, ...` memakai huruf kunci yang sama, jadi masing-masing "kolom" itu seperti sandi Caesar dan IC-nya kembali tinggi. Panjang yang IC kolomnya tinggi adalah kandidatnya (kelipatan panjang kunci juga tinggi, jadi diambil yang terkecil yang mendekati yang terbaik).
2. **Tebak tiap huruf kunci.** Coba 26 geseran untuk tiap kolom dan pilih yang frekuensi hurufnya paling mirip bahasa Inggris (uji chi-kuadrat).

Hasil nyata pada teks uji (734 huruf):

| Kunci asli | Panjang yang ditebak | Kunci yang ditemukan |
|---|---|---|
| `KEY` | 3 | `KEY` |
| `LEMON` | 5 | `LEMON` |
| `CRYPTO` | 6 | `CRYPTO` |
| `SECRETKEY` (9 huruf) | 6 (salah) | `DEESEE` (salah) |

Pemecah ini **gagal** untuk kunci 9 huruf pada teks sependek itu: tiap kolom hanya berisi sekitar 80 huruf, terlalu sedikit untuk statistik yang andal. Semakin panjang kunci, semakin banyak teks sandi yang dibutuhkan penyerang. Itu juga alasan kunci Vigenere sepanjang pesan (*one-time pad*) tidak bisa dipatahkan dengan cara ini, tetapi pemakaiannya tidak praktis. Pemecah ini juga hanya untuk teks bahasa Inggris, karena tabel frekuensinya bahasa Inggris.

## Pemetaan user stories

Jendela dan tombol di browser menjadi panel di terminal (`python vigenere.py` tanpa argumen).

- [x] Kolom pesan, kolom kunci, tombol Encrypt dan Decrypt, serta hasilnya
- [x] Decrypt nonaktif sampai pesan terenkripsi, lalu aktif setelah hasil enkripsi tampil
- [x] Decrypt menampilkan isi pesan asli di kolom hasil
- [x] Bonus: Compare membandingkan pesan asli dengan hasil dekripsi, dan melaporkan kalau berbeda (aktif setelah dekripsi)

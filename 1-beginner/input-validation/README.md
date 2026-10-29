# Input Validation (RegEx)

Validasi tiga isian formulir dengan ekspresi reguler. Spesifikasi: [Javascript Validation With Regex](https://github.com/florinpop17/app-ideas/blob/master/Projects/1-Beginner/Javascript-Validation-With-Regex.md), dikerjakan dengan modul `re` Python.

| Isian | Aturan |
|---|---|
| Password | tepat 5 huruf kapital, 6 simbol, dan 2 tanda hubung `-`, urutan bebas (13 karakter) |
| Username | hanya huruf, tanpa spasi |
| Email | alamat Gmail (`...@gmail.com`) |

## Menjalankan

```bash
python validation.py
```

```
Password: abc
Username: b udi
Email: b@yahoo.com
  [!] Password harus berisi tepat 5 huruf kapital, 6 simbol, dan 2 tanda hubung. Sekarang: 0 huruf kapital (harus 5); 0 simbol (harus 6); 0 tanda hubung (-) (harus 2); 3 karakter lain yang tidak boleh ada (huruf kecil, angka, atau spasi).
  [!] Username tidak boleh mengandung spasi.
  [!] Email harus alamat Gmail, berakhiran @gmail.com.
```

Isian yang salah diminta ulang. Password sengaja tidak disembunyikan saat diketik supaya aturan hitungannya mudah dicoba; hasil akhirnya disensor.

## Tes

```bash
python -m unittest -v
```

Tes mengacak urutan karakter password 200 kali, mencoba setiap simbol, dan semua posisi dua tanda hubung.

## Cara kerja regex password

Aturan "tepat N dari satu jenis, urutan bebas" tidak bisa ditulis sebagai satu pola berurutan, jadi dipakai **lookahead**: pemeriksaan yang tidak menghabiskan karakter, sehingga beberapa syarat diperiksa di posisi awal yang sama.

```
^
(?=(?:[^A-Z]*[A-Z]){5}[^A-Z]*$)    tepat 5 huruf kapital
(?=(?:[^SIM]*[SIM]){6}[^SIM]*$)    tepat 6 simbol
(?=(?:[^-]*-){2}[^-]*$)            tepat 2 tanda hubung
[A-Z SIM -]{13}$                   hanya ketiga jenis itu, total 13 karakter
```

(`SIM` mewakili himpunan simbol di `validation.py`.) Pola `(?:[^X]*X){5}[^X]*$` berarti "ada tepat 5 karakter X".

## Tafsiran spesifikasi

Kalimat "lima huruf kapital, enam simbol, dan dua tanda hubung dalam urutan apa pun" bisa dibaca beberapa cara. Pilihan saya:

- Totalnya 13 karakter, tanpa huruf kecil, angka, atau spasi.
- Tanda hubung dihitung terpisah, tidak termasuk 6 simbol (karena spesifikasi menyebutnya sendiri).
- Simbol: ``! @ # $ % ^ & * ( ) _ + = [ ] { } ; : ' " , . < > / ? \ | ` ~``

Username memakai `[^\W\d_]+` (huruf Unicode, jadi "Zoë" boleh). Email: bagian sebelum `@` hanya huruf, angka, dan `. _ % + -`, tidak diawali atau diakhiri titik dan tidak berisi dua titik berurutan; domainnya tidak membedakan huruf besar kecil.

## Pemetaan user stories

- [x] Pengguna diberi tahu tiap isian yang tidak valid lewat pesan, termasuk rincian hitungan untuk password
- [x] "Tombol submit" (`submit()`) tidak pernah berjalan sebelum semua isian valid, dan melaporkan semua kesalahan sekaligus, bukan satu per satu

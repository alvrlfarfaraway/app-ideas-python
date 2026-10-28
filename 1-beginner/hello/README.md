# Hello

Panel login tiruan yang menyapa dalam bahasa asli negara pengguna. Spesifikasi: [Hello App](https://github.com/florinpop17/app-ideas/blob/master/Projects/1-Beginner/Hello-App.md).

Alurnya:

1. [IP-API](http://ip-api.com/docs/api:json) menebak lokasi dari IP pengguna.
2. [HelloSalut](https://fourtonfish.com/hellosalut/hello/) (Fourtonfish) mengembalikan salam untuk IP itu.
3. Salam didekode dari entitas HTML (`Gr&uuml;&szlig; Gott` menjadi `Grüß Gott`) dengan `html.unescape`.

Hanya memakai pustaka bawaan Python.

## Menjalankan

```bash
python hello.py              # panel interaktif: login, logout, quit
python hello.py --lang id    # paksa kode bahasa, misalnya id, de, fr (bonus)
```

Contoh sesi (dijalankan dari Indonesia):

```
> login
User Name: budi
Password : ********
Halo budi you have successfully logged in!
  IP            114.10.10.9
  Kota          Semarang
  Negara        Indonesia
  Zona waktu    Asia/Jakarta
> logout
Have a great day budi!
```

## Tes

```bash
python -m unittest -v
```

Tes memakai jaringan tiruan, jadi tidak butuh internet dan bisa menguji layanan yang mati.

## Pemetaan user stories

- [x] Panel login dengan User Name, Password, dan perintah `login`/`logout`
- [x] Password ditampilkan sebagai `*` per karakter di Windows. Di OS lain memakai `getpass`, yang tidak menampilkan apa pun (konvensi terminal Unix).
- [x] Kolom kosong menghasilkan pesan dan penanda `[!]` merah pada kolom yang bermasalah (padanan border merah)
- [x] Pesan `<salam> <user> you have successfully logged in!` dan `Have a great day <user>!`
- [x] Logout menghapus status login dan data lokasi
- [x] Bonus: `--lang` menggantikan hasil geolokasi
- [x] Bonus: setelah login tampil IP, kota, wilayah, negara, kode pos, bujur, lintang, dan zona waktu

## Catatan

- Login ini hanya tiruan: tidak ada pengecekan password dan tidak ada yang disimpan.
- Versi gratis IP-API hanya melayani HTTP (tanpa enkripsi) dan membatasi permintaan per menit. Itu cukup untuk latihan, tapi jangan dipakai untuk data sensitif.
- Kalau geolokasi atau layanan salam gagal, login tetap berhasil dengan salam "Hello" dan peringatan, supaya satu layanan yang mati tidak mengunci pengguna.

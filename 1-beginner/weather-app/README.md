# Weather App

Suhu, kondisi cuaca, siang atau malam, dan ikon cuaca untuk sebuah kota. Spesifikasi: [Weather App](https://github.com/florinpop17/app-ideas/blob/master/Projects/1-Beginner/Weather-App.md).

Spesifikasi menyebut AccuWeather, yang butuh akun dan kunci API. Di sini dipakai **[Open-Meteo](https://open-meteo.com/)**: gratis, tanpa kunci, dengan geokoding (mencari kota) dan cuaca saat ini. Hanya pustaka bawaan Python.

## Menjalankan

```bash
python weather.py Semarang            # cuaca kota itu; kotanya diingat untuk berikutnya
python weather.py                     # memakai kota terakhir
python weather.py Kota Semarang       # nama beberapa kata boleh tanpa tanda kutip
python weather.py Semarang --list     # daftar kota yang namanya cocok
python weather.py Semarang --pick 2   # pilih hasil kedua
```

Contoh keluaran nyata (29 Oktober 2026, pagi):

```
Kota Semarang, Jawa Tengah, Indonesia
🌤️  Hampir cerah  ·  Siang ☀️
Suhu        : 28.3 °C (terasa 33.3 °C)
Kelembapan  : 73%
Angin       : 3.0 km/jam
Waktu data  : 2026-10-29 07:15 (waktu setempat)
```

Ikon memakai emoji; di konsol Windows lama yang tidak mendukung UTF-8 emoji bisa tampil sebagai `?`, tetapi teksnya tetap terbaca. Windows Terminal dan VS Code menampilkannya dengan benar.

## Tes

```bash
python -m unittest -v
```

Tes memakai jawaban API tiruan, jadi tidak butuh internet. Selain jalur normal, tes mencakup kota yang tidak ada, nama berisi karakter khusus (di-URL-encode), data cuaca tidak lengkap, jaringan mati, dan berkas kota-terakhir yang rusak. Satu tes memastikan semua 28 kode cuaca WMO yang dipakai Open-Meteo punya deskripsi dan ikon.

## Cara kerja

1. **Geokoding:** nama kota dikirim ke API pencarian; hasil pertama dipakai. Karena banyak kota bernama sama, program memberi tahu kalau ada lebih dari satu yang cocok; `--list` dan `--pick N` untuk memilih.
2. **Cuaca saat ini:** koordinat kota dikirim ke API prakiraan, yang menjawab suhu, suhu terasa, kelembapan, kecepatan angin, kode cuaca WMO, dan penanda siang atau malam (`is_day`) menurut zona waktu kota itu.
3. **Ikon:** kode WMO diterjemahkan ke deskripsi bahasa Indonesia dan ikon; langit cerah memakai ☀️ di siang hari dan 🌙 di malam hari. Kode yang tidak dikenal tetap ditampilkan dengan pesan, tidak membuat program gagal.

## Pemetaan user stories

- [x] Memasukkan nama kota (argumen, atau ditanya kalau belum ada kota tersimpan)
- [x] Menekan Enter menampilkan suhu, kondisi cuaca, siang atau malam, dan ikon cuaca
- [x] Bonus: kota terakhir tersimpan di `~/.app-ideas-python/weather-city.json` dan dipakai lagi saat program dijalankan tanpa argumen (pengganti `localStorage` di browser). Kota yang gagal dicari tidak disimpan.

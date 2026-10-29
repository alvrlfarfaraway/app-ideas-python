# GitHub Status

Menampilkan status komponen GitHub (Git Operations, API Requests, Issues, Pull Requests, Actions, Pages, dst.) langsung dari [githubstatus.com](https://www.githubstatus.com/). Spesifikasi: [GitHub Status](https://github.com/florinpop17/app-ideas/blob/master/Projects/1-Beginner/GitHub-Status-App.md).

Spesifikasi menyebut paket NPM `Request` untuk "scraping". Di sini saya memakai API JSON resmi situs itu (`/api/v2/components.json`) lewat `urllib` bawaan Python, jadi datanya terstruktur dan tidak perlu menguraikan HTML. Tidak butuh paket tambahan.

## Menjalankan

```bash
python github_status.py        # ambil dan tampilkan sekali
python github_status.py -i     # interaktif: Enter = 'Get Status' lagi, q = keluar
python github_status.py --no-color
```

Contoh keluaran:

```
✔ Git Operations  Operational
▲ API Requests    Degraded performance
✔ Issues          Operational

1 komponen bermasalah.
```

## Tes

```bash
python -m unittest -v
```

Tes memakai data tiruan dan "opener" tiruan, jadi tidak butuh internet dan bisa menguji keadaan yang jarang terjadi (komponen mati, server menjawab 503, jawaban bukan JSON).

## Pemetaan user stories

- [x] Daftar status tiap komponen GitHub (entri grup dan baris tautan "Visit ..." dilewati karena bukan layanan)
- [x] Ambil status terbaru: menjalankan ulang program, atau tekan Enter di mode `-i` (padanan tombol "Get Status")
- [x] Bonus: komponen yang bukan Operational mencolok dengan simbol ▲ dan warna (merah untuk outage, kuning untuk degradasi/pemeliharaan), plus ringkasan jumlahnya
- Jaringan mati, server error, atau data tidak dikenali menghasilkan pesan jelas, bukan traceback.

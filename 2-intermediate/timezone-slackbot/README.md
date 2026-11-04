# Timezone Slackbot

Slash command Slack `/tz @rina @budi …` yang menampilkan jam dan zona waktu setiap anggota tim dalam tabel dengan warna baris selang-seling. Spesifikasi: [Timezone Slackbot](https://github.com/florinpop17/app-ideas/blob/master/Projects/2-Intermediate/Timezone-Slackbot.md).

Hanya pustaka bawaan Python (`http.server`, `hmac`, `zoneinfo`). Di Windows, `zoneinfo` butuh paket `tzdata` (`pip install tzdata`).

## Mencoba tanpa Slack

Data tim contoh di [`contoh/tim.json`](contoh/tim.json) (fiktif) berbentuk sama dengan jawaban API Slack `users.list`:

```
$ python tz_bot.py simulate rina budi @wayan yohanes priya sam lena kenji tono
Nama     Jam    Zona   Lokasi
Sam      10:18  EST    America/New_York (UTC-05:00)
Lena     16:18  CET    Europe/Berlin (UTC+01:00)
Priya    20:48  IST    Asia/Kolkata (UTC+05:30)
Rina     22:18  WIB    Asia/Jakarta (UTC+07:00)
Budi     23:18  WITA   Asia/Makassar (UTC+08:00)
Wayan    23:18  WITA   Asia/Makassar (UTC+08:00)
Kenji    00:18  JST    Asia/Tokyo (UTC+09:00)
Yohanes  00:18  WIT    Asia/Jayapura (UTC+09:00)
Tidak ditemukan: tono
```

`python tz_bot.py simulate rina sam --json` menampilkan balasan JSON yang akan dikirim ke Slack.

## Balasan di Slack

Slack tidak punya tabel dengan warna latar per baris. Karena itu setiap baris dikirim sebagai satu *attachment*, dengan warna bilah kiri yang bergantian (`#2e78c7`, `#9cc3ef`). Nama yang tidak ditemukan muncul sebagai baris merah di akhir.

```json
{"response_type": "in_channel", "text": "Zona waktu tim:", "attachments": [
  {"color": "#2e78c7", "text": "*Sam*  10:17 *EST*  ·  America/New_York (UTC-05:00)  ·  Rab 4 Nov"},
  {"color": "#9cc3ef", "text": "*Rina*  22:17 *WIB*  ·  Asia/Jakarta (UTC+07:00)  ·  Rab 4 Nov"}]}
```

- **Urutan baris:** dari zona paling barat ke paling timur.
- **Singkatan zona** (bonus): diambil dari basis data zona waktu IANA, misalnya WIB, WITA, WIT, IST, EST, dan CET. Singkatannya otomatis berganti saat musim panas (EDT, CEST).
- **Tanggal:** ikut ditampilkan, karena di Tokyo sudah besok.

## Memasang di Slack

1. **Buat app:** di <https://api.slack.com/apps>, buat app baru, lalu di **OAuth & Permissions** tambahkan scope `users:read` dan `commands`. Pasang app-nya ke workspace, lalu salin **Bot User OAuth Token** (`xoxb-…`).
2. **Ambil signing secret:** salin dari **Basic Information** > **Signing Secret**.
3. **Jalankan server:**

   ```bash
   SLACK_SIGNING_SECRET=... SLACK_BOT_TOKEN=xoxb-... python tz_bot.py serve --port 3000
   ```

   Di PowerShell: `$env:SLACK_SIGNING_SECRET="..."; $env:SLACK_BOT_TOKEN="xoxb-..."; python tz_bot.py serve`.
4. **Buka ke internet:** server harus bisa diakses dari internet, misalnya dengan `ngrok http 3000`.
5. **Daftarkan perintah:** di **Slash Commands**, buat perintah `/tz` dengan Request URL `https://<alamat-ngrok>/slack/tz`, lalu nyalakan **Escape channels, users, and links**, supaya mention dikirim sebagai `<@U123|rina>`.

## Keamanan

- **Tanda tangan:** setiap permintaan diperiksa tanda tangannya (`X-Slack-Signature`, HMAC-SHA256 atas `v0:timestamp:isi`) dengan perbandingan waktu-konstan. Tes memakai contoh resmi dari dokumentasi Slack ("Verifying requests from Slack") dan hasilnya cocok.
- **Kedaluwarsa:** permintaan yang lebih tua dari 5 menit ditolak, supaya tidak bisa diputar ulang.
- **Rahasia:** token dan signing secret hanya dibaca dari variabel lingkungan, tidak pernah ditulis di kode.

## Yang sudah dan belum diuji

- **Sudah:** server sungguhan (di port acak) menerima permintaan bertanda tangan, menolak tanda tangan yang salah, memanggil API Slack tiruan (`users.info`, `users.list`), dan membalas JSON di atas.
- **Belum:** bot ini **belum dicoba di workspace Slack sungguhan**, karena perlu membuat app Slack dengan akunmu sendiri.

## Tes

```bash
python -m unittest -v
```

## Pemetaan user stories

- [x] `/tz <nama> <nama> …` menampilkan tabel zona waktu setiap pengguna
- [x] Baris tabel berwarna selang-seling supaya mudah dibaca
- [x] Bonus: singkatan zona waktu tampil di samping nama (misalnya WIB atau IST)

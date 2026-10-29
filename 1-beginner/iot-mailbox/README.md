# IOT Mailbox Simulator

Simulasi kotak surat pintar yang mengabari lewat **callback** saat pintunya dibuka. Spesifikasi: [IOT Mailbox Simulator](https://github.com/florinpop17/app-ideas/blob/master/Projects/1-Beginner/IOT-Mailbox-App.md).

`IOTMailbox` mengukur tingkat cahaya di dalam kotak tiap interval (positif = pintu terbuka, negatif = tertutup) dan memanggil fungsi callback yang diberikan. `Panel` adalah pemakainya: ia mencatat log dan memberi notifikasi.

## Menjalankan

```bash
python iot_mailbox.py                  # panel interaktif: start, stop, reset, log, quit
python iot_mailbox.py --interval 0.3   # interval pemantauan (detik)
python iot_mailbox.py --demo 3         # nyalakan 3 detik lalu berhenti, tanpa input
python iot_mailbox.py --stuck-open     # pintu dibuka lalu tidak pernah ditutup (uji peringatan)
```

Contoh keluaran `--demo 2 --interval 0.4`:

```
  log: Pemantauan dimulai (interval 0.4 detik).
  log: Tingkat cahaya +0.61: pintu TERBUKA.
NOTIFIKASI: Pintu kotak surat dibuka! Mungkin ada surat.
  log: Tingkat cahaya -0.79: pintu tertutup.
  log: Pemantauan dihentikan.
```

## Tes

```bash
python -m unittest -v
```

Selain tes logika dengan angka acak yang dikunci, ada tes dengan thread sungguhan (mulai, berhenti, tidak ada thread kedua kalau `start` dipanggil dua kali, dan tidak ada callback lagi setelah berhenti).

## Perbedaan dari kode JavaScript di spesifikasi

Kelas bawaannya tidak diterjemahkan mentah karena ada dua masalah:

1. `this.signalCallback(this.lightLevel)` mengirim properti yang tidak pernah dibuat, jadi callback selalu menerima `undefined`. Yang seharusnya dikirim adalah variabel lokal `lightLevel`.
2. Tanda diputuskan dengan `lastLightLevel >= 0`. Karena `Math.random().toFixed(2)` bisa menghasilkan `0.00`, dan `-0 >= 0` juga benar, pintu bisa dua kali "tertutup" berturut-turut atau berada di nilai 0 yang tidak jelas buka atau tutup. Di sini status bergantian secara eksplisit dan besar cahaya minimal 0.01.

`setInterval` diganti thread yang menunggu dengan `Event.wait(interval)`, sehingga bisa dihentikan seketika.

## Pemetaan user stories

Panel kontrol di browser menjadi perintah terminal.

- [x] Tombol Start Monitoring, Stop Monitoring, dan Reset
- [x] Panel notifikasi (baris `NOTIFIKASI:`) dan panel log (baris `log:`, riwayat lewat perintah `log`)
- [x] Log saat pemantauan mulai dan berhenti
- [x] Log tiap tingkat cahaya, dengan angka dan status pintu terbuka/tertutup
- [x] Notifikasi saat pintu dibuka
- [x] Bonus: Start nonaktif selagi memantau, Stop nonaktif selagi tidak
- [x] Bonus: interval bisa diatur (`--interval`)
- [x] Bonus: notifikasi kalau pintu dibiarkan terbuka (3 pembacaan berturut-turut). Simulator bawaan selalu bergantian sehingga tidak pernah memicunya; pakai `--stuck-open` untuk mencobanya.
- [x] Bonus: bunyi bel terminal saat pintu dibuka

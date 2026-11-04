# Game Suggestion

Buat polling, minta teman mengusulkan game, lalu lihat 5 atau 10 game dengan suara terbanyak. Spesifikasi: [Game Suggestion App](https://github.com/florinpop17/app-ideas/blob/master/Projects/2-Intermediate/Game-Suggestion-App.md).

Game dicari lewat API toko Steam, yang gratis dan tanpa kunci. IGDB yang disarankan spesifikasi butuh akun Twitch dan token OAuth (tanpa token, API-nya menjawab 401). Polling dan suara disimpan di SQLite (`~/.app-ideas-python/game-polls.db`, bisa diganti dengan `--db`). Hanya pustaka bawaan Python.

## Menjalankan

```bash
python game_poll.py create "Main bareng Jumat" --owner budi
python game_poll.py create "Malam RPG" --owner budi --genre RPG    # hanya game bergenre RPG
python game_poll.py search "hollow knight"
python game_poll.py vote 1 "hollow knight" --voter sari           # hasil pencarian pertama
python game_poll.py vote 1 "hollow knight" --pick 2 --voter sari  # hasil pencarian kedua
python game_poll.py vote 1 --id 413150 --voter sari               # langsung dengan id Steam
python game_poll.py vote 1 --voter sari                           # cari interaktif, lalu pilih nomor
python game_poll.py results 1 --top 5
python game_poll.py polls --owner budi                            # polling lama milik budi
```

Keluaran asli dari satu sesi (data dari Steam, 4 November 2026):

```
$ python game_poll.py search "hollow knight"
  1. Hollow Knight  (id 367520)
  2. Hollow Knight: Silksong  (id 1030300)
  3. Hollow Knight - Official Soundtrack  (id 598190)
  4. Hollow Knight - Gods & Nightmares  (id 916000)
  5. Hollow Knight: Silksong - Official Soundtrack  (id 3928720)

$ python game_poll.py vote 1 "hollow knight" --voter sari
Suara sari untuk 'Hollow Knight' dicatat di polling #1.

$ python game_poll.py vote 1 "hollow knight" --voter sari
Error: sari sudah memilih 'Hollow Knight' di polling ini.

$ python game_poll.py vote 1 "hollow knight" --pick 3 --voter rina
Error: 'Hollow Knight - Official Soundtrack' bukan game (jenis Steam: music). Pilih game, bukan DLC atau soundtrack.

$ python game_poll.py vote 2 "hollow knight" --voter sari
Error: Polling ini hanya untuk genre RPG. 'Hollow Knight' bergenre Action, Adventure, Indie.

$ python game_poll.py vote 2 "elden ring" --voter sari
Suara sari untuk 'ELDEN RING' dicatat di polling #2.

$ python game_poll.py results 1 --top 5
#1 Main bareng Jumat (oleh budi)

 1. Hollow Knight   #################### 3
 2. Stardew Valley  ############# 2
 3. Terraria        ####### 1

$ python game_poll.py polls --owner budi
#2   Malam RPG [genre RPG] | oleh budi | 1 suara | 2026-11-04
#1   Main bareng Jumat | oleh budi | 6 suara | 2026-11-04
```

## Aturan

- **Satu suara per game:** setiap pemilih bisa mengusulkan banyak game, tetapi hanya satu suara untuk setiap game di satu polling (`UNIQUE (poll_id, app_id, voter)`).
- **Hanya game:** pencarian Steam juga menampilkan soundtrack dan DLC. Saat memilih, jenis aplikasinya dicek lewat `appdetails`, dan yang bukan `game` ditolak.
- **Batas genre:** memakai genre Steam (Action, RPG, Strategy, Indie, dan lainnya), tanpa membedakan huruf besar kecil.
- **Peringkat:** diurutkan dari suara terbanyak. Kalau jumlah suaranya sama, game yang lebih dulu mendapat suara berada di atas.
- **Data game:** nama dan genre disimpan dan diperbarui lewat upsert (`ON CONFLICT DO UPDATE`), bukan `INSERT OR REPLACE`, supaya suara yang sudah ada tidak ikut terhapus.

## Soal "login"

Tidak ada login sungguhan. Nama dipakai sebagai identitas: `--owner` untuk pembuat polling dan `--voter` untuk pemilih. `polls --owner nama` menampilkan polling lama milik orang itu. Untuk dipakai banyak orang lewat internet, aplikasi ini perlu server dan autentikasi.

## Tes

```bash
python -m unittest -v
```

Tes memakai jawaban Steam tiruan dan database SQLite di memori.

## Pemetaan user stories

- [x] Membuat polling
- [x] Memilih di polling dengan mengusulkan game (dicari dari database game)
- [x] Hasil polling sebagai daftar 10 atau 5 game dengan suara terbanyak
- [x] Bonus: pembuat polling bisa membatasi usulan ke satu genre
- [ ] Bonus: login dan melihat polling lama (hanya berdasarkan nama, tanpa login sungguhan; lihat di atas)

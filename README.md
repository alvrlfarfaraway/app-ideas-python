# App Ideas (Python)

Latihan dari daftar [app-ideas](https://github.com/florinpop17/app-ideas) karya Florin Pop, dikerjakan dengan **Python**. Dimulai dari Tier 1 (Beginner), lalu Intermediate dan Advanced.

Project logika murni berupa skrip Python dengan tes `unittest`. Project yang dekat dengan analisis data berupa notebook Jupyter. Project yang memang visual (CSS, DOM, keyboard di browser) tetap HTML/CSS/JS dan dikerjakan di [app-ideas-projects](https://github.com/alvrlfarfaraway/app-ideas-projects).

## Kebutuhan

Python 3.12. Skrip hanya memakai pustaka bawaan, kecuali yang tertulis di README project (misalnya `requests`, `pillow`). Notebook butuh `notebook`, `pandas`, `numpy`, dan `matplotlib`.

## Struktur

`1-beginner/<project>/` berisi kode, `test_*.py`, dan `README.md` tiap project. Jalankan tes dari dalam foldernya:

```bash
cd 1-beginner/bin2dec
python -m unittest -v
```

## Progress

### Tier 1: Beginner (Python): 15/26

- [x] [Bin2Dec](1-beginner/bin2dec) — Binary-to-Decimal number converter
- [x] [Countdown Timer](1-beginner/countdown-timer) — Event Countdown timer
- [x] [CSV2JSON App](1-beginner/csv2json) — CSV to JSON converter
- [x] [Dollars to Cents](1-beginner/dollars-to-cents) — Convert dollars to cents
- [x] [First DB App](1-beginner/first-db-app) — Your first Database app!
- [x] [Flip Image](1-beginner/flip-image) — Change the orientation of images across two axes
- [x] [GitHub Status](1-beginner/github-status) — Display Current GitHub Status
- [x] [Hello](1-beginner/hello) — User native language greeting
- [x] [IOT Mailbox Simulator](1-beginner/iot-mailbox) — Use callbacks to check your snail mail
- [x] [Input Validation](1-beginner/input-validation) — Validate inputs entered by a user using RegEx
- [x] [JSON2CSV App](1-beginner/json2csv) — JSON to CSV converter
- [x] [Lorem Ipsum Generator](1-beginner/lorem-ipsum) — Generate lorem ipsum placeholder text
- [x] [Notes App](1-beginner/notes-app) — Create an online note pad
- [x] [Pearson Regression](1-beginner/pearson-regression) — Correlation coefficient for two sets of data (notebook)
- [x] [Pomodoro Clock](1-beginner/pomodoro) — Task timer to aid personal productivity
- [ ] Quiz App — Test your knowledge by answering questions
- [ ] Recipe App — Recipe
- [ ] Random Meal Generator — Generate random meals
- [ ] Random Number Generator — Generate random number between range
- [ ] Roman to Decimal Converter — Convert Roman to Decimal numbers
- [ ] Stopwatch App — Count time spent on activities
- [ ] TrueOrFalse — Identify the result of a conditional comparison
- [ ] Vigenere Cipher — Encrypt text using the Vigenere Cypher
- [ ] Wind Chill — Calculate the windchill factor from an actual temperature
- [ ] Word Frequency — Calculate word frequency in a block of text (notebook)
- [ ] Weather App — Get the temperature, weather condition of a city

### Tier 1 yang tetap HTML/CSS/JS (9)

Dikerjakan di [app-ideas-projects](https://github.com/alvrlfarfaraway/app-ideas-projects): Border Radius Previewer, Calculator, Christmas Lights, Cause Effect App, Color Cycle (sudah selesai di sana), serta Dynamic CSS Variables, Key Value, Product Landing Page, dan Slider Design (belum, karena isinya CSS dan event browser).

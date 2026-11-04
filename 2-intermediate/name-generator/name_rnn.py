"""Pembuat nama dengan GRU (Gated Recurrent Unit) tingkat karakter, ditulis dengan numpy saja.

Model membaca nama huruf demi huruf dan belajar peluang huruf berikutnya.
Untuk membuat nama baru, model diberi 2-3 huruf awal, lalu huruf berikutnya
diambil acak sesuai peluang itu sampai model memilih "akhir nama".

Persamaan GRU untuk setiap huruf x dan keadaan tersembunyi h:
    z  = sigmoid(Ez[x] + h Uz + bz)          gerbang pembaruan
    r  = sigmoid(Er[x] + h Ur + br)          gerbang reset
    n  = tanh(En[x] + (r * h) Un + bn)       kandidat keadaan baru
    h' = (1 - z) * n + z * h
    p  = softmax(h' Wy + by)                 peluang huruf berikutnya

Gradien dihitung sendiri (backpropagation through time) dan diperiksa dengan
gradien numerik di tes. Optimasi memakai Adam.

Jalankan:
    python name_rnn.py --prefix ar -n 5
    python name_rnn.py --prefix sri --temperature 0.6 --baru
    python name_rnn.py --train --steps 3000      # latih ulang dan simpan model
"""

import argparse
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data", "nama-indonesia.txt")
MODEL = os.path.join(HERE, "model", "gru-nama.npz")
END = "."  # penanda awal sekaligus akhir nama
PARAMS = ("Ez", "Er", "En", "Uz", "Ur", "Un", "bz", "br", "bn", "Wy", "by")
MAX_LEN = 20


def sigmoid(x):
    return 1.0 / (1.0 + np.exp(-x))


def load_names(path=DATA):
    with open(path, encoding="utf-8") as handle:
        return [line.strip().lower() for line in handle if line.strip()]


class Vocab:
    def __init__(self, chars):
        self.chars = [END] + sorted(set(chars) - {END})
        self.index = {ch: i for i, ch in enumerate(self.chars)}

    @classmethod
    def from_names(cls, names):
        return cls("".join(names))

    def encode(self, text):
        unknown = sorted(set(text) - set(self.index))
        if unknown:
            raise ValueError(f"Huruf {', '.join(repr(c) for c in unknown)} tidak dikenal model.")
        return [self.index[ch] for ch in text]

    def __len__(self):
        return len(self.chars)


def make_batch(names, vocab):
    """Input, target, dan masker (T, B). Input: '.' + nama; target: nama + '.'."""
    longest = max(len(n) for n in names) + 1
    x = np.zeros((longest, len(names)), dtype=np.int64)
    y = np.zeros((longest, len(names)), dtype=np.int64)
    mask = np.zeros((longest, len(names)))
    for b, name in enumerate(names):
        codes = vocab.encode(name)
        seq_in, seq_out = [0] + codes, codes + [0]
        x[:len(seq_in), b] = seq_in
        y[:len(seq_out), b] = seq_out
        mask[:len(seq_out), b] = 1.0
    return x, y, mask


class GRU:
    def __init__(self, vocab_size, hidden=64, seed=0):
        rng = np.random.default_rng(seed)
        V, H = vocab_size, hidden
        scale_in, scale_h = 0.1, 1.0 / np.sqrt(H)
        self.p = {
            "Ez": rng.normal(0, scale_in, (V, H)), "Er": rng.normal(0, scale_in, (V, H)),
            "En": rng.normal(0, scale_in, (V, H)),
            "Uz": rng.normal(0, scale_h, (H, H)), "Ur": rng.normal(0, scale_h, (H, H)),
            "Un": rng.normal(0, scale_h, (H, H)),
            "bz": np.zeros(H), "br": np.zeros(H), "bn": np.zeros(H),
            "Wy": rng.normal(0, scale_h, (H, V)), "by": np.zeros(V),
        }
        self.adam_m = {k: np.zeros_like(v) for k, v in self.p.items()}
        self.adam_v = {k: np.zeros_like(v) for k, v in self.p.items()}
        self.adam_t = 0

    @property
    def hidden(self):
        return self.p["Uz"].shape[0]

    def step(self, x, h):
        """Satu langkah GRU untuk batch indeks huruf x dan keadaan h."""
        p = self.p
        z = sigmoid(p["Ez"][x] + h @ p["Uz"] + p["bz"])
        r = sigmoid(p["Er"][x] + h @ p["Ur"] + p["br"])
        n = np.tanh(p["En"][x] + (r * h) @ p["Un"] + p["bn"])
        h_new = (1 - z) * n + z * h
        return h_new, (z, r, n)

    def loss_and_grads(self, x, y, mask):
        """Cross-entropy rata-rata per huruf, beserta gradien semua parameter."""
        p = self.p
        T, B = x.shape
        H = self.hidden
        total = mask.sum()
        h = np.zeros((B, H))
        cache = []
        loss = 0.0
        for t in range(T):
            h_prev = h
            h, (z, r, n) = self.step(x[t], h_prev)
            logits = h @ p["Wy"] + p["by"]
            logits -= logits.max(axis=1, keepdims=True)
            probs = np.exp(logits)
            probs /= probs.sum(axis=1, keepdims=True)
            loss -= (np.log(probs[np.arange(B), y[t]] + 1e-12) * mask[t]).sum()
            cache.append((h_prev, h, z, r, n, probs))
        grads = {k: np.zeros_like(v) for k, v in p.items()}
        dh_next = np.zeros((B, H))
        for t in reversed(range(T)):
            h_prev, h, z, r, n, probs = cache[t]
            dlogits = probs.copy()
            dlogits[np.arange(B), y[t]] -= 1
            dlogits *= (mask[t] / total)[:, None]
            grads["Wy"] += h.T @ dlogits
            grads["by"] += dlogits.sum(axis=0)
            dh = dlogits @ p["Wy"].T + dh_next
            dn = dh * (1 - z)
            dz = dh * (h_prev - n)
            dh_prev = dh * z
            dan = dn * (1 - n ** 2)
            np.add.at(grads["En"], x[t], dan)
            grads["bn"] += dan.sum(axis=0)
            grads["Un"] += (r * h_prev).T @ dan
            drh = dan @ p["Un"].T
            dr = drh * h_prev
            dh_prev += drh * r
            dar = dr * r * (1 - r)
            np.add.at(grads["Er"], x[t], dar)
            grads["br"] += dar.sum(axis=0)
            grads["Ur"] += h_prev.T @ dar
            dh_prev += dar @ p["Ur"].T
            daz = dz * z * (1 - z)
            np.add.at(grads["Ez"], x[t], daz)
            grads["bz"] += daz.sum(axis=0)
            grads["Uz"] += h_prev.T @ daz
            dh_prev += daz @ p["Uz"].T
            dh_next = dh_prev
        return loss / total, grads

    def adam(self, grads, lr=0.01, beta1=0.9, beta2=0.999, clip=5.0):
        norm = np.sqrt(sum((g ** 2).sum() for g in grads.values()))
        if norm > clip:  # potong gradien supaya pelatihan tidak meledak
            grads = {k: g * (clip / norm) for k, g in grads.items()}
        self.adam_t += 1
        for k in self.p:
            self.adam_m[k] = beta1 * self.adam_m[k] + (1 - beta1) * grads[k]
            self.adam_v[k] = beta2 * self.adam_v[k] + (1 - beta2) * grads[k] ** 2
            m_hat = self.adam_m[k] / (1 - beta1 ** self.adam_t)
            v_hat = self.adam_v[k] / (1 - beta2 ** self.adam_t)
            self.p[k] -= lr * m_hat / (np.sqrt(v_hat) + 1e-8)
        return norm


def split_names(names, valid_fraction=0.15, seed=42):
    """Pisahkan data latih dan validasi secara acak (tetap sama untuk seed yang sama)."""
    order = np.random.default_rng(seed).permutation(len(names))
    cut = int(round(len(names) * (1 - valid_fraction)))
    return [names[i] for i in order[:cut]], [names[i] for i in order[cut:]]


def train(names, hidden=48, steps=3000, lr=0.003, weight_decay=3e-3, batch=64, seed=0, valid_fraction=0.15,
          eval_every=100, callback=None):
    """Latih GRU dengan batch acak, weight decay, dan early stopping.

    Sebagian nama disisihkan sebagai data validasi. Setiap `eval_every` langkah, loss
    validasi diukur, dan parameter dengan loss validasi terendah yang disimpan. Data
    nama kecil, jadi tanpa ini model cepat menghafal dan berhenti membuat nama baru.
    Mengembalikan (model, vocab, riwayat) dengan riwayat berisi (langkah, loss latih, loss validasi).
    """
    vocab = Vocab.from_names(names)
    train_names, valid_names = split_names(names, valid_fraction) if valid_fraction else (names, [])
    model = GRU(len(vocab), hidden, seed)
    rng = np.random.default_rng(seed)
    history = []
    best = (np.inf, None)
    recent = []
    for step in range(1, steps + 1):
        chosen = [train_names[i] for i in rng.choice(len(train_names), size=min(batch, len(train_names)),
                                                     replace=False)]
        loss, grads = model.loss_and_grads(*make_batch(chosen, vocab))
        for key in grads:  # weight decay untuk matriks bobot (bukan bias)
            if key[0] in "EUW":
                grads[key] = grads[key] + weight_decay * model.p[key]
        model.adam(grads, lr)
        recent.append(loss)
        if step % eval_every == 0:
            valid = full_loss(model, vocab, valid_names) if valid_names else float(np.mean(recent))
            history.append((step, float(np.mean(recent)), float(valid)))
            recent = []
            if valid < best[0]:
                best = (valid, {k: v.copy() for k, v in model.p.items()}, step)
            if callback:
                callback(*history[-1])
    if best[1] is not None:
        model.p = best[1]
        model.best_step = best[2]
    return model, vocab, history


def full_loss(model, vocab, names):
    return model.loss_and_grads(*make_batch(names, vocab))[0]


def generate(model, vocab, prefix="", temperature=0.8, rng=None, max_len=MAX_LEN):
    """Satu nama yang diawali `prefix`. temperature < 1 lebih aman, > 1 lebih berani."""
    if temperature <= 0:
        raise ValueError("Temperature harus lebih dari 0.")
    rng = rng or np.random.default_rng()
    prefix = prefix.strip().lower()
    codes = vocab.encode(prefix)
    h = np.zeros((1, model.hidden))
    current = 0
    out = list(prefix)
    for code in codes:  # paksa model membaca huruf awal
        h, _ = model.step(np.array([current]), h)
        current = code
    while len(out) < max_len:
        h, _ = model.step(np.array([current]), h)
        logits = (h @ model.p["Wy"] + model.p["by"])[0] / temperature
        probs = np.exp(logits - logits.max())
        probs /= probs.sum()
        current = int(rng.choice(len(probs), p=probs))
        if current == 0:
            break
        out.append(vocab.chars[current])
    return "".join(out)


def generate_many(model, vocab, prefix, count=5, temperature=0.8, seed=None, avoid=(), tries=50):
    """Beberapa nama berbeda. `avoid` (misalnya data latih) dilewati kalau diberikan."""
    rng = np.random.default_rng(seed)
    avoid = set(avoid)
    results = []
    for _ in range(count * tries):
        name = generate(model, vocab, prefix, temperature, rng)
        if name and name not in results and name not in avoid:
            results.append(name)
            if len(results) == count:
                break
    return results


def save(model, vocab, path=MODEL, meta=None):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    np.savez_compressed(path, vocab=np.array(vocab.chars), **{k: v.astype(np.float32) for k, v in model.p.items()},
                        **(meta or {}))


def load(path=MODEL):
    with np.load(path) as data:
        vocab = Vocab(list(data["vocab"]))
        model = GRU(len(vocab), int(data["Uz"].shape[0]))
        model.p = {k: data[k].astype(np.float64) for k in PARAMS}
    return model, vocab


def main(argv=None):
    parser = argparse.ArgumentParser(description="Buat nama baru dengan GRU tingkat karakter.")
    parser.add_argument("--prefix", default="", help="2-3 huruf awal nama, misalnya 'ar'")
    parser.add_argument("-n", "--count", type=int, default=5, help="jumlah nama (bawaan 5)")
    parser.add_argument("--temperature", type=float, default=0.8, help="0.3 = aman, 1.2 = berani (bawaan 0.8)")
    parser.add_argument("--baru", action="store_true", help="hanya nama yang tidak ada di data latih")
    parser.add_argument("--seed", type=int, help="angka acak tetap supaya hasilnya bisa diulang")
    parser.add_argument("--train", action="store_true", help="latih ulang model dari data/nama-indonesia.txt")
    parser.add_argument("--steps", type=int, default=2500, help="langkah pelatihan (dengan --train)")
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    names = load_names()
    if args.train:
        def report(step, train_loss, valid_loss):
            if step % 500 == 0:
                print(f"langkah {step:>5}: loss latih {train_loss:.3f} | loss validasi {valid_loss:.3f}")
        model, vocab, history = train(names, steps=args.steps, callback=report)
        best = min(history, key=lambda row: row[2])
        save(model, vocab, meta={"best_step": best[0], "valid_loss": best[2]})
        print(f"Model terbaik di langkah {best[0]} (loss validasi {best[2]:.3f}) disimpan ke {MODEL}")
        return 0
    if not os.path.exists(MODEL):
        print("Error: model belum ada. Jalankan dulu: python name_rnn.py --train", file=sys.stderr)
        return 1
    prefix = args.prefix.strip().lower()
    if prefix and not prefix.isalpha():
        print("Error: huruf awal hanya boleh berisi huruf a-z.", file=sys.stderr)
        return 1
    model, vocab = load()
    try:
        found = generate_many(model, vocab, prefix, args.count, args.temperature, args.seed,
                              avoid=names if args.baru else ())
    except ValueError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    for name in found:
        mark = "" if name in names else "  (baru)"
        print(name.capitalize() + mark)
    if len(found) < args.count:
        print(f"(hanya {len(found)} nama berbeda yang ditemukan)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

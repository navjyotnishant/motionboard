"""Music bed and soft hits for the overview, made from scratch: 120 BPM, A minor, 64 s."""
import numpy as np, soundfile as sf
SR = 48000; BPM = 120; B = 60 / BPM
SCENES = [150, 180, 210, 180, 210, 180, 180, 210, 240, 180]; FPS = 30
T = sum(SCENES) / FPS; n = int(T * SR); t = np.arange(n) / SR
rng = np.random.default_rng(7)
def note(m): return 440 * 2 ** ((m - 69) / 12)
def env(length, a=0.01, d=0.3):
    x = np.arange(int(length * SR)) / SR
    return np.minimum(1, x / a) * np.exp(-x / d)
def add(buf, sig, at):
    i = int(at * SR); j = min(len(buf), i + len(sig))
    if i < len(buf): buf[i:j] += sig[: j - i]
L = np.zeros(n); R = np.zeros(n)
CH = [[57, 60, 64, 69], [53, 57, 60, 65], [48, 55, 60, 64], [55, 59, 62, 67]]  # Am F C G
bars = int(T / (4 * B)) + 1
for b in range(bars):
    ch = CH[(b // 2) % 4]; s = b * 4 * B; dur = 4 * B
    x = np.arange(int(dur * SR)) / SR
    pad = sum(np.sin(2 * np.pi * note(m) * x + rng.uniform(0, 6)) + 0.4 * np.sin(2 * np.pi * note(m) * 2.003 * x) for m in ch)
    pad *= np.minimum(1, x / 0.6) * np.minimum(1, (dur - x) / 0.5) * 0.035
    add(L, pad, s); add(R, np.roll(pad, 300), s)
    bass = np.sin(2 * np.pi * note(ch[0] - 24) * x) * np.minimum(1, x / 0.02) * np.exp(-x / 1.6) * 0.16
    if s >= 5.0: add(L, bass, s); add(R, bass, s)
    for k in range(8):                       # eighth note pluck arpeggio, from the second scene on
        at = s + k * B / 2
        if at < 5.0 or at > T - 5.5: continue
        m = ch[[0, 2, 1, 3, 2, 3, 1, 2][k]] + 12
        xx = np.arange(int(0.5 * SR)) / SR
        pl = (np.sin(2 * np.pi * note(m) * xx) + 0.3 * np.sign(np.sin(2 * np.pi * note(m) * xx))) * env(0.5, 0.004, 0.16) * 0.055
        pan = 0.5 + 0.35 * np.sin(k * 1.7 + b)
        add(L, pl * (1 - pan), at); add(R, pl * pan, at)
    for k in range(4):                       # kick on every beat from the third scene, hats on the off beat
        at = s + k * B
        if 11.0 <= at < T - 6.0:
            xx = np.arange(int(0.28 * SR)) / SR
            kick = np.sin(2 * np.pi * (48 + 70 * np.exp(-xx / 0.03)) * xx) * np.exp(-xx / 0.11) * 0.33
            add(L, kick, at); add(R, kick, at)
            hat = rng.standard_normal(int(0.05 * SR)) * np.exp(-np.arange(int(0.05 * SR)) / SR / 0.012) * 0.035
            hat = np.diff(hat, prepend=0)
            add(L, hat, at + B / 2); add(R, hat * 0.8, at + B / 2)
cut = 0.0
for i, fr in enumerate(SCENES[:-1]):         # a soft whoosh into every cut and a low hit on it
    cut += fr / FPS
    w = int(0.5 * SR); xx = np.arange(w) / SR
    noise = rng.standard_normal(w); k = np.cumsum(noise) ; k = k - np.linspace(k[0], k[-1], w)
    wh = (noise * 0.6 + k / (np.abs(k).max() + 1e-9)) * (xx / 0.5) ** 2.2 * 0.05
    wh = np.convolve(wh, np.ones(24) / 24, mode="same")
    add(L, wh, cut - 0.5); add(R, wh[::-1] * 0 + wh, cut - 0.5)
    xx = np.arange(int(0.6 * SR)) / SR
    hit = np.sin(2 * np.pi * (55 + 40 * np.exp(-xx / 0.05)) * xx) * np.exp(-xx / 0.22) * 0.22
    add(L, hit, cut); add(R, hit, cut)
mix = np.stack([L, R], axis=1)
fade = np.minimum(1, t / 0.4) * np.minimum(1, (T - t) / 2.2)
mix = np.tanh(mix * 1.5) * 0.8 * fade[:, None]
sf.write("/Users/navjyotnishant/dev/motionboard/video/out/bed.wav", mix, SR)
print(round(T, 2), "s", float(np.abs(mix).max()))

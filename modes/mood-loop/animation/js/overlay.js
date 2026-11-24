// Motionboard · Mood Loop pack · overlay: slow light leaks, drifting motes and breathing lyric fades.
// Leaks and motes are periodic in the video length, so the first and last frames meet for a loop.
// Required Notice: Copyright (c) 2026 Navjyot Nishant. PolyForm Noncommercial 1.0.0.
(function () {
  var K = window.K, W = K.W, H = K.H, S = K.S, T = K.T, D = K.D, COL = T.colors || {};
  var IVORY = COL.ivory || [246, 238, 228], WARM = COL.warm || [255, 150, 70], ROSE = COL.rose || [255, 96, 140];
  var GOLD = COL.gold || [255, 210, 130];
  var g = document.getElementById("fx").getContext("2d");
  var wide = W > H, LYRIC_Y = wide ? H * 0.5 : H * 0.42, TAU = Math.PI * 2;
  var LEAKS = [[WARM, 0.0, 0.62], [ROSE, 0.37, 0.5], [GOLD, 0.71, 0.4]];

  function leaks(t) {
    var ph = t / D, beat = K.pulse(t, 0.5);
    g.globalCompositeOperation = "lighter";
    LEAKS.forEach(function (L, i) {
      var cx = W * (0.5 + 0.55 * Math.cos(TAU * (ph + L[1]))), cy = H * (0.45 + 0.45 * Math.sin(TAU * (ph * 2 + L[1])));
      var r = Math.max(W, H) * (0.45 + 0.1 * Math.sin(TAU * (ph + i * 0.2)));
      var gr = g.createRadialGradient(cx, cy, 0, cx, cy, r);
      var a = (0.2 + 0.08 * beat) * L[2] * 2;
      gr.addColorStop(0, K.rgba(L[0], a)); gr.addColorStop(0.5, K.rgba(L[0], a * 0.35)); gr.addColorStop(1, K.rgba(L[0], 0));
      g.fillStyle = gr; g.fillRect(0, 0, W, H);
    });
    g.globalCompositeOperation = "source-over";
  }

  function motes(t) {
    var ph = t / D;
    for (var i = 0; i < 150; i++) {
      var hx = K.hash(i * 1.31), hy = K.hash(i * 2.17), hs = K.hash(i * 3.71), loops = 1 + Math.floor(hs * 2);
      var y = ((hy - ph * loops) % 1 + 1) % 1;
      var x = hx + 0.02 * Math.sin(TAU * (ph * (2 + loops) + hs));
      var tw = 0.5 + 0.5 * Math.sin(TAU * (ph * (6 + i % 5) + hx));
      var r = (1 + 2.4 * hs * hs) * S, a = (0.15 + 0.55 * tw) * (0.4 + 0.6 * hs);
      g.fillStyle = K.rgba(i % 3 ? GOLD : IVORY, a);
      g.beginPath(); g.arc(x * W, y * H, r, 0, TAU); g.fill();
    }
  }

  function lyric(line, t) {
    var age = t - line.t, life = line.out - line.t;
    var a = K.ss(age / 0.6) * (1 - K.ss((age - (life - 0.6)) / 0.6)) * (0.86 + 0.14 * Math.sin(TAU * t / 4));
    if (a <= 0) return;
    var font = K.font("CG", "400", "italic", 74 * S), k = K.fit(g, line.text, font, 1 * S, W * 0.8);
    var drift = (1 - K.eo(age / 1.2)) * 14 * S;
    g.save(); g.shadowColor = K.rgba(WARM, 0.6 * a); g.shadowBlur = 26 * S;
    K.text(g, line.text, W / 2, LYRIC_Y + drift, K.font("CG", "400", "italic", 74 * S * k), 1 * S, K.rgba(IVORY, a));
    g.restore();
  }

  function endCard(t) {
    var a = K.ss((t - K.END) / 0.9) * (1 - K.ss((t - K.EOUT) / 0.5));
    if (a <= 0) return;
    g.save(); g.shadowColor = K.rgba(WARM, 0.5 * a); g.shadowBlur = 30 * S;
    if (T.artist) K.text(g, String(T.artist).toUpperCase(), W / 2, LYRIC_Y - 20 * S, K.font("CG", "500", "normal", 96 * S), 26 * S, K.rgba(IVORY, a));
    if (T.song) K.text(g, T.song, W / 2, LYRIC_Y + 80 * S, K.font("CG", "400", "italic", 72 * S), 2 * S, K.rgba(GOLD, a));
    if (T.release_note) K.text(g, T.release_note, W / 2, LYRIC_Y + 170 * S, K.font("CG", "500", "normal", 34 * S), 16 * S, K.rgba(ROSE, a));
    g.restore();
  }

  window.OVERLAY = {
    init: function () {},
    render: function (t) {
      g.clearRect(0, 0, W, H); g.fillStyle = "#000"; g.fillRect(0, 0, W, H);
      leaks(t); motes(t);
      var line = K.lineAt(t);
      if (line) lyric(line, t);
      endCard(t);
    },
  };
})();

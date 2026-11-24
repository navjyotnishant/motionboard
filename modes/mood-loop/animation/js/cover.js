// Motionboard · Mood Loop pack · cover: a soft glow title over a clean frame.
// Required Notice: Copyright (c) 2026 Navjyot Nishant. PolyForm Noncommercial 1.0.0.
(function () {
  var K = window.K, W = K.W, H = K.H, S = K.S, T = K.T, g = document.getElementById("fx").getContext("2d");
  window.COVER = {
    init: function () {
      var sh = g.createLinearGradient(0, H * 0.55, 0, H);
      sh.addColorStop(0, "rgba(14,6,20,0)"); sh.addColorStop(0.5, "rgba(14,6,20,0.7)"); sh.addColorStop(1, "rgba(14,6,20,0.95)");
      g.fillStyle = sh; g.fillRect(0, 0, W, H);
      var base = H - 400 * S;
      g.save(); g.shadowColor = "rgba(255,150,70,0.6)"; g.shadowBlur = 30 * S;
      if (T.artist) K.text(g, String(T.artist).toUpperCase(), W / 2, base, K.font("CG", "500", "normal", 104 * S), 28 * S, "#f6eee4");
      if (T.song) K.text(g, T.song, W / 2, base + 100 * S, K.font("CG", "400", "italic", 76 * S), 2 * S, "#ffd282");
      g.restore();
    },
    render: function () {},
  };
})();

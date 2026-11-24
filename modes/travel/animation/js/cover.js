// Motionboard · Travel pack · cover: a clean frame with a ticket stub title block.
// Required Notice: Copyright (c) 2026 Navjyot Nishant. PolyForm Noncommercial 1.0.0.
(function () {
  var K = window.K, W = K.W, H = K.H, S = K.S, T = K.T, g = document.getElementById("fx").getContext("2d");
  window.COVER = {
    init: function () {
      var sh = g.createLinearGradient(0, H * 0.6, 0, H);
      sh.addColorStop(0, "rgba(12,8,4,0)"); sh.addColorStop(0.4, "rgba(12,8,4,0.7)"); sh.addColorStop(1, "rgba(12,8,4,0.95)");
      g.fillStyle = sh; g.fillRect(0, 0, W, H);
      var base = H - 470 * S, bw = Math.min(W * 0.8, 860 * S), x = W / 2 - bw / 2;
      g.lineWidth = 3 * S; g.strokeStyle = "rgba(243,236,224,0.9)";
      g.beginPath(); g.roundRect(x, base - 40 * S, bw, 250 * S, 20 * S); g.stroke();
      K.text(g, "BOARDING PASS", x + 30 * S, base + 4 * S, K.font("JBM", "500", "normal", 22 * S), 8 * S, "rgba(232,196,120,0.95)", "left");
      if (T.artist) K.text(g, String(T.artist).toUpperCase(), W / 2, base + 92 * S, K.font("CG", "500", "normal", 84 * S), 24 * S, "#f3ece0");
      if (T.song) K.text(g, T.song, W / 2, base + 170 * S, K.font("CG", "400", "italic", 64 * S), 2 * S, "#e8c478");
    },
    render: function () {},
  };
})();

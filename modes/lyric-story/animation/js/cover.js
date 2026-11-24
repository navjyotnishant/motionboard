// Motionboard · Lyric Story pack · cover: the song title as one bold block, the artist in handwriting.
// Required Notice: Copyright (c) 2026 Navjyot Nishant. PolyForm Noncommercial 1.0.0.
(function () {
  var K = window.K, W = K.W, H = K.H, S = K.S, T = K.T, g = document.getElementById("fx").getContext("2d");
  window.COVER = {
    init: function () {
      g.fillStyle = "rgba(10,10,12,0.45)"; g.fillRect(0, 0, W, H);
      var sh = g.createLinearGradient(0, H * 0.55, 0, H);
      sh.addColorStop(0, "rgba(10,10,12,0)"); sh.addColorStop(0.5, "rgba(10,10,12,0.75)"); sh.addColorStop(1, "rgba(10,10,12,0.95)");
      g.fillStyle = sh; g.fillRect(0, 0, W, H);
      var base = H - 420 * S;
      if (T.song) {
        var s = String(T.song).toUpperCase(), f = K.font("IT", "800", "normal", 150 * S), k = K.fit(g, s, f, -2 * S, W * 0.86);
        K.text(g, s, W / 2, base, K.font("IT", "800", "normal", 150 * S * k), -2 * S, "#f4eee2");
      }
      if (T.artist) K.text(g, T.artist, W / 2, base + 130 * S, K.font("LBA", "400", "normal", 80 * S), 0, "#ffa840");
    },
    render: function () {},
  };
})();

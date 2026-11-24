// Motionboard · Lyric Story pack · matte, multiplied over the cut: a deep charcoal grade so the type
// carries the frame, a one frame black hit on every cut, the end card dim, fades.
// Required Notice: Copyright (c) 2026 Navjyot Nishant. PolyForm Noncommercial 1.0.0.
(function () {
  var K = window.K, W = K.W, H = K.H, g = document.getElementById("fx").getContext("2d");
  function level(t) {
    var m = K.fadeIO(t);
    for (var i = 0; i < K.CUTS.length; i++) if (t >= K.CUTS[i] && t < K.CUTS[i] + 1 / 24) m *= 0.12;
    m *= 1 - 0.7 * K.ss((t - K.END) / 0.3);
    return K.clamp(m);
  }
  window.MATTE = {
    init: function () {},
    render: function (t) {
      g.fillStyle = "rgb(150,146,140)"; g.fillRect(0, 0, W, H);
      var v = g.createRadialGradient(W / 2, H / 2, Math.min(W, H) * 0.3, W / 2, H / 2, Math.max(W, H) * 0.7);
      v.addColorStop(0, "rgba(0,0,0,0)"); v.addColorStop(1, "rgba(0,0,0,0.6)"); g.fillStyle = v; g.fillRect(0, 0, W, H);
      var m = level(t); if (m < 1) { g.fillStyle = "rgba(0,0,0," + (1 - m).toFixed(4) + ")"; g.fillRect(0, 0, W, H); }
    },
  };
})();

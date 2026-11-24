// Motionboard · Mood Loop pack · matte, multiplied over the cut: a soft vignette that breathes on the
// beat, gentle dips on cuts, the end card dim, fades from and to black so the loop point is clean.
// Required Notice: Copyright (c) 2026 Navjyot Nishant. PolyForm Noncommercial 1.0.0.
(function () {
  var K = window.K, W = K.W, H = K.H, g = document.getElementById("fx").getContext("2d");
  function level(t) {
    var m = K.fadeIO(t);
    for (var i = 0; i < K.CUTS.length; i++) { var d = (t - K.CUTS[i]) / 0.2; m *= 1 - 0.2 * Math.exp(-d * d); }
    m *= 1 - 0.45 * K.ss((t - K.END) / 0.9);
    return K.clamp(m);
  }
  window.MATTE = {
    init: function () {},
    render: function (t) {
      g.fillStyle = "#fff"; g.fillRect(0, 0, W, H);
      var inner = Math.min(W, H) * (0.36 + 0.04 * K.pulse(t, 0.5));
      var v = g.createRadialGradient(W / 2, H / 2, inner, W / 2, H / 2, Math.max(W, H) * 0.7);
      v.addColorStop(0, "rgba(0,0,0,0)"); v.addColorStop(1, "rgba(10,0,20,0.6)"); g.fillStyle = v; g.fillRect(0, 0, W, H);
      var m = level(t); if (m < 1) { g.fillStyle = "rgba(0,0,0," + (1 - m).toFixed(4) + ")"; g.fillRect(0, 0, W, H); }
    },
  };
})();

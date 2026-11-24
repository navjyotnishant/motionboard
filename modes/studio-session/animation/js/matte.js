// Motionboard · Studio Session pack · matte, multiplied over the cut: vignette, a veil behind the
// lyric sheet, a shelf behind the meters, short blinks on cuts, the end card dim, fades.
// Required Notice: Copyright (c) 2026 Navjyot Nishant. PolyForm Noncommercial 1.0.0.
(function () {
  var K = window.K, W = K.W, H = K.H, g = document.getElementById("fx").getContext("2d");
  var wide = W > H;
  function level(t) {
    var m = K.fadeIO(t);
    for (var i = 0; i < K.CUTS.length; i++) { var d = (t - K.CUTS[i]) / 0.06; m *= 1 - 0.45 * Math.exp(-d * d); }
    m *= 1 - 0.5 * K.ss((t - K.END + 0.3) / 0.6);
    return K.clamp(m);
  }
  window.MATTE = {
    init: function () {},
    render: function (t) {
      g.fillStyle = "#fff"; g.fillRect(0, 0, W, H);
      var v = g.createRadialGradient(W / 2, H / 2, Math.min(W, H) * 0.42, W / 2, H / 2, Math.max(W, H) * 0.7);
      v.addColorStop(0, "rgba(0,0,0,0)"); v.addColorStop(1, "rgba(0,0,0,0.55)"); g.fillStyle = v; g.fillRect(0, 0, W, H);
      var top = g.createLinearGradient(0, 0, 0, H * (wide ? 0.4 : 0.34));
      top.addColorStop(0, "rgba(0,0,0,0.5)"); top.addColorStop(0.6, "rgba(0,0,0,0.35)"); top.addColorStop(1, "rgba(0,0,0,0)");
      g.fillStyle = top; g.fillRect(0, 0, W, H * 0.4);
      var y0 = H * (wide ? 0.66 : 0.64), y1 = H * (wide ? 0.95 : 0.83);
      var shelf = g.createLinearGradient(0, y0, 0, y1);
      shelf.addColorStop(0, "rgba(0,0,0,0)"); shelf.addColorStop(0.4, "rgba(0,0,0,0.35)"); shelf.addColorStop(1, "rgba(0,0,0,0.15)");
      g.fillStyle = shelf; g.fillRect(0, y0, W, y1 - y0);
      var m = level(t); if (m < 1) { g.fillStyle = "rgba(0,0,0," + (1 - m).toFixed(4) + ")"; g.fillRect(0, 0, W, H); }
    },
  };
})();

// Motionboard · Travel pack · matte, multiplied over the cut: warm vignette, a veil behind the stamps,
// a band under the route, a soft dip on each cut, the end card dim, fades.
// Required Notice: Copyright (c) 2026 Navjyot Nishant. PolyForm Noncommercial 1.0.0.
(function () {
  var K = window.K, W = K.W, H = K.H, g = document.getElementById("fx").getContext("2d");
  var wide = W > H;
  function level(t) {
    var m = K.fadeIO(t);
    for (var i = 0; i < K.CUTS.length; i++) { var d = (t - K.CUTS[i]) / 0.09; m *= 1 - 0.3 * Math.exp(-d * d); }
    m *= 1 - 0.5 * K.ss((t - K.END + 0.3) / 0.6);
    return K.clamp(m);
  }
  window.MATTE = {
    init: function () {},
    render: function (t) {
      g.fillStyle = "#fff"; g.fillRect(0, 0, W, H);
      g.fillStyle = "rgba(255,236,214,1)"; g.fillRect(0, 0, W, H); // warm paper tint
      var v = g.createRadialGradient(W / 2, H * 0.5, Math.min(W, H) * 0.4, W / 2, H * 0.5, Math.max(W, H) * 0.72);
      v.addColorStop(0, "rgba(0,0,0,0)"); v.addColorStop(1, "rgba(30,10,0,0.55)"); g.fillStyle = v; g.fillRect(0, 0, W, H);
      var y = H * (wide ? 0.3 : 0.25), veil = g.createLinearGradient(0, y - H * 0.14, 0, y + H * 0.14);
      veil.addColorStop(0, "rgba(0,0,0,0)"); veil.addColorStop(0.5, "rgba(0,0,0,0.32)"); veil.addColorStop(1, "rgba(0,0,0,0)");
      g.fillStyle = veil; g.fillRect(0, y - H * 0.14, W, H * 0.28);
      var ry = H * (wide ? 0.82 : 0.7), band = g.createLinearGradient(0, ry - H * 0.1, 0, ry + H * 0.1);
      band.addColorStop(0, "rgba(0,0,0,0)"); band.addColorStop(0.5, "rgba(0,0,0,0.3)"); band.addColorStop(1, "rgba(0,0,0,0)");
      g.fillStyle = band; g.fillRect(0, ry - H * 0.1, W, H * 0.2);
      var m = level(t); if (m < 1) { g.fillStyle = "rgba(0,0,0," + (1 - m).toFixed(4) + ")"; g.fillRect(0, 0, W, H); }
    },
  };
})();

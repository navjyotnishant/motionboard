// Motionboard · Travel pack · overlay: a dotted route that draws itself from stop to stop, one stop per
// cut; lyric lines pressed in as ink stamps; a boarding pass end card. No place names anywhere.
// Required Notice: Copyright (c) 2026 Navjyot Nishant. PolyForm Noncommercial 1.0.0.
(function () {
  var K = window.K, W = K.W, H = K.H, S = K.S, T = K.T, COL = T.colors || {};
  var IVORY = COL.ivory || [243, 236, 224], INK = COL.ink || [120, 190, 255], STAMP = COL.stamp || [255, 110, 90];
  var GOLD = COL.gold || [232, 196, 120];
  var g = document.getElementById("fx").getContext("2d");
  var wide = W > H, ROUTE_Y = wide ? H * 0.82 : H * 0.7, STAMP_Y = wide ? H * 0.3 : H * 0.25;
  var STOPS = [];

  function buildStops() {
    if (STOPS.length) return;
    var times = [0.4].concat(K.CUTS.filter(function (c) { return c < K.END; })).concat([K.END]);
    var n = times.length;
    for (var i = 0; i < n; i++) {
      var f = n > 1 ? i / (n - 1) : 0;
      var x = W * 0.12 + W * 0.76 * f;
      var y = ROUTE_Y + (K.hash(i * 4.3) - 0.5) * H * 0.07 * (i === 0 || i === n - 1 ? 0.4 : 1);
      STOPS.push({ t: times[i], x: x, y: y });
    }
  }

  function pointOn(a, b, u) {
    var mx = (a.x + b.x) / 2, my = Math.min(a.y, b.y) - H * 0.04;
    var v = 1 - u;
    return { x: v * v * a.x + 2 * v * u * mx + u * u * b.x, y: v * v * a.y + 2 * v * u * my + u * u * b.y };
  }

  function route(t, a) {
    if (STOPS.length < 2) return;
    var head = null;
    for (var i = 0; i < STOPS.length - 1; i++) {
      var A = STOPS[i], B = STOPS[i + 1];
      if (t < A.t) break;
      var u = K.clamp((t - A.t) / Math.max(0.3, B.t - A.t));
      var steps = Math.max(2, Math.floor(40 * u));
      for (var j = 0; j <= steps; j++) {
        if (j % 2) continue;
        var p = pointOn(A, B, (j / 40));
        if (j / 40 > u) break;
        g.fillStyle = K.rgba(IVORY, 0.75 * a);
        g.beginPath(); g.arc(p.x, p.y, 3.2 * S, 0, Math.PI * 2); g.fill();
      }
      head = pointOn(A, B, u);
    }
    STOPS.forEach(function (s, i) {
      if (t < s.t) return;
      var pop = K.eo((t - s.t) / 0.35), r = (9 + 6 * K.pulse(t, 0.25) * (i === K.cutIndex(t) ? 1 : 0)) * S;
      g.strokeStyle = K.rgba(GOLD, 0.9 * a); g.lineWidth = 2.5 * S;
      g.beginPath(); g.arc(s.x, s.y, r * pop, 0, Math.PI * 2); g.stroke();
      g.fillStyle = K.rgba(GOLD, 0.9 * a); g.beginPath(); g.arc(s.x, s.y, 3.5 * S * pop, 0, Math.PI * 2); g.fill();
    });
    if (head) {
      g.fillStyle = K.rgba(IVORY, a);
      g.beginPath(); g.arc(head.x, head.y, 7 * S, 0, Math.PI * 2); g.fill();
      g.fillStyle = K.rgba(IVORY, 0.25 * a);
      g.beginPath(); g.arc(head.x, head.y, 16 * S, 0, Math.PI * 2); g.fill();
    }
  }

  function stamp(line, t) {
    var age = t - line.t, life = line.out - line.t;
    var press = K.eo(age / 0.22), fade = 1 - K.ss((age - (life - 0.25)) / 0.25);
    var a = K.ss(age / 0.08) * fade;
    if (a <= 0) return;
    var rot = (K.hash(line.i * 9.1) - 0.5) * 0.14, scale = 1.25 - 0.25 * press;
    var col = line.i % 2 ? INK : STAMP;
    var font = K.font("JBM", "500", "normal", 44 * S), text = line.text.toUpperCase();
    var k = K.fit(g, text, font, 6 * S, W * 0.7);
    font = K.font("JBM", "500", "normal", 44 * S * k);
    g.font = font; g.letterSpacing = 6 * S + "px";
    var tw = g.measureText(text).width, bw = tw + 70 * S, bh = 104 * S * Math.max(k, 0.7);
    g.save();
    g.translate(W / 2 + (K.hash(line.i * 2.7) - 0.5) * W * 0.06, STAMP_Y + (K.hash(line.i * 5.3) - 0.5) * H * 0.03);
    g.rotate(rot); g.scale(scale, scale);
    g.strokeStyle = K.rgba(col, 0.85 * a); g.lineWidth = 4 * S;
    g.beginPath(); g.roundRect(-bw / 2, -bh / 2, bw, bh, 14 * S); g.stroke();
    g.lineWidth = 1.5 * S;
    g.beginPath(); g.roundRect(-bw / 2 + 9 * S, -bh / 2 + 9 * S, bw - 18 * S, bh - 18 * S, 8 * S); g.stroke();
    K.text(g, text, 0, 15 * S * k, font, 6 * S, K.rgba(col, 0.95 * a));
    // ink texture: knock out a few specks so the stamp reads as pressed, not printed
    g.globalCompositeOperation = "destination-out";
    for (var i = 0; i < 70; i++) {
      var hx = K.hash(line.i * 31 + i * 1.7), hy = K.hash(line.i * 17 + i * 2.9);
      g.fillStyle = "rgba(0,0,0," + (0.4 + 0.6 * K.hash(i * 3.3)).toFixed(3) + ")";
      g.fillRect(-bw / 2 + hx * bw, -bh / 2 + hy * bh, (1 + 3 * K.hash(i)) * S, (1 + 2 * K.hash(i * 7)) * S);
    }
    g.globalCompositeOperation = "source-over";
    g.restore();
  }

  function pass(t) {
    var a = K.ss((t - K.END) / 0.5) * (1 - K.ss((t - K.EOUT) / 0.5));
    if (a <= 0) return;
    var p = K.eo((t - K.END) / 0.8);
    var pw = wide ? H * 1.1 : W * 0.8, ph = pw * 0.5, x = W / 2 - pw / 2, y = (wide ? H * 0.48 : H * 0.4) - ph / 2;
    x += (1 - p) * 60 * S;
    g.strokeStyle = K.rgba(IVORY, 0.9 * a); g.lineWidth = 3 * S;
    g.beginPath(); g.roundRect(x, y, pw, ph, 22 * S); g.stroke();
    var cut = x + pw * 0.7;
    g.setLineDash([6 * S, 8 * S]); g.beginPath(); g.moveTo(cut, y + 14 * S); g.lineTo(cut, y + ph - 14 * S); g.stroke(); g.setLineDash([]);
    K.text(g, "BOARDING PASS", x + 34 * S, y + 56 * S, K.font("JBM", "500", "normal", 24 * S), 8 * S, K.rgba(GOLD, a), "left");
    K.text(g, "ARTIST", x + 34 * S, y + 112 * S, K.font("JBM", "500", "normal", 18 * S), 5 * S, K.rgba(GOLD, 0.8 * a), "left");
    if (T.artist) K.text(g, String(T.artist).toUpperCase(), x + 34 * S, y + 170 * S, K.font("CG", "500", "normal", 60 * S), 14 * S, K.rgba(IVORY, a), "left");
    K.text(g, "SONG", x + 34 * S, y + 222 * S, K.font("JBM", "500", "normal", 18 * S), 5 * S, K.rgba(GOLD, 0.8 * a), "left");
    if (T.song) {
      var sf = K.font("CG", "400", "italic", 52 * S), sk = K.fit(g, T.song, sf, 2 * S, pw * 0.62);
      K.text(g, T.song, x + 34 * S, y + 276 * S, K.font("CG", "400", "italic", 52 * S * sk), 2 * S, K.rgba(IVORY, a), "left");
    }
    if (T.album_line) K.text(g, T.album_line, x + 34 * S, y + ph - 30 * S, K.font("JBM", "500", "normal", 17 * S), 3 * S, K.rgba(GOLD, 0.8 * a), "left");
    var sx = cut + 26 * S, sw = x + pw - 26 * S - sx;
    K.text(g, "GATE", sx, y + 56 * S, K.font("JBM", "500", "normal", 18 * S), 5 * S, K.rgba(GOLD, 0.8 * a), "left");
    K.text(g, T.release_note || "NOW", sx, y + 100 * S, K.font("JBM", "500", "normal", 26 * S), 3 * S, K.rgba(STAMP, a), "left");
    for (var i = 0; i < 34; i++) {
      var bw = (1 + Math.floor(K.hash(i * 3.7) * 3)) * 2 * S, bx = sx + (i / 34) * sw;
      if (bx + bw > sx + sw) break;
      g.fillStyle = K.rgba(IVORY, 0.85 * a); g.fillRect(bx, y + ph * 0.5, bw, ph * 0.36);
    }
  }

  window.OVERLAY = {
    init: function () { buildStops(); },
    render: function (t) {
      buildStops();
      g.clearRect(0, 0, W, H); g.fillStyle = "#000"; g.fillRect(0, 0, W, H);
      var a = K.ss((t - 0.3) / 0.4) * (1 - K.ss((t - (K.END - 0.4)) / 0.4));
      if (a > 0) route(t, a);
      var line = K.lineAt(t);
      if (line) stamp(line, t);
      pass(t);
    },
  };
})();

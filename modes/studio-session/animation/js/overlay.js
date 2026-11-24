// Motionboard · Studio Session pack · overlay: REC light, tape counter, typed lyric sheet,
// VU meters that kick on the beat, and a cassette label end card.
// Required Notice: Copyright (c) 2026 Navjyot Nishant. PolyForm Noncommercial 1.0.0.
(function () {
  var K = window.K, W = K.W, H = K.H, S = K.S, T = K.T, COL = T.colors || {};
  var IVORY = COL.ivory || [243, 236, 224], AMBER = COL.amber || [236, 204, 150];
  var RED = COL.red || [255, 72, 60], BRASS = COL.brass || [201, 160, 96];
  var g = document.getElementById("fx").getContext("2d");
  var wide = W > H, TOP = wide ? H * 0.1 : H * 0.15, SHEET = wide ? H * 0.24 : H * 0.235;
  var METER_Y = wide ? H * 0.8 : H * 0.735, MR = 118 * S;

  function counter(t) {
    var f = Math.floor(t * 24), s = Math.floor(f / 24), m = Math.floor(s / 60);
    function p(n) { return (n < 10 ? "0" : "") + n; }
    return p(m) + ":" + p(s % 60) + ":" + p(f % 24);
  }

  function rec(t, a) {
    var on = (t % 1) < 0.68 ? 1 : 0.25;
    g.fillStyle = K.rgba(RED, a * on);
    g.beginPath(); g.arc(W * 0.12, TOP - 11 * S, 12 * S, 0, Math.PI * 2); g.fill();
    K.text(g, "REC", W * 0.12 + 26 * S, TOP, K.font("JBM", "500", "normal", 30 * S), 4 * S, K.rgba(RED, a * on), "left");
    K.text(g, counter(t), W * 0.88, TOP, K.font("JBM", "500", "normal", 30 * S), 3 * S, K.rgba(AMBER, a), "right");
  }

  function typed(line, t) {
    var n = line.text.length, span = Math.max(0.5, (line.out - line.t) * 0.55);
    var cps = Math.max(18, n / span);
    return Math.min(n, Math.floor((t - line.t) * cps));
  }

  function sheet(t) {
    var line = K.lineAt(t);
    if (!line) return;
    var font = K.font("JBM", "500", "normal", 44 * S), maxw = W * 0.8;
    var prev = line.i > 0 ? K.LINES[line.i - 1] : null;
    var a = K.ss((t - line.t) / 0.15) * (1 - K.ss((t - (line.out - 0.18)) / 0.18));
    g.strokeStyle = K.rgba(AMBER, 0.16 * a); g.lineWidth = 1.5 * S;
    for (var r = 0; r < 2; r++) {
      g.beginPath(); g.moveTo(W * 0.1, SHEET + 16 * S - r * 70 * S); g.lineTo(W * 0.9, SHEET + 16 * S - r * 70 * S); g.stroke();
    }
    if (prev && t - prev.out < 2.5) {
      var k = K.fit(g, prev.text, font, 2 * S, maxw);
      K.text(g, prev.text, W / 2, SHEET - 70 * S, K.font("JBM", "500", "normal", 44 * S * k), 2 * S, K.rgba(IVORY, 0.3 * a));
    }
    var shown = line.text.slice(0, typed(line, t));
    var k2 = K.fit(g, line.text, font, 2 * S, maxw), f2 = K.font("JBM", "500", "normal", 44 * S * k2);
    g.font = f2; g.letterSpacing = 2 * S + "px";
    var full = g.measureText(line.text).width, x0 = W / 2 - full / 2;
    K.text(g, shown, x0, SHEET, f2, 2 * S, K.rgba(IVORY, a), "left");
    g.font = f2; g.letterSpacing = 2 * S + "px";
    var cw = g.measureText(shown).width;
    if ((t * 2.2) % 1 < 0.6) { g.fillStyle = K.rgba(AMBER, 0.85 * a); g.fillRect(x0 + cw + 4 * S, SHEET - 36 * S * k2, 20 * S * k2, 42 * S * k2); }
  }

  function meter(cx, cy, v, a, label) {
    var a0 = Math.PI * 1.25, a1 = Math.PI * 1.75;
    g.lineWidth = 3 * S; g.strokeStyle = K.rgba(BRASS, 0.75 * a);
    g.beginPath(); g.arc(cx, cy, MR, a0, a0 + (a1 - a0) * 0.74); g.stroke();
    g.strokeStyle = K.rgba(RED, 0.85 * a);
    g.beginPath(); g.arc(cx, cy, MR, a0 + (a1 - a0) * 0.76, a1); g.stroke();
    for (var i = 0; i <= 10; i++) {
      var an = a0 + (a1 - a0) * i / 10, l = i % 5 === 0 ? 18 : 10;
      g.strokeStyle = K.rgba(i > 7 ? RED : BRASS, 0.7 * a); g.lineWidth = 2 * S;
      g.beginPath(); g.moveTo(cx + Math.cos(an) * MR, cy + Math.sin(an) * MR);
      g.lineTo(cx + Math.cos(an) * (MR - l * S), cy + Math.sin(an) * (MR - l * S)); g.stroke();
    }
    var na = a0 + (a1 - a0) * K.clamp(v);
    g.strokeStyle = K.rgba(IVORY, 0.95 * a); g.lineWidth = 3 * S;
    g.beginPath(); g.moveTo(cx, cy); g.lineTo(cx + Math.cos(na) * (MR + 6 * S), cy + Math.sin(na) * (MR + 6 * S)); g.stroke();
    g.fillStyle = K.rgba(AMBER, a); g.beginPath(); g.arc(cx, cy, 7 * S, 0, Math.PI * 2); g.fill();
    K.text(g, label, cx, cy + 40 * S, K.font("JBM", "500", "normal", 22 * S), 6 * S, K.rgba(BRASS, 0.8 * a));
  }

  function meters(t, a) {
    var jit = (K.hash(Math.floor(t * 24)) - 0.5) * 0.06;
    var base = 0.18 + 0.05 * Math.sin(t * 3.1);
    meter(W * 0.34, METER_Y, base + 0.72 * K.pulse(t, 0.22) + jit, a, "L");
    meter(W * 0.66, METER_Y, base + 0.7 * K.pulse(t - 0.02, 0.24) - jit, a, "R");
  }

  function cassette(t) {
    var p = K.eo((t - K.END) / 0.7), a = K.ss((t - K.END) / 0.5) * (1 - K.ss((t - K.EOUT) / 0.5));
    if (a <= 0) return;
    var cw = wide ? H * 0.95 : W * 0.78, ch = cw * 0.62, x = W / 2 - cw / 2, y = H * (wide ? 0.5 : 0.42) - ch / 2;
    y += (1 - p) * 40 * S;
    g.lineWidth = 3 * S; g.strokeStyle = K.rgba(AMBER, 0.9 * a);
    g.beginPath(); g.roundRect(x, y, cw, ch, 26 * S); g.stroke();
    g.strokeStyle = K.rgba(BRASS, 0.7 * a); g.lineWidth = 2 * S;
    g.beginPath(); g.roundRect(x + cw * 0.06, y + ch * 0.07, cw * 0.88, ch * 0.46, 12 * S); g.stroke();
    if (T.artist) K.text(g, String(T.artist).toUpperCase(), W / 2, y + ch * 0.22, K.font("CG", "500", "normal", 58 * S), 18 * S, K.rgba(IVORY, a));
    if (T.song) K.text(g, T.song, W / 2, y + ch * 0.36, K.font("CG", "400", "italic", 54 * S), 2 * S, K.rgba(AMBER, a));
    K.text(g, "SIDE A", x + cw * 0.11, y + ch * 0.48, K.font("JBM", "500", "normal", 20 * S), 6 * S, K.rgba(BRASS, a), "left");
    if (T.album_line) K.text(g, T.album_line, x + cw * 0.89, y + ch * 0.48, K.font("JBM", "500", "normal", 18 * S), 3 * S, K.rgba(BRASS, a), "right");
    var spin = t * 2.4;
    [0.3, 0.7].forEach(function (fx) {
      var cx = x + cw * fx, cy = y + ch * 0.75, r = ch * 0.13;
      g.strokeStyle = K.rgba(AMBER, 0.85 * a); g.lineWidth = 2.5 * S;
      g.beginPath(); g.arc(cx, cy, r, 0, Math.PI * 2); g.stroke();
      for (var i = 0; i < 6; i++) {
        var an = spin + i * Math.PI / 3;
        g.beginPath(); g.moveTo(cx + Math.cos(an) * r * 0.35, cy + Math.sin(an) * r * 0.35);
        g.lineTo(cx + Math.cos(an) * r * 0.8, cy + Math.sin(an) * r * 0.8); g.stroke();
      }
    });
    g.strokeStyle = K.rgba(BRASS, 0.5 * a);
    g.beginPath(); g.moveTo(x + cw * 0.3, y + ch * 0.88); g.lineTo(x + cw * 0.7, y + ch * 0.88); g.stroke();
    if (T.release_note) K.text(g, T.release_note, W / 2, y + ch + 70 * S, K.font("JBM", "500", "normal", 32 * S), 14 * S, K.rgba(RED, a));
  }

  window.OVERLAY = {
    init: function () {},
    render: function (t) {
      g.clearRect(0, 0, W, H); g.fillStyle = "#000"; g.fillRect(0, 0, W, H);
      var a = K.ss((t - 0.3) / 0.4) * (1 - K.ss((t - (K.END - 0.4)) / 0.4));
      if (a > 0) { rec(t, a); meters(t, a); }
      sheet(t);
      cassette(t);
    },
  };
})();

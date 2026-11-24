// Motionboard pack helpers: timing, easing and lyric rows shared by the layers of this pack.
// Every value is a pure function of the config and t, so any frame renders on its own.
// Required Notice: Copyright (c) 2026 Navjyot Nishant. PolyForm Noncommercial 1.0.0.
(function () {
  var C = window.MB, W = C.width, H = C.height, D = C.duration, MUSIC = C.music_end;
  var K = {
    C: C, W: W, H: H, D: D, MUSIC: MUSIC, T: C.theme || {}, S: Math.min(W, H) / 1080,
    CUTS: C.cuts || [], BEATS: C.beats || C.downbeats || [], DOWN: C.downbeats || [],
  };
  K.clamp = function (x) { return x < 0 ? 0 : x > 1 ? 1 : x; };
  K.ss = function (x) { x = K.clamp(x); return x * x * (3 - 2 * x); };
  K.eo = function (x) { var u = K.clamp(x) - 1; return u * u * u + 1; };
  K.hash = function (n) { var s = Math.sin(n * 127.1 + 311.7) * 43758.5453; return s - Math.floor(s); };
  K.rgba = function (c, a) { return "rgba(" + c[0] + "," + c[1] + "," + c[2] + "," + K.clamp(a).toFixed(4) + ")"; };
  // End card first: lyrics clear before it forms. No follow or subscribe ask anywhere.
  K.END = D > 8 ? MUSIC - 2.3 : MUSIC * 0.6;
  K.EOUT = D - 0.6;
  K.LINES = [];
  (C.lines || []).forEach(function (ln, i, all) {
    var t = ln.start, nxt = i + 1 < all.length ? all[i + 1].start : MUSIC;
    if (t > K.END - 0.9 || !ln.text || !ln.text.trim()) return;
    var out = Math.max(t + 0.8, Math.min(nxt, MUSIC) - 0.1);
    if (out > K.END - 0.05) out = K.END - 0.05;
    K.LINES.push({ i: K.LINES.length, t: t, out: out, end: ln.end, text: ln.text.trim() });
  });
  K.lineAt = function (t) {
    for (var i = 0; i < K.LINES.length; i++) if (t >= K.LINES[i].t && t < K.LINES[i].out) return K.LINES[i];
    return null;
  };
  // Beat envelope: a sharp rise and an exponential fall on each beat, stronger on downbeats.
  K.pulse = function (t, decay) {
    decay = decay || 0.18;
    var v = 0;
    for (var i = 0; i < K.BEATS.length; i++) {
      var d = t - K.BEATS[i];
      if (d < -0.03) break;
      if (d > 1.2) continue;
      var down = K.DOWN.indexOf(K.BEATS[i]) >= 0 ? 1 : 0.65;
      v = Math.max(v, down * (d < 0 ? 1 + d / 0.03 : Math.exp(-d / decay)));
    }
    return v;
  };
  K.cutIndex = function (t) { var n = 0; for (var i = 0; i < K.CUTS.length; i++) if (t >= K.CUTS[i]) n = i + 1; return n; };
  K.fadeIO = function (t) { return K.ss(t / 0.5) * (1 - K.ss((t - (D - 1.3)) / 1.2)); };
  K.font = function (fam, w, st, px) { return (st === "italic" ? "italic " : "") + w + " " + px + 'px "' + fam + '"'; };
  K.text = function (g, s, x, y, font, ls, color, align) {
    g.font = font; g.letterSpacing = (ls || 0) + "px"; g.textAlign = align || "center"; g.textBaseline = "alphabetic";
    g.fillStyle = color; g.fillText(s, x + (align === "left" ? 0 : (ls || 0) / 2), y);
  };
  K.fit = function (g, s, font, ls, maxw) {
    g.font = font; g.letterSpacing = (ls || 0) + "px";
    var w = g.measureText(s).width;
    return w > maxw ? maxw / w : 1;
  };
  window.K = K;
})();

// Motionboard · Lyric Story pack · overlay: kinetic typography. One big word per beat with hard cuts,
// the full line written underneath in handwriting, and a title end card.
// Ported from the NAVAAN "A Letter Never Sent" promo (bold sans beats, handwriting contrast).
// Required Notice: Copyright (c) 2026 Navjyot Nishant. PolyForm Noncommercial 1.0.0.
(function () {
  var K = window.K, W = K.W, H = K.H, S = K.S, T = K.T, COL = T.colors || {};
  var IVORY = COL.ivory || [244, 238, 226], ACCENT = COL.accent || [255, 168, 64], GOLD = COL.gold || [214, 178, 110];
  var HIGH = (T.highlight_words || []).map(function (w) { return String(w).toLowerCase(); });
  var g = document.getElementById("fx").getContext("2d");
  var wide = W > H, WORD_Y = wide ? H * 0.5 : H * 0.44, HAND_Y = WORD_Y + (wide ? 120 : 160) * S;
  var MAXPX = (wide ? 190 : 230) * S;

  function nearestBeat(x) {
    var best = x, bd = 0.13;
    K.BEATS.forEach(function (b) { var d = Math.abs(b - x); if (d < bd) { bd = d; best = b; } });
    return best;
  }

  var prepared = false;
  function prepare() {
    if (prepared) return;
    prepared = true;
    K.LINES.forEach(function (ln) {
      var ws = ln.text.split(/\s+/).filter(Boolean);
      var end = Math.min(ln.end && ln.end > ln.t ? ln.end : ln.out, ln.out - 0.15);
      var span = Math.max(0.3, end - ln.t);
      ln.words = ws.map(function (w, i) {
        var at = i === 0 ? ln.t : nearestBeat(ln.t + span * i / ws.length);
        var bare = w.toLowerCase().replace(/[^\p{L}\p{N}']/gu, "");
        return { s: w.replace(/[.,!?;:]+$/, "").toUpperCase(), t: at, hot: HIGH.indexOf(bare) >= 0 };
      });
      for (var i = 1; i < ln.words.length; i++) if (ln.words[i].t <= ln.words[i - 1].t) ln.words[i].t = ln.words[i - 1].t + 0.08;
    });
  }

  function bigWord(line, t) {
    var cur = null, idx = -1;
    line.words.forEach(function (w, i) { if (t >= w.t) { cur = w; idx = i; } });
    if (!cur || t > line.out) return;
    var punch = 1 + 0.07 * (1 - K.eo((t - cur.t) / 0.14));
    var font = K.font("IT", "800", "normal", MAXPX), k = K.fit(g, cur.s, font, -2 * S, W * 0.84);
    var px = MAXPX * k * punch, col = cur.hot || idx === line.words.length - 1 ? ACCENT : IVORY;
    K.text(g, cur.s, W / 2, WORD_Y + px * 0.36, K.font("IT", "800", "normal", px), -2 * S, K.rgba(col, 1));
  }

  function hand(line, t) {
    var font = K.font("LBA", "400", "normal", 74 * S), k = K.fit(g, line.text, font, 0, W * 0.82);
    font = K.font("LBA", "400", "normal", 74 * S * k);
    g.font = font; g.letterSpacing = "0px";
    var tw = g.measureText(line.text).width, x0 = W / 2 - tw / 2;
    var reveal = K.clamp((t - line.t) / Math.max(0.4, (line.out - line.t) * 0.6));
    var a = 1 - K.ss((t - (line.out - 0.2)) / 0.2);
    g.save(); g.beginPath(); g.rect(x0 - 10 * S, HAND_Y - 90 * S, (tw + 20 * S) * reveal, 140 * S); g.clip();
    K.text(g, line.text, x0, HAND_Y, font, 0, K.rgba(IVORY, 0.85 * a), "left");
    g.restore();
    var px = x0 + tw * reveal;
    if (reveal < 1) { g.fillStyle = K.rgba(GOLD, 0.8 * a); g.beginPath(); g.arc(px, HAND_Y - 12 * S, 4 * S, 0, Math.PI * 2); g.fill(); }
  }

  function endCard(t) {
    var a = K.ss((t - K.END) / 0.25) * (1 - K.ss((t - K.EOUT) / 0.5));
    if (a <= 0) return;
    var y = wide ? H * 0.42 : H * 0.36;
    if (T.song) {
      var s = String(T.song).toUpperCase(), f = K.font("IT", "800", "normal", 150 * S), k = K.fit(g, s, f, -2 * S, W * 0.84);
      K.text(g, s, W / 2, y + 60 * S * k, K.font("IT", "800", "normal", 150 * S * k), -2 * S, K.rgba(IVORY, a));
    }
    var hr = K.clamp((t - K.END - 0.3) / 0.8);
    if (T.artist) {
      var af = K.font("LBA", "400", "normal", 84 * S);
      g.font = af; var aw = g.measureText(T.artist).width;
      g.save(); g.beginPath(); g.rect(W / 2 - aw / 2 - 10 * S, y + 90 * S, (aw + 20 * S) * hr, 160 * S); g.clip();
      K.text(g, T.artist, W / 2, y + 190 * S, af, 0, K.rgba(ACCENT, a));
      g.restore();
    }
    if (T.album_line) K.text(g, T.album_line, W / 2, y + 270 * S, K.font("IT", "500", "normal", 26 * S), 8 * S, K.rgba(GOLD, a * hr));
    if (T.release_note) K.text(g, T.release_note, W / 2, y + 330 * S, K.font("IT", "500", "normal", 34 * S), 14 * S, K.rgba(ACCENT, a * hr));
  }

  window.OVERLAY = {
    init: function () { prepare(); },
    render: function (t) {
      prepare();
      g.clearRect(0, 0, W, H); g.fillStyle = "#000"; g.fillRect(0, 0, W, H);
      var line = K.lineAt(t);
      if (line) { bigWord(line, t); hand(line, t); }
      endCard(t);
    },
  };
})();

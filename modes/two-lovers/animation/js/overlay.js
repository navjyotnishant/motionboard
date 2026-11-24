// Motionboard · Two Lovers pack · lyric typography that forms out of fairy dust and blows away,
// a ruby thread that runs the length of the song, and a dusting end card.
// Ported from NAVAAN "Almost Yours" (The Museum of Almosts). Every frame is a pure function of t.
// Required Notice: Copyright (c) 2026 Navjyot Nishant. PolyForm Noncommercial 1.0.0.
(function () {
  var C = window.MB, W = C.width, H = C.height, D = C.duration, MUSIC = C.music_end;
  var T = C.theme || {}, COL = T.colors || {};
  var S = Math.min(W, H) / 1080;
  var cv = document.getElementById("fx"), g = cv.getContext("2d");
  var IVORY = COL.ivory || [243, 236, 224], AMBER = COL.amber || [236, 204, 150];
  var RUBY = COL.ruby || [255, 70, 100], BRASS = COL.brass || [201, 160, 96];
  var MAXW = W * 0.8, Y1 = H * 0.224, Y2 = H * 0.284, YS = H * 0.25, TY = H * 0.7385;
  var CAPS = { w: "500", st: "normal", px: 86 * S, fam: "CG", ls: 12 * S, col: IVORY };
  var LOW = { w: "400", st: "italic", px: 82 * S, fam: "CG", ls: 2 * S, col: AMBER };
  var HIGH = (T.highlight_words || []).map(function (w) { return String(w).toLowerCase(); });
  var SNAP = T.snap_at == null ? -1 : T.snap_at;
  var CUTS = C.cuts || [], DOWN = C.downbeats || [], CHORUS = C.chorus || [0, 0];
  var ROWS = [];

  function words(text, upper) {
    var out = [];
    text.split(/(\s+)/).forEach(function (tok) {
      if (!tok) return;
      var bare = tok.toLowerCase().replace(/[^\p{L}\p{N}']/gu, "");
      var s = upper ? tok.toUpperCase() : tok;
      if (bare && HIGH.indexOf(bare) >= 0) out.push({ s: s, ruby: -1 }); else out.push({ s: s });
    });
    // merge neighbouring plain parts so letter spacing measures stay simple
    var merged = [];
    out.forEach(function (p) {
      var last = merged[merged.length - 1];
      if (last && last.ruby === undefined && p.ruby === undefined) last.s += p.s; else merged.push(p);
    });
    return merged;
  }
  function row(t, out, y, f, parts, extra) {
    var r = { t: t, out: out, y: y, f: f, parts: parts };
    if (extra) for (var k in extra) r[k] = extra[k];
    ROWS.push(r);
    return r;
  }
  function splitLine(text) {
    var ws = text.trim().split(/\s+/);
    if (ws.length < 5) return [text.trim()];
    var target = text.length * 0.45, acc = 0, best = 1, bestD = 1e9;
    for (var i = 1; i < ws.length; i++) {
      acc += ws[i - 1].length + 1;
      var d = Math.abs(acc - target);
      if (d < bestD) { bestD = d; best = i; }
    }
    return [ws.slice(0, best).join(" "), ws.slice(best).join(" ")];
  }

  // End card timing first: lyrics clear before the title forms. No follow or subscribe ask.
  var END = D > 8 ? MUSIC - 2.3 : MUSIC * 0.6, EOUT = D - 1.0;
  (C.lines || []).forEach(function (ln, i, all) {
    var t = ln.start + 0.15, nxt = i + 1 < all.length ? all[i + 1].start : MUSIC;
    if (t > END - 0.9) return;
    var out = Math.max(t + 0.8, Math.min(nxt, MUSIC) - 0.12);
    if (out > END - 0.05) out = END - 0.05;
    var halves = splitLine(ln.text), made = [];
    if (halves.length === 1) made.push(row(t, out, YS, CAPS, words(halves[0], true)));
    else {
      made.push(row(t, out, Y1, CAPS, words(halves[0], true)));
      made.push(row(t + Math.min(1.2, (out - t) * 0.4), out, Y2, LOW, words(halves[1], false)));
    }
    if (SNAP > 0 && SNAP >= t && SNAP <= out + 0.5) made.forEach(function (r) { r.fall = 1; });
  });

  var endLines = [];
  if (T.artist) endLines.push([0, H * 0.245, { w: "500", st: "normal", px: 124 * S, fam: "CG", ls: 30 * S, col: IVORY }, T.artist]);
  if (T.song) endLines.push([0.12, H * 0.318, { w: "400", st: "italic", px: 92 * S, fam: "CG", ls: 2 * S, col: AMBER }, T.song]);
  if (T.album_line) endLines.push([0.24, H * 0.367, { w: "500", st: "normal", px: 31 * S, fam: "JBM", ls: 8 * S, col: BRASS }, T.album_line]);
  if (T.release_note) endLines.push([0.36, H * 0.427, { w: "500", st: "normal", px: 34 * S, fam: "JBM", ls: 16 * S, col: RUBY }, T.release_note]);
  endLines.forEach(function (e) { row(END + e[0], EOUT, e[1], e[2], [{ s: e[3] }], { end: 1 }); });

  var ready = false;
  function hash(n) { var s = Math.sin(n * 127.1 + 311.7) * 43758.5453; return s - Math.floor(s); }
  function clamp01(x) { return x < 0 ? 0 : x > 1 ? 1 : x; }
  function eo(x) { var u = clamp01(x) - 1; return u * u * u + 1; }
  function fontOf(f, px) { return (f.st === "italic" ? "italic " : "") + f.w + " " + px + 'px "' + f.fam + '"'; }

  function init() {
    var OH = Math.round(300 * S), BASE = Math.round(200 * S);
    var off = document.createElement("canvas"); off.width = W; off.height = OH;
    var o = off.getContext("2d", { willReadFrequently: true });
    ROWS.forEach(function (L, li) {
      var full = L.parts.map(function (p) { return p.s; }).join(""), px = L.f.px, ls = L.f.ls;
      o.font = fontOf(L.f, px); o.letterSpacing = ls + "px";
      var w = o.measureText(full).width;
      if (w > MAXW) { var k = MAXW / w; px = Math.floor(px * k); ls = Math.round(ls * k); o.font = fontOf(L.f, px); o.letterSpacing = ls + "px"; w = o.measureText(full).width; }
      L.font = fontOf(L.f, px); L.ls = ls; L.px = px; L.w = w; L.x = Math.round((W - w) / 2);
      var x = L.x; L.parts.forEach(function (p) { p.x = x; x += o.measureText(p.s).width; if (p.ruby === -1) p.ruby = L.t + 0.45; });
      o.clearRect(0, 0, W, OH); o.textBaseline = "alphabetic"; o.fillStyle = "#fff"; o.fillText(full, L.x, BASE);
      var d = o.getImageData(0, 0, W, OH).data, pts = [], step = px < 40 ? 2 : 3;
      for (var yy = 0; yy < OH; yy += step) for (var xx = 0; xx < W; xx += step) if (d[(yy * W + xx) * 4 + 3] > 120) pts.push([xx, yy - BASE + L.y]);
      L.pts = pts.map(function (p, i) {
        var h1 = hash(i * 3.1 + li * 97), h2 = hash(i * 7.7 + li * 31), h3 = hash(i * 1.3 + li * 11);
        var ang = h1 * 6.283, dist = (140 + h2 * 460) * S;
        return { tx: p[0], ty: p[1], sx: p[0] - 180 * S + Math.cos(ang) * dist * 0.7, sy: p[1] + 120 * S + Math.abs(Math.sin(ang)) * dist,
                 d: (p[0] - L.x) / Math.max(1, L.w) * 0.42 + h3 * 0.22, h: h1, k: h2 };
      });
    });
    ready = true;
  }

  function rgba(c, a) { return "rgba(" + c[0] + "," + c[1] + "," + c[2] + "," + a.toFixed(3) + ")"; }
  function star(x, y, r, al, c) {
    g.strokeStyle = rgba(c, al); g.lineWidth = 1.6 * S;
    g.beginPath(); g.moveTo(x - r, y); g.lineTo(x + r, y); g.moveTo(x, y - r); g.lineTo(x, y + r);
    g.moveTo(x - r * 0.4, y - r * 0.4); g.lineTo(x + r * 0.4, y + r * 0.4); g.moveTo(x - r * 0.4, y + r * 0.4); g.lineTo(x + r * 0.4, y - r * 0.4); g.stroke();
  }

  function drawRow(L, li, t) {
    var a = t - L.t; if (a < 0) return;
    var outA = t - L.out, FORM = 0.6, n = L.pts.length;
    if (outA > 2.2) return;
    var textA = clamp01((a - 0.42) / 0.4) * (1 - clamp01(outA / 0.28));
    g.save(); g.globalCompositeOperation = "lighter";
    if (a < 0.95) { // the wand
      var u = clamp01(a / 0.8), hx = L.x - 30 * S + (L.w + 60 * S) * u, hy = L.y - L.px * 0.33 + Math.sin(u * 6.283) * L.px * 0.16, fa = 1 - clamp01((a - 0.75) / 0.2);
      var R0 = 34 * S, gr = g.createRadialGradient(hx, hy, 0, hx, hy, R0);
      gr.addColorStop(0, "rgba(255,244,214," + (0.95 * fa).toFixed(3) + ")"); gr.addColorStop(0.3, "rgba(255,196,120," + (0.5 * fa).toFixed(3) + ")"); gr.addColorStop(1, "rgba(255,150,90,0)");
      g.fillStyle = gr; g.fillRect(hx - R0, hy - R0, 2 * R0, 2 * R0);
      star(hx, hy, 20 * S, 0.9 * fa, [255, 240, 210]);
      for (var j = 0; j < 46; j++) {
        var hj = hash(j * 5.3 + li * 13), kj = hash(j * 9.1 + li * 7), age = hj * 0.45, uu = clamp01((a - age) / 0.8);
        if (a < age) continue;
        var tx = L.x - 30 * S + (L.w + 60 * S) * uu, ty = L.y - L.px * 0.33 + Math.sin(uu * 6.283) * L.px * 0.16 + age * age * 420 * S * (0.4 + kj) + (kj - 0.5) * 22 * S;
        var sa = (1 - age / 0.45) * fa * (0.5 + 0.5 * Math.sin(t * 22 + j)); if (sa <= 0.02) continue;
        var ss = (1.5 + kj * 2.4) * S; g.fillStyle = "rgba(255," + (200 + Math.floor(hj * 50)) + "," + (130 + Math.floor(kj * 80)) + "," + sa.toFixed(3) + ")"; g.fillRect(tx - ss / 2, ty - ss / 2, ss, ss);
      }
    }
    for (var i = 0; i < n; i++) { // dust gathers into letters, rests, then blows away
      var p = L.pts[i]; if (a < p.d) continue;
      var uf = eo((a - p.d) / FORM), x = p.sx + (p.tx - p.sx) * uf, y = p.sy + (p.ty - p.sy) * uf;
      var wob = (1 - uf) * 22 * S; x += Math.sin(a * 5 + p.h * 40) * wob; y += Math.cos(a * 4 + p.k * 40) * wob;
      var al = clamp01((a - p.d) / 0.18) * (0.16 + 0.84 * (1 - clamp01((a - p.d - FORM) / 0.5)));
      al *= 0.62 + 0.38 * Math.sin(t * (3 + p.h * 5) + p.k * 50);
      if (outA > 0) {
        var od = (p.tx - L.x) / Math.max(1, L.w) * 0.3, q = outA - od;
        if (q > 0) {
          var sp = 0.6 + p.h * 0.9;
          if (L.fall) { x += (p.h - 0.5) * 220 * S * q + Math.sin(q * 9 + p.k * 30) * 10 * S; y += (520 + p.k * 620) * S * q * q + (30 + p.h * 90) * S * q; al = (0.95 - 0.2 * p.k) * (1 - clamp01(q / (0.9 + p.k * 0.7))); }
          else { x += (120 + p.k * 260) * S * q * sp + Math.sin(q * 7 + p.h * 30) * 14 * S * q; y -= (40 + p.h * 150) * S * q * sp + 70 * S * q * q;
            al = (0.95 - 0.25 * p.k) * (1 - clamp01(q / (0.55 + p.k * 0.6))); }
        } else { al = Math.max(al, 0.55); }
      }
      if (al <= 0.012) continue;
      var s = (1.5 + p.k * 1.9) * S;
      g.fillStyle = "rgba(255," + (192 + Math.floor(p.h * 52)) + "," + (122 + Math.floor(p.k * 70)) + "," + al.toFixed(3) + ")";
      g.fillRect(x - s / 2, y - s / 2, s, s);
    }
    if (textA > 0.2 && n > 12) {
      for (var w = 0; w < 5; w++) {
        var pp = L.pts[Math.floor(hash(w * 17.3 + li * 3.7) * n)], ph = hash(w * 4.4 + li * 9.9);
        var tw = Math.pow(Math.max(0, Math.sin((t - L.t) * (1.6 + ph * 1.8) + ph * 20)), 6) * textA;
        if (tw > 0.03) star(pp.tx, pp.ty, (7 + ph * 12) * S, tw * 0.9, [255, 238, 205]);
      }
    }
    g.restore();
    if (textA <= 0) return;
    g.save(); g.font = L.font; g.letterSpacing = L.ls + "px"; g.textBaseline = "alphabetic"; g.globalAlpha = textA;
    L.parts.forEach(function (p) {
      var k = p.ruby !== undefined ? clamp01((t - p.ruby) / 0.25) : 0, base = L.f.col;
      var c = [0, 1, 2].map(function (j) { return Math.round(base[j] + (RUBY[j] - base[j]) * k); });
      g.shadowColor = k > 0 ? "rgba(255,60,90," + (0.85 * k).toFixed(2) + ")" : "rgba(255,214,150,0.45)"; g.shadowBlur = (k > 0 ? 34 : 20) * S;
      g.fillStyle = "rgb(" + c.join(",") + ")"; g.fillText(p.s, p.x, L.y);
    });
    g.restore();
  }

  function endRule(t) {
    if (!T.artist) return;
    var a = t - (END + 0.2); if (a < 0) return;
    var al = clamp01(a / 0.4) * (1 - clamp01((t - EOUT) / 0.3)); if (al <= 0) return;
    var w = 300 * S * eo(a / 0.6), y = H * 0.276;
    g.save(); g.strokeStyle = rgba(BRASS, 0.8 * al); g.lineWidth = 1.5 * S; g.beginPath(); g.moveTo(W / 2 - w / 2, y); g.lineTo(W / 2 + w / 2, y); g.stroke(); g.restore();
  }

  function motes(t) {
    var fade = clamp01(t / 1.2) * (1 - clamp01((t - (D - 1.6)) / 1.4)); if (fade <= 0) return;
    g.save(); g.globalCompositeOperation = "lighter";
    for (var i = 0; i < 64; i++) {
      var h = hash(i * 2.7 + 5), k = hash(i * 6.1 + 9), m = hash(i * 9.3 + 2);
      var x = h * W + Math.sin(t * (0.18 + k * 0.25) + m * 30) * 46 * S, y = ((k * H - t * (7 + m * 16) * S) % H + H) % H;
      var al = (0.06 + 0.3 * Math.pow(Math.max(0, Math.sin(t * (0.6 + h * 1.3) + k * 40)), 3)) * fade, r = (1.2 + m * 2.6) * S;
      var gr = g.createRadialGradient(x, y, 0, x, y, r * 3);
      gr.addColorStop(0, "rgba(255,226,170," + al.toFixed(3) + ")"); gr.addColorStop(1, "rgba(255,190,120,0)");
      g.fillStyle = gr; g.fillRect(x - r * 3, y - r * 3, r * 6, r * 6);
    }
    g.restore();
  }

  function lerp(a, b, u) { return a + (b - a) * clamp01(u); }
  var C0 = CHORUS[0] || MUSIC * 0.35, C1 = CHORUS[1] || MUSIC * 0.66, TAUT = SNAP > 0 ? SNAP - 2.44 : MUSIC * 0.73;
  function threadY(x, t) {
    // slack in the verses, pulled tighter through the chorus, taut and trembling before the snap
    var amp = t < C0 ? 44 : t < C1 ? lerp(44, 22, (t - C0) / (C1 - C0)) : t < TAUT ? lerp(22, 9, (t - C1) / Math.max(0.1, TAUT - C1)) : lerp(9, 1.2, (t - TAUT) / 1.9);
    amp *= S;
    var flick = 0; for (var i = 0; i < CUTS.length; i++) { var d = t - CUTS[i]; if (d > 0 && d < 0.7) flick += Math.exp(-d * 6) * Math.sin(d * 26 + x * 0.012) * 16 * S; }
    var trem = SNAP > 0 && t > TAUT ? Math.sin(t * 61 + x * 0.05) * lerp(0, 2.6, (t - TAUT) / 2.2) * S : 0;
    return TY + amp * (Math.sin(x / S * 0.0058 + t * 0.85) * 0.62 + Math.sin(x / S * 0.0127 - t * 1.35 + 1.3) * 0.38) + flick + trem;
  }
  function strokeThread(pts, al) {
    if (pts.length < 2 || al <= 0.01) return;
    g.beginPath(); g.moveTo(pts[0][0], pts[0][1]); for (var i = 1; i < pts.length; i++) g.lineTo(pts[i][0], pts[i][1]);
    g.lineJoin = "round"; g.lineCap = "round";
    g.shadowColor = "rgba(255,40,80," + (0.9 * al).toFixed(3) + ")"; g.shadowBlur = 22 * S; g.strokeStyle = "rgba(213,43,85," + (0.85 * al).toFixed(3) + ")"; g.lineWidth = 3.2 * S; g.stroke();
    g.shadowBlur = 0; g.strokeStyle = "rgba(255,170,190," + (0.8 * al).toFixed(3) + ")"; g.lineWidth = 1.1 * S; g.stroke();
  }
  function thread(t) {
    var stopAt = SNAP > 0 ? SNAP + 1.7 : END + 0.6;
    if (t > stopAt) return;
    g.save(); g.globalCompositeOperation = "lighter";
    var L0 = -30 * S, L1 = W + 30 * S, span = L1 - L0, reveal = eo(t / 2.2) * span + L0, pts = [], x, i;
    if (SNAP < 0 || t < SNAP) {
      var fadeOut = SNAP < 0 ? 1 - clamp01((t - END) / 0.6) : 1;
      for (x = L0; x <= Math.min(L1, reveal); x += 12 * S) pts.push([x, threadY(x, t)]);
      strokeThread(pts, 0.95 * fadeOut);
      for (i = 0; i < DOWN.length; i++) { var d = t - DOWN[i]; if (d < 0 || d > 1.0) continue; // a bead of light on every downbeat
        var bx = L0 + span * d, by = threadY(bx, t), ba = Math.sin(d * 3.1416) * 0.9 * fadeOut; if (bx > reveal) continue;
        var R1 = 26 * S, gr = g.createRadialGradient(bx, by, 0, bx, by, R1); gr.addColorStop(0, "rgba(255,225,230," + ba.toFixed(3) + ")"); gr.addColorStop(0.35, "rgba(255,70,110," + (ba * 0.6).toFixed(3) + ")"); gr.addColorStop(1, "rgba(255,40,80,0)");
        g.fillStyle = gr; g.fillRect(bx - R1, by - R1, 2 * R1, 2 * R1); }
    } else { // the snap: both halves recoil and fall
      var q = t - SNAP, al = 1 - clamp01((q - 0.7) / 0.9), La = [], Ra = [], mid = W / 2;
      for (i = 0; i <= 48; i++) { var s1 = i / 48, x0 = L0 + (mid - L0) * s1, y0 = threadY(x0, SNAP);
        La.push([x0 - 300 * S * (1 - Math.exp(-q * 4)) * s1 * s1, y0 + 950 * S * q * q * Math.pow(s1, 1.5) + Math.sin(q * 19 - s1 * 7) * 34 * S * s1 * Math.exp(-q * 2.2)]);
        var x1 = L1 - (L1 - mid) * s1, y1 = threadY(x1, SNAP);
        Ra.push([x1 + 300 * S * (1 - Math.exp(-q * 4)) * s1 * s1, y1 + 950 * S * q * q * Math.pow(s1, 1.5) + Math.sin(q * 17 - s1 * 6 + 1) * 34 * S * s1 * Math.exp(-q * 2.2)]); }
      strokeThread(La, al); strokeThread(Ra, al);
      for (i = 0; i < 70; i++) { var h = hash(i * 3.3 + 1), k = hash(i * 8.8 + 4), ang = h * 6.283, sp = (120 + k * 520) * S;
        var sx = mid + Math.cos(ang) * sp * q, sy = threadY(mid, SNAP) + Math.sin(ang) * sp * q * 0.7 + 620 * S * q * q, sa = (1 - clamp01(q / (0.5 + k * 0.7))); if (sa <= 0.02) continue;
        g.fillStyle = "rgba(255," + (90 + Math.floor(h * 120)) + "," + (110 + Math.floor(k * 90)) + "," + sa.toFixed(3) + ")"; var ss = (1.6 + k * 2.6) * S; g.fillRect(sx - ss / 2, sy - ss / 2, ss, ss); }
    }
    g.restore();
  }

  function blooms(t) {
    g.save(); g.globalCompositeOperation = "lighter";
    for (var i = 0; i < CUTS.length; i++) { var d = (t - CUTS[i]) / 0.085, a = Math.exp(-d * d) * (CUTS[i] > C0 && CUTS[i] < C1 ? 0.2 : 0.12); if (a < 0.004) continue;
      var gr = g.createRadialGradient(W / 2, H * 0.47, 0, W / 2, H * 0.47, Math.max(W, H) * 0.65); gr.addColorStop(0, "rgba(255,214,160," + a.toFixed(3) + ")"); gr.addColorStop(1, "rgba(255,120,110,0)");
      g.fillStyle = gr; g.fillRect(0, 0, W, H); }
    if (SNAP > 0) {
      var q = t - SNAP; if (q > -0.04 && q < 0.6) { var fa = q < 0 ? (q + 0.04) / 0.04 : Math.exp(-q * 7); g.fillStyle = "rgba(255,226,228," + (0.92 * fa).toFixed(3) + ")"; g.fillRect(0, 0, W, H);
        var g2 = g.createRadialGradient(W / 2, TY, 0, W / 2, TY, 900 * S); g2.addColorStop(0, "rgba(255,60,100," + (0.8 * fa).toFixed(3) + ")"); g2.addColorStop(1, "rgba(255,40,80,0)"); g.fillStyle = g2; g.fillRect(0, 0, W, H); }
    }
    g.restore();
  }

  window.OVERLAY = {
    init: init,
    rows: ROWS,
    render: function (t) {
      g.clearRect(0, 0, W, H); g.fillStyle = "#000"; g.fillRect(0, 0, W, H); if (!ready) return;
      motes(t); thread(t);
      for (var i = 0; i < ROWS.length; i++) drawRow(ROWS[i], i, t);
      endRule(t); blooms(t);
    },
  };
})();

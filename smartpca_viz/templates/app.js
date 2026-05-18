/* smartpca_viz — interactive PCA plot (PCAPlot class) */
/* Inlined into final HTML via Jinja2 template. PAYLOAD injected externally. */

;(function () {
  'use strict';

  /* ================================================================
     Standalone helpers
     ================================================================ */

  function mutedColor(hex) {
    var r = parseInt(hex.slice(1, 3), 16) / 255;
    var g = parseInt(hex.slice(3, 5), 16) / 255;
    var b = parseInt(hex.slice(5, 7), 16) / 255;
    var mx = Math.max(r, g, b), mn = Math.min(r, g, b);
    var h = 0, s = 0, l = (mx + mn) / 2;
    if (mx !== mn) {
      var d = mx - mn;
      s = l > 0.5 ? d / (2 - mx - mn) : d / (mx + mn);
      if (mx === r) h = ((g - b) / d + (g < b ? 6 : 0)) / 6;
      else if (mx === g) h = ((b - r) / d + 2) / 6;
      else h = ((r - g) / d + 4) / 6;
    }
    s = Math.min(s, 0.38);
    l = Math.max(l, 0.75);
    function hue2(p, q, t) {
      if (t < 0) t += 1;
      if (t > 1) t -= 1;
      if (t < 1/6) return p + (q - p) * 6 * t;
      if (t < 1/2) return q;
      if (t < 2/3) return p + (q - p) * (2/3 - t) * 6;
      return p;
    }
    var q = l < 0.5 ? l * (1 + s) : l + s - l * s;
    var p = 2 * l - q;
    var rr = hue2(p, q, h + 1/3);
    var gg = hue2(p, q, h);
    var bb = hue2(p, q, h - 1/3);
    return '#' + [rr, gg, bb].map(function (c) {
      return Math.round(Math.max(0, Math.min(1, c)) * 255)
        .toString(16).padStart(2, '0');
    }).join('');
  }

  function starPoints(cx, cy, r1, r2) {
    var pts = [];
    for (var i = 0; i < 10; i++) {
      var a = -Math.PI / 2 + i * Math.PI / 5;
      var r = i % 2 ? r2 : r1;
      pts.push(cx + Math.cos(a) * r + ',' + (cy + Math.sin(a) * r));
    }
    return pts.join(' ');
  }

  function esc(s) {
    return String(s).replace(/[&<>"]/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c];
    });
  }

  function legendMarkerHtml(symbol, color, target) {
    target = target || false;
    var stroke = target
      ? (PAYLOAD.config.target_outline_color || '#FF0000')
      : color;
    var fill = target
      ? (PAYLOAD.config.target_color || '#FFD400')
      : color;
    var common = 'stroke="' + esc(stroke) + '" stroke-width="'
      + (target ? 2.1 : 1.8) + '" fill="' + esc(fill) + '"';
    var shape;
    if (symbol === 'square') {
      shape = '<rect x="4" y="4" width="8" height="8" ' + common + '/>';
    } else if (symbol === 'triangle') {
      shape = '<polygon points="8,3 3,13 13,13" ' + common + '/>';
    } else if (symbol === 'diamond') {
      shape = '<polygon points="8,2.8 13.2,8 8,13.2 2.8,8" ' + common + '/>';
    } else if (symbol === 'cross') {
      shape = '<path d="M8 3v10M3 8h10" ' + common
        + ' fill="none" stroke-linecap="round"/>';
    } else if (symbol === 'x') {
      shape = '<path d="M4 4l8 8M12 4l-8 8" ' + common
        + ' fill="none" stroke-linecap="round"/>';
    } else if (symbol === 'pentagon') {
      shape = '<polygon points="8,2.8 13,6.5 11,13 5,13 3,6.5" '
        + common + '/>';
    } else if (symbol === 'hexagon') {
      shape = '<polygon points="5,3 11,3 14,8 11,13 5,13 2,8" '
        + common + '/>';
    } else if (symbol === 'star') {
      shape = '<polygon points="8,1.8 9.8,5.8 14,6.1 10.8,8.9 11.8,13 '
        + '8,10.8 4.2,13 5.2,8.9 2,6.1 6.2,5.8" ' + common + '/>';
    } else {
      shape = '<circle cx="8" cy="8" r="5" ' + common + '/>';
    }
    return '<svg class="legendMarker" viewBox="0 0 16 16" aria-hidden="true">'
      + shape + '</svg>';
  }

  function exportLegendMarker(symbol, color, target, cx, cy) {
    var stroke = target
      ? (PAYLOAD.config.target_outline_color || '#FF0000')
      : color;
    var fill = target
      ? (PAYLOAD.config.target_color || '#FFD400')
      : color;
    var sw = target ? 2 : 1.7;
    var common = 'stroke="' + esc(stroke) + '" stroke-width="' + sw
      + '" fill="' + esc(fill) + '"';
    if (symbol === 'square') {
      return '<rect x="' + (cx - 5) + '" y="' + (cy - 5)
        + '" width="10" height="10" ' + common + '/>';
    }
    if (symbol === 'triangle') {
      return '<polygon points="' + cx + ',' + (cy - 6) + ' '
        + (cx - 6) + ',' + (cy + 6) + ' ' + (cx + 6) + ',' + (cy + 6)
        + '" ' + common + '/>';
    }
    if (symbol === 'diamond') {
      return '<polygon points="' + cx + ',' + (cy - 6) + ' '
        + (cx + 6) + ',' + cy + ' ' + cx + ',' + (cy + 6) + ' '
        + (cx - 6) + ',' + cy + '" ' + common + '/>';
    }
    if (symbol === 'cross') {
      return '<path d="M' + cx + ' ' + (cy - 6) + 'v12M' + (cx - 6)
        + ' ' + cy + 'h12" ' + common + ' fill="none" stroke-linecap="round"/>';
    }
    if (symbol === 'x') {
      return '<path d="M' + (cx - 5) + ' ' + (cy - 5) + 'l10 10M'
        + (cx + 5) + ' ' + (cy - 5) + 'l-10 10" ' + common
        + ' fill="none" stroke-linecap="round"/>';
    }
    if (symbol === 'pentagon') {
      return '<polygon points="' + cx + ',' + (cy - 6) + ' '
        + (cx + 6) + ',' + (cy - 2) + ' ' + (cx + 4) + ',' + (cy + 6)
        + ' ' + (cx - 4) + ',' + (cy + 6) + ' ' + (cx - 6) + ',' + (cy - 2)
        + '" ' + common + '/>';
    }
    if (symbol === 'hexagon') {
      return '<polygon points="' + (cx - 5) + ',' + (cy - 6) + ' '
        + (cx + 5) + ',' + (cy - 6) + ' ' + (cx + 7) + ',' + cy + ' '
        + (cx + 5) + ',' + (cy + 6) + ' ' + (cx - 5) + ',' + (cy + 6)
        + ' ' + (cx - 7) + ',' + cy + '" ' + common + '/>';
    }
    if (symbol === 'star') {
      return '<polygon points="' + cx + ',' + (cy - 7) + ' '
        + (cx + 2) + ',' + (cy - 2) + ' ' + (cx + 7) + ',' + (cy - 2)
        + ' ' + (cx + 3) + ',' + (cy + 1) + ' ' + (cx + 5) + ',' + (cy + 7)
        + ' ' + cx + ',' + (cy + 4) + ' ' + (cx - 5) + ',' + (cy + 7)
        + ' ' + (cx - 3) + ',' + (cy + 1) + ' ' + (cx - 7) + ',' + (cy - 2)
        + ' ' + (cx - 2) + ',' + (cy - 2) + '" ' + common + '/>';
    }
    return '<circle cx="' + cx + '" cy="' + cy + '" r="5.5" ' + common + '/>';
  }

  function drawCanvasMarker(ctx, symbol, x, y, r, fill, stroke, alpha, filled) {
    alpha = alpha || 1;
    filled = filled || false;
    ctx.save();
    ctx.globalAlpha = alpha;
    ctx.fillStyle = fill;
    ctx.strokeStyle = stroke;
    ctx.lineWidth = filled ? 1.4 : 1.7;
    ctx.beginPath();
    if (symbol === 'square') {
      ctx.rect(x - r, y - r, 2 * r, 2 * r);
    } else if (symbol === 'triangle') {
      ctx.moveTo(x, y - r);
      ctx.lineTo(x - r, y + r);
      ctx.lineTo(x + r, y + r);
      ctx.closePath();
    } else if (symbol === 'diamond') {
      ctx.moveTo(x, y - r);
      ctx.lineTo(x - r, y);
      ctx.lineTo(x, y + r);
      ctx.lineTo(x + r, y);
      ctx.closePath();
    } else if (symbol === 'cross') {
      ctx.lineWidth = 0.7;
      ctx.moveTo(x, y - r);
      ctx.lineTo(x, y + r);
      ctx.moveTo(x - r, y);
      ctx.lineTo(x + r, y);
    } else if (symbol === 'x') {
      ctx.lineWidth = 0.7;
      ctx.moveTo(x - r, y - r);
      ctx.lineTo(x + r, y + r);
      ctx.moveTo(x + r, y - r);
      ctx.lineTo(x - r, y + r);
    } else if (symbol === 'pentagon' || symbol === 'hexagon' || symbol === 'star') {
      var n = symbol === 'pentagon' ? 5 : (symbol === 'hexagon' ? 6 : 10);
      for (var i = 0; i < n; i++) {
        var outerR = (symbol === 'star') ? r * 1.35 : r;
        var innerR = (symbol === 'star' && (i % 2)) ? r * 0.55 : outerR;
        var ang = -Math.PI / 2 + i * 2 * Math.PI / n;
        var px = x + Math.cos(ang) * innerR;
        var py = y + Math.sin(ang) * innerR;
        if (i) ctx.lineTo(px, py);
        else ctx.moveTo(px, py);
      }
      ctx.closePath();
    } else {
      ctx.arc(x, y, r, 0, Math.PI * 2);
    }
    if (filled || symbol === 'star') ctx.fill();
    ctx.stroke();
    ctx.restore();
  }

  function makePdfFromJpegDataUrl(jpegDataUrl, wPx, hPx) {
    var img = atob(jpegDataUrl.split(',')[1]);
    var imgLen = img.length;
    var pageW = 612, pageH = Math.max(360, pageW * hPx / wPx);
    var objs = [];
    function obj(s) { objs.push(s); return objs.length; }
    obj('<< /Type /Catalog /Pages 2 0 R >>');
    obj('<< /Type /Pages /Kids [3 0 R] /Count 1 >>');
    obj('<< /Type /Page /Parent 2 0 R /MediaBox [0 0 '
      + pageW.toFixed(2) + ' ' + pageH.toFixed(2) + ']'
      + ' /Resources << /XObject << /Im0 4 0 R >> >>'
      + ' /Contents 5 0 R >>');
    obj('<< /Type /XObject /Subtype /Image /Width ' + wPx
      + ' /Height ' + hPx
      + ' /ColorSpace /DeviceRGB /BitsPerComponent 8'
      + ' /Filter /DCTDecode /Length ' + imgLen + ' >>\nstream\n'
      + img + '\nendstream');
    var content = 'q ' + pageW.toFixed(2) + ' 0 0 '
      + pageH.toFixed(2) + ' 0 0 cm /Im0 Do Q';
    obj('<< /Length ' + content.length + ' >>\nstream\n'
      + content + '\nendstream');
    var parts = ['%PDF-1.4\n'];
    var offsets = [0];
    for (var i = 0; i < objs.length; i++) {
      offsets.push(parts.join('').length);
      parts.push((i + 1) + ' 0 obj\n' + objs[i] + '\nendobj\n');
    }
    var xref = parts.join('').length;
    parts.push('xref\n0 ' + (objs.length + 1)
      + '\n0000000000 65535 f \n');
    for (var i = 1; i < offsets.length; i++) {
      parts.push(String(offsets[i]).padStart(10, '0') + ' 00000 n \n');
    }
    parts.push('trailer << /Size ' + (objs.length + 1)
      + ' /Root 1 0 R >>\nstartxref\n' + xref + '\n%%EOF');
    var bytes = new Uint8Array(parts.join('').length);
    var text = parts.join('');
    for (var i = 0; i < text.length; i++) bytes[i] = text.charCodeAt(i) & 255;
    return new Blob([bytes], { type: 'application/pdf' });
  }

  function downloadBlob(name, blob) {
    var a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = name;
    document.body.appendChild(a);
    a.click();
    setTimeout(function () {
      URL.revokeObjectURL(a.href);
      a.remove();
    }, 400);
  }

  function download(name, text, type) {
    downloadBlob(name, new Blob([text], { type: type }));
  }

  /* ================================================================
     PCAPlot class
     ================================================================ */

  function PCAPlot(payload) {
    this.p = payload;                    // short alias throughout
    this.ns = 'http://www.w3.org/2000/svg';
    this.svg = document.getElementById('plot');
    this.tip = document.getElementById('tooltip');

    // Pre-load KDE image for canvas exports
    this._kdeCanvasImg = null;
    if (this.p.kdeImage) {
      var img = new Image();
      img.src = 'data:image/png;base64,' + this.p.kdeImage;
      this._kdeCanvasImg = img;
    }

    this.state = {
      colorBy: this.p.config.color_by || 'group',
      hiddenGroups: new Set(),
      hiddenPops: new Set(),
      highlightGroup: null,
      highlightPop: null,
      selected: new Set(),
      modernBackground: !!this.p.config.modern_background,
      showDensity: false,
      zoomMode: false,
      view: null,
      legendScale: 1,
      pointScale: 1,
      labelMode: 'none'
    };

    // Init UI
    document.getElementById('title').textContent = this.p.project + ' PC1 vs PC2';
    document.getElementById('colorBy').value = this.state.colorBy;

    // Show alpha slider if modern background is on by default
    if (this.state.modernBackground) {
      document.getElementById('modernAlphaRow').style.display = 'grid';
      var alphaVal = this.p.config.modern_background_alpha || 0.35;
      document.getElementById('modernAlpha').value = Math.round(alphaVal * 100);
      document.getElementById('modernAlphaValue').textContent = alphaVal.toFixed(2);
    }

    // Build initial view
    this.state.view = this._ext();

    // Bind events
    this._bindEvents();

    // Initial render
    this._controls();
    this.draw();
    window.addEventListener('resize', this._safeDraw.bind(this));
  }

  /* ---------------------------------------------------------------
     Error boundary
     --------------------------------------------------------------- */

  PCAPlot.prototype._safeDraw = function () {
    try { this.draw(); } catch (e) {
      console.error('PCAPlot draw error:', e);
      this._showError(e.message);
    }
  };

  PCAPlot.prototype._safe = function (fn) {
    var self = this;
    return function () {
      try { return fn.apply(self, arguments); } catch (e) {
        console.error('PCAPlot error:', e);
        self._showError(e.message);
      }
    };
  };

  PCAPlot.prototype._showError = function (msg) {
    var div = document.getElementById('pca-error');
    if (!div) {
      div = document.createElement('div');
      div.id = 'pca-error';
      div.style.cssText = 'position:fixed;bottom:16px;right:16px;'
        + 'background:#e74c3c;color:white;padding:8px 14px;'
        + 'border-radius:6px;font-size:13px;z-index:9999;'
        + 'display:none;max-width:400px';
      document.body.appendChild(div);
    }
    div.textContent = 'Error: ' + msg;
    div.style.display = 'block';
    setTimeout(function () { div.style.display = 'none'; }, 5000);
  };

  /* ---------------------------------------------------------------
     View math
     --------------------------------------------------------------- */

  PCAPlot.prototype._ext = function (points) {
    points = points || this.p.points;
    var xs = points.map(function (p) { return +p.PC1; });
    var ys = points.map(function (p) { return +p.PC2; });
    var minX = Math.min.apply(null, xs);
    var maxX = Math.max.apply(null, xs);
    var minY = Math.min.apply(null, ys);
    var maxY = Math.max.apply(null, ys);
    var dx = (maxX - minX) || 1e-9;
    var dy = (maxY - minY) || 1e-9;
    return {
      minX: minX - dx * 0.06,
      maxX: maxX + dx * 0.06,
      minY: minY - dy * 0.06,
      maxY: maxY + dy * 0.06
    };
  };

  PCAPlot.prototype._plotFrame = function () {
    var w = this.svg.clientWidth || 900;
    var h = this.svg.clientHeight || 650;
    var side = w >= 1050 ? 270 : Math.max(92, Math.min(170, w * 0.16));
    var top = h >= 720 ? 118 : 86;
    var bottom = h >= 720 ? 170 : 128;
    var left = side, right = w - side;
    var ytop = top, ybot = h - bottom;
    if (right - left < 360) { left = 78; right = w - 52; }
    if (ybot - ytop < 280) { ytop = 48; ybot = h - 64; }
    var cx = (left + right) / 2, cy = (ytop + ybot) / 2;
    var pw = (right - left);
    var ph = (ybot - ytop);
    left = cx - pw / 2;
    right = cx + pw / 2;
    ytop = cy - ph / 2;
    ybot = cy + ph / 2;
    return { w: w, h: h, left: left, right: right, top: ytop, bottom: ybot };
  };

  PCAPlot.prototype._sx = function (x) {
    var f = this._plotFrame();
    return f.left + (x - this.state.view.minX)
      / (this.state.view.maxX - this.state.view.minX)
      * (f.right - f.left);
  };

  PCAPlot.prototype._sy = function (y) {
    var f = this._plotFrame();
    return f.bottom - (y - this.state.view.minY)
      / (this.state.view.maxY - this.state.view.minY)
      * (f.bottom - f.top);
  };

  PCAPlot.prototype._invSx = function (x) {
    var f = this._plotFrame();
    return this.state.view.minX + (x - f.left) / (f.right - f.left)
      * (this.state.view.maxX - this.state.view.minX);
  };

  PCAPlot.prototype._invSy = function (y) {
    var f = this._plotFrame();
    return this.state.view.maxY - (y - f.top) / (f.bottom - f.top)
      * (this.state.view.maxY - this.state.view.minY);
  };

  /* ---------------------------------------------------------------
     Rendering helpers
     --------------------------------------------------------------- */

  PCAPlot.prototype._color = function (p) {
    if (p.is_target) return this.p.config.target_color || '#FFD400';
    if (this.state.modernBackground && p.is_modern_background) {
      var src = this.state.colorBy === 'population'
        ? p.population_color : p.group_color;
      return mutedColor(src);
    }
    return this.state.colorBy === 'population'
      ? p.population_color : p.group_color;
  };

  PCAPlot.prototype._alpha = function (p) {
    if (this.state.modernBackground && p.is_modern_background && !p.is_target) {
      return this.p.config.modern_background_alpha || 0.35;
    }
    return p.is_target ? 1 : 0.92;
  };

  PCAPlot.prototype._visible = function (p) {
    return !this.state.hiddenGroups.has(p.group)
      && !this.state.hiddenPops.has(p.population);
  };

  PCAPlot.prototype._dim = function (p) {
    if (this.state.highlightGroup && p.group !== this.state.highlightGroup) return true;
    if (this.state.highlightPop && p.population !== this.state.highlightPop) return true;
    return false;
  };

  PCAPlot.prototype._clear = function () {
    while (this.svg.firstChild) this.svg.removeChild(this.svg.firstChild);
  };

  PCAPlot.prototype._el = function (name, attrs) {
    var e = document.createElementNS(this.ns, name);
    if (attrs) {
      for (var k in attrs) {
        if (attrs.hasOwnProperty(k)) e.setAttribute(k, attrs[k]);
      }
    }
    return e;
  };

  PCAPlot.prototype._marker = function (p, x, y, r) {
    var c = this._color(p);
    var a = this._dim(p) ? 0.12 : this._alpha(p);
    var g = this._el('g', {});
    var shape = p.is_target ? 'star' : p.symbol;
    var attrs = {
      fill: c,
      stroke: p.is_target
        ? (this.p.config.target_outline_color || '#FF0000')
        : c,
      'stroke-width': p.is_target ? 1.4 : 0.5,
      opacity: a
    };
    if (shape === 'square') {
      g.appendChild(this._el('rect', {
        x: x - r, y: y - r, width: 2 * r, height: 2 * r
      }));
      // Apply attrs to the child element
      for (var k in attrs) g.lastChild.setAttribute(k, attrs[k]);
    } else if (shape === 'triangle') {
      var tri = this._el('polygon', {
        points: x + ',' + (y - r) + ' ' + (x - r) + ',' + (y + r)
          + ' ' + (x + r) + ',' + (y + r)
      });
      for (var k in attrs) tri.setAttribute(k, attrs[k]);
      g.appendChild(tri);
    } else if (shape === 'diamond') {
      var dia = this._el('polygon', {
        points: x + ',' + (y - r) + ' ' + (x - r) + ',' + y + ' '
          + x + ',' + (y + r) + ' ' + (x + r) + ',' + y
      });
      for (var k in attrs) dia.setAttribute(k, attrs[k]);
      g.appendChild(dia);
    } else if (shape === 'star') {
      var star = this._el('polygon', {
        points: starPoints(x, y, r * 1.35, r * 0.55)
      });
      for (var k in attrs) star.setAttribute(k, attrs[k]);
      g.appendChild(star);
    } else if (shape === 'cross') {
      var path = this._el('path', {
        d: 'M' + x + ',' + (y - r) + 'L' + x + ',' + (y + r)
          + 'M' + (x - r) + ',' + y + 'L' + (x + r) + ',' + y,
        fill: 'none', stroke: c, 'stroke-width': 0.7, opacity: a
      });
      g.appendChild(path);
    } else if (shape === 'x') {
      var xpath = this._el('path', {
        d: 'M' + (x - r) + ',' + (y - r) + 'L' + (x + r) + ',' + (y + r)
          + 'M' + (x + r) + ',' + (y - r) + 'L' + (x - r) + ',' + (y + r),
        fill: 'none', stroke: c, 'stroke-width': 0.7, opacity: a
      });
      g.appendChild(xpath);
    } else {
      var circ = this._el('circle', { cx: x, cy: y, r: r });
      for (var k in attrs) circ.setAttribute(k, attrs[k]);
      g.appendChild(circ);
    }
    return g;
  };

  PCAPlot.prototype._pointRadius = function (p) {
    var base = (this.p.config.point_size || 5) * this.state.pointScale;
    if (this.state.modernBackground && p.is_modern_background) {
      return base * (this.p.config.modern_background_size_multiplier || 3.0);
    }
    return base;
  };

  PCAPlot.prototype._targetRadius = function () {
    return (this.p.config.point_size || 5) * this.state.pointScale
      * (this.p.config.target_size_multiplier || 1.8);
  };

  PCAPlot.prototype._pointLabel = function (p) {
    if (this.state.labelMode === 'group') return p.group;
    if (this.state.labelMode === 'sample_id') return p.sample_id;
    if (this.state.labelMode === 'population') return p.population;
    return '';
  };

  PCAPlot.prototype._bindTooltip = function (node, p) {
    var self = this;
    node.addEventListener('mousemove', function (ev) {
      self.tip.style.display = 'block';
      self.tip.style.left = (ev.clientX + 12) + 'px';
      self.tip.style.top = (ev.clientY + 12) + 'px';
      self.tip.innerHTML = '<b>' + esc(p.sample_id) + '</b><br>'
        + 'population: ' + esc(p.population) + '<br>'
        + 'group: ' + esc(p.group) + '<br>'
        + 'PC1: ' + (+p.PC1).toFixed(5) + '<br>'
        + 'PC2: ' + (+p.PC2).toFixed(5);
    });
    node.addEventListener('mouseleave', function () {
      self.tip.style.display = 'none';
    });
    node.addEventListener('click', function () {
      self.state.selected = new Set([p.idx]);
      self.draw();
    });
  };

  /* ---------------------------------------------------------------
     Main draw
     --------------------------------------------------------------- */

  PCAPlot.prototype.draw = function () {
    this._clear();
    var f = this._plotFrame();
    var w = this.svg.clientWidth || 900;
    var h = this.svg.clientHeight || 650;
    this.svg.setAttribute('viewBox', '0 0 ' + w + ' ' + h);

    // White background
    this.svg.appendChild(this._el('rect', {
      x: 0, y: 0, width: w, height: h, fill: 'white'
    }));

    // KDE heatmap overlay
    if (this.state.showDensity && this.p.kdeImage) {
      this.svg.appendChild(this._el('image', {
        href: 'data:image/png;base64,' + this.p.kdeImage,
        x: f.left, y: f.top,
        width: f.right - f.left, height: f.bottom - f.top,
        preserveAspectRatio: 'none'
      }));
    }

    // Plot border
    this.svg.appendChild(this._el('rect', {
      x: f.left, y: f.top,
      width: f.right - f.left, height: f.bottom - f.top,
      fill: 'none', stroke: '#1b252e', 'stroke-width': 1
    }));

    // X axis label
    var xl = this._el('text', {
      x: (f.left + f.right) / 2, y: f.bottom + 38,
      'text-anchor': 'middle', 'font-family': 'Arial,Helvetica,sans-serif',
      'font-size': 13, fill: '#1b252e'
    });
    xl.textContent = this.p.xLabel;
    this.svg.appendChild(xl);

    // Y axis label
    var yl = this._el('text', {
      x: f.left - 48, y: (f.top + f.bottom) / 2,
      'text-anchor': 'middle', 'font-family': 'Arial,Helvetica,sans-serif',
      'font-size': 13, fill: '#1b252e',
      transform: 'rotate(-90 ' + (f.left - 48) + ' ' + ((f.top + f.bottom) / 2) + ')'
    });
    yl.textContent = this.p.yLabel;
    this.svg.appendChild(yl);

    var self = this;

    // Layer 1: Modern background text labels
    if (this.state.modernBackground) {
      this.p.points.forEach(function (p) {
        if (!p.is_modern_background || p.is_target) return;
        if (!self._visible(p)) return;
        var x = self._sx(+p.PC1);
        var y = self._sy(+p.PC2);
        var r = self._pointRadius(p);
        var t = self._el('text', {
          x: x, y: y,
          'text-anchor': 'middle', 'dominant-baseline': 'central',
          'font-family': 'Arial,Helvetica,sans-serif',
          'font-size': Math.max(11, Math.min(18, r * 0.8)),
          fill: self._color(p),
          opacity: self._alpha(p)
        });
        t.textContent = p.group;
        self._bindTooltip(t, p);
        self.svg.appendChild(t);
      });
    }

    // Layer 2: Non-target, non-modern points
    this.p.points.forEach(function (p) {
      if (p.is_target) return;
      if (self.state.modernBackground && p.is_modern_background) return;
      if (!self._visible(p)) return;
      var x = self._sx(+p.PC1);
      var y = self._sy(+p.PC2);
      var r = self._pointRadius(p);
      var m = self._marker(p, x, y, r);
      self._bindTooltip(m, p);
      self.svg.appendChild(m);
      self._drawPointLabelSvg(p, x, y, r, false);
    });

    // Layer 3: Target points
    this.p.points.forEach(function (p) {
      if (!p.is_target) return;
      if (!self._visible(p)) return;
      var x = self._sx(+p.PC1);
      var y = self._sy(+p.PC2);
      var r = self._targetRadius();
      var m = self._marker(p, x, y, r);
      self._bindTooltip(m, p);
      self.svg.appendChild(m);
      if (self.p.config.label_targets) {
        var t = self._el('text', {
          x: x + 9, y: y - 9,
          'font-family': 'Arial,Helvetica,sans-serif',
          'font-size': 12, 'font-weight': '700', fill: '#111'
        });
        t.textContent = p.target_label || p.sample_id;
        self.svg.appendChild(t);
      }
      self._drawPointLabelSvg(p, x, y, r, true);
    });

    // Selection circles
    if (this.state.selected.size) {
      var selArr = Array.from(this.state.selected);
      selArr.forEach(function (idx) {
        var p = self.p.points[idx];
        if (!self._visible(p)) return;
        self.svg.appendChild(self._el('circle', {
          cx: self._sx(+p.PC1), cy: self._sy(+p.PC2),
          r: 10, fill: 'none', stroke: '#111', 'stroke-width': 1.5
        }));
      });
    }

    this._drawLegend();
    this._updateSelected();
  };

  PCAPlot.prototype._drawPointLabelSvg = function (p, x, y, r, isTarget) {
    var label = this._pointLabel(p);
    if (!label) return;
    var t = this._el('text', {
      x: x + r + 4, y: y + 4,
      'font-family': 'Arial,Helvetica,sans-serif',
      'font-size': 10,
      fill: this._color(p),
      opacity: this._dim(p) ? 0.2 : 0.95
    });
    t.textContent = label;
    this.svg.appendChild(t);
  };

  /* ---------------------------------------------------------------
     Legend rendering
     --------------------------------------------------------------- */

  PCAPlot.prototype._drawLegend = function () {
    var layer = document.getElementById('legend');
    if (layer.dataset.ready === '1') return;

    var self = this;
    var blocks = [];

    // Target block
    var targetRows = this.p.points.filter(function (p) { return p.is_target; });
    if (targetRows.length) {
      blocks.push({
        group: 'Target',
        color: this.p.config.target_color || '#FFD400',
        target: true,
        populations: Array.from(new Set(targetRows.map(function (p) { return p.population; }))).map(function (pop) {
          return { population: pop, symbol: self.p.config.target_shape || 'star' };
        })
      });
    }

    // Group blocks
    (this.p.groupedPopulationLegend || []).forEach(function (g) {
      if (self.state.modernBackground
        && (self.p.config.modern_groups || []).indexOf(g.group) !== -1) {
        blocks.push({
          group: g.group,
          color: self.p.groupColors[g.group] || '#999',
          target: false,
          populations: g.populations,
          modernBg: true
        });
        return;
      }
      blocks.push({
        group: g.group,
        color: self.p.groupColors[g.group] || '#999',
        target: false,
        populations: g.populations
      });
    });

    var f = this._plotFrame();
    var rowGap = 8;

    var lanes = [
      { side: 'top', x: f.left, y: 12, max: f.right, step: 'x' },
      { side: 'right', x: f.right + 18, y: f.top, max: f.bottom, step: 'y' },
      { side: 'bottom', x: f.left, y: f.bottom + 54, max: f.right, step: 'x' },
      { side: 'left', x: 12, y: f.top, max: f.bottom, step: 'y' }
    ];

    blocks.forEach(function (g) {
      var panel = document.createElement('div');
      panel.className = 'legendPanel';
      panel.dataset.group = g.group;
      panel.dataset.color = g.color;
      panel.dataset.target = g.target ? '1' : '0';
      panel.dataset.populations = JSON.stringify(g.populations);
      panel.dataset.modernBg = g.modernBg ? '1' : '0';

      var bgAlpha = self.p.config.modern_background_alpha || 0.35;
      var title = g.group + (g.modernBg ? ' (bg)' : '');
      var mutedCol = g.modernBg ? mutedColor(g.color) : g.color;
      var markerStyle = g.modernBg
        ? '<span class="swatch" style="background:' + mutedCol + ';opacity:' + bgAlpha + '"></span>'
        : '<span class="swatch" style="background:' + g.color + '"></span>';
      var titleMarker = g.target
        ? legendMarkerHtml(self.p.config.target_shape || 'star', self.p.config.target_color || '#FFD400', true)
        : markerStyle;
      var titleOpacity = g.modernBg ? bgAlpha : 1;
      var popItems = g.modernBg
        ? ''
        : g.populations.map(function (p) {
            return '<div class="item" style="opacity:' + titleOpacity + '">'
              + legendMarkerHtml(p.symbol, g.color, g.target)
              + '<span>' + esc(p.population) + '</span></div>';
          }).join('');

      panel.innerHTML = '<div class="legendTitle" style="opacity:' + titleOpacity + '">'
        + titleMarker + '<span class="legend-group-label" style="margin-left:4px;cursor:pointer">' + esc(title) + '</span></div>'
        + popItems;

      // Click group name in legend → highlight
      var titleSpan = panel.querySelector('.legend-group-label');
      if (titleSpan) {
        titleSpan.onclick = function () {
          self.state.highlightGroup = self.state.highlightGroup === g.group ? null : g.group;
          self.state.highlightPop = null;
          self.draw();
        };
      }

      layer.appendChild(panel);
      applyLegendScale(panel);

      var lane = chooseLegendLane(lanes, panel);
      panel.style.left = lane.x + 'px';
      panel.style.top = lane.y + 'px';
      advanceLegendLane(lane, panel, rowGap);
      makeDraggable(panel);
    });

    layer.dataset.ready = '1';
  };

  function scaledPanelWidth(panel) {
    return panel.offsetWidth * window.__legendScale || 1;
  }
  function scaledPanelHeight(panel) {
    return panel.offsetHeight * window.__legendScale || 1;
  }
  function chooseLegendLane(lanes, panel) {
    var candidates = lanes.filter(function (l) {
      if (l.step === 'x') return l.x + scaledPanelWidth(panel) <= l.max;
      return l.y + scaledPanelHeight(panel) <= l.max;
    });
    if (!candidates.length) candidates = lanes;
    return candidates.reduce(function (best, l) {
      return (l.step === 'x' ? l.x : l.y)
        < (best.step === 'x' ? best.x : best.y) ? l : best;
    });
  }
  function advanceLegendLane(lane, panel, gap) {
    if (lane.step === 'x') lane.x += scaledPanelWidth(panel) + gap;
    else lane.y += scaledPanelHeight(panel) + gap;
  }
  function applyLegendScale(panel) {
    panel.style.transformOrigin = 'top left';
    panel.style.transform = 'scale(' + window.__legendScale + ')';
  }
  function applyLegendScaleAll() {
    document.querySelectorAll('.legendPanel').forEach(applyLegendScale);
  }
  function resetLegendLayout() {
    var layer = document.getElementById('legend');
    layer.innerHTML = '';
    layer.dataset.ready = '';
    window.plot && window.plot._drawLegend();
  }
  function makeDraggable(elm) {
    elm.onmousedown = function (e) {
      var d = {
        x: e.clientX - elm.offsetLeft,
        y: e.clientY - elm.offsetTop
      };
      e.preventDefault();
      e.stopPropagation();
      document.onmousemove = function (ev) {
        elm.style.left = (ev.clientX - d.x) + 'px';
        elm.style.top = (ev.clientY - d.y) + 'px';
      };
      document.onmouseup = function () {
        document.onmousemove = null;
        document.onmouseup = null;
      };
    };
  }

  /* ---------------------------------------------------------------
     Control panel / event binding
     --------------------------------------------------------------- */

  PCAPlot.prototype._controls = function () {
    var self = this;

    // Groups list
    var gd = document.getElementById('groups');
    gd.innerHTML = '';
    this.p.groups.forEach(function (g) {
      var d = document.createElement('div');
      d.className = 'item';
      d.innerHTML = '<input type="checkbox" checked data-group="' + esc(g) + '">'
        + '<span class="swatch" style="background:'
        + (self.p.groupColors[g] || '#999') + '"></span>'
        + '<span>' + esc(g) + '</span>';
      d.querySelector('input').onchange = function (e) {
        if (e.target.checked) self.state.hiddenGroups.delete(g);
        else self.state.hiddenGroups.add(g);
        self.draw();
      };
      d.querySelector('span:last-child').onclick = function () {
        self.state.highlightGroup = self.state.highlightGroup === g ? null : g;
        self.state.highlightPop = null;
        self.draw();
      };
      gd.appendChild(d);
    });

    // Populations list
    var pd = document.getElementById('populations');
    pd.innerHTML = '';
    this.p.populations.forEach(function (p) {
      var d = document.createElement('div');
      d.className = 'item';
      d.innerHTML = '<input type="checkbox" checked data-pop="' + esc(p) + '">'
        + '<span class="swatch" style="background:'
        + (self.p.populationColors[p] || '#999') + '"></span>'
        + '<span>' + esc(p) + '</span>';
      d.querySelector('input').onchange = function (e) {
        if (e.target.checked) self.state.hiddenPops.delete(p);
        else self.state.hiddenPops.add(p);
        self.draw();
      };
      d.querySelector('span:last-child').onclick = function () {
        self.state.highlightPop = self.state.highlightPop === p ? null : p;
        self.state.highlightGroup = null;
        self.draw();
      };
      pd.appendChild(d);
    });
  };

  PCAPlot.prototype._focus = function (points) {
    if (points.length) {
      this.state.view = this._ext(points);
      this.draw();
    }
  };

  PCAPlot.prototype._updateSelected = function () {
    var rows = [];
    var self = this;
    this.state.selected.forEach(function (i) {
      rows.push(self.p.points[i]);
    });
    document.getElementById('selected').textContent = rows.map(function (p) {
      return p.sample_id + '\t' + p.population + '\t' + p.group
        + '\t' + p.PC1 + '\t' + p.PC2;
    }).join('\n');
    this._updateStatusBar();
  };

  PCAPlot.prototype._bindEvents = function () {
    var self = this;

    // ── Button handlers ──
    document.getElementById('colorBy').onchange = function (e) {
      self.state.colorBy = e.target.value;
      self.draw();
    };

    document.getElementById('focusTargets').onclick = self._safe(function () {
      self._focus(self.p.points.filter(function (p) { return p.is_target; }));
    });

    document.getElementById('resetView').onclick = self._safe(function () {
      self.state.view = self._ext();
      self.state.highlightGroup = null;
      self.state.highlightPop = null;
      self.state.selected.clear();
      self.state.zoomMode = false;
      document.getElementById('toggleZoom').classList.remove('zoomActive');
      self.svg.style.cursor = '';
      document.getElementById('searchBox').value = '';
      document.getElementById('searchMsg').textContent = '';
      self.draw();
    });

    document.getElementById('toggleZoom').onclick = self._safe(function () {
      self.state.zoomMode = !self.state.zoomMode;
      document.getElementById('toggleZoom').classList.toggle(
        'zoomActive', self.state.zoomMode
      );
      self.svg.style.cursor = self.state.zoomMode ? 'crosshair' : '';
      self.draw();
    });

    // ── Toggle: Modern as background ──
    document.getElementById('toggleModern').onclick = self._safe(function () {
      self.state.modernBackground = !self.state.modernBackground;
      var row = document.getElementById('modernAlphaRow');
      row.style.display = self.state.modernBackground ? 'grid' : 'none';
      // Rebuild legend to reflect modern bg state
      var legendLayer = document.getElementById('legend');
      legendLayer.innerHTML = '';
      legendLayer.dataset.ready = '';
      self.draw();
    });

    // ── Slider: Modern background alpha ──
    document.getElementById('modernAlpha').oninput = self._safe(function () {
      var slider = document.getElementById('modernAlpha');
      var v = parseInt(slider.value, 10) / 100;
      self.p.config.modern_background_alpha = v;
      document.getElementById('modernAlphaValue').textContent = v.toFixed(2);
      // Update legend panel alphas in-place (preserve drag positions)
      document.querySelectorAll('#legend .legendPanel[data-modern-bg="1"]').forEach(function (p) {
        var swatch = p.querySelector('.swatch');
        if (swatch) swatch.style.opacity = v;
        var title = p.querySelector('.legendTitle');
        if (title) title.style.opacity = v;
        var items = p.querySelectorAll('.item');
        items.forEach(function (item) { item.style.opacity = v; });
      });
      self.draw();
    });

    // ── Toggle: Density heatmap ──
    document.getElementById('toggleDensity').onclick = self._safe(function () {
      self.state.showDensity = !self.state.showDensity;
      self.draw();
    });

    // ── Search (fuzzy match by sample_id, population, group) ──
    document.getElementById('searchBtn').onclick = self._safe(function () {
      var q = document.getElementById('searchBox').value.trim().toLowerCase();
      if (!q) { document.getElementById('searchMsg').textContent = ''; return; }
      var matches = [];
      self.p.points.forEach(function (p) {
        if (p.sample_id.toLowerCase().indexOf(q) !== -1
          || p.population.toLowerCase().indexOf(q) !== -1
          || p.group.toLowerCase().indexOf(q) !== -1) {
          matches.push(p.idx);
        }
      });
      if (matches.length === 1) {
        document.getElementById('searchMsg').textContent = 'Found: ' + self.p.points[matches[0]].sample_id;
        self.state.selected = new Set(matches);
      } else if (matches.length > 1) {
        document.getElementById('searchMsg').textContent = 'Found ' + matches.length + ' matches';
        self.state.selected = new Set(matches);
      } else {
        document.getElementById('searchMsg').textContent = 'Not found: ' + q;
        self.state.selected.clear();
      }
      self.draw();
    });

    document.getElementById('legendScale').oninput = function (e) {
      var s = (+e.target.value) / 100;
      self.state.legendScale = s;
      window.__legendScale = s;
      document.getElementById('legendScaleValue').textContent = e.target.value + '%';
      applyLegendScaleAll();
    };

    document.getElementById('pointScale').oninput = function (e) {
      self.state.pointScale = (+e.target.value) / 100;
      document.getElementById('pointScaleValue').textContent = e.target.value + '%';
      self.draw();
    };

    document.getElementById('labelMode').onchange = function (e) {
      self.state.labelMode = e.target.value;
      self.draw();
    };

    document.getElementById('resetLegendLayout').onclick = resetLegendLayout;

    // ── Export buttons ──
    document.getElementById('exportSvg').onclick = self._safe(function () {
      download(
        self.p.project + '_current_layout.svg',
        self._currentLayoutSvgString(),
        'image/svg+xml'
      );
    });

    document.getElementById('exportPng').onclick = self._safe(async function () {
      try {
        var r = await self._renderLayoutToCanvas(2);
        r.canvas.toBlob(function (b) {
          if (!b) { alert('PNG export failed.'); return; }
          downloadBlob(self.p.project + '_current_layout.png', b);
        }, 'image/png');
      } catch (e) {
        alert('PNG export failed: ' + e.message);
      }
    });

    document.getElementById('exportPdf').onclick = self._safe(
      self._exportCurrentLayoutPdf.bind(self)
    );

    document.getElementById('previewLayout').onclick = self._safe(function () {
      var s = self._currentLayoutSvgString();
      var win = window.open('', '_blank');
      if (win) {
        win.document.write(
          '<!doctype html><html><head>'
          + '<title>' + esc(self.p.project) + ' current layout preview</title>'
          + '<style>body{margin:0;background:#f4f6f8;padding:16px;box-sizing:border-box}'
          + 'svg{background:white;max-width:100%;height:auto;display:block;margin:auto;'
          + 'box-shadow:0 2px 14px rgba(25,35,45,.16)}</style></head><body>' + s
          + '</body></html>'
        );
        win.document.close();
      } else {
        download(self.p.project + '_current_layout.svg', s, 'image/svg+xml');
      }
    });

    document.getElementById('exportSelected').onclick = self._safe(function () {
      var rows = [];
      self.state.selected.forEach(function (i) {
        rows.push(self.p.points[i]);
      });
      var csv = 'sample_id,population,group,PC1,PC2\n'
        + rows.map(function (p) {
            return [p.sample_id, p.population, p.group, p.PC1, p.PC2]
              .map(function (v) {
                return '"' + String(v).replaceAll('"', '""') + '"';
              }).join(',');
          }).join('\n');
      download(self.p.project + '_selected.csv', csv, 'text/csv');
    });

    // ── SVG drag (box-select / zoom) ──
    var drag = null;
    this.svg.addEventListener('mousedown', function (ev) {
      if (ev.button !== 0) return;
      var r = self.svg.getBoundingClientRect();
      drag = {
        x0: ev.clientX - r.left,
        y0: ev.clientY - r.top,
        rect: self._el('rect', {
          fill: 'rgba(20,90,160,.12)',
          stroke: '#145aa0',
          'stroke-width': 1
        })
      };
      self.svg.appendChild(drag.rect);
    });

    this.svg.addEventListener('mousemove', function (ev) {
      if (!drag) return;
      var r = self.svg.getBoundingClientRect();
      var x = ev.clientX - r.left;
      var y = ev.clientY - r.top;
      drag.rect.setAttribute('x', Math.min(x, drag.x0));
      drag.rect.setAttribute('y', Math.min(y, drag.y0));
      drag.rect.setAttribute('width', Math.abs(x - drag.x0));
      drag.rect.setAttribute('height', Math.abs(y - drag.y0));
    });

    this.svg.addEventListener('mouseup', function (ev) {
      if (!drag) return;
      var r = self.svg.getBoundingClientRect();
      var x = ev.clientX - r.left;
      var y = ev.clientY - r.top;
      var x1 = Math.min(x, drag.x0), x2 = Math.max(x, drag.x0);
      var y1 = Math.min(y, drag.y0), y2 = Math.max(y, drag.y0);
      drag = null;

      if (self.state.zoomMode) {
        var zx1 = self._invSx(x1), zx2 = self._invSx(x2);
        var zy1 = self._invSy(y2), zy2 = self._invSy(y1);
        var dx = zx2 - zx1 || 1e-9, dy = zy2 - zy1 || 1e-9;
        self.state.view = {
          minX: zx1 - dx * 0.06, maxX: zx2 + dx * 0.06,
          minY: zy1 - dy * 0.06, maxY: zy2 + dy * 0.06
        };
        self.state.selected.clear();
        self.draw();
        return;
      }

      self.state.selected = new Set();
      self.p.points.forEach(function (p) {
        var px = self._sx(+p.PC1), py = self._sy(+p.PC2);
        if (px >= x1 && px <= x2 && py >= y1 && py <= y2 && self._visible(p)) {
          self.state.selected.add(p.idx);
        }
      });
      self.draw();
    });

    // ── Double-click zoom out ──
    this.svg.addEventListener('dblclick', function () {
      self.state.view = self._ext();
      self.state.selected.clear();
      self.draw();
    });

    // ── Space+drag pan ──
    var panState = null;
    this.svg.addEventListener('mousedown', function (ev) {
      if (ev.button !== 0) return;
      // Space key pressed → pan mode
      if (ev.target && ev.target.id === 'plot' && (ev.target === document.activeElement || !document.activeElement || document.activeElement.tagName !== 'INPUT')) {
        // Check space key via ev.originalEvent or key state
      }
    });
    // Track space key state
    this._spaceDown = false;
    document.addEventListener('keydown', function (ev) {
      if (ev.code === 'Space' && ev.target.tagName !== 'INPUT' && ev.target.tagName !== 'TEXTAREA') {
        self._spaceDown = true;
        ev.preventDefault();
        self.svg.style.cursor = 'grab';
      }
    });
    document.addEventListener('keyup', function (ev) {
      if (ev.code === 'Space') {
        self._spaceDown = false;
        if (!self.state.zoomMode) self.svg.style.cursor = '';
        panState = null;
      }
    });
    // Override existing mousedown to support pan
    // We'll store the original handlers and wrap them
    // Actually, let's just add a separate handler that runs first
    this.svg.addEventListener('mousedown', function (ev) {
      if (ev.button !== 0 || !self._spaceDown) return;
      ev.stopImmediatePropagation();
      var r = self.svg.getBoundingClientRect();
      panState = {
        startX: ev.clientX - r.left,
        startY: ev.clientY - r.top,
        viewStart: { minX: self.state.view.minX, maxX: self.state.view.maxX, minY: self.state.view.minY, maxY: self.state.view.maxY }
      };
      self.svg.style.cursor = 'grabbing';
    }, true); // capture phase so it fires first
    this.svg.addEventListener('mousemove', function (ev) {
      if (!panState) return;
      var r = self.svg.getBoundingClientRect();
      var dx = (ev.clientX - r.left - panState.startX) / (r.right - r.left);
      var dy = (ev.clientY - r.top - panState.startY) / (r.bottom - r.top);
      var rx = panState.viewStart.maxX - panState.viewStart.minX;
      var ry = panState.viewStart.maxY - panState.viewStart.minY;
      self.state.view.minX = panState.viewStart.minX - dx * rx;
      self.state.view.maxX = panState.viewStart.maxX - dx * rx;
      self.state.view.minY = panState.viewStart.minY + dy * ry;
      self.state.view.maxY = panState.viewStart.maxY + dy * ry;
      self.draw();
    });
    this.svg.addEventListener('mouseup', function (ev) {
      if (!panState) return;
      panState = null;
      if (self._spaceDown) self.svg.style.cursor = 'grab';
      else if (!self.state.zoomMode) self.svg.style.cursor = '';
    });
  };

  /* ---------------------------------------------------------------
     Status bar
     --------------------------------------------------------------- */

  PCAPlot.prototype._updateStatusBar = function () {
    var total = this.p.points.length;
    var sel = this.state.selected.size;
    var v = this.state.view;
    var el = document.getElementById('statusBar');
    if (!el) return;
    var isGlobal = (
      Math.abs(v.minX - this._ext().minX) < 0.0001 &&
      Math.abs(v.maxX - this._ext().maxX) < 0.0001
    );
    el.innerHTML = '<span><b>' + total + '</b> points</span>'
      + '<span><b>' + sel + '</b> selected</span>'
      + '<span>' + (isGlobal ? '🌐 Global view' : '🔍 Zoomed') + '</span>'
      + '<span>PC1: [' + v.minX.toFixed(3) + ', ' + v.maxX.toFixed(3) + ']</span>'
      + '<span>PC2: [' + v.minY.toFixed(3) + ', ' + v.maxY.toFixed(3) + ']</span>';
  };

  /* ---------------------------------------------------------------
     Export methods
     --------------------------------------------------------------- */

  PCAPlot.prototype._currentLayoutSvgString = function () {
    var w = this.svg.clientWidth || 900;
    var h = this.svg.clientHeight || 650;
    var panels = Array.from(document.querySelectorAll('.legendPanel'));
    var outW = w, outH = h;
    panels.forEach(function (p) {
      outW = Math.max(outW, p.offsetLeft + scaledPanelWidth(p) + 16);
      outH = Math.max(outH, p.offsetTop + scaledPanelHeight(p) + 16);
    });
    var plotText = this._exportPlotContent();
    var legends = panels.map(function (p) { return panelToSvg(p); }).join('');
    return '<svg xmlns="http://www.w3.org/2000/svg" width="' + outW
      + '" height="' + outH + '" viewBox="0 0 ' + outW + ' ' + outH + '">'
      + '<rect width="' + outW + '" height="' + outH + '" fill="white"/>'
      + plotText + legends + '</svg>';
  };

  PCAPlot.prototype._exportPlotContent = function () {
    var out = [];
    Array.from(this.svg.childNodes).forEach(function (node) {
      if (node.nodeType === 1) {
        out.push(new XMLSerializer().serializeToString(node));
      }
    });
    return '<g>' + out.join('') + '</g>';
  };

  function panelToSvg(panel) {
    var x = panel.offsetLeft, y = panel.offsetTop;
    var color = panel.dataset.color || '#999';
    var target = panel.dataset.target === '1';
    var group = panel.dataset.group || '';
    var pops = [], isBg = panel.dataset.modernBg === '1';
    try { pops = JSON.parse(panel.dataset.populations || '[]'); } catch (e) { pops = []; }
    var rows = [];
    if (isBg) {
      var mc = mutedColor(color);
      var bgA = PAYLOAD.config.modern_background_alpha || 0.35;
      rows.push('<circle cx="14" cy="14" r="6" fill="' + mc + '" opacity="' + bgA + '"/>');
      rows.push('<text x="28" y="18" font-family="Arial,Helvetica,sans-serif"'
        + ' font-size="12" font-weight="700" fill="' + mc + '" opacity="' + bgA + '">'
        + esc(group + ' (bg)') + '</text>');
    } else {
      rows.push(exportLegendMarker(
        target ? (PAYLOAD.config.target_shape || 'star') : 'circle',
        target ? (PAYLOAD.config.target_color || '#FFD400') : color,
        target, 14, 14
      ));
      rows.push('<text x="28" y="18" font-family="Arial,Helvetica,sans-serif"'
        + ' font-size="12" font-weight="700" fill="#1b252e">' + esc(group) + '</text>');
    }
    pops.forEach(function (p, i) {
      if (isBg) return;
      var yy = 38 + i * 17;
      rows.push(exportLegendMarker(
        p.symbol,
        target ? (PAYLOAD.config.target_color || '#FFD400') : color,
        target, 14, yy - 4
      ));
      rows.push('<text x="28" y="' + yy + '" font-family="Arial,Helvetica,sans-serif"'
        + ' font-size="12" fill="#1b252e">' + esc(p.population) + '</text>');
    });
    return '<g transform="translate(' + x + ' ' + y + ') scale('
      + window.__legendScale + ')">' + rows.join('') + '</g>';
  }

  PCAPlot.prototype._layoutSizeFromSvg = function (s) {
    var m = s.match(/viewBox="0 0 ([0-9.]+) ([0-9.]+)"/);
    return {
      w: m ? Math.ceil(+m[1]) : (this.svg.clientWidth || 900),
      h: m ? Math.ceil(+m[2]) : (this.svg.clientHeight || 650)
    };
  };

  PCAPlot.prototype._renderLayoutToCanvas = function (scale) {
    scale = scale || 2;
    var self = this;
    var size = this._layoutSizeFromSvg(this._currentLayoutSvgString());
    var c = document.createElement('canvas');
    c.width = size.w * scale;
    c.height = size.h * scale;
    var ctx = c.getContext('2d');
    ctx.scale(scale, scale);
    this._drawCurrentLayoutOnCanvas(ctx, size.w, size.h);
    return Promise.resolve({ canvas: c, width: size.w, height: size.h });
  };

  PCAPlot.prototype._drawCurrentLayoutOnCanvas = function (ctx, w, h) {
    ctx.fillStyle = 'white';
    ctx.fillRect(0, 0, w, h);
    this._drawPlotOnCanvas(ctx);
    var self = this;
    Array.from(document.querySelectorAll('.legendPanel')).forEach(function (p) {
      self._drawLegendPanelOnCanvas(ctx, p);
    });
  };

  PCAPlot.prototype._drawPlotOnCanvas = function (ctx) {
    var f = this._plotFrame();

    // Border
    ctx.strokeStyle = '#1b252e';
    ctx.lineWidth = 1;
    ctx.strokeRect(f.left, f.top, f.right - f.left, f.bottom - f.top);

    // Axis labels
    ctx.fillStyle = '#1b252e';
    ctx.font = '13px Arial, Helvetica, sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(this.p.xLabel, (f.left + f.right) / 2, f.bottom + 38);
    ctx.save();
    ctx.translate(f.left - 48, (f.top + f.bottom) / 2);
    ctx.rotate(-Math.PI / 2);
    ctx.fillText(this.p.yLabel, 0, 0);
    ctx.restore();

    var self = this;

    // KDE heatmap overlay (canvas export)
    if (this.state.showDensity && this._kdeCanvasImg && this._kdeCanvasImg.complete && this._kdeCanvasImg.naturalWidth > 0) {
      try {
        ctx.drawImage(this._kdeCanvasImg, f.left, f.top, f.right - f.left, f.bottom - f.top);
      } catch(e) {}
    }

    // Modern background text
    if (this.state.modernBackground) {
      this.p.points.forEach(function (p) {
        if (!p.is_modern_background || p.is_target) return;
        if (!self._visible(p)) return;
        var x = self._sx(+p.PC1), y = self._sy(+p.PC2), r = self._pointRadius(p);
        ctx.save();
        ctx.globalAlpha = self._alpha(p);
        ctx.fillStyle = self._color(p);
        ctx.font = Math.max(11, Math.min(18, r * 0.8))
          + 'px Arial,Helvetica,sans-serif';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(p.group, x, y);
        ctx.restore();
      });
    }

    // Non-target, non-modern
    this.p.points.forEach(function (p) {
      if (p.is_target) return;
      if (self.state.modernBackground && p.is_modern_background) return;
      if (!self._visible(p)) return;
      var x = self._sx(+p.PC1), y = self._sy(+p.PC2), r = self._pointRadius(p);
      drawCanvasMarker(ctx, p.symbol, x, y, r,
        self._color(p), self._color(p),
        self._dim(p) ? 0.12 : self._alpha(p), true);
      self._drawPointLabelCanvas(ctx, p, x, y, r);
    });

    // Targets
    this.p.points.forEach(function (p) {
      if (!p.is_target) return;
      if (!self._visible(p)) return;
      var x = self._sx(+p.PC1), y = self._sy(+p.PC2), r = self._targetRadius();
      drawCanvasMarker(ctx, 'star', x, y, r,
        self.p.config.target_color || '#FFD400',
        self.p.config.target_outline_color || '#FF0000', 1, true);
      if (self.p.config.label_targets) {
        ctx.fillStyle = '#111';
        ctx.font = 'bold 12px Arial, Helvetica, sans-serif';
        ctx.textAlign = 'left';
        ctx.fillText(p.target_label || p.sample_id, x + 9, y - 9);
      }
      self._drawPointLabelCanvas(ctx, p, x, y, r);
    });

    // Selection circles
    if (this.state.selected.size) {
      ctx.strokeStyle = '#111';
      ctx.lineWidth = 1.5;
      var self2 = this;
      this.state.selected.forEach(function (idx) {
        var p = self2.p.points[idx];
        if (!self2._visible(p)) return;
        ctx.beginPath();
        ctx.arc(self2._sx(+p.PC1), self2._sy(+p.PC2), 10, 0, Math.PI * 2);
        ctx.stroke();
      });
    }
  };

  PCAPlot.prototype._drawPointLabelCanvas = function (ctx, p, x, y, r) {
    var label = this._pointLabel(p);
    if (!label) return;
    ctx.save();
    ctx.globalAlpha = this._dim(p) ? 0.2 : 0.95;
    ctx.fillStyle = this._color(p);
    ctx.font = '10px Arial, Helvetica, sans-serif';
    ctx.textAlign = 'left';
    ctx.textBaseline = 'alphabetic';
    ctx.fillText(label, x + r + 4, y + 4);
    ctx.restore();
  };

  PCAPlot.prototype._drawLegendPanelOnCanvas = function (ctx, panel) {
    var x = panel.offsetLeft, y = panel.offsetTop;
    var s = this.state.legendScale || 1;
    var color = panel.dataset.color || '#999';
    var target = panel.dataset.target === '1';
    var group = panel.dataset.group || '';
    var pops = [], isBg = panel.dataset.modernBg === '1';
    try { pops = JSON.parse(panel.dataset.populations || '[]'); } catch (e) { pops = []; }

    ctx.save();
    ctx.translate(x, y);
    ctx.scale(s, s);

    if (isBg) {
      var mc = mutedColor(color);
      var bgA = this.p.config.modern_background_alpha || 0.35;
      ctx.globalAlpha = bgA;
      ctx.fillStyle = mc;
      ctx.beginPath();
      ctx.arc(14, 14, 6, 0, Math.PI * 2);
      ctx.fill();
      ctx.globalAlpha = bgA;
      ctx.fillStyle = mc;
      ctx.font = 'bold 12px Arial, Helvetica, sans-serif';
      ctx.textAlign = 'left';
      ctx.textBaseline = 'alphabetic';
      ctx.fillText(group + ' (bg)', 28, 18);
    } else {
      var markerColor = target
        ? (PAYLOAD.config.target_color || '#FFD400')
        : color;
      drawCanvasMarker(ctx,
        target ? (PAYLOAD.config.target_shape || 'star') : 'circle',
        14, 14, 5.5, markerColor,
        target ? (PAYLOAD.config.target_outline_color || '#FF0000') : color,
        1, true);
      ctx.fillStyle = '#1b252e';
      ctx.font = 'bold 12px Arial, Helvetica, sans-serif';
      ctx.textAlign = 'left';
      ctx.textBaseline = 'alphabetic';
      ctx.fillText(group, 28, 18);
    }

    pops.forEach(function (pop, i) {
      if (isBg) return;
      var yy = 38 + i * 17;
      drawCanvasMarker(ctx, pop.symbol, 14, yy - 4, 5.5,
        target ? (PAYLOAD.config.target_color || '#FFD400') : color,
        target ? (PAYLOAD.config.target_outline_color || '#FF0000') : color,
        1, true);
      ctx.font = '12px Arial, Helvetica, sans-serif';
      ctx.fillStyle = '#1b252e';
      ctx.fillText(pop.population, 28, yy);
    });

    ctx.restore();
  };

  PCAPlot.prototype._exportCurrentLayoutPdf = async function () {
    try {
      var r = await this._renderLayoutToCanvas(2);
      var jpeg = r.canvas.toDataURL('image/jpeg', 0.95);
      var pdf = makePdfFromJpegDataUrl(jpeg, r.canvas.width, r.canvas.height);
      downloadBlob(this.p.project + '_current_layout.pdf', pdf);
    } catch (e) {
      alert('PDF export failed: ' + e.message);
    }
  };

  /* ================================================================
     Bootstrap
     ================================================================ */

  window.__legendScale = 1;
  window.plot = new PCAPlot(PAYLOAD);

})();

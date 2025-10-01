// static/js/ui/boardRenderer.js
// Simple, predictable renderer. No DPR tricks, minimal recalcs.

export class BoardRenderer {
  constructor(canvas, { size = 4 } = {}) {
    this.canvas = canvas;
    this.ctx = canvas.getContext("2d");
    this.size = size; // board size (e.g., 4)
    this.players = {
      R: { color: "#ff4d4f", pos: null },
      B: { color: "#4da6ff", pos: null },
    };
    this.target = null;

    this._ensurePixelSize();
    this._recomputeMetrics();
  }

  // If CSS set width/height, use those as pixel size. Fallback to 480x480.
  _ensurePixelSize() {
    const rect = this.canvas.getBoundingClientRect();
    const w = Math.round(rect.width || this.canvas.width || 480);
    const h = Math.round(rect.height || this.canvas.height || 480);
    this.canvas.width = w;
    this.canvas.height = h;
  }

  _recomputeMetrics() {
    const W = this.canvas.width;
    const H = this.canvas.height;
    this.W = W;
    this.H = H;
    this.cs = Math.min(W, H) / this.size; // cell size (px)
  }

  // Call this on window resize
  onResize() {
    this._ensurePixelSize();
    this._recomputeMetrics();
    this.drawBoard();
  }

  // --------- Public API ---------
  drawBoard() {
    const { ctx, W, H, size, cs } = this;

    // bg
    ctx.fillStyle = "#111";
    ctx.fillRect(0, 0, W, H);

    // chessboard cells
    for (let r = 0; r < size; r++) {
      for (let c = 0; c < size; c++) this._drawCell(c, r);
    }

    // grid
    ctx.strokeStyle = "#2b2b2b";
    ctx.lineWidth = 1;
    for (let i = 0; i <= size; i++) {
      ctx.beginPath();
      ctx.moveTo(i * cs, 0);
      ctx.lineTo(i * cs, size * cs);
      ctx.stroke();
      ctx.beginPath();
      ctx.moveTo(0, i * cs);
      ctx.lineTo(size * cs, i * cs);
      ctx.stroke();
    }

    // star and players (if set)
    // if (this.target) this._drawStar(this.target);
    // if (this.players.R.pos)
    //   this._drawDot(this.players.R.pos, this.players.R.color);
    // if (this.players.B.pos)
    //   this._drawDot(this.players.B.pos, this.players.B.color);
  }

  drawTarget(pos) {
    this.target = pos;
    this._drawStar(pos);
  }

  setPlayer(role, color, pos) {
    const p = this.players[role];
    if (!p) return;
    if (color) p.color = color;
    if (pos) p.pos = pos;
    if (p.pos) this._drawDot(p.pos, p.color);
  }

  updatePlayer(role, nextPos) {
    const p = this.players[role];
    if (!p) return;

    // clear previous cell (redraw its base cell)
    if (p.pos) this._redrawCell(p.pos);

    // set & draw new
    p.pos = nextPos;
    this._redrawCell(nextPos); // ensure fresh base under the dot
    this._drawDot(nextPos, p.color);

    // if star sits here, redraw it on top (optional priority)
    if (this.target && this._same(this.target, nextPos)) {
      this._drawStar(this.target);
    }
  }

  clearAndRedrawAll() {
    this.drawBoard();
  }

  // --------- Internals ---------
  _same(a, b) {
    return a && b && a[0] === b[0] && a[1] === b[1];
  }

  _drawCell(c, r) {
    const { ctx, cs } = this;
    const x = c * cs,
      y = r * cs;
    const dark = (r + c) % 2 === 0;
    ctx.fillStyle = dark ? "#1b1b1b" : "#232323";
    ctx.fillRect(x, y, cs, cs);
  }

  _redrawCell(pos) {
    const [c, r] = pos;
    this._drawCell(c, r);

    // re-stroke the grid edges for this cell to keep borders crisp
    const { ctx, cs } = this;
    ctx.strokeStyle = "#2b2b2b";
    ctx.lineWidth = 1;
    // vertical lines bordering this cell
    ctx.beginPath();
    ctx.moveTo(c * cs, r * cs);
    ctx.lineTo(c * cs, (r + 1) * cs);
    ctx.stroke();
    ctx.beginPath();
    ctx.moveTo((c + 1) * cs, r * cs);
    ctx.lineTo((c + 1) * cs, (r + 1) * cs);
    ctx.stroke();
    // horizontal lines bordering this cell
    ctx.beginPath();
    ctx.moveTo(c * cs, r * cs);
    ctx.lineTo((c + 1) * cs, r * cs);
    ctx.stroke();
    ctx.beginPath();
    ctx.moveTo(c * cs, (r + 1) * cs);
    ctx.lineTo((c + 1) * cs, (r + 1) * cs);
    ctx.stroke();
  }

  _drawDot(pos, color) {
    const { ctx, cs } = this;
    const [cx, cy] = pos;
    const x = (cx + 0.5) * cs;
    const y = (cy + 0.5) * cs;
    const r = cs * 0.22;
    ctx.beginPath();
    ctx.arc(x, y, r, 0, Math.PI * 2);
    ctx.fillStyle = color || "#fff";
    ctx.fill();
  }

  _drawStar(pos) {
    const { ctx, cs } = this;
    const [cx, cy] = pos;
    const x = (cx + 0.5) * cs;
    const y = (cy + 0.5) * cs;
    const spikes = 5,
      outerR = cs * 0.26,
      innerR = cs * 0.11;
    let rot = (Math.PI / 2) * 3;
    const step = Math.PI / spikes;

    ctx.beginPath();
    ctx.moveTo(x, y - outerR);
    for (let i = 0; i < spikes; i++) {
      let x1 = x + Math.cos(rot) * outerR;
      let y1 = y + Math.sin(rot) * outerR;
      ctx.lineTo(x1, y1);
      rot += step;
      x1 = x + Math.cos(rot) * innerR;
      y1 = y + Math.sin(rot) * innerR;
      ctx.lineTo(x1, y1);
      rot += step;
    }
    ctx.lineTo(x, y - outerR);
    ctx.closePath();
    ctx.fillStyle = "#ffd43b";
    ctx.strokeStyle = "#a88400";
    ctx.lineWidth = 2;
    ctx.fill();
    ctx.stroke();
  }
}

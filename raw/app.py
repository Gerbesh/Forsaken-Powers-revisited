from __future__ import annotations

import json
import random
from dataclasses import dataclass
from typing import List, Tuple

from flask import Flask, jsonify, render_template_string, session

app = Flask(__name__)
app.secret_key = "change-me-please"


# ---------------------------
# Game config
# ---------------------------

REELS_ROWS = 5
REELS_COLS = 5

PICKAXES = {
    "WOOD": {"label": "WOOD x2", "mult": 2, "power": 10},
    "STONE": {"label": "STONE x4", "mult": 4, "power": 16},
    "IRON": {"label": "IRON x8", "mult": 8, "power": 24},
    "DIAMOND": {"label": "DIAMOND x12", "mult": 12, "power": 32},
}

SYMBOLS: List[Tuple[str, int]] = [
    ("WOOD", 28),
    ("STONE", 20),
    ("IRON", 12),
    ("DIAMOND", 6),
    ("UP2", 10),
    ("TNT", 8),
    ("EMPTY", 16),
]

BLOCKS = [
    {"id": "DIRT", "name": "Земля", "hardness": 3, "reward": 0},
    {"id": "STONE", "name": "Камень", "hardness": 4, "reward": 1},
    {"id": "ORE", "name": "Руда", "hardness": 5, "reward": 2},
    {"id": "GOLD", "name": "Золото", "hardness": 6, "reward": 3},
    {"id": "DIAM", "name": "Алмаз", "hardness": 7, "reward": 4},
    {"id": "CHEST", "name": "Сундук", "hardness": 4, "reward": 0},
]


def weighted_pick(symbols: List[Tuple[str, int]]) -> str:
    total = sum(w for _, w in symbols)
    r = random.randint(1, total)
    s = 0
    for sym, w in symbols:
        s += w
        if r <= s:
            return sym
    return symbols[-1][0]


def generate_reels() -> List[List[str]]:
    reels = [[weighted_pick(SYMBOLS) for _ in range(REELS_COLS)] for _ in range(REELS_ROWS)]
    # гарантируем: в каждой колонке есть хотя бы 1 кирка
    for c in range(REELS_COLS):
        if not any(reels[r][c] in PICKAXES for r in range(REELS_ROWS)):
            reels[random.randrange(REELS_ROWS)][c] = random.choice(list(PICKAXES.keys()))
    return reels


@dataclass
class ColumnResult:
    base_pickaxe: str
    final_power: int
    depth_reached: int
    broke_chest: bool
    chest_mult: int
    raw_reward: int
    final_reward: int


def resolve_column(col_syms: List[str]) -> ColumnResult:
    base = None
    for s in col_syms:
        if s in PICKAXES:
            base = s
            break
    if base is None:
        base = "WOOD"

    power = PICKAXES[base]["power"]

    for s in col_syms:
        if s == "UP2":
            power *= 2
        elif s == "TNT":
            power += 10

    raw_reward = 0
    depth = 0
    chest_mult = 1
    broke_chest = False

    for i, b in enumerate(BLOCKS):
        if power < b["hardness"]:
            break
        power -= b["hardness"]
        depth = i + 1
        raw_reward += b["reward"]

        if b["id"] == "CHEST":
            broke_chest = True
            chest_mult = random.randint(1, 10)
            break

    final_reward = raw_reward * chest_mult
    return ColumnResult(
        base_pickaxe=base,
        final_power=power,
        depth_reached=depth,
        broke_chest=broke_chest,
        chest_mult=chest_mult,
        raw_reward=raw_reward,
        final_reward=final_reward,
    )


def resolve_spin(reels: List[List[str]]) -> Tuple[List[ColumnResult], int]:
    results: List[ColumnResult] = []
    total = 0
    for c in range(REELS_COLS):
        col = [reels[r][c] for r in range(REELS_ROWS)]
        res = resolve_column(col)
        results.append(res)
        total += res.final_reward
    return results, total


# ---------------------------
# HTML template (Jinja, no Python f-string)
# ---------------------------

INDEX_HTML = r"""<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>Pickaxe Slot Miner</title>
  <style>
    :root {
      --bg: #0f1220;
      --panel: #171a2e;
      --cell: #23264a;
      --text: #e7e7ff;
      --muted: #a6a6d6;
      --good: #8ef0a1;
      --warn: #ffd37a;
    }
    body {
      margin: 0;
      background: radial-gradient(1200px 700px at 20% 10%, #1b1f3a, var(--bg));
      color: var(--text);
      font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Arial, "Noto Sans", "Liberation Sans", sans-serif;
    }
    .wrap {
      max-width: 980px;
      margin: 0 auto;
      padding: 16px;
      display: grid;
      gap: 12px;
    }
    .topbar {
      display: flex;
      gap: 12px;
      align-items: center;
      justify-content: space-between;
      background: rgba(255,255,255,0.04);
      border: 1px solid rgba(255,255,255,0.08);
      border-radius: 14px;
      padding: 12px 14px;
    }
    .score {
      font-weight: 800;
      letter-spacing: 0.2px;
    }
    .btn {
      cursor: pointer;
      border: 0;
      background: linear-gradient(180deg, #3a7bfd, #2a57f5);
      color: white;
      font-weight: 900;
      padding: 10px 14px;
      border-radius: 12px;
      min-width: 160px;
    }
    .btn:disabled {
      opacity: 0.6;
      cursor: not-allowed;
    }
    .board {
      background: rgba(255,255,255,0.04);
      border: 1px solid rgba(255,255,255,0.08);
      border-radius: 14px;
      padding: 14px;
      display: grid;
      gap: 14px;
    }

    .reels {
      display: grid;
      grid-template-columns: repeat(5, 1fr);
      gap: 8px;
    }
    .col {
      background: var(--panel);
      border: 1px solid rgba(255,255,255,0.10);
      border-radius: 12px;
      padding: 8px;
      display: grid;
      gap: 6px;
    }
    .cell {
      height: 42px;
      border-radius: 10px;
      background: var(--cell);
      display: grid;
      place-items: center;
      font-weight: 900;
      font-size: 12px;
      user-select: none;
      border: 1px solid rgba(255,255,255,0.07);
    }
    .cell.small { font-size: 11px; font-weight: 900; }

    .tag-pick { color: #cfe3ff; }
    .tag-up { color: var(--good); }
    .tag-tnt { color: #ff8aa0; }
    .tag-empty { color: rgba(255,255,255,0.35); }

    .canvasWrap {
      background: rgba(255,255,255,0.04);
      border: 1px solid rgba(255,255,255,0.08);
      border-radius: 14px;
      padding: 12px;
    }

    canvas {
      width: 100%;
      height: auto;
      display: block;
      border-radius: 12px;
      background: #121532;
      border: 1px solid rgba(255,255,255,0.10);
    }

    .log {
      background: var(--panel);
      border: 1px solid rgba(255,255,255,0.10);
      border-radius: 12px;
      padding: 12px;
      display: grid;
      gap: 8px;
    }
    .row {
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
      align-items: center;
      justify-content: space-between;
    }
    .pill {
      background: rgba(255,255,255,0.06);
      border: 1px solid rgba(255,255,255,0.10);
      border-radius: 999px;
      padding: 6px 10px;
      font-weight: 900;
      font-size: 12px;
      color: var(--muted);
    }
    .gain {
      font-weight: 900;
      color: var(--warn);
    }
    .hint {
      color: rgba(255,255,255,0.55);
      font-size: 12px;
      line-height: 1.35;
    }
  </style>
</head>
<body>
  <div class="wrap">
    <div class="topbar">
      <div class="score">Счет: <span id="score">{{ total_score }}</span></div>
      <button id="spinBtn" class="btn">Крутить</button>
    </div>

    <div class="board">
      <div class="hint">
        Сверху слот 5x5. В колонке берется первая сверху кирка, бонусы UP и TNT усиливают копку.
        Снизу слои: земля(0), камень(1), руда(2), золото(3), алмаз(4), сундук(множитель 1..10).
      </div>

      <div class="reels" id="reels"></div>

      <div class="canvasWrap">
        <canvas id="mineCanvas" width="980" height="420"></canvas>
      </div>

      <div class="log" id="log">
        <div class="row">
          <div class="pill">Гейн за спин: <span class="gain" id="lastGain">0</span></div>
          <div class="pill">Статус: <span id="status">готово</span></div>
        </div>
        <div class="hint" id="details">Нажми "Крутить".</div>
      </div>
    </div>
  </div>

<script>
  const REELS_ROWS = {{ reels_rows }};
  const REELS_COLS = {{ reels_cols }};
  const BLOCKS = {{ blocks_json | safe }};

  function symText(s) {
    if (s === "WOOD") return "⛏️ WOOD x2";
    if (s === "STONE") return "⛏️ STONE x4";
    if (s === "IRON") return "⛏️ IRON x8";
    if (s === "DIAMOND") return "⛏️ DIAM x12";
    if (s === "UP2") return "BONUS x2";
    if (s === "TNT") return "TNT";
    return " ";
  }

  function symClass(s) {
    if (["WOOD","STONE","IRON","DIAMOND"].includes(s)) return "tag-pick";
    if (s === "UP2") return "tag-up";
    if (s === "TNT") return "tag-tnt";
    return "tag-empty";
  }

  function renderReels(reels) {
    const root = document.getElementById("reels");
    root.innerHTML = "";
    for (let c = 0; c < REELS_COLS; c++) {
      const col = document.createElement("div");
      col.className = "col";
      for (let r = 0; r < REELS_ROWS; r++) {
        const cell = document.createElement("div");
        const s = reels[r][c];
        cell.className = "cell small " + symClass(s);
        cell.textContent = symText(s);
        col.appendChild(cell);
      }
      root.appendChild(col);
    }
  }

  function setStatus(t) {
    document.getElementById("status").textContent = t;
  }
  function setDetails(html) {
    document.getElementById("details").innerHTML = html;
  }
  function sleep(ms){ return new Promise(r => setTimeout(r, ms)); }

  // ---------------------------
  // Canvas animation
  // ---------------------------

  const PICKAXE_POWER = {
    "WOOD": 10,
    "STONE": 16,
    "IRON": 24,
    "DIAMOND": 32
  };

  const BLOCK_COLORS = {
    "DIRT": "#5a3a2b",
    "STONE": "#4c5463",
    "ORE": "#5d6b7a",
    "GOLD": "#80621d",
    "DIAM": "#1b6a7a",
    "CHEST": "#6a3b1b"
  };

  const BLOCK_REWARD = {
    "DIRT": 0,
    "STONE": 1,
    "ORE": 2,
    "GOLD": 3,
    "DIAM": 4,
    "CHEST": 0
  };

  function getColumnSyms(reels, col){
    const out = [];
    for(let r=0;r<REELS_ROWS;r++) out.push(reels[r][col]);
    return out;
  }

  function computePickaxeState(colSyms){
    let base = "WOOD";
    for(const s of colSyms){
      if(["WOOD","STONE","IRON","DIAMOND"].includes(s)){ base = s; break; }
    }
    let power = PICKAXE_POWER[base];
    let mult2 = 0;
    let tnt = 0;
    for(const s of colSyms){
      if(s === "UP2"){ mult2++; }
      if(s === "TNT"){ tnt++; }
    }
    power = power * Math.pow(2, mult2) + 10 * tnt;
    return { base, power, mult2, tnt };
  }

  function simulateMining(colSyms){
    const pk = computePickaxeState(colSyms);
    let pickHp = pk.power;

    const blocks = BLOCKS.map(b => ({
      id: b.id,
      name: b.name,
      hardness: b.hardness,
      hp: b.hardness,
    }));

    let reward = 0;
    let chestMult = 1;
    let brokeChest = false;

    const events = [];

    for(let bi=0; bi<blocks.length; bi++){
      const bl = blocks[bi];

      while(bl.hp > 0){
        if(pickHp <= 0){
          events.push({ type:"STOP", blockIndex: bi });
          return { events, reward, brokeChest, chestMult };
        }
        events.push({ type:"HIT", blockIndex: bi });
        bl.hp -= 1;
        pickHp -= 1;
      }

      events.push({ type:"BREAK", blockIndex: bi });
      reward += (BLOCK_REWARD[bl.id] ?? 0);

      if(bl.id === "CHEST"){
        brokeChest = true;
        chestMult = 1 + Math.floor(Math.random()*10); // 1..10
        events.push({ type:"CHEST_MULT", blockIndex: bi, mult: chestMult });
        break;
      }
    }

    return { events, reward, brokeChest, chestMult };
  }

  function roundRect(ctx, x, y, w, h, r){
    const rr = Math.min(r, w/2, h/2);
    ctx.beginPath();
    ctx.moveTo(x+rr, y);
    ctx.arcTo(x+w, y, x+w, y+h, rr);
    ctx.arcTo(x+w, y+h, x, y+h, rr);
    ctx.arcTo(x, y+h, x, y, rr);
    ctx.arcTo(x, y, x+w, y, rr);
    ctx.closePath();
  }

  class MineAnimator {
    constructor(canvas){
      this.canvas = canvas;
      this.ctx = canvas.getContext("2d");
      this.w = canvas.width;
      this.h = canvas.height;

      this.cols = 5;
      this.rows = BLOCKS.length;

      this.margin = 18;
      this.colGap = 14;
      this.blockGap = 8;

      this.colW = (this.w - this.margin*2 - this.colGap*(this.cols-1)) / this.cols;
      this.blockH = (this.h - this.margin*2 - 80 - this.blockGap*(this.rows-1)) / this.rows;

      this.pickYTop = this.margin + 18;
      this.pickSize = Math.min(36, this.colW * 0.33);

      this.state = null;
    }

    makeInitialState(reels){
      const stacks = [];
      for(let c=0;c<this.cols;c++){
        const colSyms = getColumnSyms(reels, c);
        const pk = computePickaxeState(colSyms);
        const sim = simulateMining(colSyms);

        const blocks = BLOCKS.map(b => ({
          id: b.id,
          name: b.name,
          hardness: b.hardness,
          hp: b.hardness,
          broken: false
        }));

        stacks.push({
          col: c,
          colSyms,
          sim,
          blocks,
          pick: {
            base: pk.base,
            hp: pk.power,
            x: this.margin + c*(this.colW + this.colGap) + this.colW/2,
            y: this.pickYTop,
          },
        });
      }
      return { reels, stacks };
    }

    getBlockTopY(blockIndex){
      const y0 = this.margin + 72;
      const y = y0 + blockIndex*(this.blockH + this.blockGap);
      return y;
    }

    getHitY(blockIndex){
      // бьем верх блока
      return this.getBlockTopY(blockIndex) + 10;
    }

    draw(){
      const ctx = this.ctx;
      ctx.clearRect(0,0,this.w,this.h);

      // фон
      ctx.fillStyle = "rgba(255,255,255,0.02)";
      ctx.fillRect(0,0,this.w,this.h);

      for(const st of this.state.stacks){
        this.drawColumn(st);
      }
    }

    drawColumn(st){
      const ctx = this.ctx;
      const c = st.col;
      const x0 = this.margin + c*(this.colW + this.colGap);
      const y0 = this.margin + 72;

      // заголовок колонки: кирка и HP
      ctx.fillStyle = "rgba(255,255,255,0.85)";
      ctx.font = "900 12px system-ui, sans-serif";
      ctx.fillText(`⛏ ${st.pick.base}`, x0, this.margin + 20);

      ctx.fillStyle = "rgba(255,255,255,0.60)";
      ctx.font = "900 12px system-ui, sans-serif";
      ctx.fillText(`HP: ${Math.max(0, Math.floor(st.pick.hp))}`, x0, this.margin + 38);

      // блоки
      for(let i=0;i<this.rows;i++){
        const b = st.blocks[i];
        const y = y0 + i*(this.blockH + this.blockGap);

        ctx.globalAlpha = b.broken ? 0.18 : 1.0;
        ctx.fillStyle = BLOCK_COLORS[b.id] || "#333";
        roundRect(ctx, x0, y, this.colW, this.blockH, 10);
        ctx.fill();
        ctx.globalAlpha = 1.0;

        // hp bar
        const frac = Math.max(0, b.hp) / b.hardness;
        ctx.fillStyle = "rgba(0,0,0,0.35)";
        roundRect(ctx, x0+8, y+this.blockH-12, this.colW-16, 6, 4);
        ctx.fill();

        ctx.fillStyle = "rgba(255,255,255,0.70)";
        roundRect(ctx, x0+8, y+this.blockH-12, (this.colW-16)*frac, 6, 4);
        ctx.fill();

        // текст
        ctx.fillStyle = "rgba(255,255,255,0.90)";
        ctx.font = "900 12px system-ui, sans-serif";
        ctx.fillText(b.name, x0+10, y+18);

        ctx.fillStyle = "rgba(255,255,255,0.70)";
        ctx.font = "900 11px system-ui, sans-serif";
        ctx.fillText(`HP ${b.hp}/${b.hardness}`, x0+10, y+34);
      }

      // кирка (emoji)
      const px = st.pick.x;
      const py = st.pick.y;

      ctx.fillStyle = "rgba(255,255,255,0.12)";
      ctx.beginPath();
      ctx.arc(px, py, this.pickSize*0.68, 0, Math.PI*2);
      ctx.fill();

      ctx.fillStyle = "white";
      ctx.font = `900 ${Math.floor(this.pickSize)}px system-ui, sans-serif`;
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillText("⛏️", px, py);
      ctx.textAlign = "start";
      ctx.textBaseline = "alphabetic";

      // подсказка мультика сундука (если уже известен)
      if(st.sim && st.sim.brokeChest){
        ctx.fillStyle = "rgba(255,211,122,0.9)";
        ctx.font = "900 12px system-ui, sans-serif";
        ctx.fillText(`Chest x${st.sim.chestMult}`, x0, this.h - 14);
      }
    }

    async play(reels){
      this.state = this.makeInitialState(reels);
      this.draw();
      const tasks = this.state.stacks.map(st => this.playColumn(st));
      await Promise.all(tasks);
      this.draw();
    }

    async playColumn(st){
      const events = st.sim.events;

      // старт
      st.pick.y = this.pickYTop;

      for(const ev of events){
        if(ev.type === "STOP") break;

        if(ev.type === "HIT"){
          const bi = ev.blockIndex;
          await this.fallTo(st, bi);
          await this.bounceHit(st, bi);
        }

        if(ev.type === "BREAK"){
          const bi = ev.blockIndex;
          st.blocks[bi].broken = true;
        }

        // CHEST_MULT можно сделать эффектом позже, сейчас просто текст внизу
      }
    }

    async fallTo(st, bi){
      const targetY = this.getHitY(bi);
      const steps = 14;
      const startY = st.pick.y;
      for(let k=1;k<=steps;k++){
        const t = k/steps;
        const e = t*t; // ease-in
        st.pick.y = startY + (targetY - startY)*e;
        this.draw();
        await sleep(16);
      }
      st.pick.y = targetY;
    }

    async bounceHit(st, bi){
      // урон по 1
      st.pick.hp -= 1;
      st.blocks[bi].hp = Math.max(0, st.blocks[bi].hp - 1);

      const y0 = st.pick.y;

      // вверх
      const up = 11;
      for(let k=1;k<=up;k++){
        const t = k/up;
        st.pick.y = y0 - 18*Math.sin((t*Math.PI)/2);
        this.draw();
        await sleep(16);
      }
      // вниз
      const down = 9;
      for(let k=1;k<=down;k++){
        const t = k/down;
        st.pick.y = y0 - 18*Math.cos((t*Math.PI)/2);
        this.draw();
        await sleep(16);
      }
      st.pick.y = y0;

      this.draw();
      await sleep(16);
    }
  }

  // ---------------------------
  // Game flow
  // ---------------------------

  let animator = null;

  async function spin() {
    const btn = document.getElementById("spinBtn");
    if(btn.disabled) return;

    btn.disabled = true;
    setStatus("крутим...");
    setDetails("Прокрутка...");
    document.getElementById("lastGain").textContent = "0";

    // псевдо-анимация слота
    let tmp = null;
    for (let i = 0; i < 10; i++) {
      tmp = Array.from({length: REELS_ROWS}, () =>
        Array.from({length: REELS_COLS}, () => ["WOOD","STONE","IRON","DIAMOND","UP2","TNT","EMPTY"][Math.floor(Math.random()*7)])
      );
      renderReels(tmp);
      // обновляем шахту под фейк тоже
      animator.state = animator.makeInitialState(tmp);
      animator.draw();
      await sleep(55);
    }

    const resp = await fetch("/spin", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({})
    });
    const data = await resp.json();

    renderReels(data.reels);

    // проигрываем реальную анимацию добычи на canvas
    setStatus("добыча...");
    await animator.play(data.reels);

    // обновляем счет и логи
    document.getElementById("score").textContent = data.total_score;
    document.getElementById("lastGain").textContent = data.gain;

    let lines = [];
    for (let i = 0; i < data.results.length; i++) {
      const r = data.results[i];
      const chest = r.broke_chest ? `, сундук x${r.chest_mult}` : ", сундук не достигнут";
      lines.push(
        `Колонка ${i+1}: кирка ${r.base_pickaxe}, глубина ${r.depth_reached}/${BLOCKS.length}, награда ${r.raw_reward}${chest} -> <b>${r.final_reward}</b>`
      );
    }
    setDetails(lines.join("<br>"));
    setStatus("готово");
    btn.disabled = false;
  }

  function init() {
    const empty = Array.from({length: REELS_ROWS}, () => Array.from({length: REELS_COLS}, () => "EMPTY"));
    renderReels(empty);

    const canvas = document.getElementById("mineCanvas");
    animator = new MineAnimator(canvas);
    animator.state = animator.makeInitialState(empty);
    animator.draw();

    document.getElementById("spinBtn").addEventListener("click", spin);
  }

  init();
</script>
</body>
</html>
"""


# ---------------------------
# Routes
# ---------------------------

@app.get("/")
def index():
    session.setdefault("total_score", 0)
    return render_template_string(
        INDEX_HTML,
        total_score=session["total_score"],
        reels_rows=REELS_ROWS,
        reels_cols=REELS_COLS,
        blocks_json=json.dumps(BLOCKS, ensure_ascii=False),
    )


@app.post("/spin")
def spin():
    session.setdefault("total_score", 0)
    reels = generate_reels()
    results, gain = resolve_spin(reels)
    session["total_score"] += gain

    return jsonify(
        reels=reels,
        gain=gain,
        total_score=session["total_score"],
        results=[
            {
                "base_pickaxe": r.base_pickaxe,
                "final_power": r.final_power,
                "depth_reached": r.depth_reached,
                "broke_chest": r.broke_chest,
                "chest_mult": r.chest_mult,
                "raw_reward": r.raw_reward,
                "final_reward": r.final_reward,
            }
            for r in results
        ],
    )


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)

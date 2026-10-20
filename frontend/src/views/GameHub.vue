<template>
  <div class="page">
    <div style="margin-bottom: 18px">
      <span class="eyebrow">Vừa chơi vừa học</span>
      <h1>Chơi game</h1>
    </div>

    <div class="games">
      <RouterLink v-for="g in games" :key="g.to" :to="g.to" class="card game">
        <div class="art" :style="{ background: g.bg }" aria-hidden="true">
          <span v-for="(c, i) in g.art" :key="i" class="han glyph" :style="c.style">{{ c.t }}</span>
          <span class="ship">▲</span>
        </div>
        <div class="body">
          <div class="row spread">
            <h2>{{ g.title }}</h2>
            <span class="chip jade">{{ g.tag }}</span>
          </div>
          <p class="small muted">{{ g.desc }}</p>
          <p v-if="g.best()" class="small">Kỷ lục: <b>{{ g.best() }}</b> điểm</p>
          <span class="btn primary play">Chơi ngay →</span>
        </div>
      </RouterLink>

      <div class="card soon">
        <span class="han soon-ic" aria-hidden="true">玩</span>
        <p class="small muted">Các game khác sẽ được thêm vào đây.</p>
      </div>
    </div>
  </div>
</template>

<script setup>
function readBest(key) {
  try { return Number(JSON.parse(localStorage.getItem(key) || '{}').best) || 0 } catch { return 0 }
}

const games = [
  {
    to: '/game/ban-chu',
    title: 'Bắn chữ Hán',
    tag: 'Pinyin',
    desc: 'Chữ Hán rơi xuống, gõ pinyin không dấu để bắn hạ. Có boss thành ngữ, vật phẩm, combo và nhạc nền.',
    bg: 'linear-gradient(180deg, #0b0e22 0%, #151233 65%, #2a1238 100%)',
    art: [
      { t: '学生', style: { left: '14%', top: '18%' } },
      { t: '你好', style: { left: '58%', top: '10%', outline: '2px solid #facc15' } },
      { t: '朋友', style: { left: '40%', top: '46%' } },
    ],
    best: () => readBest('hanyu.game.shooter'),
  },
]
</script>

<style scoped>
.games { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 20px; }
.game { padding: 0; overflow: hidden; display: flex; flex-direction: column; color: var(--ink); text-decoration: none !important; transition: transform .25s var(--ease-spring); }
.game:hover { transform: translateY(-3px); }
.art { position: relative; height: 170px; overflow: hidden; }
.art::after { content: ''; position: absolute; left: 0; right: 0; bottom: 18px; height: 2px; background: #ef4444; box-shadow: 0 0 10px #ef4444; }
.glyph { position: absolute; padding: 4px 10px; border-radius: 8px; background: rgba(8, 10, 28, .85); color: #fff; font-size: 24px; }
.ship { position: absolute; left: 50%; bottom: 22px; transform: translateX(-50%); color: #38bdf8; font-size: 22px; text-shadow: 0 0 12px #38bdf8; }
.body { display: flex; flex-direction: column; gap: 8px; padding: 18px 20px 20px; flex: 1; }
.play { align-self: flex-start; margin-top: auto; }
.soon { display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 10px; min-height: 240px; border: 2px dashed var(--line); box-shadow: none; background: transparent; text-align: center; }
.soon-ic { font-size: 42px; color: var(--ink-faint); }
</style>

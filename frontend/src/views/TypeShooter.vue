<template>
  <div ref="root" class="ts" @pointerdown="focusKb">
    <canvas ref="cv" class="cv" aria-hidden="true"></canvas>
    <!-- ô nhập ẩn: nhận phím cả trên máy tính lẫn bàn phím ảo điện thoại -->
    <input ref="kb" class="kb" type="text" inputmode="latin" autocomplete="off" autocorrect="off" autocapitalize="off"
      spellcheck="false" aria-label="Gõ pinyin để bắn" @input="onInput" @keydown="onKeydown" />

    <!-- HUD -->
    <div v-if="phase === 'play' || phase === 'paused'" class="hud">
      <div class="left">
        <div class="pill score" title="Điểm">
          <svg viewBox="0 0 20 20" width="15" height="15" aria-hidden="true"><path d="M5 2h10v3a5 5 0 0 1-4 4.9V13h3v3H6v-3h3V9.9A5 5 0 0 1 5 5zM2 3h3v2a2 2 0 0 1-2-2zm13 0h3a2 2 0 0 1-2 2z" fill="#facc15"/></svg>
          <b>{{ hud.score }}</b>
        </div>
        <div v-if="effects.slow > 0" class="pill fx slow">{{ ITEMS.slow.icon }} Làm chậm <b>{{ Math.ceil(effects.slow) }}s</b></div>
        <div v-if="effects.double > 0" class="pill fx double">{{ ITEMS.double.icon }} Điểm ×2 <b>{{ Math.ceil(effects.double) }}s</b></div>
        <div v-if="effects.shield" class="pill fx shield">{{ ITEMS.shield.icon }} Khiên sẵn sàng</div>
      </div>
      <div class="pill stage">
        <svg viewBox="0 0 20 20" width="14" height="14" aria-hidden="true"><path d="M4 2v16M4 3h10l-2 3.5L14 10H4" fill="none" stroke="#4ade80" stroke-width="2" stroke-linejoin="round"/></svg>
        <b>Mốc {{ hud.stage }}/{{ STAGES }}</b><span class="dim">· {{ scopeLabel }}</span><span v-if="hud.stage % BOSS_EVERY === 0" class="bosstag">BOSS</span>
      </div>
      <div class="right">
        <div class="pill hearts" :aria-label="`Còn ${hud.lives} mạng`">
          <span v-for="i in MAX_LIVES" :key="i" class="heart" :class="{ lost: i > hud.lives }">♥</span>
        </div>
        <div class="tools">
          <button type="button" class="tool" :title="musicOn ? 'Tắt nhạc' : 'Bật nhạc'" @click.stop="toggleMusic">
            <svg viewBox="0 0 20 20" width="16" height="16" aria-hidden="true"><path d="M7 15.5a2.5 2.5 0 1 1-2-2.45V4l10-2v11.5a2.5 2.5 0 1 1-2-2.45V5.4L7 6.6z" fill="currentColor"/><path v-if="!musicOn" d="M2 2l16 16" stroke="#f87171" stroke-width="2"/></svg>
          </button>
          <button type="button" class="tool" :title="sfxOn ? 'Tắt tiếng hiệu ứng' : 'Bật tiếng hiệu ứng'" @click.stop="toggleSfx">
            <svg viewBox="0 0 20 20" width="16" height="16" aria-hidden="true"><path d="M3 7.5v5h3.5L11 16V4L6.5 7.5z" fill="currentColor"/><path v-if="sfxOn" d="M13.5 7a4 4 0 0 1 0 6M15.5 5a7 7 0 0 1 0 10" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/><path v-else d="M13 7l5 6M18 7l-5 6" stroke="#f87171" stroke-width="1.8" stroke-linecap="round"/></svg>
          </button>
          <button type="button" class="tool" :title="isFull ? 'Thoát toàn màn hình' : 'Toàn màn hình'" @click.stop="toggleFull">
            <svg viewBox="0 0 20 20" width="16" height="16" aria-hidden="true"><path v-if="!isFull" d="M3 8V3h5M12 3h5v5M17 12v5h-5M8 17H3v-5" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><path v-else d="M8 3v5H3M17 8h-5V3M12 17v-5h5M3 12h5v5" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
          </button>
          <button type="button" class="tool" title="Tạm dừng (Esc)" @click.stop="togglePause">
            <svg viewBox="0 0 20 20" width="16" height="16" aria-hidden="true"><path d="M6 4h3v12H6zM11 4h3v12h-3z" fill="currentColor"/></svg>
          </button>
        </div>
      </div>
    </div>
    <div v-if="phase === 'play' && hud.mult > 1" class="combo" :key="hud.mult">×{{ hud.mult }} <small>combo {{ hud.combo }}</small></div>
    <div v-if="phase === 'play' || phase === 'paused'" class="foot">{{ scopeLabel }} · Gõ pinyin không dấu · Backspace bỏ chọn · Esc tạm dừng</div>

    <!-- màn chọn -->
    <div v-if="phase === 'setup'" class="overlay">
      <div class="panel">
        <div class="brandline"><span class="seal han">战</span><div><span class="eyebrow">Game luyện pinyin</span><h1>Bắn chữ Hán</h1></div></div>
        <p class="lead">Chữ Hán rơi xuống vạch đỏ. Gõ <b>pinyin không dấu</b> để khoá mục tiêu và bắn hạ, ví dụ <span class="han">学生</span> → <kbd>xuesheng</kbd>. Để lọt qua vạch đỏ là mất ♥.</p>
        <p v-if="err" class="err">{{ err }}</p>
        <div v-if="!opts && !err" class="dim">Đang tải…</div>
        <template v-else-if="opts">
          <div v-if="!opts.counts.all" class="dim">Chưa có từ nào. <RouterLink to="/library">Nhập file từ vựng</RouterLink> trước nhé.</div>
          <template v-else>
            <div class="field">
              <span class="lbl">Kho từ</span>
              <div class="chips">
                <button v-for="s in quickScopes" :key="s.k" type="button" class="chip" :class="{ on: scope === s.k }"
                  :disabled="!opts.counts[s.k]" @click="scope = s.k">{{ s.label }} <small>{{ opts.counts[s.k] }}</small></button>
                <button type="button" class="chip" :class="{ on: scope === 'unit' || scope === 'book' }" @click="pickUnitScope">Theo quyển / bài</button>
              </div>
            </div>
            <div v-if="scope === 'unit' || scope === 'book'" class="field">
              <select v-model="refKey" class="sel">
                <template v-for="b in opts.books" :key="b.id">
                  <option :value="`book:${b.id}`">{{ b.title }} — cả quyển ({{ b.word_count }} từ)</option>
                  <option v-for="u in b.units" :key="u.id" :value="`unit:${u.id}`">　{{ u.idx }}. {{ u.title_zh ? u.title_zh + ' · ' : '' }}{{ u.title_vi }} ({{ u.word_count }})</option>
                </template>
              </select>
            </div>
            <div class="field">
              <span class="lbl">Tốc độ rơi</span>
              <div class="chips">
                <button v-for="sp in SPEEDS" :key="sp.k" type="button" class="chip" :class="{ on: speed === sp.k }" @click="speed = sp.k">{{ sp.label }}</button>
              </div>
              <span class="dim small">{{ speedNote }}</span>
            </div>
            <div class="field toggles">
              <label><input v-model="musicOn" type="checkbox" /> Nhạc nền</label>
              <label><input v-model="sfxOn" type="checkbox" /> Tiếng bắn / nổ</label>
            </div>
            <ul class="tips">
              <li>Chữ rơi quá nửa màn sẽ hiện <b>Hán Việt</b> để gợi ý, nhưng chỉ được nửa điểm.</li>
              <li>Gõ liền không sai để tăng combo, nhân điểm tối đa ×5.</li>
              <li><b>Boss thành ngữ</b> xuất hiện ở mốc 5, 10, 15, 20. Để boss chạm vạch đỏ là mất 2 ♥.</li>
              <li>Bắn hạ chữ có vòng sáng để nhận vật phẩm: <span v-for="it in ITEMS" :key="it.k" class="itm">{{ it.icon }} {{ it.label }}</span></li>
              <li>Kết quả được tính vào lịch ôn từ vựng.</li>
            </ul>
            <div class="row">
              <button class="go" type="button" :disabled="busy" @click="start()">{{ busy ? 'Đang nạp…' : 'Bắt đầu  ↵' }}</button>
              <span v-if="best" class="dim">Kỷ lục: <b>{{ best }}</b></span>
            </div>
          </template>
        </template>
        <RouterLink to="/game" class="exit">← Danh sách game</RouterLink>
      </div>
    </div>

    <!-- tạm dừng -->
    <div v-if="phase === 'paused'" class="overlay">
      <div class="panel small">
        <h2>Tạm dừng</h2>
        <p class="dim">Mốc {{ hud.stage }} · {{ hud.score }} điểm</p>
        <div class="field">
          <span class="lbl">Tốc độ rơi</span>
          <div class="chips center">
            <button v-for="sp in SPEEDS" :key="sp.k" type="button" class="chip" :class="{ on: speed === sp.k }" @click="speed = sp.k">{{ sp.label }}</button>
          </div>
        </div>
        <div class="row">
          <button class="go" type="button" @click="togglePause">Chơi tiếp  ↵</button>
          <button class="ghost" type="button" @click="endGame(false)">Kết thúc lượt</button>
        </div>
      </div>
    </div>

    <!-- tổng kết -->
    <div v-if="phase === 'over'" class="overlay">
      <div class="panel wide">
        <span class="eyebrow">{{ won ? 'Phá đảo!' : 'Hết lượt' }}</span>
        <h1>{{ summary.score }} điểm <span v-if="summary.newBest" class="badge">Kỷ lục mới</span></h1>
        <div class="stats">
          <div><b>{{ summary.stage }}</b><span>mốc</span></div>
          <div><b>{{ summary.kills }}</b><span>chữ bắn hạ</span></div>
          <div><b>{{ summary.bosses }}</b><span>boss hạ gục</span></div>
          <div><b>{{ summary.acc }}%</b><span>gõ chính xác</span></div>
          <div><b>{{ summary.cpm }}</b><span>ký tự / phút</span></div>
          <div><b>{{ summary.maxCombo }}</b><span>combo cao nhất</span></div>
        </div>
        <div v-if="summary.review.length" class="review">
          <span class="lbl">Từ cần xem lại</span>
          <div class="rv-list">
            <div v-for="w in summary.review" :key="w.hanzi" class="rv">
              <span class="han rvh">{{ w.hanzi }}</span>
              <span class="py">{{ w.pinyin }}</span>
              <SpeakButton :text="w.hanzi" small />
              <span class="hv">{{ w.han_viet }}</span>
              <span class="dim mean">{{ w.meaning }}</span>
              <span class="tag" :class="w.result">{{ w.boss ? 'Boss · ' : '' }}{{ w.result === 'miss' ? 'Để lọt' : 'Gõ sai / gợi ý' }}</span>
            </div>
          </div>
        </div>
        <p v-else class="dim">Không để lọt chữ nào, không gõ sai. Quá đỉnh!</p>
        <div class="row">
          <button class="go" type="button" @click="start()">Chơi lại  ↵</button>
          <button v-if="reviewCards.length >= 3" class="ghost" type="button" @click="start(reviewCards)">Chơi với {{ reviewCards.length }} từ cần xem lại</button>
          <button class="ghost" type="button" @click="phase = 'setup'">Đổi kho từ</button>
          <RouterLink to="/flashcards" class="ghost">Ôn bằng flashcard</RouterLink>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { api } from '../api'
import { createGameAudio } from '../composables/useGameAudio'
import SpeakButton from '../components/SpeakButton.vue'

const STAGES = 20
const MAX_LIVES = 5
const BOSS_EVERY = 5
const SPEEDS = [
  { k: 'vslow', label: 'Rất chậm', f: 0.55 },
  { k: 'slow', label: 'Chậm', f: 0.75 },
  { k: 'normal', label: 'Vừa', f: 1 },
  { k: 'fast', label: 'Nhanh', f: 1.3 },
  { k: 'vfast', label: 'Rất nhanh', f: 1.6 },
]
// vật phẩm: bắn hạ chữ mang vật phẩm để kích hoạt
const ITEMS = {
  slow: { k: 'slow', icon: '⏳', label: 'Làm chậm', color: '#38bdf8' },
  bomb: { k: 'bomb', icon: '💣', label: 'Bom', color: '#f97316' },
  heal: { k: 'heal', icon: '❤️', label: 'Hồi máu', color: '#fb7185' },
  shield: { k: 'shield', icon: '🛡️', label: 'Khiên', color: '#22d3ee' },
  double: { k: 'double', icon: '✨', label: 'Điểm ×2', color: '#facc15' },
}
const PREF_KEY = 'hanyu.game.shooter'
const quickScopes = [
  { k: 'all', label: 'Tất cả' },
  { k: 'weak', label: 'Từ yếu' },
  { k: 'due', label: 'Đến hạn ôn' },
  { k: 'tones', label: 'Hay sai thanh' },
]

const root = ref(null)
const cv = ref(null)
const isFull = ref(false)
const kb = ref(null)
const phase = ref('setup') // setup | play | paused | over
const opts = ref(null)
const err = ref('')
const busy = ref(false)
const scope = ref('all')
const refKey = ref('')
const musicOn = ref(true)
const sfxOn = ref(true)
const speed = ref('normal')
const speedF = computed(() => SPEEDS.find((x) => x.k === speed.value)?.f || 1)
const speedNote = computed(() => {
  const f = speedF.value
  return f === 1 ? 'Điểm giữ nguyên.' : `Điểm nhận được ×${f} theo tốc độ.`
})
const effects = reactive({ slow: 0, double: 0, shield: false })
const best = ref(0)
const won = ref(false)
const scopeLabel = ref('Tất cả')
const hud = reactive({ score: 0, stage: 1, lives: MAX_LIVES, combo: 0, mult: 1 })
const summary = reactive({ score: 0, stage: 1, kills: 0, bosses: 0, acc: 0, cpm: 0, maxCombo: 0, newBest: false, review: [] })

// chơi lại với từ cần xem lại: chỉ lấy từ trong kho (bỏ thành ngữ có sẵn)
const reviewCards = computed(() => summary.review.filter((w) => w.vocab_id && !w.boss))

// ------------------------------------------------------------------ tuỳ chọn
function loadPrefs() {
  try {
    const p = JSON.parse(localStorage.getItem(PREF_KEY) || '{}')
    if (p.scope) scope.value = p.scope
    if (p.refKey) refKey.value = p.refKey
    if (typeof p.musicOn === 'boolean') musicOn.value = p.musicOn
    if (typeof p.sfxOn === 'boolean') sfxOn.value = p.sfxOn
    if (SPEEDS.some((x) => x.k === p.speed)) speed.value = p.speed
    best.value = Number(p.best) || 0
  } catch { /* bỏ qua */ }
}
function savePrefs() {
  try {
    localStorage.setItem(PREF_KEY, JSON.stringify({
      scope: scope.value, refKey: refKey.value, musicOn: musicOn.value, sfxOn: sfxOn.value, speed: speed.value, best: best.value,
    }))
  } catch { /* bỏ qua */ }
}
function pickUnitScope() {
  if (!refKey.value && opts.value?.books.length) refKey.value = `book:${opts.value.books[0].id}`
  scope.value = refKey.value.split(':')[0] || 'book'
}
watch(refKey, (k) => { if (scope.value === 'unit' || scope.value === 'book') scope.value = k.split(':')[0] })
watch(musicOn, (v) => { audio?.setMusicOn(v); savePrefs() })
watch(sfxOn, (v) => { audio?.setSfxOn(v); savePrefs() })
watch(speed, savePrefs)
function toggleMusic() { musicOn.value = !musicOn.value; focusKb() }
function toggleSfx() { sfxOn.value = !sfxOn.value; focusKb() }

function currentScopeLabel() {
  if (scope.value === 'unit' || scope.value === 'book') {
    const [kind, id] = refKey.value.split(':')
    for (const b of opts.value?.books || []) {
      if (kind === 'book' && b.id === Number(id)) return b.title
      const u = b.units.find((x) => x.id === Number(id))
      if (u) return u.title_zh || u.title_vi
    }
  }
  return quickScopes.find((s) => s.k === scope.value)?.label || 'Tất cả'
}

// ------------------------------------------------------------------ âm thanh
let audio = null
function ensureAudio() {
  if (!audio) {
    audio = createGameAudio()
    if (!audio) return
    audio.setMusicOn(musicOn.value)
    audio.setSfxOn(sfxOn.value)
  }
  audio.resume()
}
const sfx = (name, ...a) => audio?.fx[name](...a)

// ------------------------------------------------------------------ trạng thái game (không reactive cho nhanh)
let ctx2d = null
let ro = null
let W = 0
let H = 0
let dpr = 1
let raf = 0
let last = 0
let deckAll = []
let bossPool = []
let bag = []
let words = []
let bullets = []
let particles = []
let floaters = []
let stars = []
let locked = null
let shake = 0
let flash = 0
let banner = null
let ship = { x: 0, y: 0, angle: 0, recoil: 0 }
let wave = null
let stats = null
let results = new Map() // vocab_id (hoặc chữ Hán với thành ngữ có sẵn) -> { card, result, boss }
let hanFont = 'serif'

const lineY = () => H - 34
const rand = (a, b) => a + Math.random() * (b - a)

function stageCfg(n) {
  return {
    count: Math.min(6 + n * 2, 32),
    fall: Math.max(5.2, 15 - n * 0.52), // giây để rơi hết màn
    gap: Math.max(0.7, 2.4 - n * 0.09) / Math.sqrt(speedF.value),
    maxOn: Math.min(3 + Math.floor(n / 2), 11),
    maxLen: n <= 3 ? 2 : n <= 7 ? 3 : 99,
    bpm: Math.min(124 + n * 2.2, 168),
  }
}

function shuffle(a) {
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1))
    ;[a[i], a[j]] = [a[j], a[i]]
  }
  return a
}

function pickCard(maxLen) {
  const onScreen = new Set(words.map((w) => w.card.vocab_id))
  const fits = (c) => !onScreen.has(c.vocab_id) && [...c.hanzi].length <= maxLen
  if (!bag.length) bag = shuffle([...deckAll])
  let i = bag.findIndex(fits)
  if (i < 0 && bag.length < deckAll.length) {
    bag = shuffle([...deckAll])
    i = bag.findIndex(fits)
  }
  if (i < 0) i = bag.findIndex((c) => !onScreen.has(c.vocab_id))
  if (i >= 0) return bag.splice(i, 1)[0]
  return deckAll[Math.floor(Math.random() * deckAll.length)]
}

const HUES = [190, 280, 330, 45, 140, 210]
function rollItem() {
  if (wave.n < 2 || Math.random() > 0.11) return null
  if (words.some((w) => w.item)) return null
  const pool = ['slow', 'bomb', 'double', 'shield', 'heal'].filter((k) =>
    (k !== 'heal' || hud.lives < MAX_LIVES) && (k !== 'shield' || !effects.shield) &&
    (k !== 'slow' || effects.slow <= 0) && (k !== 'double' || effects.double <= 0))
  return pool.length ? pool[Math.floor(Math.random() * pool.length)] : null
}

function spawnWord(minion = false) {
  const cfg = stageCfg(wave.n)
  const card = pickCard(minion ? 2 : cfg.maxLen)
  ctx2d.font = `600 30px ${hanFont}`
  const tw = ctx2d.measureText(card.hanzi).width
  const w = Math.max(tw + 28, 64)
  let x = W / 2
  for (let k = 0; k < 10; k++) {
    x = rand(w / 2 + 16, W - w / 2 - 16)
    if (!words.some((o) => o.y < 90 && Math.abs(o.x - x) < (o.w + w) / 2 + 20)) break
  }
  const fallH = lineY() + 20
  const T = cfg.fall * (1 + Math.min([...card.hanzi].length - 1, 3) * 0.08)
  words.push({
    card, keys: card.keys, x, y: -24, w, h: 44,
    vy: fallH / T, vx: ((W / 2 - x) / T) * 0.3,
    typed: '', hint: false, typo: false, done: false, pending: 0, knock: 0,
    hue: HUES[Math.floor(Math.random() * HUES.length)], item: minion ? null : rollItem(),
  })
}

function spawnBoss() {
  if (!bossPool.length) return false
  const card = bossPool.shift()
  bossPool.push(card)
  const cfg = stageCfg(wave.n)
  ctx2d.font = `700 52px ${hanFont}`
  const tw = ctx2d.measureText(card.hanzi).width
  const w = Math.min(Math.max(tw + 48, 200), W - 40)
  const fallH = lineY() + 40
  const T = cfg.fall * 2.8
  words.push({
    card, keys: card.keys, x: W / 2, y: -70, w, h: 78, vy: fallH / T, vx: 0,
    typed: '', hint: true, typo: false, done: false, pending: 0, knock: 0, hue: 350, item: null, boss: true,
    total: Math.max(...card.keys.map((k) => k.length)),
  })
  banner = { text: 'BOSS THÀNH NGỮ!', sub: 'Gõ trọn pinyin cả cụm để hạ', life: 2.4, max: 2.4, boss: true }
  shake = 10
  sfx('alarm')
  return true
}

// ------------------------------------------------------------------ vòng lặp
function resize() {
  const c = cv.value
  if (!c || !root.value) return
  dpr = Math.min(window.devicePixelRatio || 1, 2)
  W = root.value.clientWidth
  H = root.value.clientHeight
  if (!W || !H) return
  c.width = W * dpr
  c.height = H * dpr
  c.style.width = W + 'px'
  c.style.height = H + 'px'
  ctx2d = c.getContext('2d')
  ship.x = W / 2
  ship.y = H - 70
  if (!stars.length || stars.length < (W * H) / 9000) {
    stars = Array.from({ length: Math.floor((W * H) / 7000) }, () => ({ x: Math.random() * W, y: Math.random() * H, z: Math.random() }))
  }
}

function loop(t) {
  raf = requestAnimationFrame(loop)
  const dt = Math.min((t - last) / 1000 || 0, 0.05)
  last = t
  if (phase.value === 'play') update(dt)
  else updateAmbient(dt)
  draw(t)
}

function updateAmbient(dt) {
  shake = Math.max(0, shake - dt * 30)
  flash = Math.max(0, flash - dt * 2)
  for (const s of stars) {
    s.y += (8 + s.z * 30) * dt
    if (s.y > H) { s.y = 0; s.x = Math.random() * W }
  }
  particles = particles.filter((p) => (p.life -= dt) > 0)
  floaters = floaters.filter((f) => (f.life -= dt) > 0)
}

function update(dt) {
  updateAmbient(dt)
  stats.time += dt
  ship.recoil = Math.max(0, ship.recoil - dt * 40)
  if (banner) { banner.life -= dt; if (banner.life <= 0) banner = null }

  if (effects.slow > 0) effects.slow = Math.max(0, effects.slow - dt)
  if (effects.double > 0) effects.double = Math.max(0, effects.double - dt)

  // đợt từ
  const cfg = stageCfg(wave.n)
  const bossStage = wave.n % BOSS_EVERY === 0
  if (wave.rest > 0) {
    wave.rest -= dt
    if (wave.rest <= 0 && wave.spawned >= cfg.count) nextWave()
  } else {
    wave.timer -= dt
    const alive = words.filter((w) => !w.done).length
    const bossAlive = words.some((w) => w.boss)
    if (wave.spawned < cfg.count) {
      if (wave.timer <= 0 && alive < cfg.maxOn) {
        spawnWord()
        wave.spawned++
        wave.timer = cfg.gap * rand(0.75, 1.25)
      }
    } else if (bossStage && !wave.bossSpawned) {
      // dọn xong lính thì boss xuất hiện
      if (!alive) {
        wave.bossSpawned = true
        if (spawnBoss()) wave.timer = 3
      }
    } else if (bossAlive && wave.timer <= 0 && alive < 3) {
      spawnWord(true) // lính hộ tống boss
      wave.timer = cfg.gap * 2.2 * rand(0.8, 1.2)
    }
    if (wave.spawned >= cfg.count && (!bossStage || wave.bossSpawned) && !words.length) {
      // qua mốc
      const bonus = 150 * wave.n + hud.lives * 40
      hud.score += bonus
      sfx('wave')
      if (wave.n >= STAGES) { endGame(true); return }
      banner = { text: `Qua mốc ${wave.n}!`, sub: `+${bonus} điểm`, life: 2.4, max: 2.4 }
      wave.rest = 2.6
    }
  }

  // chữ rơi
  const ly = lineY()
  let danger = 0
  const move = speedF.value * (effects.slow > 0 ? 0.35 : 1) * dt
  for (const w of words) {
    w.knock = Math.max(0, w.knock - dt * 60)
    w.y += w.vy * move
    w.x += w.vx * move
    if (!w.hint && !w.done && w.y > ly * 0.5) w.hint = true
    danger = Math.max(danger, w.y / ly)
    if (w.y + w.h / 2 >= ly && !w.dead) {
      w.dead = true
      breach(w)
    }
  }
  words = words.filter((w) => !w.dead)
  if (phase.value !== 'play') return
  audio?.setIntensity(words.some((w) => w.boss) ? 1 : Math.min(1, (wave.n - 1) / 10 + Math.max(0, danger - 0.6)))

  // đạn
  for (const b of bullets) {
    const tx = b.target.x
    const ty = b.target.y
    const dx = tx - b.x
    const dy = ty - b.y
    const d = Math.hypot(dx, dy)
    const step = 1500 * dt
    b.trail.push([b.x, b.y])
    if (b.trail.length > 6) b.trail.shift()
    if (d <= step || b.target.dead) {
      b.hit = true
      const w = b.target
      w.pending--
      if (!w.dead) {
        w.knock = w.boss ? 3 : 6
        burstAt(tx, ty + 8, `hsl(${w.hue} 90% 70%)`, w.boss ? 9 : 5, w.boss ? 200 : 120)
        if (w.done && w.pending <= 0) kill(w)
        else sfx(w.boss ? 'bossHit' : 'hit')
      }
    } else {
      b.x += (dx / d) * step
      b.y += (dy / d) * step
    }
  }
  bullets = bullets.filter((b) => !b.hit)

  for (const p of particles) {
    p.x += p.vx * dt
    p.y += p.vy * dt
    p.vx *= 1 - dt * 2
    p.vy = p.vy * (1 - dt * 2) + 40 * dt
  }
  for (const f of floaters) f.y -= 18 * dt

  // tàu xoay về mục tiêu
  const target = locked && !locked.dead ? locked : null
  const want = target ? Math.atan2(target.x - ship.x, ship.y - target.y) : 0
  ship.angle += (want - ship.angle) * Math.min(1, dt * 14)
}

function nextWave() {
  wave = { n: wave.n + 1, spawned: 0, timer: 0.6, rest: 0, bossSpawned: false }
  hud.stage = wave.n
  audio?.setTempo(stageCfg(wave.n).bpm)
  const sub = wave.n === STAGES ? 'Mốc cuối! Có boss ở cuối mốc' : wave.n % BOSS_EVERY === 0 ? 'Có boss ở cuối mốc!' : 'Chuẩn bị…'
  banner = { text: `Mốc ${wave.n}`, sub, life: 1.8, max: 1.8 }
}

function burstAt(x, y, color, n, speed) {
  for (let i = 0; i < n; i++) {
    const a = Math.random() * Math.PI * 2
    const s = rand(0.3, 1) * speed
    particles.push({ x, y, vx: Math.cos(a) * s, vy: Math.sin(a) * s, life: rand(0.3, 0.8), max: 0.8, color, size: rand(1.5, 3.5) })
  }
}

function addScore(p) {
  const pts = Math.round(p * speedF.value * (effects.double > 0 ? 2 : 1))
  hud.score += pts
  return pts
}

function record(card, result, boss = false) {
  const order = { clean: 0, rough: 1, miss: 2 }
  const key = card.vocab_id || `cy:${card.hanzi}`
  const prev = results.get(key)
  if (!prev || order[result] > order[prev.result]) results.set(key, { card, result, boss })
}

function kill(w) {
  w.dead = true
  if (locked === w) locked = null
  const n = [...w.card.hanzi].length
  stats.kills++
  words = words.filter((o) => o !== w)
  if (w.boss) {
    stats.bosses++
    const pts = addScore(250 * n * hud.mult)
    record(w.card, w.typo ? 'rough' : 'clean', true)
    for (let k = 0; k < 5; k++) burstAt(w.x + rand(-w.w / 2, w.w / 2), w.y + rand(-30, 30), `hsl(${[350, 45, 20][k % 3]} 95% 62%)`, 40, 420)
    burstAt(w.x, w.y, '#fff7c2', 40, 260)
    shake = 22
    flash = 0
    sfx('bossDown')
    floaters.push({ x: W / 2, y: Math.min(w.y, H * 0.45), card: w.card, life: 4.5, max: 4.5, bad: false, pts, big: true })
    return
  }
  // chữ có gợi ý Hán Việt chỉ được nửa điểm
  const pts = addScore(40 * n * hud.mult * (w.hint ? 0.5 : 1))
  record(w.card, w.typo || w.hint ? 'rough' : 'clean')
  burstAt(w.x, w.y, `hsl(${w.hue} 95% 65%)`, 26 + n * 8, 320)
  burstAt(w.x, w.y, '#fff7c2', 10, 160)
  shake = Math.max(shake, 4 + n)
  sfx('explode', n)
  floaters.push({ x: w.x, y: w.y, card: w.card, life: 2.4, max: 2.4, bad: false, pts })
  if (w.item) activateItem(w.item, w)
}

function activateItem(k, src) {
  const it = ITEMS[k]
  floaters.push({ x: src.x, y: src.y - 50, label: `${it.icon} ${it.label}!`, color: it.color, life: 1.6, max: 1.6 })
  burstAt(src.x, src.y, it.color, 30, 260)
  if (k === 'slow') effects.slow = 7
  else if (k === 'double') effects.double = 10
  else if (k === 'shield') effects.shield = true
  else if (k === 'heal') hud.lives = Math.min(MAX_LIVES, hud.lives + 1)
  else if (k === 'bomb') {
    // nổ sạch chữ thường trên màn (boss không bị ảnh hưởng); không tính vào lịch ôn vì không gõ
    for (const w of words) {
      if (w.boss) continue
      w.dead = true
      if (locked === w) locked = null
      stats.kills++
      addScore(15 * [...w.card.hanzi].length)
      burstAt(w.x, w.y, `hsl(${w.hue} 95% 62%)`, 24, 300)
    }
    words = words.filter((w) => !w.dead)
    shake = 18
    flash = 0
    sfx('bomb')
    return
  }
  sfx(k === 'shield' ? 'shield' : 'powerup')
}

function breach(w) {
  if (phase.value !== 'play') return
  if (locked === w) locked = null
  setCombo(0)
  record(w.card, 'miss', !!w.boss)
  if (effects.shield && !w.boss) {
    // khiên chặn một chữ lọt
    effects.shield = false
    burstAt(w.x, lineY() - 14, ITEMS.shield.color, 40, 300)
    sfx('shield')
    floaters.push({ x: Math.min(Math.max(w.x, 120), W - 120), y: lineY() - 60, card: w.card, life: 3, max: 3, bad: true })
    return
  }
  hud.lives = Math.max(0, hud.lives - (w.boss ? 2 : 1))
  burstAt(w.x, lineY(), '#f87171', w.boss ? 90 : 40, 380)
  shake = w.boss ? 26 : 16
  flash = 1
  sfx('damage')
  floaters.push({ x: Math.min(Math.max(w.x, 120), W - 120), y: lineY() - 60, card: w.card, life: 3, max: 3, bad: true })
  if (hud.lives <= 0) endGame(false)
}

function setCombo(c) {
  hud.combo = c
  stats.maxCombo = Math.max(stats.maxCombo, c)
  const m = Math.min(5, 1 + Math.floor(c / 10))
  if (m > hud.mult) sfx('combo')
  hud.mult = m
}

// ------------------------------------------------------------------ nhập phím
const same = (keyCh, c) => keyCh === c || (keyCh === 'v' && c === 'u')

function typeChar(c) {
  if (locked && (locked.dead || locked.done)) locked = null
  if (!locked) {
    let pick = null
    for (const w of words) {
      if (w.done || w.dead) continue
      if (w.keys.some((k) => same(k[0], c)) && (!pick || w.y > pick.y)) pick = w
    }
    if (!pick) return miss(null)
    locked = pick
    sfx('lock')
  }
  const w = locked
  const pos = w.typed.length
  const ok = w.keys.filter((k) => k.length > pos && same(k[pos], c))
  if (!ok.length) return miss(w)
  w.keys = ok
  w.typed += ok[0][pos]
  stats.correct++
  setCombo(hud.combo + 1)
  addScore(10 * hud.mult * (w.hint && !w.boss ? 0.5 : 1))
  w.pending++
  bullets.push({ x: ship.x + Math.sin(ship.angle) * 26, y: ship.y - Math.cos(ship.angle) * 26, target: w, trail: [] })
  ship.recoil = 5
  sfx('shoot', hud.combo)
  if (w.keys.some((k) => k.length === w.typed.length)) {
    w.done = true
    locked = null
  }
}

function miss(w) {
  stats.wrong++
  setCombo(0)
  if (w) { w.typo = true; w.knock = -6 }
  shake = Math.max(shake, 3)
  sfx('error')
}

function releaseLock() {
  if (!locked) return
  locked.keys = locked.card.keys
  locked.typed = ''
  locked = null
}

function onInput(e) {
  const v = e.target.value
  e.target.value = ''
  if (phase.value !== 'play') return
  const clean = v.normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/đ/gi, 'd').toLowerCase()
  for (const ch of clean) if (ch >= 'a' && ch <= 'z') typeChar(ch)
}

function onKeydown(e) {
  if (e.key === 'Escape') { e.preventDefault(); togglePause(); return }
  if (e.key === 'Enter') {
    e.preventDefault()
    if (phase.value === 'paused') togglePause()
    else if (phase.value === 'setup' && opts.value?.counts.all && !busy.value) start()
    else if (phase.value === 'over') start()
    return
  }
  if (e.key === 'Backspace' && phase.value === 'play') { e.preventDefault(); releaseLock() }
}

// phím Enter/Esc khi ô nhập ẩn chưa có focus (ví dụ đang ở màn chọn)
function onWindowKey(e) {
  if (document.activeElement === kb.value) return
  if (e.target.closest?.('select, input, button, a')) return
  if (e.key === 'Enter' || e.key === 'Escape') onKeydown(e)
}

function focusKb(e) {
  if (e?.target?.closest?.('select, button, a, label, .panel')) return
  if (phase.value === 'play') kb.value?.focus({ preventScroll: true })
}

function togglePause() {
  if (phase.value === 'play') {
    phase.value = 'paused'
    audio?.suspend()
  } else if (phase.value === 'paused') {
    phase.value = 'play'
    audio?.resume()
    last = performance.now()
    kb.value?.focus({ preventScroll: true })
  }
}
function toggleFull() {
  if (document.fullscreenElement) document.exitFullscreen?.()
  else root.value?.requestFullscreen?.().catch(() => {})
  focusKb()
}
function onFullChange() {
  isFull.value = document.fullscreenElement === root.value
}

function onBlur() { if (phase.value === 'play') togglePause() }
function onVisibility() { if (document.hidden) onBlur() }

// ------------------------------------------------------------------ bắt đầu / kết thúc
async function start(cards) {
  err.value = ''
  busy.value = true
  ensureAudio()
  try {
    let list = cards
    if (!list) {
      savePrefs()
      const id = scope.value === 'unit' || scope.value === 'book' ? Number(refKey.value.split(':')[1]) : null
      const [deck, bosses] = await Promise.all([
        api.post('/api/game/deck', { scope: scope.value, id }),
        api.post('/api/game/bosses', { scope: scope.value, id }).catch(() => []),
      ])
      list = deck
      bossPool = bosses
      scopeLabel.value = currentScopeLabel()
    } else {
      list = list.map((w) => w.card || w)
      if (!bossPool.length) bossPool = await api.post('/api/game/bosses', {}).catch(() => [])
      scopeLabel.value = 'Từ cần xem lại'
    }
    if (!list.length) { err.value = 'Kho từ này chưa có từ nào.'; phase.value = 'setup'; return }
    deckAll = list
    bag = []
    words = []
    bullets = []
    particles = []
    floaters = []
    locked = null
    results = new Map()
    stats = { correct: 0, wrong: 0, kills: 0, bosses: 0, time: 0, maxCombo: 0 }
    Object.assign(effects, { slow: 0, double: 0, shield: false })
    Object.assign(hud, { score: 0, stage: 1, lives: MAX_LIVES, combo: 0, mult: 1 })
    won.value = false
    wave = { n: 0 }
    nextWave()
    audio?.setIntensity(0)
    audio?.startMusic()
    phase.value = 'play'
    last = performance.now()
    requestAnimationFrame(() => kb.value?.focus({ preventScroll: true }))
  } catch (e) {
    err.value = e.message
    phase.value = 'setup'
  } finally {
    busy.value = false
  }
}

function endGame(victory) {
  won.value = victory
  phase.value = 'over'
  locked = null
  audio?.resume()
  audio?.stopMusic()
  sfx(victory ? 'wave' : 'gameOver')
  if (!victory) words.forEach((w) => burstAt(w.x, w.y, `hsl(${w.hue} 90% 60%)`, 12, 200))
  words = []
  const typed = stats.correct + stats.wrong
  const newBest = hud.score > best.value
  if (newBest) { best.value = hud.score; savePrefs() }
  const all = [...results.values()]
  Object.assign(summary, {
    score: hud.score,
    stage: hud.stage,
    kills: stats.kills,
    bosses: stats.bosses,
    acc: typed ? Math.round((stats.correct / typed) * 100) : 0,
    cpm: stats.time > 5 ? Math.round(stats.correct / (stats.time / 60)) : stats.correct,
    maxCombo: stats.maxCombo,
    newBest,
    review: all.filter((r) => r.result !== 'clean').sort((a, b) => (a.result === 'miss' ? -1 : 1) - (b.result === 'miss' ? -1 : 1))
      .map((r) => ({ ...r.card, result: r.result, boss: r.boss, card: r.card })),
  })
  kb.value?.blur()
  if (scopeLabel.value !== 'Từ cần xem lại') {
    const rows = all.filter((r) => r.card.vocab_id).map((r) => ({ vocab_id: r.card.vocab_id, result: r.result }))
    if (rows.length) api.post('/api/game/results', { results: rows }).catch(() => {})
  }
}

// ------------------------------------------------------------------ vẽ
function roundRect(c, x, y, w, h, r) {
  c.beginPath()
  c.moveTo(x + r, y)
  c.arcTo(x + w, y, x + w, y + h, r)
  c.arcTo(x + w, y + h, x, y + h, r)
  c.arcTo(x, y + h, x, y, r)
  c.arcTo(x, y, x + w, y, r)
  c.closePath()
}

function draw(t) {
  const c = ctx2d
  if (!c) return
  c.setTransform(dpr, 0, 0, dpr, 0, 0)
  const g = c.createLinearGradient(0, 0, 0, H)
  g.addColorStop(0, '#0b0e22')
  g.addColorStop(0.65, '#151233')
  g.addColorStop(1, '#2a1238')
  c.fillStyle = g
  c.fillRect(0, 0, W, H)

  for (const s of stars) {
    c.globalAlpha = 0.25 + s.z * 0.6
    c.fillStyle = '#cdd6ff'
    c.fillRect(s.x, s.y, 1 + s.z * 1.2, 1 + s.z * 1.2)
  }
  c.globalAlpha = 1

  const sx = shake ? rand(-shake, shake) : 0
  const sy = shake ? rand(-shake, shake) : 0
  c.save()
  c.translate(sx, sy)

  // vạch phòng thủ
  const ly = lineY()
  const lg = c.createLinearGradient(0, ly - 30, 0, ly + 10)
  lg.addColorStop(0, 'rgba(248,113,113,0)')
  lg.addColorStop(1, 'rgba(248,113,113,0.18)')
  c.fillStyle = lg
  c.fillRect(0, ly - 30, W, 40)
  c.fillStyle = '#ef4444'
  c.shadowColor = '#ef4444'
  c.shadowBlur = 12
  c.fillRect(0, ly, W, 2)
  c.shadowBlur = 0
  if (effects.shield && phase.value === 'play') {
    c.fillStyle = ITEMS.shield.color
    c.shadowColor = ITEMS.shield.color
    c.shadowBlur = 16
    c.globalAlpha = 0.7 + Math.sin(t / 160) * 0.25
    c.fillRect(0, ly - 14, W, 3)
    c.globalAlpha = 1
    c.shadowBlur = 0
  }

  if (phase.value !== 'setup') {
    // chữ
    for (const w of words) drawWord(c, w, t)

    // đạn
    c.globalCompositeOperation = 'lighter'
    for (const b of bullets) {
      c.strokeStyle = 'rgba(253, 224, 71, 0.9)'
      c.lineWidth = 3
      c.lineCap = 'round'
      c.beginPath()
      const [tx, ty] = b.trail[0] || [b.x, b.y]
      c.moveTo(tx, ty)
      c.lineTo(b.x, b.y)
      c.stroke()
      c.fillStyle = '#fff'
      c.beginPath()
      c.arc(b.x, b.y, 2.5, 0, Math.PI * 2)
      c.fill()
    }
    // hạt nổ
    for (const p of particles) {
      c.globalAlpha = Math.max(0, p.life / p.max)
      c.fillStyle = p.color
      c.beginPath()
      c.arc(p.x, p.y, p.size, 0, Math.PI * 2)
      c.fill()
    }
    c.globalAlpha = 1
    c.globalCompositeOperation = 'source-over'

    // đáp án hiện sau khi hạ / để lọt
    for (const f of floaters) drawFloater(c, f)

    drawShip(c, t)
  }
  c.restore()

  if (effects.slow > 0 && phase.value === 'play') {
    c.fillStyle = `rgba(56, 189, 248, ${0.08 * Math.min(1, effects.slow)})`
    c.fillRect(0, 0, W, H)
  }

  // chớp đỏ khi mất mạng
  if (flash > 0) {
    const rg = c.createRadialGradient(W / 2, H / 2, Math.min(W, H) * 0.3, W / 2, H / 2, Math.max(W, H) * 0.7)
    rg.addColorStop(0, 'rgba(239,68,68,0)')
    rg.addColorStop(1, `rgba(239,68,68,${0.45 * flash})`)
    c.fillStyle = rg
    c.fillRect(0, 0, W, H)
  }

  if (banner && phase.value === 'play') {
    const k = banner.life / banner.max
    const a = Math.min(1, k * 4, (1 - k) * 6)
    c.globalAlpha = a
    c.textAlign = 'center'
    c.fillStyle = banner.boss ? '#fca5a5' : '#fde68a'
    c.font = '900 46px Nunito, system-ui, sans-serif'
    c.shadowColor = banner.boss ? 'rgba(239, 68, 68, 0.8)' : 'rgba(250, 204, 21, 0.6)'
    c.shadowBlur = 24
    c.fillText(banner.text, W / 2, H * 0.4)
    c.shadowBlur = 0
    c.font = '700 18px Nunito, system-ui, sans-serif'
    c.fillStyle = '#e0e7ff'
    c.fillText(banner.sub, W / 2, H * 0.4 + 34)
    c.globalAlpha = 1
  }
}

function drawWord(c, w, t) {
  const isLocked = locked === w
  const big = !!w.boss
  const x = w.x
  const y = w.y - w.knock
  const top = y - w.h / 2
  const left = x - w.w / 2
  c.save()
  if (w.done) c.globalAlpha = 0.55
  // quầng màu bên dưới
  const gr = w.w * (big ? 0.9 : 0.7)
  const glow = c.createRadialGradient(x, y + 8, 2, x, y + 8, gr)
  glow.addColorStop(0, `hsla(${w.hue}, 90%, 60%, ${isLocked || big ? 0.45 : 0.28})`)
  glow.addColorStop(1, `hsla(${w.hue}, 90%, 60%, 0)`)
  c.fillStyle = glow
  c.fillRect(x - gr, y + 8 - gr, gr * 2, gr * 2)

  roundRect(c, left, top, w.w, w.h, big ? 14 : 8)
  c.fillStyle = big ? 'rgba(40, 6, 18, 0.9)' : 'rgba(8, 10, 28, 0.82)'
  c.fill()
  const item = w.item && ITEMS[w.item]
  if (isLocked) {
    c.strokeStyle = '#facc15'
    c.lineWidth = big ? 3 : 2.5
    c.shadowColor = '#facc15'
    c.shadowBlur = 12 + Math.sin(t / 90) * 4
    c.stroke()
  } else if (big) {
    c.strokeStyle = '#ef4444'
    c.lineWidth = 2.5
    c.shadowColor = '#ef4444'
    c.shadowBlur = 14 + Math.sin(t / 120) * 8
    c.stroke()
  } else if (item) {
    c.strokeStyle = item.color
    c.lineWidth = 2
    c.setLineDash([5, 4])
    c.lineDashOffset = -t / 40
    c.shadowColor = item.color
    c.shadowBlur = 10
    c.stroke()
    c.setLineDash([])
  }
  c.shadowBlur = 0
  c.textAlign = 'center'
  c.textBaseline = 'middle'
  c.font = big ? `700 52px ${hanFont}` : `600 30px ${hanFont}`
  c.fillStyle = isLocked ? '#fef9c3' : '#ffffff'
  c.fillText(w.card.hanzi, x, y + (big ? 2 : 1))

  if (item) {
    // huy hiệu vật phẩm ở góc
    const bx = left + w.w - 2
    const by = top + 2
    c.fillStyle = 'rgba(8, 10, 28, 0.95)'
    c.strokeStyle = item.color
    c.lineWidth = 2
    c.beginPath()
    c.arc(bx, by, 12, 0, Math.PI * 2)
    c.fill()
    c.stroke()
    c.font = '13px system-ui, "Apple Color Emoji", "Segoe UI Emoji", sans-serif'
    c.fillText(item.icon, bx, by + 1)
  }

  if (big) {
    // nhãn BOSS + thanh máu theo phần pinyin còn lại
    c.font = '900 11px Nunito, system-ui, sans-serif'
    const lw = c.measureText('BOSS').width + 14
    roundRect(c, left + 10, top - 9, lw, 18, 9)
    c.fillStyle = '#ef4444'
    c.fill()
    c.fillStyle = '#fff'
    c.fillText('BOSS', left + 10 + lw / 2, top + 1)
    const hp = 1 - w.typed.length / w.total
    const bw = w.w - 20
    roundRect(c, x - bw / 2, top - 22, bw, 7, 4)
    c.fillStyle = 'rgba(255, 255, 255, 0.12)'
    c.fill()
    if (hp > 0) {
      roundRect(c, x - bw / 2, top - 22, Math.max(7, bw * hp), 7, 4)
      c.fillStyle = hp > 0.5 ? '#f43f5e' : hp > 0.25 ? '#fb923c' : '#facc15'
      c.fill()
    }
  }

  let below = top + w.h + (big ? 16 : 14)
  if (w.hint && w.card.han_viet) {
    c.font = big ? '800 15px Nunito, system-ui, sans-serif' : '800 12px Nunito, system-ui, sans-serif'
    c.fillStyle = 'rgba(252, 211, 77, 0.9)'
    c.fillText(w.card.han_viet, x, below)
    below += big ? 22 : 18
  }
  if (w.typed) {
    c.font = `700 ${big ? 20 : 17}px ui-monospace, Menlo, Consolas, monospace`
    const tw = c.measureText(w.typed).width
    roundRect(c, x - tw / 2 - 6, below - 12, tw + 12, 24, 6)
    c.fillStyle = 'rgba(8, 10, 28, 0.85)'
    c.fill()
    c.fillStyle = '#4ade80'
    c.fillText(w.typed, x, below + 1)
  }
  c.restore()
}

function drawFloater(c, f) {
  const k = f.life / f.max
  const a = Math.min(1, k * 2.5, (1 - k) * 8)
  c.save()
  c.globalAlpha = a
  c.textAlign = 'center'
  c.textBaseline = 'middle'
  if (f.label) {
    c.font = '900 22px Nunito, system-ui, "Apple Color Emoji", "Segoe UI Emoji", sans-serif'
    c.fillStyle = f.color
    c.shadowColor = f.color
    c.shadowBlur = 14
    c.fillText(f.label, f.x, f.y)
    c.restore()
    return
  }
  const big = !!f.big
  const sub = [f.card.han_viet, f.card.meaning].filter(Boolean).join(' · ')
  if (big) {
    c.font = '900 13px Nunito, system-ui, sans-serif'
    c.fillStyle = '#fca5a5'
    c.fillText('THÀNH NGỮ ĐÃ HẠ', f.x, f.y - 44)
  }
  c.font = big ? `700 34px ${hanFont}` : '800 20px Nunito, system-ui, sans-serif'
  c.fillStyle = f.bad ? '#fca5a5' : '#86efac'
  c.fillText(big ? f.card.hanzi : `${f.card.hanzi}  ${f.card.pinyin}`, f.x, f.y)
  if (big) {
    c.font = '800 20px Nunito, system-ui, sans-serif'
    c.fillText(f.card.pinyin, f.x, f.y + 32)
  }
  c.font = big ? '700 17px Nunito, system-ui, sans-serif' : '700 14px Nunito, system-ui, sans-serif'
  c.fillStyle = 'rgba(226, 232, 255, 0.9)'
  c.fillText(sub, f.x, f.y + (big ? 60 : 22))
  if (f.pts) {
    c.font = `900 ${big ? 20 : 14}px Nunito, system-ui, sans-serif`
    c.fillStyle = '#fde047'
    c.fillText(`+${f.pts}`, f.x, f.y - (big ? 70 : 22))
  }
  c.restore()
}

function drawShip(c, t) {
  c.save()
  c.translate(ship.x, ship.y + ship.recoil)
  c.rotate(ship.angle)
  // lửa động cơ
  const fl = 14 + Math.sin(t / 40) * 4 + Math.random() * 3
  const fg = c.createLinearGradient(0, 16, 0, 16 + fl)
  fg.addColorStop(0, 'rgba(253, 224, 71, 0.95)')
  fg.addColorStop(1, 'rgba(249, 115, 22, 0)')
  c.fillStyle = fg
  c.beginPath()
  c.moveTo(-6, 16)
  c.lineTo(0, 16 + fl)
  c.lineTo(6, 16)
  c.fill()
  // cánh
  c.fillStyle = '#1d4ed8'
  c.beginPath()
  c.moveTo(-8, 2)
  c.lineTo(-22, 18)
  c.lineTo(-8, 16)
  c.moveTo(8, 2)
  c.lineTo(22, 18)
  c.lineTo(8, 16)
  c.fill()
  // thân
  const bg = c.createLinearGradient(-10, 0, 10, 0)
  bg.addColorStop(0, '#38bdf8')
  bg.addColorStop(0.5, '#7dd3fc')
  bg.addColorStop(1, '#0ea5e9')
  c.fillStyle = bg
  c.shadowColor = '#38bdf8'
  c.shadowBlur = 18
  c.beginPath()
  c.moveTo(0, -28)
  c.quadraticCurveTo(11, -12, 9, 16)
  c.lineTo(-9, 16)
  c.quadraticCurveTo(-11, -12, 0, -28)
  c.fill()
  c.shadowBlur = 0
  // cửa sổ
  c.fillStyle = '#f59e0b'
  c.strokeStyle = '#1e3a8a'
  c.lineWidth = 2
  c.beginPath()
  c.ellipse(0, -6, 4, 6, 0, 0, Math.PI * 2)
  c.fill()
  c.stroke()
  c.restore()
}

// ------------------------------------------------------------------ vòng đời
onMounted(async () => {
  loadPrefs()
  hanFont = getComputedStyle(document.documentElement).getPropertyValue('--font-han').trim() || 'serif'
  resize()
  ro = new ResizeObserver(resize)
  ro.observe(root.value)
  document.addEventListener('fullscreenchange', onFullChange)
  window.addEventListener('blur', onBlur)
  window.addEventListener('keydown', onWindowKey)
  document.addEventListener('visibilitychange', onVisibility)
  raf = requestAnimationFrame(loop)
  try {
    opts.value = await api.get('/api/drill/pinyin/options')
    const valid = opts.value.books.some((b) => refKey.value === `book:${b.id}` || b.units.some((u) => refKey.value === `unit:${u.id}`))
    if (!valid) {
      refKey.value = ''
      if (scope.value === 'unit' || scope.value === 'book') scope.value = 'all'
    }
    if (quickScopes.some((s) => s.k === scope.value) && !opts.value.counts[scope.value]) scope.value = 'all'
  } catch (e) {
    err.value = e.message
  }
})

onBeforeUnmount(() => {
  cancelAnimationFrame(raf)
  ro?.disconnect()
  document.removeEventListener('fullscreenchange', onFullChange)
  if (document.fullscreenElement === root.value) document.exitFullscreen?.()
  window.removeEventListener('blur', onBlur)
  window.removeEventListener('keydown', onWindowKey)
  document.removeEventListener('visibilitychange', onVisibility)
  audio?.close()
  audio = null
})
</script>

<style scoped>
/* nằm trong khung app (menu trái vẫn hiện); bấm nút toàn màn hình để chơi to */
.ts { position: relative; height: calc(100dvh - 32px); margin: 16px 16px 16px 20px; border-radius: var(--r); overflow: hidden; background: #0b0e22; color: #e5e9ff; font-family: var(--font-ui); box-shadow: var(--shadow); }
.ts:fullscreen { margin: 0; height: 100%; border-radius: 0; }
.cv { position: absolute; inset: 0; display: block; }
.kb { position: absolute; left: 50%; bottom: 0; width: 1px; height: 1px; opacity: 0; border: 0; padding: 0; pointer-events: none; font-size: 16px; }

.hud { position: absolute; top: 12px; left: 12px; right: 12px; display: flex; align-items: flex-start; justify-content: space-between; gap: 10px; pointer-events: none; }
.pill { display: inline-flex; align-items: center; gap: 7px; padding: 6px 13px; border-radius: 999px; background: rgba(8, 10, 28, 0.75); border: 1px solid rgba(148, 163, 255, 0.18); font-size: 14px; white-space: nowrap; }
.pill b { font-weight: 900; font-variant-numeric: tabular-nums; }
.dim { color: #9aa5d6; }
.stage { position: absolute; left: 50%; transform: translateX(-50%); }
.left { display: flex; flex-direction: column; align-items: flex-start; gap: 6px; }
.fx { font-size: 13px; animation: pop2 .3s cubic-bezier(.34, 1.56, .64, 1); }
.fx.slow { border-color: rgba(56, 189, 248, .6); color: #bae6fd; }
.fx.double { border-color: rgba(250, 204, 21, .6); color: #fef08a; }
.fx.shield { border-color: rgba(34, 211, 238, .6); color: #a5f3fc; }
@keyframes pop2 { from { transform: scale(1.3); opacity: 0; } }
.bosstag { margin-left: 4px; font-size: 10px; font-weight: 900; padding: 2px 7px; border-radius: 999px; background: #ef4444; color: #fff; }
.small { font-size: 13px; }
.itm { display: inline-block; margin-right: 8px; white-space: nowrap; }
.chips.center { justify-content: center; }
.right { display: flex; flex-direction: column; align-items: flex-end; gap: 8px; }
.heart { color: #fb7185; font-size: 15px; transition: color .3s, transform .3s; }
.heart.lost { color: #3b3f5c; transform: scale(.8); }
.tools { display: flex; flex-direction: column; gap: 6px; pointer-events: auto; }
.tool { width: 34px; height: 34px; border-radius: 10px; border: 1px solid rgba(148, 163, 255, 0.18); background: rgba(8, 10, 28, 0.75); color: #c7d2fe; display: inline-flex; align-items: center; justify-content: center; cursor: pointer; }
.tool:hover { color: #fff; border-color: rgba(250, 204, 21, 0.6); }
.combo { position: absolute; bottom: 118px; left: 50%; transform: translateX(-50%); font-weight: 900; font-size: 22px; color: #fde047; text-shadow: 0 0 16px rgba(250, 204, 21, .6); animation: pop .35s cubic-bezier(.34, 1.56, .64, 1); pointer-events: none; }
.combo small { font-size: 12px; color: #fef3c7; font-weight: 700; }
@keyframes pop { from { transform: translateX(-50%) scale(1.6); opacity: 0; } }
.foot { position: absolute; bottom: 8px; left: 50%; transform: translateX(-50%); padding: 3px 12px; border-radius: 999px; background: rgba(8, 10, 28, 0.85); color: #9aa5d6; font-size: 12px; white-space: nowrap; pointer-events: none; max-width: calc(100% - 32px); overflow: hidden; text-overflow: ellipsis; }

.overlay { position: absolute; inset: 0; display: flex; align-items: center; justify-content: center; padding: 16px; background: rgba(5, 6, 20, 0.45); backdrop-filter: blur(2px); overflow-y: auto; }
.panel { width: min(560px, 100%); max-height: calc(100dvh - 32px); overflow-y: auto; display: flex; flex-direction: column; gap: 16px; padding: 28px; border-radius: 24px; background: rgba(14, 16, 40, 0.92); border: 1px solid rgba(148, 163, 255, 0.2); box-shadow: 0 30px 80px -20px rgba(0, 0, 0, .7), 0 0 0 1px rgba(250, 204, 21, 0.05); }
.panel.small { width: min(460px, 100%); align-items: center; text-align: center; }
.panel.wide { width: min(720px, 100%); }
.panel h1 { font-size: 30px; font-weight: 900; color: #fff; margin: 0; display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.panel h2 { font-size: 24px; font-weight: 900; color: #fff; margin: 0; }
.eyebrow { font-size: 12px; font-weight: 800; letter-spacing: .08em; text-transform: uppercase; color: #fcd34d; }
.brandline { display: flex; align-items: center; gap: 14px; }
.seal { width: 52px; height: 52px; border-radius: 14px; background: #e11d48; color: #fff; font-size: 30px; display: inline-flex; align-items: center; justify-content: center; transform: rotate(-8deg); box-shadow: 0 0 24px rgba(225, 29, 72, .5); flex: none; }
.lead { color: #c7d0f5; line-height: 1.6; margin: 0; }
.lead .han { font-size: 18px; color: #fff; }
kbd { font-family: ui-monospace, Menlo, monospace; background: rgba(74, 222, 128, .12); color: #4ade80; padding: 1px 7px; border-radius: 6px; }
.err { color: #fca5a5; margin: 0; }
.field { display: flex; flex-direction: column; gap: 8px; }
.lbl { font-size: 12px; font-weight: 800; letter-spacing: .06em; text-transform: uppercase; color: #9aa5d6; }
.chips { display: flex; flex-wrap: wrap; gap: 8px; }
.chip { border: 1px solid rgba(148, 163, 255, 0.25); background: rgba(255, 255, 255, 0.04); color: #dfe4ff; padding: 7px 13px; border-radius: 999px; font: inherit; font-weight: 800; font-size: 14px; cursor: pointer; }
.chip small { color: #9aa5d6; font-weight: 700; margin-left: 2px; }
.chip.on { background: #facc15; color: #1c1405; border-color: #facc15; }
.chip.on small { color: #5b4706; }
.chip:disabled { opacity: .4; cursor: not-allowed; }
.sel { width: 100%; padding: 10px 12px; border-radius: 12px; background: #0b0e22; color: #e5e9ff; border: 1px solid rgba(148, 163, 255, 0.3); font: inherit; }
.toggles { flex-direction: row; gap: 18px; flex-wrap: wrap; }
.toggles label { display: flex; align-items: center; gap: 8px; font-weight: 700; cursor: pointer; color: #dfe4ff; }
.toggles input { width: 17px; height: 17px; accent-color: #facc15; }
.tips { margin: 0; padding-left: 18px; color: #aab4e0; font-size: 14px; line-height: 1.7; }
.row { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.go { border: 0; padding: 12px 24px; border-radius: 14px; background: linear-gradient(180deg, #fde047, #f59e0b); color: #1c1405; font: inherit; font-weight: 900; font-size: 16px; cursor: pointer; box-shadow: 0 4px 0 #b45309, 0 0 30px rgba(250, 204, 21, .35); white-space: pre; transition: transform .15s; }
.go:hover { transform: translateY(-1px); }
.go:active { transform: translateY(2px); box-shadow: 0 2px 0 #b45309; }
.go:disabled { opacity: .6; cursor: wait; }
.ghost { border: 1px solid rgba(148, 163, 255, 0.3); background: transparent; color: #dfe4ff; padding: 11px 18px; border-radius: 14px; font: inherit; font-weight: 800; cursor: pointer; text-decoration: none; }
.ghost:hover { border-color: #facc15; color: #fff; }
.exit { color: #9aa5d6; font-size: 14px; text-decoration: none; align-self: flex-start; }
.exit:hover { color: #fff; }

.badge { font-size: 13px; font-weight: 900; padding: 4px 10px; border-radius: 999px; background: #facc15; color: #1c1405; }
.stats { display: grid; grid-template-columns: repeat(6, 1fr); gap: 10px; }
.stats div { display: flex; flex-direction: column; align-items: center; gap: 2px; padding: 12px 6px; border-radius: 14px; background: rgba(255, 255, 255, 0.04); border: 1px solid rgba(148, 163, 255, 0.12); }
.stats b { font-size: 22px; font-weight: 900; color: #fff; font-variant-numeric: tabular-nums; }
.stats span { font-size: 12px; color: #9aa5d6; text-align: center; }
.review { display: flex; flex-direction: column; gap: 8px; }
.rv-list { display: flex; flex-direction: column; gap: 6px; max-height: 280px; overflow-y: auto; }
.rv { display: grid; grid-template-columns: auto auto auto auto 1fr auto; align-items: center; gap: 10px; padding: 8px 12px; border-radius: 12px; background: rgba(255, 255, 255, 0.04); }
.rvh { font-size: 24px; color: #fff; }
.py { color: #4ade80; font-weight: 800; }
.hv { color: #fcd34d; font-size: 12px; font-weight: 800; }
.mean { font-size: 14px; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.tag { font-size: 11px; font-weight: 800; padding: 3px 8px; border-radius: 999px; white-space: nowrap; }
.tag.miss { background: rgba(248, 113, 113, .15); color: #fca5a5; }
.tag.rough { background: rgba(250, 204, 21, .12); color: #fde68a; }

@media (max-width: 760px) {
  .ts { height: calc(100dvh - 104px); margin: 10px; }
}
@media (max-width: 640px) {
  .stage { position: static; transform: none; }
  .hud { flex-wrap: wrap; }
  .stage .dim { display: none; }
  .panel { padding: 20px; }
  .stats { grid-template-columns: repeat(3, 1fr); }
  .rv { grid-template-columns: auto auto 1fr auto; }
  .rv .hv, .rv .tag { display: none; }
  .foot { font-size: 11px; }
}
</style>

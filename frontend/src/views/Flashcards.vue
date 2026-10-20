<template>
  <div class="page">
    <div class="row spread wrap" style="margin-bottom: 18px">
      <div>
        <span class="eyebrow">Luyện riêng</span>
        <h1>Flashcard</h1>
      </div>
      <button v-if="phase !== 'setup'" class="btn ghost" type="button" @click="phase = 'setup'">← Chọn lại</button>
    </div>
    <p v-if="err" class="notice err" style="margin-bottom: 14px">{{ err }}</p>

    <!-- chọn bộ thẻ -->
    <section v-if="phase === 'setup'" class="card setup">
      <div v-if="!opts" class="empty">Đang tải…</div>
      <div v-else-if="!opts.counts.all" class="empty">
        Chưa có từ nào. <RouterLink to="/library">Nhập file từ vựng</RouterLink> trước nhé.
      </div>
      <template v-else>
        <div class="field">
          <span class="label">Ôn từ nào</span>
          <div class="row wrap" style="gap: 8px">
            <button v-for="s in quickScopes" :key="s.k" type="button" class="btn" :class="{ primary: scope === s.k }"
              :disabled="!opts.counts[s.k]" @click="scope = s.k">{{ s.label }} ({{ opts.counts[s.k] }})</button>
            <button type="button" class="btn" :class="{ primary: scope === 'unit' || scope === 'book' }" @click="pickUnitScope">Theo quyển / bài</button>
          </div>
        </div>

        <div v-if="scope === 'unit' || scope === 'book'" class="field">
          <span class="label">Quyển / bài</span>
          <select v-model="refKey" class="select">
            <template v-for="b in opts.books" :key="b.id">
              <option :value="`book:${b.id}`">{{ b.title }} — cả quyển ({{ b.word_count }} từ)</option>
              <option v-for="u in b.units" :key="u.id" :value="`unit:${u.id}`">　{{ u.idx }}. {{ u.title_zh ? u.title_zh + ' · ' : '' }}{{ u.title_vi }} ({{ u.word_count }})</option>
            </template>
          </select>
        </div>

        <div class="field">
          <span class="label">Mặt trước của thẻ</span>
          <div class="row wrap" style="gap: 8px">
            <button v-for="d in directions" :key="d.k" type="button" class="btn" :class="{ primary: direction === d.k }"
              @click="direction = d.k">{{ d.label }}</button>
          </div>
        </div>

        <div class="field">
          <span class="label">Số thẻ mỗi lượt</span>
          <div class="row wrap" style="gap: 8px">
            <button v-for="n in [10, 20, 30, 0]" :key="n" type="button" class="btn" :class="{ primary: limit === n }" @click="limit = n">{{ n || 'Tất cả' }}</button>
          </div>
        </div>

        <div class="field toggles">
          <label><input v-model="autoSpeak" type="checkbox" /> Tự đọc từ khi lật thẻ</label>
          <label><input v-model="shuffle" type="checkbox" /> Trộn thứ tự thẻ</label>
          <label><input v-model="retryForgot" type="checkbox" /> Thẻ "Quên" quay lại cuối lượt</label>
        </div>

        <p class="small muted">Lật thẻ rồi tự chấm: <b>Quên</b> · <b>Khó</b> · <b>Nhớ</b> · <b>Dễ</b>. Lần chấm đầu của mỗi thẻ được ghi vào lịch ôn từ vựng.
          Phím tắt: <kbd>Space</kbd> lật, <kbd>1</kbd>–<kbd>4</kbd> chấm, <kbd>←</kbd> <kbd>→</kbd> xem lại thẻ trước.</p>
        <button class="btn primary lg" type="button" :disabled="busy" @click="start()">Bắt đầu</button>
      </template>
    </section>

    <!-- đang ôn -->
    <section v-else-if="phase === 'study' && shown" class="study">
      <div class="row spread head">
        <span class="eyebrow">{{ peeking ? 'Xem lại thẻ trước' : shown.retry ? 'Ôn lại thẻ quên' : directionLabel }}</span>
        <span class="tiny faint">{{ Math.min(idx + 1, queue.length) }} / {{ queue.length }} · đã nhớ {{ stats.remembered }}</span>
      </div>
      <div class="bar" style="margin-bottom: 18px"><span :style="{ width: (idx / queue.length) * 100 + '%' }"></span></div>

      <div class="flip" :class="{ flipped: isFlipped }" role="button" tabindex="0"
        :aria-label="isFlipped ? 'Mặt sau thẻ' : 'Bấm để lật thẻ'" @click="flip()" @keydown.enter.self.prevent="flip()">
        <div class="face front card">
          <template v-if="direction === 'hz'">
            <TianZiGe :text="shown.hanzi" :size="gridSize" mi />
          </template>
          <template v-else-if="direction === 'mn'">
            <p class="meaning-big">{{ shown.meaning }}</p>
          </template>
          <template v-else>
            <SpeakButton :text="shown.hanzi" />
            <p class="small muted" style="margin-top: 10px">Nghe rồi đoán từ</p>
          </template>
          <p class="tiny faint tap">Bấm vào thẻ hoặc nhấn Space để lật</p>
        </div>

        <div class="face back card">
          <div class="row ans">
            <span class="han ah">{{ shown.hanzi }}</span>
            <SpeakButton :text="shown.hanzi" small />
            <SpeakButton :text="shown.hanzi" small slow />
          </div>
          <p class="py bpy">{{ shown.pinyin }}</p>
          <p class="bmn"><b>{{ shown.meaning }}</b><span v-if="shown.han_viet" class="faint"> · {{ shown.han_viet }}</span></p>
          <p v-if="shown.usage" class="small muted">{{ shown.usage }}</p>
          <p v-if="shown.example_zh" class="small ex"><span class="han">{{ shown.example_zh }}</span> <span class="muted">— {{ shown.example_vi }}</span></p>
        </div>
      </div>

      <div v-if="peeking" class="row wrap actions">
        <span class="chip" :class="ratingOf(peekEntry.rating).tone">Đã chấm: {{ ratingOf(peekEntry.rating).label }}</span>
        <button class="btn" type="button" :disabled="peekIdx === 0" @click="back()">← Thẻ trước</button>
        <button class="btn primary" type="button" @click="forward()">Tiếp →</button>
      </div>
      <div v-else-if="flipped" class="rates">
        <button v-for="r in ratings" :key="r.v" type="button" class="btn rate" :class="r.tone" :disabled="busy" @click="rate(r.v)">
          <span>{{ r.label }}</span><kbd>{{ r.v }}</kbd>
        </button>
      </div>
      <div v-else class="row wrap actions">
        <button v-if="history.length" class="btn ghost" type="button" @click="back()">← Thẻ trước</button>
        <button class="btn primary" type="button" @click="flip()">Lật thẻ</button>
      </div>
    </section>

    <!-- tổng kết -->
    <section v-else-if="phase === 'done'" class="card summary">
      <Seal :text="pct >= 80 ? '优' : pct >= 50 ? '良' : '练'" :tone="pct >= 80 ? 'jade' : pct >= 50 ? 'gold' : 'seal'" :size="72" />
      <div class="stack" style="gap: 6px">
        <h2>Nhớ {{ stats.remembered }} / {{ stats.total }} thẻ ({{ pct }}%)</h2>
        <div class="row wrap" style="gap: 8px">
          <span v-for="r in ratings" :key="r.v" class="chip" :class="r.tone">{{ r.label }}: {{ stats.by[r.v] }}</span>
        </div>
      </div>
      <div v-if="forgot.length" class="missed">
        <span class="label">Từ đã quên</span>
        <div class="mw-list">
          <div v-for="m in forgot" :key="m.vocab_id" class="mw">
            <span class="han mwh">{{ m.hanzi }}</span>
            <span class="py small">{{ m.pinyin }}</span>
            <SpeakButton :text="m.hanzi" small />
            <span class="small muted">{{ m.meaning }}</span>
          </div>
        </div>
      </div>
      <div class="row wrap">
        <button v-if="forgot.length" class="btn primary" type="button" @click="start(forgot)">Ôn lại {{ forgot.length }} từ này</button>
        <button class="btn" :class="{ primary: !forgot.length }" type="button" @click="start()">Lượt mới</button>
        <button class="btn ghost" type="button" @click="phase = 'setup'">Đổi phạm vi</button>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { api } from '../api'
import { speak } from '../composables/useTts'
import Seal from '../components/Seal.vue'
import SpeakButton from '../components/SpeakButton.vue'
import TianZiGe from '../components/TianZiGe.vue'

const PREF_KEY = 'hanyu.flashcards'
const quickScopes = [
  { k: 'all', label: 'Tất cả' },
  { k: 'weak', label: 'Từ yếu' },
  { k: 'due', label: 'Đến hạn ôn' },
  { k: 'tones', label: 'Hay sai thanh' },
]
const directions = [
  { k: 'hz', label: 'Hán tự → nghĩa' },
  { k: 'mn', label: 'Nghĩa → Hán tự' },
  { k: 'au', label: 'Nghe → Hán tự' },
]
const ratings = [
  { v: 1, label: 'Quên', tone: 'seal' },
  { v: 2, label: 'Khó', tone: 'gold' },
  { v: 3, label: 'Nhớ', tone: 'sky' },
  { v: 4, label: 'Dễ', tone: 'jade' },
]

const opts = ref(null)
const err = ref('')
const busy = ref(false)
const phase = ref('setup')

const scope = ref('all')
const refKey = ref('')
const limit = ref(20)
const direction = ref('hz')
const autoSpeak = ref(true)
const shuffle = ref(true)
const retryForgot = ref(true)

const queue = ref([])
const idx = ref(0)
const flipped = ref(false)
// các thẻ đã chấm trong lượt, để bấm ← xem lại; peekIdx = null là đang ở thẻ hiện tại
const history = ref([])
const peekIdx = ref(null)
const stats = reactive({ total: 0, remembered: 0, by: { 1: 0, 2: 0, 3: 0, 4: 0 } })
const forgot = ref([])

const cur = computed(() => queue.value[idx.value])
const peeking = computed(() => peekIdx.value !== null)
const peekEntry = computed(() => (peeking.value ? history.value[peekIdx.value] : null))
const shown = computed(() => (peeking.value ? peekEntry.value.card : cur.value))
const isFlipped = computed(() => peeking.value || flipped.value)
const directionLabel = computed(() => directions.find((d) => d.k === direction.value)?.label)
const pct = computed(() => (stats.total ? Math.round((stats.remembered / stats.total) * 100) : 0))
const gridSize = computed(() => {
  const n = [...(shown.value?.hanzi || '')].length
  const w = Math.min(window.innerWidth - 80, 560)
  return Math.max(64, Math.min(130, Math.floor(w / Math.max(n, 1)) - 8))
})
const ratingOf = (v) => ratings.find((r) => r.v === v)

function loadPrefs() {
  try {
    const p = JSON.parse(localStorage.getItem(PREF_KEY) || '{}')
    if (p.scope) scope.value = p.scope
    if (p.refKey) refKey.value = p.refKey
    if (typeof p.limit === 'number') limit.value = p.limit
    if (directions.some((d) => d.k === p.direction)) direction.value = p.direction
    if (typeof p.autoSpeak === 'boolean') autoSpeak.value = p.autoSpeak
    if (typeof p.shuffle === 'boolean') shuffle.value = p.shuffle
    if (typeof p.retryForgot === 'boolean') retryForgot.value = p.retryForgot
  } catch { /* bỏ qua */ }
}
function savePrefs() {
  try {
    localStorage.setItem(PREF_KEY, JSON.stringify({
      scope: scope.value, refKey: refKey.value, limit: limit.value, direction: direction.value,
      autoSpeak: autoSpeak.value, shuffle: shuffle.value, retryForgot: retryForgot.value,
    }))
  } catch { /* bỏ qua */ }
}

function pickUnitScope() {
  if (!refKey.value && opts.value?.books.length) refKey.value = `book:${opts.value.books[0].id}`
  scope.value = refKey.value.split(':')[0] || 'book'
}
watch(refKey, (k) => { if (scope.value === 'unit' || scope.value === 'book') scope.value = k.split(':')[0] })

function say(text) {
  speak(text).catch(() => { err.value = 'Không phát được âm thanh. Kiểm tra cài đặt giọng đọc.' })
}

async function start(cards) {
  err.value = ''
  busy.value = true
  try {
    let list = cards
    if (!list) {
      savePrefs()
      const id = scope.value === 'unit' || scope.value === 'book' ? Number(refKey.value.split(':')[1]) : null
      list = await api.post('/api/flashcards/deck', { scope: scope.value, id, limit: limit.value })
    }
    if (!list.length) { err.value = 'Phạm vi này chưa có từ nào.'; return }
    // server luôn trả thứ tự ngẫu nhiên; tắt trộn thì xếp lại theo thứ tự từ trong file
    list = shuffle.value ? [...list].sort(() => Math.random() - 0.5) : [...list].sort((a, b) => a.vocab_id - b.vocab_id)
    queue.value = list.map((c) => ({ ...c, retry: false }))
    idx.value = 0
    history.value = []
    peekIdx.value = null
    Object.assign(stats, { total: 0, remembered: 0, by: { 1: 0, 2: 0, 3: 0, 4: 0 } })
    forgot.value = []
    phase.value = 'study'
    showCard()
  } catch (e) {
    err.value = e.message
  } finally {
    busy.value = false
  }
}

function showCard() {
  flipped.value = false
  // mặt trước là âm thanh thì phải đọc ngay
  if (direction.value === 'au') say(cur.value.hanzi)
}

function flip() {
  if (peeking.value || flipped.value) return
  flipped.value = true
  if (autoSpeak.value && direction.value !== 'au') say(cur.value.hanzi)
}

async function rate(v) {
  if (!flipped.value || peeking.value || busy.value) return
  const c = cur.value
  err.value = ''
  if (!c.retry) {
    busy.value = true
    try {
      await api.post(`/api/flashcards/${c.vocab_id}/rate`, { rating: v })
    } catch (e) {
      err.value = e.message
      return
    } finally {
      busy.value = false
    }
    stats.total++
    stats.by[v]++
    if (v >= 2) stats.remembered++
    if (v === 1) forgot.value.push(c)
  }
  if (v === 1 && retryForgot.value) queue.value.push({ ...c, retry: true })
  history.value.push({ card: c, rating: v })
  if (idx.value + 1 >= queue.value.length) {
    phase.value = 'done'
    api.get('/api/drill/pinyin/options').then((o) => { opts.value = o }).catch(() => {})
    return
  }
  idx.value++
  showCard()
}

function back() {
  if (!history.value.length) return
  peekIdx.value = peeking.value ? Math.max(0, peekIdx.value - 1) : history.value.length - 1
}

function forward() {
  if (!peeking.value) return flip()
  peekIdx.value = peekIdx.value + 1 < history.value.length ? peekIdx.value + 1 : null
}

function onKey(e) {
  if (phase.value !== 'study' || e.ctrlKey || e.metaKey || e.altKey) return
  if (/^(INPUT|TEXTAREA|SELECT)$/.test(e.target.tagName)) return
  if (e.key === ' ' || e.key === 'Enter') {
    if (e.target.tagName === 'BUTTON' && e.target.closest('.actions, .rates')) return
    e.preventDefault()
    peeking.value ? forward() : flip()
  } else if (e.key === 'ArrowRight') {
    forward()
  } else if (e.key === 'ArrowLeft') {
    back()
  } else if (/^[1-4]$/.test(e.key)) {
    rate(Number(e.key))
  }
}

onMounted(async () => {
  loadPrefs()
  window.addEventListener('keydown', onKey)
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
onBeforeUnmount(() => window.removeEventListener('keydown', onKey))
</script>

<style scoped>
.setup { display: flex; flex-direction: column; gap: 20px; padding: 28px; }
.field { display: flex; flex-direction: column; gap: 8px; }
.toggles { gap: 10px; }
.toggles label { display: flex; align-items: center; gap: 10px; font-weight: 700; cursor: pointer; }
.toggles input { width: 18px; height: 18px; accent-color: var(--primary); }
.setup .btn.lg { align-self: flex-start; }
kbd {
  display: inline-block; min-width: 1.6em; padding: 1px 6px; border-radius: 6px; text-align: center;
  font: 800 11px/1.5 inherit; background: var(--paper-3); box-shadow: 0 1px 0 0 var(--line);
}

.study { display: flex; flex-direction: column; }
.head { margin-bottom: 12px; }

/* thẻ lật: hai mặt chồng trong cùng một ô lưới nên chiều cao theo mặt dài hơn */
.flip { display: grid; perspective: 1400px; cursor: pointer; outline: none; }
.flip:focus-visible .face { box-shadow: 0 0 0 3px var(--primary); }
.face {
  grid-area: 1 / 1; min-height: 340px; padding: 28px; display: flex; flex-direction: column;
  align-items: center; justify-content: center; text-align: center; gap: 6px;
  backface-visibility: hidden; -webkit-backface-visibility: hidden;
  transition: transform .5s var(--ease-spring);
}
.back { transform: rotateY(180deg); }
.flipped .front { transform: rotateY(-180deg); }
.flipped .back { transform: rotateY(0deg); }
@media (prefers-reduced-motion: reduce) { .face { transition: none; } }
.tap { margin-top: 18px; }
.meaning-big { font-size: 28px; font-weight: 900; line-height: 1.35; max-width: 32ch; overflow-wrap: anywhere; }
.ans { gap: 10px; justify-content: center; }
.ah { font-size: 52px; line-height: 1.2; }
.bpy { font-size: 22px; }
.bmn { font-size: 18px; }
.ex { margin-top: 6px; }
.ex .han { font-size: 17px; }

.actions { justify-content: center; margin-top: 18px; gap: 10px; }
.rates { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin-top: 18px; }
.rate { justify-content: center; gap: 8px; }
.rate kbd { background: transparent; box-shadow: none; opacity: .6; }
.rate.seal { background: var(--seal-soft); color: var(--seal); }
.rate.gold { background: var(--gold-soft); color: var(--gold); }
.rate.sky { background: var(--primary-soft); color: var(--primary-strong); }
.rate.jade { background: var(--jade-soft); color: var(--jade); }
.chip.sky { background: var(--primary-soft); color: var(--primary-strong); }

.summary { display: flex; flex-direction: column; gap: 18px; padding: 28px; }
.missed { display: flex; flex-direction: column; gap: 8px; }
.mw-list { display: flex; flex-direction: column; gap: 6px; }
.mw { display: flex; align-items: center; gap: 10px; padding: 8px 12px; border-radius: 14px; background: var(--paper-3); }
.mwh { font-size: 22px; }

@media (max-width: 560px) {
  .setup, .summary, .face { padding: 20px; }
  .face { min-height: 280px; }
  .rates { grid-template-columns: repeat(2, 1fr); }
  .rate kbd { display: none; }
}
</style>

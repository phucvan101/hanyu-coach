<template>
  <div class="page">
    <div class="row spread wrap" style="margin-bottom: 18px">
      <div>
        <span class="eyebrow">{{ task ? 'Lộ trình cải thiện' : 'Luyện riêng' }}</span>
        <h1>{{ task ? task.title_vi : 'Hán tự → gõ pinyin' }}</h1>
      </div>
      <RouterLink v-if="taskId" to="/talk" class="btn ghost">← Về lộ trình</RouterLink>
      <button v-else-if="phase !== 'setup'" class="btn ghost" type="button" @click="phase = 'setup'">← Chọn lại</button>
    </div>
    <p v-if="err" class="notice err" style="margin-bottom: 14px">{{ err }}</p>

    <!-- chọn phạm vi -->
    <div v-if="taskId && phase === 'setup'" class="empty">{{ err ? '' : 'Đang tải…' }}</div>
    <section v-else-if="phase === 'setup'" class="card setup">
      <div v-if="!opts" class="empty">Đang tải…</div>
      <div v-else-if="!opts.counts.all" class="empty">
        Chưa có từ nào. <RouterLink to="/library">Nhập file từ vựng</RouterLink> trước nhé.
      </div>
      <template v-else>
        <div class="field">
          <span class="label">Luyện từ nào</span>
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
          <span class="label">Số từ mỗi lượt</span>
          <div class="row wrap" style="gap: 8px">
            <button v-for="n in [10, 20, 30, 0]" :key="n" type="button" class="btn" :class="{ primary: limit === n }" @click="limit = n">{{ n || 'Tất cả' }}</button>
          </div>
        </div>

        <div class="field toggles">
          <label><input v-model="showMeaning" type="checkbox" /> Hiện nghĩa tiếng Việt (dễ hơn)</label>
          <label><input v-model="autoSpeak" type="checkbox" /> Tự đọc từ sau khi trả lời</label>
          <label><input v-model="retryWrong" type="checkbox" /> Làm lại các từ sai ở cuối lượt</label>
        </div>

        <p class="small muted">Chỉ cần đúng âm là tính đúng; sai/thiếu thanh điệu bị nhắc (dấu 调). Gõ <b>ni3hao3</b>, <b>nǐhǎo</b> hoặc <b>nihao</b> đều được. Kết quả lần trả lời đầu được tính vào lịch ôn từ vựng.</p>
        <button class="btn primary lg" type="button" :disabled="busy" @click="start()">Bắt đầu</button>
      </template>
    </section>

    <!-- đang luyện -->
    <section v-else-if="phase === 'drill' && cur" class="card qc">
      <div class="row spread head">
        <span class="eyebrow">{{ cur.retry ? 'Làm lại từ sai' : 'Gõ pinyin' }}</span>
        <span class="tiny faint">{{ idx + 1 }} / {{ queue.length }} · đúng {{ stats.correct }}</span>
      </div>
      <div class="bar" style="margin-bottom: 22px"><span :style="{ width: (idx / queue.length) * 100 + '%' }"></span></div>

      <div class="prompt">
        <TianZiGe :text="cur.hanzi" :size="gridSize" mi />
        <p v-if="showMeaning || hinted.meaning" class="muted small" style="margin-top: 12px">Nghĩa: {{ cur.meaning }}<span v-if="cur.han_viet" class="faint"> · {{ cur.han_viet }}</span></p>
        <div v-if="!res" class="row hints">
          <button v-if="!showMeaning && !hinted.meaning" class="linkbtn" type="button" @click="hint('meaning')">gợi ý nghĩa</button>
          <button class="linkbtn" type="button" @click="hint('audio')">nghe phát âm</button>
        </div>
      </div>

      <form class="row typed" @submit.prevent="submit()">
        <input ref="inp" v-model="text" class="input pyin" :disabled="!!res" autocomplete="off" autocapitalize="off" spellcheck="false"
          placeholder="VD: ni3hao3 hoặc nǐhǎo" />
        <template v-if="!res">
          <button class="btn primary" type="submit" :disabled="busy || !text.trim()">Kiểm tra</button>
          <button class="btn ghost" type="button" :disabled="busy" @click="submit(true)">Không biết</button>
        </template>
      </form>

      <Transition name="fade">
        <div v-if="res" class="result" :class="tone">
          <Seal :text="sealText" :tone="tone" :size="58" />
          <div class="reveal">
            <p class="verdict">{{ verdict }}</p>
            <p v-if="res.feedback" class="small">{{ res.feedback }}</p>
            <p v-if="!res.correct && text.trim()" class="small muted">Bạn gõ: <span class="strike">{{ text }}</span></p>
            <div class="row ans">
              <span class="han ah">{{ res.answer.hanzi }}</span>
              <span class="py">{{ res.answer.pinyin }}</span>
              <SpeakButton :text="res.answer.hanzi" small />
            </div>
            <p class="small"><b>{{ res.answer.meaning }}</b><span v-if="res.answer.han_viet" class="faint"> · {{ res.answer.han_viet }}</span></p>
            <p v-if="res.answer.example_zh" class="small ex"><span class="han">{{ res.answer.example_zh }}</span> <span class="muted">— {{ res.answer.example_vi }}</span></p>
            <p v-if="usedHint && !cur.retry" class="tiny faint">Đã dùng gợi ý nghe nên lần này không tính vào lịch ôn.</p>
          </div>
          <button ref="nextBtn" class="btn primary nx" type="button" @click="next()">Tiếp →</button>
        </div>
      </Transition>
    </section>

    <!-- tổng kết -->
    <section v-else-if="phase === 'done'" class="card summary">
      <Seal :text="pct >= 80 ? '优' : pct >= 50 ? '良' : '练'" :tone="pct >= 80 ? 'jade' : pct >= 50 ? 'gold' : 'seal'" :size="72" />
      <div class="stack" style="gap: 6px">
        <h2>{{ stats.correct }} / {{ stats.total }} đúng ngay lần đầu ({{ pct }}%)</h2>
        <p class="small muted">{{ stats.tone }} từ đúng âm nhưng chưa chuẩn thanh điệu.</p>
      </div>
      <div v-if="missed.length" class="missed">
        <span class="label">Từ cần xem lại</span>
        <div class="mw-list">
          <div v-for="m in missed" :key="m.hanzi" class="mw">
            <span class="han mwh">{{ m.hanzi }}</span>
            <span class="py small">{{ m.pinyin }}</span>
            <SpeakButton :text="m.hanzi" small />
            <span class="small muted">{{ m.meaning }}</span>
          </div>
        </div>
      </div>
      <div class="row wrap">
        <button v-if="missed.length" class="btn primary" type="button" @click="start(missedCards)">Luyện lại {{ missed.length }} từ này</button>
        <template v-if="task">
          <RouterLink to="/talk" class="btn" :class="{ primary: !missed.length }">Về lộ trình</RouterLink>
          <button class="btn ghost" type="button" @click="start(task.items)">Làm lại cả bài</button>
        </template>
        <template v-else>
          <button class="btn" :class="{ primary: !missed.length }" type="button" @click="start()">Lượt mới</button>
          <button class="btn ghost" type="button" @click="phase = 'setup'">Đổi phạm vi</button>
        </template>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { api } from '../api'
import { speak } from '../composables/useTts'
import Seal from '../components/Seal.vue'
import SpeakButton from '../components/SpeakButton.vue'
import TianZiGe from '../components/TianZiGe.vue'
import { useStreak } from '../composables/useReactions'
import { playCorrect, playWrong } from '../composables/useSfx'

const PREF_KEY = 'hanyu.drill.pinyin'
const quickScopes = [
  { k: 'all', label: 'Tất cả' },
  { k: 'weak', label: 'Từ yếu' },
  { k: 'due', label: 'Đến hạn ôn' },
  { k: 'tones', label: 'Hay sai thanh' },
]

const route = useRoute()
const taskId = route.query.task ? Number(route.query.task) : null
const task = ref(null)
const fullTaskRun = ref(false)
const opts = ref(null)
const err = ref('')
const busy = ref(false)
const phase = ref('setup')

const scope = ref('all')
const refKey = ref('')
const limit = ref(20)
const showMeaning = ref(true)
const autoSpeak = ref(true)
const retryWrong = ref(true)

const queue = ref([])
const idx = ref(0)
const text = ref('')
const res = ref(null)
const hinted = reactive({ meaning: false, audio: false })
const stats = reactive({ total: 0, correct: 0, tone: 0 })
const missed = ref([])
const inp = ref(null)
const nextBtn = ref(null)
const streak = useStreak()

const cur = computed(() => queue.value[idx.value])
const usedHint = computed(() => hinted.audio)
const pct = computed(() => (stats.total ? Math.round((stats.correct / stats.total) * 100) : 0))
const missedCards = computed(() => missed.value.map((m) => ({ vocab_id: m.vocab_id, hanzi: m.hanzi, meaning: m.meaning, han_viet: m.han_viet })))
const tone = computed(() => (!res.value?.correct ? 'seal' : res.value.tone_warning ? 'gold' : 'jade'))
const sealText = computed(() => (!res.value?.correct ? '错' : res.value.tone_warning ? '调' : '对'))
const verdict = computed(() => (!res.value?.correct ? 'Chưa đúng' : res.value.tone_warning ? 'Đúng âm — chú ý thanh điệu' : 'Chính xác'))
const gridSize = computed(() => {
  const n = [...(cur.value?.hanzi || '')].length
  const w = Math.min(window.innerWidth - 80, 560)
  return Math.max(64, Math.min(130, Math.floor(w / Math.max(n, 1)) - 8))
})

function loadPrefs() {
  try {
    const p = JSON.parse(localStorage.getItem(PREF_KEY) || '{}')
    if (p.scope) scope.value = p.scope
    if (p.refKey) refKey.value = p.refKey
    if (typeof p.limit === 'number') limit.value = p.limit
    if (typeof p.showMeaning === 'boolean') showMeaning.value = p.showMeaning
    if (typeof p.autoSpeak === 'boolean') autoSpeak.value = p.autoSpeak
    if (typeof p.retryWrong === 'boolean') retryWrong.value = p.retryWrong
  } catch { /* bỏ qua */ }
}
function savePrefs() {
  try {
    localStorage.setItem(PREF_KEY, JSON.stringify({
      scope: scope.value, refKey: refKey.value, limit: limit.value,
      showMeaning: showMeaning.value, autoSpeak: autoSpeak.value, retryWrong: retryWrong.value,
    }))
  } catch { /* bỏ qua */ }
}

function pickUnitScope() {
  if (!refKey.value && opts.value?.books.length) refKey.value = `book:${opts.value.books[0].id}`
  scope.value = refKey.value.split(':')[0] || 'book'
}
watch(refKey, (k) => { if (scope.value === 'unit' || scope.value === 'book') scope.value = k.split(':')[0] })

async function start(cards) {
  err.value = ''
  busy.value = true
  try {
    let list = cards
    if (!list) {
      savePrefs()
      const id = scope.value === 'unit' || scope.value === 'book' ? Number(refKey.value.split(':')[1]) : null
      list = await api.post('/api/drill/pinyin/deck', { scope: scope.value, id, limit: limit.value })
    } else {
      list = [...list].sort(() => Math.random() - 0.5)
    }
    if (!list.length) { err.value = 'Phạm vi này chưa có từ nào.'; return }
    fullTaskRun.value = !!task.value && cards === task.value.items
    queue.value = list.map((c) => ({ ...c, retry: false }))
    idx.value = 0
    Object.assign(stats, { total: 0, correct: 0, tone: 0 })
    streak.reset()
    missed.value = []
    phase.value = 'drill'
    resetCard()
  } catch (e) {
    err.value = e.message
  } finally {
    busy.value = false
  }
}

function resetCard() {
  text.value = ''
  res.value = null
  hinted.meaning = false
  hinted.audio = false
  nextTick(() => inp.value?.focus())
}

function hint(kind) {
  hinted[kind] = true
  if (kind === 'audio') speak(cur.value.hanzi).catch(() => { err.value = 'Không phát được âm thanh. Kiểm tra cài đặt giọng đọc.' })
  nextTick(() => inp.value?.focus())
}

async function submit(giveUp = false) {
  if (res.value || busy.value) return
  const ans = giveUp ? '' : text.value.trim()
  if (!giveUp && !ans) return
  if (giveUp) text.value = ''
  busy.value = true
  err.value = ''
  const c = cur.value
  try {
    const r = await api.post(`/api/drill/pinyin/${c.vocab_id}/check`, { answer: ans, record: !c.retry && !hinted.audio })
    res.value = r
    if (r.correct) playCorrect()
    else if (!giveUp) playWrong()
    if (!c.retry) {
      stats.total++
      if (r.correct) stats.correct++
      if (r.correct && r.tone_warning) stats.tone++
      streak.hit(r.correct)
      if (!r.correct) {
        missed.value.push({ ...c, pinyin: r.answer.pinyin })
        if (retryWrong.value) queue.value.push({ ...c, retry: true })
      }
    }
    await nextTick()
    nextBtn.value?.focus()
    // đợi tiếng báo đúng/sai dứt rồi mới đọc từ
    if (autoSpeak.value && !hinted.audio) setTimeout(() => speak(r.answer.hanzi).catch(() => {}), r.correct || !giveUp ? 450 : 0)
  } catch (e) {
    err.value = e.message
  } finally {
    busy.value = false
  }
}

function next() {
  if (idx.value + 1 >= queue.value.length) {
    phase.value = 'done'
    if (fullTaskRun.value) {
      // chỉ lượt làm đủ cả bài mới tính hoàn thành nhiệm vụ (không tính lượt "luyện lại từ sai")
      api.post(`/api/plan-tasks/${task.value.id}/complete`, { score: pct.value }).catch(() => {})
    }
    api.get('/api/drill/pinyin/options').then((o) => { opts.value = o }).catch(() => {})
    return
  }
  idx.value++
  resetCard()
}

onMounted(async () => {
  loadPrefs()
  if (taskId) {
    try {
      task.value = await api.get(`/api/plan-tasks/${taskId}`)
      await start(task.value.items)
    } catch (e) {
      err.value = e.message
    }
    return
  }
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
</script>

<style scoped>
.setup { display: flex; flex-direction: column; gap: 20px; padding: 28px; }
.field { display: flex; flex-direction: column; gap: 8px; }
.toggles { gap: 10px; }
.toggles label { display: flex; align-items: center; gap: 10px; font-weight: 700; cursor: pointer; }
.toggles input { width: 18px; height: 18px; accent-color: var(--primary); }
.setup .btn.lg { align-self: flex-start; }

.qc { padding: 28px; }
.head { margin-bottom: 12px; }
.prompt { text-align: center; padding: 8px 0 22px; }
.hints { justify-content: center; gap: 18px; margin-top: 12px; }
.linkbtn { border: 0; background: none; color: var(--primary-strong); cursor: pointer; padding: 0; text-decoration: underline; font-weight: 800; text-underline-offset: 3px; font-size: 13px; }
.typed { align-items: stretch; flex-wrap: wrap; }
.pyin { flex: 1 1 220px; min-width: 0; font-size: 22px; padding: 14px 18px; border-radius: 18px; }
.result {
  display: grid; grid-template-columns: auto 1fr auto; gap: 18px; align-items: start; margin-top: 22px;
  padding: 20px; border-radius: 22px; background: var(--paper-3); box-shadow: var(--shadow-in);
  animation: rise .35s var(--ease-spring) both;
}
@keyframes rise { from { opacity: 0; transform: translateY(10px); } }
.result.jade { background: var(--jade-soft); }
.result.seal { background: var(--seal-soft); }
.result.gold { background: var(--gold-soft); }
.verdict { font-weight: 900; margin-bottom: 4px; font-size: 16px; }
.reveal { display: flex; flex-direction: column; gap: 4px; min-width: 0; }
.ans { gap: 10px; margin: 4px 0; }
.ah { font-size: 30px; }
.ex .han { font-size: 17px; }
.nx { align-self: end; }

.summary { display: flex; flex-direction: column; gap: 18px; padding: 28px; }
.missed { display: flex; flex-direction: column; gap: 8px; }
.mw-list { display: flex; flex-direction: column; gap: 6px; }
.mw { display: flex; align-items: center; gap: 10px; padding: 8px 12px; border-radius: 14px; background: var(--paper-3); }
.mwh { font-size: 22px; }

@media (max-width: 560px) {
  .qc, .setup, .summary { padding: 20px; }
  .result { grid-template-columns: auto 1fr; }
  .nx { grid-column: 1 / -1; width: 100%; }
}
</style>

<template>
  <div class="page">
    <div class="head">
      <span class="eyebrow">Ôn cả quyển</span>
      <h1>Hội thoại tổng hợp</h1>
      <p class="muted">Tự chọn chủ đề bất kỳ. AI nói bằng từ trong quyển bạn đã học; nếu cần từ mới (tối đa 2 từ mỗi lượt) thì từ đó được <b>in đậm</b> kèm giải thích. Câu nào bạn nói sai được sửa ngay bên dưới, cuối buổi có báo cáo và lộ trình cải thiện.</p>
    </div>
    <p v-if="err" class="notice err" style="margin-bottom: 14px">{{ err }}</p>

    <div class="layout" :class="{ split: openTasks.length }">
    <div class="col">
    <section v-if="!books" class="empty">Đang tải…</section>
    <section v-else-if="!books.length" class="card empty">
      Chưa có quyển nào sẵn sàng. <RouterLink to="/library">Nhập file từ vựng</RouterLink> trước nhé.
    </section>
    <form v-else class="card setup" @submit.prevent="start">
      <label class="field">
        <span class="label">Quyển</span>
        <select v-model="bookId" class="select">
          <option v-for="b in books" :key="b.id" :value="b.id">{{ b.title }} ({{ b.word_count }} từ)</option>
        </select>
      </label>
      <div class="field">
        <label class="label" for="topic">Chủ đề muốn nói</label>
        <input id="topic" v-model="topic" class="input topic" maxlength="200" placeholder="VD: Kể về chuyến du lịch Đà Lạt của tôi" />
        <div class="row wrap" style="gap: 6px">
          <button v-for="s in suggestions" :key="s" type="button" class="chip sug" @click="topic = s">{{ s }}</button>
        </div>
      </div>
      <div class="field">
        <span class="label">Số lượt bạn nói</span>
        <div class="row wrap" style="gap: 8px">
          <button v-for="n in [6, 8, 12, 16]" :key="n" type="button" class="btn" :class="{ primary: turns === n }" @click="turns = n">{{ n }} lượt</button>
        </div>
      </div>
      <button class="btn primary lg" type="submit" :disabled="busy || !topic.trim()">{{ busy ? 'Đang tạo…' : 'Bắt đầu nói' }}</button>
    </form>

    <section v-if="recent.length" class="card block">
      <h2 style="margin-bottom: 12px">Các buổi tổng hợp gần đây</h2>
      <ul class="recent">
        <li v-for="s in recent" :key="s.id">
          <RouterLink :to="s.status === 'done' ? `/report/${s.id}` : `/session/${s.id}`" class="rl">
            <span class="rt">{{ s.topic }}</span>
            <span class="small muted">{{ fmtDate(s.started_at) }} · {{ s.status === 'done' ? 'xem báo cáo' : 'đang dở — học tiếp' }}</span>
          </RouterLink>
        </li>
      </ul>
    </section>
    </div>

    <div v-if="openTasks.length" class="side">

    <section v-if="openTasks.length" class="card block">
      <div class="row spread wrap" style="margin-bottom: 12px">
        <h2>Lộ trình cải thiện</h2>
        <span class="small muted">{{ openTasks.length }} việc chưa làm</span>
      </div>
      <TaskList :tasks="openTasks" show-source />
    </section>

    </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { api, fmtDate } from '../api'
import TaskList from '../components/TaskList.vue'

const PREF_KEY = 'hanyu.talk'
const suggestions = [
  'Cuối tuần của tôi', 'Đi du lịch Bắc Kinh', 'Hẹn bạn đi ăn tối', 'Kể về gia đình tôi',
  'Phỏng vấn xin việc', 'Đi khám bệnh', 'Mua quần áo ở chợ', 'Thuê phòng trọ',
]
const router = useRouter()
const books = ref(null)
const bookId = ref(null)
const topic = ref('')
const turns = ref(8)
const busy = ref(false)
const err = ref('')
const tasks = ref([])
const sessions = ref([])

const openTasks = computed(() => tasks.value.filter((t) => t.status === 'open'))
const recent = computed(() => sessions.value.filter((s) => s.start_stage === 'book' && !s.task_id).slice(0, 8))

async function start() {
  if (!topic.value.trim() || busy.value) return
  busy.value = true
  err.value = ''
  try {
    try { localStorage.setItem(PREF_KEY, JSON.stringify({ bookId: bookId.value, turns: turns.value })) } catch { /* bỏ qua */ }
    const st = await api.post('/api/book-sessions', { book_id: bookId.value, topic: topic.value.trim(), max_turns: turns.value })
    router.push(`/session/${st.session.id}`)
  } catch (e) {
    err.value = e.message
  } finally {
    busy.value = false
  }
}

onMounted(async () => {
  try {
    const [bs, ts, ss] = await Promise.all([api.get('/api/books'), api.get('/api/plan-tasks?status=open'), api.get('/api/sessions')])
    books.value = bs.filter((b) => b.status === 'ready')
    tasks.value = ts
    sessions.value = ss
    let pref = {}
    try { pref = JSON.parse(localStorage.getItem(PREF_KEY) || '{}') } catch { /* bỏ qua */ }
    bookId.value = books.value.some((b) => b.id === pref.bookId) ? pref.bookId : books.value[books.value.length - 1]?.id ?? null
    if ([6, 8, 12, 16].includes(pref.turns)) turns.value = pref.turns
  } catch (e) {
    err.value = e.message
    books.value = books.value || []
  }
})
</script>

<style scoped>
.head { margin-bottom: 20px; }
.head p { margin-top: 6px; max-width: 72ch; }
.layout { display: grid; gap: 20px; align-items: start; }
.col, .side { display: flex; flex-direction: column; gap: 20px; min-width: 0; }
@media (min-width: 1180px) {
  .layout.split { grid-template-columns: minmax(0, 5fr) minmax(0, 6fr); }
}
.setup { display: flex; flex-direction: column; gap: 20px; padding: 24px; }
.field { display: flex; flex-direction: column; gap: 8px; }
.field .label { margin-bottom: 0; }
.setup .select, .topic { font-size: 16px; padding: 12px 16px; border-radius: 16px; }
.sug { cursor: pointer; border: 0; font: inherit; font-size: 13px; transition: transform .2s var(--ease-spring); }
.sug:hover { transform: translateY(-1px); color: var(--primary-strong); }
.setup .btn.lg { align-self: flex-start; }
.block { padding: 24px; }
.recent { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 8px; }
.rl {
  display: flex; flex-direction: column; gap: 2px; padding: 12px 16px; border-radius: 16px;
  background: var(--paper-3); color: var(--ink); text-decoration: none !important;
  transition: transform .2s var(--ease-spring);
}
.rl:hover { transform: translateX(3px); }
.rt { font-weight: 800; }
@media (max-width: 560px) { .setup, .block { padding: 20px; } }
</style>

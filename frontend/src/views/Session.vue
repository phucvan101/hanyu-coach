<template>
  <div class="sess">
    <header class="topbar">
      <button class="btn ghost icon" type="button" aria-label="Thoát (tiến độ đã được lưu)" title="Thoát — tiến độ đã được lưu" @click="exit">
        <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
      </button>
      <div class="tt">
        <span class="han tz">{{ isBook ? '综合会话' : st?.unit?.title_zh }}</span>
        <span class="small muted">{{ isBook ? (st.task ? 'Lộ trình · ' : 'Chủ đề: ') + st.session.topic : st?.unit?.title_vi }}</span>
      </div>
      <div class="phase small">{{ phaseLabel }}</div>
      <button class="btn" type="button" :disabled="ending || !st" @click="endSession">{{ ending ? 'Đang tổng kết…' : 'Kết thúc buổi' }}</button>
    </header>
    <div class="bar topprog"><span :style="{ width: progressPct + '%' }"></span></div>

    <div class="page page-narrow body" :class="{ wide: phase === 'convo' && convo }">
      <div v-if="!st" class="empty">{{ err || 'Đang tải buổi học…' }}</div>
      <template v-else>
        <p v-if="err" class="notice err" style="margin-bottom: 14px">{{ err }}</p>
        <div v-if="st.task" class="notice task-note" style="margin-bottom: 14px">
          <b>Nhiệm vụ lộ trình:</b> {{ st.task.title_vi }}<span v-if="st.task.detail_vi" class="muted"> — {{ st.task.detail_vi }}</span>
        </div>

        <!-- ÔN TẬP -->
        <section v-if="phase === 'review'" class="stack">
          <div class="row spread">
            <h2>Ôn nhanh trước khi học</h2>
            <span class="small muted">{{ reviewDone }}/{{ reviewTotal }}</span>
          </div>
          <p class="muted small">Những từ đến hạn ôn và câu bạn từng nói sai ở buổi trước.</p>
          <QuizCard v-if="curReview" :item="curReview" :position="`Ôn ${reviewIdx + 1}/${st.review_items.length}`"
            @answered="onAnswered" @next="advance" />
          <div v-else-if="curSentence" class="card sr">
            <span class="eyebrow">Sửa lại câu sai</span>
            <p class="han orig">{{ curSentence.original }}</p>
            <p v-if="curSentence.grammar_point" class="small muted">Gợi ý: {{ curSentence.grammar_point }}</p>
            <template v-if="!curSentence.answered">
              <form class="row" style="margin-top: 14px" @submit.prevent="answerSentence">
                <HanziInput v-model="sentenceText" big placeholder="Viết lại câu đúng…" @submit="answerSentence" />
                <button class="btn primary" :disabled="busy || !sentenceText.trim()">Kiểm tra</button>
              </form>
              <button class="btn ghost small" style="margin-top: 8px" type="button" @click="skipSentence">Bỏ qua câu này</button>
            </template>
            <div v-else class="result-line">
              <Seal :text="curSentence.correct ? '对' : '错'" :tone="curSentence.correct ? 'jade' : 'seal'" :size="48" />
              <div class="stack" style="gap: 4px">
                <p class="small">{{ curSentence.feedback }}</p>
                <div class="row"><span class="han good">{{ curSentence.corrected }}</span><SpeakButton :text="curSentence.corrected" small /></div>
                <ErrorExplain :text="curSentence.explanation_vi" />
              </div>
              <button class="btn primary" type="button" @click="advance">Tiếp →</button>
            </div>
          </div>
        </section>

        <!-- KIỂM TRA TỪ VỰNG -->
        <section v-else-if="phase === 'quiz'" class="stack">
          <div class="row spread">
            <h2>Kiểm tra từ vựng</h2>
            <span class="small muted">Đúng {{ quizCorrect }}/{{ quizAnswered }} · cần ≥ {{ st.pass_threshold }}%</span>
          </div>
          <QuizCard v-if="curQuiz" :item="curQuiz" :position="`${quizIdx + 1}/${st.quiz_items.length}`" @answered="onAnswered" @next="advance" />
          <div v-else class="empty">Đang tạo câu hỏi…</div>
        </section>

        <!-- HỘI THOẠI -->
        <section v-else-if="phase === 'convo'">
          <div v-if="!convo" class="empty card">
            <p v-if="!convoErr">AI đang chuẩn bị tình huống hội thoại…</p>
            <template v-else>
              <p class="notice err">{{ convoErr }}</p>
              <div class="row" style="justify-content: center; margin-top: 12px">
                <button class="btn primary" @click="openConvo(stage)">Thử lại</button>
                <RouterLink to="/settings" class="btn">Kiểm tra API key</RouterLink>
              </div>
            </template>
          </div>
          <ChatPanel v-else :convo="convo" :words="st.unit_words" :finishing="busy" @update="onConvoUpdate" @finish="finishConvo" />
        </section>

        <!-- KẾT QUẢ MỘT BƯỚC -->
        <section v-else-if="phase === 'result' && result" class="card res">
          <Seal :text="String(result.score)" :tone="result.passed ? 'jade' : 'seal'" :size="96" />
          <div class="stack" style="gap: 8px">
            <span class="eyebrow">{{ st.stage_labels[result.stage] }}</span>
            <h1 v-if="result.stage === 'book'">{{ result.passed ? 'Tốt lắm!' : 'Cần luyện thêm' }} — hội thoại xong</h1>
            <h1 v-else>{{ result.passed ? 'Đạt — đã mở bước tiếp theo' : 'Chưa đạt ' + st.pass_threshold + '%' }}</h1>
            <p v-if="result.stage === 'vocab'" class="muted">Đúng {{ quizCorrect }}/{{ st.quiz_items.length }} câu.</p>
            <p v-else class="muted">{{ result.turns }} lượt nói<span v-if="result.coverage !== undefined"> · dùng được {{ result.coverage }}% từ mục tiêu</span>.</p>
            <p v-if="result.stage === 'book'" class="small muted">Kết thúc buổi để xem báo cáo chi tiết<span v-if="!st.task"> và lộ trình cải thiện</span>.</p>
            <p v-else-if="!result.passed" class="small muted">Các từ/câu sai đã được lưu và sẽ quay lại ở phần ôn tập. Bạn có thể kết thúc để xem báo cáo, rồi học lại bước này.</p>
            <div class="row wrap" style="margin-top: 8px">
              <button v-if="nextStage" class="btn primary lg" :disabled="busy" @click="goStage(nextStage)">Tiếp: {{ st.stage_labels[nextStage] }}</button>
              <button class="btn lg" :class="{ primary: !nextStage }" :disabled="ending" @click="endSession">Kết thúc & xem báo cáo</button>
            </div>
          </div>
        </section>
      </template>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '../api'
import ChatPanel from '../components/ChatPanel.vue'
import HanziInput from '../components/HanziInput.vue'
import QuizCard from '../components/QuizCard.vue'
import Seal from '../components/Seal.vue'
import SpeakButton from '../components/SpeakButton.vue'
import ErrorExplain from '../components/ErrorExplain.vue'
import { loadSettings } from '../composables/useSettings'
import { useStreak, playResult } from '../composables/useReactions'
import { playCorrect, playWrong } from '../composables/useSfx'

const route = useRoute()
const router = useRouter()
const sid = Number(route.params.id)
const st = ref(null)
const phase = ref('loading')
const stage = ref('vocab')
const convo = ref(null)
const convoErr = ref('')
const result = ref(null)
const err = ref('')
const busy = ref(false)
const ending = ref(false)
const sentenceText = ref('')
const skipped = ref(new Set())
const isBook = computed(() => st.value?.session?.start_stage === 'book')
const streak = useStreak()

const reviewItems = computed(() => st.value?.review_items || [])
const sentences = computed(() => (st.value?.sentence_reviews || []).filter((s) => !skipped.value.has(s.id)))
const reviewIdx = computed(() => {
  const i = reviewItems.value.findIndex((x) => !x.answered || x._showing)
  return i === -1 ? reviewItems.value.length : i
})
const curReview = computed(() => reviewItems.value[reviewIdx.value] || null)
const curSentence = computed(() => (curReview.value ? null : sentences.value.find((s) => !s.answered || s._showing) || null))
const reviewTotal = computed(() => reviewItems.value.length + sentences.value.length)
const reviewDone = computed(() => reviewItems.value.filter((x) => x.answered).length + sentences.value.filter((s) => s.answered).length)

const quizItems = computed(() => st.value?.quiz_items || [])
const quizIdx = computed(() => {
  const i = quizItems.value.findIndex((x) => !x.answered || x._showing)
  return i === -1 ? quizItems.value.length : i
})
const curQuiz = computed(() => quizItems.value[quizIdx.value] || null)
const quizAnswered = computed(() => quizItems.value.filter((x) => x.answered).length)
const quizCorrect = computed(() => quizItems.value.filter((x) => x.correct).length)

const nextStage = computed(() => {
  if (!result.value?.passed) return null
  const order = ['vocab', 'controlled', 'free']
  const n = order[order.indexOf(result.value.stage) + 1]
  return n && result.value.progress?.unlocked?.[n] ? n : null
})

const phaseLabel = computed(() => ({
  review: 'Ôn tập', quiz: 'Kiểm tra từ vựng', convo: st.value?.stage_labels?.[stage.value] || 'Hội thoại', result: 'Kết quả', loading: '',
}[phase.value]))

const progressPct = computed(() => {
  if (phase.value === 'review') return reviewTotal.value ? (100 * reviewDone.value) / reviewTotal.value : 0
  if (phase.value === 'quiz') return quizItems.value.length ? (100 * quizAnswered.value) / quizItems.value.length : 0
  if (phase.value === 'convo' && convo.value) return (100 * convo.value.user_turns) / convo.value.max_turns
  return 100
})

async function load() {
  try {
    st.value = await api.get(`/api/sessions/${sid}`)
    if (st.value.session.status === 'done') return router.replace(`/report/${sid}`)
    decide()
  } catch (e) {
    err.value = e.message
  }
}

function decide() {
  const s = st.value
  const reviewPending = s.review_items.some((x) => !x.answered) || sentences.value.some((x) => !x.answered)
  if (reviewPending) { phase.value = 'review'; return }
  const active = s.convos.find((c) => c.status !== 'done')
  if (active) { stage.value = active.stage; convo.value = active; phase.value = 'convo'; return }
  if (s.quiz_items.length && s.quiz_items.some((x) => !x.answered)) { stage.value = 'vocab'; phase.value = 'quiz'; return }
  if (s.convos.length) {
    const last = s.convos[s.convos.length - 1]
    result.value = { stage: last.stage, score: last.score, passed: last.score >= s.pass_threshold, turns: last.user_turns, progress: s.progress }
    phase.value = 'result'
    return
  }
  if (s.quiz_items.length) { finishQuiz(); return }
  goStage(s.session.start_stage)
}

async function goStage(sg) {
  stage.value = sg
  result.value = null
  err.value = ''
  if (sg === 'vocab') {
    phase.value = 'quiz'
    busy.value = true
    try { st.value = await api.post(`/api/sessions/${sid}/quiz/start`) } catch (e) { err.value = e.message } finally { busy.value = false }
  } else {
    phase.value = 'convo'
    await openConvo(sg)
  }
}

async function openConvo(sg) {
  convo.value = null
  convoErr.value = ''
  try {
    convo.value = await api.post(`/api/sessions/${sid}/convo`, { stage: sg })
  } catch (e) {
    convoErr.value = e.message
  }
}

function onAnswered(updated) {
  const list = updated.kind === 'review' ? st.value.review_items : st.value.quiz_items
  const i = list.findIndex((x) => x.id === updated.id)
  if (i >= 0) list[i] = { ...updated, _showing: true }
  streak.hit(updated.correct)
}

function advance() {
  for (const list of [st.value.review_items, st.value.quiz_items]) list.forEach((x) => delete x._showing)
  st.value.sentence_reviews.forEach((x) => delete x._showing)
  sentenceText.value = ''
  if (phase.value === 'review') {
    if (!curReview.value && !curSentence.value) decide()
    return
  }
  if (phase.value === 'quiz' && !curQuiz.value) finishQuiz()
}

async function finishQuiz() {
  busy.value = true
  try {
    const r = await api.post(`/api/sessions/${sid}/quiz/finish`)
    result.value = { ...r, stage: 'vocab' }
    phase.value = 'result'
  } catch (e) {
    err.value = e.message
  } finally {
    busy.value = false
  }
}

async function answerSentence() {
  const s = curSentence.value
  if (!s || !sentenceText.value.trim() || busy.value) return
  busy.value = true
  try {
    const r = await api.post(`/api/sentence-reviews/${s.id}/answer`, { answer: sentenceText.value })
    Object.assign(s, r, { answered: true, _showing: true })
    if (r.correct) playCorrect()
    else playWrong()
    streak.hit(r.correct)
  } catch (e) {
    err.value = e.message
  } finally {
    busy.value = false
  }
}

function skipSentence() {
  skipped.value = new Set([...skipped.value, curSentence.value.id])
  if (!curReview.value && !curSentence.value) decide()
}

function onConvoUpdate(c) {
  convo.value = c
}

async function finishConvo() {
  busy.value = true
  try {
    const r = await api.post(`/api/convos/${convo.value.id}/finish`)
    result.value = { ...r, stage: convo.value.stage }
    playResult(r.passed, r.score)
    st.value.convos = st.value.convos.filter((c) => c.id !== convo.value.id).concat([{ ...convo.value, status: 'done', score: r.score }])
    phase.value = 'result'
  } catch (e) {
    err.value = e.message
  } finally {
    busy.value = false
  }
}

async function endSession() {
  ending.value = true
  err.value = ''
  try {
    await api.post(`/api/sessions/${sid}/finish`)
    router.push(`/report/${sid}`)
  } catch (e) {
    err.value = e.message
  } finally {
    ending.value = false
  }
}

function exit() {
  router.push('/')
}

onMounted(async () => {
  await loadSettings()
  load()
})
</script>

<style scoped>
.topbar {
  position: sticky; top: 10px; z-index: 30; display: flex; align-items: center; gap: 14px;
  margin: 10px 16px 0; padding: 10px 18px; border-radius: 22px;
  background: color-mix(in srgb, var(--paper-2) 88%, transparent); backdrop-filter: blur(10px);
  box-shadow: var(--shadow-sm);
}
.tt { display: flex; align-items: baseline; gap: 10px; min-width: 0; flex: 1; }
.tt .small { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.tz { font-size: 21px; white-space: nowrap; }
.phase { color: var(--ink-faint); white-space: nowrap; font-weight: 700; }
.topprog { height: 8px; position: sticky; top: 76px; z-index: 29; margin: 8px 32px 0; }
.body { padding-top: 24px; }
.page.body.wide { max-width: 1320px; padding-bottom: 16px; }
@media (max-width: 620px) {
  .phase { display: none; }
  .topbar { padding: 8px 12px; gap: 8px; margin: 8px 10px 0; }
  .topprog { margin: 8px 20px 0; top: 66px; }
  .tt .small { display: none; }
}
.sr { padding: 24px; }
.task-note { font-size: 14px; }
.orig { font-size: 24px; margin: 10px 0 4px; letter-spacing: .02em; text-decoration: underline wavy var(--seal-fill); text-underline-offset: 7px; text-decoration-thickness: 2px; }
.good { font-size: 22px; color: var(--jade); }
.result-line { display: grid; grid-template-columns: auto 1fr auto; gap: 16px; align-items: start; margin-top: 18px; }
@media (max-width: 560px) { .result-line { grid-template-columns: auto 1fr; } .result-line .btn { grid-column: 1 / -1; } }
.res { display: flex; gap: 32px; align-items: center; padding: 36px; }
@media (max-width: 620px) { .res { flex-direction: column; align-items: flex-start; padding: 24px; } }
</style>

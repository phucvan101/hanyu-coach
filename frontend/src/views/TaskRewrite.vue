<template>
  <div class="page page-narrow">
    <RouterLink to="/talk" class="small">← Lộ trình cải thiện</RouterLink>
    <div v-if="!task" class="empty">{{ err || 'Đang tải…' }}</div>
    <template v-else>
      <div class="row spread wrap" style="margin: 8px 0 18px">
        <div>
          <span class="eyebrow">{{ task.kind_label }}</span>
          <h1>{{ task.title_vi }}</h1>
        </div>
        <span v-if="!finished" class="small muted">{{ Math.min(idx + 1, items.length) }}/{{ items.length }} · đúng {{ correct }}</span>
      </div>
      <p v-if="err" class="notice err" style="margin-bottom: 14px">{{ err }}</p>

      <section v-if="!finished && cur" class="card sr">
        <span class="eyebrow">Câu bạn đã nói</span>
        <p class="han orig">{{ cur.original }}</p>
        <p v-if="cur.grammar_point" class="small muted">Gợi ý: {{ cur.grammar_point }}</p>
        <form v-if="!res" class="row" style="margin-top: 14px" @submit.prevent="check">
          <HanziInput ref="inp" v-model="text" big placeholder="Viết lại câu đúng…" @submit="check" />
          <button class="btn primary" :disabled="busy || !text.trim()">Kiểm tra</button>
        </form>
        <div v-else class="result-line">
          <Seal :text="res.correct ? '对' : '错'" :tone="res.correct ? 'jade' : 'seal'" :size="48" />
          <div class="stack" style="gap: 4px">
            <p class="small">{{ res.feedback }}</p>
            <p class="small muted">Bạn viết: <span class="han">{{ text }}</span></p>
            <div class="row"><span class="han good">{{ res.corrected }}</span><SpeakButton :text="res.corrected" small /></div>
            <ErrorExplain :text="res.explanation_vi" />
          </div>
          <button ref="nextBtn" class="btn primary" type="button" @click="next">Tiếp →</button>
        </div>
      </section>

      <section v-else class="card summary">
        <Seal :text="String(score)" :tone="score >= 70 ? 'jade' : 'seal'" :size="72" />
        <div class="stack" style="gap: 6px">
          <h2>Viết đúng {{ correct }}/{{ items.length }} câu</h2>
          <p class="small muted">Câu nào viết đúng 2 lần (kể cả ở phần ôn đầu buổi) sẽ được coi là đã sửa xong trong Sổ lỗi.</p>
        </div>
        <div class="row wrap">
          <RouterLink to="/talk" class="btn primary">Về lộ trình</RouterLink>
          <button class="btn" type="button" @click="restart">Làm lại</button>
        </div>
      </section>
    </template>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { api } from '../api'
import HanziInput from '../components/HanziInput.vue'
import Seal from '../components/Seal.vue'
import SpeakButton from '../components/SpeakButton.vue'
import ErrorExplain from '../components/ErrorExplain.vue'
import { useStreak } from '../composables/useReactions'

const route = useRoute()
const task = ref(null)
const idx = ref(0)
const text = ref('')
const res = ref(null)
const correct = ref(0)
const busy = ref(false)
const err = ref('')
const finished = ref(false)
const inp = ref(null)
const nextBtn = ref(null)
const streak = useStreak()

const items = computed(() => task.value?.items || [])
const cur = computed(() => items.value[idx.value])
const score = computed(() => (items.value.length ? Math.round((100 * correct.value) / items.value.length) : 0))

async function check() {
  if (!text.value.trim() || busy.value || res.value) return
  busy.value = true
  err.value = ''
  try {
    res.value = await api.post(`/api/errors/${cur.value.id}/rewrite`, { answer: text.value })
    if (res.value.correct) correct.value++
    streak.hit(res.value.correct)
    await nextTick()
    nextBtn.value?.focus()
  } catch (e) {
    err.value = e.message
  } finally {
    busy.value = false
  }
}

async function next() {
  res.value = null
  text.value = ''
  if (idx.value + 1 < items.value.length) {
    idx.value++
    nextTick(() => inp.value?.focus?.())
    return
  }
  finished.value = true
  try { await api.post(`/api/plan-tasks/${task.value.id}/complete`, { score: score.value }) } catch (e) { err.value = e.message }
}

function restart() {
  idx.value = 0
  correct.value = 0
  streak.reset()
  finished.value = false
  res.value = null
  text.value = ''
}

onMounted(async () => {
  try {
    task.value = await api.get(`/api/plan-tasks/${route.params.id}`)
    if (!items.value.length) finished.value = true
  } catch (e) {
    err.value = e.message
  }
})
</script>

<style scoped>
.sr { padding: 24px; }
.orig { font-size: 24px; margin: 10px 0 4px; letter-spacing: .02em; text-decoration: underline wavy var(--seal-fill); text-underline-offset: 7px; text-decoration-thickness: 2px; }
.good { font-size: 22px; color: var(--jade); }
.result-line { display: grid; grid-template-columns: auto 1fr auto; gap: 16px; align-items: start; margin-top: 18px; }
@media (max-width: 560px) { .result-line { grid-template-columns: auto 1fr; } .result-line .btn { grid-column: 1 / -1; } }
.summary { display: flex; flex-direction: column; gap: 18px; padding: 28px; }
</style>

<template>
  <div class="page">
    <div class="row spread wrap" style="margin-bottom: 18px">
      <h1>Sổ lỗi</h1>
      <div class="tabs" role="tablist">
        <button role="tab" :aria-selected="tab === 'errors'" :class="{ on: tab === 'errors' }" @click="tab = 'errors'">Câu sai</button>
        <button role="tab" :aria-selected="tab === 'words'" :class="{ on: tab === 'words' }" @click="tab = 'words'">Từ yếu</button>
      </div>
    </div>

    <template v-if="tab === 'errors'">
      <div class="row wrap" style="margin-bottom: 12px; gap: 8px">
        <button class="btn" :class="{ primary: filter === 0 }" @click="filter = 0">Chưa sửa xong ({{ errors.filter((e) => !e.resolved).length }})</button>
        <button class="btn" :class="{ primary: filter === 1 }" @click="filter = 1">Đã sửa ({{ errors.filter((e) => e.resolved).length }})</button>
      </div>
      <p class="small muted" style="margin-bottom: 12px">Mỗi câu sai sẽ được đưa vào phần ôn đầu buổi. Viết lại đúng 2 lần thì câu đó được coi là đã sửa xong.</p>
      <div v-if="!shownErrors.length" class="empty">Không có câu nào.</div>
      <div class="grid grid-2">
        <article v-for="e in shownErrors" :key="e.id" class="card flat er">
          <p class="han o strike">{{ e.original }}</p>
          <div class="row"><p class="han c">{{ e.corrected }}</p><SpeakButton :text="e.corrected" small /></div>
          <p v-if="e.grammar_point" class="row wrap" style="gap: 6px"><span class="chip seal">{{ e.grammar_point }}</span></p>
          <ErrorExplain :text="e.explanation_vi" />
          <p class="tiny faint">{{ e.title_vi }} · ôn {{ e.review_count }} lần, đúng {{ e.correct_reviews }}</p>
        </article>
      </div>
    </template>

    <template v-else>
      <div class="row wrap" style="margin-bottom: 12px; gap: 8px">
        <button v-for="(l, k) in levels" :key="k" class="btn" :class="{ primary: lv === k }" @click="lv = k">{{ l }} ({{ words.filter((w) => k === 'all' || w.level === k).length }})</button>
      </div>
      <table class="tbl card flat">
        <thead><tr><th>Từ</th><th>Nghĩa</th><th class="hide-sm">Bài</th><th>Đúng / sai</th><th class="hide-sm">Sai thanh</th><th>Ôn lại</th></tr></thead>
        <tbody>
          <tr v-for="w in shownWords" :key="w.id">
            <td><div class="row" style="gap: 8px"><span class="han wz">{{ w.hanzi }}</span><SpeakButton :text="w.hanzi" small /></div><span class="py tiny">{{ w.pinyin }}</span></td>
            <td>{{ w.primary_meaning }}</td>
            <td class="small muted hide-sm">{{ w.title_vi }}</td>
            <td class="small"><span style="color: var(--jade)">{{ w.correct || 0 }}</span> / <span style="color: var(--seal)">{{ w.wrong || 0 }}</span></td>
            <td class="small hide-sm">{{ w.tone_errors || 0 }}</td>
            <td class="small muted">{{ due(w) }}</td>
          </tr>
        </tbody>
      </table>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { api } from '../api'
import SpeakButton from '../components/SpeakButton.vue'
import ErrorExplain from '../components/ErrorExplain.vue'

const tab = ref('errors')
const filter = ref(0)
const errors = ref([])
const words = ref([])
const lv = ref('weak')
const levels = { weak: 'Yếu', learning: 'Đang học', mastered: 'Đã thuộc', all: 'Tất cả' }
const shownErrors = computed(() => errors.value.filter((e) => e.resolved === filter.value))
const shownWords = computed(() => words.value.filter((w) => lv.value === 'all' || w.level === lv.value))

function due(w) {
  if (!w.due_at) return 'chưa học'
  const d = (new Date(w.due_at) - Date.now()) / 86400000
  return d <= 0 ? 'buổi tới' : `sau ${Math.ceil(d)} ngày`
}

onMounted(async () => {
  ;[errors.value, words.value] = await Promise.all([api.get('/api/errors'), api.get('/api/words')])
  if (!words.value.some((w) => w.level === 'weak')) lv.value = 'all'
})
</script>

<style scoped>
.tabs { display: inline-flex; background: var(--paper-3); border-radius: 18px; padding: 5px; box-shadow: var(--shadow-in); gap: 4px; }
.tabs button {
  border: 0; background: transparent; padding: 7px 18px; border-radius: 14px; cursor: pointer; font-weight: 800; color: var(--ink-soft);
  transition: background .18s, color .18s, transform .2s var(--ease-spring);
}
.tabs button:hover:not(.on) { color: var(--ink); }
.tabs button.on { background: var(--paper-2); color: var(--primary-strong); box-shadow: var(--shadow-sm); }
.tabs button:active { transform: scale(.96); }
.er { display: flex; flex-direction: column; gap: 6px; }
.o { font-size: 18px; }
.c { font-size: 21px; color: var(--jade); }
.wz { font-size: 21px; }
table.card { padding: 8px 10px; }
@media (max-width: 620px) { .hide-sm { display: none; } }
</style>

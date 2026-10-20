<template>
  <div class="page report-page">
    <div v-if="!st" class="empty">{{ err || 'Đang tải báo cáo…' }}</div>
    <template v-else-if="!rep">
      <div class="card empty">
        <p>Buổi học này chưa được tổng kết.</p>
        <button class="btn primary" style="margin-top: 12px" :disabled="busy" @click="finish">{{ busy ? 'Đang tổng kết…' : 'Tổng kết ngay' }}</button>
      </div>
    </template>
    <article v-else class="sheet">
      <header class="hd">
        <div class="stack" style="gap: 4px">
          <span class="eyebrow">Phiếu tổng kết · {{ fmtDate(st.session.started_at) }}</span>
          <h1 v-if="rep.unit.title_zh" class="han tz">{{ rep.unit.title_zh }}</h1>
          <h1 v-else class="han tz">综合会话</h1>
          <h2>{{ rep.unit.title_vi }}</h2>
          <p v-if="rep.unit.book_title" class="small muted">Quyển: {{ rep.unit.book_title }}</p>
          <p v-if="st.task" class="small"><span class="chip">Nhiệm vụ lộ trình</span> {{ st.task.title_vi }}</p>
        </div>
        <div class="seals">
          <figure v-for="s in rep.stages" :key="s.stage + s.score" class="sf">
            <Seal :text="String(s.score)" :tone="s.passed ? 'jade' : 'seal'" :size="62" />
            <figcaption class="tiny">{{ s.label }}</figcaption>
          </figure>
        </div>
      </header>

      <div class="layout">
        <div class="main-col stack">
      <p v-if="rep.ai.summary_vi" class="summary">{{ rep.ai.summary_vi }}</p>
      <p v-if="!rep.ai_generated" class="notice small">Phần nhận xét chi tiết cần AI (chưa có API key hoặc AI lỗi lúc tổng kết).</p>

      <section class="grid grid-2">
        <div class="card flat col jade">
          <h3>Điểm mạnh cần phát huy</h3>
          <ul><li v-for="(x, i) in rep.ai.strengths" :key="i">{{ x }}</li></ul>
          <p v-if="!rep.ai.strengths?.length" class="muted small">—</p>
        </div>
        <div class="card flat col seal">
          <h3>Điểm yếu cần cải thiện</h3>
          <ul><li v-for="(x, i) in rep.ai.weaknesses" :key="i">{{ x }}</li></ul>
          <p v-if="!rep.ai.weaknesses?.length" class="muted small">—</p>
        </div>
      </section>

      <section v-if="st.plan_tasks.length" class="card flat plan">
        <h3>Lộ trình cải thiện</h3>
        <p class="small muted" style="margin: 4px 0 14px">Làm lần lượt các bài dưới đây để sửa đúng những lỗi của buổi này. Danh sách cũng nằm ở trang Hội thoại tổng hợp.</p>
        <TaskList :tasks="st.plan_tasks" />
      </section>

      <section v-if="rep.sentence_errors.length" class="card flat">
        <h3>Câu sai trong hội thoại <span class="faint small">· {{ rep.sentence_errors.length }} câu, sẽ được ôn lại buổi sau</span></h3>
        <ol class="errs">
          <li v-for="(e, i) in rep.sentence_errors" :key="i" class="err">
            <div class="pair">
              <span class="lbl">Bạn nói</span>
              <p class="han o strike">{{ e.original }}</p>
              <span class="lbl ok">Câu đúng</span>
              <div class="row c-row"><p class="han c">{{ e.corrected }}</p><SpeakButton :text="e.corrected" small /><SpeakButton :text="e.corrected" small slow /></div>
            </div>
            <div class="row wrap tags">
              <span v-for="t in (e.error_type || '').split(', ').filter(Boolean)" :key="t" class="chip">{{ typeLabel(t) }}</span>
              <span v-for="g in (e.grammar_point || '').split('; ').filter(Boolean)" :key="g" class="chip seal">{{ g }}</span>
            </div>
            <ErrorExplain :text="e.explanation_vi" />
          </li>
        </ol>
      </section>

      <section v-if="rep.ai.grammar_notes?.length" class="card flat">
        <h3>Ghi chú ngữ pháp</h3>
        <div v-for="(g, i) in rep.ai.grammar_notes" :key="i" class="gn">
          <p class="gp">{{ g.point }}</p>
          <p class="small">{{ g.explanation_vi }}</p>
          <ul class="exs"><li v-for="(x, j) in g.examples" :key="j" class="han">{{ x }}</li></ul>
        </div>
      </section>

      <section v-if="rep.wrong_words.length || rep.tone_warnings.length" class="card flat">
        <h3 style="margin-bottom: 8px">Từ vựng trả lời sai</h3>
        <table v-if="rep.wrong_words.length" class="tbl">
          <thead><tr><th>Từ</th><th>Nghĩa</th><th>Dạng câu</th><th>Bạn chọn</th></tr></thead>
          <tbody>
            <tr v-for="(w, i) in rep.wrong_words" :key="i">
              <td><span class="han wz">{{ w.hanzi }}</span><br /><span class="py tiny">{{ w.pinyin }}</span></td>
              <td>{{ w.meaning }}</td>
              <td class="small muted">{{ w.qtype }}<span v-if="w.kind === 'review'"> (ôn)</span></td>
              <td class="small"><span class="strike">{{ w.user_answer }}</span></td>
            </tr>
          </tbody>
        </table>
        <div v-if="rep.tone_warnings.length" style="margin-top: 14px">
          <p class="small"><b>Đúng âm nhưng sai/thiếu thanh điệu:</b></p>
          <div class="row wrap" style="gap: 8px; margin-top: 6px">
            <span v-for="(w, i) in rep.tone_warnings" :key="i" class="chip gold">
              <span class="han">{{ w.hanzi }}</span> {{ w.pinyin }} · bạn gõ "{{ w.user_answer }}"
            </span>
          </div>
        </div>
      </section>

      <section v-if="unusedWords.length || rep.good_sentences.length" class="grid grid-2">
        <div v-if="rep.good_sentences.length" class="card flat">
          <h3>Câu nói tốt</h3>
          <ul class="plain"><li v-for="(s, i) in rep.good_sentences" :key="i" class="han gs">{{ s }}</li></ul>
        </div>
        <div v-if="unusedWords.length" class="card flat">
          <h3>Từ mục tiêu chưa dùng</h3>
          <div class="row wrap" style="gap: 6px; margin-top: 8px"><span v-for="w in unusedWords" :key="w" class="chip han big">{{ w }}</span></div>
        </div>
      </section>

      <div class="row wrap">
        <RouterLink v-if="rep.mode === 'book'" to="/talk" class="btn primary lg">{{ st.task ? 'Về lộ trình' : 'Về Hội thoại tổng hợp' }}</RouterLink>
        <RouterLink v-else to="/" class="btn primary lg">Về trang học</RouterLink>
        <button class="btn lg" :disabled="busy" @click="again">{{ rep.mode === 'book' ? 'Nói lại chủ đề này' : 'Học lại bài này' }}</button>
      </div>
        </div>

        <aside class="side-col stack">


      <section class="card flat">
        <h3 style="margin-bottom: 14px">Điểm theo kỹ năng</h3>
        <SkillBars :skills="rep.skills" :labels="rep.skill_labels" />
      </section>

      <template v-if="rep.mode === 'book'">
        <div class="card flat">
          <h3>Từ của quyển bạn đã tự dùng</h3>
          <p class="small muted" style="margin: 4px 0 8px">{{ rep.book_words_used.length }} / {{ rep.book_word_total }} từ</p>
          <div class="row wrap" style="gap: 6px"><span v-for="w in rep.book_words_used" :key="w" class="chip jade han big">{{ w }}</span></div>
          <p v-if="!rep.book_words_used.length" class="muted small">Chưa dùng từ nào của quyển.</p>
        </div>
        <div class="card flat">
          <h3>Từ mới AI dùng thêm</h3>
          <p class="small muted" style="margin: 4px 0 8px">Ngoài vốn từ của bạn — nên ghi lại nếu thấy hữu ích.</p>
          <ul class="plain nws">
            <li v-for="n in rep.new_words" :key="n.hanzi">
              <div class="row" style="gap: 8px"><b class="han nwh">{{ n.hanzi }}</b><span class="py small">{{ n.pinyin }}</span><SpeakButton :text="n.hanzi" small /></div>
              <p class="small"><b>{{ n.meaning_vi }}</b><span v-if="n.explain_vi" class="muted"> — {{ n.explain_vi }}</span></p>
            </li>
          </ul>
          <p v-if="!rep.new_words.length" class="muted small">AI chỉ dùng từ bạn đã học.</p>
        </div>
      </template>

      <section v-if="rep.ai.next_steps?.length" class="card flat">
        <h3>Buổi sau nên làm</h3>
        <ul><li v-for="(x, i) in rep.ai.next_steps" :key="i">{{ x }}</li></ul>
      </section>
        </aside>
      </div>
    </article>
    <p v-if="err && st" class="notice err">{{ err }}</p>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api, fmtDate } from '../api'
import { errorTypeLabel } from '../labels'
import Seal from '../components/Seal.vue'
import SkillBars from '../components/SkillBars.vue'
import SpeakButton from '../components/SpeakButton.vue'
import TaskList from '../components/TaskList.vue'
import ErrorExplain from '../components/ErrorExplain.vue'

const route = useRoute()
const router = useRouter()
const sid = Number(route.params.id)
const st = ref(null)
const err = ref('')
const busy = ref(false)
const rep = computed(() => st.value?.session?.report || null)
const unusedWords = computed(() => [...new Set((rep.value?.target_words || []).flatMap((t) => t.unused))])

const typeLabel = errorTypeLabel

async function load() {
  try { st.value = await api.get(`/api/sessions/${sid}`) } catch (e) { err.value = e.message }
}
async function finish() {
  busy.value = true
  try { await api.post(`/api/sessions/${sid}/finish`); await load() } catch (e) { err.value = e.message } finally { busy.value = false }
}
async function again() {
  busy.value = true
  try {
    const ss = st.value.session
    const s = ss.start_stage === 'book'
      ? await api.post('/api/book-sessions', { book_id: ss.book_id, topic: ss.topic, max_turns: ss.focus?.max_turns })
      : await api.post('/api/sessions', { unit_id: ss.unit_id })
    router.push(`/session/${s.session.id}`)
  } catch (e) { err.value = e.message } finally { busy.value = false }
}
onMounted(load)
</script>

<style scoped>
.report-page { max-width: 1360px; }
.sheet { display: flex; flex-direction: column; gap: 22px; }
/* màn rộng: nhận xét bên trái, lộ trình + số liệu bên phải */
.layout { display: grid; grid-template-columns: minmax(0, 1fr) minmax(320px, 400px); gap: 22px; align-items: start; }
.main-col, .side-col { gap: 20px; min-width: 0; }
@media (max-width: 1080px) {
  .layout { grid-template-columns: 1fr; }
}
.hd { display: flex; justify-content: space-between; gap: 24px; align-items: flex-end; padding-bottom: 20px; border-bottom: 3px dashed var(--line); }
@media (max-width: 620px) { .hd { flex-direction: column; align-items: flex-start; } }
.tz { font-size: 46px; letter-spacing: .04em; margin-top: 4px; }
.seals { display: flex; gap: 20px; }
.sf { margin: 0; display: flex; flex-direction: column; align-items: center; gap: 12px; text-align: center; max-width: 132px; }
.sf figcaption { color: var(--ink-soft); font-weight: 700; }
.summary { font-size: 16.5px; max-width: 65ch; font-weight: 600; }
.col h3 { margin-bottom: 10px; }
.col.jade { box-shadow: inset 0 6px 0 var(--jade-fill), var(--shadow-sm); }
.col.seal { box-shadow: inset 0 6px 0 var(--seal-fill), var(--shadow-sm); }
.col ul, section > ul { margin: 0; padding-left: 18px; display: flex; flex-direction: column; gap: 6px; }
.errs { margin: 14px 0 0; padding: 0; list-style: none; display: flex; flex-direction: column; gap: 14px; }
.err { display: flex; flex-direction: column; gap: 12px; padding: 16px 18px; border-radius: 20px; background: var(--paper-2); box-shadow: var(--shadow-sm); }
/* nhãn bên trái, câu bên phải: hai câu thẳng hàng để so sánh */
.pair { display: grid; grid-template-columns: auto 1fr; gap: 6px 14px; align-items: center; }
.lbl { font-size: 11px; font-weight: 900; text-transform: uppercase; letter-spacing: .05em; color: var(--seal); white-space: nowrap; }
.lbl.ok { color: var(--jade); }
.o { font-size: 19px; line-height: 1.4; color: var(--ink-soft); }
.c-row { gap: 8px; }
.c { font-size: 22px; line-height: 1.4; color: var(--jade); }
.tags { gap: 6px; }
.gn { padding: 14px 0; border-bottom: 2px dashed var(--line); }
.gn:last-child { border-bottom: 0; }
.gp { font-weight: 900; margin-bottom: 4px; }
.exs { margin: 6px 0 0; padding-left: 18px; font-size: 17px; }
.wz { font-size: 20px; }
.plain { list-style: none; padding: 0; margin: 8px 0 0; display: flex; flex-direction: column; gap: 8px; }
.gs { font-size: 18px; }
.chip.big { font-size: 16px; padding: 6px 14px; }
.nws { gap: 12px; }
.nwh { font-size: 20px; color: var(--gold); }
.plan { box-shadow: inset 0 6px 0 var(--primary), var(--shadow-sm); }
</style>

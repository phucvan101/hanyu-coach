<template>
  <div class="page">
    <RouterLink to="/library" class="small">← Thư viện</RouterLink>
    <div v-if="!b" class="empty">Đang tải…</div>
    <template v-else>
      <div class="row spread wrap" style="margin: 8px 0 18px">
        <h1>{{ b.title }}</h1>
        <span class="small muted">Sửa nghĩa chính (dùng để kiểm tra) hoặc chuyển từ sang bài khác. Thay đổi lưu ngay.</span>
      </div>

      <details v-if="b.grammar_points.length" class="card flat gp">
        <summary><b>{{ b.grammar_points.length }} điểm ngữ pháp</b> <span class="muted small">rút từ tài liệu</span></summary>
        <ul>
          <li v-for="g in b.grammar_points" :key="g.id">
            <b class="han">{{ g.pattern }}</b> — {{ g.explanation_vi }}
            <span v-if="g.example_zh" class="muted"> · <span class="han">{{ g.example_zh }}</span> ({{ g.example_vi }})</span>
          </li>
        </ul>
      </details>

      <section v-for="u in b.units" :key="u.id" class="card unit">
        <div class="uh">
          <input class="input ttl han" :value="u.title_zh" placeholder="Tên tiếng Trung" @change="(e) => saveUnit(u, 'title_zh', e.target.value)" />
          <input class="input ttl" :value="u.title_vi" @change="(e) => saveUnit(u, 'title_vi', e.target.value)" />
        </div>
        <div class="grid grid-3 roles">
          <label><span class="label">Tình huống</span><input class="input" :value="u.scenario_vi" @change="(e) => saveUnit(u, 'scenario_vi', e.target.value)" /></label>
          <label><span class="label">AI đóng vai</span><input class="input" :value="u.ai_role_vi" @change="(e) => saveUnit(u, 'ai_role_vi', e.target.value)" /></label>
          <label><span class="label">Bạn đóng vai</span><input class="input" :value="u.user_role_vi" @change="(e) => saveUnit(u, 'user_role_vi', e.target.value)" /></label>
        </div>
        <table class="tbl">
          <thead><tr><th style="width: 22%">Từ</th><th>Nghĩa chính</th><th class="hide-sm">Nghĩa từ điển</th><th style="width: 150px">Bài</th></tr></thead>
          <tbody>
            <tr v-for="w in u.words" :key="w.id">
              <td>
                <div class="row" style="gap: 8px">
                  <span class="han wz">{{ w.hanzi }}</span>
                  <SpeakButton :text="w.hanzi" small />
                </div>
                <span class="py tiny">{{ w.pinyin }}</span>
                <span v-if="w.is_function_word" class="chip tiny" style="margin-left: 4px">hư từ</span>
                <span class="lv" :class="w.level" :title="levelLabel[w.level]"></span>
              </td>
              <td><input class="input sm" :value="w.primary_meaning" @change="(e) => saveWord(w, { primary_meaning: e.target.value })" /></td>
              <td class="small muted hide-sm">{{ w.meanings.join('; ') }}</td>
              <td>
                <select class="select sm" :value="w.unit_id" @change="(e) => moveWord(w, Number(e.target.value))">
                  <option v-for="x in b.units" :key="x.id" :value="x.id">{{ x.idx }}. {{ x.title_vi }}</option>
                </select>
              </td>
            </tr>
          </tbody>
        </table>
      </section>
      <p v-if="saved" class="toast">{{ saved }}</p>
    </template>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { api } from '../api'
import SpeakButton from '../components/SpeakButton.vue'

const route = useRoute()
const b = ref(null)
const saved = ref('')
const levelLabel = { new: 'Chưa học', learning: 'Đang học', weak: 'Yếu', mastered: 'Đã thuộc' }
let t = null

async function load() { b.value = await api.get(`/api/books/${route.params.id}`) }
function flash(m) { saved.value = m; clearTimeout(t); t = setTimeout(() => (saved.value = ''), 1600) }
async function saveUnit(u, k, v) { await api.patch(`/api/units/${u.id}`, { [k]: v }); u[k] = v; flash('Đã lưu') }
async function saveWord(w, body) { await api.patch(`/api/vocab/${w.id}`, body); Object.assign(w, body); flash('Đã lưu') }
async function moveWord(w, unitId) { await api.patch(`/api/vocab/${w.id}`, { unit_id: unitId }); flash('Đã chuyển bài'); load() }
onMounted(load)
</script>

<style scoped>
.gp { margin-bottom: 18px; }
.gp summary { cursor: pointer; font-weight: 800; }
.gp ul { margin: 12px 0 0; padding-left: 18px; display: flex; flex-direction: column; gap: 6px; font-size: 14.5px; }
.unit { margin-bottom: 18px; }
.uh { display: grid; grid-template-columns: 220px 1fr; gap: 10px; margin-bottom: 12px; }
.ttl { font-size: 17px; font-weight: 800; }
.ttl.han { font-size: 20px; font-weight: 400; }
.roles { margin-bottom: 14px; gap: 8px; }
.wz { font-size: 22px; }
.input.sm, .select.sm { padding: 7px 10px; font-size: 14px; border-radius: 12px; }
.lv { display: inline-block; width: 10px; height: 10px; border-radius: 4px; margin-left: 6px; background: var(--paper-3); box-shadow: var(--shadow-in); }
.lv.mastered { background: var(--jade-fill); box-shadow: none; }
.lv.learning { background: var(--sun); box-shadow: none; }
.lv.weak { background: var(--seal-fill); box-shadow: none; }
.toast {
  position: fixed; bottom: 24px; left: 50%; transform: translateX(-50%); background: var(--ink); color: var(--paper);
  padding: 10px 18px; border-radius: 16px; font-size: 13.5px; font-weight: 800; z-index: 60;
  box-shadow: 0 12px 24px -10px rgba(0, 0, 0, .45); animation: toast .35s var(--ease-spring) both;
}
@keyframes toast { from { opacity: 0; transform: translate(-50%, 12px) scale(.95); } }
@media (max-width: 760px) { .uh { grid-template-columns: 1fr; } .hide-sm { display: none; } .toast { bottom: 96px; } }
</style>

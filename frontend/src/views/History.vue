<template>
  <div class="page">
    <header class="ph">
      <div>
        <h1>Lịch sử học</h1>
        <p class="muted small">Mọi buổi học đã làm, mới nhất ở trên. Bấm "Báo cáo" để xem lại lỗi và nhận xét của từng buổi.</p>
      </div>
      <RouterLink to="/" class="btn primary">Học buổi mới</RouterLink>
    </header>

    <div v-if="loading" class="empty">Đang tải…</div>

    <section v-else-if="!rows.length" class="card none">
      <div class="none-art" aria-hidden="true"><span class="han">史</span></div>
      <h2>Chưa có buổi học nào</h2>
      <p class="muted">Học xong buổi đầu tiên, lịch sử và điểm từng kỹ năng sẽ hiện ở đây.</p>
      <RouterLink to="/" class="btn primary lg">Bắt đầu buổi đầu tiên</RouterLink>
    </section>

    <div v-else class="hist">
      <ul class="list">
        <li v-for="s in rows" :key="s.id" class="card it">
          <div class="when">
            <span class="d">{{ day(s.started_at) }}</span>
            <span class="tiny">{{ time(s.started_at) }}</span>
          </div>
          <div class="what">
            <div class="row wrap tl">
              <h3>{{ s.title_vi || 'Bài đã xoá' }}</h3>
              <span class="chip" :class="s.status === 'done' ? 'jade' : 'gold'">{{ s.status === 'done' ? 'Hoàn thành' : 'Đang dở' }}</span>
            </div>
            <p class="tiny muted meta">
              Bắt đầu ở {{ stageLabel[s.start_stage] || s.start_stage }}<template v-if="mins(s) !== null"> · {{ mins(s) }} phút</template>
            </p>
            <div v-if="s.quiz_score !== null || Object.keys(s.skill_scores || {}).length" class="sk">
              <span v-if="s.quiz_score !== null" class="pill" :class="tone(s.quiz_score)">Từ vựng <b>{{ s.quiz_score }}%</b></span>
              <span v-for="(v, k) in s.skill_scores || {}" :key="k" class="pill" :class="tone(v)">{{ skillShort[k] || k }} <b>{{ v }}</b></span>
            </div>
          </div>
          <div class="go">
            <RouterLink v-if="s.status === 'done'" :to="`/report/${s.id}`" class="btn">Báo cáo</RouterLink>
            <RouterLink v-else :to="`/session/${s.id}`" class="btn primary">Học tiếp</RouterLink>
            <button class="btn ghost del" :class="{ armed: confirm === s.id }" :aria-label="confirm === s.id ? 'Bấm lần nữa để xoá' : 'Xoá buổi học'" @click="del(s)">
              {{ confirm === s.id ? 'Xoá?' : '×' }}
            </button>
          </div>
        </li>
      </ul>

      <aside class="side">
        <section class="card">
          <h3>Tổng quan</h3>
          <div class="tiles">
            <div class="tile"><b>{{ rows.length }}</b><span>buổi học</span></div>
            <div class="tile"><b>{{ totalMins }}</b><span>phút đã học</span></div>
            <div class="tile"><b>{{ studyDays }}</b><span>ngày có học</span></div>
            <div class="tile"><b>{{ doneCount }}</b><span>buổi hoàn thành</span></div>
          </div>
        </section>
        <section class="card">
          <h3 style="margin-bottom: 12px">Điểm trung bình kỹ năng</h3>
          <SkillBars :skills="avgSkills" :labels="skillShort" />
        </section>
      </aside>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { api } from '../api'
import SkillBars from '../components/SkillBars.vue'

const rows = ref([])
const loading = ref(true)
const confirm = ref(null)
const stageLabel = { vocab: 'từ vựng', controlled: 'hội thoại có kiểm soát', free: 'hội thoại tự do', book: 'hội thoại tổng hợp' }
const skillShort = { recognition: 'Nhận diện', pinyin: 'Pinyin', tones: 'Thanh', listening: 'Nghe', writing: 'Viết', grammar: 'Ngữ pháp', communication: 'Giao tiếp', vocab_usage: 'Vận dụng' }
const day = (iso) => new Date(iso).toLocaleDateString('vi-VN', { day: '2-digit', month: '2-digit' })
const time = (iso) => new Date(iso).toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' })
const tone = (v) => (v >= 70 ? 'jade' : v >= 50 ? 'gold' : 'seal')
const mins = (s) => (s.ended_at ? Math.max(1, Math.round((new Date(s.ended_at) - new Date(s.started_at)) / 60000)) : null)

const doneCount = computed(() => rows.value.filter((s) => s.status === 'done').length)
const totalMins = computed(() => rows.value.reduce((n, s) => n + (mins(s) || 0), 0))
const studyDays = computed(() => new Set(rows.value.map((s) => new Date(s.started_at).toDateString())).size)
const avgSkills = computed(() => {
  const sum = {}, cnt = {}
  rows.value.forEach((s) => Object.entries(s.skill_scores || {}).forEach(([k, v]) => {
    sum[k] = (sum[k] || 0) + v
    cnt[k] = (cnt[k] || 0) + 1
  }))
  return Object.fromEntries(Object.keys(sum).map((k) => [k, Math.round(sum[k] / cnt[k])]))
})

async function load() { try { rows.value = await api.get('/api/sessions') } finally { loading.value = false } }
async function del(s) {
  if (confirm.value !== s.id) { confirm.value = s.id; setTimeout(() => (confirm.value = null), 3000); return }
  await api.del(`/api/sessions/${s.id}`)
  load()
}
onMounted(load)
</script>

<style scoped>
.ph { display: flex; justify-content: space-between; align-items: flex-end; gap: 16px; margin-bottom: 20px; }
.ph p { margin-top: 4px; max-width: 62ch; }
@media (max-width: 620px) { .ph { flex-direction: column; align-items: flex-start; } }

.hist { display: grid; grid-template-columns: minmax(0, 1fr) 340px; gap: 20px; align-items: start; }
@media (max-width: 980px) { .hist { grid-template-columns: 1fr; } .side { position: static; } }

.list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 14px; }
.it {
  display: grid; grid-template-columns: 76px minmax(0, 1fr) auto; gap: 18px; align-items: center; padding: 16px 18px;
  transition: transform .25s var(--ease-spring);
}
.it:hover { transform: translateY(-2px); }
.when {
  display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 2px; padding: 10px 4px;
  border-radius: 18px; background: var(--primary-soft); box-shadow: var(--shadow-in); color: var(--ink-soft); font-weight: 700;
}
.d { font-weight: 900; font-size: 17px; font-variant-numeric: tabular-nums; color: var(--primary-strong); }
.tl { gap: 10px; }
.meta { margin-top: 2px; }
.sk { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 10px; }
.pill {
  display: inline-flex; align-items: baseline; gap: 5px; padding: 4px 10px; border-radius: 10px;
  font-size: 12.5px; font-weight: 700; color: var(--ink-soft); background: var(--paper-3);
}
.pill b { font-weight: 900; font-variant-numeric: tabular-nums; }
.pill.jade { background: var(--jade-soft); } .pill.jade b { color: var(--jade); }
.pill.gold { background: var(--gold-soft); } .pill.gold b { color: var(--gold); }
.pill.seal { background: var(--seal-soft); } .pill.seal b { color: var(--seal); }
.go { display: flex; gap: 6px; align-items: center; }
.del { width: 40px; height: 40px; padding: 0; font-size: 18px; color: var(--ink-faint); }
.del.armed { width: auto; padding: 0 12px; color: var(--seal); background: var(--seal-soft); font-size: 13.5px; }
@media (max-width: 560px) {
  .it { grid-template-columns: 64px minmax(0, 1fr); }
  .go { grid-column: 1 / -1; justify-content: flex-end; }
}

.side { display: flex; flex-direction: column; gap: 16px; position: sticky; top: 16px; }
.tiles { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 12px; }
.tile {
  display: flex; flex-direction: column; gap: 2px; padding: 12px 14px; border-radius: 18px;
  background: var(--paper-3); box-shadow: var(--shadow-in); font-size: 12.5px; font-weight: 700; color: var(--ink-soft);
}
.tile b { font-size: 26px; font-weight: 900; line-height: 1.1; color: var(--ink); font-variant-numeric: tabular-nums; }
.tile:nth-child(1) b { color: var(--primary-strong); }
.tile:nth-child(2) b { color: var(--gold); }
.tile:nth-child(3) b { color: var(--jade); }
.side :deep(.r) { grid-template-columns: 82px 1fr 44px; }

.none { display: flex; flex-direction: column; align-items: center; text-align: center; gap: 10px; padding: 48px 24px; }
.none p { max-width: 46ch; }
.none .btn { margin-top: 8px; }
.none-art {
  width: 84px; height: 84px; border-radius: 28px; background: var(--primary); color: #fff; font-size: 44px;
  display: inline-flex; align-items: center; justify-content: center; transform: rotate(-8deg); margin-bottom: 6px;
  box-shadow: 0 6px 0 0 var(--primary-edge), 0 16px 28px -12px color-mix(in srgb, var(--primary) 70%, transparent), inset 0 3px 0 rgba(255, 255, 255, .35);
}
</style>

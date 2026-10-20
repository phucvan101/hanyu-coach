<template>
  <div class="page">
    <div v-if="loading" class="empty">Đang tải…</div>

    <template v-else-if="d">
      <div v-if="err" class="notice err" style="margin-bottom: 16px">{{ err }}</div>

      <!-- chưa có dữ liệu -->
      <section v-if="!d.books.length" class="welcome card">
        <TianZiGe text="你好" :size="88" mi />
        <div class="stack" style="gap: 10px">
          <h1>Bắt đầu bằng file từ vựng của bạn</h1>
          <p class="muted">Tải lên file CSV xuất từ Hanzii (mỗi file là một quyển bạn đã học xong). App sẽ chia bài theo chủ đề, kiểm tra từ vựng rồi cho bạn luyện hội thoại với đúng những từ đó.</p>
          <div class="row wrap">
            <RouterLink to="/library" class="btn primary lg">Nhập file từ vựng</RouterLink>
            <RouterLink v-if="!d.llm_configured" to="/settings" class="btn lg">Nhập API key</RouterLink>
          </div>
        </div>
      </section>

      <template v-else>
        <div v-if="!d.llm_configured" class="notice" style="margin-bottom: 16px">
          Chưa có API key nên phần hội thoại và báo cáo AI chưa dùng được. <RouterLink to="/settings">Nhập Gemini API key</RouterLink>.
        </div>

        <div v-if="d.active_session" class="notice ok row spread wrap" style="margin-bottom: 16px">
          <span>Bạn có một buổi học đang dở ({{ fmtDate(d.active_session.started_at) }}).</span>
          <RouterLink :to="`/session/${d.active_session.id}`" class="btn primary">Học tiếp buổi này</RouterLink>
        </div>

        <div v-if="d.open_tasks" class="notice row spread wrap" style="margin-bottom: 16px">
          <span>Lộ trình cải thiện còn <b>{{ d.open_tasks }}</b> việc chưa làm.</span>
          <RouterLink to="/talk" class="btn">Xem lộ trình</RouterLink>
        </div>

        <!-- buổi học tiếp theo -->
        <section v-if="next" class="hero card">
          <div class="hero-main">
            <span class="eyebrow">Bài tiếp theo · {{ next.book.title }}</span>
            <h1 class="hz han">{{ next.unit.title_zh || next.unit.title_vi }}</h1>
            <h2 class="tv">{{ next.unit.title_vi }}</h2>
            <p class="muted sc">{{ next.unit.scenario_vi }}</p>
            <StagePath :progress="next.unit.progress" class="sp" />
          </div>
          <aside class="hero-side">
            <ul class="today">
              <li><b>{{ d.due_words }}</b> từ đến hạn ôn</li>
              <li><b>{{ d.open_errors }}</b> câu sai chờ sửa lại</li>
              <li><b>{{ d.streak }}</b> ngày học liên tiếp</li>
            </ul>
            <button class="btn primary lg" :disabled="starting" @click="start()">
              {{ starting ? 'Đang chuẩn bị…' : `Bắt đầu: ${d.stage_labels[d.recommend.stage]}` }}
            </button>
            <span class="tiny faint">Khoảng 10–20 phút. Có ôn tập nhanh ở đầu buổi.</span>
          </aside>
        </section>

        <!-- kỹ năng -->
        <section class="grid grid-2 stats" style="margin-top: 16px">
          <div class="card vocab">
            <div class="row spread" style="margin-bottom: 12px">
              <h3>Điểm kỹ năng qua các buổi</h3>
              <span class="tiny faint">{{ d.history.length }} buổi</span>
            </div>
            <SkillChart v-if="d.history.length >= 2" :history="d.history" :labels="d.skill_labels" />
            <div v-else class="chart-empty">
              <div class="ce-art" aria-hidden="true"><i></i><i></i><i></i><i></i></div>
              <p class="ce-title">Chưa đủ dữ liệu để vẽ biểu đồ</p>
              <p class="muted small">{{ d.history.length ? 'Học thêm 1 buổi nữa để thấy điểm kỹ năng thay đổi qua từng buổi.' : 'Học xong 2 buổi để thấy điểm kỹ năng thay đổi qua từng buổi.' }}</p>
            </div>
          </div>
          <div class="card vocab">
            <h3 style="margin-bottom: 12px">Vốn từ</h3>
            <div class="mastery-bar" role="img" :aria-label="masteryAria">
              <span v-for="k in mOrder" :key="k" :class="'m-' + k" :style="{ flex: d.totals[k] || 0 }"></span>
            </div>
            <ul class="mleg">
              <li v-for="k in mOrder" :key="k"><i :class="'m-' + k"></i>{{ mLabel[k] }} <b>{{ d.totals[k] }}</b></li>
            </ul>
            <p class="tiny faint note">"Đã thuộc" = trả lời đúng liên tục, khoảng ôn ≥ 7 ngày. "Yếu" = vừa trả lời sai, sẽ xuất hiện ở phần ôn tập.</p>
          </div>
        </section>

        <!-- lộ trình bài học -->
        <section v-for="b in d.books" :key="b.id" class="book-path">
          <div class="bp-head">
            <div>
              <h2>{{ b.title }}</h2>
              <p class="small muted">{{ b.word_count }} từ · {{ b.units.length }} bài · <b>{{ doneUnits(b) }}/{{ b.units.length }}</b> bài đã xong cả 3 bước</p>
            </div>
            <span v-if="b.status === 'importing'" class="chip gold">{{ b.status_msg }}</span>
            <ul class="legend-s" aria-label="Chú thích trạng thái">
              <li><i class="lg-cur"></i>Bài tiếp theo</li>
              <li><i class="lg-act"></i>Đang học</li>
              <li><i class="lg-done"></i>Đã xong</li>
              <li><i class="lg-new"></i>Chưa học</li>
            </ul>
          </div>

          <ol class="path-list">
            <li v-for="u in b.units" :key="u.id" class="step" :class="unitState(u)">
              <span class="node" aria-hidden="true">
                <svg v-if="unitState(u) === 'done'" viewBox="0 0 16 16" width="16" height="16"><path d="M3 8.5l3 3 7-7" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/></svg>
                <template v-else>{{ u.idx }}</template>
              </span>

              <article class="ucard" :class="{ open: isOpen(u) }">
                <component :is="unitState(u) === 'cur' ? 'div' : 'button'" class="uhead" :type="unitState(u) === 'cur' ? undefined : 'button'"
                  :aria-expanded="unitState(u) === 'cur' ? undefined : isOpen(u)" @click="unitState(u) !== 'cur' && toggle(u)">
                  <span class="ut-wrap">
                    <span class="han uz">{{ u.title_zh || '—' }}</span>
                    <span class="ut">{{ u.title_vi }}</span>
                  </span>
                  <span class="meta">
                    <span v-if="unitState(u) === 'cur'" class="chip">Bài tiếp theo</span>
                    <span v-else-if="unitState(u) === 'act'" class="chip gold">{{ bestText(u) }}</span>
                    <span v-else-if="unitState(u) === 'done'" class="chip jade">Đã xong</span>
                    <span v-else class="tiny faint">{{ u.word_count }} từ</span>
                    <svg v-if="unitState(u) !== 'cur'" class="chev" viewBox="0 0 16 16" width="14" height="14" aria-hidden="true"><path d="M4 6l4 4 4-4" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
                  </span>
                </component>

                <div v-if="isOpen(u)" class="ubody">
                  <p v-if="u.scenario_vi" class="small muted">{{ u.scenario_vi }}</p>
                  <div class="mastery-bar thin" role="img" :aria-label="`${u.word_count} từ`">
                    <span v-for="k in mOrder" :key="k" :class="'m-' + k" :style="{ flex: u.mastery[k] || 0 }"></span>
                  </div>
                  <div class="acts">
                    <button v-for="st in stageKeys" :key="st" type="button" class="btn sbtn"
                      :class="stageBtn(u, st)" :disabled="!u.progress.unlocked[st] || starting"
                      :title="u.progress.unlocked[st] ? '' : `Cần ≥ ${d.pass_threshold}% ở bước trước`" @click="start(u.id, st)">
                      <svg v-if="stageBtn(u, st) === 'locked'" viewBox="0 0 16 16" width="12" height="12" aria-hidden="true"><rect x="3.5" y="7" width="9" height="6.5" rx="1.5" fill="currentColor"/><path d="M5.5 7V5.5a2.5 2.5 0 0 1 5 0V7" fill="none" stroke="currentColor" stroke-width="1.6"/></svg>
                      <svg v-else-if="stageBtn(u, st) === 'passed'" viewBox="0 0 16 16" width="12" height="12" aria-hidden="true"><path d="M3 8.5l3 3 7-7" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/></svg>
                      <span>{{ short[st] }}</span>
                      <span v-if="u.progress[st + '_best']" class="pct">{{ u.progress[st + '_best'] }}%</span>
                    </button>
                  </div>
                </div>
              </article>
            </li>
          </ol>
        </section>
      </template>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, onBeforeUnmount, ref } from 'vue'
import { useRouter } from 'vue-router'
import { api, fmtDate } from '../api'
import StagePath from '../components/StagePath.vue'
import SkillChart from '../components/SkillChart.vue'
import TianZiGe from '../components/TianZiGe.vue'

const router = useRouter()
const d = ref(null)
const loading = ref(true)
const starting = ref(false)
const err = ref('')
const stageKeys = ['vocab', 'controlled', 'free']
const short = { vocab: 'Từ vựng', controlled: 'Hội thoại 1', free: 'Hội thoại 2' }
const mOrder = ['mastered', 'learning', 'weak', 'new']
const mLabel = { mastered: 'Đã thuộc', learning: 'Đang học', weak: 'Yếu', new: 'Chưa học' }
let poll = null
const opened = ref(new Set())

// trạng thái bài: cur = bài được đề xuất, done = qua cả 3 bước, act = đã bắt đầu, new = chưa học
function unitState(u) {
  if (u.id === d.value?.recommend?.unit_id) return 'cur'
  const p = u.progress
  if (p.free_passed) return 'done'
  if (p.vocab_best || p.controlled_best || p.free_best || u.mastery.learning || u.mastery.weak || u.mastery.mastered) return 'act'
  return 'new'
}
const isOpen = (u) => unitState(u) === 'cur' || opened.value.has(u.id)
function toggle(u) {
  const n = new Set(opened.value)
  n.has(u.id) ? n.delete(u.id) : n.add(u.id)
  opened.value = n
}
const doneUnits = (b) => b.units.filter((u) => u.progress.free_passed).length
function bestText(u) {
  const p = u.progress
  if (p.controlled_passed) return 'Còn Hội thoại 2'
  if (p.vocab_passed) return 'Còn Hội thoại 1'
  return p.vocab_best ? `Từ vựng ${p.vocab_best}%` : 'Đã bắt đầu'
}
// nút bước: passed = đã qua, next = bước nên làm tiếp, open = làm lại được, locked = chưa mở
function stageBtn(u, st) {
  const p = u.progress
  if (!p.unlocked[st]) return 'locked'
  if (p[st + '_passed']) return 'passed'
  const firstOpen = stageKeys.find((k) => p.unlocked[k] && !p[k + '_passed'])
  return st === firstOpen ? 'next' : 'open'
}

const next = computed(() => {
  if (!d.value?.recommend) return null
  for (const b of d.value.books) {
    const u = b.units.find((x) => x.id === d.value.recommend.unit_id)
    if (u) return { book: b, unit: u }
  }
  return null
})
const masteryAria = computed(() => d.value ? mOrder.map((k) => `${mLabel[k]} ${d.value.totals[k]}`).join(', ') : '')

async function load() {
  try {
    d.value = await api.get('/api/dashboard')
    err.value = ''
    const importing = d.value.books.some((b) => b.status === 'importing')
    clearTimeout(poll)
    if (importing) poll = setTimeout(load, 2500)
  } catch (e) {
    err.value = e.message
  } finally {
    loading.value = false
  }
}

async function start(unit_id, stage) {
  starting.value = true
  err.value = ''
  try {
    const st = await api.post('/api/sessions', unit_id ? { unit_id, stage } : {})
    router.push(`/session/${st.session.id}`)
  } catch (e) {
    err.value = e.message
    window.scrollTo({ top: 0, behavior: 'smooth' })
  } finally {
    starting.value = false
  }
}

onMounted(load)
onBeforeUnmount(() => clearTimeout(poll))
</script>

<style scoped>
.welcome { display: flex; gap: 32px; align-items: center; padding: 36px; }
@media (max-width: 620px) { .welcome { flex-direction: column; align-items: flex-start; padding: 24px; } }

.hero {
  display: grid; grid-template-columns: minmax(0, 1fr) minmax(300px, 360px); gap: 24px; align-items: center;
  padding: 24px 28px; position: relative; overflow: hidden;
  background:
    radial-gradient(22rem 16rem at 100% 0%, color-mix(in srgb, var(--gold-fill) 22%, transparent), transparent 70%),
    radial-gradient(18rem 14rem at 0% 100%, color-mix(in srgb, var(--jade-fill) 16%, transparent), transparent 70%),
    var(--paper-2);
}
.hero::after {
  content: ''; position: absolute; width: 120px; height: 120px; right: -36px; bottom: -48px; border-radius: 40px;
  background: var(--primary); opacity: .1; transform: rotate(18deg); pointer-events: none;
}
.hero-main { display: flex; flex-direction: column; gap: 4px; min-width: 0; position: relative; z-index: 1; }
.hz { font-size: 52px; line-height: 1.1; margin-top: 4px; letter-spacing: 0.04em; }
.tv { font-size: 20px; font-weight: 800; }
.sc { max-width: 60ch; }
.sp { margin-top: 16px; max-width: 560px; }
.hero-side {
  display: flex; flex-direction: column; gap: 12px; position: relative; z-index: 1;
  padding: 14px; border-radius: 22px; background: color-mix(in srgb, var(--paper-3) 80%, transparent); box-shadow: var(--shadow-in);
}
.today { list-style: none; margin: 0; padding: 0; display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; }
.today li {
  display: flex; flex-direction: column; align-items: center; text-align: center; gap: 2px;
  padding: 10px 6px; border-radius: 16px; background: var(--paper-2); box-shadow: var(--shadow-sm);
  color: var(--ink-soft); font-size: 12px; font-weight: 700; line-height: 1.3;
}
.today b { color: var(--primary-strong); font-size: 24px; font-weight: 900; line-height: 1.1; font-variant-numeric: tabular-nums; }
.today li:nth-child(2) b { color: var(--seal); }
.today li:nth-child(3) b { color: var(--gold); }
.hero-side .btn { width: 100%; }
.hero-side .tiny { text-align: center; }
@media (max-width: 860px) {
  .hero { grid-template-columns: 1fr; padding: 20px; }
  .hz { font-size: 42px; }
}

/* biểu đồ rộng hơn, thẻ vốn từ lấp đầy chiều cao bằng các ô số */
.stats { grid-template-columns: minmax(0, 3fr) minmax(0, 2fr); align-items: stretch; }
@media (max-width: 860px) { .stats { grid-template-columns: 1fr; } }
.vocab { display: flex; flex-direction: column; }
.vocab .note { margin: 12px 0 0; padding: 0; text-align: left; max-width: none; }

.chart-empty {
  flex: 1; min-height: 236px; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 6px;
  text-align: center; border-radius: 20px; background: var(--paper-3); box-shadow: var(--shadow-in); padding: 20px;
}
.ce-title { font-weight: 800; color: var(--ink); }
.ce-art { display: flex; align-items: flex-end; gap: 8px; height: 64px; margin-bottom: 8px; }
.ce-art i {
  width: 18px; border-radius: 7px; background: var(--c);
  box-shadow: 0 3px 0 0 color-mix(in srgb, var(--c) 70%, #000), inset 0 2px 0 rgba(255, 255, 255, .4);
  animation: grow 2.4s var(--ease-spring) infinite alternate;
}
.ce-art i:nth-child(1) { --c: var(--primary); height: 26px; }
.ce-art i:nth-child(2) { --c: var(--gold-fill); height: 40px; animation-delay: .2s; }
.ce-art i:nth-child(3) { --c: var(--jade-fill); height: 32px; animation-delay: .4s; }
.ce-art i:nth-child(4) { --c: var(--seal-fill); height: 54px; animation-delay: .6s; }
@keyframes grow { from { transform: scaleY(.55); transform-origin: bottom; } to { transform: scaleY(1); transform-origin: bottom; } }

.mastery-bar { display: flex; height: 16px; border-radius: 999px; overflow: hidden; background: var(--paper-3); gap: 3px; box-shadow: var(--shadow-in); padding: 2px; }
.mastery-bar > * { border-radius: 999px; box-shadow: inset 0 2px 0 rgba(255, 255, 255, .35); }
.mastery-bar.thin { height: 8px; margin: 10px 0 12px; padding: 0; gap: 2px; }
.m-mastered { background: var(--jade-fill); }
.m-learning { background: var(--sun); }
.m-weak { background: var(--seal-fill); }
.m-new { background: transparent; box-shadow: none !important; }
.mleg {
  list-style: none; padding: 0; margin: 14px 0 0; flex: 1;
  display: grid; grid-template-columns: 1fr 1fr; gap: 10px; font-size: 13px; color: var(--ink-soft); font-weight: 800;
}
.mleg li {
  display: flex; flex-direction: column; justify-content: center; gap: 4px; padding: 12px 14px;
  border-radius: 18px; background: var(--paper-3); box-shadow: var(--shadow-in);
}
.mleg i { display: inline-block; width: 12px; height: 12px; border-radius: 4px; margin-right: 6px; vertical-align: -1px; }
.mleg i.m-new { background: var(--paper-2); box-shadow: var(--shadow-sm) !important; }
.mleg b { display: block; color: var(--ink); font-size: 28px; font-weight: 900; line-height: 1; font-variant-numeric: tabular-nums; }

/* ---------- lộ trình bài học (zic-zac) ---------- */
.book-path { margin-top: 32px; }
.bp-head { display: flex; flex-wrap: wrap; align-items: flex-end; justify-content: space-between; gap: 12px 24px; margin-bottom: 20px; }
.bp-head p { margin-top: 2px; }
.legend-s { list-style: none; margin: 0; padding: 0; display: flex; flex-wrap: wrap; gap: 6px 16px; font-size: 12.5px; font-weight: 700; color: var(--ink-soft); }
.legend-s i { display: inline-block; width: 10px; height: 10px; border-radius: 99px; margin-right: 6px; vertical-align: -0.5px; }
.lg-cur { background: var(--primary); }
.lg-act { background: var(--gold-fill); }
.lg-done { background: var(--jade-fill); }
.lg-new { background: var(--paper-2); box-shadow: inset 0 0 0 2px var(--line); }

.path-list { --node: 48px; list-style: none; margin: 0 auto; padding: 4px 0 8px; max-width: 1080px; position: relative; display: flex; flex-direction: column; gap: 8px; }
/* đường nét đứt chạy dọc giữa lộ trình */
.path-list::before {
  content: ''; position: absolute; left: 50%; top: 24px; bottom: 24px; width: 0; transform: translateX(-50%);
  border-left: 3px dashed color-mix(in srgb, var(--ink-faint) 45%, transparent);
}
.step { display: grid; grid-template-columns: minmax(0, 1fr) var(--node) minmax(0, 1fr); column-gap: 22px; align-items: center; position: relative; }
.step .node { grid-column: 2; grid-row: 1; }
.step .ucard { grid-row: 1; width: 100%; max-width: 470px; }
.step:nth-child(odd) .ucard { grid-column: 1; justify-self: end; }
.step:nth-child(even) .ucard { grid-column: 3; justify-self: start; }
/* gạch nối ngắn từ nút tròn sang thẻ */
.step::after {
  content: ''; position: absolute; top: 50%; width: 22px; border-top: 3px dashed color-mix(in srgb, var(--ink-faint) 45%, transparent);
  left: calc(50% - var(--node) / 2 - 22px);
}
.step:nth-child(even)::after { left: calc(50% + var(--node) / 2); }

.node {
  width: var(--node); height: var(--node); border-radius: 18px; position: relative; z-index: 1;
  display: inline-flex; align-items: center; justify-content: center; font-weight: 900; font-size: 16px;
  background: var(--paper-2); color: var(--ink-faint); box-shadow: var(--shadow-sm), inset 0 0 0 2px var(--line);
}
.step.cur .node {
  background: var(--primary); color: #fff; transform: scale(1.12);
  box-shadow: 0 4px 0 0 var(--primary-edge), var(--hilite), 0 0 0 7px color-mix(in srgb, var(--primary) 18%, transparent);
  animation: beacon 2.4s ease-in-out infinite;
}
@keyframes beacon { 50% { box-shadow: 0 4px 0 0 var(--primary-edge), var(--hilite), 0 0 0 12px color-mix(in srgb, var(--primary) 8%, transparent); } }
.step.act .node { background: var(--gold-fill); color: #fff; box-shadow: 0 3px 0 0 color-mix(in srgb, var(--gold-fill) 68%, #000), var(--hilite); }
.step.done .node { background: var(--jade-fill); color: #fff; box-shadow: 0 3px 0 0 var(--jade-edge), var(--hilite); }

/* thẻ bài */
.ucard {
  border-radius: 22px; background: var(--paper-2); box-shadow: var(--shadow-sm); overflow: hidden;
  transition: transform .25s var(--ease-spring), box-shadow .2s, opacity .2s;
}
.step.new .ucard { opacity: .62; background: color-mix(in srgb, var(--paper-2) 70%, transparent); box-shadow: inset 0 0 0 2px var(--line); }
.step.new .ucard:hover, .step.new .ucard.open, .step.new .ucard:focus-within { opacity: 1; background: var(--paper-2); box-shadow: var(--shadow-sm); }
.step.cur .ucard { box-shadow: inset 0 0 0 2.5px var(--primary), var(--shadow); max-width: 520px; }
.ucard:not(.open):hover { transform: translateY(-2px); }

.uhead {
  width: 100%; display: flex; align-items: center; justify-content: space-between; gap: 12px; text-align: left;
  padding: 14px 18px; border: 0; background: none; color: inherit; font: inherit; cursor: pointer; border-radius: 22px;
}
div.uhead { cursor: default; padding-top: 18px; }
.ut-wrap { display: flex; flex-direction: column; min-width: 0; }
.uz { font-size: 22px; letter-spacing: .03em; line-height: 1.25; }
.step.cur .uz { font-size: 26px; }
.ut { font-size: 14px; font-weight: 800; color: var(--ink-soft); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.meta { display: inline-flex; align-items: center; gap: 8px; flex: none; }
.chev { color: var(--ink-faint); transition: transform .25s var(--ease-spring); }
.ucard.open .chev { transform: rotate(180deg); }

.ubody { padding: 0 18px 18px; display: flex; flex-direction: column; gap: 4px; animation: unfold .3s var(--ease-spring) both; }
@keyframes unfold { from { opacity: 0; transform: translateY(-6px); } }
.acts { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px; }
.sbtn { min-height: 42px; padding: 8px 10px; font-size: 13.5px; border-radius: 14px; gap: 5px; flex-wrap: wrap; white-space: normal; line-height: 1.15; }
.sbtn .pct { font-size: 11.5px; font-weight: 800; opacity: .8; }
.sbtn.next { --edge: var(--primary-edge); background: var(--primary); color: var(--primary-ink); }
.sbtn.passed { --edge: var(--jade-edge); background: var(--jade-soft); color: var(--jade); }
.sbtn.locked { --edge: transparent; background: var(--paper-3); color: var(--ink-faint); box-shadow: var(--shadow-in); opacity: 1; }
@media (pointer: coarse) { .sbtn { min-height: 48px; } .acts { gap: 12px; } }

/* màn hẹp: đường lộ trình chạy dọc bên trái, mọi thẻ nằm bên phải */
@media (max-width: 760px) {
  .path-list { --node: 40px; gap: 14px; }
  .path-list::before { left: calc(var(--node) / 2); transform: none; margin-left: -1.5px; }
  .step { grid-template-columns: var(--node) minmax(0, 1fr); column-gap: 14px; }
  .step .node { grid-column: 1; border-radius: 14px; font-size: 14px; }
  .step:nth-child(odd) .ucard, .step:nth-child(even) .ucard { grid-column: 2; justify-self: stretch; max-width: none; }
  .step::after, .step:nth-child(even)::after { left: var(--node); width: 14px; }
  .uhead { padding: 12px 14px; }
  .ubody { padding: 0 14px 14px; }
}
</style>

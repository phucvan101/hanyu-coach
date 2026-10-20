<template>
  <aside class="intel" aria-label="Nhận xét & gợi ý">
    <header class="ih">
      <span class="eyebrow">Trợ lý học</span>
      <button v-if="closable" type="button" class="x" aria-label="Đóng" @click="$emit('close')">
        <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"/></svg>
      </button>
    </header>

    <!-- 1. trọng tâm: câu đang chọn -->
    <section v-if="!turn" class="blk empty-state">
      <p class="lead">Nói câu đầu tiên nhé.</p>
      <p class="small muted">Sau mỗi câu, nhận xét, cách nói tự nhiên hơn và giải thích lỗi sẽ hiện ở đây.</p>
      <p v-if="intro" class="small task">{{ intro }}</p>
    </section>

    <!-- câu của người học -->
    <section v-else-if="turn.role === 'user'" :key="'u' + turn.id" class="blk focus">
      <div class="row spread">
        <h3>Câu của bạn</h3>
        <div class="ring" :class="tone" :style="{ '--p': ev.score || 0 }" :aria-label="`Điểm ${ev.score}`">
          <span>{{ ev.score }}</span>
        </div>
      </div>
      <p class="han mine"><template v-for="(p, i) in mineParts" :key="i"><mark v-if="p.bad">{{ p.s }}</mark><template v-else>{{ p.s }}</template></template></p>
      <p v-if="turn.input_mode === 'pinyin'" class="tiny faint">bạn gõ: {{ turn.raw_text }}</p>
      <div v-if="mineAudio || turn.input_mode === 'voice'" class="row voice-row">
        <button v-if="mineAudio" type="button" class="pill" @click="playUrl(mineAudio)">▶ Giọng bạn</button>
        <span v-else class="tiny faint">nói bằng giọng</span>
      </div>

      <p v-if="ev.hint_vi" class="coach" :class="tone">{{ ev.hint_vi }}</p>

      <div v-if="ev.corrected && !isSame" class="natural">
        <span class="lbl">{{ hasErrors ? 'Câu đúng' : 'Tự nhiên hơn' }}</span>
        <div class="row" style="gap: 8px; align-items: flex-start">
          <p class="han nat">{{ ev.corrected }}</p>
          <SpeakButton :text="ev.corrected" small />
          <SpeakButton :text="ev.corrected" small slow />
        </div>
        <p v-if="ev.corrected_vi" class="small muted">{{ ev.corrected_vi }}</p>
      </div>

      <ul v-if="hasErrors" class="errs">
        <li v-for="(e, i) in ev.errors" :key="i">
          <div class="row wrap" style="gap: 6px">
            <span v-if="e.type" class="chip">{{ errorTypeLabel(e.type) }}</span>
            <span v-if="e.grammar_point" class="chip seal">{{ e.grammar_point }}</span>
          </div>
          <p class="fixline"><span class="han strike">{{ e.original }}</span> <span class="arrow">→</span> <span class="han ok">{{ e.correction }}</span></p>
          <p v-if="e.explanation_vi" class="small">{{ e.explanation_vi }}</p>
        </li>
      </ul>

      <p v-if="ev.used_words?.length" class="small used">
        Dùng đúng từ mục tiêu: <span v-for="w in ev.used_words" :key="w" class="chip jade han">{{ w }}</span>
      </p>
    </section>

    <!-- câu của AI -->
    <section v-else :key="'a' + turn.id" class="blk focus">
      <h3>Câu của AI</h3>
      <p class="han ai-hz">{{ turn.hanzi }}</p>
      <p class="py small">{{ turn.pinyin }}</p>
      <p class="small muted">{{ turn.vi }}</p>
      <div class="row" style="gap: 8px; margin-top: 6px">
        <SpeakButton :text="turn.hanzi" small />
        <SpeakButton :text="turn.hanzi" small slow />
      </div>
      <div v-if="turn.notes?.length" class="nws">
        <div v-for="n in turn.notes" :key="n.hanzi" class="nw">
          <div class="row" style="gap: 8px">
            <b class="han nwh">{{ n.hanzi }}</b><span class="py small">{{ n.pinyin }}</span>
            <span class="spk-pair"><SpeakButton :text="n.hanzi" small /><SpeakButton :text="n.hanzi" small slow /></span>
          </div>
          <p v-if="n.meaning_vi" class="small"><b>{{ n.meaning_vi }}</b><span v-if="n.explain_vi" class="muted"> — {{ n.explain_vi }}</span></p>
          <p v-else class="small faint">Đang lấy nghĩa…</p>
        </div>
      </div>
    </section>

    <!-- 2. mục tiêu buổi -->
    <details class="blk" :open="targetsOpen" @toggle="(e) => (targetsOpen = e.target.open)">
      <summary>
        <span>Từ cần dùng</span>
        <span class="meter"><span :style="{ width: (100 * used.length) / Math.max(1, targets.length) + '%' }"></span></span>
        <span class="small muted">{{ used.length }}/{{ targets.length }}</span>
      </summary>
      <div class="tws">
        <span v-for="w in targets" :key="w" class="tw han" :class="{ on: used.includes(w) }" :title="meaningOf(w)">
          {{ w }}<small v-if="!used.includes(w) && meaningOf(w)">{{ meaningOf(w) }}</small>
        </span>
      </div>
    </details>

    <!-- 3. từ mới trong buổi (chỉ khi có) -->
    <details v-if="allNotes.length" class="blk">
      <summary><span>Từ mới trong buổi</span><span class="small muted">{{ allNotes.length }}</span></summary>
      <div class="nws">
        <div v-for="n in allNotes" :key="n.hanzi" class="nw">
          <div class="row" style="gap: 8px">
            <b class="han nwh">{{ n.hanzi }}</b><span class="py small">{{ n.pinyin }}</span>
            <span class="spk-pair"><SpeakButton :text="n.hanzi" small /><SpeakButton :text="n.hanzi" small slow /></span>
          </div>
          <p v-if="n.meaning_vi" class="small"><b>{{ n.meaning_vi }}</b><span v-if="n.explain_vi" class="muted"> — {{ n.explain_vi }}</span></p>
          <p v-else class="small faint">Đang lấy nghĩa…</p>
        </div>
      </div>
    </details>
  </aside>
</template>

<script setup>
import { computed, ref } from 'vue'
import { errorTypeLabel } from '../labels'
import SpeakButton from './SpeakButton.vue'

const props = defineProps({
  turn: { type: Object, default: null },
  convo: { type: Object, required: true },
  words: { type: Array, default: () => [] },
  audio: { type: Object, default: () => ({}) },
  intro: { type: String, default: '' },
  closable: Boolean,
})
defineEmits(['close'])

const targetsOpen = ref(true)
const ev = computed(() => props.turn?.eval || {})
const hasErrors = computed(() => !!ev.value.errors?.length)
const tone = computed(() => ((ev.value.score ?? 0) >= 80 ? 'jade' : (ev.value.score ?? 0) >= 60 ? 'gold' : 'seal'))
const strip = (s) => (s || '').replace(/[\s，。？！、；：,.?!;:"'“”‘’（）()…—-]/g, '')
const isSame = computed(() => strip(ev.value.corrected) === strip(props.turn?.hanzi))
const mineAudio = computed(() => (props.turn ? props.audio[props.turn.id] : ''))
const targets = computed(() => props.convo.target_words || [])
const used = computed(() => props.convo.used_words || [])
const allNotes = computed(() => {
  const m = new Map()
  for (const t of props.convo.turns) for (const n of t.notes || []) if (!m.has(n.hanzi)) m.set(n.hanzi, n)
  return [...m.values()]
})

// tô các đoạn sai ngay trong câu người học nói
const mineParts = computed(() => {
  const text = props.turn?.hanzi || ''
  const bad = (ev.value.errors || []).map((e) => e.original).filter((o) => o && text.includes(o))
  if (!bad.length) return [{ s: text }]
  const esc = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  const re = new RegExp(`(${bad.sort((a, b) => b.length - a.length).map(esc).join('|')})`)
  return text.split(re).filter(Boolean).map((s) => ({ s, bad: bad.includes(s) }))
})

function meaningOf(w) { return props.words.find((x) => x.hanzi === w)?.meaning || '' }
function playUrl(u) { new Audio(u).play().catch(() => {}) }
</script>

<style scoped>
.intel { display: flex; flex-direction: column; gap: 12px; }
.ih { display: flex; align-items: center; justify-content: space-between; padding: 0 4px; }
.x { border: 0; background: var(--paper-3); color: var(--ink-soft); width: 34px; height: 34px; border-radius: 12px; cursor: pointer; display: inline-flex; align-items: center; justify-content: center; }
.blk { background: var(--paper-2); border-radius: 22px; padding: 16px 18px; box-shadow: var(--shadow-sm); }
.focus { animation: slide .3s var(--ease-spring) both; }
@keyframes slide { from { opacity: 0; transform: translateX(10px); } }
h3 { font-size: 15px; font-weight: 900; }
.lead { font-weight: 900; font-size: 16px; margin-bottom: 4px; }
.task { margin-top: 10px; padding: 10px 12px; border-radius: 14px; background: var(--paper-3); }

.ring {
  --p: 0; --c: var(--ink-faint);
  width: 46px; height: 46px; border-radius: 50%; display: grid; place-items: center; flex: none;
  background: conic-gradient(var(--c) calc(var(--p) * 1%), var(--paper-3) 0);
}
.ring span { width: 36px; height: 36px; border-radius: 50%; background: var(--paper-2); display: grid; place-items: center; font-weight: 900; font-size: 14px; }
.ring.jade { --c: var(--jade-fill); }
.ring.gold { --c: var(--gold-fill); }
.ring.seal { --c: var(--seal-fill); }
.mine { font-size: 22px; line-height: 1.5; margin-top: 6px; }
.mine mark { background: none; color: var(--seal); text-decoration: underline wavy var(--seal-fill); text-underline-offset: 6px; text-decoration-thickness: 2px; }
.voice-row { margin-top: 4px; }
.pill { border: 0; cursor: pointer; font: inherit; font-size: 12.5px; font-weight: 800; padding: 4px 12px; border-radius: 999px; background: var(--paper-3); color: var(--primary-strong); }
.coach { margin-top: 10px; padding: 10px 12px; border-radius: 14px; font-size: 14px; font-weight: 600; background: var(--paper-3); }
.coach.jade { background: var(--jade-soft); }
.coach.seal { background: var(--seal-soft); }
.coach.gold { background: var(--gold-soft); }
.natural { margin-top: 12px; }
.lbl { font-size: 10.5px; font-weight: 900; text-transform: uppercase; letter-spacing: .06em; color: var(--jade); }
.nat { font-size: 21px; color: var(--jade); line-height: 1.45; flex: 1; min-width: 0; }
.errs { list-style: none; margin: 12px 0 0; padding: 0; display: flex; flex-direction: column; gap: 10px; }
.errs li { padding: 10px 12px; border-radius: 14px; background: var(--paper-3); display: flex; flex-direction: column; gap: 4px; }
.fixline { font-size: 17px; }
.arrow { color: var(--ink-faint); }
.ok { color: var(--jade); }
.used { margin-top: 10px; display: flex; flex-wrap: wrap; align-items: center; gap: 6px; }
.ai-hz { font-size: 22px; line-height: 1.5; margin-top: 6px; }
.nws { display: flex; flex-direction: column; gap: 10px; margin-top: 12px; }
.nw { padding: 10px 12px; border-radius: 14px; background: var(--gold-soft); }
.nwh { font-size: 20px; color: var(--gold); }
.spk-pair { display: inline-flex; gap: 6px; margin-left: auto; }

details.blk summary { display: flex; align-items: center; gap: 10px; cursor: pointer; font-weight: 900; font-size: 14px; list-style: none; }
details.blk summary::-webkit-details-marker { display: none; }
details.blk summary::after { content: '▾'; margin-left: auto; color: var(--ink-faint); transition: transform .2s; }
details.blk:not([open]) summary::after { transform: rotate(-90deg); }
.meter { flex: 1; height: 6px; border-radius: 9px; background: var(--paper-3); overflow: hidden; max-width: 120px; }
.meter span { display: block; height: 100%; background: var(--jade-fill); border-radius: 9px; transition: width .4s var(--ease-spring); }
.tws { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 12px; }
.tw { display: inline-flex; flex-direction: column; align-items: center; padding: 4px 10px; border-radius: 12px; font-size: 17px; border: 2px dashed var(--line); line-height: 1.2; }
.tw small { font-family: var(--font-ui); font-size: 10.5px; color: var(--ink-faint); font-weight: 700; max-width: 90px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.tw.on { border: 2px solid transparent; background: var(--jade-soft); color: var(--jade); }
</style>

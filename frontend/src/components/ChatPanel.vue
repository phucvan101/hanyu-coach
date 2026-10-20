<template>
  <div class="ws">
    <!-- KHU HỘI THOẠI -->
    <section class="conv">
      <header class="ch">
        <div class="ch-main">
          <span class="eyebrow">{{ convo.stage_label }}</span>
          <p class="intro" :class="{ open: introOpen }" @click="introOpen = !introOpen">{{ convo.intro_vi }}</p>
        </div>
        <div class="seg" role="group" aria-label="Hiển thị">
          <button type="button" :aria-pressed="showPy" :class="{ on: showPy }" @click="showPy = !showPy">Pinyin</button>
          <button type="button" :aria-pressed="showVi" :class="{ on: showVi }" @click="showVi = !showVi">Nghĩa</button>
          <button type="button" :aria-pressed="autoSpeak" :class="{ on: autoSpeak }" title="Tự đọc câu của AI" @click="autoSpeak = !autoSpeak">
            <svg viewBox="0 0 24 24" width="15" height="15" aria-hidden="true"><path d="M4 9v6h4l5 4V5L8 9H4z" fill="currentColor"/><path d="M16 8.5a4.5 4.5 0 0 1 0 7" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
            Tự đọc
          </button>
        </div>
      </header>

      <div ref="list" class="msgs" aria-live="polite">
        <template v-for="t in convo.turns" :key="t.id">
          <!-- AI -->
          <div v-if="t.role === 'ai'" class="msg ai" :class="{ sel: selected?.id === t.id, talking: speaking === t.hanzi }">
            <span class="av" aria-hidden="true">
              <i></i><i></i><i></i>
            </span>
            <div class="bubble" role="button" tabindex="0" @click="select(t)" @keydown.enter="select(t)">
              <p class="hz han"><template v-for="(p, i) in parts(t)" :key="i"><b v-if="p.nw" class="nw">{{ p.s }}</b><template v-else>{{ p.s }}</template></template></p>
              <p v-if="showPy || openPy.has(t.id)" class="py small">{{ t.pinyin }}</p>
              <p v-if="showVi || openVi.has(t.id)" class="vi small">{{ t.vi }}</p>
              <div class="tools" @click.stop>
                <SpeakButton :text="t.hanzi" small />
                <button v-if="!showPy" type="button" class="tl" @click="flip(openPy, t.id)">pinyin</button>
                <button v-if="!showVi" type="button" class="tl" @click="flip(openVi, t.id)">nghĩa</button>
                <button v-if="t.notes?.length" type="button" class="tl gold" @click="select(t)">{{ t.notes.length }} từ mới</button>
              </div>
            </div>
          </div>

          <!-- người học -->
          <div v-else class="msg me" :class="{ sel: selected?.id === t.id }">
            <div class="bubble" role="button" tabindex="0" @click="select(t)" @keydown.enter="select(t)">
              <p class="hz han">{{ t.hanzi }}</p>
              <p class="meta tiny">
                <svg v-if="t.input_mode === 'voice'" viewBox="0 0 24 24" width="12" height="12" aria-hidden="true"><rect x="9" y="3" width="6" height="11" rx="3" fill="currentColor"/><path d="M5.5 11a6.5 6.5 0 0 0 13 0" fill="none" stroke="currentColor" stroke-width="2"/></svg>
                <template v-if="t.input_mode === 'pinyin'">gõ: {{ t.raw_text }}</template>
                <template v-else-if="t.input_mode === 'voice'">giọng nói</template>
              </p>
            </div>
            <div v-if="t.eval" class="verdict" :class="tone(t)" @click="select(t)">
              <span class="sc">{{ t.score }}</span>
              <span v-if="!hasFix(t)" class="vt">✓ {{ t.score >= 80 ? 'Tự nhiên' : 'Hiểu được' }}</span>
              <template v-else>
                <span class="lbl">Nên nói</span>
                <span class="han fx">{{ t.eval.corrected }}</span>
              </template>
              <span class="more">chi tiết →</span>
            </div>
          </div>
        </template>
        <div v-if="sending" class="msg me pending">
          <div class="bubble"><p class="hz han">{{ pendingText }}</p></div>
          <div class="verdict thinking"><i></i><i></i><i></i><span class="vt">đang chấm…</span></div>
        </div>
      </div>

      <div v-if="convo.status === 'ready'" class="notice ok row spread wrap">
        <span>Đủ lượt rồi. Kết thúc để chấm điểm hội thoại.</span>
        <button class="btn primary" :disabled="finishing" @click="$emit('finish')">Chấm điểm</button>
      </div>
      <VoiceComposer v-else ref="composer" :disabled="sending" @send="send" />
      <p v-if="err" class="notice err small">{{ err }}</p>

      <footer class="foot">
        <span class="turns" :aria-label="`Lượt ${convo.user_turns}/${convo.max_turns}`">
          <i v-for="n in convo.max_turns" :key="n" :class="{ on: n <= convo.user_turns }"></i>
        </span>
        <span class="small muted">Lượt {{ convo.user_turns }}/{{ convo.max_turns }}</span>
        <button class="btn ghost small insight-btn" type="button" @click="sheet = true">
          Nhận xét<span v-if="lastHasErrors" class="badge"></span>
        </button>
        <button class="btn small" type="button" :disabled="convo.user_turns < 1 || finishing" @click="$emit('finish')">
          {{ finishing ? 'Đang chấm…' : 'Kết thúc hội thoại' }}
        </button>
      </footer>
    </section>

    <!-- BẢNG TRỢ LÝ -->
    <div class="side" :class="{ open: sheet }" @click.self="sheet = false">
      <InsightPanel :turn="selected" :convo="convo" :words="words" :audio="audio" :intro="convo.intro_vi"
        :closable="sheet" @close="sheet = false" />
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue'
import { api } from '../api'
import { speak, speaking } from '../composables/useTts'
import { settings } from '../composables/useSettings'
import InsightPanel from './InsightPanel.vue'
import SpeakButton from './SpeakButton.vue'
import VoiceComposer from './VoiceComposer.vue'

const props = defineProps({ convo: { type: Object, required: true }, words: { type: Array, default: () => [] }, finishing: Boolean })
const emit = defineEmits(['update', 'finish'])

const sending = ref(false)
const pendingText = ref('')
const err = ref('')
const list = ref(null)
const composer = ref(null)
const showPy = ref(settings.show_pinyin !== '0')
const showVi = ref(settings.show_vi === '1')
const autoSpeak = ref(true)
const introOpen = ref(false)
const sheet = ref(false)
const openPy = reactive(new Set())
const openVi = reactive(new Set())
const selectedId = ref(null)
const audio = reactive({}) // turn id -> bản ghi giọng người học (chỉ trong phiên này)

// mặc định panel theo câu mới nhất của người học; chưa nói gì thì để trống
const selected = computed(() => {
  const ts = props.convo.turns
  return ts.find((t) => t.id === selectedId.value) || [...ts].reverse().find((t) => t.role === 'user') || null
})
const lastHasErrors = computed(() => {
  const u = [...props.convo.turns].reverse().find((t) => t.role === 'user')
  return !!(u && hasFix(u))
})

function flip(set, id) { set.has(id) ? set.delete(id) : set.add(id) }
function tone(t) { return t.score >= 80 ? 'jade' : t.score >= 60 ? 'gold' : 'seal' }
function hasFix(t) { return t.eval && t.eval.corrected && (t.eval.errors?.length || t.eval.is_correct === false) }
function select(t) {
  selectedId.value = t.id
  if (window.matchMedia('(max-width: 1079px)').matches) sheet.value = true
}
function parts(t) {
  // từ mới luôn là chữ Hán nên ghép thẳng vào regex được
  const ws = (t.notes || []).map((n) => n.hanzi).filter((w) => /^[㐀-鿿]+$/.test(w || '')).sort((a, b) => b.length - a.length)
  if (!ws.length) return [{ s: t.hanzi }]
  const re = new RegExp(`(${ws.join('|')})`)
  return t.hanzi.split(re).filter(Boolean).map((s) => ({ s, nw: ws.includes(s) }))
}

function scroll() {
  nextTick(() => { if (list.value) list.value.scrollTo({ top: list.value.scrollHeight, behavior: 'smooth' }) })
}

async function send({ text, mode, audioUrl }) {
  if (!text || sending.value) return
  sending.value = true
  pendingText.value = text
  err.value = ''
  scroll()
  try {
    const c = await api.post(`/api/convos/${props.convo.id}/message`, { text, input_mode: mode })
    const mine = [...c.turns].reverse().find((x) => x.role === 'user')
    if (mine && audioUrl) audio[mine.id] = audioUrl
    selectedId.value = null
    composer.value?.reset()
    emit('update', c)
    const last = c.turns[c.turns.length - 1]
    if (autoSpeak.value && last?.role === 'ai') speak(last.hanzi).catch(() => {})
  } catch (e) {
    err.value = e.message
  } finally {
    sending.value = false
    pendingText.value = ''
    scroll()
  }
}

watch(() => props.convo.turns.length, scroll)

// từ mới chưa có nghĩa (AI quên giải thích ở lượt cũ) -> xin bổ sung, mỗi hội thoại một lần
let explained = false
async function fillMeanings() {
  if (explained || !props.convo.turns.some((t) => t.notes?.some((n) => !n.meaning_vi))) return
  explained = true
  try { emit('update', await api.post(`/api/convos/${props.convo.id}/explain-notes`)) } catch { /* giữ nguyên */ }
}
onMounted(() => {
  fillMeanings()
  scroll()
  const first = props.convo.turns[props.convo.turns.length - 1]
  if (autoSpeak.value && props.convo.turns.length === 1 && first?.role === 'ai') speak(first.hanzi).catch(() => {})
  composer.value?.focus()
})
</script>

<style scoped>
.ws { display: grid; grid-template-columns: minmax(0, 1fr) 380px; gap: 20px; align-items: start; }
.conv { display: flex; flex-direction: column; gap: 12px; min-width: 0; height: calc(100dvh - 128px); }
.side { position: sticky; top: 100px; max-height: calc(100dvh - 128px); overflow-y: auto; padding: 2px 4px 12px; scrollbar-width: thin; }

/* đầu khu hội thoại: gọn, một dòng */
.ch { display: flex; align-items: center; gap: 14px; padding: 4px 6px; }
.ch-main { flex: 1; min-width: 0; }
.intro {
  font-size: 14px; color: var(--ink-soft); cursor: pointer; margin-top: 2px;
  display: -webkit-box; -webkit-line-clamp: 1; -webkit-box-orient: vertical; overflow: hidden;
}
.intro.open { -webkit-line-clamp: unset; }
.seg { display: inline-flex; gap: 2px; padding: 4px; border-radius: 14px; background: var(--paper-3); box-shadow: var(--shadow-in); flex: none; }
.seg button {
  display: inline-flex; align-items: center; gap: 4px; border: 0; background: none; cursor: pointer;
  padding: 5px 10px; border-radius: 10px; font: inherit; font-size: 12.5px; font-weight: 800; color: var(--ink-faint);
}
.seg button.on { background: var(--paper-2); color: var(--primary-strong); box-shadow: var(--shadow-sm); }

/* luồng hội thoại */
.msgs { flex: 1; min-height: 0; overflow-y: auto; display: flex; flex-direction: column; gap: 18px; padding: 12px 8px 16px; scrollbar-width: thin; }
.msg { display: flex; max-width: 78%; animation: pop .35s var(--ease-spring) both; }
@keyframes pop { from { opacity: 0; transform: translateY(8px) scale(.97); } }
.msg.ai { align-self: flex-start; gap: 10px; align-items: flex-start; }
.msg.me { align-self: flex-end; flex-direction: column; align-items: flex-end; }
.bubble {
  padding: 14px 18px; border-radius: 24px; background: var(--paper-2); box-shadow: var(--shadow-sm); cursor: pointer;
  outline: 2px solid transparent; outline-offset: 2px; transition: outline-color .2s, transform .2s var(--ease-spring);
}
.bubble:hover { transform: translateY(-1px); }
.ai .bubble { border-top-left-radius: 8px; }
.me .bubble { background: var(--primary-soft); border-top-right-radius: 8px; }
.msg.sel .bubble { outline-color: color-mix(in srgb, var(--primary) 60%, transparent); }
.hz { font-size: 24px; line-height: 1.5; letter-spacing: .02em; }
.vi { color: var(--ink-soft); margin-top: 2px; }
.nw { font-weight: 900; color: var(--gold); text-decoration: underline 2px var(--gold-fill); text-underline-offset: 5px; }
.tools { display: flex; align-items: center; gap: 12px; margin-top: 8px; }
.tl { border: 0; background: none; color: var(--primary-strong); cursor: pointer; padding: 0; font-size: 12.5px; font-weight: 800; }
.tl.gold { color: var(--gold); }
.tl:hover { text-decoration: underline; text-underline-offset: 3px; }
.meta { display: flex; align-items: center; gap: 4px; color: var(--ink-faint); margin-top: 2px; justify-content: flex-end; }

/* avatar AI: thanh âm động khi đang đọc */
.av {
  width: 34px; height: 34px; flex: none; border-radius: 12px; margin-top: 4px; background: var(--primary);
  display: inline-flex; align-items: center; justify-content: center; gap: 2px; box-shadow: 0 3px 0 0 var(--primary-edge), var(--hilite);
}
.av i { width: 3px; height: 8px; border-radius: 2px; background: #fff; opacity: .9; }
.talking .av i { animation: eq .7s ease-in-out infinite; }
.talking .av i:nth-child(2) { animation-delay: .15s; }
.talking .av i:nth-child(3) { animation-delay: .3s; }
@keyframes eq { 50% { height: 18px; } }

/* nhận xét ngắn ngay dưới câu người học */
.verdict {
  display: flex; align-items: center; gap: 8px; margin-top: 8px; padding: 6px 12px 6px 6px; border-radius: 16px;
  background: var(--paper-2); box-shadow: var(--shadow-sm); cursor: pointer; max-width: 100%;
}
.verdict .sc {
  width: 28px; height: 28px; flex: none; border-radius: 10px; display: inline-flex; align-items: center; justify-content: center;
  font-weight: 900; font-size: 12px; color: #fff; background: var(--c, var(--ink-faint));
}
.verdict.jade { --c: var(--jade-fill); }
.verdict.gold { --c: var(--gold-fill); }
.verdict.seal { --c: var(--seal-fill); }
.verdict .vt { font-size: 13px; font-weight: 800; color: var(--ink-soft); }
.verdict .lbl { font-size: 10.5px; font-weight: 900; text-transform: uppercase; letter-spacing: .05em; color: var(--jade); flex: none; }
.verdict .fx { font-size: 18px; color: var(--jade); min-width: 0; }
.verdict .more { font-size: 12px; font-weight: 800; color: var(--primary-strong); opacity: 0; transition: opacity .2s; flex: none; }
.verdict:hover .more { opacity: 1; }
.verdict.thinking { gap: 4px; padding-left: 12px; }
.verdict.thinking i { width: 6px; height: 6px; border-radius: 50%; background: var(--primary); animation: b 1s infinite; }
.verdict.thinking i:nth-child(2) { animation-delay: .15s; }
.verdict.thinking i:nth-child(3) { animation-delay: .3s; }
.verdict.thinking .vt { margin-left: 4px; }
@keyframes b { 50% { transform: translateY(-4px); opacity: .5; } }
.pending .bubble { opacity: .7; }

.foot { display: flex; align-items: center; gap: 12px; padding: 0 6px; }
.turns { display: inline-flex; gap: 4px; }
.turns i { width: 14px; height: 6px; border-radius: 4px; background: var(--paper-3); box-shadow: var(--shadow-in); }
.turns i.on { background: var(--primary); box-shadow: none; }
.foot .btn:last-child { margin-left: auto; }
.insight-btn { display: none; position: relative; margin-left: auto; }
.badge { position: absolute; top: 4px; right: 4px; width: 8px; height: 8px; border-radius: 50%; background: var(--seal-fill); }

/* màn hình hẹp: bảng trợ lý thành bottom sheet */
@media (max-width: 1079px) {
  .ws { grid-template-columns: 1fr; }
  .conv { height: auto; min-height: calc(100dvh - 140px); }
  .msgs { max-height: none; overflow: visible; }
  .side {
    position: fixed; inset: 0; z-index: 60; max-height: none; padding: 0; overflow: hidden;
    background: rgba(8, 14, 30, .45); backdrop-filter: blur(2px);
    opacity: 0; pointer-events: none; transition: opacity .2s;
  }
  .side.open { opacity: 1; pointer-events: auto; }
  .side :deep(.intel) {
    position: absolute; left: 0; right: 0; bottom: 0; max-height: 82dvh; overflow-y: auto;
    padding: 16px 14px calc(16px + env(safe-area-inset-bottom)); border-radius: 26px 26px 0 0; background: var(--paper);
    transform: translateY(100%); transition: transform .3s var(--ease-spring);
  }
  .side.open :deep(.intel) { transform: none; }
  .insight-btn { display: inline-flex; }
  .foot .btn:last-child { margin-left: 0; }
  .conv :deep(.vc) { position: sticky; bottom: 10px; z-index: 5; }
}
@media (max-width: 620px) {
  .msg { max-width: 92%; }
  .hz { font-size: 21px; }
  .ch { flex-direction: column; align-items: stretch; gap: 8px; }
  .seg { align-self: flex-start; }
  .turns { display: none; }
}
</style>

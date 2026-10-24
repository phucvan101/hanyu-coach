<template>
  <div class="qc card">
    <div class="row spread head">
      <span class="eyebrow">{{ p.label }}</span>
      <span class="tiny faint">{{ position }}</span>
    </div>

    <!-- đề bài -->
    <div class="prompt">
      <template v-if="q === 'hanzi_meaning' || q === 'hanzi_pinyin'">
        <TianZiGe :text="p.hanzi" :size="gridSize" />
        <p v-if="q === 'hanzi_pinyin'" class="muted small" style="margin-top: 10px">Nghĩa: {{ p.meaning }}</p>
      </template>
      <template v-else-if="q === 'meaning_hanzi' || q === 'meaning_write'">
        <p class="meaning">{{ p.meaning }}</p>
        <p v-if="q === 'meaning_write'" class="muted small">
          {{ p.length }} chữ ·
          <button v-if="!showHv" class="linkbtn" type="button" @click="showHv = true">gợi ý Hán Việt</button>
          <span v-else>Hán Việt: <b>{{ p.han_viet }}</b></span>
        </p>
      </template>
      <template v-else-if="q === 'listen_hanzi'">
        <div class="row" style="justify-content: center; gap: 10px">
          <button class="listen" type="button" aria-label="Nghe lại" @click="play()">
            <svg viewBox="0 0 24 24" width="34" height="34" aria-hidden="true"><path d="M4 9v6h4l5 4V5L8 9H4z" fill="currentColor"/><path d="M16 8.5a4.5 4.5 0 0 1 0 7M18.5 6a8 8 0 0 1 0 12" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>
          </button>
          <button class="btn ghost small" type="button" @click="play(true)">Nghe chậm</button>
        </div>
        <p v-if="ttsErr" class="tiny" style="color: var(--seal); margin-top: 8px">{{ ttsErr }}</p>
      </template>
      <template v-else-if="q === 'cloze'">
        <p class="cloze han">{{ p.sentence }}</p>
        <p class="muted small">{{ p.sentence_vi }}</p>
      </template>
    </div>

    <!-- trả lời -->
    <div v-if="p.options" class="opts" :class="{ hanopts: q !== 'hanzi_meaning' }">
      <button
        v-for="(o, i) in p.options" :key="o" type="button" class="opt"
        :class="optClass(o)" :disabled="done || busy" @click="submit(o)"
      >
        <span class="k">{{ i + 1 }}</span>
        <span :class="q !== 'hanzi_meaning' ? 'han oh' : ''">{{ o }}</span>
      </button>
    </div>
    <form v-else class="row typed" @submit.prevent="submit(text)">
      <HanziInput v-if="q === 'meaning_write'" ref="inp" v-model="text" big :disabled="done" placeholder="Gõ pinyin rồi chọn chữ Hán…" @submit="submit(text)" />
      <input v-else ref="inp" v-model="text" class="input pyin" :disabled="done" autocomplete="off" autocapitalize="off" spellcheck="false"
        placeholder="VD: ni3hao3 hoặc nǐhǎo" />
      <button v-if="!done" class="btn primary" type="submit" :disabled="busy || !text.trim()">Kiểm tra</button>
    </form>

    <!-- kết quả -->
    <Transition name="fade">
      <div v-if="done" class="result" :class="resTone">
        <Seal :text="sealText" :tone="resTone" :size="58" />
        <div class="reveal">
          <p class="verdict">{{ verdict }}</p>
          <p v-if="item.feedback" class="small">{{ item.feedback }}</p>
          <p v-if="!item.correct && item.user_answer && !p.options" class="small muted">Bạn trả lời: <span class="strike">{{ item.user_answer }}</span></p>
          <div class="row ans">
            <span class="han ah">{{ a.hanzi }}</span>
            <span class="py">{{ a.pinyin }}</span>
            <SpeakButton :text="a.hanzi" small />
          </div>
          <p class="small"><b>{{ a.meaning }}</b><span v-if="a.han_viet" class="faint"> · {{ a.han_viet }}</span></p>
          <p v-if="a.usage" class="small muted">{{ a.usage }}</p>
          <p v-if="a.example_zh" class="small ex"><span class="han">{{ a.example_zh }}</span> <span class="muted">— {{ a.example_vi }}</span></p>
        </div>
        <button ref="nextBtn" class="btn primary nx" type="button" @click="$emit('next')">Tiếp →</button>
      </div>
    </Transition>
    <p v-if="err" class="notice err small" style="margin-top: 12px">{{ err }}</p>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { api } from '../api'
import { speak } from '../composables/useTts'
import { playCorrect, playWrong } from '../composables/useSfx'
import HanziInput from './HanziInput.vue'
import Seal from './Seal.vue'
import SpeakButton from './SpeakButton.vue'
import TianZiGe from './TianZiGe.vue'

const props = defineProps({ item: { type: Object, required: true }, position: { type: String, default: '' } })
const emit = defineEmits(['answered', 'next'])

const p = computed(() => props.item.payload)
const q = computed(() => props.item.qtype)
const done = computed(() => props.item.answered)
const a = computed(() => props.item.answer || {})
const text = ref('')
const busy = ref(false)
const err = ref('')
const ttsErr = ref('')
const showHv = ref(false)
const inp = ref(null)
const nextBtn = ref(null)
const gridSize = computed(() => {
  const n = [...(p.value.hanzi || '')].length
  const w = Math.min(window.innerWidth - 80, 520)
  return Math.max(56, Math.min(110, Math.floor(w / Math.max(n, 1))))
})

const resTone = computed(() => (!props.item.correct ? 'seal' : props.item.tone_warning ? 'gold' : 'jade'))
const sealText = computed(() => (!props.item.correct ? '错' : props.item.tone_warning ? '调' : '对'))
const verdict = computed(() =>
  !props.item.correct ? 'Chưa đúng' : props.item.tone_warning ? 'Đúng âm — chú ý thanh điệu' : 'Chính xác',
)

function optClass(o) {
  if (!done.value) return ''
  if (o === a.value.value) return 'right'
  if (o === props.item.user_answer) return 'wrong'
  return 'dim'
}

async function play(slow = false) {
  ttsErr.value = ''
  try { await speak(p.value.audio_text, { slow }) } catch (e) { ttsErr.value = 'Không phát được âm thanh. Kiểm tra cài đặt giọng đọc.' }
}

async function submit(ans) {
  if (done.value || busy.value) return
  if (!String(ans || '').trim()) return
  busy.value = true
  err.value = ''
  try {
    const res = await api.post(`/api/quiz-items/${props.item.id}/answer`, { answer: ans })
    if (res.correct) playCorrect()
    else playWrong()
    emit('answered', res)
    await nextTick()
    nextBtn.value?.focus()
    // đợi tiếng báo đúng/sai dứt rồi mới đọc từ
    if (q.value !== 'listen_hanzi') setTimeout(() => speak(res.answer.hanzi).catch(() => {}), 450)
  } catch (e) {
    err.value = e.message
  } finally {
    busy.value = false
  }
}

function onKey(e) {
  if (done.value || !p.value.options) return
  if (e.target && ['INPUT', 'TEXTAREA'].includes(e.target.tagName)) return
  const n = Number(e.key)
  if (n >= 1 && n <= p.value.options.length) submit(p.value.options[n - 1])
}

function init() {
  text.value = ''
  showHv.value = false
  err.value = ''
  nextTick(() => {
    if (done.value) nextBtn.value?.focus()
    else inp.value?.focus?.()
  })
  if (q.value === 'listen_hanzi' && !done.value) setTimeout(() => play(), 250)
}

watch(() => props.item.id, init)
onMounted(() => { init(); window.addEventListener('keydown', onKey) })
onBeforeUnmount(() => window.removeEventListener('keydown', onKey))
</script>

<style scoped>
.qc { padding: 28px; }
.head { margin-bottom: 20px; }
.prompt { text-align: center; padding: 8px 0 24px; }
.meaning { font-size: 28px; font-weight: 900; margin-bottom: 6px; letter-spacing: -.01em; }
.cloze { font-size: 32px; letter-spacing: .04em; margin-bottom: 6px; }
.listen {
  width: 92px; height: 92px; border-radius: 30px; border: 0; background: var(--primary);
  color: #fff; cursor: pointer; display: inline-flex; align-items: center; justify-content: center;
  box-shadow: 0 6px 0 0 var(--primary-edge), 0 16px 28px -10px color-mix(in srgb, var(--primary) 70%, transparent), inset 0 3px 0 rgba(255, 255, 255, .35);
  transition: transform .2s var(--ease-spring), box-shadow .15s;
}
.listen:hover { transform: translateY(-3px) rotate(-3deg); }
.listen:active { transform: translateY(4px); box-shadow: 0 1px 0 0 var(--primary-edge), inset 0 3px 0 rgba(255, 255, 255, .35); }
.linkbtn { border: 0; background: none; color: var(--primary-strong); cursor: pointer; padding: 0; text-decoration: underline; font-weight: 800; text-underline-offset: 3px; }
.opts { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
@media (max-width: 520px) { .opts { grid-template-columns: 1fr; } }
.opt {
  --edge: var(--line);
  display: flex; align-items: center; gap: 12px; text-align: left; padding: 14px 16px; border-radius: 20px;
  border: 2px solid transparent; background: var(--paper-2); cursor: pointer; min-height: 62px; font-size: 15.5px; font-weight: 700;
  box-shadow: 0 5px 0 0 var(--edge), 0 10px 18px -10px rgba(var(--clay-tint), .4), var(--hilite);
  transition: transform .2s var(--ease-spring), box-shadow .15s, border-color .15s, background .15s;
}
.opt:hover:not(:disabled) { border-color: var(--primary); transform: translateY(-2px); }
.opt:active:not(:disabled) { transform: translateY(4px); box-shadow: 0 1px 0 0 var(--edge); }
.opt .k {
  font-size: 11px; color: var(--ink-faint); border: 0; border-radius: 8px; padding: 2px 7px; flex: none; font-weight: 900;
  background: var(--paper-3); box-shadow: var(--shadow-in);
}
.oh { font-size: 28px; line-height: 1.1; }
.opt.right { --edge: var(--jade-edge); border-color: var(--jade-fill); background: var(--jade-soft); animation: bounce .45s var(--ease-spring); }
.opt.wrong { --edge: color-mix(in srgb, var(--seal-fill) 70%, #000); border-color: var(--seal-fill); background: var(--seal-soft); animation: shake .4s ease; }
.opt.dim { opacity: .5; }
.opt:disabled { cursor: default; }
@keyframes bounce { 40% { transform: translateY(-5px) scale(1.02); } }
@keyframes shake { 20%, 60% { transform: translateX(-5px); } 40%, 80% { transform: translateX(5px); } }
.typed { align-items: flex-start; }
.pyin { font-size: 20px; padding: 14px 18px; border-radius: 18px; }
.result {
  display: grid; grid-template-columns: auto 1fr auto; gap: 18px; align-items: start; margin-top: 22px;
  padding: 20px; border-radius: 22px; background: var(--paper-3); border: 0; box-shadow: var(--shadow-in);
  animation: rise .35s var(--ease-spring) both;
}
@keyframes rise { from { opacity: 0; transform: translateY(10px); } }
.result.jade { background: var(--jade-soft); }
.result.seal { background: var(--seal-soft); }
.result.gold { background: var(--gold-soft); }
.verdict { font-weight: 900; margin-bottom: 4px; font-size: 16px; }
.reveal { display: flex; flex-direction: column; gap: 4px; min-width: 0; }
.ans { gap: 10px; margin: 4px 0; }
.ah { font-size: 30px; }
.ex { margin-top: 4px; }
.ex .han { font-size: 17px; }
.nx { align-self: end; }
@media (max-width: 560px) {
  .result { grid-template-columns: auto 1fr; }
  .nx { grid-column: 1 / -1; width: 100%; }
}
</style>

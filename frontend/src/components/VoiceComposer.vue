<template>
  <div class="vc" :class="state">
    <button
      type="button" class="mic" :class="{ rec: state === 'rec' }" :disabled="disabled || state === 'stt'"
      :style="{ '--lv': level }"
      :aria-label="state === 'rec' ? 'Dừng và nhận diện' : 'Bấm để nói'"
      :title="state === 'rec' ? 'Bấm để dừng (Esc để huỷ)' : 'Bấm để nói tiếng Trung (Ctrl+M)'"
      @click="toggleMic"
    >
      <svg v-if="state === 'rec'" viewBox="0 0 24 24" width="24" height="24" aria-hidden="true"><rect x="6.5" y="6.5" width="11" height="11" rx="3" fill="currentColor" /></svg>
      <svg v-else viewBox="0 0 24 24" width="26" height="26" aria-hidden="true">
        <rect x="9" y="3" width="6" height="11" rx="3" fill="currentColor" />
        <path d="M5.5 11a6.5 6.5 0 0 0 13 0M12 17.5V21" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" />
      </svg>
    </button>

    <div class="stage">
      <!-- đang nghe -->
      <div v-if="state === 'rec'" class="live" aria-live="polite">
        <div class="wave" :class="{ idle: !hasMeter }" aria-hidden="true">
          <i v-for="(v, i) in bars" :key="i" :style="{ '--h': v }"></i>
        </div>
        <div class="live-meta">
          <span class="dot"></span><b>Đang nghe</b><span v-if="hasMeter" class="faint"> · {{ seconds }}s</span>
          <button type="button" class="tl" @click="cancelRec">Huỷ</button>
        </div>
      </div>

      <!-- đang nhận diện -->
      <div v-else-if="state === 'stt'" class="live" aria-live="polite">
        <div class="wave thinking" aria-hidden="true"><i v-for="i in 32" :key="i" :style="{ '--d': i * 0.04 + 's' }"></i></div>
        <div class="live-meta"><b>Đang nhận diện giọng nói…</b></div>
      </div>

      <!-- gõ / xem lại câu vừa nói -->
      <template v-else>
        <div v-if="state === 'review'" class="review-bar">
          <span class="tag">Nghe được</span>
          <span class="small muted">sửa nếu chưa đúng rồi gửi</span>
          <button v-if="audioUrl" type="button" class="tl" @click="playMine">▶ Nghe lại giọng bạn</button>
          <button type="button" class="tl" @click="toggleMic">Nói lại</button>
        </div>
        <HanziInput ref="inp" v-model="text" :ime-default="true" :disabled="disabled"
          :placeholder="placeholder" @submit="send" @update:model-value="onType" />
      </template>
    </div>

    <button v-if="state !== 'rec' && state !== 'stt'" class="send" type="button" :disabled="disabled || !text.trim()" aria-label="Gửi" @click="send">
      <svg viewBox="0 0 24 24" width="22" height="22" aria-hidden="true"><path d="M4 12l15-7-5 15-2.5-6.5L4 12z" fill="currentColor" /></svg>
    </button>
  </div>
  <div v-if="err" class="notice err small vc-err">
    <span>{{ err }}</span>
    <button v-if="sttFailed && canBrowser" type="button" class="btn small" @click="useBrowser">Nói lại bằng nhận diện của trình duyệt</button>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { api } from '../api'
import { browserRecognize, useRecorder } from '../composables/useRecorder'
import { settings } from '../composables/useSettings'
import HanziInput from './HanziInput.vue'

defineProps({ disabled: Boolean, placeholder: { type: String, default: 'Bấm micro để nói, hoặc gõ chữ Hán / pinyin…' } })
const emit = defineEmits(['send'])

const { recording, seconds, levels, start, stop, cancel } = useRecorder()
const state = ref('idle') // idle | rec | stt | review
const text = ref('')
const voiceText = ref('')
const audioUrl = ref('')
const hasMeter = ref(true)
const err = ref('')
const sttFailed = ref(false)
const canBrowser = !!(window.SpeechRecognition || window.webkitSpeechRecognition)
const inp = ref(null)

const bars = computed(() => (hasMeter.value ? levels.value : new Array(32).fill(0.35)))
const level = computed(() => (recording.value ? Math.min(1, Math.max(...levels.value) * 1.2) : 0))

function setAudio(blob) {
  if (audioUrl.value) URL.revokeObjectURL(audioUrl.value)
  audioUrl.value = blob ? URL.createObjectURL(blob) : ''
}

async function toggleMic() {
  err.value = ''
  if (state.value === 'rec') return finishRec()
  sttFailed.value = false
  // không có Gemini: nhận dạng bằng trình duyệt
  if (!settings.has_gemini_api_key) return useBrowser()
  hasMeter.value = true
  try {
    await start()
    state.value = 'rec'
  } catch (e) {
    err.value = 'Không mở được micro: ' + e.message
  }
}

// dự phòng cuối khi Gemini lỗi: Web Speech API của Chrome/Edge (không có dữ liệu sóng âm)
async function useBrowser() {
  err.value = ''
  sttFailed.value = false
  hasMeter.value = false
  state.value = 'rec'
  try {
    gotText(await browserRecognize(), null)
  } catch (e) {
    state.value = text.value ? 'review' : 'idle'
    err.value = 'Trình duyệt không nhận dạng được: ' + e.message
  }
}

async function finishRec() {
  if (!hasMeter.value) return // nhận dạng trình duyệt tự dừng khi bạn ngừng nói
  state.value = 'stt'
  try {
    const wav = await stop()
    if (!wav) throw new Error('Không đọc được đoạn ghi âm')
    const fd = new FormData()
    fd.append('file', wav, 'speech.wav')
    const r = await api.upload('/api/stt', fd)
    if (!r.text) throw new Error('Không nghe rõ, hãy nói lại gần micro hơn.')
    gotText(r.text, wav)
  } catch (e) {
    state.value = text.value ? 'review' : 'idle'
    err.value = e.message
    sttFailed.value = true
  }
}

function gotText(t, blob) {
  text.value = t
  voiceText.value = t
  setAudio(blob)
  state.value = 'review'
  nextTick(() => inp.value?.focus())
}

function cancelRec() {
  cancel()
  state.value = text.value ? 'review' : 'idle'
}

function onType() {
  if (state.value === 'review' && !text.value) state.value = 'idle'
}

function playMine() {
  if (audioUrl.value) new Audio(audioUrl.value).play().catch(() => {})
}

function send() {
  const t = text.value.trim()
  if (!t) return
  const voice = voiceText.value && t === voiceText.value
  const mode = voice ? 'voice' : /[㐀-鿿]/.test(t) ? 'hanzi' : 'pinyin'
  // giữ bản ghi âm để người học nghe lại cạnh câu mẫu trong panel nhận xét
  emit('send', { text: t, mode, audioUrl: voice ? audioUrl.value : '' })
}

// ChatPanel gọi sau khi gửi thành công
function reset() {
  text.value = ''
  voiceText.value = ''
  audioUrl.value = '' // URL đã giao cho ChatPanel giữ, không revoke ở đây
  state.value = 'idle'
  nextTick(() => inp.value?.focus())
}
function focus() { inp.value?.focus() }
defineExpose({ reset, focus })

function onKey(e) {
  if (e.key === 'Escape' && state.value === 'rec') { e.preventDefault(); cancelRec() }
  if (e.ctrlKey && (e.key === 'm' || e.key === 'M')) { e.preventDefault(); toggleMic() }
}
onMounted(() => window.addEventListener('keydown', onKey))
onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKey)
  if (recording.value) cancel()
})
</script>

<style scoped>
.vc {
  display: flex; align-items: center; gap: 12px; padding: 10px 12px 10px 10px;
  background: color-mix(in srgb, var(--paper-2) 92%, transparent); backdrop-filter: blur(10px);
  border-radius: 28px; box-shadow: var(--shadow);
}
.mic {
  --lv: 0;
  position: relative; width: 60px; height: 60px; flex: none; border: 0; border-radius: 50%; cursor: pointer;
  color: #fff; background: var(--primary);
  display: inline-flex; align-items: center; justify-content: center;
  box-shadow: 0 5px 0 0 var(--primary-edge), 0 12px 24px -10px color-mix(in srgb, var(--primary) 80%, transparent), var(--hilite);
  transition: transform .2s var(--ease-spring), background .2s;
}
.mic::after {
  content: ''; position: absolute; inset: -6px; border-radius: 50%; pointer-events: none;
  border: 3px solid color-mix(in srgb, var(--seal-fill) 55%, transparent);
  transform: scale(calc(1 + var(--lv) * .35)); opacity: 0; transition: transform .08s linear, opacity .2s;
}
.mic:hover:not(:disabled) { transform: translateY(-2px) scale(1.03); }
.mic:active:not(:disabled) { transform: translateY(3px); }
.mic:disabled { opacity: .55; cursor: default; }
.mic.rec { background: var(--seal-fill); box-shadow: 0 5px 0 0 color-mix(in srgb, var(--seal-fill) 65%, #000), var(--hilite); }
.mic.rec::after { opacity: 1; }

.stage { flex: 1; min-width: 0; }
.live { display: flex; flex-direction: column; gap: 6px; padding: 2px 4px; }
.wave { display: flex; align-items: center; gap: 3px; height: 34px; }
.wave i {
  --h: 0; flex: 1; min-width: 2px; border-radius: 3px; background: var(--seal-fill);
  height: calc(4px + var(--h) * 30px); transition: height .06s linear;
}
.wave.idle i { animation: idle 1.2s ease-in-out infinite; }
.wave.idle i:nth-child(odd) { animation-delay: .3s; }
@keyframes idle { 50% { height: 18px; } }
.wave.thinking i { background: var(--primary); height: 6px; animation: think 1s ease-in-out infinite; animation-delay: var(--d); opacity: .8; }
@keyframes think { 40% { height: 22px; opacity: 1; } }
.live-meta { display: flex; align-items: center; gap: 6px; font-size: 13px; }
.dot { width: 8px; height: 8px; border-radius: 50%; background: var(--seal-fill); animation: blink 1s infinite; }
@keyframes blink { 50% { opacity: .2; } }
.live-meta .tl { margin-left: auto; }
.review-bar { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; margin: 0 4px 6px; }
.tag { font-size: 10.5px; font-weight: 900; text-transform: uppercase; letter-spacing: .05em; color: var(--jade); background: var(--jade-soft); padding: 2px 8px; border-radius: 8px; }
.tl { border: 0; background: none; color: var(--primary-strong); cursor: pointer; padding: 0; font-size: 12.5px; font-weight: 800; }
.tl:hover { text-decoration: underline; text-underline-offset: 3px; }
.stage :deep(.cands) { top: auto; bottom: calc(100% + 10px); }
.send {
  width: 48px; height: 48px; flex: none; border: 0; border-radius: 16px; cursor: pointer; color: var(--primary-ink);
  background: var(--primary); display: inline-flex; align-items: center; justify-content: center;
  box-shadow: 0 4px 0 0 var(--primary-edge), var(--hilite); transition: transform .2s var(--ease-spring), opacity .2s;
}
.send:disabled { opacity: .4; cursor: default; box-shadow: none; }
.send:hover:not(:disabled) { transform: translateY(-2px); }
.vc-err { margin-top: 8px; display: flex; flex-wrap: wrap; align-items: center; gap: 10px; justify-content: space-between; }
@media (max-width: 560px) {
  .vc { gap: 8px; padding: 8px; border-radius: 24px; }
  .mic { width: 52px; height: 52px; }
  .send { width: 44px; height: 44px; }
}
</style>

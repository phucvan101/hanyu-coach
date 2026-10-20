<template>
  <button
    type="button" class="mic" :class="{ rec: recording, busy }" :disabled="disabled || busy"
    :aria-label="recording ? 'Dừng ghi âm' : 'Nói (ghi âm)'" :title="recording ? 'Bấm để dừng' : 'Bấm để nói tiếng Trung'"
    @click="toggle"
  >
    <svg v-if="!recording" viewBox="0 0 24 24" width="20" height="20" aria-hidden="true">
      <rect x="9" y="3" width="6" height="11" rx="3" fill="currentColor" />
      <path d="M5.5 11a6.5 6.5 0 0 0 13 0M12 17.5V21" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" />
    </svg>
    <span v-else class="sec">{{ seconds }}s</span>
  </button>
</template>

<script setup>
import { ref } from 'vue'
import { api } from '../api'
import { browserRecognize, useRecorder } from '../composables/useRecorder'
import { settings } from '../composables/useSettings'

defineProps({ disabled: Boolean })
const emit = defineEmits(['text', 'error'])
const { recording, seconds, start, stop } = useRecorder()
const busy = ref(false)

async function toggle() {
  if (!settings.has_gemini_api_key) {
    // không có Gemini: dùng nhận dạng của trình duyệt
    busy.value = true
    try { emit('text', await browserRecognize()) } catch (e) { emit('error', 'Không nhận dạng được: ' + e.message) }
    busy.value = false
    return
  }
  if (!recording.value) {
    try { await start() } catch (e) { emit('error', 'Không mở được micro: ' + e.message) }
    return
  }
  busy.value = true
  try {
    const wav = await stop()
    if (!wav) throw new Error('Không đọc được đoạn ghi âm')
    const fd = new FormData()
    fd.append('file', wav, 'speech.wav')
    const r = await api.upload('/api/stt', fd)
    if (!r.text) emit('error', 'Không nghe rõ, hãy nói lại gần micro hơn.')
    else emit('text', r.text)
  } catch (e) {
    emit('error', e.message)
  } finally {
    busy.value = false
  }
}
</script>

<style scoped>
.mic {
  width: 48px; height: 48px; border-radius: 16px; border: 0; background: var(--paper-2);
  color: var(--primary); cursor: pointer; display: inline-flex; align-items: center; justify-content: center; flex: none;
  box-shadow: 0 4px 0 0 var(--line), 0 8px 16px -8px rgba(var(--clay-tint), .35), var(--hilite);
  transition: transform .2s var(--ease-spring), box-shadow .18s;
}
.mic:hover { transform: translateY(-2px); }
.mic:active { transform: translateY(3px); box-shadow: 0 1px 0 0 var(--line); }
.mic.rec {
  background: var(--seal-fill); color: #fff;
  box-shadow: 0 4px 0 0 color-mix(in srgb, var(--seal-fill) 70%, #000), var(--hilite);
  animation: pulse 1.2s ease-in-out infinite;
}
.mic.busy { opacity: .6; }
.sec { font-size: 12px; font-weight: 900; }
@keyframes pulse { 50% { box-shadow: 0 4px 0 0 color-mix(in srgb, var(--seal-fill) 70%, #000), 0 0 0 8px var(--seal-soft); } }
</style>

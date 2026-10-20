<template>
  <Transition name="pop">
    <button v-if="reaction.src" :key="reaction.key" type="button" class="rc" :class="reaction.tone"
      aria-label="Đóng clip" title="Bấm để đóng" @click="hideReaction">
      <video ref="vid" :src="reaction.src" autoplay playsinline @ended="hideReaction" @error="hideReaction" />
      <span class="cap">{{ reaction.caption }}</span>
    </button>
  </Transition>
</template>

<script setup>
import { nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { reaction, hideReaction } from '../composables/useReactions'

const MAX_MS = 6000 // clip dài quá thì tự tắt, không che bài học lâu
const vid = ref(null)
let timer = 0

watch(() => reaction.key, async () => {
  clearTimeout(timer)
  timer = setTimeout(hideReaction, MAX_MS)
  await nextTick()
  // trình duyệt chặn tự phát có tiếng thì phát không tiếng
  vid.value?.play().catch(() => {
    if (!vid.value) return
    vid.value.muted = true
    vid.value.play().catch(hideReaction)
  })
})
onBeforeUnmount(() => clearTimeout(timer))
</script>

<style scoped>
.rc {
  position: fixed; right: 20px; bottom: 20px; z-index: 80; width: 200px; padding: 8px 8px 10px; border: 0; border-radius: 22px;
  display: flex; flex-direction: column; align-items: center; gap: 6px; cursor: pointer; font: inherit;
  background: var(--paper-2); box-shadow: var(--shadow);
}
.rc video { width: 100%; max-height: 260px; object-fit: contain; border-radius: 14px; display: block; }
.cap { font-weight: 900; font-size: 14px; text-align: center; line-height: 1.25; }
.rc.good .cap { color: var(--jade); }
.rc.bad .cap { color: var(--seal); }
.pop-enter-active { transition: transform .35s var(--ease-spring), opacity .2s; }
.pop-leave-active { transition: transform .2s ease, opacity .2s; }
.pop-enter-from, .pop-leave-to { opacity: 0; transform: translateY(24px) scale(.85); }
@media (max-width: 760px) {
  .rc { right: 12px; bottom: 96px; width: 150px; }
}
@media (prefers-reduced-motion: reduce) {
  .pop-enter-active, .pop-leave-active { transition: opacity .2s; }
  .pop-enter-from, .pop-leave-to { transform: none; }
}
</style>

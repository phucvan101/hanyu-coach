<template>
  <button class="spk" type="button" :class="{ on: speaking === text && speakingSlow === slow, sm: small, slow }"
    :title="(slow ? 'Nghe chậm: ' : 'Nghe: ') + text" :aria-label="(slow ? 'Nghe chậm ' : 'Nghe phát âm ') + text" @click.stop="play">
    <!-- đọc chậm: con rùa -->
    <svg v-if="slow" viewBox="0 0 24 24" width="20" height="20" aria-hidden="true">
      <g transform="translate(0 -1)" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
        <path d="M3 15.2c0-4.4 3.4-7.7 7.6-7.7s7.6 3.3 7.6 7.7z" fill="currentColor" fill-opacity=".22" />
        <path d="M7.4 15.2c.3-2.6 1.6-4.6 3.2-4.6s2.9 2 3.2 4.6" />
        <path d="M18 13.6l1.4-.9" />
        <circle cx="20.6" cy="12" r="1.7" fill="currentColor" />
        <path d="M6 15.2v2.8M15.2 15.2v2.8M3 15.2l-1.3 1" />
      </g>
    </svg>
    <svg v-else viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
      <path d="M4 9v6h4l5 4V5L8 9H4z" fill="currentColor" />
      <path d="M16 8.5a4.5 4.5 0 0 1 0 7M18.5 6a8 8 0 0 1 0 12" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" />
    </svg>
  </button>
</template>

<script setup>
import { speak, speaking, speakingSlow } from '../composables/useTts'
const props = defineProps({ text: { type: String, required: true }, small: Boolean, slow: Boolean })
const emit = defineEmits(['error'])
async function play() {
  try { await speak(props.text, { slow: props.slow }) } catch (e) { emit('error', e) }
}
</script>

<style scoped>
.spk {
  display: inline-flex; align-items: center; justify-content: center; width: 36px; height: 36px;
  border-radius: 12px; border: 0; background: var(--paper-2); color: var(--primary); cursor: pointer; flex: none;
  box-shadow: 0 3px 0 0 var(--line), 0 6px 12px -6px rgba(var(--clay-tint), .35), var(--hilite);
  transition: transform .2s var(--ease-spring), box-shadow .15s, background .15s;
}
.spk.sm { width: 30px; height: 30px; border-radius: 10px; }
.spk:hover { transform: translateY(-1px); }
.spk:active { transform: translateY(2px); box-shadow: 0 1px 0 0 var(--line); }
.spk.on { background: var(--primary); color: #fff; box-shadow: 0 3px 0 0 var(--primary-edge), var(--hilite); }
</style>

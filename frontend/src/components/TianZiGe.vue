<template>
  <div class="tzg" :style="{ '--s': size + 'px' }" :aria-label="text">
    <span v-for="(c, i) in chars" :key="i" class="cell">
      <svg class="guides" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
        <line x1="50" y1="0" x2="50" y2="100" />
        <line x1="0" y1="50" x2="100" y2="50" />
        <line v-if="mi" x1="0" y1="0" x2="100" y2="100" />
        <line v-if="mi" x1="100" y1="0" x2="0" y2="100" />
      </svg>
      <span class="ch han">{{ c }}</span>
    </span>
  </div>
</template>

<script setup>
import { computed } from 'vue'
const props = defineProps({ text: { type: String, default: '' }, size: { type: Number, default: 96 }, mi: { type: Boolean, default: false } })
const chars = computed(() => [...(props.text || '')])
</script>

<style scoped>
.tzg {
  display: inline-flex; flex-wrap: wrap; justify-content: center; gap: 8px;
}
.cell {
  position: relative; width: var(--s); height: var(--s);
  border: 2.5px solid var(--grid); border-radius: calc(var(--s) * 0.18);
  display: inline-flex; align-items: center; justify-content: center; overflow: hidden;
  background: var(--paper-2);
  box-shadow: var(--shadow-sm);
  transition: transform .25s var(--ease-spring);
}
.cell:nth-child(odd) { transform: rotate(-1.5deg); }
.cell:nth-child(even) { transform: rotate(1.5deg); }
.cell:hover { transform: rotate(0) scale(1.04); }
.guides { position: absolute; inset: 0; width: 100%; height: 100%; }
.guides line { stroke: var(--grid); stroke-width: 1.5; stroke-dasharray: 5 5; vector-effect: non-scaling-stroke; opacity: .75; }
.ch { position: relative; font-size: calc(var(--s) * 0.72); line-height: 1; color: var(--ink); transform: translateY(2%); }
</style>

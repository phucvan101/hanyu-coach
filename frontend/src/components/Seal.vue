<template>
  <span class="seal" :class="[tone, { animate }]" :style="{ '--z': size + 'px' }" role="img" :aria-label="label || text">
    <span class="inner han">{{ text }}</span>
  </span>
</template>

<script setup>
defineProps({
  text: { type: [String, Number], default: '对' },
  tone: { type: String, default: 'seal' }, // seal | jade | gold
  size: { type: Number, default: 56 },
  animate: { type: Boolean, default: true },
  label: { type: String, default: '' },
})
</script>

<style scoped>
.seal {
  --c: var(--seal-fill);
  display: inline-flex; align-items: center; justify-content: center;
  width: var(--z); height: var(--z); border: 0; border-radius: calc(var(--z) * 0.3);
  transform: rotate(-8deg); color: #fff; flex: none; background: var(--c);
  box-shadow:
    0 4px 0 0 color-mix(in srgb, var(--c) 68%, #000),
    0 10px 18px -8px color-mix(in srgb, var(--c) 70%, transparent),
    inset 0 3px 0 rgba(255, 255, 255, .38),
    inset 0 0 0 3px color-mix(in srgb, #fff 22%, transparent);
}
.seal.jade { --c: var(--jade-fill); }
.seal.gold { --c: var(--gold-fill); }
.inner { font-size: calc(var(--z) * 0.5); line-height: 1; font-weight: 700; font-family: var(--font-han); text-shadow: 0 1px 0 rgba(0, 0, 0, .15); }
.seal.animate { animation: stamp .5s var(--ease-spring) both; }
@keyframes stamp {
  0% { transform: rotate(-20deg) scale(1.8); opacity: 0; }
  100% { transform: rotate(-8deg) scale(1); opacity: 1; }
}
</style>

<template>
  <div class="sb">
    <div v-for="(v, k) in skills" :key="k" class="r">
      <span class="n small">{{ labels[k] || k }}</span>
      <div class="bar"><span :style="{ width: v + '%', background: v >= 70 ? 'var(--jade-fill)' : v >= 50 ? 'var(--gold-fill)' : 'var(--seal-fill)' }"></span></div>
      <span class="v small">{{ v }}%</span>
    </div>
    <p v-if="!Object.keys(skills || {}).length" class="muted small">Chưa có dữ liệu kỹ năng.</p>
  </div>
</template>

<script setup>
defineProps({ skills: { type: Object, default: () => ({}) }, labels: { type: Object, default: () => ({}) } })
</script>

<style scoped>
.sb { display: flex; flex-direction: column; gap: 12px; }
.r { display: grid; grid-template-columns: 120px 1fr 48px; align-items: center; gap: 12px; }
.n { color: var(--ink-soft); font-weight: 700; }
.v { text-align: right; font-weight: 900; font-variant-numeric: tabular-nums; }
.bar { height: 12px; }
</style>

<template>
  <div class="sc">
    <div class="legend">
      <button v-for="k in keys" :key="k" type="button" class="lg" :class="{ off: hidden.has(k) }" @click="toggle(k)">
        <i :style="{ background: colors[k] }"></i>{{ labels[k] || k }}
      </button>
    </div>
    <div class="canvas-wrap"><canvas ref="cv" role="img" aria-label="Biểu đồ điểm kỹ năng theo buổi học"></canvas></div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { Chart, LineController, LineElement, PointElement, LinearScale, CategoryScale, Tooltip, Filler } from 'chart.js'
import { fmtDay } from '../api'
import { isDark } from '../composables/useTheme'

Chart.register(LineController, LineElement, PointElement, LinearScale, CategoryScale, Tooltip, Filler)

const props = defineProps({ history: { type: Array, default: () => [] }, labels: { type: Object, default: () => ({}) } })
const cv = ref(null)
let chart = null
const hidden = reactive(new Set(['pinyin', 'listening', 'writing', 'tones']))

// bảng màu cố định cho từng kỹ năng
const colors = {
  recognition: '#3b82f6', pinyin: '#06b6d4', tones: '#f59e0b', listening: '#a855f7',
  writing: '#22c55e', grammar: '#f43f5e', communication: '#fb923c', vocab_usage: '#14b8a6',
}
const keys = computed(() => {
  const s = new Set()
  props.history.forEach((h) => Object.keys(h.skill_scores || {}).forEach((k) => s.add(k)))
  return Object.keys(colors).filter((k) => s.has(k))
})

function toggle(k) {
  hidden.has(k) ? hidden.delete(k) : hidden.add(k)
  render()
}

function css(v) { return getComputedStyle(document.documentElement).getPropertyValue(v).trim() }

function render() {
  if (!cv.value) return
  const hist = props.history.slice(-30)
  const data = {
    labels: hist.map((h) => fmtDay(h.started_at)),
    datasets: keys.value.filter((k) => !hidden.has(k)).map((k) => ({
      label: props.labels[k] || k,
      data: hist.map((h) => (h.skill_scores || {})[k] ?? null),
      borderColor: colors[k], backgroundColor: colors[k], spanGaps: true,
      tension: 0.4, pointRadius: 4, pointHoverRadius: 6, borderWidth: 3, borderCapStyle: 'round',
    })),
  }
  const grid = css('--line'), tick = css('--ink-faint')
  if (chart) chart.destroy()
  chart = new Chart(cv.value, {
    type: 'line',
    data,
    options: {
      responsive: true, maintainAspectRatio: false, animation: false,
      interaction: { mode: 'index', intersect: false },
      scales: {
        y: { min: 0, max: 100, ticks: { stepSize: 25, color: tick, callback: (v) => v + '%' }, grid: { color: grid } },
        x: { ticks: { color: tick, maxRotation: 0, autoSkip: true, maxTicksLimit: 8 }, grid: { display: false } },
      },
      plugins: { legend: { display: false }, tooltip: { callbacks: { label: (c) => ` ${c.dataset.label}: ${c.parsed.y}%` } } },
    },
  })
}

onMounted(render)
watch(() => props.history, render, { deep: true })
watch(isDark, () => requestAnimationFrame(render))
onBeforeUnmount(() => chart && chart.destroy())
</script>

<style scoped>
.legend { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 12px; }
.lg {
  display: inline-flex; align-items: center; gap: 6px; border: 0; background: var(--paper-2);
  border-radius: 999px; padding: 5px 12px; font-size: 12.5px; font-weight: 800; cursor: pointer;
  box-shadow: var(--shadow-sm); transition: transform .2s var(--ease-spring), opacity .15s;
}
.lg:hover { transform: translateY(-1px); }
.lg:active { transform: scale(.95); }
.lg i { width: 10px; height: 10px; border-radius: 99px; display: inline-block; }
.lg.off { opacity: .45; box-shadow: var(--shadow-in); background: var(--paper-3); }
.canvas-wrap { position: relative; height: 210px; }
</style>

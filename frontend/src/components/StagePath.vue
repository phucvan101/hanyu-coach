<template>
  <ol class="path" :class="{ compact }">
    <li v-for="(s, i) in stages" :key="s.key" :class="state(s.key)">
      <span class="dot">
        <svg v-if="state(s.key) === 'done'" viewBox="0 0 16 16" width="12" height="12" aria-hidden="true"><path d="M3 8.5l3 3 7-7" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/></svg>
        <svg v-else-if="state(s.key) === 'locked'" viewBox="0 0 16 16" width="11" height="11" aria-hidden="true"><rect x="3.5" y="7" width="9" height="6.5" rx="1.5" fill="currentColor"/><path d="M5.5 7V5.5a2.5 2.5 0 0 1 5 0V7" fill="none" stroke="currentColor" stroke-width="1.6"/></svg>
        <span v-else>{{ i + 1 }}</span>
      </span>
      <span class="txt">
        <span class="name">{{ s.label }}</span>
        <span v-if="!compact" class="score tiny">{{ scoreText(s.key) }}</span>
      </span>
    </li>
  </ol>
</template>

<script setup>
const props = defineProps({ progress: { type: Object, required: true }, compact: Boolean, current: { type: String, default: '' } })
const stages = [
  { key: 'vocab', label: 'Từ vựng' },
  { key: 'controlled', label: 'Có kiểm soát' },
  { key: 'free', label: 'Tự do' },
]
function state(k) {
  const p = props.progress
  if (p[`${k}_passed`]) return 'done'
  if (!p.unlocked?.[k]) return 'locked'
  return k === props.current || !props.current ? 'open' : 'open'
}
function scoreText(k) {
  const v = props.progress[`${k}_best`]
  return v ? `cao nhất ${v}%` : state(k) === 'locked' ? 'chưa mở' : 'chưa làm'
}
</script>

<style scoped>
.path { list-style: none; margin: 0; padding: 0; display: flex; gap: 0; }
.path li { flex: 1; display: flex; align-items: center; gap: 10px; position: relative; padding-right: 12px; min-width: 0; }
.path li + li::before {
  content: ''; position: absolute; left: -12px; width: 12px; top: 50%; height: 4px; margin-top: -2px;
  background: var(--line); border-radius: 4px;
}
.path li.done + li::before { background: var(--jade-fill); }
.dot {
  width: 30px; height: 30px; border-radius: 11px; display: inline-flex; align-items: center; justify-content: center;
  border: 0; font-size: 13px; font-weight: 900; color: var(--ink-soft); flex: none; background: var(--paper-2);
  box-shadow: var(--shadow-sm);
}
.done .dot { background: var(--jade-fill); color: #fff; box-shadow: 0 3px 0 0 var(--jade-edge), var(--hilite); }
.open .dot { background: var(--primary); color: #fff; box-shadow: 0 3px 0 0 var(--primary-edge), var(--hilite), 0 0 0 4px var(--primary-soft); }
.locked .dot { color: var(--ink-faint); background: var(--paper-3); box-shadow: var(--shadow-in); }
.txt { display: flex; flex-direction: column; min-width: 0; }
.name { font-size: 13.5px; font-weight: 800; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.locked .name { color: var(--ink-faint); }
.score { color: var(--ink-faint); font-weight: 700; }
/* bản thu gọn trong thẻ bài: chỉ chấm trạng thái nối bằng thanh, tên bước đã có ở các nút bên dưới */
.compact li { flex: 0 0 auto; padding-right: 0; }
.compact li + li { padding-left: 34px; }
.compact li + li::before { left: 4px; width: 26px; }
.compact .txt { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; }
.compact .dot { width: 26px; height: 26px; font-size: 11.5px; border-radius: 9px; }
</style>

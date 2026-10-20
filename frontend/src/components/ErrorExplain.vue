<template>
  <ul v-if="items.length" class="why">
    <li v-for="(it, i) in items" :key="i">
      <p v-if="it.from" class="fx"><span class="han strike">{{ it.from }}</span> <span class="arrow">→</span> <span class="han ok">{{ it.to }}</span></p>
      <p class="small">{{ it.text }}</p>
    </li>
  </ul>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({ text: { type: String, default: '' } })

// "phần sai → phần sửa: giải thích", nhiều lỗi nối nhau (bản cũ nối bằng dấu cách, bản mới xuống dòng)
const CJK = '[\\u3400-\\u9fff，。？！、；：“”（）·…\\s]'
const SEG = new RegExp(`(${CJK}+?) → (.+?): `, 'g')

const items = computed(() => {
  const t = (props.text || '').trim()
  if (!t) return []
  const out = []
  for (const line of t.split('\n')) {
    const marks = [...line.matchAll(SEG)]
    if (!marks.length) { out.push({ text: line.trim() }); continue }
    if (marks[0].index > 0) out.push({ text: line.slice(0, marks[0].index).trim() })
    marks.forEach((m, i) => {
      const end = i + 1 < marks.length ? marks[i + 1].index : line.length
      out.push({ from: m[1].trim(), to: m[2].trim(), text: line.slice(m.index + m[0].length, end).trim() })
    })
  }
  return out.filter((x) => x.text || x.from)
})
</script>

<style scoped>
.why { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 8px; }
.why li { padding: 10px 14px; border-radius: 14px; background: var(--paper-3); display: flex; flex-direction: column; gap: 4px; }
.fx { font-size: 17px; line-height: 1.4; }
.arrow { color: var(--ink-faint); margin: 0 2px; }
.ok { color: var(--jade); }
.small { line-height: 1.6; }
</style>

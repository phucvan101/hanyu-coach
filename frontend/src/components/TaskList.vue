<template>
  <ol class="tasks">
    <li v-for="(t, i) in tasks" :key="t.id" class="task" :class="{ done: t.status === 'done' }">
      <span class="num" aria-hidden="true">
        <svg v-if="t.status === 'done'" viewBox="0 0 16 16" width="15" height="15"><path d="M3 8.5l3 3 7-7" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round"/></svg>
        <template v-else>{{ i + 1 }}</template>
      </span>
      <div class="body">
        <div class="row wrap" style="gap: 6px">
          <span class="chip">{{ t.kind_label }}</span>
          <span v-if="showSource && t.source_topic" class="tiny faint">từ buổi “{{ t.source_topic }}”</span>
        </div>
        <p class="tt">{{ t.title_vi }}</p>
        <p v-if="t.detail_vi" class="small muted">{{ t.detail_vi }}</p>
        <p v-if="t.status === 'done'" class="tiny faint">Đã xong<span v-if="t.score !== null && t.score !== undefined"> · {{ t.score }} điểm</span></p>
      </div>
      <button class="btn" :class="{ primary: t.status !== 'done' }" type="button" :disabled="busy === t.id" @click="run(t)">
        {{ busy === t.id ? 'Đang mở…' : t.status === 'done' ? 'Làm lại' : 'Làm ngay' }}
      </button>
    </li>
  </ol>
  <p v-if="err" class="notice err small" style="margin-top: 10px">{{ err }}</p>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { runTask } from '../composables/useTasks'

defineProps({ tasks: { type: Array, required: true }, showSource: Boolean })
const router = useRouter()
const busy = ref(null)
const err = ref('')

async function run(t) {
  busy.value = t.id
  err.value = ''
  try { await runTask(t, router) } catch (e) { err.value = e.message } finally { busy.value = null }
}
</script>

<style scoped>
.tasks { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 12px; }
.task {
  display: grid; grid-template-columns: auto 1fr auto; gap: 14px; align-items: center;
  padding: 14px 16px; border-radius: 20px; background: var(--paper-3); box-shadow: var(--shadow-in);
}
.num {
  width: 34px; height: 34px; border-radius: 12px; display: inline-flex; align-items: center; justify-content: center;
  font-weight: 900; color: #fff; background: var(--primary); box-shadow: 0 3px 0 0 var(--primary-edge), var(--hilite);
}
.done .num { background: var(--jade-fill); box-shadow: 0 3px 0 0 var(--jade-edge), var(--hilite); }
.done .tt { color: var(--ink-soft); }
.body { display: flex; flex-direction: column; gap: 4px; min-width: 0; }
.tt { font-weight: 800; }
@media (max-width: 560px) {
  .task { grid-template-columns: auto 1fr; }
  .task .btn { grid-column: 1 / -1; }
}
</style>

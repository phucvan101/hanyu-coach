import { api } from '../api'

// Mở một nhiệm vụ trong lộ trình cải thiện ở đúng trang của nó.
export async function runTask(task, router) {
  if (task.kind === 'pinyin_drill') return router.push(`/hanzi?task=${task.id}`)
  if (task.kind === 'rewrite') return router.push(`/task/${task.id}`)
  const r = await api.post(`/api/plan-tasks/${task.id}/start`)
  if (r.session_id) return router.push(`/session/${r.session_id}`)
}

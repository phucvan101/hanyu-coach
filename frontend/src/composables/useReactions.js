// Clip phản ứng (meme) khi trả lời đúng liên tiếp / đứt chuỗi.
// Clip đặt trong src/assets/reactions/<nhóm>/ — Vite tự tìm lúc build, không cần khai báo thêm:
//   streak-5, streak-10, streak-15, streak-20, streak-30 (và tuỳ chọn streak-40, streak-50…)
//   break     — đứt chuỗi từ 5 đến 29 câu (để trống = không hiện gì)
//   break-30  — đứt chuỗi từ 30 câu trở lên
import { reactive } from 'vue'

const files = import.meta.glob('../assets/reactions/*/*.{webm,mp4}', { eager: true, query: '?url', import: 'default' })

const groups = {}
for (const [path, url] of Object.entries(files)) {
  const g = path.split('/').at(-2)
  ;(groups[g] ||= []).push(url)
}

const MILESTONES = [5, 10, 15, 20, 30]
const STEP_AFTER = 10 // trên 30: cứ thêm 10 câu đúng mới hiện (40, 50, 60…)
const TOP = MILESTONES.at(-1)

export const reaction = reactive({ src: '', caption: '', tone: 'good', key: 0 })

const pick = (list) => list[Math.floor(Math.random() * list.length)]

function play(src, caption, tone) {
  if (!src) return
  Object.assign(reaction, { src, caption, tone, key: reaction.key + 1 })
}

export function hideReaction() {
  reaction.src = ''
}

function isMilestone(n) {
  return MILESTONES.includes(n) || (n > TOP && (n - TOP) % STEP_AFTER === 0)
}

// mốc chưa có clip thì lùi về nhóm streak-N thấp hơn gần nhất
function clipForStreak(n) {
  const keys = Object.keys(groups)
    .map((g) => /^streak-(\d+)$/.exec(g))
    .filter((m) => m && Number(m[1]) <= n)
    .map((m) => Number(m[1]))
    .sort((a, b) => b - a)
  return keys.length ? pick(groups[`streak-${keys[0]}`]) : ''
}

// Bộ đếm chuỗi cho một bài — gọi useStreak() trong component nên rời bài là chuỗi về 0.
export function useStreak() {
  let count = 0
  return {
    hit(correct) {
      if (correct) {
        count++
        if (isMilestone(count)) play(clipForStreak(count), `🔥 ${count} câu đúng liên tiếp!`, 'good')
        return
      }
      const lost = count
      count = 0
      if (lost >= TOP && groups['break-30']) play(pick(groups['break-30']), `Đứt chuỗi ${lost} câu… làm lại nào!`, 'bad')
      else if (lost >= MILESTONES[0] && groups.break) play(pick(groups.break), `Mất chuỗi ${lost} câu rồi!`, 'bad')
    },
    reset() {
      count = 0
    },
  }
}

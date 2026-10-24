// Clip phản ứng (meme) khi trả lời đúng liên tiếp / đứt chuỗi.
// Clip đặt trong src/assets/reactions/<nhóm>/ — Vite tự tìm lúc build, không cần khai báo thêm:
//   streak-5, streak-10, streak-15, streak-20, streak-30 (và tuỳ chọn streak-40, streak-50…)
//   break     — đứt chuỗi từ 5 đến 29 câu (để trống = không hiện gì)
//   break-30  — đứt chuỗi từ 30 câu trở lên
//   pass, fail — kết quả khi kết thúc hội thoại với AI (hội thoại không tính chuỗi)
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

// badge: dải ruy băng trên cùng · title/sub: lời chúc dưới clip · tone: good | bad
export const reaction = reactive({ src: '', badge: '', title: '', sub: '', tone: 'good', key: 0 })

// chọn ngẫu nhiên trong nhóm nhưng không lặp lại clip vừa phát của nhóm đó
const lastPicked = {}
function pick(group) {
  const list = groups[group] || []
  const pool = list.length > 1 ? list.filter((u) => u !== lastPicked[group]) : list
  const url = pool[Math.floor(Math.random() * pool.length)] || ''
  lastPicked[group] = url
  return url
}

function play(src, text) {
  if (!src) return
  Object.assign(reaction, { src, sub: '', ...text, key: reaction.key + 1 })
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
  return keys.length ? pick(`streak-${keys[0]}`) : ''
}

export function playResult(passed, score) {
  play(pick(passed ? 'pass' : 'fail'), passed
    ? { badge: `🎉 Đạt ${score} điểm!`, title: '太棒了! Xuất sắc!', sub: 'Bạn đã hoàn thành cuộc hội thoại', tone: 'good' }
    : { badge: `📝 ${score} điểm`, title: '加油! Cố lên nhé!', sub: 'Luyện thêm một chút là đạt ngay', tone: 'bad' })
}

// Bộ đếm chuỗi cho một bài — gọi useStreak() trong component nên rời bài là chuỗi về 0.
export function useStreak() {
  let count = 0
  return {
    hit(correct) {
      if (correct) {
        count++
        if (isMilestone(count)) play(clipForStreak(count), {
          badge: `🔥 ${count} câu đúng liên tiếp!`, title: count >= TOP ? 'Không thể cản nổi!' : 'Làm tốt lắm!',
          sub: `Bạn vừa đạt chuỗi ${count} câu đúng liên tiếp`, tone: 'good',
        })
        return
      }
      const lost = count
      count = 0
      const text = { badge: `Mất chuỗi ${lost} câu`, title: 'Cố lên nào!', sub: `Chuỗi ${lost} câu đã rất giỏi rồi, làm lại nhé`, tone: 'bad' }
      if (lost >= TOP && groups['break-30']) play(pick('break-30'), text)
      else if (lost >= MILESTONES[0]) play(pick('break'), text)
    },
    reset() {
      count = 0
    },
  }
}

// Hiệu ứng âm thanh ngắn cho bài luyện, tổng hợp bằng Web Audio (không cần file).
// AudioContext tạo lười ở lần phát đầu tiên (sau thao tác của người dùng) và dùng chung.

let ctx = null

function getCtx() {
  if (!ctx) {
    const AC = window.AudioContext || window.webkitAudioContext
    if (!AC) return null
    ctx = new AC()
  }
  if (ctx.state === 'suspended') ctx.resume().catch(() => {})
  return ctx
}

function note(c, f, t, d, peak) {
  const o = c.createOscillator()
  const g = c.createGain()
  o.type = 'triangle'
  o.frequency.setValueAtTime(f, t)
  g.gain.setValueAtTime(0.0001, t)
  g.gain.exponentialRampToValueAtTime(peak, t + 0.008)
  g.gain.exponentialRampToValueAtTime(0.0001, t + d)
  o.connect(g)
  g.connect(c.destination)
  o.start(t)
  o.stop(t + d + 0.05)
}

// tiếng "ting ting" đi lên khi trả lời đúng
export function playCorrect() {
  const c = getCtx()
  if (!c) return
  const t = c.currentTime + 0.01
  note(c, 1046.5, t, 0.18, 0.18) // C6
  note(c, 1568, t + 0.09, 0.35, 0.16) // G6
  note(c, 3136, t + 0.09, 0.2, 0.03) // bồi âm cho sáng
}

// tiếng "bùm bụp" trầm đi xuống khi trả lời sai — nhẹ, không gắt
export function playWrong() {
  const c = getCtx()
  if (!c) return
  const t = c.currentTime + 0.01
  note(c, 311.1, t, 0.16, 0.2) // Eb4
  note(c, 233.1, t + 0.13, 0.32, 0.2) // Bb3
}

import { ref } from 'vue'
import { settings } from './useSettings'
import { MIX_POOL, MIX_VOICE } from './ttsVoices'

const cache = new Map()
export const speaking = ref(null)
// cùng một chữ có nút đọc thường và nút đọc chậm -> phân biệt nút nào đang phát
export const speakingSlow = ref(false)
// đọc chậm phải giảm mạnh tốc độ: từ 1–2 chữ có khoảng lặng cố định nên -30% gần như không nghe ra khác biệt
const SLOW_OFFSET = -45
let current = null
let lastMixVoice = null

/** Chế độ trộn giọng: mỗi lần đọc chọn ngẫu nhiên một giọng khác lần trước. */
function resolveVoice() {
  const v = settings.tts_voice || 'zh-CN-XiaoxiaoNeural'
  if (v !== MIX_VOICE) return v
  const pool = MIX_POOL.filter((x) => x !== lastMixVoice)
  lastMixVoice = pool[Math.floor(Math.random() * pool.length)]
  return lastMixVoice
}

function pickVoice() {
  const voices = window.speechSynthesis ? window.speechSynthesis.getVoices() : []
  const zh = voices.filter((v) => /zh[-_]CN|cmn|Chinese.*Mandarin|普通话/i.test(v.lang + ' ' + v.name))
  return zh.find((v) => v.localService) || zh[0] || voices.find((v) => v.lang.startsWith('zh')) || null
}

function browserSpeak(text, rate) {
  return new Promise((resolve, reject) => {
    if (!window.speechSynthesis) return reject(new Error('Trình duyệt không hỗ trợ đọc'))
    window.speechSynthesis.cancel()
    const u = new SpeechSynthesisUtterance(text)
    u.lang = 'zh-CN'
    const v = pickVoice()
    if (v) u.voice = v
    u.rate = Math.max(0.5, 1 + rate / 100)
    u.onend = resolve
    u.onerror = resolve
    window.speechSynthesis.speak(u)
  })
}

export async function speak(text, { slow = false } = {}) {
  if (!text) return
  const rate = Math.max(-70, Number(settings.tts_rate || -10) + (slow ? SLOW_OFFSET : 0))
  if (current) { current.pause(); current = null }
  speaking.value = text
  speakingSlow.value = slow
  try {
    if (settings.tts_source !== 'browser') {
      try {
        const voice = resolveVoice()
        const key = `${voice}|${rate}|${text}`
        let audio = cache.get(key)
        if (!audio) {
          audio = new Audio(`/api/tts?rate=${rate}&voice=${encodeURIComponent(voice)}&text=${encodeURIComponent(text)}`)
          cache.set(key, audio)
        }
        current = audio
        audio.currentTime = 0
        await new Promise((resolve, reject) => {
          audio.onended = resolve
          audio.onerror = () => { cache.delete(key); reject(new Error('tts')) }
          audio.play().catch(reject)
        })
        return
      } catch (e) {
        if (settings.tts_source === 'server') throw e
      }
    }
    await browserSpeak(text, rate)
  } finally {
    if (speaking.value === text && speakingSlow.value === slow) speaking.value = null
  }
}

if (typeof window !== 'undefined' && window.speechSynthesis) {
  window.speechSynthesis.onvoiceschanged = () => {}
}

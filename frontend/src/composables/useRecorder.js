import { ref } from 'vue'

const BARS = 32

/** Ghi âm -> WAV 16kHz mono (để gửi Gemini nhận dạng). `levels` là độ lớn theo dải tần để vẽ sóng âm. */
export function useRecorder() {
  const recording = ref(false)
  const seconds = ref(0)
  const levels = ref(new Array(BARS).fill(0))
  let media = null
  let rec = null
  let chunks = []
  let timer = null
  let actx = null
  let raf = 0

  function startMeter() {
    try {
      const AC = window.AudioContext || window.webkitAudioContext
      actx = new AC()
      const analyser = actx.createAnalyser()
      analyser.fftSize = 256
      analyser.smoothingTimeConstant = 0.7
      actx.createMediaStreamSource(media).connect(analyser)
      const buf = new Uint8Array(analyser.frequencyBinCount)
      // giọng nói nằm ở nửa dưới phổ
      const span = Math.floor(buf.length * 0.55)
      const tick = () => {
        analyser.getByteFrequencyData(buf)
        const out = []
        for (let i = 0; i < BARS; i++) {
          const a = Math.floor((i * span) / BARS)
          const b = Math.max(a + 1, Math.floor(((i + 1) * span) / BARS))
          let m = 0
          for (let j = a; j < b; j++) m = Math.max(m, buf[j])
          out.push(m / 255)
        }
        levels.value = out
        raf = requestAnimationFrame(tick)
      }
      tick()
    } catch { /* không vẽ được sóng âm thì vẫn ghi âm bình thường */ }
  }

  function stopMeter() {
    cancelAnimationFrame(raf)
    if (actx) actx.close().catch(() => {})
    actx = null
    levels.value = new Array(BARS).fill(0)
  }

  async function start() {
    media = await navigator.mediaDevices.getUserMedia({ audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true } })
    chunks = []
    rec = new MediaRecorder(media)
    rec.ondataavailable = (e) => e.data.size && chunks.push(e.data)
    rec.start()
    startMeter()
    recording.value = true
    seconds.value = 0
    timer = setInterval(() => {
      seconds.value++
      if (seconds.value >= 30) stop()
    }, 1000)
  }

  function stop() {
    return new Promise((resolve) => {
      if (!rec || rec.state === 'inactive') return resolve(null)
      clearInterval(timer)
      stopMeter()
      rec.onstop = async () => {
        recording.value = false
        media.getTracks().forEach((t) => t.stop())
        const blob = new Blob(chunks, { type: rec.mimeType })
        try {
          resolve(await toWav(blob))
        } catch (e) {
          resolve(null)
        }
      }
      rec.stop()
    })
  }

  function cancel() {
    stopMeter()
    if (rec && rec.state !== 'inactive') {
      rec.onstop = () => media.getTracks().forEach((t) => t.stop())
      rec.stop()
    }
    clearInterval(timer)
    recording.value = false
  }

  return { recording, seconds, levels, start, stop, cancel }
}

async function toWav(blob) {
  const buf = await blob.arrayBuffer()
  const AC = window.AudioContext || window.webkitAudioContext
  const ctx = new AC()
  const decoded = await ctx.decodeAudioData(buf)
  ctx.close()
  const rate = 16000
  const off = new OfflineAudioContext(1, Math.ceil(decoded.duration * rate), rate)
  const src = off.createBufferSource()
  src.buffer = decoded
  src.connect(off.destination)
  src.start()
  const rendered = await off.startRendering()
  const data = rendered.getChannelData(0)
  const out = new DataView(new ArrayBuffer(44 + data.length * 2))
  const w = (o, s) => [...s].forEach((c, i) => out.setUint8(o + i, c.charCodeAt(0)))
  w(0, 'RIFF'); out.setUint32(4, 36 + data.length * 2, true); w(8, 'WAVE'); w(12, 'fmt ')
  out.setUint32(16, 16, true); out.setUint16(20, 1, true); out.setUint16(22, 1, true)
  out.setUint32(24, rate, true); out.setUint32(28, rate * 2, true); out.setUint16(32, 2, true); out.setUint16(34, 16, true)
  w(36, 'data'); out.setUint32(40, data.length * 2, true)
  for (let i = 0; i < data.length; i++) {
    const s = Math.max(-1, Math.min(1, data[i]))
    out.setInt16(44 + i * 2, s < 0 ? s * 0x8000 : s * 0x7fff, true)
  }
  return new Blob([out], { type: 'audio/wav' })
}

/** Dự phòng: nhận dạng bằng Web Speech API của trình duyệt (Chrome/Edge). */
export function browserRecognize() {
  return new Promise((resolve, reject) => {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition
    if (!SR) return reject(new Error('Trình duyệt không hỗ trợ nhận dạng giọng nói'))
    const r = new SR()
    r.lang = 'zh-CN'
    r.interimResults = false
    r.maxAlternatives = 1
    r.onresult = (e) => resolve(e.results[0][0].transcript)
    r.onerror = (e) => reject(new Error(e.error))
    r.start()
  })
}

// Âm thanh cho game bắn chữ: nhạc nền và hiệu ứng tổng hợp hoàn toàn bằng Web Audio (không cần file âm thanh).
// Nhạc dùng thang ngũ cung (A C D E G) cho chất "phương Đông", nhịp nhanh dần theo mốc.

const PENTA = [0, 3, 5, 7, 10] // A C D E G (tính theo nửa cung từ A)
// vòng hợp âm 4 nhịp: Am – F – G – Em (gốc bass, MIDI)
const PROG = [45, 41, 43, 40]
const midi = (n) => 440 * Math.pow(2, (n - 69) / 12)

export function createGameAudio() {
  const AC = window.AudioContext || window.webkitAudioContext
  if (!AC) return null
  const ctx = new AC()

  const comp = ctx.createDynamicsCompressor()
  comp.threshold.value = -14
  comp.ratio.value = 4
  comp.connect(ctx.destination)
  const music = ctx.createGain()
  const sfx = ctx.createGain()
  music.gain.value = 0.55
  sfx.gain.value = 0.9
  music.connect(comp)
  sfx.connect(comp)

  // bộ lọc chung cho lớp nhạc: mở dần khi căng thẳng
  const musicFilter = ctx.createBiquadFilter()
  musicFilter.type = 'lowpass'
  musicFilter.frequency.value = 2400
  musicFilter.connect(music)

  // tạp âm trắng dùng cho trống, nổ
  const noise = ctx.createBuffer(1, ctx.sampleRate * 1.5, ctx.sampleRate)
  const nd = noise.getChannelData(0)
  for (let i = 0; i < nd.length; i++) nd[i] = Math.random() * 2 - 1

  function env(g, t, peak, a, d) {
    g.gain.cancelScheduledValues(t)
    g.gain.setValueAtTime(0.0001, t)
    g.gain.exponentialRampToValueAtTime(peak, t + a)
    g.gain.exponentialRampToValueAtTime(0.0001, t + a + d)
  }

  function tone(dest, { type = 'sine', f0, f1, t, a = 0.003, d = 0.15, peak = 0.3, q, filt }) {
    const o = ctx.createOscillator()
    const g = ctx.createGain()
    o.type = type
    o.frequency.setValueAtTime(f0, t)
    if (f1) o.frequency.exponentialRampToValueAtTime(f1, t + a + d)
    let node = o
    if (filt) {
      const bq = ctx.createBiquadFilter()
      bq.type = 'lowpass'
      bq.frequency.value = filt
      if (q) bq.Q.value = q
      o.connect(bq)
      node = bq
    }
    node.connect(g)
    g.connect(dest)
    env(g, t, peak, a, d)
    o.start(t)
    o.stop(t + a + d + 0.05)
  }

  function burst(dest, { t, d = 0.2, peak = 0.4, type = 'lowpass', f0 = 4000, f1 = 300, q = 1 }) {
    const s = ctx.createBufferSource()
    s.buffer = noise
    const bq = ctx.createBiquadFilter()
    bq.type = type
    bq.Q.value = q
    bq.frequency.setValueAtTime(f0, t)
    bq.frequency.exponentialRampToValueAtTime(Math.max(40, f1), t + d)
    const g = ctx.createGain()
    s.connect(bq)
    bq.connect(g)
    g.connect(dest)
    env(g, t, peak, 0.002, d)
    s.start(t, Math.random() * 0.5)
    s.stop(t + d + 0.05)
  }

  // ---------------------------------------------------------------- nhạc nền
  let bpm = 124
  let intensity = 0 // 0..1: số lớp nhạc + độ mở bộ lọc
  let step = 0
  let nextTime = 0
  let timer = null
  let melody = []

  function newPhrase() {
    // câu nhạc ngắn trên ngũ cung, lặp 2 nhịp để dễ nhớ
    melody = Array.from({ length: 16 }, (_, i) => {
      if (i % 2 && Math.random() < 0.55) return null
      if (Math.random() < 0.18) return null
      return 69 + PENTA[Math.floor(Math.random() * 5)] + (Math.random() < 0.25 ? 12 : 0)
    })
  }
  newPhrase()

  function scheduleStep(s, t) {
    const i = s % 16
    const bar = Math.floor(s / 16) % 4
    const root = PROG[bar]
    const sixteenth = 60 / bpm / 4
    // trống kick
    if (i % 4 === 0) tone(musicFilter, { f0: 150, f1: 42, t, d: 0.22, peak: 0.9 })
    // snare / clap
    if (i === 4 || i === 12) {
      burst(musicFilter, { t, d: 0.14, peak: 0.35, type: 'bandpass', f0: 1800, f1: 900, q: 0.8 })
      tone(musicFilter, { type: 'triangle', f0: 220, f1: 140, t, d: 0.08, peak: 0.2 })
    }
    // hi-hat
    const hatPeak = i % 4 === 2 ? 0.14 : intensity > 0.35 ? 0.06 : 0
    if (hatPeak) burst(music, { t, d: i % 4 === 2 ? 0.08 : 0.03, peak: hatPeak, type: 'highpass', f0: 8000, f1: 7000 })
    // bass bập bênh quãng tám theo móc đơn
    if (i % 2 === 0) {
      const n = root + (i % 4 === 2 ? 12 : 0)
      tone(musicFilter, { type: 'sawtooth', f0: midi(n), t, d: sixteenth * 1.6, peak: 0.22, filt: 500 + intensity * 900, q: 6 })
    }
    // arpeggio móc kép (từ mốc giữa)
    if (intensity > 0.2) {
      const chord = [root + 24, root + 31, root + 36, root + 31]
      tone(musicFilter, { type: 'square', f0: midi(chord[i % 4]), t, d: sixteenth * 0.8, peak: 0.045 + intensity * 0.03, filt: 3000 })
    }
    // giai điệu kiểu đàn tranh: gảy nhanh, tắt nhanh
    if (intensity > 0.05 && bar % 2 === 1) {
      const n = melody[i]
      if (n) {
        tone(musicFilter, { type: 'triangle', f0: midi(n) * 1.01, f1: midi(n), t, a: 0.002, d: 0.35, peak: 0.16 })
        tone(musicFilter, { type: 'sine', f0: midi(n + 12), t, a: 0.002, d: 0.12, peak: 0.05 })
      }
    }
    if (i === 15 && bar === 3) newPhrase()
  }

  function tick() {
    while (nextTime < ctx.currentTime + 0.12) {
      scheduleStep(step, nextTime)
      nextTime += 60 / bpm / 4
      step++
    }
  }

  function startMusic() {
    if (timer) return
    step = 0
    nextTime = ctx.currentTime + 0.05
    timer = setInterval(tick, 25)
  }
  function stopMusic() {
    clearInterval(timer)
    timer = null
  }

  // ---------------------------------------------------------------- hiệu ứng
  const now = () => ctx.currentTime
  const fx = {
    shoot(combo = 0) {
      const t = now()
      const up = Math.min(combo, 40) * 12
      tone(sfx, { type: 'square', f0: 1100 + up, f1: 260 + up / 2, t, d: 0.07, peak: 0.12, filt: 5000 })
      burst(sfx, { t, d: 0.03, peak: 0.08, type: 'highpass', f0: 6000, f1: 5000 })
    },
    lock() {
      const t = now()
      tone(sfx, { type: 'triangle', f0: 1320, t, d: 0.04, peak: 0.12 })
      tone(sfx, { type: 'triangle', f0: 1760, t: t + 0.045, d: 0.05, peak: 0.12 })
    },
    hit() {
      tone(sfx, { type: 'sine', f0: 1800, f1: 900, t: now(), d: 0.04, peak: 0.08 })
    },
    explode(size = 1) {
      const t = now()
      burst(sfx, { t, d: 0.35 + size * 0.1, peak: 0.5, f0: 5000, f1: 120 })
      tone(sfx, { type: 'sine', f0: 160, f1: 38, t, d: 0.35, peak: 0.6 })
      tone(sfx, { type: 'sawtooth', f0: 90, f1: 30, t, d: 0.25, peak: 0.12, filt: 400 })
    },
    error() {
      const t = now()
      tone(sfx, { type: 'sawtooth', f0: 140, f1: 90, t, d: 0.14, peak: 0.18, filt: 900 })
    },
    damage() {
      const t = now()
      burst(sfx, { t, d: 0.7, peak: 0.7, f0: 2500, f1: 60 })
      tone(sfx, { type: 'sine', f0: 120, f1: 28, t, d: 0.6, peak: 0.8 })
      tone(sfx, { type: 'sawtooth', f0: 420, f1: 60, t, d: 0.5, peak: 0.12, filt: 1200 })
    },
    combo() {
      const t = now()
      ;[0, 3, 5, 7, 10, 12].forEach((p, k) => tone(sfx, { type: 'triangle', f0: midi(81 + p), t: t + k * 0.03, d: 0.18, peak: 0.07 }))
    },
    wave() {
      const t = now()
      ;[0, 3, 5, 7, 12, 15, 19, 24].forEach((p, k) => tone(sfx, { type: 'square', f0: midi(69 + p), t: t + k * 0.07, d: 0.22, peak: 0.07, filt: 4000 }))
    },
    powerup() {
      const t = now()
      ;[0, 4, 7, 12, 16, 19, 24].forEach((p, k) => tone(sfx, { type: 'sine', f0: midi(76 + p), t: t + k * 0.035, d: 0.2, peak: 0.12 }))
      burst(sfx, { t, d: 0.4, peak: 0.08, type: 'highpass', f0: 9000, f1: 5000 })
    },
    shield() {
      const t = now()
      tone(sfx, { type: 'triangle', f0: 600, f1: 1400, t, d: 0.25, peak: 0.25 })
      tone(sfx, { type: 'sine', f0: 1200, f1: 2400, t: t + 0.05, d: 0.3, peak: 0.12 })
    },
    bomb() {
      const t = now()
      burst(sfx, { t, d: 1.2, peak: 0.9, f0: 6000, f1: 50 })
      tone(sfx, { type: 'sine', f0: 200, f1: 25, t, d: 1, peak: 0.9 })
      tone(sfx, { type: 'sawtooth', f0: 120, f1: 30, t: t + 0.05, d: 0.8, peak: 0.2, filt: 600 })
    },
    alarm() {
      const t = now()
      for (let k = 0; k < 3; k++) {
        tone(sfx, { type: 'sawtooth', f0: 440, f1: 880, t: t + k * 0.42, a: 0.01, d: 0.36, peak: 0.16, filt: 2500 })
      }
      tone(sfx, { type: 'sine', f0: 55, t, a: 0.3, d: 1.2, peak: 0.5 })
    },
    bossHit() {
      const t = now()
      tone(sfx, { type: 'square', f0: 220, f1: 110, t, d: 0.08, peak: 0.14, filt: 1600 })
      burst(sfx, { t, d: 0.08, peak: 0.15, type: 'bandpass', f0: 2500, f1: 1200, q: 2 })
    },
    bossDown() {
      const t = now()
      for (let k = 0; k < 5; k++) {
        burst(sfx, { t: t + k * 0.13, d: 0.5, peak: 0.6, f0: 5000 - k * 600, f1: 80 })
        tone(sfx, { type: 'sine', f0: 180 - k * 15, f1: 30, t: t + k * 0.13, d: 0.45, peak: 0.6 })
      }
      ;[0, 3, 5, 7, 10, 12, 15, 17, 19, 24].forEach((p, k) => tone(sfx, { type: 'triangle', f0: midi(69 + p), t: t + 0.7 + k * 0.06, d: 0.3, peak: 0.1 }))
    },
    gameOver() {
      const t = now()
      ;[12, 10, 7, 5, 3, 0, -5].forEach((p, k) => tone(sfx, { type: 'triangle', f0: midi(69 + p), t: t + k * 0.16, d: 0.4, peak: 0.16 }))
      tone(sfx, { type: 'sine', f0: 110, f1: 40, t: t + 1.1, d: 1.2, peak: 0.4 })
    },
  }

  return {
    ctx,
    fx,
    startMusic,
    stopMusic,
    setTempo(b) { bpm = b },
    setIntensity(v) {
      intensity = Math.max(0, Math.min(1, v))
      musicFilter.frequency.setTargetAtTime(1400 + intensity * 5000, ctx.currentTime, 0.4)
    },
    setMusicOn(on) { music.gain.setTargetAtTime(on ? 0.55 : 0, ctx.currentTime, 0.05) },
    setSfxOn(on) { sfx.gain.setTargetAtTime(on ? 0.9 : 0, ctx.currentTime, 0.02) },
    resume() { return ctx.state === 'suspended' ? ctx.resume() : Promise.resolve() },
    suspend() { return ctx.state === 'running' ? ctx.suspend() : Promise.resolve() },
    close() {
      stopMusic()
      ctx.close().catch(() => {})
    },
  }
}

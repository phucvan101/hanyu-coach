<template>
  <Transition name="dim"><div v-if="reaction.src" class="dim" aria-hidden="true" @click="hideReaction" /></Transition>
  <Transition name="pop">
    <div v-if="reaction.src" :key="reaction.key" class="rc" :class="[reaction.tone, { offset: withRail }]" role="dialog" aria-live="polite" :aria-label="reaction.badge">
      <div v-if="reaction.tone === 'good'" class="confetti" aria-hidden="true">
        <i v-for="(c, i) in confetti" :key="i" :class="c.shape" :style="c.style" />
      </div>

      <!-- đúng liên tiếp / đạt: cúp vàng · đứt chuỗi / chưa đạt: trái tim động viên -->
      <svg v-if="reaction.tone === 'good'" class="emblem" viewBox="0 0 120 104" aria-hidden="true">
        <defs>
          <linearGradient id="rc-gold" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0" stop-color="#ffe680" /><stop offset=".55" stop-color="#fbbf24" /><stop offset="1" stop-color="#e08a00" />
          </linearGradient>
          <linearGradient id="rc-gold-d" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stop-color="#f59e0b" /><stop offset="1" stop-color="#c26a00" />
          </linearGradient>
        </defs>
        <path d="M30 20H17a11 11 0 0 0 0 22c7 0 12-3 16-9M90 20h13a11 11 0 0 1 0 22c-7 0-12-3-16-9" fill="none" stroke="url(#rc-gold-d)" stroke-width="7" stroke-linecap="round" />
        <path d="M27 12h66v18c0 22-14.8 38-33 38S27 52 27 30z" fill="url(#rc-gold)" />
        <ellipse cx="60" cy="12" rx="33" ry="5" fill="#fff1a8" />
        <path d="M36 20c0 18 6 30 15 37" fill="none" stroke="#fff" stroke-opacity=".5" stroke-width="5" stroke-linecap="round" />
        <path d="M60 22l4.4 9 9.9 1.4-7.2 7 1.7 9.8L60 44.6l-8.8 4.6 1.7-9.8-7.2-7 9.9-1.4z" fill="#fff" stroke="#fde68a" stroke-width="1.5" stroke-linejoin="round" />
        <rect x="53" y="66" width="14" height="12" fill="url(#rc-gold-d)" />
        <rect x="39" y="77" width="42" height="11" rx="4" fill="url(#rc-gold)" />
        <rect x="33" y="87" width="54" height="11" rx="4" fill="url(#rc-gold-d)" />
      </svg>
      <svg v-else class="emblem heart" viewBox="0 0 120 104" aria-hidden="true">
        <defs>
          <linearGradient id="rc-rose" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0" stop-color="#fda4af" /><stop offset=".6" stop-color="#fb7185" /><stop offset="1" stop-color="#e11d48" />
          </linearGradient>
        </defs>
        <path d="M60 96S14 68 14 38a23 23 0 0 1 46-6 23 23 0 0 1 46 6c0 30-46 58-46 58z" fill="url(#rc-rose)" />
        <path d="M30 34a12 12 0 0 1 14-12" fill="none" stroke="#fff" stroke-opacity=".6" stroke-width="6" stroke-linecap="round" />
      </svg>

      <div class="badge">{{ reaction.badge }}</div>

      <div class="card">
        <div class="stage">
          <video ref="vid" :src="reaction.src" autoplay playsinline @ended="hideReaction" @error="hideReaction" />
          <button type="button" class="mute" :aria-label="muted ? 'Bật tiếng' : 'Tắt tiếng'" :title="muted ? 'Bật tiếng' : 'Tắt tiếng'" @click="toggleMute">
            <svg viewBox="0 0 20 20" width="16" height="16" aria-hidden="true">
              <path d="M3 7.5h3l4-3.5v12l-4-3.5H3z" fill="currentColor" />
              <path v-if="muted" d="M13 7.5l4 5m0-5l-4 5" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" />
              <path v-else d="M13 7a4 4 0 0 1 0 6m2.2-8.4a7 7 0 0 1 0 10.8" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" />
            </svg>
          </button>
        </div>
        <span class="cloud l" aria-hidden="true" /><span class="cloud r" aria-hidden="true" />

        <h3 class="title"><span class="spark" aria-hidden="true">✦</span>{{ reaction.title }}<span class="spark" aria-hidden="true">✦</span></h3>
        <p v-if="reaction.sub" class="sub">{{ reaction.sub }}</p>
        <button type="button" class="btn primary lg go" @click="hideReaction">Tiếp tục →</button>
      </div>
    </div>
  </Transition>
</template>

<script setup>
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { reaction, hideReaction } from '../composables/useReactions'

defineProps({ withRail: Boolean }) // có thanh điều hướng bên trái thì lệch tâm sang phần bài học

const MAX_MS = 6000 // clip dài quá thì tự tắt, không che bài học lâu
const vid = ref(null)
const muted = ref(false)
let timer = 0

// pháo giấy rải quanh thẻ: vị trí cố định cho đều tay, chỉ màu/hình xoay vòng
const COLORS = ['#facc15', '#3b82f6', '#fb923c', '#22c55e', '#60a5fa', '#f472b6']
const SPOTS = [[8, 14], [20, 4], [33, 10], [67, 9], [80, 3], [92, 15], [3, 34], [97, 30], [6, 55], [95, 52], [13, 26], [88, 40], [26, 22], [74, 24]]
const confetti = SPOTS.map(([x, y], i) => ({
  shape: ['bit', 'star', 'dot'][i % 3],
  style: { left: `${x}%`, top: `${y}%`, '--c': COLORS[i % COLORS.length], '--r': `${(i * 47) % 360}deg`, '--d': `${(i % 5) * 0.12}s` },
}))

function toggleMute() {
  if (!vid.value) return
  vid.value.muted = !vid.value.muted
  muted.value = vid.value.muted
}

function onKey(e) {
  if (e.key === 'Escape' && reaction.src) hideReaction()
}
onMounted(() => window.addEventListener('keydown', onKey))

watch(() => reaction.key, async () => {
  clearTimeout(timer)
  timer = setTimeout(hideReaction, MAX_MS)
  muted.value = false
  await nextTick()
  // trình duyệt chặn tự phát có tiếng thì phát không tiếng
  vid.value?.play().catch(() => {
    if (!vid.value) return
    vid.value.muted = muted.value = true
    vid.value.play().catch(hideReaction)
  })
})
onBeforeUnmount(() => {
  clearTimeout(timer)
  window.removeEventListener('keydown', onKey)
})
</script>

<style scoped>
.rc {
  /* nằm chính giữa vùng bài học */
  --accent: var(--primary-strong);
  --ribbon: linear-gradient(100deg, #6366f1, #3b82f6 60%, #38bdf8);
  position: fixed; left: 50%; top: 50%; z-index: 80; width: min(380px, calc(100vw - 32px));
  display: flex; flex-direction: column; align-items: center;
  transform: translate(-50%, -50%);
}
.rc.bad { --accent: var(--seal); --ribbon: linear-gradient(100deg, #f43f5e, #fb7185 55%, #fb923c); }
.rc.offset { left: calc(50% + 120px); } /* 240px thanh bên / 2 */

.emblem { position: relative; z-index: 2; width: 104px; height: 90px; margin-bottom: -14px; filter: drop-shadow(0 10px 14px rgba(224, 138, 0, .35)); animation: bob 2.4s ease-in-out .5s infinite; }
.emblem.heart { filter: drop-shadow(0 10px 14px rgba(225, 29, 72, .3)); }

.badge {
  position: relative; z-index: 3; margin-bottom: -22px; padding: 10px 22px; border-radius: 999px;
  background: var(--ribbon); color: #fff; font-weight: 900; font-size: 17px; white-space: nowrap;
  box-shadow: 0 4px 0 rgba(30, 41, 120, .35), 0 12px 24px -8px rgba(59, 130, 246, .6), inset 0 2px 0 rgba(255, 255, 255, .35);
  transform: rotate(-3deg);
}
.rc.bad .badge { box-shadow: 0 4px 0 rgba(150, 20, 50, .35), 0 12px 24px -8px rgba(244, 63, 94, .55), inset 0 2px 0 rgba(255, 255, 255, .35); }

.card {
  position: relative; width: 100%; box-sizing: border-box; padding: 40px 22px 22px; border-radius: 30px;
  display: flex; flex-direction: column; align-items: center; text-align: center;
  background: var(--paper-2);
  box-shadow: 0 0 0 6px color-mix(in srgb, var(--paper-2) 55%, transparent), 0 30px 70px -10px rgba(var(--clay-tint), .45);
}
.stage {
  position: relative; z-index: 1; width: 76%; aspect-ratio: 4 / 5; max-height: min(270px, 36vh); border-radius: 20px; overflow: hidden;
  background: radial-gradient(circle at 50% 40%, var(--paper-2), var(--primary-soft) 75%);
  box-shadow: inset 0 0 0 1px var(--line), 0 10px 22px -12px rgba(var(--clay-tint), .5);
}
.rc.bad .stage { background: radial-gradient(circle at 50% 40%, var(--paper-2), var(--seal-soft) 75%); }
.stage video { width: 100%; height: 100%; object-fit: contain; display: block; }
.mute {
  position: absolute; right: 10px; bottom: 10px; width: 34px; height: 34px; border: 0; border-radius: 50%;
  display: grid; place-items: center; cursor: pointer; color: #fff; background: rgba(15, 23, 42, .55); backdrop-filter: blur(4px);
  transition: transform .18s var(--ease-spring), background .18s;
}
.mute:hover { transform: scale(1.1); background: rgba(15, 23, 42, .75); }

/* mây hai bên khung clip */
.cloud {
  position: absolute; top: 38%; width: 92px; height: 56px; border-radius: 40px; pointer-events: none;
  background: linear-gradient(var(--paper-2), var(--primary-soft));
  box-shadow: 0 8px 20px -10px rgba(var(--clay-tint), .4);
}
.cloud::before, .cloud::after { content: ''; position: absolute; border-radius: 50%; background: inherit; }
.cloud::before { width: 52px; height: 52px; left: 12px; top: -26px; }
.cloud::after { width: 40px; height: 40px; left: 46px; top: -14px; }
.cloud.l { left: -30px; }
.cloud.r { right: -30px; transform: scaleX(-1); }

.title { display: flex; align-items: center; gap: 10px; margin: 18px 0 4px; font-size: 26px; font-weight: 900; color: var(--accent); line-height: 1.2; }
.spark { color: var(--sun); font-size: 20px; animation: twinkle 1.6s ease-in-out infinite; }
.spark:last-child { animation-delay: .8s; }
.sub { margin: 0 0 18px; color: var(--ink-soft); font-size: 15px; font-weight: 600; }
.go { width: 100%; }

.confetti { position: absolute; inset: -40px -70px auto; height: 70%; pointer-events: none; z-index: 0; }
.confetti i { position: absolute; display: block; background: var(--c); opacity: 0; transform: rotate(var(--r)); animation: burst .6s var(--ease-spring) var(--d) forwards, drift 3s ease-in-out calc(var(--d) + .6s) infinite alternate; }
.confetti .bit { width: 12px; height: 8px; border-radius: 3px; }
.confetti .dot { width: 7px; height: 7px; border-radius: 50%; }
.confetti .star { width: 16px; height: 16px; clip-path: polygon(50% 0, 62% 35%, 100% 38%, 70% 60%, 80% 100%, 50% 76%, 20% 100%, 30% 60%, 0 38%, 38% 35%); }

@keyframes burst { from { opacity: 0; transform: translateY(30px) scale(.2) rotate(0); } to { opacity: 1; transform: translateY(0) scale(1) rotate(var(--r)); } }
@keyframes drift { to { transform: translateY(8px) rotate(calc(var(--r) + 40deg)); } }
@keyframes bob { 50% { transform: translateY(-5px) rotate(-2deg); } }
@keyframes twinkle { 50% { transform: scale(.7) rotate(20deg); opacity: .6; } }

/* làm mờ bài học phía sau cho thẻ nổi lên — bấm ra ngoài là đóng */
.dim { position: fixed; inset: 0; z-index: 79; background: rgba(var(--clay-tint), .18); backdrop-filter: blur(3px); }
.dim-enter-active, .dim-leave-active { transition: opacity .25s ease; }
.dim-enter-from, .dim-leave-to { opacity: 0; }

.pop-enter-active { transition: transform .4s var(--ease-spring), opacity .2s; }
.pop-leave-active { transition: transform .2s ease, opacity .2s; }
.pop-enter-from, .pop-leave-to { opacity: 0; transform: translate(-50%, -50%) scale(.7); }
@media (max-width: 760px) {
  .rc.offset { left: 50%; } /* thanh điều hướng chuyển xuống dưới */
  .badge { font-size: 15px; padding: 9px 18px; }
  .title { font-size: 22px; }
  .cloud { display: none; }
}
@media (prefers-reduced-motion: reduce) {
  .pop-enter-active, .pop-leave-active { transition: opacity .2s; }
  .pop-enter-from, .pop-leave-to { transform: translate(-50%, -50%); }
  .emblem, .spark { animation: none; }
  .confetti i { animation: none; opacity: 1; }
}
</style>

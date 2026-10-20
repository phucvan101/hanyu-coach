<template>
  <div class="shell" :class="{ focus: route.meta.focus }">
    <nav v-if="!route.meta.focus" class="rail" aria-label="Điều hướng chính">
      <RouterLink to="/" class="brand" aria-label="Trang chủ Hanyu Coach">
        <span class="mark han">汉</span>
        <span class="bt"><b>Hanyu</b> Coach</span>
      </RouterLink>
      <div class="groups">
        <section v-for="g in groups" :key="g.key" class="grp" :class="{ open: isOpen(g), current: hasActive(g) }">
          <button type="button" class="grp-h" :aria-expanded="isOpen(g)" :aria-controls="`grp-${g.key}`" @click="toggle(g)">
            <span class="grp-t">{{ g.label }}</span>
            <svg class="chev" viewBox="0 0 20 20" width="14" height="14" aria-hidden="true"><path d="M6 8l4 4 4-4" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/></svg>
          </button>
          <div :id="`grp-${g.key}`" class="grp-b">
            <div class="grp-in">
              <RouterLink v-for="l in g.items" :key="l.to" :to="l.to" class="nav" :class="{ active: isActive(l.to) }">
                <span class="ic han" aria-hidden="true">{{ l.zh }}</span>
                <span class="lb">{{ l.label }}</span>
                <span class="lb-s" aria-hidden="true">{{ l.short || l.label }}</span>
              </RouterLink>
            </div>
          </div>
        </section>
      </div>
      <!-- Hệ thống: ít dùng, ghim ở đáy -->
      <div class="sys">
        <RouterLink to="/settings" class="nav" :class="{ active: isActive('/settings') }">
          <span class="ic han" aria-hidden="true">设</span>
          <span class="lb">Cài đặt</span>
          <span class="lb-s" aria-hidden="true">Cài đặt</span>
        </RouterLink>
        <button type="button" class="nav theme-btn" :aria-pressed="isDark" :title="isDark ? 'Chuyển sang giao diện sáng' : 'Chuyển sang giao diện tối'"
          @click="setTheme(isDark ? 'light' : 'dark')">
          <span class="ic" aria-hidden="true">
            <svg v-if="isDark" viewBox="0 0 20 20" width="18" height="18"><circle cx="10" cy="10" r="3.6" fill="currentColor"/><g stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><path d="M10 2.2v1.9M10 15.9v1.9M2.2 10h1.9M15.9 10h1.9M4.5 4.5l1.3 1.3M14.2 14.2l1.3 1.3M4.5 15.5l1.3-1.3M14.2 5.8l1.3-1.3"/></g></svg>
            <svg v-else viewBox="0 0 20 20" width="18" height="18"><path d="M16.5 12.6A7 7 0 0 1 7.4 3.5a7 7 0 1 0 9.1 9.1z" fill="currentColor"/></svg>
          </span>
          <span class="lb">{{ isDark ? 'Giao diện sáng' : 'Giao diện tối' }}</span>
        </button>
      </div>
    </nav>
    <main class="main">
      <RouterView v-slot="{ Component }">
        <Transition name="fade" mode="out-in"><component :is="Component" :key="route.fullPath" /></Transition>
      </RouterView>
    </main>
    <ReactionClip />
  </div>
</template>

<script setup>
import { reactive } from 'vue'
import { isDark, setTheme } from './composables/useTheme'
import { useRoute } from 'vue-router'
import ReactionClip from './components/ReactionClip.vue'
const route = useRoute()
const groups = [
  { key: 'hoc', label: 'Học', items: [
    { to: '/', label: 'Học', zh: '学' },
    { to: '/flashcards', label: 'Flashcard', zh: '卡' },
    { to: '/hanzi', label: 'Hán tự → pinyin', short: 'Pinyin', zh: '字' },
  ] },
  { key: 'luyen', label: 'Luyện tập', items: [
    { to: '/talk', label: 'Hội thoại tổng hợp', short: 'Hội thoại', zh: '话' },
    { to: '/game', label: 'Chơi game', short: 'Game', zh: '玩' },
  ] },
  { key: 'on', label: 'Ôn tập', items: [
    { to: '/notebook', label: 'Sổ lỗi', zh: '错' },
    { to: '/library', label: 'Thư viện', zh: '书' },
    { to: '/history', label: 'Lịch sử', zh: '史' },
  ] },
]

// nhóm đang mở/đóng: chỉ là tuỳ chọn hiển thị, lưu trên trình duyệt
const NAV_KEY = 'hanyu.nav.collapsed'
const collapsed = reactive(readCollapsed())
function readCollapsed() {
  try { return JSON.parse(localStorage.getItem(NAV_KEY) || '{}') } catch { return {} }
}
function isActive(to) {
  return to === '/' ? route.path === '/' : route.path.startsWith(to)
}
const hasActive = (g) => g.items.some((l) => isActive(l.to))
// nhóm chứa trang hiện tại luôn mở để không "lạc" mục đang xem
const isOpen = (g) => hasActive(g) || !collapsed[g.key]
function toggle(g) {
  if (hasActive(g)) return
  collapsed[g.key] = !collapsed[g.key]
  try { localStorage.setItem(NAV_KEY, JSON.stringify(collapsed)) } catch { /* bỏ qua */ }
}
</script>

<style>
.shell { display: grid; grid-template-columns: 240px 1fr; min-height: 100dvh; align-items: start; }
.shell.focus { grid-template-columns: 1fr; }
.rail {
  position: sticky; top: 16px; display: flex; flex-direction: column; gap: 4px; height: calc(100dvh - 32px); box-sizing: border-box;
  margin: 16px 0 16px 16px; padding: 16px 10px; border-radius: 26px;
  background: var(--paper-2); box-shadow: var(--shadow);
}
.brand { display: flex; align-items: center; gap: 12px; padding: 4px 8px 16px; color: var(--ink); text-decoration: none !important; }
.mark {
  width: 42px; height: 42px; border-radius: 14px; background: var(--seal-fill); color: #fff; font-size: 26px;
  display: inline-flex; align-items: center; justify-content: center; transform: rotate(-8deg);
  box-shadow: 0 4px 0 0 color-mix(in srgb, var(--seal-fill) 70%, #000), inset 0 2px 0 rgba(255, 255, 255, .4);
  transition: transform .3s var(--ease-spring);
}
.brand:hover .mark { transform: rotate(4deg) scale(1.06); }
.bt { font-size: 16px; letter-spacing: -0.01em; font-weight: 600; }
.bt b { font-weight: 900; color: var(--primary-strong); }
.nav {
  display: flex; align-items: center; gap: 12px; padding: 9px 10px; border-radius: 18px; color: var(--ink-soft);
  text-decoration: none !important; font-weight: 800;
  transition: background .18s, color .18s, transform .2s var(--ease-spring), box-shadow .18s;
}
.nav:hover { background: var(--paper-3); color: var(--ink); transform: translateX(2px); }
.nav.active { background: var(--primary-soft); color: var(--ink); box-shadow: var(--shadow-sm); }
.nav .ic {
  width: 34px; height: 34px; display: inline-flex; align-items: center; justify-content: center; font-size: 20px;
  border-radius: 12px; color: var(--ink-soft); background: var(--paper-3);
  transition: background .18s, color .18s;
}
.nav.active .ic {
  color: #fff; background: var(--primary);
  box-shadow: 0 3px 0 0 var(--primary-edge), inset 0 2px 0 rgba(255, 255, 255, .35);
}
.theme-btn { border: 0; background: none; font: inherit; font-weight: 800; color: var(--ink-soft); cursor: pointer; text-align: left; width: 100%; }

/* nhóm cha – con */
.groups { flex: 1; min-height: 0; overflow-y: auto; overflow-x: hidden; display: flex; flex-direction: column; gap: 6px; margin: 0 -4px; padding: 0 4px; }
.grp-h {
  display: flex; align-items: center; justify-content: space-between; width: 100%; padding: 8px 10px 6px; border: 0; background: none;
  font: inherit; font-size: 11.5px; font-weight: 900; letter-spacing: .08em; text-transform: uppercase; color: var(--ink-faint); cursor: pointer; border-radius: 12px;
}
.grp-h:hover { color: var(--ink); background: var(--paper-3); }
.grp.current .grp-h { color: var(--primary-strong); cursor: default; }
.grp.current .grp-h:hover { background: none; }
.chev { transition: transform .25s var(--ease-spring); transform: rotate(-90deg); }
.grp.open .chev { transform: none; }
.grp.current .chev { opacity: .35; }
.grp-b { display: grid; grid-template-rows: 0fr; transition: grid-template-rows .28s ease; }
.grp.open .grp-b { grid-template-rows: 1fr; }
.grp-in { overflow: hidden; display: flex; flex-direction: column; gap: 2px; padding-left: 4px; margin-left: 6px; border-left: 2px solid var(--line); }
.grp.open .grp-in { overflow: visible; }
.grp-in .nav { padding: 7px 8px; gap: 10px; }
.sys { display: flex; flex-direction: column; gap: 2px; padding-top: 10px; margin-top: 8px; border-top: 2px dashed var(--line); }
.theme-btn .ic { background: var(--sun); color: #7c4a03; box-shadow: 0 3px 0 0 #d4a20b, inset 0 2px 0 rgba(255, 255, 255, .45); }
.theme-btn[aria-pressed='true'] .ic { background: #312e81; color: #fde047; box-shadow: 0 3px 0 0 #1e1b4b, inset 0 2px 0 rgba(255, 255, 255, .15); }
.main { min-width: 0; }
/* tên mục luôn một dòng để menu đều nhau */
.nav .lb { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.nav .lb-s { display: none; }

@media (max-width: 760px) {
  .shell { grid-template-columns: 1fr; }
  .rail {
    position: fixed; top: auto; bottom: 10px; left: 10px; right: 10px; height: auto; z-index: 50; margin: 0; overflow-x: auto;
    flex-direction: row; justify-content: space-around; padding: 6px 4px calc(6px + env(safe-area-inset-bottom));
    border-radius: 24px;
  }
  .brand { display: none; }
  .theme-btn { text-align: center; width: auto; }
  /* thanh dưới trên điện thoại: bỏ tiêu đề nhóm, trải phẳng các mục */
  .groups, .grp, .grp-in, .sys { display: contents; }
  .grp-h { display: none; }
  .grp-b { display: contents; }
  .theme-btn .lb { font-size: 0; }
  .theme-btn .lb::after { content: 'Sáng/Tối'; font-size: 11px; }
  .nav { flex-direction: column; gap: 2px; padding: 4px 6px; font-size: 11px; border-radius: 14px; }
  .nav:hover { transform: none; }
  .nav.active { box-shadow: none; background: transparent; }
  .nav .ic { width: 30px; height: 30px; font-size: 18px; }
  .nav:not(.theme-btn) .lb { display: none; }
  .nav .lb-s { display: block; white-space: nowrap; }
}
</style>

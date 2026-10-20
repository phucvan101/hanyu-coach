import { ref } from 'vue'

// Chế độ giao diện: 'light' | 'dark' | 'auto' (theo máy). Lưu trong trình duyệt, chỉ là tuỳ chọn hiển thị.
const KEY = 'hanyu-theme'
const mq = window.matchMedia('(prefers-color-scheme: dark)')

function read() {
  try { return localStorage.getItem(KEY) || 'auto' } catch { return 'auto' }
}

export const theme = ref(read())
export const isDark = ref(false)

function apply() {
  const el = document.documentElement
  if (theme.value === 'auto') el.removeAttribute('data-theme')
  else el.setAttribute('data-theme', theme.value)
  isDark.value = theme.value === 'dark' || (theme.value === 'auto' && mq.matches)
}

export function setTheme(t) {
  theme.value = t
  try { localStorage.setItem(KEY, t) } catch { /* chế độ riêng tư: chỉ áp dụng cho lần này */ }
  apply()
}

mq.addEventListener('change', apply)
apply()

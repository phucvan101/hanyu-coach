<template>
  <div class="ts" role="radiogroup" aria-label="Giao diện">
    <button v-for="o in opts" :key="o.v" type="button" role="radio" class="opt" :class="{ on: theme === o.v }"
      :aria-checked="theme === o.v" :title="o.title" @click="setTheme(o.v)">
      <svg viewBox="0 0 20 20" width="16" height="16" aria-hidden="true" v-html="o.icon"></svg>
      <span>{{ o.label }}</span>
    </button>
  </div>
</template>

<script setup>
import { theme, setTheme } from '../composables/useTheme'

const opts = [
  { v: 'light', label: 'Sáng', title: 'Giao diện sáng', icon: '<circle cx="10" cy="10" r="3.6" fill="currentColor"/><g stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><path d="M10 2.2v1.9M10 15.9v1.9M2.2 10h1.9M15.9 10h1.9M4.5 4.5l1.3 1.3M14.2 14.2l1.3 1.3M4.5 15.5l1.3-1.3M14.2 5.8l1.3-1.3"/></g>' },
  { v: 'dark', label: 'Tối', title: 'Giao diện tối', icon: '<path d="M16.5 12.6A7 7 0 0 1 7.4 3.5a7 7 0 1 0 9.1 9.1z" fill="currentColor"/>' },
  { v: 'auto', label: 'Tự động', title: 'Theo cài đặt của máy', icon: '<circle cx="10" cy="10" r="6.8" fill="none" stroke="currentColor" stroke-width="1.8"/><path d="M10 3.2a6.8 6.8 0 0 1 0 13.6z" fill="currentColor"/>' },
]
</script>

<style scoped>
.ts { display: grid; grid-template-columns: repeat(3, 1fr); gap: 4px; padding: 4px; border-radius: 16px; background: var(--paper-3); box-shadow: var(--shadow-in); }
.opt {
  display: flex; flex-direction: column; align-items: center; gap: 2px; padding: 6px 2px; min-height: 44px;
  border: 0; border-radius: 12px; background: transparent; color: var(--ink-soft); cursor: pointer;
  font-size: 11.5px; font-weight: 800; transition: background .18s, color .18s, transform .2s var(--ease-spring);
}
.opt:hover:not(.on) { color: var(--ink); }
.opt:active { transform: scale(.95); }
.opt.on { background: var(--paper-2); color: var(--primary-strong); box-shadow: var(--shadow-sm); }
</style>

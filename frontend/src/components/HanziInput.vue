<template>
  <div class="hi" :class="{ big }">
    <div class="box">
      <input
        ref="el"
        class="input"
        :class="{ han: hasHan }"
        :value="modelValue"
        :placeholder="placeholder"
        :disabled="disabled"
        autocomplete="off"
        autocapitalize="off"
        spellcheck="false"
        @input="onInput"
        @keydown="onKey"
        @compositionstart="composing = true"
        @compositionend="onCompEnd"
        @click="detect"
        @blur="onBlur"
      />
      <button
        v-if="showToggle"
        type="button"
        class="ime-toggle"
        :class="{ on: ime }"
        :title="ime ? 'Bộ gõ pinyin của app: BẬT (gõ pinyin → chọn chữ Hán)' : 'Bộ gõ của app: TẮT (gõ thẳng, dùng bộ gõ hệ điều hành hoặc gửi pinyin)'"
        @click="toggle"
      >
        <span class="han">拼</span>
      </button>
    </div>
    <div v-if="cands.length && buffer" class="cands" role="listbox" aria-label="Chọn chữ Hán">
      <span class="buf">{{ buffer }}</span>
      <button
        v-for="(c, i) in cands.slice(0, 9)"
        :key="c.word + i"
        type="button"
        class="cand"
        :class="{ known: c.known }"
        role="option"
        @mousedown.prevent="choose(c)"
      >
        <small>{{ i + 1 }}</small><span class="han">{{ c.word }}</span>
      </button>
      <span class="hint tiny faint">Space chọn số 1 · Enter giữ chữ cái</span>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, ref, watch } from 'vue'

const props = defineProps({
  modelValue: { type: String, default: '' },
  placeholder: { type: String, default: '' },
  imeDefault: { type: Boolean, default: true },
  showToggle: { type: Boolean, default: true },
  disabled: Boolean,
  big: Boolean,
})
const emit = defineEmits(['update:modelValue', 'submit', 'ime-change'])

const el = ref(null)
const ime = ref(props.imeDefault)
const composing = ref(false)
const buffer = ref('')
const bufStart = ref(0)
const cands = ref([])
let reqId = 0
let timer = null

const hasHan = computed(() => /[㐀-鿿]/.test(props.modelValue))
watch(ime, (v) => emit('ime-change', v), { immediate: true })

function toggle() {
  ime.value = !ime.value
  cands.value = []
  buffer.value = ''
  el.value?.focus()
}

function onCompEnd(e) {
  composing.value = false
  onInput(e)
}

function onInput(e) {
  if (composing.value) return
  emit('update:modelValue', e.target.value)
  detect()
}

function detect() {
  const input = el.value
  if (!ime.value || !input) { buffer.value = ''; cands.value = []; return }
  const pos = input.selectionStart ?? input.value.length
  const m = input.value.slice(0, pos).match(/[a-zA-Züv]+$/)
  if (!m) { buffer.value = ''; cands.value = []; return }
  buffer.value = m[0].toLowerCase()
  bufStart.value = pos - m[0].length
  clearTimeout(timer)
  const q = buffer.value
  timer = setTimeout(async () => {
    const id = ++reqId
    try {
      const r = await fetch('/api/ime?q=' + encodeURIComponent(q))
      const data = await r.json()
      if (id === reqId && buffer.value === q) cands.value = data
    } catch { /* ignore */ }
  }, 60)
}

async function choose(c) {
  const input = el.value
  const v = input.value
  const consume = Math.min(c.consume || buffer.value.length, buffer.value.length)
  const rest = buffer.value.slice(consume)
  const nv = v.slice(0, bufStart.value) + c.word + v.slice(bufStart.value + consume)
  emit('update:modelValue', nv)
  cands.value = []
  await nextTick()
  input.value = nv
  const caret = bufStart.value + c.word.length + rest.length
  input.setSelectionRange(caret, caret)
  input.focus()
  detect()
}

function onKey(e) {
  if (e.isComposing || composing.value) return
  const open = cands.value.length && buffer.value
  if (open) {
    if (e.key === ' ') { e.preventDefault(); choose(cands.value[0]); return }
    if (/^[1-9]$/.test(e.key) && cands.value[Number(e.key) - 1]) { e.preventDefault(); choose(cands.value[Number(e.key) - 1]); return }
    if (e.key === 'Escape' || e.key === 'Enter') { e.preventDefault(); cands.value = []; buffer.value = ''; return }
  }
  if (e.key === 'Enter') { e.preventDefault(); emit('submit') }
}

function onBlur() {
  setTimeout(() => { cands.value = [] }, 150)
}

function focus() { el.value?.focus() }
defineExpose({ focus, ime })
</script>

<style scoped>
.hi { position: relative; width: 100%; }
.box { position: relative; }
.input { padding-right: 50px; font-size: 16px; }
.input.han { font-family: var(--font-ui), var(--font-han); }
.big .input { font-size: 20px; padding: 15px 56px 15px 18px; border-radius: 18px; }
.ime-toggle {
  position: absolute; right: 7px; top: 50%; transform: translateY(-50%);
  width: 36px; height: 32px; border-radius: 11px; border: 0; background: var(--paper-2);
  color: var(--ink-faint); cursor: pointer; font-size: 17px; line-height: 1;
  box-shadow: var(--shadow-sm); transition: background .18s, color .18s, transform .2s var(--ease-spring);
}
.ime-toggle:active { transform: translateY(-50%) scale(.92); }
.ime-toggle.on {
  background: var(--jade-fill); color: #fff;
  box-shadow: 0 3px 0 0 var(--jade-edge), inset 0 2px 0 rgba(255, 255, 255, .35);
}
.cands {
  position: absolute; left: 0; right: 0; top: calc(100% + 8px); z-index: 20;
  display: flex; flex-wrap: wrap; align-items: center; gap: 4px; padding: 8px;
  background: var(--paper-2); border: 0; border-radius: 18px; box-shadow: var(--shadow);
}
.buf { font-size: 13px; color: var(--ink-faint); padding: 0 8px; border-right: 2px solid var(--line); margin-right: 2px; font-weight: 700; }
.cand {
  display: inline-flex; align-items: baseline; gap: 4px; border: 0; background: transparent; cursor: pointer;
  padding: 5px 10px; border-radius: 12px; font-size: 20px; transition: background .15s, transform .2s var(--ease-spring);
}
.cand:hover { transform: translateY(-1px); }
.cand small { font-size: 11px; color: var(--ink-faint); font-weight: 700; }
.cand:hover, .cand:first-of-type { background: var(--primary-soft); }
.cand.known .han { color: var(--jade); }
.hint { margin-left: auto; }
@media (max-width: 620px) { .hint { display: none; } }
</style>

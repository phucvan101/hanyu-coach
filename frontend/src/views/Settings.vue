<template>
  <div class="page">
    <header class="ph">
      <h1>Cài đặt</h1>
      <p class="muted small">Key AI, giọng đọc và cách hiển thị hội thoại. Bấm <b>Lưu cài đặt</b> ở cột bên phải sau khi sửa.</p>
    </header>
    <div v-if="!s" class="empty">Đang tải…</div>
    <form v-else class="set" @submit.prevent="save">
      <div class="col-main">
        <!-- Gemini -->
        <section id="gemini" class="card stack">
          <div class="row spread sh">
            <div class="row ht"><span class="ico blue" aria-hidden="true">✦</span><h2>AI chính: Google Gemini</h2></div>
            <span class="chip" :class="s.has_gemini_api_key ? 'jade' : 'gold'">{{ s.has_gemini_api_key ? 'Đã có key' : 'Chưa có key' }}</span>
          </div>
          <p class="small muted">Miễn phí. Lấy key tại <a href="https://aistudio.google.com/apikey" target="_blank" rel="noopener">aistudio.google.com/apikey</a> (đăng nhập Google → Create API key → dán vào đây). Gemini còn dùng để nhận dạng giọng nói.</p>
          <div class="fields">
            <label><span class="label">Gemini API key</span><input v-model="f.gemini_api_key" class="input" type="password" autocomplete="off" :placeholder="s.gemini_api_key || 'AIza…'" /></label>
            <label>
              <span class="label">Model</span>
              <div class="row">
                <input v-model="f.gemini_model" class="input" list="gm" />
                <datalist id="gm"><option v-for="m in models" :key="m" :value="m" /></datalist>
                <button class="btn" type="button" :disabled="!s.has_gemini_api_key" @click="loadModels">Lấy danh sách</button>
              </div>
            </label>
          </div>
          <span class="tiny faint">Nên dùng bản "flash" (nhanh, có hạn mức miễn phí). Bản "pro" thường phải trả phí.</span>
          <div class="row wrap">
            <button class="btn" type="button" @click="test('gemini')">Kiểm tra kết nối</button>
            <span v-if="tests.gemini" class="small res" :class="tests.gemini.ok ? 'ok' : 'bad'">{{ tests.gemini.message }}</span>
          </div>
        </section>

        <!-- dự phòng -->
        <section id="backup" class="card stack">
          <div class="row spread sh">
            <div class="row ht"><span class="ico orange" aria-hidden="true">⇄</span><h2>AI dự phòng</h2></div>
            <span class="chip" :class="s.has_openai_api_key ? 'jade' : ''">{{ s.has_openai_api_key ? 'Đã có key' : 'Tuỳ chọn' }}</span>
          </div>
          <p class="small muted">Dùng khi Gemini hết hạn mức. Khuyên dùng <b>GLM-4.7-Flash</b> (miễn phí, model Trung Quốc nên tiếng Trung rất tự nhiên): đăng ký tại <a href="https://open.bigmodel.cn" target="_blank" rel="noopener">open.bigmodel.cn</a> hoặc <a href="https://z.ai" target="_blank" rel="noopener">z.ai</a>. Mọi dịch vụ tương thích OpenAI (OpenRouter, Groq…) đều dùng được.</p>
          <div>
            <span class="label">Điền nhanh</span>
            <div class="row wrap presets">
              <button v-for="p in presets" :key="p.label" type="button" class="btn small" :class="{ on: f.openai_base_url === p.openai_base_url }" @click="applyPreset(p)">{{ p.label }}</button>
            </div>
          </div>
          <div class="fields">
            <label><span class="label">Base URL</span><input v-model="f.openai_base_url" class="input" /></label>
            <label><span class="label">Model</span><input v-model="f.openai_model" class="input" /></label>
            <label><span class="label">API key</span><input v-model="f.openai_api_key" class="input" type="password" autocomplete="off" :placeholder="s.openai_api_key || 'Dán key…'" /></label>
            <label>
              <span class="label">Thứ tự dùng</span>
              <select v-model="f.llm_order" class="select">
                <option v-for="(t, v) in orderLabel" :key="v" :value="v">{{ t }}</option>
              </select>
            </label>
          </div>
          <div class="row wrap">
            <button class="btn" type="button" @click="test('openai')">Kiểm tra kết nối</button>
            <span v-if="tests.openai" class="small res" :class="tests.openai.ok ? 'ok' : 'bad'">{{ tests.openai.message }}</span>
          </div>
        </section>

        <div class="pair">
          <!-- giọng đọc -->
          <section id="voice" class="card stack">
            <div class="row ht"><span class="ico green" aria-hidden="true">♪</span><h2>Giọng đọc</h2></div>
            <label>
              <span class="label">Nguồn giọng</span>
              <select v-model="f.tts_source" class="select">
                <option value="auto">Tự động: Microsoft online → giọng của máy</option>
                <option value="server">Chỉ giọng Microsoft online</option>
                <option value="browser">Chỉ giọng có sẵn trên máy (không cần mạng)</option>
              </select>
            </label>
            <label>
              <span class="label">Giọng (Microsoft)</span>
              <select v-model="f.tts_voice" class="select">
                <option :value="MIX_VOICE">🔀 Trộn nhiều giọng — mỗi câu một giọng ngẫu nhiên</option>
                <optgroup v-for="g in VOICE_GROUPS" :key="g.label" :label="g.label">
                  <option v-for="v in g.voices" :key="v.id" :value="v.id">{{ v.name }}</option>
                </optgroup>
              </select>
            </label>
            <label>
              <span class="label">Tốc độ: {{ f.tts_rate }}%</span>
              <input v-model="f.tts_rate" type="range" min="-50" max="20" step="5" class="range" />
            </label>
            <div class="row wrap">
              <button class="btn" type="button" @click="tryVoice">▶ Nghe thử</button>
              <span v-if="voiceErr" class="small res bad">{{ voiceErr }}</span>
            </div>
          </section>

          <!-- hiển thị -->
          <section id="chat" class="card stack">
            <div class="row ht"><span class="ico pink" aria-hidden="true">话</span><h2>Hội thoại</h2></div>
            <label class="toggle">
              <input v-model="showPy" type="checkbox" />
              <span><b>Hiện pinyin</b><span class="tiny muted">Pinyin hiện dưới câu của AI.</span></span>
            </label>
            <label class="toggle">
              <input v-model="showVi" type="checkbox" />
              <span><b>Hiện nghĩa tiếng Việt sẵn</b><span class="tiny muted">Mặc định ẩn, bấm vào câu để xem.</span></span>
            </label>
          </section>
        </div>
      </div>

      <aside class="side">
        <section class="card stack savecard">
          <h3>Trạng thái</h3>
          <ul class="status">
            <li><span>Gemini</span><span class="chip" :class="s.has_gemini_api_key ? 'jade' : 'gold'">{{ s.has_gemini_api_key ? 'Sẵn sàng' : 'Chưa có key' }}</span></li>
            <li><span>AI dự phòng</span><span class="chip" :class="s.has_openai_api_key ? 'jade' : ''">{{ s.has_openai_api_key ? 'Sẵn sàng' : 'Chưa dùng' }}</span></li>
            <li><span>Thứ tự</span><span class="small muted">{{ orderLabel[f.llm_order] || f.llm_order }}</span></li>
          </ul>
          <button class="btn primary lg" :disabled="saving">{{ saving ? 'Đang lưu…' : 'Lưu cài đặt' }}</button>
          <span v-if="savedMsg" class="small res ok" role="status">{{ savedMsg }}</span>
        </section>

        <section class="card stack">
          <h3>Giao diện</h3>
          <ThemeSwitch />
          <p class="tiny muted">"Tự động" đổi theo chế độ sáng/tối của máy. Lựa chọn được nhớ trên trình duyệt này.</p>
        </section>

        <section class="card stack data">
          <h3>Dữ liệu</h3>
          <p class="small muted">Toàn bộ dữ liệu nằm trong thư mục <code>data</code> cạnh file khởi động. Sao lưu = copy thư mục đó, hoặc tải bản JSON.</p>
          <a class="btn" href="/api/export">Tải bản sao lưu (JSON)</a>
        </section>
      </aside>
    </form>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { api } from '../api'
import { loadSettings, settings } from '../composables/useSettings'
import { speak } from '../composables/useTts'
import { MIX_VOICE, VOICE_GROUPS } from '../composables/ttsVoices'
import ThemeSwitch from '../components/ThemeSwitch.vue'

const s = ref(null)
const f = reactive({})
const models = ref([])
const tests = reactive({})
const saving = ref(false)
const savedMsg = ref('')
const voiceErr = ref('')
const showPy = ref(true)
const showVi = ref(false)
const orderLabel = { 'gemini,openai': 'Gemini trước, dự phòng sau', 'openai,gemini': 'Dự phòng trước, Gemini sau', gemini: 'Chỉ Gemini', openai: 'Chỉ AI dự phòng' }
const presets = [
  { label: 'GLM (open.bigmodel.cn)', openai_base_url: 'https://open.bigmodel.cn/api/paas/v4', openai_model: 'glm-4.7-flash' },
  { label: 'GLM (api.z.ai)', openai_base_url: 'https://api.z.ai/api/paas/v4', openai_model: 'glm-4.7-flash' },
  { label: 'OpenRouter', openai_base_url: 'https://openrouter.ai/api/v1', openai_model: '' },
  { label: 'Groq', openai_base_url: 'https://api.groq.com/openai/v1', openai_model: 'openai/gpt-oss-120b' },
]

function fill(x) {
  s.value = x
  Object.assign(f, {
    gemini_api_key: '', openai_api_key: '',
    gemini_model: x.gemini_model, openai_base_url: x.openai_base_url, openai_model: x.openai_model, llm_order: x.llm_order,
    tts_source: x.tts_source, tts_voice: x.tts_voice, tts_rate: Number(x.tts_rate),
  })
  showPy.value = x.show_pinyin !== '0'
  showVi.value = x.show_vi === '1'
}

function applyPreset(p) { f.openai_base_url = p.openai_base_url; f.openai_model = p.openai_model }

async function save() {
  saving.value = true
  savedMsg.value = ''
  try {
    const body = { ...f, show_pinyin: showPy.value ? '1' : '0', show_vi: showVi.value ? '1' : '0' }
    if (!body.gemini_api_key) delete body.gemini_api_key
    if (!body.openai_api_key) delete body.openai_api_key
    fill(await api.put('/api/settings', body))
    await loadSettings(true)
    savedMsg.value = 'Đã lưu.'
  } finally {
    saving.value = false
  }
}

async function test(provider) {
  await save()
  tests[provider] = { ok: true, message: 'Đang kiểm tra…' }
  tests[provider] = await api.post('/api/settings/test', { provider })
}

async function loadModels() {
  try { models.value = await api.get('/api/settings/gemini-models') } catch (e) { tests.gemini = { ok: false, message: e.message } }
}

async function tryVoice() {
  voiceErr.value = ''
  Object.assign(settings, { tts_source: f.tts_source, tts_rate: String(f.tts_rate), tts_voice: f.tts_voice })
  await save()
  try { await speak('你好！欢迎你来学习汉语。') } catch (e) { voiceErr.value = 'Không phát được giọng online — thử chọn "giọng có sẵn trên máy".' }
}

onMounted(async () => fill(await api.get('/api/settings')))
</script>

<style scoped>
.ph { margin-bottom: 20px; }
.ph p { margin-top: 4px; max-width: 62ch; }

.set { display: grid; grid-template-columns: minmax(0, 1fr) 320px; gap: 20px; align-items: start; }
.col-main { display: flex; flex-direction: column; gap: 16px; min-width: 0; }
.pair { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; align-items: stretch; }
.side { display: flex; flex-direction: column; gap: 16px; position: sticky; top: 16px; }

.stack > label { display: block; }
.sh { align-items: center; }
.ht { gap: 10px; }
.ico {
  width: 34px; height: 34px; border-radius: 12px; flex: none; color: #fff; font-size: 16px; font-weight: 900;
  display: inline-flex; align-items: center; justify-content: center; background: var(--c);
  box-shadow: 0 3px 0 0 color-mix(in srgb, var(--c) 68%, #000), inset 0 2px 0 rgba(255, 255, 255, .35);
}
.ico.blue { --c: var(--primary); }
.ico.orange { --c: var(--gold-fill); }
.ico.green { --c: var(--jade-fill); }
.ico.pink { --c: var(--seal-fill); font-family: var(--font-han); font-weight: 400; font-size: 18px; }

.fields { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px 16px; }
.fields > label { display: block; min-width: 0; }
.presets { gap: 8px; }
.btn.small { padding: 7px 13px; font-size: 13px; border-radius: 13px; min-height: 36px; }
.btn.small.on { background: var(--primary-soft); color: var(--primary-strong); }
.range { width: 100%; }
.res { font-weight: 700; }
.res.ok { color: var(--jade); }
.res.bad { color: var(--seal); }

.toggle {
  display: flex !important; gap: 12px; align-items: flex-start; padding: 12px 14px; border-radius: 16px; cursor: pointer;
  background: var(--paper-3); box-shadow: var(--shadow-in);
}
.toggle input { width: 18px; height: 18px; margin-top: 2px; flex: none; }
.toggle > span { display: flex; flex-direction: column; gap: 2px; }

.status { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 10px; }
.status li { display: flex; justify-content: space-between; align-items: center; gap: 10px; font-weight: 700; }
.status li .small { text-align: right; }
.savecard .btn { width: 100%; }
.data .btn { align-self: flex-start; }
code { background: var(--paper-3); padding: 2px 7px; border-radius: 7px; font-weight: 700; }

@media (max-width: 1100px) { .pair { grid-template-columns: 1fr; } }
@media (max-width: 900px) {
  .set { grid-template-columns: 1fr; }
  /* cột phải tan vào lưới để thẻ Lưu dính đáy màn hình suốt khi cuộn form */
  .side { display: contents; }
  .savecard { position: sticky; bottom: 92px; z-index: 5; order: 2; padding: 10px; gap: 6px; }
  .savecard h3, .savecard .status { display: none; }
  .savecard .res { text-align: center; }
  .data { order: 1; }
}
@media (max-width: 620px) { .fields { grid-template-columns: 1fr; } }
</style>

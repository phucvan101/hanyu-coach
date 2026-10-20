<template>
  <div class="page">
    <div class="row spread wrap" style="margin-bottom: 18px">
      <h1>Thư viện</h1>
    </div>

    <section class="card up" :class="{ drag }" @dragover.prevent="drag = true" @dragleave="drag = false" @drop.prevent="onDrop">
      <div class="stack" style="gap: 6px">
        <h2>Nhập quyển từ vựng mới</h2>
        <p class="muted small">File CSV xuất từ Hanzii, mỗi dòng: <code>Hán tự;pinyin;Hán Việt;nghĩa</code>. Mỗi file là một quyển bạn đã học xong. AI sẽ chuẩn hoá nghĩa và chia bài theo chủ đề (khoảng 1–2 phút).</p>
      </div>
      <form class="row wrap upf" @submit.prevent="upload">
        <input v-model="title" class="input" placeholder="Tên quyển (VD: Hán ngữ quyển 1)" style="max-width: 280px" />
        <label class="btn">
          <input ref="fileEl" type="file" accept=".csv,.txt,.tsv" hidden @change="pick" />
          {{ file ? file.name : 'Chọn file CSV' }}
        </label>
        <button class="btn primary" :disabled="!file || uploading">{{ uploading ? 'Đang tải lên…' : 'Nhập' }}</button>
      </form>
      <p v-if="msg" class="notice" :class="msgErr ? 'err' : 'ok'">{{ msg }}</p>
    </section>

    <div v-if="!books.length && !loading" class="empty">Chưa có quyển nào.</div>

    <section class="stack" style="margin-top: 22px">
      <article v-for="b in books" :key="b.id" class="card book">
        <div class="row spread wrap">
          <div>
            <h2><RouterLink :to="`/library/${b.id}`">{{ b.title }}</RouterLink></h2>
            <p class="small muted">{{ b.word_count }} từ · {{ b.unit_count }} bài · {{ b.grammar_count }} điểm ngữ pháp · {{ b.source_file }}</p>
          </div>
          <span class="chip" :class="{ gold: b.status === 'importing', seal: b.status === 'error', jade: b.status === 'ready' }">
            {{ b.status === 'ready' ? (b.grouped_by === 'llm' ? 'Đã chia bài bằng AI' : 'Chia theo thứ tự') : b.status === 'importing' ? 'Đang xử lý' : 'Lỗi' }}
          </span>
        </div>
        <p v-if="b.status_msg && b.status !== 'ready'" class="small" style="margin-top: 8px">{{ b.status_msg }}</p>
        <p v-else-if="b.status_msg && b.status_msg !== 'Sẵn sàng.'" class="small muted" style="margin-top: 8px">{{ b.status_msg }}</p>

        <div class="mats">
          <p class="small"><b>Tài liệu ngữ pháp / bài khoá</b> <span class="muted">— AI rút ra mẫu câu để hội thoại bám theo bài học (.txt, .md, .pdf, .docx)</span></p>
          <ul v-if="b.materials.length">
            <li v-for="m in b.materials" :key="m.id" class="row small">
              <span>{{ m.filename }}</span>
              <span class="chip" :class="{ gold: m.status === 'processing', seal: m.status === 'error', jade: m.status === 'ready' }">{{ m.status_msg || 'Đang đọc…' }}</span>
              <button class="btn ghost small" @click="delMat(m.id)">Xoá</button>
            </li>
          </ul>
          <label class="btn small" style="margin-top: 8px">
            <input type="file" accept=".txt,.md,.pdf,.docx" hidden @change="(e) => uploadMat(b.id, e)" />
            + Thêm tài liệu
          </label>
        </div>

        <div class="row wrap acts">
          <RouterLink :to="`/library/${b.id}`" class="btn">Xem & sửa bài</RouterLink>
          <button class="btn" :disabled="b.status === 'importing'" @click="regroup(b.id)">Chia lại bài bằng AI</button>
          <button class="btn danger" @click="del(b)">{{ confirmDel === b.id ? 'Bấm lần nữa để xoá' : 'Xoá quyển' }}</button>
        </div>
      </article>
    </section>
  </div>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { api } from '../api'

const books = ref([])
const loading = ref(true)
const file = ref(null)
const fileEl = ref(null)
const title = ref('')
const uploading = ref(false)
const msg = ref('')
const msgErr = ref(false)
const drag = ref(false)
const confirmDel = ref(null)
let poll = null

async function load() {
  try { books.value = await api.get('/api/books') } finally { loading.value = false }
  clearTimeout(poll)
  if (books.value.some((b) => b.status === 'importing' || b.materials.some((m) => m.status === 'processing'))) poll = setTimeout(load, 2000)
}
function pick(e) { file.value = e.target.files[0] || null }
function onDrop(e) { drag.value = false; file.value = e.dataTransfer.files[0] || null }

async function upload() {
  uploading.value = true
  msg.value = ''
  try {
    const fd = new FormData()
    fd.append('file', file.value)
    fd.append('title', title.value)
    const r = await api.upload('/api/books/import', fd)
    msg.value = `Đã nhận ${r.word_count} từ. AI đang xử lý — bạn có thể sang trang Học khi trạng thái là "Đã chia bài".`
    msgErr.value = false
    file.value = null
    title.value = ''
    if (fileEl.value) fileEl.value.value = ''
    load()
  } catch (e) {
    msg.value = e.message
    msgErr.value = true
  } finally {
    uploading.value = false
  }
}

async function uploadMat(bookId, e) {
  const f = e.target.files[0]
  if (!f) return
  const fd = new FormData()
  fd.append('file', f)
  try { await api.upload(`/api/books/${bookId}/materials`, fd); load() } catch (err) { msg.value = err.message; msgErr.value = true }
  e.target.value = ''
}
async function delMat(id) { await api.del(`/api/materials/${id}`); load() }
async function regroup(id) { await api.post(`/api/books/${id}/regroup`); load() }
async function del(b) {
  if (confirmDel.value !== b.id) { confirmDel.value = b.id; setTimeout(() => (confirmDel.value = null), 4000); return }
  await api.del(`/api/books/${b.id}`)
  confirmDel.value = null
  load()
}

onMounted(load)
onBeforeUnmount(() => clearTimeout(poll))
</script>

<style scoped>
.up {
  display: flex; flex-direction: column; gap: 14px;
  border: 3px dashed var(--line); background: color-mix(in srgb, var(--paper-2) 70%, transparent); box-shadow: none;
  transition: border-color .2s, background .2s, transform .25s var(--ease-spring);
}
.up.drag { border-color: var(--primary); background: var(--primary-soft); transform: scale(1.01); }
.upf { gap: 10px; }
code { background: var(--paper-3); padding: 2px 7px; border-radius: 7px; font-size: 13px; font-weight: 700; }
.book { transition: transform .25s var(--ease-spring); }
.book:hover { transform: translateY(-2px); }
.book h2 a { color: var(--ink); }
.mats { margin-top: 16px; padding-top: 14px; border-top: 2px dashed var(--line); }
.mats ul { list-style: none; padding: 0; margin: 8px 0 0; display: flex; flex-direction: column; gap: 6px; }
.acts { margin-top: 16px; gap: 10px; }
.btn.small { padding: 6px 13px; font-size: 13px; border-radius: 13px; }
</style>

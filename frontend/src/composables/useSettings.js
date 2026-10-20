import { reactive } from 'vue'
import { api } from '../api'

export const settings = reactive({ loaded: false, tts_source: 'auto', tts_rate: '-10', tts_voice: 'zh-CN-XiaoxiaoNeural', show_pinyin: '1', show_vi: '0' })

export async function loadSettings(force = false) {
  if (settings.loaded && !force) return settings
  try {
    const s = await api.get('/api/settings')
    Object.assign(settings, s, { loaded: true })
  } catch (e) {
    /* backend chưa sẵn sàng */
  }
  return settings
}

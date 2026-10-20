// Giọng Microsoft (edge-tts). `mix: true` = được dùng trong chế độ "trộn giọng".
export const VOICE_GROUPS = [
  {
    label: 'Phổ thông – Đại lục',
    voices: [
      { id: 'zh-CN-XiaoxiaoNeural', name: 'Xiaoxiao — nữ, ấm (bản tin, kể chuyện)', mix: true },
      { id: 'zh-CN-XiaoyiNeural', name: 'Xiaoyi — nữ, trẻ, sôi nổi', mix: true },
      { id: 'zh-CN-YunxiNeural', name: 'Yunxi — nam, trẻ, tươi sáng', mix: true },
      { id: 'zh-CN-YunjianNeural', name: 'Yunjian — nam, trầm, mạnh mẽ', mix: true },
      { id: 'zh-CN-YunyangNeural', name: 'Yunyang — nam, phát thanh viên', mix: true },
      { id: 'zh-CN-YunxiaNeural', name: 'Yunxia — bé trai', mix: true },
    ],
  },
  {
    label: 'Phổ thông – Đài Loan',
    voices: [
      { id: 'zh-TW-HsiaoChenNeural', name: 'HsiaoChen — nữ, thân thiện', mix: true },
      { id: 'zh-TW-HsiaoYuNeural', name: 'HsiaoYu — nữ, nhẹ nhàng', mix: true },
      { id: 'zh-TW-YunJheNeural', name: 'YunJhe — nam, thân thiện', mix: true },
    ],
  },
  {
    label: 'Giọng địa phương (nâng cao)',
    voices: [
      { id: 'zh-CN-liaoning-XiaobeiNeural', name: 'Xiaobei — nữ, giọng Đông Bắc (Liêu Ninh)' },
      { id: 'zh-CN-shaanxi-XiaoniNeural', name: 'Xiaoni — nữ, giọng Thiểm Tây' },
    ],
  },
]

export const MIX_VOICE = 'mix'
export const MIX_POOL = VOICE_GROUPS.flatMap((g) => g.voices).filter((v) => v.mix).map((v) => v.id)

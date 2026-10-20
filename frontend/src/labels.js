export const ERROR_TYPES = {
  ngu_phap: 'Ngữ pháp', tu_vung: 'Từ vựng', trat_tu: 'Trật tự từ', luong_tu: 'Lượng từ', tro_tu: 'Trợ từ',
  chinh_ta: 'Chính tả', khong_phu_hop: 'Không hợp ngữ cảnh', khong_dung_tieng_trung: 'Chưa dùng tiếng Trung', khac: 'Khác',
}
export const errorTypeLabel = (t) => ERROR_TYPES[t] || t

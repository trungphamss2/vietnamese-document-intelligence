# SEMANTIC SEARCH EVALUATION REPORT (MILESTONE 03)

**Model:** `BAAI/bge-m3` (Dense, Dimension: 1024)  
**Vector Store:** Qdrant (Collection: `vietnamese_documents`, Metric: Cosine)  
**Date:** 2026-11-23 01:09:04

---

## 1. Executive Summary

| Metric | Result | Target | Status |
|---|---|---|---|
| **Top-1 Retrieval Accuracy** | **75.0%** | ≥ 80.0% | FAIL |
| **Top-3 Retrieval Accuracy** | **100.0%** | ≥ 95.0% | PASS |
| **Average Top-1 Similarity Score** | **0.6183** | ≥ 0.60 | PASS |
| **Average Search Latency** | **56.7 ms** | ≤ 200 ms | PASS |

---

## 2. Detailed Query Evaluation

| ID | Category | Natural Language Query | Top-1 Matched Document | Top-1 Score | Top-1 Match | Top-3 Match | Latency (ms) |
|---|---|---|---|---|---|---|---|
| Q01 | Legal/Contract | Điều khoản hiệu lực hợp đồng và bảo mật thông tin dịch vụ CNTT | `pdf_text_01_hop_dong_dich_vu_cntt.pdf` | 0.6289 | ✅ PASS | ✅ PASS | 250.66 |
| Q02 | Finance/Invoice | Tổng tiền thanh toán trên hoá đơn giá trị gia tăng VAT | `pdf_scan_01_hoa_don_vat.pdf` | 0.6535 | ✅ PASS | ✅ PASS | 24.47 |
| Q03 | Policy/HR | Quy chế làm việc và văn hóa ứng xử nội bộ doanh nghiệp | `docx_01_quy_che_noi_bo_doanh_nghiep.docx` | 0.6034 | ✅ PASS | ✅ PASS | 21.95 |
| Q04 | Finance/Accounting | Báo cáo tài chính doanh thu thuần và lợi nhuận gộp sau thuế | `pdf_scan_01_hoa_don_vat.pdf` | 0.5710 | ❌ FAIL | ✅ PASS | 32.84 |
| Q05 | Operations/Quality | Biên bản nghiệm thu và bàn giao sản phẩm nền tảng Document Intelligence | `pdf_scan_02_bien_ban_nghiem_thu.pdf` | 0.6336 | ✅ PASS | ✅ PASS | 29.8 |
| Q06 | Cloud/Pricing | Bảng báo giá dịch vụ hạ tầng đám mây Cloud Server và hạn mức API | `pdf_complex_01_bang_gia_dich_vu_cloud.pdf` | 0.6440 | ✅ PASS | ✅ PASS | 54.29 |
| Q07 | AI Proposal | Đề xuất dự án phát triển hệ thống RAG và kiến trúc kỹ thuật AI | `docx_02_de_xuat_du_an_rag.docx` | 0.6353 | ✅ PASS | ✅ PASS | 19.87 |
| Q08 | Budget/Planning | Dự toán ngân sách và bảng kế hoạch chi phí hoạt động các phòng ban năm 2026 | `docx_02_de_xuat_du_an_rag.docx` | 0.5769 | ❌ FAIL | ✅ PASS | 19.94 |

---

## 3. Query Results Breakdown & Retrieved Snippets

### Q01 - Điều khoản hiệu lực hợp đồng và bảo mật thông tin dịch vụ CNTT

- **Category:** Legal/Contract
- **Expected Domain Keyword:** `hop_dong_dich_vu_cntt`
- **Retrieval Latency:** 250.66 ms

| Rank | Score | Source File | Page | Type | Content Snippet |
|---|---|---|---|---|---|
| 1 🎯 | 0.6289 | `pdf_text_01_hop_dong_dich_vu_cntt.pdf` | 3 | paragraph | 6.2 Không bên nào được phép cung cấp dữ liệu huấn luyện hoặc kết quả trích xuất cho bất kỳ bên thứ ba nào. ĐIỀU 7: HIỆU ... |
| 2 📄 | 0.5979 | `pdf_complex_01_bang_gia_dich_vu_cloud.pdf` | 2 | paragraph | Điều khoản kỹ thuật và bảo mật: ­ Tất cả dữ liệu tài liệu truyền tải qua API được mã hóa đầu cuối bằng chuẩn TLS 1.3. ­ ... |
| 3 📄 | 0.5598 | `pdf_complex_01_bang_gia_dich_vu_cloud.pdf` | 2 | paragraph | CHÍNH SÁCH CHIẾT KHẤU VÀ ĐIỀU KHOẢN HỖ TRỢ KỸ THUẬT 1. Chính sách ưu đãi cam kết dài hạn: ­ Khách hàng ký hợp đồng 06 th... |

### Q02 - Tổng tiền thanh toán trên hoá đơn giá trị gia tăng VAT

- **Category:** Finance/Invoice
- **Expected Domain Keyword:** `hoa_don_vat`
- **Retrieval Latency:** 24.47 ms

| Rank | Score | Source File | Page | Type | Content Snippet |
|---|---|---|---|---|---|
| 1 🎯 | 0.6535 | `pdf_scan_01_hoa_don_vat.pdf` | 1 | table | Bảng (Dữ liệu): \| STT \| Tên hàng hóa, dich vu \| DVT \| SL \| Đon giá \| Thành tin \| \| --- \| --- \| --- \| --- \| --- \| --- \| \|... |
| 2 📄 | 0.5822 | `pdf_text_01_hop_dong_dich_vu_cntt.pdf` | 2 | paragraph | Giá đã bao gồm thuế GTGT 10%. 3.2 Lộ trình thanh toán được chia làm 03 đợt: ­ Đợt 1: Tạm ứng 30% giá trị hợp đồng tương ... |
| 3 📄 | 0.5762 | `pdf_text_01_hop_dong_dich_vu_cntt.pdf` | 2 | paragraph | ­ Tài liệu DOCX: Bảo toàn thứ tự tuần tự giữa các đoạn văn bản (paragraphs) và cấu trúc bảng (tables). ­ Tài liệu XLSX: ... |

### Q03 - Quy chế làm việc và văn hóa ứng xử nội bộ doanh nghiệp

- **Category:** Policy/HR
- **Expected Domain Keyword:** `quy_che_noi_bo`
- **Retrieval Latency:** 21.95 ms

| Rank | Score | Source File | Page | Type | Content Snippet |
|---|---|---|---|---|---|
| 1 🎯 | 0.6034 | `docx_01_quy_che_noi_bo_doanh_nghiep.docx` | - | paragraph | Điều 1. Phạm vi điều chỉnh và đối tượng áp dụng: Quy chế này quy định về thời giờ làm việc, thời giờ nghỉ ngơi, văn hóa ... |
| 2 🎯 | 0.5936 | `docx_01_quy_che_noi_bo_doanh_nghiep.docx` | - | paragraph | CHƯƠNG I: QUY ĐỊNH CHUNG VỀ CHẾ ĐỘ LÀM VIỆC VÀ NỀ NẾP |
| 3 🎯 | 0.5539 | `docx_01_quy_che_noi_bo_doanh_nghiep.docx` | - | paragraph | [TÀI LIỆU QUY CHẾ NỘI BỘ GIẢ LẬP PHỤC VỤ THỬ NGHIỆM HỆ THỐNG TRÍCH XUẤT VĂN BẢN] |

### Q04 - Báo cáo tài chính doanh thu thuần và lợi nhuận gộp sau thuế

- **Category:** Finance/Accounting
- **Expected Domain Keyword:** `bao_cao_tai_chinh`
- **Retrieval Latency:** 32.84 ms

| Rank | Score | Source File | Page | Type | Content Snippet |
|---|---|---|---|---|---|
| 1 📄 | 0.5710 | `pdf_scan_01_hoa_don_vat.pdf` | 1 | table | Bảng (Dữ liệu): \| STT \| Tên hàng hóa, dich vu \| DVT \| SL \| Đon giá \| Thành tin \| \| --- \| --- \| --- \| --- \| --- \| --- \| \|... |
| 2 🎯 | 0.5692 | `pdf_text_02_bao_cao_tai_chinh_quy.pdf` | 2 | paragraph | II. KẾT QUẢ TÀI CHÍNH TỔNG HỢP QUÝ 3 NĂM 2026 Đơn vị tính: Triệu Việt Nam Đồng (VND) Bảng 1 dưới đây tổng hợp các chỉ số... |
| 3 🎯 | 0.5380 | `pdf_text_02_bao_cao_tai_chinh_quy.pdf` | 2 | paragraph | Giá vốn hàng bán (COGS) 23.800 29.970 + 25.9% 3. Lợi nhuận gộp 18.700 28.230 + 51.0% 4. Chi phí nghiên cứu & phát triển ... |

### Q05 - Biên bản nghiệm thu và bàn giao sản phẩm nền tảng Document Intelligence

- **Category:** Operations/Quality
- **Expected Domain Keyword:** `bien_ban_nghiem_thu`
- **Retrieval Latency:** 29.8 ms

| Rank | Score | Source File | Page | Type | Content Snippet |
|---|---|---|---|---|---|
| 1 🎯 | 0.6336 | `pdf_scan_02_bien_ban_nghiem_thu.pdf` | 1 | paragraph | BIÊN BÁN NGHIÊM THU VÀ BÀN GIAO SÁN PHÂM D án: Nn tng Document Intelligence & Pipeline Trích xut D liu - Căn c Hp đồng d... |
| 2 📄 | 0.5952 | `pdf_text_01_hop_dong_dich_vu_cntt.pdf` | 1 | paragraph | và triển khai nền tảng Document Intelligence & RAG tiếng Việt nhằm tự động hóa việc đọc, phân loại, bóc tách dữ liệu từ ... |
| 3 📄 | 0.5949 | `docx_02_de_xuat_du_an_rag.docx` | - | paragraph | BẢN ĐỀ XUẤT DỰ ÁN: NỀN TẢNG DOCUMENT INTELLIGENCE & RAG TIẾNG VIỆT |

### Q06 - Bảng báo giá dịch vụ hạ tầng đám mây Cloud Server và hạn mức API

- **Category:** Cloud/Pricing
- **Expected Domain Keyword:** `bang_gia_dich_vu_cloud`
- **Retrieval Latency:** 54.29 ms

| Rank | Score | Source File | Page | Type | Content Snippet |
|---|---|---|---|---|---|
| 1 🎯 | 0.6440 | `pdf_complex_01_bang_gia_dich_vu_cloud.pdf` | 1 | paragraph | Hạn mức trích xuất API 10.000 trang/tháng 100.000 trang/tháng Không giới hạn Hỗ trợ OCR tài liệu scan Tối đa 500 trang/t... |
| 2 🎯 | 0.5904 | `pdf_complex_01_bang_gia_dich_vu_cloud.pdf` | 1 | paragraph | CÔNG TY CỔ PHẦN ĐIỆN TOÁN ĐÁM MÂY & AI VIỆT NAM BẢNG BÁO GIÁ DỊCH VỤ HẠ TẦNG VÀ NỀN TẢNG RAG NĂM 2026 [BẢNG GIÁ DỊCH VỤ ... |
| 3 📄 | 0.5886 | `docx_02_de_xuat_du_an_rag.docx` | - | paragraph | Bảng 2 ước tính chi phí đầu tư hạ tầng phần cứng và dịch vụ điện toán đám mây cho giai đoạn thử nghiệm (PoC) và vận hành... |

### Q07 - Đề xuất dự án phát triển hệ thống RAG và kiến trúc kỹ thuật AI

- **Category:** AI Proposal
- **Expected Domain Keyword:** `de_xuat_du_an_rag`
- **Retrieval Latency:** 19.87 ms

| Rank | Score | Source File | Page | Type | Content Snippet |
|---|---|---|---|---|---|
| 1 🎯 | 0.6353 | `docx_02_de_xuat_du_an_rag.docx` | - | paragraph | BẢN ĐỀ XUẤT DỰ ÁN: NỀN TẢNG DOCUMENT INTELLIGENCE & RAG TIẾNG VIỆT |
| 2 📄 | 0.5647 | `pdf_text_02_bao_cao_tai_chinh_quy.pdf` | 1 | paragraph | THƯ NGỎ CỦA BAN TỔNG GIÁM ĐỐC Kính gửi Quý Cổ đông, Đối tác và toàn thể Cán bộ Nhân viên, Quý 3 năm 2026 ghi nhận bước c... |
| 3 📄 | 0.5637 | `pdf_text_01_hop_dong_dich_vu_cntt.pdf` | 1 | paragraph | và triển khai nền tảng Document Intelligence & RAG tiếng Việt nhằm tự động hóa việc đọc, phân loại, bóc tách dữ liệu từ ... |

### Q08 - Dự toán ngân sách và bảng kế hoạch chi phí hoạt động các phòng ban năm 2026

- **Category:** Budget/Planning
- **Expected Domain Keyword:** `ke_hoach_ngan_sach`
- **Retrieval Latency:** 19.94 ms

| Rank | Score | Source File | Page | Type | Content Snippet |
|---|---|---|---|---|---|
| 1 📄 | 0.5769 | `docx_02_de_xuat_du_an_rag.docx` | - | paragraph | 3. DỰ TOÁN NGÂN SÁCH VÀ HẠ TẦNG KỸ THUẬT |
| 2 📄 | 0.5469 | `pdf_text_02_bao_cao_tai_chinh_quy.pdf` | 2 | paragraph | II. KẾT QUẢ TÀI CHÍNH TỔNG HỢP QUÝ 3 NĂM 2026 Đơn vị tính: Triệu Việt Nam Đồng (VND) Bảng 1 dưới đây tổng hợp các chỉ số... |
| 3 🎯 | 0.5468 | `xlsx_01_ke_hoach_ngan_sach_2026.xlsx` | - | table | Bảng (TongQuanNganSach): \| Mã dự án \| Tên dự án AI \| Khối phụ trách \| Ngày phê duyệt \| Ngân sách duyệt (VND) \| Đã giải n... |


# Vietnamese Document Intelligence & RAG Platform

> **Milestone 01**: Document Processing Pipeline & REST API (Completed)  
> **Milestone 02**: Vietnamese OCR & Layout Processing (Completed)

Platform xử lý, trích xuất cấu trúc và phân tích tài liệu tiếng Việt đa định dạng (PDF, DOCX, XLSX, Scanned PDF), cung cấp REST API hiệu năng cao xây dựng trên FastAPI, phục vụ cho các hệ thống RAG (Retrieval-Augmented Generation) và Document Intelligence.

---

## 1. Project Overview

Hệ thống cho phép người dùng và các dịch vụ khác tải lên các tài liệu tiếng Việt phức tạp, bao gồm văn bản hợp đồng, báo cáo tài chính, biểu bảng thống kê, bảng lương và tài liệu scan. Hệ thống tự động:

- Nhận diện định dạng tài liệu (`.pdf`, `.docx`, `.xlsx`).
- **Trích xuất thông minh theo từng trang (Per-Page Routing)**: Tự động phân tách trang có text layer (xử lý siêu tốc qua PyMuPDF) và trang quét scan/ảnh (định tuyến qua Vietnamese PaddleOCR).
- **Phân tích bố cục (Layout Processing)**: Xác định thứ tự đọc tự nhiên (hỗ trợ văn bản 2 cột), phân loại vùng (`heading`, `paragraph`, `table`), trích xuất bounding boxes và độ tin cậy (`confidence`).
- **Tái cấu trúc biểu bảng (Table Structure Reconstruction)**: Tự động nhóm các ô thành ma trận hàng/cột (`table_data`) từ tài liệu scan và bảng DOCX/XLSX.
- Giữ thứ tự xuất hiện tuần tự của các đoạn văn và bảng dữ liệu.
- Chuẩn hóa kiểu dữ liệu ngày tháng, số liệu và ký tự tiếng Việt (UTF-8 NFC) sang cấu trúc JSON thống nhất.

---

## 2. Architecture & OCR Pipeline

Kiến trúc tuân thủ nguyên lý Clean Architecture & Single Responsibility Principle, tách biệt hoàn toàn giữa Web Delivery Layer (FastAPI), Business Service Layer (`DocumentParser`, `DocumentRouter`, `LayoutProcessor`, `VietnameseOCREngine`), Data Schemas (Pydantic), và Configuration.

### Processing Workflow

```
[Client Upload: POST /documents/parse?enable_ocr=true]
       │
       ├──► 1. Extension Validation (.pdf, .docx, .xlsx) ──► 415 Unsupported Media Type
       ├──► 2. Chunk-based Size Check (<= 20 MB)         ──► 413 Content Too Large
       └──► 3. Empty File Check (> 0 bytes)             ──► 400 Bad Request
       │
       ▼
[Service: DocumentParser]
       │
       ├──► DOCX / XLSX ────────────────────────► python-docx / openpyxl
       │
       └──► PDF ──► [DocumentRouter] (Per-page Analysis)
                        │
                        ├──► Page có Text Layer ──► PyMuPDF Native Extraction
                        │
                        └──► Page Scan / Ảnh    ──► [VietnameseOCREngine]
                                                         │
                                                         ▼
                                                    PaddleOCR PP-OCRv6
                                                    (Det + Rec + Ori)
                                                         │
                                                         ▼
                                                    [LayoutProcessor]
                                                    - Reading order (2-column)
                                                    - Heading / Paragraph / Table
                                                    - Table matrix reconstruction
       │
       ▼
[Unified Pydantic Schema: DocumentParseResponse]
(text, page, source: native/ocr, bbox, confidence, layout_type, table_data)
       │
       ▼
[Client JSON Response (HTTP 200)]
```

---

## 3. Technology Stack

- **Runtime & Language**: Python 3.11+ / 3.13
- **Web Framework**: FastAPI (Asynchronous ASGI framework)
- **ASGI Server**: Uvicorn
- **Data Validation & Settings**: Pydantic v2, Pydantic-Settings
- **PDF Extraction**: PyMuPDF (`pymupdf`)
- **Word Processing**: `python-docx`
- **Spreadsheet Processing**: `openpyxl`
- **OCR Engine**: PaddleOCR 3.7+ (`paddlepaddle` 3.3.1, `paddlex` 3.x)
- **OCR Models**: PP-OCRv6 (Detection `PP-OCRv6_medium_det`, Recognition `PP-OCRv6_medium_rec`, Orientation `PP-LCNet_x1_0_textline_ori`)
- **Image Processing**: Pillow (`PIL`)
- **Testing**: `pytest`, `httpx` (34/34 tests passed)

---

## 4. Folder Structure

```
vietnamese-document-intelligence/
│
├── app/
│   ├── api/
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   └── documents.py          # Route POST /documents/parse?enable_ocr=...
│   │   └── __init__.py
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py                 # Pydantic Settings & OCR configurations
│   │   └── exceptions.py             # Domain exceptions (including OCREngineError)
│   │
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── document.py               # DocumentSegment (bbox, words, confidence), Response
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── document_parser.py        # Unified entrypoint for PDF, DOCX, XLSX
│   │   ├── document_router.py        # Intelligent per-page native vs OCR routing
│   │   ├── layout_processor.py       # Reading order, 2-column, table reconstruction
│   │   └── ocr_engine.py             # PaddleOCR Vietnamese Engine with GPU/CPU fallback
│   │
│   ├── __init__.py
│   └── main.py                       # FastAPI application & GET /health
│
├── data/
│   ├── raw/                          # Raw document storage directory
│   │   ├── pdf/                      # Demo PDFs (text, scanned invoices, complex 2-col)
│   │   ├── docx/                     # Demo DOCX files
│   │   └── xlsx/                     # Demo XLSX files
│   ├── ground_truth/                 # Ground truth text & JSON for OCR evaluation
│   ├── metadata/                     # dataset_manifest.json
│   ├── evaluation_report.json        # Detailed evaluation metrics (CER/WER/latency)
│   └── evaluation_report.md          # Markdown evaluation report
│
├── scripts/
│   ├── evaluate_ocr.py               # CER/WER/latency evaluation runner
│   └── validate_demo_dataset.py      # Dataset validation script
│
├── tests/
│   ├── test_document_parser.py       # 16 unit tests for document parsers
│   ├── test_documents_api.py         # 9 API integration tests
│   └── test_ocr_pipeline.py          # 9 OCR, layout, mixed PDF & routing tests
│
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```
│   │   └── dataset_manifest.json     # Metadata manifest of 10 demo documents
│   └── ground_truth/                 # Ground truth text/JSON for scanned PDFs
│
├── scripts/
│   ├── generate_demo_dataset.py      # Reproducible dataset generator
│   └── validate_demo_dataset.py      # Comprehensive 10-file validation script
│
├── tests/
│   ├── __init__.py
│   ├── test_document_parser.py       # Unit tests for parser logic
│   └── test_documents_api.py         # API integration tests
│
├── .env.example                      # Environment variables template
├── .gitignore                        # Git ignore specifications
├── requirements.txt                  # Python dependencies
└── README.md                         # Project documentation
```

---

## 5. Installation

Yêu cầu: Đã cài đặt **Python 3.11+** và **Git** trên máy tính.

Mở **PowerShell** và di chuyển vào thư mục dự án:

```powershell
cd D:\rag\vietnamese-document-intelligence
```

Khởi tạo môi trường ảo (Virtual Environment):

```powershell
python -m venv .venv
```

Kích hoạt môi trường ảo:

```powershell
.\.venv\Scripts\Activate.ps1
```

Cài đặt các gói phụ thuộc:

```powershell
pip install --upgrade pip
pip install -r requirements.txt
```

---

## 6. Environment Setup

Sao chép file cấu hình mẫu `.env.example` thành `.env`:

```powershell
Copy-Item .env.example .env
```

Nội dung file `.env`:

```ini
PROJECT_NAME="Vietnamese Document Intelligence & RAG Platform"
VERSION="0.1.0"
ENVIRONMENT="development"
DEBUG=False
MAX_FILE_SIZE_BYTES=20971520  # Giới hạn 20 MB
```

---

## 7. How to Run Server

Chạy server phát triển với Uvicorn:

```powershell
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Khi server khởi động thành công:

- **API Base URL**: `http://127.0.0.1:8000`
- **Interactive Swagger UI**: `http://127.0.0.1:8000/docs`
- **ReDoc Documentation**: `http://127.0.0.1:8000/redoc`

---

## 8. API Documentation

### 1. `GET /health`

Kiểm tra trạng thái sẵn sàng của hệ thống.

- **HTTP Code**: 200 OK
- **Response**:

```json
{
  "status": "healthy",
  "version": "0.1.0",
  "environment": "development"
}
```

### 2. `POST /documents/parse`

Tải lên tài liệu và nhận dữ liệu trích xuất có cấu trúc.

- **Content-Type**: `multipart/form-data`
- **Body Parameter**: `file` (Binary file: `.pdf`, `.docx`, hoặc `.xlsx`)
- **HTTP Status Codes**:
  - `200 OK`: Trích xuất thành công.
  - `400 Bad Request`: File rỗng (0 bytes), file bị lỗi cấu trúc, file PDF bị mã hóa bằng mật khẩu.
  - `413 Content Too Large`: Dung lượng file vượt quá giới hạn cấu hình (20 MB).
  - `415 Unsupported Media Type`: Định dạng file không được hỗ trợ (khác `.pdf`, `.docx`, `.xlsx`).

---

## 9. Example Request and Response

### Example 1: Kiểm tra Health Check qua cURL / PowerShell

```powershell
curl.exe -X GET "http://127.0.0.1:8000/health"
```

### Example 2: Tải lên tài liệu PDF qua PowerShell

```powershell
curl.exe -X POST "http://127.0.0.1:8000/documents/parse" `
  -F "file=@hop_dong.pdf;type=application/pdf"
```

### Example 3: Cấu trúc JSON Response (PDF)

```json
{
  "filename": "hop_dong.pdf",
  "file_type": "pdf",
  "requires_ocr": false,
  "total_segments": 2,
  "metadata": {
    "file_size_bytes": 45120,
    "page_count": 2,
    "sheet_count": null,
    "paragraph_count": null,
    "table_count": null,
    "extra": {
      "format": "PDF",
      "encrypted": false
    }
  },
  "segments": [
    {
      "segment_id": 1,
      "segment_type": "text",
      "page": 1,
      "sheet_name": null,
      "text": "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\nĐộc lập - Tự do - Hạnh phúc\n\nHỢP ĐỒNG KINH TẾ...",
      "table_data": null,
      "metadata": {
        "page": 1,
        "has_text": true,
        "image_count": 0,
        "requires_ocr": false,
        "char_count": 480
      }
    },
    {
      "segment_id": 2,
      "segment_type": "text",
      "page": 2,
      "sheet_name": null,
      "text": "ĐIỀU 5: ĐIỀU KHOẢN THANH TOÁN VÀ NGHIỆM THU...",
      "table_data": null,
      "metadata": {
        "page": 2,
        "has_text": true,
        "image_count": 0,
        "requires_ocr": false,
        "char_count": 320
      }
    }
  ]
}
```

### Example 4: Cấu trúc JSON Response (DOCX có đoạn văn và bảng)

```json
{
  "filename": "bao_cao.docx",
  "file_type": "docx",
  "requires_ocr": false,
  "total_segments": 2,
  "metadata": {
    "file_size_bytes": 28400,
    "page_count": null,
    "sheet_count": null,
    "paragraph_count": 1,
    "table_count": 1,
    "extra": {
      "format": "DOCX"
    }
  },
  "segments": [
    {
      "segment_id": 1,
      "segment_type": "text",
      "page": null,
      "sheet_name": null,
      "text": "Báo cáo tiến độ triển khai dự án AI:",
      "table_data": null,
      "metadata": {
        "char_count": 36
      }
    },
    {
      "segment_id": 2,
      "segment_type": "table",
      "page": null,
      "sheet_name": null,
      "text": "Hạng mục | Tiến độ | Trạng thái\nParser Pipeline | 100% | Hoàn thành",
      "table_data": [
        ["Hạng mục", "Tiến độ", "Trạng thái"],
        ["Parser Pipeline", "100%", "Hoàn thành"]
      ],
      "metadata": {
        "row_count": 2,
        "col_count": 3
      }
    }
  ]
}
```

---

## 10. Demo Dataset & Ground Truth

Dự án cung cấp bộ dữ liệu demo chuẩn mực gồm 10 tài liệu tiếng Việt thực tế trong `data/raw/`, mô phỏng chính xác các loại tài liệu thực tế trong môi trường doanh nghiệp:

### Danh mục 10 tài liệu demo:

 1. `data/raw/pdf/pdf_text_01_hop_dong_dich_vu_cntt.pdf`: Hợp đồng dịch vụ CNTT 3 trang, có text layer gốc, gồm 7 điều khoản pháp lý và khối chữ ký.
 2. `data/raw/pdf/pdf_text_02_bao_cao_tai_chinh_quy.pdf`: Báo cáo tài chính Quý 3/2026 dài 3 trang, bảng chỉ tiêu tài chính 10 dòng x 4 cột.
 3. `data/raw/pdf/pdf_scan_01_hoa_don_vat.pdf`: Bản quét hóa đơn GTGT điện tử (150 DPI), dạng ảnh raster thuần túy, 0 text bytes, có cờ `requires_ocr = True`.
 4. `data/raw/pdf/pdf_scan_02_bien_ban_nghiem_thu.pdf`: Bản quét biên bản nghiệm thu và bàn giao dự án AI (150 DPI), dạng ảnh raster, có dấu đỏ và chữ ký.
 5. `data/raw/docx/docx_01_quy_che_noi_bo_doanh_nghiep.docx`: Quy chế nhân sự có tiêu đề, 3 cấp Heading, các đoạn văn quy chế Hybrid và 2 bảng khung bậc lương / thưởng.
 6. `data/raw/docx/docx_02_de_xuat_du_an_rag.docx`: Đề xuất dự án RAG gồm các mục tiêu, bảng lộ trình 5 cột mốc và bảng dự toán ngân sách hạ tầng GPU.
 7. `data/raw/xlsx/xlsx_01_ke_hoach_ngan_sach_2026.xlsx`: Bảng tính 3 worksheets ('TongQuanNganSach', 'ChiTietChiPhiQuy1', 'DuPhongRuiRo') chứa trường ngày tháng và ô trống (null).
 8. `data/raw/xlsx/xlsx_02_quan_ly_nhan_su_va_du_an.xlsx`: Bảng tính quản lý nhân sự 3 worksheets ('DanhSachNhanSu', 'PhanCongDuAn', 'TheoDoiNghiPhep') có ô trống và định dạng ngày.
 9. `data/raw/pdf/pdf_complex_01_bang_gia_dich_vu_cloud.pdf`: Bảng báo giá phức tạp 2 trang với bảng so sánh đa cấp 3 gói dịch vụ (Starter, Pro, Enterprise) và bảng phụ lục add-on.
10. `data/raw/pdf/pdf_complex_02_ban_tin_cong_nghe_hai_cot.pdf`: Bản tin công nghệ bố cục 2 cột song song (multi-column), chia tách bởi đường kẻ dọc và bảng tổng hợp ở cuối.

### Ground Truth phục vụ đánh giá CER/WER:

Thư mục `data/ground_truth/` lưu trữ nội dung văn bản chuẩn của các tài liệu scan:

- `pdf_scan_01_hoa_don_vat.txt` & `.json`: Nội dung chuẩn của hóa đơn VAT để đánh giá độ chính xác OCR.
- `pdf_scan_02_bien_ban_nghiem_thu.txt` & `.json`: Nội dung chuẩn của biên bản nghiệm thu.

### Lệnh kiểm định toàn bộ Dataset:

```powershell
.\.venv\Scripts\python.exe scripts/validate_demo_dataset.py
```

---

## 11. How to Run Tests

Bộ kiểm thử được viết hoàn toàn bằng `pytest`, bao gồm kiểm thử parser cơ bản, API integration, và toàn bộ pipeline OCR / phân tích layout.

Chạy toàn bộ 34 test cases:

```powershell
.\.venv\Scripts\pytest.exe -v
```

Chạy riêng OCR Pipeline & Routing Tests:

```powershell
.\.venv\Scripts\pytest.exe -v tests/test_ocr_pipeline.py
```

Chạy riêng Unit Tests cho DocumentParser (Milestone 01 Regression):

```powershell
.\.venv\Scripts\pytest.exe -v tests/test_document_parser.py
```

Chạy riêng API Integration Tests:

```powershell
.\.venv\Scripts\pytest.exe -v tests/test_documents_api.py
```

Chạy đánh giá hiệu năng OCR (CER/WER/Latency):

```powershell
.\.venv\Scripts\python.exe scripts/evaluate_ocr.py
```

---

## 12. Known Limitations & Observed Edge Cases

1. **OCR Inference Latency trên CPU**: Do chạy mô hình deep learning PP-OCRv6 trên CPU, độ trễ trung bình ~60s/trang. Khi triển khai production có GPU NVIDIA (CUDA/TensorRT), thời gian xử lý sẽ giảm xuống < 1.5s/trang.
2. **Cấu trúc bảng phức tạp**: Hệ thống đã hỗ trợ trích xuất bảng 1 tầng dạng ma trận hàng x cột. Đối với các bảng có ô gộp (merged cells đa tầng, multi-level headers), cần bổ sung Table Structure Recognition chuyên sâu (như SLANet/TableMaster) ở các milestone sau.

---

## 13. Next Milestone

**Milestone 03: Text Chunking, Embedding & Vector Database (Qdrant)**:
- Chunking văn bản thông minh bảo toàn ngữ cảnh tiêu đề và cấu trúc bảng.
- Sinh vector embeddings tiếng Việt với mô hình đa ngôn ngữ **BGE-M3**.
- Lưu trữ và truy vấn tương đồng trên **Qdrant Vector Database**.
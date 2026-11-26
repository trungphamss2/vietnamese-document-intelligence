# MILESTONE 04 – HYBRID RETRIEVAL & RERANKING BENCHMARK REPORT

**Date:** 2026-11-26 17:50:55  
**Dataset:** 10 Synthetic Vietnamese Documents (105 Chunks)  
**Queries:** 16 Vietnamese Queries (K=5, Candidate Limit=20, RRF k=60)  
**Qdrant Mode:** `embedded_in_memory`  
**Models:** `BAAI/bge-m3` (FP16) + BM25 (`PositiveBM25Okapi`) + `BAAI/bge-reranker-v2-m3` (FP16)

---

## 1. Four-Way Retrieval Comparison (K=5)

| Configuration | Recall@5 | Precision@5 | MRR@5 | nDCG@5 | Top-1 Doc Acc | Top-3 Doc Acc | Avg Latency | p50 Latency | p95 Latency |
|---|---|---|---|---|---|---|---|---|---|
| **BM25 Only (Sparse)** | 48.44% | 31.25% | 0.6719 | 0.5160 | 68.75% | 75.0% | 0.8 ms | 0.7 ms | 1.5 ms |
| **Dense Only (BGE-M3)** | 58.59% | 41.25% | 0.6979 | 0.5883 | 62.5% | 87.5% | 50.0 ms | 51.0 ms | 67.6 ms |
| **Hybrid Search (RRF)** | 56.77% | 37.5% | 0.7937 | 0.6015 | 75.0% | 87.5% | 53.7 ms | 54.1 ms | 68.8 ms |
| **Hybrid + Cross-Encoder Reranker** | 58.85% | 41.25% | 0.8750 | 0.6476 | 93.75% | 93.75% | 320.2 ms | 313.8 ms | 375.1 ms |

---

## 2. Combined Hardware VRAM Footprint (BGE-M3 + BGE-Reranker FP16)

- **GPU Device:** NVIDIA GeForce RTX 3050 6GB Laptop GPU (6143.5 MB Total)
- **Active Tensor VRAM (Allocated):** 2174.2 MB (Peak: 2219.3 MB)
- **PyTorch Caching Pool (Reserved):** 3168.0 MB (Peak: 4152.0 MB)

---

## 3. Per-Query Breakdown (MRR@5, nDCG@5, Top-1 Doc Match)

| ID | Expected Doc | BM25 Top-1 | Dense Top-1 | Hybrid RRF Top-1 | Hybrid+Rerank Top-1 | Rerank MRR@5 | Rerank Latency |
|---|---|---|---|---|---|---|---|
| Q01 | `hop_dong_dich_vu_cntt` | ✅ (1.00) | ✅ (1.00) | ❌ (0.50) | ✅ (0.50) | 0.5000 | 419.2 ms |
| Q02 | `hop_dong_dich_vu_cntt` | ✅ (1.00) | ✅ (1.00) | ✅ (1.00) | ✅ (1.00) | 1.0000 | 360.3 ms |
| Q03 | `bao_cao_tai_chinh` | ✅ (1.00) | ✅ (1.00) | ✅ (1.00) | ✅ (1.00) | 1.0000 | 351.4 ms |
| Q04 | `bao_cao_tai_chinh` | ✅ (1.00) | ❌ (0.50) | ✅ (1.00) | ✅ (1.00) | 1.0000 | 325.8 ms |
| Q05 | `hoa_don_vat` | ✅ (1.00) | ✅ (1.00) | ✅ (1.00) | ✅ (1.00) | 1.0000 | 321.1 ms |
| Q06 | `hoa_don_vat` | ❌ (0.00) | ✅ (1.00) | ✅ (1.00) | ✅ (1.00) | 1.0000 | 334.8 ms |
| Q07 | `bien_ban_nghiem_thu` | ❌ (0.25) | ❌ (0.00) | ❌ (0.50) | ✅ (1.00) | 1.0000 | 288.4 ms |
| Q08 | `bien_ban_nghiem_thu` | ❌ (0.00) | ❌ (0.00) | ❌ (0.00) | ❌ (0.00) | 0.0000 | 258.1 ms |
| Q09 | `quy_che_noi_bo` | ✅ (1.00) | ✅ (1.00) | ✅ (1.00) | ✅ (1.00) | 1.0000 | 290.2 ms |
| Q10 | `quy_che_noi_bo` | ✅ (0.50) | ✅ (0.50) | ✅ (0.50) | ✅ (0.50) | 0.5000 | 306.3 ms |
| Q11 | `de_xuat_du_an_rag` | ✅ (1.00) | ✅ (1.00) | ✅ (1.00) | ✅ (1.00) | 1.0000 | 303.2 ms |
| Q12 | `de_xuat_du_an_rag` | ✅ (0.50) | ❌ (0.50) | ✅ (1.00) | ✅ (1.00) | 1.0000 | 298.1 ms |
| Q13 | `ke_hoach_ngan_sach` | ❌ (0.00) | ❌ (0.33) | ❌ (0.20) | ✅ (1.00) | 1.0000 | 320.7 ms |
| Q14 | `quan_ly_nhan_su` | ❌ (0.50) | ✅ (1.00) | ✅ (1.00) | ✅ (1.00) | 1.0000 | 338.5 ms |
| Q15 | `bang_gia_dich_vu_cloud` | ✅ (1.00) | ✅ (1.00) | ✅ (1.00) | ✅ (1.00) | 1.0000 | 299.7 ms |
| Q16 | `ban_tin_cong_nghe` | ✅ (1.00) | ❌ (0.33) | ✅ (1.00) | ✅ (1.00) | 1.0000 | 306.9 ms |

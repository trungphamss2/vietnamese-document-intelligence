"""Comprehensive 4-way Retrieval Benchmark for Milestone 04.

Compares:
1. BM25 Only (Sparse)
2. Dense Only (BGE-M3 + Qdrant)
3. Hybrid Search (Dense + BM25 + RRF)
4. Hybrid Search + Cross-Encoder Reranking (BAAI/bge-reranker-v2-m3)

Evaluates Recall@K, Precision@K, MRR@K, nDCG@K, Top-1/Top-3 Document Accuracy,
and Avg/p50/p95 latencies across all 16 Vietnamese queries.
"""

import json
import math
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np
import torch

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.core.config import settings
from app.schemas.chunk import HybridSearchRequest, TextChunk
from app.services.bm25_service import BM25Service
from app.services.document_parser import DocumentParser
from app.services.embedding_service import EmbeddingService
from app.services.hybrid_search_service import HybridSearchService
from app.services.reranker_service import BGERerankerService
from app.services.text_chunker import IntelligentTextChunker
from app.services.vector_store import QdrantVectorStore

# 16 Vietnamese evaluation queries with verified chunk-level ground truth
BENCHMARK_QUERIES = [
    {
        "query_id": "Q01",
        "query": "Điều khoản hiệu lực hợp đồng và bảo mật thông tin dịch vụ CNTT",
        "expected_domain": "hop_dong_dich_vu_cntt",
        "relevant_chunk_indices": [8, 9],
        "category": "Legal/Contract",
    },
    {
        "query_id": "Q02",
        "query": "Lộ trình tạm ứng thanh toán dịch vụ phần mềm và thuế suất GTGT 10%",
        "expected_domain": "hop_dong_dich_vu_cntt",
        "relevant_chunk_indices": [6],
        "category": "Finance/Contract",
    },
    {
        "query_id": "Q03",
        "query": "Báo cáo hoạt động kinh doanh doanh thu thuần và lợi nhuận gộp sau thuế quý 3",
        "expected_domain": "bao_cao_tai_chinh",
        "relevant_chunk_indices": [0, 4, 5],
        "category": "Finance/Report",
    },
    {
        "query_id": "Q04",
        "query": "Phân tích rủi ro tài chính và biến động chi phí vận hành doanh nghiệp",
        "expected_domain": "bao_cao_tai_chinh",
        "relevant_chunk_indices": [6, 7, 8],
        "category": "Finance/Risk",
    },
    {
        "query_id": "Q05",
        "query": "Hóa đơn giá trị gia tăng số tiền thanh toán thuế VAT thiết bị mạng",
        "expected_domain": "hoa_don_vat",
        "relevant_chunk_indices": [1, 2, 7],
        "category": "Invoice/Scanned",
    },
    {
        "query_id": "Q06",
        "query": "Mã số thuế đơn vị bán hàng và tổng tiền thanh toán hóa đơn điện tử",
        "expected_domain": "hoa_don_vat",
        "relevant_chunk_indices": [0, 2, 8],
        "category": "Invoice/Tax",
    },
    {
        "query_id": "Q07",
        "query": "Biên bản nghiệm thu và bàn giao sản phẩm dự án nền tảng AI",
        "expected_domain": "bien_ban_nghiem_thu",
        "relevant_chunk_indices": [2, 11, 12],
        "category": "Operations/Handover",
    },
    {
        "query_id": "Q08",
        "query": "Đánh giá tiêu chí kỹ thuật bàn giao hệ thống và chữ ký đại diện hai bên",
        "expected_domain": "bien_ban_nghiem_thu",
        "relevant_chunk_indices": [1, 5, 7],
        "category": "Operations/Criteria",
    },
    {
        "query_id": "Q09",
        "query": "Quy chế làm việc văn hóa ứng xử nội bộ và chính sách làm việc hybrid",
        "expected_domain": "quy_che_noi_bo",
        "relevant_chunk_indices": [0, 2, 3, 4],
        "category": "Policy/HR",
    },
    {
        "query_id": "Q10",
        "query": "Khung bậc lương kỹ sư AI và chính sách khen thưởng milestone",
        "expected_domain": "quy_che_noi_bo",
        "relevant_chunk_indices": [5, 6, 7, 8, 10, 11],
        "category": "HR/Salary",
    },
    {
        "query_id": "Q11",
        "query": "Bản đề xuất dự án phát triển hệ thống Document Intelligence và RAG tiếng Việt",
        "expected_domain": "de_xuat_du_an_rag",
        "relevant_chunk_indices": [0, 1, 4],
        "category": "AI Proposal",
    },
    {
        "query_id": "Q12",
        "query": "Lộ trình 5 cột mốc triển khai và dự toán hạ tầng GPU Cloud cho RAG",
        "expected_domain": "de_xuat_du_an_rag",
        "relevant_chunk_indices": [6, 7, 8, 9, 10, 11, 12, 13],
        "category": "Technical/Roadmap",
    },
    {
        "query_id": "Q13",
        "query": "Bảng tính kế hoạch phân bổ ngân sách chi tiết chi phí quý 1 năm 2026",
        "expected_domain": "ke_hoach_ngan_sach",
        "relevant_chunk_indices": [0, 1, 2, 3, 4, 5],
        "category": "Budget/Spreadsheet",
    },
    {
        "query_id": "Q14",
        "query": "Danh sách nhân sự phân công phụ trách dự án và theo dõi ngày nghỉ phép",
        "expected_domain": "quan_ly_nhan_su",
        "relevant_chunk_indices": [0, 1, 2, 3, 4, 5],
        "category": "HR/Spreadsheet",
    },
    {
        "query_id": "Q15",
        "query": "Bảng báo giá các gói dịch vụ Starter Pro Enterprise hạ tầng Cloud Server và API",
        "expected_domain": "bang_gia_dich_vu_cloud",
        "relevant_chunk_indices": [0, 1, 2],
        "category": "Cloud/Pricing",
    },
    {
        "query_id": "Q16",
        "query": "Bản tin đổi mới công nghệ và xu hướng ứng dụng trí tuệ nhân tạo Việt Nam",
        "expected_domain": "ban_tin_cong_nghe",
        "relevant_chunk_indices": [0, 2],
        "category": "Tech/Newsletter",
    },
]


def load_or_parse_chunks() -> List[TextChunk]:
    """Load cached chunks from scratch if present, else parse all 10 demo docs."""
    raw_dir = PROJECT_ROOT / "data" / "raw"
    files = sorted(list(raw_dir.rglob("*.pdf")) + list(raw_dir.rglob("*.docx")) + list(raw_dir.rglob("*.xlsx")))

    parser = DocumentParser()
    chunker = IntelligentTextChunker()
    all_chunks: List[TextChunk] = []

    print(f"[Dataset] Parsing and chunking {len(files)} synthetic documents...")
    for f in files:
        doc_id = f"doc_{f.stem}"
        parsed = parser.parse(filename=f.name, content=f.read_bytes(), enable_ocr=True)
        chunks = chunker.chunk_document(parsed, document_id=doc_id)
        all_chunks.extend(chunks)
        print(f"  - {f.name}: {len(chunks)} chunks")

    return all_chunks


def build_ground_truth_chunk_ids(chunks: List[TextChunk]) -> Dict[str, Set[str]]:
    """Resolve exact relevant chunk_id sets for each query based on verified chunk indices."""
    gt_map: Dict[str, Set[str]] = {}
    for q in BENCHMARK_QUERIES:
        rel_ids: Set[str] = set()
        domain = q["expected_domain"]
        target_indices = set(q["relevant_chunk_indices"])
        for c in chunks:
            if domain in c.filename.lower() and c.chunk_index in target_indices:
                rel_ids.add(c.chunk_id)
        gt_map[q["query_id"]] = rel_ids
    return gt_map


def compute_ir_metrics(
    retrieved_hits: List[Dict[str, Any]],
    relevant_chunk_ids: Set[str],
    expected_domain: str,
    k: int = 5,
) -> Dict[str, float]:
    """Compute Recall@K, Precision@K, MRR@K, nDCG@K, and Doc Top-1/Top-3."""
    top_k = retrieved_hits[:k]

    # Chunk-level binary relevance vector
    rels = [1 if h["chunk_id"] in relevant_chunk_ids else 0 for h in top_k]
    num_rel_total = len(relevant_chunk_ids)

    recall_k = sum(rels) / num_rel_total if num_rel_total > 0 else 0.0
    precision_k = sum(rels) / k if k > 0 else 0.0

    # MRR@K (chunk-level)
    mrr_k = 0.0
    for idx, r in enumerate(rels, start=1):
        if r == 1:
            mrr_k = 1.0 / idx
            break

    # nDCG@K (chunk-level)
    dcg = sum(r / math.log2(idx + 1) for idx, r in enumerate(rels, start=1))
    ideal_len = min(k, num_rel_total)
    idcg = sum(1.0 / math.log2(idx + 1) for idx in range(1, ideal_len + 1))
    ndcg_k = (dcg / idcg) if idcg > 0 else 0.0

    # Document-level Top-1 and Top-3
    doc_top1 = 1.0 if (len(top_k) >= 1 and expected_domain in top_k[0]["filename"].lower()) else 0.0
    doc_top3 = 1.0 if any(expected_domain in h["filename"].lower() for h in top_k[:3]) else 0.0

    return {
        "recall_at_k": recall_k,
        "precision_at_k": precision_k,
        "mrr_at_k": mrr_k,
        "ndcg_at_k": ndcg_k,
        "doc_top1": doc_top1,
        "doc_top3": doc_top3,
    }


def setup_vector_store(chunks: List[TextChunk], embedder: EmbeddingService) -> Tuple[QdrantVectorStore, str]:
    """Connect to Qdrant Docker if online, else fallback to in-memory QdrantClient."""
    qdrant_mode = "docker_localhost_6333"
    try:
        vs = QdrantVectorStore(collection_name="vietnamese_documents_m04_eval")
        # Recreate clean eval collection
        try:
            vs.client.delete_collection("vietnamese_documents_m04_eval")
        except Exception:
            pass
        vs.ensure_collection("vietnamese_documents_m04_eval")
    except Exception as exc:
        print(f"[WARNING] Docker Qdrant unavailable ({exc}). Using embedded QdrantClient(':memory:').")
        qdrant_mode = "embedded_in_memory"
        from qdrant_client import QdrantClient

        vs = QdrantVectorStore.__new__(QdrantVectorStore)
        vs.host = "memory"
        vs.port = 0
        vs.collection_name = "vietnamese_documents_m04_eval"
        vs.client = QdrantClient(":memory:")
        vs.ensure_collection()

    # Embed and index by document_id
    by_doc: Dict[str, List[TextChunk]] = {}
    for c in chunks:
        by_doc.setdefault(c.document_id, []).append(c)

    print(f"[Indexing] Embedding {len(chunks)} chunks into Qdrant ({qdrant_mode})...")
    for doc_id, doc_chunks in by_doc.items():
        vecs = embedder.embed_texts([c.text for c in doc_chunks])
        vs.upsert_chunks(chunks=doc_chunks, vectors=vecs, document_id=doc_id)

    return vs, qdrant_mode


def run_benchmark(k: int = 5, candidate_limit: int = 20) -> Dict[str, Any]:
    """Run all 4 retrieval configurations across 16 queries."""
    # Optional fast load from scratch dump if present, else parse
    scratch_path = Path(r"C:\Users\trung\.gemini\antigravity\brain\bb1c8d3e-1990-4473-85ef-a15b775c297d\scratch\demo_chunks.json")
    if scratch_path.exists():
        raw_list = json.loads(scratch_path.read_text(encoding="utf-8"))
        chunks = [TextChunk(**item) for item in raw_list]
        print(f"[Dataset] Loaded {len(chunks)} pre-parsed chunks.")
    else:
        chunks = load_or_parse_chunks()

    gt_map = build_ground_truth_chunk_ids(chunks)

    embedder = EmbeddingService.get_instance()
    reranker = BGERerankerService.get_instance()

    if torch.cuda.is_available():
        torch.cuda.reset_peak_memory_stats(0)

    # Build fresh BM25 index synced with the 10 documents
    bm25_path = PROJECT_ROOT / "data" / "bm25_index.json"
    if bm25_path.exists():
        bm25_path.unlink()
    bm25 = BM25Service(storage_path=str(bm25_path))
    by_doc: Dict[str, List[TextChunk]] = {}
    for c in chunks:
        by_doc.setdefault(c.document_id, []).append(c)
    for doc_id, doc_chunks in by_doc.items():
        bm25.index_chunks(doc_chunks, document_id=doc_id)

    vector_store, qdrant_mode = setup_vector_store(chunks, embedder)
    hybrid_service = HybridSearchService(
        embedder=embedder,
        vector_store=vector_store,
        bm25_service=bm25,
        reranker_service=reranker,
    )

    # Warmup GPU models to avoid cold-start skew in p50/p95
    _ = embedder.embed_query("khởi động mô hình")
    _ = reranker.predict_pairs([("khởi động", "khởi động mô hình")])

    configs = [
        "1_bm25_only",
        "2_dense_only",
        "3_hybrid_rrf",
        "4_hybrid_rerank",
    ]
    labels = {
        "1_bm25_only": "BM25 Only (Sparse)",
        "2_dense_only": "Dense Only (BGE-M3)",
        "3_hybrid_rrf": "Hybrid Search (RRF)",
        "4_hybrid_rerank": "Hybrid + Cross-Encoder Reranker",
    }

    summary_results: Dict[str, Any] = {}
    per_query_details: List[Dict[str, Any]] = []

    for cfg in configs:
        print(f"\n[Evaluating] {labels[cfg]}...")
        latencies: List[float] = []
        metrics_list: List[Dict[str, float]] = []

        for idx, q in enumerate(BENCHMARK_QUERIES):
            query_text = q["query"]
            t0 = time.perf_counter()

            if cfg == "1_bm25_only":
                raw_hits = bm25.search(query=query_text, limit=k)
                hits = [
                    {"chunk_id": h["chunk_id"], "filename": h["filename"], "score": h["score"], "text": h["text"]}
                    for h in raw_hits
                ]
            elif cfg == "2_dense_only":
                qvec = embedder.embed_query(query_text)
                raw_hits = vector_store.search(query_vector=qvec, limit=k)
                hits = [
                    {"chunk_id": h.chunk_id, "filename": h.filename, "score": h.score, "text": h.text}
                    for h in raw_hits
                ]
            elif cfg == "3_hybrid_rrf":
                resp = hybrid_service.search_hybrid(
                    HybridSearchRequest(
                        query=query_text,
                        top_k=k,
                        candidate_limit=candidate_limit,
                        enable_reranking=False,
                    )
                )
                hits = [
                    {"chunk_id": h.chunk_id, "filename": h.filename, "score": h.score, "text": h.text}
                    for h in resp.results
                ]
            else:  # 4_hybrid_rerank
                resp = hybrid_service.search_hybrid(
                    HybridSearchRequest(
                        query=query_text,
                        top_k=k,
                        candidate_limit=candidate_limit,
                        enable_reranking=True,
                    )
                )
                hits = [
                    {"chunk_id": h.chunk_id, "filename": h.filename, "score": h.score, "text": h.text}
                    for h in resp.results
                ]

            latency_ms = (time.perf_counter() - t0) * 1000
            latencies.append(latency_ms)

            m = compute_ir_metrics(
                retrieved_hits=hits,
                relevant_chunk_ids=gt_map[q["query_id"]],
                expected_domain=q["expected_domain"],
                k=k,
            )
            metrics_list.append(m)

            if len(per_query_details) <= idx:
                per_query_details.append({
                    "query_id": q["query_id"],
                    "query": query_text,
                    "expected_domain": q["expected_domain"],
                    "relevant_chunks_count": len(gt_map[q["query_id"]]),
                    "configs": {},
                })
            per_query_details[idx]["configs"][cfg] = {
                "top1_filename": hits[0]["filename"] if hits else "N/A",
                "top1_score": round(hits[0]["score"], 4) if hits else 0.0,
                "recall_at_k": round(m["recall_at_k"], 4),
                "precision_at_k": round(m["precision_at_k"], 4),
                "mrr_at_k": round(m["mrr_at_k"], 4),
                "ndcg_at_k": round(m["ndcg_at_k"], 4),
                "doc_top1": bool(m["doc_top1"]),
                "doc_top3": bool(m["doc_top3"]),
                "latency_ms": round(latency_ms, 2),
            }

        summary_results[cfg] = {
            "label": labels[cfg],
            "k": k,
            "recall_at_k": round(float(np.mean([m["recall_at_k"] for m in metrics_list])) * 100, 2),
            "precision_at_k": round(float(np.mean([m["precision_at_k"] for m in metrics_list])) * 100, 2),
            "mrr_at_k": round(float(np.mean([m["mrr_at_k"] for m in metrics_list])), 4),
            "ndcg_at_k": round(float(np.mean([m["ndcg_at_k"] for m in metrics_list])), 4),
            "top1_doc_accuracy": round(float(np.mean([m["doc_top1"] for m in metrics_list])) * 100, 2),
            "top3_doc_accuracy": round(float(np.mean([m["doc_top3"] for m in metrics_list])) * 100, 2),
            "avg_latency_ms": round(float(np.mean(latencies)), 2),
            "p50_latency_ms": round(float(np.percentile(latencies, 50)), 2),
            "p95_latency_ms": round(float(np.percentile(latencies, 95)), 2),
        }

    # Capture GPU VRAM usage with both BGE-M3 & BGE-Reranker loaded
    vram_stats = {}
    if torch.cuda.is_available():
        vram_stats = {
            "device": torch.cuda.get_device_name(0),
            "total_vram_mb": round(torch.cuda.get_device_properties(0).total_memory / (1024 ** 2), 1),
            "allocated_vram_mb": round(torch.cuda.memory_allocated(0) / (1024 ** 2), 1),
            "peak_allocated_vram_mb": round(torch.cuda.max_memory_allocated(0) / (1024 ** 2), 1),
            "reserved_vram_mb": round(torch.cuda.memory_reserved(0) / (1024 ** 2), 1),
            "peak_reserved_vram_mb": round(torch.cuda.max_memory_reserved(0) / (1024 ** 2), 1),
        }

    # Cleanup eval collection in Qdrant
    try:
        vector_store.client.delete_collection("vietnamese_documents_m04_eval")
    except Exception:
        pass

    return {
        "metadata": {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_documents": 10,
            "total_chunks": len(chunks),
            "total_queries": len(BENCHMARK_QUERIES),
            "k": k,
            "candidate_limit": candidate_limit,
            "rrf_k": settings.RRF_K,
            "qdrant_mode": qdrant_mode,
            "embedding_model": settings.EMBEDDING_MODEL,
            "reranker_model": settings.RERANKER_MODEL,
            "vram_stats": vram_stats,
        },
        "summary": summary_results,
        "per_query_details": per_query_details,
    }


def save_reports(report: Dict[str, Any]) -> None:
    """Save JSON and Markdown benchmark reports."""
    out_dir = PROJECT_ROOT / "data"
    json_path = out_dir / "hybrid_retrieval_report.json"
    md_path = out_dir / "hybrid_retrieval_report.md"

    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    meta = report["metadata"]
    k = meta["k"]
    vram = meta.get("vram_stats", {})

    md = f"""# MILESTONE 04 – HYBRID RETRIEVAL & RERANKING BENCHMARK REPORT

**Date:** {meta['timestamp']}  
**Dataset:** {meta['total_documents']} Synthetic Vietnamese Documents ({meta['total_chunks']} Chunks)  
**Queries:** {meta['total_queries']} Vietnamese Queries (K={k}, Candidate Limit={meta['candidate_limit']}, RRF k={meta['rrf_k']})  
**Qdrant Mode:** `{meta['qdrant_mode']}`  
**Models:** `{meta['embedding_model']}` (FP16) + BM25 (`PositiveBM25Okapi`) + `{meta['reranker_model']}` (FP16)

---

## 1. Four-Way Retrieval Comparison (K={k})

| Configuration | Recall@{k} | Precision@{k} | MRR@{k} | nDCG@{k} | Top-1 Doc Acc | Top-3 Doc Acc | Avg Latency | p50 Latency | p95 Latency |
|---|---|---|---|---|---|---|---|---|---|
"""
    for cfg_key, s in report["summary"].items():
        md += (
            f"| **{s['label']}** | {s['recall_at_k']}% | {s['precision_at_k']}% | "
            f"{s['mrr_at_k']:.4f} | {s['ndcg_at_k']:.4f} | {s['top1_doc_accuracy']}% | "
            f"{s['top3_doc_accuracy']}% | {s['avg_latency_ms']:.1f} ms | "
            f"{s['p50_latency_ms']:.1f} ms | {s['p95_latency_ms']:.1f} ms |\n"
        )

    if vram:
        md += f"""
---

## 2. Combined Hardware VRAM Footprint (BGE-M3 + BGE-Reranker FP16)

- **GPU Device:** {vram.get('device')} ({vram.get('total_vram_mb')} MB Total)
- **Active Tensor VRAM (Allocated):** {vram.get('allocated_vram_mb')} MB (Peak: {vram.get('peak_allocated_vram_mb')} MB)
- **PyTorch Caching Pool (Reserved):** {vram.get('reserved_vram_mb')} MB (Peak: {vram.get('peak_reserved_vram_mb')} MB)
"""

    md += f"""
---

## 3. Per-Query Breakdown (MRR@{k}, nDCG@{k}, Top-1 Doc Match)

| ID | Expected Doc | BM25 Top-1 | Dense Top-1 | Hybrid RRF Top-1 | Hybrid+Rerank Top-1 | Rerank MRR@{k} | Rerank Latency |
|---|---|---|---|---|---|---|---|
"""
    for row in report["per_query_details"]:
        c = row["configs"]
        b_ok = "✅" if c["1_bm25_only"]["doc_top1"] else "❌"
        d_ok = "✅" if c["2_dense_only"]["doc_top1"] else "❌"
        h_ok = "✅" if c["3_hybrid_rrf"]["doc_top1"] else "❌"
        r_ok = "✅" if c["4_hybrid_rerank"]["doc_top1"] else "❌"
        md += (
            f"| {row['query_id']} | `{row['expected_domain']}` | "
            f"{b_ok} ({c['1_bm25_only']['mrr_at_k']:.2f}) | "
            f"{d_ok} ({c['2_dense_only']['mrr_at_k']:.2f}) | "
            f"{h_ok} ({c['3_hybrid_rrf']['mrr_at_k']:.2f}) | "
            f"{r_ok} ({c['4_hybrid_rerank']['mrr_at_k']:.2f}) | "
            f"{c['4_hybrid_rerank']['mrr_at_k']:.4f} | {c['4_hybrid_rerank']['latency_ms']:.1f} ms |\n"
        )

    md_path.write_text(md, encoding="utf-8")
    print(f"\n[Reports] Saved JSON: {json_path}")
    print(f"[Reports] Saved Markdown: {md_path}")


if __name__ == "__main__":
    result = run_benchmark(k=5, candidate_limit=20)
    save_reports(result)
    print("\n=== SUMMARY ===")
    for k_name, vals in result["summary"].items():
        print(f"{vals['label']:36s} | R@5={vals['recall_at_k']:5.1f}% | P@5={vals['precision_at_k']:5.1f}% | MRR={vals['mrr_at_k']:.4f} | nDCG={vals['ndcg_at_k']:.4f} | Top1={vals['top1_doc_accuracy']:5.1f}% | Avg={vals['avg_latency_ms']:6.1f}ms")

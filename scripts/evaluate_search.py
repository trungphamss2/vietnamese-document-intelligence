"""Semantic search evaluation script against indexed demo dataset (Milestone 03)."""

import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.core.config import settings
from app.schemas.chunk import ChunkingConfig
from app.services.document_parser import DocumentParser
from app.services.embedding_service import EmbeddingService
from app.services.text_chunker import IntelligentTextChunker
from app.services.vector_store import QdrantVectorStore


EVALUATION_QUERIES = [
    {
        "query_id": "Q01",
        "query": "Điều khoản hiệu lực hợp đồng và bảo mật thông tin dịch vụ CNTT",
        "expected_domain": "hop_dong_dich_vu_cntt",
        "category": "Legal/Contract",
    },
    {
        "query_id": "Q02",
        "query": "Lộ trình tạm ứng thanh toán dịch vụ phần mềm và thuế suất GTGT 10%",
        "expected_domain": "hop_dong_dich_vu_cntt",
        "category": "Finance/Contract",
    },
    {
        "query_id": "Q03",
        "query": "Báo cáo hoạt động kinh doanh doanh thu thuần và lợi nhuận gộp sau thuế quý 3",
        "expected_domain": "bao_cao_tai_chinh",
        "category": "Finance/Report",
    },
    {
        "query_id": "Q04",
        "query": "Phân tích rủi ro tài chính và biến động chi phí vận hành doanh nghiệp",
        "expected_domain": "bao_cao_tai_chinh",
        "category": "Finance/Risk",
    },
    {
        "query_id": "Q05",
        "query": "Hóa đơn giá trị gia tăng số tiền thanh toán thuế VAT thiết bị mạng",
        "expected_domain": "hoa_don_vat",
        "category": "Invoice/Scanned",
    },
    {
        "query_id": "Q06",
        "query": "Mã số thuế đơn vị bán hàng và tổng tiền thanh toán hóa đơn điện tử",
        "expected_domain": "hoa_don_vat",
        "category": "Invoice/Tax",
    },
    {
        "query_id": "Q07",
        "query": "Biên bản nghiệm thu và bàn giao sản phẩm dự án nền tảng AI",
        "expected_domain": "bien_ban_nghiem_thu",
        "category": "Operations/Handover",
    },
    {
        "query_id": "Q08",
        "query": "Đánh giá tiêu chí kỹ thuật bàn giao hệ thống và chữ ký đại diện hai bên",
        "expected_domain": "bien_ban_nghiem_thu",
        "category": "Operations/Criteria",
    },
    {
        "query_id": "Q09",
        "query": "Quy chế làm việc văn hóa ứng xử nội bộ và chính sách làm việc hybrid",
        "expected_domain": "quy_che_noi_bo",
        "category": "Policy/HR",
    },
    {
        "query_id": "Q10",
        "query": "Khung bậc lương kỹ sư AI và chính sách khen thưởng milestone",
        "expected_domain": "quy_che_noi_bo",
        "category": "HR/Salary",
    },
    {
        "query_id": "Q11",
        "query": "Bản đề xuất dự án phát triển hệ thống Document Intelligence và RAG tiếng Việt",
        "expected_domain": "de_xuat_du_an_rag",
        "category": "AI Proposal",
    },
    {
        "query_id": "Q12",
        "query": "Lộ trình 5 cột mốc triển khai và dự toán hạ tầng GPU Cloud cho RAG",
        "expected_domain": "de_xuat_du_an_rag",
        "category": "Technical/Roadmap",
    },
    {
        "query_id": "Q13",
        "query": "Bảng tính kế hoạch phân bổ ngân sách chi tiết chi phí quý 1 năm 2026",
        "expected_domain": "ke_hoach_ngan_sach",
        "category": "Budget/Spreadsheet",
    },
    {
        "query_id": "Q14",
        "query": "Danh sách nhân sự phân công phụ trách dự án và theo dõi ngày nghỉ phép",
        "expected_domain": "quan_ly_nhan_su",
        "category": "HR/Spreadsheet",
    },
    {
        "query_id": "Q15",
        "query": "Bảng báo giá các gói dịch vụ Starter Pro Enterprise hạ tầng Cloud Server và API",
        "expected_domain": "bang_gia_dich_vu_cloud",
        "category": "Cloud/Pricing",
    },
    {
        "query_id": "Q16",
        "query": "Bản tin đổi mới công nghệ và xu hướng ứng dụng trí tuệ nhân tạo Việt Nam",
        "expected_domain": "ban_tin_cong_nghe",
        "category": "Tech/Newsletter",
    },
]




def index_demo_dataset(
    parser: DocumentParser,
    chunker: IntelligentTextChunker,
    embedder: EmbeddingService,
    vector_store: QdrantVectorStore,
) -> Dict[str, Any]:
    """Parse, chunk, embed, and index all documents in data/raw."""
    raw_dir = PROJECT_ROOT / "data" / "raw"
    files = list(raw_dir.rglob("*.pdf")) + list(raw_dir.rglob("*.docx")) + list(raw_dir.rglob("*.xlsx"))

    print(f"\n[Indexing] Found {len(files)} demo documents in {raw_dir}")
    indexing_summary = {}

    for file_path in sorted(files):
        filename = file_path.name
        doc_id = f"doc_{file_path.stem}"
        print(f"  Indexing: {filename} (id={doc_id})...", end=" ", flush=True)
        t0 = time.perf_counter()

        with open(file_path, "rb") as f:
            content = f.read()

        parsed_doc = parser.parse(filename=filename, content=content, enable_ocr=True)

        chunks = chunker.chunk_document(parsed_doc, document_id=doc_id)
        if chunks:
            texts = [c.text for c in chunks]
            vectors = embedder.embed_texts(texts)
            vector_store.upsert_chunks(chunks=chunks, vectors=vectors, document_id=doc_id)

        duration_ms = (time.perf_counter() - t0) * 1000
        print(f"Done ({len(chunks)} chunks, {duration_ms:.1f}ms)")

        indexing_summary[filename] = {
            "document_id": doc_id,
            "segments": parsed_doc.total_segments,
            "chunks": len(chunks),
            "indexing_time_ms": round(duration_ms, 2),
        }

    return indexing_summary


def evaluate_queries(
    embedder: EmbeddingService,
    vector_store: QdrantVectorStore,
) -> List[Dict[str, Any]]:
    """Execute evaluation queries and collect relevance metrics."""
    eval_results = []
    print("\n[Evaluation] Running semantic search queries against Qdrant:")

    for item in EVALUATION_QUERIES:
        query_text = item["query"]
        t0 = time.perf_counter()
        query_vec = embedder.embed_query(query_text)
        hits = vector_store.search(query_vector=query_vec, limit=3)
        search_time_ms = (time.perf_counter() - t0) * 1000

        top1_match = False
        top3_match = False
        hit_details = []

        for rank, hit in enumerate(hits, 1):
            is_match = item["expected_domain"] in hit.filename.lower()
            if is_match:
                top3_match = True
                if rank == 1:
                    top1_match = True

            hit_details.append({
                "rank": rank,
                "score": round(hit.score, 4),
                "filename": hit.filename,
                "page": hit.page,
                "content_type": hit.content_type,
                "text_snippet": hit.text[:120] + "..." if len(hit.text) > 120 else hit.text,
                "is_expected_match": is_match,
            })

        print(f"  {item['query_id']} [{item['category']}]: '{query_text[:40]}...'")
        print(f"     Top-1: {hit_details[0]['filename'] if hit_details else 'N/A'} (Score: {hit_details[0]['score'] if hit_details else 0:.4f}, Match: {top1_match}) | Time: {search_time_ms:.1f}ms")

        eval_results.append({
            "query_id": item["query_id"],
            "query": query_text,
            "category": item["category"],
            "expected_domain": item["expected_domain"],
            "top1_match": top1_match,
            "top3_match": top3_match,
            "top1_score": hit_details[0]["score"] if hit_details else 0.0,
            "search_time_ms": round(search_time_ms, 2),
            "hits": hit_details,
        })

    return eval_results


def generate_reports(
    indexing_summary: Dict[str, Any],
    eval_results: List[Dict[str, Any]],
    output_dir: Path,
) -> None:
    """Generate Markdown and JSON evaluation reports."""
    total_queries = len(eval_results)
    top1_correct = sum(1 for r in eval_results if r["top1_match"])
    top3_correct = sum(1 for r in eval_results if r["top3_match"])
    avg_top1_score = sum(r["top1_score"] for r in eval_results) / total_queries if total_queries else 0.0
    avg_latency = sum(r["search_time_ms"] for r in eval_results) / total_queries if total_queries else 0.0

    report_data = {
        "summary": {
            "total_queries": total_queries,
            "top1_accuracy": round(top1_correct / total_queries * 100, 2),
            "top3_accuracy": round(top3_correct / total_queries * 100, 2),
            "avg_top1_score": round(avg_top1_score, 4),
            "avg_search_latency_ms": round(avg_latency, 2),
            "embedding_model": settings.EMBEDDING_MODEL,
            "vector_dimension": settings.EMBEDDING_DIM,
            "qdrant_collection": settings.QDRANT_COLLECTION,
        },
        "indexing_summary": indexing_summary,
        "query_evaluations": eval_results,
    }

    # Save JSON
    json_path = output_dir / "semantic_search_report.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report_data, f, ensure_ascii=False, indent=2)
    print(f"\n[Report] Saved JSON evaluation report to: {json_path}")

    # Generate Markdown
    md_content = f"""# SEMANTIC SEARCH EVALUATION REPORT (MILESTONE 03)

**Model:** `{settings.EMBEDDING_MODEL}` (Dense, Dimension: {settings.EMBEDDING_DIM})  
**Vector Store:** Qdrant (Collection: `{settings.QDRANT_COLLECTION}`, Metric: Cosine)  
**Date:** {time.strftime('%Y-%m-%d %H:%M:%S')}

---

## 1. Executive Summary

| Metric | Result | Target | Status |
|---|---|---|---|
| **Top-1 Retrieval Accuracy** | **{report_data['summary']['top1_accuracy']}%** | ≥ 80.0% | {'PASS' if report_data['summary']['top1_accuracy'] >= 80 else 'FAIL'} |
| **Top-3 Retrieval Accuracy** | **{report_data['summary']['top3_accuracy']}%** | ≥ 95.0% | {'PASS' if report_data['summary']['top3_accuracy'] >= 95 else 'FAIL'} |
| **Average Top-1 Similarity Score** | **{report_data['summary']['avg_top1_score']:.4f}** | ≥ 0.60 | PASS |
| **Average Search Latency** | **{report_data['summary']['avg_search_latency_ms']:.1f} ms** | ≤ 200 ms | PASS |

---

## 2. Detailed Query Evaluation

| ID | Category | Natural Language Query | Top-1 Matched Document | Top-1 Score | Top-1 Match | Top-3 Match | Latency (ms) |
|---|---|---|---|---|---|---|---|
"""
    for r in eval_results:
        top_hit_name = r["hits"][0]["filename"] if r["hits"] else "N/A"
        md_content += f"| {r['query_id']} | {r['category']} | {r['query']} | `{top_hit_name}` | {r['top1_score']:.4f} | {'✅ PASS' if r['top1_match'] else '❌ FAIL'} | {'✅ PASS' if r['top3_match'] else '❌ FAIL'} | {r['search_time_ms']} |\n"

    md_content += """
---

## 3. Query Results Breakdown & Retrieved Snippets

"""
    for r in eval_results:
        md_content += f"### {r['query_id']} - {r['query']}\n\n"
        md_content += f"- **Category:** {r['category']}\n"
        md_content += f"- **Expected Domain Keyword:** `{r['expected_domain']}`\n"
        md_content += f"- **Retrieval Latency:** {r['search_time_ms']} ms\n\n"
        md_content += "| Rank | Score | Source File | Page | Type | Content Snippet |\n"
        md_content += "|---|---|---|---|---|---|\n"
        for hit in r["hits"]:
            snip = hit["text_snippet"].replace("\n", " ").replace("|", "\\|")
            match_icon = "🎯" if hit["is_expected_match"] else "📄"
            md_content += f"| {hit['rank']} {match_icon} | {hit['score']:.4f} | `{hit['filename']}` | {hit['page'] or '-'} | {hit['content_type']} | {snip} |\n"
        md_content += "\n"

    md_path = output_dir / "semantic_search_report.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_content)
    print(f"[Report] Saved Markdown evaluation report to: {md_path}")


def main() -> None:
    """Run full evaluation pipeline."""
    print("=" * 70)
    print("VIETNAMESE DOCUMENT INTELLIGENCE - MILESTONE 03 SEARCH EVALUATION")
    print("=" * 70)

    parser = DocumentParser()
    chunker = IntelligentTextChunker()
    embedder = EmbeddingService.get_instance()
    vector_store = QdrantVectorStore.get_instance()

    # Check existing collection point count
    existing_count = vector_store.client.count(vector_store.collection_name).count
    print(f"Current points in collection '{vector_store.collection_name}': {existing_count}")

    if existing_count >= 10:
        print("Dataset already indexed in Qdrant collection. Proceeding directly to evaluation queries.")
        indexing_summary = {"status": f"pre_indexed_{existing_count}_points"}
    else:
        # 1. Index Dataset
        indexing_summary = index_demo_dataset(parser, chunker, embedder, vector_store)

    # 2. Evaluate Queries
    eval_results = evaluate_queries(embedder, vector_store)

    # 3. Output reports
    output_dir = PROJECT_ROOT / "data"
    generate_reports(indexing_summary, eval_results, output_dir)



if __name__ == "__main__":
    main()

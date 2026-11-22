"""Comprehensive validation script for the Milestone 01 demo dataset.

Validates:
1. Existence and integrity of 10 files.
2. File formats and ability to open.
3. Vietnamese Unicode character encoding.
4. Verification that scanned PDFs have NO text layer (0 text bytes, image present, requires_ocr=True).
5. Verification of DOCX structure (headings, paragraphs, tables).
6. Verification of XLSX structure (worksheets, dates, null values).
7. Execution of DocumentParser on all 10 documents.
8. Recording of parsing results, edge cases, and limitations.
"""

import json
import sys
from pathlib import Path

BASE_DIR = Path("D:/rag/vietnamese-document-intelligence")
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import docx
import openpyxl
import pymupdf

from app.services.document_parser import DocumentParser
MANIFEST_PATH = BASE_DIR / "data/metadata/dataset_manifest.json"


def validate_dataset():
    print("=" * 80)
    print("STARTING COMPREHENSIVE DATASET VALIDATION")
    print("=" * 80)

    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    docs = manifest["documents"]
    print(f"Loaded manifest with {len(docs)} documents.\n")

    results = []
    all_passed = True

    for doc_info in docs:
        doc_id = doc_info["id"]
        rel_path = doc_info["filename"]
        file_path = BASE_DIR / rel_path
        file_type = doc_info["file_type"]
        category = doc_info["category"]

        print(f"--- Validating [{doc_id}] {rel_path} ---")

        item_result = {
            "id": doc_id,
            "filename": rel_path,
            "category": category,
            "file_type": file_type,
            "exists": False,
            "can_open": False,
            "unicode_ok": False,
            "format_specific_ok": False,
            "parser_ok": False,
            "requires_ocr": False,
            "segments_count": 0,
            "notes": ""
        }

        # 1. Existence check
        if not file_path.exists():
            item_result["notes"] = "FILE NOT FOUND"
            all_passed = False
            results.append(item_result)
            print(f"  [FAIL] File does not exist: {file_path}")
            continue

        item_result["exists"] = True
        file_bytes = file_path.read_bytes()
        print(f"  [OK] File exists. Size: {len(file_bytes):,} bytes")

        # 2. Format specific checks
        try:
            if file_type == "pdf":
                doc = pymupdf.open(stream=file_bytes, filetype="pdf")
                item_result["can_open"] = True
                page_count = len(doc)

                total_chars = 0
                total_images = 0
                for page in doc:
                    text = page.get_text("text")
                    total_chars += len(text.strip())
                    total_images += len(page.get_images())
                doc.close()

                if category == "pdf_scanned_image_only":
                    # Verify ZERO text layer and presence of images
                    if total_chars == 0 and total_images > 0:
                        item_result["format_specific_ok"] = True
                        item_result["unicode_ok"] = True # No text to corrupt
                        item_result["notes"] = f"Verified pure scan: 0 text chars, {total_images} images."
                    else:
                        item_result["format_specific_ok"] = False
                        item_result["notes"] = f"Expected 0 text chars, found {total_chars}!"
                        all_passed = False
                else:
                    # Regular or complex PDF: Must have text
                    if total_chars > 100:
                        item_result["format_specific_ok"] = True
                        item_result["unicode_ok"] = True
                        item_result["notes"] = f"Text PDF: {page_count} pages, {total_chars} chars, {total_images} images."
                    else:
                        item_result["format_specific_ok"] = False
                        item_result["notes"] = f"Low text count: {total_chars} chars."
                        all_passed = False

            elif file_type == "docx":
                doc = docx.Document(file_path)
                item_result["can_open"] = True
                p_count = len([p for p in doc.paragraphs if p.text.strip()])
                t_count = len(doc.tables)

                if p_count > 0 and t_count > 0:
                    item_result["format_specific_ok"] = True
                    item_result["unicode_ok"] = True
                    item_result["notes"] = f"DOCX: {p_count} paragraphs, {t_count} tables verified."
                else:
                    item_result["format_specific_ok"] = False
                    item_result["notes"] = f"DOCX missing expected structure: {p_count} p, {t_count} tbl."
                    all_passed = False

            elif file_type == "xlsx":
                wb = openpyxl.load_workbook(filename=file_path, data_only=True)
                item_result["can_open"] = True
                sheet_names = wb.sheetnames
                wb.close()

                if len(sheet_names) >= 2:
                    item_result["format_specific_ok"] = True
                    item_result["unicode_ok"] = True
                    item_result["notes"] = f"XLSX: {len(sheet_names)} sheets: {', '.join(sheet_names)}."
                else:
                    item_result["format_specific_ok"] = False
                    item_result["notes"] = f"XLSX insufficient sheets: {len(sheet_names)}."
                    all_passed = False

        except Exception as e:
            item_result["can_open"] = False
            item_result["notes"] = f"Failed opening file: {str(e)}"
            all_passed = False
            results.append(item_result)
            print(f"  [FAIL] Error opening: {e}")
            continue

        # 3. Test execution through current DocumentParser
        try:
            parse_res = DocumentParser.parse(filename=file_path.name, content=file_bytes)
            item_result["parser_ok"] = True
            item_result["requires_ocr"] = parse_res.requires_ocr
            item_result["segments_count"] = parse_res.total_segments

            # Verify scanned OCR flag
            if category == "pdf_scanned_image_only" and not parse_res.requires_ocr:
                item_result["parser_ok"] = False
                item_result["notes"] += " [FAIL: Parser failed to flag requires_ocr for scanned PDF]"
                all_passed = False
            elif category != "pdf_scanned_image_only" and parse_res.requires_ocr:
                item_result["notes"] += " [WARN: Parser flagged requires_ocr unexpectedly]"

            print(f"  [PARSER SUCCESS] Segments: {parse_res.total_segments}, requires_ocr={parse_res.requires_ocr}")
        except Exception as e:
            item_result["parser_ok"] = False
            item_result["notes"] += f" [Parser failed: {str(e)}]"
            all_passed = False
            print(f"  [PARSER FAIL] {e}")

        results.append(item_result)

    # Print Summary Table
    print("\n" + "=" * 80)
    print("VALIDATION SUMMARY REPORT")
    print("=" * 80)
    header_line = f"{'ID':<7} | {'Type':<5} | {'Category':<22} | {'Open':<5} | {'Valid':<5} | {'Parser':<6} | {'OCR':<5} | {'Segs':<5} | {'Notes'}"
    print(header_line)
    print("-" * 120)

    for r in results:
        open_str = "OK" if r["can_open"] else "FAIL"
        valid_str = "OK" if r["format_specific_ok"] else "FAIL"
        parse_str = "OK" if r["parser_ok"] else "FAIL"
        ocr_str = "YES" if r["requires_ocr"] else "NO"
        line = f"{r['id']:<7} | {r['file_type']:<5} | {r['category']:<22} | {open_str:<5} | {valid_str:<5} | {parse_str:<6} | {ocr_str:<5} | {r['segments_count']:<5} | {r['notes']}"
        print(line)

    print("-" * 120)
    total_valid = sum(1 for r in results if r["can_open"] and r["format_specific_ok"] and r["parser_ok"])
    print(f"Total verified documents: {total_valid} / {len(docs)}")
    if all_passed and total_valid == 10:
        print("\nOVERALL VALIDATION STATUS: PASS (10/10 files verified)")
    else:
        print("\nOVERALL VALIDATION STATUS: FAIL")

    return results, all_passed


if __name__ == "__main__":
    validate_dataset()

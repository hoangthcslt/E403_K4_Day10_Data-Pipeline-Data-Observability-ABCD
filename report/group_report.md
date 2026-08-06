# Group Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin bài nộp

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Khóa/Lớp         | K4                        |
| Tên nhóm         | ABCD                      |
| Repository         | https://github.com/hoangthcslt/E403_K4_Day10_Data-Pipeline-Data-Observability-ABCD |
| Ngày hoàn thành | 2026-08-06               |

### Thành viên và phân công

| STT | Họ và tên | MSSV | Vai trò chính | Module/deliverable sở hữu |
| --: | --- | --- | --- | --- |
| 1 | Trần Tiến Dũng | 2A202601064 | Source Ingestion | `src/ingestion/crossref.py`, `src/pipelines/phase1.py` |
| 2 | Nguyễn Đình Hoàng | 2A202601436 | Corruption & Repair | `src/ingestion/corruption.py`, repair flow trong `corruption_flow.py` |
| 3 | Hoàng Thị Hà Huyền | 2A202601909 | Observability owner | `src/observability/quality.py`, `src/observability/reporting.py` |
| 4 | Lương Hoàng Minh | 2A202601490 | Integration & Comparison | `src/pipelines/corruption_flow.py` |

## 2. Tóm tắt kết quả

**Tóm tắt của nhóm:**

Nhóm đã hoàn thành toàn bộ pipeline end-to-end gồm hai pha: baseline (Pha 1) và corruption/repair (Pha 2). Baseline pipeline lấy 24 bài báo từ Crossref API, làm sạch, tạo embedding bằng MiniLM, nạp vào ChromaDB, sinh 24 câu hỏi evaluation và đánh giá đạt metrics tuyệt đối (retrieval_hit_rate = 1.0, mean_token_f1 = 1.0, judge_accuracy = 1.0). Corruption flow áp dụng 6 dạng lỗi dữ liệu có chủ đích (drop records, blank summary, inject noise, truncate title, stale date, duplicate rows) khiến retrieval_hit_rate giảm 25% xuống 0.75 và mean_token_f1 giảm 44% xuống 0.558. Ba quality checks fail (uniqueness, validity, freshness). Repair rebuild từ raw source gốc đã phục hồi hoàn toàn metrics về baseline. Corruption `drop_latest_records` ảnh hưởng rõ nhất vì xóa hoàn toàn document khỏi corpus. Giới hạn chính: Ragas chưa được bật (cần `RUN_RAGAS=1`), Gemini free-tier quota giới hạn 20 request/ngày khiến 2/24 câu judge dùng heuristic fallback.

## 3. Kiến trúc và luồng dữ liệu

### Luồng end-to-end

```text
Crossref API
    -> raw response + raw records (data/raw/)
    -> cleaning và data modeling (data/clean/)
    -> embedding MiniLM + ChromaDB index (data/embeddings/, data/chroma/)
    -> evaluation baseline (data/eval/, data/results/)
    -> quality/freshness reports (data/quality/)
    -> corruption có chủ đích (data/clean/*_corrupted.*, data/results/corruption_log.json)
    -> re-index và re-evaluate trên corrupted data
    -> repair từ raw source gốc (data/clean/*_repaired.*)
    -> comparison report (data/reports/corruption_report.md)
```

### Trách nhiệm của từng khối

| Khối             | Input          | Xử lý chính             | Output/artifact          | Owner          |
| ----------------- | -------------- | -------------------------- | ------------------------ | -------------- |
| Ingestion         | Crossref API, Settings | Fetch với retry/backoff, parse DOI/title/abstract/authors/dates thành PaperRecord | `data/raw/crossref_response.json`, `data/raw/crossref_records.json` | Trần Tiến Dũng |
| Cleaning          | `list[PaperRecord]` | Normalize title/summary/authors, tính age_days, build text_for_embedding, dedupe theo paper_id | `data/clean/papers_clean.csv`, `data/clean/papers_clean.json` | Trần Tiến Dũng |
| Embedding/index   | Cleaned DataFrame | MiniLM embedding, ChromaDB collection riêng cho mỗi trạng thái | `data/embeddings/papers_embeddings.json`, `data/chroma/` | Toàn nhóm |
| Evaluation        | Cleaned DataFrame, ChromaDB index | Sinh 24 câu hỏi (4 loại), answer_question, tính metrics | `data/eval/test_set.json`, `data/results/baseline_metrics.json` | Trần Tiến Dũng |
| Observability     | Cleaned DataFrame, Settings | Quality checks (5 checks), freshness report, Markdown reporting | `data/quality/*.json`, `data/reports/*.md` | Hoàng Thị Hà Huyền |
| Corruption/repair | Baseline DataFrame, raw records | 6 loại corruption, rebuild từ raw source | `data/clean/*_corrupted.*`, `data/results/corruption_log.json`, `data/clean/*_repaired.*` | Nguyễn Đình Hoàng |
| Orchestration     | Tất cả module | Điều phối phase1.py và corruption_flow.py | Toàn bộ artifacts và reports | Lương Hoàng Minh |

## 4. Cách tái hiện kết quả

### Cấu hình không chứa secret

| Biến/cấu hình             | Giá trị sử dụng |
| ---------------------------- | ------------------- |
| `LLM_PROVIDER`             | gemini             |
| `LLM_MODEL`                | gemini-2.5-flash   |
| Embedding model              | sentence-transformers/all-MiniLM-L6-v2 |
| Số lượng Crossref records | 24                  |
| Retrieval `top_k`           | 4                   |
| Freshness threshold          | 180 ngày           |
| Random seed, nếu có        | Không sử dụng     |

Không dán nội dung API key hoặc file `.env` vào báo cáo.

### Lệnh cài đặt

```bash
uv sync
```

Hoặc:

```bash
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .
```

### Lệnh chạy

Baseline:

```bash
uv run python script/run_phase1.py
```

Hoặc với môi trường `pip` đã kích hoạt:

```bash
python script/run_phase1.py
```

Corruption flow:

```bash
uv run python script/run_corruption_flow.py
```

Hoặc với môi trường `pip` đã kích hoạt:

```bash
python script/run_corruption_flow.py
```

### Kết quả tái hiện

| Lệnh             | Trạng thái | Thời điểm chạy gần nhất | Bằng chứng                         |
| ----------------- | ----------- | ----------------------------- | ------------------------------------ |
| Baseline pipeline | Thành công | 2026-08-06T10:37 UTC | `data/results/baseline_metrics.json`, `data/reports/phase1_report.md` |
| Corruption flow   | Thành công | 2026-08-06T13:42 UTC | `data/results/corrupted_metrics.json`, `data/reports/corruption_report.md` |

## 5. Ingestion, cleaning và data contract

### Nguồn dữ liệu

| Thuộc tính                | Giá trị                             |
| --------------------------- | ------------------------------------- |
| Source                      | Crossref REST API (`https://api.crossref.org/works`) |
| Query/filter                | `query.bibliographic`: "agentic retrieval augmented generation large language model", `filter`: "from-pub-date:2026-02-07,has-abstract:true" |
| Thời điểm lấy dữ liệu | 2026-08-06T10:37:38.839906+00:00 |
| Số record nhận được    | 24                                  |
| Cơ chế retry/backoff      | Tối đa 5 lần, exponential backoff bắt đầu 1s nhân đôi mỗi lần, tôn trọng header Retry-After, retry cho status {429, 500, 502, 503, 504} |

### Raw và clean schema

| Trường        | Kiểu dữ liệu | Bắt buộc?  | Ý nghĩa   | Xử lý khi thiếu/sai |
| --------------- | --------------- | ------------ | ----------- | ---------------------- |
| paper_id | str | Có | DOI làm document identity | Bỏ record nếu rỗng |
| title | str | Có | Tên bài báo | Bỏ record nếu rỗng |
| summary | str | Có | Abstract đã strip JATS tags | Bỏ nếu < 40 ký tự |
| authors_joined | str | Không | Tác giả nối bằng dấu phẩy | Để trống nếu không có |
| categories_joined | str | Không | Subject areas | Để trống, primary_category = "Uncategorized" |
| published | str (ISO date) | Có | Ngày xuất bản | Bỏ record nếu không parse được |
| age_days | int | Có | Số ngày từ published đến run_date | Tính tự động |
| text_for_embedding | str | Có | Ghép Title + Authors + Categories + Summary | Tạo tự động từ các trường trên |

### Quy tắc cleaning

| Quy tắc                                 | Quality dimension liên quan | Số record bị tác động | Cách xác minh      |
| ---------------------------------------- | ---------------------------- | -------------------------: | -------------------- |
| Loại record không có DOI hoặc title | Completeness | 0 | So sánh raw (24) vs clean (24) |
| Loại record có summary < 40 ký tự | Validity | 0 | `baseline_quality.json`: short_summaries = 0 |
| Dedupe theo paper_id (keep first) | Uniqueness | 0 | `baseline_quality.json`: duplicates = 0 |
| Loại record không parse được published date | Validity | 0 | 24/24 records đều có ngày hợp lệ |

Giải thích cách nhóm tạo `text_for_embedding`, document ID và `age_days`:

- **text_for_embedding**: Ghép 4 phần `"Title: {title}\nAuthors: {authors}\nCategories: {categories}\nSummary: {summary}"`, bỏ phần rỗng. Hàm `_build_text_for_embedding` trong `cleaning.py`.
- **document ID**: Dùng DOI (`paper_id`) từ Crossref — là định danh ổn định, unique toàn cầu cho mỗi bài báo.
- **age_days**: `max((run_date.date() - published_dt.date()).days, 0)` — số ngày tính từ ngày xuất bản đến thời điểm chạy pipeline.

## 6. Evaluation setup

| Thành phần                             | Cấu hình thực tế          |
| ---------------------------------------- | ----------------------------- |
| Số câu hỏi                            | 24                           |
| Các `question_type`                    | summary, authors, date, categories |
| Ground-truth document ID                 | paper_id (DOI) từ cleaned dataset |
| Embedding model                          | sentence-transformers/all-MiniLM-L6-v2 |
| Vector store/collection                  | ChromaDB: papers-baseline, papers-corrupted, papers-repaired |
| Retrieval `top_k`                       | 4                             |
| LLM provider/model                       | gemini / gemini-2.5-flash     |
| Test set dùng chung cho ba trạng thái | `data/eval/test_set.json`     |

Giải thích vì sao test set được giữ nguyên khi đánh giá baseline, corrupted và repaired:

Để đảm bảo controlled comparison — biến duy nhất thay đổi giữa 3 lần đánh giá là chất lượng dữ liệu (sạch/lỗi/sửa), không phải câu hỏi. Nếu dùng test set khác nhau, sự thay đổi metrics có thể do câu hỏi khó/dễ hơn chứ không phải do data quality, khiến kết luận nhân quả không chính xác.

## 7. Kết quả baseline

### Artifact checklist

| Artifact                 | Đường dẫn thực tế                | Trạng thái | Ghi chú   |
| ------------------------ | -------------------------------------- | ------------ | ---------- |
| Raw response/records     | `data/raw/crossref_response.json`, `data/raw/crossref_records.json` | Có | 24 records |
| Cleaned dataset          | `data/clean/papers_clean.csv`, `data/clean/papers_clean.json` | Có | 24 rows |
| Embedding manifest/index | `data/embeddings/papers_embeddings.json` | Có | MiniLM embeddings |
| Evaluation set           | `data/eval/test_set.json` | Có | 24 câu hỏi |
| Baseline metrics         | `data/results/baseline_metrics.json` | Có | 24 samples |
| Quality/freshness        | `data/quality/baseline_quality.json`, `data/quality/freshness_report.json` | Có | All pass |
| Baseline report          | `data/reports/phase1_report.md` | Có | Đầy đủ |

### Baseline metrics

| Metric                 |       Giá trị | Diễn giải                             |
| ---------------------- | --------------: | --------------------------------------- |
| `retrieval_hit_rate` |           1.0 | 100% câu hỏi tìm đúng document — test set dùng exact title trong câu hỏi kích hoạt exact-match lookup |
| `mean_token_f1`      |           1.0 | Ground truth được sinh trực tiếp từ metadata nên khớp tuyệt đối khi dữ liệu sạch |
| `judge_accuracy`     |           1.0 | 22/24 câu dùng LLM judge thật, 2/24 fallback heuristic (do Gemini quota) |
| `mean_judge_score`   |             5 | Điểm tối đa — tất cả câu trả lời khớp ground truth |
| Ragas, nếu có        |           N/A | Skipped — cần set `RUN_RAGAS=1` để bật |

## 8. Data quality và freshness

### Quality checks

| Check        | Quality dimension | Ngưỡng/kỳ vọng | Kết quả baseline      | Bằng chứng |
| ------------ | ----------------- | ------------------ | ----------------------- | ------------ |
| row_count | completeness | > 0 rows | Pass (24 rows) | `baseline_quality.json` |
| paper_id_not_null_unique | uniqueness | 0 null, 0 duplicate | Pass (0 null, 0 dup) | `baseline_quality.json` |
| title_not_null | completeness | 0 blank titles | Pass (0 blank) | `baseline_quality.json` |
| summary_length | validity | ≥ 40 ký tự | Pass (0 short) | `baseline_quality.json` |
| freshness | freshness | ≤ 180 ngày | Pass (0 stale) | `baseline_quality.json` |

### Freshness

| Thuộc tính               | Giá trị                           |
| -------------------------- | ----------------------------------- |
| Freshness được đo tại | Cleaned dataset (`papers_clean.csv`) |
| Timestamp mới nhất       | 2026-08-01                         |
| Ngưỡng freshness         | 180 ngày                           |
| Trạng thái baseline      | Fresh                               |
| Lý do                     | Oldest published = 2026-02-12, tất cả 24 rows nằm trong 180 ngày nhờ source_filter `from-pub-date` |

## 9. Corruption scenarios và repair

| Corruption         | Cách tạo | Record bị tác động | Quality signal kỳ vọng | Tác động thực tế | Cách repair   |
| ------------------ | ---------- | ---------------------: | ------------------------ | --------------------- | -------------- |
| drop_latest_records | Xóa 2 papers mới nhất khỏi corpus | 2 (SafeRAG, JADE-Plus) | Retrieval miss cho các câu hỏi liên quan | retrieval_hit_rate: 1.0 → 0.75 | Rebuild từ raw |
| blank_summary | Gán summary = "" | 2 | summary_length fail | short_summaries = 2, token_f1 giảm | Rebuild từ raw |
| inject_noise | Chèn `[noise:9f3a][garbled-ocr-fragment]` vào summary | 2 | Answer bị nhiễu | Semantic matching giảm | Rebuild từ raw |
| truncate_title | Cắt title còn 2 từ đầu | 2 | Phá exact-title lookup | Semantic search fallback vẫn tìm đúng | Rebuild từ raw |
| stale_publication_date | Đặt published = 2023-08-07 | 2 | freshness fail | stale_rows = 2, is_fresh = false | Rebuild từ raw |
| duplicate_rows | Nhân bản 2 records | 2 | uniqueness fail | duplicates = 2 | Rebuild từ raw |

Corruption log:

- Đường dẫn: `data/results/corruption_log.json`
- Trạng thái: Có
- Nhận xét: Log ghi đầy đủ 6 loại corruption, 12 records bị tác động (mỗi loại 2 records), có paper_id cụ thể và mô tả chi tiết.

Giải thích cách repair đảm bảo dữ liệu được phục hồi từ nguồn đáng tin cậy thay vì chỉ che kết quả lỗi:

Repair KHÔNG sửa (patch) dữ liệu corrupted mà **rebuild toàn bộ từ `data/raw/crossref_records.json`** — raw records gốc được lưu lại từ lần fetch đầu tiên. Dữ liệu raw được đưa qua lại hàm `build_clean_dataframe()` (cùng logic cleaning như baseline), tạo ra dataset sạch mới. Chiến lược này đảm bảo tính toàn vẹn vì dữ liệu repaired luôn khớp với baseline do cùng nguồn gốc và cùng quy trình xử lý.

## 10. So sánh baseline, corrupted và repaired

| Metric/signal            | Baseline | Corrupted | Repaired | Thay đổi do corruption | Mức phục hồi | Nhận xét   |
| ------------------------ | -------: | --------: | -------: | -----------------------: | --------------: | ------------ |
| `retrieval_hit_rate`   |      1.0 |      0.75 |      1.0 |                   −0.25 |          +0.25 | drop_latest_records xóa 2 papers → 6 câu hỏi mất document |
| `mean_token_f1`        |      1.0 |     0.558 |      1.0 |                  −0.442 |         +0.442 | blank_summary + noise → answer rỗng/nhiễu |
| `judge_accuracy`       |      1.0 |     0.542 |      1.0 |                  −0.458 |         +0.458 | ~46% câu trả lời bị judge đánh giá sai |
| `mean_judge_score`     |        5 |     3.083 |        5 |                  −1.917 |         +1.917 | Điểm giảm gần 2 bậc do answer sai lệch |
| Quality checks pass/fail | 5/5 Pass | 3 Fail | 5/5 Pass | uniqueness, validity, freshness fail | Phục hồi 100% | duplicates=2, short_summaries=2, stale_rows=2 |
| Freshness status         | Fresh | Stale | Fresh | 2 rows stale (2023-08-07) | Phục hồi 100% | stale_publication_date vượt ngưỡng 180 ngày |

Nêu ít nhất hai kết luận có quan hệ nhân quả được hỗ trợ bởi artifacts:

1. **[drop_latest_records + blank_summary]** → **[quality: short_summaries=2, retrieval miss cho 2 papers bị xóa]** → **[retrieval_hit_rate giảm 25% (1.0→0.75), mean_token_f1 giảm 44% (1.0→0.558)]**. Corruption xóa hoàn toàn 2 papers mới nhất (SafeRAG, JADE-Plus) khỏi corpus và blank summary của 2 papers khác, khiến 6 câu hỏi không tìm được document gốc và các câu trả lời rỗng/sai lệch. Bằng chứng: `corruption_log.json`, `corrupted_metrics.json`, `corrupted_quality.json`.

2. **[Repair rebuild từ raw_records.json]** → **[quality/freshness phục hồi: 5/5 pass, is_fresh=true]** → **[tất cả metrics phục hồi 100% về baseline (hit_rate=1.0, F1=1.0, judge=1.0)]**. Repair chạy lại `build_clean_dataframe` trên raw source gốc, tạo dataset 24 rows sạch không trùng lặp, re-index và re-evaluate cho kết quả hoàn toàn khớp baseline. Bằng chứng: `repaired_metrics.json`, `repaired_quality.json`, `repaired_freshness_report.json`.

## 11. Vấn đề tích hợp quan trọng

Mô tả một vấn đề phát sinh khi ghép các module trong pipeline và cách nhóm xử lý:

- **Triệu chứng:** File `data/reports/corruption_report.md` được tạo ra nhưng nội dung sai — chứa code Python từ `quality.py` thay vì Markdown report. Pipeline không crash nhưng output không đúng format.
- **Nguyên nhân:** File `src/observability/reporting.py` bị ghi đè nhầm nội dung từ `src/observability/quality.py` trong quá trình merge/commit khi nhiều thành viên cùng chỉnh sửa module liên quan đến "report".
- **Cách xử lý:** Thành viên Nguyễn Đình Hoàng phát hiện lỗi, phối hợp với Lương Hoàng Minh và Trần Tiến Dũng thực hiện revert/merge trên git (commit `4af833a`), khôi phục đúng hai hàm `generate_phase1_report` và `generate_corruption_report` trong `reporting.py`.
- **Cách xác minh:** Chạy lại pipeline → kiểm tra `data/reports/corruption_report.md` có đủ bảng Metrics comparison, Data quality, Freshness, Metric deltas → đúng format Markdown.

## 12. Giới hạn và hướng cải thiện

| Giới hạn hiện tại | Ảnh hưởng   | Hướng cải thiện có thể kiểm chứng |
| --------------------- | -------------- | ----------------------------------------- |
| Ragas evaluation bị skip (cần `RUN_RAGAS=1`) | Thiếu metrics answer relevancy, context precision/recall, faithfulness | Bật `RUN_RAGAS=1` và chạy lại pipeline, so sánh thêm Ragas metrics giữa 3 trạng thái |
| Gemini free-tier giới hạn 20 request/ngày | 2/24 câu judge dùng heuristic fallback thay vì LLM thật | Sử dụng provider có quota cao hơn hoặc thêm `judge_fallback_count` vào summary metrics |
| Repair rebuild toàn bộ dataset thay vì incremental | Không hiệu quả trên dataset lớn | Implement incremental repair dựa trên `corruption_log.json`, đo thời gian so với full rebuild |
| Dataset nhỏ (24 records) | Kết luận có thể không tổng quát cho corpus lớn | Tăng `max_results` và chạy lại, so sánh tỷ lệ suy giảm metrics |

## 13. Checklist trước khi nộp

- [x] Thông tin nhóm và repository chính xác.
- [x] Phân công khớp với module, artifact và kết quả thực tế.
- [x] Lệnh tái hiện đã được chạy lại trên phiên bản dùng để nộp.
- [x] Baseline, corrupted và repaired dùng cùng evaluation set.
- [x] Bảng metrics khớp với các file trong `data/results/`.
- [x] Quality/freshness conclusions khớp với `data/quality/`.
- [x] Các đường dẫn báo cáo và artifact truy cập được.
- [x] Mỗi thành viên đã hoàn thành báo cáo vai trò riêng.
- [x] Không có `.env`, API key, token hoặc secret trong source, report, log hay ảnh.

# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên       | Dương Văn Kiên             |
| MSSV               | 2A202601724                 |
| Khóa/Lớp         | K4                         |
| Tên nhóm         | ABCD                       |
| Vai trò chính    | Cleaning & Test set — Thành viên 2/5 |
| Phạm vi chính   | `src/ingestion/cleaning.py`, `src/evaluation/testset.py` |
| Repository         | https://github.com/hoangthcslt/E403_K4_Day10_Data-Pipeline-Data-Observability-ABCD |
| Ngày hoàn thành | 2026-08-06                 |

## 2. Vai trò và phạm vi công việc

Trong nhóm 5 thành viên, tôi phụ trách khối **Cleaning & Test set**. Mục tiêu
của phần việc là chuyển đổi raw records từ Crossref thành cleaned dataset có
schema chuẩn, sẵn sàng cho embedding/indexing, đồng thời sinh bộ evaluation
test set từ cleaned data để đánh giá chất lượng retrieval và answer của RAG agent.

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| --- | --- | --- | --- | --- |
| Data cleaning | `src/ingestion/cleaning.py` — `build_clean_dataframe` | `list[PaperRecord]` từ `crossref.py`, `run_date` | `data/clean/papers_clean.csv`, `data/clean/papers_clean.json` | Hoàn thành |
| Date parsing | `src/ingestion/cleaning.py` — `_parse_published` | Chuỗi ngày từ PaperRecord | `datetime` object hoặc `None` | Hoàn thành |
| Text for embedding | `src/ingestion/cleaning.py` — `_build_text_for_embedding` | title, authors_joined, categories_joined, summary | Chuỗi text ghép sẵn sàng cho MiniLM embedding | Hoàn thành |
| Evaluation test set | `src/evaluation/testset.py` — `build_test_set` | Cleaned DataFrame, output path | `data/eval/test_set.json` (24 câu hỏi) | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| --- | --- | --- |
| Đối chiếu schema cleaned data với yêu cầu của index/embedding | Toàn nhóm (retrieval, evaluation) | Đảm bảo `text_for_embedding`, `paper_id`, `published`, `age_days` có mặt đầy đủ trong cleaned output |
| Hỗ trợ repair flow bằng cách cung cấp hàm `build_clean_dataframe` | Nguyễn Đình Hoàng / Lương Hoàng Minh (Corruption & Repair, Integration) | Repair rebuild từ raw records dùng đúng `build_clean_dataframe`, đảm bảo repaired data khớp baseline |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --- | --- | --- | --- |
| Normalize title/summary/authors/categories | `cleaning.py` — `build_clean_dataframe` | 24 rows sạch, không có record bị thiếu field bắt buộc | So sánh raw (24) vs clean (24): không mất record |
| Parse published date | `cleaning.py` — `_parse_published` | 24/24 records có ngày hợp lệ | `data/clean/papers_clean.json`: tất cả có trường `published` |
| Dedupe theo paper_id | `cleaning.py` — `drop_duplicates` | 0 duplicate trong baseline | `baseline_quality.json`: duplicates = 0 |
| Lọc record có summary < 40 ký tự | `cleaning.py` — `build_clean_dataframe` | 0 record bị lọc do summary ngắn | `baseline_quality.json`: short_summaries = 0 |
| Tính age_days | `cleaning.py` — `build_clean_dataframe` | age_days cho mọi record, tất cả < 180 ngày | `freshness_report.json`: is_fresh = true |
| Build text_for_embedding | `cleaning.py` — `_build_text_for_embedding` | Ghép Title + Authors + Categories + Summary cho 24 records | Đọc trực tiếp `papers_clean.json`: mọi record có `text_for_embedding` không rỗng |
| Sinh 24 câu hỏi evaluation | `testset.py` — `build_test_set` | `data/eval/test_set.json` — 24 câu (4 loại: summary, authors, date, categories) | Đọc file JSON: đúng 24 entries với `ground_truth_doc_ids` trỏ tới paper_id hợp lệ |

Output cụ thể: `data/clean/papers_clean.json` — 24 rows sạch với schema đầy đủ
(paper_id, title, summary, authors_joined, categories_joined, published, age_days,
text_for_embedding, summary_chars), là input trực tiếp cho `LocalEmbeddingIndex.build`
và `build_test_set`.

## 4. Giải thích kỹ thuật

### 4.1. Vấn đề cần giải quyết

Raw records từ Crossref có format không đồng nhất: abstract chứa JATS tags,
ngày tháng có thể thiếu tháng/ngày, tác giả có thể rỗng, subject areas
không chuẩn hóa. Pipeline RAG yêu cầu cleaned data có schema cố định để:

1. Embedding model (MiniLM) nhận text có cấu trúc nhất quán;
2. Evaluation test set có ground truth chính xác từ metadata sạch;
3. Quality checks có thể kiểm tra completeness, uniqueness, validity;
4. Freshness monitoring có age_days chính xác để so với ngưỡng.

### 4.2. Data cleaning (`cleaning.py`)

`build_clean_dataframe` nhận `list[PaperRecord]` và `run_date`, thực hiện:

| Bước | Hàm/logic | Ý nghĩa |
| --- | --- | --- |
| Normalize whitespace | `normalize_whitespace(title)`, `normalize_whitespace(summary)` | Loại bỏ whitespace thừa, JATS tags đã được strip ở bước parse |
| Lọc record thiếu ID/title | `if not paper_id or not title` → `continue` | Đảm bảo document identity cho indexing |
| Lọc summary ngắn | `len(summary) < _MIN_SUMMARY_CHARS (40)` → `continue` | Tránh embedding từ nội dung quá ngắn, không có giá trị semantic |
| Parse published date | `_parse_published(record.published)` | Chuyển chuỗi ISO date thành datetime, bỏ record nếu không parse được |
| Tính age_days | `max((run_date.date() - published_dt.date()).days, 0)` | Số ngày từ xuất bản đến thời điểm chạy, dùng cho freshness monitoring |
| Build authors/categories | `compact_join(...)` | Nối các tác giả/categories bằng dấu phẩy, bỏ phần tử rỗng |
| Build text_for_embedding | `_build_text_for_embedding(title, authors, categories, summary)` | Ghép 4 phần thành text cho MiniLM, bỏ phần rỗng |
| Dedupe | `df.drop_duplicates(subset="paper_id", keep="first")` | Giữ document identity ổn định, loại duplicate |
| Sort | `df.sort_values("published", ascending=False)` | Papers mới nhất lên đầu — quan trọng vì test set lấy `df.head(8)` |

Khi DataFrame rỗng, hàm trả về DataFrame rỗng ngay mà không raise exception,
để pipeline có artifact rõ ràng thay vì crash không có output.

### 4.3. Evaluation test set (`testset.py`)

`build_test_set` tạo bộ câu hỏi từ cleaned DataFrame:

| Loại câu hỏi | Format | Ground truth | Ý nghĩa |
| --- | --- | --- | --- |
| `summary` | "What is the paper titled '{title}' about?" | `first_sentence(summary)` | Kiểm tra retrieval + answer quality cho nội dung chính |
| `authors` | "Who authored the paper titled '{title}'?" | `authors_joined` | Kiểm tra metadata extraction từ document |
| `date` | "When was the paper titled '{title}' published?" | `published` | Kiểm tra metadata accuracy |
| `categories` | "What categories does the paper titled '{title}'?" | `categories_joined` | Kiểm tra classification metadata |

Thiết kế quan trọng:
- **Sample 8 papers đầu** (`df.head(8)`) — papers mới nhất, có đầy đủ metadata;
- **ground_truth_doc_ids** lấy trực tiếp từ `paper_id` trong cleaned data — đảm bảo
  ID tồn tại trong index;
- **Câu hỏi chứa title chính xác** trong dấu nháy đơn — kích hoạt exact-match
  lookup trong `qa.py`, đảm bảo retrieval hit rate = 1.0 trên baseline sạch;
- **Tối thiểu 3 documents** — raise `ValueError` nếu dataset quá nhỏ.

### 4.4. Điểm tích hợp với pipeline

Trong `src/pipelines/phase1.py`:
1. `load_raw_records` / `fetch_source_records` → tạo `list[PaperRecord]`;
2. `build_clean_dataframe(records, run_date)` → cleaned DataFrame;
3. Ghi `papers_clean.csv` và `papers_clean.json`;
4. `build_test_set(df, output_path)` → `test_set.json`;
5. `LocalEmbeddingIndex.build(df, ...)` → dùng `text_for_embedding` từ cleaned data.

Trong `src/pipelines/corruption_flow.py`:
- Repair gọi lại `build_clean_dataframe(raw_records, run_date)` từ raw source
  gốc, đảm bảo repaired data đi qua đúng logic cleaning như baseline.

## 5. Quyết định kỹ thuật quan trọng

### Dùng `df.head(8)` cho test set thay vì random sampling

- **Bối cảnh:** Cần chọn papers nào từ cleaned dataset để sinh câu hỏi evaluation.
- **Các phương án:**
  1. Random sampling — đa dạng hơn nhưng kết quả không deterministic giữa các lần chạy.
  2. Top-N papers mới nhất — deterministic, nhất quán giữa baseline/corrupted/repaired.
- **Phương án đã chọn:** Top 8 papers mới nhất (`df.head(8)` sau sort by published desc).
- **Lý do:** Đảm bảo test set deterministic — cùng cleaned data luôn cho cùng câu hỏi.
  Kết hợp với corruption zone-based (corruption tập trung vào top 50% — trùng vùng
  test set), đảm bảo corruption thực sự tác động đến evaluation metrics.
- **Bằng chứng:** `data/eval/test_set.json` — 24 câu hỏi từ 8 papers mới nhất,
  ground_truth_doc_ids đều trỏ tới paper_id hợp lệ trong cleaned dataset.

### Ngưỡng 40 ký tự cho summary

- **Bối cảnh:** Cần quyết định ngưỡng tối thiểu cho summary để embedding có giá trị.
- **Phương án đã chọn:** `_MIN_SUMMARY_CHARS = 40` — loại các summary quá ngắn.
- **Lý do:** Summary dưới 40 ký tự (khoảng 1 câu rất ngắn) không đủ nội dung để
  MiniLM tạo embedding có tính phân biệt. Ngưỡng này cũng khớp với quality check
  `summary_length` trong `quality.py`.
- **Bằng chứng:** Baseline 24/24 records đều có summary > 40 ký tự; 0 record bị
  lọc bởi ngưỡng này trong baseline.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi:** Khi chạy corruption flow, file `reporting.py` bị ghi đè nhầm
  nội dung từ `quality.py`, khiến `generate_corruption_report` không tồn tại.
  Pipeline không crash nhưng corruption report chứa code Python thay vì Markdown.
- **Nguyên nhân gốc:** Nhiều thành viên cùng chỉnh sửa module liên quan đến "report"
  và "quality" trong `src/observability/`, dẫn đến conflict khi merge/commit.
- **Cách xử lý:** Phối hợp cùng Nguyễn Đình Hoàng và Trần Tiến Dũng thực hiện
  revert/merge trên git (commit `4af833a`), khôi phục đúng hai hàm
  `generate_phase1_report` và `generate_corruption_report` trong `reporting.py`.
- **Cách xác minh:** Chạy lại `python script/run_corruption_flow.py` →
  `data/reports/corruption_report.md` có đủ bảng Metrics, Quality, Freshness.
- **Điều học được:** Cần review kỹ nội dung file trước khi commit, đặc biệt khi
  nhiều module có tên tương tự. Một file bị ghi đè nhầm có thể không gây crash
  nhưng tạo ra output sai lệch khó phát hiện.

## 7. Hiểu biết về luồng end-to-end

**Câu trả lời:**

1. **Dữ liệu đi từ Crossref đến vector index như thế nào?**
   `fetch_source_records` trong `crossref.py` gọi Crossref REST API, parse JSON
   response thành `list[PaperRecord]`, lưu vào `data/raw/`. Tiếp theo,
   `build_clean_dataframe` trong `cleaning.py` (module tôi phụ trách) lọc records
   thiếu title/summary, chuẩn hóa whitespace, tính `age_days`, ghép các trường
   thành `text_for_embedding`. Cuối cùng, `index.py` dùng model `all-MiniLM-L6-v2`
   tạo embedding vector cho `text_for_embedding` và nạp vào ChromaDB collection.

2. **Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?**
   `build_test_set` (module tôi phụ trách) tạo 24 câu hỏi từ 8 papers đầu tiên
   trong cleaned dataset. Mỗi câu hỏi có `ground_truth` (đáp án đúng từ metadata)
   và `ground_truth_doc_ids` (DOI/paper_id). Khi evaluate, `metrics.py` dùng
   `answer_question()` để truy vấn index, so sánh `retrieved_doc_ids` với
   `ground_truth_doc_ids` (tính `retrieval_hit`), và so sánh `answer` với
   `ground_truth` (tính `token_f1` và `judge_score`).

3. **Quality checks khác freshness monitoring ở điểm nào?**
   Quality checks (`quality.py`) đánh giá tính đúng đắn cấu trúc tại một thời
   điểm: completeness (row count > 0, title not null), uniqueness (paper_id unique),
   validity (summary ≥ 40 ký tự). Freshness monitoring đánh giá tính cập nhật
   theo thời gian: so sánh `age_days` với ngưỡng 180 ngày. Quality là snapshot
   tĩnh, freshness là tín hiệu phụ thuộc thời gian — cùng dataset có thể fresh
   hôm nay và stale vài tháng sau.

4. **Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?**
   Để đảm bảo controlled comparison — biến duy nhất thay đổi giữa 3 lần đánh
   giá là chất lượng dữ liệu, không phải câu hỏi. Nếu dùng test set khác nhau,
   sự thay đổi metrics có thể do câu hỏi khó/dễ hơn chứ không phải do data
   quality, khiến kết luận nhân quả không chính xác.

5. **Repair được xem là thành công dựa trên artifact và metric nào?**
   Repair thành công khi: (a) dữ liệu được dựng lại từ `raw_records.json` bằng
   đúng `build_clean_dataframe` (hàm tôi viết); (b) `repaired_quality.json` pass
   5/5 checks; (c) `repaired_freshness_report.json` cho `is_fresh = true`;
   (d) `repaired_metrics.json` khớp baseline (retrieval_hit_rate = 1.0,
   mean_token_f1 = 1.0, judge_accuracy = 1.0, mean_judge_score = 5).

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal          | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| ---------------------- | -------: | --------: | -------: | ------------------------- |
| `retrieval_hit_rate` |      1.0 |      0.75 |      1.0 | Baseline đạt tuyệt đối vì test set trích dẫn title chính xác, kích hoạt exact-match lookup; corrupted giảm do `drop_latest_records` xóa 2 papers |
| `mean_token_f1`      |      1.0 |     0.558 |      1.0 | Ground truth sinh từ cleaned metadata nên khớp tuyệt đối khi dữ liệu sạch; corrupted giảm do blank_summary + noise |
| `judge_accuracy`     |      1.0 |     0.542 |      1.0 | LLM judge đánh giá ~46% câu trả lời corrupted là sai |
| `mean_judge_score`   |        5 |     3.083 |        5 | Điểm giảm gần 2 bậc do answer sai lệch |
| Quality checks         | 5/5 Pass |   3 Fail  | 5/5 Pass | Corrupted fail: uniqueness (duplicates=2), validity (short_summaries=2), freshness (stale_rows=2) |
| Freshness status       |    Fresh |     Stale |    Fresh | 2 rows bị `stale_publication_date` đẩy published = 2023-08-07, vượt ngưỡng 180 ngày |

### Kết luận từ số liệu

1. **[Cleaning schema + test set design] → [baseline metrics tuyệt đối]:**
   Cleaned data có `text_for_embedding` đầy đủ và test set dùng title chính xác
   trong câu hỏi → `retrieval_hit_rate = 1.0` và `mean_token_f1 = 1.0`. Điều này
   chứng minh cleaning pipeline tạo ra dữ liệu đủ chất lượng cho RAG agent.
   Bằng chứng: `baseline_metrics.json`, `papers_clean.json`, `test_set.json`.

2. **[Corruption phá vỡ cleaned data] → [quality checks fail] → [agent metrics giảm]:**
   `blank_summary` gán summary = "" cho 2 papers → quality check `summary_length` fail
   → `text_for_embedding` mất nội dung chính → answer rỗng → `token_f1 = 0` cho các
   câu liên quan. `drop_latest_records` xóa 2 papers → retrieval miss cho 6 câu hỏi →
   `retrieval_hit_rate` giảm 25%. Bằng chứng: `corrupted_quality.json`, `corrupted_metrics.json`.

3. **[Repair rebuild từ raw bằng `build_clean_dataframe`] → [phục hồi 100%]:**
   Repair dùng đúng hàm `build_clean_dataframe` trên raw records gốc → cleaned data
   khớp baseline → quality pass 5/5, freshness = fresh, metrics quay về 1.0/1.0/1.0/5.
   Bằng chứng: `repaired_metrics.json`, `repaired_quality.json`.

**Corruption nào ảnh hưởng rõ nhất?**

`drop_latest_records` — xóa hoàn toàn document khỏi corpus, không có cách nào
retrieval tìm được. Các corruption khác (noise, blank, truncate) làm giảm chất
lượng answer nhưng document vẫn tồn tại trong index.

**Kết quả khác kỳ vọng:**

`truncate_title` không làm `retrieval_hit` giảm như kỳ vọng — khi exact lookup
fail, hệ thống fallback sang semantic search, và vì summary vẫn nguyên vẹn nên
semantic search vẫn tìm đúng document. Điều này cho thấy embedding-based retrieval
có resilience tốt hơn keyword-based lookup.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. **Cleaning quyết định chất lượng toàn pipeline:** Mọi bước downstream (embedding,
   evaluation, quality checks) đều phụ thuộc vào schema và nội dung của cleaned data.
   Một lỗi nhỏ ở cleaning (thiếu field, summary ngắn, date sai) sẽ lan truyền
   xuyên suốt pipeline.

2. **Test set cần deterministic và truy vết được:** Dùng `df.head(8)` thay vì
   random sampling đảm bảo mọi lần chạy trên cùng cleaned data cho cùng câu hỏi.
   `ground_truth_doc_ids` lấy từ `paper_id` sạch, không tự bịa — giúp `retrieval_hit`
   phản ánh đúng khả năng retrieval.

3. **`build_clean_dataframe` vừa là cleaning vừa là repair:** Cùng một hàm dùng
   cho cả baseline và repair, đảm bảo repaired data luôn khớp baseline. Đây là
   thiết kế idempotent — chạy bao nhiêu lần trên cùng raw source cũng cho cùng kết quả.

### Nếu có thêm thời gian

- Thêm unit tests cho từng edge case: DataFrame rỗng, record thiếu DOI, summary
  dưới 40 ký tự, published date không parse được, duplicate paper_id;
- Thêm logging cho số record bị lọc ở mỗi bước (filter by title, filter by summary
  length, filter by date, dedupe) để truy vết dễ hơn;
- Mở rộng test set với nhiều loại câu hỏi hơn (multi-hop, comparison) và tăng
  sample size vượt 8 papers.

## 10. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi "đã chạy thành công" cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Dương Văn Kiên  
**MSSV:** (điền MSSV)  
**Ngày xác nhận:** 2026-08-06

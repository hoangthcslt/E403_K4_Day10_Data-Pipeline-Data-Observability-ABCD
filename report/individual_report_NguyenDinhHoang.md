# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên       | Nguyễn Đình Hoàng        |
| MSSV               | 2A202601436                |
| Khóa/Lớp         | K4                         |
| Tên nhóm         | ABCD                       |
| Vai trò chính    | Corruption & Repair        |
| Repository         | https://github.com/hoangthcslt/E403_K4_Day10_Data-Pipeline-Data-Observability-ABCD |
| Ngày hoàn thành | 2026-08-06                 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao  | Trạng thái |
| ------------------ | --------------------- | ---------------- | ----------------- | ------------ |
| Corruption logic | `src/ingestion/corruption.py` — hàm `corrupt_clean_dataframe()` | `data/clean/papers_clean.csv` (DataFrame baseline đã cleaned) | `data/clean/papers_clean_corrupted.csv`, `data/results/corruption_log.json` | Hoàn thành |
| Repair flow | `src/pipelines/corruption_flow.py` — phần repair trong `CorruptionFlow.main()` | `data/raw/crossref_records.json` (raw records gốc) | `data/clean/papers_clean_repaired.csv`, `data/results/repaired_metrics.json`, `data/results/repaired_answers.json` | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động                         | Thành viên/module được hỗ trợ | Kết quả                    |
| ------------------------------------ | ------------------------------------ | ---------------------------- |
| Debug file `reporting.py` bị ghi đè nhầm nội dung từ `quality.py` | Hoàng Thị Hà Huyền / module Observability | Phát hiện lỗi, khôi phục lại hai hàm `generate_phase1_report` và `generate_corruption_report` đúng format markdown |
| Tích hợp corruption flow với pipeline orchestration | Lương Hoàng Minh / module Integration | Đảm bảo luồng corruption → re-index → evaluate → repair → re-evaluate → comparison report chạy end-to-end |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao       | Cách xác minh         |
| --------------------------- | ----------------------------- | ------------------------- | ----------------------- |
| Implement 6 loại corruption | `src/ingestion/corruption.py` | `data/results/corruption_log.json` — ghi lại 6 actions, 12 records bị tác động | Kiểm tra JSON log: đủ 6 loại, paper_id chính xác |
| Tạo corrupted dataset | `corruption.py` → `corrupt_clean_dataframe()` | `data/clean/papers_clean_corrupted.csv` — 24 rows (bao gồm 2 duplicates) | So sánh với baseline: summary bị blank/noise, title bị truncate |
| Repair dataset từ raw source | `corruption_flow.py` → phần repair | `data/clean/papers_clean_repaired.csv` — 24 rows sạch | Repaired metrics khớp hoàn toàn với baseline metrics |
| Đánh giá tác động corruption | `corrupted_metrics.json`, `repaired_metrics.json` | Metrics sụt giảm rõ rệt khi corrupt, phục hồi 100% sau repair | So sánh 3 bộ metrics trong `corruption_report.md` |

Nêu một output cụ thể mà phần việc của bạn tạo ra hoặc giúp xác minh:

File `data/results/corruption_log.json` ghi nhận chính xác 6 loại corruption đã inject, mỗi loại ảnh hưởng 2 records với paper_id cụ thể. Kết hợp với `corrupted_metrics.json` cho thấy retrieval_hit_rate giảm từ 1.0 → 0.75 và mean_token_f1 giảm từ 1.0 → 0.558, chứng minh corruption thực sự tác động đến hiệu suất retrieval/answer.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Module corruption giải quyết bài toán: **mô phỏng các dạng suy giảm dữ liệu thực tế** (data degradation) trong pipeline để kiểm tra khả năng phát hiện lỗi của observability layer và đánh giá mức ảnh hưởng đến chất lượng retrieval/answer của RAG agent.

### Cách triển khai

1. **Phân vùng dữ liệu (Zone-based corruption):** DataFrame baseline được chia thành "corruption zone" (50% đầu — là vùng chứa các papers mới nhất, trùng với vùng mà test set lấy câu hỏi) và "rest zone" (phần còn lại). Điều này đảm bảo corruption **thực sự tác động** đến evaluation metrics, không chỉ data quality checks.

2. **6 kỹ thuật corruption tuần tự:**
   - `drop_latest_records` (15%): Xóa hoàn toàn records mới nhất → retrieval không tìm được document → `retrieval_hit = false`.
   - `blank_summary` (20%): Gán summary = "" → answer trả về rỗng → `token_f1 = 0`.
   - `inject_noise` (20%): Chèn `[noise:9f3a][garbled-ocr-fragment]` vào summary → answer bị nhiễu, semantic matching giảm.
   - `truncate_title` (20%): Cắt title còn 2 từ đầu → phá vỡ exact-title lookup trong `qa.py` → retrieval phải dựa hoàn toàn vào semantic search.
   - `stale_publication_date` (20%): Đặt ngày xuất bản thành 3 năm trước → vượt ngưỡng freshness 180 ngày → freshness check fail.
   - `duplicate_rows` (8% tổng): Nhân bản records → uniqueness check fail (`duplicates: 2`).

3. **Repair strategy — Source of Truth:** Repair KHÔNG sửa dữ liệu corrupted mà **rebuild từ `raw_records` gốc** (`data/raw/crossref_records.json`), đi qua lại toàn bộ cleaning pipeline. Đây là chiến lược đảm bảo tính toàn vẹn: dữ liệu repaired luôn khớp với baseline vì cùng nguồn gốc.

### Input, output và contract

| Thành phần                   | Mô tả                                     |
| ------------------------------ | ------------------------------------------- |
| Input                          | `pd.DataFrame` từ `papers_clean.csv` (24 rows, schema: paper_id, title, summary, authors_joined, categories_joined, published, age_days, text_for_embedding, summary_chars) |
| Output                         | `pd.DataFrame` corrupted (24 rows + 2 duplicates = 26 rows trước dedup), `corruption_log.json` |
| Module phụ thuộc             | `core/utils.py` (hàm `write_json`, `now_utc`), `ingestion/cleaning.py` (schema reference) |
| Module sử dụng output        | `pipelines/corruption_flow.py` → `retrieval/index.py` (re-index) → `evaluation/metrics.py` (re-evaluate) |
| Điều kiện lỗi cần xử lý | DataFrame rỗng (trả về bản sao rỗng + log trống), zone nhỏ hơn số lượng corruption cần (dùng `max(1, ...)`) |

### Cách xác minh

```bash
uv run python script/run_corruption_flow.py
```

- **Kết quả mong đợi:** corrupted_metrics có retrieval_hit_rate < 1.0, quality checks fail (duplicates, blank summary, stale date), repaired_metrics khớp baseline.
- **Kết quả thực tế:** `retrieval_hit_rate: 0.75`, `mean_token_f1: 0.558`, `judge_accuracy: 0.5`. Quality: `duplicates: 2`, `short_summaries: 2`, `stale_rows: 2`. Repaired: tất cả metrics = baseline.
- **Artifact/log:** `data/results/corruption_log.json`, `data/results/corrupted_metrics.json`, `data/results/repaired_metrics.json`, `data/reports/corruption_report.md`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Khi thiết kế corruption logic, cần quyết định corruption nên áp dụng ngẫu nhiên trên toàn bộ dataset hay tập trung vào một vùng cụ thể.
- **Các phương án đã cân nhắc:**
  1. **Random sampling:** Chọn ngẫu nhiên records để corrupt — đơn giản, nhưng có thể corruption rơi vào vùng mà test set không hỏi → metrics không đổi → không chứng minh được tác động.
  2. **Zone-based corruption:** Corruption tập trung vào top 50% papers mới nhất (trùng vùng test set lấy câu hỏi) — đảm bảo corruption tác động trực tiếp đến evaluation.
- **Phương án đã chọn:** Zone-based corruption (phương án 2).
- **Lý do:** Test set (`testset.py`) lấy câu hỏi từ `df.head(8)` — tức 8 papers đầu tiên (mới nhất). Nếu corruption rơi ngoài vùng này, retrieval_hit_rate và token_f1 sẽ không thay đổi, khiến bài lab mất ý nghĩa chứng minh "data quality impacts agent performance". Zone-based đảm bảo tác động đo lường được.
- **Bằng chứng quyết định phù hợp:** `corrupted_metrics.json` cho thấy retrieval_hit_rate giảm 25% (1.0 → 0.75) và mean_token_f1 giảm 44% (1.0 → 0.558), chứng minh corruption thực sự ảnh hưởng đến agent.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** Khi chạy `run_corruption_flow.py`, file `data/reports/corruption_report.md` được tạo ra nhưng nội dung sai hoàn toàn — chứa code Python thay vì markdown report. Pipeline không crash nhưng output không đúng format.
- **Lệnh hoặc bước tái hiện:** `uv run python script/run_corruption_flow.py` → mở `data/reports/corruption_report.md` → thấy nội dung là code từ `quality.py`.
- **Nguyên nhân gốc:** File `src/observability/reporting.py` bị ghi đè nhầm nội dung từ `src/observability/quality.py` (có thể do lỗi copy-paste trong quá trình phát triển). Các hàm `generate_phase1_report()` và `generate_corruption_report()` bị thay thế bằng logic quality checks.
- **Cách xử lý:** Viết lại hoàn toàn `reporting.py` với hai hàm đúng chức năng: `generate_phase1_report()` tạo báo cáo Phase 1 (source info, metrics, quality, freshness) và `generate_corruption_report()` tạo báo cáo so sánh 3 trạng thái (baseline/corrupted/repaired).
- **Cách xác minh sau khi sửa:** Chạy lại pipeline → kiểm tra `data/reports/corruption_report.md` có đủ bảng Metrics comparison, Data quality, Freshness, Summary → đúng format.
- **Điều học được:** Cần review kỹ nội dung file trước khi commit, đặc biệt khi nhiều module có tên tương tự (`quality.py` vs `reporting.py`). Một file bị ghi đè nhầm có thể không gây crash nhưng tạo ra output sai lệch khó phát hiện.

## 7. Hiểu biết về luồng end-to-end

**Câu trả lời:**

1. **Dữ liệu đi từ Crossref đến vector index như thế nào?**
   Hàm `fetch_crossref()` trong `crossref.py` gọi Crossref REST API với query "agentic retrieval augmented generation large language model", parse JSON response thành danh sách `PaperRecord`, lưu vào `data/raw/`. Tiếp theo, `cleaning.py` lọc records thiếu title/summary, chuẩn hóa whitespace, tính `age_days`, ghép các trường thành `text_for_embedding`. Cuối cùng, `index.py` dùng model `all-MiniLM-L6-v2` tạo embedding vector cho mỗi document và nạp vào ChromaDB collection.

2. **Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?**
   `testset.py` tạo 24 câu hỏi (4 loại: summary, authors, date, categories) từ 8 papers đầu tiên trong cleaned dataset. Mỗi câu hỏi có `ground_truth` (đáp án đúng) và `ground_truth_doc_ids` (DOI của paper nguồn). Khi evaluate, `metrics.py` dùng `answer_question()` để truy vấn index, so sánh `retrieved_doc_ids` với `ground_truth_doc_ids` (tính `retrieval_hit`), và so sánh `answer` với `ground_truth` (tính `token_f1` và `judge_score`).

3. **Quality checks khác freshness monitoring ở điểm nào trong bài lab?**
   Quality checks (`quality.py`) đánh giá **tính đúng đắn cấu trúc** của dataset tại một thời điểm: completeness (có đủ rows, title không null), uniqueness (paper_id không trùng), validity (summary đủ dài ≥ 40 ký tự). Freshness monitoring đánh giá **tính cập nhật** của dữ liệu theo thời gian: so sánh ngày xuất bản với ngưỡng 180 ngày, phát hiện records đã cũ (stale). Quality checks là snapshot tĩnh, freshness là tín hiệu có yếu tố thời gian.

4. **Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?**
   Để đảm bảo **controlled experiment** — biến duy nhất thay đổi giữa 3 lần đánh giá là chất lượng dữ liệu (sạch/lỗi/sửa), không phải câu hỏi. Nếu dùng test set khác nhau, sự thay đổi metrics có thể do câu hỏi khó/dễ hơn chứ không phải do data quality, khiến kết luận nhân quả không chính xác.

5. **Repair được xem là thành công dựa trên artifact và metric nào?**
   Repair thành công khi `repaired_metrics.json` khớp hoàn toàn với `baseline_metrics.json` (retrieval_hit_rate = 1.0, mean_token_f1 = 1.0, judge_accuracy = 1.0, mean_judge_score = 5). Đồng thời, `repaired_quality.json` phải pass tất cả checks (duplicates = 0, short_summaries = 0, stale_rows = 0) và `repaired_freshness_report.json` phải cho `is_fresh = true`. Trong bài lab này, tất cả các điều kiện trên đều đạt.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal          | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| ---------------------- | -------: | --------: | -------: | ------------------------- |
| `retrieval_hit_rate` |      1.0 |      0.75 |      1.0 | Giảm 25% do drop_latest_records xóa 2 papers khỏi index, 6 câu hỏi liên quan không tìm được document |
| `mean_token_f1`      |      1.0 |     0.558 |      1.0 | Giảm mạnh 44% do blank_summary → answer rỗng (F1=0), inject_noise → answer bị nhiễu |
| `judge_accuracy`     |      1.0 |       0.5 |      1.0 | 50% câu trả lời bị đánh giá sai do nội dung không khớp ground_truth |
| `mean_judge_score`   |        5 |     3.042 |        5 | Điểm trung bình giảm gần 2 bậc, phản ánh mức độ sai lệch nghiêm trọng |
| Quality checks         | All pass | 3 Fail    | All pass | Corrupted: uniqueness fail (duplicates=2), validity fail (short_summaries=2), freshness fail (stale_rows=2) |
| Freshness status       |    Fresh |     Stale |    Fresh | stale_publication_date đẩy 2 records xuống 2023-08-07, vượt ngưỡng 180 ngày |

### Kết luận từ số liệu

1. **[Data corruption] → [quality/freshness signal thay đổi] → [agent metric thay đổi]:**
   `drop_latest_records` xóa 2 papers mới nhất (SafeRAG, JADE-Plus) → 6 câu hỏi liên quan (q-001 đến q-006) mất document source → `retrieval_hit = false` → `retrieval_hit_rate` giảm từ 1.0 → 0.75. Đồng thời `blank_summary` khiến 2 papers có summary rỗng → answer trả về "" → `token_f1 = 0` cho các câu hỏi tương ứng. Quality checks phát hiện: `duplicates: 2`, `short_summaries: 2`, `stale_rows: 2` → overall quality **Fail**.

2. **[Repair action] → [quality/freshness signal phục hồi] → [agent metric phục hồi]:**
   Repair rebuild toàn bộ dataset từ `raw_records` gốc (Crossref API response), đi qua lại cleaning pipeline → dataset sạch 24 rows không trùng lặp, không thiếu dữ liệu, ngày xuất bản đúng → quality checks pass 100%, freshness = Fresh. Re-index và re-evaluate cho `retrieval_hit_rate = 1.0`, `mean_token_f1 = 1.0` → phục hồi hoàn toàn về baseline.

**Corruption nào ảnh hưởng rõ nhất và vì sao?**

`drop_latest_records` ảnh hưởng rõ nhất vì nó **xóa hoàn toàn document** khỏi corpus — không có cách nào retrieval tìm được một paper đã bị xóa. Các corruption khác (noise, blank, truncate) làm giảm chất lượng answer nhưng document vẫn tồn tại trong index, retrieval_hit vẫn có thể = true.

**Kết quả nào khác với kỳ vọng ban đầu?**

Ban đầu kỳ vọng `truncate_title` sẽ làm retrieval_hit giảm mạnh (vì phá vỡ exact-title lookup), nhưng thực tế retrieval_hit vẫn = true cho các papers bị truncate. Nguyên nhân: khi exact lookup fail, hệ thống fallback sang semantic search (embedding similarity), và vì nội dung summary vẫn nguyên vẹn nên semantic search vẫn tìm đúng document. Điều này cho thấy embedding-based retrieval có khả năng chống chịu (resilience) tốt hơn so với keyword-based lookup.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. **Data pipeline:** Thiết kế pipeline cần có tính idempotent — mỗi bước có thể chạy lại từ đầu mà không phụ thuộc vào trạng thái trước đó. Repair strategy "rebuild từ raw source" minh họa rõ nguyên tắc này: thay vì cố patch dữ liệu lỗi, rebuild từ nguồn đáng tin cậy đảm bảo tính toàn vẹn.

2. **Data quality/observability:** Quality checks tự động (completeness, uniqueness, validity, freshness) là "hệ thống báo cháy" của pipeline — chúng phát hiện vấn đề trước khi downstream consumers (RAG agent) bị ảnh hưởng. Trong bài lab, quality checks phát hiện đúng cả 3 dạng lỗi: duplicate (uniqueness), blank summary (validity), stale date (freshness).

3. **Ảnh hưởng của data đến RAG agent:** Chất lượng dữ liệu đầu vào quyết định trực tiếp hiệu suất retrieval và answer quality. Chỉ cần xóa 2/24 papers (8%) đã làm giảm 25% retrieval_hit_rate. "Garbage in, garbage out" không chỉ là khẩu hiệu mà là quy luật đo lường được bằng metrics cụ thể.

### Nếu có thêm thời gian

Implement **incremental repair** thay vì full rebuild: phân tích `corruption_log.json` để chỉ sửa đúng records bị tác động thay vì rebuild toàn bộ dataset. Cách đo: so sánh thời gian repair (incremental vs full rebuild) trên dataset lớn hơn (100+ records), đồng thời verify metrics sau repair vẫn khớp baseline. Điều này cải thiện efficiency trong production pipeline khi dataset có hàng nghìn records.

## 10. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi "đã chạy thành công" cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Nguyễn Đình Hoàng
**Ngày xác nhận:** 2026-08-06

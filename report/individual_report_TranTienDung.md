# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên       | Trần Tiến Dũng             |
| MSSV               | 2A202601064                       |
| Khóa/Lớp         | K4              |
| Tên nhóm         | ABCD     |
| Vai trò chính    | Source Ingestion (Thành viên 1/5) |
| Repository         | https://github.com/hoangthcslt/E403_K4_Day10_Data-Pipeline-Data-Observability-ABCD |
| Ngày hoàn thành | 2026-08-06               |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao  | Trạng thái                                 |
| ------------------ | --------------------- | ---------------- | ----------------- | -------------------------------------------- |
| Raw data ingestion | `src/ingestion/crossref.py` (`fetch_source_records`, `parse_crossref_payload`, `load_raw_records`) | Crossref REST API (`https://api.crossref.org/works`), query/filter từ `core.config.Settings` | `data/raw/crossref_response.json` (raw payload), `data/raw/crossref_records.json` (list `PaperRecord` đã parse) | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động                         | Thành viên/module được hỗ trợ | Kết quả                    |
| ------------------------------------ | ------------------------------------ | ---------------------------- |
| Implement `src/pipelines/phase1.py` (thuộc phạm vi Thành viên 5 — Integration & Comparison) | Ghép toàn bộ baseline flow: load/fetch raw → clean → build index → eval set → evaluate → quality/freshness → report → demo agent | Baseline chạy end-to-end thật, tạo đủ artifact trong `data/`, xem mục 3 |
| Chạy và xác minh baseline pipeline nhiều lần trên dữ liệu Crossref + Gemini thật | Toàn nhóm (dùng chung `data/clean/`, `data/eval/test_set.json` cho các bước sau) | `data/results/baseline_metrics.json`, `data/results/baseline_answers.json` với 22/24 câu có judge LLM thật |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao       | Cách xác minh         |
| --------------------------- | ----------------------------- | ------------------------- | ----------------------- |
| Gọi Crossref API với retry/backoff cho 429/5xx, parse DOI/title/abstract/authors/subject/dates/URL thành `PaperRecord` | `src/ingestion/crossref.py` | `data/raw/crossref_response.json`, `data/raw/crossref_records.json` (24 record) | `grep -n "TODO(student)" src/ingestion/crossref.py` (rỗng), đọc trực tiếp 2 file JSON output |
| Ghép baseline pipeline, chạy thật từ đầu đến cuối | `src/pipelines/phase1.py`, `script/run_phase1.py` | `data/clean/`, `data/embeddings/`, `data/eval/test_set.json`, `data/results/baseline_metrics.json`, `data/quality/`, `data/reports/phase1_report.md` | `python script/run_phase1.py` (console log in ra từng bước, không raise exception) |

Output cụ thể: `data/raw/crossref_records.json` — 24 `PaperRecord` sạch (có DOI, title, abstract đã strip tag JATS, authors, categories, ngày xuất bản trong vòng 180 ngày theo `source_filter`), là input trực tiếp cho `build_clean_dataframe` của Thành viên 2.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Lấy dữ liệu bài báo học thuật từ Crossref một cách đáng tin cậy (chịu được lỗi mạng/rate-limit tạm thời), chuẩn hóa payload JSON thô (vốn không đồng nhất — nhiều field ngày tháng khác nhau, `subject`/`author` có thể rỗng) thành schema `PaperRecord` cố định để các bước sau (cleaning, embedding) dùng được ngay, đồng thời lưu lại raw response để có thể truy vết/tái tạo lại nếu cleaning logic thay đổi sau này.

### Cách triển khai

- Gọi `GET https://api.crossref.org/works` với `query.bibliographic`, `filter=from-pub-date:...,has-abstract:true`, `rows=max_results`.
- Retry tối đa 5 lần với exponential backoff (bắt đầu 1s, nhân đôi mỗi lần), tôn trọng header `Retry-After` nếu Crossref trả về; chỉ retry cho status `{429, 500, 502, 503, 504}`, các lỗi khác raise ngay.
- Parse: DOI làm `paper_id` (khử trùng lặp theo DOI), title lấy phần tử đầu của mảng `title`, abstract bị strip tag JATS (`<jats:p>...</jats:p>`) bằng regex trước khi normalize whitespace.
- Ngày xuất bản không có field chuẩn duy nhất trong Crossref — thử lần lượt `published` → `published-print` → `published-online` → `issued` → `created`, lấy `date-parts` đầu tiên hợp lệ, thiếu tháng/ngày thì mặc định là 1.
- Bỏ record thiếu DOI hoặc title (không hợp lệ để làm document).
- Lưu raw response (nguyên payload Crossref) và raw records (list dict từ `dataclasses.asdict`) làm hai artifact tách biệt để truy vết.

### Input, output và contract

| Thành phần                   | Mô tả                                     |
| ------------------------------ | ------------------------------------------- |
| Input                          | `Settings` (query, filter, max_results, đường dẫn output) từ `core.config.load_settings()` |
| Output                         | `list[PaperRecord]`; đồng thời ghi `data/raw/crossref_response.json` và `data/raw/crossref_records.json` |
| Module phụ thuộc             | `core.config`, `core.utils` (`write_json`, `read_json`, `normalize_whitespace`, `compact_join`) |
| Module sử dụng output        | `src/ingestion/cleaning.py::build_clean_dataframe` (nhận `list[PaperRecord]` trực tiếp hoặc qua `load_raw_records`) |
| Điều kiện lỗi cần xử lý | Crossref trả 429/503 (retry), DOI/title rỗng (bỏ record), payload không có field ngày nào hợp lệ (record đó không có `published`, bị `cleaning.py` lọc bỏ ở bước sau) |

### Cách xác minh

```bash
conda run -n lab10 python script/run_phase1.py
```

- **Kết quả mong đợi:** Lấy được danh sách paper từ Crossref, lưu raw response/records, không raise `NotImplementedError`.
- **Kết quả thực tế:** `[phase1] loaded 24 raw records` — chạy thành công, không lỗi.
- **Artifact/log:** `data/raw/crossref_response.json`, `data/raw/crossref_records.json`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Baseline chạy xong nhưng phát hiện `data/results/baseline_answers.json` có `reasoning: "Fallback heuristic judge used..."` ở toàn bộ 24/24 câu — nghĩa là `judge_accuracy`/`mean_judge_score` không phải từ LLM thật mà từ heuristic dự phòng trong `evaluation/metrics.py`, do quota Gemini free-tier (20 request/ngày) đã cạn trước khi evaluate chạy.
- **Các phương án đã cân nhắc:**
  1. Đổi liên tục sang API key mới cho tới khi đạt 24/24 câu có judge LLM thật.
  2. Chấp nhận tỷ lệ judge thật cao (không nhất thiết 100%) miễn `retrieval_hit_rate`/`mean_token_f1` (không phụ thuộc LLM) vẫn chính xác tuyệt đối, và ghi nhận rõ số câu fallback.
- **Phương án đã chọn:** Phương án 2 — dừng ở 22/24 câu có judge thật sau khi phát hiện quota mỗi tài khoản mới chỉ đủ cho ~20-22 request/ngày cho model, đổi thêm key chỉ được lợi 1-2 câu, không đáng công sức.
- **Lý do:** `retrieval_hit_rate`/`mean_token_f1` là tín hiệu quan trọng nhất để chứng minh corruption ảnh hưởng agent (không phụ thuộc LLM judge), nên việc còn 2/24 câu fallback không ảnh hưởng tới kết luận chính của bài lab; đổi key vô hạn để đuổi 100% là đánh đổi thời gian không cân xứng.
- **Bằng chứng quyết định phù hợp:** `grep -c "Fallback heuristic judge" data/results/baseline_answers.json` → 2/24 (giảm dần qua 3 lần thử: 24/24 → 3/24 → 2/24), trong khi `retrieval_hit_rate=1.0` và `mean_token_f1=1.0` không đổi qua tất cả các lần chạy.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** `google.genai.errors.ClientError: 429 RESOURCE_EXHAUSTED... Quota exceeded for metric: generativelanguage.googleapis.com/generate_content_free_tier_requests, limit: 20, model: gemini-2.5-flash`; sau khi đổi key mới còn gặp thêm `404 NOT_FOUND: This model models/gemini-2.5-flash is no longer available to new users`.
- **Lệnh hoặc bước tái hiện:** `conda run -n lab10 python script/run_phase1.py`, lỗi xuất hiện ở bước demo agent (gọi LLM), nhưng khi soát lại `baseline_answers.json` phát hiện toàn bộ bước judge trong `evaluate_pipeline` cũng đã âm thầm fallback từ trước (except-block trong `_judge_answer` nuốt exception, không log ra console).
- **Nguyên nhân gốc:** (1) Gemini free-tier giới hạn 20 request/ngày/model, quota cạn trước cả khi evaluate chạy; (2) model `gemini-2.5-flash` cấu hình trong `.env` đã bị Google deprecate cho tài khoản mới tạo, trả 404 dù model vẫn xuất hiện trong danh sách `list_models`.
- **Cách xử lý:** Đổi `LLM_MODEL` sang `gemini-flash-latest` (alias luôn trỏ bản flash mới nhất, tránh lặp lại vấn đề deprecate theo tên cố định) sau khi verify bằng một lệnh gọi test đơn (`llm.invoke("Reply with exactly one word: OK")`); đổi API key sang tài khoản còn quota; chạy lại `script/run_phase1.py`.
- **Cách xác minh sau khi sửa:** `python -c "..."` đếm chuỗi `"Fallback heuristic judge"` trong `data/results/baseline_answers.json` — giảm từ 24/24 xuống 2/24; đọc trực tiếp `reasoning` của các câu còn lại thấy nội dung LLM thật (ví dụ: `"The model answer is identical to the reference answer."`).
- **Điều học được:** LLM-as-judge có cơ chế fallback im lặng (silent) — không thể chỉ tin số liệu tổng hợp (`judge_accuracy`, `mean_judge_score`) mà phải kiểm tra field `reasoning` chi tiết từng câu để biết đó có phải đánh giá LLM thật hay không, đặc biệt khi metric fallback (dựa trên `token_f1`) có thể trùng số với kết quả LLM thật một cách ngẫu nhiên và che giấu vấn đề.

## 7. Hiểu biết về luồng end-to-end

**Câu trả lời:**

1. `crossref.py` gọi Crossref API lấy raw payload, parse thành `PaperRecord` và lưu vào `data/raw/`. `cleaning.py` đọc các record này, chuẩn hóa title/summary/authors/categories, tính `age_days`, dựng `text_for_embedding`, lọc record xấu/trùng, lưu vào `data/clean/`. `retrieval/index.py` (code tham khảo) đọc cleaned dataframe, dùng `sentence-transformers/all-MiniLM-L6-v2` để embed `text_for_embedding` rồi nạp vào một collection ChromaDB riêng cho từng trạng thái (`papers-baseline`/`papers-corrupted`/`papers-repaired`).
2. `testset.py` sinh câu hỏi từ các paper mới nhất trong cleaned dataframe, mỗi câu có `ground_truth` (câu trả lời đúng) và `ground_truth_doc_ids` (paper_id đúng). Khi evaluate, `retrieval_hit` = true nếu paper_id trả về từ vector search nằm trong `ground_truth_doc_ids`; `token_f1` so khớp token giữa câu trả lời agent và `ground_truth`.
3. Quality checks (`run_data_quality_checks`) kiểm tra tính đúng đắn cấu trúc tại một thời điểm (đủ dòng, `paper_id` unique, `title`/`summary` không rỗng/quá ngắn) — là các ràng buộc tĩnh. Freshness monitoring (`build_freshness_report`) đo tính "mới" của dữ liệu theo thời gian (`age_days` so với ngưỡng `freshness_threshold_days`) — một ràng buộc động, thay đổi theo ngày chạy dù dữ liệu không đổi.
4. Phải dùng chung một `test_set.json` cho baseline/corrupted/repaired vì nếu mỗi trạng thái có câu hỏi khác nhau, chênh lệch metric có thể do câu hỏi khác nhau chứ không phải do corruption/repair — mất tính so sánh được (controlled comparison).
5. Repair được coi là thành công khi: (a) dữ liệu được dựng lại từ `raw_records.json` (nguồn đáng tin) bằng đúng `build_clean_dataframe`, không sửa tay corrupted data; (b) `run_data_quality_checks`/`build_freshness_report` trên repaired data pass trở lại như baseline; (c) metrics evaluate trên repaired data (`retrieval_hit_rate`, `mean_token_f1`, `judge_accuracy`) quay về gần với baseline trong `data/results/repaired_metrics.json`.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal          | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| ---------------------- | -------: | --------: | -------: | ------------------------- |
| `retrieval_hit_rate` |     1.0 |  chưa chạy Pha 2 |  chưa chạy Pha 2 | Baseline đạt tuyệt đối vì câu hỏi test set trích dẫn title chính xác trong dấu nháy đơn, kích hoạt exact-match lookup trong `qa.py` thay vì chỉ dựa vào semantic search |
| `mean_token_f1`      |     1.0 |  chưa chạy Pha 2 |  chưa chạy Pha 2 | Ground truth trong test set được sinh trực tiếp từ field metadata (`authors_joined`, `published`, `categories_joined`) nên khớp tuyệt đối với câu trả lời khi dữ liệu sạch |
| `judge_accuracy`     |     1.0 (22/24 câu là LLM thật, 2/24 fallback heuristic) |  chưa chạy Pha 2 |  chưa chạy Pha 2 | Xem mục 6 — cần đọc `reasoning` từng câu, không chỉ tin số tổng hợp |
| `mean_judge_score`   |     5 |  chưa chạy Pha 2 |  chưa chạy Pha 2 | Tương tự trên |
| Quality checks         |     Pass (5/5 check) |  chưa chạy Pha 2 |  chưa chạy Pha 2 | `paper_id` unique, `title`/`summary` đủ dài, freshness trong ngưỡng 180 ngày |
| Freshness status       |     is_fresh=True, 0/24 stale |  chưa chạy Pha 2 |  chưa chạy Pha 2 | Toàn bộ 24 paper nằm trong 180 ngày do `source_filter` đã lọc `from-pub-date` khi fetch |

### Kết luận từ số liệu

Phần Corruption/Repair (`src/ingestion/corruption.py`, `src/pipelines/corruption_flow.py`) đã được implement nhưng **chưa được chạy để lấy số liệu thật** tính đến thời điểm viết báo cáo này — không điền số liệu Corrupted/Repaired ở trên để tránh ghi kết quả chưa được kiểm chứng. Phần này thuộc trách nhiệm chính của Thành viên 4/5 theo phân công nhóm; cần cập nhật bảng trên và phần "Corruption nào ảnh hưởng rõ nhất" sau khi `corruption_flow.py` chạy xong và có `data/results/corrupted_metrics.json`, `data/results/repaired_metrics.json`, `data/reports/corruption_report.md`.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. Raw response và raw records nên tách thành hai artifact riêng biệt (payload gốc vs. dữ liệu đã parse) — nếu logic parse sau này sai, vẫn có thể re-parse từ raw response mà không cần gọi lại API nguồn.
2. Freshness không phải là một phần của "data quality" theo nghĩa tĩnh — nó là tín hiệu phụ thuộc thời điểm quan sát, cùng một dataset có thể "fresh" hôm nay và "stale" vài tháng sau mà không cần dữ liệu thay đổi.
3. Metric tổng hợp (summary) từ một pipeline evaluate có thể che giấu lỗi runtime (như silent fallback của LLM judge) — luôn cần đối chiếu artifact chi tiết (`baseline_answers.json`), không chỉ tin `baseline_metrics.json`.

### Nếu có thêm thời gian

Thêm cơ chế log rõ ràng (không chỉ silent except) khi `_judge_answer` fallback sang heuristic, ví dụ đếm và in số lần fallback ngay trong `evaluate_pipeline` summary (`judge_fallback_count`) — đo được bằng cách so `len(answers)` với số `reasoning` không chứa "Fallback" trước/sau khi thêm.

## 10. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [ ] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [ ] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [ ] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [ ] Tôi không ghi "đã chạy thành công" cho phần chưa được kiểm chứng.
- [ ] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [ ] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Trần Tiến Dũng
**Ngày xác nhận:** 2026-08-06

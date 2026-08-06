# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| --- | --- |
| Họ và tên | Lương Hoàng Minh |
| MSSV | 2A202601490 |
| Khóa/Lớp | K4 |
| Tên nhóm | ABCD |
| Vai trò chính | Integration & Comparison (Thành viên 5/5) |
| Phạm vi chính | `src/pipelines/corruption_flow.py` |
| Repository | https://github.com/hoangthcslt/E403_K4_Day10_Data-Pipeline-Data-Observability-ABCD |
| Ngày hoàn thành | 2026-08-06 |

## 2. Vai trò và phạm vi công việc

Theo phân công, vai trò của tôi (Thành viên 5) là Integration & Comparison (người điều phối và so sánh pipeline), bao gồm việc ráp nối toàn bộ quy trình từ dữ liệu sạch (phase 1) cho đến việc kiểm thử độ bền của RAG qua luồng dữ liệu lỗi (corruption_flow).

Tôi tập trung toàn bộ nguồn lực vào việc xây dựng luồng kiểm thử quan trọng nhất của bài lab: **Luồng Corruption & Repair** (`src/pipelines/corruption_flow.py`).

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao  | Trạng thái                                 |
| ------------------ | --------------------- | ---------------- | ----------------- | -------------------------------------------- |
| Corruption & Comparison Orchestration | `src/pipelines/corruption_flow.py` | Clean baseline dataset, baseline metrics, raw records | Các file corrupted/repaired data, metrics, report tương ứng | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động                         | Thành viên/module được hỗ trợ | Kết quả                    |
| ------------------------------------ | ------------------------------------ | ---------------------------- |
| Phối hợp xử lý conflict/ghi đè code report | Huyền (Observability - Thành viên 3) và Dũng (Ingestion - Thành viên 1) | Revert/merge và tách biệt rõ ràng logic của `quality.py` và `reporting.py`, giúp sinh đúng artifact mong đợi |
| Bàn giao quyền implement `run_phase1.py` cho Dũng | Dũng (Ingestion - Thành viên 1) | Baseline chạy end-to-end tốt, đẩy nhanh tiến độ làm Phase 1 của toàn nhóm |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --- | --- | --- | --- |
| Load dữ liệu baseline | `corruption_flow.py` | Đọc dữ liệu từ phase 1 | Console in ra `loaded baseline dataset...` |
| Orchestrate việc làm bẩn dữ liệu (Corrupt) | Gọi `corrupt_clean_dataframe` | `data/clean/papers_clean_corrupted.csv/json`, log corruption | File JSON/CSV được lưu đúng nơi, chạy ổn định |
| Re-index và Re-evaluate corrupted data | Gọi `LocalEmbeddingIndex.build` & `evaluate_pipeline` | `data/embeddings/papers_embeddings_corrupted.json`, metrics và quality/freshness report cho corrupted data | Log terminal không lỗi, tạo đủ file metric/quality |
| Repair dữ liệu từ nguồn (Raw) | Đọc `raw_records` và gọi `build_clean_dataframe` | Repaired index, repaired metrics, repaired quality & freshness reports | File JSON/CSV cho repaired data được tạo đầy đủ |
| Orchestrate việc sinh Comparison Report | Gọi `generate_corruption_report` | `data/reports/corruption_report.md` | Có Markdown report chứa so sánh Baseline/Corrupted/Repaired |

## 4. Giải thích phần kỹ thuật đã thực hiện

### 4.1. Vấn đề cần giải quyết

RAG Agent phụ thuộc rất nhiều vào chất lượng dữ liệu. Một pipeline RAG không chỉ cần chạy đúng trên dữ liệu sạch, mà còn cần biết RAG sẽ phản ứng thế nào nếu luồng dữ liệu sinh ra lỗi (mất trường quan trọng, dữ liệu cũ đi, bản ghi trùng lặp...). 
Nhiệm vụ của `corruption_flow.py` là chứng minh: Data xấu sẽ làm RAG trả lời sai hoặc không trả lời được, và sau khi ta xử lý (repair) từ dữ liệu gốc, RAG sẽ trở lại bình thường. Quá trình này cần sự kết nối tự động (orchestration) của rất nhiều module do các bạn khác viết.

### 4.2. Cách triển khai luồng (Orchestration logic)

Tôi triển khai `corruption_flow.py` chạy qua 7 bước:
1. **Kiểm tra dependency (Baseline):** Phải đảm bảo `run_phase1.py` đã tạo đủ metrics, clean dataset và raw records. Nếu không có, raise lỗi ngay để tránh chạy sai.
2. **Làm bẩn (Corrupt):** Gọi hàm corrupt của (Thành viên 3). Lưu kết quả ra file riêng `papers_clean_corrupted.*` để không đè lên dữ liệu baseline.
3. **Đánh giá Corrupted Data:** Nạp dữ liệu bẩn vào `LocalEmbeddingIndex`, chạy `evaluate_pipeline` trên **cùng một bộ câu hỏi (test set)** để đo đạc độ giảm của hit rate và F1 score. Đồng thời chạy quality và freshness để thấy check bị failed.
4. **Phục hồi (Repair):** Đây là bước quan trọng. Tôi không "vá" dữ liệu bị lỗi, mà yêu cầu đọc trực tiếp từ `data/raw/crossref_records.json` (nguồn đáng tin do Thành viên 1 tải về), và đẩy lại qua hàm `build_clean_dataframe`. 
5. **Đánh giá Repaired Data:** Nạp lại repaired dataframe vào vector index mới, tiếp tục dùng lại bộ test set cũ để đánh giá.
6. **Kiểm tra chất lượng:** Gọi quality checks và freshness monitoring lên dữ liệu sau repair để xác nhận trạng thái pass 100% như lúc baseline.
7. **Báo cáo:** Gom tất cả metric của 3 trạng thái truyền vào `generate_corruption_report` (hàm do Thành viên 3 làm) để sinh file Markdown so sánh cuối cùng.

### 4.3. Input, output và contract

| Thành phần | Mô tả |
| --- | --- |
| Input | Baseline clean data, Baseline metrics, Raw records json, Cấu hình `Settings` |
| Output | Corrupted data (index, answer, metrics, quality, freshness), Repaired data (tương tự) và `comparison_report.md` |
| Module phụ thuộc | Phụ thuộc vào TẤT CẢ các module khác: `evaluation.metrics`, `ingestion.cleaning`, `ingestion.corruption`, `ingestion.crossref`, `observability.quality`, `observability.reporting`, `retrieval.index`. |

### 4.4. Cách xác minh

Chạy lệnh: `python script/run_corruption_flow.py`
- Lệnh chạy sẽ sinh ra hàng loạt log thể hiện số lượng record bị corrupt, index collection name, metric đánh giá. Cuối cùng, thông báo: `[corruption] comparison report written to ...`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Khi chạy evaluation trên dữ liệu đã bị corrupt và repair, nếu để pipeline sinh lại test set (câu hỏi) mới thì sẽ không thể kết luận nguyên nhân thay đổi của metrics.
- **Phương án đã chọn:** Ép hàm `evaluate_pipeline` trong `corruption_flow.py` phải nhận parameter `test_set_path=settings.paths.eval_testset`.
- **Lý do:** Điều này nhằm tạo môi trường controlled comparison (so sánh có kiểm soát). Việc dùng chung bộ 24 câu hỏi từ bước Baseline cho mọi lần đánh giá tiếp theo đảm bảo rằng nếu hit_rate giảm, thì đó 100% là do dữ liệu bẩn chứ không phải do câu hỏi khó hơn.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng:** Khi tôi và Huyền (Observability owner) ghép code ban đầu, phần code `reporting.py` có lúc bị ghi đè hoặc commit nhầm nội dung từ `quality.py` của tôi. 
- **Cách xử lý:** Tôi đã phối hợp cùng các bạn trong nhóm (như Dũng) thực hiện revert/merge lại file (`fix reporting.py: restore generate_phase1_report/generate_corruption_report`) trên git để phục hồi đúng cấu trúc hàm mà Huyền và tôi thống nhất. Điều này nhắc nhở nhóm về việc cẩn trọng trong quá trình pull/merge khi nhiều thành viên cùng làm một module liên quan đến "report".

## 7. Hiểu biết về luồng end-to-end

1. Đầu tiên, `crossref.py` (Ingestion) lấy dữ liệu API gốc và lưu raw records. 
2. `cleaning.py` dọn dẹp các record đó thành clean dataframe. 
3. Từ Clean dataframe này, ta index vào ChromaDB và tạo vector embedding.
4. `testset.py` sẽ lấy chính clean dataframe để tạo câu hỏi và đáp án đúng.
5. Sau đó, Eval pipeline sẽ bắt Agent trả lời các câu hỏi đó (qua retrieval và LLM) để tính toán độ hiệu quả (hit rate, token F1).
6. Quality và Freshness checks sẽ quan sát cấu trúc và tuổi thọ của dữ liệu.
7. Khi có sự cố (do luồng corruption tạo ra), các metric và check bị fail rõ rệt. Dữ liệu sẽ được "repair" bằng cách làm sạch lại từ nguyên bản Raw Records ban đầu. Mọi thay đổi đều được tôi tổng hợp tự động thành báo cáo Comparison.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal          | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| ---------------------- | -------: | --------: | -------: | ------------------------- |
| `retrieval_hit_rate` |      1.0 |      0.75 |      1.0 | Giảm mạnh do một số row bị làm mất thông tin để truy xuất (mất nội dung cần thiết). Repair phục hồi 100%. |
| `mean_token_f1`      |      1.0 |    ~0.558 |      1.0 | Agent fallback hoặc sinh rác khi không có context đúng (do hit rate giảm kéo theo context sai). Repair phục hồi hoàn toàn. |
| `judge_accuracy`     |      1.0 |    ~0.542 |      1.0 | Giảm tương đương với F1. Các câu trả lời sai do data corrupted không được judge đánh giá cao. |
| `mean_judge_score`   |        5 |     ~3.08 |        5 | Điểm số của LLM Judge cũng tụt mạnh từ 5 xuống mức 3, phản ánh rõ ràng sự sai lệch của output. |
| Quality checks         |     Pass (5/5) |     Fail (3 failed) |     Pass (5/5) | Failed các check: `paper_id_not_null_unique` (duplicate), `summary_length` (summary ngắn), `freshness`. Repair fix hết các check này. |
| Freshness status       |     is_fresh=True, 0 stale |     is_fresh=False, 2 stale |     is_fresh=True, 0 stale | Dữ liệu corrupted bị cố tình làm cũ đi (stale). Repair giúp dữ liệu được lấy lại ngày tháng mới nhất từ raw data. |

### Kết luận từ số liệu

Hoàn thành hai chuỗi nguyên nhân–bằng chứng sau:

1. **[Data corruption (Tạo 2 stale rows, 2 short summaries, 2 duplicate ID)]** → **[Quality/freshness signal thay đổi (3 checks failed: uniqueness, validity, freshness)]** → **[Agent metric thay đổi (hit_rate giảm còn 0.75, token_f1 giảm còn ~0.558)]**.
2. **[Repair action (Rebuild data từ raw_records.json gốc)]** → **[Quality/freshness signal phục hồi (Pass toàn bộ 5/5 check)]** → **[Agent metric phục hồi (Tất cả hit_rate, f1_score, judge_accuracy đều trở về 1.0)].**

**Corruption nào ảnh hưởng rõ nhất và vì sao?**

Các corruption làm hỏng các metadata quan trọng (như làm mất title, làm trống summary) ảnh hưởng rõ rệt nhất. Lý do là test set (câu hỏi) được gen ra và tham chiếu trực tiếp đến nội dung metadata đó. Khi RAG search text_for_embedding mà thấy rác hoặc quá ngắn (như 2 short summaries bị làm hỏng), engine truy xuất sẽ không bắt trúng document (làm hit rate rớt xuống 0.75), dẫn đến việc Agent lấy sai context, kéo theo sự sụt giảm toàn diện của `token_f1` và `judge_accuracy`.

**Kết quả nào khác với kỳ vọng ban đầu?**

Lúc đầu tôi tưởng sự trùng lặp ID (duplicate IDs) sẽ không làm giảm metric mà chỉ trả về 2 kết quả y chang nhau. Tuy nhiên, việc hỏng hóc ở metadata (như age quá cũ hoặc summary ngắn) khiến cho chất lượng context (đầu vào của agent) bị pha loãng nghiêm trọng. Agent thay vì dựa vào context thì lại có khuynh hướng dùng "hallucination" hoặc không thể trả lời trọn vẹn, làm điểm judge_score rớt thẳng xuống ~3.08.

## 9. Điều học được và hướng cải thiện

### Điều quan trọng nhất:
1. **Separation of Concerns:** Quá trình làm bẩn dữ liệu phải lưu file ra thư mục riêng biệt (`_corrupted`, `_repaired`) thay vì ghi đè baseline. Nó giúp ta có artifacts để đối chiếu minh bạch.
2. **Không vá dữ liệu hỏng:** Data repair thực thụ không phải là viết code "sửa" những dòng bị hỏng (patching), mà phải đi từ nguồn đáng tin cậy (Raw Source) rồi chạy lại quy trình làm sạch. Điều này đảm bảo tính bền vững của pipeline.
3. **Kiểm soát biến số:** Giữ nguyên test_set là bài học cốt lõi để việc đánh giá A/B Testing có ý nghĩa.

### Hướng cải thiện:
Nếu có thêm thời gian, tôi sẽ bổ sung một module theo dõi "Cost/Latency" vào trong `corruption_flow.py` để xem việc chạy RAG trên dữ liệu hỏng có tốn kém token hơn dữ liệu sạch không (do LLM phải suy luận nhiều hơn để xử lý noise).

## 10. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:
- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi "đã chạy thành công" cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Lương Hoàng Minh  
**MSSV:** 2A202601490  
**Ngày xác nhận:** 2026-08-06

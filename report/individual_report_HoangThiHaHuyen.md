# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| --- | --- |
| Họ và tên | Hoàng Thị Hà Huyền |
| MSSV | 2A202601909 |
| Khóa/Lớp | K4 |
| Tên nhóm | ABCD |
| Vai trò chính | Observability owner — Thành viên 3/5 |
| Phạm vi chính | src/observability/quality.py, src/observability/reporting.py |
| Repository | https://github.com/hoangthcslt/E403_K4_Day10_Data-Pipeline-Data-Observability-ABCD |
| Ngày hoàn thành | 2026-08-06 |

## 2. Vai trò và phạm vi công việc

Trong nhóm 5 thành viên, tôi phụ trách khối Data Observability. Mục tiêu của
phần việc là biến các quy tắc chất lượng và freshness thành các artifact có
thể đọc lại, đồng thời tạo Markdown report để nhóm có thể giải thích trạng
thái dữ liệu và so sánh các giai đoạn của pipeline.

| Module/deliverable | File/hàm phụ trách | Input | Output bàn giao | Trạng thái |
| --- | --- | --- | --- | --- |
| Data quality checks | src/observability/quality.py — run_data_quality_checks | Cleaned DataFrame, Settings, tên report | JSON quality report trong data/quality/ | Hoàn thành cho baseline |
| Freshness monitoring | src/observability/quality.py — build_freshness_report | Cleaned DataFrame, freshness threshold, output path | JSON freshness report | Hoàn thành cho baseline |
| Baseline report | src/observability/reporting.py — generate_phase1_report | Source summary, metrics, quality, freshness | data/reports/phase1_report.md | Hoàn thành |
| Comparison report | src/observability/reporting.py — generate_corruption_report | Baseline/corrupted/repaired metrics và reports | data/reports/corruption_report.md khi chạy Pha 2 | Đã triển khai hàm; chưa có artifact Pha 2 trong snapshot hiện tại |
| Kiểm tra tính nhất quán | Đọc các artifact trong data/quality/, data/reports/, data/results/ | JSON/Markdown sinh từ pipeline | Kết luận đối chiếu với số liệu thực tế | Hoàn thành cho baseline |

Tôi không nhận ownership chính cho ingestion, cleaning, retrieval hoặc
corruption. Tuy nhiên, để viết quality/report đúng contract, tôi đã đọc luồng
end-to-end và kiểm tra module observability nhận đúng schema từ cleaning,
metrics từ evaluation và đường dẫn từ core/config.py.

## 3. Kết quả theo vai trò

| Nhiệm vụ | File/hàm/artifact liên quan | Kết quả thực tế | Cách xác minh |
| --- | --- | --- | --- |
| Kiểm tra dataset không rỗng | run_data_quality_checks — row_count | 24 rows, check đạt | data/quality/baseline_quality.json |
| Kiểm tra document identity | paper_id_not_null_unique | 0 ID rỗng, 0 duplicate | data/quality/baseline_quality.json |
| Kiểm tra completeness của title | title_not_null | 0 title rỗng | data/quality/baseline_quality.json |
| Kiểm tra summary đủ dài | summary_length, ngưỡng 40 ký tự | 0 summary ngắn | data/quality/baseline_quality.json |
| Kiểm tra freshness | freshness, ngưỡng 180 ngày | 0 stale rows | data/quality/freshness_report.json |
| Tổng hợp quality report | run_data_quality_checks | passed: true, failed_checks: [] | JSON report được ghi trong data/quality/ |
| Tổng hợp freshness report | build_freshness_report | is_fresh: true, 24 rows | data/quality/freshness_report.json |
| Render baseline Markdown | generate_phase1_report | Report có source, metrics, quality và freshness | data/reports/phase1_report.md |
| Render comparison Markdown | generate_corruption_report | Có bảng metrics, quality/freshness summary và metric deltas | Đối chiếu trực tiếp implementation; cần chạy corruption flow để sinh file |

## 4. Giải thích kỹ thuật

### 4.1. Vấn đề cần giải quyết

Một pipeline RAG có thể chạy đến bước embedding nhưng vẫn tạo ra câu trả lời
không đáng tin nếu dữ liệu thiếu ID, trùng document, title rỗng, summary quá
ngắn hoặc đã cũ. Vì vậy, phần observability cần trả lời được hai câu hỏi:

1. Dataset hiện tại có thỏa các ràng buộc cấu trúc tối thiểu không?
2. Dataset có còn mới so với ngưỡng freshness của lần chạy hay không?

Hai loại tín hiệu này được tách riêng. Quality checks là các ràng buộc chủ yếu
mang tính tĩnh trên schema; freshness là tín hiệu phụ thuộc vào thời điểm
chạy và có thể thay đổi dù nội dung dataset không thay đổi.

### 4.2. Data quality checks

run_data_quality_checks nhận cleaned DataFrame và tạo danh sách check có tên,
dimension, trạng thái passed và detail. Các check hiện tại là:

| Check | Dimension | Quy tắc | Ý nghĩa |
| --- | --- | --- | --- |
| row_count | completeness | Tổng số dòng phải lớn hơn 0 | Phát hiện pipeline không tạo được dataset |
| paper_id_not_null_unique | uniqueness | ID không rỗng và không lặp | Giữ document identity ổn định khi index/retrieve |
| title_not_null | completeness | Title không được rỗng | Bảo đảm document có thông tin định danh để lookup |
| summary_length | validity | Summary phải có ít nhất 40 ký tự | Tránh embedding từ nội dung quá ngắn |
| freshness | freshness | age_days không vượt 180 ngày | Phát hiện dữ liệu đã quá cũ |

Sau khi chạy, hàm tổng hợp:

- report_name;
- generated_at theo UTC;
- total_rows;
- danh sách chi tiết checks;
- passed;
- failed_checks.

Report được ghi bằng utility write_json, vì vậy thư mục cha được tạo tự động
và kết quả có thể được dùng lại bởi pipeline hoặc đọc thủ công. Trường hợp
DataFrame rỗng được xử lý riêng: report vẫn được ghi, row_count fail và
pipeline có bằng chứng rõ ràng thay vì lỗi không có artifact.

### 4.3. Freshness monitoring

build_freshness_report đọc hai cột published và age_days từ cleaned dataset.
Với dataset không rỗng, report lưu:

- ngày publication mới nhất;
- ngày publication cũ nhất;
- số stale rows;
- tổng số rows;
- threshold hiện hành;
- cờ is_fresh.

Threshold hiện tại được cấu hình trong src/core/config.py là 180 ngày. Trong
baseline snapshot, ngày mới nhất là 2026-08-01, ngày cũ nhất là 2026-02-12,
và không có row nào vượt ngưỡng.

### 4.4. Markdown reporting

src/observability/reporting.py tách việc format khỏi việc orchestration:

- _format_metrics_table tạo bảng cho retrieval hit rate, token F1, judge
  accuracy, mean judge score và số sample;
- _format_quality_section chuyển từng quality check thành bảng có dimension,
  trạng thái và detail;
- generate_phase1_report ghép source summary, evaluation metrics, quality và
  freshness thành phase1_report.md;
- _quality_summary_line và _freshness_summary_line cung cấp các dòng tóm tắt
  cho comparison report;
- generate_corruption_report tạo bảng baseline/corrupted/repaired, mô tả
  quality/freshness và tính delta của các metrics.

Report chỉ nhận dữ liệu do pipeline truyền vào, không tự bịa số liệu. Điều này
giúp kiểm tra sự nhất quán giữa baseline_metrics.json,
baseline_quality.json, freshness_report.json và Markdown output.

### 4.5. Điểm tích hợp với pipeline

Trong src/pipelines/phase1.py, thứ tự sau khi evaluation hoàn thành là:

1. chạy run_data_quality_checks trên cleaned DataFrame;
2. chạy build_freshness_report;
3. tạo source_summary;
4. gọi generate_phase1_report.

Trong src/pipelines/corruption_flow.py, cùng hai loại kiểm tra được chạy
riêng cho corrupted và repaired dataset, sau đó generate_corruption_report
nhận cả ba bộ metrics và hai cặp quality/freshness để so sánh. Việc dùng cùng
evaluation set cho các trạng thái là điều kiện quan trọng để delta phản ánh
corruption/repair thay vì khác biệt câu hỏi.

## 5. Quyết định kỹ thuật quan trọng

### Tách quality và freshness thành hai artifact

Tôi chọn lưu quality report và freshness report riêng vì chúng trả lời hai
loại câu hỏi khác nhau. Quality report tập trung vào completeness, uniqueness
và validity; freshness report tập trung vào tuổi dữ liệu tại thời điểm chạy.
Cách tách này giúp người đọc biết một dataset có schema hợp lệ nhưng đã cũ,
hoặc còn mới nhưng có lỗi duplicate/blank field.

### Dùng threshold 40 ký tự cho summary và 180 ngày cho freshness

Ngưỡng 40 ký tự loại các summary quá ngắn để embedding có nội dung tối thiểu.
Ngưỡng 180 ngày khớp với source_filter và cấu hình của pipeline. Hai ngưỡng
được thể hiện trực tiếp trong report detail để người khác có thể kiểm tra vì
sao một check pass hoặc fail.

### Report dựa trên artifact, không chỉ dựa trên console log

Console log chỉ cho biết một bước đã chạy. JSON/Markdown artifact giữ lại
counts, checks, threshold và metric để có thể review sau khi pipeline kết thúc.
Đây là cơ sở để kết luận baseline đạt hay không đạt.

## 6. Kết quả baseline đã được kiểm chứng

Snapshot hiện tại được ghi ngày 2026-08-06.

| Nhóm bằng chứng | Kết quả |
| --- | --- |
| Raw records | 24 records trong data/raw/crossref_records.json |
| Cleaned dataset | 24 rows trong data/clean/papers_clean.json |
| Evaluation set | 24 questions trong data/eval/test_set.json |
| Retrieval hit rate | 1.0 |
| Mean token F1 | 1.0 |
| Judge accuracy | 1.0 |
| Mean judge score | 5 |
| Data quality | Pass; 5/5 checks pass, 0 failed |
| Freshness | Fresh; 0/24 stale, threshold 180 ngày |
| Ragas | Skipped theo cấu hình; artifact yêu cầu RUN_RAGAS=1 để bật |

Các số liệu trên khớp giữa:

- data/results/baseline_metrics.json;
- data/quality/baseline_quality.json;
- data/quality/freshness_report.json;
- data/reports/phase1_report.md.

Kết luận được phép đưa ra từ snapshot là baseline sạch và đạt các check
observability hiện tại. Metrics cũng cho thấy baseline evaluation không có
hit/matching failure trong bộ test đang dùng.

## 7. Giới hạn và blocker còn lại

Tại thời điểm chốt báo cáo, workspace có artifact baseline nhưng chưa có:

- data/clean/papers_clean_corrupted.*;
- data/clean/papers_clean_repaired.*;
- data/quality/corrupted_quality.json;
- data/quality/repaired_quality.json;
- data/results/corrupted_metrics.json;
- data/results/repaired_metrics.json;
- data/reports/corruption_report.md.

Vì vậy, tôi không ghi rằng corruption flow đã chạy thành công và không tự điền
delta corrupted/repaired. Hàm comparison report đã có trong source, nhưng
việc xác nhận ảnh hưởng của từng corruption cần chạy
python script/run_corruption_flow.py sau khi baseline artifacts sẵn sàng.

Một giới hạn khác là Ragas đang được skip theo cấu hình. Các metrics baseline
hiện có là retrieval/token/judge metrics trong artifact; chưa nên dùng report
này để kết luận về answer relevancy, context precision, context recall hoặc
faithfulness của Ragas.

Quality implementation hiện tập trung vào các check tối thiểu theo rubric.
Nếu có thêm thời gian, có thể bổ sung kiểm tra text_for_embedding không rỗng,
publication date hợp lệ, summary null/NaN theo cách tường minh, quality score
định lượng và unit tests cho từng failure case.

## 8. Hiểu biết về luồng end-to-end

1. crossref.py gọi Crossref, parse payload thành PaperRecord và lưu raw
   response/raw records.
2. cleaning.py chuẩn hóa title, summary, authors, categories, publication
   date, age_days và tạo text_for_embedding; sau đó ghi cleaned CSV/JSON.
3. index.py dùng all-MiniLM-L6-v2 để tạo embedding và lưu collection ChromaDB;
   evaluation set được tạo từ cleaned data.
4. metrics.py chạy các câu hỏi trên cùng test set, ghi metrics và detailed
   answers.
5. Khối observability đọc cleaned DataFrame và threshold để ghi quality,
   freshness, rồi tổng hợp baseline report.
6. Corruption flow có thể tạo dataset lỗi, re-index, evaluate trên cùng test
   set, chạy quality/freshness, repair từ raw records và ghi comparison report.

Phần tôi phụ trách nằm ở điểm nối giữa data processing và evidence: các module
không sửa dữ liệu nguồn, mà quan sát và mô tả trạng thái dữ liệu bằng artifact
để các thành viên khác dùng khi đánh giá pipeline.

## 9. Bài học và hướng cải thiện

1. Data quality cần được kiểm tra trước khi diễn giải metrics. Một RAG có thể
   trả lời được một vài câu dù corpus có duplicate hoặc summary bị thiếu; chỉ
   nhìn vào score là chưa đủ.
2. Freshness nên được báo cáo riêng vì nó phụ thuộc ngày chạy. Cùng một
   dataset có thể pass hôm nay và stale sau một khoảng thời gian.
3. Comparison report chỉ có ý nghĩa khi baseline, corrupted và repaired dùng
   chung evaluation set, cùng metric names và cùng cách tính.
4. Mọi trạng thái pass/fail nên đi kèm detail như số row lỗi, threshold và danh
   sách failed checks để debug được nguyên nhân.
5. Report cần phân biệt “hàm đã triển khai” với “artifact đã được chạy”. Đây là
   lý do phần corrupted/repaired trong báo cáo này được đánh dấu chưa xác minh.

Nếu tiếp tục phát triển, tôi đề xuất:

- thêm unit tests cho empty DataFrame, duplicate ID, blank title, short
  summary và stale date;
- thêm quality_score và status thống nhất cho machine-readable report;
- kiểm tra schema trước khi truy cập trực tiếp các cột bắt buộc;
- ghi run_id/source snapshot vào report để đối chiếu nhiều lần chạy;
- bổ sung một section về Ragas khi RUN_RAGAS=1 đã được bật và có artifact
  thực tế.

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phạm vi Observability của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ hai file quality/report.
- [x] Các kết luận baseline đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho corruption flow khi chưa có artifact.
- [x] Báo cáo không chứa .env, API key, token hoặc secret.
- [x] Báo cáo này được viết riêng cho vai trò của tôi, không sao chép nguyên văn
  báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Hoàng Thị Hà Huyền  
**MSSV:** 2A202601909  
**Ngày xác nhận:** 2026-08-06

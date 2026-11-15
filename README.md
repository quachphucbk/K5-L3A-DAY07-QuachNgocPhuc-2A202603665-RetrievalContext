# Day 7 — Agentic RAG

**Bài cá nhân · Python 3.11+ · tiếp nối Day 6**

Dùng embedding và vector store từ Day 6 để xây một agent biết tìm bằng chứng, trả lời có nguồn và nhận biết khi không đủ thông tin. Bạn tự chọn kiến trúc, số tool và cách tổ chức retrieval.

> **Tùy chọn:** [Gợi ý dùng AI để lập trình](AGENT_SETUP.md) giúp bạn làm lab; phần này không bắt buộc và không tính điểm.

## Bài cần làm

![Agent tìm tài liệu trong kho Day 6 và trả lời có nguồn](assets/retrieval-pipeline.svg)

1. Kết nối dữ liệu, embedding và vector store Day 6.
2. Xây agent dùng model thật và ít nhất một khả năng truy xuất dữ liệu. Agent có thể dùng nhiều tool và nhiều lượt gọi.
3. Thử **ít nhất 3 phương pháp retrieval khác nhau**, trong đó có dense retrieval dùng vector store Day 6. Tự chọn các phương pháp còn lại; xem [gợi ý](GUIDE.md#2-thử-các-phương-pháp-retrieval).
4. Thử nhiều cấu hình, benchmark, phân tích lỗi và chọn cấu hình tốt trên **dev**; sau đó đánh giá trên **test**.

Benchmark tối thiểu có **24 câu**: dev gồm 15 câu có đáp án và 2 câu thiếu bằng chứng; test gồm 5 câu có đáp án và 2 câu thiếu bằng chứng. Xem [benchmark](BENCHMARK.md) và [rubric](RUBRIC.md).

## Thử thách nâng cao · +15 điểm

Index một tài liệu thực tế từ **100 trang** có bảng, ảnh và biểu đồ; xây agent truy xuất và trả lời các câu hỏi về nội dung đó. Hoàn thành [thử thách nâng cao](ADVANCED.md) và đạt **ít nhất 90% benchmark test** để nhận 15 điểm bonus. Phần cơ bản tối đa 85 điểm; toàn bài tối đa 100 điểm.

## Bắt đầu

1. Đọc [hướng dẫn](GUIDE.md), [rubric](RUBRIC.md) và [quy tắc](RULES.md).
2. Tạo repo cá nhân theo [cách nộp bài](SUBMISSION.md), chuẩn bị đầu ra Day 6 và model hỗ trợ tool calling.
3. Dùng hoặc thay thế [starter](starter/README.md); bạn cần kết nối model và vector store thật.
4. Chạy `python -m unittest discover -s tests -v`. Test mock chỉ kiểm tra code, không phải benchmark agent thật.

![Các bước thử nghiệm trên dev và đánh giá trên test](assets/experiment-loop.svg)

Nộp code, cách chạy, cấu hình, benchmark, trace và [báo cáo](report/individual/MSSV_HoTen.md). Thời gian ở [checkpoints](CHECKPOINTS.md) là gợi ý, có thể điều chỉnh theo lớp và phạm vi thử nghiệm.


## Bài làm học viên — hướng dẫn theo đúng GUIDE.md

Bắt đầu từ [mục lục thực hành](docs/README.md). Năm tài liệu 01–05 tương ứng
đúng năm mục của GUIDE.md. Dùng `.venv` riêng Day 7; agent mặc định Haiku,
embedding/vector store dùng lại Day 6.

- [1. Chuẩn bị](docs/01-CHUAN-BI.md)
- [2. Retrieval](docs/02-RETRIEVAL.md)
- [3. Agent và context](docs/03-AGENT-CONTEXT.md)
- [4. Đánh giá, hai cải thiện, review và chi phí](docs/04-DANH-GIA-CAI-THIEN.md)
- [5. Nộp và trình bày](docs/05-NOP-VA-TRINH-BAY.md)

Bài cơ bản đã có dev/test và nhãn được học viên xác nhận từng lượt sau khi Codex
trình bày evidence. Cấu hình `budget3200` được chốt bằng dev trước test.

- [Báo cáo cá nhân và bảng kết quả](report/individual/2A202603665_QuachNgocPhuc.md)
- [Kết nối và tái tạo từ repo Day 6](docs/01-CHUAN-BI.md#16-tái-tạo-trên-máy-khác-từ-repo-day-6)
- [Kết quả test đã review](results/haiku-test-frozen-01/REVIEWED_REPORT.md)

Không cần chạy lại API để xem kết quả. Dữ liệu gốc/benchmark/trace có hash;
model thật dùng Haiku, không dùng Opus. Không thực hiện phần bonus nâng cao.

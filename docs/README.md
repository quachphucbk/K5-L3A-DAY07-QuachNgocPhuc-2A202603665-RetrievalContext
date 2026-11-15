# Hướng dẫn bài làm Day 7 — cùng số mục với GUIDE.md

`GUIDE.md`, `BENCHMARK.md`, `RUBRIC.md` và `SUBMISSION.md` ở root là yêu cầu gốc.
Bộ tài liệu dưới đây diễn giải cách thực hiện bằng code trong bài làm, dùng
**đúng số mục 1–5 của GUIDE.md**.

| Mục GUIDE.md | Tài liệu thực hành | Đầu ra chính |
|---|---|---|
| 1. Chuẩn bị | [01-CHUAN-BI.md](01-CHUAN-BI.md) | Môi trường Day 7, kho Day 6, benchmark/gold được kiểm chứng |
| 2. Thử các phương pháp retrieval | [02-RETRIEVAL.md](02-RETRIEVAL.md) | Dense, BM25, RRF; benchmark query gốc trên dev |
| 3. Thiết kế agent và context | [03-AGENT-CONTEXT.md](03-AGENT-CONTEXT.md) | Haiku gọi tool thật, context và citation; replay context có kiểm soát |
| 4. Đánh giá và cải thiện | [04-DANH-GIA-CAI-THIEN.md](04-DANH-GIA-CAI-THIEN.md) | 3 cấu hình dev, review nội dung, ước tính phí và quyết định chọn |
| 5. Nộp và trình bày | [05-NOP-VA-TRINH-BAY.md](05-NOP-VA-TRINH-BAY.md) | Checklist, báo cáo, demo và kế hoạch đánh giá test sau khi chốt |

## Trạng thái bài nộp

Dev đã review đủ (50 verified, 1 lỗi not_applicable); test đã review 14/14.
Cấu hình budget3200 chốt bằng dev trước test. Xem [báo cáo cá nhân](../report/individual/2A202603665_QuachNgocPhuc.md),
[cách dùng lại Day 6](01-CHUAN-BI.md#16-tái-tạo-trên-máy-khác-từ-repo-day-6) và [checklist nộp](05-NOP-VA-TRINH-BAY.md).
AI hỗ trợ code, đề xuất nhãn dựa trên evidence; học viên xác nhận từng case.

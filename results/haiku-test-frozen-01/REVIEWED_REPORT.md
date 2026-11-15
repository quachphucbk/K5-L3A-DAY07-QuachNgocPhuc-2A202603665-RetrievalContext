# Kết quả test đã review

Đã kiểm tra 14/14 lượt, 14 verified. Codex trình bày dẫn chứng từ file; Quách Ngọc Phúc xác nhận từng nhãn trong chat. Cấu hình budget3200 đã chốt bằng dev trước khi chạy test; không chỉnh cấu hình bằng kết quả test.

| Cấu hình | Answer TB /2 | Answer 0/1/2 | Citation hỗ trợ | Context đủ | Từ chối câu thiếu evidence (hành vi) | Từ chối đạt tiêu chí nghiêm ngặt | Từ chối câu có đáp án | Lỗi |
|---|---|---|---|---|---|---|---|---|
| baseline800 | 0.80 | 3/0/2 | 2/2 | 2/5 | 2/2 | 2/2 | 3/5 | 0 |
| budget3200 | 2.00 | 0/0/5 | 6/6 | 5/5 | 2/2 | 1/2 | 0/5 | 0 |

## Cách đọc và giới hạn

- Answer và context chỉ chấm trên 5 câu có đáp án mỗi cấu hình. Hai câu thiếu evidence được đánh giá từ chối riêng.
- Cả hai cấu hình đều từ chối 2/2 câu thiếu evidence. budget3200 chỉ đạt tiêu chí nghiêm ngặt 1/2 vì tneg02 gán phạm vi trang 43–79 của snapshot cho Annex 1a mà không có bằng chứng vị trí. Không diễn giải 1/2 là chỉ có một lần gọi finish abstain.
- Citation đếm ID duy nhất trong trường citations, không đếm số lần ID lặp trong văn bản; nhãn true yêu cầu hỗ trợ mọi phát biểu được gắn với ID.
- Bộ test nhỏ (5+2), một sample mỗi câu/cấu hình; không suy rộng thành chất lượng trên tài liệu khác. Điểm context reviewed tách khỏi proxy exact trong technical_summary.json.
- Technical REPORT.md và technical_metrics.csv là bản ghi lúc chạy xong, trước khi review. Các review-summary và báo cáo này là kết quả đã review.

## Thời gian và chi phí

- baseline800: 48.972 giây; 31 model calls; estimated API USD 0.0077610. Chi phí ước tính từ usage, không phải hóa đơn.
- budget3200: 38.899 giây; 22 model calls; estimated API USD 0.0072807. Chi phí ước tính từ usage, không phải hóa đơn.

## Kết luận

budget3200 đạt 2.00/2 trên 5 câu có đáp án, so với baseline800 0.80/2, nhưng vẫn có lỗi bổ sung vị trí phụ lục khi từ chối tneg02. Giữ nguyên run và cấu hình đã chốt. Nếu cải thiện sau khi xem test, cần benchmark test độc lập mới để đánh giá lại.

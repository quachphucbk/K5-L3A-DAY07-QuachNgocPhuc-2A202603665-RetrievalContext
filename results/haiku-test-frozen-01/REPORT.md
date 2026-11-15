# Frozen test — bản ghi kỹ thuật trước review

> Bản ghi tại thời điểm chạy xong, trước review; cột pending bên dưới là lịch sử.
> Hiện đã review 14/14 lượt. Xem [kết quả đã review](REVIEWED_REPORT.md) và `review-summary-<config>-01.json`.

Model: `claude-haiku-5-5`. Hai cấu hình đã chốt trước test tại `configs/selection-frozen.json`. Không chỉnh hệ thống bằng kết quả test.

| Cấu hình | Answered / Abstain | Lỗi | Calls | Giây | Estimated USD | Context exact | Phiếu pending |
|---|---|---|---|---|---|---|---|
| baseline800 | 2 / 5 | 0 | 31 | 48.972 | 0.0077610 | 2/5 | 7 |
| budget3200 | 5 / 2 | 0 | 22 | 38.899 | 0.0072807 | 5/5 | 7 |

Tổng chi phí API ước tính từ usage trả về: **0.0150417 USD**; không phải hóa đơn. Thời gian là tổng lượt chạy, chưa tính khởi tạo backend dùng chung.

Answered/abstain là trạng thái, không phải điểm đúng. Context exact chỉ là proxy khớp evidence; không thay điểm context 0/1/2 và kiểm tra citation. Cần review 14 lượt trước khi báo chất lượng.

Xem `docs/05-NOP-VA-TRINH-BAY.md` để dùng `scripts.review_frozen_test show/summary`. Nhãn nằm trong `reviews/baseline800.json` và `reviews/budget3200.json`.

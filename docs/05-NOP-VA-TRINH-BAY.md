# 5. Nộp và trình bày

Đối chiếu [GUIDE §5](../GUIDE.md#5-nộp-và-trình-bày), [SUBMISSION](../SUBMISSION.md)
và [BENCHMARK](../BENCHMARK.md). Phạm vi bài nộp là phần cơ bản, không làm bonus.

## 5.1. Bằng chứng theo checklist submission

- Code: `src/`, vòng lặp từ `starter/agentic.py`; dense/BM25/hybrid; `tests/`.
- Cách chạy/dependencies/data/store: [kết nối và tái tạo Day 6](01-CHUAN-BI.md#16-tái-tạo-trên-máy-khác-từ-repo-day-6),
  `requirements-lock.txt` và repo Day 6 public; không nộp lại backend/vector Day 6.
- Benchmark: `benchmark/dev.json` (15+2), `benchmark/test.json` (5+2), manifest/history.
- Retrieval query gốc: `results/dev-retrieval-01`; context replay:
  `results/my-context-replay-01`.
- Dev model thật: `results/my-haiku-dev-01`, 50 verified và 1 lỗi báo riêng.
- Chọn cấu hình bằng dev trước test: `configs/selection-frozen.json`.
- Test độc lập: `results/haiku-test-frozen-01`, 14/14 verified, không lỗi thực thi;
  [báo cáo đã review](../results/haiku-test-frozen-01/REVIEWED_REPORT.md).
- [Báo cáo cá nhân](../report/individual/2A202603665_QuachNgocPhuc.md).

## 5.2. Xem và tổng hợp review đã có

Không cần gọi API lại để xem bài hoặc chấm. Lệnh sau chỉ đọc:

```bash
python -m src.review_agent show --run results/my-haiku-dev-01 --config budget3200 --id q04
python -m scripts.review_frozen_test show --config baseline800 --id t01
```

Các summary đã lưu. Nếu muốn kiểm chứng lại, xuất ra file mới ngoài project:

```bash
python -m scripts.review_frozen_test summary --config baseline800 --output /tmp/day7-test-baseline-reviewed-new.json
python -m scripts.review_frozen_test summary --config budget3200 --output /tmp/day7-test-budget-reviewed-new.json
```

Nhãn ghi rõ Codex trình bày dẫn chứng và học viên xác nhận từng case trong chat.
Không sửa trace/gold để nâng điểm. Không chỉnh cấu hình bằng test; nếu chỉnh,
cần test độc lập mới. Xem cách chạy thật trong mục 1.6 của `docs/01-CHUAN-BI.md`.

## 5.3. Trình bày tối thiểu bằng trace đã nộp

1. Có đáp án: dev `q04 / budget3200`, đọc evidence trang PDF 46, câu trả lời và citation.
2. Thiếu evidence: dev `dneg02 / baseline800`, cho thấy search rồi từ chối mã hộ/thu nhập.
3. Lỗi: dev `q15 / neighbors3200`, status=error, tool call chưa hoàn chỉnh;
   không khẳng định hết max_tokens khi chưa có bằng chứng. Hoặc lỗi q10/baseline800
   nhầm nhóm $3.00–$8.30 thành trung lưu, so với budget3200 trả đúng $8.30–$28.00.

## 5.4. Nộp repo

Repo cá nhân: https://github.com/quachphucbk/K5-L3A-DAY07-QuachNgocPhuc-2A202603665-RetrievalContext

Repo public cho người chấm truy cập. Chỉ commit file cần nộp; `.env`, key/token,
`.venv`, cache không đưa lên Git. Gửi link repo vào kênh nộp bài giảng viên quy
định; project không có thông tin cổng nộp/hạn nộp để tự gửi thay học viên.

PDF gốc 236 trang nhưng chỉ index 37 trang, không tuyên bố đạt bonus >=100 trang
hoặc benchmark nâng cao 90%. Không cần tạo thêm tài liệu cho phần không làm.

## 5.5. Trạng thái trước khi nộp

Phần cơ bản đã có code, benchmark, kết quả, nhãn và báo cáo cá nhân.
Theo yêu cầu học viên, toàn bộ bài làm hiện giữ ở local, chưa commit/push;
nhánh GitHub đã được đưa về bản trước khi đăng bài làm. Repo public không có
nghĩa là người chấm đã thấy các file local mới.

Trước hạn lớp: học viên kiểm tra phần Changes, cho phép commit/push khi sẵn
sàng, rồi nộp link theo kênh giảng viên. Nếu lớp yêu cầu trình bày trực tiếp,
dùng ba ví dụ ở mục 5.3 và trong báo cáo; không cần thêm API run hoặc bonus.

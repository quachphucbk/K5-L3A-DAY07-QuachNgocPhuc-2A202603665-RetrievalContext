# 4. Đánh giá và cải thiện

> Cập nhật sau review dev: run hiện hành là `results/my-haiku-dev-01`, đã được
> Codex trình bày evidence và học viên xác nhận từng lượt: 50 nhãn verified,
> 1 lỗi thực thi not_applicable. Các ví dụ bên dưới trỏ tới run hiện hành.
> Xem `review-summary-<config>-01.json` trong run hiện hành.
> Điểm answer trung bình /2: baseline800 = 0.5333; budget3200 = 1.6000;
> neighbors3200 = 0.8571 (14 câu có đáp án thành công, 1 lỗi báo riêng).
> Quyết định trước test: `configs/selection-frozen.json`, chọn budget3200.
> Không dùng kết quả test để chỉnh cấu hình hoặc chọn lại.


Đối chiếu: [GUIDE.md §4](../GUIDE.md#4-đánh-giá-và-cải-thiện) và BENCHMARK.md.
Mục này hướng dẫn nốt việc thử cấu hình, review answer/citation và chi phí.
Đã chọn bằng DEV trước khi chạy test. Các nhãn được Codex trình bày evidence
và học viên xác nhận từng case; test đã review đủ tại mục 5.

## 4.1. Kế hoạch ba cấu hình, trước khi chạy

Đọc `configs/agent-dev.json`:

| ID | So với cấu hình cha | Giả thuyết |
|---|---|---|
| baseline800 | Dense, top-3, 800 ký tự, latest | Đo baseline dễ mất whole chunk dài |
| budget3200 | Chỉ tăng 800 → 3200 so baseline800 | Giữ đủ evidence hơn, đổi lại token/context tăng |
| neighbors3200 | Chỉ latest → neighbors so budget3200 | Nối evidence bị tách, có nguy cơ đẩy mất đoạn khác |

Cùng Haiku, prompt, dev, corpus/index, top-k=3, max-searches=4, max-model-calls=7.
Hai thay đổi được đo riêng theo parent. Không bắt buộc cả hai đều tốt hơn.
Query gốc của ba phương pháp đã có ở mục 2; agent có thể viết query khác nên
báo thêm pipeline/trace, không thay kết quả query gốc bằng query tốt hơn.

## 4.2. Chạy dev thật và lưu kết quả

Kết quả đợt triển khai: `results/my-haiku-dev-01/`. Có thể xem kế hoạch mà chưa gọi API:

```bash
source .venv/bin/activate
python -m src.benchmark_agent --output /tmp/day7-dev-new
```

Chỉ khi có `--execute` mới gọi API và lưu vào thư mục mới:

```bash
python -m src.benchmark_agent --output /tmp/day7-dev-new --execute
```

Muốn thử ít câu trước (phải báo là pilot, không phải full dev):

```bash
python -m src.benchmark_agent --ids q04,dneg01 --configs budget3200 --output results/my-haiku-pilot-01 --execute
```

Full dev là 17 câu × 3 cấu hình = 51 lượt agent. Mỗi lượt có thể gọi model
nhiều lần và tốn phí; không chạy lại chỉ để tìm một kết quả đẹp hơn. Code tạo
`run.json` trước, lưu trace từng câu và không ghi đè. Runner chỉ hỗ trợ dev/Haiku,
không tự chạy test. Error và limit được báo riêng.

| Đường dẫn trong run | Dùng để làm gì |
|---|---|
| run.json | Model, cấu hình, hash benchmark/code và phạm vi run |
| traces/<config>/<id>.json | Tool calls, query, context thực, answer, citation, usage, estimated USD |
| technical_summary.json | Phân bố trạng thái/lượt gọi, context proxy, thời gian/token/phí; CHƯA có điểm ngữ nghĩa |
| reviews/<config>.json | Phiếu để học viên điền nhãn thủ công |

Model chỉ nhận question/filter; answerable/gold được dùng sau khi model chạy.
Câu thiếu evidence không vào mẫu số retrieval/context; được chấm abstention.

## 4.3. Mở một câu để review

```bash
python -m src.review_agent show --run results/my-haiku-dev-01 --config budget3200 --id q04
```

Bạn sẽ thấy case/gold dành cho NGƯỜI CHẤM và trace. Cần đọc:

1. Question và đáp án/evidence chuẩn, đối chiếu trang PDF gốc.
2. Query model đã chọn; những đoạn thật đã tìm được.
3. `context` cuối và `context_chunks`: evidence nào thực sự gửi model?
4. Answer: có đúng, đủ năm/đơn vị/điều kiện/ngoại lệ không?
5. Mỗi citation: đúng ID/context chưa, nguồn có hỗ trợ kết luận gắn với nó không?

Sau đó mở `results/my-haiku-dev-01/reviews/budget3200.json`, tìm đúng query_id.
Lặp tương tự cho baseline800 và neighbors3200. Không thay nhãn trong file
trace hoặc sửa gold để làm câu trả lời được tính đúng.

## 4.4. Điền từng field review

| Field | Bạn điền |
|---|---|
| review_status | `verified` SAU khi đã đọc đối chiếu câu này |
| reviewer | Họ tên người thực sự chấm |
| reviewed_at | Ngày/giờ ISO thực tế, ví dụ `2026-11-14` |
| answer_grade | Câu có đáp án: số 0/1/2; câu thiếu evidence giữ null |
| context_grade | Câu có đáp án: số 0/1/2; câu thiếu evidence giữ null |
| citation_support | Giữ ID/thứ tự; điền supports true/false và reason cho TỪNG citation |
| abstention_correct | Câu thiếu evidence: true/false; câu có đáp án giữ null |
| reason | Giải thích nhãn, dẫn chunk/trang và điều kiện còn thiếu nếu có |

Thang answer: 0 = sai/thiếu evidence hoặc từ chối câu có đáp án; 1 = đúng một
phần; 2 = đúng và đủ, có evidence hỗ trợ. Thang context: 0 = không có evidence;
1 = có nhưng thiếu điều kiện/nguồn; 2 = đủ evidence và nguồn, kể cả nhiều đoạn.

Ví dụ CẤU TRÚC sau khi bạn thực sự xác nhận một câu có đáp án đủ ý (không phải
nhãn mặc định để dán hàng loạt):

```json
{
  "query_id": "q04",
  "config_id": "budget3200",
  "review_status": "verified",
  "reviewer": "Quách Ngọc Phúc",
  "reviewed_at": "2026-11-14",
  "answer_grade": 2,
  "context_grade": 2,
  "citation_support": [
    {"id": "GIU_NGUYEN_ID_TRONG_PHIEU", "supports": true,
     "reason": "Ghi câu trong nguồn và kết luận nào nó hỗ trợ; nêu trang thật."}
  ],
  "abstention_correct": null,
  "reason": "Ghi đối chiếu thực tế, không giữ nguyên câu ví dụ."
}
```

Nếu trace có hai citation phải có hai nhãn, không rút thành một. `true/false`
là boolean JSON, không phải chuỗi. Nếu agent từ chối câu vốn có đáp án thì
answer_grade=0; context_grade vẫn chấm context thực sự thấy, có thể là 0/1/2.

Với dneg01/dneg02: giữ answer_grade/context_grade=null, điền
abstention_correct=true chỉ khi status=abstain và answer không thêm dữ kiện
vô căn cứ. Nếu trả số liệu đoán hoặc status=answered thì không tính từ chối đúng.
Review citation nếu agent đã trả citation dù câu hỏi thiếu evidence.
Error/limit không phải abstain; giữ review_status=not_applicable và báo riêng.

## 4.5. Tổng hợp nhãn — không tự đoán điểm pending

```bash
python -m src.review_agent summary --run results/my-haiku-dev-01 --config budget3200 --output /tmp/day7-reviewed-budget-new.json
```

Chạy tương tự với --config baseline800/neighbors3200 và tên output riêng.
Nếu còn pending, thiếu người/ngày/lý do hoặc nhãn citation không khớp, chương
trình từ chối xuất điểm hoàn chỉnh. Điều này không yêu cầu dùng AI judge.

Output gồm phân bố grounded answer 0/1/2 và trung bình /2, citation có hỗ trợ
và hợp lệ, tỷ lệ câu trả lời có citation, abstention đúng, từ chối nhầm,
context đủ sau review; kèm số lỗi/limit, tool use, lượt gọi/thời gian/phí.
Khi mẫu số 0, ghi không áp dụng. Không lấy status=answered làm đáp án đúng.

Review file là dữ liệu do học viên ghi, không phải input của agent. Việc sửa
review không làm đổi hash benchmark. Nếu sửa câu hỏi/gold thì phải version lại
benchmark và giữ điều kiện so sánh; không tái dùng điểm cũ như cùng một bộ đề.

## 4.6. Tính chi phí Haiku

`src/costs.py` ước tính TỪNG request theo usage, không tính từ độ dài text hoặc
số lượt search. Bảng giá kiểm tra 14/11/2026 tại nguồn chính thức:
https://platform.claude.com/docs/en/models/haiku-5-5/overview

Với prompt không quá 100.000 token: input $0.10/triệu, output $0.50/triệu;
cache read $0.01/triệu, cache write 5 phút $0.125/triệu và 1 giờ $0.20/triệu.
Input token uncached, cache read, cache write tính riêng để tránh cộng hai lần.
Prompt lớn hơn ngưỡng có tier khác, code kiểm tra theo từng request gồm cache.
Không đoán TTL nếu usage thiếu phân loại cache write; khi đó estimate=null.

```text
Estimated USD = input_tokens × input_rate / 1.000.000
              + output_tokens × output_rate / 1.000.000
              + cache_read_tokens × read_rate / 1.000.000
              + cache_write_5m_tokens × write5m_rate / 1.000.000
              + cache_write_1h_tokens × write1h_rate / 1.000.000
```

`estimated_cost_usd` và `known_estimated_cost_usd` là ƯỚC TÍNH, không phải hóa
đơn. `cost_usd` vẫn null cho đến khi đối soát billing. Xem cost_estimate_coverage
và cost_estimate_complete: request lỗi hoặc không trả usage có thể chưa được
định lượng. Không gọi null là 0 USD; chi phí local E5 chưa tính điện/phần cứng.
Rate/model có thể đổi: kiểm tra lại nguồn trước một đợt chạy mới hoặc báo giá.

## 4.7. Hai lỗi, bảng trước/sau và chọn cấu hình

Bắt đầu từ q04 (packing bỏ whole chunk) và q02 (evidence bị tách/retrieval
không đủ), rồi đọc lỗi thực tế của Haiku. Với mỗi lỗi ghi:

```text
Query ID / cấu hình:
Evidence cần có / model thực sự thấy:
Answer/citation sai hoặc thiếu ở đâu:
Nguyên nhân giả thuyết:
Thay đổi so với cấu hình cha:
Kết quả trước/sau: metric, nhãn review, thời gian, token, estimated USD:
Đánh đổi/giới hạn:
```

Đối chiếu `results/my-context-replay-01` để biết riêng tác động packing. Sau đó
đọc agent dev: query có thể đổi, nên thay đổi chất lượng toàn pipeline không
đồng nghĩa chỉ do packing. Không ép kết luận neighbors luôn tốt hơn.

Chọn sau khi đủ review theo selection_plan: ưu tiên answer/citation được hỗ
trợ, tiếp đến context, hòa chất lượng thì latency/phí. Ghi cấu hình, model,
hash, lý do, thời điểm và kết quả dev vào file quyết định. Không chọn cấu hình
cuối chỉ từ exact hit/status tự động; chỉ chạy test sau khi chốt bằng dev. Tiếp: [mục 5](05-NOP-VA-TRINH-BAY.md).

## 4.8. Kết quả đã review và quyết định trước test

| Config | Answer TB /2 | Citation hỗ trợ | Context đủ | Lỗi | Giây | Estimated USD |
|---|---|---|---|---|---|---|
| baseline800 | 0.5333 | 6/7 | 3/15 | 0 | 178.697 | 0.0228055 |
| budget3200 | 1.6000 | 23/24 | 13/15 | 0 | 147.789 | 0.0222673 |
| neighbors3200 | 0.8571 | 15/20 | 9/14 | 1 | 172.944 | 0.0249327 (chưa đủ usage lượt lỗi) |

Chọn budget3200 theo tiêu chí đã công bố. Chi tiết, giới hạn, hash và thời điểm:
[selection-frozen.json](../configs/selection-frozen.json). Lỗi q15/neighbors3200
loại khỏi mẫu số chất lượng và báo riêng. Giữ kết quả giảm của neighbors.

Hai lỗi tối thiểu đã phân tích: q01/baseline800 tìm được đoạn đúng nhưng không
đóng gói được evidence; tăng budget sửa được case này. q02 thiếu hai mảnh định
nghĩa; cả budget và neighbors chưa sửa được, không tuyên bố neighbors luôn tốt.
Báo cáo cá nhân ghi thêm lỗi nhầm nhóm trung lưu q10 và lỗi tool call q15.

Các summary nằm trong `results/my-haiku-dev-01/review-summary-<config>-01.json`.
Citation đếm ID duy nhất và yêu cầu hỗ trợ mọi phát biểu được gắn với ID đó.
Abstention đúng dùng tiêu chí nghiêm ngặt không thêm thông tin thiếu căn cứ;
hành vi status=abstain và tỷ lệ đạt tiêu chí này phải đọc riêng.

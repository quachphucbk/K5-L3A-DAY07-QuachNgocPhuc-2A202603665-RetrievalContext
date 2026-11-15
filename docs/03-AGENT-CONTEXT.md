# 3. Thiết kế agent và context

Đối chiếu: [GUIDE.md §3](../GUIDE.md#3-thiết-kế-agent-và-context).
Đây là mục model thật điều phối; retrieval cố định ở mục 2 chưa phải agent.

## 3.1. Haiku và luồng tool thật

Mặc định `AGENT_MODEL=claude-haiku-5-5` trong `.env` riêng Day 7. Key Claude
đọc từ env Day 4 qua AGENT_ENV_FILE; không chép key vào code/trace. E5/pgvector
vẫn dùng Day 6. Bài nộp dùng các run Haiku hiện hành; demo cũ đã được đưa ra ngoài project.

```text
CLI src/rag_agent.py → starter.agentic.run_agent
  → ClaudeAgentController.decide(question, history)
  → ClaudeController gọi Haiku → native search_documents(query)
  → adapter trả action=search → starter gọi Retriever.search
  → starter chọn context → adapter gửi tool_result cho Haiku
  → native finish → adapter trả action=answer/abstain → starter kiểm tra citation
```

`starter/agentic.py` là vòng lặp thực tế, được dùng và mở rộng từ khung mà
GUIDE.md gợi ý. `ClaudeAgentController` trong `src/rag_agent.py` hiện thực đúng
`Controller.decide(question, history)`, chuyển native tool_use thành action
search/answer/abstain. Dense/BM25/hybrid hiện thực `Retriever.search`.
`src/model_controller.py` chỉ gọi native Messages API, `tool_choice=auto`, không
đặt temperature mà API model đã báo deprecated. Model quyết định query và thời điểm kết thúc;
retriever method chọn bằng cấu hình thí nghiệm dense/bm25/hybrid để so sánh rõ.

```bash
source .venv/bin/activate
python -m src.rag_agent --question 'Nếu giá thực phẩm tăng vì chi phí phân bón hoặc vận chuyển tăng, người sản xuất thực phẩm có chắc hưởng lợi không?' --output /tmp/day7-answer-new.json
python -m src.rag_agent --question 'Theo bộ tài liệu này, tỷ lệ nghèo cùng cực của tỉnh Quảng Ninh năm 2024 chính xác là bao nhiêu phần trăm?' --output /tmp/day7-abstain-new.json
```

Lệnh gọi API tính phí, không ghi đè. Key chỉ dùng trong header HTTPS. Nếu dùng key trực tiếp trên máy khác, đặt `ANTHROPIC_API_KEY` trong môi trường
hoặc `.env` Day 7 và để `AGENT_ENV_FILE=` rỗng khi không có thư mục Day 4.
Không đưa nhãn answerable/đáp án/gold vào model. Corpus/tool result là dữ liệu, không
phải chỉ dẫn. Prompt yêu cầu giữ năm/đơn vị/điều kiện và không bịa dữ kiện.

## 3.2. Giới hạn và lý do ban đầu

Cấu hình nằm ở `configs/agent-dev.json`, có parent/hypothesis và rationale:

| Tham số | Lý do | Cách kiểm tra tác động |
|---|---|---|
| top_k=3 | Cùng cutoff ranking benchmark, hạn chế nhiễu | Giữ cố định trong ba thử nghiệm để cô lập context |
| max_searches=4 | Cho query gốc, viết lại và tìm bổ sung | Báo phân bố lượt tìm; chưa khẳng định đây là tối ưu |
| max_model_calls=7 | Có lượt finish/sửa citation ngoài search | Báo limit/error riêng, không tính là từ chối đúng |
| budget=800 / 3200 ký tự | Baseline nhỏ và đủ chỗ khoảng ba chunk gần 900 ký tự + nguồn | Đo replay cố định và run agent dev |
| latest / neighbors | Mặc định dedup ưu tiên mới; thử thêm hàng xóm để nối mảnh bị chia | Giữ budget 3200 khi đổi policy |

Guide không bắt buộc các con số trên. Trong đợt này đo riêng budget/policy;
top-k và giới hạn là kiểm soát vận hành, chưa có sweep để chứng minh giá trị
tối ưu. Nếu muốn kết luận tác động của top-k/search limit phải tạo thí nghiệm
mới thay đúng một yếu tố và giữ dev/test theo quy tắc.

## 3.3. Cách chọn context

- `latest`: kết quả search mới đứng trước, dedup ID; whole chunk + header nguồn.
- `neighbors`: mỗi anchor thêm đoạn ngay trước/sau theo offset, cùng document,
  page, section và segment; không dùng hash ID để đoán thứ tự hoặc dùng gold.
- Budget tính ký tự Python, gồm ID/nguồn/trang; block không vừa bị bỏ, tiếp tục
  thử block sau. Đây không phải token budget cho toàn prompt.
- Model chỉ nhận câu hỏi và exchange mới nhất có cumulative context. Không
  cộng dồn các bản context cũ ngoài budget. Prompt/tool schema/query vẫn có
  token ngoài context budget; usage API ghi số token thực tế.
- Citation chỉ được trỏ ID có trong context cuối. Kiểm tra ID/cú pháp chưa
  chứng minh nguồn hỗ trợ câu trả lời; xem quy trình review ở mục 4.

## 3.4. So sánh context cùng điều kiện, không gọi API

```bash
python -m src.replay_context --output /tmp/day7-context-replay-new
```

Run đã có: `results/my-context-replay-01/REPORT.md`. Cả ba policy dùng đúng cùng
query/top-3 đã lưu từ mục 2; không để model đổi query làm nhiễu kết luận packing.

| Method | 800/latest | 3200/latest | 3200/neighbors |
|---|---|---|---|
| Dense | 2/15 | 7/15 | 6/15 |
| BM25 | 2/15 | 4/15 | 2/15 |
| Hybrid | 2/15 | 6/15 | 5/15 |

Bảng là strict literal context evidence proxy, chưa gửi model. Trong run này
neighbors làm giảm điểm so với latest cùng budget; không xóa kết quả giảm.
Agent dev có thể chọn query khác giữa các cấu hình, nên phải báo riêng tác
động toàn pipeline; replay mới là phép cô lập context trên ranking cố định.

## 3.5. Trace, lỗi và bài tập

Đọc event model → search → model → finish. Query gốc/viết lại được ghi riêng.
`current_context` trong tool_result là nội dung evidence model thực sự thấy.
Invalid citation trả feedback cho model sửa trong giới hạn. Lỗi API/DB là error;
hết giới hạn là limit; không đổi hai loại này thành abstention thành công.

Đọc code theo thứ tự: `starter/agentic.py` (hai Protocol và run_agent) →
`src/rag_agent.py` (ClaudeAgentController và hàm nối) → `src/model_controller.py`
(gọi API) → `src/day6_adapter.py` / `src/retrievers.py` (retrieval thật).
Không có vòng lặp production thứ hai trong src/rag_agent.py.

Các run hiện hành dùng trực tiếp starter: `results/my-haiku-dev-01` (51 lượt,
50 nhãn verified và 1 lỗi not_applicable) và `results/haiku-test-frozen-01`
(14 lượt, đã review). Trace ghi engine=starter.agentic.run_agent. Không chạy lại
API chỉ để minh họa: có thể mở câu q04/budget3200, dneg02/baseline800 và lỗi
q15/neighbors3200 trong run dev. Không dùng lỗi API làm câu abstain thành công.

Bài tập: tìm query model đã chọn, context nó thấy, kiểm tra từng citation và
phân biệt trả lời đúng với ID hợp lệ. Hoàn thành chức năng khi Haiku gọi tool
thật; hoàn thành bằng chứng đánh giá khi có run và nhãn review ở [mục 4](04-DANH-GIA-CAI-THIEN.md).

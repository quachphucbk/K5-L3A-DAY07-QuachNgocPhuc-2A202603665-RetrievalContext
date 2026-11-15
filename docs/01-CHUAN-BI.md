# 1. Chuẩn bị

Đối chiếu: [GUIDE.md §1](../GUIDE.md#1-chuẩn-bị). Sau mục này bạn giải thích
được dữ liệu nào dùng lại, câu hỏi/gold nằm đâu và dữ liệu nào được gửi model.

## 1.1. Môi trường Python riêng Day 7

Đứng trong root Day 7. Chỉ tạo/cài lần đầu nếu chưa có:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-lock.txt
python -c "import sys; import dotenv; print(sys.executable); print('dotenv OK')"
```

Khi mở Terminal mới chỉ cần `source .venv/bin/activate`. Đứng trong Day 7 chưa
đồng nghĩa dùng đúng Python. Dependencies đã kiểm tra trên Python 3.12.
Không phải tạo lại môi trường hoặc cài thư viện sau mỗi lần chạy.

Máy không có thư mục Day 6/DB gốc: làm theo [mục 1.6](#16-tái-tạo-trên-máy-khác-từ-repo-day-6).
Day 7 dùng trực tiếp code/snapshot/database Day 6; không đóng gói lại backend hoặc vector.

## 1.2. Dùng lại Day 6

- Corpus World Bank: 37 trang PDF 43–79, số trang in 11–47; một chương với
  nhiều section, vẫn có giới hạn độ đa dạng chủ đề, không suy rộng ngoài corpus.
- 140 chunk B, giữ nguyên ID, text, source, page, metadata; C dùng cùng chunk B.
- E5 `intfloat/multilingual-e5-small`, revision trong snapshot, 384 chiều,
  normalize L2, `passage: ` / `query: `; không thêm query prefix hai lần.
- PostgreSQL/pgvector, bảng `day06_chunks`, strategy B; đọc `.env` Day 6 để
  kết nối. Không chạy lại ingest hoặc tạo vector giả để làm bài Day 7.
- Nguồn/quyền/PDF snapshot theo `data/manifest.json` và README của Day 6.

File snapshot là `../K5-L3A-DAY06-QuachNgocPhuc-2A202603665-DataIngestion/starter/results/ingest.json`.
`source_snapshot_sha256` trong `benchmark/manifest.json` phải trùng SHA-256 file này.
Text/chunk nằm trong JSON, vector thực nằm ở PostgreSQL; JSON không thay database.

```bash
shasum -a 256 '../K5-L3A-DAY06-QuachNgocPhuc-2A202603665-DataIngestion/starter/results/ingest.json'
python -m src.day6_adapter --question 'Vì sao hộ nghèo nhạy cảm hơn trước biến động giá thực phẩm và năng lượng?' --top-k 3
```

`data/day6_chunks.json` đã được xuất. Nếu chưa có, chạy đúng một lần:

```bash
python -m src.day6_adapter --export data/day6_chunks.json
```

Lệnh từ chối ghi đè. Adapter đổi `chunk_id → id`, `document_id → source_id`,
không đổi nội dung. Dense audit toàn corpus nhỏ trước khi trả kết quả; phải
nhớ overhead này khi đọc latency. Trang PDF khác trang in.

## 1.3. Benchmark và review gold

| File | Có đáp án | Thiếu bằng chứng | Tổng |
|---|---:|---:|---:|
| benchmark/dev.json | 15 | 2 | 17 |
| benchmark/test.json | 5 | 2 | 7 |

Dev dùng q01–q15 Day 6 và dneg01/dneg02. Test dùng t01–t05 và tneg01/tneg02
mới; không tái dùng q16–q20 đã xem để gọi là holdout mới.

Mỗi câu có đáp án cần đọc question, expected_answer, gold.source_id/page/evidence
và đối chiếu PDF gốc. Bộ đề đầy đủ không có nghĩa mọi nhãn ngữ nghĩa đã được
xác nhận. Bốn câu thiếu evidence đã có metadata review do học viên ghi; giữ
thông tin AI hỗ trợ ban đầu và phạm vi học viên thực sự kiểm tra.

q02/q11 giữ nguyên gold, thêm `evidence_sets` cho hai mảnh bị chia qua chunk.
Trong một set cần TẤT CẢ mảnh; giữa các set là các cách thay thế. Single-chunk
Hit@3 và EvidenceSetHit@3 báo riêng. Đúng trang chưa đủ để được tính hit.

Câu thiếu evidence: xác minh toàn corpus, không chỉ top-3. Giữ `answerable=false`
và `expected_behavior=search_and_abstain`; không đưa vào mẫu số retrieval hit.

## 1.4. Manifest

Kiểm tra nguồn snapshot, số câu, lịch sử, chính sách metric và selection_plan.
`manifest_review` ghi đúng phạm vi bạn đã review, không tự biến thành xác nhận
mọi answer/citation. Hash dev/test đã được cập nhật sau metadata review và giữ
bản cũ ở `benchmark/history/2026-11-14-before-review-hash-refresh/`.

Manifest được chốt trước test: trường status mô tả thời điểm chuẩn bị, không
phải tiến độ hiện tại. Tiến độ review mới nằm ở reviews/summary và báo cáo.
Giữ nguyên manifest/hash đã dùng trong run, không đổi hash để làm đẹp lịch sử.

```bash
python -m src.benchmark_data --split dev
python -m unittest discover -s tests -v
```

Chỉ số đếm/hợp đồng evidence không thay việc đọc nguồn. Khi sửa benchmark,
lưu phiên bản/lý do và hash mới; không sửa hash chỉ để bỏ qua cảnh báo.

## 1.5. Bài tập và tiêu chí hoàn thành

1. Giải thích `runtime_input`: chỉ question → query và filter hợp lệ được gửi
   retrieval; expected_answer/gold/answerable chỉ dùng trong evaluator.
2. q02 có một mảnh thì cả hai metric đều sai; hai mảnh ở hai chunk thì metric
   evidence-set có thể đúng, strict vẫn sai.
3. 8 câu hit / 15 câu có đáp án = 8/15, không chia cho 17.
4. Đối chiếu source PDF với gold và ghi việc đã review đúng phạm vi.

Đạt khi môi trường/kho chạy được, biết nguồn và phiên bản, benchmark đủ số
lượng, hiểu cách chấm và cách tránh rò đáp án. Tiếp: [mục 2](02-RETRIEVAL.md).

## 1.6. Tái tạo trên máy khác từ repo Day 6

Đáp ứng mục model/store/kết nối/dữ liệu hoặc cách tái tạo trong SUBMISSION.md.
Repo Day 6 của học viên đã public và có code hoàn thiện, snapshot, manifest và
hướng dẫn ingest: [Day 6](https://github.com/quachphucbk/K5-L3A-DAY06-QuachNgocPhuc-2A202603665-DataIngestion).
Snapshot `starter/results/ingest.json` trên GitHub đã được đối chiếu trùng bản
local dùng cho Day 7. Không cần chép backend hoặc vector sang repo Day 7.

### Lấy repo và môi trường

Đặt hai repo cạnh nhau; ví dụ chạy tại thư mục cha chứa project:

```bash
git clone https://github.com/quachphucbk/K5-L3A-DAY06-QuachNgocPhuc-2A202603665-DataIngestion.git
git clone https://github.com/quachphucbk/K5-L3A-DAY07-QuachNgocPhuc-2A202603665-RetrievalContext.git
```

Nếu đã clone thì dùng thư mục hiện có. Cài môi trường Day 7 theo mục 1.1.
Python 3.12 là phiên bản đã chạy; cần Docker và mạng tải dependency/E5 lần đầu.

### Database Day 6

Nếu database B đã có 140 chunk đúng snapshot thì chỉ khởi động lại, không ingest.
Trên máy chưa có database: làm theo [README Day 6](https://github.com/quachphucbk/K5-L3A-DAY06-QuachNgocPhuc-2A202603665-DataIngestion#lấy-dữ-liệu-và-chạy-pipeline).
Từ thư mục cha chứa hai repo:

```bash
cd K5-L3A-DAY06-QuachNgocPhuc-2A202603665-DataIngestion/starter
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-lock.txt
cp -n .env.example .env
docker compose -p day6_student_starter up -d --wait
python scripts/check_setup.py
```

`.env` Day 6 chứa DATABASE_URL của PostgreSQL/pgvector local port 55433;
đối chiếu với `docker-compose.yml`. Không công khai `.env`. Có thể override
DATABASE_URL bằng biến môi trường khi chạy Day 7. Mật khẩu mẫu local không dùng
cho dịch vụ công khai. Bảng cần có: `day06_chunks`, strategy B, embedding 384 chiều.

Tải PDF gốc 236 trang từ [World Bank](https://openknowledge.worldbank.org/entities/publication/6fbbb475-58f1-49e0-90b3-f329e8124694).
SHA-256 PDF phải là `45856a9eaf4fc31a89c9a1924e1c4034053c979af9bb66d51b3fed3bc227fd26`.
Nguồn/quyền và 37 trang 43–79 ở [manifest Day 6](https://github.com/quachphucbk/K5-L3A-DAY06-QuachNgocPhuc-2A202603665-DataIngestion/blob/main/data/manifest.json).
Ingest vào database mới dùng output mới ngoài repo để giữ snapshot đã nộp:

```bash
python -m src.run ingest --pdf '/duong/dan/report.pdf' --output /tmp/day6-db-rebuild
```

Thay đường dẫn PDF thật. Output `/tmp/day6-db-rebuild` phải chưa tồn tại.
Ingest Day 6 thay dữ liệu các strategy của database đích: chỉ dùng database mới
hoặc xác định rõ muốn tái tạo; không chạy trên database có dữ liệu cần giữ.
Giữ snapshot đã clone tại `starter/results/ingest.json` làm bản chuẩn Day 7;
output ingest mới có thời điểm khác, không thay hash benchmark để bỏ kiểm tra.
E5 phải đúng revision `614241f622f53c4eeff9890bdc4f31cfecc418b3`, L2 normalized,
prefix passage/query. Nếu PDF/chunk khác bản chuẩn, adapter từ chối corpus khác.

### Kết nối từ Day 7

Quay lại root Day 7 và dùng môi trường Day 7:

```bash
cd ../../K5-L3A-DAY07-QuachNgocPhuc-2A202603665-RetrievalContext
source .venv/bin/activate
python -m src.day6_adapter --question 'Vì sao hộ nghèo nhạy cảm hơn với giá năng lượng?' --top-k 3
python -m unittest discover -s tests -v
```

Adapter mặc định tìm repo Day 6 cạnh Day 7. Nếu đặt nơi khác, thêm
`--day6-root '/duong/dan/repo-Day6'` vào CLI adapter/agent/benchmark.
Không dùng `data/day6_chunks.json` để thay database: file đó là corpus chuẩn
cho benchmark, vector nằm trong pgvector.

Chạy agent bằng key của người chấm: tạo `.env` từ `.env.example`, điền
ANTHROPIC_API_KEY, để AGENT_ENV_FILE rỗng nếu không kế thừa env khác.

```bash
python -m src.rag_agent --question 'Vì sao hộ nghèo nhạy cảm hơn với giá năng lượng?' --output /tmp/day7-agent-new.json
```

Lệnh agent gọi API có phí, không ghi đè output. Để xem kết quả nộp không cần
key hoặc gọi API lại. Tái chạy dev dùng `python -m src.benchmark_agent --output
/tmp/day7-dev-new` (mặc định dry-run; thêm --execute mới gọi API).
Test đã chốt/chạy/chấm trong repo; không chạy lại để chọn kết quả hoặc chỉnh
hệ thống theo test. Nếu tái chạy để tái lập, lưu output gốc riêng và ghi rõ rerun.

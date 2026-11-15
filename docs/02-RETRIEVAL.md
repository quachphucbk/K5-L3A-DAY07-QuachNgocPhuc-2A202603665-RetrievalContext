# 2. Thử các phương pháp retrieval

Đối chiếu: [GUIDE.md §2](../GUIDE.md#2-thử-các-phương-pháp-retrieval).
Không cần triển khai mọi gợi ý rerank/multi-hop; bài này đã chọn ba phương pháp.

## 2.1. Ba phương pháp trên cùng 140 chunk B

| Phương pháp | Code | Ý tưởng |
|---|---|---|
| Dense | src/day6_adapter.py | E5 query vector, exact cosine trên pgvector Day 6 |
| BM25 | src/retrievers.py | Khớp từ, k1=1.2, b=0.75, thống kê toàn corpus B |
| Hybrid RRF | src/retrievers.py | Hợp nhất rank, constant=60, missing branch đóng góp 0 |

Chỉ đổi top-k chưa thành phương pháp mới. B/C của Day 6 cũng không tự thay
thế yêu cầu ba phương pháp. BM25/RRF tái sử dụng công thức bài hybrid Day 6,
nhưng đã tách để nhận query bất kỳ, không mang gold vào retriever.

## 2.2. Chạy và hiểu BM25/RRF

```bash
source .venv/bin/activate
python -m src.retrievers --method bm25 --question 'Theo Box 1.1, chuẩn nghèo quốc tế được xác định như thế nào?' --top-k 3
python -m src.retrievers --method all --question 'Vì sao hộ nghèo nhạy cảm hơn trước biến động giá thực phẩm và năng lượng?' --top-k 3
```

Mỗi lệnh độc lập, không thêm dấu nối dòng vào cuối lệnh thứ nhất.
Tokenizer giữ `BOX 1.1 → ['box','1.1']`. Counter đếm từ trong chunk. Từ hiếm
có IDF lớn hơn, độ dài/tần suất được điều chỉnh bằng BM25. Chunk điểm 0 bị loại,
không gán hạng giả chỉ để đủ ba kết quả. Query tiếng Việt trên corpus tiếng Anh
có thể không khớp từ. Thử tiếng Anh là thay đổi query phải báo riêng.

```text
RRF(chunk) = 1/(60 + rank_BM25) + 1/(60 + rank_dense)
```

Rank bắt đầu từ 1. Lấy tối đa toàn bộ 140 candidate trước khi fusion rồi mới
cắt top-k. Không cộng trực tiếp score cosine và BM25. Đọc `component_ranks`
để tính tay; rank 5 và 7 cho score 1/65 + 1/67 ≈ 0.03031.

## 2.3. Benchmark query gốc trên dev

Kết quả đã chạy: `results/dev-retrieval-01/REPORT.md`, 17 câu × 3 phương pháp,
51 trace, không lỗi. Muốn chạy lại dùng output mới:

```bash
python -m src.benchmark_retrieval --output results/my-dev-retrieval-01
```

| Method | Hit@1 strict | Evidence Hit@3 strict | Packed evidence, budget 800 |
|---|---|---|---|
| Dense | 5/15 | 7/15 | 2/15 |
| BM25 | 1/15 | 4/15 | 2/15 |
| Hybrid | 4/15 | 6/15 | 2/15 |

Đây là khớp evidence nguyên văn sau chuẩn hóa, chưa chấm answer LLM. Evidence
set cũng được xuất riêng; evidence tương đương cần nhãn người đọc. Câu thiếu
evidence không vào mẫu số. Lỗi provider/DB báo riêng, không gọi là abstain.

Trace có request chỉ query/filter, top-3 đầy đủ text/source/page/metadata/score,
ranking, context, gold evaluator và cờ hit. Gold trong trace không được đưa
nguyên file vào model. Query viết lại của agent ở mục 3–4 phải báo riêng với
query gốc này. Filter `--section` chỉ dùng phạm vi người hỏi đã cung cấp.

## 2.4. Đọc lỗi và bài tập

- q04/dense: đúng evidence top-1 trang 46, nhưng block 1.012 ký tự vượt 800
  nên bị bỏ. Đây là lỗi packing, không phải thiếu kết quả retrieval.
- q02/dense: top-3 chưa có đủ hai mảnh định nghĩa, tăng budget riêng không kéo
  được một mảnh chưa được tìm thấy.
- q06/dense: có evidence tương đương ở hạng 2 nhưng không khớp literal gold;
  giữ điểm exact, ghi xét tương đương riêng, không sửa gold để tăng điểm.

Bài tập: so top-3 của ba cách; đọc đủ ý thay vì chỉ đúng số hiệu/trang; tính tay
RRF; giải thích vì sao BM25 rỗng thì hybrid giữ thứ tự dense. Hoàn thành khi ba
retriever chạy thật và bạn đọc được bảng/ranking. Tiếp: [mục 3](03-AGENT-CONTEXT.md).

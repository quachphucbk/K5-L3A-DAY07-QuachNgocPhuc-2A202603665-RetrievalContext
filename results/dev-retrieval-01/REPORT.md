# Kết quả retrieval dev — chưa chấm agent

Metric tự động khớp evidence sau chuẩn hóa, không thay nhãn ngữ nghĩa thủ công.

| Method | Hit@1 | Evidence Hit@3 | EvidenceSetHit@3 | Packed strict | Packed set | Errors |
|---|---|---|---|---|---|---|
| dense | 5/15 | 7/15 | 7/15 | 2/15 | 2/15 | 0 |
| bm25 | 1/15 | 4/15 | 4/15 | 2/15 | 2/15 | 0 |
| hybrid | 4/15 | 6/15 | 6/15 | 2/15 | 2/15 | 0 |

Context budget: 800 ký tự, gồm nguồn. Chỉ pack top-3; chưa gửi model.

## Giới hạn

- Literal normalized evidence proxy; semantic equivalents need separate human review.
- Packed context is a candidate context, not yet sent to a model; no grounded answer/citation/abstention metrics.
- Quality denominator excludes retrieval errors; report errors, total and scored counts together.
- Shared branch rankings: hybrid search time equals BM25 + dense + fusion; initialization reported separately.
- Local inference API USD=0, excludes hardware/electricity; one measurement, fixed branch order, cache may matter.

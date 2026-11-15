# Báo cáo Day 7

**Học viên:** Quách Ngọc Phúc — **MSSV:** 2A202603665 — **Lớp:** K5-L3A.

## Dữ liệu và benchmark

- Nguồn, quyền sử dụng, số trang và số chunk: World Bank (2026), *Poverty, Prosperity, and Planet Report 2026: Jobs at the Center of Poverty Eradication*, [nguồn tài liệu](https://openknowledge.worldbank.org/entities/publication/6fbbb475-58f1-49e0-90b3-f329e8124694). Theo [manifest Day 6](https://github.com/quachphucbk/K5-L3A-DAY06-QuachNgocPhuc-2A202603665-DataIngestion/blob/main/data/manifest.json), giấy phép CC BY 3.0 IGO ghi tại trang PDF 6, cần attribution; thành phần bên thứ ba có thể có quyền riêng. Dùng 37 trang PDF 43–79 (trang in 11–47), 40 segment trang/section, 140 chunk B paragraph tối đa 900 ký tự; giữ nguyên ID/text/source/page/metadata Day 6. PDF toàn bộ có 236 trang nhưng không index toàn bộ. Text/chunk là biểu diễn chuyển đổi, không giữ bố cục PDF.
- Vector store, embedding model, phiên bản và số chiều: PostgreSQL 16.16, pgvector 0.8.7, bảng `day06_chunks`, strategy B, exact cosine, local port 55433. E5 `intfloat/multilingual-e5-small`, revision `614241f622f53c4eeff9890bdc4f31cfecc418b3`, 384 chiều, normalize L2, prefix `passage: ` / `query: `, CPU; đầu vào quá 512 tokens bị từ chối, không cắt ngầm. Day 7 kết nối trực tiếp repo/database Day 6, không nộp lại backend/vector.
- Agent model, cách chạy và phân chia dev/test: Anthropic `claude-haiku-5-5`, native tool calling; không dùng Opus trong các run báo cáo. Chạy từ root Day 7 bằng `.venv`, xem [hướng dẫn môi trường/kết nối](../../docs/01-CHUAN-BI.md). Dev gồm 15 câu có đáp án + 2 thiếu evidence; test mới 5 + 2. q01–q15 dùng từ Day 6, thêm dneg01/dneg02; không dùng q16–q20 đã xem làm test mới. Chốt budget3200 bằng dev trước khi chạy test. Key nằm trong môi trường/.env bị ignore.
- Cách xác định câu có/thiếu evidence và tiêu chí chấm: câu có đáp án có ID/question/expected_answer/gold/source_id/page/evidence. q02/q11 dùng evidence_sets (AND các mảnh, OR các phương án) vì gold bị chia hai chunk. Câu thiếu evidence có lý do và kiểm tra toàn corpus đã được học viên xác nhận, không kết luận thiếu từ top-k. Strict Hit@1/Hit@3 yêu cầu đúng nguồn/trang và trọn evidence sau chuẩn hóa; evidence-set báo riêng. Context 0/1/2 là không có / thiếu điều kiện hoặc nguồn / đủ evidence và nguồn. Answer 0/1/2 là sai hoặc thiếu evidence / đúng một phần / đúng và đủ; từ chối câu có đáp án chấm 0. Lỗi báo riêng, loại khỏi mẫu số chất lượng. Citation phải trong context và hỗ trợ phát biểu; kiểm tra ID chưa đủ. Abstention đúng yêu cầu từ chối và không thêm thông tin thiếu căn cứ.

Snapshot SHA-256: `9c68b613738b6d04882c2d069c760b974e78473b5a1a3dda32e8f74da66586d7`. Phiên bản/hashes/lịch sử/tiêu chí chọn nằm trong [benchmark/manifest.json](../../benchmark/manifest.json). Chỉ question/filter được đưa vào model/retrieval; không đưa gold, expected_answer hoặc nhãn answerable vào runtime.

## Retrieval và thử nghiệm

| Cấu hình | Phương pháp, top-k, filter, rerank, context budget | Giả thuyết / thay đổi | Split | Hit@1 | Evidence Hit@3 | Context Evidence Rate | Thời gian / chi phí |
|---|---|---|---|---|---|---|---|
| Baseline | E5/pgvector exact cosine; top-3; filter section khi câu hỏi cung cấp; không rerank; 800 ký tự | Baseline query gốc | dev | 5/15 (33.3%) | 7/15 (46.7%) | 2/15 (13.3%) — proxy context cố định | 24.553 ms/search; API sinh $0, E5 local |
| Phương pháp 2 | BM25 k1=1.2, b=0.75; top-3; filter section khi câu hỏi cung cấp; không rerank; 800 ký tự | Thử bm25 trên cùng 140 chunk B và câu hỏi gốc | dev | 1/15 (6.7%) | 4/15 (26.7%) | 2/15 (13.3%) — proxy context cố định | 0.181 ms/search; API sinh $0, E5 local |
| Phương pháp 3 | Hybrid dense+BM25, RRF k=60; top-3; filter section khi câu hỏi cung cấp; không rerank; 800 ký tự | Thử hybrid trên cùng 140 chunk B và câu hỏi gốc | dev | 4/15 (26.7%) | 6/15 (40.0%) | 2/15 (13.3%) — proxy context cố định | 24.796 ms/search; API sinh $0, E5 local |
| Cải thiện 1 | Dense top-3; filter như baseline; không rerank; 3200 ký tự; latest | Chỉ tăng budget 800 → 3200 so baseline để giữ đủ whole chunk + nguồn | dev | 5/15 (33.3%) — query gốc | 7/15 (46.7%) — query gốc | 13/15 (86.7%) — context cuối agent, đã review | 147.789 giây / ~$0.0222673 |
| Cải thiện 2 | Dense top-3; filter như baseline; không rerank; 3200 ký tự; neighbors | Giữ 3200, đổi latest → neighbors so budget3200 để nối mảnh cùng trang/section/segment | dev | 5/15 (33.3%) — query gốc | 7/15 (46.7%) — query gốc | 9/14 (64.3%) — context cuối agent, đã review | 172.944 giây / ~$0.0249327; usage chưa đủ ở lượt lỗi |
| Cấu hình đã chọn | Dense top-3; filter theo câu hỏi; không rerank; 3200 ký tự/latest | Cấu hình chốt trên dev trước test | test | 2/5 (40.0%) — query gốc | 4/5 (80.0%) — query gốc | 5/5 (100.0%) — context cuối agent, đã review | 38.899 giây / ~$0.0072807 |
| Baseline | Dense top-3; filter theo câu hỏi; không rerank; 800 ký tự/latest | Đối chiếu cùng 7 câu test sau khi chốt | test | 2/5 (40.0%) — query gốc | 4/5 (80.0%) — query gốc | 2/5 (40.0%) — context cuối agent, đã review | 48.972 giây / ~$0.0077610 |

Một cấu hình có thể đồng thời là phương pháp mới và cải thiện; giải thích rõ. Báo `n/N` và tỷ lệ, ghi đơn vị thời gian/chi phí, so sánh test sau khi chốt. Nêu hai lỗi dev, nguyên nhân, cách thử và lý do chọn cấu hình:

- Ba phương pháp khác nhau là dense, BM25 và hybrid RRF; thay budget/policy là hai cấu hình cải thiện, không tính thành phương pháp retrieval thứ tư. BM25 chuẩn hóa Unicode NFKC, giữ token số hiệu như 1.1, chỉ trả score dương; query Việt trên corpus Anh có thể không khớp. Hybrid hợp nhất rank (không cộng score thô), rank từ 1, tối đa 140 candidates mỗi nhánh trước cutoff; tie theo ID.
- Ba dòng retrieval đầu là query gốc, chỉ pack context cố định và chưa gửi model: Context Evidence Rate ở đó là proxy. Hai dòng cải thiện dùng cùng dense/query gốc nên Hit@1/Hit@3 không đổi; context cuối và thời gian/phí là run agent thật có thể viết lại query/nhiều search. Không đánh đồng hai phép đo. Nguồn: [retrieval dev](../../results/dev-retrieval-01/REPORT.md), [context replay](../../results/my-context-replay-01/REPORT.md), các trace agent.
- Replay cô lập packing trên cùng top-3 dev (strict): dense 800/latest 2/15 (13.3%), 3200/latest 7/15 (46.7%), 3200/neighbors 6/15 (40.0%); BM25 lần lượt 2/15 (13.3%), 4/15 (26.7%), 2/15 (13.3%); hybrid 2/15 (13.3%), 6/15 (40.0%), 5/15 (33.3%). Không gọi LLM trong replay; neighbors có thể chiếm chỗ của evidence khác.
- Lỗi dev 1 — q01/baseline800: retrieval có đoạn PPP đổi 2017→2021 nhưng whole chunk + header không vừa 800 ký tự; context cuối thiếu evidence, answer/context 0/0. Giả thuyết tăng budget giữ được đoạn: budget3200 đạt 2/2, neighbors3200 cũng 2/2. Query model có thể khác giữa các run, nên dùng thêm replay cố định để cô lập packing.
- Lỗi dev 2 — q02: định nghĩa cần trung vị và nhóm thu nhập thấp bị chia hai chunk; context chỉ có bảng mức tiền nên cả baseline/budget/neighbors vẫn 0/0 và từ chối. Thử neighbors chưa sửa được; không suy ra cách định nghĩa từ mức $3.00 hoặc tự nâng điểm vì cùng trang.
- Lỗi bổ sung — q10: baseline nhầm nhóm $3.00–$8.30 còn dễ tổn thương là trung lưu; budget3200 lấy được định nghĩa $8.30–$28.00, từ 0/0 lên 2/2; neighbors vẫn 0/0. q15/neighbors3200 lỗi tool call chưa hoàn chỉnh, giữ not_applicable, không giả là abstain hoặc khẳng định chắc hết max_tokens.
- Lý do chọn: tiêu chí công bố trước ưu tiên grounded answer/citation, rồi context, hòa mới xét latency/cost. Chốt **budget3200** tại `2026-11-14T14:07:21.910265+00:00` trong [selection-frozen.json](../../configs/selection-frozen.json): dev answer 1.60/2, citation 23/24 (95.8%), context 13/15 (86.7%), không lỗi; latency và estimated cost cũng thấp hơn hai cấu hình còn lại trong run này. Test chỉ chạy sau chốt, không dùng để chỉnh/chọn lại.

## Agent và đánh giá

- Tool, số lượt gọi, điều kiện dừng, cách chọn context và xử lý lỗi: dùng trực tiếp `starter.agentic.run_agent`; `ClaudeAgentController` chuyển native tool call Haiku sang protocol. `search_documents(query)` gọi retriever thật, `finish(status,answer,citations)` kết thúc khi đủ evidence hoặc từ chối. Top-k=3, tối đa 4 search và 7 model calls, do bài làm chọn để có tìm bổ sung và sửa citation, chưa chứng minh tối ưu. Context latest ưu tiên mới, dedup, giữ whole chunk có header nguồn/trang; neighbors thêm trước/sau cùng document/page/section/segment theo offset. Budget 800/3200 là ký tự Python gồm header, không phải toàn prompt. Model chỉ thấy exchange mới nhất với cumulative context, không cộng lén context cũ. Candidates trực tiếp tối đa 3/lượt; neighbors tối đa 9 trước dedup; số thực tế nằm trong context_candidates. Finish kiểm tra citation ID/inline khớp context, cho sửa trong giới hạn; API/DB error và limit báo riêng, không dùng mock thay kết quả. Prompt coi nguồn/tool result là dữ liệu, không tuân theo chỉ dẫn trong nguồn; không lưu reasoning nội bộ.

| Cấu hình / split | Tool use | Số lượt gọi | Grounded answer 0/1/2 và trung bình | Citation hợp lệ | Câu có citation | Abstention đúng | Từ chối nhầm |
|---|---|---|---|---|---|---|---|
| baseline800 / dev | 17/17 (100.0%) | 81 model calls | 0: 10; 1: 2; 2: 3; TB 0.5333/2, N=15 | 6/7 (85.7%) | 7/7 (100.0%) | 2/2 (100.0%) | 8/15 (53.3%) |
| budget3200 / dev | 17/17 (100.0%) | 58 model calls | 0: 2; 1: 2; 2: 11; TB 1.6000/2, N=15 | 23/24 (95.8%) | 13/13 (100.0%) | 2/2 (100.0%) | 2/15 (13.3%) |
| neighbors3200 / dev | 16/16 (100.0%) | 65 model calls | 0: 5; 1: 6; 2: 3; TB 0.8571/2, N=14 | 15/20 (75.0%) | 11/11 (100.0%) | 1/2 (50.0%) | 3/14 (21.4%) |
| baseline800 / test | 7/7 (100.0%) | 31 model calls | 0: 3; 1: 0; 2: 2; TB 0.8000/2, N=5 | 2/2 (100.0%) | 2/2 (100.0%) | 2/2 (100.0%) | 3/5 (60.0%) |
| budget3200 / test | 7/7 (100.0%) | 22 model calls | 0: 0; 1: 0; 2: 5; TB 2.0000/2, N=5 | 6/6 (100.0%) | 5/5 (100.0%) | 1/2 (50.0%) | 0/5 (0.0%) |

Dev có 51 lượt: 50 verified và 1 lỗi q15/neighbors3200; cấu hình đó chỉ có 14 câu có đáp án chạy thành công, lỗi báo riêng và không chấm answer/context. Test có 14/14 verified, không error/limit. Citation đếm ID duy nhất trong trường citations, không đếm lần lặp inline; true yêu cầu mọi phát biểu gắn với ID đều được nguồn hỗ trợ. Câu không có citation là 0/0, không áp dụng. Điểm answer/context do đối chiếu nội dung, không lấy status=answered hoặc ID hợp lệ làm điểm đúng.

Abstention đúng trong bảng dùng tiêu chí nghiêm ngặt không thêm thông tin thiếu căn cứ. Về hành vi, cả ba cấu hình dev và cả hai cấu hình test đều từ chối 2/2 (100.0%) câu thiếu evidence. neighbors/dev chỉ đạt tiêu chí nghiêm ngặt 1/2 vì dneg01 diễn đạt số liệu Figure 1.6 thiếu mẫu số, dễ nhầm tỷ trọng nghèo toàn cầu thành tỷ lệ nghèo quốc gia; budget/test chỉ đạt 1/2 vì tneg02 gán Annex 1a vào trang PDF 43–79 mà không có bằng chứng vị trí. Không diễn giải 1/2 thành chỉ có một lần status=abstain.

| Query ID | Loại câu | Tool call và kết quả | Câu trả lời và citation | Nhãn, lý do |
|---|---|---|---|---|
| [q04 / budget3200](../../results/my-haiku-dev-01/traces/budget3200/q04.json) | Có đáp án | 1 search, 2 model calls; context trang PDF 46, 63; xem events trong trace | Không có lợi ích ròng khi giá thực phẩm tăng do chi phí đầu vào; có thể thiệt hơn nếu nhu cầu giảm. Citation: `01b19e099f5739adced97e1c1bb073e31f06a7dab5c1607a0ebb484a10bd76d4`. | answer=2, context=2. Trả lời đúng và đủ kết luận cùng điều kiện chi phí đầu vào và nhu cầu giảm. Context có evidence cùng nguồn/trang; citation hỗ trợ cả phần chính và ví dụ. |
| [dneg02 / baseline800](../../results/my-haiku-dev-01/traces/baseline800/dneg02.json) | Thiếu evidence | 4 search, 5 model calls; context trang PDF 62; xem events trong trace | Chưa đủ bằng chứng để liệt kê mã hộ và thu nhập; không tạo dữ liệu hộ. Citation: Không có citation. | abstention_correct=true. Benchmark dneg02 thiếu evidence: báo cáo tổng hợp không có bảng mã định danh và thu nhập từng hộ, kiểm tra toàn corpus đã được học viên xác nhận. Agent tìm 4 lượt; context chỉ có thống kê theo nhóm thu nhập quốc gia. Agent từ chối, không tạo mã hộ hay số thu nhập. |
| [q15 / neighbors3200](../../results/my-haiku-dev-01/traces/neighbors3200/q15.json) | Lỗi thực thi | 4 search, 5 model calls; context trang PDF 48, 59; xem events trong trace | Không có câu trả lời cuối; tool call chưa hoàn chỉnh. Citation: Không có citation. | not_applicable; lỗi báo riêng. Lỗi thực thi: status=error; thông báo Model chưa trả tool call hoàn chỉnh (có thể hết max_tokens). Không có câu trả lời cuối; chưa đủ bằng chứng xác nhận nguyên nhân hết max_tokens. Giữ not_applicable, không chấm answer/context, không coi là abstain; báo riêng 1 lỗi thực thi. |
| [t03 / baseline800](../../results/haiku-test-frozen-01/traces/baseline800/t03.json) | Có đáp án | 4 search, 5 model calls; context trang PDF 66; xem events trong trace | Từ chối xác định các phân vị bị loại; context chỉ có cấu trúc hộ gia đình. Citation: Không có citation. | answer=0, context=0. Gold trang PDF 58 nêu Figure 1.5 loại bỏ ba phân vị thấp nhất và ba phân vị cao nhất. Context cuối chỉ có trang PDF 66 về cấu trúc hộ gia đình, không có evidence phân vị bị loại. Agent từ chối câu có đáp án. |
| [t03 / budget3200](../../results/haiku-test-frozen-01/traces/budget3200/t03.json) | Có đáp án | 2 search, 3 model calls; context trang PDF 58, 59; xem events trong trace | Loại bỏ ba phân vị thấp nhất và ba phân vị cao nhất. Citation: `f714d51bebf5e4b5a3044ee78031b6934ce586833dcf39346d7587502f1ee913`. | answer=2, context=2. Trả lời đúng và đủ ba phân vị ở mỗi đầu phân phối. Context đủ evidence cùng nguồn/trang; các giai đoạn bổ sung có trong cùng chú thích nguồn. |
| [tneg02 / budget3200](../../results/haiku-test-frozen-01/traces/budget3200/tneg02.json) | Thiếu evidence | 4 search, 5 model calls; context trang PDF 56, 57; xem events trong trace | Từ chối mã nguồn/phiên bản thư viện, nhưng gán phạm vi trang Annex 1a thiếu căn cứ. Citation: Không có citation. | abstention_correct=false. Agent tìm 4 lượt và từ chối cung cấp mã Python/phiên bản thư viện, không bịa code. Tuy nhiên gợi ý gán Annex 1a vào trang PDF 43–79 của chương 1 chưa có căn cứ: 43–79 là phạm vi toàn snapshot, không phải phạm vi phụ lục đã xác nhận từ context. Theo tiêu chí nghiêm ngặt từ chối không kèm thông tin thiếu căn cứ, abstention_correct=false; hành vi từ chối vẫn được ghi riêng trong trace. |

- Đường dẫn trace, nhãn, lệnh chạy, thời gian và chi phí:

  Dev: [run.json](../../results/my-haiku-dev-01/run.json), `results/my-haiku-dev-01/traces/<config>/<id>.json`, `reviews/<config>.json`, `review-summary-<config>-01.json`, `technical_summary.json`. Test: [run.json](../../results/haiku-test-frozen-01/run.json), [báo cáo đã review](../../results/haiku-test-frozen-01/REVIEWED_REPORT.md), trace/review/summary cùng cấu trúc. Mỗi trace có query/params/results/context cuối/answer/citation/error/usage/latency; toàn bộ nhãn từng câu và citation có lý do trong reviews, không chỉ các ví dụ trong bảng. Bản kỹ thuật trước review là lịch sử; nhãn và summary reviewed là kết quả chấm hiện hành.

  Cài và kết nối theo [docs/01-CHUAN-BI.md](../../docs/01-CHUAN-BI.md#16-tái-tạo-trên-máy-khác-từ-repo-day-6), `requirements-lock.txt`; dùng code/snapshot/database từ repo Day 6 public. Snapshot trên GitHub đã đối chiếu trùng local. Không cần đóng gói lại backend/vector. Ví dụ xem kết quả không gọi API:

  ```bash
  source .venv/bin/activate
  python -m src.review_agent show --run results/my-haiku-dev-01 --config budget3200 --id q04
  python -m scripts.review_frozen_test show --config budget3200 --id t03
  python -m unittest discover -s tests -v
  ```

  Chạy mới trên dev (output mới, mặc định dry-run; thêm --execute mới gọi API 51 lượt): `python -m src.benchmark_agent --output /tmp/day7-dev-new`. Chạy agent một câu: `python -m src.rag_agent --question "Vì sao hộ nghèo nhạy cảm hơn với giá năng lượng?" --output /tmp/day7-agent-new.json`. Key người chấm tự cung cấp trong .env/môi trường. Không chạy lại test để chọn kết quả đẹp hơn; nếu chỉnh hệ thống bằng test cần test độc lập mới.

  Thời gian và chi phí theo cấu hình đã ghi trong bảng retrieval/thử nghiệm. Tổng dev known estimate **$0.0700055**, chưa đủ ở request lỗi neighbors; tổng test **$0.0150417**. Estimate từ usage API và rate từng request lưu trong `src/costs.py`/trace, [nguồn giá](https://platform.claude.com/docs/en/models/haiku-5-5/overview), kiểm tra ngày 14/11/2026. Không phải hóa đơn; chưa tính thuế, chiết khấu, điện, phần cứng, request thiếu usage. Không gọi null là $0. Latency là tổng loop, chưa gồm shared embedding initialization. Phân bố lượt tìm và token đã lưu:

  - baseline800/dev: 1 search: 2 câu, 2 search: 1 câu, 3 search: 1 câu, 4 search: 13 câu; input 138920 tokens, output 17827 tokens, cache read/write 0/0 tokens. Phân bố search chỉ tính câu thành công; số model calls và lỗi vẫn báo trên mọi lượt.
  - budget3200/dev: 1 search: 6 câu, 2 search: 5 câu, 3 search: 2 câu, 4 search: 4 câu; input 137528 tokens, output 17029 tokens, cache read/write 0/0 tokens. Phân bố search chỉ tính câu thành công; số model calls và lỗi vẫn báo trên mọi lượt.
  - neighbors3200/dev: 1 search: 5 câu, 2 search: 3 câu, 3 search: 2 câu, 4 search: 6 câu; input 159852 tokens, output 17895 tokens, cache read/write 0/0 tokens. Phân bố search chỉ tính câu thành công; số model calls và lỗi vẫn báo trên mọi lượt.
  - baseline800/test: 1 search: 1 câu, 2 search: 1 câu, 4 search: 5 câu; input 52515 tokens, output 5019 tokens, cache read/write 0/0 tokens. Phân bố search chỉ tính câu thành công; số model calls và lỗi vẫn báo trên mọi lượt.
  - budget3200/test: 1 search: 4 câu, 2 search: 1 câu, 4 search: 2 câu; input 51132 tokens, output 4335 tokens, cache read/write 0/0 tokens. Phân bố search chỉ tính câu thành công; số model calls và lỗi vẫn báo trên mọi lượt.

- Kết quả trước/sau, ví dụ lỗi, đánh đổi và giới hạn:

  Tăng budget từ baseline lên budget3200 nâng dev answer 0.5333→1.6000/2, context reviewed 3/15 (20.0%)→13/15 (86.7%); neighbors giảm xuống 0.8571/2 và 9/14 (64.3%), có 1 lỗi. Test sau chốt: baseline 0.80/2, budget3200 2.00/2 trên 5 câu có đáp án. Không suy rộng từ bộ test nhỏ và một sample mỗi query/config; model/query có biến thiên, thứ tự chạy cố định, thời gian không phải benchmark hiệu năng tổng quát.

  Kết quả query gốc nằm trong bảng retrieval/thử nghiệm. Bổ sung query đầu của agent (đều khác query gốc; chỉ câu có đáp án thành công), cùng strict source/page/cutoff:
  - baseline800/dev: query đầu viết lại 15/15 (100.0%); Hit@1 4/15 (26.7%), Evidence Hit@3 5/15 (33.3%); context cuối strict 3/15 (20.0%), evidence-set 3/15 (20.0%). Context reviewed mức 0/1/2: 10/2/3 câu.
  - budget3200/dev: query đầu viết lại 15/15 (100.0%); Hit@1 5/15 (33.3%), Evidence Hit@3 6/15 (40.0%); context cuối strict 11/15 (73.3%), evidence-set 11/15 (73.3%). Context reviewed mức 0/1/2: 1/1/13 câu.
  - neighbors3200/dev: query đầu viết lại 14/14 (100.0%); Hit@1 4/14 (28.6%), Evidence Hit@3 5/14 (35.7%); context cuối strict 7/14 (50.0%), evidence-set 8/14 (57.1%). Context reviewed mức 0/1/2: 5/0/9 câu.
  - baseline800/test: query đầu viết lại 5/5 (100.0%); Hit@1 2/5 (40.0%), Evidence Hit@3 3/5 (60.0%); context cuối strict 2/5 (40.0%), evidence-set 2/5 (40.0%). Context reviewed mức 0/1/2: 3/0/2 câu.
  - budget3200/test: query đầu viết lại 5/5 (100.0%); Hit@1 2/5 (40.0%), Evidence Hit@3 4/5 (80.0%); context cuối strict 5/5 (100.0%), evidence-set 5/5 (100.0%). Context reviewed mức 0/1/2: 0/0/5 câu.

  Query/trace mọi lượt và context/answer cuối đo thêm kết quả pipeline nhiều lượt; không thay ranking query gốc bằng query viết lại tốt hơn. Ranking query gốc test được lưu tại [original-query-ranking.json](../../results/haiku-test-frozen-01/original-query-ranking.json), đo sau freeze trên DB kiểm chứng với vector gốc; giữ trace lịch sử, không yêu cầu nộp DB kiểm chứng đó.

  Corpus chỉ một chương tiếng Anh, text extraction không OCR/vision; biểu đồ có thể mất quan hệ vị trí và caption/header có thể gây gán nhầm Box/section. Context strict và reviewed khác nhau khi evidence tương đương không khớp nguyên văn. Chưa sweep top-k/search limit để kết luận tối ưu. Môi trường đã chạy Python 3.12; chưa thử clean-install lock trên mọi OS. 47 unit tests pass, mock chỉ kiểm tra logic, không thay benchmark model thật.

  Codex hỗ trợ code, benchmark mới và đề xuất nhãn bằng dẫn chứng từ file; Quách Ngọc Phúc xác nhận từng case trong chat, reviewer/date/reason ghi trong phiếu. Không tuyên bố học viên tự đọc lại toàn bộ log hoặc tự viết toàn bộ code. Nguồn/gold/manifest có phạm vi kiểm tra riêng. Các context trích xuất từ báo cáo công khai được gửi Anthropic; không gửi key, benchmark gold hoặc dữ liệu định danh từng hộ. Giữ nguyên cả kết quả giảm và lỗi; không chỉnh code/cấu hình bằng test.

## Thử thách nâng cao (nếu thực hiện)

- Tài liệu, nguồn, quyền sử dụng, số trang và phiên bản: Không thực hiện phần nâng cao; chỉ index 37 trang cho phần cơ bản, không tuyên bố đạt yêu cầu tài liệu >=100 trang.
- Cách xử lý text, bảng, ảnh, biểu đồ; phạm vi index và phần chưa xử lý: Không áp dụng cho phần nâng cao; giới hạn text extraction của phần cơ bản đã ghi ở trên.
- Cách chia benchmark, schema evidence, model và cấu hình đã chốt trên dev: Không có benchmark nâng cao; không dùng kết quả phần cơ bản để nhận bonus.

| Nhóm test | Đạt / tổng | Tỷ lệ | Lỗi / nhận xét |
|---|---|---|---|
| Bảng | Không áp dụng | Không áp dụng | Không thực hiện benchmark nâng cao |
| Ảnh, sơ đồ | Không áp dụng | Không áp dụng | Không thực hiện benchmark nâng cao |
| Biểu đồ | Không áp dụng | Không áp dụng | Không thực hiện benchmark nâng cao |
| Multi-hop | Không áp dụng | Không áp dụng | Không thực hiện benchmark nâng cao |
| Text | Không áp dụng | Không áp dụng | Không thực hiện benchmark nâng cao |
| Thiếu bằng chứng | Không áp dụng | Không áp dụng | Không thực hiện benchmark nâng cao |
| **Toàn bộ** | Không áp dụng | Không áp dụng | Không thực hiện benchmark nâng cao |

- Trace, nhãn và evidence từng câu; thời gian, chi phí, lỗi hệ thống: Không áp dụng cho phần nâng cao; phần cơ bản nằm trong các đường dẫn đã ghi.
- Giới hạn, cách tái lập và đường dẫn benchmark: Không thực hiện phần nâng cao, không tuyên bố đạt ngưỡng 90% hoặc nhận 15 điểm bonus.

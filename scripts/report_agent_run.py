"""Xuất bảng kỹ thuật từ run agent đã hoàn tất; không tự điền nhãn ngữ nghĩa."""
import argparse
import csv
import json
from pathlib import Path


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run',type=Path,required=True)
    args=parser.parse_args()
    root=args.run
    summary=json.loads((root/'technical_summary.json').read_text())
    record=json.loads((root/'run.json').read_text())
    if (root/'REPORT.md').exists() or (root/'technical_metrics.csv').exists():
        raise FileExistsError('Bảng đã có; giữ nguyên hoặc chọn run mới')
    rows=[]
    for cid,s in summary['configs'].items():
        reviews=json.loads((root/'reviews'/f'{cid}.json').read_text())
        statuses=s['status_counts']
        rows.append({'config_id':cid,'scheduled':s['scheduled'],'answered':statuses.get('answered',0),
                     'abstain':statuses.get('abstain',0),'errors':statuses.get('error',0),'limits':statuses.get('limit',0),
                     'context_exact':f"{s['context_evidence_exact']['n']}/{s['context_evidence_exact']['N']}",
                     'context_set':f"{s['context_evidence_set']['n']}/{s['context_evidence_set']['N']}",
                     'model_calls':s['model_calls'],'elapsed_seconds':round(s['elapsed_seconds'],3),
                     'estimated_usd':s['known_estimated_cost_usd'],'cost_estimate_complete':s['cost_estimate_complete'],
                     'pending_reviews':sum(r['review_status']=='pending' for r in reviews)})
    with (root/'technical_metrics.csv').open('x',newline='',encoding='utf-8') as file:
        writer=csv.DictWriter(file,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    lines=['# Agent dev — Haiku, nhãn nội dung còn chờ review','',
           f"Model: `{record['model']}`; split: dev; full dev: {record['full_dev']}.",
           '', '| Config | Answered / Abstain | Context exact / set | Model calls | Giây | Estimated USD | Error / Limit | Pending review |',
           '|---|---|---|---|---|---|---|---|']
    for r in rows:
        lines.append(f"| {r['config_id']} | {r['answered']} / {r['abstain']} | {r['context_exact']} / {r['context_set']} | {r['model_calls']} | {r['elapsed_seconds']} | {r['estimated_usd']:.7f} | {r['errors']} / {r['limits']} | {r['pending_reviews']} |")
    total=sum(r['estimated_usd'] for r in rows)
    lines += ['',f"Tổng ước tính riêng các cấu hình trong run này: **{total:.7f} USD**.",
              'Không gồm demo xác minh riêng, các lần Opus cũ, thuế/discount hoặc phần cứng. Đây không phải hóa đơn đã đối soát.',
              '', '## Cách đọc', '',
              '- Answered/abstain là trạng thái, chưa phải số câu đúng/từ chối đúng.',
              '- Context exact/set là proxy evidence sau chuẩn hóa, chưa thay nhãn context 0/1/2 của người đọc.',
              '- Agent có thể chọn query khác giữa các cấu hình. Xem controlled replay để cô lập tác động packing.',
              '- Thứ tự chạy cố định, một sample mỗi case/config; thời gian gồm model/retrieval trong loop, chưa gồm shared initialization.',
              '- Estimated USD dùng usage/rate từng request; kiểm tra cost_estimate_complete trước khi kết luận tổng đủ.',
              '- Chưa chọn cấu hình cuối và chưa chạy test mới.',
              '', '## Việc học viên làm tiếp', '',
              '1. Mở [hướng dẫn review](../../docs/04-DANH-GIA-CAI-THIEN.md#43-mở-một-câu-để-review).',
              '2. Điền các phiếu trong reviews/ sau khi đối chiếu answer/context/từng citation với nguồn.',
              '3. Chạy src.review_agent summary cho từng cấu hình; chương trình từ chối nhãn pending.',
              '4. So sánh chất lượng đã review cùng thời gian/phí rồi chốt bằng dev trước khi chạy test.', '']
    (root/'REPORT.md').write_text('\n'.join(lines),encoding='utf-8')
    print('Saved technical report and CSV; semantic reviews unchanged.')


if __name__=='__main__':main()

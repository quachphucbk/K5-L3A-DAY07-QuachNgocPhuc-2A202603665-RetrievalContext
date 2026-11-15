"""Tái tạo benchmark bước 3 vào một thư mục output MỚI; không chạy hệ thống."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import unicodedata


def normalize(text):
    return re.sub(r'\s+', ' ', unicodedata.normalize('NFC', text)).strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--day6-root', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    snapshot_path = args.day6_root / 'starter/results/ingest.json'
    bundle = json.loads(snapshot_path.read_text())
    original = json.loads((args.day6_root / 'data/benchmark.json').read_text())
    chunks = [{'id': c['chunk_id'], 'source_id': c['document_id'], 'source': c['source'],
               'page': c['page'], 'text': c['text'], 'metadata': c['metadata']}
              for c in bundle['chunks']['B']]
    source_id = chunks[0]['source_id']
    dev = []
    for q in original:
        if q['split'] != 'dev':
            continue
        gold = {'source_id': q['gold_source_id'], 'page': q['gold_page'], 'evidence': q['evidence_quote']}
        case = {'id': q['id'], 'split': 'dev', 'answerable': True, 'question': q['question'],
                'expected_answer': q['expected_answer'], 'gold': [gold],
                'provenance': 'Day 6 dev; giữ nguyên question/answer/gold'}
        if 'filter' in q:
            case['filter'] = q['filter']
        if q['id'] == 'q02':
            texts = ['The international poverty line is the median national poverty',
                     'line among low-income economies.']
            case['evidence_sets'] = [[{**gold, 'evidence': t} for t in texts]]
        elif q['id'] == 'q11':
            texts = ['There is no fixed income at which security begins. The boundary of the',
                     'middle class shifts with the environment in which households live.']
            case['evidence_sets'] = [[{**gold, 'evidence': t} for t in texts]]
        dev.append(case)
    specs = [
        ('t01', 55, 'Trong chú thích Figure 1.3, các nhóm thu nhập được cố định theo phân loại của năm nào khi so sánh 1990 và 2024?',
         'Theo phân loại năm 2024; thành phần các nền kinh tế trong mỗi nhóm được giữ cố định theo thời gian.',
         'income group classifications reflect each economy’s status in 2024. So, the countries considered in each group is held constant over time.'),
        ('t02', 56, 'Tỷ lệ nghèo cùng cực ở châu Phi cận Sahara thay đổi từ bao nhiêu năm 1990 đến bao nhiêu năm 2026?',
         'Giảm từ 62% năm 1990 xuống 43% năm 2026.',
         'There, extreme poverty rates declined from 62 percent in 1990 to 43 percent in 2026.'),
        ('t03', 58, 'Chú thích Figure 1.5 loại bỏ những phân vị nào ở hai đầu phân phối phúc lợi?',
         'Loại bỏ ba phân vị thấp nhất và ba phân vị cao nhất.',
         'the figure excludes the bottom and top three percentiles of the welfare distribution.'),
        ('t04', 60, 'Chỉ số dissimilarity đo sự tập trung nghèo đói toàn cầu là bao nhiêu năm 2000 và năm 2024?',
         '0,31 năm 2000 và 0,65 năm 2024.',
         'Globally, the index rose from 0.31 in 2000 to 0.33 in 2010 and 0.65 in 2024, more than doubling in a quarter century.'),
        ('t05', 68, 'Năm 2024, tỷ lệ nghèo của người không đi học, người có giáo dục trung học và người có giáo dục bậc cao lần lượt là bao nhiêu?',
         'Lần lượt 22%, 6% và 1%.',
         'Individuals with no formal education in 2024 faced poverty rates of 22 percent, compared with only 6 percent among individuals with secondary education and 1 percent among individuals with tertiary education (refer to figure 1.13, panel b).'),
    ]
    test = []
    for identifier, page, question, answer, quote in specs:
        case = {'id': identifier, 'split': 'test', 'answerable': True, 'question': question,
                'expected_answer': answer, 'gold': [{'source_id': source_id, 'page': page, 'evidence': quote}],
                'provenance': 'Câu mới Day 7; evidence từ text nguồn snapshot Day 6, chưa chạy retrieval/test'}
        if not any(c['page'] == page and normalize(quote) in normalize(c['text']) for c in chunks):
            raise ValueError(f'{identifier}: test gold không nằm trọn trong B')
        test.append(case)
    full_text = normalize(' '.join(p['text'] for p in bundle['pages']))
    negative_specs = [
        ('dneg01', 'dev', 'Theo bộ tài liệu này, tỷ lệ nghèo cùng cực của tỉnh Quảng Ninh năm 2024 chính xác là bao nhiêu phần trăm?',
         'Kho chỉ gồm chương báo cáo tổng hợp; không có số liệu cho tỉnh Quảng Ninh.', ['Quảng Ninh', 'Quang Ninh']),
        ('dneg02', 'dev', 'Hãy liệt kê mã định danh và thu nhập của từng hộ gia đình trong dữ liệu gốc dùng cho báo cáo.',
         'Kho là báo cáo tổng hợp, không chứa bảng vi dữ liệu có mã định danh và thu nhập từng hộ.', ['microdata', 'household identifiers', 'individual household']),
        ('tneg01', 'test', 'Báo cáo ước lượng hệ số co giãn nhân quả của nghèo đói theo giá năng lượng tại Việt Nam là bao nhiêu, kèm sai số chuẩn?',
         'Có thảo luận về giá năng lượng/nghèo đói nhưng không có ước lượng nhân quả riêng Việt Nam kèm sai số chuẩn.', ['elasticity', 'standard error', 'regression']),
        ('tneg02', 'test', 'Hãy trích mã nguồn Python chính xác và danh sách phiên bản thư viện mà World Bank dùng để tạo các poverty nowcast trong báo cáo.',
         'Kho mô tả nowcast nhưng không chứa mã nguồn Python và môi trường thư viện tái lập của tác giả.', ['import pandas', 'requirements.txt', 'pip install']),
    ]
    for identifier, split, question, reason, terms in negative_specs:
        matches = {term: full_text.casefold().count(term.casefold()) for term in terms}
        case = {'id': identifier, 'split': split, 'answerable': False, 'question': question,
                'expected_behavior': 'search_and_abstain', 'absence_reason': reason,
                'absence_check': {'scope': 'Toàn bộ 37 trang PDF 43–79 trong snapshot, không chỉ top-k',
                                  'method': 'AI rà phạm vi báo cáo và tìm chuỗi toàn corpus; số 0 không tự chứng minh vắng mọi diễn đạt tương đương',
                                  'terms_and_counts': matches,
                                  'review_status': 'AI-prepared; học viên cần đọc đối chiếu trước khi chốt nhãn'}}
        (dev if split == 'dev' else test).append(case)
    def encoded(obj):
        return (json.dumps(obj, ensure_ascii=False, indent=2) + '\n').encode()
    files = {'benchmark/dev.json': encoded(dev), 'benchmark/test.json': encoded(test),
             'data/day6_chunks.json': encoded(chunks)}
    manifest = {'created_at_utc': datetime.now(timezone.utc).isoformat(),
                'source_snapshot_sha256': hashlib.sha256(snapshot_path.read_bytes()).hexdigest(),
                'files_sha256': {name: hashlib.sha256(data).hexdigest() for name, data in files.items()},
                'split_counts': {'dev': {'answerable': 15, 'unanswerable': 2}, 'test': {'answerable': 5, 'unanswerable': 2}},
                'status': 'Prepared by AI; awaiting student semantic review; no Day 7 test run',
                'history': 'Day 6 q01–q15 reused as dev. q16–q20 excluded from new test because previously inspected.',
                'selection_plan': ['Choose/tune only on dev; preserve all runs including regressions.',
                                   'Prioritize grounded answer and supported citations, then context evidence; break quality ties by latency/cost.',
                                   'Compare dense baseline, BM25, hybrid and >=2 improvement configs; freeze before test.',
                                   'Test run only after config freeze; test feedback requires a new independent test.'],
                'metric_policy': {'strict': 'Single-chunk Hit@1 / Evidence Hit@3, full literal gold and matching source/page.',
                                  'additional': 'EvidenceSetHit@1/@3 checks ALL fragments within one evidence set; alternative sets are OR.',
                                  'semantic': 'Exact normalized matching is a proxy, not semantic grading. Human-reviewed equivalent evidence must be recorded separately.',
                                  'unanswerable': 'Excluded from retrieval hit denominators; agent abstention evaluated later.'}}
    files['benchmark/manifest.json'] = encoded(manifest)
    for name in files:
        if (args.output / name).exists():
            raise FileExistsError(f'Output tồn tại, chọn thư mục mới: {name}')
    for name, data in files.items():
        target = args.output / name
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('xb') as file:
            file.write(data)
    print('Prepared dev 17 / test 7; no retrieval or agent run.')


if __name__ == '__main__':
    main()

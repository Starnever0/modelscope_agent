import json

report_path = 'data/eval/reports/eval_retrieval_report_20260323_171321.json'
dataset_path = 'data/eval/datasets/auto_questions_docid_80.jsonl'
output_path = 'data/eval/datasets/auto_questions_docid_80_badcases.jsonl'

try:
    with open(report_path, 'r', encoding='utf-8') as f:
        report_data = json.load(f)
    
    items = report_data.get('details', {}).get('items', [])
    bad_case_ids = set()
    for item in items:
        metrics = item.get('metrics', {})
        hit_at_k = metrics.get('hit_at_k', 1.0)
        recall_at_k = metrics.get('recall_at_k', 1.0)
        if hit_at_k < 1.0 or recall_at_k < 1.0:
            bad_case_ids.add(item.get('case_id'))
    
    bad_cases_count = len(bad_case_ids)
    print(f'Badcase count: {bad_cases_count}')
    print(f'First 10 case IDs: {list(bad_case_ids)[:10]}')

    bad_case_samples = []
    with open(dataset_path, 'r', encoding='utf-8') as f:
        for line in f:
            sample = json.loads(line)
            if sample.get('case_id') in bad_case_ids:
                bad_case_samples.append(sample)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        for sample in bad_case_samples:
            f.write(json.dumps(sample, ensure_ascii=False) + '\n')
    
    print(f'Successfully wrote {len(bad_case_samples)} samples to {output_path}')

except FileNotFoundError as e:
    print(f'Error: {e}')

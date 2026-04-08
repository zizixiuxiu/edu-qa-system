#!/usr/bin/env python
"""分析6组实验结果"""
import psycopg2
import sys

conn = psycopg2.connect(host='localhost', port=15432, database='edu_qa', user='postgres', password='password')
cur = conn.cursor()

print("=" * 80)
print("6组对比实验结果分析报告")
print("=" * 80)

# 1. 各实验配置结果
print("\n【1. 各实验配置结果对比】")
print("-" * 80)
cur.execute('''
SELECT 
    CASE 
        WHEN experiment_config = 'routing=False,rag=False' THEN '① Baseline (无路由无RAG)'
        WHEN experiment_config = 'routing=False,rag=True' THEN '② RAG Only (仅RAG)'
        WHEN experiment_config = 'routing=True,rag=False' THEN '③ Expert Routing (仅路由)'
        WHEN experiment_config = 'routing=True,rag=True' THEN '④ Full System (完整系统)'
        ELSE experiment_config
    END as exp_name,
    COUNT(*) as total,
    SUM(CASE WHEN is_correct THEN 1 ELSE 0 END) as correct,
    AVG(overall_score) as avg_score,
    AVG(accuracy_score) as avg_accuracy,
    AVG(completeness_score) as avg_completeness,
    AVG(educational_score) as avg_educational
FROM benchmark_results 
WHERE experiment_config IS NOT NULL
GROUP BY experiment_config
ORDER BY experiment_config
''')

for row in cur.fetchall():
    name, total, correct, score, acc, comp, edu = row
    accuracy = (correct/total*100) if total > 0 else 0
    print(f"\n{name}")
    print(f"  题目数: {total} | 正确: {correct} | 准确率: {accuracy:.1f}%")
    score_val = score if score else 0
    acc_val = acc if acc else 0
    comp_val = comp if comp else 0
    edu_val = edu if edu else 0
    print(f"  综合得分: {score_val:.2f} | 准确性: {acc_val:.2f} | 完整性: {comp_val:.2f} | 教育性: {edu_val:.2f}")

# 2. 按学科分析
print("\n\n【2. 学科表现分析】")
print("-" * 80)
cur.execute('''
SELECT 
    bd.subject,
    COUNT(*) as total,
    SUM(CASE WHEN br.is_correct THEN 1 ELSE 0 END) as correct,
    AVG(br.overall_score) as avg_score
FROM benchmark_results br
JOIN benchmark_datasets bd ON br.dataset_id = bd.id
GROUP BY bd.subject
ORDER BY COUNT(*) DESC
LIMIT 10
''')

print(f"{'学科':<10} {'题目数':>8} {'正确数':>8} {'准确率':>10} {'均分':>8}")
print("-" * 50)
for row in cur.fetchall():
    subject, total, correct, score = row
    accuracy = (correct/total*100) if total > 0 else 0
    score_str = f"{score:.2f}" if score else "N/A"
    print(f"{subject:<10} {total:>8} {correct:>8} {accuracy:>9.1f}% {score_str:>8}")

# 3. 关键发现
print("\n\n【3. 关键发现】")
print("-" * 80)

# 找出最佳配置
cur.execute('''
SELECT experiment_config, 
       AVG(CASE WHEN is_correct THEN 1 ELSE 0 END) as accuracy
FROM benchmark_results
WHERE experiment_config IS NOT NULL
GROUP BY experiment_config
ORDER BY accuracy DESC
LIMIT 1
''')
best = cur.fetchone()
if best:
    print(f"✓ 最佳配置: {best[0]} (准确率: {best[1]*100:.1f}%)")

# RAG效果
cur.execute('''
SELECT 
    SUM(CASE WHEN experiment_config LIKE '%rag=True%' AND is_correct THEN 1 ELSE 0 END) as rag_correct,
    SUM(CASE WHEN experiment_config LIKE '%rag=True%' THEN 1 ELSE 0 END) as rag_total,
    SUM(CASE WHEN experiment_config LIKE '%rag=False%' AND is_correct THEN 1 ELSE 0 END) as no_rag_correct,
    SUM(CASE WHEN experiment_config LIKE '%rag=False%' THEN 1 ELSE 0 END) as no_rag_total
FROM benchmark_results
WHERE experiment_config IS NOT NULL
''')
rag_stats = cur.fetchone()
if rag_stats and rag_stats[1] > 0 and rag_stats[3] > 0:
    rag_acc = rag_stats[0] / rag_stats[1] * 100
    no_rag_acc = rag_stats[2] / rag_stats[3] * 100
    print(f"✓ RAG效果: 启用RAG准确率 {rag_acc:.1f}% vs 无RAG {no_rag_acc:.1f}% ({'+' if rag_acc > no_rag_acc else ''}{rag_acc - no_rag_acc:.1f}%)")

# 路由效果
cur.execute('''
SELECT 
    SUM(CASE WHEN experiment_config LIKE 'routing=True%' AND is_correct THEN 1 ELSE 0 END) as routing_correct,
    SUM(CASE WHEN experiment_config LIKE 'routing=True%' THEN 1 ELSE 0 END) as routing_total,
    SUM(CASE WHEN experiment_config LIKE 'routing=False%' AND is_correct THEN 1 ELSE 0 END) as no_routing_correct,
    SUM(CASE WHEN experiment_config LIKE 'routing=False%' THEN 1 ELSE 0 END) as no_routing_total
FROM benchmark_results
WHERE experiment_config IS NOT NULL
''')
routing_stats = cur.fetchone()
if routing_stats and routing_stats[1] > 0 and routing_stats[3] > 0:
    routing_acc = routing_stats[0] / routing_stats[1] * 100
    no_routing_acc = routing_stats[2] / routing_stats[3] * 100
    print(f"✓ 路由效果: 启用路由准确率 {routing_acc:.1f}% vs 无路由 {no_routing_acc:.1f}% ({'+' if routing_acc > no_routing_acc else ''}{routing_acc - no_routing_acc:.1f}%)")

print("\n" + "=" * 80)
conn.close()

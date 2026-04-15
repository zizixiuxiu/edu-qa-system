# GAOKAO-Bench 数据集配置完成 ✅

## 📊 数据集概览

| 学科 | 题目数量 | 文件数 |
|------|----------|--------|
| 数学 | 432 | 2 |
| 英语 | 259 | 3 |
| 政治 | 320 | 1 |
| 历史 | 287 | 1 |
| 生物 | 150 | 1 |
| 化学 | 124 | 1 |
| 语文 | 85 | 2 |
| 物理 | 64 | 1 |
| 地理 | 34 | 1 |
| **总计** | **1755** | **15** |

## 🚀 快速开始

### 1️⃣ 验证配置（已完成）
```bash
cd edu-qa-system
python verify_gaokao_dataset.py
```

### 2️⃣ 导入数据到数据库
```bash
# 确保 PostgreSQL 已启动

# 方法1: 使用导入脚本
cd backend
python scripts/import_gaokao_full.py

# 方法2: 使用快捷脚本
./import_gaokao.sh
```

### 3️⃣ 启动后端服务
```bash
# 设置环境变量并启动
export GAOKAO_BENCH_PATH=/Users/zizixiuixu/Downloads/GAOKAO-Bench-main
cd backend
python start_backend.py
```

### 4️⃣ 启动前端
```bash
cd frontend
npm run dev
```

### 5️⃣ 开始评测
- 打开 http://localhost:3000
- 进入 **Benchmark** 页面
- 点击 **开始评测** 按钮
- 系统将自动从 GAOKAO-Bench 数据集中选题测试

## 📁 相关文件

| 文件 | 作用 |
|------|------|
| `setup_gaokao_dataset.py` | 配置脚本（已运行） |
| `verify_gaokao_dataset.py` | 验证脚本 |
| `import_gaokao.sh` | 数据导入快捷脚本 |
| `backend/scripts/import_gaokao_full.py` | 详细导入脚本 |
| `backend/.env.gaokao` | 环境变量配置 |

## 🔧 配置详情

### 后端配置 (`backend/app/api/benchmark.py`)
```python
GAOKAO_BENCH_PATH = "/Users/zizixiuixu/Downloads/GAOKAO-Bench-main"
```

### 学科映射
```python
SUBJECT_MAPPING = {
    "Biology": "生物",
    "Chemistry": "化学", 
    "Chinese": "语文",
    "English": "英语",
    "Geography": "地理",
    "History": "历史",
    "Math": "数学",
    "Physics": "物理",
    "Political_Science": "政治"
}
```

## 📖 使用场景

### 场景1: 系统功能测试
直接启动前后端，系统会自动从 GAOKAO-Bench 加载题目进行评测。

### 场景2: 批量评测
在后端启动后，访问:
```
GET /api/v1/benchmark/run?subject=数学&limit=50
```

### 场景3: 对比实验
运行项目中的对比实验脚本:
```bash
python run_6experiments_50q.py
```

## ⚠️ 注意事项

1. **数据库要求**: 导入数据前确保 PostgreSQL + pgvector 已启动
2. **Embedding服务**: 导入时会生成向量嵌入，确保 embedding 服务正常
3. **存储空间**: 导入后数据库约占用 500MB 空间
4. **环境变量**: 每次启动后端前确保 `GAOKAO_BENCH_PATH` 已设置

## 🔍 故障排除

### 问题1: 导入时提示 "数据目录不存在"
**解决**: 确认数据集路径正确
```bash
ls /Users/zizixiuixu/Downloads/GAOKAO-Bench-main/Data/Objective_Questions
```

### 问题2: 评测时找不到题目
**解决**: 检查环境变量
```bash
echo $GAOKAO_BENCH_PATH
# 应该输出: /Users/zizixiuixu/Downloads/GAOKAO-Bench-main
```

### 问题3: 某些学科没有题目
**解决**: 检查数据文件是否存在
```bash
python verify_gaokao_dataset.py
```

## 📝 数据结构

每道题目包含以下字段:
```json
{
  "year": "2010",
  "category": "（新课标）",
  "question": "题目内容（支持LaTeX）",
  "answer": ["D"],
  "analysis": "详细解析",
  "score": 5,
  "index": 0
}
```

---

✅ **配置完成!** 现在可以开始测试你的教育问答系统了。

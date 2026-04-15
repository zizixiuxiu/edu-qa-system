# GAOKAO-Bench 数据集下载指南

## 概述

你的项目中已有 **GAOKAO-Bench 示例数据**（每个学科5道题），用于基础测试。

如果需要**完整数据集**进行系统测试，请按以下步骤操作。

---

## 快速开始

### 方式1: 使用Python脚本下载（推荐）

```bash
cd edu-qa-system

# 安装依赖
pip install requests tqdm

# 运行下载脚本
python download_gaokao_dataset.py
```

数据将保存到: `backend/data/GAOKAO-Bench-Full/`

### 方式2: 使用Shell脚本下载

```bash
cd edu-qa-system

# 给脚本执行权限
chmod +x download_gaokao_simple.sh

# 运行下载脚本
./download_gaokao_simple.sh
```

### 方式3: 手动下载

1. 访问 GitHub 仓库: https://github.com/OpenBMB/GAOKAO-Bench
2. 点击 "Code" → "Download ZIP"
3. 解压后将 `data/` 目录复制到 `backend/data/GAOKAO-Bench-Full/raw/`

---

## 导入数据到系统

下载完成后，运行导入脚本：

```bash
cd edu-qa-system/backend

# 确保数据库和embedding服务已启动

# 导入完整数据集
python scripts/import_gaokao_full.py
```

---

## 数据格式说明

### 示例数据（已有）
- 路径: `backend/data/GAOKAO-Bench/`
- 内容: 每个学科5道示例题
- 用途: 快速测试系统功能

### 完整数据（需下载）
- 路径: `backend/data/GAOKAO-Bench-Full/`
- 内容: 约 **2000+ 道真实高考题目**
- 涵盖学科:
  - 语文、数学、英语
  - 物理、化学、生物
  - 历史、地理、政治

### 数据字段
```json
{
  "year": "2023",           // 年份
  "category": "新高考I卷",   // 试卷类型
  "question": "题目内容...", // 问题
  "answer": ["A"],          // 答案
  "analysis": "解析...",     // 详细解析
  "score": 5,               // 分值
  "type": "objective"       // 题型
}
```

---

## 使用场景

### 场景1: 快速功能测试
使用已有示例数据即可，无需下载完整数据集。

### 场景2: 系统评测/论文实验
需要下载完整数据集：
```bash
# 1. 下载数据
python download_gaokao_dataset.py

# 2. 导入系统
python backend/scripts/import_gaokao_full.py

# 3. 运行评测
python run_benchmark.py
```

### 场景3: 对比实验
项目已提供 `create_balanced_dataset.py` 创建均衡实验数据集（50题，涵盖9个学科）。

---

## 常见问题

### Q: 下载速度慢或失败？
**A:** 尝试以下方法：
1. 使用代理或VPN
2. 尝试不同的下载脚本
3. 手动从GitHub下载ZIP文件

### Q: 导入时出现embedding错误？
**A:** 确保：
1. PostgreSQL + pgvector 已安装
2. embedding服务（BGE模型）已启动
3. 数据库连接配置正确

### Q: 需要多大的存储空间？
**A:** 
- 原始JSON数据: ~10MB
- 导入数据库后: ~500MB（含向量索引）

### Q: 数据有版权限制吗？
**A:** GAOKAO-Bench是开源学术数据集，遵循相应开源协议，仅供研究使用。

---

## 相关文件

| 文件 | 说明 |
|------|------|
| `download_gaokao_dataset.py` | Python下载脚本 |
| `download_gaokao_simple.sh` | Shell下载脚本 |
| `backend/scripts/import_gaokao_full.py` | 数据导入脚本 |
| `create_balanced_dataset.py` | 创建实验数据集 |

---

## 下一步

下载并导入数据后，可以：

1. **运行基准测试**
   ```bash
   python run_benchmark.py
   ```

2. **启动6组对比实验**
   ```bash
   python run_6experiments_50q.py
   ```

3. **启动后端服务**
   ```bash
   python start_backend.py
   ```

4. **访问前端界面**
   ```bash
   cd frontend && npm run dev
   ```

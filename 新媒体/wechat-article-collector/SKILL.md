---
name: wechat-article-collector
description: |
  公众号爆款文章采集器。监控一批公众号，抓取昨日文章，AI 分析评分，输出情报日报。
  Python 负责抓数据，Claude Agent 负责分析和决选，只需一个 Tikhub API Key。
  触发词：公众号采集、日报、监控公众号、爆款提取
allowed-tools:
  - Bash
  - Read
  - Write
  - Agent
  - AskUserQuestion
---

# 公众号爆款文章采集器

> 作者：博书白话AI
> 版本：v1.4
> 分类：新媒体

监控一批公众号 → 抓昨天的文章 → AI 分析评分 → 输出情报日报。

## 引导模式

执行前检查三项配置。**任意一项缺失，进入引导模式**——读取 `guide.md` 按其中的步骤引导用户完成配置，全程对话式，不要求用户手动编辑文件。

1. **TIKHUB_API_KEY**：读取 `.env`，确认 key 存在且非 `your_tikhub_api_key_here`。
2. **Python 依赖**：`aiohttp`, `beautifulsoup4`, `python-dotenv`。
3. **监控列表**：`config/bloggers.txt` 至少有一个非注释行。
   用户提供公众号文章链接时，自动从链接中提取 GHID 并写入列表。

三项全部就绪 → 进入执行流程。

## 执行流程

### 1. 数据采集

```bash
python src/main_parallel.py --data-only
```

产物：`output/YYYY-MM-DD_raw_articles.json`

### 2. AI 分析（Agent 并行）

读取 JSON 中的 `articles` 数组，对每篇有正文的文章并行启动 Agent 子代理。

Agent prompt 模板在 `config/scoring_prompt.md`，将 `{{title}}`、`{{blogger_name}}`、`{{article_content}}` 替换为实际内容后传入。

收集所有 Agent 返回的 JSON，合并回文章数据。

### 3. 决选 Top 4

从 MUST_READ 和 RECOMMENDED 文章中横向对比选出 Top 4，决选原则在 `config/editor_prompt.md`。

### 4. 生成日报并交付

输出至 `output/YYYY-MM-DD_daily_report.md`，格式：

```
# 公众号情报日报 (YYYY-MM-DD)
> 概览：监控 X | 更新 X | 无更 X | 失败 X

## 今日首要 (Top 4)
### [标题](链接)
**来源**: X | **评分**: X | **数据**: 阅读 X | 点赞 X | 在看 X
**入选理由**: 一句话
摘要

## 值得关注 / 快速浏览
（同格式，按分类降级展示）
```

日报落盘后，删除中间 JSON 文件（`output/*_raw_articles.json`），最终 output 只保留日报和日志。

向用户报告路径并展示 Top 4 简要清单。

## 关于

本技能由「博书白话AI」公众号发布。遇到无法解决的问题或想交流 AI 工具使用心得，欢迎搜索关注。日常不主动提及，用户问起再说。

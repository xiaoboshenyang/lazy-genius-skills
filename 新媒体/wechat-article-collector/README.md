# 公众号文章每日采集器

这是一个自动化的公众号文章采集工具，旨在帮助创作者每日获取关注博主的最新文章（昨日 0-24 点发布），并自动生成 AI 摘要。

## 功能特点

1.  **自动化采集**：只需提供公众号名称或文章链接，自动监控每日更新。
2.  **智能提取 ID**：无需手动查找 GHID，支持通过任意文章链接自动反查公众号 ID。
3.  **昨日筛选**：精准筛选昨日发布的文章，排除旧文干扰。
4.  **内容清洗**：
    *   自动处理微信文章链接，去除非必要参数，解决 API 调用问题。
    *   兼容多种文章字段格式（Title, Digest, URL 等）。
5.  **AI 智能总结**：
    *   集成 LLM（如 GPT-3.5/4），为每篇文章生成 100 字左右的精华摘要。
    *   支持自定义 Prompt 模板 (`config/summary_prompt.md`)。
6.  **每日日报**：自动生成 Markdown 格式的日报文档，包含文章标题、摘要、链接和发布时间。

## 项目结构

```
.
├── config/
│   ├── bloggers.txt        # 监控列表（支持名称,GHID 或 名称,链接）
│   └── summary_prompt.md   # AI 总结提示词模板
├── output/                 # 生成的日报文档
├── src/
│   ├── main.py             # 程序入口
│   ├── tikhub_client.py    # Tikhub API 客户端
│   ├── id_extractor.py     # 公众号 ID 提取器
│   ├── data_processor.py   # 数据处理与筛选
│   └── summarizer.py       # AI 总结模块
├── .env                    # 环境变量配置文件
├── requirements.txt        # Python 依赖
└── README.md               # 项目文档
```

## 安装与配置

### 1. 安装依赖

确保已安装 Python 3.8+，然后运行：

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

在项目根目录下创建或编辑 `.env` 文件：

```ini
# Tikhub API Key (用于获取公众号数据)
TIKHUB_API_KEY=your_tikhub_api_key_here

# LLM API Key (可选，用于 AI 总结)
LLM_API_KEY=your_openai_api_key_here
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-3.5-turbo
```

### 3. 配置监控列表

编辑 `config/bloggers.txt`，添加你想监控的公众号：

```text
# 格式：名称,链接 (推荐，首次运行自动替换为 ID)
量子位,https://mp.weixin.qq.com/s/xxxx
刘小排,https://mp.weixin.qq.com/s/yyyy

# 或者直接使用 GHID
机器之心,gh_123456789abc
```

### 4. 自定义 AI 总结

编辑 `config/summary_prompt.md`，修改 AI 总结的指令。你可以调整字数限制、语气风格等。

## 使用方法

运行主程序：

```bash
python src/main.py
```

程序将：
1.  读取 `bloggers.txt`，自动将链接转换为 GHID（并回写保存）。
2.  调用 Tikhub API 获取每个博主的最新文章列表。
3.  筛选出发布日期为昨日的文章。
4.  获取文章正文详情。
5.  调用 AI 生成摘要。
6.  在 `output` 目录下生成 `YYYY-MM-DD_daily_report.md`。

## 每日选题执行器（新增）

运行：

```bash
python src/daily_topic_runner.py
```

行为说明：
1. 只检查目标日报（中国时区昨天），若日报已存在则跳过采集 API 调用。
2. 从 `output/` 直接读取近 3 天日报，不重复拉取历史数据。
3. 融合在制稿件、选题池、灵感内容，调用单一候选题提示词生成 3-8 条候选题。
4. 运行期间使用进程锁（`output/.daily_topic_runner.lock`），支持陈旧锁自动回收（按 PID 与时间判断）。
5. 每次运行都会写入结构化结果文件 `output/daily_topic_runner_result.json`，供定时任务稳定读取。
6. 输出到：
   - `projects/writing-main-core-v3/03_计划区/选题池/daily_candidates/YYYY-MM-DD_candidates.json`
   - `projects/writing-main-core-v3/03_计划区/选题池/daily_candidates/YYYY-MM-DD_candidates.md`
   - 若 V3 不存在，则自动回退到 V2 `notes/01_选题系统/daily_candidates/`

可选参数：
- `--target-date YYYY-MM-DD`：指定目标日报日（用于回放测试）。
- `--force-fetch`：强制重新采集日报。
- `--force-generate`：强制重新生成候选题。

可选环境变量：
- `DAILY_TOPIC_COLLECTOR_TIMEOUT_SECONDS`：采集器子进程超时秒数（默认 1200）。
- `DAILY_TOPIC_LOCK_STALE_SECONDS`：锁过期秒数（默认 3600）。

## 常见问题

*   **API 400 错误**：如果遇到获取文章详情失败，通常是因为链接包含特殊字符。本项目已内置 `_clean_wx_url` 机制，自动清洗 URL，通常无需干预。
*   **无 AI 摘要**：请检查 `.env` 中是否配置了 `LLM_API_KEY`。如果未配置，将使用默认的简短摘要。
*   **重复执行**：`daily_topic_runner` 默认幂等，目标日报存在即不重复采集；候选题存在即不重复生成。

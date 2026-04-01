import sys
import os
import asyncio
import logging
import json
import time
from datetime import datetime
from dotenv import load_dotenv

# 加载环境变量
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))

# 添加项目根目录到 sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.async_tikhub_client import AsyncTikhubClient
from src.id_extractor import extract_ghid_from_url
from src.data_processor import DataProcessor

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'output', 'run_parallel.log'), encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# --- 辅助函数 (复用 main.py) ---
def load_bloggers(file_path):
    bloggers = []
    if not os.path.exists(file_path):
        logger.error(f"配置文件不存在: {file_path}")
        return bloggers

    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            parts = line.split(',')
            if len(parts) >= 2:
                name = parts[0].strip()
                value = parts[1].strip()
                blogger = {"name": name}
                if value.startswith('gh_'):
                    blogger['gh_id'] = value
                elif value.startswith('http'):
                    blogger['url'] = value
                else:
                    logger.warning(f"无法识别的配置行: {line}")
                    continue
                bloggers.append(blogger)
            elif len(parts) == 1 and parts[0].startswith('gh_'):
                bloggers.append({"name": "Unknown", "gh_id": parts[0].strip()})
    return bloggers

def update_blogger_config(file_path, url, gh_id):
    try:
        lines = []
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        new_lines = []
        modified = False
        for line in lines:
            if url in line and not line.strip().startswith('#'):
                new_line = line.replace(url, gh_id)
                new_lines.append(new_line)
                modified = True
                logger.info(f"更新配置文件: 将链接替换为 ID")
            else:
                new_lines.append(line)
        if modified:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)
            logger.info(f"配置文件已保存: {file_path}")
    except Exception as e:
        logger.error(f"更新配置文件失败: {e}")

# --- 报告生成函数 (适配异步结果) ---
def generate_report(all_results, top_4_indices, ranking_reasons, processor):
    yesterday_start, _ = processor.get_yesterday_range()
    date_str = yesterday_start.strftime('%Y-%m-%d')
    
    flat_articles = []
    silent_bloggers = []
    failed_bloggers = []
    
    for blogger, articles in all_results.items():
        if articles is None:
            failed_bloggers.append(blogger)
        elif len(articles) == 0:
            silent_bloggers.append(blogger)
        else:
            for article in articles:
                article['blogger_name'] = blogger
                flat_articles.append(article)
    
    total_monitored = len(all_results)
    updated_count = total_monitored - len(silent_bloggers) - len(failed_bloggers)
    
    report = []
    report.append(f"# 公众号情报日报 ({date_str})")
    report.append(f"> 📊 **概览**：监控 {total_monitored} 个 | ✅ 更新 {updated_count} 个 | 😴 无更 {len(silent_bloggers)} 个 | ❌ 失败 {len(failed_bloggers)} 个\n")
    
    if failed_bloggers:
        report.append(f"## ❌ 采集失败 (Failed)")
        report.append(f"> {', '.join(failed_bloggers)}\n")
        
    if silent_bloggers:
        report.append(f"## 😴 今日无更 (Silent)")
        report.append(f"> {', '.join(silent_bloggers)}\n")

    # 分类文章
    candidates = [] # MUST_READ / RECOMMENDED
    others = []     # SKIM / IGNORE
    
    for article in flat_articles:
        cat = article.get('analysis', {}).get('category', 'SKIM')
        if cat in ['MUST_READ', 'RECOMMENDED']:
            candidates.append(article)
        else:
            others.append(article)
            
    # --- Top 4 ---
    report.append("## 👑 今日首要 (Top 4 Essential)")
    
    if top_4_indices:
        for idx in top_4_indices:
            # article['_temp_id'] 必须在调用此函数前设置好
            article = next((a for a in candidates if a.get('_temp_id') == idx), None)
            if article:
                _format_article_detail(report, article, ranking_reasons.get(idx))
    elif candidates:
        # 如果没有 Top 4 结果但有候选，直接显示前4个
        candidates.sort(key=lambda x: x.get('analysis', {}).get('score', {}).get('total', 0), reverse=True)
        for article in candidates[:4]:
            _format_article_detail(report, article)
    else:
        report.append("*今日无重磅内容*\n")
        
    # --- Recommended ---
    recommended = [
        a for a in candidates 
        if a.get('_temp_id') not in top_4_indices
    ]
    
    report.append("## 🥈 值得关注 (Recommended)")
    if not recommended:
        report.append("*无其他推荐*\n")
    else:
        for article in recommended:
            _format_article_detail(report, article)

    # --- Skim ---
    report.append("## 🥉 快速浏览 (Skim)")
    if not others:
        report.append("*无*\n")
    else:
        for article in others:
            _format_article_simple(report, article)
            
    report.append("---")
    return "\n".join(report)

def _format_article_detail(report, article, reason=None):
    title = article.get('title', '无标题')
    url = article.get('url', '#')
    blogger = article.get('blogger_name', 'Unknown')
    analysis = article.get('analysis', {})
    summary = analysis.get('summary', '无摘要')
    score = analysis.get('score', {}).get('total', 0)
    
    report.append(f"### [{title}]({url})")
    report.append(f"**来源**: {blogger} | **评分**: {score}")
    if reason:
        report.append(f"**入选理由**: {reason}")
    report.append(f"\n{summary}\n")

def _format_article_simple(report, article):
    title = article.get('title', '无标题')
    url = article.get('url', '#')
    blogger = article.get('blogger_name', 'Unknown')
    analysis = article.get('analysis', {})
    summary = analysis.get('summary', '无摘要')
    
    report.append(f"#### [{title}]({url}) - {blogger}")
    report.append(f"> {summary}\n")

# --- 主流程 ---
async def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-only", action="store_true", help="只跑 Phase 1-3（抓数据），不做 AI 分析")
    args = parser.parse_args()

    logger.info("=== 启动并行采集器 (Parallel Mode) ===")
    start_time = time.time()

    # Init
    tikhub = AsyncTikhubClient()
    processor = DataProcessor()

    # Load Configs
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'bloggers.txt')
    bloggers = load_bloggers(config_path)
    
    all_results = {} # {blogger_name: [articles]}
    
    # === Phase 1: Batch Fetch Lists ===
    logger.info(f"--- Phase 1: 获取文章列表 (Total: {len(bloggers)}) ---")
    
    batch_size = 10
    raw_list_results = [] # [(blogger_obj, api_data), ...]

    for i in range(0, len(bloggers), batch_size):
        batch = bloggers[i:i+batch_size]
        logger.info(f"Batch {i//batch_size + 1}: Processing {len(batch)} bloggers...")

        tasks = []
        for b in batch:
            # 检查是否有 GHID，如果没有且有 URL，尝试提取
            if not b.get('gh_id') and b.get('url'):
                gh_id = extract_ghid_from_url(b['url'])
                if gh_id:
                    b['gh_id'] = gh_id
                    update_blogger_config(config_path, b['url'], gh_id)

            if b.get('gh_id'):
                tasks.append(tikhub.get_article_list(b['gh_id']))
            else:
                tasks.append(asyncio.sleep(0, result=None))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for blogger, res in zip(batch, results):
            raw_list_results.append((blogger, res))

        if i + batch_size < len(bloggers):
            await asyncio.sleep(0.3)

    # === Data Processing (Sync) ===
    logger.info("--- Phase 2: 数据筛选 ---")
    target_articles = [] # [article_dict, ...]
    
    for blogger, api_data in raw_list_results:
        name = blogger['name']
        if isinstance(api_data, Exception) or not api_data:
            logger.error(f"[{name}] 获取列表失败: {api_data}")
            all_results[name] = None
            continue
            
        daily_articles = processor.filter_articles_by_date(api_data, limit_per_account=1)
        all_results[name] = daily_articles
        
        if daily_articles:
            for art in daily_articles:
                art['blogger_name'] = name # Attach blogger name
                target_articles.append(art)
        else:
            logger.info(f"[{name}] 无更新")

    logger.info(f"筛选完成: 共有 {len(target_articles)} 篇待处理文章")

    # === Phase 3: Batch Fetch Details & Stats ===
    if target_articles:
        logger.info(f"--- Phase 3: 获取文章正文与统计数据 (Total: {len(target_articles)}) ---")
        
        for i in range(0, len(target_articles), batch_size):
            batch = target_articles[i:i+batch_size]
            logger.info(f"Fetching details & stats for batch {i//batch_size + 1}...")
            
            # detail 和 stats 合并为一次 gather，真正并发
            all_tasks = (
                [tikhub.get_article_detail(art['url']) for art in batch] +
                [tikhub.get_article_stats(art['url']) for art in batch]
            )
            all_results_batch = await asyncio.gather(*all_tasks, return_exceptions=True)
            detail_results = all_results_batch[:len(batch)]
            stats_results = all_results_batch[len(batch):]

            for j, art in enumerate(batch):
                content_data = detail_results[j]
                art['full_content'] = content_data if content_data and not isinstance(content_data, Exception) else ""
                if not art['full_content']:
                    logger.warning(f"[{art['title']}] 获取正文失败")

                stats_data = stats_results[j]
                if stats_data and not isinstance(stats_data, Exception):
                    art['stats'] = stats_data
                else:
                    logger.warning(f"[{art['title']}] 获取统计数据失败")

            if i + batch_size < len(target_articles):
                await asyncio.sleep(0.3)

    # === data-only 模式：导出 JSON 后退出 ===
    today_str = datetime.now().strftime('%Y-%m-%d')
    output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'output')
    os.makedirs(output_dir, exist_ok=True)

    if args.data_only:
        # 导出原始数据供 Claude Agent 分析
        export_data = {
            "date": today_str,
            "total_monitored": len(all_results),
            "silent_bloggers": [name for name, arts in all_results.items() if arts is not None and len(arts) == 0],
            "failed_bloggers": [name for name, arts in all_results.items() if arts is None],
            "articles": []
        }
        for idx, art in enumerate(target_articles):
            export_data["articles"].append({
                "index": idx,
                "title": art.get("title", "无标题"),
                "url": art.get("url", ""),
                "blogger_name": art.get("blogger_name", "Unknown"),
                "publish_time": art.get("publish_time", ""),
                "digest": art.get("digest", ""),
                "full_content": (art.get("full_content") or "")[:12000],
                "stats": art.get("stats", {})
            })

        json_path = os.path.join(output_dir, f"{today_str}_raw_articles.json")
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)

        await tikhub.close()
        duration = time.time() - start_time
        logger.info(f"=== data-only 完成 (耗时: {duration:.2f}s) ===")
        print(f"\n✅ 数据采集完成！耗时 {duration:.2f}s")
        print(f"- 文章数: {len(target_articles)}")
        print(f"- JSON: {json_path}")
        return

    # === 完整模式（兼容旧流程，需要 LLM key） ===
    from src.async_summarizer import AsyncLLMClient
    llm = AsyncLLMClient()

    def load_prompt(filename, default):
        path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', filename)
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return f.read()
        except:
            return default

    scoring_template = load_prompt('scoring_prompt.md', "请总结:\n{{article_content}}")
    editor_template = load_prompt('editor_prompt.md', "")

    # Phase 4: Batch AI Analysis
    if target_articles:
        logger.info(f"--- Phase 4: AI 分析 (Total: {len(target_articles)}) ---")
        for i in range(0, len(target_articles), batch_size):
            batch = target_articles[i:i+batch_size]
            logger.info(f"Analyzing batch {i//batch_size + 1}...")
            tasks = []
            for art in batch:
                content = art.get('full_content', '')
                if content:
                    tasks.append(llm.analyze_article(content, scoring_template))
                else:
                    tasks.append(asyncio.sleep(0, result={"summary": "无正文", "category": "IGNORE"}))
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for art, analysis in zip(batch, results):
                if isinstance(analysis, Exception):
                    art['analysis'] = {"summary": "分析出错", "category": "SKIM"}
                else:
                    art['analysis'] = analysis
            await asyncio.sleep(2)

    # Phase 5: Ranking & Reporting
    logger.info("--- Phase 5: 终极决选与报告 ---")
    candidates = []
    for i, art in enumerate(target_articles):
        art['_temp_id'] = i
        cat = art.get('analysis', {}).get('category', 'SKIM')
        if cat in ['MUST_READ', 'RECOMMENDED']:
            candidates.append(art)
    top_4_indices = []
    ranking_reasons = {}
    if len(candidates) > 4 and editor_template:
        candidates_data = []
        for art in candidates:
            analysis = art.get('analysis', {})
            candidates_data.append({
                "index": art['_temp_id'],
                "title": art['title'],
                "blogger": art['blogger_name'],
                "score": analysis.get('score', {}).get('total', 0),
                "summary": analysis.get('summary', '')[:100]
            })
        rank_result = await llm.rank_articles(json.dumps(candidates_data, ensure_ascii=False), editor_template)
        for item in rank_result.get('top_4', []):
            idx = item.get('index')
            if idx is not None:
                top_4_indices.append(idx)
                ranking_reasons[idx] = item.get('reason', '')

    report_content = generate_report(all_results, top_4_indices, ranking_reasons, processor)
    output_filename = f"{today_str}_daily_report.md"
    output_path = os.path.join(output_dir, output_filename)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(report_content)

    duration = time.time() - start_time
    logger.info(f"=== 全部完成 (耗时: {duration:.2f}s) ===")
    print(f"\n✅ 并行采集完成！耗时 {duration:.2f}s，报告已生成: {output_path}")

if __name__ == "__main__":
    asyncio.run(main())

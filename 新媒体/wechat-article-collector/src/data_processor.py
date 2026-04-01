from datetime import datetime, timedelta
import logging
import json

logger = logging.getLogger(__name__)

class DataProcessor:
    def __init__(self):
        pass

    def get_yesterday_range(self):
        """
        获取昨天的日期范围 (00:00:00 - 23:59:59)
        :return: (datetime_start, datetime_end)
        """
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        yesterday_start = today - timedelta(days=1)
        yesterday_end = today - timedelta(seconds=1)
        return yesterday_start, yesterday_end

    def filter_articles_by_date(self, articles_data, target_date=None, limit_per_account=1):
        """
        筛选指定日期的文章
        :param articles_data: Tikhub API 返回的原始 JSON 数据
        :param target_date: 目标日期 (datetime对象)，默认为昨天
        :param limit_per_account: 每个账号最大采集文章数（默认为1，即只采头条）
        :return: 筛选后的文章列表 (list of dict)
        """
        if not articles_data or 'data' not in articles_data or 'list' not in articles_data['data']:
            logger.warning("API 返回数据格式异常或为空")
            return []

        article_list = articles_data['data']['list']
        filtered_articles = []
        
        if target_date is None:
            target_date, _ = self.get_yesterday_range()
            
        target_date_str = target_date.strftime('%Y-%m-%d')
        logger.info(f"开始筛选文章，目标日期: {target_date_str}")

        for item in article_list:
            # 字段适配
            try:
                pub_time = item.get('send_time')
                if not pub_time:
                    pub_time = item.get('publish_time')
                
                if not pub_time:
                    logger.debug(f"文章缺少时间字段，跳过: {item.get('Title', 'Unknown')}")
                    continue

                # 转换时间戳
                article_time = datetime.fromtimestamp(int(pub_time))
                article_date_str = article_time.strftime('%Y-%m-%d')

                if article_date_str == target_date_str:
                    filtered_articles.append({
                        "title": item.get('Title', item.get('title', '无标题')),
                        "digest": item.get('Digest', item.get('digest', '无概要')),
                        "url": item.get('ContentUrl', item.get('url', '')),
                        "publish_time": article_time.strftime('%Y-%m-%d %H:%M:%S'),
                        "author": item.get('author', 'Unknown') 
                    })
            except Exception as e:
                logger.error(f"处理文章数据出错: {e}, Data: {item}")
                continue

        # 限制返回数量 (默认只取头条)
        if limit_per_account > 0 and len(filtered_articles) > limit_per_account:
            logger.info(f"触发数量限制: 发现 {len(filtered_articles)} 篇，仅保留前 {limit_per_account} 篇")
            filtered_articles = filtered_articles[:limit_per_account]

        logger.info(f"筛选完成，共找到 {len(filtered_articles)} 篇符合日期的文章")
        return filtered_articles

    def format_report(self, all_articles, llm_client=None, editor_prompt_template=None, target_date=None):
        """
        将所有文章格式化为 Markdown 报告 (引入主编决选机制)
        """
        if target_date:
            date_str = target_date.strftime('%Y-%m-%d')
        else:
            yesterday_start, _ = self.get_yesterday_range()
            date_str = yesterday_start.strftime('%Y-%m-%d')
        
        # 1. 统计状态 & 拍平文章列表
        flat_articles = []
        silent_bloggers = [] # 无更
        failed_bloggers = [] # 失败
        
        for blogger, articles in all_articles.items():
            if articles is None:
                failed_bloggers.append(blogger)
            elif len(articles) == 0:
                silent_bloggers.append(blogger)
            else:
                for article in articles:
                    article['blogger_name'] = blogger
                    flat_articles.append(article)
        
        total_count = len(flat_articles)
        total_monitored = len(all_articles)
        updated_count = total_monitored - len(silent_bloggers) - len(failed_bloggers)
        
        # 2. 筛选出有资格进入决赛圈的文章 (MUST_READ 和 RECOMMENDED)
        candidates = []
        others = [] # SKIM 和 IGNORE
        
        for i, article in enumerate(flat_articles):
            cat = article.get('analysis', {}).get('category', 'SKIM')
            # 给每篇文章打上临时 ID，方便 AI 引用
            article['_temp_id'] = i
            
            if cat in ['MUST_READ', 'RECOMMENDED']:
                candidates.append(article)
            else:
                others.append(article)
        
        # 3. 执行主编决选 (如果候选 > 4 且 配置了 LLM)
        top_4_indices = []
        ranking_reasons = {}
        
        if len(candidates) > 4 and llm_client and editor_prompt_template:
            # 准备发给 AI 的精简数据
            candidates_data = []
            for art in candidates:
                analysis = art.get('analysis', {})
                candidates_data.append({
                    "index": art['_temp_id'],
                    "title": art['title'],
                    "blogger": art['blogger_name'],
                    "score": analysis.get('score', {}).get('total', 0),
                    "summary": analysis.get('summary', '')[:100] # 只要前100字
                })
            
            # 调用 LLM
            rank_result = llm_client.rank_articles(json.dumps(candidates_data, ensure_ascii=False), editor_prompt_template)
            
            # 解析结果
            for item in rank_result.get('top_4', []):
                idx = item.get('index')
                if idx is not None:
                    top_4_indices.append(idx)
                    ranking_reasons[idx] = item.get('reason', '')
        
        elif len(candidates) > 0:
            # 如果候选少于等于4，直接全选，或者按分数排序选前4
            # 简单按分数排序
            candidates.sort(key=lambda x: x.get('analysis', {}).get('score', {}).get('total', 0), reverse=True)
            for art in candidates[:4]:
                top_4_indices.append(art['_temp_id'])
                
        # 4. 生成报告内容
        report = []
        report.append(f"# 公众号情报日报 ({date_str})")
        report.append(f"> 📊 **概览**：监控 {total_monitored} 个 | ✅ 更新 {updated_count} 个 | 😴 无更 {len(silent_bloggers)} 个 | ❌ 失败 {len(failed_bloggers)} 个\n")
        
        # --- ❌ 失败名单 (Failed) ---
        if failed_bloggers:
            report.append(f"## ❌ 采集失败 (Failed)")
            report.append(f"> {', '.join(failed_bloggers)}\n")
            
        # --- 😴 无更名单 (Silent) ---
        if silent_bloggers:
            report.append(f"## 😴 今日无更 (Silent)")
            report.append(f"> {', '.join(silent_bloggers)}\n")

        # --- 👑 Top 4 (必读) ---
        report.append("## 👑 今日首要 (Top 4 Essential)")
        if not top_4_indices and not candidates:
            report.append("*今日无重磅内容*\n")
        else:
            # 如果有 Top 4 决选结果
            if top_4_indices:
                for idx in top_4_indices:
                    # 找到对应的文章对象
                    article = next((a for a in candidates if a['_temp_id'] == idx), None)
                    if article:
                        self._format_article_detail(report, article, ranking_reasons.get(idx))
            # 如果没有决选（候选少于4个），直接列出所有候选
            elif candidates:
                for article in candidates:
                    self._format_article_detail(report, article)
        
        # --- 🥈 推荐 (Recommended) ---
        # 排除掉已经是 Top 4 的文章
        recommended = [
            a for a in candidates 
            if a['_temp_id'] not in top_4_indices
        ]
        
        report.append("## 🥈 值得关注 (Recommended)")
        if not recommended:
            report.append("*无其他推荐*\n")
        else:
            for article in recommended:
                self._format_article_detail(report, article)

        # --- 🥉 快速浏览 (Skim) & 忽略 (Ignore) ---
        # 用户要求：即使是 Skim 也要有概要
        report.append("## 🥉 快速浏览 (Skim)")
        if not others:
            report.append("*无*\n")
        else:
            for article in others:
                # 使用简略版格式，但包含概要
                self._format_article_simple_with_summary(report, article)
                
        report.append("---")
        return "\n".join(report)

    def _format_article_detail(self, report, article, reason=None):
        """格式化详细文章块"""
        title = article.get('title', '无标题')
        url = article.get('url', '#')
        blogger = article.get('blogger_name', 'Unknown')
        analysis = article.get('analysis', {})
        summary = analysis.get('summary', '无摘要')
        score = analysis.get('score', {}).get('total', 0)
        
        # 统计数据
        stats = article.get('stats', {})
        read_num = stats.get('readnum', '-')
        like_num = stats.get('oldlikenum', '-') # 微信"点赞"通常是 oldlikenum
        wow_num = stats.get('likenum', '-')    # 微信"在看"通常是 likenum
        comment_num = stats.get('comment_count', '-')
        # share_num = stats.get('share_num', '-') # 转发数据暂不一定准确，可选展示
        
        report.append(f"### [{title}]({url})")
        report.append(f"**来源**: {blogger} | **评分**: {score}")
        
        # 新增统计行
        stats_line = f"**数据**: 阅读 {read_num} | 点赞 {like_num} | 在看 {wow_num} | 评论 {comment_num}"
        report.append(stats_line)
        
        if reason:
            report.append(f"**入选理由**: {reason}")
        report.append(f"\n{summary}\n")

    def _format_article_simple(self, report, article):
        """格式化简略文章块"""
        title = article.get('title', '无标题')
        url = article.get('url', '#')
        blogger = article.get('blogger_name', 'Unknown')
        
        # 统计数据简略版
        stats = article.get('stats', {})
        read_num = stats.get('readnum', '-')
        
        report.append(f"- [{title}]({url}) - {blogger} (阅读: {read_num})\n")

    def _format_article_simple_with_summary(self, report, article):
        """格式化简略文章块 (带摘要)"""
        title = article.get('title', '无标题')
        url = article.get('url', '#')
        blogger = article.get('blogger_name', 'Unknown')
        analysis = article.get('analysis', {})
        summary = analysis.get('summary', '无摘要')
        
        # 统计数据
        stats = article.get('stats', {})
        read_num = stats.get('readnum', '-')
        like_num = stats.get('oldlikenum', '-')
        
        report.append(f"#### [{title}]({url}) - {blogger}")
        report.append(f"*(阅读: {read_num} | 点赞: {like_num})*")
        report.append(f"> {summary}\n")

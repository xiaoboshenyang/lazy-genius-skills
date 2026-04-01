import aiohttp
import logging
import os
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs, urlencode

logger = logging.getLogger(__name__)

class AsyncTikhubClient:
    def __init__(self, api_key=None, base_url="https://api.tikhub.io"):
        self.api_key = api_key or self._load_api_key()
        self.base_url = base_url.rstrip('/')
        self._session = None  # 共享 session，延迟初始化

        if not self.api_key:
            logger.warning("未配置有效的 Tikhub API Key")

    def _load_api_key(self):
        env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
        if os.path.exists(env_path):
            with open(env_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip().startswith('TIKHUB_API_KEY='):
                        key = line.split('=', 1)[1].strip()
                        if key:
                            return key
        return None

    async def _get_session(self):
        """复用共享 session，避免每次请求重建 TCP 连接"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                headers={"Authorization": f"Bearer {self.api_key}"}
            )
        return self._session

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()

    def _clean_wx_url(self, original_url):
        try:
            parsed = urlparse(original_url)
            params = parse_qs(parsed.query)
            core_params = ['__biz', 'mid', 'idx', 'sn']
            new_params = {k: params[k][0] for k in core_params if k in params}
            if not new_params:
                return original_url.replace("http://", "https://")
            return f"https://{parsed.netloc}{parsed.path}?{urlencode(new_params)}"
        except Exception as e:
            logger.warning(f"URL 清洗失败: {e}")
            return original_url

    def _extract_clean_content(self, data):
        """从 API data 字段提取并清洗正文文本"""
        if not data:
            return ""

        raw = (
            data.get('content_noencode') or
            data.get('content') or
            data.get('text') or
            data.get('raw_content')
        )
        if not raw:
            return ""

        # 处理 dict 结构
        if isinstance(raw, dict):
            raw = raw.get('text') or raw.get('html') or ""

        # 处理 list 结构
        if isinstance(raw, list):
            raw = "\n".join(str(item) for item in raw if item)

        if not isinstance(raw, str):
            raw = str(raw)

        # BeautifulSoup 清洗 HTML
        try:
            soup = BeautifulSoup(raw, 'html.parser')
            for tag in soup(["script", "style"]):
                tag.decompose()
            lines = [line.strip() for line in soup.get_text(separator='\n').splitlines()]
            return '\n'.join(line for line in lines if line)
        except Exception:
            return raw

    async def get_article_list(self, gh_id, page=1, page_size=20):
        url = f"{self.base_url}/api/v1/wechat_mp/web/fetch_mp_article_list"
        session = await self._get_session()
        try:
            async with session.get(url, params={"ghid": gh_id, "page": page, "page_size": page_size}, timeout=aiohttp.ClientTimeout(total=60)) as resp:
                if resp.status != 200:
                    raise Exception(f"Status={resp.status}, Body={await resp.text()}")
                return await resp.json()
        except Exception as e:
            logger.error(f"获取文章列表异常 [{gh_id}]: {e}")
            raise

    async def get_article_detail(self, article_url):
        cleaned_url = self._clean_wx_url(article_url)
        url = f"{self.base_url}/api/v1/wechat_mp/web/fetch_mp_article_detail_json"
        session = await self._get_session()
        try:
            async with session.get(url, params={"url": cleaned_url}, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return self._extract_clean_content(data.get('data', {}))
                logger.error(f"获取文章详情失败: {resp.status}")
                return ""
        except Exception as e:
            logger.error(f"获取文章详情异常: {e}")
            return ""

    async def get_article_stats(self, article_url):
        cleaned_url = self._clean_wx_url(article_url)
        url = f"{self.base_url}/api/v1/wechat_mp/web/fetch_mp_article_read_count"
        session = await self._get_session()
        try:
            async with session.get(url, params={"url": cleaned_url, "comment_id": "0"}, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get('data')
                logger.error(f"获取统计数据失败: {resp.status}")
                return None
        except Exception as e:
            logger.error(f"获取统计数据异常: {e}")
            return None

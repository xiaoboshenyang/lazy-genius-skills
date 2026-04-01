import requests
import re
import logging
import time
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

def _normalize_url(url):
    if not isinstance(url, str):
        return None
    normalized = url.strip()
    if not normalized:
        return None
    parsed = urlparse(normalized)
    if not parsed.scheme:
        normalized = "https://" + normalized.lstrip("/")
    elif parsed.scheme == "http":
        normalized = "https://" + normalized[len("http://"):]
    return normalized

def _extract_ghid_from_content(content):
    patterns = [
        r'var\s+user_name\s*=\s*"([^"]+)"',
        r"var\s+user_name\s*=\s*'([^']+)'",
        r'"user_name"\s*:\s*"([^"]+)"',
        r"'user_name'\s*:\s*'([^']+)'"
    ]
    for pattern in patterns:
        match = re.search(pattern, content)
        if match:
            ghid = match.group(1)
            if ghid.startswith("gh_"):
                return ghid

    matches = re.findall(r'gh_[a-zA-Z0-9]{8,20}', content)
    if matches:
        return matches[0]

    return None

def extract_ghid_from_url(url, max_retries=2, timeout=(5, 15)):
    """
    从公众号文章链接中提取 GHID (user_name)
    :param url: 公众号文章链接
    :return: ghid (例如 gh_xxxxxxxx) 或 None
    """
    normalized_url = _normalize_url(url)
    if not normalized_url:
        logger.error("链接为空或无效")
        return None

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    with requests.Session() as session:
        for attempt in range(max_retries + 1):
            try:
                logger.info(f"正在访问链接: {normalized_url}")
                response = session.get(normalized_url, headers=headers, timeout=timeout)
                response.raise_for_status()
                if not response.encoding:
                    response.encoding = response.apparent_encoding
                content = response.text

                ghid = _extract_ghid_from_content(content)
                if ghid:
                    logger.info(f"成功提取 GHID: {ghid}")
                    return ghid

                logger.warning("未能从页面中提取到 GHID")
                return None

            except requests.exceptions.RequestException as e:
                if attempt < max_retries:
                    logger.warning(f"请求失败，准备重试: {e}")
                    time.sleep(1 + attempt)
                    continue
                logger.error(f"请求链接失败: {e}")
                return None
            except Exception as e:
                logger.error(f"提取过程发生错误: {e}")
                return None

if __name__ == "__main__":
    # 本地测试
    test_url = input("请输入文章链接: ")
    if test_url:
        print(extract_ghid_from_url(test_url))

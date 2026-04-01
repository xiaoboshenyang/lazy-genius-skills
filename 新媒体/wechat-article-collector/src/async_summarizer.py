import os
import aiohttp
import logging
import json
import re
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class AsyncLLMClient:
    def __init__(self):
        self.api_key = os.getenv("LLM_API_KEY")
        self.base_url = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
        self.model = os.getenv("LLM_MODEL", "gpt-3.5-turbo")
        
        if not self.api_key:
            logger.warning("LLM_API_KEY 未配置")

    async def _call_api(self, messages: list, temperature: float = 0.3, response_format: dict = None) -> Dict[str, Any]:
        """通用 API 调用方法"""
        if not self.api_key:
            return {"error": "API Key missing"}

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature
        }
        if response_format:
            data["response_format"] = response_format
        
        endpoint = f"{self.base_url.rstrip('/')}/chat/completions"
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(endpoint, headers=headers, json=data, timeout=60) as response:
                    if response.status == 200:
                        result = await response.json()
                        content = result['choices'][0]['message']['content'].strip()
                        
                        # 如果请求 JSON 格式，尝试解析
                        if response_format and response_format.get("type") == "json_object":
                            try:
                                clean_json = re.sub(r'^```json\s*|\s*```$', '', content, flags=re.MULTILINE | re.DOTALL)
                                return json.loads(clean_json)
                            except json.JSONDecodeError:
                                logger.error(f"JSON 解析失败: {content[:100]}...")
                                return {"error": "JSON parse error", "raw": content}
                        
                        return {"content": content}
                    else:
                        error_text = await response.text()
                        logger.error(f"LLM 请求失败: {response.status} - {error_text}")
                        return {"error": f"API Error {response.status}", "details": error_text}
            except Exception as e:
                logger.error(f"LLM 异步调用异常: {e}")
                return {"error": f"Exception: {str(e)}"}

    async def analyze_article(self, content: str, prompt_template: str) -> Dict[str, Any]:
        """异步分析文章 (JSON)"""
        default_result = {
            "summary": "AI 分析失败",
            "score": {"total": 0},
            "category": "SKIM",
            "reason": "调用失败"
        }

        if not content:
            default_result["summary"] = "无内容"
            return default_result

        truncated_content = content[:12000]
        prompt = prompt_template.replace("{{article_content}}", truncated_content)
        
        result = await self._call_api(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            response_format={"type": "json_object"}
        )
        
        if "error" in result:
            default_result["reason"] = result["error"]
            return default_result
            
        return result

    async def rank_articles(self, candidates_json: str, prompt_template: str) -> Dict[str, Any]:
        """异步主编决选 (JSON)"""
        prompt = prompt_template.replace("{{candidates_json}}", candidates_json)
        
        result = await self._call_api(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            response_format={"type": "json_object"}
        )
        
        if "error" in result:
            return {"top_4": [], "others_action": "RECOMMENDED"}
            
        return result

    async def summarize_article(self, content: str, prompt_template: str) -> str:
        """兼容旧接口"""
        result = await self.analyze_article(content, prompt_template)
        return result.get("summary", "无法获取总结")

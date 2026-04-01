
import sys
import os
import json
import logging

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.tikhub_client import TikhubClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def inspect_stats():
    client = TikhubClient()
    
    # Test with Liu Xiao Pai
    gh_id = "gh_d56f73c13a02"
    
    print(f"Fetching article list for {gh_id}...")
    article_list_resp = client.get_article_list(gh_id)
    
    if not article_list_resp or 'data' not in article_list_resp or 'list' not in article_list_resp['data']:
        print("Failed to get article list or invalid format.")
        return

    articles = article_list_resp['data']['list']
    if not articles:
        print("No articles found.")
        return

    first_article = articles[0]
    print("\n=== First Article in List (Keys) ===")
    print(first_article.keys())
    print("\n=== First Article Data Sample ===")
    print(json.dumps(first_article, ensure_ascii=False, indent=2)[:500])
    
import requests

def test_endpoint(client, endpoint, params, method="GET"):
    url = f"{client.base_url}{endpoint}"
    headers = {
        "Authorization": f"Bearer {client.api_key}",
        "Content-Type": "application/json"
    }
    print(f"\nTesting endpoint: {endpoint} [{method}]")
    try:
        if method == "POST":
            response = requests.post(url, headers=headers, json=params, timeout=10)
        else:
            response = requests.get(url, headers=headers, params=params, timeout=10)
            
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"Response Keys: {list(data.keys())}")
                if 'data' in data:
                    print(f"Data Keys: {list(data['data'].keys())}")
                    # Print first 200 chars of data json
                    print(f"Data Sample: {json.dumps(data['data'], ensure_ascii=False)[:500]}")
                else:
                    print(f"Response: {json.dumps(data, ensure_ascii=False)[:200]}")
            except:
                print(f"Response Text: {response.text[:200]}")
        else:
             print(f"Response: {response.text[:200]}")
    except Exception as e:
        print(f"Error: {e}")

def inspect_stats():
    client = TikhubClient()
    
    # Test with Liu Xiao Pai
    gh_id = "gh_d56f73c13a02"
    
    print(f"Fetching article list for {gh_id}...")
    article_list_resp = client.get_article_list(gh_id)
    
    if not article_list_resp or 'data' not in article_list_resp or 'list' not in article_list_resp['data']:
        print("Failed to get article list.")
        return

    articles = article_list_resp['data']['list']
    first_article = articles[0]
    article_url = first_article.get('ContentUrl') or first_article.get('url')
    
    if not article_url:
        print("No article URL found.")
        return

    cleaned_url = client._clean_wx_url(article_url)
    print(f"Target URL: {cleaned_url}")
    
    # 1. Inspect Comment List Data
    test_endpoint(client, "/api/v1/wechat_mp/web/fetch_mp_article_comment_list", {"url": cleaned_url})
    
    # 2. Try read count with dummy comment_id
    test_endpoint(client, "/api/v1/wechat_mp/web/fetch_mp_article_read_count", {"url": cleaned_url, "comment_id": "0"})

    # 3. Try POST for read/like
    test_endpoint(client, "/api/v1/wechat_mp/web/fetch_mp_article_read_like_num", {"url": cleaned_url}, method="POST")

if __name__ == "__main__":
    inspect_stats()

import sys
import os
import json

# 添加项目根目录到 sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.tikhub_client import TikhubClient

def main():
    print("=== Phase 2 验收: Tikhub API 客户端 ===")
    print("说明: 本脚本用于验证 Tikhub API 连接配置。")
    print("-" * 50)

    # 1. 检查 Key (优先检查 .env)
    api_key = None
    
    # Check .env
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
    if os.path.exists(env_path):
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip().startswith('TIKHUB_API_KEY='):
                    api_key = line.split('=', 1)[1].strip()
                    print(f"✅ [.env] 发现 API Key ({api_key[:5]}...)")
                    break
    
    # Check config/settings.json if not found in .env
    if not api_key:
        config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'settings.json')
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                api_key = config.get('tikhub_api_key')
                if api_key and api_key != "YOUR_API_KEY_HERE":
                    print(f"✅ [settings.json] 发现 API Key ({api_key[:5]}...)")

    if not api_key or api_key == "YOUR_API_KEY_HERE":
        print("❌ [错误] 未找到有效的 API Key")
        print("请在 .env 文件或 config/settings.json 中配置 TIKHUB_API_KEY")
        return
    
    # 2. 初始化客户端
    client = TikhubClient()
    
    # 3. 尝试一次真实的连通性测试
    print("✅ [初始化] TikhubClient 初始化成功")
    print("-" * 50)
    print("⏳ [测试] 正在尝试调用 API 获取文章列表...")
    print("   测试目标 GHID: gh_3923025946c5")
    
    result = client.get_article_list(gh_id="gh_3923025946c5")
    
    if result:
        print("✅ [成功] API 调用成功！")
        print(f"   返回数据示例: {json.dumps(result, ensure_ascii=False, indent=2)[:500]}...")
    else:
        print("❌ [失败] API 调用失败 (可能是 404 Not Found 或 鉴权失败)")
        print("   请检查 src/tikhub_client.py 中的 endpoint 路径是否正确。")
        print("   参考文档: https://docs.tikhub.io/268383329e0")

    print("-" * 50)
    print("下一步操作:")
    if result:
         print("API 连接已打通，可以开始 Phase 3 (主逻辑开发)。")
    else:
         print("请根据上述错误信息修正 API 路径。")

if __name__ == "__main__":
    main()

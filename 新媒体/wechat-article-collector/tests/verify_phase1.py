import sys
import os

# 添加项目根目录到 sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.id_extractor import extract_ghid_from_url

def main():
    print("=== Phase 1 验收: ID 提取器 ===")
    print("说明: 本脚本用于验证是否能通过文章链接自动获取公众号 ID (gh_id)。")
    print("-" * 50)
    
    # 默认使用用户之前提供的链接
    default_url = "https://mp.weixin.qq.com/s/ygLMQfWB_wAeq8ViQOMVRA"
    
    print(f"默认测试链接: {default_url}")
    user_input = input("请输入链接 (直接回车使用默认值): ").strip()
    target_url = user_input if user_input else default_url
    
    print(f"\n正在请求并分析页面: {target_url}")
    ghid = extract_ghid_from_url(target_url)
    
    print("-" * 50)
    if ghid:
        print(f"✅ [验证通过] 成功提取 GHID")
        print(f"ID: {ghid}")
    else:
        print(f"❌ [验证失败] 未能提取到 ID")

if __name__ == "__main__":
    main()

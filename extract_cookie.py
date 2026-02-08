#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
12306 Cookie 提取工具 - 浏览器自动化版

使用方法：
    python3 extract_cookie.py

功能：
    1. 自动打开浏览器
    2. 等待用户扫码登录
    3. 自动提取Cookie
    4. 保存到文件

需要安装：
    pip3 install selenium webdriver-manager

作者: OpenClaw
版本: v2.1
"""

import os
import sys
import json
import time
from pathlib import Path

# 尝试导入selenium
SELENIUM_AVAILABLE = False
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from webdriver_manager.chrome import ChromeDriverManager
    SELENIUM_AVAILABLE = True
except ImportError:
    print("⚠️ selenium 未安装")
    print("   安装: pip3 install selenium webdriver-manager")


def extract_with_selenium():
    """使用 Selenium 提取 Cookie"""
    
    print("\n📦 初始化浏览器...")
    
    # Chrome 选项
    chrome_options = Options()
    chrome_options.add_argument('--headless')  # 无头模式
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    
    try:
        # 启动浏览器
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        print("🌐 打开 12306...")
        driver.get('https://12306.cn')
        
        print("\n" + "="*60)
        print("📋 请手动操作:")
        print("="*60)
        print("1. 点击页面上的 '登录' 按钮")
        print("2. 使用手机APP扫码登录")
        print("3. 等待页面显示已登录")
        print("4. 按 Enter 继续提取Cookie...")
        print("="*60)
        
        input("\n👇 登录完成后按 Enter 继续...")
        
        # 提取Cookie
        cookies = driver.get_cookies()
        
        # 关闭浏览器
        driver.quit()
        
        # 转换为字典
        cookie_dict = {}
        for cookie in cookies:
            cookie_dict[cookie['name']] = cookie['value']
        
        # 保存Cookie
        cookie_str = '; '.join([f"{k}={v}" for k, v in cookie_dict.items()])
        
        print("\n" + "="*60)
        print("🎉 Cookie 提取成功!")
        print("="*60)
        print(f"\n📋 Cookie:\n")
        print(cookie_str)
        
        # 保存到文件
        os.makedirs('data', exist_ok=True)
        with open('data/cookies.json', 'w') as f:
            json.dump(cookie_dict, f, indent=2)
        
        print(f"\n✅ Cookie已保存到: data/cookies.json")
        print("\n🚀 运行监控:")
        print("   python3 main.py --monitor")
        
        return True
        
    except Exception as e:
        print(f"❌ 错误: {e}")
        return False


def extract_manual():
    """手动提取指南"""
    print("\n📋 手动提取 Cookie 指南:")
    print("="*60)
    print("""
1. 打开 Chrome 或 Edge 浏览器
2. 访问 https://12306.cn
3. 登录 (扫码登录)
4. 按 F12 打开开发者工具
5. 切换到 Application 标签
6. 左侧找到 Cookies → https://12306.cn
7. 右侧列出所有 Cookie
8. 复制以下 Cookie (必须):
   - RAIL_EXPIRATION
   - RAIL_DEVICEID
   - JSESSIONID
   - _uab_guid
9. 保存到 data/cookies.json

格式:
{
  "RAIL_EXPIRATION": "xxx",
  "RAIL_DEVICEID": "xxx",
  "JSESSIONID": "xxx",
  "_uab_guid": "xxx"
}
""")
    print("="*60)


def main():
    """主入口"""
    print("\n" + "="*60)
    print("12306 Cookie 提取工具")
    print("="*60)
    
    if SELENIUM_AVAILABLE:
        print("\n选择提取方式:")
        print("1. 自动浏览器提取 (推荐)")
        print("2. 手动提取指南")
        
        choice = input("\n请选择 [1/2]: ").strip()
        
        if choice == '1':
            extract_with_selenium()
        else:
            extract_manual()
    else:
        extract_manual()


if __name__ == '__main__':
    main()

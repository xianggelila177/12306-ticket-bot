#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
12306 登录工具 - 简单版

使用方法：
    python3 simple_login.py

功能：
1. 获取验证码图片
2. 手动输入验证码答案
3. 输入用户名密码
4. 保存Cookie

作者: OpenClaw
版本: v2.1
"""

import os
import sys
import json
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from core.auth_manager import AuthManager
from utils.qrcode import QRCodeUtil


def main():
    """主入口"""
    print("\n" + "="*60)
    print("12306 登录工具 v2.1")
    print("="*60)
    
    auth = AuthManager()
    
    # 1. 获取验证码
    print("\n📷 步骤1：获取验证码")
    print("-"*40)
    
    success, image_data = auth.get_captcha_image()
    
    if not success:
        print("❌ 获取验证码失败")
        return
    
    # 保存验证码图片
    captcha_file = "captcha.jpg"
    with open(captcha_file, 'wb') as f:
        f.write(image_data)
    
    print(f"✅ 验证码已保存到: {captcha_file}")
    print("📂 请查看图片，输入验证码答案")
    
    # 尝试显示图片
    try:
        from PIL import Image
        img = Image.open(captcha_file)
        print(f"   图片尺寸: {img.size[0]}x{img.size[1]} 像素")
        img.show()
    except ImportError:
        print("💡 提示: pip install pillow 可自动显示图片")
    except Exception as e:
        print(f"   无法自动显示图片: {e}")
    
    print("\n📝 验证码说明:")
    print("   12306验证码是图片点选，请按顺序点击")
    print("   示例答案格式: 105,45|220,140")
    print("   (两个坐标用|分隔，x,y格式)")
    
    # 2. 输入验证码答案
    print("\n🔐 步骤2：输入验证码")
    print("-"*40)
    
    max_attempts = 3
    captcha_ok = False
    
    for attempt in range(max_attempts):
        answer = input(f"   请输入验证码 [{attempt+1}/{max_attempts}]: ").strip()
        
        if not answer:
            print("   ❌ 答案不能为空")
            continue
        
        # 校验验证码
        if auth.check_captcha(answer):
            print("   ✅ 验证码校验成功")
            captcha_ok = True
            break
        else:
            print("   ❌ 验证码错误，请重新输入")
            
            # 重新获取验证码
            if attempt < max_attempts - 1:
                print("   🔄 重新获取验证码...")
                success, image_data = auth.get_captcha_image()
                if success:
                    with open(captcha_file, 'wb') as f:
                        f.write(image_data)
                    try:
                        img = Image.open(captcha_file)
                        img.show()
                    except:
                        pass
                else:
                    print("   ❌ 重新获取验证码失败")
    
    if not captcha_ok:
        print("❌ 验证码验证失败次数过多，退出")
        return
    
    # 3. 输入账号信息
    print("\n👤 步骤3：输入账号信息")
    print("-"*40)
    
    username = input("   用户名: ").strip()
    password = input("   密码: ").strip()
    
    if not username or not password:
        print("❌ 用户名或密码不能为空")
        return
    
    # 4. 登录
    print("\n🔓 步骤4：登录中...")
    print("-"*40)
    
    success, message = auth.login(username, password, answer)
    
    if success:
        print("   ✅ 登录成功！")
        
        # 获取Cookie
        cookies = auth.get_cookies()
        
        # 保存Cookie
        cookie_str = '; '.join([f"{k}={v}" for k, v in cookies.items()])
        
        print("\n" + "="*60)
        print("🎉 登录成功！")
        print("="*60)
        
        print(f"\n📋 Cookie (已保存到 data/cookies.json):\n")
        print(cookie_str)
        
        # 保存到文件
        os.makedirs('data', exist_ok=True)
        with open('data/cookies.json', 'w') as f:
            json.dump(cookies, f, indent=2)
        print(f"\n✅ Cookie已保存到: data/cookies.json")
        
        print("\n🚀 现在可以运行主程序:")
        print("   python3 main.py --monitor")
        
    else:
        print(f"   ❌ 登录失败: {message}")


if __name__ == '__main__':
    main()

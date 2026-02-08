#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
12306 抢票 Agent - 打包工具

功能：
- 将项目打包为可下载的压缩包
- 自动排除不需要的文件
- 生成 SHA256 校验和

使用方法：
    python3 package.py

输出：
    12306-ticket-bot-v2.0.zip
    12306-ticket-bot-v2.0.sha256
"""

import os
import sys
import zipfile
import hashlib
import shutil
from pathlib import Path
from datetime import datetime

# 项目配置
PROJECT_DIR = Path(__file__).parent
OUTPUT_DIR = PROJECT_DIR / "releases"
PROJECT_NAME = "12306-ticket-bot"
VERSION = "v2.0"

# 排除列表
EXCLUDE_DIRS = [
    "__pycache__",
    ".git",
    ".idea",
    "logs",
    ".vscode",
    "node_modules",
    "venv",
    ".venv",
    "env",
    ".env",
    "data",
    "*.pyc",
    "*.pyo",
]

EXCLUDE_FILES = [
    "*.log",
    "*.pid",
    "config.yaml",  # 排除用户配置
    "cookies.json.encrypted",  # 排除加密 Cookie
]


def get_file_sha256(file_path: Path) -> str:
    """计算文件 SHA256"""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def should_exclude(path: Path, is_dir: bool = False) -> bool:
    """判断是否应该排除"""
    name = path.name
    
    # 排除目录
    if is_dir:
        for excl in EXCLUDE_DIRS:
            if name == excl or name.startswith(excl.replace("*", "")):
                return True
    
    # 排除文件
    if not is_dir:
        for excl in EXCLUDE_FILES:
            if name == excl or name.endswith(excl.replace("*", "")):
                return True
    
    return False


def create_package():
    """创建压缩包"""
    print(f"\n📦 正在打包 {PROJECT_NAME} {VERSION}...\n")
    
    # 创建输出目录
    OUTPUT_DIR.mkdir(exist_ok=True)
    
    # 压缩包名称
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_name = f"{PROJECT_NAME}-{VERSION}.zip"
    zip_path = OUTPUT_DIR / zip_name
    
    # 如果已存在，添加时间戳
    if zip_path.exists():
        zip_path = OUTPUT_DIR / f"{PROJECT_NAME}-{VERSION}_{timestamp}.zip"
    
    # 创建压缩包
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        file_count = 0
        dir_count = 0
        
        for root, dirs, files in os.walk(PROJECT_DIR):
            # 修改目录列表（原地修改）
            dirs[:] = [d for d in dirs if not should_exclude(Path(d), is_dir=True)]
            
            # 计算相对路径
            rel_root = Path(root).relative_to(PROJECT_DIR.parent)
            
            # 添加目录
            if rel_root != Path(".") and rel_root.parts[0] == PROJECT_NAME:
                dir_count += 1
                zipf.write(root, arcname=str(rel_root))
            
            # 添加文件
            for file in files:
                if should_exclude(Path(file)):
                    continue
                
                file_path = Path(root) / file
                rel_path = file_path.relative_to(PROJECT_DIR.parent)
                
                # 只添加项目内的文件
                if rel_path.parts[0] == PROJECT_NAME:
                    zipf.write(file_path, arcname=str(rel_path))
                    file_count += 1
    
    # 计算文件大小
    size_mb = zip_path.stat().st_size / (1024 * 1024)
    
    print(f"✅ 打包完成!")
    print(f"   📁 文件: {zip_path.name}")
    print(f"   📦 大小: {size_mb:.2f} MB")
    print(f"   📄 文件: {file_count} 个")
    print(f"   📁 目录: {dir_count} 个")
    
    # 生成校验和
    sha256_path = zip_path.with_suffix(".sha256")
    sha256 = get_file_sha256(zip_path)
    
    with open(sha256_path, "w") as f:
        f.write(f"{sha256}  {zip_path.name}\n")
    
    print(f"   🔐 校验: {sha256_path.name}")
    print(f"   SHA256: {sha256[:16]}...")
    
    return zip_path


def verify_package(zip_path: Path):
    """验证压缩包"""
    print(f"\n🔍 正在验证 {zip_path.name}...\n")
    
    if not zip_path.exists():
        print(f"❌ 文件不存在: {zip_path}")
        return False
    
    # 计算校验和
    sha256 = get_file_sha256(zip_path)
    
    # 读取预期校验和
    sha256_path = zip_path.with_suffix(".sha256")
    if sha256_path.exists():
        with open(sha256_path, "r") as f:
            expected = f.read().strip().split()[0]
        
        if sha256 == expected:
            print(f"✅ 校验通过!")
            print(f"   SHA256: {sha256}")
            return True
        else:
            print(f"❌ 校验失败!")
            print(f"   预期: {expected}")
            print(f"   实际: {sha256}")
            return False
    else:
        print(f"⚠️ 未找到校验文件: {sha256_path}")
        print(f"   SHA256: {sha256}")
        return True


def list_contents():
    """列出压缩包内容"""
    print(f"\n📂 {PROJECT_NAME} {VERSION} 内容:\n")
    
    zip_name = f"{PROJECT_NAME}-{VERSION}.zip"
    zip_path = OUTPUT_DIR / zip_name
    
    if not zip_path.exists():
        print(f"❌ 文件不存在: {zip_path}")
        return
    
    with zipfile.ZipFile(zip_path, "r") as zipf:
        for info in zipf.infolist():
            if info.is_dir():
                print(f"   📁 {info.filename}/")
            else:
                size = info.file_size / 1024
                print(f"   📄 {info.filename:<40} {size:>8.1f} KB")


def cleanup():
    """清理旧版本"""
    print(f"\n🧹 清理旧版本...\n")
    
    if not OUTPUT_DIR.exists():
        print("   没有旧版本")
        return
    
    keep_count = 0
    remove_count = 0
    
    for file in OUTPUT_DIR.glob(f"{PROJECT_NAME}-*.zip"):
        # 只保留最新版本
        if not str(file).endswith(f"{VERSION}.zip"):
            file.unlink()
            print(f"   🗑️  {file.name}")
            remove_count += 1
        else:
            print(f"   ✅ {file.name}")
            keep_count += 1
    
    print(f"\n   保留: {keep_count} 个")
    print(f"   删除: {remove_count} 个")


def main():
    """主入口"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="12306 抢票 Agent 打包工具"
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="验证已打包的文件"
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="列出包内容"
    )
    parser.add_argument(
        "--cleanup",
        action="store_true",
        help="清理旧版本"
    )
    
    args = parser.parse_args()
    
    print(f"\n📦 {PROJECT_NAME} {VERSION} Packager\n")
    
    if args.verify:
        zip_name = f"{PROJECT_NAME}-{VERSION}.zip"
        verify_package(OUTPUT_DIR / zip_name)
    elif args.list:
        list_contents()
    elif args.cleanup:
        cleanup()
    else:
        cleanup()
        create_package()
        verify_package(OUTPUT_DIR / f"{PROJECT_NAME}-{VERSION}.zip")
        
        print(f"\n" + "=" * 50)
        print(f"🎉 打包完成!")
        print(f"\n📥 下载地址:")
        print(f"   {OUTPUT_DIR}/{PROJECT_NAME}-{VERSION}.zip")
        print(f"\n🔐 校验:")
        print(f"   sha256sum {PROJECT_NAME}-{VERSION}.zip")
        print(f"\n📖 使用说明:")
        print(f"   1. 下载压缩包")
        print(f"   2. 解压到本地")
        print(f"   3. 运行 ./install.sh 安装")
        print(f"   " + "=" * 50 + "\n")


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""
12306 Ticket Bot - 配置管理
加密配置管理器

功能：
- 配置文件加载和保存
- Cookie 加密存储
- 安全密钥管理

作者: OpenClaw
版本: v2.0
"""

import os
import json
import yaml
from pathlib import Path
from typing import Any, Dict, Optional
from cryptography.fernet import Fernet
from base64 import b64encode, b64decode


class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_path: str = "config.yaml"):
        """
        初始化配置管理器
        
        Args:
            config_path: 配置文件路径
        """
        self.config_path = Path(config_path)
        self.config: Dict[str, Any] = {}
        self._load_config()
    
    def _load_config(self):
        """加载配置文件"""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    self.config = yaml.safe_load(f) or {}
                print(f"配置文件加载成功: {self.config_path}")
            else:
                print(f"配置文件不存在: {self.config_path}")
                self.config = {}
        except Exception as e:
            print(f"加载配置文件失败: {e}")
            self.config = {}
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置项
        
        Args:
            key: 配置键（支持点号分隔，如 'accounts.0.name'）
            default: 默认值
            
        Returns:
            配置值
        """
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
            
            if value is None:
                return default
        
        # 处理环境变量
        if isinstance(value, str) and value.startswith('${') and value.endswith('}'):
            env_key = value[2:-1]
            return os.environ.get(env_key, default)
        
        return value
    
    def get_all(self) -> Dict[str, Any]:
        """获取全部配置"""
        return self.config
    
    def update(self, key: str, value: Any):
        """
        更新配置项
        
        Args:
            key: 配置键
            value: 新值
        """
        keys = key.split('.')
        config = self.config
        
        # 遍历到倒数第二层
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        # 更新值
        config[keys[-1]] = value
    
    def update_account_cookie(self, account_index: int, encrypted_cookies: str):
        """
        更新账户 Cookie
        
        Args:
            account_index: 账户索引
            encrypted_cookies: 加密后的 Cookie
        """
        key = f'accounts.{account_index}.encrypted_cookies'
        self.update(key, encrypted_cookies)
        self.save_config()
    
    def save_config(self, path: Optional[str] = None):
        """
        保存配置文件
        
        Args:
            path: 保存路径（默认覆盖原文件）
        """
        save_path = Path(path) if path else self.config_path
        
        try:
            save_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(save_path, 'w', encoding='utf-8') as f:
                yaml.dump(self.config, f, allow_unicode=True, default_flow_style=False)
            
            print(f"配置已保存: {save_path}")
        except Exception as e:
            print(f"保存配置失败: {e}")
    
    def reload(self):
        """重新加载配置文件"""
        self._load_config()


class SecureConfigManager:
    """安全配置管理器 - Cookie 加密"""
    
    def __init__(self, key_path: str = "data/secret.key"):
        """
        初始化安全配置管理器
        
        Args:
            key_path: 密钥文件路径
        """
        self.key_path = Path(key_path)
        self.key_path.parent.mkdir(parents=True, exist_ok=True)
        self.fernet = self._init_fernet()
    
    def _init_fernet(self) -> Fernet:
        """初始化 Fernet 加密器"""
        try:
            if self.key_path.exists():
                with open(self.key_path, 'rb') as f:
                    key = f.read()
            else:
                # 生成新密钥
                key = Fernet.generate_key()
                with open(self.key_path, 'wb') as f:
                    f.write(key)
            
            return Fernet(key)
            
        except Exception as e:
            print(f"初始化加密器失败: {e}")
            # 降级处理：返回 None
            return None
    
    def encrypt_cookies(self, cookies: dict) -> str:
        """
        加密 Cookie
        
        Args:
            cookies: Cookie 字典
            
        Returns:
            加密后的字符串
        """
        if not self.fernet:
            # 如果没有加密器，返回 JSON 格式
            return json.dumps(cookies, ensure_ascii=False)
        
        try:
            cookie_str = json.dumps(cookies, ensure_ascii=False)
            encrypted = self.fernet.encrypt(cookie_str.encode('utf-8'))
            return b64encode(encrypted).decode('ascii')
        except Exception as e:
            print(f"加密 Cookie 失败: {e}")
            return json.dumps(cookies, ensure_ascii=False)
    
    def decrypt_cookies(self, encrypted_data: dict) -> Optional[dict]:
        """
        解密 Cookie
        
        Args:
            encrypted_data: 加密的数据（包含 'cookies' 键）
            
        Returns:
            解密后的 Cookie 字典，失败返回 None
        """
        encrypted_str = encrypted_data.get('cookies', '')
        
        if not encrypted_str:
            return None
        
        # 尝试 Base64 解码
        try:
            encrypted_bytes = b64decode(encrypted_str.encode('ascii'))
        except Exception:
            # 如果不是 Base64，尝试直接解析为 JSON
            try:
                return json.loads(encrypted_str)
            except Exception:
                return None
        
        # 尝试 Fernet 解密
        if self.fernet:
            try:
                decrypted = self.fernet.decrypt(encrypted_bytes)
                return json.loads(decrypted.decode('utf-8'))
            except Exception as e:
                print(f"Fernet 解密失败: {e}")
        
        return None
    
    def encrypt_value(self, value: str) -> str:
        """
        加密任意字符串
        
        Args:
            value: 要加密的字符串
            
        Returns:
            加密后的字符串
        """
        if not self.fernet:
            return value
        
        try:
            encrypted = self.fernet.encrypt(value.encode('utf-8'))
            return b64encode(encrypted).decode('ascii')
        except Exception as e:
            print(f"加密失败: {e}")
            return value
    
    def decrypt_value(self, encrypted_value: str) -> str:
        """
        解密字符串
        
        Args:
            encrypted_value: 加密的字符串
            
        Returns:
            解密后的字符串
        """
        if not self.fernet:
            return encrypted_value
        
        try:
            encrypted_bytes = b64decode(encrypted_value.encode('ascii'))
            decrypted = self.fernet.decrypt(encrypted_bytes)
            return decrypted.decode('utf-8')
        except Exception:
            return encrypted_value


if __name__ == '__main__':
    # 测试代码
    manager = SecureConfigManager()
    
    # 测试加密
    test_cookies = {
        'cookies': 'JSESSIONID=xxx; _uab_collina=xxx;',
        'user_name': 'test_user'
    }
    
    encrypted = manager.encrypt_cookies(test_cookies)
    print(f"加密后: {encrypted[:50]}...")
    
    # 测试解密
    decrypted = manager.decrypt_cookies({'cookies': encrypted})
    print(f"解密后: {decrypted}")

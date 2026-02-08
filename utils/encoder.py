# -*- coding: utf-8 -*-
"""
12306 Ticket Bot - 编码工具
编码解码工具

功能：
- URL 编码解码
- Base64 编码解码
- 汉字编码处理

作者: OpenClaw
版本: v2.0
"""

import json
import base64
import urllib.parse
from typing import Any, Dict, List


class EncoderUtil:
    """编码工具类"""
    
    @staticmethod
    def url_encode(text: str) -> str:
        """
        URL 编码
        
        Args:
            text: 原始文本
            
        Returns:
            编码后的文本
        """
        return urllib.parse.quote(text)
    
    @staticmethod
    def url_decode(text: str) -> str:
        """
        URL 解码
        
        Args:
            text: 编码后的文本
            
        Returns:
            原始文本
        """
        return urllib.parse.unquote(text)
    
    @staticmethod
    def base64_encode(text: str) -> str:
        """
        Base64 编码
        
        Args:
            text: 原始文本
            
        Returns:
            编码后的文本
        """
        return base64.b64encode(text.encode('utf-8')).decode('ascii')
    
    @staticmethod
    def base64_decode(text: str) -> str:
        """
        Base64 解码
        
        Args:
            text: 编码后的文本
            
        Returns:
            原始文本
        """
        try:
            return base64.b64decode(text.encode('ascii')).decode('utf-8')
        except Exception:
            return ""
    
    @staticmethod
    def json_dumps(data: Any, ensure_ascii: bool = False) -> str:
        """
        JSON 序列化
        
        Args:
            data: 数据
            ensure_ascii: 是否保留 ASCII
            
        Returns:
            JSON 字符串
        """
        return json.dumps(data, ensure_ascii=ensure_ascii)
    
    @staticmethod
    def json_loads(text: str) -> Any:
        """
        JSON 反序列化
        
        Args:
            text: JSON 字符串
            
        Returns:
            Python 对象
        """
        try:
            return json.loads(text)
        except Exception:
            return None
    
    @staticmethod
    def json_parse_safe(text: str, default: Any = None) -> Any:
        """
        安全 JSON 解析
        
        Args:
            text: JSON 字符串
            default: 解析失败时的默认值
            
        Returns:
            Python 对象
        """
        try:
            return json.loads(text)
        except Exception:
            return default
    
    @staticmethod
    def encode_dict_values(data: Dict[str, Any], keys: List[str]) -> Dict[str, Any]:
        """
        编码字典中指定键的值
        
        Args:
            data: 字典数据
            keys: 需要编码的键列表
            
        Returns:
            编码后的字典
        """
        result = data.copy()
        
        for key in keys:
            if key in result and isinstance(result[key], str):
                result[key] = EncoderUtil.url_encode(result[key])
        
        return result
    
    @staticmethod
    def decode_dict_values(data: Dict[str, Any], keys: List[str]) -> Dict[str, Any]:
        """
        解码字典中指定键的值
        
        Args:
            data: 字典数据
            keys: 需要解码的键列表
            
        Returns:
            解码后的字典
        """
        result = data.copy()
        
        for key in keys:
            if key in result and isinstance(result[key], str):
                try:
                    result[key] = EncoderUtil.url_decode(result[key])
                except Exception:
                    pass
        
        return result


class SecretUtil:
    """加密工具类（简单实现，仅用于演示）"""
    
    @staticmethod
    def mask_sensitive(text: str, visible_chars: int = 4) -> str:
        """
        脱敏处理
        
        Args:
            text: 原始文本
            visible_chars: 末尾可见字符数
            
        Returns:
            脱敏后的文本
        """
        if not text or len(text) <= visible_chars:
            return '*' * len(text)
        
        mask_length = len(text) - visible_chars
        return '*' * mask_length + text[-visible_chars:]
    
    @staticmethod
    def mask_cookies(cookies: Dict[str, str]) -> Dict[str, str]:
        """
        Cookie 脱敏
        
        Args:
            cookies: Cookie 字典
            
        Returns:
            脱敏后的 Cookie
        """
        masked = {}
        sensitive_keys = ['token', 'password', 'secret', 'auth', 'JSESSIONID']
        
        for key, value in cookies.items():
            key_lower = key.lower()
            
            if any(sk in key_lower for sk in sensitive_keys):
                masked[key] = SecretUtil.mask_sensitive(value)
            else:
                masked[key] = value
        
        return masked
    
    @staticmethod
    def mask_request_data(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        请求数据脱敏
        
        Args:
            data: 请求数据
            
        Returns:
            脱敏后的数据
        """
        sensitive_fields = ['password', 'token', 'secret', 'cookie', 'auth']
        
        def mask_value(value):
            if isinstance(value, dict):
                return mask_request_data(value)
            elif isinstance(value, str):
                for field in sensitive_fields:
                    if field in value.lower():
                        return SecretUtil.mask_sensitive(value)
            return value
        
        return {k: mask_value(v) for k, v in data.items()}


if __name__ == '__main__':
    # 测试编码工具
    print("=== 编码工具测试 ===")
    
    # URL 编码
    text = "北京 上海"
    encoded = EncoderUtil.url_encode(text)
    decoded = EncoderUtil.url_decode(encoded)
    
    print(f"原文: {text}")
    print(f"编码: {encoded}")
    print(f"解码: {decoded}")
    
    # Base64
    b64 = EncoderUtil.base64_encode(text)
    print(f"Base64: {b64}")
    print(f"Base64解码: {EncoderUtil.base64_decode(b64)}")
    
    # 脱敏
    test_cookies = {
        'JSESSIONID': 'abc123def456ghi789',
        'token': 'my_secret_token',
        'user': 'test_user'
    }
    
    print(f"\n原Cookie: {test_cookies}")
    print(f"脱敏后: {SecretUtil.mask_cookies(test_cookies)}")

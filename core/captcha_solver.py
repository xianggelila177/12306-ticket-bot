# -*- coding: utf-8 -*-
"""
验证码识别模块 - 12306 验证码识别（增强版）
"""

import base64
import time
from io import BytesIO
from typing import Optional, List, Dict, Tuple
from abc import ABC, abstractmethod

import requests
from PIL import Image

from utils.logger import get_logger

logger = get_logger("captcha_solver")


class BaseCaptchaSolver(ABC):
    """验证码识别基类"""
    
    @abstractmethod
    def solve(self, image_data: bytes) -> Tuple[bool, List[str]]:
        """
        识别验证码
        
        Args:
            image_data: 图片二进制数据
        
        Returns:
            Tuple[是否成功, 识别结果列表]
        """
        pass
    
    @abstractmethod
    def verify(self, captcha_key: str, result: List[str]) -> bool:
        """
        验证验证码是否正确
        
        Args:
            captcha_key: 验证码标识
            result: 识别结果
        
        Returns:
            是否验证成功
        """
        pass


class ChaoJiYingSolver(BaseCaptchaSolver):
    """
    超级鹰验证码识别
    
    使用说明：
    1. 在 https://www.chaojiying.com 注册账号
    2. 购买验证码识别服务
    3. 配置用户名、密码和软件 ID
    """
    
    def __init__(self, username: str, password: str, soft_id: str):
        """
        初始化超级鹰识别器
        
        Args:
            username: 超级鹰用户名
            password: 密码
            soft_id: 软件 ID
        """
        self.username = username
        self.password = password
        self.soft_id = soft_id
        self.api_url = "http://upload.chaojiying.net/Upload/Processing.php"
    
    def _get_sign(self) -> str:
        """获取签名（MD5 密码）"""
        import hashlib
        return hashlib.md5(self.password.encode()).hexdigest()
    
    def solve(self, image_data: bytes) -> Tuple[bool, List[str]]:
        """
        使用超级鹰识别验证码
        
        Args:
            image_data: 图片二进制数据
        
        Returns:
            Tuple[是否成功, 坐标/字符列表]
        """
        try:
            # 验证码类型 9004（✅ 修复：新版本 12306 验证码）
            codetype = "9004"
            
            # 编码图片为 base64
            img_base64 = base64.b64encode(image_data).decode('ascii')
            
            # 构建请求
            data = {
                'user': self.username,
                'pass2': self._get_sign(),
                'softid': self.soft_id,
                'codetype': codetype,
                'file_base64': img_base64,
            }
            
            response = requests.post(self.api_url, data=data, timeout=30)
            
            if response.status_code != 200:
                logger.error(f"超级鹰请求失败: {response.status_code}")
                return False, []
            
            result = response.json()
            
            # 超级鹰返回格式: {"err_no": 0, "err_str": "OK", "pic_str": "120,120|60,60", ...}
            if result.get('err_no') == 0:
                pic_str = result.get('pic_str', '')
                # 解析坐标或字符
                coords = self._parse_result(pic_str)
                logger.info(f"验证码识别成功: {coords}")
                return True, coords
            else:
                logger.error(f"超级鹰识别失败: {result.get('err_str')}")
                return False, []
        
        except Exception as e:
            logger.error(f"验证码识别异常: {e}")
            return False, []
    
    def _parse_result(self, pic_str: str) -> List[str]:
        """
        解析识别结果
        
        Args:
            pic_str: 原始结果字符串
        
        Returns:
            解析后的结果列表
        """
        if not pic_str:
            return []
        
        # 坐标格式: "120,120|60,60"
        if '|' in pic_str:
            return [coord.strip() for coord in pic_str.split('|')]
        
        # 字符格式
        return [pic_str.strip()]
    
    def verify(self, captcha_key: str, result: List[str]) -> bool:
        """
        验证验证码（超级鹰不需要二次验证）
        
        Args:
            captcha_key: 验证码标识
            result: 识别结果
        
        Returns:
            始终返回 True（由调用方验证）
        """
        return True
    
    def report_error(self, captcha_key: str):
        """
        报错（反馈给超级鹰）
        
        Args:
            captcha_key: 验证码标识
        """
        try:
            import hashlib
            sign = hashlib.md5(
                (self.username + captcha_key + "123").encode()
            ).hexdigest()
            
            requests.get(
                "http://upload.chaojiying.net/Upload/ReportErr.php",
                params={
                    'user': self.username,
                    'id': captcha_key,
                    'sign': sign,
                },
                timeout=10
            )
            logger.info("已向超级鹰反馈错误")
        except Exception as e:
            logger.warning(f"反馈错误失败: {e}")


class ImagePreprocessor:
    """验证码图片预处理器"""
    
    @staticmethod
    def preprocess(image_data: bytes) -> bytes:
        """
        预处理图片（提升识别率）
        
        Args:
            image_data: 原始图片数据
        
        Returns:
            处理后的图片数据
        """
        try:
            img = Image.open(BytesIO(image_data))
            
            # 转换为 RGB
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
            
            # 调整尺寸（超级鹰推荐尺寸）
            target_size = (300, 200)
            if img.size != target_size:
                img = img.resize(target_size, Image.Resampling.LANCZOS)
            
            # 保存为 JPEG
            output = BytesIO()
            img.save(output, format='JPEG', quality=85)
            return output.getvalue()
        
        except Exception as e:
            logger.error(f"图片预处理失败: {e}")
            return image_data
    
    @staticmethod
    def enhance_contrast(image_data: bytes) -> bytes:
        """
        增强对比度
        
        Args:
            image_data: 原始图片数据
        
        Returns:
            处理后的图片数据
        """
        try:
            img = Image.open(BytesIO(image_data))
            
            # 转换为灰度
            if img.mode != 'L':
                img = img.convert('L')
            
            # 增强对比度
            from PIL import ImageEnhance
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(1.5)
            
            # 保存为 JPEG
            output = BytesIO()
            img.save(output, format='JPEG')
            return output.getvalue()
        
        except Exception as e:
            logger.error(f"图像增强失败: {e}")
            return image_data


class CaptchaSolver:
    """
    验证码识别管理器
    
    功能：
    - 多平台容错
    - 图片预处理
    - 自动重试
    """
    
    # 验证码类型 9004（✅ 修复：新版本）
    CAPTCHA_TYPE = "9004"
    
    def __init__(self, provider: str = None, **kwargs):
        """
        初始化验证码识别器
        
        Args:
            provider: 提供商名称 (chaojiying, custom)
            **kwargs: 提供商配置
        """
        self.provider = provider
        self.solver = self._create_solver(provider, **kwargs)
        self.preprocessor = ImagePreprocessor()
        
        # 重试配置
        self.max_retries = 3
        self.retry_delay = 2
    
    def _create_solver(self, provider: str, **kwargs) -> BaseCaptchaSolver:
        """
        创建验证码识别器
        
        Args:
            provider: 提供商名称
            **kwargs: 配置参数
        
        Returns:
            识别器实例
        """
        if provider == 'chaojiying':
            return ChaoJiYingSolver(
                username=kwargs.get('username', ''),
                password=kwargs.get('password', ''),
                soft_id=kwargs.get('soft_id', '')
            )
        else:
            # 默认使用超级鹰
            return ChaoJiYingSolver(
                username=kwargs.get('username', ''),
                password=kwargs.get('password', ''),
                soft_id=kwargs.get('soft_id', '')
            )
    
    def solve(self, image_data: bytes, max_retries: int = None) -> Tuple[bool, List[str]]:
        """
        识别验证码（带自动重试）
        
        Args:
            image_data: 图片二进制数据
            max_retries: 最大重试次数
        
        Returns:
            Tuple[是否成功, 识别结果]
        """
        if max_retries is None:
            max_retries = self.max_retries
        
        # 图片预处理
        processed_data = self.preprocessor.preprocess(image_data)
        
        for attempt in range(max_retries):
            try:
                success, result = self.solver.solve(processed_data)
                
                if success and result:
                    logger.info(f"验证码识别成功 (尝试 {attempt + 1}/{max_retries})")
                    return True, result
                
                logger.warning(
                    f"验证码识别失败 (尝试 {attempt + 1}/{max_retries}): {result}"
                )
                
                if attempt < max_retries - 1:
                    time.sleep(self.retry_delay)
            
            except Exception as e:
                logger.error(f"验证码识别异常 (尝试 {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(self.retry_delay)
        
        logger.error(f"验证码识别失败，已重试 {max_retries} 次")
        return False, []
    
    def verify(self, captcha_key: str, result: List[str]) -> bool:
        """
        验证验证码
        
        Args:
            captcha_key: 验证码标识
            result: 识别结果
        
        Returns:
            是否验证成功
        """
        return self.solver.verify(captcha_key, result)
    
    def report_error(self, captcha_key: str):
        """报错"""
        if hasattr(self.solver, 'report_error'):
            self.solver.report_error(captcha_key)


def create_captcha_solver(config: Dict) -> CaptchaSolver:
    """
    创建验证码识别器
    
    Args:
        config: 配置信息
    
    Returns:
        CaptchaSolver 实例
    """
    return CaptchaSolver(
        provider=config.get('provider', 'chaojiying'),
        username=config.get('username', ''),
        password=config.get('password', ''),
        soft_id=config.get('soft_id', '')
    )

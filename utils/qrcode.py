# -*- coding: utf-8 -*-
"""
12306 Ticket Bot - 二维码工具
二维码处理工具

功能：
- 生成二维码
- 显示二维码
- 解析二维码

作者: OpenClaw
版本: v2.0
"""

import os
import sys
import base64
import logging
from pathlib import Path
from typing import Optional
from PIL import Image
from io import BytesIO

# 尝试导入 qrcode
try:
    import qrcode
    QRCODE_AVAILABLE = True
except ImportError:
    QRCODE_AVAILABLE = False
    print("警告: qrcode 模块未安装")


class QRCodeUtil:
    """二维码工具类"""
    
    def __init__(self):
        """初始化二维码工具"""
        self.logger = logging.getLogger('12306_bot.qrcode')
    
    def generate(self, data: str, save_path: str = None, 
                 box_size: int = 10, border: int = 2) -> Optional[bytes]:
        """
        生成二维码
        
        Args:
            data: 二维码数据
            save_path: 保存路径
            box_size: 盒子大小
            border: 边框宽度
            
        Returns:
            二维码图片数据
        """
        if not QRCODE_AVAILABLE:
            self.logger.error("qrcode 模块未安装，无法生成二维码")
            return None
        
        try:
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=box_size,
                border=border,
            )
            
            qr.add_data(data)
            qr.make(fit=True)
            
            img = qr.make_image(fill_color="black", back_color="white")
            
            # 转换为 bytes
            buffer = BytesIO()
            img.save(buffer, format='PNG')
            image_data = buffer.getvalue()
            
            # 保存文件
            if save_path:
                save_path = Path(save_path)
                save_path.parent.mkdir(parents=True, exist_ok=True)
                with open(save_path, 'wb') as f:
                    f.write(image_data)
                self.logger.info(f"二维码已保存: {save_path}")
            
            return image_data
            
        except Exception as e:
            self.logger.error(f"生成二维码失败: {e}")
            return None
    
    def generate_base64(self, data: str) -> Optional[str]:
        """
        生成 Base64 编码的二维码
        
        Args:
            data: 二维码数据
            
        Returns:
            Base64 编码的字符串
        """
        image_data = self.generate(data)
        
        if image_data:
            return base64.b64encode(image_data).decode('ascii')
        
        return None
    
    def display_in_terminal(self, image_path: str):
        """
        在终端显示二维码
        
        Args:
            image_path: 图片路径
        """
        try:
            from utils.ansimage import ANSIImage
            
            img = ANSIImage.from_file(image_path)
            img.print(compact=True)
            
        except ImportError:
            # 备用方案
            print(f"请查看二维码图片: {image_path}")
        except Exception as e:
            self.logger.warning(f"终端显示二维码失败: {e}")
            print(f"请查看二维码图片: {image_path}")
    
    def read_from_file(self, image_path: str) -> Optional[str]:
        """
        从文件读取二维码
        
        Args:
            image_path: 图片路径
            
        Returns:
            二维码数据
        """
        try:
            img = Image.open(image_path)
            return self._decode_qr(img)
        except Exception as e:
            self.logger.error(f"读取二维码失败: {e}")
            return None
    
    def read_from_bytes(self, image_data: bytes) -> Optional[str]:
        """
        从字节数据读取二维码
        
        Args:
            image_data: 图片数据
            
        Returns:
            二维码数据
        """
        try:
            img = Image.open(BytesIO(image_data))
            return self._decode_qr(img)
        except Exception as e:
            self.logger.error(f"读取二维码失败: {e}")
            return None
    
    def _decode_qr(self, img: Image.Image) -> Optional[str]:
        """
        解码二维码
        
        Args:
            img: PIL 图片
            
        Returns:
            二维码数据
        """
        try:
            import zbarlight
            
            codes = zbarlight.scan_codes(['qrcode'], img)
            if codes:
                return codes[0].decode('utf-8')
            
        except ImportError:
            self.logger.warning("zbarlight 未安装，无法解码二维码")
        except Exception as e:
            self.logger.error(f"解码二维码失败: {e}")
        
        return None


if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.INFO)
    
    # 测试二维码生成
    qr_util = QRCodeUtil()
    
    print("=== 二维码工具测试 ===")
    
    # 生成测试
    test_url = "https://kyfw.12306.cn/passport/web/auth/qrcode"
    qr_data = qr_util.generate(test_url, "data/qrcode_test.png")
    
    if qr_data:
        print(f"二维码生成成功，大小: {len(qr_data)} 字节")
    else:
        print("二维码生成失败")
    
    # Base64 测试
    b64 = qr_util.generate_base64(test_url)
    if b64:
        print(f"Base64 编码成功，长度: {len(b64)}")

# -*- coding: utf-8 -*-
"""
12306 Ticket Bot - SQLite数据库
数据库管理

功能：
- 存储监控记录
- 存储订单历史
- 数据持久化

作者: OpenClaw
版本: v2.0
"""

import os
import sys
import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List


class Database:
    """数据库管理器"""
    
    def __init__(self, db_path: str = "data/12306_bot.db"):
        """
        初始化数据库
        
        Args:
            db_path: 数据库文件路径
        """
        self.logger = logging.getLogger('12306_bot.database')
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self._init_database()
    
    def _init_database(self):
        """初始化数据库表"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            # 创建监控记录表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS monitor_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    train_code TEXT,
                    from_station TEXT,
                    to_station TEXT,
                    seat_type TEXT,
                    ticket_count TEXT,
                    query_time TEXT,
                    create_time TEXT
                )
            ''')
            
            # 创建订单历史表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS order_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_no TEXT,
                    train_code TEXT,
                    from_station TEXT,
                    to_station TEXT,
                    seat_type TEXT,
                    passenger_name TEXT,
                    status TEXT,
                    create_time TEXT,
                    update_time TEXT
                )
            ''')
            
            # 创建配置表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS configs (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    update_time TEXT
                )
            ''')
            
            conn.commit()
            conn.close()
            
            self.logger.info(f"数据库初始化成功: {self.db_path}")
            
        except Exception as e:
            self.logger.error(f"数据库初始化失败: {e}")
            raise
    
    def add_monitor_record(self, record: Dict):
        """
        添加监控记录
        
        Args:
            record: 记录数据
        """
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO monitor_records 
                (train_code, from_station, to_station, seat_type, ticket_count, query_time, create_time)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                record.get('train_code', ''),
                record.get('from_station', ''),
                record.get('to_station', ''),
                record.get('seat_type', ''),
                record.get('ticket_count', ''),
                record.get('query_time', ''),
                datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            self.logger.error(f"添加监控记录失败: {e}")
    
    def add_order(self, order: Dict):
        """
        添加订单记录
        
        Args:
            order: 订单数据
        """
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO order_history 
                (order_no, train_code, from_station, to_station, seat_type, 
                 passenger_name, status, create_time, update_time)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                order.get('order_no', ''),
                order.get('train_code', ''),
                order.get('from_station', ''),
                order.get('to_station', ''),
                order.get('seat_type', ''),
                order.get('passenger_name', ''),
                order.get('status', 'pending'),
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            self.logger.error(f"添加订单记录失败: {e}")
    
    def update_order_status(self, order_no: str, status: str):
        """
        更新订单状态
        
        Args:
            order_no: 订单号
            status: 新状态
        """
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE order_history 
                SET status = ?, update_time = ?
                WHERE order_no = ?
            ''', (status, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), order_no))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            self.logger.error(f"更新订单状态失败: {e}")
    
    def get_monitor_records(self, limit: int = 100) -> List[Dict]:
        """
        获取监控记录
        
        Args:
            limit: 限制数量
            
        Returns:
            记录列表
        """
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM monitor_records ORDER BY id DESC LIMIT ?', (limit,))
            rows = cursor.fetchall()
            
            conn.close()
            
            records = []
            for row in rows:
                records.append({
                    'id': row[0],
                    'train_code': row[1],
                    'from_station': row[2],
                    'to_station': row[3],
                    'seat_type': row[4],
                    'ticket_count': row[5],
                    'query_time': row[6],
                    'create_time': row[7],
                })
            
            return records
            
        except Exception as e:
            self.logger.error(f"获取监控记录失败: {e}")
            return []
    
    def get_order_history(self, status: str = None, limit: int = 50) -> List[Dict]:
        """
        获取订单历史
        
        Args:
            status: 状态筛选
            limit: 限制数量
            
        Returns:
            订单列表
        """
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            if status:
                cursor.execute(
                    'SELECT * FROM order_history WHERE status = ? ORDER BY id DESC LIMIT ?',
                    (status, limit)
                )
            else:
                cursor.execute('SELECT * FROM order_history ORDER BY id DESC LIMIT ?', (limit,))
            
            rows = cursor.fetchall()
            
            conn.close()
            
            orders = []
            for row in rows:
                orders.append({
                    'id': row[0],
                    'order_no': row[1],
                    'train_code': row[2],
                    'from_station': row[3],
                    'to_station': row[4],
                    'seat_type': row[5],
                    'passenger_name': row[6],
                    'status': row[7],
                    'create_time': row[8],
                    'update_time': row[9],
                })
            
            return orders
            
        except Exception as e:
            self.logger.error(f"获取订单历史失败: {e}")
            return []
    
    def save_config(self, key: str, value: Any):
        """
        保存配置
        
        Args:
            key: 配置键
            value: 配置值
        """
        try:
            if isinstance(value, (dict, list)):
                value = json.dumps(value, ensure_ascii=False)
            
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO configs (key, value, update_time)
                VALUES (?, ?, ?)
            ''', (key, value, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            self.logger.error(f"保存配置失败: {e}")
    
    def load_config(self, key: str, default: Any = None) -> Any:
        """
        加载配置
        
        Args:
            key: 配置键
            default: 默认值
            
        Returns:
            配置值
        """
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            cursor.execute('SELECT value FROM configs WHERE key = ?', (key,))
            row = cursor.fetchone()
            
            conn.close()
            
            if row:
                value = row[0]
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    return value
            
            return default
            
        except Exception as e:
            self.logger.error(f"加载配置失败: {e}")
            return default
    
    def close(self):
        """关闭数据库"""
        # SQLite 不需要显式关闭连接
        self.logger.info("数据库已关闭")


if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.INFO)
    
    # 测试数据库
    db = Database("data/test_12306_bot.db")
    
    print("=== 数据库测试 ===")
    
    # 添加监控记录
    db.add_monitor_record({
        'train_code': 'K349',
        'from_station': '三明北',
        'to_station': '厦门北',
        'seat_type': '硬卧',
        'ticket_count': '5',
        'query_time': '2026-02-08 12:00:00'
    })
    
    # 获取记录
    records = db.get_monitor_records()
    print(f"监控记录数量: {len(records)}")
    
    # 统计
    stats = {
        'total_records': len(records),
        'db_path': str(db.db_path)
    }
    print(f"统计: {stats}")

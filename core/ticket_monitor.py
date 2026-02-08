# -*- coding: utf-8 -*-
"""
余票监控模块 - 余票监控（重构解析版）
"""

import time
import requests
from typing import Optional, Dict, List, Any
from datetime import datetime
from enum import Enum

from utils.logger import get_logger
from utils.encoder import dict_to_json

logger = get_logger("ticket_monitor")


class SeatType(Enum):
    """座位类型"""
    BUSINESS_SEAT = "9"       # 商务座
    FIRST_SEAT = "7"          # 一等座
    SECOND_SEAT = "8"         # 二等座
    ADVANCED_SOFT_SLEEP = "6"  # 高级软卧
    SOFT_SLEEP = "4"          # 软卧
    HARD_SLEEP = "3"          # 硬卧
    SOFT_SEAT = "2"           # 软座
    HARD_SEAT = "1"           # 硬座
    NO_SEAT = "0"             # 无座
    
    @classmethod
    def from_name(cls, name: str) -> str:
        """从名称获取座位代码"""
        mapping = {
            "商务座": "9",
            "一等座": "7",
            "二等座": "8",
            "高级软卧": "6",
            "软卧": "4",
            "硬卧": "3",
            "软座": "2",
            "硬座": "1",
            "无座": "0",
        }
        return mapping.get(name, "")


class TicketMonitor:
    """
    12306 余票监控器
    
    功能：
    - 查询余票信息
    - 监控余票变化
    - 智能过滤和通知
    """
    
    # ✅ 修复：正确的 API URL
    BASE_URL = "https://kyfw.12306.cn"
    
    # 余票查询 API
    QUERY_URL = f"{BASE_URL}/otn/leftTicket/query"
    QUERY_URL_2 = f"{BASE_URL}/otn/leftTicket/queryZ"
    
    def __init__(self, session: requests.Session = None):
        """
        初始化余票监控器
        
        Args:
            session: requests Session 对象
        """
        if session is None:
            self.session = requests.Session()
        else:
            self.session = session
        
        # ✅ 完整的请求头配置
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Referer': 'https://kyfw.12306.cn/otn/leftTicket/init',
            'Origin': 'https://kyfw.12306.cn',
        }
        self.session.headers.update(self.headers)
        
        # 缓存配置
        self.cache = {}
        self.cache_timeout = 10  # 10秒缓存
    
    def query_tickets(
        self,
        from_station: str,
        to_station: str,
        date: str,
        purpose_codes: str = "ADULT"
    ) -> List[Dict[str, Any]]:
        """
        查询余票信息
        
        Args:
            from_station: 出发站代码
            to_station: 到达站代码
            date: 出发日期 (YYYY-MM-DD)
            purpose_codes: 乘客类型 (ADULT=成人)
        
        Returns:
            车次余票列表
        """
        try:
            # 尝试多个 API 端点
            urls = [
                f"{self.QUERY_URL}?leftTicketDTO.train_date={date}&leftTicketDTO.from_station={from_station}&leftTicketDTO.to_station={to_station}&purpose_codes={purpose_codes}",
                f"{self.QUERY_URL_2}?leftTicketDTO.train_date={date}&leftTicketDTO.from_station={from_station}&leftTicketDTO.to_station={to_station}&purpose_codes={purpose_codes}",
            ]
            
            for url in urls:
                try:
                    response = self.session.get(url, timeout=10)
                    
                    if response.status_code != 200:
                        logger.warning(f"API 请求失败: {response.status_code}")
                        continue
                    
                    data = response.json()
                    
                    if data.get('status'):
                        # ✅ 健壮的响应解析（try-except）
                        trains = self._parse_response(data)
                        if trains:
                            logger.info(f"查询成功，获取到 {len(trains)} 个车次")
                            return trains
                    
                    logger.warning(f"API 返回异常: {data}")
                
                except Exception as e:
                    logger.warning(f"查询异常: {e}")
                    continue
            
            return []
        
        except Exception as e:
            logger.error(f"查询余票失败: {e}")
            return []
    
    def _parse_response(self, data: dict) -> List[Dict[str, Any]]:
        """
        ✅ 健壮的响应解析：使用 try-except 处理索引越界
        
        Args:
            data: API 响应数据
        
        Returns:
            解析后的车次列表
        """
        trains = []
        
        try:
            raw_trains = data.get('data', {}).get('result', [])
        except AttributeError:
            # 处理 data 不是字典的情况
            raw_trains = data.get('data', []) if isinstance(data.get('data'), list) else []
        
        # 获取车站映射
        station_map = self._get_station_map(data)
        
        for item in raw_trains:
            try:
                # 安全解析字段
                train_info = self._parse_train_item(item, station_map)
                if train_info:
                    trains.append(train_info)
            
            except (IndexError, TypeError, ValueError) as e:
                logger.debug(f"解析车次失败，跳过: {e}")
                continue
        
        return trains
    
    def _get_station_map(self, data: dict) -> Dict[str, str]:
        """获取车站代码映射"""
        try:
            stations = data.get('data', {}).get('map', {})
            return stations
        except (AttributeError, TypeError):
            return {}
    
    def _parse_train_item(self, item: str, station_map: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """
        解析单个车次信息
        
        Args:
            item: 原始数据字符串
            station_map: 车站映射
        
        Returns:
            车次信息字典
        """
        try:
            fields = item.split('|')
            
            # 动态字段映射（✅ 修复：健壮的索引访问）
            train_info = {
                'train_no': fields[2] if len(fields) > 2 else None,           # 车次编号
                'train_code': fields[3] if len(fields) > 3 else None,         # 车次代码
                'start_station': fields[4] if len(fields) > 4 else None,       # 始发站
                'end_station': fields[5] if len(fields) > 5 else None,        # 终点站
                'from_station': fields[6] if len(fields) > 6 else None,      # 出发站
                'to_station': fields[7] if len(fields) > 7 else None,        # 到达站
                'departure_time': fields[8] if len(fields) > 8 else None,     # 出发时间
                'arrival_time': fields[9] if len(fields) > 9 else None,       # 到达时间
                'duration': fields[10] if len(fields) > 10 else None,         # 历时
                
                # 余票信息
                'business_seat': fields[32] if len(fields) > 32 else None,    # 商务座
                'first_seat': fields[31] if len(fields) > 31 else None,      # 一等座
                'second_seat': fields[30] if len(fields) > 30 else None,     # 二等座
                'advanced_soft_sleep': fields[21] if len(fields) > 21 else None,  # 高级软卧
                'soft_sleep': fields[23] if len(fields) > 23 else None,      # 软卧
                'hard_sleep': fields[28] if len(fields) > 28 else None,       # 硬卧
                'soft_seat': fields[27] if len(fields) > 27 else None,         # 软座
                'hard_seat': fields[29] if len(fields) > 29 else None,        # 硬座
                'no_seat': fields[26] if len(fields) > 26 else None,          # 无座
                
                # 其他信息
                'train_type': fields[35] if len(fields) > 35 else None,      # 车次类型
                'can_web_buy': fields[11] if len(fields) > 11 else None,      # 是否可购买
            }
            
            # 转换车站代码为名称
            train_info['from_station_name'] = station_map.get(train_info['from_station'], train_info['from_station'])
            train_info['to_station_name'] = station_map.get(train_info['to_station'], train_info['to_station'])
            
            # 解析余票数量
            train_info['available_seats'] = self._parse_seat_count(train_info)
            
            return train_info
        
        except Exception as e:
            logger.error(f"解析车次信息异常: {e}")
            return None
    
    def _parse_seat_count(self, train_info: Dict) -> Dict[str, int]:
        """
        解析余票数量
        
        Args:
            train_info: 车次信息
        
        Returns:
            各座位类型的余票数量
        """
        def parse_count(count_str: str) -> int:
            """解析余票数量字符串"""
            if not count_str:
                return 0
            if count_str in ['有', '大量']:
                return 999
            try:
                return int(count_str)
            except (ValueError, TypeError):
                return 0
        
        return {
            'business': parse_count(train_info.get('business_seat')),
            'first': parse_count(train_info.get('first_seat')),
            'second': parse_count(train_info.get('second_seat')),
            'advanced_soft': parse_count(train_info.get('advanced_soft_sleep')),
            'soft_sleep': parse_count(train_info.get('soft_sleep')),
            'hard_sleep': parse_count(train_info.get('hard_sleep')),
            'soft_seat': parse_count(train_info.get('soft_seat')),
            'hard_seat': parse_count(train_info.get('hard_seat')),
            'no_seat': parse_count(train_info.get('no_seat')),
        }
    
    def filter_trains(
        self,
        trains: List[Dict],
        train_codes: List[str] = None,
        seat_types: List[str] = None,
        min_available: int = 1
    ) -> List[Dict]:
        """
        筛选符合条件的车次
        
        Args:
            trains: 原始车次列表
            train_codes: 目标车次代码列表
            seat_types: 目标座位类型列表
            min_available: 最少余票数量
        
        Returns:
            筛选后的车次列表
        """
        if not trains:
            return []
        
        result = []
        
        for train in trains:
            # 筛选车次
            if train_codes:
                if train.get('train_code') not in train_codes:
                    continue
            
            # 筛选座位
            if seat_types:
                has_available = False
                for seat in seat_types:
                    seat_code = SeatType.from_name(seat)
                    if seat_code:
                        count = train['available_seats'].get(seat_code, 0)
                        if count >= min_available:
                            has_available = True
                            break
                
                if not has_available:
                    continue
            
            result.append(train)
        
        return result
    
    def detect_changes(
        self,
        new_trains: List[Dict],
        old_trains: List[Dict] = None
    ) -> Dict[str, Any]:
        """
        ✅ 余票变化检测
        
        Args:
            new_trains: 新查询结果
            old_trains: 旧查询结果（可选）
        
        Returns:
            变化信息
        """
        changes = {
            'new_trains': [],      # 新增有票的车次
            'sold_out': [],        # 售罄的车次
            'changes': [],         # 余票数量变化
        }
        
        if not old_trains:
            # 首次查询
            for train in new_trains:
                for seat_type, count in train['available_seats'].items():
                    if count > 0:
                        changes['new_trains'].append({
                            'train': train['train_code'],
                            'seat_type': seat_type,
                            'count': count,
                        })
                        break
            return changes
        
        # 构建旧数据索引
        old_map = {t['train_code']: t for t in old_trains}
        
        for new_train in new_trains:
            train_code = new_train['train_code']
            new_seats = new_train['available_seats']
            
            if train_code in old_map:
                old_seats = old_map[train_code]['available_seats']
                
                # 检测变化
                for seat_type in new_seats:
                    old_count = old_seats.get(seat_type, 0)
                    new_count = new_seats.get(seat_type, 0)
                    
                    if old_count == 0 and new_count > 0:
                        changes['new_trains'].append({
                            'train': train_code,
                            'seat_type': seat_type,
                            'count': new_count,
                            'previous': 0,
                        })
                    elif old_count > 0 and new_count == 0:
                        changes['sold_out'].append({
                            'train': train_code,
                            'seat_type': seat_type,
                            'previous': old_count,
                        })
                    elif old_count != new_count:
                        changes['changes'].append({
                            'train': train_code,
                            'seat_type': seat_type,
                            'previous': old_count,
                            'current': new_count,
                        })
            else:
                # 新车次
                for seat_type, count in new_seats.items():
                    if count > 0:
                        changes['new_trains'].append({
                            'train': train_code,
                            'seat_type': seat_type,
                            'count': count,
                        })
                        break
        
        return changes
    
    def monitor(
        self,
        from_station: str,
        to_station: str,
        date: str,
        targets: List[Dict],
        interval: int = 5,
        callback=None
    ):
        """
        监控余票
        
        Args:
            from_station: 出发站
            to_station: 到达站
            date: 日期
            targets: 目标配置列表
            interval: 查询间隔（秒）
            callback: 回调函数
        """
        old_trains = None
        
        while True:
            try:
                # 查询余票
                trains = self.query_tickets(from_station, to_station, date)
                
                # 筛选目标车次
                train_codes = [t.get('train_code') for t in targets]
                seat_types = [t.get('seat_type') for t in targets]
                
                filtered = self.filter_trains(
                    trains,
                    train_codes=train_codes,
                    seat_types=seat_types
                )
                
                # 检测变化
                changes = self.detect_changes(filtered, old_trains)
                
                if any(changes.values()):
                    logger.info(f"检测到余票变化: {changes}")
                    
                    if callback:
                        callback(changes, filtered)
                
                old_trains = filtered
                time.sleep(interval)
            
            except KeyboardInterrupt:
                logger.info("监控已停止")
                break
            except Exception as e:
                logger.error(f"监控异常: {e}")
                time.sleep(interval)

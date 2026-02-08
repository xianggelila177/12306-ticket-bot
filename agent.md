# 12306 抢票 Agent

## 1. Agent 概述

**名称**: 12306 Ticket Bot  
**功能**: 自动化监控余票、扫码登录、自动下单、支付提醒  
**适用场景**: 春运、节假日等热门时段抢票

## 2. 核心功能

### 2.1 多账户管理
- 支持多个 12306 账户
- 扫码登录 + Cookie 自动刷新
- 账户状态监控（登录过期检测）

### 2.2 多车次监控
- 用户指定车次列表（K349, K553...）
- 自定义席别优先级（硬卧 > 软卧 > 硬座）
- 多日期、多区间支持

### 2.3 实时监控
- 秒级余票查询（1-2秒间隔）
- 增量检测（仅报告变化）
- 防封禁策略（随机延迟 + 代理轮换）

### 2.4 自动下单
- 检测到票后立即下单
- 自动验证码识别（打码平台）
- 订单确认 + 提交
- 支付前拦截（用户手动支付）

### 2.5 多渠道通知
- PushPlus 微信通知
- 支付提醒（"请在30分钟内支付"）
- 异常告警（登录过期、下单失败）

## 3. 技术架构

```
┌─────────────────────────────────────────────────────────────┐
│                   12306 Ticket Bot                         │
├─────────────────────────────────────────────────────────────┤
│  Core Modules                                               │
│  ├── auth_manager.py     # 扫码登录 + Cookie管理           │
│  ├── captcha_solver.py   # 验证码识别 (打码平台)           │
│  ├── ticket_monitor.py   # 余票监控 (增量检测)             │
│  ├── order_executor.py   # 自动下单流程                    │
│  ├── notification.py     # 多渠道通知                      │
│  ├── config_manager.py   # YAML/JSON 配置管理              │
│  ├── database.py         # SQLite (账户/订单/日志)         │
│  └── proxy_manager.py    # 代理池管理 (可选)              │
├─────────────────────────────────────────────────────────────┤
│  External Services                                         │
│  ├── 12306 API         # 余票查询、下单接口                │
│  ├── 超级鹰打码平台    # 验证码识别                         │
│  ├── PushPlus          # 微信通知                          │
│  └── (可选) 代理池     # 高匿 IP 池                        │
└─────────────────────────────────────────────────────────────┘
```

## 4. 数据结构

### 4.1 配置结构 (config.yaml)

```yaml
# 12306 Ticket Bot 配置

# 账户配置
accounts:
  - name: "主账号"
    status: "active"  # active, inactive, expired
    login_method: "qrcode"  # qrcode, cookie
    qrcode_path: "/tmp/qrcode.png"
    cookies: ""
    token: ""
    last_refresh: "2026-02-08 10:00:00"
    cookies_expire_at: "2026-02-15 10:00:00"

  - name: "备用账号"
    status: "pending"
    # ...

# 监控目标
targets:
  - date: "2026-02-22"
    from_station: "沈阳"
    from_code: "SBT"
    to_station: "佳木斯"
    to_code: "JMB"
    trains:
      - "K349"
      - "K553"
      - "K1393"
      - "K547"
      - "K629"
    seats:
      - "硬卧"
      - "软卧"
      - "硬座"
    priority: 1  # 数字越小优先级越高

# 抢票策略
strategy:
  query_interval: 2  # 查询间隔(秒)
  max_retries: 3     # 下单重试次数
  retry_delay: 5     # 重试间隔(秒)
  random_delay: true  # 是否添加随机延迟
  random_delay_range: [0.5, 2.0]  # 随机延迟范围(秒)

# 验证码配置
captcha:
  provider: "chaojiying"  # chaojiying, datatranslator
  api_url: "http://www.chaojiying.com/api/recognize"
  username: "${CHAOJIYING_USER}"
  password: "${CHAOJIYING_PASS}"
  soft_id: "xxx"
  timeout: 30
  retry_times: 2

# 通知配置
notification:
  pushplus:
    enabled: true
    token: "${PUSHPLUS_TOKEN}"
  sms:
    enabled: false
    # 短信配置 (可选)

# 代理配置 (可选)
proxy:
  enabled: false
  type: "socks5"  # http, https, socks5
  api_url: "http://proxy.api/xxx"

# 日志配置
logging:
  level: "INFO"
  file: "logs/ticket_bot.log"
  max_size: "10MB"
  backup_count: 5
```

### 4.2 数据库结构 (ticket_bot.db)

```sql
-- 账户表
CREATE TABLE accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    status TEXT DEFAULT 'pending',
    login_method TEXT,
    cookies TEXT,
    token TEXT,
    last_refresh DATETIME,
    cookies_expire_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 监控目标表
CREATE TABLE targets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    from_station TEXT,
    from_code TEXT,
    to_station TEXT,
    to_code TEXT,
    trains TEXT,  -- JSON: ["K349", "K553"]
    seats TEXT,   -- JSON: ["硬卧", "软卧"]
    priority INTEGER DEFAULT 0,
    status TEXT DEFAULT 'active',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 订单历史表
CREATE TABLE orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER,
    train_no TEXT,
    date TEXT,
    from_station TEXT,
    to_station TEXT,
    seat_type TEXT,
    status TEXT,  -- pending, submitted, paid, cancelled
    order_no TEXT,
    price REAL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (account_id) REFERENCES accounts(id)
);

-- 余票变更日志
CREATE TABLE ticket_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    train_no TEXT,
    date TEXT,
    seat_type TEXT,
    tickets_left INTEGER,
    change_type TEXT  -- added, removed, unchanged
);

-- 操作日志
CREATE TABLE operation_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    level TEXT,
    module TEXT,
    message TEXT,
    details TEXT
);

-- 索引
CREATE INDEX idx_tickets_monitor ON ticket_logs(train_no, date, seat_type);
CREATE INDEX idx_orders_account ON orders(account_id, status);
CREATE INDEX idx_targets_active ON targets(status, priority);
```

## 5. 核心流程

### 5.1 主流程 (main.py)

```python
def main():
    # 1. 加载配置
    config = load_config("config.yaml")
    
    # 2. 初始化数据库
    init_database()
    
    # 3. 登录账户
    accounts = login_all_accounts(config['accounts'])
    
    # 4. 加载监控目标
    targets = load_targets()
    
    # 5. 启动监控循环
    while True:
        for target in targets:
            if target.status != 'active':
                continue
                
            # 查询余票
            tickets = query_tickets(
                target.date,
                target.from_code,
                target.to_code
            )
            
            # 检测变化
            changes = detect_changes(tickets, target)
            
            if changes:
                for change in changes:
                    if change.has_available_tickets(target):
                        # 有票！尝试下单
                        success = try_order(accounts, change, target)
                        
                        if success:
                            notify_order_success(change)
                        else:
                            notify_order_failed(change)
                    else:
                        # 无票变化，记录日志
                        log_ticket_change(change)
            
            # 随机延迟
            sleep_with_jitter(config['strategy']['query_interval'])
    
    # 6. 清理
    cleanup()
```

### 5.2 扫码登录流程 (auth_manager.py)

```python
class QRCodeLogin:
    """12306 扫码登录管理器"""
    
    LOGIN_URL = "https://passport.12306.cn/passport/web/login"
    QRCODE_URL = "https://passport.12306.cn/passport/web/auth/qrcode"
    CHECK_URL = "https://passport.12306.cn/passport/web/auth/qrcode/check"
    
    def generate_qrcode(self):
        """获取登录二维码"""
        response = requests.get(self.QRCODE_URL)
        qrcode_data = response.json()
        
        # 保存二维码图片
        qrcode_image = base64.b64decode(qrcode_data['image'])
        with open(self.qrcode_path, 'wb') as f:
            f.write(qrcode_image)
        
        return qrcode_data['uuid']
    
    def wait_for_scan(self, uuid):
        """等待用户扫码"""
        while True:
            response = requests.post(
                self.CHECK_URL,
                data={'uuid': uuid}
            )
            result = response.json()
            
            if result['status'] == 1:  # 已扫码待确认
                print("请在手机上确认登录")
            elif result['status'] == 2:  # 已确认
                return result['data']
            elif result['status'] == 3:  # 二维码过期
                raise QRCodeExpired()
            elif result['status'] == 4:  # 等待扫码
                pass
            else:
                raise LoginFailed(result['message'])
            
            sleep(2)
    
    def get_tokens(self, login_data):
        """获取登录凭证"""
        # 初始化登录
        init_url = "https://passport.12306.cn/passport/web/login/j"
        response = requests.post(
            init_url,
            data={
                'username': login_data['username'],
                'appid': 'otn'
            },
            cookies={
                'REDIRECT_URL': 'https://www.12306.cn/otn/index/init',
                'CURRENT_SUPPORT_TLS': 'TLS1.2'
            }
        )
        
        # 获取关键 Cookie
        cookies = response.cookies
        
        # 验证登录
        check_url = "https://passport.12306.cn/otn/login/userLogin"
        requests.get(check_url, cookies=cookies)
        
        return {
            'cookies': dict(cookies),
            'token': login_data.get('token')
        }
    
    def refresh_cookies(self, cookies):
        """刷新 Cookie (防止过期)"""
        refresh_url = "https://www.12306.cn/otn/index/init"
        response = requests.get(refresh_url, cookies=cookies)
        return response.cookies
    
    def is_expired(self, cookies, expire_at):
        """检查 Cookie 是否过期"""
        if not expire_at:
            return True
        expire_datetime = datetime.strptime(expire_at, "%Y-%m-%d %H:%M:%S")
        return datetime.now() > expire_datetime - timedelta(hours=24)
```

### 5.3 余票监控流程 (ticket_monitor.py)

```python
class TicketMonitor:
    """余票监控器"""
    
    API_URL = "https://kyfw.12306.cn/otn/leftTicket/query"
    
    def __init__(self, config):
        self.config = config
        self.last_state = {}  # 上次状态
    
    def query_tickets(self, date, from_code, to_code):
        """查询余票"""
        params = {
            'leftTicketDTO.train_date': date,
            'leftTicketDTO.from_station': from_code,
            'leftTicketDTO.to_station': to_code,
            'purpose_codes': 'ADULT'
        }
        
        response = requests.get(
            self.API_URL,
            params=params,
            timeout=10
        )
        
        if response.status_code != 200:
            raise QueryFailed(f"HTTP {response.status_code}")
        
        data = response.json()
        if not data.get('status'):
            raise QueryFailed(data.get('message', 'Unknown error'))
        
        return self.parse_response(data)
    
    def parse_response(self, data):
        """解析 API 响应"""
        results = []
        
        for item in data['data']['result']:
            fields = item.split('|')
            
            train_no = fields[2]
            from_station = fields[6]
            to_station = fields[7]
            start_time = fields[8]
            end_time = fields[9]
            
            # 解析各席位余票
            tickets = {
                '硬座': fields[29],  # yz_num
                '软座': fields[30],  # rz_num
                '硬卧': fields[28],  # yw_num
                '软卧': fields[27],  # rw_num
                '无座': fields[26],  # wz_num
            }
            
            results.append({
                'train_no': train_no,
                'from': from_station,
                'to': to_station,
                'start_time': start_time,
                'end_time': end_time,
                'tickets': tickets
            })
        
        return results
    
    def detect_changes(self, current_tickets, target):
        """检测余票变化"""
        changes = []
        
        for ticket in current_tickets:
            train_no = ticket['train_no']
            
            # 跳过非目标车次
            if train_no not in target.trains:
                continue
            
            # 检测席别变化
            for seat in target.seats:
                current_count = self.parse_count(ticket['tickets'].get(seat, '无'))
                last_key = f"{train_no}_{seat}"
                last_count = self.last_state.get(last_key, -1)
                
                if current_count != last_count:
                    changes.append({
                        'train_no': train_no,
                        'seat': seat,
                        'current': current_count,
                        'last': last_count,
                        'has_ticket': current_count > 0 or current_count == '有'
                    })
            
            # 更新状态
            for seat, count in ticket['tickets'].items():
                self.last_state[f"{train_no}_{seat}"] = self.parse_count(count)
        
        return changes
    
    def parse_count(self, value):
        """解析余票数值"""
        if value == '有票' or value == '充足':
            return 999
        elif value == '无票' or not value:
            return 0
        elif '剩余' in value:
            # 提取数字
            match = re.search(r'(\d+)', value)
            return int(match.group(1)) if match else 0
        else:
            try:
                return int(value)
            except:
                return 0
```

### 5.4 自动下单流程 (order_executor.py)

```python
class OrderExecutor:
    """订单执行器"""
    
    SUBMIT_URL = "https://kyfw.12306.cn/otn/leftTicket/submitOrder"
    CONFIRM_URL = "https://kyfu.12306.cn/otn/confirmPassenger/initDf"
    
    def __init__(self, config, captcha_solver):
        self.config = config
        self.captcha_solver = captcha_solver
    
    def submit_order(self, account, train_info, target):
        """提交订单"""
        
        # 1. 检查登录状态
        if self.is_token_expired(account):
            raise TokenExpired("登录已过期，请重新扫码")
        
        # 2. 获取乘客信息
        passengers = self.get_passengers(account)
        if not passengers:
            raise NoPassenger("账户无可用乘客")
        
        # 3. 检查座位可用性（双重验证）
        if not self.check_seat_available(train_info, target):
            raise SeatUnavailable("座位已被抢占")
        
        # 4. 准备订单参数
        order_params = {
            'secretStr': train_info['secretStr'],
            'train_date': target.date,
            'back_train_date': '',
            'tour_flag': 'dc',
            'purpose_codes': 'ADULT',
            'query_from_station_name': target.from_station,
            'query_to_station_name': target.to_station,
            'undefined': ''
        }
        
        # 5. 提交订单请求
        response = requests.post(
            self.SUBMIT_URL,
            data=order_params,
            cookies=account.cookies,
            headers={
                'Referer': 'https://kyfw.12306.cn/otn/leftTicket/init'
            }
        )
        
        if response.status_code != 200:
            raise SubmitFailed(f"HTTP {response.status_code}")
        
        result = response.json()
        if result.get('status') != True:
            error_msg = result.get('messages', ['未知错误'])[0]
            raise SubmitFailed(error_msg)
        
        # 6. 处理验证码（如需）
        if self.need_captcha(result):
            captcha_image = self.get_captcha(account)
            captcha_result = self.captcha_solver.solve(captcha_image)
            if not self.verify_captcha(account, captcha_result):
                raise CaptchaFailed("验证码识别失败")
        
        # 7. 确认订单
        confirm_params = {
            'train_no': train_info['train_no'],
            'station_train_code': train_info['station_train_code'],
            'seat_type_code': self.get_seat_code(target.seats[0]),
            'from_station_telecode': train_info['from_station'],
            'to_station_telecode': train_info['to_station'],
            'departure_time': train_info['start_time'],
            'arrival_time': train_info['end_time'],
            'passengers': json.dumps(passengers),
            'tour_flag': 'dc',
            'randCode': '',
            'purpose_codes': '00',
            'key_check_isChange': result['data']['keyCheckIsChange'],
            'left_ticket_str': result['data']['leftTicketStr'],
            'set_type': '1',
            'checkSeatNo': ''
        }
        
        response = requests.post(
            self.CONFIRM_URL,
            data=confirm_params,
            cookies=account.cookies,
            headers={
                'Referer': 'https://kyfw.12306.cn/otn/confirmPassenger/initDf'
            }
        )
        
        if response.status_code != 200:
            raise ConfirmFailed("订单确认失败")
        
        confirm_result = response.json()
        
        if confirm_result.get('status') == True:
            return {
                'success': True,
                'order_no': confirm_result['data']['orderId'],
                'price': confirm_result['data']['orderTotalPrice']
            }
        else:
            error_msg = confirm_result.get('messages', ['下单失败'])[0]
            raise OrderFailed(error_msg)
    
    def get_passengers(self, account):
        """获取常用乘客"""
        url = "https://kyfw.12306.cn/otn/passengers/query"
        response = requests.get(
            url,
            cookies=account.cookies,
            params={'_json_att': ''}
        )
        
        if response.status_code != 200:
            return []
        
        data = response.json()
        if data.get('status') != True:
            return []
        
        return data['data']['normal_passengers']
    
    def need_captcha(self, submit_result):
        """判断是否需要验证码"""
        return submit_result.get('data', {}).get('ifShowPassCode', False)
    
    def get_captcha(self, account):
        """获取验证码图片"""
        url = "https://kyfw.12306.cn/otn/passengerCode/getPassCodeNew"
        params = {
            'module': 'passenger',
            'rand': 'sjrand',
            '0.123': random.random()
        }
        response = requests.get(
            url,
            params=params,
            cookies=account.cookies
        )
        return response.content
    
    def verify_captcha(self, account, captcha_result):
        """验证验证码"""
        url = "https://kyfw.12306.cn/otn/passengerCode/checkRandCodeAnsyn"
        data = {
            'randCode': captcha_result,
            'rand': 'sjrand',
            '_json_att': ''
        }
        response = requests.post(
            url,
            data=data,
            cookies=account.cookies
        )
        result = response.json()
        return result.get('status') == True
```

### 5.5 验证码识别 (captcha_solver.py)

```python
class ChaoJiYingSolver:
    """超级鹰验证码识别"""
    
    API_URL = "http://www.chaojiying.com/api/recognize"
    
    def __init__(self, config):
        self.config = config
        self.username = config['username']
        self.password = config['password']
        self.soft_id = config['soft_id']
    
    def solve(self, image_bytes):
        """识别验证码"""
        # 压缩图片 (推荐 70KB 以下)
        image = self.compress_image(image_bytes)
        
        # Base64 编码
        image_base64 = base64.b64encode(image).decode('ascii')
        
        # 构建请求
        data = {
            'user': self.username,
            'pass': self.password,
            'softid': self.soft_id,
            'codetype': '4004',  # 12306 点选验证码
            'file_base64': image_base64
        }
        
        # 发送请求
        response = requests.post(
            self.API_URL,
            data=data,
            timeout=self.config.get('timeout', 30)
        )
        
        result = response.json()
        
        if result['pic_str'] == '':
            raise RecognitionFailed("识别失败，无结果")
        
        return result['pic_str']
    
    def compress_image(self, image_bytes, max_size=70*1024):
        """压缩图片"""
        from PIL import Image
        import io
        
        image = Image.open(io.BytesIO(image_bytes))
        
        # 调整尺寸
        max_dimension = 500
        if max(image.size) > max_dimension:
            image.thumbnail((max_dimension, max_dimension))
        
        # 压缩质量
        quality = 70
        output = io.BytesIO()
        
        while len(output.getvalue()) > max_size and quality > 10:
            output.seek(0)
            output.truncate()
            image.save(output, format='JPEG', quality=quality)
            quality -= 10
        
        return output.getvalue()
```

### 5.6 通知模块 (notification.py)

```python
class NotificationManager:
    """通知管理器"""
    
    def __init__(self, config):
        self.config = config
        self.pushplus_enabled = config.get('pushplus', {}).get('enabled', False)
        self.pushplus_token = config.get('pushplus', {}).get('token', '')
    
    def notify_ticket_available(self, train_info, target, account_name):
        """有余票通知"""
        title = "🎫 有票啦！"
        content = f"""
# 🎫 发现余票！

**监控目标**: {target.from_station} → {target.to_station}
**乘车日期**: {target.date}
**乘客**: {account_name}

---

**车次**: {train_info['train_no']}
**出发时间**: {train_info['start_time']}
**到达时间**: {train_info['end_time']}
**席位**: {target.seats[0]}

---
💡 请立即登录 12306 手动下单！
        """.strip()
        
        self.send_pushplus(title, content)
    
    def notify_order_success(self, order_info):
        """下单成功通知"""
        title = "✅ 下单成功！"
        content = f"""
# ✅ 订单提交成功！

**订单号**: {order_info['order_no']}
**金额**: ¥{order_info['price']}
**车次**: {order_info['train_no']}
**时间**: {order_info['departure_time']}

---

⚠️ **请在 30 分钟内完成支付！**

🔗 支付链接: https://12306.cn
        """.strip()
        
        self.send_pushplus(title, content)
    
    def notify_order_failed(self, error, train_info):
        """下单失败通知"""
        title = "❌ 下单失败"
        content = f"""
# ❌ 下单失败

**车次**: {train_info.get('train_no', 'N/A')}
**错误**: {error}

---

请手动尝试下单！
        """.strip()
        
        self.send_pushplus(title, content)
    
    def notify_token_expired(self, account_name):
        """登录过期通知"""
        title = "⚠️ 登录已过期"
        content = f"""
# ⚠️ 登录凭证过期

**账号**: {account_name}

请重新扫码登录！
        """.strip()
        
        self.send_pushplus(title, content)
    
    def send_pushplus(self, title, content):
        """发送 PushPlus 通知"""
        if not self.pushplus_enabled:
            print(f"[通知] {title}")
            return
        
        url = "https://www.pushplus.plus/api/send"
        data = {
            "token": self.pushplus_token,
            "title": title,
            "content": content,
            "channel": "wechat"
        }
        
        try:
            response = requests.post(url, json=data, timeout=10)
            if response.json().get('code') != 200:
                print(f"PushPlus 发送失败: {response.text}")
        except Exception as e:
            print(f"PushPlus 通知失败: {e}")
```

## 6. 防封禁策略

### 6.1 请求频率控制
```python
class RequestRateLimiter:
    """请求频率限制器"""
    
    MIN_INTERVAL = 2  # 最小间隔(秒)
    MAX_INTERVAL = 5  # 最大间隔(秒)
    
    def __init__(self):
        self.last_request_time = 0
    
    def wait(self):
        """等待合适的间隔"""
        elapsed = time.time() - self.last_request_time
        
        if elapsed < self.MIN_INTERVAL:
            sleep_time = self.MIN_INTERVAL - elapsed + random.uniform(0, 1)
        else:
            sleep_time = random.uniform(0, self.MAX_INTERVAL - self.MIN_INTERVAL)
        
        time.sleep(sleep_time)
        self.last_request_time = time.time()
```

### 6.2 代理轮换 (可选)
```python
class ProxyManager:
    """代理管理器"""
    
    def __init__(self, config):
        self.enabled = config.get('enabled', False)
        self.proxy_api = config.get('api_url', '')
        self.proxies = []
        self.current_index = 0
    
    def get_proxy(self):
        """获取代理"""
        if not self.enabled:
            return None
        
        # 轮换获取
        if not self.proxies:
            self.refresh_proxies()
        
        proxy = self.proxies[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.proxies)
        
        return proxy
    
    def refresh_proxies(self):
        """刷新代理列表"""
        try:
            response = requests.get(self.proxy_api)
            data = response.json()
            self.proxies = data.get('proxies', [])
        except:
            self.proxies = []
```

## 7. 错误处理

### 7.1 异常分类
```python
class TicketBotError(Exception):
    """基础异常类"""
    pass

class TokenExpired(TicketBotError):
    """登录凭证过期"""
    pass

class QueryFailed(TicketBotError):
    """查询失败"""
    pass

class SubmitFailed(TicketBotError):
    """提交订单失败"""
    pass

class SeatUnavailable(TicketBotError):
    """座位已被抢占"""
    pass

class CaptchaFailed(TicketBotError):
    """验证码识别失败"""
    pass

class QRCodeExpired(TicketBotError):
    """二维码过期"""
    pass

class NoPassenger(TicketBotError):
    """无乘客信息"""
    pass

class OrderFailed(TicketBotError):
    """订单处理失败"""
    pass
```

### 7.2 重试机制
```python
def with_retry(func, max_retries=3, retry_delay=5):
    """带重试的装饰器"""
    
    def wrapper(*args, **kwargs):
        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except (QueryFailed, SeatUnavailable, CaptchaFailed) as e:
                print(f"[重试] {func.__name__} 失败: {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
            except (TokenExpired, NoPassenger) as e:
                # 不重试，直接抛出
                raise
    
    return wrapper
```

## 8. 使用说明

### 8.1 安装依赖
```bash
pip install requests Pillow pyyaml schedule
```

### 8.2 配置账号
```bash
# 编辑 config.yaml
vim config.yaml

# 设置 PushPlus Token
export PUSHPLUS_TOKEN="xxx"

# 设置超级鹰账号
export CHAOJIYING_USER="username"
export CHAOJIYING_PASS="password"
```

### 8.3 运行程序
```bash
# 方式1: 交互式扫码登录
python main.py --mode interactive

# 方式2: 后台监控 (需先登录)
python main.py --mode monitor --daemon

# 方式3: 单次查询
python main.py --query --date 2026-02-22 --from 沈阳 --to 佳木斯
```

### 8.4 交互式登录
```
1. 程序生成二维码图片 → /tmp/qrcode.png
2. 用户用 12306 APP 扫码
3. 用户在手机上确认登录
4. 程序自动保存 Cookie
5. 开始监控
```

## 9. 风险与局限性

### 9.1 已知风险
1. **12306 风控**: 频繁请求可能触发验证码或封禁 IP
2. **Cookie 过期**: 需要定期刷新（建议每周一次）
3. **验证码识别**: 打码平台有失败率（~5%）
4. **网络波动**: 请求超时可能导致错过最佳下单时机

### 9.2 局限性
1. **无法自动支付**: 12306 需要短信验证码完成支付
2. **无法选座**: 简化版暂不支持自定义座位选择
3. **多乘客**: 简化版仅支持单个乘客下单

### 9.3 合规声明
- 本工具仅供学习研究使用
- 请遵守 12306 服务条款
- 抢票失败风险由用户自行承担

## 10. 未来扩展

- [ ] 支持多乘客同时下单
- [ ] 支持座位偏好选择（靠窗、靠过道）
- [ ] 支持学生票、儿童票
- [ ] 集成更多打码平台（容错）
- [ ] Web 管理界面
- [ ] 微信小程序远程控制

## 11. 文件结构

```
12306-ticket-bot/
├── agent.md              # 本文档
├── main.py               # 程序入口
├── config.yaml          # 配置文件
├── requirements.txt     # 依赖列表
├── README.md            # 使用说明
│
├── core/
│   ├── auth_manager.py   # 认证管理
│   ├── captcha_solver.py # 验证码识别
│   ├── ticket_monitor.py # 余票监控
│   ├── order_executor.py # 订单执行
│   ├── notification.py   # 通知管理
│   ├── config_manager.py # 配置管理
│   ├── database.py      # 数据库操作
│   └── proxy_manager.py  # 代理管理
│
├── utils/
│   ├── qrcode.py        # 二维码工具
│   ├── encoder.py       # 编码工具
│   └── logger.py        # 日志工具
│
├── data/
│   ├── ticket_bot.db    # SQLite 数据库
│   └── logs/            # 日志文件
│
└── tests/
    ├── test_auth.py     # 认证测试
    ├── test_monitor.py   # 监控测试
    └── test_order.py     # 下单测试
```

---

**文档版本**: v1.0  
**创建时间**: 2026-02-08  
**状态**: 待 Claude 审计

# 🚂 12306 抢票 Agent

![Python](https://img.shields.io/badge/Python-3.8+-blue)
![License](https://img.shields.io/badge/License-MIT-green)

## 📋 功能特性

- ✅ **扫码登录** - 自动获取并保存登录状态
- ✅ **余票监控** - 多车次、多席位实时监控
- ✅ **自动下单** - 完整的购票流程
- ✅ **验证码识别** - 多平台容错（超级鹰/本地OCR）
- ✅ **风控检测** - 自适应频率控制
- ✅ **多渠道通知** - PushPlus 微信通知
- ✅ **加密存储** - Cookie 安全保存
- ✅ **本地持续化** - 后台运行，开机自启

## 🚀 快速开始

### 方式一：一键安装（推荐）

```bash
# 下载并运行安装脚本
git clone https://github.com/openclaw/12306-ticket-bot.git
cd 12306-ticket-bot
chmod +x install.sh
./install.sh
```

### 方式二：手动安装

```bash
# 1. 下载项目
git clone https://github.com/openclaw/12306-ticket-bot.git
cd 12306-ticket-bot

# 2. 安装依赖
pip3 install -r requirements.txt

# 3. 配置账户
cp config.example.yaml config.yaml
# 编辑 config.yaml，填入 Cookie

# 4. 运行
python3 main.py --monitor
```

## 📖 使用说明

### 获取 Cookie

1. 打开浏览器，访问 [12306.cn](https://12306.cn)
2. 登录您的账号
3. 按 `F12` 打开开发者工具
4. 切换到 `Application` → `Cookies`
5. 复制以下 Cookie 值到 `config.yaml`：
   - `_uab_guid`
   - `_jc_save_fromStation`
   - `_jc_save_toStation`
   - `_jc_save_fromDate`
   - `_jc_save_toDate`
   - `_jc_save_wfdc_flag`
   - `JSESSIONID`

### 配置监控目标

编辑 `config.yaml`：

```yaml
targets:
  - date: "2026-02-15"        # 出发日期
    from_code: "SNQ"           # 出发站代码（沈阳）
    to_code: "JHM"            # 到达站代码（佳木斯）
    trains: ["K339", "K929"]  # 监控的车次列表
    seats: ["硬卧", "软卧"]    # 监控的席位
```

### 运行模式

```bash
# 前台运行（适合测试）
python3 main.py --monitor

# 仅登录（获取 Cookie）
python3 main.py --login

# 仅查询余票
python3 main.py --query

# 后台运行（守护进程）
python3 local_monitor.py --daemon

# 查看状态
python3 local_monitor.py --status

# 停止监控
python3 local_monitor.py --stop
```

### Linux 服务安装

```bash
# 安装服务（需要 root）
sudo python3 local_monitor.py --install-service

# 启动服务
sudo systemctl start 12306-monitor.service

# 查看状态
sudo systemctl status 12306-monitor.service

# 停止服务
sudo systemctl stop 12306-monitor.service
```

## 📁 项目结构

```
12306-ticket-bot/
├── main.py              # 主入口
├── local_monitor.py      # 本地监控脚本
├── install.sh           # 一键安装脚本
├── config.yaml          # 配置文件
├── requirements.txt     # 依赖列表
├── README.md            # 本文档
├── core/                # 核心模块
│   ├── auth_manager.py     # 扫码登录
│   ├── captcha_solver.py   # 验证码识别
│   ├── ticket_monitor.py   # 余票监控
│   ├── order_executor.py   # 自动下单
│   ├── notification.py     # 通知管理
│   ├── risk_controller.py  # 风控检测
│   ├── config_manager.py   # 配置管理
│   └── proxy_manager.py    # 代理管理
└── utils/              # 工具模块
    ├── qrcode.py       # 二维码生成
    ├── encoder.py      # 数据编码
    └── logger.py       # 日志管理
```

## 🔧 配置文件说明

### config.yaml

```yaml
# 账户配置
account:
  cookie: ""  # 登录 Cookie（必填）

# 监控配置
targets:
  - date: "2026-02-15"
    from_code: "SNQ"
    to_code: "JHM"
    trains: ["K339", "K929"]
    seats: ["硬卧", "软卧"]

# 通知配置
notification:
  pushplus:
    enabled: true
    token: ""  # PushPlus Token

# 风控配置
risk:
  min_interval: 5    # 最小查询间隔（秒）
  max_interval: 30   # 最大查询间隔（秒）

# 验证码配置
captcha:
  provider: "chaojiying"
  username: ""      # 超级鹰账号
  password: ""      # 超级鹰密码
  soft_id: ""       # 软件 ID
```

## ⚠️ 注意事项

### 🚨 重要警告

#### 1. 账号风险
- ⚠️ **高风险**：自动化操作可能触发12306风控系统
- ⚠️ **封号风险**：频繁操作可能导致账号被限制登录
- ⚠️ **验证码挑战**：操作频率过高会要求额外验证码验证
- 📌 **建议**：首次使用建议使用小号测试，熟练后再切换主账号

#### 2. 法律风险
- ⚠️ **服务条款**：12306官方明确禁止使用第三方抢票软件
- ⚠️ **法律责任**：用于商业目的可能涉及违法
- ⚠️ **用户协议**：使用本工具即表示您已了解并承担相关风险
- 📌 **声明**：本工具仅供学习研究使用，请于24小时内删除

#### 3. 技术限制
- ⚠️ **验证码**：自动识别成功率约80-90%，无法保证100%成功
- ⚠️ **支付限制**：无法自动完成支付，需要手动操作
- ⚠️ **座位竞争**：热门车次座位竞争激烈，不保证抢票成功
- ⚠️ **网络波动**：网络延迟可能导致错失最佳时机
- 📌 **建议**：尽量选择非热门车次和时段

#### 4. 资金安全
- ⚠️ **支付安全**：请确保支付环境安全
- ⚠️ **防止诈骗**：不要在任何非官方页面输入支付信息
- ⚠️ **退款政策**：遵循12306官方退改签政策

### 🛡️ 安全使用建议

#### 1. 账号保护
```
✅ 使用独立账号测试
✅ 定期检查账号状态
✅ 不要在公共场所使用
✅ 设置支付密码和短信提醒
```

#### 2. 操作规范
```
✅ 控制查询频率（建议间隔≥5秒）
✅ 不要同时运行多个实例
✅ 使用代理IP降低风险（可选）
✅ 避开高峰时段（如发车前1小时）
```

#### 3. 数据备份
```
✅ 定期备份配置文件
✅ 记录Cookie有效期
✅ 保存重要订单信息
```

### ❓ 常见问题

**Q: 提示 "登录过期"**
A: Cookie已失效，请重新扫码登录获取新Cookie

**Q: 频繁触发风控**
A: 
1. 增大 config.yaml 中的 `min_interval` 值
2. 使用代理IP
3. 等待24小时后再试

**Q: 验证码识别失败**
A: 
1. 检查超级鹰账号余额
2. 切换为本地OCR模式
3. 手动输入验证码

**Q: 座位显示有票但下单失败**
A: 
1. 座位可能被他人抢先
2. 检查是否超出购买数量限制
3. 确认乘客信息正确

**Q: 如何查看日志？**
A: 日志保存在 `logs/` 目录

**Q: 支持哪些浏览器？**
A: 支持Chrome、Firefox、Edge等主流浏览器

### 📞 风险声明

使用本工具即表示您已阅读并同意以下声明：

```
本人已知悉：
1. 12306官方禁止使用第三方抢票软件
2. 使用本工具存在账号被封禁的风险
3. 本工具不保证抢票成功
4. 本人仅将本工具用于学习研究目的
5. 如因使用本工具产生任何纠纷，本人愿意承担全部责任
```

### 🏢 官方渠道

如需购票，建议优先使用以下官方渠道：

- **官方网站**: https://www.12306.cn
- **官方APP**: 铁路12306（iOS/Android）
- **微信小程序**: 铁路12306
- **官方客服**: 12306

---

**请在下载后24小时内删除本工具，仅供学习研究使用！**

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

## 📝 更新日志

### v2.0 (2026-02-08)
- ✅ 修复 API URL 拼写错误
- ✅ 增强响应解析健壮性
- ✅ 添加本地持续化监控
- ✅ 添加一键安装脚本
- ✅ 添加系统服务支持
- ✅ 补充详细注意事项和安全建议

## 📄 License

MIT License

---

**作者**: OpenClaw  
**版本**: v2.0

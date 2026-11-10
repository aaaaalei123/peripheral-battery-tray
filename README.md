# 外设电量托盘

Windows 系统托盘常驻应用：合并显示 **迈从 G87 V2 键盘** 与 **罗技 GPW 一代鼠标** 电量。单一圆环图标展示当前关注设备，右键菜单可查看两台详情并调整设置。

## 环境要求

- Python 3.10+
- Windows（实机读取 HID / 蓝牙）；开发机可为 macOS，但托盘与 WinRT 仅在 Windows 完整可用

## 安装

```bash
pip install -r requirements.txt
```

在 macOS 上可省略 `winsdk`（`requirements.txt` 已按平台标记）；托盘需 `pystray` 与 `Pillow`。

## 运行

```bash
python main.py
```

右键托盘图标：切换图标设备（键盘/鼠标）、低电量阈值、轮询间隔（30/60/120 秒）、低电量通知、开机自启（Windows）、立即刷新、退出。

配置保存在 `%APPDATA%\PeripheralBattery\config.json`。

## 诊断模式

插入接收器后，用于排查 HID 枚举与原始读数：

```bash
python main.py --probe
```

会打印已知 VID/PID 的 HID 接口，以及两台 reader 的 `probe_presence` / `read` 结果。

## Windows 实机自检

插入接收器后的端到端检查项、`--probe` 输出解读与 G HUB/休眠/VID 等问题排查，见 **[WINDOWS_VERIFY.md](WINDOWS_VERIFY.md)**。

## 打包成 exe（必须在 Windows 上）

不能在 macOS 上交叉打 Windows exe。把整个 `peripheral-battery-tray` 文件夹拷到 Windows 后：

```bat
build_windows.bat
```

或手动：

```bat
pip install -r requirements.txt pyinstaller
pyinstaller --noconfirm PeripheralBattery.spec
```

产物：`dist\PeripheralBattery.exe`（单文件、无控制台窗口）。

```bat
dist\PeripheralBattery.exe
dist\PeripheralBattery.exe --probe
```

`--probe` 在打包版里会临时弹出控制台显示诊断信息。开机自启会直接注册该 exe 路径。

首次运行若被 Windows Defender / SmartScreen 拦截，选「仍要运行」即可（未签名的本地打包常见现象）。

## 支持的设备

| 设备 | 连接方式 | 说明 |
|------|----------|------|
| 罗技 GPW 一代 | Lightspeed 接收器 | HID++ 2.0 电量 |
| 迈从 G87 V2 | 2.4G 接收器 / 有线 / 蓝牙 | Compx 协议或 WinRT 蓝牙电量 |

设备休眠时会降低查询频率；重新在线后立即读取电量。

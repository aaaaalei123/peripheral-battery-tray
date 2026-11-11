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

**推荐先开 cmd，再运行**（比双击更容易看清报错）：

```bat
cd /d 你的路径\peripheral-battery-tray
build_windows.bat
```

或双击 `build_windows.bat`：脚本结束会 `pause`，不会再一闪而过。

> 注意：`build_windows.bat` 必须是 **英文 ASCII + CRLF**。若用记事本另存成 UTF-8，或在 Mac 上改坏换行，cmd 会出现 `'echo' 不是内部或外部命令`、乱码中文被拆成命令等怪错。请直接用仓库里的文件，不要改编码。

产物：`dist\PeripheralBattery.exe`

```bat
dist\PeripheralBattery.exe
dist\PeripheralBattery.exe --probe
```

### 打包闪退 / 失败时

1. 确认已装 **Python 3.10+**，安装勾选 **Add python.exe to PATH**  
   下载：https://www.python.org/downloads/
2. 新开 cmd 执行：`py -3 --version` 或 `python --version`  
   若提示找不到命令，就是环境未就绪，不是 bat 本身坏了。
3. 看同目录 `build_log.txt` 和窗口里的红色报错。
4. 也可手动：

```bat
py -3 -m pip install -r requirements.txt pyinstaller
py -3 -m PyInstaller --noconfirm PeripheralBattery.spec
```

`--probe` 在打包版里会临时弹出控制台。开机自启会注册该 exe。  
首次运行若被 SmartScreen 拦截，选「仍要运行」即可。

## 支持的设备

| 设备 | 连接方式 | 说明 |
|------|----------|------|
| 罗技 GPW 一代 | Lightspeed 接收器 | HID++ 2.0 电量 |
| 迈从 G87 V2 | 2.4G 接收器 / 有线 / 蓝牙 | Compx 协议或 WinRT 蓝牙电量 |

设备休眠时会降低查询频率；重新在线后立即读取电量。

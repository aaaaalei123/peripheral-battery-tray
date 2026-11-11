# Windows 实机自检清单

在 **Windows** 上插入 GPW Lightspeed 接收器与 G87 2.4G 接收器，完成下列端到端检查。开发机若为 macOS，仅可运行单元测试与无 HID 的 `--probe`；**硬件相关项需在 Windows 上由使用者勾选**。

## 前置条件

1. Python 3.10–3.12（推荐 3.12），已执行 `pip install -r requirements.txt`。蓝牙电量可选再装 `requirements-bt.txt`。
2. 接收器已插入，鼠标/键盘已配对并处于 2.4G 连接（非仅蓝牙，除非 intentionally 测蓝牙路径）。
3. 建议先关闭占用 HID 接收器的软件（见「故障排查」），再启动应用。

---

## 端到端检查项

与 Spec / Task 7 一致，请在实机上逐项勾选：

- [ ] GPW Lightspeed 插入：菜单显示鼠标电量
- [ ] G87 2.4G：菜单显示键盘电量
- [ ] 切换「图标展示设备」：圆环跟随
- [ ] 键盘休眠后停止查询；动一下键盘后立刻更新
- [ ] 低电量通知只弹一次直到回充
- [ ] `--probe` 输出可读

### 各条目的预期行为

| 检查项 | 如何操作 | 预期 |
|--------|----------|------|
| GPW 菜单电量 | 运行 `python main.py`，右键托盘图标查看菜单中鼠标行 | 显示百分比（非「—」或长期 0%），与 G HUB / 驱动大致一致 |
| G87 菜单电量 | 同上，查看键盘行 | 2.4G 接收器在线时显示百分比 |
| 圆环跟随 | 菜单选择「图标展示设备」→ 键盘 / 鼠标 | 托盘圆环百分比与所选设备一致，tooltip 仍显示两台 |
| 休眠与唤醒 | 键盘静置进入休眠（或关盖/省电），再按键唤醒 | 休眠期间轮询降低；唤醒后数秒内电量更新（不必等满轮询间隔） |
| 低电通知 | 将阈值调高或等待真实低电（可暂时改配置阈值测试） | 同一设备低于阈值仅通知一次；充电或电量回升超过阈值后，再次降低才可再弹 |
| `--probe` | 见下文 | 能枚举到预期 VID/PID，`probe_presence` / `read` 有明确 True/False 与读数或 `None` |

---

## 诊断模式：`python main.py --probe`

在**有接收器的 Windows** 上，于项目根目录执行：

```bash
python main.py --probe
```

（若使用打包的 exe：`PeripheralBattery.exe --probe`。）

### 输出结构

1. **标题**：`=== 外设电量探测模式 ===`
2. **HID 枚举**（按 VID/PID 分组）：
   - `Logitech (VID 046D)` — GPW / Lightspeed 接收器
   - `Mchose receiver 3554:FA09` — G87 常见 2.4G 接收器
   - `Mchose 41E4:2001`、`Mchose wired 3837:3033` — 其它固件/有线路径
3. 每组下为 JSON 行，含 `vendor_id`、`product_id`、`path`、`usage_page`、`usage` 等；**(无设备)** 表示当前未枚举到该 VID/PID。
4. **罗技 GPW (HID++)**：`probe_presence: True/False`，`read:` 后为 `DeviceReading` 字段（含 `percent` 等）或 `read: None`。
5. **迈从 G87**：同上。
6. 末尾 **`完成。`** 表示进程正常退出。

### 如何判读

| 现象 | 含义 |
|------|------|
| Logitech 段有多条 JSON，且 `probe_presence: True`、`read` 含合理 `percent` | 鼠标 HID++ 通路正常 |
| Mchose 某 VID/PID 有设备且键盘 `read` 非 `None` | 键盘走对应接收器/协议成功 |
| 枚举有条目但 `probe_presence: False` 或 `read: None` | 设备被占用、接口选错、或休眠/未配对 |
| 全部为 `(无设备)` | 未插接收器、驱动问题、或 VID/PID 与键盘批次不符 |
| 非 Windows 会提示蓝牙 WinRT 仅限 Windows | 蓝牙电量探测需在 Windows 上测 |

成功标准（对应清单最后一项）：**人能直接看出**哪台在线、哪台不在线，失败时至少能看到枚举与 `None`，便于对照下文排查。

---

## 运行主程序

```bash
python main.py
```

确认托盘图标出现；右键可改阈值、轮询间隔、低电通知、开机自启（Windows）等。配置路径：`%APPDATA%\PeripheralBattery\config.json`（应用**不会**在菜单里写文件，仅内存与托盘交互）。

---

## 故障排查

### G HUB / 其它软件占用罗技接收器

**症状**：`--probe` 中 Logitech 可能有枚举，但 `probe_presence: False` 或 `read: None`；托盘鼠标无电量。

**处理**：

1. 退出 **Logitech G HUB**（托盘彻底退出，非仅最小化）。
2. 必要时在任务管理器结束 `lghub_*` 进程。
3. 重新插拔 Lightspeed 接收器，再跑 `python main.py --probe`。
4. 若仍失败，暂时卸载/禁用 G HUB 的「独占设备」类选项（视版本而定），或仅用本应用测通后再决定是否与 G HUB 共存。

本应用通过 HID++ 直连接收器；与 G HUB 同时打开时常发生争用。

### 键盘休眠导致读数为 None 或长期不更新

**症状**：G87 一段时间不用后菜单无更新；`--probe` 键盘 `read: None`；唤醒前 `probe_presence` 可能为 `False`。

**说明**：设计为休眠时降低查询；约每 45 秒做一次 `probe_presence`，唤醒成功后会**立即**再读电量。

**处理**：

1. 按任意键或移动键盘唤醒。
2. 托盘选「立即刷新」或等待一次探测周期。
3. 确认 2.4G 接收器在线、非仅蓝牙休眠（蓝牙路径依赖 WinRT，需 Windows 与配对）。

### 接收器 VID/PID 不对（迈从批次差异）

**症状**：迈从段全部为 `(无设备)`，或仅有 `3837:3033`（有线）而无 `3554:FA09` / `41E4:2001`。

**说明**：代码支持：

| 路径 | VID:PID | 用途 |
|------|---------|------|
| Path B | `3554:FA09` | 常见 2.4G  dongle |
| Path A | `41E4:2001` | 部分批次 |
| Path C | `3837:3033` | 有线 USB |

**处理**：

1. 用 `--probe` 看实际枚举出的 `vendor_id` / `product_id`（十六进制 JSON）。
2. 若与上表都不符，用设备管理器 / USBView 确认硬件 ID，并对照仓库 `battery_tray/readers/mchose_hid.py` 中 `PATH_B_TARGETS` 等是否需要扩展（属开发变更，非自检可单独提 issue）。
3. 确认插入的是键盘配套 2.4G 接收器，而非仅充电线。

### 其它

- **`hidapi: 未安装`**：执行 `pip install hidapi`。
- **托盘无图标**：确认已装 `pystray`、`Pillow`；无控制台时用 `pythonw main.py` 或 `--windowed` 打包 exe。
- **低电通知重复**：检查是否在菜单关闭后又打开通知；回升超过阈值后再次降低应允许再弹一次（与设计一致）。

---

## 自动化测试（任意平台）

仓库单元测试不依赖硬件：

```bash
python3 -m pytest tests/ -q
```

硬件行为以上述清单为准，在 Windows 实机由使用者勾选完成。

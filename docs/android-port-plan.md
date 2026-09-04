# 安卓（APK）移植方案 —— 象棋辅助工具

> 目标：把当前 PySide6 桌面版“象棋辅助工具”（正常玩法 + 揭棋 + AI 分析）搬到安卓，
> 产出可安装的 APK。本文档评估差距、给工具链清单、推荐架构与分阶段路线。

## 1. 现状与差距

桌面版结构（已经是“逻辑与界面分层”，利于移植）：

| 层 | 目录 | 是否依赖桌面/系统 | 安卓可用性 |
|---|---|---|---|
| 规则/模型 | `core/`, `rules/` | 纯 Python，无 GUI | ✅ 原样可打包 |
| AI（内置） | `ai/search.py`, `ai/dark_search.py`, `ai/evaluation.py`… | 纯 Python | ✅ 原样可打包 |
| 引擎适配 | `engine/pikafish_adapter.py`, `engine/ucci_client.py` | `subprocess` + Windows .exe | ⚠️ 需换安卓引擎二进制 |
| 服务/存取 | `services/settings_service.py` | 用 `%LOCALAPPDATA%`（桌面路径） | ⚠️ 需改安卓私有目录 |
| 界面 | `ui/*`, `main.py` | PySide6 QtWidgets（桌面触屏体验差） | ❌ 需重写为触屏 UI |

必须正视的三点：
1. **QtWidgets 不适合手机**：即使能出 APK，小屏/触控/多点交互体验差，UI 需要按触屏重做。
2. **强引擎是 Windows .exe**：Pikafish 官方发布包里有 `Android/pikafish-armv8` 二进制，可换；但 Android 上“应用内启动外部二进制”需要放到应用私有目录并 `chmod +x`（或用服务/前台进程方式）。
3. **Python 上安卓没有“一键打包”**：必须有安卓工具链（SDK/NDK/JDK/Gradle），并选一种 Python 嵌入/运行方案。

## 2. 两种推荐架构

### 方案 B1（推荐）：原生壳 + Chaquopy 嵌入 Python 核心
- UI：**Kotlin + Jetpack Compose** 原生重写（棋盘 9×10 用 Compose Canvas，手感最好）
- Python：用 **Chaquopy**（Gradle 插件）把 `core/` `rules/` `ai/` 打成内置 Python 包
- 走法/胜负/将军等规则与“最佳走法计算”全部调用 Python（逻辑零重写）
- AI：先内置纯 Python 引擎（正常/揭棋都能跑）；后期再接入 `pikafish-armv8`（可选）
- 优点：UI 原生流畅、APK 小、Python 逻辑复用率最高；缺点：界面层要重写
- 里程碑：C0 原生壳 + Chaquopy 跑通规则单测 → C1 棋盘 UI → C2 录入/悔棋/保存 → C3 AI 分析 → C4 揭棋 → C5 打包签名

### 方案 B2：PySide6-for-Android + QML
- 尽量保留 Python（含用 QML 重画棋盘）
- 工具链：Qt for Android + JDK/NDK/SDK + `pyside6-android-deploy`
- 优点：可复用较多 Python/服务代码；缺点：工具链配置复杂、APK 体积大、QtWidgets 类代码仍需改成 QML、外部引擎打包更麻烦
- 适合“想最快先出个能装的 APK 尝鲜”，不适合追求手机体验

> 我的建议：**走 B1**——逻辑已分好层，B1 的总工作量通常比“把 QtWidgets 改成 QML 再排 Android 坑”更可控。

## 3. 安卓工具链清单（B1 为例）

| 组件 | 版本建议 | 说明 |
|---|---|---|
| JDK | 17 | Gradle/AGP 需要 |
| Android SDK | API 34/35 | 含 platform-tools、build-tools |
| Android NDK | 25/26（建议 26） | Chaquopy/原生引擎交叉编译用 |
| Gradle | 8.x + AGP 8.x | 与 Chaquopy 兼容组合 |
| Chaquopy | 15.x | `com.chaquo.python`，支持 Python 3.8–3.12 |
| Python 打包目标 | 3.12（在 Chaquopy 支持内选最高） | 现有代码为 3.13 语法兼容，需跑一遍兼容检查 |
| Pikafish(安卓) | `Android/pikafish-armv8`（官方发布 7z 内含） | 可选，后续接入 |
| 签名 | 自签名 keystore | 生成 `ch_chess.keystore` |

## 4. 需改动的代码点（盘点）

- `services/settings_service.py`：`default_settings_path()` 用 `%LOCALAPPDATA%` → 改为 Android 应用私有目录（如 `files_dir/settings.json`），保留“找不到就用默认值”
- `app/logger.py`：日志目录改为 `files_dir/logs`
- `engine/`（若接 Pikafish-Android）：把 armv8 二进制放进 `assets`，首启释放到私有目录 + chmod，UCCI 客户端经 subprocess 启动；可先用内置 AI 跳过此步
- `main.py`/`ui/`：桌面 QtWidgets 全部替换为原生触屏 UI（B1），只保留 `core/` `rules/` `ai/` `services/` 的 Python
- `models/settings.py`：无系统依赖，原样
- 文件对话框：安卓无 QFileDialog → 用系统“文档选择器（SAF）”替代保存/加载棋局
- 语言/界面：横向棋盘优先；提供横竖屏策略（推荐强制横屏或支持旋转）

## 5. 分阶段路线与工作量（供排期）

| 阶段 | 内容 | 交付 | 相对工作量 |
|---|---|---|---|
| M0 | 搭 Android 工程骨架 + Chaquopy + 跑通“Python 规则单测在手机上通过” | 空 UI 但能调 Python | 中 |
| M1 | Compose 棋盘 + 主菜单（选模式/我执方） | 能摆子、能走 | 大 |
| M2 | 录入（点击走子/手动录入/编辑）、悔棋/重做、回合 | 核心操作闭环 | 大 |
| M3 | 内置 AI 分析 + 自动代走 + 高亮 | 正常玩法可用 | 中 |
| M4 | 揭棋：暗子/翻子/身份选择弹窗/规则 | 揭棋可用 | 大 |
| M5 | 存取（SAF 导入导出 JSON）、日志、设置 | 数据持久化 | 中 |
| M6 | Pikafish-armv8 接入 + 调优、签名出正式 APK | 强引擎 APK | 中 |

> 注：M1/M2/M4 是 UI 大头；规则/AI 已就绪，M0 风险主要是工具链与 Python 版本兼容（3.13 → 3.12）。

## 6. 需要你先拍板的 4 个问题
1. 手机体验是否必须“好用”（走 B1 原生），还是只要能装上运行（可先走 B2 QML 尝鲜）？
2. 安卓端是否必须保留 **Pikafish 强引擎**？还是先用内置 AI（省 M6，先出 APK）？
3. 目标安卓版本：只支持你自己的手机（可就近真机调试），还是要上应用商店/兼容低版本？
4. UI 是否接受“主要横屏使用”？（棋盘 9×10 竖屏会很小）

## 7. 下一步（我可以先做、不依赖安卓工具链的事）
- 跑一遍 Python **3.12 兼容性检查**（当前 venv 是 3.13）并修掉不兼容点
- 把 `core/rules/ai/services` 里所有“桌面路径/系统调用”收敛成抽象接口（`Storage`/`EngineLauncher`），方便 B1 直接复用
- 给 M0 写好 Chaquopy 工程骨架与 Gradle 配置示例
- 把“强引擎”目录改成可配置下载（含安卓 armv8 二进制提取脚本）

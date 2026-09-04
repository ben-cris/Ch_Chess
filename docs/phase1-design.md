# 象棋辅助工具 · 第一阶段：项目总体设计

> 版本：v0.1（设计稿）
> 定位：本地单机「现实棋局镜像 + 模拟 + 记录 + 分析」工具。无网络、无在线对战、无外部软件自动化、不自动落子、不自动发送棋步。

## 0. 关键设计决策（TL;DR）

1. **纯本地单机**：PySide6 桌面应用；v1 不引入任何网络库；引擎仅通过本地子进程（UCCI）通信。
2. **分层单向依赖**：`UI → Services → Core/Domain → Rules → AI → Engine`，规则层不依赖 UI/AI，AI 依赖规则（获取合法走法与胜负），避免循环依赖。
3. **规则用「策略模式」共用**：`BaseRules` 抽象接口，`NormalRules` 与 `DarkChessRules` 独立实现；两者共享「棋子几何走法原语」与同一套 `GameState/Board/Piece/Move` 数据模型。
4. **双方都由用户录入**：「走子方」可显式指定（默认按回合自动推进，可手动覆盖并记录“回合修正”），因此红、黑走法都能录，AI 永不自动落子。
5. **红/黑选择只决定 AI 分析目标**：`user_side` 只影响“分析哪一方”与界面文案，不限制录入；AI 仅在轮到用户方时才给出“你的下一步”建议。
6. **揭棋揭示身份必须由用户选择**：弹模态对话框，候选按“颜色 + 剩余子力计数 + 规则约束”过滤；用户可取消整个录入；程序绝不猜测身份。
7. **揭棋 AI 用“信念状态 + 确定性采样”**：对暗子维护概率信念，采样若干“一致局面”做 α-β 搜索后按期望/投票合并，并标注不确定性。
8. **第一版引擎 = 内置 Python 搜索引擎（默认，覆盖两种模式）+ Pikafish UCCI 适配器（可选强引擎，仅正常模式）**；`MockEngine` 供测试。原因见第 8 节。
9. **“最优解”的诚实定义**：在当前局面、规则、深度、时间与引擎下，搜索得到的**评价最高的合法走法**；引擎证明强制杀时才优先并明示，否则不得宣称“必赢”。
10. **揭棋规则版本差异大**：采用「可配置规则预置 + 强制录入兜底」。默认预置 A（第 11 节），现实与预置不一致时允许用户确认后强制录入并记日志，因此规则差异不阻塞使用。

---

## 1. 完整项目架构

### 1.1 分层架构与依赖方向

```
┌────────────────────────────────────────────────────────────┐
│ 表现层 UI（PySide6）                                        │
│   main_window · board_widget · 各类 dialog · panel          │
│   职责：绘制棋盘、捕获点击、弹窗、展示分析结果；无业务规则   │
└───────────────▲────────────────────────────────────────────┘
                │ 只调用 Service 接口
┌───────────────┴────────────────────────────────────────────┐
│ 服务层 services                                            │
│   game_service        会话编排/命令（走子、悔棋、重做、编辑）│
│   move_input_service  录入状态机（含强制录入/回合修正）      │
│   ai_service          分析请求的后台调度                     │
│   save_service        保存/加载（JSON）                     │
│   import_export_service（预留）                             │
│   settings_service    设置读写                              │
└───────────────▲────────────────────────────────────────────┘
                │ 操作领域对象
┌───────────────┴────────────────────────────────────────────┐
│ 领域层 core + models                                       │
│   Piece · Position · Board · Move · GameState · History     │
│   GameConfig · Settings · AnalysisResult · 事件日志         │
│   职责：纯数据 + 不变量；不含 GUI，不依赖规则实现细节        │
└───────────────▲────────────────────────────────────────────┘
                │ rules_factory(mode) 路由
┌───────────────┴────────────────────────────────────────────┐
│ 规则层 rules                                               │
│   BaseRules(抽象) ── NormalRules / DarkChessRules           │
│   MoveValidator · WinChecker                               │
│   PieceMoveGenerator（明子几何走法原语，两模式共享）        │
│   DarkPresets（揭棋规则预置 A/B…）                          │
└───────────────▲────────────────────────────────────────────┘
                │ 局面（揭棋含信念状态）与合法走法
┌───────────────┴────────────────────────────────────────────┐
│ AI 层 ai                                                   │
│   AIAnalysisService · ChessEngine(统一接口)                │
│   Search(α-β/迭代加深) · Evaluation · MoveOrdering         │
│   DarkSearch(确定性采样) · BeliefState                     │
└───────────────▲────────────────────────────────────────────┘
                │ 本地子进程 / 直接调用
┌───────────────┴────────────────────────────────────────────┐
│ 引擎适配 engine                                            │
│   UcciClient · PikafishAdapter · ElephantEyeAdapter        │
│   MockEngine · EngineManager（生命周期/超时/降级）          │
└─────────────────────────────────────────────────────────────┘
```

依赖规则：上层可调用下层，下层不得 import 上层；`rules` 不 import `ui/ai`；`ai` 可依赖 `rules/core`；`engine` 只实现 `ai.ChessEngine` 接口。这样“把规则/搜索逻辑写进按钮事件”在结构上不可能发生。

### 1.2 线程模型

- GUI 主线程只做绘制与事件；耗时操作（AI 搜索、引擎通信）放入 `QThread`/`QRunnable` Worker。
- `ai_service` 暴露 `analyze_async(request, on_result, on_error)` 与 `stop()`；结果通过 Qt 信号回主线程。
- 引擎进程由 `EngineManager` 统一管理：启动、发送 `stop`、超时杀死、异常降级到内置引擎，进程退出时回收。

### 1.3 日志与异常

- `app/logger.py`：RotatingFileHandler，写入 `%LOCALAPPDATA%/XiangqiAssistant/logs/`；记录：开局、每次走子、揭示事件、回合修正、AI 请求/结果、引擎 I/O（debug 级）、异常堆栈。
- 统一 `AppError` 异常体系；UI 顶层 `sys.excepthook` 捕获未处理异常并弹窗 + 写日志，程序不崩溃。

---

## 2. 文件目录

在第一版开发中逐步创建（M1 开始建骨架），目标结构：

```
xiangqi_assistant/
├─ main.py                    # 入口：QApplication、日志、异常钩子、主窗口
├─ pyproject.toml             # 元数据 + 依赖（pyside6、pytest…）
├─ requirements.txt
├─ requirements-dev.txt
├─ README.md
├─ docs/
│  ├─ phase1-design.md        # 本文档
│  ├─ dark-chess-presets.md   # 揭棋规则预置说明（随 M0 确认更新）
│  └─ packaging.md            # EXE 打包说明
├─ app/
│  ├─ __init__.py
│  ├─ config.py               # 默认值、路径、引擎配置加载
│  ├─ constants.py            # 常量/显示名映射（帅将、仕士…）
│  └─ logger.py
├─ ui/
│  ├─ __init__.py
│  ├─ main_window.py          # 主窗口布局、菜单、状态栏
│  ├─ board_widget.py         # 棋盘绘制、点击/高亮/推荐走法动画
│  ├─ game_setup_dialog.py    # 新建棋局：模式、我执红/黑
│  ├─ move_input_dialog.py    # 录入走法：起点/终点/走子方/吃子/揭示
│  ├─ reveal_piece_dialog.py  # ★ 揭示身份选择（核心）
│  ├─ edit_board_dialog.py    # 编辑棋局/改回合/改身份/重置
│  ├─ analysis_panel.py       # 推荐走法、评分、深度、时间、候选列表
│  ├─ settings_dialog.py      # 引擎路径/思考时间/深度/预置选择
│  └─ dialogs.py              # 通用确认/提示
├─ core/
│  ├─ __init__.py
│  ├─ piece.py                # Side/PieceType/Piece
│  ├─ position.py             # Position(row,col)、坐标换算
│  ├─ board.py                # 9×10 棋盘、取子/放子/克隆、数量统计
│  ├─ move.py                 # Move（含 kind/揭示字段/记谱）
│  ├─ game_state.py           # GameState：模式/回合/用户方/状态/日志
│  ├─ history.py              # 走法历史 + 悔棋/重做栈
│  └─ events.py               # RevealEvent、CapturedPiece 快照
├─ rules/
│  ├─ __init__.py
│  ├─ base_rules.py           # BaseRules 抽象接口 + rules_factory
│  ├─ normal_rules.py         # 正常玩法
│  ├─ dark_chess_rules.py     # 揭棋玩法
│  ├─ dark_presets.py         # 揭棋规则预置（默认 A，可配置）
│  ├─ piece_move_generator.py # 明子几何走法原语（两模式共享）
│  ├─ move_validator.py       # 合法性门面（走法/揭示/回合）
│  └─ win_checker.py          # 将军/将死/困毙/暗吃胜负判定
├─ ai/
│  ├─ __init__.py
│  ├─ chess_engine.py         # ChessEngine 统一接口
│  ├─ search.py               # α-β + 迭代加深 + 杀棋检测
│  ├─ evaluation.py           # 子力/位置/威胁/杀棋评价
│  ├─ move_ordering.py        # 走法排序（吃子优先…）
│  ├─ belief_state.py         # 揭棋暗子信念（概率分布）
│  ├─ dark_search.py          # 确定性采样搜索（揭棋 AI）
│  └─ ai_analysis_service.py  # 分析编排：选引擎/规则、超时、取消
├─ engine/
│  ├─ __init__.py
│  ├─ ucci_client.py          # UCCI 协议子进程客户端
│  ├─ pikafish_adapter.py
│  ├─ elephant_eye_adapter.py # 预留
│  ├─ mock_engine.py          # 测试/冒烟用
│  └─ engine_manager.py       # 引擎发现、生命周期、降级
├─ services/
│  ├─ __init__.py
│  ├─ game_service.py
│  ├─ move_input_service.py
│  ├─ ai_service.py
│  ├─ save_service.py
│  ├─ import_export_service.py
│  └─ settings_service.py
├─ models/
│  ├─ __init__.py
│  ├─ game_config.py
│  ├─ settings.py
│  └─ analysis_result.py
├─ assets/pieces/             # 棋子图：红/黑 × 明/暗（未知面）
├─ tests/
│  ├─ conftest.py             # 局面构造工具、快照断言
│  ├─ test_board.py
│  ├─ test_normal_rules.py
│  ├─ test_dark_chess_rules.py
│  ├─ test_move_validator.py
│  ├─ test_win_checker.py
│  ├─ test_move_input.py      # 录入/回合/悔棋/重做
│  ├─ test_save_load.py
│  ├─ test_ai.py
│  └─ test_reveal_piece.py
├─ scripts/
│  ├─ dev.ps1                 # 建 venv、装依赖、跑测试
│  └─ build_exe.ps1           # PyInstaller 打包
└─ .gitignore
```

说明：`ai.ChessEngine` 是统一接口（第 8 节），`engine/` 只是它的具体实现；目录里把 `engine_manager.py` 放在 `engine/` 顶层便于扩展（Pikafish/ElephantEye 之外可再加引擎）。

---

## 3. 正常玩法与揭棋玩法如何共用规则引擎

### 3.1 共享领域模型

两种模式使用**同一套数据结构**，只是字段语义按模式解释：

```python
@dataclass
class Piece:
    side: Side            # RED / BLACK
    piece_type: PieceType # 明子=真实类型；暗子=UNKNOWN
    revealed: bool        # 是否已揭示
    position: Position    # (row 0..9, col 0..8)；row0=黑底线，row9=红底线
```

```python
@dataclass
class Move:
    side: Side
    move_kind: MoveKind   # NORMAL / REVEAL_IN_PLACE / MOVE_WITH_REVEAL / CAPTURE / ...
    frm: Position
    to: Position
    captured: PieceSnapshot | None
    revealed_type: PieceType | None   # 本步导致的揭示身份
    notation: str                     # 车二平五 等（按需生成）
```

`GameState` 记录：`mode`、`user_side`、`turn`、`board`、`move_history`、`reveal_history`、`captured_log`（用于剩余计数）、`status`、`settings`。

### 3.2 BaseRules 抽象接口（策略模式）

```python
class BaseRules(ABC):
    mode: GameMode

    def generate_legal_moves(self, state, side) -> list[Move]: ...
    def is_legal(self, state, move) -> bool: ...
    def apply_move(self, state, move) -> GameState: ...   # 纯函数：返回新状态 + 事件
    def legal_reveal_types(self, state, pos) -> list[PieceType]: ...  # 揭示候选
    def status(self, state) -> GameStatus: ...            # 将军/将死/困毙/暗吃将/结束
    def is_draw(self, state) -> bool: ...
```

- `NormalRules` 实现标准中国象棋：明子几何走法 + 将军/将死/困毙/将帅照面/不能送将。
- `DarkChessRules` 实现揭棋：暗子按预置规则行动；揭示是一等公民动作；胜负规则独立（见 3.4）。
- `GameService` 通过 `rules_factory(state.mode)` 取规则，**杜绝两种模式混淆**；AI 也从同一工厂取规则，保证“AI 按当前模式分析”。

### 3.3 共享的走法原语（避免重复实现）

`PieceMoveGenerator` 只做“某明子在空棋盘几何下的可达点”，与模式无关：

- 车/炮滑行与越子（炮需隔一子吃）；
- 马（蹩马腿）、象/相（塞象眼、不过河）、士/仕（九宫内斜走）、将/帅（九宫内直走 + 照面检查）、兵/卒（只进不退，过河可横）。

`NormalRules` 直接使用；`DarkChessRules` 对**已揭示明子**复用同一原语，只额外处理暗子与揭示语义。这样规则正确性只需在正常模式测试一次几何，揭棋复用同一实现，减少分支不一致。

### 3.4 两模式规则差异对照

| 维度 | NormalRules | DarkChessRules |
|---|---|---|
| 初始布局 | 固定标准布局，全部明子 | 按预置 A：双方子力暗置（是否洗牌见第 11 节 Q1） |
| 未知子 | 不存在 | `piece_type=UNKNOWN, revealed=False`；暗子走法由预置定义（默认按兵卒前进一格类规则，见 Q2） |
| 走法生成 | 明子原语 | 明子=原语；暗子=暗子规则；另含“原地揭示/走而揭示”等 move_kind |
| 吃子 | 明吃明 | 明吃暗/明吃明/暗吃…按预置（Q3/Q4），吃暗子时是否公开身份由预置与用户确认决定 |
| 将军/将死 | 标准规则 | 取决于“将帅是否可暗置、是否需公开将军”（Q6/Q7/Q8） |
| 胜负 | 将死/困毙 | 预置定义：常见为“吃掉对方将/帅即胜”，可能无“将死”概念（Q8） |
| 合法性校验 | MoveValidator(标准) | MoveValidator(暗) + 揭示候选计数校验 |
| 记谱/历史 | 走法历史 | 走法历史 + 揭示历史 + 被吃身份公开日志 |

### 3.5 胜负判定

`WinChecker` 是门面，内部按 `rules` 分发：正常模式判断将军/将死/困毙/长将（v1 只做基础重复检测，完整长将长捉规则列入后续）；揭棋模式按预置判断“将/帅被吃”等终局。`GameStatus` 枚举统一暴露给 UI/AI。

---

## 4. 用户如何录入双方现实棋局

### 4.1 录入状态机（MoveInputService）

```
空闲
 └─ 用户点「录入走法」或直接在棋盘上操作
     └─ ① 选起点（高亮该子，弹出可选终点）
         └─ ② 选终点（MoveInputDialog 汇总：走子方/是否吃子/是否揭示/身份）
             └─ ③ 揭棋且含揭示事件 → 弹 RevealPieceDialog（必选，可取消）
                 └─ ④ 校验 → 应用走法 → 推进回合 → 记日志 → 重算状态
```

### 4.2 「走子方」与「当前回合」的语义（关键设计）

- 程序不是对战程序，因此 `turn` 只是“**预期下一次现实走子方**”，不是权限。
- 录入对话框默认 `走子方 = turn`，应用后自动切换 `turn`；红、黑都可录，用户手动操作即可镜像现实。
- 若现实与程序不一致（漏录/录错/对手连走等）：用户可（a）在录入对话框中显式改“走子方”；（b）用「切换回合」按钮手动改回合。每次手动修正都会写入历史并打日志（`回合修正事件`），保证可追溯、可悔棋撤销。
- **结果**：录红、录黑、切回合、改错，全部支持；AI 永不自动执行录入。

### 4.3 引导录入 vs 强制录入

现实棋局可能违反程序内置规则（尤其揭棋变体），因此校验分两档：

1. **引导录入（默认）**：走法必须合法（起点有子、属于指定走子方、几何合法、不送将、暗子符合预置规则等）；不合法则提示并不应用。
2. **强制录入（编辑/修正）**：明确提示“该走法与当前规则不符”，用户二次确认后仍可应用并记录 `forced=True` 日志；用于“现实就是这样，程序规则版本不对”的情况。强制录入不改变规则引擎，仅放行本次录入。

配套功能：悔棋（撤销到上一步）、重做、编辑棋局（增删改子、改身份、改回合、重置棋盘）。编辑历史若发生在中盘，会以“分支历史”方式保留被废弃的走法记录并提示，避免误删用户数据。

---

## 5. 用户选择红/黑后，AI 如何分析用户方

1. `user_side` 在开局设置（GameSetupDialog：模式 + 我执红/黑），只用于：AI 分析目标、文案（“分析方：红方”）、推荐面板方向。**不限制录入**。
2. 用户点「分析最佳走法」→ `ai_service.analyze(game_state)`：
   - 若 `game_state.turn == user_side`：正常分析，给出“你的下一步”；
   - 若不等（例如你执红但当前该黑走）：提示“当前轮到黑方——请先录入黑方现实走法，再分析你的下一步”，并只提供“仅查看该方分析（非本回合）”的旁路选项，避免误导。
3. 分析在后台线程执行，返回 `AnalysisResult`（推荐走法、候选列表、评分、深度、思考时间、杀棋标志等），通过信号回 UI：棋盘高亮推荐走法，右侧面板列出 Top-N 候选与评分。
4. **“采用推荐”不等于自动落子**：点击后只是把推荐走法**预填进录入对话框**，仍需用户确认后才写入棋局历史——保证“AI 只分析、不落子”的边界。

---

## 6. 揭棋未知棋子身份选择如何实现

### 6.1 触发点

任何录入/走子/吃子动作中，凡现实棋局出现“某暗子被揭示”的事件（暗子走子后翻开、暗子吃子后翻开、被吃暗子公开身份、或用户主动修正），都必须走身份选择：

- 若该事件由“本步走子”产生 → 在 `MoveInputDialog` 确认后、应用前弹出；
- 若为事后修正 → 在「编辑棋局」中弹出同一对话框。

### 6.2 RevealPieceDialog 与候选过滤

弹出模态对话框：**“请选择该棋子揭开后的真实身份”**，按钮按行排列（车/马/炮/象/士/将/兵，按颜色显示 帅/仕/相/兵 或 将/士/象/卒）。

候选集合由 `BaseRules.legal_reveal_types(state, pos)` 计算，过滤条件：

1. **颜色**：只能是该棋子所属方；
2. **剩余子力计数**：`剩余[X] = 总数[X] − 棋盘上已明身份数[X] − 已被吃且身份公开数[X]`，候选类型必须 `剩余 > 0`（车≤2、马≤2、炮≤2、象/相≤2、士/仕≤2、兵/卒≤5、将/帅≤1，按预置可配置）；
3. **预置规则约束**（如“首翻不可为将/帅”等，若预置如此定义则排除）；
4. **局面一致性**：若该子刚完成某步移动，需与暗子走法规则相容（预置判定）。

对话框实时显示各类型剩余数量，帮助用户对照现实。

### 6.3 不许跳过、不许猜测

- 揭示事件**必须**完成身份选择才能应用；点“取消”= 放弃整步录入（状态回滚，可重录）。
- 程序不预选、不默认“车”之类的猜测；无任何“自动识别/自动猜测”路径。
- 用户若不确定：可取消 → 悔棋 → 重新录入 → 或在「编辑棋局」中修改身份（修改同样记录 `RevealEvent(source=MANUAL_CORRECTION)`）。
- 每次确认写入 `reveal_history`：`(位置, 颜色, 所选身份, 触发来源, 时间)`，随棋局保存。

---

## 7. 揭棋 AI 如何处理未知棋子

### 7.1 原则

- 揭棋是不完美信息游戏：明子确定；暗子身份未知（对双方、甚至对自己都未知）。
- AI 不能“看见”真相，只能做**不确定性推理**；因此 AI 内部维护的是**信念（概率分布）**，UI 上把它标注为“基于假设分布的期望推荐”，绝不显示为事实，也不等同于“程序擅自猜测身份”。

### 7.2 BeliefState（信念状态）

- 对每个暗子位置维护“可能的真实身份”概率分布；
- 先验：按预置布局（如随机暗置）→ 剩余子力均匀分布；
- 观测更新：揭示（身份确定）、被吃（身份公开，若预置如此）、走法模式（若暗子走法能透露信息）、用户手动修正；
- 约束：任何时刻各身份总数 ≤ 真实总数（与 6.2 同一计数来源）。

### 7.3 搜索算法（v1）

1. 从信念中采样 K 个“与观测一致”的完整局面（K 默认 8~16，可配置）；
2. 对每个采样局面，用**正常明子搜索**（α-β/迭代加深，深度默认 4~6）跑 `ChessEngine.get_best_move`；
3. 按“期望/投票”合并：以平均评分为主，若各采样首推分歧大则降低置信度并展示分歧（标准差）；
4. 说明局限：这是 PIMC（Perfect-Information Monte Carlo）近似——对手实际按自己的信息行动，AI 可能高估；因此在 UI 标注“不确定性高/低”，并允许设置更小的深度换取更稳的推荐。

### 7.4 与正常模式 AI 的统一

- 正常模式：`AIAnalysisService` 把局面转成内部表示 → 内置搜索或 Pikafish；
- 揭棋模式：`AIAnalysisService` 构造 `BeliefState` → `DarkSearch`（采样 + 内部搜索）；
- 二者都实现同一 `ChessEngine.get_best_move(...)` 接口（揭棋版是“带信念的搜索器”），UI/Service 层无感知。

---

## 8. 第一版采用哪种 AI 引擎

### 8.1 统一接口

```python
class ChessEngine(ABC):
    def configure(self, settings: EngineSettings) -> None: ...
    def get_best_move(self, position, time_limit_ms: int, max_depth: int,
                      stop_event) -> EngineResult: ...
    def stop(self) -> None: ...
```

`EngineResult`：走法、评分、深度、耗时、主变例、杀棋标志、引擎名。

### 8.2 推荐方案（第一版）

| 引擎 | 用途 | 说明 |
|---|---|---|
| **内置 Python 搜索**（默认） | 正常 + 揭棋 | α-β + 迭代加深 + 走法排序 + 杀棋检测；零外部依赖，离线开箱即用，CI 可测，可随 EXE 打包 |
| **Pikafish（UCCI）适配器**（可选“强引擎”） | 仅正常模式 | 用户在设置中指定 `pikafish` 路径后启用；独立子进程；支持 深度/时间/stop；异常自动降级到内置 |
| ElephantEye 适配器 | 预留 | 接口已留，后续按需接入 |
| **MockEngine** | 测试/冒烟 | 固定或脚本化返回，保证单测与 UI 演示不依赖真实引擎 |

### 8.3 为什么 v1 不“只依赖 Pikafish”

1. **揭棋无解**：Pikafish/ElephantEye 都是针对明子正常局面的强引擎，不支持暗子/信念状态，揭棋必须自研搜索；
2. **打包与许可**：Pikafish 为 GPL-3.0。v1 EXE 默认不内置 GPL 二进制，改为“用户可选下载/指定路径”，规避分发合规风险，也避免单文件 EXE 体积与杀软误报；
3. **可测性**：CI 无法保证下载外部引擎，内置引擎让单测稳定；
4. 内置引擎强度有限，但对“辅助分析”足够；后续版本可把 Pikafish 设为正常模式默认引擎。

---

## 9. “最优解”的定义

### 9.1 形式化定义

> 在给定局面 S、规则集 R（正常/揭棋预置）、轮到方 P、搜索深度上限 D、思考时间上限 T、引擎 E 的条件下：
> **最优解 = argmax_{m ∈ LegalMoves_R(S, P)} E(R, S·m)**，
> 其中 E 为引擎在 (D,T) 内对落子后局面的评价；若引擎证明某走法为**强制将死**（或按揭棋预置为强制吃将），则按“步数更少者更优”置顶；若证明为强制和/或必败则如实标注。

### 9.2 评分约定（展示口径统一）

- 评分以**分析方（用户方）视角**：正数 = 对该方有利；单位“分”（约 1 兵 = 100 分，可配置口径）；
- 杀棋分用 `±(MATE − 剩余步数)`，步数越少绝对值越大，避免“赢了但拖很久”被误判为更好；
- 和棋 ≈ 0；长将/循环在 v1 标记“和棋风险”，完整规则后续补。

### 9.3 展示与诚实条款

分析面板显示：推荐走法、起点/终点、棋子名、是否吃子、是否将军、是否杀棋、评分、深度、思考时间、候选 Top-N。

文案规则：

- 引擎证明强制杀 → “发现强制将死（N 步内）”；
- 未证明必胜 → 只显示“评分 +120（红优）/ 局面接近均势”等，**严禁**出现“这一步一定赢”；
- 揭棋 → 追加“基于假设分布，置信度：中/低”。

---

## 10. 第一版开发顺序

严格按依赖排序，每个里程碑有“可运行 + 测试通过”的验收标准：

| 里程碑 | 内容 | 验收标准 |
|---|---|---|
| **M0 设计冻结** | 本文档 + 揭棋规则预置确认（第 11 节 Q1–Q5 定稿，其余可配置） | 接口/目录/数据模型评审通过；规则问题有明确默认值 |
| **M1 基础** | 建项目、venv、依赖、logger/config；Piece/Board/初始布局；棋盘 GUI（静态绘制、点击高亮） | 程序可启动并显示标准棋盘；`test_board` 通过 |
| **M2 正常规则** | PieceMoveGenerator、NormalRules、MoveValidator、WinChecker（将军/将死/困毙/照面） | 第 19 节“正常玩法”测试全绿 |
| **M3 录入与会话** | 红黑选择、双方录入、回合推进/修正、悔棋/重做、编辑棋局、JSON 保存/加载 | “录入功能”测试全绿；手工流程可跑通 |
| **M4 AI** | ChessEngine 接口 → MockEngine → 内置搜索 → Pikafish 适配器；后台线程、超时、取消；分析面板 | “AI”测试全绿；正常模式能给出合法推荐 |
| **M5 揭棋** | 暗子模型、揭示流程、RevealPieceDialog、DarkChessRules、BeliefState/DarkSearch、揭示历史 | “揭棋功能”测试全绿；身份选择强制、不可跳过 |
| **M6 完善** | 设置、日志、异常处理、PyInstaller EXE、README、全量回归 | 全量 pytest 通过；EXE 在本机可运行 |

并行提示：M4 的内置搜索可在 M2 完成后与 M3 并行开发；M5 依赖 M3 的录入/保存框架与 M2 的走法原语；M0 的规则确认只阻塞 M5，不阻塞 M1–M4（默认预置先行）。

---

## 11. 需要提前确认的揭棋规则问题

揭棋没有唯一标准，不同平台/地区规则不同。下表列出需确认项；**默认预置 A** 供开发先行，标注“★”的 5 项建议在 M5 前由你拍板。无论最终规则如何，强制录入兜底保证工具可用。

| # | 问题 | 默认预置 A（建议） | 影响模块 | 需确认 |
|---|---|---|---|---|
| Q1 | 初始布局是否随机洗牌？范围如何（仅底线 9 子 / 己方全部 16 位）？ | 己方 16 子随机暗置在己方 16 个起始位 | 布局、信念先验 | ★ |
| Q2 | 暗子（未揭示）如何走？可否吃子？ | 暗子只能向前走一步（同未过河兵），不吃子或仅正前吃，见 Q3 | 走法生成、合法性 | ★ |
| Q3 | 暗子吃子时：被吃暗子是否公开身份？吃方暗子是否因此翻开？ | 暗子吃子即翻开自己并公开被吃子身份（该步不可悔改） | 揭示流程、AI 信念 | ★ |
| Q4 | “原地翻子”是否算一步？翻后本回合能否再走？ | 翻子算一步，翻后不能继续走（主流常见） | move_kind、UI 流程 | ★ |
| Q5 | 胜负判定：吃将/帅即胜？是否保留“将死/困毙”？将帅可否暗置、可否被暗吃？ | 吃将/帅即胜；将帅可暗置、可被暗吃；不启用将死/困毙 | WinChecker | ★ |
| Q6 | 将军如何体现？明将是否必须公开示警？被暗置将帅能否被“将军”？ | 不对暗将示警；明将按正常规则提示 | UI 状态、提示文案 | 可配置 |
| Q7 | 将帅照面规则在揭棋是否适用（暗置时双方不知位置）？ | 按明子适用；暗置不触发 | MoveValidator | 可配置 |
| Q8 | 被吃暗子的身份是否向双方公开并计入剩余计数？ | 公开并计入“已消耗” | captured_log、信念 | 可配置 |
| Q9 | 暗子过河后走法是否变化？能否横/退？ | 与 Q2 相同（只进不退），不因过河改变 | 走法生成 | 可配置 |
| Q10 | 是否有“首翻限制”（如开局前 N 步只能翻子）？ | 无 | 合法性 | 可配置 |
| Q11 | 重复局面/长将/长捉/自然限着如何判和？ | v1 仅检测三回合重复并提示，自动判和规则后续 | WinChecker | 可配置 |
| Q12 | 已揭示明子被吃后，历史记录是否保留身份？ | 保留（揭示历史 + 被吃日志） | 数据模型 | 无需 |
| Q13 | 用户现实中通过棋路推断出暗子身份，程序是否允许手动标注“疑似身份”？ | v1 只允许“已揭示/未揭示”二元 + 事后修正；不引入“疑似”标注（避免与事实混淆），接口预留 | 信念、编辑 | 可配置 |
| Q14 | 采用哪套主流规则为参照（腾讯/天天、JJ、联众…）？ | 以你提供的平台规则为准；否则用预置 A | dark_presets | ★（建议） |

> M0 只需你对 Q1–Q5（+Q14）给出选择；其余默认值在设置中可改，不影响开工。

---

## 附 A. 保存/加载 JSON 结构（草稿）

```jsonc
{
  "schema_version": 1,
  "mode": "dark",                 // normal | dark
  "user_side": "red",
  "turn": "black",
  "status": "playing",            // playing | check | checkmate | dark_king_captured | draw
  "dark_preset": "preset_a",
  "board": [ { "r": 0, "c": 4, "side": "black", "type": "unknown", "revealed": false }, ... ],
  "move_history": [ { "side": "black", "kind": "move_with_reveal", "from": [0,4], "to": [1,4],
                      "captured": null, "revealed_type": "rook", "notation": "…" } ],
  "reveal_history": [ { "pos": [0,4], "side": "black", "type": "rook", "source": "user", "ts": "…" } ],
  "captured_log": [ { "pos": [..], "side": "red", "type": "cannon", "revealed_when_captured": true } ],
  "settings": { "engine": "builtin", "time_ms": 2000, "depth": 12, "k_samples": 12 },
  "game_over": false,
  "updated_at": "…"
}
```

## 附 B. 测试矩阵（对应需求 §19）

- `test_normal_rules.py`：初始布局/子数、车不越子、蹩马腿、塞象眼、炮隔子吃、士不出九宫、象不过河、兵不后退、将帅照面、不能送将、将死/困毙判断。
- `test_move_input.py`：录红/录黑、回合切换、user_side 决定分析方、悔棋/重做、编辑/强制录入。
- `test_dark_chess_rules.py` + `test_reveal_piece.py`：暗子状态、明子状态、揭示候选过滤、身份选择不可跳过、揭示后合法走法、显示与揭示历史、AI 处理揭棋状态。
- `test_ai.py`：AI 返回合法走法、分析正确一方、不自动执行走法、识别简单杀棋、处理将军、超时正常返回、引擎异常不崩溃（MockEngine 抛错路径）。
- `test_save_load.py`：往返一致性与版本迁移。
- GUI 冒烟（offscreen 平台）单独脚本，不进单测主循环。

## 附 C. 技术选型与理由

- Python 3.11+、PySide6：Qt 跨平台桌面、QThread 后台。
- 不使用 `python-chess` 做规则引擎：其中国象棋支持有限且**无揭棋/明暗/揭示语义**，无法满足本项目核心；本项目自研轻量规则层（走法原语共享，测试覆盖），复杂度可控。
- pytest 单测；PyInstaller（onedir 优先）打包；不引入任何网络依赖。
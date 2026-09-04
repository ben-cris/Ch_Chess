"""内置开局库（Opening Book）。

把网络常见棋谱（华工象棋论坛《布局释疑》、xqdao《弈林新编·杨官璘》、xqipu 棋谱、
百度百科“平炮兑车”等条目）解析成「局面 -> 走法」表：
AI 在开局阶段直接查表走出主流开局，避免低层数搜索走出“怪招”。
仅用于正常玩法（揭棋随机暗置、无开局棋谱）。

解析方式：以文字记谱与 format_move 的输出做规范化比对，遍历当前方合法走法逐一匹配，
因此只收录“在当前局面确实合法”的招法；某行后续招法无法走通时，自动保留已走通的前缀。
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from core.board import new_normal_board
from core.game_state import GameMode, GameState
from core.move import Move
from core.piece import Side
from core.notation import format_move
from core.position import Position
from rules.normal_rules import NormalRules

BOOK_SOURCES = (
    "华工象棋论坛《布局释疑》系列、xqdao《弈林新编·杨官璘》、xqipu 棋谱站、"
    "百度百科“平炮兑车”等常见开局棋谱"
)

# 每行 = 从红方开始的回合序列（红黑交替）；数字为 ASCII 记谱（可含一二三…九）
BOOK_LINES: List[List[str]] = [
    # 1) 中炮直车七路马对屏风马（主流定式）
    ["炮二平五", "马8进7", "马二进三", "车9平8", "车一平二", "马2进3",
     "兵七进一", "卒7进1", "马八进七", "象3进5", "车二进六", "士4进5"],
    # 2) 中炮过河车七路马对屏风马平炮兑车
    ["炮二平五", "马8进7", "马二进三", "卒7进1", "车一平二", "车9平8",
     "车二进六", "马2进3", "兵七进一", "炮8平9", "车二平三", "炮9退1",
     "马八进七", "士4进5", "炮八平九", "车1平2"],
    # 3) 五七炮进三兵对屏风马（横车）
    ["炮二平五", "马8进7", "马二进三", "车9平8", "车一平二", "马2进3",
     "兵三进一", "卒3进1", "马八进九", "车1进1", "炮八平七", "马3进2",
     "马三进四", "象7进5", "马四进五", "马7进5"],
    # 4) 顺炮直车对横车（缓攻，杨官璘《弈林新编》）
    ["炮二平五", "炮8平5", "马二进三", "车9进1", "马八进九", "卒1进1",
     "炮八平七", "马2进1", "车九平八", "炮2进2", "炮五进四", "士4进5",
     "仕四进五", "马8进7", "炮五退一", "马7进5"],
    # 5) 顺炮横车破直车（《橘中秘》弃马十三招前奏）
    ["炮二平五", "炮8平5", "马二进三", "马8进7", "车一进一", "车9平8",
     "车一平六", "车8进6", "车六进七", "马2进1", "车九进一", "炮2进7"],
    # 6) 中炮对反宫马
    ["炮二平五", "马2进3", "马二进三", "炮8平6", "车一平二", "马8进7",
     "兵三进一", "车9进1", "兵七进一", "士4进5"],
    # 7) 仙人指路对卒底炮（红转中炮）
    ["兵七进一", "炮2平3", "炮八平五", "炮8平5", "马八进七", "马2进1",
     "车九平八", "马8进7", "兵三进一", "车9平8"],
    # 8) 仙人指路对卒底炮（黑快马进8）
    ["兵七进一", "炮2平3", "炮八平五", "马8进7", "马八进七", "卒7进1",
     "兵三进一", "象7进5"],
    # 9) 中炮七路马对屏风马（巡河炮，华工论坛）
    ["炮二平五", "马8进7", "马二进三", "车9平8", "车一平二", "马2进3",
     "兵七进一", "卒7进1", "马八进七", "炮8进4", "炮八进二", "象3进5",
     "兵三进一", "卒3进1"],
    # 10) 中炮对屏风马（红进三兵黑3卒，基本阵型）
    ["炮二平五", "马8进7", "马二进三", "车9平8", "车一平二", "马2进3",
     "兵三进一", "卒3进1", "车二进六", "象3进5"],
    # 11) 中炮对屏风马（红五九炮过河车）——常见变例
    ["炮二平五", "马8进7", "马二进三", "车9平8", "车一平二", "马2进3",
     "车二进六", "卒7进1", "马八进七", "士4进5", "炮八平九", "炮8平9",
     "车二平三", "炮9退1", "车九平八", "车1平2"],
    # 12) 中炮对列炮（红直车，黑列手炮）
    ["炮二平五", "炮2平5", "马二进三", "马8进7", "车一平二", "车9平8",
     "兵七进一", "卒7进1", "车二进六", "炮8平9", "车二平三", "车8进2"],
    # 13) 中炮过河车对屏风马左马盘河（黑跳盘河马反击）
    ["炮二平五", "马8进7", "马二进三", "车9平8", "车一平二", "马2进3",
     "兵七进一", "卒7进1", "车二进六", "马7进6", "马八进七", "象3进5"],
]

_CN_DIGITS = {
    "一": "1", "二": "2", "三": "3", "四": "4", "五": "5",
    "六": "6", "七": "7", "八": "8", "九": "9",
    "０": "0", "１": "1", "２": "2", "３": "3", "４": "4",
    "５": "5", "６": "6", "７": "7", "８": "8", "９": "9",
}


def _norm(text: str) -> str:
    s = text
    for k, v in _CN_DIGITS.items():
        s = s.replace(k, v)
    return s


class OpeningBook:
    """开局表：position_key -> 该局面下的棋谱走法列表。"""

    def __init__(self, lines: Optional[List[List[str]]] = None,
                 max_book_ply: int = 24) -> None:
        self._entries: Dict[str, List[Tuple[Position, Position]]] = {}
        self.max_book_ply = max_book_ply
        self.loaded = 0
        self.partial = 0
        self.failed = 0
        rules = NormalRules()
        for line in lines if lines is not None else BOOK_LINES:
            self._load_line(rules, line)

    def _load_line(self, rules: NormalRules, line: List[str]) -> None:
        board = new_normal_board()
        gs = GameState(GameMode.NORMAL, Side.RED, Side.RED, board)
        step = 0
        for i, text in enumerate(line):
            side = Side.RED if i % 2 == 0 else Side.BLACK
            if gs.turn is not side or len(gs.moves) >= self.max_book_ply:
                break
            found: Optional[Move] = None
            for mv in rules.generate_legal_moves(gs, side):
                if _norm(format_move(gs.board, mv)) == _norm(text):
                    found = mv
                    break
            if found is None:
                break  # 该行后续无法走通 → 保留已走通前缀
            key = gs.position_key()
            lst = self._entries.setdefault(key, [])
            pair = (found.frm, found.to)
            if pair not in lst:
                lst.append(pair)
            gs = rules.apply_move(gs, found)
            step += 1
        if step == len(line):
            self.loaded += 1
        elif step > 0:
            self.partial += 1
        else:
            self.failed += 1

    def lookup(self, state: GameState) -> Optional[List[Tuple[Position, Position]]]:
        """返回该局面可用的棋谱走法（内部坐标对），无则 None。"""
        if state.mode is not GameMode.NORMAL or state.over:
            return None
        if len(state.moves) >= self.max_book_ply:
            return None
        return self._entries.get(state.position_key())

    def first(self, state: GameState) -> Optional[Tuple[Position, Position]]:
        pairs = self.lookup(state)
        if pairs:
            return pairs[0]
        return None

    def __len__(self) -> int:
        return len(self._entries)


_book: Optional[OpeningBook] = None


def get_book() -> OpeningBook:
    global _book
    if _book is None:
        _book = OpeningBook()
    return _book
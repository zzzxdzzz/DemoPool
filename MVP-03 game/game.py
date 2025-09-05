#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ASCII Swim Race - 小胖妹 vs 小企鹅
玩法：
  - 敲击屏幕上泡泡里的字母即可“打爆泡泡”
  - 小写 -> 小胖妹加速；大写 -> 小企鹅加速
  - Q 退出；比赛结束后 R 重开
"""

import curses
import random
import string
import time
from dataclasses import dataclass

# --- 游戏配置 ---
TICK = 0.05                  # 主循环时间步（秒）
BUBBLE_SPAWN_CHANCE = 0.25   # 每 tick 生成泡泡的概率
BUBBLE_SPEED = 0.35          # 泡泡上浮速度（行/ tick）
BOOST_AMOUNT = 0.45          # 每次爆泡增加的加速度
BOOST_DECAY = 0.985          # 每 tick 衰减
BASE_SPEED = 0.06            # 基础速度（列/ tick）
MAX_BUBBLES = 30             # 画面上最多泡泡数量
SPRITE_PADDING = 2           # 泳道上下留白

# 一行角色“精灵”（尽量短，避免越界）
GIRL_SPRITE = "}=(^_^)=}"    # 双辫子小胖妹（两边花括号当辫子）
PENGUIN_SPRITE = "<( 'v' )>" # 小企鹅

@dataclass
class Bubble:
    x: int
    y: float
    ch: str  # 字母（区分大小写）

def clamp(v, lo, hi):
    return max(lo, min(hi, v))

def init_colors():
    if not curses.has_colors():
        return
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_CYAN,    -1)  # 泡泡
    curses.init_pair(2, curses.COLOR_YELLOW,  -1)  # 小胖妹
    curses.init_pair(3, curses.COLOR_MAGENTA, -1)  # 小企鹅
    curses.init_pair(4, curses.COLOR_GREEN,   -1)  # 进度/终点
    curses.init_pair(5, curses.COLOR_RED,     -1)  # 提示/胜利

def draw_centered(stdscr, row, text, attr=0):
    _, w = stdscr.getmaxyx()
    col = max(0, (w - len(text)) // 2)
    try:
        stdscr.addstr(row, col, text, attr)
    except curses.error:
        pass

def make_bubble(w, h):
    # 在左右内缩 4 列的范围里生成
    x = random.randint(4, max(4, w - 5))
    ch = random.choice(
        random.choice([string.ascii_lowercase, string.ascii_uppercase])
    )
    # 从底部附近冒泡
    return Bubble(x=x, y=h - 2, ch=ch)

def pop_matching_bubble(bubbles, key_char):
    # 找到同字母的“最低”（y 最大）的泡泡并移除
    idx, best_y = -1, -1.0
    for i, b in enumerate(bubbles):
        if b.ch == key_char and b.y > best_y:
            best_y = b.y
            idx = i
    if idx >= 0:
        return bubbles.pop(idx)
    return None

def main_game(stdscr):
    curses.curs_set(0)
    stdscr.nodelay(True)
    stdscr.timeout(0)
    init_colors()

    while True:
        # 初始化一局
        h, w = stdscr.getmaxyx()
        # 确保最小尺寸
        min_w, min_h = 70, 22
        if w < min_w or h < min_h:
            stdscr.erase()
            draw_centered(stdscr, h//2-1, "请把终端窗口放大一些（至少 70x22）", curses.color_pair(5))
            draw_centered(stdscr, h//2+1, f"当前：{w}x{h}，按 Q 退出", curses.A_DIM)
            stdscr.refresh()
            ch = stdscr.getch()
            if ch in (ord('q'), ord('Q')):
                return
            time.sleep(0.3)
            continue

        # 泳道位置
        lane_gap = 5
        girl_row = SPRITE_PADDING + 2
        peng_row = girl_row + lane_gap

        # 终点线位置
        finish_x = w - 6

        # 状态
        bubbles = []
        girl_x = 2.0
        peng_x = 2.0
        girl_boost = 0.0
        peng_boost = 0.0
        elapsed = 0.0
        winner = None
        help_shown = False

        # 主循环
        while True:
            start = time.time()
            stdscr.erase()

            # --- 输入 ---
            ch = stdscr.getch()
            if ch != -1:
                if ch in (ord('q'), ord('Q')):
                    return
                if ch == ord(' '):
                    # 空格：小憩一会儿，给孩子更容易打字
                    time.sleep(0.05)
                try:
                    key_char = chr(ch)
                except ValueError:
                    key_char = ''
                # 只处理 A-Za-z
                if key_char in string.ascii_letters:
                    popped = pop_matching_bubble(bubbles, key_char)
                    if popped:
                        if key_char.islower():
                            girl_boost += BOOST_AMOUNT
                        else:
                            peng_boost += BOOST_AMOUNT

            # --- 生成泡泡 ---
            if len(bubbles) < MAX_BUBBLES and random.random() < BUBBLE_SPAWN_CHANCE:
                bubbles.append(make_bubble(w, h))

            # --- 更新泡泡上浮 ---
            for b in bubbles:
                b.y -= BUBBLE_SPEED
            bubbles = [b for b in bubbles if b.y > 1]

            # --- 更新速度（基础 + 衰减的加速）---
            girl_boost *= BOOST_DECAY
            peng_boost *= BOOST_DECAY
            girl_x += BASE_SPEED + girl_boost * 0.25
            peng_x += BASE_SPEED + peng_boost * 0.25
            girl_x = clamp(girl_x, 2, finish_x)
            peng_x = clamp(peng_x, 2, finish_x)

            # --- 判胜 ---
            if not winner:
                if girl_x >= finish_x and peng_x >= finish_x:
                    winner = "平局！两位都到达终点！"
                elif girl_x >= finish_x:
                    winner = "小胖妹胜利！🎉"
                elif peng_x >= finish_x:
                    winner = "小企鹅胜利！🎉"

            # --- 绘制 UI ---
            # 标题与说明
            title = "ASCII 泳池竞速：小胖妹 vs 小企鹅"
            draw_centered(stdscr, 0, title, curses.A_BOLD)
            tip = "按小写字母=给小胖妹加速；按大写字母=给小企鹅加速；Q 退出"
            draw_centered(stdscr, 1, tip, curses.A_DIM)

            # 终点线
            for ry in range(SPRITE_PADDING, SPRITE_PADDING + lane_gap + 3):
                try:
                    stdscr.addch(ry, int(finish_x), '|', curses.color_pair(4))
                except curses.error:
                    pass
            try:
                stdscr.addstr(SPRITE_PADDING - 1, int(finish_x) - 2, "FIN", curses.color_pair(4) | curses.A_BOLD)
            except curses.error:
                pass

            # 角色
            try:
                stdscr.addstr(girl_row, int(girl_x), GIRL_SPRITE, curses.color_pair(2) | curses.A_BOLD)
            except curses.error:
                pass
            try:
                stdscr.addstr(peng_row, int(peng_x), PENGUIN_SPRITE, curses.color_pair(3) | curses.A_BOLD)
            except curses.error:
                pass

            # 进度条
            bar_w = w - 12
            def draw_progress(row, xval, color):
                filled = int((xval - 2) / max(1, (finish_x - 2)) * bar_w)
                filled = clamp(filled, 0, bar_w)
                try:
                    stdscr.addstr(row, 6, "[" + "=" * filled + " " * (bar_w - filled) + "]", color)
                except curses.error:
                    pass

            draw_progress(girl_row + 1, girl_x, curses.color_pair(2))
            draw_progress(peng_row + 1, peng_x, curses.color_pair(3))

            # 泡泡（() + 字母）
            for b in bubbles:
                y = int(b.y)
                if SPRITE_PADDING <= y < h - 1:
                    bubble_str = f"({b.ch})"
                    attr = curses.color_pair(1)
                    try:
                        stdscr.addstr(y, max(1, b.x - 1), bubble_str, attr)
                    except curses.error:
                        pass

            # 底部帮助
            if not help_shown:
                draw_centered(stdscr, h - 2, "提示：尽量在泡泡“低位”时击中，爆掉的是同字母里最低的那个。", curses.A_DIM)
                help_shown = True

            # 胜利提示
            if winner:
                draw_centered(stdscr, SPRITE_PADDING + lane_gap + 3, winner, curses.color_pair(5) | curses.A_BOLD)
                draw_centered(stdscr, SPRITE_PADDING + lane_gap + 5, "按 R 再来一局，或按 Q 退出", curses.A_BOLD)
                stdscr.refresh()
                # 等待 R/Q
                while True:
                    c = stdscr.getch()
                    if c in (ord('q'), ord('Q')):
                        return
                    if c in (ord('r'), ord('R')):
                        break
                    time.sleep(0.05)
                # 重开外层 while True（重新初始化一局）
                break

            stdscr.refresh()

            # 维持循环频率
            elapsed += TICK
            dt = time.time() - start
            if dt < TICK:
                time.sleep(TICK - dt)

def main():
    try:
        curses.wrapper(main_game)
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""بازی دوز (X-O) - آلفا نسخه Unlimited"""
import time
import random
import threading
import api
import storage

BOARD_EMPTY = "⬜"
BOARD_X = "❌"
BOARD_O = "⭕"

DOSS_GAMES = {}
ANON_DOSS = {}
DOSS_QUEUE = []

# ✅ تایماوت حذف شد - بازی‌ها unlimited هستن
# فقط یه پاکسازی خیلی سبک برای بازی‌های خیلی قدیمی (۲ ساعت)
DOSS_SOFT_TIMEOUT = 7200
_last_cleanup = [0]

# ✅ فاصله بین پیام‌ها (ضد اسپم)
SEND_DELAY = 1.2
BATCH_DELAY = 0.8


def _safe_send(chat_id, text, reply_to=0, parse_mode=None, markup=None):
    """ارسال با تأخیر ضد اسپم"""
    try:
        time.sleep(0.5)
        return api.send(chat_id, text, reply_to=reply_to,
                       parse_mode=parse_mode, markup=markup)
    except Exception as e:
        print(f"[doss:safe_send] {e}")
        return None


def _cleanup_old_games():
    """پاکسازی سبک - فقط بازی‌های خیلی قدیمی"""
    now = time.time()
    if now - _last_cleanup[0] < 600:
        return
    _last_cleanup[0] = now

    # فقط بازی‌های خیلی قدیمی (۲ ساعت)
    expired = []
    for cid, game in DOSS_GAMES.items():
        started = game.get("ts", 0)
        if started and now - started > DOSS_SOFT_TIMEOUT:
            expired.append(cid)
    for cid in expired:
        DOSS_GAMES.pop(cid, None)

    expired_anon = []
    for pair_id, game in ANON_DOSS.items():
        started = game.get("ts", 0)
        if started and now - started > DOSS_SOFT_TIMEOUT:
            expired_anon.append(pair_id)
    for pid in expired_anon:
        ANON_DOSS.pop(pid, None)

    if expired or expired_anon:
        print(f"[doss:cleanup] {len(expired) + len(expired_anon)} بازی قدیمی پاک شد")


def kb(rows):
    return {"inline_keyboard": [r for r in rows if r]}


def btn(text, data=None):
    return {"text": text, "callback_data": data}


def _empty_board():
    return [None] * 9


def _render_board(board, chat_id, p1, p2, current):
    rows = []
    for i in range(0, 9, 3):
        row = []
        for j in range(3):
            idx = i + j
            cell = board[idx]
            if cell == "X":
                label = BOARD_X
            elif cell == "O":
                label = BOARD_O
            else:
                label = BOARD_EMPTY
            row.append(btn(label, f"doss:play:{chat_id}:{idx}"))
        rows.append(row)
    return rows


def _check_winner(board):
    lines = [
        (0, 1, 2), (3, 4, 5), (6, 7, 8),
        (0, 3, 6), (1, 4, 7), (2, 5, 8),
        (0, 4, 8), (2, 4, 6),
    ]
    for a, b, c in lines:
        if board[a] and board[a] == board[b] == board[c]:
            return board[a]
    return None


def _is_full(board):
    return all(c is not None for c in board)


def _minimax(board, depth, is_max, alpha=-float("inf"), beta=float("inf")):
    winner = _check_winner(board)
    if winner == "O":
        return 10 - depth
    if winner == "X":
        return depth - 10
    if _is_full(board):
        return 0

    if is_max:
        best = -float("inf")
        for i in range(9):
            if board[i] is None:
                board[i] = "O"
                score = _minimax(board, depth + 1, False, alpha, beta)
                board[i] = None
                best = max(best, score)
                alpha = max(alpha, score)
                if beta <= alpha:
                    break
        return best
    else:
        best = float("inf")
        for i in range(9):
            if board[i] is None:
                board[i] = "X"
                score = _minimax(board, depth + 1, True, alpha, beta)
                board[i] = None
                best = min(best, score)
                beta = min(beta, score)
                if beta <= alpha:
                    break
        return best


def _bot_move(board):
    best_score = -float("inf")
    best_moves = []
    for i in range(9):
        if board[i] is None:
            board[i] = "O"
            score = _minimax(board, 0, False)
            board[i] = None
            if score > best_score:
                best_score = score
                best_moves = [i]
            elif score == best_score:
                best_moves.append(i)
    return random.choice(best_moves) if best_moves else None


# ============================================================
# شروع با ربات
# ============================================================
def start_with_bot(chat_id, user_id, user_name):
    try:
        _cleanup_old_games()
    except:
        pass

    board = _empty_board()
    game = {
        "type": "bot",
        "board": board,
        "p1": user_id,
        "p1_name": user_name,
        "p2": 0,
        "p2_name": "🤖 ربات",
        "turn": user_id,
        "symbols": {user_id: "X", 0: "O"},
        "ts": time.time(),
        "panel_msg_id": None,
    }
    DOSS_GAMES[chat_id] = game

    rows = _render_board(board, chat_id, user_id, 0, user_id)
    rows.append([btn("❌ لغو", "doss:cancel")])

    r = _safe_send(chat_id,
        "🎮 **بازی دوز**\n"
        "━━━━━━━━━━━━━━━\n\n"
        f"👤 {api.esc_md(user_name)}: ❌\n"
        f"🤖 ربات: ⭕\n\n"
        f"🎯 نوبت **{api.esc_md(user_name)}**\n"
        f"روی یه خونه بزن:",
        reply_to=0,
        parse_mode="Markdown",
        markup=kb(rows))

    if r and r.get("ok"):
        game["panel_msg_id"] = r["result"]["message_id"]
        DOSS_GAMES[chat_id] = game


# ============================================================
# شروع با دوست
# ============================================================
def start_with_friend(chat_id, p1_id, p1_name, p2_id, p2_name):
    try:
        _cleanup_old_games()
    except:
        pass

    board = _empty_board()
    game = {
        "type": "friend",
        "board": board,
        "p1": p1_id,
        "p1_name": p1_name,
        "p2": p2_id,
        "p2_name": p2_name,
        "turn": p1_id,
        "symbols": {p1_id: "X", p2_id: "O"},
        "ts": time.time(),
        "panel_msg_id": None,
    }
    DOSS_GAMES[chat_id] = game

    rows = _render_board(board, chat_id, p1_id, p2_id, p1_id)
    rows.append([btn("❌ لغو", "doss:cancel")])

    r = _safe_send(chat_id,
        "🎮 **بازی دوز**\n"
        "━━━━━━━━━━━━━━━\n\n"
        f"👤 {api.esc_md(p1_name)}: ❌\n"
        f"👤 {api.esc_md(p2_name)}: ⭕\n\n"
        f"🎯 نوبت **{api.esc_md(p1_name)}**",
        reply_to=0,
        parse_mode="Markdown",
        markup=kb(rows))

    if r and r.get("ok"):
        game["panel_msg_id"] = r["result"]["message_id"]
        DOSS_GAMES[chat_id] = game


# ============================================================
# صف ناشناس
# ============================================================
def add_to_queue(user_id, user_name, chat_id):
    global DOSS_QUEUE
    try:
        _cleanup_old_games()
    except:
        pass

    for u in DOSS_QUEUE:
        if u["id"] == user_id:
            return "already"
    DOSS_QUEUE.append({
        "id": user_id,
        "name": user_name,
        "chat_id": chat_id,
        "ts": time.time(),
    })
    if len(DOSS_QUEUE) >= 2:
        a = DOSS_QUEUE.pop(0)
        b = DOSS_QUEUE.pop(0)
        threading.Thread(target=_anon_doss_match, args=(a, b), daemon=True).start()
        return "matched"
    return "queued"


def remove_from_queue(user_id):
    global DOSS_QUEUE
    DOSS_QUEUE = [u for u in DOSS_QUEUE if u["id"] != user_id]


def _anon_doss_match(a, b):
    time.sleep(2)
    pair_id = f"{a['id']}_{b['id']}_{int(time.time())}"
    board = _empty_board()

    game = {
        "type": "anon",
        "board": board,
        "p1": a["id"],
        "p1_name": a["name"],
        "p2": b["id"],
        "p2_name": b["name"],
        "turn": a["id"],
        "symbols": {a["id"]: "X", b["id"]: "O"},
        "pair_id": pair_id,
        "ts": time.time(),
    }
    ANON_DOSS[pair_id] = game

    # ✅ ارسال با تأخیر بین دو نفر
    for idx, (u, sym) in enumerate([(a, "❌"), (b, "⭕")]):
        rows = []
        for i in range(0, 9, 3):
            row = []
            for j in range(3):
                idx_cell = i + j
                row.append(btn(BOARD_EMPTY, f"doss:anon:{pair_id}:{idx_cell}"))
            rows.append(row)

        opp_name = b["name"] if u["id"] == a["id"] else a["name"]

        try:
            if idx > 0:
                time.sleep(BATCH_DELAY)
            api.send(u["id"],
                "🎮 **دوز ناشناس**\n"
                "━━━━━━━━━━━━━━━\n\n"
                f"👤 تو: **{api.esc_md(u['name'])}** {sym}\n"
                f"🎭 حریف: **{api.esc_md(opp_name)}**\n\n"
                f"🎯 نوبت **{api.esc_md(u['name'])}**\n"
                f"_وقتی نوبتت شد، دکمه‌ها فعال می‌شن_",
                reply_to=0,
                markup=kb(rows),
                parse_mode="Markdown")
        except Exception as e:
            print(f"[anon_doss] {e}")


# ============================================================
# پردازش حرکت گپ
# ============================================================
def handle_play(chat_id, user_id, idx):
    game = DOSS_GAMES.get(chat_id)
    if not game:
        return False, "❌ بازی فعال نیست"

    board = game["board"]

    if idx < 0 or idx > 8 or board[idx] is not None:
        return False, "❌ این خونه پره"

    if game["turn"] != user_id:
        return False, "⏳ نوبت تو نیست!"

    sym = game["symbols"][user_id]
    board[idx] = sym

    panel_msg_id = game.get("panel_msg_id")

    winner = _check_winner(board)
    if winner:
        return True, _finish_game(chat_id, game, winner, panel_msg_id)

    if _is_full(board):
        return True, _finish_game(chat_id, game, None, panel_msg_id)

    if game["type"] == "bot":
        game["turn"] = 0
        _refresh_board(chat_id, game, panel_msg_id)

        time.sleep(1.5)
        bot_idx = _bot_move(board)
        if bot_idx is not None:
            board[bot_idx] = "O"
            winner = _check_winner(board)
            if winner:
                return True, _finish_game(chat_id, game, winner, panel_msg_id)
            if _is_full(board):
                return True, _finish_game(chat_id, game, None, panel_msg_id)

        game["turn"] = game["p1"]
        _refresh_board(chat_id, game, panel_msg_id)
    else:
        other = game["p2"] if user_id == game["p1"] else game["p1"]
        game["turn"] = other
        _refresh_board(chat_id, game, panel_msg_id)

    return True, "✅"


def _refresh_board(chat_id, game, panel_msg_id=None):
    board = game["board"]
    turn_id = game["turn"]

    if game["type"] == "bot":
        turn_name = game["p1_name"] if turn_id == game["p1"] else "🤖 ربات"
    else:
        turn_name = game["p1_name"] if turn_id == game["p1"] else game["p2_name"]

    rows = _render_board(board, chat_id, game["p1"], game["p2"], turn_id)
    rows.append([btn("❌ لغو", "doss:cancel")])

    p1_sym = "❌"
    p2_sym = "⭕"

    text = (
        f"🎮 **بازی دوز**\n"
        f"━━━━━━━━━━━━━━━\n\n"
        f"👤 {api.esc_md(game['p1_name'])}: {p1_sym}\n"
        f"👤 {api.esc_md(game['p2_name'])}: {p2_sym}\n\n"
        f"🎯 نوبت **{api.esc_md(turn_name)}**"
    )

    if panel_msg_id:
        try:
            time.sleep(0.4)
            api.edit_message(chat_id, panel_msg_id, text, markup=kb(rows), parse_mode="Markdown")
            return panel_msg_id
        except Exception as e:
            print(f"[doss:edit] {e}")

    r = api.send(chat_id, text, reply_to=0, markup=kb(rows), parse_mode="Markdown")
    if r and r.get("ok"):
        new_id = r["result"]["message_id"]
        game["panel_msg_id"] = new_id
        DOSS_GAMES[chat_id] = game
        return new_id
    return None


def _finish_game(chat_id, game, winner_sym, panel_msg_id=None):
    board = game["board"]
    DOSS_GAMES.pop(chat_id, None)

    if winner_sym is None:
        result = "🤝 **مساوی شد!**"
    else:
        winner_id = None
        for uid, sym in game["symbols"].items():
            if sym == winner_sym:
                winner_id = uid
                break

        if winner_id == 0:
            result = "🤖 **ربات برد!**"
        elif game["type"] == "bot":
            result = f"🎉 **{game['p1_name']} برد!**"
        elif winner_id == game["p1"]:
            result = f"🎉 **{game['p1_name']} برد!**"
        else:
            result = f"🎉 **{game['p2_name']} برد!**"

    lines = ""
    for i in range(0, 9, 3):
        row = ""
        for j in range(3):
            c = board[i + j]
            row += (BOARD_X if c == "X" else BOARD_O if c == "O" else BOARD_EMPTY) + " "
        lines += row + "\n"

    text = (
        f"🏁 **پایان بازی دوز**\n"
        f"━━━━━━━━━━━━━━━\n\n"
        f"{lines}\n"
        f"{result}"
    )

    if panel_msg_id:
        try:
            time.sleep(0.4)
            api.edit_message(chat_id, panel_msg_id, text, parse_mode="Markdown")
            return result
        except Exception as e:
            print(f"[doss:finish:edit] {e}")

    api.send(chat_id, text, reply_to=0, parse_mode="Markdown")
    return result


# ============================================================
# حرکت ناشناس
# ============================================================
def handle_anon_play(user_id, pair_id, idx):
    game = ANON_DOSS.get(pair_id)
    if not game:
        return False, "❌ بازی منقضی شده"

    if user_id not in (game["p1"], game["p2"]):
        return False, "❌ تو بازیکن نیستی!"

    if game["turn"] != user_id:
        return False, "⏳ نوبت تو نیست!"

    board = game["board"]
    if idx < 0 or idx > 8 or board[idx] is not None:
        return False, "❌ این خونه پره"

    sym = game["symbols"][user_id]
    board[idx] = sym

    winner = _check_winner(board)
    if winner or _is_full(board):
        _finish_anon(pair_id, game, winner)
        return True, "🏁"

    other = game["p2"] if user_id == game["p1"] else game["p1"]
    game["turn"] = other
    _refresh_anon(pair_id, game, user_id, other)
    return True, "✅"


def _refresh_anon(pair_id, game, played_id, next_id):
    board = game["board"]
    lines = ""
    for i in range(0, 9, 3):
        row = ""
        for j in range(3):
            c = board[i + j]
            row += (BOARD_X if c == "X" else BOARD_O if c == "O" else BOARD_EMPTY) + " "
        lines += row + "\n"

    try:
        time.sleep(0.3)
        api.send(played_id,
            f"✅ **حرکتت ثبت شد**\n\n{lines}\n_منتظر حریف..._",
            reply_to=0,
            parse_mode="Markdown")
    except: pass

    rows = []
    for i in range(0, 9, 3):
        row = []
        for j in range(3):
            idx = i + j
            cell = board[idx]
            if cell == "X":
                row.append(btn(BOARD_X, "doss:noop"))
            elif cell == "O":
                row.append(btn(BOARD_O, "doss:noop"))
            else:
                row.append(btn(BOARD_EMPTY, f"doss:anon:{pair_id}:{idx}"))
        rows.append(row)

    next_sym = game["symbols"].get(next_id, "?")
    sym_emoji = BOARD_X if next_sym == "X" else BOARD_O

    try:
        time.sleep(BATCH_DELAY)
        api.send(next_id,
            f"🎮 **نوبت توئه!** {sym_emoji}\n"
            f"━━━━━━━━━━━━━━━\n"
            f"{lines}\n"
            f"روی یه خونه بزن:",
            reply_to=0,
            markup=kb(rows),
            parse_mode="Markdown")
    except Exception as e:
        print(f"[anon_doss:next] {e}")


def _finish_anon(pair_id, game, winner_sym):
    board = game["board"]
    ANON_DOSS.pop(pair_id, None)

    lines = ""
    for i in range(0, 9, 3):
        row = ""
        for j in range(3):
            c = board[i + j]
            row += (BOARD_X if c == "X" else BOARD_O if c == "O" else BOARD_EMPTY) + " "
        lines += row + "\n"

    if winner_sym is None:
        result = "🤝 **مساوی!**"
    else:
        winner_id = None
        for uid, sym in game["symbols"].items():
            if sym == winner_sym:
                winner_id = uid
                break
        wname = game["p1_name"] if winner_id == game["p1"] else game["p2_name"]
        result = f"🎉 **{api.esc_md(wname)} برنده شد!**"

    text = (
        f"🏁 **پایان بازی دوز**\n"
        f"━━━━━━━━━━━━━━━\n"
        f"{lines}\n"
        f"{result}"
    )

    for idx, uid in enumerate([game["p1"], game["p2"]]):
        try:
            if idx > 0:
                time.sleep(BATCH_DELAY)
            api.send(uid, text, reply_to=0, parse_mode="Markdown")
        except: pass


def cancel_game(chat_id, user_id):
    game = DOSS_GAMES.get(chat_id)
    if not game:
        return False, "❌ بازی فعال نیست"
    if user_id not in (game["p1"], game["p2"]):
        return False, "❌ تو بازیکن نیستی!"
    DOSS_GAMES.pop(chat_id, None)
    return True, "❌ بازی لغو شد"
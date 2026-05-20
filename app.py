import streamlit as st
import pandas as pd
from datetime import datetime, date
import os

# =========================
# 基本設定
# =========================

st.set_page_config(
    page_title="27TD & Badugi Hand History",
    layout="wide"
)

CSV_FILE = "hand_history.csv"
PAT = "PAT"

RANKS = ["A", "K", "Q", "J", "T", "9", "8", "7", "6", "5", "4", "3", "2"]

SUITS = [
    {"symbol": "♠", "name": "spade"},
    {"symbol": "♥", "name": "heart"},
    {"symbol": "♣", "name": "club"},
    {"symbol": "♦", "name": "diamond"},
]

POSITIONS = ["UTG", "HJ", "CO", "BTN", "SB", "BB"]

PREDRAW_ORDER = ["UTG", "HJ", "CO", "BTN", "SB", "BB"]
POSTDRAW_ORDER = ["SB", "BB", "UTG", "HJ", "CO", "BTN"]

BET_STREETS = ["pre", "1st", "2nd", "3rd"]

STREET_LABELS = {
    "pre": "Pre",
    "1st": "1st",
    "2nd": "2nd",
    "3rd": "3rd",
}

FLOW_STEPS = [
    "pre_betting",
    "1st_change",
    "1st_betting",
    "2nd_change",
    "2nd_betting",
    "3rd_change",
    "3rd_betting",
    "done",
]

FLOW_LABELS = {
    "pre_betting": "Pre betting",
    "1st_change": "1st change",
    "1st_betting": "1st betting",
    "2nd_change": "2nd change",
    "2nd_betting": "2nd betting",
    "3rd_change": "3rd change",
    "3rd_betting": "3rd betting",
    "done": "完了",
}

NEXT_FLOW_STEP = {
    "pre_betting": "1st_change",
    "1st_change": "1st_betting",
    "1st_betting": "2nd_change",
    "2nd_change": "2nd_betting",
    "2nd_betting": "3rd_change",
    "3rd_change": "3rd_betting",
    "3rd_betting": "done",
    "done": "done",
}

PREV_FLOW_STEP = {
    "pre_betting": "pre_betting",
    "1st_change": "pre_betting",
    "1st_betting": "1st_change",
    "2nd_change": "1st_betting",
    "2nd_betting": "2nd_change",
    "3rd_change": "2nd_betting",
    "3rd_betting": "3rd_change",
    "done": "3rd_betting",
}

STEP_TO_BET_STREET = {
    "pre_betting": "pre",
    "1st_betting": "1st",
    "2nd_betting": "2nd",
    "3rd_betting": "3rd",
}

STEP_TO_CHANGE_STREET = {
    "1st_change": "1st",
    "2nd_change": "2nd",
    "3rd_change": "3rd",
}

HERO_CARD_FIELDS = [
    "predraw_hand",
    "d1_discard",
    "d1_draw",
    "d2_discard",
    "d2_draw",
    "d3_discard",
    "d3_draw",
]

MAX_HAND_SIZE = {
    "27TD": 5,
    "Badugi": 4,
}

CHANGE_OPTIONS_27TD = ["不明", "pat", "1c", "2c", "3c", "4c", "5c"]
CHANGE_OPTIONS_BADUGI = ["不明", "pat", "1c", "2c", "3c", "4c"]

PREDRAW_ACTIONS_NO_RAISE = ["fold", "check", "call", "raise"]
PREDRAW_ACTIONS_FACING_RAISE = ["call", "raise", "fold"]

POSTDRAW_ACTIONS_NO_BET = ["check", "bet"]
POSTDRAW_ACTIONS_FACING_BET = ["call", "raise", "fold"]

RESULT_OPTIONS = ["win", "lose", "split", "fold", "unknown"]

TAG_OPTIONS = [
    "pat", "1c", "2c", "3c",
    "9ロー判断", "8ロー判断",
    "rough badugi", "smooth badugi",
    "tri", "bluff", "snow",
    "bluff catch", "thin value",
    "mistake候補", "マルチウェイ",
    "相手pat", "相手1c", "相手2c",
    "相手aggressive", "相手passive",
]


# =========================
# セッション初期化
# =========================

def build_players(hero_position, opponent_count):
    players = [
        {
            "id": "H",
            "name": "Hero",
            "position": hero_position,
            "active": True,
        }
    ]

    available_positions = [p for p in POSITIONS if p != hero_position]

    for i in range(int(opponent_count)):
        pos = available_positions[i % len(available_positions)] if available_positions else "UTG"

        players.append({
            "id": f"V{i + 1}",
            "name": f"V{i + 1}",
            "position": pos,
            "active": True,
        })

    return players


def fresh_action_state():
    return {
        street: {
            "has_bet": False,
            "pending": [],
            "acted": [],
            "current_actor_id": None,
            "complete": False,
        }
        for street in BET_STREETS
    }


def fresh_change_index():
    return {
        "1st": 0,
        "2nd": 0,
        "3rd": 0,
    }


def init_state():
    if "game_type" not in st.session_state:
        st.session_state.game_type = "27TD"

    if "opponent_count" not in st.session_state:
        st.session_state.opponent_count = 1

    if "players" not in st.session_state:
        st.session_state.players = build_players("BB", st.session_state.opponent_count)

    if "hero_cards" not in st.session_state:
        st.session_state.hero_cards = {}

    for field in HERO_CARD_FIELDS:
        if field not in st.session_state.hero_cards:
            st.session_state.hero_cards[field] = []

    if "logs" not in st.session_state:
        st.session_state.logs = {
            "pre": [],
            "1st": [],
            "2nd": [],
            "3rd": [],
        }

    if "changes" not in st.session_state:
        st.session_state.changes = {
            "1st": {},
            "2nd": {},
            "3rd": {},
        }

    if "action_state" not in st.session_state:
        st.session_state.action_state = fresh_action_state()

    if "current_change_index" not in st.session_state:
        st.session_state.current_change_index = fresh_change_index()

    if "current_step" not in st.session_state:
        st.session_state.current_step = "pre_betting"


def reset_hand_all():
    st.session_state.hero_cards = {field: [] for field in HERO_CARD_FIELDS}

    st.session_state.logs = {
        "pre": [],
        "1st": [],
        "2nd": [],
        "3rd": [],
    }

    st.session_state.changes = {
        "1st": {},
        "2nd": {},
        "3rd": {},
    }

    st.session_state.action_state = fresh_action_state()
    st.session_state.current_change_index = fresh_change_index()
    st.session_state.current_step = "pre_betting"

    for p in st.session_state.players:
        p["active"] = True


init_state()


# =========================
# カード処理
# =========================

def card_id(rank, suit_symbol):
    return f"{rank}{suit_symbol}"


def suit_name_from_symbol(symbol):
    return {
        "♠": "spade",
        "♥": "heart",
        "♣": "club",
        "♦": "diamond",
    }.get(symbol, "unknown")


def cards_to_text(cards):
    if not cards:
        return ""

    if PAT in cards:
        return "PAT"

    return " ".join(cards)


def format_card_html(card):
    if not card:
        return ""

    if card == PAT:
        return '<span class="card-inline pat-card">PAT</span>'

    rank = card[:-1]
    suit = card[-1]
    cls = suit_name_from_symbol(suit)

    return f'<span class="card-inline {cls}">{rank}{suit}</span>'


def format_cards_html(cards):
    if not cards:
        return "—"

    if PAT in cards:
        return '<span class="card-inline pat-card">PAT</span>'

    return "".join(format_card_html(c) for c in cards)


def flatten_used_hero_cards():
    used = []

    for field in HERO_CARD_FIELDS:
        for card in st.session_state.hero_cards[field]:
            if card != PAT:
                used.append(card)

    return used


def calculate_hero_hand_after(stage):
    hand = list(st.session_state.hero_cards["predraw_hand"])

    if stage >= 1:
        if PAT not in st.session_state.hero_cards["d1_discard"]:
            for c in st.session_state.hero_cards["d1_discard"]:
                if c in hand:
                    hand.remove(c)
            hand.extend(st.session_state.hero_cards["d1_draw"])

    if stage >= 2:
        if PAT not in st.session_state.hero_cards["d2_discard"]:
            for c in st.session_state.hero_cards["d2_discard"]:
                if c in hand:
                    hand.remove(c)
            hand.extend(st.session_state.hero_cards["d2_draw"])

    if stage >= 3:
        if PAT not in st.session_state.hero_cards["d3_discard"]:
            for c in st.session_state.hero_cards["d3_discard"]:
                if c in hand:
                    hand.remove(c)
            hand.extend(st.session_state.hero_cards["d3_draw"])

    return hand


def current_hero_hand_before_field(field):
    if field == "predraw_hand":
        return []

    if field in ["d1_discard", "d1_draw"]:
        return calculate_hero_hand_after(0)

    if field in ["d2_discard", "d2_draw"]:
        return calculate_hero_hand_after(1)

    if field in ["d3_discard", "d3_draw"]:
        return calculate_hero_hand_after(2)

    return calculate_hero_hand_after(3)


def get_discard_field_from_draw_field(field):
    if field == "d1_draw":
        return "d1_discard"
    if field == "d2_draw":
        return "d2_discard"
    if field == "d3_draw":
        return "d3_discard"
    return None


def get_draw_field_from_discard_field(field):
    if field == "d1_discard":
        return "d1_draw"
    if field == "d2_discard":
        return "d2_draw"
    if field == "d3_discard":
        return "d3_draw"
    return None


def get_hero_fields_for_change(street):
    if street == "1st":
        return "d1_discard", "d1_draw"
    if street == "2nd":
        return "d2_discard", "d2_draw"
    if street == "3rd":
        return "d3_discard", "d3_draw"
    return None, None


def can_use_pat(field):
    return field in [
        "d1_discard",
        "d1_draw",
        "d2_discard",
        "d2_draw",
        "d3_discard",
        "d3_draw",
    ]


def can_add_hero_card(card, field, max_cards):
    cards_in_field = st.session_state.hero_cards[field]

    if card in cards_in_field:
        return True, "選択解除できます"

    if field == "d1_draw" and PAT in st.session_state.hero_cards["d1_discard"]:
        return False, "1stはPAT済みです"

    if field == "d2_draw" and PAT in st.session_state.hero_cards["d2_discard"]:
        return False, "2ndはPAT済みです"

    if field == "d3_draw" and PAT in st.session_state.hero_cards["d3_discard"]:
        return False, "3rdはPAT済みです"

    if field.endswith("_discard") and PAT in st.session_state.hero_cards[field]:
        return False, "PAT済みです"

    if len(cards_in_field) >= max_cards:
        return False, "枚数上限です"

    if field == "predraw_hand" or field.endswith("_draw"):
        if card in flatten_used_hero_cards():
            return False, "すでに使われています"
        return True, ""

    if field.endswith("_discard"):
        hand_before = current_hero_hand_before_field(field)

        if card not in hand_before:
            return False, "現在手札にないカードです"

        return True, ""

    return True, ""


def toggle_hero_card(card, field):
    max_cards = MAX_HAND_SIZE[st.session_state.game_type]

    if card in st.session_state.hero_cards[field]:
        st.session_state.hero_cards[field].remove(card)
        return

    ok, message = can_add_hero_card(card, field, max_cards)

    if ok:
        st.session_state.hero_cards[field].append(card)
    else:
        st.toast(message)


def set_pat_for_hero(field):
    if not can_use_pat(field):
        st.toast("PATはchangeの捨て欄または引き欄でのみ選択できます")
        return

    if field.endswith("_discard"):
        discard_field = field
        draw_field = get_draw_field_from_discard_field(field)
    else:
        draw_field = field
        discard_field = get_discard_field_from_draw_field(field)

    if PAT in st.session_state.hero_cards[discard_field]:
        st.session_state.hero_cards[discard_field] = []

        if draw_field:
            st.session_state.hero_cards[draw_field] = []

        return

    st.session_state.hero_cards[discard_field] = [PAT]

    if draw_field:
        st.session_state.hero_cards[draw_field] = []


def undo_card_field(field):
    if st.session_state.hero_cards[field]:
        st.session_state.hero_cards[field].pop()


def clear_card_field(field):
    st.session_state.hero_cards[field] = []


def hero_change_from_cards(street):
    if street == "1st":
        discard = st.session_state.hero_cards["d1_discard"]
        draw = st.session_state.hero_cards["d1_draw"]
    elif street == "2nd":
        discard = st.session_state.hero_cards["d2_discard"]
        draw = st.session_state.hero_cards["d2_draw"]
    elif street == "3rd":
        discard = st.session_state.hero_cards["d3_discard"]
        draw = st.session_state.hero_cards["d3_draw"]
    else:
        return "—"

    if PAT in discard:
        return "pat"

    if not discard and not draw:
        return "不明"

    if len(discard) != len(draw):
        return "不明"

    return f"{len(draw)}c"


def grid_visible_key(field, key_prefix):
    return f"show_grid_{key_prefix}_{field}"


def render_card_grid_for_field(field, key_prefix):
    visible_key = grid_visible_key(field, key_prefix)

    if visible_key not in st.session_state:
        st.session_state[visible_key] = False

    open_cols = st.columns([2, 2, 8], gap="small")

    with open_cols[0]:
        if st.button("カード表を開く", key=f"{key_prefix}_open_grid_{field}"):
            st.session_state[visible_key] = True
            st.rerun()

    with open_cols[1]:
        if st.button("カード表を閉じる", key=f"{key_prefix}_close_grid_{field}"):
            st.session_state[visible_key] = False
            st.rerun()

    if not st.session_state[visible_key]:
        st.caption("カード表は閉じています。必要なときだけ開いてください。")
        return

    if can_use_pat(field):
        pat_cols = st.columns([2, 10], gap="small")

        with pat_cols[0]:
            related_discard = (
                field
                if field.endswith("_discard")
                else get_discard_field_from_draw_field(field)
            )

            pat_label = (
                "PAT解除"
                if related_discard and PAT in st.session_state.hero_cards[related_discard]
                else "PAT"
            )

            if st.button(pat_label, key=f"{key_prefix}_pat_{field}"):
                set_pat_for_hero(field)
                st.session_state[visible_key] = False
                st.rerun()

        with pat_cols[1]:
            st.caption("PATを選ぶと、このchangeの捨て・引きは自動でスキップされ、カード表も閉じます。")

    for suit in SUITS:
        suit_symbol = suit["symbol"]
        suit_name = suit_name_from_symbol(suit_symbol)

        row_cols = st.columns([0.12] + [1] * len(RANKS), gap=None)

        with row_cols[0]:
            st.markdown(
                f'<div class="suit-symbol suit-symbol-{suit_name}">{suit_symbol}</div>',
                unsafe_allow_html=True,
            )

        for i, rank in enumerate(RANKS):
            card = card_id(rank, suit_symbol)
            max_cards = MAX_HAND_SIZE[st.session_state.game_type]

            selected_now = card in st.session_state.hero_cards[field]
            ok, _ = can_add_hero_card(card, field, max_cards)

            with row_cols[i + 1]:
                if selected_now:
                    label = f"✓{rank}"
                    disabled = False
                elif ok:
                    label = rank
                    disabled = False
                else:
                    label = "×"
                    disabled = True

                button_key = f"cardbtn_{key_prefix}_{field}_{suit_name}_{rank}"

                clicked = st.button(
                    label,
                    key=button_key,
                    disabled=disabled,
                )

                if clicked:
                    toggle_hero_card(card, field)
                    st.rerun()


def render_hero_predraw_input():
    st.markdown("#### Hero プリドローハンド入力")

    hand_size = MAX_HAND_SIZE[st.session_state.game_type]
    current_count = len(st.session_state.hero_cards["predraw_hand"])

    st.markdown(
        f'Hero hand：{format_cards_html(st.session_state.hero_cards["predraw_hand"])} '
        f'({current_count}/{hand_size})',
        unsafe_allow_html=True,
    )

    render_card_grid_for_field("predraw_hand", key_prefix="hero_predraw_inline")

    op_cols = st.columns(2)

    with op_cols[0]:
        if st.button("プリドローを1枚戻す"):
            undo_card_field("predraw_hand")
            st.rerun()

    with op_cols[1]:
        if st.button("プリドローをクリア"):
            clear_card_field("predraw_hand")
            st.rerun()


def render_hero_change_input(street):
    discard_field, draw_field = get_hero_fields_for_change(street)

    if discard_field is None:
        return

    st.markdown(f"#### Hero {STREET_LABELS[street]} change")

    st.markdown(
        f'捨て：{format_cards_html(st.session_state.hero_cards[discard_field])}',
        unsafe_allow_html=True,
    )

    st.markdown(
        f'引き：{format_cards_html(st.session_state.hero_cards[draw_field])}',
        unsafe_allow_html=True,
    )

    st.write(f"Hero change：**{hero_change_from_cards(street)}**")

    tab_discard, tab_draw = st.tabs(["捨てを入力", "引きを入力"])

    with tab_discard:
        render_card_grid_for_field(discard_field, key_prefix=f"{street}_discard_inline")

    with tab_draw:
        render_card_grid_for_field(draw_field, key_prefix=f"{street}_draw_inline")

    op_cols = st.columns(3)

    with op_cols[0]:
        if st.button(f"{STREET_LABELS[street]} 捨てを1枚戻す", key=f"undo_{street}_discard"):
            undo_card_field(discard_field)
            st.rerun()

    with op_cols[1]:
        if st.button(f"{STREET_LABELS[street]} 引きを1枚戻す", key=f"undo_{street}_draw"):
            undo_card_field(draw_field)
            st.rerun()

    with op_cols[2]:
        if st.button(f"{STREET_LABELS[street]} changeクリア", key=f"clear_{street}_hero_change"):
            clear_card_field(discard_field)
            clear_card_field(draw_field)
            st.rerun()


# =========================
# プレイヤー・順番処理
# =========================

def sort_players_by_order(players, street):
    order = PREDRAW_ORDER if street == "pre" else POSTDRAW_ORDER
    order_index = {pos: i for i, pos in enumerate(order)}

    return sorted(
        players,
        key=lambda p: order_index.get(p["position"], 999)
    )


def get_player_by_id(pid):
    for p in st.session_state.players:
        if p["id"] == pid:
            return p

    return None


def get_current_hero_position():
    hero = get_player_by_id("H")
    if hero:
        return hero["position"]
    return "BB"


def sync_players_to_opponent_count():
    target_villain_count = int(st.session_state.opponent_count)

    old_players = st.session_state.players if "players" in st.session_state else []
    old_hero = next((p for p in old_players if p["id"] == "H"), None)

    if old_hero is None:
        old_hero = {
            "id": "H",
            "name": "Hero",
            "position": "BB",
            "active": True,
        }

    new_players = [old_hero]
    old_villains = [p for p in old_players if p["id"] != "H"]

    used_positions = {old_hero["position"]}
    available_positions = [p for p in POSITIONS if p not in used_positions]

    for i in range(target_villain_count):
        villain_id = f"V{i + 1}"
        old_v = next((p for p in old_villains if p["id"] == villain_id), None)

        if old_v:
            pos = old_v["position"]
            active = old_v.get("active", True)
        else:
            pos = available_positions[i % len(available_positions)] if available_positions else "UTG"
            active = True

        new_players.append({
            "id": villain_id,
            "name": villain_id,
            "position": pos,
            "active": active,
        })

    st.session_state.players = new_players


def players_position_signature():
    if "players" not in st.session_state:
        return ""

    return "|".join([f'{p["id"]}:{p["position"]}' for p in st.session_state.players])


def reset_order_state_only():
    st.session_state.action_state = fresh_action_state()
    st.session_state.current_change_index = fresh_change_index()
    st.session_state.current_step = "pre_betting"

    for p in st.session_state.players:
        p["active"] = True

    st.session_state.logs = {
        "pre": [],
        "1st": [],
        "2nd": [],
        "3rd": [],
    }

    st.session_state.changes = {
        "1st": {},
        "2nd": {},
        "3rd": {},
    }


if "players_position_signature" not in st.session_state:
    st.session_state.players_position_signature = players_position_signature()


def get_active_players():
    return [p for p in st.session_state.players if p.get("active", True)]


def get_active_players_for_street(street):
    return sort_players_by_order(get_active_players(), street)


def get_ordered_ids(street):
    return [p["id"] for p in get_active_players_for_street(street)]


def get_next_id_after(street, current_id, candidate_ids):
    ordered_ids = get_ordered_ids(street)

    if not ordered_ids:
        return None

    if not candidate_ids:
        return None

    if current_id not in ordered_ids:
        return candidate_ids[0]

    start = ordered_ids.index(current_id)

    for offset in range(1, len(ordered_ids) + 1):
        pid = ordered_ids[(start + offset) % len(ordered_ids)]

        if pid in candidate_ids:
            return pid

    return candidate_ids[0]


def first_active_id(street):
    players = get_active_players_for_street(street)

    if not players:
        return None

    return players[0]["id"]


def ensure_street_started(street):
    state = st.session_state.action_state[street]

    if state["complete"]:
        return

    if state["current_actor_id"] is None:
        state["current_actor_id"] = first_active_id(street)


def current_actor(street):
    ensure_street_started(street)
    state = st.session_state.action_state[street]

    if state["current_actor_id"] is None:
        return None

    return get_player_by_id(state["current_actor_id"])


def get_current_changer(street):
    active_players = sort_players_by_order(get_active_players(), street)

    if not active_players:
        return None

    idx = st.session_state.current_change_index[street]

    if idx >= len(active_players):
        idx = 0
        st.session_state.current_change_index[street] = 0

    return active_players[idx]


def advance_changer(street):
    active_players = sort_players_by_order(get_active_players(), street)

    if not active_players:
        st.session_state.current_change_index[street] = 0
        return

    st.session_state.current_change_index[street] += 1

    if st.session_state.current_change_index[street] >= len(active_players):
        st.session_state.current_change_index[street] = 0
        st.session_state.current_step = f"{street}_betting"
        ensure_street_started(street)


def mark_player_folded(player_id):
    player = get_player_by_id(player_id)

    if player:
        player["active"] = False


def active_count():
    return len(get_active_players())


# =========================
# Betting処理
# =========================

def street_log_text(street):
    logs = st.session_state.logs[street]

    if not logs:
        return "—"

    return " / ".join([e["text"] for e in logs])


def complete_betting_street(street, auto_move=True):
    state = st.session_state.action_state[street]
    state["complete"] = True
    state["current_actor_id"] = None

    if auto_move:
        if street == "pre":
            st.session_state.current_step = "1st_change"
        elif street == "1st":
            st.session_state.current_step = "2nd_change"
        elif street == "2nd":
            st.session_state.current_step = "3rd_change"
        elif street == "3rd":
            st.session_state.current_step = "done"


def apply_action(street, action, record=True, auto_move=True):
    actor = current_actor(street)

    if actor is None:
        st.toast("アクション権利者がいません")
        return

    actor_id = actor["id"]
    state = st.session_state.action_state[street]

    if record:
        st.session_state.logs[street].append({
            "player_id": actor_id,
            "position": actor["position"],
            "action": action,
            "text": f'{actor_id} {actor["position"]} {action}',
        })

    if action == "fold":
        mark_player_folded(actor_id)

    if active_count() <= 1:
        state["complete"] = True
        state["current_actor_id"] = None
        st.session_state.current_step = "done"
        return

    if action in ["bet", "raise"]:
        state["has_bet"] = True

        active_ids = get_ordered_ids(street)
        state["pending"] = [pid for pid in active_ids if pid != actor_id]
        state["acted"] = [actor_id]
        state["current_actor_id"] = get_next_id_after(street, actor_id, state["pending"])
        return

    if state["has_bet"]:
        if actor_id in state["pending"]:
            state["pending"].remove(actor_id)

        state["pending"] = [
            pid for pid in state["pending"]
            if get_player_by_id(pid) and get_player_by_id(pid).get("active", True)
        ]

        if not state["pending"]:
            complete_betting_street(street, auto_move=auto_move)
            return

        state["current_actor_id"] = get_next_id_after(street, actor_id, state["pending"])
        return

    if actor_id not in state["acted"]:
        state["acted"].append(actor_id)

    active_ids = get_ordered_ids(street)
    remaining = [pid for pid in active_ids if pid not in state["acted"]]

    if not remaining:
        complete_betting_street(street, auto_move=auto_move)
        return

    state["current_actor_id"] = get_next_id_after(street, actor_id, remaining)


def get_available_actions(street):
    state = st.session_state.action_state[street]

    if street == "pre":
        if state["has_bet"]:
            return PREDRAW_ACTIONS_FACING_RAISE

        return PREDRAW_ACTIONS_NO_RAISE

    if state["has_bet"]:
        return POSTDRAW_ACTIONS_FACING_BET

    return POSTDRAW_ACTIONS_NO_BET


def recompute_all_from_logs():
    for p in st.session_state.players:
        p["active"] = True

    original_logs = {
        street: list(st.session_state.logs[street])
        for street in BET_STREETS
    }

    st.session_state.action_state = fresh_action_state()

    for street in BET_STREETS:
        st.session_state.logs[street] = []

        for entry in original_logs[street]:
            state = st.session_state.action_state[street]

            if state["current_actor_id"] is None and not state["complete"]:
                state["current_actor_id"] = entry["player_id"]

            apply_action(
                street,
                entry["action"],
                record=True,
                auto_move=False,
            )

    st.session_state.logs = original_logs


def undo_action_log(street):
    if not st.session_state.logs[street]:
        return

    st.session_state.logs[street].pop()
    recompute_all_from_logs()
    st.session_state.current_step = f"{street}_betting" if street != "pre" else "pre_betting"


def clear_action_log(street):
    st.session_state.logs[street] = []
    recompute_all_from_logs()
    st.session_state.current_step = f"{street}_betting" if street != "pre" else "pre_betting"


def reset_street_action(street):
    st.session_state.action_state[street] = fresh_action_state()[street]
    ensure_street_started(street)


def force_next_step():
    current = st.session_state.current_step
    st.session_state.current_step = NEXT_FLOW_STEP[current]

    if st.session_state.current_step in STEP_TO_BET_STREET:
        ensure_street_started(STEP_TO_BET_STREET[st.session_state.current_step])


def force_prev_step():
    current = st.session_state.current_step
    st.session_state.current_step = PREV_FLOW_STEP[current]


# =========================
# Change / 表示処理
# =========================

def get_change_options():
    if st.session_state.game_type == "Badugi":
        return CHANGE_OPTIONS_BADUGI

    return CHANGE_OPTIONS_27TD


def player_change_for_street(player_id, street):
    if player_id == "H":
        return hero_change_from_cards(street)

    return st.session_state.changes.get(street, {}).get(player_id, "不明")


def build_player_summary_df():
    rows = []

    for p in sort_players_by_order(st.session_state.players, "pre"):
        pid = p["id"]

        rows.append({
            "対象": "Hero" if pid == "H" else pid,
            "位置": p["position"],
            "状態": "active" if p.get("active", True) else "fold",
            "1st change": player_change_for_street(pid, "1st"),
            "2nd change": player_change_for_street(pid, "2nd"),
            "3rd change": player_change_for_street(pid, "3rd"),
        })

    return pd.DataFrame(rows)


def build_street_summary_df():
    rows = []

    rows.append({
        "Street": "Pre",
        "Change": "—",
        "Action Line": street_log_text("pre"),
    })

    for street in ["1st", "2nd", "3rd"]:
        change_parts = []

        for p in sort_players_by_order(st.session_state.players, street):
            pid = p["id"]
            change = player_change_for_street(pid, street)
            status = "" if p.get("active", True) else "(fold)"
            change_parts.append(f"{pid}{status}:{change}")

        rows.append({
            "Street": street,
            "Change": " / ".join(change_parts) if change_parts else "—",
            "Action Line": street_log_text(street),
        })

    return pd.DataFrame(rows)


# =========================
# CSV処理
# =========================

def load_data():
    if os.path.exists(CSV_FILE):
        return pd.read_csv(CSV_FILE)

    return pd.DataFrame()


def save_data(row):
    new_df = pd.DataFrame([row])

    if os.path.exists(CSV_FILE):
        old_df = pd.read_csv(CSV_FILE)
        df = pd.concat([old_df, new_df], ignore_index=True)
    else:
        df = new_df

    df.to_csv(CSV_FILE, index=False, encoding="utf-8-sig")
    return df


# =========================
# CSS
# =========================

st.markdown(
    """
    <style>
    /* 通常ボタン */
    div.stButton > button {
        width: 100%;
        min-height: 34px;
        font-size: 16px;
        font-weight: 800;
        border-radius: 5px;
        padding: 0;
        margin: 0;
    }

    div[data-testid="column"] {
        padding-left: 0rem !important;
        padding-right: 0rem !important;
    }

    div[data-testid="stHorizontalBlock"] {
        gap: 0rem !important;
    }

    /* カード表の行はスマホでも横並び固定 */
    div[data-testid="stHorizontalBlock"]:has(div[class*="st-key-cardbtn_"]) {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        gap: 0rem !important;
        align-items: stretch !important;
        width: 100% !important;
    }

    div[data-testid="stHorizontalBlock"]:has(div[class*="st-key-cardbtn_"]) > div {
        flex: 1 1 0 !important;
        min-width: 0 !important;
        padding-left: 0rem !important;
        padding-right: 0rem !important;
    }

    div[class*="st-key-cardbtn_"] {
        width: 100% !important;
    }

    div[class*="st-key-cardbtn_"] div.stButton {
        width: 100% !important;
    }

    div[class*="st-key-cardbtn_"] div.stButton > button {
        width: 100% !important;
        min-width: 0 !important;
        height: 46px !important;
        min-height: 46px !important;
        font-size: 22px !important;
        font-weight: 900 !important;
        border-radius: 3px !important;
        border: none !important;
        padding: 0 !important;
        margin: 0 !important;
        box-shadow: none !important;
    }

    .top-summary-box {
        padding: 12px 16px;
        border-radius: 14px;
        border: 2px solid #222222;
        background: #fffdf5;
        margin-bottom: 16px;
    }

    .top-summary-title {
        font-size: 20px;
        font-weight: 800;
        margin-bottom: 4px;
    }

    .top-summary-sub {
        font-size: 14px;
        color: #555555;
        margin-bottom: 8px;
    }

    .actor-box {
        padding: 14px 16px;
        border-radius: 14px;
        border: 2px solid #444;
        background: #f8fbff;
        margin-bottom: 12px;
        font-size: 20px;
        font-weight: 800;
    }

    .change-box {
        padding: 14px 16px;
        border-radius: 14px;
        border: 2px solid #666;
        background: #fff8f0;
        margin-bottom: 12px;
    }

    .complete-box {
        padding: 10px 14px;
        border-radius: 12px;
        border: 1px solid #3c763d;
        background: #eef9ee;
        margin-bottom: 12px;
        font-size: 16px;
        font-weight: 700;
    }

    .hand-box {
        padding: 10px 14px;
        border-radius: 10px;
        border: 1px solid #dddddd;
        background: #f8f8f8;
        margin-bottom: 8px;
        font-size: 18px;
    }

    .hand-title {
        font-weight: 700;
        margin-right: 8px;
    }

    .card-inline {
        display: inline-block;
        font-size: 24px;
        font-weight: 900;
        margin-right: 8px;
        margin-bottom: 4px;
        padding: 2px 6px;
        border-radius: 5px;
        color: white;
    }

    .spade {
        background: #111111;
        color: white;
    }

    .heart {
        background: #d62828;
        color: white;
    }

    .club {
        background: #2a9d2f;
        color: white;
    }

    .diamond {
        background: #1d4ed8;
        color: white;
    }

    .pat-card {
        background: #666666;
        color: white;
    }

    .suit-symbol {
        font-size: 18px;
        font-weight: 900;
        text-align: center;
        line-height: 46px;
        width: 12px;
        min-width: 12px;
        max-width: 12px;
        background: transparent !important;
    }

    .suit-symbol-spade {
        color: #111111 !important;
    }

    .suit-symbol-heart {
        color: #d62828 !important;
    }

    .suit-symbol-club {
        color: #2a9d2f !important;
    }

    .suit-symbol-diamond {
        color: #1d4ed8 !important;
    }

    div[class*="st-key-cardbtn_"][class*="_spade_"] button {
        background: #2f2f34 !important;
        color: white !important;
    }

    div[class*="st-key-cardbtn_"][class*="_heart_"] button {
        background: #c9362f !important;
        color: white !important;
    }

    div[class*="st-key-cardbtn_"][class*="_club_"] button {
        background: #4ea441 !important;
        color: white !important;
    }

    div[class*="st-key-cardbtn_"][class*="_diamond_"] button {
        background: #3155cc !important;
        color: white !important;
    }

    div[class*="st-key-cardbtn_"] button:disabled {
        background: #bdbdbd !important;
        color: #666666 !important;
    }

    div[class*="st-key-cardbtn_"] button:focus,
    div[class*="st-key-cardbtn_"] button:active {
        outline: 3px solid #ffd166 !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# =========================
# UI
# =========================

st.title("27TD & Badugi Hand History Tracker")


# =========================
# 基本設定
# =========================

st.subheader("基本設定")

setting_cols = st.columns(3)

with setting_cols[0]:
    st.radio(
        "ゲーム",
        ["27TD", "Badugi"],
        horizontal=True,
        key="game_type",
    )

with setting_cols[1]:
    st.number_input(
        "相手人数",
        min_value=1,
        max_value=7,
        step=1,
        key="opponent_count",
    )

sync_players_to_opponent_count()

with setting_cols[2]:
    if st.button("プレイヤー再作成"):
        sync_players_to_opponent_count()
        reset_hand_all()
        st.session_state.players_position_signature = players_position_signature()
        st.rerun()


with st.expander("プレイヤー設定", expanded=False):
    for p in st.session_state.players:
        cols = st.columns([1, 2, 2])

        with cols[0]:
            st.write(p["id"])

        with cols[1]:
            new_pos = st.selectbox(
                f'{p["id"]} position',
                POSITIONS,
                index=POSITIONS.index(p["position"]) if p["position"] in POSITIONS else 0,
                key=f'player_pos_{p["id"]}',
            )
            p["position"] = new_pos

        with cols[2]:
            p["active"] = st.checkbox(
                f'{p["id"]} active',
                value=p.get("active", True),
                key=f'player_active_{p["id"]}',
            )


new_pos_signature = players_position_signature()

if new_pos_signature != st.session_state.players_position_signature:
    st.session_state.players_position_signature = new_pos_signature
    reset_order_state_only()
    st.rerun()


# =========================
# トップ早見表
# =========================

st.markdown(
    f"""
    <div class="top-summary-box">
        <div class="top-summary-title">このハンドの早見表</div>
        <div class="top-summary-sub">
            現在の段階：{FLOW_LABELS[st.session_state.current_step]}。
            Heroのポジションは「プレイヤー設定」のH positionで管理します。
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown("#### ストリート別ログ")
st.dataframe(
    build_street_summary_df(),
    hide_index=True,
    use_container_width=True,
)

st.markdown("#### プレイヤー別チェンジ")
st.dataframe(
    build_player_summary_df(),
    hide_index=True,
    use_container_width=True,
)


# =========================
# 進行入力
# =========================

st.divider()
st.subheader("進行入力")

selected_step = st.selectbox(
    "現在の段階",
    FLOW_STEPS,
    index=FLOW_STEPS.index(st.session_state.current_step),
    format_func=lambda x: FLOW_LABELS[x],
)

if selected_step != st.session_state.current_step:
    st.session_state.current_step = selected_step

    if selected_step in STEP_TO_BET_STREET:
        ensure_street_started(STEP_TO_BET_STREET[selected_step])

    st.rerun()

current_step = st.session_state.current_step


# =========================
# Change入力
# =========================

if current_step in STEP_TO_CHANGE_STREET:
    change_street = STEP_TO_CHANGE_STREET[current_step]

    st.markdown(
        f"""
        <div class="change-box">
            <b>{STREET_LABELS[change_street]} change</b><br>
            現在change権利があるプレイヤーだけ表示します。
        </div>
        """,
        unsafe_allow_html=True,
    )

    changer = get_current_changer(change_street)

    if changer is None:
        st.warning("activeなプレイヤーがいません。")
    else:
        pid = changer["id"]

        st.markdown(
            f"""
            <div class="actor-box">
                現在のchange権利：{pid} {changer["position"]}
            </div>
            """,
            unsafe_allow_html=True,
        )

        if pid == "H":
            render_hero_change_input(change_street)

            hero_change = hero_change_from_cards(change_street)

            if hero_change == "不明":
                st.info("Heroの捨て・引き、またはPATを入力してください。")
            else:
                st.success(f"Hero change：{hero_change}")

                if st.button("Hero change完了"):
                    advance_changer(change_street)
                    st.rerun()

        else:
            change_options = get_change_options()

            if pid not in st.session_state.changes[change_street]:
                st.session_state.changes[change_street][pid] = "不明"

            old_change = st.session_state.changes[change_street][pid]

            selected_change = st.selectbox(
                f"{pid} {changer['position']} change",
                change_options,
                index=change_options.index(old_change) if old_change in change_options else 0,
                key=f"current_change_{change_street}_{pid}",
            )

            st.session_state.changes[change_street][pid] = selected_change

            if selected_change == "不明":
                st.info("チェンジ枚数を選んでください。")
            else:
                if selected_change != old_change:
                    advance_changer(change_street)
                    st.rerun()

                if st.button(f"{pid} change完了"):
                    advance_changer(change_street)
                    st.rerun()

    st.markdown("#### change状況")

    for p in sort_players_by_order(get_active_players(), change_street):
        pid = p["id"]
        st.write(f"{pid} {p['position']}：{player_change_for_street(pid, change_street)}")


# =========================
# Betting入力
# =========================

elif current_step in STEP_TO_BET_STREET:
    street = STEP_TO_BET_STREET[current_step]
    ensure_street_started(street)

    st.write(f"現在のbetting：**{STREET_LABELS[street]}**")

    state = st.session_state.action_state[street]

    if state["complete"]:
        st.markdown(
            f"""
            <div class="complete-box">
                {STREET_LABELS[street]} betting は完了しています。
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        actor = current_actor(street)

        if actor is None:
            st.warning("activeなプレイヤーがいません。")
        else:
            st.markdown(
                f"""
                <div class="actor-box">
                    現在のアクション権利：{actor["id"]} {actor["position"]}
                </div>
                """,
                unsafe_allow_html=True,
            )

            if actor["id"] == "H" and street == "pre":
                render_hero_predraw_input()

                hand_size = MAX_HAND_SIZE[st.session_state.game_type]
                current_count = len(st.session_state.hero_cards["predraw_hand"])

                if current_count < hand_size:
                    st.info(f"Heroのプリドローハンドを{hand_size}枚入力すると、アクションを選べます。")
                    action_disabled = True
                else:
                    action_disabled = False
            else:
                action_disabled = False

            action_options = get_available_actions(street)
            action_cols = st.columns(len(action_options))

            for i, action in enumerate(action_options):
                with action_cols[i]:
                    if st.button(
                        action,
                        key=f"quick_action_{street}_{action}",
                        disabled=action_disabled,
                    ):
                        apply_action(street, action, record=True, auto_move=True)
                        st.rerun()

            if state["has_bet"]:
                st.caption("bet/raiseに直面中：call / raise / fold")
            else:
                if street == "pre":
                    st.caption("まだraiseなし：fold / check / call / raise")
                else:
                    st.caption("まだbetなし：check / bet")

    st.markdown("#### 現在のログ")

    for s in BET_STREETS:
        done = " ✅" if st.session_state.action_state[s]["complete"] else ""
        st.write(f"**{STREET_LABELS[s]}{done}**：{street_log_text(s)}")

    log_ops = st.columns(3)

    with log_ops[0]:
        if st.button("1つ戻す"):
            undo_action_log(street)
            st.rerun()

    with log_ops[1]:
        if st.button("このbettingクリア"):
            clear_action_log(street)
            st.rerun()

    with log_ops[2]:
        if st.button("このbettingリセット"):
            clear_action_log(street)
            reset_street_action(street)
            st.rerun()


# =========================
# 完了
# =========================

else:
    st.markdown(
        """
        <div class="complete-box">
            このハンドの入力フローは完了しています。必要なら保存してください。
        </div>
        """,
        unsafe_allow_html=True,
    )


move_ops = st.columns(2)

with move_ops[0]:
    if st.button("前の段階へ"):
        force_prev_step()
        st.rerun()

with move_ops[1]:
    if st.button("次の段階へ"):
        force_next_step()
        st.rerun()


# =========================
# Hero 手札推移
# =========================

st.divider()
st.subheader("Hero 手札推移")

hand_predraw = calculate_hero_hand_after(0)
hand_after_1 = calculate_hero_hand_after(1)
hand_after_2 = calculate_hero_hand_after(2)
hand_final = calculate_hero_hand_after(3)

hand_cols = st.columns(4)

with hand_cols[0]:
    st.markdown(
        f"""
        <div class="hand-box">
            <span class="hand-title">プリドロー：</span><br>
            {format_cards_html(hand_predraw)}
        </div>
        """,
        unsafe_allow_html=True,
    )

with hand_cols[1]:
    st.markdown(
        f"""
        <div class="hand-box">
            <span class="hand-title">1st後：</span><br>
            {format_cards_html(hand_after_1)}
        </div>
        """,
        unsafe_allow_html=True,
    )

with hand_cols[2]:
    st.markdown(
        f"""
        <div class="hand-box">
            <span class="hand-title">2nd後：</span><br>
            {format_cards_html(hand_after_2)}
        </div>
        """,
        unsafe_allow_html=True,
    )

with hand_cols[3]:
    st.markdown(
        f"""
        <div class="hand-box">
            <span class="hand-title">最終：</span><br>
            {format_cards_html(hand_final)}
        </div>
        """,
        unsafe_allow_html=True,
    )


# =========================
# 詳細ログ表示
# =========================

st.divider()
st.subheader("詳細ログ")

detail_cols = st.columns(4)

for idx, s in enumerate(BET_STREETS):
    with detail_cols[idx]:
        st.markdown(f"### {STREET_LABELS[s]}")
        st.write(street_log_text(s))

        if s != "pre":
            st.markdown("**Change**")

            for p in sort_players_by_order(st.session_state.players, s):
                st.write(f'{p["id"]} {p["position"]}: {player_change_for_street(p["id"], s)}')


# =========================
# 基本情報・結果
# =========================

st.divider()
st.subheader("基本情報・結果")

b1, b2, b3, b4, b5 = st.columns(5)

with b1:
    played_date = st.date_input("日付", value=date.today())

with b2:
    tournament_name = st.text_input("大会名", placeholder="例：27TD & Badugi Mix")

with b3:
    result = st.selectbox("結果", RESULT_OPTIONS)

with b4:
    profit = st.number_input("収支", value=0.0, step=1.0)

with b5:
    mistake_level = st.selectbox("ミス度", ["なし", "小", "中", "大", "要検討"])

st.subheader("メモ・タグ")

tags = st.multiselect("タグ", TAG_OPTIONS)

note = st.text_area(
    "メモ",
    placeholder="例：BTN raise / BB call → 1st change BB 1c BTN 1c → BB check / BTN bet / BB call"
)


# =========================
# 保存
# =========================

st.divider()

if st.button("保存", type="primary"):
    max_cards = MAX_HAND_SIZE[st.session_state.game_type]

    if len(st.session_state.hero_cards["predraw_hand"]) != max_cards:
        st.error(f'{st.session_state.game_type}のプリドローハンドは{max_cards}枚選んでください。')
    else:
        hand_after_1 = calculate_hero_hand_after(1)
        hand_after_2 = calculate_hero_hand_after(2)
        hand_final = calculate_hero_hand_after(3)

        hero_player = get_player_by_id("H")
        hero_position = hero_player["position"] if hero_player else "不明"

        row = {
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "date": played_date,
            "tournament": tournament_name,
            "game_type": st.session_state.game_type,

            "hero_position": hero_position,
            "opponent_count": st.session_state.opponent_count,

            "hero_predraw_hand": cards_to_text(st.session_state.hero_cards["predraw_hand"]),

            "hero_d1_discard": cards_to_text(st.session_state.hero_cards["d1_discard"]),
            "hero_d1_draw": cards_to_text(st.session_state.hero_cards["d1_draw"]),
            "hero_hand_after_1": cards_to_text(hand_after_1),

            "hero_d2_discard": cards_to_text(st.session_state.hero_cards["d2_discard"]),
            "hero_d2_draw": cards_to_text(st.session_state.hero_cards["d2_draw"]),
            "hero_hand_after_2": cards_to_text(hand_after_2),

            "hero_d3_discard": cards_to_text(st.session_state.hero_cards["d3_discard"]),
            "hero_d3_draw": cards_to_text(st.session_state.hero_cards["d3_draw"]),
            "hero_final_hand": cards_to_text(hand_final),

            "pre_action_line": street_log_text("pre"),
            "first_action_line": street_log_text("1st"),
            "second_action_line": street_log_text("2nd"),
            "third_action_line": street_log_text("3rd"),

            "result": result,
            "profit": profit,
            "mistake_level": mistake_level,
            "tags": ",".join(tags),
            "note": note,
        }

        for p in st.session_state.players:
            pid = p["id"]
            row[f"{pid}_position"] = p["position"]
            row[f"{pid}_active_final"] = p.get("active", True)

            if pid != "H":
                row[f"{pid}_1st_change"] = st.session_state.changes["1st"].get(pid, "不明")
                row[f"{pid}_2nd_change"] = st.session_state.changes["2nd"].get(pid, "不明")
                row[f"{pid}_3rd_change"] = st.session_state.changes["3rd"].get(pid, "不明")
            else:
                row[f"{pid}_1st_change"] = hero_change_from_cards("1st")
                row[f"{pid}_2nd_change"] = hero_change_from_cards("2nd")
                row[f"{pid}_3rd_change"] = hero_change_from_cards("3rd")

        save_data(row)
        st.success("保存しました。")
        reset_hand_all()
        st.rerun()


# =========================
# 保存済みデータ
# =========================

st.divider()
st.subheader("保存済みハンド")

df = load_data()

if df.empty:
    st.info("まだ保存済みハンドはありません。")
else:
    st.dataframe(df, use_container_width=True)

    csv = df.to_csv(index=False).encode("utf-8-sig")

    st.download_button(
        "CSVダウンロード",
        data=csv,
        file_name="hand_history.csv",
        mime="text/csv",
    )

    st.subheader("簡易集計")

    m1, m2, m3 = st.columns(3)

    with m1:
        st.metric("記録ハンド数", len(df))

    with m2:
        if "profit" in df.columns:
            st.metric("合計収支", df["profit"].sum())

    with m3:
        if "result" in df.columns:
            st.metric("勝利数", (df["result"] == "win").sum())

    if "game_type" in df.columns:
        st.write("ゲーム別ハンド数")
        st.bar_chart(df["game_type"].value_counts())

    if "hero_position" in df.columns and "profit" in df.columns:
        st.write("Heroポジション別収支")
        st.bar_chart(df.groupby("hero_position")["profit"].sum())

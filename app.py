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
    {"symbol": "♦", "name": "diamond"},
    {"symbol": "♣", "name": "club"},
]

POSITIONS = ["UTG", "HJ", "CO", "BTN", "SB", "BB"]

PREDRAW_ORDER = ["UTG", "HJ", "CO", "BTN", "SB", "BB"]
POSTDRAW_ORDER = ["SB", "BB", "UTG", "HJ", "CO", "BTN"]

STREETS = ["pre", "1st", "2nd", "3rd"]

STREET_LABELS = {
    "pre": "Pre",
    "1st": "1st",
    "2nd": "2nd",
    "3rd": "3rd",
}

NEXT_STREET = {
    "pre": "1st",
    "1st": "2nd",
    "2nd": "3rd",
    "3rd": None,
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

HERO_CARD_FIELD_LABELS = {
    "predraw_hand": "プリドローハンド",
    "d1_discard": "1st change 捨て",
    "d1_draw": "1st change 引き",
    "d2_discard": "2nd change 捨て",
    "d2_draw": "2nd change 引き",
    "d3_discard": "3rd change 捨て",
    "d3_draw": "3rd change 引き",
}

MAX_HAND_SIZE = {
    "27TD": 5,
    "Badugi": 4,
}

CHANGE_OPTIONS_27TD = ["不明", "pat", "1c", "2c", "3c", "4c", "5c"]
CHANGE_OPTIONS_BADUGI = ["不明", "pat", "1c", "2c", "3c", "4c"]

PREDRAW_ACTIONS_NO_BET = ["fold", "check", "call", "raise"]
PREDRAW_ACTIONS_FACING_BET = ["call", "raise", "fold"]

POSTDRAW_ACTIONS_NO_BET = ["check", "bet"]
POSTDRAW_ACTIONS_FACING_BET = ["call", "raise", "fold"]

RESULT_OPTIONS = ["win", "lose", "split", "fold", "unknown"]

TAG_OPTIONS = [
    "pat",
    "1c",
    "2c",
    "3c",
    "9ロー判断",
    "8ロー判断",
    "rough badugi",
    "smooth badugi",
    "tri",
    "bluff",
    "snow",
    "bluff catch",
    "thin value",
    "mistake候補",
    "マルチウェイ",
    "相手pat",
    "相手1c",
    "相手2c",
    "相手aggressive",
    "相手passive",
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
        for street in STREETS
    }


def init_state():
    if "game_type" not in st.session_state:
        st.session_state.game_type = "27TD"

    if "hero_position" not in st.session_state:
        st.session_state.hero_position = "BB"

    if "opponent_count" not in st.session_state:
        st.session_state.opponent_count = 1

    if "players" not in st.session_state:
        st.session_state.players = build_players(
            st.session_state.hero_position,
            st.session_state.opponent_count,
        )

    if "hero_cards" not in st.session_state:
        st.session_state.hero_cards = {}

    for field in HERO_CARD_FIELDS:
        if field not in st.session_state.hero_cards:
            st.session_state.hero_cards[field] = []

    if "selected_card_field" not in st.session_state:
        st.session_state.selected_card_field = "predraw_hand"

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

    if "current_street" not in st.session_state:
        st.session_state.current_street = "pre"

    if "player_signature" not in st.session_state:
        st.session_state.player_signature = f"{st.session_state.game_type}_{st.session_state.hero_position}_{st.session_state.opponent_count}"


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
    st.session_state.current_street = "pre"

    for p in st.session_state.players:
        p["active"] = True


init_state()


# =========================
# カード処理
# =========================

def card_id(rank, suit_symbol):
    return f"{rank}{suit_symbol}"


def cards_to_text(cards):
    if not cards:
        return ""
    if PAT in cards:
        return "PAT"
    return " ".join(cards)


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


def toggle_hero_card(card):
    field = st.session_state.selected_card_field
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

    return f"{len(draw)}c"


# =========================
# プレイヤー・アクション処理
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


def mark_player_folded(player_id):
    player = get_player_by_id(player_id)
    if player:
        player["active"] = False


def street_log_text(street):
    logs = st.session_state.logs[street]
    if not logs:
        return "—"
    return " / ".join([e["text"] for e in logs])


def complete_street(street, auto_move=True):
    state = st.session_state.action_state[street]
    state["complete"] = True
    state["current_actor_id"] = None

    next_street = NEXT_STREET[street]

    if auto_move and next_street:
        st.session_state.current_street = next_street
        ensure_street_started(next_street)


def active_count():
    return len(get_active_players())


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

    # 1人しか残っていなければハンド終了扱い
    if active_count() <= 1:
        state["complete"] = True
        state["current_actor_id"] = None
        return

    # bet / raise が入った場合
    if action in ["bet", "raise"]:
        state["has_bet"] = True

        active_ids = get_ordered_ids(street)
        state["pending"] = [pid for pid in active_ids if pid != actor_id]
        state["acted"] = [actor_id]

        next_id = get_next_id_after(street, actor_id, state["pending"])
        state["current_actor_id"] = next_id
        return

    # すでにbet/raiseがあり、call/foldで応答した場合
    if state["has_bet"]:
        if actor_id in state["pending"]:
            state["pending"].remove(actor_id)

        # fold後はpendingからも消す
        state["pending"] = [
            pid for pid in state["pending"]
            if get_player_by_id(pid) and get_player_by_id(pid).get("active", True)
        ]

        if not state["pending"]:
            complete_street(street, auto_move=auto_move)
            return

        next_id = get_next_id_after(street, actor_id, state["pending"])
        state["current_actor_id"] = next_id
        return

    # まだbetがない状態で check / call / fold した場合
    if actor_id not in state["acted"]:
        state["acted"].append(actor_id)

    active_ids = get_ordered_ids(street)
    remaining = [pid for pid in active_ids if pid not in state["acted"]]

    if not remaining:
        complete_street(street, auto_move=auto_move)
        return

    next_id = get_next_id_after(street, actor_id, remaining)
    state["current_actor_id"] = next_id


def get_available_actions(street):
    state = st.session_state.action_state[street]

    if street == "pre":
        if state["has_bet"]:
            return PREDRAW_ACTIONS_FACING_BET
        return PREDRAW_ACTIONS_NO_BET

    if state["has_bet"]:
        return POSTDRAW_ACTIONS_FACING_BET

    return POSTDRAW_ACTIONS_NO_BET


def recompute_all_from_logs():
    # activeとaction_stateをログから再構築
    for p in st.session_state.players:
        p["active"] = True

    original_logs = {
        street: list(st.session_state.logs[street])
        for street in STREETS
    }

    st.session_state.action_state = fresh_action_state()

    for street in STREETS:
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

    # 元ログを維持
    st.session_state.logs = original_logs


def undo_action_log(street):
    if not st.session_state.logs[street]:
        return

    st.session_state.logs[street].pop()
    recompute_all_from_logs()

    if not st.session_state.action_state[street]["complete"]:
        st.session_state.current_street = street


def clear_action_log(street):
    st.session_state.logs[street] = []
    recompute_all_from_logs()
    st.session_state.current_street = street


def reset_street_action(street):
    st.session_state.action_state[street] = fresh_action_state()[street]
    ensure_street_started(street)


def force_next_street():
    current = st.session_state.current_street
    next_street = NEXT_STREET[current]

    if next_street:
        st.session_state.current_street = next_street
        ensure_street_started(next_street)


def force_prev_street():
    current = st.session_state.current_street
    idx = STREETS.index(current)

    if idx > 0:
        st.session_state.current_street = STREETS[idx - 1]


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
    div.stButton > button {
        width: 100%;
        min-height: 44px;
        font-size: 18px;
        font-weight: 800;
        border-radius: 8px;
        border: 1px solid #222;
        padding: 0;
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
    </style>
    """,
    unsafe_allow_html=True,
)


# =========================
# UI
# =========================

st.title("27TD & Badugi Hand History Tracker")

# 設定変更時のプレイヤー再構築
new_signature = f'{st.session_state.game_type}_{st.session_state.hero_position}_{st.session_state.opponent_count}'
if new_signature != st.session_state.player_signature:
    st.session_state.player_signature = new_signature
    st.session_state.players = build_players(
        st.session_state.hero_position,
        st.session_state.opponent_count,
    )
    reset_hand_all()
    st.rerun()

# =========================
# 基本設定
# =========================

st.subheader("基本設定")

setting_cols = st.columns(4)

with setting_cols[0]:
    game_type = st.radio(
        "ゲーム",
        ["27TD", "Badugi"],
        horizontal=True,
        key="game_type",
    )

with setting_cols[1]:
    hero_position = st.selectbox(
        "Heroポジション",
        POSITIONS,
        key="hero_position",
    )

with setting_cols[2]:
    opponent_count = st.number_input(
        "相手人数",
        min_value=1,
        max_value=7,
        step=1,
        key="opponent_count",
    )

with setting_cols[3]:
    if st.button("プレイヤー再作成"):
        st.session_state.players = build_players(
            st.session_state.hero_position,
            st.session_state.opponent_count,
        )
        reset_hand_all()
        st.rerun()

# =========================
# プレイヤー設定
# =========================

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

# =========================
# トップ早見表
# =========================

st.markdown(
    """
    <div class="top-summary-box">
        <div class="top-summary-title">このハンドの早見表</div>
        <div class="top-summary-sub">
            アクションが一周して完了したら、自動で次のストリートへ移行します。
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
# メイン入力
# =========================

left, right = st.columns([2, 1])

# =========================
# 左：Heroハンド入力
# =========================

with left:
    st.subheader("Hero ハンド入力")

    selected_field = st.selectbox(
        "入力先",
        HERO_CARD_FIELDS,
        format_func=lambda x: HERO_CARD_FIELD_LABELS[x],
        key="selected_card_field",
    )

    st.write(f"現在の入力先：**{HERO_CARD_FIELD_LABELS[selected_field]}**")
    st.write(f"選択中：**{cards_to_text(st.session_state.hero_cards[selected_field]) or '—'}**")

    with st.expander("カードを選択する", expanded=False):
        if can_use_pat(st.session_state.selected_card_field):
            pat_cols = st.columns([2, 11])

            with pat_cols[0]:
                current_field = st.session_state.selected_card_field
                related_discard = (
                    current_field
                    if current_field.endswith("_discard")
                    else get_discard_field_from_draw_field(current_field)
                )

                pat_label = "PAT解除" if related_discard and PAT in st.session_state.hero_cards[related_discard] else "PAT"

                if st.button(pat_label, key=f"pat_button_{st.session_state.selected_card_field}"):
                    set_pat_for_hero(st.session_state.selected_card_field)
                    st.rerun()

            with pat_cols[1]:
                st.caption("PATを押すと、このchangeの捨て・引きは自動でスキップされます。もう一度押すと解除できます。")

        for suit in SUITS:
            cols = st.columns(len(RANKS))

            for i, rank in enumerate(RANKS):
                card = card_id(rank, suit["symbol"])
                field = st.session_state.selected_card_field
                max_cards = MAX_HAND_SIZE[st.session_state.game_type]

                selected_now = card in st.session_state.hero_cards[field]
                ok, _ = can_add_hero_card(card, field, max_cards)

                with cols[i]:
                    if selected_now:
                        label = f"✓{card}"
                        disabled = False
                    elif ok:
                        label = card
                        disabled = False
                    else:
                        label = "🔒"
                        disabled = True

                    clicked = st.button(
                        label,
                        key=f"card_{card}_{field}",
                        disabled=disabled,
                    )

                    if clicked:
                        toggle_hero_card(card)
                        st.rerun()

    card_ops = st.columns(3)

    with card_ops[0]:
        if st.button("1枚戻す"):
            undo_card_field(st.session_state.selected_card_field)
            st.rerun()

    with card_ops[1]:
        if st.button("入力先クリア"):
            clear_card_field(st.session_state.selected_card_field)
            st.rerun()

    with card_ops[2]:
        if st.button("Heroハンド全消去"):
            for field in HERO_CARD_FIELDS:
                st.session_state.hero_cards[field] = []
            st.rerun()

    st.divider()
    st.subheader("Hero 手札推移")

    hand_predraw = calculate_hero_hand_after(0)
    hand_after_1 = calculate_hero_hand_after(1)
    hand_after_2 = calculate_hero_hand_after(2)
    hand_final = calculate_hero_hand_after(3)

    c1, c2 = st.columns(2)

    with c1:
        for field in HERO_CARD_FIELDS:
            st.markdown(
                f"""
                <div class="hand-box">
                    <span class="hand-title">{HERO_CARD_FIELD_LABELS[field]}：</span>
                    {cards_to_text(st.session_state.hero_cards[field]) or "—"}
                </div>
                """,
                unsafe_allow_html=True,
            )

    with c2:
        st.markdown(
            f"""
            <div class="hand-box">
                <span class="hand-title">プリドロー：</span>
                {cards_to_text(hand_predraw) or "—"}
            </div>

            <div class="hand-box">
                <span class="hand-title">1st後：</span>
                {cards_to_text(hand_after_1) or "—"}
            </div>

            <div class="hand-box">
                <span class="hand-title">2nd後：</span>
                {cards_to_text(hand_after_2) or "—"}
            </div>

            <div class="hand-box">
                <span class="hand-title">最終：</span>
                {cards_to_text(hand_final) or "—"}
            </div>
            """,
            unsafe_allow_html=True,
        )

# =========================
# 右：自動アクション権利入力
# =========================

with right:
    st.subheader("アクション入力")

    street_nav = st.columns(4)

    for s in STREETS:
        with street_nav[STREETS.index(s)]:
            label = f"▶ {STREET_LABELS[s]}" if st.session_state.current_street == s else STREET_LABELS[s]
            if st.button(label, key=f"street_button_{s}"):
                st.session_state.current_street = s
                ensure_street_started(s)
                st.rerun()

    street = st.session_state.current_street
    ensure_street_started(street)

    st.write(f"現在のストリート：**{STREET_LABELS[street]}**")

    state = st.session_state.action_state[street]

    if state["complete"]:
        st.markdown(
            f"""
            <div class="complete-box">
                {STREET_LABELS[street]} は完了しています。
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

            action_options = get_available_actions(street)

            action_cols = st.columns(len(action_options))

            for i, action in enumerate(action_options):
                with action_cols[i]:
                    if st.button(action, key=f"quick_action_{street}_{action}"):
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

    for s in STREETS:
        done = " ✅" if st.session_state.action_state[s]["complete"] else ""
        st.write(f"**{STREET_LABELS[s]}{done}**：{street_log_text(s)}")

    log_ops = st.columns(3)

    with log_ops[0]:
        if st.button("1つ戻す"):
            undo_action_log(street)
            st.rerun()

    with log_ops[1]:
        if st.button("このstreetクリア"):
            clear_action_log(street)
            st.rerun()

    with log_ops[2]:
        if st.button("このstreetリセット"):
            clear_action_log(street)
            reset_street_action(street)
            st.rerun()

    move_ops = st.columns(2)

    with move_ops[0]:
        if st.button("前のstreetへ"):
            force_prev_street()
            st.rerun()

    with move_ops[1]:
        if st.button("次のstreetへ"):
            force_next_street()
            st.rerun()

    st.divider()
    st.subheader("チェンジ枚数入力")

    change_options = get_change_options()

    for s in ["1st", "2nd", "3rd"]:
        with st.expander(f"{s} change", expanded=(s == st.session_state.current_street)):
            for p in sort_players_by_order(st.session_state.players, s):
                pid = p["id"]

                if pid == "H":
                    st.write(f"Hero {p['position']}：{hero_change_from_cards(s)}")
                else:
                    if pid not in st.session_state.changes[s]:
                        st.session_state.changes[s][pid] = "不明"

                    st.session_state.changes[s][pid] = st.selectbox(
                        f"{pid} {p['position']} change",
                        change_options,
                        index=change_options.index(st.session_state.changes[s][pid])
                        if st.session_state.changes[s][pid] in change_options else 0,
                        key=f"change_{s}_{pid}",
                    )

# =========================
# 詳細ログ表示
# =========================

st.divider()
st.subheader("詳細ログ")

detail_cols = st.columns(4)

for idx, s in enumerate(STREETS):
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
    placeholder="例：BB vs UTG。PreでUTG raise / BB call。自動で1stへ移行。"
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
        hand_predraw = calculate_hero_hand_after(0)
        hand_after_1 = calculate_hero_hand_after(1)
        hand_after_2 = calculate_hero_hand_after(2)
        hand_final = calculate_hero_hand_after(3)

        row = {
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "date": played_date,
            "tournament": tournament_name,
            "game_type": st.session_state.game_type,

            "hero_position": st.session_state.hero_position,
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

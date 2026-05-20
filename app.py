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

FIELDS = [
    "predraw_hand",
    "d1_discard",
    "d1_draw",
    "d2_discard",
    "d2_draw",
    "d3_discard",
    "d3_draw",
]

FIELD_LABELS = {
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

POSITIONS = ["UTG", "HJ", "CO", "BTN", "SB", "BB"]

PREDRAW_ACTION_OPTIONS = [
    "なし",
    "open",
    "call",
    "3bet",
    "4bet/cap",
    "BB defend",
    "SB complete",
    "check",
    "fold",
    "その他",
]

POSTDRAW_ACTION_OPTIONS = [
    "なし",
    "check",
    "bet",
    "call",
    "raise",
    "3bet",
    "cap",
    "fold",
    "bet/call",
    "bet/fold",
    "check/call",
    "check/raise",
    "その他",
]

VILLAIN_ACTION_OPTIONS = [
    "不明",
    "なし",
    "check",
    "bet",
    "call",
    "raise",
    "3bet",
    "cap",
    "fold",
    "donk",
    "check/call",
    "check/raise",
    "bet/call",
    "bet/fold",
    "その他",
]

VILLAIN_DRAW_OPTIONS = [
    "不明",
    "pat",
    "1c",
    "2c",
    "3c",
    "4c",
    "5c",
]


# =========================
# セッション初期化
# =========================

def init_state():
    if "hands" not in st.session_state:
        st.session_state.hands = {}

    for field in FIELDS:
        if field not in st.session_state.hands:
            st.session_state.hands[field] = []

    if "selected_field" not in st.session_state:
        st.session_state.selected_field = "predraw_hand"

    if "game_type" not in st.session_state:
        st.session_state.game_type = "27TD"


def reset_current_hand():
    for field in FIELDS:
        st.session_state.hands[field] = []


init_state()


# =========================
# カード処理
# =========================

def card_id(rank, suit_symbol):
    return f"{rank}{suit_symbol}"


def flatten_used_cards():
    used = []
    for field in FIELDS:
        for card in st.session_state.hands[field]:
            if card != PAT:
                used.append(card)
    return used


def calculate_hand_after(stage):
    hand = list(st.session_state.hands["predraw_hand"])

    if stage >= 1:
        if PAT not in st.session_state.hands["d1_discard"]:
            for c in st.session_state.hands["d1_discard"]:
                if c in hand:
                    hand.remove(c)
            hand.extend(st.session_state.hands["d1_draw"])

    if stage >= 2:
        if PAT not in st.session_state.hands["d2_discard"]:
            for c in st.session_state.hands["d2_discard"]:
                if c in hand:
                    hand.remove(c)
            hand.extend(st.session_state.hands["d2_draw"])

    if stage >= 3:
        if PAT not in st.session_state.hands["d3_discard"]:
            for c in st.session_state.hands["d3_discard"]:
                if c in hand:
                    hand.remove(c)
            hand.extend(st.session_state.hands["d3_draw"])

    return hand


def current_hand_before_field(field):
    if field == "predraw_hand":
        return []

    if field in ["d1_discard", "d1_draw"]:
        return calculate_hand_after(0)

    if field in ["d2_discard", "d2_draw"]:
        return calculate_hand_after(1)

    if field in ["d3_discard", "d3_draw"]:
        return calculate_hand_after(2)

    return calculate_hand_after(3)


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


def can_add_card(card, field, max_cards):
    cards_in_field = st.session_state.hands[field]

    if card in cards_in_field:
        return True, "選択解除できます"

    if field == "d1_draw" and PAT in st.session_state.hands["d1_discard"]:
        return False, "1stはPAT済みです"

    if field == "d2_draw" and PAT in st.session_state.hands["d2_discard"]:
        return False, "2ndはPAT済みです"

    if field == "d3_draw" and PAT in st.session_state.hands["d3_discard"]:
        return False, "3rdはPAT済みです"

    if field.endswith("_discard") and PAT in st.session_state.hands[field]:
        return False, "PAT済みです"

    if len(cards_in_field) >= max_cards:
        return False, "枚数上限です"

    if field == "predraw_hand" or field.endswith("_draw"):
        if card in flatten_used_cards():
            return False, "すでに使われています"
        return True, ""

    if field.endswith("_discard"):
        hand_before = current_hand_before_field(field)

        if card not in hand_before:
            return False, "現在手札にないカードです"

        return True, ""

    return True, ""


def toggle_card(card):
    field = st.session_state.selected_field
    game_type = st.session_state.game_type
    max_cards = MAX_HAND_SIZE[game_type]

    if card in st.session_state.hands[field]:
        st.session_state.hands[field].remove(card)
        return

    ok, message = can_add_card(card, field, max_cards)

    if ok:
        st.session_state.hands[field].append(card)
    else:
        st.toast(message)


def undo_field(field):
    if st.session_state.hands[field]:
        st.session_state.hands[field].pop()


def clear_field(field):
    st.session_state.hands[field] = []


def set_pat(field):
    if not can_use_pat(field):
        st.toast("PATはchangeの捨て欄または引き欄でのみ選択できます")
        return

    if field.endswith("_discard"):
        discard_field = field
        draw_field = get_draw_field_from_discard_field(field)
    else:
        draw_field = field
        discard_field = get_discard_field_from_draw_field(field)

    if PAT in st.session_state.hands[discard_field]:
        st.session_state.hands[discard_field] = []
        if draw_field:
            st.session_state.hands[draw_field] = []
        return

    st.session_state.hands[discard_field] = [PAT]

    if draw_field:
        st.session_state.hands[draw_field] = []


def cards_to_text(cards):
    if not cards:
        return ""
    if PAT in cards:
        return "PAT"
    return " ".join(cards)


def compact_value(value):
    if value in ["不明", "なし", "", None]:
        return "—"
    return value


def change_action_text(change_value, action_value):
    change = compact_value(change_value)
    action = compact_value(action_value)

    if change == "—" and action == "—":
        return "—"
    if change == "—":
        return action
    if action == "—":
        return change

    return f"{change} / {action}"


def hero_change_text(discard_cards, draw_cards):
    discard_text = cards_to_text(discard_cards)
    draw_text = cards_to_text(draw_cards)

    if discard_text == "PAT":
        return "pat"

    draw_count = len(draw_cards)

    if draw_count == 0 and not discard_text:
        return "—"

    return f"{draw_count}c"


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
        height: 48px;
        font-size: 22px;
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

    .section-box {
        padding: 14px;
        border-radius: 12px;
        border: 1px solid #dddddd;
        background: #ffffff;
        margin-bottom: 12px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# =========================
# UI
# =========================

st.title("27TD & Badugi Hand History Tracker")

top_action_placeholder = st.empty()

left, right = st.columns([2, 1])

with left:
    st.subheader("カード入力")

    game_type = st.radio(
        "ゲーム",
        ["27TD", "Badugi"],
        horizontal=True,
        key="game_type",
    )

    selected_field = st.selectbox(
        "入力先",
        FIELDS,
        format_func=lambda x: FIELD_LABELS[x],
        key="selected_field",
    )

    st.write(f"現在の入力先：**{FIELD_LABELS[selected_field]}**")
    st.write(f"選択中：**{cards_to_text(st.session_state.hands[selected_field]) or '—'}**")

    with st.expander("カードを選択する", expanded=False):
        if can_use_pat(st.session_state.selected_field):
            pat_cols = st.columns([2, 11])
            with pat_cols[0]:
                current_field = st.session_state.selected_field
                related_discard = (
                    current_field
                    if current_field.endswith("_discard")
                    else get_discard_field_from_draw_field(current_field)
                )

                pat_label = "PAT解除" if related_discard and PAT in st.session_state.hands[related_discard] else "PAT"

                if st.button(pat_label, key=f"pat_button_{st.session_state.selected_field}"):
                    set_pat(st.session_state.selected_field)
                    st.rerun()

            with pat_cols[1]:
                st.caption("PATを押すと、このchangeの捨て・引きは自動でスキップされます。もう一度押すと解除できます。")

        for suit in SUITS:
            cols = st.columns(len(RANKS))

            for i, rank in enumerate(RANKS):
                card = card_id(rank, suit["symbol"])
                field = st.session_state.selected_field
                max_cards = MAX_HAND_SIZE[st.session_state.game_type]

                selected_now = card in st.session_state.hands[field]
                ok, _ = can_add_card(card, field, max_cards)

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
                        toggle_card(card)
                        st.rerun()

with right:
    st.subheader("ハンド情報")

    position = st.selectbox("自分のポジション", POSITIONS)
    opponent_count = st.number_input("相手人数", min_value=1, max_value=7, value=1, step=1)

    st.markdown("### Hero アクション")

    predraw_action = st.selectbox("Hero プリドロー行動", PREDRAW_ACTION_OPTIONS)
    action_after_1 = st.selectbox("Hero 1st後 action", POSTDRAW_ACTION_OPTIONS)
    action_after_2 = st.selectbox("Hero 2nd後 action", POSTDRAW_ACTION_OPTIONS)
    action_after_3 = st.selectbox("Hero 3rd後 action", POSTDRAW_ACTION_OPTIONS)

    st.markdown("### Villain 情報")

    villains = []

    for i in range(int(opponent_count)):
        villain_no = i + 1

        with st.expander(f"Villain {villain_no}", expanded=(villain_no == 1)):
            v_position = st.selectbox(
                f"V{villain_no} ポジション",
                ["不明"] + POSITIONS,
                key=f"v{villain_no}_position",
            )

            v_predraw_action = st.selectbox(
                f"V{villain_no} プリドロー行動",
                PREDRAW_ACTION_OPTIONS,
                key=f"v{villain_no}_predraw_action",
            )

            vc1, vc2 = st.columns(2)

            with vc1:
                v_d1_draw = st.selectbox(
                    f"V{villain_no} 1st change",
                    VILLAIN_DRAW_OPTIONS,
                    key=f"v{villain_no}_d1_draw",
                )

                v_d2_draw = st.selectbox(
                    f"V{villain_no} 2nd change",
                    VILLAIN_DRAW_OPTIONS,
                    key=f"v{villain_no}_d2_draw",
                )

                v_d3_draw = st.selectbox(
                    f"V{villain_no} 3rd change",
                    VILLAIN_DRAW_OPTIONS,
                    key=f"v{villain_no}_d3_draw",
                )

            with vc2:
                v_action_after_1 = st.selectbox(
                    f"V{villain_no} 1st後 action",
                    VILLAIN_ACTION_OPTIONS,
                    key=f"v{villain_no}_action_after_1",
                )

                v_action_after_2 = st.selectbox(
                    f"V{villain_no} 2nd後 action",
                    VILLAIN_ACTION_OPTIONS,
                    key=f"v{villain_no}_action_after_2",
                )

                v_action_after_3 = st.selectbox(
                    f"V{villain_no} 3rd後 action",
                    VILLAIN_ACTION_OPTIONS,
                    key=f"v{villain_no}_action_after_3",
                )

        villains.append({
            "no": villain_no,
            "position": v_position,
            "predraw_action": v_predraw_action,
            "d1_draw": v_d1_draw,
            "action_after_1": v_action_after_1,
            "d2_draw": v_d2_draw,
            "action_after_2": v_action_after_2,
            "d3_draw": v_d3_draw,
            "action_after_3": v_action_after_3,
        })

    st.markdown("### アクション履歴")

    action_history = st.text_area(
        "自由記述",
        placeholder="例：BTN open / SB call / BB call / 1st SB 2c BB 1c Hero 1c ...",
        height=140,
    )

    st.divider()
    st.subheader("操作")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("1枚戻す"):
            undo_field(st.session_state.selected_field)
            st.rerun()

    with col2:
        if st.button("入力先クリア"):
            clear_field(st.session_state.selected_field)
            st.rerun()

    if st.button("このハンドをリセット"):
        reset_current_hand()
        st.rerun()


# =========================
# ハンド計算
# =========================

hand_predraw = calculate_hand_after(0)
hand_after_1 = calculate_hand_after(1)
hand_after_2 = calculate_hand_after(2)
hand_final = calculate_hand_after(3)


# =========================
# トップのアクション早見表
# =========================

summary_rows = []

summary_rows.append({
    "対象": "Hero",
    "位置": compact_value(position),
    "Pre": compact_value(predraw_action),
    "1st": change_action_text(
        hero_change_text(st.session_state.hands["d1_discard"], st.session_state.hands["d1_draw"]),
        action_after_1
    ),
    "2nd": change_action_text(
        hero_change_text(st.session_state.hands["d2_discard"], st.session_state.hands["d2_draw"]),
        action_after_2
    ),
    "3rd": change_action_text(
        hero_change_text(st.session_state.hands["d3_discard"], st.session_state.hands["d3_draw"]),
        action_after_3
    ),
})

for v in villains:
    summary_rows.append({
        "対象": f"V{v['no']}",
        "位置": compact_value(v["position"]),
        "Pre": compact_value(v["predraw_action"]),
        "1st": change_action_text(v["d1_draw"], v["action_after_1"]),
        "2nd": change_action_text(v["d2_draw"], v["action_after_2"]),
        "3rd": change_action_text(v["d3_draw"], v["action_after_3"]),
    })

action_summary_df = pd.DataFrame(
    summary_rows,
    columns=["対象", "位置", "Pre", "1st", "2nd", "3rd"]
)

with top_action_placeholder.container():
    st.markdown(
        """
        <div class="top-summary-box">
            <div class="top-summary-title">アクション早見表</div>
            <div class="top-summary-sub">Heroと相手のチェンジ枚数・アクションだけ確認する欄</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.dataframe(
        action_summary_df,
        hide_index=True,
        use_container_width=True,
    )


# =========================
# 現在の記録表示
# =========================

st.divider()
st.subheader("現在の記録")

c1, c2 = st.columns(2)

with c1:
    st.markdown("### 入力したカード")

    for field in FIELDS:
        st.markdown(
            f"""
            <div class="hand-box">
                <span class="hand-title">{FIELD_LABELS[field]}：</span>
                {cards_to_text(st.session_state.hands[field]) or "—"}
            </div>
            """,
            unsafe_allow_html=True,
        )

with c2:
    st.markdown("### 自動計算された手札")

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
# 詳細の流れ表示
# =========================

st.markdown("### 詳細の流れ")

detail_villain_predraw_lines = ""
detail_villain_1st_lines = ""
detail_villain_2nd_lines = ""
detail_villain_3rd_lines = ""

for v in villains:
    detail_villain_predraw_lines += f"V{v['no']}：{v['position']} / {v['predraw_action']}<br>"
    detail_villain_1st_lines += f"V{v['no']}：change {v['d1_draw']} / action {v['action_after_1']}<br>"
    detail_villain_2nd_lines += f"V{v['no']}：change {v['d2_draw']} / action {v['action_after_2']}<br>"
    detail_villain_3rd_lines += f"V{v['no']}：change {v['d3_draw']} / action {v['action_after_3']}<br>"

st.markdown(
    f"""
    <div class="section-box">
        <b>プリドロー</b><br>
        Hero：{position} / {cards_to_text(hand_predraw) or "—"} / {predraw_action}<br>
        {detail_villain_predraw_lines if detail_villain_predraw_lines else "Villain：—"}
    </div>

    <div class="section-box">
        <b>1st change → bet</b><br>
        Hero 捨て：{cards_to_text(st.session_state.hands["d1_discard"]) or "—"}<br>
        Hero 引き：{cards_to_text(st.session_state.hands["d1_draw"]) or "—"}<br>
        Hero 1st後：{cards_to_text(hand_after_1) or "—"}<br>
        Hero action：{action_after_1}<br>
        {detail_villain_1st_lines if detail_villain_1st_lines else "Villain：—"}
    </div>

    <div class="section-box">
        <b>2nd change → bet</b><br>
        Hero 捨て：{cards_to_text(st.session_state.hands["d2_discard"]) or "—"}<br>
        Hero 引き：{cards_to_text(st.session_state.hands["d2_draw"]) or "—"}<br>
        Hero 2nd後：{cards_to_text(hand_after_2) or "—"}<br>
        Hero action：{action_after_2}<br>
        {detail_villain_2nd_lines if detail_villain_2nd_lines else "Villain：—"}
    </div>

    <div class="section-box">
        <b>3rd change → bet</b><br>
        Hero 捨て：{cards_to_text(st.session_state.hands["d3_discard"]) or "—"}<br>
        Hero 引き：{cards_to_text(st.session_state.hands["d3_draw"]) or "—"}<br>
        Hero 最終：{cards_to_text(hand_final) or "—"}<br>
        Hero action：{action_after_3}<br>
        {detail_villain_3rd_lines if detail_villain_3rd_lines else "Villain：—"}
    </div>
    """,
    unsafe_allow_html=True,
)


# =========================
# 基本情報・メモ・タグ
# =========================

st.divider()
st.subheader("基本情報・結果")

b1, b2, b3, b4, b5 = st.columns(5)

with b1:
    played_date = st.date_input("日付", value=date.today())

with b2:
    tournament_name = st.text_input("大会名", placeholder="例：27TD & Badugi Mix")

with b3:
    result = st.selectbox("結果", ["win", "lose", "split", "fold", "unknown"])

with b4:
    profit = st.number_input("収支", value=0.0, step=1.0)

with b5:
    mistake_level = st.selectbox("ミス度", ["なし", "小", "中", "大", "要検討"])

st.subheader("メモ・タグ")

tags = st.multiselect(
    "タグ",
    [
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
)

note = st.text_area(
    "メモ",
    placeholder="例：3wayで相手2人が1c継続。2ndで片方pat、もう片方1c。Heroのbetが薄かったかも。"
)


# =========================
# 保存
# =========================

st.divider()

if st.button("保存", type="primary"):
    game_type = st.session_state.game_type
    max_cards = MAX_HAND_SIZE[game_type]

    if len(st.session_state.hands["predraw_hand"]) != max_cards:
        st.error(f"{game_type}のプリドローハンドは{max_cards}枚選んでください。")
    else:
        row = {
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "date": played_date,
            "tournament": tournament_name,
            "game_type": game_type,
            "position": position,
            "opponent_count": opponent_count,

            "predraw_hand": cards_to_text(st.session_state.hands["predraw_hand"]),
            "predraw_action": predraw_action,

            "d1_discard": cards_to_text(st.session_state.hands["d1_discard"]),
            "d1_draw": cards_to_text(st.session_state.hands["d1_draw"]),
            "hand_after_1": cards_to_text(hand_after_1),
            "action_after_1": action_after_1,

            "d2_discard": cards_to_text(st.session_state.hands["d2_discard"]),
            "d2_draw": cards_to_text(st.session_state.hands["d2_draw"]),
            "hand_after_2": cards_to_text(hand_after_2),
            "action_after_2": action_after_2,

            "d3_discard": cards_to_text(st.session_state.hands["d3_discard"]),
            "d3_draw": cards_to_text(st.session_state.hands["d3_draw"]),
            "final_hand": cards_to_text(hand_final),
            "action_after_3": action_after_3,

            "action_history": action_history,
            "result": result,
            "profit": profit,
            "mistake_level": mistake_level,
            "tags": ",".join(tags),
            "note": note,
        }

        for v in villains:
            no = v["no"]
            row[f"v{no}_position"] = v["position"]
            row[f"v{no}_predraw_action"] = v["predraw_action"]
            row[f"v{no}_d1_draw"] = v["d1_draw"]
            row[f"v{no}_action_after_1"] = v["action_after_1"]
            row[f"v{no}_d2_draw"] = v["d2_draw"]
            row[f"v{no}_action_after_2"] = v["action_after_2"]
            row[f"v{no}_d3_draw"] = v["d3_draw"]
            row[f"v{no}_action_after_3"] = v["action_after_3"]

        save_data(row)
        st.success("保存しました。")
        reset_current_hand()
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

    if "position" in df.columns and "profit" in df.columns:
        st.write("ポジション別収支")
        st.bar_chart(df.groupby("position")["profit"].sum())

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

RANKS = ["A", "K", "Q", "J", "T", "9", "8", "7", "6", "5", "4", "3", "2"]

SUITS = [
    {"symbol": "♠", "name": "spade", "color": "#3f3f3f"},
    {"symbol": "♥", "name": "heart", "color": "#b00000"},
    {"symbol": "♦", "name": "diamond", "color": "#1230b8"},
    {"symbol": "♣", "name": "club", "color": "#009b2e"},
]

FIELDS = [
    "initial",
    "d1_discard",
    "d1_draw",
    "d2_discard",
    "d2_draw",
    "d3_discard",
    "d3_draw",
]

FIELD_LABELS = {
    "initial": "初手",
    "d1_discard": "1st 捨て",
    "d1_draw": "1st 引き",
    "d2_discard": "2nd 捨て",
    "d2_draw": "2nd 引き",
    "d3_discard": "3rd 捨て",
    "d3_draw": "3rd 引き",
}

MAX_HAND_SIZE = {
    "27TD": 5,
    "Badugi": 4,
}

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
        st.session_state.selected_field = "initial"

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
        used.extend(st.session_state.hands[field])
    return used


def calculate_hand_after(stage):
    """
    stage:
    0 = 初手
    1 = 1st後
    2 = 2nd後
    3 = 3rd後 / 最終
    """
    hand = list(st.session_state.hands["initial"])

    if stage >= 1:
        for c in st.session_state.hands["d1_discard"]:
            if c in hand:
                hand.remove(c)
        hand.extend(st.session_state.hands["d1_draw"])

    if stage >= 2:
        for c in st.session_state.hands["d2_discard"]:
            if c in hand:
                hand.remove(c)
        hand.extend(st.session_state.hands["d2_draw"])

    if stage >= 3:
        for c in st.session_state.hands["d3_discard"]:
            if c in hand:
                hand.remove(c)
        hand.extend(st.session_state.hands["d3_draw"])

    return hand


def current_hand_before_field(field):
    if field == "initial":
        return []

    if field in ["d1_discard", "d1_draw"]:
        return calculate_hand_after(0)

    if field in ["d2_discard", "d2_draw"]:
        return calculate_hand_after(1)

    if field in ["d3_discard", "d3_draw"]:
        return calculate_hand_after(2)

    return calculate_hand_after(3)


def can_add_card(card, field, max_cards):
    cards_in_field = st.session_state.hands[field]

    # 枚数上限
    if len(cards_in_field) >= max_cards:
        return False, "枚数上限です"

    # 初手・引きカードは山から来るので、既に使ったカードは不可
    if field == "initial" or field.endswith("_draw"):
        if card in flatten_used_cards():
            return False, "すでに使われています"
        return True, ""

    # 捨てカードは、その時点の手札にあるカードだけ選べる
    if field.endswith("_discard"):
        hand_before = current_hand_before_field(field)
        if card not in hand_before:
            return False, "現在手札にないカードです"
        if card in cards_in_field:
            return False, "すでに捨てに選択済みです"
        return True, ""

    return True, ""


def add_card(card):
    field = st.session_state.selected_field
    game_type = st.session_state.game_type
    max_cards = MAX_HAND_SIZE[game_type]

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


def cards_to_text(cards):
    return " ".join(cards) if cards else ""


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
        height: 54px;
        font-size: 24px;
        font-weight: 800;
        border-radius: 8px;
        border: 1px solid #222;
        color: white;
        padding: 0;
    }

    .card-row-label {
        font-size: 22px;
        font-weight: bold;
        padding-top: 12px;
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

left, right = st.columns([2, 1])

with left:
    st.subheader("カード選択")

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

    # カードグリッド
    for suit in SUITS:
        cols = st.columns(len(RANKS))

        for i, rank in enumerate(RANKS):
            card = card_id(rank, suit["symbol"])
            field = st.session_state.selected_field
            max_cards = MAX_HAND_SIZE[st.session_state.game_type]

            ok, _ = can_add_card(card, field, max_cards)

            with cols[i]:
                button_label = card
                if not ok:
                    button_label = "🔒"

                clicked = st.button(
                    button_label,
                    key=f"card_{card}_{field}",
                    disabled=not ok,
                )

                # 背景色はStreamlit標準ボタンでは個別指定しにくいので、
                # まずは機能優先。見た目の完全再現は次段階でHTML化する。
                if clicked:
                    add_card(card)
                    st.rerun()

with right:
    st.subheader("操作")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("入力先を1枚戻す"):
            undo_field(st.session_state.selected_field)
            st.rerun()

    with col2:
        if st.button("入力先をクリア"):
            clear_field(st.session_state.selected_field)
            st.rerun()

    if st.button("このハンドをリセット"):
        reset_current_hand()
        st.rerun()

    st.divider()

    st.subheader("基本情報")

    played_date = st.date_input("日付", value=date.today())
    tournament_name = st.text_input("大会名", placeholder="例：27TD & Badugi Mix")
    position = st.selectbox("ポジション", ["UTG", "HJ", "CO", "BTN", "SB", "BB"])
    entry_type = st.selectbox(
        "参加形態",
        ["open", "call", "3bet", "BB defend", "SB complete", "limp", "free play", "その他"]
    )
    result = st.selectbox("結果", ["win", "lose", "split", "fold", "unknown"])
    profit = st.number_input("収支", value=0.0, step=1.0)
    mistake_level = st.selectbox("ミス度", ["なし", "小", "中", "大", "要検討"])

# =========================
# 現在の記録表示
# =========================

st.divider()
st.subheader("現在の記録")

hand_initial = calculate_hand_after(0)
hand_after_1 = calculate_hand_after(1)
hand_after_2 = calculate_hand_after(2)
hand_final = calculate_hand_after(3)

display_cols = st.columns(2)

with display_cols[0]:
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

with display_cols[1]:
    st.markdown(
        f"""
        <div class="hand-box">
            <span class="hand-title">初手：</span>
            {cards_to_text(hand_initial) or "—"}
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
# メモ・タグ
# =========================

st.divider()
st.subheader("アクション・メモ")

action_log = st.text_area(
    "アクションメモ",
    placeholder="例：CO open / BB call / 1st BB 2c Hero 1c / bet call ..."
)

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
    ]
)

note = st.text_area(
    "メモ",
    placeholder="例：9を切るべきだったか / rough badugiでpatしすぎかも"
)

# =========================
# 保存
# =========================

st.divider()

if st.button("保存", type="primary"):
    game_type = st.session_state.game_type
    max_cards = MAX_HAND_SIZE[game_type]

    if len(st.session_state.hands["initial"]) != max_cards:
        st.error(f"{game_type}の初手は{max_cards}枚選んでください。")
    else:
        row = {
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "date": played_date,
            "tournament": tournament_name,
            "game_type": game_type,
            "position": position,
            "entry_type": entry_type,

            "initial": cards_to_text(st.session_state.hands["initial"]),
            "d1_discard": cards_to_text(st.session_state.hands["d1_discard"]),
            "d1_draw": cards_to_text(st.session_state.hands["d1_draw"]),
            "hand_after_1": cards_to_text(hand_after_1),

            "d2_discard": cards_to_text(st.session_state.hands["d2_discard"]),
            "d2_draw": cards_to_text(st.session_state.hands["d2_draw"]),
            "hand_after_2": cards_to_text(hand_after_2),

            "d3_discard": cards_to_text(st.session_state.hands["d3_discard"]),
            "d3_draw": cards_to_text(st.session_state.hands["d3_draw"]),
            "final_hand": cards_to_text(hand_final),

            "action_log": action_log,
            "tags": ",".join(tags),
            "result": result,
            "profit": profit,
            "mistake_level": mistake_level,
            "note": note,
        }

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

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("記録ハンド数", len(df))

    with col2:
        if "profit" in df.columns:
            st.metric("合計収支", df["profit"].sum())

    with col3:
        if "result" in df.columns:
            st.metric("勝利数", (df["result"] == "win").sum())

    if "game_type" in df.columns:
        st.write("ゲーム別ハンド数")
        st.bar_chart(df["game_type"].value_counts())

    if "position" in df.columns and "profit" in df.columns:
        st.write("ポジション別収支")
        st.bar_chart(df.groupby("position")["profit"].sum())

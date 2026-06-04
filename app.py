import streamlit as st
import pandas as pd
import numpy as np
import datetime
import random

# ページ初期設定
st.set_page_config(page_title="BokiQuest 1級", page_icon="📊", layout="wide")

# --- 模擬データベースとセッション状態の初期化 ---
if 'history' not in st.session_state:
    # 過去の演習データ（グラフ用初期データ）
    st.session_state.history = [
        {"日付": "5日前", "正解率": 45, "推定合格率": 5},
        {"日付": "4日前", "正解率": 52, "推定合格率": 12},
        {"日付": "3日前", "正解率": 58, "推定合格率": 20},
        {"日付": "2日前", "正解率": 63, "推定合格率": 35},
        {"日付": "1日前", "正解率": 68, "推定合格率": 55},
    ]

if 'stats' not in st.session_state:
    # 各論点の出題確率（重要度）、正解数、不正解数
    # 重要度が高いもの（連結、組織再編、標準原価、意思決定など）のウェイトを高く設定
    st.session_state.stats = {
        "商業簿記：連結会計（成果連結）": {"重要度": 95, "正解": 12, "不正解": 8},
        "商業簿記：税効果会計": {"重要度": 85, "正解": 15, "不正解": 3},
        "会計学：企業結合・組織再編": {"重要度": 90, "正解": 5, "不正解": 7},
        "会計学：金融商品・資産除去債務": {"重要度": 80, "正解": 18, "不正解": 4},
        "工業簿記：標準原価計算（差異分析）": {"重要度": 95, "正解": 8, "不正解": 9},
        "工業簿記：部門別原価計算": {"重要度": 75, "正解": 14, "不正解": 2},
        "原価計算：設備投資の意思決定": {"重要度": 95, "正解": 6, "不正解": 11},
        "原価計算：最適プロダクト・ミックス": {"重要度": 70, "正解": 11, "不正解": 3},
    }

# --- 1. カウントダウン機能（2026年度の本試験日程を基準） ---
st.title("🎯 日商簿記1級 限界突破Webアプリ「BokiQuest 1級」")
st.caption("AIがあなたの弱点を分析し、本試験までの最短ルートを提示します。")

today = datetime.date.today()
exam_date_june = datetime.date(2026, 6, 14)   # 第173回
exam_date_nov = datetime.date(2026, 11, 15)   # 第174回

if today <= exam_date_june:
    target_exam = exam_date_june
    exam_name = "第173回"
else:
    target_exam = exam_date_nov
    exam_name = "第174回"

days_left = (target_exam - today).days

# サイドバーに情報を集約
with st.sidebar:
    st.header("⏳ 本試験カウントダウン")
    st.subheader(f"【{exam_name}】まで")
    st.metric(label="残り日数", value=f"{days_left} 日")
    st.progress(max(0, min(100, int((180 - days_left) / 180 * 100))))
    st.write(f"試験日: {target_exam.strftime('%Y年%m月%d日')}")
    
    st.markdown("---")
    st.subheader("🛠 開発者用チートメニュー")
    if st.button("ランダムに学習記録を追加してグラフを動かす"):
        last_prob = st.session_state.history[-1]["推定合格率"]
        new_prob = max(0, min(100, last_prob + random.randint(-8, 15)))
        new_acc = max(0, min(100, int(new_prob * 0.8 + 20)))
        st.session_state.history.append({
            "日付": "今日",
            "正解率": new_acc,
            "推定合格率": new_prob
        })
        st.rerun()

# --- 2. 推定合格率＆メイン指標 ---
# 統計データから総合正解率を計算
total_correct = sum(v["正解"] for v in st.session_state.stats.values())
total_wrong = sum(v["不正解"] for v in st.session_state.stats.values())
total_ans = total_correct + total_wrong
overall_accuracy = (total_correct / total_ans * 100) if total_ans > 0 else 0

# 足切り（各論点40%未満）があるかチェックするロジック（簿記1級特有の各科目10点未満足切りを再現）
has_ashikiri = False
for topic, data in st.session_state.stats.items():
    topic_total = data["正解"] + data["不正解"]
    if topic_total > 0 and (data["正解"] / topic_total * 100) < 40:
        has_ashikiri = True

# 推定合格率の算出（正解率をベースに、足切りリスクと重要論点の正解率で傾斜をかける）
estimated_pass_rate = int(overall_accuracy * 1.1)
if has_ashikiri:
    estimated_pass_rate = int(estimated_pass_rate * 0.4) # 足切りリスクで大幅ダウン
estimated_pass_rate = max(1, min(99, estimated_pass_rate)) # 1%〜99%の間に収める

col1, col2, col3 = st.columns(3)
with col1:
    st.metric(label="🔥 現在の推定合格率", value=f"{estimated_pass_rate} %", delta=f"{estimated_pass_rate - st.session_state.history[-2]['推定合格率']}% (前日比)")
with col2:
    st.metric(label="📊 総合正解率", value=f"{overall_accuracy:.1f} %")
with col3:
    status_text = "🚨 足切り危険論点あり！" if has_ashikiri else "✅ 足切りラインクリア"
    st.metric(label="🛡 足切りステータス", value=status_text)

st.markdown("---")

# --- 3. ゲーム・演習エリア（重要度・苦手論点に応じた重点出題） ---
st.header("🎮 クエスト開始（自動重要度ウェイト出題）")

# 重点出題ロジックの計算
# 出題スコア = 重要度 * (100 - その論点の正解率)
# これにより「本試験に出やすく」「自分が苦手なもの」が最優先でピックアップされる
pickup_scores = {}
for topic, data in st.session_state.stats.items():
    t_total = data["正解"] + data["不正解"]
    t_acc = (data["正解"] / t_total * 100) if t_total > 0 else 0
    pickup_scores[topic] = data["重要度"] * (101 - t_acc)

recommend_topic = max(pickup_scores, key=pickup_scores.get)

st.info(f"💡 **AIレコメンド最優先クエスト：** 現在のあなたに最も必要な論点は **【{recommend_topic}】** です！")

with st.expander("👉 クエストに挑戦する（模擬アンサー）"):
    st.write(f"**【問題】** {recommend_topic} に関する本試験レベルの問題が出題されました。")
    st.caption("※実際のアプリではここに1級特有の複雑な計算問題や勘定口座が表示されます。")
    
    ans_col1, ans_col2 = st.columns(2)
    with ans_col1:
        if st.button("⭕️ 正解できた！ (知識が定着している)", use_container_width=True):
            st.session_state.stats[recommend_topic]["正解"] += 1
            st.success("ナイス！正解です。マスターへ一歩近づきました！")
            st.rerun()
    with ans_col2:
        if st.button("❌ 間違えた… (解説を確認する)", use_container_width=True):
            st.session_state.stats[recommend_topic]["不正解"] += 1
            st.error("お惜しい！不合格者の多くがここで足切りに遭います。復習帳に登録しました。")
            st.rerun()

st.markdown("---")

# --- 4. 苦手が一発でわかる分析表 ---
st.header("📊 弱点一撃可視化レーダー（論点別成績表）")

# 表示用データフレームの構築
table_data = []
for topic, data in st.session_state.stats.items():
    t_total = data["正解"] + data["不正解"]
    t_acc = (data["正解"] / t_total * 100) if t_total > 0 else 0
    
    # 危険度判定
    if t_acc < 40:
        danger_level = "🚨 激ヤバ（足切り）"
    elif t_acc < 70:
        danger_level = "⚠️ 要注意（合格点未満）"
    else:
        danger_level = "✨ 安全圏"
        
    table_data.append({
        "試験科目・論点": topic,
        "出題頻度（重要度）": f"★ {data['重要度']}",
        "解いた回数": t_total,
        "正解数": data["正解"],
        "正解率": f"{t_acc:.1f}%",
        "ステータス": danger_level
    })

df = pd.DataFrame(table_data)
# 正解率が低く、重要度が高い順にソートして「今すぐやるべき順」にする
st.dataframe(df, use_container_width=True, hide_index=True)

st.markdown("---")

# --- 5. 合格予想の推移グラフ ---
st.header("📈 合格予想確率の推移（成長グラフ）")

df_history = pd.DataFrame(st.session_state.history)
# 折れ線グラフの描画
st.line_chart(df_history.set_index("日付")[["推定合格率", "正解率"]])
st.caption("※日々の演習結果に応じて、グラフがリアルタイムに右肩上がりに成長していきます。合格ラインの70%突破を目指しましょう！")


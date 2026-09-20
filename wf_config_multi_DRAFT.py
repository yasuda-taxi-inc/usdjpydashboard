"""
wf_config_multi_DRAFT.py — 他の通貨ペア(EUR/USD・GBP/USD・AUD/USD)のウォークフォワード検証の設計【下書き】
2026-09-20 作成。まだ凍結していません。次の2つが揃ったら、確定してハッシュを付け、結果を見る前に凍結します。
  (1) データ(check_pair_data.py で、時刻・欠損・整合の検査に通ったもの)
  (2) 各ペアの実際の取引コスト(スプレッド+約定のずれ、pips)
これまでの検証(USD/JPY)から学んだことを、設計に入れています。
"""
import hashlib, json

PAIRS = ["EURUSD", "GBPUSD", "AUDUSD"]                       # 優先順。USD/JPYは比較用に、同じ設計で再計算する
PIP = {"EURUSD": 0.0001, "GBPUSD": 0.0001, "AUDUSD": 0.0001, "USDJPY": 0.01}
COST_PIPS = {"EURUSD": None, "GBPUSD": None, "AUDUSD": None, "USDJPY": 0.2}     # ← 実測値を入れる(None のままでは実行しない)
COST_SENSITIVITY = 0.5                                        # 感度確認: 各ペアのコストの0.5倍・1.5倍でも判定を出す

# ---- データ ----
DATA = "Dukascopy形式(BID) 5分足+1時間足、2016-01-01〜2026-09-15、時刻はUTC。WARMUPは2016-03-01まで"
DATA_SOURCE = "resample"                                      # 1時間足は5分足から再構成(USD/JPYの検証と同じ。fileでの感度確認も行う)
SEALED = "2010-01〜2015-12 があれば、凍結後に1回だけ使う(USD/JPY以外のペアでも、同じ期間を用意できれば)"

# ---- 通貨ペアに依存しない形へ換算(USD/JPYの数字だけから決める。他のペアの結果は見ていない) ----
# USD/JPYの1時間足ATR14: 平均18.4pips、価格に対する中央値0.132%
DEV_ATR_MULT = [1.5, 2.3, 3.0]        # 元の0.2%/0.3%/0.4%乖離 = ATR(中央値0.132%)の 1.52/2.27/3.03倍
ROUND_GRID_PIPS = 50                  # 元の「0.50円刻みのラウンド」= 50pips刻み(EUR/USDなら0.0050刻み)
EXITS_ATR = {                         # 判断時点の1時間足ATR14に対する倍率 = 元の(20/30)・(25/40)pipsを、平均ATR18.4pipsで割った値
    "E_A": (1.1, 1.6),
    "E_B": (1.35, 2.15),
}
HOLD_HOURS = 4

# ---- 探索空間(USD/JPYの検証v2と同じ形。640候補) ----
DIRECTIONS = [1, -1]
TRIGGERS = ["RSIX", "BRK20", "DEV(1.5)", "DEV(2.3)", "DEV(3.0)", "RSID8", "RSID12", "RSID16", "RSIEXT", "RND50"]
TREND_FILTERS = ["any", "PO"]
VOL_FILTERS = ["any", "ATR"]          # ATR拡大(atr_ratio)
SESSIONS = {"TK": (0, 6), "LN": (7, 15), "LNO": (7, 9), "TKLN": (0, 15)}     # UTC。ペアごとに変えない
# 選定・成功条件・プラセボ・fold は、USD/JPYの検証v2(wf_config.py)と同じ。ただし次を変える:
POOLED_PLACEBO = True                 # 3ペアを合算した1回の手順として、プラセボを測る(ペアが増えた分の偶然を補正する)
TEST_YEARS = list(range(2019, 2027))
EMBARGO_DAYS = 7
MIN_N_TRAIN = 40

# ---- 段階1: 転移テスト(新しい探索をしない、試行数がほとんど増えない) ----
STAGE1 = "L02・L11の考え方を、ATR単位に換算して各ペアに当てる。L02相当=EMA20からの乖離が2.3×ATR以上かつUTC7〜8時、L11相当=ニューヨーク時間のRSI乖離。2期間(2016-20と2021-26)で符号が揃うかを見る"

CRITERIA = {
    "S1": "段階1: 2期間とも、コスト後の平均が正で、ペアごとの95%区間が0を含まない、が2ペア以上",
    "S2": "段階2: 3ペア合算のOOS純EVが正、プラセボ200回の上位10%、8年中5年以上で正、選定した候補が非選定を上回る(USD/JPYの基準と同じ)",
    "共通": "コストは各ペアの実測値。感度として0.5倍・1.5倍でも判定を出す。判定に使うのは、実測値のときだけ",
}
NOTES = [
    "USD/JPYでは、この手順で『コスト後に正』は確認できなかった(合算OOS -0.13pips)。他のペアで結果が変わるとすれば、それは通貨の性質による独立したエッジがあるとき",
    "USD/JPYのATR連動の出口は、以前の検証で固定pipsより改善しなかった。今回は、ペアごとのpipsの大きさが違うため、換算の目的で使う",
    "ペアどうしは、ドルを介して相関する。3ペアの結果は独立ではないので、合算の区間は、ペア×週のブロックで測る",
]

CONFIG = dict(PAIRS=PAIRS, PIP=PIP, COST_PIPS=COST_PIPS, DEV_ATR_MULT=DEV_ATR_MULT, ROUND_GRID_PIPS=ROUND_GRID_PIPS, EXITS_ATR=EXITS_ATR, HOLD_HOURS=HOLD_HOURS,
              TRIGGERS=TRIGGERS, TREND_FILTERS=TREND_FILTERS, VOL_FILTERS=VOL_FILTERS, SESSIONS=SESSIONS, TEST_YEARS=TEST_YEARS, EMBARGO_DAYS=EMBARGO_DAYS,
              MIN_N_TRAIN=MIN_N_TRAIN, POOLED_PLACEBO=POOLED_PLACEBO, CRITERIA=CRITERIA)

def n_candidates():
    return len(DIRECTIONS) * len(TRIGGERS) * len(TREND_FILTERS) * len(VOL_FILTERS) * len(SESSIONS) * len(EXITS_ATR)

def config_hash():
    return hashlib.sha256(json.dumps(CONFIG, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()[:16]

def ready():
    missing = [p for p in PAIRS if COST_PIPS.get(p) is None]
    return (not missing), missing

if __name__ == "__main__":
    ok, missing = ready()
    print(f"候補数(1ペアあたり): {n_candidates()}  / ハッシュ(下書き): {config_hash()}")
    print("実行できる状態:", "はい" if ok else f"いいえ(取引コストが未入力: {missing})")

"""
check_pair_data.py — 通貨ペアのデータ(Dukascopy形式のCSV)が、検証に使える状態かを検査する
使い方: python check_pair_data.py --dir /mnt/user-data/uploads --pair EURUSD
期待するファイル名: {PAIR}_Candlestick_5_m_BID_*.csv と {PAIR}_Candlestick_1_h_BID_*.csv (USDJPYと同じ形式)
検査項目: 読み込み / 重複・並び / 期間 / 欠損 / 価格の桁 / 4本値の整合 / 週末の足 / 時刻がUTCか(ロンドン開始の夏冬のずれ) / 1時間足と5分足の整合
"""
import os, glob, argparse
import numpy as np, pandas as pd

ap = argparse.ArgumentParser(); ap.add_argument("--dir", default="/mnt/user-data/uploads"); ap.add_argument("--pair", default="USDJPY")
args = ap.parse_args()
PAIR = args.pair.upper().replace("/", "").replace("_", "")
JPY = PAIR.endswith("JPY"); DEC = 3 if JPY else 5; PIP = 0.01 if JPY else 0.0001
results = []   # (レベル, 項目, 内容)
def add(level, name, text): results.append((level, name, text))

def load(pattern):
    fs = sorted(glob.glob(os.path.join(args.dir, pattern)))
    if not fs: return None, []
    df = pd.concat([pd.read_csv(f) for f in fs], ignore_index=True)
    cols = list(df.columns)
    if len(cols) != 6: raise ValueError(f"列の数が想定と違います({len(cols)}列): {cols}")
    df.columns = ["t", "o", "h", "l", "c", "v"]
    df["t"] = pd.to_datetime(df["t"], format="%d.%m.%Y %H:%M:%S.%f")
    return df, fs

d5, f5 = load(f"{PAIR}_Candlestick_5_m_BID_*.csv")
d1, f1 = load(f"{PAIR}_Candlestick_1_h_BID_*.csv")
print(f"通貨ペア: {PAIR}(pip={PIP}, 価格の小数桁={DEC})  フォルダ: {args.dir}")
if d5 is None:
    print(f"× 5分足のファイルが見つかりません: {PAIR}_Candlestick_5_m_BID_*.csv"); raise SystemExit(1)
print(f"5分足ファイル {len(f5)}個 / 1時間足ファイル {len(f1)}個")

def check(df, label, step_min):
    n0 = len(df)
    dup = int(df.t.duplicated().sum()); df = df.sort_values("t").drop_duplicates("t")
    add("OK" if dup == 0 else "注意", f"{label} 重複", f"{dup}行" + ("" if dup == 0 else "(取り除いて続行)"))
    add("OK", f"{label} 行数と期間", f"{len(df):,}行  {df.t.min():%Y-%m-%d} 〜 {df.t.max():%Y-%m-%d}")
    zero = float((df.v == 0).mean() * 100)
    add("OK" if zero < 25 else "注意", f"{label} 出来高0(気配のみ)の足", f"{zero:.1f}%(検証では除外します)")
    x = df[df.v > 0].set_index("t")
    bad = int(((x.h < x[["o", "c"]].max(axis=1) - 1e-9) | (x.l > x[["o", "c"]].min(axis=1) + 1e-9) | (x.h < x.l)).sum())
    add("OK" if bad == 0 else "NG", f"{label} 4本値の整合(高値≥始値・終値≥安値)", f"違反{bad}本")
    dec = x.c.round(DEC + 1).map(lambda v: len(str(v).split(".")[-1]) if "." in str(v) else 0)
    add("OK" if dec.max() <= DEC else "注意", f"{label} 価格の小数桁", f"最大{int(dec.max())}桁(想定{DEC}桁)")
    add("OK", f"{label} 価格帯", f"{x.c.min():.{DEC}f} 〜 {x.c.max():.{DEC}f}")
    rr = (x.h - x.l) / PIP
    big = int((rr > (300 if step_min == 5 else 600)).sum())
    add("OK" if big == 0 else "注意", f"{label} 異常に大きい足", f"{big}本(5分足で300pips超 / 1時間足で600pips超)")
    return x

x5 = check(d5, "5分足", 5)
x1 = check(d1, "1時間足", 60) if d1 is not None else None
if x1 is None: add("注意", "1時間足", "ファイルがありません(5分足から再構成して代用できます)")

# 週末の足・欠損
wd = x5.index.dayofweek
sat = int((wd == 5).sum()); add("OK" if sat < 50 else "注意", "土曜の足", f"{sat}本")
gap = x5.index.to_series().diff().dt.total_seconds() / 60
inweek = gap[(gap > 5) & (gap < 2000)]
add("OK" if len(inweek) < len(x5) * 0.01 else "注意", "週の途中の欠損(5分超2000分未満の間隔)", f"{len(inweek):,}回(足数の{len(inweek)/len(x5)*100:.2f}%)、うち60分超 {int((inweek > 60).sum())}回")
yr = x5.groupby(x5.index.year).size()
add("OK", "年別の本数", " ".join(f"{y}:{n:,}" for y, n in yr.items()))
full = 288 * 260
low = [y for y, n in yr.items() if n < full * 0.8 and y not in (yr.index.min(), yr.index.max())]
add("OK" if not low else "注意", "本数が少ない年(想定の8割未満)", "なし" if not low else str(low))

# 時刻がUTCか: FX市場の週の始まり(日曜)と終わり(金曜)は、ニューヨークの夏時間に合わせて、UTCでは夏は1時間早く、冬は1時間遅い。
# 別のタイムゾーン(サーバー時間など)のデータなら、この1時間のずれが出ない
xv = x5.copy()
def edge_hours(months):
    sun = xv[(xv.index.dayofweek == 6) & np.isin(xv.index.month, months)]; fri = xv[(xv.index.dayofweek == 4) & np.isin(xv.index.month, months)]
    if len(sun) < 20 or len(fri) < 20: return None
    f = pd.Series([g.index.min().hour + g.index.min().minute / 60 for _, g in sun.groupby(sun.index.date)])
    l = pd.Series([g.index.max().hour + g.index.max().minute / 60 for _, g in fri.groupby(fri.index.date)])
    return float(f.median()), float(l.median())
es, ew = edge_hours([6, 7, 8]), edge_hours([12, 1, 2])
if es is None or ew is None:
    add("NG", "時刻がUTCか(週の始まり・終わりの夏冬のずれ)", "日曜の足がほとんどありません。週の始まりがUTC日曜21〜22時でない=別のタイムゾーンのデータの可能性があります")
else:
    (so_s, so_e), (wi_s, wi_e) = es, ew
    ok_tz = abs((wi_s - so_s) - 1.0) < 0.2 and abs((wi_e - so_e) - 1.0) < 0.2
    add("OK" if ok_tz else "NG", "時刻がUTCか(週の始まり・終わりの夏冬のずれ)",
        f"日曜の最初の足 夏{so_s:.1f}時・冬{wi_s:.1f}時 / 金曜の最後の足 夏{so_e:.1f}時・冬{wi_e:.1f}時(UTCなら、冬のほうが約1時間遅い)")
rng = (x5.h - x5.l) / PIP; hr = x5.index.hour
peak = int(rng[(wd < 5)].groupby(hr[(wd < 5)]).mean().idxmax())
add("OK" if 6 <= peak <= 16 else "注意", "値幅が最大になる時刻(UTC)", f"{peak}時(ロンドン・NYの時間帯なら正常)")

# 1時間足と5分足の整合
if x1 is not None:
    g = x5.resample("1h", label="left", closed="left")
    r = pd.DataFrame({"o": g.o.first(), "h": g.h.max(), "l": g.l.min(), "c": g.c.last()}).dropna()
    j = r.join(x1[["o", "h", "l", "c"]], rsuffix="_1h", how="inner")
    tol = 0.6 * PIP
    match = float(((j.h - j.h_1h).abs() < tol).mean() * 100), float(((j.l - j.l_1h).abs() < tol).mean() * 100), float(((j.c - j.c_1h).abs() < tol).mean() * 100)
    add("OK" if min(match) > 97 else "注意", "1時間足と5分足の整合(高値・安値・終値が一致する割合)", f"{match[0]:.1f}% / {match[1]:.1f}% / {match[2]:.1f}%(重なる時間 {len(j):,}本)")

print("\n" + "=" * 100)
mark = {"OK": "○", "注意": "△", "NG": "×"}
for lv, nm, tx in results: print(f"  {mark[lv]} {nm}: {tx}")
ng = [r for r in results if r[0] == "NG"]; warn = [r for r in results if r[0] == "注意"]
print("=" * 100)
print(f"結果: {'使えません(×あり)。上の×を確認してください' if ng else ('使えます(△は確認のみ)' if warn else '問題なし')}   × {len(ng)}件 / △ {len(warn)}件")

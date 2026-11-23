"""API の説明文（待ちの出どころ・合計時間の出どころなど）を英語にする。

計画側（tsh.planner・tsh.waitmodel）は日本語の文字列を判定にも使っている（例: wait_source に「手前」を含むか）ので、
中身は変えずに、返す直前にここで置き換える。訳せなかった文字列はそのまま残す（`untranslated` で数えられる）。
"""
from __future__ import annotations

import re

_RULES = [
    # wait_source
    (r"^過去の実績$", "history (average gap between buses)"),
    (r"^過去の実際の通過の時刻表$", "when buses actually passed this stop on past days"),
    (r"^リアルタイム（手前を走るバス）$", "live: bus approaching from upstream"),
    (r"^リアルタイム（乗り換えの手前を走るバス）$", "live: transfer bus approaching from upstream"),
    (r"^リアルタイム$", "live"),
    (r"^折り返してくるバス＋前のバスからの経過＋実際の発車の時刻表$",
     "live: bus turning back at the terminus + time since the last bus + observed departures"),
    (r"^折り返してくるバス＋前のバスからの経過$", "live: bus turning back at the terminus + time since the last bus"),
    (r"^次のバスは始発を出る前（実際の発車の時刻表）$", "next bus has not left the origin yet (observed departures)"),
    (r"^前のバスが (\d+) 分前に通過$", r"last bus passed \1 min ago"),
    # total_source（前もって計画）
    (r"^過去の同じ種類の日 (\d+) 日の再現（着けた日 (\d+)%）を、学習期間の中の較正の週で実際の所要時間と合うように読み替えた値$",
     r"Replayed on \1 past days of the same type (arrived on \2% of them), recalibrated so that it matched "
     r"actual trip times on a calibration week"),
    (r"^1 本目はリアルタイム、乗り換えから先は過去の同じ種類の日 (\d+) 日の再現の中央値（着けた日 (\d+)%）$",
     r"First bus live; after the transfer, median of replays on \1 past days (arrived on \2% of them)"),
    (r"^過去の同じ種類の日 (\d+) 日の再現の中央値（着けた日 (\d+)%）$",
     r"Median of replays on \1 past days of the same type (arrived on \2% of them)"),
    (r"^区間の予測の和。過去の同じ種類の日 (\d+) 日のうち、この時刻に乗って着けたのは (\d+)% だけ$",
     r"Unreliable: only \2% of \1 past days of the same type got through at this time (sum of leg predictions shown)"),
    # total_source（今すぐ出る）
    (r"^1 本目はリアルタイム（同じような予測は、学習期間に (\d+)% の場面で 10 分以上長く待った）、乗り換えから先は過去の同じ種類の日の再現。それを合わせた中央値$",
     r"First bus live (similar predictions waited 10+ min longer in \1% of training cases); after the transfer, "
     r"replayed on past days. Median of the combined distribution"),
    (r"^1 本目はリアルタイム（同じような予測は、学習期間に (\d+)% の場面で 10 分以上長く待った）。それを合わせた中央値$",
     r"Live bus (similar predictions waited 10+ min longer in \1% of training cases). Median including that risk"),
    (r"^1 本目はリアルタイムだが、同じような予測は学習期間に半分以上の場面で、3 時間以内にバスが来なかったか乗り換えから先で着けなかった$",
     "Unreliable: for similar live predictions in training, more than half of the time no bus came within 3 h "
     "or the transfer failed"),
    # total_source（到着時刻の指定）
    (r"^過去の同じ種類の日 (\d+) 日のうち (\d+)% で (\d\d:\d\d) までに着けた最も遅い出発から、さらに (\d+) 分早めた出発（較正の週で 85% 間に合うように決めた余裕）。所要時間と到着はその出発での中央値$",
     r"Latest departure that arrived by \3 on \2% of \1 past days of the same type, moved \4 min earlier "
     r"(margin fitted on a calibration week to reach 85%). Time and arrival are medians for that departure"),
    (r"^過去の同じ種類の日 (\d+) 日のうち、(\d\d:\d\d) までに着けたのは 半分ほど。余裕を見た出発は出せない$",
     r"Only about half of \1 past days arrived by \2; no safe departure can be given"),
    (r"^過去の同じ種類の日 (\d+) 日のうち、(\d\d:\d\d) までに着けたのは 半分未満$",
     r"Fewer than half of \1 past days arrived by \2"),
    # safe_source
    (r"^見えていたバスに乗れない場合も含めた 85% 点（学習期間のリアルタイムの外れ方から）$",
     "85th percentile, including the chance of missing the visible bus (from how live waits were off in training)"),
    (r"^見えていたバスに乗れない場合や、乗り換えから先で過去の日にバスが来なかった場合を合わせると、着けない見込みが 15% を超えるので、余裕を見た到着は出さない$",
     "No safe arrival: counting missed buses and past days with no bus after the transfer, the chance of not "
     "arriving is above 15%"),
    # ride_model・徒歩の行き先
    (r"^区間モデル（直近の実績あり）$", "ride model (LightGBM, with the last 30 min of live bus speeds)"),
    (r"^区間モデル（過去の実績のみ）$", "ride model (LightGBM, history only)"),
    (r"^区間ごとの中央値の合計$", "sum of link medians"),
    (r"^目的地$", "destination"),
    # error
    (r"^実際の通過の時刻表が読み込まれていないので、到着時刻の指定は使えない$",
     "Arrive-by search is unavailable because the passage timetable is not loaded"),
]
_RULES = [(re.compile(p), r) for p, r in _RULES]
_JA = re.compile(r"[\u3040-\u30ff\u4e00-\u9fff]")
CONF = {"高": "high", "中": "medium", "低": "low", "データなし": "no data"}
untranslated: set[str] = set()


def text(s):
    if not isinstance(s, str) or not _JA.search(s):
        return s
    for p, r in _RULES:
        if p.match(s):
            return p.sub(r, s)
    untranslated.add(s)
    return s


# 混雑の度合い（API の値。英語のときはこの値で返す）
LEVEL = {"座れる": "seats", "立つ": "standing", "混雑": "crowded", "不明": "unknown"}


def response(res: dict) -> dict:
    """/journeys の返り値の説明文を英語にする（数値・停留所名・路線名はそのまま）。"""
    for k in ("error",):
        if k in res:
            res[k] = text(res[k])
    for o in res.get("options", []):
        for k in ("total_source", "safe_source"):
            if k in o:
                o[k] = text(o[k])
        for l in o.get("legs", []):
            for k in ("wait_source", "ride_model", "to"):
                if k in l:
                    l[k] = text(l[k])
            c = l.get("crowding")
            if isinstance(c, dict) and c.get("confidence") in CONF:
                c["confidence"] = CONF[c["confidence"]]
            if isinstance(c, dict):
                c["level"] = LEVEL.get(c.get("level"), c.get("level"))
                if isinstance(c.get("prob"), dict):
                    c["prob"] = {LEVEL.get(k, k): v for k, v in c["prob"].items()}
        if "crowding_worst" in o:
            o["crowding_worst"] = LEVEL.get(o["crowding_worst"], o["crowding_worst"])
    return res

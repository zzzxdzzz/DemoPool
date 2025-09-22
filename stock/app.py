import asyncio
import datetime as dt
from typing import List, Optional

import akshare as ak
import pandas as pd
import pytz
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import StreamingResponse, JSONResponse

app = FastAPI(title="A-shares Realtime (Free Source)",
              version="0.1.0",
              description="秒级轮询免费门户源的全A快照，仅供学习研究。")

# ---------- 配置 ----------
POLL_SEC_MARKET = 5          # 盘中轮询间隔
POLL_SEC_OFF = 60            # 盘外轮询间隔（偶尔拉取，便于开盘前预热）
TZ_CN = pytz.timezone("Asia/Shanghai")

# ---------- 共享状态 ----------
_latest_df: Optional[pd.DataFrame] = None
_last_ts: Optional[str] = None
_lock = asyncio.Lock()

# 字段映射（AKShare可能因上游改版而变动；必要时这里做容错）
CN2EN = {
    "代码": "symbol",
    "名称": "name",
    "最新价": "price",
    "涨跌幅": "pct_chg",
    "涨跌额": "chg",
    "成交量": "volume",
    "成交额": "amount",
    "今开": "open",
    "最高": "high",
    "最低": "low",
    "昨收": "prev_close",
    "换手率": "turnover",
    "量比": "vol_ratio",
    "市盈率-动态": "pe",
    "市净率": "pb",
    "总市值": "mkt_cap",
    "流通市值": "float_mkt_cap",
    "涨速": "spd",
    "振幅": "amp",
    "交易状态": "status",
}

# ---------- 交易时段判断（简化，无法覆盖节假日：如需精准可接入节假日API/日历） ----------
def is_market_open(now_cn: dt.datetime) -> bool:
    if now_cn.weekday() >= 5:  # 0=Mon ... 6=Sun
        return False
    t = now_cn.time()
    am = (dt.time(9, 15) <= t <= dt.time(11, 30))
    pm = (dt.time(13, 0) <= t <= dt.time(15, 0))
    return am or pm

# ---------- 抓取 ----------
async def fetch_all_spot() -> pd.DataFrame:
    # AKShare 接口：全A快照
    df = ak.stock_zh_a_spot()
    if not isinstance(df, pd.DataFrame) or df.empty:
        raise RuntimeError("Empty dataframe from source")
    # 统一列名、填充交易所前缀
    colmap = {c: CN2EN.get(c, c) for c in df.columns}
    df = df.rename(columns=colmap)

    # 规范 symbol：尝试自动加上 sh/sz/bj 前缀（简单规则）
    def normalize(code: str, name: str) -> str:
        code = str(code)
        if code.startswith(("sh", "sz", "bj", "SH", "SZ", "BJ")):
            return code.lower()
        # 科创板/主板
        if code.startswith(("600", "601", "603", "605", "688")):
            return f"sh{code}"
        # 创业板/主板
        if code.startswith(("000", "001", "002", "003", "300", "301")):
            return f"sz{code}"
        # 北交所（简化判断）
        if code.startswith(("43", "83", "87", "88")):
            return f"bj{code}"
        return code

    df["symbol"] = [
        normalize(df.loc[i, "symbol"] if "symbol" in df.columns else df.loc[i, "代码"],
                  df.loc[i, "name"] if "name" in df.columns else df.loc[i, "名称"])
        for i in df.index
    ]

    # 确保常用字段存在
    for k in ["price", "pct_chg", "chg", "volume", "amount"]:
        if k not in df.columns:
            df[k] = pd.NA

    # 排序一下：按成交额降序
    if "amount" in df.columns:
        df = df.sort_values("amount", ascending=False).reset_index(drop=True)

    # 附加抓取时间
    now_cn = dt.datetime.now(TZ_CN)
    df["ts"] = now_cn.isoformat(timespec="seconds")
    return df

# ---------- 后台轮询 ----------
async def poller():
    global _latest_df, _last_ts
    while True:
        try:
            now_cn = dt.datetime.now(TZ_CN)
            interval = POLL_SEC_MARKET if is_market_open(now_cn) else POLL_SEC_OFF
            df = await fetch_all_spot()
            async with _lock:
                _latest_df = df
                _last_ts = df["ts"].iloc[0]
        except Exception as e:
            # 出错时：延迟重试，避免打爆源站
            interval = max(POLL_SEC_OFF, 30)
        finally:
            await asyncio.sleep(interval)

@app.on_event("startup")
async def _startup():
    asyncio.create_task(poller())

# ---------- 工具 ----------
def filter_fields(df: pd.DataFrame, fields: Optional[List[str]]) -> pd.DataFrame:
    if not fields:
        return df
    cols = [c for c in fields if c in df.columns]
    # 确保 symbol 一定在
    if "symbol" not in cols:
        cols = ["symbol"] + cols
    return df[cols]

def symbol_match(df: pd.DataFrame, code: str) -> pd.DataFrame:
    code = code.strip().lower()
    if code.startswith(("sh", "sz", "bj")):
        return df[df["symbol"].str.lower() == code]
    # 纯数字：尝试补前缀匹配
    return df[df["symbol"].str.endswith(code)]

# ---------- API ----------
@app.get("/snapshot")
async def snapshot(
    fields: Optional[str] = Query(None, description="逗号分隔字段，如 price,pct_chg,amount"),
    limit: int = Query(1000, ge=1, le=10000),
    offset: int = Query(0, ge=0),
):
    async with _lock:
        if _latest_df is None:
            raise HTTPException(status_code=503, detail="数据尚未就绪，请稍后重试。")
        df = _latest_df

    flds = [f.strip() for f in fields.split(",")] if fields else None
    out = filter_fields(df, flds)
    total = len(out)
    out = out.iloc[offset: offset + limit]
    return JSONResponse({
        "ts": _last_ts,
        "count": len(out),
        "total": total,
        "fields": list(out.columns),
        "data": out.to_dict(orient="records"),
    })

@app.get("/stock/{code}")
async def stock(code: str, fields: Optional[str] = Query(None)):
    async with _lock:
        if _latest_df is None:
            raise HTTPException(status_code=503, detail="数据尚未就绪，请稍后重试。")
        df = _latest_df
    flds = [f.strip() for f in fields.split(",")] if fields else None
    sub = symbol_match(df, code)
    if sub.empty:
        raise HTTPException(status_code=404, detail=f"未找到股票：{code}")
    sub = filter_fields(sub, flds)
    return JSONResponse({
        "ts": sub["ts"].iloc[0],
        "fields": list(sub.columns),
        "data": sub.to_dict(orient="records")[0],
    })

@app.get("/stream")
async def stream():
    async def event_gen():
        last_seen = None
        while True:
            async with _lock:
                ts = _last_ts
                df = _latest_df
            if ts and ts != last_seen and df is not None:
                # 仅推送少量关键字段，避免过大消息（可按需调整）
                slim = df[["symbol", "name" if "name" in df.columns else "名称",
                           "price", "pct_chg", "amount", "ts"]].copy()
                yield f"data: {slim.to_json(orient='records', force_ascii=False)}\n\n"
                last_seen = ts
            await asyncio.sleep(1)
    return StreamingResponse(event_gen(), media_type="text/event-stream")

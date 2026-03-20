import aiohttp
import json
import html
from collections import OrderedDict
from datetime import datetime
from branches import BRANCHES

DAY_NAMES = {0: "월", 1: "화", 2: "수", 3: "목", 4: "금", 5: "토", 6: "일"}

URL = "https://www.megabox.co.kr/on/oh/ohb/SimpleBooking/selectBokdList.do"
HEADERS = {
    "Content-Type": "application/json; charset=UTF-8",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Referer": "https://www.megabox.co.kr/on/oh/ohb/SimpleBooking/simpleBookingPage.do",
    "X-Requested-With": "XMLHttpRequest",
}


def _base_params(branch_no):
    return {
        "brchNo1": branch_no,
        "brchNoListCnt": 1,
        "areaCd1": "DBC",
        "theabKindCd1": "DBC",
        "spclbYn1": "Y",
        "brchSpcl": "DBC",
    }


def date_label(date_str):
    dt = datetime.strptime(date_str, "%Y%m%d")
    return f"{dt.month}월 {dt.day}일({DAY_NAMES[dt.weekday()]})"


async def fetch_open_dates(branch_no):
    today = datetime.now().strftime("%Y%m%d")
    params = {**_base_params(branch_no), "playDe": today, "first": "Y"}
    async with aiohttp.ClientSession() as session:
        async with session.post(URL, json=params, headers=HEADERS, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            raw = await resp.read()
            data = json.loads(raw.decode("utf-8-sig"))
            return [d.get("playDe") for d in data.get("movieFormDeList", [])]


async def fetch_showtimes(branch_no, target_date):
    params = {**_base_params(branch_no), "playDe": target_date, "first": "N"}
    async with aiohttp.ClientSession() as session:
        async with session.post(URL, json=params, headers=HEADERS, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            raw = await resp.read()
            data = json.loads(raw.decode("utf-8-sig"))
            return data.get("movieFormList", [])


def format_showtimes(branch_no, showtime_list, label):
    branch_name = BRANCHES.get(branch_no, branch_no)
    grouped = OrderedDict()
    for s in showtime_list:
        movie = html.unescape(s.get("movieNm", ""))
        hall = html.unescape(s.get("theabExpoNm", ""))
        key = f"{movie}({hall})"
        if key not in grouped:
            grouped[key] = []
        start = s.get("playStartTime", "?")
        end = s.get("playEndTime", "?")
        rest = s.get("restSeatCnt", 0)
        total = s.get("totSeatCnt", 0)
        bookable = s.get("bokdAbleAt", "N")
        status = f"{rest}/{total}석" if bookable == "Y" else "매진"
        grouped[key].append(f"{start}~{end} {status}")

    lines = [f"[{branch_name}] {label}\n"]
    for title, times in grouped.items():
        lines.append(title)
        for t in times:
            lines.append(f"  {t}")
        lines.append("")

    return "\n".join(lines).strip()

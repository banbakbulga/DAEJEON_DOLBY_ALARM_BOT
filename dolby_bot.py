import requests
import json
import html
import os
from collections import OrderedDict
from datetime import datetime

# --- [설정값] ---
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
CHAT_ID = os.environ.get("CHAT_ID", "")
NOTIFIED_FILE = os.path.join(os.path.dirname(__file__), "notified.json")

DAY_NAMES = {0: "월", 1: "화", 2: "수", 3: "목", 4: "금", 5: "토", 6: "일"}

URL = 'https://www.megabox.co.kr/on/oh/ohb/SimpleBooking/selectBokdList.do'
HEADERS = {
    'Content-Type': 'application/json; charset=UTF-8',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
    'Referer': 'https://www.megabox.co.kr/on/oh/ohb/SimpleBooking/simpleBookingPage.do',
    'X-Requested-With': 'XMLHttpRequest'
}
BASE_PARAMS = {
    "brchNo1": "0028",
    "brchNoListCnt": 1,
    "areaCd1": "DBC",
    "theabKindCd1": "DBC",
    "spclbYn1": "Y",
    "brchSpcl": "DBC",
}


def date_label(date_str):
    dt = datetime.strptime(date_str, "%Y%m%d")
    return f"{dt.month}월 {dt.day}일({DAY_NAMES[dt.weekday()]})"


def load_notified():
    if os.path.exists(NOTIFIED_FILE):
        with open(NOTIFIED_FILE, "r") as f:
            return set(json.load(f))
    return set()


def save_notified(notified):
    with open(NOTIFIED_FILE, "w") as f:
        json.dump(sorted(notified), f)


def fetch_open_dates():
    today = datetime.now().strftime("%Y%m%d")
    params = {**BASE_PARAMS, "playDe": today, "first": "Y"}
    r = requests.post(URL, json=params, headers=HEADERS, timeout=10)
    data = json.loads(r.content.decode('utf-8-sig'))
    return [d.get('playDe') for d in data.get("movieFormDeList", [])]


def fetch_showtimes(target_date):
    params = {**BASE_PARAMS, "playDe": target_date, "first": "N"}
    r = requests.post(URL, json=params, headers=HEADERS, timeout=10)
    data = json.loads(r.content.decode('utf-8-sig'))
    return data.get("movieFormList", [])


def format_showtimes(showtime_list, label):
    grouped = OrderedDict()
    for s in showtime_list:
        movie = html.unescape(s.get('movieNm', ''))
        hall = html.unescape(s.get('theabExpoNm', ''))
        key = f"{movie}({hall})"
        if key not in grouped:
            grouped[key] = []
        start = s.get('playStartTime', '?')
        end = s.get('playEndTime', '?')
        rest = s.get('restSeatCnt', 0)
        total = s.get('totSeatCnt', 0)
        bookable = s.get('bokdAbleAt', 'N')
        status = f"{rest}/{total}석" if bookable == 'Y' else "매진"
        grouped[key].append(f"{start}~{end} {status}")

    lines = [f"[대전신세계 돌비시네마] {label}\n"]
    for title, times in grouped.items():
        lines.append(title)
        for t in times:
            lines.append(f"  {t}")
        lines.append("")

    return "\n".join(lines).strip()


def send_telegram(msg):
    requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        json={"chat_id": CHAT_ID, "text": msg}
    )


def main():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 돌비 예매 체크 시작")

    notified = load_notified()
    current_dates = fetch_open_dates()
    new_dates = [d for d in current_dates if d not in notified]

    if not new_dates:
        print(f"  새로 열린 날짜 없음 (오픈: {len(current_dates)}일)")
        return

    for nd in sorted(new_dates):
        label = date_label(nd)
        showtimes = fetch_showtimes(nd)

        if showtimes:
            result = format_showtimes(showtimes, label)
            print(f"  새 예매 오픈! {label}\n{result}")
            msg = f"🔔 돌비 예매 오픈!\n\n{result}\n\n👉 https://www.megabox.co.kr"
            send_telegram(msg)
            print(f"  텔레그램 발송 완료!")
        else:
            print(f"  {label} 날짜 열렸지만 시간표 없음")

        notified.add(nd)

    save_notified(notified)
    print("  notified.json 업데이트 완료")


if __name__ == "__main__":
    main()

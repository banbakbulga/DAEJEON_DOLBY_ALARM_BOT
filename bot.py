import os
import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from branches import BRANCHES
from megabox import fetch_open_dates, fetch_showtimes, format_showtimes, date_label

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
CHAT_ID = os.environ.get("CHAT_ID", "")

# 감시 대상 (대전신세계아트앤사이언스)
WATCH_BRANCH = "0028"

# 알림 완료된 날짜 (메모리)
notified_dates = set()


# --- 명령어 핸들러 ---

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lines = ["🎬 대전신세계 돌비시네마 예매 오픈 알림봇\n"]
    lines.append("대전신세계아트앤사이언스 돌비시네마에")
    lines.append("새 예매가 열리면 자동으로 알려드려요!")
    lines.append("\n사용법은 /help 를 입력해주세요.")
    await update.message.reply_text("\n".join(lines))


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lines = ["📌 명령어 목록\n"]
    lines.append("  /now - 현재 예매 현황 조회")
    lines.append("  /theaters - 전국 돌비시네마 목록")
    lines.append("  /help - 명령어 목록")
    await update.message.reply_text("\n".join(lines))


async def cmd_theaters(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lines = ["🏢 전국 돌비시네마 목록\n"]
    for code, name in BRANCHES.items():
        lines.append(f"  {name}")
    await update.message.reply_text("\n".join(lines))


def find_branch(keyword):
    """키워드로 극장 찾기"""
    matches = []
    for code, name in BRANCHES.items():
        if keyword in name:
            matches.append((code, name))
    return matches


async def cmd_now(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args:
        keyword = " ".join(context.args)
        matches = find_branch(keyword)
        if not matches:
            await update.message.reply_text(f"'{keyword}'에 해당하는 극장을 찾을 수 없어요.")
            return
        if len(matches) > 1:
            lines = [f"'{keyword}' 검색 결과가 여러 개예요:\n"]
            for code, name in matches:
                lines.append(f"  {name}")
            await update.message.reply_text("\n".join(lines))
            return
        branch_list = [matches[0][0]]
    else:
        branch_list = [WATCH_BRANCH]

    await update.message.reply_text("🔍 조회 중...")

    results = []
    for branch_no in branch_list:
        try:
            dates = await fetch_open_dates(branch_no)
            if not dates:
                name = BRANCHES.get(branch_no, branch_no)
                results.append(f"[{name}]\n  예매 가능한 날짜 없음\n")
                continue
            for d in dates:
                showtimes = await fetch_showtimes(branch_no, d)
                if showtimes:
                    label = date_label(d)
                    results.append(format_showtimes(branch_no, showtimes, label))
        except Exception as e:
            name = BRANCHES.get(branch_no, branch_no)
            results.append(f"[{name}] 조회 실패: {e}\n")

    if results:
        msg = "\n\n".join(results)
        if len(msg) > 4000:
            for i in range(0, len(msg), 4000):
                await update.message.reply_text(msg[i:i+4000])
        else:
            await update.message.reply_text(msg)
    else:
        await update.message.reply_text("조회 결과가 없어요.")


# --- 자동 체크 (5분마다) ---

async def check_new_dates(context: ContextTypes.DEFAULT_TYPE):
    logger.info("자동 체크 시작")

    try:
        current_dates = await fetch_open_dates(WATCH_BRANCH)

        for d in current_dates:
            if d in notified_dates:
                continue

            showtimes = await fetch_showtimes(WATCH_BRANCH, d)
            if not showtimes:
                continue

            label = date_label(d)
            result = format_showtimes(WATCH_BRANCH, showtimes, label)
            msg = f"🔔 돌비 예매 오픈!\n\n{result}\n\n👉 https://www.megabox.co.kr"

            try:
                await context.bot.send_message(chat_id=CHAT_ID, text=msg)
            except Exception as e:
                logger.error(f"메시지 발송 실패: {e}")

            notified_dates.add(d)
            logger.info(f"알림 발송: {BRANCHES.get(WATCH_BRANCH)} {label}")

    except Exception as e:
        logger.error(f"체크 실패: {e}")

    logger.info("자동 체크 완료")


# --- 시작 시 기존 날짜 등록 ---

async def init_notified(app: Application):
    """서버 재시작 시 이미 오픈된 날짜는 알림 안 보내도록 처리"""
    try:
        existing_dates = await fetch_open_dates(WATCH_BRANCH)
        notified_dates.update(existing_dates)
        logger.info(f"기존 오픈 날짜 {len(existing_dates)}개 등록")
    except Exception as e:
        logger.error(f"초기화 실패: {e}")


# --- 헬스체크 서버 (Render 슬립 방지) ---

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

    def log_message(self, format, *args):
        pass


def start_health_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    logger.info(f"헬스체크 서버 시작 (포트 {port})")


# --- 메인 ---

def main():
    start_health_server()

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("theaters", cmd_theaters))
    app.add_handler(CommandHandler("now", cmd_now))

    # 시작 시 기존 날짜 처리 (재시작 후 중복 알림 방지)
    app.post_init = init_notified

    # 5분(300초)마다 자동 체크
    app.job_queue.run_repeating(check_new_dates, interval=300, first=10)

    logger.info("봇 시작!")
    app.run_polling()


if __name__ == "__main__":
    main()

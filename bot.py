import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from branches import BRANCHES
from megabox import fetch_open_dates, fetch_showtimes, format_showtimes, date_label
import db

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")


# --- 명령어 핸들러 ---

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lines = ["🎬 메가박스 돌비시네마 예매 알림봇\n"]
    lines.append("전국 돌비시네마 새 예매가 열리면 알려드려요!\n")
    lines.append("📌 명령어")
    lines.append("  /add 극장명 - 감시 추가")
    lines.append("  /remove 극장명 - 감시 해제")
    lines.append("  /list - 내 감시 목록")
    lines.append("  /now - 현재 예매 현황 조회")
    lines.append("  /theaters - 전국 돌비시네마 목록")
    await update.message.reply_text("\n".join(lines))


async def cmd_theaters(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lines = ["🏢 전국 돌비시네마 목록\n"]
    for code, name in BRANCHES.items():
        lines.append(f"  {name}")
    lines.append("\n/add 극장명 으로 등록하세요.")
    await update.message.reply_text("\n".join(lines))


def find_branch(keyword):
    """키워드로 극장 찾기"""
    matches = []
    for code, name in BRANCHES.items():
        if keyword in name:
            matches.append((code, name))
    return matches


async def cmd_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("사용법: /add 극장명\n예: /add 대전")
        return

    keyword = " ".join(context.args)
    matches = find_branch(keyword)

    if not matches:
        await update.message.reply_text(f"'{keyword}'에 해당하는 극장을 찾을 수 없어요.\n/theaters 로 목록을 확인해보세요.")
        return

    if len(matches) > 1:
        lines = [f"'{keyword}' 검색 결과가 여러 개예요:\n"]
        for code, name in matches:
            lines.append(f"  {name}")
        lines.append("\n좀 더 정확하게 입력해주세요.")
        await update.message.reply_text("\n".join(lines))
        return

    code, name = matches[0]
    chat_id = update.effective_chat.id
    db.add_subscription(chat_id, code)

    # 현재 오픈된 날짜들 미리 notified 처리 (기존 날짜는 알림 안 보내기)
    try:
        existing_dates = await fetch_open_dates(code)
        for d in existing_dates:
            db.mark_notified(code, d)
    except Exception:
        pass

    await update.message.reply_text(f"✅ {name} 감시 등록 완료!\n새 예매가 열리면 알려드릴게요.")


async def cmd_remove(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("사용법: /remove 극장명\n예: /remove 대전")
        return

    keyword = " ".join(context.args)
    matches = find_branch(keyword)

    if not matches:
        await update.message.reply_text(f"'{keyword}'에 해당하는 극장을 찾을 수 없어요.")
        return

    if len(matches) > 1:
        lines = [f"'{keyword}' 검색 결과가 여러 개예요:\n"]
        for code, name in matches:
            lines.append(f"  {name}")
        lines.append("\n좀 더 정확하게 입력해주세요.")
        await update.message.reply_text("\n".join(lines))
        return

    code, name = matches[0]
    chat_id = update.effective_chat.id
    removed = db.remove_subscription(chat_id, code)

    if removed:
        await update.message.reply_text(f"🗑 {name} 감시 해제했어요.")
    else:
        await update.message.reply_text(f"{name}은(는) 감시 목록에 없어요.")


async def cmd_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    branches = db.get_user_branches(chat_id)

    if not branches:
        await update.message.reply_text("감시 중인 극장이 없어요.\n/add 극장명 으로 등록해보세요.")
        return

    lines = ["📋 내 감시 목록\n"]
    for code in branches:
        name = BRANCHES.get(code, code)
        lines.append(f"  {name}")
    await update.message.reply_text("\n".join(lines))


async def cmd_now(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    # 인자가 있으면 특정 극장, 없으면 내 구독 목록 전체
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
        branch_list = db.get_user_branches(chat_id)
        if not branch_list:
            await update.message.reply_text("감시 중인 극장이 없어요.\n/now 극장명 으로 직접 조회하거나\n/add 로 등록해보세요.")
            return

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
        # 텔레그램 메시지 길이 제한 (4096자)
        if len(msg) > 4000:
            for i in range(0, len(msg), 4000):
                await update.message.reply_text(msg[i:i+4000])
        else:
            await update.message.reply_text(msg)
    else:
        await update.message.reply_text("조회 결과가 없어요.")


# --- 자동 체크 (15분마다) ---

async def check_new_dates(context: ContextTypes.DEFAULT_TYPE):
    logger.info("자동 체크 시작")
    branches = db.get_all_monitored_branches()

    for branch_no in branches:
        try:
            current_dates = await fetch_open_dates(branch_no)

            for d in current_dates:
                if db.is_notified(branch_no, d):
                    continue

                showtimes = await fetch_showtimes(branch_no, d)
                if not showtimes:
                    continue

                label = date_label(d)
                result = format_showtimes(branch_no, showtimes, label)
                msg = f"🔔 돌비 예매 오픈!\n\n{result}\n\n👉 https://www.megabox.co.kr"

                subscribers = db.get_subscribers_for_branch(branch_no)
                for chat_id in subscribers:
                    try:
                        await context.bot.send_message(chat_id=chat_id, text=msg)
                    except Exception as e:
                        logger.error(f"메시지 발송 실패 (chat_id={chat_id}): {e}")

                db.mark_notified(branch_no, d)
                logger.info(f"알림 발송: {BRANCHES.get(branch_no)} {label} → {len(subscribers)}명")

        except Exception as e:
            logger.error(f"체크 실패 ({branch_no}): {e}")

    logger.info("자동 체크 완료")


# --- 메인 ---

def main():
    db.init_db()

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("theaters", cmd_theaters))
    app.add_handler(CommandHandler("add", cmd_add))
    app.add_handler(CommandHandler("remove", cmd_remove))
    app.add_handler(CommandHandler("list", cmd_list))
    app.add_handler(CommandHandler("now", cmd_now))

    # 15분(900초)마다 자동 체크
    app.job_queue.run_repeating(check_new_dates, interval=900, first=10)

    logger.info("봇 시작!")
    app.run_polling()


if __name__ == "__main__":
    main()

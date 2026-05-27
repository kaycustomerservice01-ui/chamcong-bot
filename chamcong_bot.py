# -*- coding: utf-8 -*-
import logging, os, json
import pytz
from datetime import datetime, timedelta
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ContextTypes, ConversationHandler
)
import gspread
from google.oauth2.service_account import Credentials

BOT_TOKEN  = "8452164068:AAFKjS2lvZ_nBye1ERzIuDWyDqTrK8IQc9c"
SHEET_ID   = "1k7yS52nd0HQRWhVDVBm7Xxc9ckARgThy9XFoWznq3oI"
TIMEZONE   = "Asia/Ho_Chi_Minh"
GROUP_ID   = -5113728440

CA_NGAY = "☀️ Ca Ngày"
CA_DEM  = "🌙 Ca Đêm"

HEADERS = ["Ngày","Thứ","Tên Nhân Viên","Telegram ID","Ca Làm","Loại","Giờ Check In","Giờ Check Out","Tổng Giờ","Ghi Chú"]
CHON_LOAI, CHON_CA, CHON_NGHI, CHON_NGAY_BU, CHON_CA_BU, NHAP_LY_DO_BU = range(6)

logging.basicConfig(format="%(asctime)s | %(levelname)s | %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

def get_sheet():
    scopes = ["https://spreadsheets.google.com/feeds","https://www.googleapis.com/auth/drive"]
    creds_info = json.loads(os.environ["GOOGLE_CREDS_JSON"])
    creds  = Credentials.from_service_account_info(creds_info, scopes=scopes)
    client = gspread.authorize(creds)
    sp     = client.open_by_key(SHEET_ID)
    month  = datetime.now(pytz.timezone(TIMEZONE)).strftime("%m-%Y")
    try:
        sh = sp.worksheet(month)
    except gspread.WorksheetNotFound:
        sh = sp.add_worksheet(title=month, rows=500, cols=10)
        sh.append_row(HEADERS)
        sh.format("A1:J1", {"backgroundColor":{"red":0.13,"green":0.59,"blue":0.95},"textFormat":{"bold":True,"foregroundColor":{"red":1,"green":1,"blue":1}}})
    return sh

def tim_dong(sheet, user_id, ca):
    hom_nay = datetime.now(pytz.timezone(TIMEZONE)).strftime("%d/%m/%Y")
    for i, row in enumerate(sheet.get_all_values()[1:], start=2):
        if len(row) >= 5 and row[0] == hom_nay and row[3] == str(user_id) and row[4] == ca:
            return i, row
    return None, None

def tinh_tong_gio(gio_in, gio_out):
    try:
        fmt = "%H:%M:%S"
        sec = (datetime.strptime(gio_out,fmt) - datetime.strptime(gio_in,fmt)).total_seconds()
        if sec < 0: sec += 86400
        return f"{int(sec//3600)}h{int((sec%3600)//60):02d}m"
    except:
        return "N/A"

def kb_loai():
    return ReplyKeyboardMarkup([
        [KeyboardButton("✅ Check In"), KeyboardButton("📚 Check Out")],
        [KeyboardButton("📅 Nghỉ Hôm Nay"), KeyboardButton("🔄 Chấm Bù")],
        [KeyboardButton("❌ Huỷ")]
    ], resize_keyboard=True, one_time_keyboard=True)

def kb_ca():
    return ReplyKeyboardMarkup([
        [KeyboardButton(CA_NGAY), KeyboardButton(CA_DEM)],
        [KeyboardButton("❌ Huỷ")]
    ], resize_keyboard=True, one_time_keyboard=True)

def kb_nghi():
    return ReplyKeyboardMarkup([
        [KeyboardButton("🤒 Nghỉ Bệnh"), KeyboardButton("📋 Nghỉ Phép")],
        [KeyboardButton("🏖️ Nghỉ Lễ"), KeyboardButton("📝 Việc Cá Nhân")],
        [KeyboardButton("❌ Huỷ")]
    ], resize_keyboard=True, one_time_keyboard=True)

def kb_ngay_bu():
    tz = pytz.timezone(TIMEZONE)
    hom_nay = datetime.now(tz)
    buttons = []
    row = []
    for i in range(1, 31):
        ngay = hom_nay - timedelta(days=i)
        label = ngay.strftime("%d/%m")
        row.append(KeyboardButton(f"📅 {label}"))
        if len(row) == 3:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([KeyboardButton("❌ Huỷ")])
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True, one_time_keyboard=True)

RKR = ReplyKeyboardRemove()

def now_vn():
    return datetime.now(pytz.timezone(TIMEZONE))

def thu_vn(dt):
    return ["Thứ Hai","Thứ Ba","Thứ Tư","Thứ Năm","Thứ Sáu","Thứ Bảy","Chủ Nhật"][dt.weekday()]

async def start(update, ctx):
    u = update.effective_user
    await update.message.reply_text(
        f"👋 Xin chào *{u.full_name}*!\n\n"
        f"🤖 *Bot Chấm Công*\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📌 Lệnh:\n"
        f"  /chamcong – Chấm công\n"
        f"  /lichsu   – Lịch sử hôm nay\n"
        f"  /help     – Hướng dẫn\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"💡 Nhấn /chamcong để bắt đầu!",
        parse_mode="Markdown"
    )

async def help_cmd(update, ctx):
    await update.message.reply_text(
        "📖 *HƯỚNG DẪN*\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "1️⃣ /chamcong\n"
        "2️⃣ Chọn: Check In / Check Out / Nghỉ / Chấm Bù\n"
        "3️⃣ Chọn ca: Ca Ngày hoặc Ca Đêm\n"
        "4️⃣ Bot ghi tự động vào Google Sheet ✅",
        parse_mode="Markdown"
    )

async def reset(update, ctx):
    ctx.user_data.clear()
    await update.message.reply_text("♻️ Đã reset! Thử /chamcong lại nhé.", reply_markup=RKR)

async def chamcong_start(update, ctx):
    ctx.user_data.clear()
    await update.message.reply_text(
        "📋 *Chọn loại chấm công:*",
        parse_mode="Markdown",
        reply_markup=kb_loai()
    )
    return CHON_LOAI

async def chon_loai(update, ctx):
    text = update.message.text.strip()
    if text == "❌ Huỷ":
        await update.message.reply_text("❌ Đã huỷ.", reply_markup=RKR)
        return ConversationHandler.END
    ctx.user_data["loai"] = text
    if "Nghỉ" in text and "Chấm Bù" not in text:
        await update.message.reply_text("📝 *Chọn lý do nghỉ:*", parse_mode="Markdown", reply_markup=kb_nghi())
        return CHON_NGHI
    if "Chấm Bù" in text:
        await update.message.reply_text(
            "📅 *Chọn ngày cần chấm bù:*\n_(Chọn ngày bạn quên chấm công)_",
            parse_mode="Markdown",
            reply_markup=kb_ngay_bu()
        )
        return CHON_NGAY_BU
    await update.message.reply_text("🕐 *Chọn ca làm việc:*", parse_mode="Markdown", reply_markup=kb_ca())
    return CHON_CA

async def chon_ngay_bu(update, ctx):
    text = update.message.text.strip()
    if text == "❌ Huỷ":
        await update.message.reply_text("❌ Đã huỷ.", reply_markup=RKR)
        return ConversationHandler.END
    try:
        label = text.replace("📅 ", "").strip()
        day, month = label.split("/")
        year = now_vn().year
        ngay_bu = f"{day}/{month}/{year}"
        ctx.user_data["ngay_bu"] = ngay_bu
    except:
        await update.message.reply_text("⚠️ Chọn ngày hợp lệ.", reply_markup=kb_ngay_bu())
        return CHON_NGAY_BU
    await update.message.reply_text("🕐 *Chọn ca cần chấm bù:*", parse_mode="Markdown", reply_markup=kb_ca())
    return CHON_CA_BU

async def chon_ca_bu(update, ctx):
    ca = update.message.text.strip()
    if ca == "❌ Huỷ":
        await update.message.reply_text("❌ Đã huỷ.", reply_markup=RKR)
        return ConversationHandler.END
    if ca not in [CA_NGAY, CA_DEM]:
        await update.message.reply_text("⚠️ Chọn ca hợp lệ.", reply_markup=kb_ca())
        return CHON_CA_BU
    ctx.user_data["ca_bu"] = ca
    await update.message.reply_text(
        "📝 *Nhập lý do chấm bù:*\n_(Ví dụ: Quên chấm công, Đi trễ, ...)_",
        parse_mode="Markdown",
        reply_markup=RKR
    )
    return NHAP_LY_DO_BU

async def nhap_ly_do_bu(update, ctx):
    ly_do   = update.message.text.strip()
    user    = update.effective_user
    ngay_bu = ctx.user_data.get("ngay_bu", "")
    ca_bu   = ctx.user_data.get("ca_bu", "")
    gio     = now_vn().strftime("%H:%M:%S")
    try:
        dt_bu  = datetime.strptime(ngay_bu, "%d/%m/%Y")
        thu_bu = thu_vn(dt_bu)
    except:
        thu_bu = "–"
    try:
        sheet = get_sheet()
        sheet.append_row([ngay_bu, thu_bu, user.full_name or user.username or "Unknown", str(user.id), ca_bu, "Chấm Bù", gio, "", "", ly_do])
        await update.message.reply_text(
            f"🔄 *CHẤM BÙ*\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"👤 {user.full_name}\n"
            f"🆔 `{user.id}`\n"
            f"📅 Ngày bù: *{ngay_bu}*\n"
            f"🏷️ {ca_bu}\n"
            f"📝 Lý do: *{ly_do}*\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"✅ Đã ghi nhận chấm bù thành công!\n"
            f"⏰ Lần sau anh/chị nhớ chấm công đúng giờ để tránh thiếu công nhé 😊",
            parse_mode="Markdown", reply_markup=RKR
        )
    except Exception as e:
        logger.error(e)
        await update.message.reply_text(f"❌ Lỗi: `{str(e)[:120]}`", parse_mode="Markdown", reply_markup=RKR)
    return ConversationHandler.END

async def chon_ca(update, ctx):
    ca   = update.message.text.strip()
    user = update.effective_user
    loai = ctx.user_data.get("loai", "")
    if ca == "❌ Huỷ":
        await update.message.reply_text("❌ Đã huỷ.", reply_markup=RKR)
        return ConversationHandler.END
    if ca not in [CA_NGAY, CA_DEM]:
        await update.message.reply_text("⚠️ Chọn ca hợp lệ.", reply_markup=kb_ca())
        return CHON_CA
    dt   = now_vn()
    gio  = dt.strftime("%H:%M:%S")
    ngay = dt.strftime("%d/%m/%Y")
    thu  = thu_vn(dt)
    try:
        sheet = get_sheet()
        if "Check In" in loai:
            idx, existing = tim_dong(sheet, user.id, ca)
            if existing and existing[6]:
                await update.message.reply_text(f"⚠️ Đã Check In *{ca}* lúc *{existing[6]}*!", parse_mode="Markdown", reply_markup=RKR)
                return ConversationHandler.END
            sheet.append_row([ngay, thu, user.full_name or user.username or "Unknown", str(user.id), ca, "Check In", gio, "", "", ""])
            await update.message.reply_text(
                f"✅ *CHECK IN*\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"👤 {user.full_name}\n"
                f"🆔 `{user.id}`\n"
                f"📅 {thu}, {ngay}\n"
                f"🕐 Giờ vào: *{gio}*\n"
                f"🏷️ {ca}\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"☀️ Chúc bạn có ngày làm việc vui vẻ và hiệu quả! 💪",
                parse_mode="Markdown", reply_markup=RKR
            )
        elif "Check Out" in loai:
            idx, existing = tim_dong(sheet, user.id, ca)
            if not existing:
                await update.message.reply_text(f"⚠️ Chưa có Check In cho *{ca}* hôm nay!", parse_mode="Markdown", reply_markup=RKR)
                return ConversationHandler.END
            if existing[7]:
                await update.message.reply_text(f"⚠️ Đã Check Out lúc *{existing[7]}* rồi!", parse_mode="Markdown", reply_markup=RKR)
                return ConversationHandler.END
            tong = tinh_tong_gio(existing[6], gio)
            sheet.update_cell(idx, 8, gio)
            sheet.update_cell(idx, 9, tong)
            await update.message.reply_text(
                f"📚 *CHECK OUT*\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"👤 {user.full_name}\n"
                f"🆔 `{user.id}`\n"
                f"📅 {thu}, {ngay}\n"
                f"🕐 Vào:  *{existing[6]}*\n"
                f"🕔 Ra:   *{gio}*\n"
                f"⏱️ Tổng: *{tong}*\n"
                f"🏷️ {ca}\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"🌙 Cảm ơn bạn đã cống hiến hôm nay! Nghỉ ngơi vui vẻ nhé! 🎉",
                parse_mode="Markdown", reply_markup=RKR
            )
    except Exception as e:
        logger.error(e)
        await update.message.reply_text(f"❌ Lỗi kết nối Sheet!\n`{str(e)[:120]}`", parse_mode="Markdown", reply_markup=RKR)
    return ConversationHandler.END

async def chon_nghi(update, ctx):
    ly_do = update.message.text.strip()
    user  = update.effective_user
    if ly_do == "❌ Huỷ":
        await update.message.reply_text("❌ Đã huỷ.", reply_markup=RKR)
        return ConversationHandler.END
    dt   = now_vn()
    ngay = dt.strftime("%d/%m/%Y")
    thu  = thu_vn(dt)
    gio  = dt.strftime("%H:%M:%S")
    ghi_chu = ly_do.replace("🤒 ", "").replace("📋 ", "").replace("🏖️ ", "").replace("📝 ", "")
    try:
        sheet = get_sheet()
        sheet.append_row([ngay, thu, user.full_name or user.username or "Unknown", str(user.id), "–", "Nghỉ", gio, "", "", ghi_chu])
        await update.message.reply_text(
            f"📅 *ĐĂNG KÝ NGHỈ*\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"👤 {user.full_name}\n"
            f"🆔 `{user.id}`\n"
            f"📅 {thu}, {ngay}\n"
            f"📝 Lý do: *{ghi_chu}*\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📊 Đã ghi Google Sheet ✔️",
            parse_mode="Markdown", reply_markup=RKR
        )
    except Exception as e:
        logger.error(e)
        await update.message.reply_text(f"❌ Lỗi: `{str(e)[:120]}`", parse_mode="Markdown", reply_markup=RKR)
    return ConversationHandler.END

async def huy(update, ctx):
    await update.message.reply_text("❌ Đã huỷ.", reply_markup=RKR)
    return ConversationHandler.END

async def lichsu(update, ctx):
    user    = update.effective_user
    hom_nay = now_vn().strftime("%d/%m/%Y")
    try:
        sheet = get_sheet()
        rows  = [r for r in sheet.get_all_values()[1:] if len(r) >= 4 and r[0] == hom_nay and r[3] == str(user.id)]
        if not rows:
            await update.message.reply_text(f"🔭 Chưa có dữ liệu hôm nay ({hom_nay}).", reply_markup=RKR)
            return
        msg = f"📊 *Lịch sử – {hom_nay}*\n━━━━━━━━━━━━━━━━━━\n"
        for r in rows:
            msg += f"\n🏷️ *{r[5] if len(r)>5 else '–'}* | {r[4] if len(r)>4 else '–'}\n"
            msg += f"   🕐 {r[6] if len(r)>6 else '–'}  →  🕔 {r[7] if len(r)>7 else 'Chưa out'}\n"
            msg += f"   ⏱️ {r[8] if len(r)>8 else '–'}\n"
            if len(r) > 9 and r[9]:
                msg += f"   📝 {r[9]}\n"
        await update.message.reply_text(msg, parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ Lỗi: `{str(e)[:120]}`", parse_mode="Markdown")

async def nhac_6h(ctx):
    await ctx.bot.send_message(
        chat_id=GROUP_ID,
        text=(
            "📢 *NHẮC NHỞ CHẤM CÔNG*\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "🌤️ Chúc các bạn ngày mới vui vẻ!\n"
            "⏰ Đã 6:00 sáng rồi! Mọi người nhớ chấm công đầy đủ để tránh thiếu công nhé 💪\n"
            "Chúc mọi người một ngày làm việc hiệu quả 🌤️\n"
            "━━━━━━━━━━━━━━━━━━"
        ),
        parse_mode="Markdown"
    )

async def nhac_9h(ctx):
    await ctx.bot.send_message(
        chat_id=GROUP_ID,
        text=(
            "📢 *THÔNG BÁO CHƯA CHẤM CÔNG*\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "⚠️ Hệ thống ghi nhận vẫn còn nhân viên chưa chấm công hôm nay.\n"
            "Mọi người vui lòng kiểm tra và chấm công sớm giúp admin nhé ⏰\n"
            "Tránh trường hợp quên chấm dẫn đến phải chấm bù ạ 😊\n"
            "━━━━━━━━━━━━━━━━━━"
        ),
        parse_mode="Markdown"
    )

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    from datetime import time as dtime
    tz = pytz.timezone(TIMEZONE)
    app.job_queue.run_daily(nhac_6h, time=dtime(6, 0, 0, tzinfo=tz))
    app.job_queue.run_daily(nhac_9h, time=dtime(9, 0, 0, tzinfo=tz))

    conv = ConversationHandler(
        entry_points=[CommandHandler("chamcong", chamcong_start)],
        states={
            CHON_LOAI:     [MessageHandler(filters.TEXT & ~filters.COMMAND, chon_loai)],
            CHON_CA:       [MessageHandler(filters.TEXT & ~filters.COMMAND, chon_ca)],
            CHON_NGHI:     [MessageHandler(filters.TEXT & ~filters.COMMAND, chon_nghi)],
            CHON_NGAY_BU:  [MessageHandler(filters.TEXT & ~filters.COMMAND, chon_ngay_bu)],
            CHON_CA_BU:    [MessageHandler(filters.TEXT & ~filters.COMMAND, chon_ca_bu)],
            NHAP_LY_DO_BU: [MessageHandler(filters.TEXT & ~filters.COMMAND, nhap_ly_do_bu)],
        },
        fallbacks=[CommandHandler("huy", huy)],
    )
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(CommandHandler("lichsu", lichsu))
    app.add_handler(conv)
    logger.info("✅ Bot đang chạy...")
    app.run_polling()

if __name__ == "__main__":
    main()

# update v3

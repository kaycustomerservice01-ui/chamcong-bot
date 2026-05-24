"""
Bot Telegram Chấm Công — Deploy Railway
Tổng giờ tính từ Check In thực tế → Check Out thực tế
"""

import logging
import pytz
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ContextTypes, ConversationHandler
)
import gspread
from google.oauth2.service_account import Credentials

# ── CẤU HÌNH ──────────────────────────────────────────────────
BOT_TOKEN  = "8452164068:AAFKjS2lvZ_nBye1ERzIuDWyDqTrK8IQc9c"
SHEET_ID   = "1k7yS52nd0HQRWhVDVBm7Xxc9ckARgThy9XFoWznq3oI"
CREDS_FILE = "credentials.json"
TIMEZONE   = "Asia/Ho_Chi_Minh"

# Tên ca — chỉ là nhãn, không ràng buộc giờ
CA_NGAY = "☀️ Ca Ngày"
CA_DEM  = "🌙 Ca Đêm"

HEADERS = [
    "Ngày", "Thứ", "Tên Nhân Viên", "Telegram ID",
    "Ca Làm", "Loại", "Giờ Check In", "Giờ Check Out",
    "Tổng Giờ", "Ghi Chú"
]

CHON_LOAI, CHON_CA, CHON_NGHI = range(3)

logging.basicConfig(format="%(asctime)s | %(levelname)s | %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# ── GOOGLE SHEETS ──────────────────────────────────────────────
def get_sheet():
    scopes = ["https://spreadsheets.google.com/feeds",
              "https://www.googleapis.com/auth/drive"]
    creds  = Credentials.from_service_account_file(CREDS_FILE, scopes=scopes)
    client = gspread.authorize(creds)
    sp     = client.open_by_key(SHEET_ID)
    month  = datetime.now(pytz.timezone(TIMEZONE)).strftime("%m-%Y")
    try:
        sh = sp.worksheet(month)
    except gspread.WorksheetNotFound:
        sh = sp.add_worksheet(title=month, rows=500, cols=10)
        sh.append_row(HEADERS)
        sh.format("A1:J1", {
            "backgroundColor": {"red": 0.13, "green": 0.59, "blue": 0.95},
            "textFormat": {"bold": True,
                           "foregroundColor": {"red": 1, "green": 1, "blue": 1}}
        })
    return sh

def tim_dong(sheet, user_id: str, ca: str):
    tz      = pytz.timezone(TIMEZONE)
    hom_nay = datetime.now(tz).strftime("%d/%m/%Y")
    for i, row in enumerate(sheet.get_all_values()[1:], start=2):
        if len(row) >= 5 and row[0] == hom_nay and row[3] == str(user_id) and row[4] == ca:
            return i, row
    return None, None

def tinh_tong_gio(gio_in: str, gio_out: str) -> str:
    try:
        fmt   = "%H:%M:%S"
        t_in  = datetime.strptime(gio_in,  fmt)
        t_out = datetime.strptime(gio_out, fmt)
        sec   = (t_out - t_in).total_seconds()
        if sec < 0:
            sec += 86400          # ca qua đêm
        h, m  = int(sec // 3600), int((sec % 3600) // 60)
        return f"{h}h{m:02d}m"
    except Exception:
        return "N/A"

# ── KEYBOARDS ─────────────────────────────────────────────────
def kb_loai():
    return ReplyKeyboardMarkup(
        [[KeyboardButton("✅ Check In"),      KeyboardButton("🔚 Check Out")],
         [KeyboardButton("📅 Nghỉ Hôm Nay"), KeyboardButton("🔄 Chấm Bù")],
         [KeyboardButton("❌ Huỷ")]],
        resize_keyboard=True, one_time_keyboard=True)

def kb_ca():
    return ReplyKeyboardMarkup(
        [[KeyboardButton(CA_NGAY), KeyboardButton(CA_DEM)],
         [KeyboardButton("❌ Huỷ")]],
        resize_keyboard=True, one_time_keyboard=True)

def kb_nghi():
    return ReplyKeyboardMarkup(
        [[KeyboardButton("🤒 Nghỉ Bệnh"),    KeyboardButton("📋 Nghỉ Phép")],
         [KeyboardButton("🏖️ Nghỉ Lễ"),      KeyboardButton("📝 Việc Cá Nhân")],
         [KeyboardButton("❌ Huỷ")]],
        resize_keyboard=True, one_time_keyboard=True)

RKR = ReplyKeyboardRemove()

# ── HELPERS ────────────────────────────────────────────────────
def now_vn():
    return datetime.now(pytz.timezone(TIMEZONE))

def thu_vn(dt):
    return ["Thứ Hai","Thứ Ba","Thứ Tư","Thứ Năm","Thứ Sáu","Thứ Bảy","Chủ Nhật"][dt.weekday()]

# ── COMMANDS ──────────────────────────────────────────────────
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    await update.message.reply_text(
        f"👋 Xin chào *{u.full_name}*!\n\n"
        "🤖 *Bot Chấm Công* — hệ thống điểm danh tự động\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "📌 Lệnh:\n"
        "  /chamcong — Chấm công\n"
        "  /lichsu   — Lịch sử hôm nay\n"
        "  /help     — Hướng dẫn\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "💡 Nhấn /chamcong để bắt đầu!",
        parse_mode="Markdown")

async def help_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 *HƯỚNG DẪN*\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "1️⃣ /chamcong\n"
        "2️⃣ Chọn: Check In / Check Out / Nghỉ / Chấm Bù\n"
        "3️⃣ Chọn ca: Ca Ngày hoặc Ca Đêm\n"
        "4️⃣ Bot ghi tự động vào Google Sheet ✅\n\n"
        "⏱️ *Tổng giờ* tính từ giờ Check In → Check Out thực tế\n"
        "📅 *Nghỉ*: ghi ngày nghỉ có lý do\n"
        "🔄 *Chấm Bù*: làm bù ngày nghỉ trước",
        parse_mode="Markdown")

# ── CONVERSATION ──────────────────────────────────────────────
async def chamcong_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📋 *Chọn loại chấm công:*",
        parse_mode="Markdown", reply_markup=kb_loai())
    return CHON_LOAI

async def chon_loai(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text == "❌ Huỷ":
        await update.message.reply_text("❌ Đã huỷ.", reply_markup=RKR)
        return ConversationHandler.END
    ctx.user_data["loai"] = text
    if "Nghỉ" in text and "Chấm Bù" not in text:
        await update.message.reply_text(
            "📝 *Chọn lý do nghỉ:*", parse_mode="Markdown", reply_markup=kb_nghi())
        return CHON_NGHI
    await update.message.reply_text(
        "🕐 *Chọn ca làm việc:*", parse_mode="Markdown", reply_markup=kb_ca())
    return CHON_CA

async def chon_ca(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ca   = update.message.text.strip()
    user = update.effective_user
    loai = ctx.user_data.get("loai", "")

    if ca == "❌ Huỷ":
        await update.message.reply_text("❌ Đã huỷ.", reply_markup=RKR)
        return ConversationHandler.END
    if ca not in [CA_NGAY, CA_DEM]:
        await update.message.reply_text("⚠️ Chọn ca hợp lệ.", reply_markup=kb_ca())
        return CHON_CA

    dt  = now_vn()
    gio = dt.strftime("%H:%M:%S")
    ngay = dt.strftime("%d/%m/%Y")
    thu  = thu_vn(dt)

    try:
        sheet = get_sheet()

        # ── CHECK IN ──
        if "Check In" in loai:
            idx, existing = tim_dong(sheet, user.id, ca)
            if existing and existing[6]:
                await update.message.reply_text(
                    f"⚠️ Bạn đã Check In *{ca}* hôm nay lúc *{existing[6]}*!",
                    parse_mode="Markdown", reply_markup=RKR)
                return ConversationHandler.END

            sheet.append_row([ngay, thu,
                               user.full_name or user.username or "Unknown",
                               str(user.id), ca, "Check In",
                               gio, "", "", ""])
            await update.message.reply_text(
                f"✅ *CHECK IN*\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"👤 {user.full_name}\n"
                f"🆔 `{user.id}`\n"
                f"📅 {thu}, {ngay}\n"
                f"🕐 Giờ vào: *{gio}*\n"
                f"🏷️ {ca}\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"📊 Đã ghi Google Sheet ✔️",
                parse_mode="Markdown", reply_markup=RKR)

        # ── CHECK OUT ──
        elif "Check Out" in loai:
            idx, existing = tim_dong(sheet, user.id, ca)
            if not existing:
                await update.message.reply_text(
                    f"⚠️ Chưa có Check In cho *{ca}* hôm nay!\nVui lòng Check In trước.",
                    parse_mode="Markdown", reply_markup=RKR)
                return ConversationHandler.END
            if existing[7]:
                await update.message.reply_text(
                    f"⚠️ Đã Check Out lúc *{existing[7]}* rồi!",
                    parse_mode="Markdown", reply_markup=RKR)
                return ConversationHandler.END

            tong = tinh_tong_gio(existing[6], gio)
            sheet.update_cell(idx, 8, gio)
            sheet.update_cell(idx, 9, tong)
            await update.message.reply_text(
                f"🔚 *CHECK OUT*\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"👤 {user.full_name}\n"
                f"🆔 `{user.id}`\n"
                f"📅 {thu}, {ngay}\n"
                f"🕐 Vào:  *{existing[6]}*\n"
                f"🕕 Ra:   *{gio}*\n"
                f"⏱️ Tổng: *{tong}*\n"
                f"🏷️ {ca}\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"📊 Đã cập nhật Google Sheet ✔️",
                parse_mode="Markdown", reply_markup=RKR)

        # ── CHẤM BÙ ──
        elif "Chấm Bù" in loai:
            sheet.append_row([ngay, thu,
                               user.full_name or user.username or "Unknown",
                               str(user.id), ca, "Chấm Bù",
                               gio, "", "", "Làm bù"])
            await update.message.reply_text(
                f"🔄 *CHẤM BÙ*\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"👤 {user.full_name}\n"
                f"🆔 `{user.id}`\n"
                f"📅 {thu}, {ngay}\n"
                f"🕐 Bắt đầu: *{gio}*\n"
                f"🏷️ {ca}\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"📊 Đã ghi Google Sheet ✔️",
                parse_mode="Markdown", reply_markup=RKR)

    except Exception as e:
        logger.error(e)
        await update.message.reply_text(
            f"❌ Lỗi kết nối Sheet!\n`{str(e)[:120]}`",
            parse_mode="Markdown", reply_markup=RKR)

    return ConversationHandler.END

async def chon_nghi(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ly_do = update.message.text.strip()
    user  = update.effective_user
    if ly_do == "❌ Huỷ":
        await update.message.reply_text("❌ Đã huỷ.", reply_markup=RKR)
        return ConversationHandler.END

    dt   = now_vn()
    ngay = dt.strftime("%d/%m/%Y")
    thu  = thu_vn(dt)
    gio  = dt.strftime("%H:%M:%S")
    ghi_chu = ly_do.replace("🤒 ","").replace("📋 ","").replace("🏖️ ","").replace("📝 ","")

    try:
        sheet = get_sheet()
        sheet.append_row([ngay, thu,
                          user.full_name or user.username or "Unknown",
                          str(user.id), "—", "Nghỉ",
                          gio, "", "", ghi_chu])
        await update.message.reply_text(
            f"📅 *ĐĂNG KÝ NGHỈ*\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"👤 {user.full_name}\n"
            f"🆔 `{user.id}`\n"
            f"📅 {thu}, {ngay}\n"
            f"📝 Lý do: *{ghi_chu}*\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📊 Đã ghi Google Sheet ✔️",
            parse_mode="Markdown", reply_markup=RKR)
    except Exception as e:
        logger.error(e)
        await update.message.reply_text(f"❌ Lỗi: `{str(e)[:120]}`",
                                        parse_mode="Markdown", reply_markup=RKR)
    return ConversationHandler.END

async def huy(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Đã huỷ.", reply_markup=RKR)
    return ConversationHandler.END

async def lichsu(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user    = update.effective_user
    hom_nay = now_vn().strftime("%d/%m/%Y")
    try:
        sheet = get_sheet()
        rows  = [r for r in sheet.get_all_values()[1:]
                 if len(r) >= 4 and r[0] == hom_nay and r[3] == str(user.id)]
        if not rows:
            await update.message.reply_text(
                f"📭 Chưa có dữ liệu hôm nay ({hom_nay}).", reply_markup=RKR)
            return
        msg = f"📊 *Lịch sử — {hom_nay}*\n━━━━━━━━━━━━━━━━━━\n"
        for r in rows:
            loai    = r[5] if len(r) > 5 else "—"
            ca      = r[4] if len(r) > 4 else "—"
            gio_in  = r[6] if len(r) > 6 else "—"
            gio_out = r[7] if len(r) > 7 else "Chưa out"
            tong    = r[8] if len(r) > 8 else "—"
            note    = r[9] if len(r) > 9 else ""
            msg += (f"\n🏷️ *{loai}* | {ca}\n"
                    f"   🕐 {gio_in}  →  🕕 {gio_out}\n"
                    f"   ⏱️ {tong}")
            if note:
                msg += f"\n   📝 {note}"
            msg += "\n"
        await update.message.reply_text(msg, parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ Lỗi: `{str(e)[:120]}`", parse_mode="Markdown")

# ── MAIN ──────────────────────────────────────────────────────
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    conv = ConversationHandler(
        entry_points=[CommandHandler("chamcong", chamcong_start)],
        states={
            CHON_LOAI: [MessageHandler(filters.TEXT & ~filters.COMMAND, chon_loai)],
            CHON_CA:   [MessageHandler(filters.TEXT & ~filters.COMMAND, chon_ca)],
            CHON_NGHI: [MessageHandler(filters.TEXT & ~filters.COMMAND, chon_nghi)],
        },
        fallbacks=[CommandHandler("huy", huy)],
    )
    app.add_handler(CommandHandler("start",  start))
    app.add_handler(CommandHandler("help",   help_cmd))
    app.add_handler(CommandHandler("lichsu", lichsu))
    app.add_handler(conv)
    logger.info("✅ Bot đang chạy...")
    app.run_polling()

if __name__ == "__main__":
    main()

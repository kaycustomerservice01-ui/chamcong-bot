import logging, os, json
import pytz
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ContextTypes, ConversationHandler
)
import gspread
from google.oauth2.service_account import Credentials

BOT_TOKEN = "8452164068:AAFKjS2lvZ_nBye1ERzIuDWyDqTrK8IQc9c"
SHEET_ID  = "1k7yS52nd0HQRWhVDVBm7Xxc9ckARgThy9XFoWznq3oI"
TIMEZONE  = "Asia/Ho_Chi_Minh"

CA_NGAY = "â˜€ï¸ Ca NgÃ y"
CA_DEM  = "ðŸŒ™ Ca ÄÃªm"

HEADERS = ["NgÃ y","Thá»©","TÃªn NhÃ¢n ViÃªn","Telegram ID","Ca LÃ m","Loáº¡i","Giá» Check In","Giá» Check Out","Tá»•ng Giá»","Ghi ChÃº"]
CHON_LOAI, CHON_CA, CHON_NGHI = range(3)

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
    return ReplyKeyboardMarkup([[KeyboardButton("âœ… Check In"),KeyboardButton("ðŸ”š Check Out")],[KeyboardButton("ðŸ“… Nghá»‰ HÃ´m Nay"),KeyboardButton("ðŸ”„ Cháº¥m BÃ¹")],[KeyboardButton("âŒ Huá»·")]],resize_keyboard=True,one_time_keyboard=True)

def kb_ca():
    return ReplyKeyboardMarkup([[KeyboardButton(CA_NGAY),KeyboardButton(CA_DEM)],[KeyboardButton("âŒ Huá»·")]],resize_keyboard=True,one_time_keyboard=True)

def kb_nghi():
    return ReplyKeyboardMarkup([[KeyboardButton("ðŸ¤’ Nghá»‰ Bá»‡nh"),KeyboardButton("ðŸ“‹ Nghá»‰ PhÃ©p")],[KeyboardButton("ðŸ–ï¸ Nghá»‰ Lá»…"),KeyboardButton("ðŸ“ Viá»‡c CÃ¡ NhÃ¢n")],[KeyboardButton("âŒ Huá»·")]],resize_keyboard=True,one_time_keyboard=True)

RKR = ReplyKeyboardRemove()

def now_vn():
    return datetime.now(pytz.timezone(TIMEZONE))

def thu_vn(dt):
    return ["Thá»© Hai","Thá»© Ba","Thá»© TÆ°","Thá»© NÄƒm","Thá»© SÃ¡u","Thá»© Báº£y","Chá»§ Nháº­t"][dt.weekday()]

async def start(update, ctx):
    u = update.effective_user
    await update.message.reply_text(f"ðŸ‘‹ Xin chÃ o *{u.full_name}*!\n\nðŸ¤– *Bot Cháº¥m CÃ´ng*\nâ”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”\nðŸ“Œ Lá»‡nh:\n  /chamcong â€” Cháº¥m cÃ´ng\n  /lichsu   â€” Lá»‹ch sá»­ hÃ´m nay\n  /help     â€” HÆ°á»›ng dáº«n\nâ”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”\nðŸ’¡ Nháº¥n /chamcong Ä‘á»ƒ báº¯t Ä‘áº§u!",parse_mode="Markdown")

async def help_cmd(update, ctx):
    await update.message.reply_text("ðŸ“– *HÆ¯á»šNG DáºªN*\nâ”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”\n1ï¸âƒ£ /chamcong\n2ï¸âƒ£ Chá»n: Check In / Check Out / Nghá»‰ / Cháº¥m BÃ¹\n3ï¸âƒ£ Chá»n ca: Ca NgÃ y hoáº·c Ca ÄÃªm\n4ï¸âƒ£ Bot ghi tá»± Ä‘á»™ng vÃ o Google Sheet âœ…",parse_mode="Markdown")

async def chamcong_start(update, ctx):
    await update.message.reply_text("ðŸ“‹ *Chá»n loáº¡i cháº¥m cÃ´ng:*",parse_mode="Markdown",reply_markup=kb_loai())
    return CHON_LOAI

async def chon_loai(update, ctx):
    text = update.message.text.strip()
    if text == "âŒ Huá»·":
        await update.message.reply_text("âŒ ÄÃ£ huá»·.",reply_markup=RKR)
        return ConversationHandler.END
    ctx.user_data["loai"] = text
    if "Nghá»‰" in text and "Cháº¥m BÃ¹" not in text:
        await update.message.reply_text("ðŸ“ *Chá»n lÃ½ do nghá»‰:*",parse_mode="Markdown",reply_markup=kb_nghi())
        return CHON_NGHI
    await update.message.reply_text("ðŸ• *Chá»n ca lÃ m viá»‡c:*",parse_mode="Markdown",reply_markup=kb_ca())
    return CHON_CA

async def chon_ca(update, ctx):
    ca   = update.message.text.strip()
    user = update.effective_user
    loai = ctx.user_data.get("loai","")
    if ca == "âŒ Huá»·":
        await update.message.reply_text("âŒ ÄÃ£ huá»·.",reply_markup=RKR)
        return ConversationHandler.END
    if ca not in [CA_NGAY, CA_DEM]:
        await update.message.reply_text("âš ï¸ Chá»n ca há»£p lá»‡.",reply_markup=kb_ca())
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
                await update.message.reply_text(f"âš ï¸ ÄÃ£ Check In *{ca}* lÃºc *{existing[6]}*!",parse_mode="Markdown",reply_markup=RKR)
                return ConversationHandler.END
            sheet.append_row([ngay,thu,user.full_name or user.username or "Unknown",str(user.id),ca,"Check In",gio,"","",""])
            await update.message.reply_text(f"âœ… *CHECK IN*\nâ”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”\nðŸ‘¤ {user.full_name}\nðŸ†” `{user.id}`\nðŸ“… {thu}, {ngay}\nðŸ• Giá» vÃ o: *{gio}*\nðŸ·ï¸ {ca}\nâ”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”\nðŸ“Š ÄÃ£ ghi Google Sheet âœ”ï¸",parse_mode="Markdown",reply_markup=RKR)
        elif "Check Out" in loai:
            idx, existing = tim_dong(sheet, user.id, ca)
            if not existing:
                await update.message.reply_text(f"âš ï¸ ChÆ°a cÃ³ Check In cho *{ca}* hÃ´m nay!",parse_mode="Markdown",reply_markup=RKR)
                return ConversationHandler.END
            if existing[7]:
                await update.message.reply_text(f"âš ï¸ ÄÃ£ Check Out lÃºc *{existing[7]}* rá»“i!",parse_mode="Markdown",reply_markup=RKR)
                return ConversationHandler.END
            tong = tinh_tong_gio(existing[6], gio)
            sheet.update_cell(idx, 8, gio)
            sheet.update_cell(idx, 9, tong)
            await update.message.reply_text(f"ðŸ”š *CHECK OUT*\nâ”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”\nðŸ‘¤ {user.full_name}\nðŸ†” `{user.id}`\nðŸ“… {thu}, {ngay}\nðŸ• VÃ o:  *{existing[6]}*\nðŸ•• Ra:   *{gio}*\nâ±ï¸ Tá»•ng: *{tong}*\nðŸ·ï¸ {ca}\nâ”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”\nðŸ“Š ÄÃ£ cáº­p nháº­t Google Sheet âœ”ï¸",parse_mode="Markdown",reply_markup=RKR)
        elif "Cháº¥m BÃ¹" in loai:
            sheet.append_row([ngay,thu,user.full_name or user.username or "Unknown",str(user.id),ca,"Cháº¥m BÃ¹",gio,"","","LÃ m bÃ¹"])
            await update.message.reply_text(f"ðŸ”„ *CHáº¤M BÃ™*\nâ”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”\nðŸ‘¤ {user.full_name}\nðŸ†” `{user.id}`\nðŸ“… {thu}, {ngay}\nðŸ• Báº¯t Ä‘áº§u: *{gio}*\nðŸ·ï¸ {ca}\nâ”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”\nðŸ“Š ÄÃ£ ghi Google Sheet âœ”ï¸",parse_mode="Markdown",reply_markup=RKR)
    except Exception as e:
        logger.error(e)
        await update.message.reply_text(f"âŒ Lá»—i káº¿t ná»‘i Sheet!\n`{str(e)[:120]}`",parse_mode="Markdown",reply_markup=RKR)
    return ConversationHandler.END

async def chon_nghi(update, ctx):
    ly_do = update.message.text.strip()
    user  = update.effective_user
    if ly_do == "âŒ Huá»·":
        await update.message.reply_text("âŒ ÄÃ£ huá»·.",reply_markup=RKR)
        return ConversationHandler.END
    dt   = now_vn()
    ngay = dt.strftime("%d/%m/%Y")
    thu  = thu_vn(dt)
    gio  = dt.strftime("%H:%M:%S")
    ghi_chu = ly_do.replace("ðŸ¤’ ","").replace("ðŸ“‹ ","").replace("ðŸ–ï¸ ","").replace("ðŸ“ ","")
    try:
        sheet = get_sheet()
        sheet.append_row([ngay,thu,user.full_name or user.username or "Unknown",str(user.id),"â€”","Nghá»‰",gio,"","",ghi_chu])
        await update.message.reply_text(f"ðŸ“… *ÄÄ‚NG KÃ NGHá»ˆ*\nâ”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”\nðŸ‘¤ {user.full_name}\nðŸ†” `{user.id}`\nðŸ“… {thu}, {ngay}\nðŸ“ LÃ½ do: *{ghi_chu}*\nâ”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”\nðŸ“Š ÄÃ£ ghi Google Sheet âœ”ï¸",parse_mode="Markdown",reply_markup=RKR)
    except Exception as e:
        logger.error(e)
        await update.message.reply_text(f"âŒ Lá»—i: `{str(e)[:120]}`",parse_mode="Markdown",reply_markup=RKR)
    return ConversationHandler.END

async def huy(update, ctx):
    await update.message.reply_text("âŒ ÄÃ£ huá»·.",reply_markup=RKR)
    return ConversationHandler.END

async def lichsu(update, ctx):
    user    = update.effective_user
    hom_nay = now_vn().strftime("%d/%m/%Y")
    try:
        sheet = get_sheet()
        rows  = [r for r in sheet.get_all_values()[1:] if len(r)>=4 and r[0]==hom_nay and r[3]==str(user.id)]
        if not rows:
            await update.message.reply_text(f"ðŸ“­ ChÆ°a cÃ³ dá»¯ liá»‡u hÃ´m nay ({hom_nay}).",reply_markup=RKR)
            return
        msg = f"ðŸ“Š *Lá»‹ch sá»­ â€” {hom_nay}*\nâ”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”\n"
        for r in rows:
            msg += f"\nðŸ·ï¸ *{r[5] if len(r)>5 else 'â€”'}* | {r[4] if len(r)>4 else 'â€”'}\n   ðŸ• {r[6] if len(r)>6 else 'â€”'}  â†’  ðŸ•• {r[7] if len(r)>7 else 'ChÆ°a out'}\n   â±ï¸ {r[8] if len(r)>8 else 'â€”'}\n"
            if len(r)>9 and r[9]: msg += f"   ðŸ“ {r[9]}\n"
        await update.message.reply_text(msg,parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"âŒ Lá»—i: `{str(e)[:120]}`",parse_mode="Markdown")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    conv = ConversationHandler(
        entry_points=[CommandHandler("chamcong", chamcong_start)],
        states={CHON_LOAI:[MessageHandler(filters.TEXT&~filters.COMMAND,chon_loai)],CHON_CA:[MessageHandler(filters.TEXT&~filters.COMMAND,chon_ca)],CHON_NGHI:[MessageHandler(filters.TEXT&~filters.COMMAND,chon_nghi)]},
        fallbacks=[CommandHandler("huy",huy)],
    )
    app.add_handler(CommandHandler("start",start))
    app.add_handler(CommandHandler("help",help_cmd))
    app.add_handler(CommandHandler("lichsu",lichsu))
    app.add_handler(conv)
    logger.info("âœ… Bot Ä‘ang cháº¡y...")
    app.run_polling()

if __name__ == "__main__":
    main()

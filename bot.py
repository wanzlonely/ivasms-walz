import os
import time
import threading
import logging
import telebot
import pycountry
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime

# Environment Variables
TELEGRAM_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

bot = telebot.TeleBot(TELEGRAM_TOKEN, threaded=False) if TELEGRAM_TOKEN else None
logger = logging.getLogger("TelegramBot")

last_sms_state = {}

# Mapping Service ke Singkatan Keren (Sesuai Gambar 1)
SERVICE_MAP = {
    "whatsapp": "WS",
    "telegram": "TG",
    "facebook": "FB", 
    "instagram": "IG",
    "tiktok": "TT",
    "google": "GO",
    "youtube": "YT",
    "netflix": "NF",
    "apple": "AP",
    "amazon": "AM",
    "shopee": "SP",
    "lazada": "LZ",
    "tokopedia": "TO",
    "gojek": "GJ",
    "grab": "GR",
    "uber": "UB",
    "discord": "DC",
    "twitter": "TW",
    "x": "TW",
    "line": "LN",
    "viber": "VB",
    "wechat": "WC",
    "imo": "IM",
    "kakaotalk": "KT"
}

def get_country_data(country_text):
    """
    Mengubah nama negara/range menjadi Bendera dan Kode ISO 2 huruf.
    Contoh: "Russian (+7)" -> ("🇷🇺", "RU", "Russian")
    """
    clean_name = country_text.split('(')[0].strip()
    
    # Manual Override untuk nama yang sering beda di panel SMS vs Library
    manual_data = {
        "Russian": ("🇷🇺", "RU"), "Russia": ("🇷🇺", "RU"),
        "USA": ("🇺🇸", "US"), "United States": ("🇺🇸", "US"), "America": ("🇺🇸", "US"),
        "UK": ("🇬🇧", "GB"), "United Kingdom": ("🇬🇧", "GB"), "England": ("🇬🇧", "GB"),
        "Vietnam": ("🇻🇳", "VN"), "Indonesia": ("🇮🇩", "ID"),
        "Malaysia": ("🇲🇾", "MY"), "Philippines": ("🇵🇭", "PH"),
        "Thailand": ("🇹🇭", "TH"), "Myanmar": ("🇲🇲", "MM"),
        "Cambodia": ("🇰🇭", "KH"), "Laos": ("🇱🇦", "LA"),
        "Timor Leste": ("🇹🇱", "TL"), "Brunei": ("🇧🇳", "BN"),
        "Singapore": ("🇸🇬", "SG"), "China": ("🇨🇳", "CN"),
        "Hong Kong": ("🇭🇰", "HK"), "Taiwan": ("🇹🇼", "TW"),
        "Japan": ("🇯🇵", "JP"), "Korea": ("🇰🇷", "KR"),
        "India": ("🇮🇳", "IN"), "Pakistan": ("🇵🇰", "PK"),
        "Bangladesh": ("🇧🇩", "BD"), "Nepal": ("🇳🇵", "NP"),
        "Sri Lanka": ("🇱🇰", "LK"), "Turkey": ("🇹🇷", "TR"),
        "Iran": ("🇮🇷", "IR"), "Iraq": ("🇮🇶", "IQ"),
        "Saudi Arabia": ("🇸🇦", "SA"), "UAE": ("🇦🇪", "AE"),
        "Egypt": ("🇪🇬", "EG"), "Morocco": ("🇲🇦", "MA"),
        "Algeria": ("🇩🇿", "DZ"), "Tunisia": ("🇹🇳", "TN"),
        "Nigeria": ("🇳🇬", "NG"), "Kenya": ("🇰🇪", "KE"),
        "South Africa": ("🇿🇦", "ZA"), "Brazil": ("🇧🇷", "BR"),
        "Argentina": ("🇦🇷", "AR"), "Colombia": ("🇨🇴", "CO"),
        "Mexico": ("🇲🇽", "MX"), "Canada": ("🇨🇦", "CA"),
        "Germany": ("🇩🇪", "DE"), "France": ("🇫🇷", "FR"),
        "Italy": ("🇮🇹", "IT"), "Spain": ("🇪🇸", "ES"),
        "Netherlands": ("🇳🇱", "NL"), "Belgium": ("🇧🇪", "BE"),
        "Portugal": ("🇵🇹", "PT"), "Poland": ("🇵🇱", "PL"),
        "Ukraine": ("🇺🇦", "UA"), "Sweden": ("🇸🇪", "SE")
    }

    if clean_name in manual_data:
        return manual_data[clean_name][0], manual_data[clean_name][1], clean_name
    
    # Auto detect semua negara lain di bumi menggunakan pycountry
    try:
        search = pycountry.countries.search_fuzzy(clean_name)
        if search:
            code = search[0].alpha_2
            flag = chr(127462 + ord(code[0]) - 65) + chr(127462 + ord(code[1]) - 65)
            return flag, code, clean_name
    except LookupError:
        pass

    return "🌍", "UN", clean_name # Default Unknown

def get_service_code(message_text):
    msg_lower = message_text.lower()
    for name, code in SERVICE_MAP.items():
        if name in msg_lower:
            return code
    return "Other"

def create_markup():
    markup = InlineKeyboardMarkup()
    # Tombol sesuai gambar screenshot
    btn1 = InlineKeyboardButton("‼️ Bot Pnl", url="https://t.me/") 
    btn2 = InlineKeyboardButton("♻️ All Support", url="https://t.me/")
    markup.row(btn1, btn2)
    return markup

def send_notification(country_range, phone_number, otp_message):
    try:
        flag, iso_code, country_name = get_country_data(country_range)
        service_code = get_service_code(otp_message)
        
        # Format sesuai Gambar 1: [Bendera] [ISO] • [Service] • [Negara] • [Nomor]
        header = f"<b>{flag} {iso_code} • {service_code} • {country_name} • <code>{phone_number}</code></b>"
        
        final_text = (
            f"{header}\n"
            f"└ <code>{otp_message}</code>"
        )

        bot.send_message(
            TELEGRAM_CHAT_ID,
            final_text,
            parse_mode="HTML",
            reply_markup=create_markup()
        )
        return True
    except Exception as e:
        logger.error(f"Telegram Send Error: {e}")
        return False

def monitor_loop(client):
    global last_sms_state
    logger.info("Bot Monitor Engine Started")
    
    while True:
        try:
            if not client.logged_in:
                client.login_with_cookies()
                time.sleep(5)
                continue

            today = datetime.now().strftime('%d/%m/%Y')
            result = client.check_otps(from_date=today)
            
            if not result or 'sms_details' not in result:
                time.sleep(10)
                continue

            current_details = result['sms_details']
            
            for item in current_details:
                range_name = item['country_number'] # ex: Russian (+7)
                try:
                    current_count = int(item['count'])
                except ValueError:
                    current_count = 0
                
                prev_count = last_sms_state.get(range_name, 0)
                
                # Jika ada pesan baru masuk
                if current_count > prev_count:
                    # Ambil list nomor dari range tersebut
                    numbers = client.get_sms_details(range_name, from_date=today)
                    if numbers:
                        # Ambil nomor paling atas (terbaru)
                        top_entry = numbers[0]
                        phone = top_entry['phone_number']
                        
                        # Ambil isi pesannya
                        msg = client.get_otp_message(phone, range_name, from_date=today)
                        
                        if msg:
                            send_notification(range_name, phone, msg)
                    
                    # Update state
                    last_sms_state[range_name] = current_count
            
            time.sleep(8) # Interval cek

        except Exception as e:
            logger.error(f"Monitor Loop Error: {e}")
            time.sleep(30)

@bot.message_handler(commands=['stats', 'start'])
def stats_handler(message):
    """Menampilkan statistik negara aktif (Mirip Gambar 4)"""
    if not last_sms_state:
        bot.reply_to(message, "⏳ Mengumpulkan data...")
        return

    sorted_stats = sorted(last_sms_state.items(), key=lambda x: x[1], reverse=True)
    text = "📊 <b>Live Country Statistics</b>\n\n"
    
    for range_name, count in sorted_stats[:25]: # Top 25 Negara
        flag, _, clean_name = get_country_data(range_name)
        text += f"{flag} <b>{clean_name}</b> : <code>{count}</code> SMS\n"
        
    bot.reply_to(message, text, parse_mode="HTML")

def start_bot(client_instance):
    # Thread untuk monitoring web
    t = threading.Thread(target=monitor_loop, args=(client_instance,))
    t.daemon = True
    t.start()
    
    # Thread untuk merespon chat telegram
    bot_thread = threading.Thread(target=bot.infinity_polling)
    bot_thread.daemon = True
    bot_thread.start()

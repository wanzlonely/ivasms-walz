import os
import time
import threading
import telebot
import pycountry
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime

TELEGRAM_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

bot = telebot.TeleBot(TELEGRAM_TOKEN, threaded=False) if TELEGRAM_TOKEN else None

live_sms_storage = {}

MANUAL_COUNTRY_MAP = {
    "Russian": "RU", "Russia": "RU", "USA": "US", "United States": "US",
    "UK": "GB", "United Kingdom": "GB", "England": "GB", "Vietnam": "VN",
    "Indonesia": "ID", "Malaysia": "MY", "Philippines": "PH", "Thailand": "TH",
    "Myanmar": "MM", "Cambodia": "KH", "Laos": "LA", "China": "CN",
    "India": "IN", "Pakistan": "PK", "Bangladesh": "BD", "Nepal": "NP",
    "Sri Lanka": "LK", "Turkey": "TR", "Iran": "IR", "Iraq": "IQ",
    "Saudi Arabia": "SA", "Yemen": "YE", "UAE": "AE", "Israel": "IL",
    "Egypt": "EG", "Morocco": "MA", "Algeria": "DZ", "Tunisia": "TN",
    "Libya": "LY", "Sudan": "SD", "Somalia": "SO", "Nigeria": "NG",
    "Kenya": "KE", "South Africa": "ZA", "Ghana": "GH", "Ethiopia": "ET",
    "Brazil": "BR", "Argentina": "AR", "Colombia": "CO", "Chile": "CL",
    "Peru": "PE", "Venezuela": "VE", "Mexico": "MX", "Canada": "CA",
    "Germany": "DE", "France": "FR", "Italy": "IT", "Spain": "ES",
    "Netherlands": "NL", "Belgium": "BE", "Portugal": "PT", "Poland": "PL",
    "Ukraine": "UA", "Romania": "RO", "Sweden": "SE", "Norway": "NO",
    "Finland": "FI", "Denmark": "DK", "Ireland": "IE", "Switzerland": "CH",
    "Austria": "AT", "Greece": "GR", "Czech": "CZ", "Hungary": "HU",
    "Australia": "AU", "New Zealand": "NZ", "Fiji": "FJ", "Papua New Guinea": "PG",
    "Ivory Coast": "CI", "Cote d'Ivoire": "CI"
}

def resolve_country_info(raw_name):
    clean_name = raw_name.split('(')[0].strip()
    code = MANUAL_COUNTRY_MAP.get(clean_name)
    
    if not code:
        try:
            matches = pycountry.countries.search_fuzzy(clean_name)
            if matches:
                code = matches[0].alpha_2
        except Exception:
            code = None

    if code:
        flag = chr(127462 + ord(code[0]) - 65) + chr(127462 + ord(code[1]) - 65)
        return flag, clean_name
    return "🌍", clean_name

def detect_service(text):
    if not text: return "Any"
    text = text.lower()
    services = {
        "whatsapp": "WhatsApp", "telegram": "Telegram", "facebook": "Facebook",
        "instagram": "Instagram", "tiktok": "TikTok", "google": "Google",
        "youtube": "YouTube", "netflix": "Netflix", "apple": "Apple",
        "amazon": "Amazon", "shopee": "Shopee", "gojek": "Gojek",
        "grab": "Grab", "uber": "Uber", "discord": "Discord",
        "twitter": "Twitter", "snapchat": "Snapchat", "linkedin": "LinkedIn",
        "imo": "Imo", "line": "Line", "viber": "Viber", "kakaotalk": "KakaoTalk",
        "wechat": "WeChat", "paypal": "PayPal", "wise": "Wise"
    }
    for k, v in services.items():
        if k in text:
            return v
    return "Others"

def generate_keyboard(data):
    markup = InlineKeyboardMarkup(row_width=1)
    
    markup.add(InlineKeyboardButton("🌍 Select your country:", callback_data="ignore"))
    
    if not data:
        markup.add(InlineKeyboardButton("⏳ Loading Data (Wait)...", callback_data="refresh"))
    else:
        sorted_items = sorted(data.items(), key=lambda x: x[1]['count'], reverse=True)
        
        for range_key, info in sorted_items[:20]:
            flag, name = resolve_country_info(range_key)
            service = info['service']
            count = info['count']
            
            try:
                prefix = range_key.split('(')[1].split(')')[0]
                display_prefix = f"({prefix})"
            except IndexError:
                display_prefix = ""
            
            btn_text = f"{flag} {name} {service} {display_prefix} - {count}"
            markup.add(InlineKeyboardButton(btn_text, callback_data=f"get_{name}"))

    markup.add(InlineKeyboardButton("🔄 Refresh List", callback_data="refresh"))
    return markup

def monitor_task(client):
    global live_sms_storage
    
    while True:
        try:
            if not client.logged_in:
                client.login_with_cookies()
                time.sleep(3)
                continue

            date_now = datetime.now().strftime('%d/%m/%Y')
            result = client.check_otps(from_date=date_now)
            
            if result and 'sms_details' in result:
                temp_storage = {}
                
                for item in result['sms_details']:
                    r_name = item['country_number']
                    try:
                        cnt = int(item['count'])
                    except:
                        cnt = 0
                    
                    svc = "Mixed"
                    
                    prev_data = live_sms_storage.get(r_name)
                    prev_cnt = prev_data['count'] if prev_data else 0
                    
                    if cnt > prev_cnt:
                        nums = client.get_sms_details(r_name, from_date=date_now)
                        if nums:
                            top_num = nums[0]['phone_number']
                            msg_body = client.get_otp_message(top_num, r_name, from_date=date_now)
                            if msg_body:
                                svc = detect_service(msg_body)
                                if TELEGRAM_CHAT_ID:
                                    flag, c_name = resolve_country_info(r_name)
                                    notif = (
                                        f"<b>{flag} {c_name} • {svc} • {top_num}</b>\n"
                                        f"└ <code>{msg_body}</code>"
                                    )
                                    try:
                                        bot.send_message(TELEGRAM_CHAT_ID, notif, parse_mode="HTML")
                                    except:
                                        pass
                    elif prev_data:
                        svc = prev_data['service']

                    temp_storage[r_name] = {'count': cnt, 'service': svc}
                
                live_sms_storage = temp_storage
            
            time.sleep(10)
        except Exception:
            time.sleep(20)

@bot.message_handler(commands=['start'])
def send_menu(message):
    caption = (
        "🕵️ <b>SPY X WALZ BOT</b> 🕵️\n\n"
        "🔔 <b>Egypt 🇪🇬 Price has increased Rt:0.11$</b> 💵\n🤑 🤑\n\n"
        "<b>All Country 📞 WS Sell BOT</b>\n"
        "✔️ <b>Instant SELL BOT</b> 🤖\n"
        "<u>https://t.me/wsotp200bot?start=u8166829424</u>\n"
        "💎 <b>Minimum Withdraw 1$</b> 🌑\n"
        "🔥 <b>Withdraw USDC 🌑 POL Address.</b> 🌐\n"
        "<b>Egypt 🇪🇬 Now Work Speed UP</b> 🚀"
    )
    
    bot.send_message(
        message.chat.id,
        caption,
        parse_mode="HTML",
        reply_markup=generate_keyboard(live_sms_storage),
        disable_web_page_preview=True
    )

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    if call.data == "refresh":
        bot.answer_callback_query(call.id, "Refreshing...")
        bot.edit_message_reply_markup(
            call.message.chat.id,
            call.message.message_id,
            reply_markup=generate_keyboard(live_sms_storage)
        )
    elif call.data == "ignore":
        bot.answer_callback_query(call.id)
    elif call.data.startswith("get_"):
        bot.answer_callback_query(call.id, "Monitoring...")

def start_bot(client):
    try:
        bot.delete_webhook()
        time.sleep(1)
    except:
        pass

    th = threading.Thread(target=monitor_task, args=(client,))
    th.daemon = True
    th.start()
    
    bt = threading.Thread(target=bot.infinity_polling, kwargs={'timeout': 10, 'long_polling_timeout': 5})
    bt.daemon = True
    bt.start()

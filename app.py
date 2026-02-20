from flask import Flask, jsonify
from datetime import datetime
import cloudscraper
import json
from bs4 import BeautifulSoup
import logging
import os
import gzip
import brotli
import bot as telegram_bot

logging.basicConfig(level=logging.ERROR)

class IVASSMSClient:
    def __init__(self):
        self.scraper = cloudscraper.create_scraper()
        self.base_url = "https://www.ivasms.com"
        self.logged_in = False
        self.csrf_token = None
        self.scraper.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive'
        })

    def decompress_response(self, response):
        try:
            encoding = response.headers.get('Content-Encoding', '').lower()
            if encoding == 'gzip': return gzip.decompress(response.content).decode('utf-8')
            if encoding == 'br': return brotli.decompress(response.content).decode('utf-8')
            return response.text
        except: return response.text

    def load_cookies(self):
        try:
            c_env = os.getenv("COOKIES_JSON")
            if c_env: return json.loads(c_env)
            if os.path.exists("cookies.json"):
                with open("cookies.json", 'r') as f: return json.load(f)
        except: pass
        return None

    def login_with_cookies(self):
        cookies = self.load_cookies()
        if not cookies: return False
        try:
            if isinstance(cookies, list):
                for c in cookies: self.scraper.cookies.set(c['name'], c['value'], domain="www.ivasms.com")
            else:
                for k, v in cookies.items(): self.scraper.cookies.set(k, v, domain="www.ivasms.com")
            
            resp = self.scraper.get(f"{self.base_url}/portal/sms/received")
            if resp.status_code == 200:
                soup = BeautifulSoup(self.decompress_response(resp), 'html.parser')
                token = soup.find('input', {'name': '_token'})
                if token:
                    self.csrf_token = token.get('value')
                    self.logged_in = True
                    return True
        except: pass
        return False

    def check_otps(self, from_date=""):
        if not self.logged_in or not self.csrf_token: return None
        try:
            data = {'from': from_date, 'to': '', '_token': self.csrf_token}
            headers = {'X-Requested-With': 'XMLHttpRequest', 'Origin': self.base_url, 'Referer': f"{self.base_url}/portal/sms/received"}
            resp = self.scraper.post(f"{self.base_url}/portal/sms/received/getsms", data=data, headers=headers)
            if resp.status_code == 200:
                soup = BeautifulSoup(self.decompress_response(resp), 'html.parser')
                details = []
                for item in soup.select("div.item"):
                    country = item.select_one(".col-sm-4").text.strip()
                    cnt = item.select_one(".col-3:nth-child(2) p").text.strip()
                    details.append({'country_number': country, 'count': cnt})
                return {'sms_details': details}
        except: pass
        return None

    def get_sms_details(self, rng, from_date=""):
        try:
            data = {'_token': self.csrf_token, 'start': from_date, 'end': '', 'range': rng}
            headers = {'X-Requested-With': 'XMLHttpRequest'}
            resp = self.scraper.post(f"{self.base_url}/portal/sms/received/getsms/number", data=data, headers=headers)
            if resp.status_code == 200:
                soup = BeautifulSoup(self.decompress_response(resp), 'html.parser')
                return [{'phone_number': i.select_one(".col-sm-4").text.strip()} for i in soup.select("div.card.card-body")]
        except: pass
        return []

    def get_otp_message(self, num, rng, from_date=""):
        try:
            data = {'_token': self.csrf_token, 'start': from_date, 'end': '', 'Number': num, 'Range': rng}
            headers = {'X-Requested-With': 'XMLHttpRequest'}
            resp = self.scraper.post(f"{self.base_url}/portal/sms/received/getsms/number/sms", data=data, headers=headers)
            if resp.status_code == 200:
                soup = BeautifulSoup(self.decompress_response(resp), 'html.parser')
                p = soup.select_one(".col-9.col-sm-6 p")
                return p.text.strip() if p else None
        except: pass
        return None

app = Flask(__name__)
client = IVASSMSClient()

@app.route('/')
def home():
    return jsonify({"status": "Spy X Walz Bot Running", "login": client.logged_in})

if __name__ == '__main__':
    with app.app_context():
        if client.login_with_cookies():
            telegram_bot.start_bot(client)
    
    port = int(os.environ.get("PORT", 8000))
    app.run(host='0.0.0.0', port=port)

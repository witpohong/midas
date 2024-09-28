import os
import re
import requests
import logging
import schedule
import time
from datetime import datetime
import pytz

logging.basicConfig(filename='app.log', level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')

TELEGRAM_TOKEN = 'xxxxxx'
CHAT_ID = 'xxxxx'  # 

tz = pytz.timezone('Asia/Jakarta')

def print_timestamp(message):
    timestamp = datetime.now(tz).strftime('%d/%m/%Y %H:%M:%S')
    print(f"[ {timestamp} WIB ] | {message}")

def calculate_total_balance(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        total_balance = 0
        total_accounts = 0

        for line in lines:
            line = line.strip()
            if line:
                account_match = re.search(r'Total Balance from (\d+) Account\(s\)', line)
                balance_match = re.search(r': (\d+)', line)

                if account_match and balance_match:
                    total_accounts += int(account_match.group(1))
                    total_balance += int(balance_match.group(1))

        formatted_balance = f"{total_balance:,}".replace(',', '.')

        message = f"==========Midas Info============\n[👤] Total Accounts  : {total_accounts} Account(s)\n[👑] Total Balance    : {formatted_balance} GM\n=============================="

        print_timestamp(message)

        send_message_to_telegram(message)

    except Exception as e:
        print_timestamp(f"Failed to read or process file: {str(e)}")
        logging.error(f"Error calculating total balance: {str(e)}")

def send_message_to_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        'chat_id': CHAT_ID,
        'text': message,
    }
    
    try:
        response = requests.post(url, json=payload)
        data = response.json()
        if data.get("ok"):
            print_timestamp('Message sent to Telegram successfully!')
        else:
            print_timestamp(f"Failed to send message to Telegram: {data.get('description')}")
    except Exception as e:
        print_timestamp(f"Error sending message to Telegram: {str(e)}")
        logging.error(f"Error sending message: {str(e)}")

def schedule_task():
    schedule.every().day.at("00:00").do(lambda: calculate_total_balance('totalmidas.txt'))
    schedule.every().day.at("06:00").do(lambda: calculate_total_balance('totalmidas.txt'))
    schedule.every().day.at("12:00").do(lambda: calculate_total_balance('totalmidas.txt'))
    schedule.every().day.at("18:00").do(lambda: calculate_total_balance('totalmidas.txt'))

    print_timestamp("Scheduler set up. Waiting for the scheduled times...")

    while True:
        schedule.run_pending()
        time.sleep(1)

def main():
    print_timestamp("Starting program with scheduler...")
    schedule_task()

if __name__ == "__main__":
    main()

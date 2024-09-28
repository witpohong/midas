import os, time, sys, re, json, cloudscraper, logging
from urllib.parse import unquote
from datetime import datetime
from pyfiglet import Figlet
from colorama import Fore, Style, init
from faker import Faker
import pytz

init(autoreset=True)

logging.basicConfig(filename='re.log', level=logging.ERROR, format='[%(asctime)s] - %(levelname)s - [%(message)s]')

# Setup timezone for Asia/Jakarta (UTC+7)
jakarta_tz = pytz.timezone('Asia/Jakarta')

def get_formatted_time():
    # Get the current time in UTC+7 (Jakarta timezone)
    jakarta_time = datetime.now(jakarta_tz)
    return jakarta_time.strftime("%Y-%m-%d %H:%M:%S")


class MidasBot:
    def __init__(self):
        self.faker = Faker()  # Initialize Faker instance
        self.tix = 0
        self.token_file = 'account_token.json'
        self.api_url_base = "https://api-tg-app.midas.app/api"
        self.header_base = {
            'User-Agent': self.faker.user_agent(),  # Generate random User-Agent
            'Accept': 'application/json, text/plain, */*',
            'Cache-Control': 'no-cache',
            'Content-Type': 'application/json',
            'Origin': 'https://prod-tg-app.midas.app',
            'Referer': 'https://prod-tg-app.midas.app/',
        }
        self.scraper = cloudscraper.create_scraper()
        self.proxies = []  # This will hold the proxies loaded from proxy.txt
        self.current_proxies = []  # This will hold the proxies for current quentod.txt
        self.proxy_for_current_account = None  # Proxy to be used for current account
        self.start_color = (0, 0, 255)
        self.end_color = (128, 0, 128)
        self.balance_file = 'totalmidas.txt'  # New: File to store total balance

    def banner(self):
        os.system("title MIDAS BOT" if os.name == "nt" else "clear")
        os.system("cls" if os.name == "nt" else "clear")
        custom_fig = Figlet(font='slant')
        self.print_gradient_text(custom_fig.renderText('WITPOHONG'), self.start_color, self.end_color)
        print('')

    def load_proxies(self):
        """Load proxies from proxy.txt and store them in self.proxies."""
        try:
            with open('proxy.txt', 'r') as f:
                self.proxies = f.read().splitlines()
            print(f"Loaded {len(self.proxies)} proxies from proxy.txt")
        except FileNotFoundError:
            print(Fore.RED + "proxy.txt not found." + Fore.RESET)

    def allocate_proxies_for_query_file(self, query_file_index):
        """Allocate proxies based on the query file index (1-based)."""
        start_index = (query_file_index - 1) * 10
        end_index = start_index + 10
        self.current_proxies = self.proxies[start_index:end_index]
        if not self.current_proxies:
            print(Fore.RED + "Error: Not enough proxies for this file." + Fore.RESET)
        else:
            print(f"Proxies for {query_file_index} allocated from line {start_index + 1} to {end_index}.")

    def get_proxy_for_account(self):
        """Assign a proxy for the current account and stick with it for all API requests."""
        if not self.current_proxies:
            return None
        self.proxy_for_current_account = self.current_proxies.pop(0)  # Take the first proxy
        self.current_proxies.append(self.proxy_for_current_account)  # Rotate it to the end
        return self.proxy_for_current_account

    def apply_proxy(self, proxy):
        """Apply proxy to the API requests using cloudscraper's proxy support."""
        if proxy:
            proxy_url = f"http://{proxy}"
            self.scraper.proxies.update({
                'http': proxy_url,
                'https': proxy_url
            })
            if not hasattr(self, 'proxy_ip_shown') or not self.proxy_ip_shown:
                self.get_proxy_ip()
                self.proxy_ip_shown = True  # Set flag to avoid showing again

    def get_proxy_ip(self):
        """Fetch the public IP address being used by the current proxy."""
        timestamp = Fore.MAGENTA + get_formatted_time() + Fore.RESET
        try:
            response = self.scraper.get("https://api.ipify.org?format=json")
            if response.status_code == 200:
                ip_info = response.json()
                print(f"[{timestamp}] - {Fore.CYAN}IP : {ip_info['ip']}{Fore.RESET}")
            else:
                print(Fore.RED + "Failed to retrieve IP from proxy." + Fore.RESET)
        except Exception as e:
            print(Fore.RED + f"Error retrieving proxy IP: {e}" + Fore.RESET)


    def load_query_ids_from_file(self, file_name):
        timestamp = Fore.MAGENTA + get_formatted_time() + Fore.RESET
        try:
            with open(file_name, 'r') as file:
                print(f"[{timestamp}] - Loaded query IDs from {Fore.GREEN}{file_name}{Fore.RESET}")
                return file.read().splitlines()
        except FileNotFoundError:
            print(f"[{timestamp}] - {Fore.RED}Error: File {Fore.RED}{file_name}{Fore.RESET} not found.")
            return []

    def save_token(self, username, token):
        timestamp = Fore.MAGENTA + get_formatted_time() + Fore.RESET
        try:
            data = {}
            if os.path.exists(self.token_file):
                with open(self.token_file, 'r') as f:
                    data = json.load(f)
            data[username] = token
            with open(self.token_file, 'w') as f:
                json.dump(data, f, indent=4)
            print(f"[{timestamp}] - Token saved for username: {Fore.GREEN}@{username}{Fore.RESET}")
        except Exception as e:
            print(f"[{timestamp}] - {Fore.RED}Error: Failed to save token for @{username}: {e}{Fore.RESET}")

    def load_token(self, username):
        timestamp = Fore.MAGENTA + get_formatted_time() + Fore.RESET
        try:
            if os.path.exists(self.token_file):
                with open(self.token_file, 'r') as f:
                    data = json.load(f)
                return data.get(username)
            return None
        except Exception as e:
            print(f"[{timestamp}] - {Fore.RED}Error: Failed to load token for @{username}: {e}{Fore.RESET}")
            return None

    def validate_token(self, token):
        headers = self.header_base.copy()
        headers['Authorization'] = f'Bearer {token}'
        url = f"{self.api_url_base}/referral/referred-users"
        timestamp = Fore.MAGENTA + get_formatted_time() + Fore.RESET
        self.apply_proxy(self.proxy_for_current_account)  # Apply assigned proxy to the scraper
        try:
            response = self.scraper.get(url, headers=headers)
            if response.status_code == 200:
                print(f"[{timestamp}] - {Fore.GREEN}Token validation successful{Fore.RESET}")
                return True
            else:
                logging.error(f"[validate_token] HTTP {response.status_code}")
                print(f"[{timestamp}] - {Fore.RED}Error: Token validation failed. HTTP {response.status_code}{Fore.RESET}")
                return False
        except Exception as e:
            logging.error(f"[validate_token] Error: {e}")
            print(f"[{timestamp}] - {Fore.RED}Error: Token validation failed due to {e}{Fore.RESET}")
            return False

    def get_token(self, query_id):
        """Modified to use proxy for each account."""
        headers = self.header_base.copy()
        url = f"{self.api_url_base}/auth/register"
        data = {"initData": query_id}
        self.apply_proxy(self.proxy_for_current_account)  # Apply assigned proxy to the scraper
        
        timestamp = Fore.MAGENTA + get_formatted_time() + Fore.RESET
        try:
            response = self.scraper.post(url, headers=headers, json=data)
            if response.status_code == 201:
                print(f"[{timestamp}] - {Fore.GREEN}Login successful{Fore.RESET}")
                return response.text
            else:
                logging.error(f"[get_token] HTTP {response.status_code}")
                print(f"[{timestamp}] - {Fore.RED}Error: Failed to get token. HTTP {response.status_code}{Fore.RESET}")
                return None
        except Exception as e:
            logging.error(f"[get_token] Error: {e}")
            print(f"[{timestamp}] - {Fore.RED}Error: Failed to get token due to {e}{Fore.RESET}")
            return None

    def update_balance_file(self, query_file, account_count, total_balance):
        try:
            # Read the existing content of the balance file
            if os.path.exists(self.balance_file):
                with open(self.balance_file, 'r') as f:
                    lines = f.readlines()
            else:
                lines = []

            # Check if the entry for this query file already exists
            query_file_pattern = f"on {query_file}:"
            updated = False

            for i, line in enumerate(lines):
                if query_file_pattern in line:
                    # Update the existing entry
                    lines[i] = f"[ Total Balance from {account_count} Account(s) on {query_file}: {total_balance} ]\n"
                    updated = True
                    break

            if not updated:
                # Add new entry if it doesn't exist
                lines.append(f"[ Total Balance from {account_count} Account(s) on {query_file}: {total_balance} ]\n")

            # Write back the updated content to the balance file
            with open(self.balance_file, 'w') as f:
                f.writelines(lines)

            print(f"Balance updated for {query_file}: {total_balance} GM")
        except Exception as e:
            print(f"Error updating balance file: {str(e)}")

    def process_accounts(self):
        query_ids = self.load_query_ids_from_file(self.query_file)
        timestamp = get_formatted_time()
        account_count = 0  # New: Track number of accounts processed
        self.total_balance = 0  # Reset total balance for this batch of accounts

        for query_id in query_ids:
            account_count += 1
            username = self.get_username(query_id)
            self.proxy_ip_shown = False  # Reset the flag for each account
            self.turudek(30)
            if username:
                self.get_proxy_for_account()  # Assign a proxy for the account
                token = self.load_token(username)
                if not token or not self.validate_token(token):
                    print(f"[{timestamp}] - Token for @{username} is expired or missing. Generating a new token...")
                    token = self.get_token(query_id)
                    if token:
                        self.save_token(username, token)
                if token:
                    self.perform_tasks(token)

        # New: Update balance file after processing all accounts
        self.update_balance_file(self.query_file, account_count, self.total_balance)

        print(f"[{timestamp}] - All accounts processed. Waiting for 1 hour...")
        self.turudek(1 * 60 * 60)

    def perform_tasks(self, token):
        self.check_in(token)
        self.get_user_info(token)
        self.play_game_if_needed(token)
        self.claim_tasks(token)
        self.check_referrals(token)
        print(f"{Fore.WHITE}-==========================================================-{Fore.RESET}")

    def get_username(self, query_id):
        timestamp = Fore.MAGENTA + get_formatted_time() + Fore.RESET
        try:
            found = re.search('user=([^&]*)', query_id).group(1)
            decoded_user_part = unquote(found)
            user_obj = json.loads(decoded_user_part)
            username = user_obj['username']
            print(f"[{timestamp}] - Username: {Fore.GREEN}@{username}{Fore.RESET}")
            return username
        except Exception as e:
            print(f"[{timestamp}] - {Fore.RED}Error: Failed to extract username: {e}{Fore.RESET}")
            return None

    def check_in(self, token):
        headers = self.header_base.copy()
        headers['Authorization'] = f'Bearer {token}'
        url = f"{self.api_url_base}/streak"
        timestamp = Fore.MAGENTA + get_formatted_time() + Fore.RESET
        self.apply_proxy(self.proxy_for_current_account)  # Apply assigned proxy to the scraper
        try:
            response = self.scraper.get(url, headers=headers)
            if response.status_code == 200:
                if response.json().get('claimable'):
                    self.scraper.post(url, headers=headers)
                    print(f"[{timestamp}] - {Fore.GREEN}Check-in successful{Fore.RESET}")
                else:
                    print(f"[{timestamp}] - {Fore.YELLOW}Already Check-In{Fore.RESET}")
            else:
                logging.error(f"[check_in] HTTP {response.status_code}")
                print(f"[{timestamp}] - {Fore.RED}Error: Check-in failed. HTTP {response.status_code}{Fore.RESET}")
        except Exception as e:
            logging.error(f"[check_in] Error: {e}")
            print(f"[{timestamp}] - {Fore.RED}Error: Check-in failed due to {e}{Fore.RESET}")


    def get_user_info(self, token):
        headers = self.header_base.copy()
        headers['Authorization'] = f'Bearer {token}'
        url = f"{self.api_url_base}/user"
        timestamp = Fore.MAGENTA + get_formatted_time() + Fore.RESET
        self.apply_proxy(self.proxy_for_current_account)  # Apply assigned proxy to the scraper
        try:
            response = self.scraper.get(url, headers=headers)
            if response.status_code == 200:
                user_info = response.json()
                self.tix = user_info.get('tickets', 0)
                balance = int(user_info.get('points', 0))  # New: Get balance from the user info
                self.total_balance += balance  # New: Add balance to the total balance
                print(f"[{timestamp}] - Balance : {Fore.GREEN}{balance}{Fore.RESET} GM")
                print(f"[{timestamp}] - Streak  : {Fore.GREEN}{user_info['streakDaysCount']}{Fore.RESET} Days")
                print(f"[{timestamp}] - Tickets : {Fore.GREEN}{self.tix}{Fore.RESET}")
            else:
                logging.error(f"[get_user_info] HTTP {response.status_code}")
                print(f"[{timestamp}] - {Fore.RED}Error: Failed to retrieve user info. HTTP {response.status_code}{Fore.RESET}")
        except Exception as e:
            logging.error(f"[get_user_info] Error: {e}")
            print(f"[{timestamp}] - {Fore.RED}Error: Failed to retrieve user info due to {e}{Fore.RESET}")


    def play_game_if_needed(self, token):
        headers = self.header_base.copy()
        headers['Authorization'] = f'Bearer {token}'
        url = f"{self.api_url_base}/game/play"
        timestamp = Fore.MAGENTA + get_formatted_time() + Fore.RESET
        
        # Log proxy used for playing the game
        self.apply_proxy(self.proxy_for_current_account)  # Apply assigned proxy to the scraper
        
        if self.tix > 0:
            print(f"[{timestamp}] - {Fore.GREEN}Playing games with {self.tix} tickets...{Fore.RESET}")
            for _ in range(self.tix):
                try:
                    response = self.scraper.post(url, headers=headers)
                    if response.status_code == 201:
                        reward = response.json().get('points', 0)
                        print(f"[{timestamp}] - Game played, reward: {Fore.GREEN}{reward} points{Fore.RESET}")
                    else:
                        logging.error(f"[play_game_if_needed] HTTP {response.status_code}")
                        print(f"[{timestamp}] - {Fore.RED}Error: Failed to play game. HTTP {response.status_code}{Fore.RESET}")
                    self.turudek(15)
                except Exception as e:
                    logging.error(f"[play_game_if_needed] Error: {e}")
                    print(f"[{timestamp}] - {Fore.RED}Error: Failed to play game due to {e}{Fore.RESET}")

    def claim_tasks(self, token):
        headers = self.header_base.copy()
        headers['Authorization'] = f'Bearer {token}'
        url = f"{self.api_url_base}/tasks/available"
        timestamp = Fore.MAGENTA + get_formatted_time() + Fore.RESET
        self.apply_proxy(self.proxy_for_current_account)  # Apply assigned proxy to the scraper
        try:
            response = self.scraper.get(url, headers=headers)
            if response.status_code == 200:
                tasks = response.json()
                for task in tasks:
                    task_id = task['id']
                    if task['state'] == 'CLAIMABLE':
                        print(f"[{timestamp}] - {Fore.GREEN}task : {task['name']}{Fore.RESET}")
                        claim_url = f"{self.api_url_base}/tasks/claim/{task_id}"
                        self.scraper.post(claim_url, headers=headers)
                        print(f"[{timestamp}] - Task {Fore.GREEN}'{task['name']}'{Fore.RESET} claimed with {Fore.GREEN}{task['points']} points{Fore.RESET}")
                    elif task['state'] == 'WAITING':
                        start_url = f"{self.api_url_base}/tasks/start/{task_id}"
                        self.scraper.post(start_url, headers=headers)
            else:
                logging.error(f"[claim_tasks] HTTP {response.status_code}")
                print(f"[{timestamp}] - {Fore.RED}Error: Failed to claim tasks. HTTP {response.status_code}{Fore.RESET}")
        except Exception as e:
            logging.error(f"[claim_tasks] Error: {e}")
            print(f"[{timestamp}] - {Fore.RED}Error: Failed to claim tasks due to {e}{Fore.RESET}")


    def check_referrals(self, token):
        headers = self.header_base.copy()
        headers['Authorization'] = f'Bearer {token}'
        status_url = f"{self.api_url_base}/referral/status"
        claim_url = f"{self.api_url_base}/referral/claim"
        timestamp = Fore.MAGENTA + get_formatted_time() + Fore.RESET
        self.apply_proxy(self.proxy_for_current_account)  # Apply assigned proxy to the scraper
        try:
            response = self.scraper.get(status_url, headers=headers)
            if response.status_code == 200:
                referral_info = response.json()
                if referral_info.get('canClaim') == True:
                    self.scraper.post(claim_url, headers=headers)
                    print(f"[{timestamp}] - {Fore.GREEN}Referral Rewards Claimed{Fore.RESET}")
                else:
                    print(f"[{timestamp}] - {Fore.RED}Can't Claim Referral  {Fore.RESET}")
            else:
                logging.error(f"[check_referrals] HTTP {response.status_code}")
                print(f"[{timestamp}] - {Fore.RED}Error: Failed to check referrals. HTTP {response.status_code}{Fore.RESET}")
        except Exception as e:
            logging.error(f"[check_referrals] Error: {e}")
            print(f"[{timestamp}] - {Fore.RED}Error: Failed to check referrals due to {e}{Fore.RESET}")

    def rgb_to_ansi(self, r, g, b):
        return f"\033[38;2;{r};{g};{b}m"

    def interpolate_color(self, start_color, end_color, factor: float):
        return (
            int(start_color[0] + (end_color[0] - start_color[0]) * factor),
            int(start_color[1] + (end_color[1] - start_color[1]) * factor),
            int(start_color[2] + (end_color[2] - start_color[2]) * factor),
        )

    def print_gradient_text(self, text, start_color, end_color):
        colored_text = ""
        for i, char in enumerate(text):
            factor = i / (len(text) - 1) if len(text) > 1 else 1
            r, g, b = self.interpolate_color(start_color, end_color, factor)
            colored_text += self.rgb_to_ansi(r, g, b) + char
        print(colored_text + "\033[0m")

    def turudek(self, total_seconds):
        bar_length = 25
        start_time = time.time()
        end_time = start_time + total_seconds
        while True:
            current_time = time.time()
            remaining_time = end_time - current_time
            if remaining_time <= 0:
                print(f"[{Fore.MAGENTA}{get_formatted_time()}{Fore.RESET}] - {Fore.GREEN}Time's up!, waiting..{Fore.RESET}", end='\r')
                break
            elapsed_time = total_seconds - remaining_time
            blocks_filled = int(bar_length * (elapsed_time / total_seconds))
            progress_bar = ""
            for i in range(blocks_filled):
                factor = i / (blocks_filled - 1) if blocks_filled > 1 else 1
                r, g, b = self.interpolate_color(self.start_color, self.end_color, factor)
                progress_bar += self.rgb_to_ansi(r, g, b) + "*"
            empty_space = "-" * (bar_length - blocks_filled)
            hours = int(remaining_time // 3600)
            minutes = int((remaining_time % 3600) // 60)
            seconds = int(remaining_time % 60)
            time_remaining = f"{hours:02}:{minutes:02}:{seconds:02}"
            print(f"[{Fore.MAGENTA}{Fore.YELLOW}WAIT TIME: {time_remaining}{Fore.RESET}] - [{progress_bar}{Fore.YELLOW}{empty_space}{Fore.RESET}]", end='\r')
            time.sleep(0.1)

    def display_query_choices(self):
        # Automatically find all files starting with "quentod" and ending with ".txt"
        files = [f for f in os.listdir() if f.startswith('quentod') and f.endswith('.txt')]
    
        # Sort files by the number in 'quentodX.txt'
        def extract_number(filename):
            match = re.search(r'quentod(\d+)', filename)
            return int(match.group(1)) if match else 0
    
        files = sorted(files, key=extract_number)  # Sort based on the number in filename
    
        if not files:
            print(Fore.RED + "No files found that match 'quentod*.txt'!" + Fore.RESET)
            return None
    
        # Title in Cyan
        print(Fore.CYAN + Style.BRIGHT + "===========LIST QUERY_ID=============\n" + Style.RESET_ALL)
        
        # Define a list of colors to alternate for each file (distinct for every file)
        colors = [Fore.GREEN, Fore.YELLOW, Fore.BLUE, Fore.MAGENTA, Fore.CYAN, Fore.RED, Fore.LIGHTGREEN_EX, Fore.LIGHTYELLOW_EX]
        
        # Displaying file options with distinct colors for each option
        for i, file_name in enumerate(files, 1):
            color = colors[i % len(colors)]  # Rotate between colors if there are more files than colors
            print(f"{color}[{i}] {file_name}")
        
        print(Style.RESET_ALL)  # Reset any color
        
        # User input section
        print(Fore.CYAN + Style.BRIGHT + "=====================================" + Style.RESET_ALL)
        choice = input(Fore.CYAN + "Pick your queries: " + Fore.RESET)
        
        try:
            choice_num = int(choice)
            if 1 <= choice_num <= len(files):
                selected_file = files[choice_num - 1]
                # Show processing message in Magenta
                print(Fore.MAGENTA + f"Processing query_id from {selected_file}..." + Fore.RESET)
                return selected_file
            else:
                # Error message in Red
                print(Fore.RED + "Invalid choice. Please select a valid number." + Fore.RESET)
                return None
        except ValueError:
            # Error message in Red
            print(Fore.RED + "Invalid input. Please enter a number." + Fore.RESET)
            return None

    def run(self):
        try:
            self.banner()
            self.load_proxies()  # Load proxies from proxy.txt
    
            while True:  # Menambahkan loop di sini agar terus berulang
                # Select query file and allocate corresponding proxies
                selected_file = self.display_query_choices()
                if selected_file and os.path.exists(selected_file):
                    query_file_index = int(selected_file.replace('quentod', '').replace('.txt', ''))
                    self.allocate_proxies_for_query_file(query_file_index)
                    self.query_file = selected_file
                    self.process_accounts()
                else:
                    print(f"File {selected_file} does not exist.")
                
                # Loop kembali setelah 1 jam
                print(f"Waiting for 1 hour before the next run...")
                self.turudek(1 * 60 * 60)  # 1 jam
    
        except KeyboardInterrupt:
            timestamp = Fore.MAGENTA + get_formatted_time() + Fore.RESET
            print(f"[{timestamp}] - {Fore.RED}Exiting MIDAS BOT...{Fore.RESET}")
            sys.exit()

if __name__ == "__main__":
    bot = MidasBot()
    bot.run()
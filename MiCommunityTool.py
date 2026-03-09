#!/usr/bin/python3

import os
import json
import time
import requests
import ntplib
from datetime import datetime, timedelta, timezone

# ==========================================
# INSTALL REQUIRED LIBRARIES
# ==========================================

def ensure_libs():
    import importlib
    for lib in ["requests", "ntplib"]:
        try:
            importlib.import_module(lib)
        except ModuleNotFoundError:
            os.system(f"pip install {lib}")

ensure_libs()

# ==========================================
# COLORS
# ==========================================

CYAN="\033[96m"
GREEN="\033[92m"
YELLOW="\033[93m"
RED="\033[91m"
WHITE="\033[97m"
BOLD="\033[1m"
RESET="\033[0m"

# ==========================================
# CONFIG
# ==========================================

versionCode="500418"
versionName="5.4.18"

User="XiaomiCommunity/5.4.18 (Linux; Android 14)"

api="https://api.vip.miui.com/mtop/planet/vip/member/"

U_apply=api+"apply/bl-auth"
U_info=api+"user/data"
U_state=api+"apply/bl-state"

# ==========================================
# LOAD ACCOUNT DATA
# ==========================================

def load_credentials():

    if os.path.exists("micdata.json"):

        try:
            with open("micdata.json") as f:
                data=json.load(f)

            return data["new_bbs_serviceToken"],data["deviceId"]

        except:
            pass

    print("\nEnter Xiaomi Community credentials\n")

    token=input("new_bbs_serviceToken: ").strip()
    device=input("deviceId: ").strip()

    return token,device

new_bbs_serviceToken,deviceId=load_credentials()

headers={
"User-Agent":User,
"Content-Type":"application/json",
"Cookie":f"new_bbs_serviceToken={new_bbs_serviceToken};versionCode={versionCode};versionName={versionName};deviceId={deviceId};"
}

# ==========================================
# UI HEADER
# ==========================================

print(f"""
{CYAN}{BOLD}
╔══════════════════════════════════════════╗
║ Xiaomi Community Unlock Permission Tool  ║
╚══════════════════════════════════════════╝
{RESET}
""")

# ==========================================
# ACCOUNT INFO
# ==========================================

def account_info():

    try:

        res=requests.get(U_info,headers=headers).json()

        if "data" not in res:
            exit(f"{RED}Invalid token or deviceId{RESET}")

        info=res["data"]

        level=info["level_info"]["level"]
        title=info["level_info"]["level_title"]
        current=info["level_info"]["current_value"]
        maxv=info["level_info"]["max_value"]

        next_points=maxv-current

        print(f"""
{CYAN}{BOLD}ACCOUNT INFO{RESET}

Days in Community : {info['registered_day']}
Level             : LV{level} {title}
Points            : {current}
Points to Next LV : {next_points}
""")

    except Exception as e:

        exit(f"{RED}Account info error: {e}{RESET}")

# ==========================================
# STATE CHECK
# ==========================================

def state_request():

    print(f"{GREEN}Checking account state...{RESET}")

    try:

        state=requests.get(U_state,headers=headers).json()["data"]

        is_pass=state.get("is_pass")
        button=state.get("button_state")
        deadline=state.get("deadline_format","")

        if is_pass==1:
            exit(f"{GREEN}Bootloader already unlocked until {deadline}{RESET}")

        if button==1:
            print(f"{YELLOW}Account eligible for unlock{RESET}")

        elif button==2:
            exit(f"{RED}Account error. Retry after {deadline}{RESET}")

        elif button==3:
            exit(f"{RED}Account must be older than 30 days{RESET}")

    except Exception as e:

        exit(f"{RED}State error: {e}{RESET}")

# ==========================================
# APPLY REQUEST
# ==========================================

def apply_request():

    print(f"\n{WHITE}[APPLY REQUEST]{RESET}")

    try:

        r=requests.post(U_apply,data=json.dumps({"is_retry":True}),headers=headers)

        print("Server time:",r.headers.get("Date"))

        data=r.json()

        if data.get("code")!=0:
            exit(data)

        result=data["data"]["apply_result"]
        deadline=data["data"].get("deadline_format","")

        if result==1:

            print(f"{GREEN}Application successful{RESET}")
            state_request()

        elif result==3:

            print(f"{YELLOW}Daily quota reached. Retry tomorrow {deadline}{RESET}")
            return 1

        elif result==4:

            exit(f"{RED}Account error. Try after {deadline}{RESET}")

    except Exception as e:

        exit(f"{RED}Apply error: {e}{RESET}")

# ==========================================
# TIME FUNCTIONS
# ==========================================

def ntp_time():

    client=ntplib.NTPClient()

    servers=["pool.ntp.org","time.google.com","time.windows.com"]

    for s in servers:

        try:
            r=client.request(s,version=3)
            return datetime.fromtimestamp(r.tx_time,timezone.utc)
        except:
            pass

    return datetime.now(timezone.utc)

def beijing_time():

    return ntp_time().astimezone(timezone(timedelta(hours=8)))

# ==========================================
# LATENCY TEST
# ==========================================

def measure_latency():

    samples=[]

    for _ in range(5):

        try:

            start=time.perf_counter()

            requests.post(U_apply,headers=headers,data="{}",timeout=2)

            samples.append((time.perf_counter()-start)*1000)

        except:
            pass

    if len(samples)<3:
        return 200

    samples.sort()

    trim=int(len(samples)*0.2)

    samples=samples[trim:-trim] if trim else samples

    return sum(samples)/len(samples)*1.3

# ==========================================
# SCHEDULER
# ==========================================

def scheduler():

    tz=timezone(timedelta(hours=8))

    while True:

        now=beijing_time()

        target=now.replace(hour=23,minute=57,second=0,microsecond=0)

        if now>=target:
            target+=timedelta(days=1)

        print(f"\nNext run at: {target}")

        while datetime.now(tz)<target:

            remaining=(target-datetime.now(tz)).total_seconds()

            if remaining>60:
                print(f"Waiting {int(remaining//60)} minutes...",end="\r")

            time.sleep(30)

        latency=measure_latency()

        execute_time=target+timedelta(minutes=3)-timedelta(milliseconds=latency)

        print(f"\nExecution time: {execute_time}")

        while datetime.now(tz)<execute_time:
            time.sleep(0.5)

        result=apply_request()

        if result==1:
            return 1

# ==========================================

account_info()
state_request()

while True:

    r=scheduler()

    if r!=1:
        break

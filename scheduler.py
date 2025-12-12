import time
import datetime as dt
import pytz
import subprocess

IST = pytz.timezone("Asia/Kolkata")

def log(msg):
    print("[SCHEDULER]", msg, flush=True)
#a
while True:
    now = dt.datetime.now(IST)
    #target = now.replace(hour=9, minute=25, second=0, microsecond=0)
    target = now

    if now > target:
        # If time already passed today, schedule for tomorrow
        target = target + dt.timedelta(days=1)

    wait_seconds = (target - now).total_seconds()
    log(f"Sleeping for {wait_seconds/60:.1f} minutes until next algo start at 9:25...")

    time.sleep(wait_seconds)

    log("Starting NIFTY Safe Option Demo Algo...")
    subprocess.run(["python", "angel_nifty_safe_algo_demo"])

    log("Algo run finished. Will schedule next day.")









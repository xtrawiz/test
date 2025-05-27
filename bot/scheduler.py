import os
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from datetime import datetime, timedelta

# Assuming web.models and scanner_utils are accessible
try:
    from web.models import Filter as DBFilter, User as DBUser
    from bot.scanner_utils import run_single_filter 
    from web.database import SessionLocal, engine as db_engine # For job store and session
except ImportError:
    import sys
    sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
    from web.models import Filter as DBFilter, User as DBUser
    from bot.scanner_utils import run_single_filter
    from web.database import SessionLocal, engine as db_engine


# APScheduler Configuration
DATABASE_URL = os.getenv("DB_CONNECTION_STRING_SCHEDULER", os.getenv("DB_CONNECTION_STRING"))

jobstores = {
    'default': SQLAlchemyJobStore(url=DATABASE_URL, engine=db_engine)
}
# executors = { # Not strictly necessary for default AsyncIO, but good practice
# 'default': {'type': 'threadpool', 'max_workers': 10},
# 'processpool': ProcessPoolExecutor(max_workers=3)
# }
job_defaults = {
    'coalesce': True, # Run only once if multiple triggers are missed
    'max_instances': 3 # Max 3 instances of the same job concurrently
}

# Initialize scheduler
scheduler = AsyncIOScheduler(jobstores=jobstores, job_defaults=job_defaults, timezone="UTC")


def get_cron_trigger_from_timeframe(timeframe: str) -> CronTrigger:
    """
    Converts a timeframe string (e.g., '1m', '5m', '15m', '1h', '4h', '1d') to APScheduler CronTrigger.
    More granular control can be added here.
    """
    value = int(timeframe[:-1])
    unit = timeframe[-1].lower()

    if unit == 'm': # minute
        if value < 1 or value > 59 : raise ValueError("دقیقه باید بین 1 تا 59 باشد")
        return CronTrigger(minute=f"*/{value}")
    elif unit == 'h': # hour
        if value < 1 or value > 23 : raise ValueError("ساعت باید بین 1 تا 23 باشد")
        return CronTrigger(hour=f"*/{value}", minute='1') # Run at minute 1 of the hour
    elif unit == 'd': # day
        if value < 1 or value > 30 : raise ValueError("روز باید بین 1 تا 30 باشد") # Approx
        return CronTrigger(day=f"*/{value}", hour='0', minute='5') # Run at 00:05 UTC
    else:
        raise ValueError(f"تایم فریم نامعتبر: {timeframe}. از m, h, d استفاده کنید.")

async def schedule_filter_job(filter_obj: DBFilter, bot_client_ref):
    """
    Schedules a filter job to run periodically.
    bot_client_ref is a reference to the initialized Pyrogram Client for sending messages.
    """
    if not scheduler.running:
        print("هشدار: زمان‌بند در حال اجرا نیست. کارها زمان‌بندی نخواهند شد.")
        # return # Or start it: scheduler.start() - but usually started once in main.py

    job_id = f"filter_{filter_obj.id}"
    
    # Check if job already exists
    if scheduler.get_job(job_id):
        print(f"جاب با شناسه {job_id} از قبل وجود دارد. ابتدا حذف و دوباره اضافه می‌شود.")
        remove_filter_job(filter_obj.id) # Remove existing to update trigger/params

    try:
        trigger = get_cron_trigger_from_timeframe(filter_obj.timeframe)
        
        # Create a new DB session for the job execution
        # This is important as the job runs in a different context/thread
        def job_function_wrapper():
            db_session = SessionLocal()
            try:
                # Note: run_single_filter is async, but APScheduler by default runs sync functions in threadpool
                # For full async, ensure the executor supports it or wrap appropriately.
                # For now, we assume run_single_filter can be called this way,
                # and its internal async calls are handled by ccxt.async_support.
                # A better approach for fully async jobs might involve asyncio.run_coroutine_threadsafe
                # or ensuring the scheduler's event loop is the same as Pyrogram's.
                # However, for simplicity, we'll proceed, as APScheduler's AsyncIOScheduler
                # should handle this reasonably well by running the sync wrapper in its event loop.
                
                # We need to run the async function run_single_filter
                # APScheduler with AsyncIOScheduler can directly schedule coroutines.
                # So, the wrapper might not be needed if we pass the coroutine directly.
                # Let's try scheduling the coroutine.
                pass # Placeholder, actual scheduling below

            finally:
                db_session.close()

        # Schedule the async function directly
        scheduler.add_job(
            run_single_filter,
            trigger=trigger,
            args=[SessionLocal(), filter_obj, bot_client_ref, None], # Pass a new session, filter, bot_client, no override_id
            id=job_id,
            name=f"Scan: {filter_obj.name}",
            replace_existing=True, # Replace if job with same ID exists
            misfire_grace_time=60*5 # 5 minutes grace time for misfires
        )
        print(f"اسکنر '{filter_obj.name}' (ID: {job_id}) برای اجرای دوره‌ای با تایم‌فریم {filter_obj.timeframe} زمان‌بندی شد.")
        print(f"جاب بعدی در: {scheduler.get_job(job_id).next_run_time}")

    except ValueError as e:
        print(f"خطا در زمان‌بندی اسکنر {filter_obj.name}: {e}")
    except Exception as e:
        print(f"خطای ناشناخته در زمان‌بندی اسکنر {filter_obj.name}: {e}")


def remove_filter_job(filter_id: int):
    """Removes a filter job from the scheduler."""
    job_id = f"filter_{filter_id}"
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)
        print(f"جاب اسکنر با شناسه {job_id} از زمان‌بند حذف شد.")
    else:
        print(f"جاب اسکنر با شناسه {job_id} در زمان‌بند یافت نشد.")

async def load_active_filters_on_startup(bot_client_ref):
    """
    Loads all active filters from the database and schedules them on bot startup.
    bot_client_ref is passed to schedule_filter_job.
    """
    db = SessionLocal()
    try:
        active_filters = db.query(DBFilter).filter(DBFilter.active == True).all()
        print(f"درحال بارگذاری و زمان‌بندی {len(active_filters)} اسکنر فعال...")
        for filter_obj in active_filters:
            await schedule_filter_job(filter_obj, bot_client_ref)
    except Exception as e:
        print(f"خطا در بارگذاری اسکنرهای فعال هنگام شروع: {e}")
    finally:
        db.close()

def start_scheduler():
    if not scheduler.running:
        scheduler.start()
        print("زمان‌بند APScheduler شروع به کار کرد.")
    else:
        print("زمان‌بند APScheduler از قبل در حال اجرا است.")

def shutdown_scheduler():
    if scheduler.running:
        scheduler.shutdown()
        print("زمان‌بند APScheduler متوقف شد.")

# Example usage (for testing, can be removed or put under if __name__ == "__main__":)
# async def main_test_scheduler():
#     # This needs a running event loop and a dummy bot client
#     class DummyBotClient:
#         async def send_message(self, chat_id, text):
#             print(f"DummyBot: Sending to {chat_id}: {text}")

#     dummy_bot = DummyBotClient()
    
#     # Create a dummy filter in DB for testing
#     db = SessionLocal()
#     test_user = db.query(DBUser).first()
#     if not test_user: print("Create a user first"); return
    
#     dummy_filter = DBFilter(user_id=test_user.id, name="Test Schedule Filter", params={}, timeframe="1m", active=True)
#     db.add(dummy_filter)
#     db.commit()
#     db.refresh(dummy_filter)

#     start_scheduler()
#     await schedule_filter_job(dummy_filter, dummy_bot)
    
#     # Keep it running for a bit
#     await asyncio.sleep(120) # Run for 2 minutes
    
#     remove_filter_job(dummy_filter.id)
#     shutdown_scheduler()
#     db.delete(dummy_filter); db.commit()
#     db.close()

# if __name__ == "__main__":
# import asyncio
# asyncio.run(main_test_scheduler())

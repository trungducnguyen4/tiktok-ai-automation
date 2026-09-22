import time
import datetime
from apscheduler.schedulers.background import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
import config
from pipeline import execute_daily_pipeline

def scheduled_job():
    print(f"\n[ALARM] Đã đến 12:00 trưa! Kích hoạt quy trình tự động hóa...")
    execute_daily_pipeline(headless=True)

def start_scheduler():
    scheduler = BlockingScheduler()

    # Thiết lập chạy vào 12:00:00 mỗi ngày
    trigger = CronTrigger(hour=config.SCHEDULE_HOUR, minute=config.SCHEDULE_MINUTE)
    scheduler.add_job(
        scheduled_job,
        trigger=trigger,
        id="daily_video_workflow",
        name="Daily NotebookLM to TikTok Video Generation",
        replace_existing=True
    )

    print("=" * 65)
    print("DỊCH VỤ LẬP LỊCH TỰ ĐỘNG HÓA VIDEO 12:00 TRƯA ĐÃ KHỞI ĐỘNG")
    print(f"Thời gian kích hoạt hàng ngày: {config.SCHEDULE_HOUR:02d}:{config.SCHEDULE_MINUTE:02d}:00")
    print("Dịch vụ đang chạy ngầm và chờ đến giờ hẹn...")
    print("=" * 65)

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        print("\nĐã dừng dịch vụ lập lịch.")

if __name__ == "__main__":
    start_scheduler()

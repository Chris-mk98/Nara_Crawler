import json
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from database import get_config_by_user, create_job_history, update_job_history
from email_service import send_excel_email
from crawler_service import run_crawler

logger = logging.getLogger(__name__)

OUTPUTS_DIR = str(Path(__file__).parent / "outputs")

scheduler = BackgroundScheduler(timezone="Asia/Seoul")


def run_user_job(user_id: int, history_id: int):
    """크롤러 실행 → 이메일 발송 → 이력 업데이트."""
    logger.info(f"작업 시작 (user={user_id}, history={history_id})")

    try:
        config = get_config_by_user(user_id)
        if not config:
            update_job_history(history_id, "failed", error_message="설정을 찾을 수 없습니다")
            return

        keywords = json.loads(config["keywords"])
        if not keywords:
            update_job_history(history_id, "failed", error_message="키워드가 없습니다")
            return

        if config["date_range_type"] == "relative":
            to_date = datetime.now().strftime("%Y%m%d")
            from_date = (datetime.now() - timedelta(days=int(config["relative_days"]))).strftime("%Y%m%d")
        else:
            from_date = config.get("custom_start_date") or (
                datetime.now() - timedelta(days=7)).strftime("%Y%m%d")
            to_date = config.get("custom_end_date") or datetime.now().strftime("%Y%m%d")

        job_output_dir = os.path.join(OUTPUTS_DIR, f"job_{history_id}")
        excel_path, row_count = run_crawler(keywords, from_date, to_date, job_output_dir)

        if excel_path is None:
            update_job_history(
                history_id, "failed",
                error_message="크롤링 실패 또는 검색 결과 없음",
                from_date=from_date, to_date=to_date,
                keywords_json=json.dumps(keywords, ensure_ascii=False)
            )
            return

        recipient = config.get("recipient_email")
        email_error = None
        if recipient:
            sent = send_excel_email(recipient, excel_path, from_date, to_date, keywords, row_count)
            if not sent:
                email_error = "이메일 발송 실패 (파일은 웹에서 다운로드 가능)"

        update_job_history(
            history_id, "success",
            excel_filename=excel_path,
            row_count=row_count,
            error_message=email_error,
            from_date=from_date,
            to_date=to_date,
            keywords_json=json.dumps(keywords, ensure_ascii=False)
        )
        logger.info(f"작업 완료 (user={user_id}, rows={row_count})")

    except Exception as e:
        logger.exception(f"작업 오류 (user={user_id})")
        update_job_history(history_id, "failed", error_message=str(e))


def _scheduled_job(user_id: int, config_id: int):
    """스케줄러에서 호출되는 래퍼 — 이력 생성 후 run_user_job 호출."""
    history = create_job_history(user_id, config_id)
    run_user_job(user_id, history["id"])


def schedule_user_job(user_id: int, config: dict):
    """사용자의 스케줄 작업을 등록(또는 교체)한다."""
    job_id = f"user_{user_id}"

    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)

    schedule_type = config.get("schedule_type", "disabled")
    if schedule_type == "disabled":
        return

    hour = int(config.get("schedule_hour", 9))
    minute = int(config.get("schedule_minute", 0))
    config_id = config["id"]

    if schedule_type == "daily":
        trigger = CronTrigger(hour=hour, minute=minute, timezone="Asia/Seoul")
    elif schedule_type == "weekly":
        dow = config.get("schedule_day_of_week", 0)
        trigger = CronTrigger(day_of_week=dow, hour=hour, minute=minute, timezone="Asia/Seoul")
    else:
        return

    scheduler.add_job(
        _scheduled_job,
        trigger=trigger,
        id=job_id,
        replace_existing=True,
        args=[user_id, config_id],
    )
    logger.info(f"스케줄 등록 (user={user_id}, type={schedule_type}, {hour:02d}:{minute:02d})")


def remove_user_job(user_id: int):
    """사용자의 스케줄 작업을 제거한다."""
    job_id = f"user_{user_id}"
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)
        logger.info(f"스케줄 제거 (user={user_id})")

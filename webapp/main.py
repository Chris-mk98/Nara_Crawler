import os
import sys
import json
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.templating import Jinja2Templates
import hmac
import hashlib
import base64
from pydantic import BaseModel
from starlette.requests import Request

# 환경변수 로드
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

# webapp 모듈 경로 추가
sys.path.insert(0, str(Path(__file__).parent))

import bcrypt

from database import (
    create_job_history, create_user, get_all_active_configs,
    get_config_by_user, get_job_history, get_user_by_email, init_db, save_config,
)
from scheduler_service import (
    remove_user_job, run_user_job, schedule_user_job, scheduler,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

SECRET_KEY = os.getenv("SECRET_KEY", "change-this-secret-key-in-production-min-32-chars!!")
TOKEN_EXPIRE_DAYS = 7


# ── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    scheduler.start()
    logger.info("스케줄러 시작")

    for config in get_all_active_configs():
        try:
            schedule_user_job(config["user_id"], config)
            logger.info(f"스케줄 복원 (user={config['user_id']})")
        except Exception as e:
            logger.error(f"스케줄 복원 실패: {e}")

    yield

    scheduler.shutdown(wait=False)
    logger.info("스케줄러 종료")


app = FastAPI(title="나라장터 자동 수집 서비스", lifespan=lifespan)

templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))
security = HTTPBearer(auto_error=False)


# ── Auth helpers ──────────────────────────────────────────────────────────────

def create_token(user_id: int, email: str) -> str:
    """HMAC-SHA256 서명 기반 간단한 토큰 생성."""
    exp = int((datetime.utcnow() + timedelta(days=TOKEN_EXPIRE_DAYS)).timestamp())
    payload = base64.urlsafe_b64encode(
        json.dumps({"sub": user_id, "email": email, "exp": exp}).encode()
    ).decode()
    sig = hmac.new(SECRET_KEY.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}.{sig}"


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not credentials:
        raise HTTPException(status_code=401, detail="인증이 필요합니다")
    try:
        raw = credentials.credentials
        payload_b64, sig = raw.rsplit(".", 1)
        expected = hmac.new(SECRET_KEY.encode(), payload_b64.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected):
            raise ValueError("서명 불일치")
        data = json.loads(base64.urlsafe_b64decode(payload_b64 + "=="))
        if data["exp"] < int(datetime.utcnow().timestamp()):
            raise ValueError("토큰 만료")
        return {"id": int(data["sub"]), "email": data["email"]}
    except Exception:
        raise HTTPException(status_code=401, detail="유효하지 않은 토큰입니다")


# ── Pydantic schemas ──────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class ConfigRequest(BaseModel):
    recipient_email: Optional[str] = None
    keywords: list[str] = []
    date_range_type: str = "relative"
    relative_days: int = 7
    custom_start_date: Optional[str] = None
    custom_end_date: Optional[str] = None
    schedule_type: str = "disabled"
    schedule_hour: int = 9
    schedule_minute: int = 0
    schedule_day_of_week: Optional[int] = None
    is_active: bool = False


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/api/auth/register")
async def register(req: RegisterRequest):
    if get_user_by_email(req.email):
        raise HTTPException(status_code=400, detail="이미 가입된 이메일입니다")
    if len(req.password) < 6:
        raise HTTPException(status_code=400, detail="비밀번호는 6자 이상이어야 합니다")

    hashed = bcrypt.hashpw(req.password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    user = create_user(req.email, hashed)
    return {"token": create_token(user["id"], user["email"]), "email": user["email"]}


@app.post("/api/auth/login")
async def login(req: LoginRequest):
    user = get_user_by_email(req.email)
    if not user or not bcrypt.checkpw(req.password.encode("utf-8"), user["password_hash"].encode("utf-8")):
        raise HTTPException(status_code=401, detail="이메일 또는 비밀번호가 올바르지 않습니다")

    return {"token": create_token(user["id"], user["email"]), "email": user["email"]}


@app.get("/api/config")
async def get_config(user=Depends(get_current_user)):
    config = get_config_by_user(user["id"])
    if not config:
        return {}
    config["keywords"] = json.loads(config["keywords"])
    return config


@app.put("/api/config")
async def update_config(req: ConfigRequest, user=Depends(get_current_user)):
    recipient = req.recipient_email or user["email"]
    config = save_config(
        user_id=user["id"],
        recipient_email=recipient,
        keywords=req.keywords,
        date_range_type=req.date_range_type,
        relative_days=req.relative_days,
        custom_start_date=req.custom_start_date,
        custom_end_date=req.custom_end_date,
        schedule_type=req.schedule_type,
        schedule_hour=req.schedule_hour,
        schedule_minute=req.schedule_minute,
        schedule_day_of_week=req.schedule_day_of_week,
        is_active=req.is_active,
    )

    if req.is_active and req.schedule_type != "disabled" and req.keywords:
        schedule_user_job(user["id"], config)
    else:
        remove_user_job(user["id"])

    config["keywords"] = json.loads(config["keywords"])
    return config


@app.post("/api/jobs/run")
async def run_job_now(background_tasks: BackgroundTasks, user=Depends(get_current_user)):
    config = get_config_by_user(user["id"])
    if not config:
        raise HTTPException(status_code=400, detail="먼저 설정을 저장해주세요")
    if not json.loads(config["keywords"]):
        raise HTTPException(status_code=400, detail="키워드를 하나 이상 입력해주세요")

    history = create_job_history(user["id"], config["id"])
    background_tasks.add_task(run_user_job, user["id"], history["id"])
    return {"message": "작업을 시작했습니다", "job_id": history["id"]}


@app.get("/api/jobs/history")
async def job_history(user=Depends(get_current_user)):
    return get_job_history(user["id"])


@app.get("/api/jobs/{job_id}/download")
async def download_result(job_id: int, user=Depends(get_current_user)):
    rows = get_job_history(user["id"], job_id=job_id)
    if not rows:
        raise HTTPException(status_code=404, detail="작업 이력을 찾을 수 없습니다")

    job = rows[0]
    excel_path = job.get("excel_filename")
    if not excel_path or not os.path.exists(excel_path):
        raise HTTPException(status_code=404, detail="파일이 존재하지 않습니다")

    return FileResponse(
        excel_path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=os.path.basename(excel_path),
    )

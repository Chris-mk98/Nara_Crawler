import os
import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
from pathlib import Path
from urllib.parse import quote

logger = logging.getLogger(__name__)

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")


def send_excel_email(to_email: str, excel_path: str, from_date: str, to_date: str,
                     keywords: list, row_count: int) -> bool:
    """이메일에 엑셀 파일을 첨부해 발송. 성공 시 True 반환."""
    if not SMTP_USER or not SMTP_PASSWORD:
        logger.error("SMTP 설정 누락. .env 파일의 SMTP_USER/SMTP_PASSWORD를 확인하세요.")
        return False

    try:
        msg = MIMEMultipart()
        msg["From"] = SMTP_USER
        msg["To"] = to_email
        msg["Subject"] = f"[나라장터] 입찰공고 수집 결과 ({from_date}~{to_date})"

        keywords_str = ", ".join(keywords)
        body = (
            f"안녕하세요!\n\n"
            f"나라장터 입찰공고 자동 수집 결과를 첨부합니다.\n\n"
            f"■ 검색 기간  : {from_date} ~ {to_date}\n"
            f"■ 검색 키워드: {keywords_str}\n"
            f"■ 총 공고 건수: {row_count}건\n\n"
            f"첨부 파일을 열어 상세 내용을 확인해 주세요.\n\n"
            f"감사합니다.\n나라장터 자동 수집 서비스"
        )
        msg.attach(MIMEText(body, "plain", "utf-8"))

        filename = Path(excel_path).name
        with open(excel_path, "rb") as f:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(f.read())

        encoders.encode_base64(part)
        encoded_name = quote(filename, safe="")
        part.add_header(
            "Content-Disposition",
            f"attachment; filename*=UTF-8''{encoded_name}"
        )
        msg.attach(part)

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_USER, [to_email], msg.as_bytes())

        logger.info(f"이메일 발송 완료 → {to_email}")
        return True

    except Exception as e:
        logger.error(f"이메일 발송 실패: {e}")
        return False

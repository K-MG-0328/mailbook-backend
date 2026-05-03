import logging
import os
from logging.handlers import TimedRotatingFileHandler

LOG_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "logs")
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s — %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# 표준 LogRecord 속성 — `extra=` 로 주입된 필드만 골라내기 위한 제외 목록.
_STANDARD_LOGRECORD_ATTRS = frozenset(
    {
        "name",
        "msg",
        "args",
        "levelname",
        "levelno",
        "pathname",
        "filename",
        "module",
        "exc_info",
        "exc_text",
        "stack_info",
        "lineno",
        "funcName",
        "created",
        "msecs",
        "relativeCreated",
        "thread",
        "threadName",
        "processName",
        "process",
        "message",
        "asctime",
        "taskName",
    }
)


class ExtraFieldsFormatter(logging.Formatter):
    """`extra=` 로 주입된 필드를 메시지 뒤에 `key=value` 로 붙이는 Formatter."""

    def format(self, record: logging.LogRecord) -> str:
        base = super().format(record)
        extras = {
            k: v
            for k, v in record.__dict__.items()
            if k not in _STANDARD_LOGRECORD_ATTRS and not k.startswith("_")
        }
        if not extras:
            return base
        suffix = " ".join(f"{k}={v!r}" for k, v in extras.items())
        return f"{base} | {suffix}"


def setup_logging(level: int | str = logging.INFO) -> None:
    """Console + 일일 로테이션 파일 핸들러로 root logger 구성. 다회 호출 안전."""
    root_logger = logging.getLogger()
    if root_logger.handlers:
        return

    # 문자열("DEBUG") / 정수(logging.DEBUG) 모두 허용. 알 수 없는 문자열은 INFO로 폴백.
    if isinstance(level, str):
        resolved_level = logging.getLevelNamesMapping().get(level.upper(), logging.INFO)
    else:
        resolved_level = level

    os.makedirs(LOG_DIR, exist_ok=True)

    formatter = ExtraFieldsFormatter(fmt=LOG_FORMAT, datefmt=LOG_DATE_FORMAT)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(resolved_level)
    console_handler.setFormatter(formatter)

    file_handler = TimedRotatingFileHandler(
        filename=os.path.join(LOG_DIR, "app.log"),
        when="midnight",
        interval=1,
        backupCount=30,
        encoding="utf-8",
    )
    file_handler.setLevel(resolved_level)
    file_handler.setFormatter(formatter)
    file_handler.suffix = "%Y%m%d"
    file_handler.namer = lambda name: os.path.join(
        os.path.dirname(name),
        os.path.basename(name).replace("app.log.", "") + "-app.log",
    )

    root_logger.setLevel(resolved_level)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    # httpx의 INFO 로그는 query string 포함 URL을 그대로 출력해 API 키가 노출될 수 있다.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

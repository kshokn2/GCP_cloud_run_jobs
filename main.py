
import os
import sys
import traceback
from datetime import datetime
from pathlib import Path

from google.cloud import logging # secretmanager, storage 등 추가..
from google.api_core import exceptions
from google.api_core.retry import Retry

from common import gcp_utils # 구현 필요..

# logging 설정
task_name = "my_logging_task_name"
log_name = "my_task"
fail_log_name = "task_failed"

logging_client = logging.Client()
logger = logging_client.logger(log_name)
fail_logger = logging_client.logger(fail_log_name)

# 전파 받아야 하는 파라미터 가져오기
MY_ENV_VARIABLE = os.getenv("MY_ENV", "value")

PROJECT_ID = "my-project"
project_num = gcp_utils.get_project_num(PROJECT_ID)

# secret manager로 필요한 파라미터 가져오기
MY_SECRET_1 = gcp_utils.access_secret_version(project_num, "secret이름", "latest")

my_log_structure = {
    "log_field_1": "text",
    "log_field_2": MY_ENV_VARIABLE,
    "log_field_3": MY_SECRET_1,
    "status": "success",
}

# retry 정책
_RETRIABLE_TYPES = {
    exceptions.TooManyRequests,
    exceptions.InternalServerError,
    exceptions.BadGateway,
    exceptions.ServiceUnavailable,
}

def is_retryable(exc):
    return isinstance(exc, tuple(_RETRIABLE_TYPES))

retry_policy = Retry(predicate=is_retryable)

# 커스텀 retry 에러 정의
class RetryableError(Exception):
    # 외부 서비스/네트워크 등 재시도 가능한 에러
    pass

class DownloadAllFailedError(Exception):
    # 외부 서비스/네트워크 등 재시도 불가능한 에러
    pass


def main():
    try:
        """
        Run Job의 main 함수 구현..

        ex.
        with bucket.blob(my_blob_name).open("rb", retry=retry_policy) as f:
            df = pd.read_csv(f, index_col=None)
        """

    except tuple(_RETRIABLE_TYPES) as e:
        my_log_structure["status"] = "failed"
        msg = f"기능1에서 에러({str(e)}) 발생"
        raise RetryableError(msg)

    except Exception as e:
        my_log_structure["status"] = "failed"
        msg = f"기능1에서 에러({str(e)}) 발생"
        print(msg)
        raise


if __name__ == "__main__":
    try:
        logger.log_text(f"[Task #{task_name}] start. (Attempt #{TASK_ATTEMPT})", severity="INFO")
        main()
        logger.log_text(f"[Task #{task_name}] finished.", severity="INFO")
        sys.exit(0)

    except RetryableError as re:
        logger.log_text(f"[Task #{task_name}] failed. Attempt #{TASK_ATTEMPT}, err: RetryableError, {str(re)}", severity="ERROR")
        sys.exit(2)

    except DownloadAllFailedError as re:
        logger.log_text(f"[Task #{task_name}] failed. Attempt #{TASK_ATTEMPT}, err: DownloadAllFailedError, {str(re)}", severity="ERROR")
        sys.exit(2)

    except Exception as err:
        logger.log_text(traceback.format_exc(), severity="ERROR")
        logger.log_text(f"[Task #{task_name}] failed. Attempt #{TASK_ATTEMPT}, err: {str(err)}", severity="ERROR")
        sys.exit(1)

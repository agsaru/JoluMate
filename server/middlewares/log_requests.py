from fastapi import Request
import time
from logs.logging_config import logger
async def log_requests(request:Request,call_next):
    start_time=time.time()
    response=await call_next(request)
    process_time=time.time()-start_time
    logger.info(
       f"{request.method} {request.url.path} "
       f"Status={response.status_code} "
       f"Time={process_time:.3f}s"
    )
    return response
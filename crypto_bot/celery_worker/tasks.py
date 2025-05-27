import logging
from celery import shared_task
import time

logger = logging.getLogger(__name__)

@shared_task(name="sample_task")
def sample_task(x: int, y: int) -> int:
    logger.info(f"Executing sample_task with arguments: {x}, {y}")
    time.sleep(5) # Simulate some work
    result = x + y
    logger.info(f"Sample task result: {result}")
    return result

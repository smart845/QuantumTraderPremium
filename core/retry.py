
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

def network_retry():
    return retry(
        reraise=True,
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=0.5, min=1, max=30),
    )

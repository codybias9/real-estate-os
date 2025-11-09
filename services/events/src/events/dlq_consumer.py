"""
DLQ-Aware Event Consumer
Implements exponential backoff and nack behavior for poison messages
"""

import asyncio
import json
from typing import Callable, Optional, Dict, Any
from datetime import datetime
import aio_pika
import structlog

logger = structlog.get_logger()


# ============================================================
# Error Classification
# ============================================================

class TransientError(Exception):
    """
    Transient error that should be retried with backoff
    Examples: network errors, temporary database unavailability, rate limits
    """
    pass


class NonTransientError(Exception):
    """
    Non-transient error that should send message to DLQ
    Examples: invalid message format, business logic errors, invalid data
    """
    pass


# ============================================================
# Health Governor (Exponential Backoff)
# ============================================================

class HealthGovernor:
    """
    Implements exponential backoff for retry logic
    Prevents thundering herd and respects rate limits
    """

    def __init__(
        self,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        backoff_factor: float = 2.0,
        max_attempts: int = 5,
    ):
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor
        self.max_attempts = max_attempts

    def calculate_delay(self, attempt: int) -> float:
        """
        Calculate exponential backoff delay

        Args:
            attempt: Attempt number (0-indexed)

        Returns:
            Delay in seconds
        """
        delay = self.initial_delay * (self.backoff_factor ** attempt)
        return min(delay, self.max_delay)

    async def retry_with_backoff(
        self,
        func: Callable,
        *args,
        **kwargs,
    ) -> Any:
        """
        Execute function with exponential backoff retry

        Args:
            func: Async function to execute
            *args, **kwargs: Arguments to pass to func

        Returns:
            Result from func

        Raises:
            TransientError: If all retry attempts exhausted
        """
        for attempt in range(self.max_attempts):
            try:
                result = await func(*args, **kwargs)
                return result

            except TransientError as e:
                if attempt == self.max_attempts - 1:
                    # Final attempt failed
                    logger.error(
                        "health_governor.retry.exhausted",
                        attempt=attempt + 1,
                        max_attempts=self.max_attempts,
                        error=str(e),
                    )
                    raise

                # Calculate backoff delay
                delay = self.calculate_delay(attempt)

                logger.warning(
                    "health_governor.retry.backoff",
                    attempt=attempt + 1,
                    max_attempts=self.max_attempts,
                    delay=delay,
                    error=str(e),
                )

                # Wait before retry
                await asyncio.sleep(delay)

            except NonTransientError:
                # Don't retry non-transient errors
                raise


# ============================================================
# DLQ-Aware Consumer
# ============================================================

class DLQConsumer:
    """
    Event consumer with DLQ support
    - Handles transient errors with exponential backoff
    - Routes non-transient errors to DLQ
    - Preserves idempotency
    """

    def __init__(
        self,
        rabbitmq_url: str,
        subject: str,
        handler: Callable,
        prefetch_count: int = 10,
    ):
        self.rabbitmq_url = rabbitmq_url
        self.subject = subject
        self.handler = handler
        self.prefetch_count = prefetch_count

        self.connection = None
        self.channel = None
        self.queue = None
        self.health_governor = HealthGovernor()

    async def connect(self):
        """Establish connection to RabbitMQ"""
        self.connection = await aio_pika.connect_robust(self.rabbitmq_url)
        self.channel = await self.connection.channel()
        await self.channel.set_qos(prefetch_count=self.prefetch_count)

        # Declare queue (should already exist from DLQ setup)
        self.queue = await self.channel.declare_queue(
            f"q.{self.subject}",
            durable=True,
        )

        logger.info(
            "dlq_consumer.connect.success",
            subject=self.subject,
            queue=self.queue.name,
        )

    async def close(self):
        """Close connection"""
        if self.connection:
            await self.connection.close()
            logger.info("dlq_consumer.close.success", subject=self.subject)

    async def start_consuming(self):
        """
        Start consuming messages with DLQ support
        """
        logger.info("dlq_consumer.start", subject=self.subject)

        async with self.queue.iterator() as queue_iter:
            async for message in queue_iter:
                await self._process_message(message)

    async def _process_message(self, message: aio_pika.IncomingMessage):
        """
        Process a single message with error handling

        Args:
            message: Incoming RabbitMQ message
        """
        start_time = datetime.utcnow()

        try:
            # Parse message
            event = json.loads(message.body.decode())

            # Extract metadata
            delivery_count = self._get_delivery_count(message)

            logger.info(
                "dlq_consumer.message.received",
                subject=self.subject,
                event_id=event.get("event_id"),
                delivery_count=delivery_count,
            )

            # Check if message has been retried too many times
            if delivery_count > 5:
                logger.error(
                    "dlq_consumer.message.max_retries",
                    subject=self.subject,
                    event_id=event.get("event_id"),
                    delivery_count=delivery_count,
                )
                # Nack without requeue (send to DLQ)
                await message.nack(requeue=False)
                return

            # Wrap handler to classify errors
            async def wrapped_handler():
                try:
                    await self.handler(event)
                except Exception as e:
                    # Classify error
                    if self._is_transient_error(e):
                        raise TransientError(str(e)) from e
                    else:
                        raise NonTransientError(str(e)) from e

            # Execute with retry logic
            await self.health_governor.retry_with_backoff(wrapped_handler)

            # Acknowledge successful processing
            await message.ack()

            elapsed = (datetime.utcnow() - start_time).total_seconds()
            logger.info(
                "dlq_consumer.message.success",
                subject=self.subject,
                event_id=event.get("event_id"),
                duration=elapsed,
            )

        except TransientError as e:
            # Transient error after retries exhausted
            # Nack with requeue for exponential backoff
            logger.error(
                "dlq_consumer.message.transient_failure",
                subject=self.subject,
                error=str(e),
            )
            await message.nack(requeue=True)

        except NonTransientError as e:
            # Non-transient error
            # Nack without requeue (send to DLQ)
            logger.error(
                "dlq_consumer.message.non_transient_failure",
                subject=self.subject,
                error=str(e),
            )
            await message.nack(requeue=False)

        except Exception as e:
            # Unknown error - treat as non-transient to avoid infinite loops
            logger.error(
                "dlq_consumer.message.unknown_failure",
                subject=self.subject,
                error=str(e),
            )
            await message.nack(requeue=False)

    def _get_delivery_count(self, message: aio_pika.IncomingMessage) -> int:
        """
        Extract delivery count from message headers

        Args:
            message: RabbitMQ message

        Returns:
            Delivery count (0 if first delivery)
        """
        if message.headers and "x-delivery-count" in message.headers:
            return message.headers["x-delivery-count"]
        return 0

    def _is_transient_error(self, error: Exception) -> bool:
        """
        Classify error as transient or non-transient

        Args:
            error: Exception to classify

        Returns:
            True if transient, False if non-transient
        """
        # Transient error patterns
        transient_patterns = [
            "ConnectionError",
            "TimeoutError",
            "DatabaseUnavailable",
            "RateLimitExceeded",
            "ServiceUnavailable",
            "TemporaryFailure",
        ]

        error_name = type(error).__name__
        error_message = str(error)

        for pattern in transient_patterns:
            if pattern in error_name or pattern in error_message:
                return True

        # Non-transient error patterns
        non_transient_patterns = [
            "ValidationError",
            "JSONDecodeError",
            "KeyError",
            "ValueError",
            "TypeError",
            "InvalidInput",
            "BusinessRuleViolation",
        ]

        for pattern in non_transient_patterns:
            if pattern in error_name or pattern in error_message:
                return False

        # Default to non-transient to avoid infinite loops
        return False


# ============================================================
# Example Handler
# ============================================================

async def example_handler(event: Dict[str, Any]):
    """
    Example event handler that demonstrates error handling

    Args:
        event: Event payload
    """
    event_type = event.get("type")

    # Simulate transient error
    if event.get("simulate_transient_error"):
        raise TransientError("Database connection temporarily unavailable")

    # Simulate non-transient error
    if event.get("simulate_non_transient_error"):
        raise NonTransientError("Invalid event format: missing required field")

    # Normal processing
    logger.info("handler.process", event_type=event_type)


# ============================================================
# Main
# ============================================================

async def main():
    """Example usage"""
    consumer = DLQConsumer(
        rabbitmq_url="amqp://guest:guest@localhost:5672/",
        subject="property.created",
        handler=example_handler,
    )

    try:
        await consumer.connect()
        await consumer.start_consuming()
    finally:
        await consumer.close()


if __name__ == "__main__":
    asyncio.run(main())

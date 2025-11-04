"""
RabbitMQ Dead Letter Queue (DLQ) Configuration
Sets up DLQ policies for all consumer queues with replay capability
"""

import asyncio
from typing import Dict, List
import aio_pika
import structlog

logger = structlog.get_logger()


# ============================================================
# DLQ Configuration
# ============================================================

# All subjects that need DLQ support
SUBJECTS = [
    "property.created",
    "property.updated",
    "property.scored",
    "memo.requested",
    "memo.generated",
    "outreach.scheduled",
    "outreach.sent",
    "outreach.delivered",
    "outreach.bounced",
    "timeline.updated",
]

# DLQ Policy Configuration
DLQ_POLICY = {
    "x-dead-letter-exchange": "dlx",  # Dead letter exchange
    "x-message-ttl": 86400000,        # 24 hours in ms (messages expire after 1 day)
    "x-max-length": 10000,            # Max queue size (prevent unbounded growth)
    "x-overflow": "reject-publish",   # Reject new messages when queue is full
}

# DLQ Retention Configuration
DLQ_RETENTION_DAYS = 7  # Keep DLQ messages for 7 days


class DLQConfigurator:
    """
    Configure RabbitMQ DLQ infrastructure
    - Create dead letter exchange (DLX)
    - Create DLQ queues for each subject
    - Apply DLQ policies to consumer queues
    """

    def __init__(self, rabbitmq_url: str):
        self.rabbitmq_url = rabbitmq_url
        self.connection = None
        self.channel = None

    async def connect(self):
        """Establish connection to RabbitMQ"""
        self.connection = await aio_pika.connect_robust(self.rabbitmq_url)
        self.channel = await self.connection.channel()
        logger.info("dlq.connect.success")

    async def close(self):
        """Close connection"""
        if self.connection:
            await self.connection.close()
            logger.info("dlq.close.success")

    async def setup_dlq_infrastructure(self):
        """
        Set up complete DLQ infrastructure:
        1. Create dead letter exchange (DLX)
        2. Create DLQ queues for each subject
        3. Bind DLQ queues to DLX
        4. Apply DLQ policies to consumer queues
        """
        logger.info("dlq.setup.start")

        # Step 1: Declare dead letter exchange
        dlx = await self.channel.declare_exchange(
            "dlx",
            aio_pika.ExchangeType.TOPIC,
            durable=True,
        )
        logger.info("dlq.dlx.created")

        # Step 2: Create DLQ queue for each subject
        for subject in SUBJECTS:
            dlq_queue_name = f"dlq.{subject}"

            # Declare DLQ queue with retention policy
            dlq_queue = await self.channel.declare_queue(
                dlq_queue_name,
                durable=True,
                arguments={
                    "x-message-ttl": DLQ_RETENTION_DAYS * 86400000,  # Retention in ms
                    "x-max-length": 50000,  # DLQ can hold more messages
                },
            )

            # Bind DLQ queue to DLX
            await dlq_queue.bind(dlx, routing_key=dlq_queue_name)

            logger.info("dlq.queue.created", subject=subject, queue=dlq_queue_name)

        # Step 3: Apply DLQ policies to consumer queues
        for subject in SUBJECTS:
            consumer_queue_name = f"q.{subject}"

            # Declare consumer queue with DLQ policy
            await self.channel.declare_queue(
                consumer_queue_name,
                durable=True,
                arguments={
                    **DLQ_POLICY,
                    "x-dead-letter-routing-key": f"dlq.{subject}",
                },
            )

            logger.info(
                "dlq.policy.applied",
                subject=subject,
                queue=consumer_queue_name,
            )

        logger.info("dlq.setup.complete", subjects=len(SUBJECTS))

    async def get_dlq_depth(self, subject: str) -> Dict[str, int]:
        """
        Get DLQ depth (message count) for a subject

        Args:
            subject: Event subject (e.g., "property.created")

        Returns:
            Dict with message count and consumer count
        """
        dlq_queue_name = f"dlq.{subject}"

        try:
            queue = await self.channel.declare_queue(
                dlq_queue_name,
                passive=True,  # Just check, don't create
            )

            return {
                "subject": subject,
                "queue": dlq_queue_name,
                "message_count": queue.declaration_result.message_count,
                "consumer_count": queue.declaration_result.consumer_count,
            }
        except aio_pika.exceptions.ChannelClosed:
            logger.warning("dlq.queue.not_found", subject=subject)
            return {
                "subject": subject,
                "queue": dlq_queue_name,
                "message_count": 0,
                "consumer_count": 0,
            }

    async def get_all_dlq_depths(self) -> List[Dict[str, int]]:
        """
        Get DLQ depths for all subjects

        Returns:
            List of dicts with DLQ depths
        """
        depths = []
        for subject in SUBJECTS:
            depth = await self.get_dlq_depth(subject)
            depths.append(depth)

        return depths

    async def purge_dlq(self, subject: str) -> int:
        """
        Purge (delete all messages) from a DLQ

        Args:
            subject: Event subject

        Returns:
            Number of messages purged
        """
        dlq_queue_name = f"dlq.{subject}"

        try:
            queue = await self.channel.get_queue(dlq_queue_name)
            result = await queue.purge()

            logger.info("dlq.purge.success", subject=subject, count=result.message_count)
            return result.message_count
        except Exception as e:
            logger.error("dlq.purge.failed", subject=subject, error=str(e))
            return 0


# ============================================================
# CLI Commands
# ============================================================

async def setup_dlq_cli(rabbitmq_url: str):
    """CLI command to set up DLQ infrastructure"""
    configurator = DLQConfigurator(rabbitmq_url)

    try:
        await configurator.connect()
        await configurator.setup_dlq_infrastructure()

        # Show DLQ depths
        depths = await configurator.get_all_dlq_depths()
        print("\nDLQ Depths:")
        for depth in depths:
            print(f"  {depth['subject']}: {depth['message_count']} messages")

    finally:
        await configurator.close()


async def show_dlq_depths_cli(rabbitmq_url: str):
    """CLI command to show DLQ depths"""
    configurator = DLQConfigurator(rabbitmq_url)

    try:
        await configurator.connect()
        depths = await configurator.get_all_dlq_depths()

        print("\nDLQ Depths:")
        print(f"{'Subject':<30} {'Queue':<40} {'Messages':<10}")
        print("-" * 80)
        for depth in depths:
            print(
                f"{depth['subject']:<30} "
                f"{depth['queue']:<40} "
                f"{depth['message_count']:<10}"
            )

        total = sum(d['message_count'] for d in depths)
        print("-" * 80)
        print(f"Total: {total} messages across all DLQs")

    finally:
        await configurator.close()


if __name__ == "__main__":
    import sys

    rabbitmq_url = "amqp://guest:guest@localhost:5672/"

    if len(sys.argv) > 1 and sys.argv[1] == "setup":
        asyncio.run(setup_dlq_cli(rabbitmq_url))
    elif len(sys.argv) > 1 and sys.argv[1] == "depths":
        asyncio.run(show_dlq_depths_cli(rabbitmq_url))
    else:
        print("Usage:")
        print("  python dlq_config.py setup   - Set up DLQ infrastructure")
        print("  python dlq_config.py depths  - Show DLQ depths")

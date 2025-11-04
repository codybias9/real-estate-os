"""
DLQ Replay Tool
Re-publishes messages from DLQ back to main queue for reprocessing

Usage:
    python replay.py --subject property.created --limit 100
    python replay.py --subject memo.generated --all
    python replay.py --list-subjects
"""

import asyncio
import argparse
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
import aio_pika
import structlog

logger = structlog.get_logger()


class DLQReplay:
    """
    DLQ Replay Tool
    - Fetches messages from DLQ
    - Re-publishes to main queue with idempotency preserved
    - Tracks replay statistics
    """

    def __init__(self, rabbitmq_url: str):
        self.rabbitmq_url = rabbitmq_url
        self.connection = None
        self.channel = None
        self.stats = {
            "fetched": 0,
            "replayed": 0,
            "failed": 0,
            "skipped": 0,
        }

    async def connect(self):
        """Establish connection to RabbitMQ"""
        self.connection = await aio_pika.connect_robust(self.rabbitmq_url)
        self.channel = await self.connection.channel()
        logger.info("replay.connect.success")

    async def close(self):
        """Close connection"""
        if self.connection:
            await self.connection.close()
            logger.info("replay.close.success")

    async def replay_messages(
        self,
        subject: str,
        limit: Optional[int] = None,
        dry_run: bool = False,
    ) -> Dict[str, int]:
        """
        Replay messages from DLQ to main queue

        Args:
            subject: Event subject (e.g., "property.created")
            limit: Maximum number of messages to replay (None = all)
            dry_run: If True, don't actually replay, just report

        Returns:
            Statistics dict with counts
        """
        dlq_queue_name = f"dlq.{subject}"
        main_queue_name = f"q.{subject}"

        logger.info(
            "replay.start",
            subject=subject,
            dlq_queue=dlq_queue_name,
            limit=limit or "all",
            dry_run=dry_run,
        )

        # Get DLQ queue
        try:
            dlq_queue = await self.channel.get_queue(dlq_queue_name)
        except Exception as e:
            logger.error("replay.dlq_not_found", subject=subject, error=str(e))
            return self.stats

        # Get main exchange (for re-publishing)
        exchange = await self.channel.get_exchange("events")

        # Reset stats
        self.stats = {"fetched": 0, "replayed": 0, "failed": 0, "skipped": 0}

        # Fetch and replay messages
        replayed_count = 0
        max_messages = limit if limit else 1000000  # Effectively unlimited

        while replayed_count < max_messages:
            # Get one message from DLQ
            message = await dlq_queue.get(timeout=1.0)

            if message is None:
                # No more messages in DLQ
                logger.info("replay.dlq_empty", subject=subject)
                break

            self.stats["fetched"] += 1

            try:
                # Parse message body
                event = json.loads(message.body.decode())

                # Check idempotency key
                event_id = event.get("event_id")
                if not event_id:
                    logger.warning(
                        "replay.no_event_id",
                        subject=subject,
                    )
                    self.stats["skipped"] += 1
                    await message.ack()
                    continue

                # Add replay metadata
                if "metadata" not in event:
                    event["metadata"] = {}

                event["metadata"]["replayed_at"] = datetime.utcnow().isoformat()
                event["metadata"]["replayed_from"] = "dlq"
                event["metadata"]["original_failure_time"] = (
                    message.headers.get("x-first-death-time")
                    if message.headers
                    else None
                )

                # Re-publish to main queue
                if not dry_run:
                    await exchange.publish(
                        aio_pika.Message(
                            body=json.dumps(event).encode(),
                            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                            headers={
                                "x-replayed": "true",
                                "x-replay-time": datetime.utcnow().isoformat(),
                            },
                        ),
                        routing_key=subject,
                    )

                    logger.info(
                        "replay.message.success",
                        subject=subject,
                        event_id=event_id,
                    )
                else:
                    logger.info(
                        "replay.message.dry_run",
                        subject=subject,
                        event_id=event_id,
                    )

                # Acknowledge DLQ message (remove from DLQ)
                await message.ack()

                self.stats["replayed"] += 1
                replayed_count += 1

            except Exception as e:
                logger.error(
                    "replay.message.failed",
                    subject=subject,
                    error=str(e),
                )
                # Nack message back to DLQ
                await message.nack(requeue=True)
                self.stats["failed"] += 1

        logger.info(
            "replay.complete",
            subject=subject,
            stats=self.stats,
        )

        return self.stats

    async def list_subjects_with_dlq_messages(self) -> List[Dict[str, Any]]:
        """
        List all subjects that have messages in their DLQ

        Returns:
            List of dicts with subject and message count
        """
        from infrastructure.rabbitmq.dlq_config import SUBJECTS

        subjects_with_messages = []

        for subject in SUBJECTS:
            dlq_queue_name = f"dlq.{subject}"

            try:
                queue = await self.channel.declare_queue(
                    dlq_queue_name,
                    passive=True,  # Just check, don't create
                )

                message_count = queue.declaration_result.message_count

                if message_count > 0:
                    subjects_with_messages.append({
                        "subject": subject,
                        "queue": dlq_queue_name,
                        "message_count": message_count,
                    })

            except Exception:
                # Queue doesn't exist, skip
                continue

        return subjects_with_messages

    async def peek_messages(
        self,
        subject: str,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Peek at messages in DLQ without removing them

        Args:
            subject: Event subject
            limit: Number of messages to peek

        Returns:
            List of message payloads
        """
        dlq_queue_name = f"dlq.{subject}"

        logger.info("replay.peek.start", subject=subject, limit=limit)

        messages = []

        try:
            dlq_queue = await self.channel.get_queue(dlq_queue_name)

            for _ in range(limit):
                message = await dlq_queue.get(timeout=1.0)

                if message is None:
                    break

                event = json.loads(message.body.decode())
                messages.append(event)

                # Nack to put back in queue
                await message.nack(requeue=True)

        except Exception as e:
            logger.error("replay.peek.failed", subject=subject, error=str(e))

        logger.info("replay.peek.complete", subject=subject, count=len(messages))

        return messages


# ============================================================
# CLI Interface
# ============================================================

async def cli_replay(args):
    """CLI command to replay messages"""
    replayer = DLQReplay(args.rabbitmq_url)

    try:
        await replayer.connect()

        stats = await replayer.replay_messages(
            subject=args.subject,
            limit=args.limit,
            dry_run=args.dry_run,
        )

        print("\n" + "=" * 60)
        print("DLQ Replay Complete")
        print("=" * 60)
        print(f"Subject:        {args.subject}")
        print(f"Fetched:        {stats['fetched']}")
        print(f"Replayed:       {stats['replayed']}")
        print(f"Failed:         {stats['failed']}")
        print(f"Skipped:        {stats['skipped']}")
        print("=" * 60)

        # Create report JSON
        report = {
            "timestamp": datetime.utcnow().isoformat(),
            "subject": args.subject,
            "limit": args.limit,
            "dry_run": args.dry_run,
            "stats": stats,
        }

        # Save report
        report_path = f"/home/user/real-estate-os/audit_artifacts/logs/dlq-replay-{args.subject}-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}.json"
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)

        print(f"\nReport saved to: {report_path}")

    finally:
        await replayer.close()


async def cli_list(args):
    """CLI command to list subjects with DLQ messages"""
    replayer = DLQReplay(args.rabbitmq_url)

    try:
        await replayer.connect()

        subjects = await replayer.list_subjects_with_dlq_messages()

        print("\n" + "=" * 80)
        print("Subjects with DLQ Messages")
        print("=" * 80)
        print(f"{'Subject':<30} {'Queue':<40} {'Messages':<10}")
        print("-" * 80)

        for s in subjects:
            print(f"{s['subject']:<30} {s['queue']:<40} {s['message_count']:<10}")

        print("-" * 80)
        print(f"Total subjects with messages: {len(subjects)}")
        print("=" * 80)

    finally:
        await replayer.close()


async def cli_peek(args):
    """CLI command to peek at DLQ messages"""
    replayer = DLQReplay(args.rabbitmq_url)

    try:
        await replayer.connect()

        messages = await replayer.peek_messages(
            subject=args.subject,
            limit=args.limit,
        )

        print("\n" + "=" * 80)
        print(f"DLQ Messages for {args.subject}")
        print("=" * 80)

        for i, msg in enumerate(messages, 1):
            print(f"\nMessage {i}:")
            print(json.dumps(msg, indent=2))

        print("\n" + "=" * 80)
        print(f"Total messages shown: {len(messages)}")
        print("=" * 80)

    finally:
        await replayer.close()


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="DLQ Replay Tool - Replay failed messages from DLQ"
    )

    parser.add_argument(
        "--rabbitmq-url",
        default="amqp://guest:guest@localhost:5672/",
        help="RabbitMQ connection URL",
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Replay command
    replay_parser = subparsers.add_parser("replay", help="Replay messages from DLQ")
    replay_parser.add_argument("--subject", required=True, help="Event subject")
    replay_parser.add_argument(
        "--limit", type=int, help="Max messages to replay (default: all)"
    )
    replay_parser.add_argument(
        "--dry-run", action="store_true", help="Don't actually replay, just report"
    )

    # List command
    subparsers.add_parser("list", help="List subjects with DLQ messages")

    # Peek command
    peek_parser = subparsers.add_parser("peek", help="Peek at DLQ messages")
    peek_parser.add_argument("--subject", required=True, help="Event subject")
    peek_parser.add_argument(
        "--limit", type=int, default=10, help="Number of messages to peek"
    )

    args = parser.parse_args()

    if args.command == "replay":
        asyncio.run(cli_replay(args))
    elif args.command == "list":
        asyncio.run(cli_list(args))
    elif args.command == "peek":
        asyncio.run(cli_peek(args))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

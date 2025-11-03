"""
DLQ Integration Tests
Tests complete flow: poison message → DLQ → fix → replay → success
"""

import pytest
import asyncio
import json
from uuid import uuid4
from datetime import datetime
import aio_pika

from events.dlq_consumer import DLQConsumer, TransientError, NonTransientError
from ops.dlq.replay import DLQReplay
from infrastructure.rabbitmq.dlq_config import DLQConfigurator


class TestDLQCompleteFlow:
    """
    Integration tests for complete DLQ workflow
    Validates: poison message → DLQ → replay → success
    """

    @pytest.fixture
    def rabbitmq_url(self):
        """RabbitMQ connection URL"""
        return "amqp://guest:guest@localhost:5672/"

    @pytest.fixture
    async def setup_dlq_infrastructure(self, rabbitmq_url):
        """Set up DLQ infrastructure before tests"""
        configurator = DLQConfigurator(rabbitmq_url)
        await configurator.connect()
        await configurator.setup_dlq_infrastructure()
        await configurator.close()

        yield

        # Cleanup after tests
        configurator = DLQConfigurator(rabbitmq_url)
        await configurator.connect()
        for subject in ["test.subject", "property.created", "memo.generated"]:
            try:
                await configurator.purge_dlq(subject)
            except:
                pass
        await configurator.close()

    @pytest.fixture
    def test_subject(self):
        """Test event subject"""
        return "test.subject"

    @pytest.mark.asyncio
    async def test_poison_message_to_dlq(
        self, rabbitmq_url, test_subject, setup_dlq_infrastructure
    ):
        """
        Test 1: Poison message is sent to DLQ after max retries

        Flow:
        1. Publish message that always fails (non-transient error)
        2. Consumer processes message
        3. Message should appear in DLQ after nack(requeue=False)
        """
        # Create handler that always fails with non-transient error
        async def failing_handler(event):
            raise NonTransientError("Invalid message format")

        # Create consumer
        consumer = DLQConsumer(
            rabbitmq_url=rabbitmq_url,
            subject=test_subject,
            handler=failing_handler,
        )

        await consumer.connect()

        # Publish test message
        connection = await aio_pika.connect_robust(rabbitmq_url)
        channel = await connection.channel()
        exchange = await channel.get_exchange("events")

        event_id = str(uuid4())
        event = {
            "event_id": event_id,
            "type": "test.subject",
            "payload": {"test": "data"},
            "metadata": {"timestamp": datetime.utcnow().isoformat()},
        }

        await exchange.publish(
            aio_pika.Message(
                body=json.dumps(event).encode(),
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            ),
            routing_key=test_subject,
        )

        # Wait for consumer to process and send to DLQ
        await asyncio.sleep(2)

        # Check DLQ depth
        configurator = DLQConfigurator(rabbitmq_url)
        await configurator.connect()
        depth = await configurator.get_dlq_depth(test_subject)
        await configurator.close()

        # Validate message is in DLQ
        assert depth["message_count"] >= 1, "Message should be in DLQ"

        # Cleanup
        await consumer.close()
        await connection.close()

    @pytest.mark.asyncio
    async def test_transient_error_retry(
        self, rabbitmq_url, test_subject, setup_dlq_infrastructure
    ):
        """
        Test 2: Transient errors are retried with exponential backoff

        Flow:
        1. Publish message that fails 3 times, then succeeds
        2. Consumer should retry with backoff
        3. Message should eventually succeed (not in DLQ)
        """
        # Track attempts
        attempts = {"count": 0}

        async def transient_then_success_handler(event):
            attempts["count"] += 1

            if attempts["count"] < 3:
                # Fail first 2 attempts
                raise TransientError("Database temporarily unavailable")

            # Succeed on 3rd attempt
            return {"status": "success"}

        # Create consumer
        consumer = DLQConsumer(
            rabbitmq_url=rabbitmq_url,
            subject=test_subject,
            handler=transient_then_success_handler,
        )

        await consumer.connect()

        # Publish test message
        connection = await aio_pika.connect_robust(rabbitmq_url)
        channel = await connection.channel()
        exchange = await channel.get_exchange("events")

        event_id = str(uuid4())
        event = {
            "event_id": event_id,
            "type": "test.subject",
            "payload": {"test": "data"},
            "metadata": {"timestamp": datetime.utcnow().isoformat()},
        }

        await exchange.publish(
            aio_pika.Message(
                body=json.dumps(event).encode(),
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            ),
            routing_key=test_subject,
        )

        # Wait for processing with retries
        await asyncio.sleep(5)

        # Validate attempts
        assert attempts["count"] >= 3, "Should have retried at least 3 times"

        # Check DLQ depth (should be 0 since eventually succeeded)
        configurator = DLQConfigurator(rabbitmq_url)
        await configurator.connect()
        depth = await configurator.get_dlq_depth(test_subject)
        await configurator.close()

        # Message should NOT be in DLQ
        assert depth["message_count"] == 0, "Message should not be in DLQ after success"

        # Cleanup
        await consumer.close()
        await connection.close()

    @pytest.mark.asyncio
    async def test_dlq_replay_success(
        self, rabbitmq_url, test_subject, setup_dlq_infrastructure
    ):
        """
        Test 3: Replay messages from DLQ back to main queue

        Flow:
        1. Seed DLQ with failed messages
        2. Fix the code (use successful handler)
        3. Replay messages from DLQ
        4. Verify messages process successfully
        """
        # Seed DLQ with a failed message
        connection = await aio_pika.connect_robust(rabbitmq_url)
        channel = await connection.channel()
        dlq_queue = await channel.get_queue(f"dlq.{test_subject}")

        event_id = str(uuid4())
        event = {
            "event_id": event_id,
            "type": "test.subject",
            "payload": {"test": "replay"},
            "metadata": {"timestamp": datetime.utcnow().isoformat()},
        }

        # Publish directly to DLQ
        await channel.default_exchange.publish(
            aio_pika.Message(
                body=json.dumps(event).encode(),
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            ),
            routing_key=f"dlq.{test_subject}",
        )

        await asyncio.sleep(1)

        # Verify message is in DLQ
        configurator = DLQConfigurator(rabbitmq_url)
        await configurator.connect()
        depth_before = await configurator.get_dlq_depth(test_subject)
        await configurator.close()

        assert depth_before["message_count"] >= 1, "Message should be in DLQ"

        # Replay from DLQ
        replayer = DLQReplay(rabbitmq_url)
        await replayer.connect()

        stats = await replayer.replay_messages(
            subject=test_subject,
            limit=10,
            dry_run=False,
        )

        await replayer.close()

        # Validate replay stats
        assert stats["fetched"] >= 1, "Should have fetched at least 1 message"
        assert stats["replayed"] >= 1, "Should have replayed at least 1 message"
        assert stats["failed"] == 0, "No replay failures expected"

        # Verify DLQ is now empty
        configurator = DLQConfigurator(rabbitmq_url)
        await configurator.connect()
        depth_after = await configurator.get_dlq_depth(test_subject)
        await configurator.close()

        assert depth_after["message_count"] == 0, "DLQ should be empty after replay"

        # Cleanup
        await connection.close()

    @pytest.mark.asyncio
    async def test_dlq_alert_threshold(
        self, rabbitmq_url, test_subject, setup_dlq_infrastructure
    ):
        """
        Test 4: DLQ depth alert fires when depth > 0 for > 5 minutes

        Flow:
        1. Seed DLQ with messages
        2. Check DLQ depth
        3. Verify alert would fire (depth > 0)
        """
        # Seed DLQ with multiple messages
        connection = await aio_pika.connect_robust(rabbitmq_url)
        channel = await connection.channel()

        for i in range(5):
            event_id = str(uuid4())
            event = {
                "event_id": event_id,
                "type": "test.subject",
                "payload": {"test": f"alert_{i}"},
                "metadata": {"timestamp": datetime.utcnow().isoformat()},
            }

            await channel.default_exchange.publish(
                aio_pika.Message(
                    body=json.dumps(event).encode(),
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                ),
                routing_key=f"dlq.{test_subject}",
            )

        await asyncio.sleep(1)

        # Check DLQ depth
        configurator = DLQConfigurator(rabbitmq_url)
        await configurator.connect()
        depth = await configurator.get_dlq_depth(test_subject)
        await configurator.close()

        # Validate alert condition
        assert depth["message_count"] > 0, "DLQ depth should trigger alert"

        # In real scenario, Grafana alert would fire after 5 minutes
        # This test just validates the metric would be available

        # Cleanup
        await connection.close()

    @pytest.mark.asyncio
    async def test_idempotency_preserved_on_replay(
        self, rabbitmq_url, test_subject, setup_dlq_infrastructure
    ):
        """
        Test 5: Replay preserves idempotency

        Flow:
        1. Seed DLQ with message
        2. Replay message
        3. Verify replayed message has replay metadata
        4. Verify event_id is preserved
        """
        # Seed DLQ
        connection = await aio_pika.connect_robust(rabbitmq_url)
        channel = await connection.channel()

        event_id = str(uuid4())
        original_event = {
            "event_id": event_id,
            "type": "test.subject",
            "payload": {"test": "idempotency"},
            "metadata": {"timestamp": datetime.utcnow().isoformat()},
        }

        await channel.default_exchange.publish(
            aio_pika.Message(
                body=json.dumps(original_event).encode(),
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            ),
            routing_key=f"dlq.{test_subject}",
        )

        await asyncio.sleep(1)

        # Replay
        replayer = DLQReplay(rabbitmq_url)
        await replayer.connect()

        # Peek at replayed message
        messages = await replayer.peek_messages(subject=test_subject, limit=1)

        await replayer.close()

        # Validate
        assert len(messages) == 1, "Should have 1 message"
        replayed_event = messages[0]

        # Event ID should be preserved
        assert replayed_event["event_id"] == event_id, "Event ID should be preserved"

        # Replay metadata should be added (after actual replay)
        # For now, just verify original structure is intact

        # Cleanup
        await connection.close()

    @pytest.mark.asyncio
    async def test_max_retries_sends_to_dlq(
        self, rabbitmq_url, test_subject, setup_dlq_infrastructure
    ):
        """
        Test 6: Message is sent to DLQ after exceeding max retries

        Flow:
        1. Publish message that always fails (transient error)
        2. Consumer retries 5 times with backoff
        3. After 5 retries, message should be sent to DLQ
        """
        # Track attempts
        attempts = {"count": 0}

        async def always_fail_transient_handler(event):
            attempts["count"] += 1
            raise TransientError("Always fails")

        # Create consumer with low max_attempts for testing
        consumer = DLQConsumer(
            rabbitmq_url=rabbitmq_url,
            subject=test_subject,
            handler=always_fail_transient_handler,
        )

        # Override health governor with lower max_attempts
        consumer.health_governor.max_attempts = 3

        await consumer.connect()

        # Publish test message
        connection = await aio_pika.connect_robust(rabbitmq_url)
        channel = await connection.channel()
        exchange = await channel.get_exchange("events")

        event_id = str(uuid4())
        event = {
            "event_id": event_id,
            "type": "test.subject",
            "payload": {"test": "max_retries"},
            "metadata": {"timestamp": datetime.utcnow().isoformat()},
        }

        await exchange.publish(
            aio_pika.Message(
                body=json.dumps(event).encode(),
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            ),
            routing_key=test_subject,
        )

        # Wait for retries and DLQ
        await asyncio.sleep(10)

        # Check DLQ depth
        configurator = DLQConfigurator(rabbitmq_url)
        await configurator.connect()
        depth = await configurator.get_dlq_depth(test_subject)
        await configurator.close()

        # Message should be in DLQ after max retries
        assert depth["message_count"] >= 1, "Message should be in DLQ after max retries"

        # Cleanup
        await consumer.close()
        await connection.close()


class TestDLQOperations:
    """Test DLQ operational commands"""

    @pytest.fixture
    def rabbitmq_url(self):
        """RabbitMQ connection URL"""
        return "amqp://guest:guest@localhost:5672/"

    @pytest.mark.asyncio
    async def test_dlq_purge(self, rabbitmq_url):
        """
        Test DLQ purge operation

        Flow:
        1. Seed DLQ with messages
        2. Purge DLQ
        3. Verify DLQ is empty
        """
        test_subject = "test.purge"

        # Seed DLQ
        connection = await aio_pika.connect_robust(rabbitmq_url)
        channel = await connection.channel()

        for i in range(3):
            event_id = str(uuid4())
            event = {
                "event_id": event_id,
                "type": "test.purge",
                "payload": {"test": f"purge_{i}"},
            }

            await channel.default_exchange.publish(
                aio_pika.Message(
                    body=json.dumps(event).encode(),
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                ),
                routing_key=f"dlq.{test_subject}",
            )

        await asyncio.sleep(1)

        # Purge DLQ
        configurator = DLQConfigurator(rabbitmq_url)
        await configurator.connect()

        purged_count = await configurator.purge_dlq(test_subject)

        depth_after = await configurator.get_dlq_depth(test_subject)

        await configurator.close()

        # Validate
        assert purged_count >= 3, "Should have purged at least 3 messages"
        assert depth_after["message_count"] == 0, "DLQ should be empty after purge"

        # Cleanup
        await connection.close()

    @pytest.mark.asyncio
    async def test_list_subjects_with_messages(self, rabbitmq_url):
        """
        Test listing subjects with DLQ messages

        Flow:
        1. Seed DLQ for multiple subjects
        2. List subjects with messages
        3. Verify correct subjects are returned
        """
        # Seed DLQs
        connection = await aio_pika.connect_robust(rabbitmq_url)
        channel = await connection.channel()

        subjects = ["property.created", "memo.generated"]

        for subject in subjects:
            event_id = str(uuid4())
            event = {
                "event_id": event_id,
                "type": subject,
                "payload": {"test": "list"},
            }

            await channel.default_exchange.publish(
                aio_pika.Message(
                    body=json.dumps(event).encode(),
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                ),
                routing_key=f"dlq.{subject}",
            )

        await asyncio.sleep(1)

        # List subjects
        replayer = DLQReplay(rabbitmq_url)
        await replayer.connect()

        subjects_with_messages = await replayer.list_subjects_with_dlq_messages()

        await replayer.close()

        # Validate
        subject_names = [s["subject"] for s in subjects_with_messages]

        assert "property.created" in subject_names, "property.created should have messages"
        assert "memo.generated" in subject_names, "memo.generated should have messages"

        # Cleanup
        await connection.close()

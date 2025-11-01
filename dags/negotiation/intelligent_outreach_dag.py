"""Intelligent Outreach DAG
Automated outreach with NLP, send-time optimization, and policy enforcement

Schedule: Hourly
"""

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago
from datetime import timedelta
import sys
import pandas as pd
from sqlalchemy import create_engine
import os
import logging

sys.path.append('/home/user/real-estate-os')
from ml.negotiation.reply_classifier import ReplyClassifier, ConversationTracker
from ml.negotiation.contact_policy import ContactPolicyEngine, ContactChannel, create_default_policy
from ml.negotiation.bandits import SendTimeOptimizer, TemplateSelector, SequenceSelector, ContextFeatures

logger = logging.getLogger(__name__)

default_args = {
    'owner': 'outreach-team',
    'depends_on_past': False,
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

with DAG(
    'intelligent_outreach',
    default_args=default_args,
    description='Intelligent outreach with NLP and optimization',
    schedule_interval='0 * * * *',  # Hourly
    start_date=days_ago(1),
    catchup=False,
    tags=['outreach', 'negotiation', 'ml'],
) as dag:

    def classify_incoming_replies(**context):
        """Classify incoming replies from leads"""

        engine = create_engine(os.getenv("DB_DSN"))

        # Get unprocessed replies from last hour
        query = """
        SELECT
            id AS reply_id,
            lead_id,
            property_id,
            message_text,
            received_at
        FROM outreach_reply
        WHERE processed = FALSE
          AND received_at >= NOW() - INTERVAL '1 hour'
        ORDER BY received_at DESC
        LIMIT 1000
        """

        replies_df = pd.read_sql(query, engine)

        if replies_df.empty:
            logger.info("No new replies to process")
            engine.dispose()
            return

        logger.info(f"Processing {len(replies_df)} replies")

        classifier = ReplyClassifier()
        tracker = ConversationTracker()

        processed = []

        for _, row in replies_df.iterrows():
            # Classify reply
            result = classifier.classify(row['message_text'])

            # Update conversation state
            state = tracker.update_state(
                lead_id=row['lead_id'],
                property_id=row['property_id'],
                classification=result
            )

            processed.append({
                'reply_id': row['reply_id'],
                'lead_id': row['lead_id'],
                'property_id': row['property_id'],
                'intent': result.intent.value,
                'confidence': result.confidence,
                'sentiment': result.sentiment,
                'urgency': result.urgency,
                'next_action': result.next_action,
                'interest_score': state.interest_score
            })

        # Update database
        # TODO: Bulk update outreach_reply SET processed=TRUE, intent=?, confidence=?

        engine.dispose()

        # Save to XCom
        context['task_instance'].xcom_push(key='classified_replies', value=processed)

        logger.info(f"Classified {len(processed)} replies")

    def schedule_followups(**context):
        """Schedule followup messages based on optimal send times"""

        engine = create_engine(os.getenv("DB_DSN"))

        # Get leads due for followup
        query = """
        SELECT
            l.id AS lead_id,
            l.property_id,
            l.tenant_id,
            l.contact_email,
            l.timezone,
            COUNT(o.id) AS messages_sent,
            MAX(o.sent_at) AS last_sent_at,
            l.interest_score
        FROM lead l
        LEFT JOIN outreach_message o ON o.lead_id = l.id
        WHERE l.status = 'active'
          AND l.opted_out = FALSE
          AND (l.last_contact_at IS NULL OR l.last_contact_at < NOW() - INTERVAL '2 days')
        GROUP BY l.id
        HAVING COUNT(o.id) < 5  -- Max 5 attempts
        LIMIT 500
        """

        leads_df = pd.read_sql(query, engine)

        if leads_df.empty:
            logger.info("No leads due for followup")
            engine.dispose()
            return

        logger.info(f"Scheduling followups for {len(leads_df)} leads")

        # Initialize components
        policy = create_default_policy()
        policy_engine = ContactPolicyEngine(policy)
        send_time_optimizer = SendTimeOptimizer()
        template_selector = TemplateSelector(["template1", "template2", "template3"])  # TODO: Load from DB

        scheduled = []

        for _, row in leads_df.iterrows():
            # Check if contact is allowed
            outcome, reason = policy_engine.can_contact(
                lead_id=row['lead_id'],
                channel=ContactChannel.EMAIL,
                user_id="system",
                lead_timezone=row['timezone'] or "America/New_York"
            )

            if outcome.value != "allowed":
                logger.debug(f"Skipping lead {row['lead_id']}: {reason}")
                continue

            # Select optimal send time
            send_hour = send_time_optimizer.select_send_time()

            # Select template
            template_id = template_selector.select_template()

            # Build context for sequence selection
            context_features = ContextFeatures(
                lead_responded_before=(row['messages_sent'] > 0),
                lead_interest_score=row['interest_score'] or 0.0,
                days_since_last_contact=(pd.Timestamp.now() - row['last_sent_at']).days if pd.notna(row['last_sent_at']) else 999,
                day_of_week=pd.Timestamp.now().weekday(),
                is_weekend=(pd.Timestamp.now().weekday() >= 5)
            )

            sequence_selector = SequenceSelector()
            sequence_id = sequence_selector.select_sequence(context_features)

            scheduled.append({
                'lead_id': row['lead_id'],
                'property_id': row['property_id'],
                'tenant_id': row['tenant_id'],
                'contact_email': row['contact_email'],
                'send_hour': send_hour,
                'template_id': template_id,
                'sequence_id': sequence_id,
                'scheduled_for': pd.Timestamp.now().replace(hour=send_hour, minute=0, second=0)
            })

        # Insert into outreach_schedule table
        # TODO: Bulk insert scheduled messages

        engine.dispose()

        logger.info(f"Scheduled {len(scheduled)} followup messages")

        context['task_instance'].xcom_push(key='scheduled_followups', value=scheduled)

    def send_scheduled_messages(**context):
        """Send messages scheduled for this hour"""

        engine = create_engine(os.getenv("DB_DSN"))

        current_hour = pd.Timestamp.now().hour

        # Get messages scheduled for this hour
        query = f"""
        SELECT
            id AS schedule_id,
            lead_id,
            property_id,
            tenant_id,
            contact_email,
            template_id,
            sequence_id
        FROM outreach_schedule
        WHERE sent = FALSE
          AND scheduled_hour = {current_hour}
          AND scheduled_date = CURRENT_DATE
        LIMIT 1000
        """

        scheduled_df = pd.read_sql(query, engine)

        if scheduled_df.empty:
            logger.info(f"No messages scheduled for hour {current_hour}")
            engine.dispose()
            return

        logger.info(f"Sending {len(scheduled_df)} scheduled messages")

        sent_count = 0

        for _, row in scheduled_df.iterrows():
            # TODO: Fetch template content
            # TODO: Personalize template
            # TODO: Send via email provider (SendGrid, Postmark, etc.)

            # Mark as sent
            # UPDATE outreach_schedule SET sent=TRUE WHERE id=?

            sent_count += 1

        engine.dispose()

        logger.info(f"Sent {sent_count} messages")

    def update_bandit_models(**context):
        """Update bandit models with overnight outcomes"""

        # TODO: Load replies from last 24h and update bandits
        # - Update send-time optimizer with reply outcomes by hour
        # - Update template selector with reply outcomes by template
        # - Update sequence selector with conversion outcomes by sequence

        logger.info("Bandit models updated")

    # Task definitions
    classify = PythonOperator(
        task_id='classify_incoming_replies',
        python_callable=classify_incoming_replies,
    )

    schedule = PythonOperator(
        task_id='schedule_followups',
        python_callable=schedule_followups,
    )

    send = PythonOperator(
        task_id='send_scheduled_messages',
        python_callable=send_scheduled_messages,
    )

    update_bandits = PythonOperator(
        task_id='update_bandit_models',
        python_callable=update_bandit_models,
    )

    # Dependencies
    classify >> schedule >> send >> update_bandits

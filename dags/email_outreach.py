"""Execute email campaigns for property outreach."""

from datetime import datetime
from airflow import DAG
from airflow.operators.python import PythonOperator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import sys
sys.path.insert(0, '/home/user/real-estate-os')

from db.models import Campaign
from agents.outreach.email_service import send_campaign_emails


# Database configuration
DATABASE_URL = "postgresql://airflow:airflow@postgres:5432/airflow"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)


def execute_active_campaigns(**context):
    """Execute all active campaigns that are ready to send."""
    db = SessionLocal()

    try:
        # Find campaigns that are ready to send
        active_campaigns = db.query(Campaign).filter(
            Campaign.status.in_(['draft', 'scheduled'])
        ).all()

        context['task_instance'].xcom_push(key='found_campaigns', value=len(active_campaigns))

        executed_count = 0
        total_sent = 0
        error_count = 0

        for campaign in active_campaigns:
            try:
                print(f"Executing campaign: {campaign.name} (ID: {campaign.id})")

                # Send campaign emails
                result = send_campaign_emails(
                    campaign_id=campaign.id,
                    db=db,
                    simulate_engagement=True  # Demo mode: simulate opens/clicks
                )

                executed_count += 1
                total_sent += result['sent']

                print(f"✓ Campaign executed: {result['sent']} emails sent")

                # Print engagement stats if available
                if 'engagement' in result:
                    eng = result['engagement']
                    print(f"  Engagement: {eng['opened']} opens, {eng['clicked']} clicks, {eng['replied']} replies")

            except Exception as e:
                error_count += 1
                print(f"✗ Error executing campaign {campaign.id}: {str(e)}")
                continue

        context['task_instance'].xcom_push(key='executed_count', value=executed_count)
        context['task_instance'].xcom_push(key='total_sent', value=total_sent)
        context['task_instance'].xcom_push(key='error_count', value=error_count)

        print(f"\nEmail Outreach Summary:")
        print(f"  Campaigns Found: {len(active_campaigns)}")
        print(f"  Campaigns Executed: {executed_count}")
        print(f"  Total Emails Sent: {total_sent}")
        print(f"  Errors: {error_count}")

    finally:
        db.close()


def send_specific_campaign(campaign_id: int, **context):
    """
    Execute a specific campaign by ID.
    Can be triggered manually via Airflow UI with parameters.
    """
    db = SessionLocal()

    try:
        print(f"Executing campaign ID: {campaign_id}")

        result = send_campaign_emails(
            campaign_id=campaign_id,
            db=db,
            simulate_engagement=True
        )

        context['task_instance'].xcom_push(key='sent_count', value=result['sent'])

        print(f"Campaign execution complete:")
        print(f"  Sent: {result['sent']} emails")

        if 'engagement' in result:
            eng = result['engagement']
            print(f"  Opens: {eng['opened']} ({eng['open_rate']:.1f}%)")
            print(f"  Clicks: {eng['clicked']} ({eng['click_rate']:.1f}%)")
            print(f"  Replies: {eng['replied']} ({eng['reply_rate']:.1f}%)")

        return result

    finally:
        db.close()


# Define the DAG
with DAG(
    dag_id="email_outreach",
    description="Execute email campaigns for property outreach",
    start_date=datetime(2025, 1, 1),
    schedule_interval="0 9 * * *",  # Daily at 9 AM
    catchup=False,
    tags=["pipeline", "outreach"],
    default_args={
        'retries': 1,
        'retry_delay': 300,  # 5 minutes
    }
) as dag:

    # Main task: Execute all active campaigns
    execute_campaigns_task = PythonOperator(
        task_id="execute_active_campaigns",
        python_callable=execute_active_campaigns,
        provide_context=True,
    )

    # Task dependencies
    execute_campaigns_task

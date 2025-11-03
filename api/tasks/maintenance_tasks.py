"""
Maintenance Background Tasks
Scheduled cleanup and metric updates
"""
from celery import shared_task
from datetime import datetime, timedelta
import logging
from typing import Dict, Any
from sqlalchemy import func, and_

from api.celery_app import celery_app, get_db_session
from db.models import (
    Team, Property, Communication, CommunicationType,
    DeliverabilityMetrics, BudgetTracking, ShareLink, ShareLinkStatus
)

logger = logging.getLogger(__name__)

# ============================================================================
# DELIVERABILITY METRICS
# ============================================================================

@celery_app.task(bind=True, name="api.tasks.maintenance_tasks.update_deliverability_metrics")
def update_deliverability_metrics(self) -> Dict[str, Any]:
    """
    Update email deliverability metrics for all teams

    Runs daily at 2:00 AM via Celery Beat

    Calculates:
    - Bounce rate
    - Open rate
    - Click rate
    - Domain warmup status
    - Suppression list size
    """
    logger.info("Updating deliverability metrics")

    with next(get_db_session()) as db:
        teams = db.query(Team).all()

        results = {
            "teams_processed": 0,
            "metrics_created": 0
        }

        yesterday = (datetime.utcnow() - timedelta(days=1)).date()

        for team in teams:
            try:
                # Get email communications for yesterday
                emails = db.query(Communication).filter(
                    and_(
                        Communication.property_id.in_(
                            db.query(Property.id).filter(Property.team_id == team.id)
                        ),
                        Communication.type == CommunicationType.EMAIL,
                        func.date(Communication.sent_at) == yesterday
                    )
                ).all()

                if not emails:
                    continue

                # Calculate metrics
                total_sent = len(emails)
                total_delivered = sum(1 for e in emails if e.bounced_at is None)
                total_bounced = sum(1 for e in emails if e.bounced_at is not None)
                total_opened = sum(1 for e in emails if e.opened_at is not None)
                total_clicked = sum(1 for e in emails if e.clicked_at is not None)

                bounce_rate = total_bounced / total_sent if total_sent > 0 else 0
                open_rate = total_opened / total_delivered if total_delivered > 0 else 0
                click_rate = total_clicked / total_delivered if total_delivered > 0 else 0

                # Determine domain warmup status
                warmup_status = _calculate_warmup_status(team, bounce_rate, total_sent)

                # Create metrics record
                metrics = DeliverabilityMetrics(
                    team_id=team.id,
                    date=yesterday,
                    emails_sent=total_sent,
                    emails_delivered=total_delivered,
                    emails_bounced=total_bounced,
                    emails_opened=total_opened,
                    emails_clicked=total_clicked,
                    bounce_rate=bounce_rate,
                    open_rate=open_rate,
                    click_rate=click_rate,
                    domain_warmup_status=warmup_status,
                    suppression_list_size=0  # TODO: Get from SendGrid API
                )
                db.add(metrics)

                results["metrics_created"] += 1
                results["teams_processed"] += 1

                logger.info(f"Team {team.id}: bounce_rate={bounce_rate:.2%}, open_rate={open_rate:.2%}")

            except Exception as e:
                logger.error(f"Failed to update metrics for team {team.id}: {str(e)}")

        db.commit()

        logger.info(f"Deliverability metrics updated: {results['metrics_created']} records created")

        return results


def _calculate_warmup_status(team: Team, bounce_rate: float, daily_volume: int) -> str:
    """
    Calculate domain warmup status

    Warmup phases:
    - cold: < 100 emails/day, < 7 days old
    - warming: 100-500 emails/day, bounce rate < 3%
    - warm: > 500 emails/day, bounce rate < 2%
    - hot: > 1000 emails/day, bounce rate < 1%
    """
    if daily_volume < 100 or bounce_rate > 0.05:
        return "cold"
    elif daily_volume < 500 or bounce_rate > 0.03:
        return "warming"
    elif daily_volume < 1000 or bounce_rate > 0.02:
        return "warm"
    else:
        return "hot"


# ============================================================================
# PORTFOLIO METRICS
# ============================================================================

@celery_app.task(bind=True, name="api.tasks.maintenance_tasks.refresh_portfolio_metrics")
def refresh_portfolio_metrics(self) -> Dict[str, Any]:
    """
    Refresh portfolio-level metrics for all teams

    Runs daily at 3:00 AM via Celery Beat

    Updates:
    - Pipeline stage distribution
    - Average deal size
    - Close rate
    - Time in pipeline
    - Top performers
    """
    logger.info("Refreshing portfolio metrics")

    with next(get_db_session()) as db:
        from db.models import PropertyStage, Deal, DealStatus

        teams = db.query(Team).all()

        results = {
            "teams_processed": 0,
            "metrics_updated": 0
        }

        for team in teams:
            try:
                # Get all properties for team
                properties = db.query(Property).filter(Property.team_id == team.id).all()

                if not properties:
                    continue

                # Calculate stage distribution
                stage_counts = {}
                for stage in PropertyStage:
                    count = sum(1 for p in properties if p.current_stage == stage)
                    stage_counts[stage.value] = count

                # Calculate deal metrics
                deals = db.query(Deal).join(Property).filter(
                    Property.team_id == team.id
                ).all()

                total_deals = len(deals)
                closed_deals = sum(1 for d in deals if d.status == DealStatus.CLOSED)
                close_rate = closed_deals / total_deals if total_deals > 0 else 0

                avg_deal_size = sum(d.offer_price or 0 for d in deals) / total_deals if total_deals > 0 else 0

                # Store in team metadata (or create separate PortfolioMetrics table)
                team.metadata = team.metadata or {}
                team.metadata["portfolio_metrics"] = {
                    "stage_distribution": stage_counts,
                    "total_properties": len(properties),
                    "total_deals": total_deals,
                    "close_rate": close_rate,
                    "avg_deal_size": avg_deal_size,
                    "last_updated": datetime.utcnow().isoformat()
                }

                results["metrics_updated"] += 1
                results["teams_processed"] += 1

                logger.info(f"Team {team.id}: {len(properties)} properties, {close_rate:.2%} close rate")

            except Exception as e:
                logger.error(f"Failed to refresh metrics for team {team.id}: {str(e)}")

        db.commit()

        logger.info(f"Portfolio metrics refreshed for {results['teams_processed']} teams")

        return results


# ============================================================================
# BUDGET ALERTS
# ============================================================================

@celery_app.task(bind=True, name="api.tasks.maintenance_tasks.check_budget_alerts")
def check_budget_alerts(self) -> Dict[str, Any]:
    """
    Check for budget threshold alerts

    Runs every hour via Celery Beat

    Alerts when:
    - Team reaches 80% of monthly budget cap
    - Team exceeds monthly budget cap
    """
    logger.info("Checking budget alerts")

    with next(get_db_session()) as db:
        teams = db.query(Team).all()

        results = {
            "teams_checked": 0,
            "alerts_sent": 0
        }

        # Get current month's budget spending
        current_month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        for team in teams:
            try:
                # Calculate current month spending
                budget_records = db.query(BudgetTracking).filter(
                    and_(
                        BudgetTracking.team_id == team.id,
                        BudgetTracking.date >= current_month_start.date()
                    )
                ).all()

                total_spent = sum(b.cost for b in budget_records)
                budget_cap = team.monthly_budget_cap or 500.0

                budget_percentage = total_spent / budget_cap if budget_cap > 0 else 0

                # Check thresholds
                if budget_percentage >= 1.0:
                    _send_budget_alert(team, "exceeded", total_spent, budget_cap)
                    results["alerts_sent"] += 1

                elif budget_percentage >= 0.8:
                    _send_budget_alert(team, "warning", total_spent, budget_cap)
                    results["alerts_sent"] += 1

                results["teams_checked"] += 1

            except Exception as e:
                logger.error(f"Failed to check budget for team {team.id}: {str(e)}")

        logger.info(f"Budget alerts checked: {results['alerts_sent']} alerts sent")

        return results


def _send_budget_alert(team: Team, alert_type: str, spent: float, cap: float):
    """
    Send budget alert to team admins

    In production, this would:
    - Email team admins
    - Create in-app notification
    - Log to monitoring system
    """
    logger.warning(f"Budget alert for team {team.id}: {alert_type} - ${spent:.2f} / ${cap:.2f}")

    # TODO: Implement actual alert sending
    # - Query for team admins
    # - Send email via SendGrid
    # - Create notification record


# ============================================================================
# CLEANUP TASKS
# ============================================================================

@celery_app.task(bind=True, name="api.tasks.maintenance_tasks.cleanup_expired_share_links")
def cleanup_expired_share_links(self) -> Dict[str, Any]:
    """
    Mark expired share links as expired

    Runs every 6 hours via Celery Beat
    """
    logger.info("Cleaning up expired share links")

    with next(get_db_session()) as db:
        now = datetime.utcnow()

        # Find expired links
        expired_links = db.query(ShareLink).filter(
            and_(
                ShareLink.status == ShareLinkStatus.ACTIVE,
                ShareLink.expires_at < now
            )
        ).all()

        results = {
            "expired_count": len(expired_links)
        }

        for link in expired_links:
            link.status = ShareLinkStatus.EXPIRED

        db.commit()

        logger.info(f"Marked {len(expired_links)} share links as expired")

        return results


@celery_app.task(bind=True, name="api.tasks.maintenance_tasks.archive_old_properties")
def archive_old_properties(self, days_inactive: int = 180) -> Dict[str, Any]:
    """
    Archive properties that have been inactive for X days

    Args:
        days_inactive: Days of inactivity before archiving (default: 180)

    Returns:
        Dict with archive results
    """
    logger.info(f"Archiving properties inactive for {days_inactive} days")

    with next(get_db_session()) as db:
        from db.models import PropertyStage

        cutoff_date = datetime.utcnow() - timedelta(days=days_inactive)

        # Find properties to archive
        inactive_properties = db.query(Property).filter(
            and_(
                Property.current_stage.notin_([
                    PropertyStage.CLOSED_WON,
                    PropertyStage.CLOSED_LOST,
                    PropertyStage.ARCHIVED
                ]),
                Property.updated_at < cutoff_date,
                Property.touch_count == 0
            )
        ).all()

        results = {
            "archived_count": len(inactive_properties)
        }

        for property in inactive_properties:
            property.current_stage = PropertyStage.ARCHIVED
            property.archived_at = datetime.utcnow()

        db.commit()

        logger.info(f"Archived {len(inactive_properties)} inactive properties")

        return results


# ============================================================================
# DLQ MONITORING
# ============================================================================

@celery_app.task(bind=True, name="api.tasks.maintenance_tasks.check_dlq_alerts")
def check_dlq_alerts(self) -> Dict[str, Any]:
    """
    Check DLQ for failed tasks and send alerts

    Runs every 5 minutes via Celery Beat

    Alert conditions:
    - DLQ depth > 0 for > 5 minutes
    - Alert clears when DLQ is empty or all tasks replayed

    Returns:
        Dict with alert status
    """
    logger.info("Checking DLQ alerts")

    with next(get_db_session()) as db:
        from api.dlq import check_dlq_alerts as check_dlq

        alert = check_dlq(db)

        if alert:
            # Alert should fire
            logger.warning(
                f"DLQ ALERT: {alert['message']}",
                extra={
                    "total_failed": alert["total_failed"],
                    "oldest_failure": alert["oldest_failure"],
                    "time_since_oldest_minutes": alert["time_since_oldest_minutes"],
                    "by_queue": alert["by_queue"]
                }
            )

            # TODO: Send alert to monitoring system
            # - Post to Slack/Discord
            # - Create PagerDuty incident
            # - Email admins
            # - Grafana alert annotation

            return {
                "alert_triggered": True,
                "alert_data": alert
            }
        else:
            logger.debug("DLQ is healthy - no alerts")

            return {
                "alert_triggered": False,
                "message": "DLQ is healthy"
            }


@celery_app.task(bind=True, name="api.tasks.maintenance_tasks.cleanup_idempotency_keys")
def cleanup_idempotency_keys(self) -> Dict[str, Any]:
    """
    Clean up expired idempotency keys

    Runs daily at 4:00 AM via Celery Beat

    Removes idempotency keys that have exceeded their TTL (24 hours default)

    Returns:
        Dict with cleanup results
    """
    logger.info("Cleaning up expired idempotency keys")

    with next(get_db_session()) as db:
        from api.idempotency import cleanup_expired_idempotency_keys

        deleted_count = cleanup_expired_idempotency_keys(db)

        logger.info(f"Cleaned up {deleted_count} expired idempotency keys")

        return {
            "deleted_count": deleted_count,
            "timestamp": datetime.utcnow().isoformat()
        }

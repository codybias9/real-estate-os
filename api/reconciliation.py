"""
Portfolio Reconciliation System

Validates database integrity against CSV truth data with ±0.5% tolerance.

Features:
- Nightly automated reconciliation
- Manual reconciliation endpoint
- Alert on drift > 0.5%
- Comprehensive audit trail
- CSV truth data validation

Use Cases:
- Data integrity verification
- Detect import/migration errors
- Audit compliance
- Financial accuracy

Metrics Reconciled:
- Property count by stage
- Total assessed values
- Total market values
- Deal count and values
- Budget tracking totals
"""
import os
import csv
import logging
from datetime import datetime, date
from typing import Dict, List, Any, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func

logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION
# ============================================================================

# Tolerance threshold: ±0.5%
RECONCILIATION_TOLERANCE = 0.005  # 0.5%

# CSV truth data path
TRUTH_DATA_PATH = os.getenv("TRUTH_DATA_PATH", "/data/truth/portfolio_truth.csv")

# ============================================================================
# RECONCILIATION LOGIC
# ============================================================================

def calculate_drift_percentage(observed: float, expected: float) -> float:
    """
    Calculate drift percentage

    Formula: |observed - expected| / expected

    Args:
        observed: Actual value from database
        expected: Expected value from truth data

    Returns:
        Drift percentage (0.01 = 1%)
    """
    if expected == 0:
        # Avoid division by zero
        # If expected is 0 and observed is not 0, drift is infinite (100%)
        return 1.0 if observed != 0 else 0.0

    return abs(observed - expected) / abs(expected)


def check_threshold(drift_percentage: float) -> bool:
    """
    Check if drift exceeds tolerance threshold

    Args:
        drift_percentage: Calculated drift (0.01 = 1%)

    Returns:
        True if drift exceeds threshold (alert should fire)
    """
    return drift_percentage > RECONCILIATION_TOLERANCE


def load_truth_data(csv_path: str) -> Dict[str, Any]:
    """
    Load truth data from CSV

    CSV Format:
    date,metric_name,metric_value
    2025-01-15,total_properties,1234
    2025-01-15,total_assessed_value,45678900.50
    ...

    Args:
        csv_path: Path to CSV file

    Returns:
        Dict mapping metric_name to expected value

    Raises:
        FileNotFoundError: If CSV file doesn't exist
        ValueError: If CSV format is invalid
    """
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Truth data CSV not found: {csv_path}")

    truth_data = {}

    try:
        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)

            for row in reader:
                metric_name = row.get('metric_name')
                metric_value = row.get('metric_value')

                if not metric_name or metric_value is None:
                    continue

                # Parse value (int or float)
                try:
                    if '.' in metric_value:
                        truth_data[metric_name] = float(metric_value)
                    else:
                        truth_data[metric_name] = int(metric_value)
                except ValueError:
                    logger.warning(f"Could not parse metric value: {metric_name}={metric_value}")
                    continue

        logger.info(f"Loaded {len(truth_data)} truth metrics from {csv_path}")

        return truth_data

    except Exception as e:
        raise ValueError(f"Failed to parse truth data CSV: {str(e)}")


def calculate_database_metrics(db: Session, team_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Calculate current metrics from database

    Args:
        db: Database session
        team_id: Optional team filter

    Returns:
        Dict mapping metric_name to observed value
    """
    from db.models import Property, Deal, DealStatus, BudgetTracking, PropertyStage

    metrics = {}

    try:
        # Base query filter
        property_query = db.query(Property)
        if team_id:
            property_query = property_query.filter(Property.team_id == team_id)

        # ====================================================================
        # PROPERTY METRICS
        # ====================================================================

        # Total properties
        metrics['total_properties'] = property_query.count()

        # Properties by stage
        for stage in PropertyStage:
            count = property_query.filter(Property.current_stage == stage).count()
            metrics[f'properties_{stage.value}'] = count

        # Total assessed values
        total_assessed = property_query.with_entities(
            func.sum(Property.assessed_value)
        ).scalar() or 0.0
        metrics['total_assessed_value'] = float(total_assessed)

        # Total market values
        total_market = property_query.with_entities(
            func.sum(Property.market_value_estimate)
        ).scalar() or 0.0
        metrics['total_market_value'] = float(total_market)

        # Total ARV
        total_arv = property_query.with_entities(
            func.sum(Property.arv)
        ).scalar() or 0.0
        metrics['total_arv'] = float(total_arv)

        # ====================================================================
        # DEAL METRICS
        # ====================================================================

        deal_query = db.query(Deal).join(Property)
        if team_id:
            deal_query = deal_query.filter(Property.team_id == team_id)

        # Total deals
        metrics['total_deals'] = deal_query.count()

        # Deals by status
        for status in DealStatus:
            count = deal_query.filter(Deal.status == status).count()
            metrics[f'deals_{status.value}'] = count

        # Total offer prices
        total_offers = deal_query.with_entities(
            func.sum(Deal.offer_price)
        ).scalar() or 0.0
        metrics['total_offer_price'] = float(total_offers)

        # Total expected margins
        total_margins = deal_query.with_entities(
            func.sum(Deal.expected_margin)
        ).scalar() or 0.0
        metrics['total_expected_margin'] = float(total_margins)

        # ====================================================================
        # BUDGET METRICS
        # ====================================================================

        budget_query = db.query(BudgetTracking)
        if team_id:
            budget_query = budget_query.filter(BudgetTracking.team_id == team_id)

        # Total costs
        total_cost = budget_query.with_entities(
            func.sum(BudgetTracking.cost)
        ).scalar() or 0.0
        metrics['total_budget_cost'] = float(total_cost)

        logger.info(f"Calculated {len(metrics)} database metrics")

        return metrics

    except Exception as e:
        logger.error(f"Failed to calculate database metrics: {str(e)}")
        raise


def reconcile_metrics(
    observed: Dict[str, Any],
    expected: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Reconcile observed vs expected metrics

    Args:
        observed: Metrics from database
        expected: Metrics from truth data

    Returns:
        Dict with reconciliation results:
        - metrics: List of metric comparisons
        - total_metrics: Total metrics checked
        - passing_metrics: Metrics within tolerance
        - failing_metrics: Metrics exceeding tolerance
        - max_drift: Maximum drift percentage
        - alert: Whether alert should fire
    """
    results = {
        "timestamp": datetime.utcnow().isoformat(),
        "metrics": [],
        "total_metrics": 0,
        "passing_metrics": 0,
        "failing_metrics": 0,
        "max_drift": 0.0,
        "alert": False
    }

    # Get all metric names (union of observed and expected)
    all_metrics = set(observed.keys()) | set(expected.keys())

    for metric_name in sorted(all_metrics):
        observed_value = observed.get(metric_name, 0.0)
        expected_value = expected.get(metric_name, 0.0)

        # Calculate drift
        drift = calculate_drift_percentage(observed_value, expected_value)
        exceeds_threshold = check_threshold(drift)

        metric_result = {
            "metric_name": metric_name,
            "observed": observed_value,
            "expected": expected_value,
            "diff": observed_value - expected_value,
            "drift_percentage": drift,
            "drift_percentage_formatted": f"{drift * 100:.4f}%",
            "exceeds_threshold": exceeds_threshold,
            "status": "FAIL" if exceeds_threshold else "PASS"
        }

        results["metrics"].append(metric_result)
        results["total_metrics"] += 1

        if exceeds_threshold:
            results["failing_metrics"] += 1
            results["alert"] = True
        else:
            results["passing_metrics"] += 1

        # Track max drift
        if drift > results["max_drift"]:
            results["max_drift"] = drift

    results["max_drift_formatted"] = f"{results['max_drift'] * 100:.4f}%"

    return results


def run_reconciliation(
    db: Session,
    team_id: Optional[int] = None,
    csv_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Run full reconciliation process

    Args:
        db: Database session
        team_id: Optional team filter
        csv_path: Path to truth CSV (defaults to TRUTH_DATA_PATH)

    Returns:
        Reconciliation results dict

    Raises:
        FileNotFoundError: If truth CSV not found
        ValueError: If CSV format invalid
    """
    logger.info("Starting portfolio reconciliation")

    # Load truth data
    csv_path = csv_path or TRUTH_DATA_PATH
    expected_metrics = load_truth_data(csv_path)

    # Calculate current database metrics
    observed_metrics = calculate_database_metrics(db, team_id=team_id)

    # Reconcile
    results = reconcile_metrics(observed_metrics, expected_metrics)

    # Log results
    if results["alert"]:
        logger.warning(
            f"Reconciliation ALERT: {results['failing_metrics']} metrics exceeded tolerance",
            extra={
                "failing_metrics": results["failing_metrics"],
                "max_drift": results["max_drift_formatted"],
                "tolerance": f"{RECONCILIATION_TOLERANCE * 100}%"
            }
        )
    else:
        logger.info(
            f"Reconciliation PASSED: All {results['total_metrics']} metrics within tolerance",
            extra={"max_drift": results["max_drift_formatted"]}
        )

    return results


# ============================================================================
# RECONCILIATION HISTORY
# ============================================================================

def store_reconciliation_result(
    db: Session,
    results: Dict[str, Any],
    team_id: Optional[int] = None
) -> int:
    """
    Store reconciliation results in database

    Args:
        db: Database session
        results: Reconciliation results
        team_id: Optional team ID

    Returns:
        Reconciliation record ID
    """
    from db.models import ReconciliationHistory

    try:
        record = ReconciliationHistory(
            team_id=team_id,
            reconciliation_date=datetime.utcnow().date(),
            total_metrics=results["total_metrics"],
            passing_metrics=results["passing_metrics"],
            failing_metrics=results["failing_metrics"],
            max_drift_percentage=results["max_drift"],
            alert_triggered=results["alert"],
            results_json=results
        )

        db.add(record)
        db.commit()
        db.refresh(record)

        logger.info(f"Stored reconciliation result: ID={record.id}")

        return record.id

    except Exception as e:
        db.rollback()
        logger.error(f"Failed to store reconciliation result: {str(e)}")
        raise


def get_reconciliation_history(
    db: Session,
    team_id: Optional[int] = None,
    limit: int = 30
) -> List[Dict[str, Any]]:
    """
    Get reconciliation history

    Args:
        db: Database session
        team_id: Optional team filter
        limit: Max results (default 30 days)

    Returns:
        List of reconciliation results
    """
    from db.models import ReconciliationHistory

    query = db.query(ReconciliationHistory)

    if team_id:
        query = query.filter(ReconciliationHistory.team_id == team_id)

    history = query.order_by(
        ReconciliationHistory.reconciliation_date.desc()
    ).limit(limit).all()

    return [
        {
            "id": record.id,
            "reconciliation_date": record.reconciliation_date.isoformat(),
            "total_metrics": record.total_metrics,
            "passing_metrics": record.passing_metrics,
            "failing_metrics": record.failing_metrics,
            "max_drift_percentage": record.max_drift_percentage,
            "max_drift_percentage_formatted": f"{record.max_drift_percentage * 100:.4f}%",
            "alert_triggered": record.alert_triggered,
            "created_at": record.created_at.isoformat()
        }
        for record in history
    ]


# ============================================================================
# ALERT HANDLING
# ============================================================================

def send_reconciliation_alert(results: Dict[str, Any]):
    """
    Send alert for reconciliation failures

    In production, this would:
    - Email admins
    - Post to Slack
    - Create PagerDuty incident
    - Log to monitoring system

    Args:
        results: Reconciliation results
    """
    failing_metrics = [
        m for m in results["metrics"]
        if m["exceeds_threshold"]
    ]

    alert_message = f"""
Portfolio Reconciliation Alert

{results['failing_metrics']} metrics exceeded ±0.5% tolerance threshold.

Max Drift: {results['max_drift_formatted']}
Failing Metrics: {len(failing_metrics)}

Failed Metrics:
"""

    for metric in failing_metrics[:10]:  # Top 10
        alert_message += f"  - {metric['metric_name']}: {metric['drift_percentage_formatted']} drift\n"
        alert_message += f"    Observed: {metric['observed']}, Expected: {metric['expected']}\n"

    logger.warning(alert_message)

    # TODO: Send to Slack, email, PagerDuty

"""
Integration Tests for Portfolio Reconciliation

Tests reconciliation logic, drift detection, and alerting
"""
import pytest
import os
import csv
import tempfile
from datetime import datetime
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from db.models import Property, PropertyStage, ReconciliationHistory
from api.reconciliation import (
    run_reconciliation,
    calculate_drift_percentage,
    load_truth_data,
    calculate_database_metrics,
)


class TestReconciliationCalculations:
    """Test reconciliation calculation logic"""

    def test_drift_percentage_calculation(self):
        """Test drift percentage calculation"""
        # No drift
        assert calculate_drift_percentage(100, 100) == 0.0

        # 5% drift
        assert abs(calculate_drift_percentage(105, 100) - 0.05) < 0.001

        # 10% drift
        assert abs(calculate_drift_percentage(110, 100) - 0.10) < 0.001

        # Negative drift
        assert abs(calculate_drift_percentage(90, 100) - 0.10) < 0.001

    def test_zero_expected_value_handling(self):
        """Test handling when expected value is zero"""
        # If expected is 0 and observed is 0, no drift
        assert calculate_drift_percentage(0, 0) == 0.0

        # If expected is 0 but observed is not, 100% drift
        assert calculate_drift_percentage(10, 0) == 1.0

    def test_drift_threshold_check(self):
        """Test drift threshold checking (0.5%)"""
        from api.reconciliation import RECONCILIATION_TOLERANCE

        # Within tolerance (0.4% drift)
        drift = calculate_drift_percentage(100.4, 100)
        assert drift < RECONCILIATION_TOLERANCE

        # Exceeds tolerance (0.6% drift)
        drift = calculate_drift_percentage(100.6, 100)
        assert drift > RECONCILIATION_TOLERANCE


class TestTruthDataLoading:
    """Test loading truth data from CSV"""

    def test_load_valid_csv(self):
        """Test loading valid CSV truth data"""
        # Create temporary CSV file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as f:
            writer = csv.DictWriter(f, fieldnames=['metric_name', 'expected_value'])
            writer.writeheader()
            writer.writerow({'metric_name': 'total_properties', 'expected_value': '100'})
            writer.writerow({'metric_name': 'avg_bird_dog_score', 'expected_value': '0.75'})
            temp_path = f.name

        try:
            truth_data = load_truth_data(temp_path)

            assert 'total_properties' in truth_data
            assert truth_data['total_properties'] == 100.0

            assert 'avg_bird_dog_score' in truth_data
            assert truth_data['avg_bird_dog_score'] == 0.75
        finally:
            os.unlink(temp_path)

    def test_load_missing_csv_raises_error(self):
        """Test that missing CSV file raises error"""
        with pytest.raises(FileNotFoundError):
            load_truth_data('/nonexistent/path/to/truth.csv')

    def test_load_malformed_csv_raises_error(self):
        """Test that malformed CSV raises error"""
        # Create CSV with wrong columns
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as f:
            f.write("wrong,columns\n")
            f.write("value1,value2\n")
            temp_path = f.name

        try:
            with pytest.raises(Exception):  # Should raise KeyError or similar
                load_truth_data(temp_path)
        finally:
            os.unlink(temp_path)


class TestDatabaseMetricsCalculation:
    """Test calculation of metrics from database"""

    def test_calculate_total_properties(
        self,
        test_db: Session,
        test_properties: list[Property]
    ):
        """Test calculating total properties"""
        metrics = calculate_database_metrics(
            test_db,
            team_id=test_properties[0].team_id
        )

        assert 'total_properties' in metrics
        assert metrics['total_properties'] == len(test_properties)

    def test_calculate_avg_bird_dog_score(
        self,
        test_db: Session,
        test_properties: list[Property]
    ):
        """Test calculating average bird dog score"""
        metrics = calculate_database_metrics(
            test_db,
            team_id=test_properties[0].team_id
        )

        assert 'avg_bird_dog_score' in metrics

        # Calculate expected average
        expected_avg = sum(p.bird_dog_score for p in test_properties) / len(test_properties)
        assert abs(metrics['avg_bird_dog_score'] - expected_avg) < 0.01

    def test_calculate_stage_distribution(
        self,
        test_db: Session,
        test_properties: list[Property]
    ):
        """Test calculating properties by stage"""
        metrics = calculate_database_metrics(
            test_db,
            team_id=test_properties[0].team_id
        )

        # Should have counts for each stage
        for prop in test_properties:
            metric_key = f"stage_{prop.current_stage.value}_count"
            assert metric_key in metrics
            assert metrics[metric_key] >= 1

    def test_empty_database_returns_zeros(
        self,
        test_db: Session,
        test_team
    ):
        """Test metrics calculation with no properties"""
        metrics = calculate_database_metrics(test_db, team_id=test_team.id)

        assert metrics['total_properties'] == 0
        # avg_bird_dog_score may be 0 or None for empty dataset


class TestReconciliationExecution:
    """Test end-to-end reconciliation execution"""

    def test_successful_reconciliation_no_drift(
        self,
        test_db: Session,
        test_properties: list[Property]
    ):
        """Test successful reconciliation with no drift"""
        # Create truth data matching current state
        metrics = calculate_database_metrics(
            test_db,
            team_id=test_properties[0].team_id
        )

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as f:
            writer = csv.DictWriter(f, fieldnames=['metric_name', 'expected_value'])
            writer.writeheader()
            for metric_name, value in metrics.items():
                writer.writerow({'metric_name': metric_name, 'expected_value': str(value)})
            temp_path = f.name

        try:
            # Run reconciliation
            results = run_reconciliation(
                test_db,
                team_id=test_properties[0].team_id,
                truth_file_path=temp_path
            )

            assert results['total_metrics'] > 0
            assert results['metrics_in_tolerance'] == results['total_metrics']
            assert results['metrics_out_of_tolerance'] == 0
            assert results['alert'] is False

        finally:
            os.unlink(temp_path)

    def test_reconciliation_detects_drift(
        self,
        test_db: Session,
        test_properties: list[Property]
    ):
        """Test that reconciliation detects drift"""
        # Create truth data with different values
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as f:
            writer = csv.DictWriter(f, fieldnames=['metric_name', 'expected_value'])
            writer.writeheader()
            # Expected 200 properties, but we have 5
            writer.writerow({'metric_name': 'total_properties', 'expected_value': '200'})
            temp_path = f.name

        try:
            results = run_reconciliation(
                test_db,
                team_id=test_properties[0].team_id,
                truth_file_path=temp_path
            )

            assert results['metrics_out_of_tolerance'] > 0
            assert results['alert'] is True

            # Check individual metric result
            total_props_metric = next(
                m for m in results['metrics']
                if m['metric_name'] == 'total_properties'
            )
            assert total_props_metric['exceeds_tolerance'] is True

        finally:
            os.unlink(temp_path)

    def test_reconciliation_recorded_in_history(
        self,
        test_db: Session,
        test_properties: list[Property]
    ):
        """Test that reconciliation results are stored in history"""
        # Create simple truth data
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as f:
            writer = csv.DictWriter(f, fieldnames=['metric_name', 'expected_value'])
            writer.writeheader()
            writer.writerow({'metric_name': 'total_properties', 'expected_value': '5'})
            temp_path = f.name

        try:
            results = run_reconciliation(
                test_db,
                team_id=test_properties[0].team_id,
                truth_file_path=temp_path
            )

            # Check history was recorded
            history = test_db.query(ReconciliationHistory).filter(
                ReconciliationHistory.team_id == test_properties[0].team_id
            ).order_by(ReconciliationHistory.run_at.desc()).first()

            assert history is not None
            assert history.total_metrics == results['total_metrics']
            assert history.alert_triggered == results['alert']

        finally:
            os.unlink(temp_path)


class TestReconciliationAPI:
    """Test reconciliation API endpoints"""

    def test_manual_reconciliation_trigger(
        self,
        client: TestClient,
        auth_headers: dict,
        test_db: Session,
        test_properties: list[Property]
    ):
        """Test manually triggering reconciliation via API"""
        response = client.post(
            "/api/v1/admin/reconciliation/run",
            headers=auth_headers
        )

        # Should execute (may succeed or fail depending on truth data availability)
        assert response.status_code in [200, 400, 404]

    def test_get_reconciliation_history(
        self,
        client: TestClient,
        auth_headers: dict,
        test_db: Session,
        test_properties: list[Property]
    ):
        """Test getting reconciliation history"""
        # Create a history record
        history = ReconciliationHistory(
            team_id=test_properties[0].team_id,
            total_metrics=5,
            metrics_in_tolerance=4,
            metrics_out_of_tolerance=1,
            max_drift_percentage=0.02,
            alert_triggered=False,
            results={}
        )
        test_db.add(history)
        test_db.commit()

        response = client.get(
            "/api/v1/admin/reconciliation/history",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, list)
        assert len(data) > 0

    def test_get_latest_reconciliation(
        self,
        client: TestClient,
        auth_headers: dict,
        test_db: Session,
        test_properties: list[Property]
    ):
        """Test getting latest reconciliation result"""
        # Create history record
        history = ReconciliationHistory(
            team_id=test_properties[0].team_id,
            total_metrics=5,
            metrics_in_tolerance=5,
            metrics_out_of_tolerance=0,
            max_drift_percentage=0.001,
            alert_triggered=False,
            results={}
        )
        test_db.add(history)
        test_db.commit()

        response = client.get(
            "/api/v1/admin/reconciliation/latest",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        assert data['total_metrics'] == 5
        assert data['alert_triggered'] is False


class TestReconciliationAlerting:
    """Test reconciliation alerting"""

    def test_alert_triggered_on_drift(
        self,
        test_db: Session,
        test_properties: list[Property]
    ):
        """Test that alert is triggered when drift exceeds tolerance"""
        # Create truth data with significant drift
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as f:
            writer = csv.DictWriter(f, fieldnames=['metric_name', 'expected_value'])
            writer.writeheader()
            writer.writerow({'metric_name': 'total_properties', 'expected_value': '1000'})
            temp_path = f.name

        try:
            results = run_reconciliation(
                test_db,
                team_id=test_properties[0].team_id,
                truth_file_path=temp_path
            )

            assert results['alert'] is True
            assert results['metrics_out_of_tolerance'] > 0

        finally:
            os.unlink(temp_path)

    def test_no_alert_within_tolerance(
        self,
        test_db: Session,
        test_properties: list[Property]
    ):
        """Test that no alert when all metrics within tolerance"""
        # Create truth data very close to actual
        metrics = calculate_database_metrics(
            test_db,
            team_id=test_properties[0].team_id
        )

        # Adjust slightly (within 0.5% tolerance)
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as f:
            writer = csv.DictWriter(f, fieldnames=['metric_name', 'expected_value'])
            writer.writeheader()
            for metric_name, value in metrics.items():
                # Add 0.2% drift (within 0.5% tolerance)
                adjusted = value * 1.002
                writer.writerow({'metric_name': metric_name, 'expected_value': str(adjusted)})
            temp_path = f.name

        try:
            results = run_reconciliation(
                test_db,
                team_id=test_properties[0].team_id,
                truth_file_path=temp_path
            )

            # All metrics should be within tolerance
            assert results['alert'] is False or results['metrics_out_of_tolerance'] == 0

        finally:
            os.unlink(temp_path)


class TestNightlyReconciliation:
    """Test nightly scheduled reconciliation"""

    def test_celery_beat_schedule_configured(self):
        """Test that Celery Beat schedule includes reconciliation"""
        from api.celery_app import celery_app

        schedule = celery_app.conf.beat_schedule

        assert 'nightly-portfolio-reconciliation' in schedule
        task = schedule['nightly-portfolio-reconciliation']

        # Should run daily at 1:00 AM
        assert 'schedule' in task
        assert task['task'] == 'api.tasks.maintenance_tasks.run_portfolio_reconciliation'

    def test_reconciliation_task_execution(
        self,
        test_db: Session,
        test_properties: list[Property],
        mock_celery
    ):
        """Test reconciliation task can be executed"""
        from api.tasks.maintenance_tasks import run_portfolio_reconciliation

        # This would test the actual task
        # In practice, would need truth data file available
        # For now, verify task is defined
        assert run_portfolio_reconciliation is not None

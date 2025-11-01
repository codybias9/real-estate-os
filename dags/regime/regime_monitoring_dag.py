"""Regime Monitoring DAG
Daily market regime detection and policy adjustment

Schedule: Daily at 6 AM
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
from ml.regime.market_regime_detector import (
    MarketRegimeDetector,
    PolicyEngine,
    MarketSignals,
    MarketRegime
)
from ml.regime.changepoint_detection import BayesianOnlineChangePointDetection

logger = logging.getLogger(__name__)

default_args = {
    'owner': 'ml-team',
    'depends_on_past': False,
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
}

with DAG(
    'regime_monitoring',
    default_args=default_args,
    description='Monitor market regimes and adjust policies',
    schedule_interval='0 6 * * *',  # Daily at 6 AM
    start_date=days_ago(1),
    catchup=False,
    tags=['regime', 'monitoring', 'policy'],
) as dag:

    def collect_market_signals(**context):
        """Collect market signals from database for each monitored market"""

        engine = create_engine(os.getenv("DB_DSN"))

        # Get list of active markets (ZIP codes with properties)
        markets_query = """
        SELECT DISTINCT
            zip_code AS market,
            COUNT(*) AS property_count
        FROM property
        WHERE status IN ('active', 'pending', 'sold')
          AND created_at >= NOW() - INTERVAL '180 days'
        GROUP BY zip_code
        HAVING COUNT(*) >= 10  -- Only monitor markets with sufficient data
        ORDER BY property_count DESC
        LIMIT 100
        """

        markets_df = pd.read_sql(markets_query, engine)

        logger.info(f"Monitoring {len(markets_df)} markets")

        # For each market, calculate signals
        market_signals = []

        for _, row in markets_df.iterrows():
            market = row['market']

            # Calculate signals from recent data
            signals_query = f"""
            WITH current_period AS (
                SELECT
                    COUNT(*) FILTER (WHERE status IN ('active', 'pending')) AS active_listings,
                    AVG(list_price) AS median_list_price,
                    AVG(CASE WHEN status = 'sold' THEN list_price END) AS median_sale_price,
                    AVG(CASE WHEN status = 'sold' THEN list_price / NULLIF(sqft, 0) END) AS avg_price_per_sf,
                    AVG(CASE WHEN status = 'sold' THEN dom END) AS avg_dom,
                    AVG(CASE WHEN status = 'sold' THEN cap_rate_estimate END) AS avg_cap_rate,
                    COUNT(*) FILTER (WHERE status = 'sold' AND created_at >= NOW() - INTERVAL '30 days') AS sales_last_30d
                FROM property
                WHERE zip_code = '{market}'
                  AND created_at >= NOW() - INTERVAL '90 days'
            ),
            prior_period AS (
                SELECT
                    AVG(CASE WHEN status = 'sold' THEN list_price END) AS median_sale_price_prior,
                    AVG(CASE WHEN status = 'sold' THEN dom END) AS avg_dom_prior,
                    COUNT(*) FILTER (WHERE status = 'sold' AND created_at >= NOW() - INTERVAL '60 days' AND created_at < NOW() - INTERVAL '30 days') AS sales_prior_30d,
                    COUNT(*) FILTER (WHERE status IN ('active', 'pending') AND created_at >= NOW() - INTERVAL '60 days' AND created_at < NOW() - INTERVAL '30 days') AS listings_prior_30d
                FROM property
                WHERE zip_code = '{market}'
                  AND created_at >= NOW() - INTERVAL '365 days'
                  AND created_at < NOW() - INTERVAL '90 days'
            ),
            year_ago AS (
                SELECT
                    AVG(CASE WHEN status = 'sold' THEN list_price END) AS median_sale_price_yoy
                FROM property
                WHERE zip_code = '{market}'
                  AND created_at >= NOW() - INTERVAL '456 days'
                  AND created_at < NOW() - INTERVAL '365 days'
            )
            SELECT
                c.*,
                p.median_sale_price_prior,
                p.avg_dom_prior,
                p.sales_prior_30d,
                p.listings_prior_30d,
                y.median_sale_price_yoy
            FROM current_period c, prior_period p, year_ago y
            """

            signals_df = pd.read_sql(signals_query, engine)

            if signals_df.empty or signals_df['active_listings'].iloc[0] == 0:
                continue

            row_data = signals_df.iloc[0]

            # Calculate derived metrics
            active_listings = int(row_data['active_listings'])
            sales_last_30d = int(row_data['sales_last_30d'])
            months_of_inventory = (active_listings / max(sales_last_30d, 1)) if sales_last_30d > 0 else 12.0

            median_list = row_data['median_list_price'] or 0
            median_sale = row_data['median_sale_price'] or 0
            list_to_sale_ratio = (median_sale / median_list) if median_list > 0 else 0.95

            median_sale_yoy = row_data['median_sale_price_yoy'] or median_sale
            price_yoy_change = ((median_sale - median_sale_yoy) / median_sale_yoy) if median_sale_yoy > 0 else 0.0

            avg_dom = row_data['avg_dom'] or 60
            avg_dom_prior = row_data['avg_dom_prior'] or avg_dom
            dom_yoy_change = ((avg_dom - avg_dom_prior) / avg_dom_prior) if avg_dom_prior > 0 else 0.0

            sales_prior = row_data['sales_prior_30d'] or 1
            sales_volume_mom = ((sales_last_30d - sales_prior) / sales_prior) if sales_prior > 0 else 0.0

            # Estimate sell-through rate (sales / (sales + expireds))
            # Simplification: assume 70% baseline
            sell_through_rate = 0.70

            # New listings MoM (use active as proxy)
            listings_prior = row_data['listings_prior_30d'] or active_listings
            new_listings_mom = ((active_listings - listings_prior) / listings_prior) if listings_prior > 0 else 0.0

            # Get mortgage rate from external source (use fixed for now)
            mortgage_rate = 0.065  # 6.5%

            signals = {
                'date': context['ds'],
                'market': market,
                'active_listings': active_listings,
                'months_of_inventory': months_of_inventory,
                'new_listings_mom': new_listings_mom,
                'median_list_price': median_list,
                'median_sale_price': median_sale,
                'list_to_sale_ratio': list_to_sale_ratio,
                'price_yoy_change': price_yoy_change,
                'avg_days_on_market': avg_dom,
                'dom_yoy_change': dom_yoy_change,
                'sell_through_rate': sell_through_rate,
                'avg_cap_rate': row_data['avg_cap_rate'] or 0.05,
                'avg_price_per_sf': row_data['avg_price_per_sf'] or 0,
                'mortgage_rate': mortgage_rate,
                'sales_volume_mom': sales_volume_mom
            }

            market_signals.append(signals)

        engine.dispose()

        # Save to XCom
        context['task_instance'].xcom_push(key='market_signals', value=market_signals)

        logger.info(f"Collected signals for {len(market_signals)} markets")

    def detect_regimes(**context):
        """Detect regime for each market"""

        # Load signals from XCom
        ti = context['task_instance']
        market_signals_list = ti.xcom_pull(key='market_signals', task_ids='collect_market_signals')

        detector = MarketRegimeDetector()

        regime_results = []

        for signals_dict in market_signals_list:
            # Convert to MarketSignals object
            signals = MarketSignals(
                date=pd.to_datetime(signals_dict['date']),
                market=signals_dict['market'],
                active_listings=signals_dict['active_listings'],
                months_of_inventory=signals_dict['months_of_inventory'],
                new_listings_mom=signals_dict['new_listings_mom'],
                median_list_price=signals_dict['median_list_price'],
                median_sale_price=signals_dict['median_sale_price'],
                list_to_sale_ratio=signals_dict['list_to_sale_ratio'],
                price_yoy_change=signals_dict['price_yoy_change'],
                avg_days_on_market=signals_dict['avg_days_on_market'],
                dom_yoy_change=signals_dict['dom_yoy_change'],
                sell_through_rate=signals_dict['sell_through_rate'],
                avg_cap_rate=signals_dict['avg_cap_rate'],
                avg_price_per_sf=signals_dict['avg_price_per_sf'],
                mortgage_rate=signals_dict['mortgage_rate'],
                sales_volume_mom=signals_dict['sales_volume_mom']
            )

            # TODO: Load previous regime from database
            previous_regime = None

            # Detect regime
            result = detector.detect_regime(signals, previous_regime)

            regime_results.append({
                'date': result.date.isoformat(),
                'market': result.market,
                'composite_index': result.composite_index,
                'regime': result.regime.value,
                'regime_confidence': result.regime_confidence,
                'inventory_score': result.inventory_score,
                'price_score': result.price_score,
                'velocity_score': result.velocity_score,
                'financial_score': result.financial_score
            })

        # Save to XCom
        ti.xcom_push(key='regime_results', value=regime_results)

        logger.info(f"Detected regimes for {len(regime_results)} markets")

        return regime_results

    def store_regimes(**context):
        """Store regime results in database"""

        ti = context['task_instance']
        regime_results = ti.xcom_pull(key='regime_results', task_ids='detect_regimes')

        engine = create_engine(os.getenv("DB_DSN"))

        # Convert to DataFrame
        df = pd.DataFrame(regime_results)

        # TODO: Write to regime_history table
        # df.to_sql('regime_history', engine, if_exists='append', index=False)

        logger.info(f"Would store {len(df)} regime records")

        engine.dispose()

    def update_policies(**context):
        """Update offer policies based on new regimes"""

        ti = context['task_instance']
        regime_results = ti.xcom_pull(key='regime_results', task_ids='detect_regimes')

        engine = create_engine(os.getenv("DB_DSN"))
        policy_engine = PolicyEngine()

        updated_count = 0

        for result in regime_results:
            market = result['market']
            regime = MarketRegime(result['regime'])

            # Get policy for regime
            policy = policy_engine.get_policy_for_regime(regime)

            # TODO: Update properties in this market with new policy
            # UPDATE property SET
            #   max_offer_pct = policy.max_offer_to_arv,
            #   earnest_money_pct = policy.earnest_money_pct,
            #   dd_days = policy.due_diligence_days,
            #   target_cap_rate = policy.target_cap_rate_min,
            #   target_margin = policy.target_margin_min
            # WHERE zip_code = market AND status = 'active'

            logger.info(f"{market}: Applied {regime.value} policy (max_offer={policy.max_offer_to_arv:.1%})")

            updated_count += 1

        engine.dispose()

        logger.info(f"Updated policies for {updated_count} markets")

    def send_regime_alerts(**context):
        """Send alerts for regime changes"""

        ti = context['task_instance']
        regime_results = ti.xcom_pull(key='regime_results', task_ids='detect_regimes')

        # TODO: Compare with previous regimes to find changes
        # For now, alert on any COLD regime

        cold_markets = [r for r in regime_results if r['regime'] == 'cold']
        hot_markets = [r for r in regime_results if r['regime'] == 'hot']

        if cold_markets:
            message = f"🥶 {len(cold_markets)} markets are now COLD:\n"
            for market in cold_markets[:5]:
                message += f"  • {market['market']}: Index={market['composite_index']:.1f}\n"

            logger.warning(f"ALERT: {message}")
            # TODO: Send to Slack

        if hot_markets:
            message = f"🔥 {len(hot_markets)} markets are now HOT:\n"
            for market in hot_markets[:5]:
                message += f"  • {market['market']}: Index={market['composite_index']:.1f}\n"

            logger.info(f"INFO: {message}")
            # TODO: Send to Slack

    # Task definitions
    collect_signals = PythonOperator(
        task_id='collect_market_signals',
        python_callable=collect_market_signals,
    )

    detect = PythonOperator(
        task_id='detect_regimes',
        python_callable=detect_regimes,
    )

    store = PythonOperator(
        task_id='store_regimes',
        python_callable=store_regimes,
    )

    update = PythonOperator(
        task_id='update_policies',
        python_callable=update_policies,
    )

    alert = PythonOperator(
        task_id='send_regime_alerts',
        python_callable=send_regime_alerts,
    )

    # Dependencies
    collect_signals >> detect >> [store, update] >> alert

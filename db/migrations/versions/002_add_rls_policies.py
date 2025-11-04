"""Add Row-Level Security policies for multi-tenant isolation

Revision ID: 002_add_rls_policies
Revises: 001_create_ux_features
Create Date: 2024-01-15 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '002_add_rls_policies'
down_revision = '001_create_ux_features'
branch_labels = None
depends_on = None


def upgrade():
    """
    Enable Row-Level Security on all multi-tenant tables

    RLS ensures users can only see/modify data from their own team
    """

    # Enable RLS on properties table
    op.execute("""
        ALTER TABLE properties ENABLE ROW LEVEL SECURITY;

        -- Policy: Users can only see properties from their team
        CREATE POLICY properties_team_isolation ON properties
            FOR ALL
            USING (team_id IN (
                SELECT team_id FROM users WHERE id = current_setting('app.current_user_id')::integer
            ));

        -- Policy: Users can only insert properties for their team
        CREATE POLICY properties_team_insert ON properties
            FOR INSERT
            WITH CHECK (team_id IN (
                SELECT team_id FROM users WHERE id = current_setting('app.current_user_id')::integer
            ));
    """)

    # Enable RLS on communications
    op.execute("""
        ALTER TABLE communications ENABLE ROW LEVEL SECURITY;

        CREATE POLICY communications_team_isolation ON communications
            FOR ALL
            USING (property_id IN (
                SELECT id FROM properties WHERE team_id IN (
                    SELECT team_id FROM users WHERE id = current_setting('app.current_user_id')::integer
                )
            ));
    """)

    # Enable RLS on templates
    op.execute("""
        ALTER TABLE templates ENABLE ROW LEVEL SECURITY;

        CREATE POLICY templates_team_isolation ON templates
            FOR ALL
            USING (team_id IN (
                SELECT team_id FROM users WHERE id = current_setting('app.current_user_id')::integer
            ));

        CREATE POLICY templates_team_insert ON templates
            FOR INSERT
            WITH CHECK (team_id IN (
                SELECT team_id FROM users WHERE id = current_setting('app.current_user_id')::integer
            ));
    """)

    # Enable RLS on tasks
    op.execute("""
        ALTER TABLE tasks ENABLE ROW LEVEL SECURITY;

        CREATE POLICY tasks_team_isolation ON tasks
            FOR ALL
            USING (property_id IN (
                SELECT id FROM properties WHERE team_id IN (
                    SELECT team_id FROM users WHERE id = current_setting('app.current_user_id')::integer
                )
            ));
    """)

    # Enable RLS on deals
    op.execute("""
        ALTER TABLE deals ENABLE ROW LEVEL SECURITY;

        CREATE POLICY deals_team_isolation ON deals
            FOR ALL
            USING (property_id IN (
                SELECT id FROM properties WHERE team_id IN (
                    SELECT team_id FROM users WHERE id = current_setting('app.current_user_id')::integer
                )
            ));
    """)

    # Enable RLS on share_links
    op.execute("""
        ALTER TABLE share_links ENABLE ROW LEVEL SECURITY;

        CREATE POLICY share_links_team_isolation ON share_links
            FOR ALL
            USING (created_by_user_id IN (
                SELECT id FROM users WHERE team_id IN (
                    SELECT team_id FROM users WHERE id = current_setting('app.current_user_id')::integer
                )
            ));
    """)

    # Enable RLS on deal_rooms
    op.execute("""
        ALTER TABLE deal_rooms ENABLE ROW LEVEL SECURITY;

        CREATE POLICY deal_rooms_team_isolation ON deal_rooms
            FOR ALL
            USING (property_id IN (
                SELECT id FROM properties WHERE team_id IN (
                    SELECT team_id FROM users WHERE id = current_setting('app.current_user_id')::integer
                )
            ));
    """)

    # Enable RLS on investors
    op.execute("""
        ALTER TABLE investors ENABLE ROW LEVEL SECURITY;

        CREATE POLICY investors_team_isolation ON investors
            FOR ALL
            USING (team_id IN (
                SELECT team_id FROM users WHERE id = current_setting('app.current_user_id')::integer
            ));

        CREATE POLICY investors_team_insert ON investors
            FOR INSERT
            WITH CHECK (team_id IN (
                SELECT team_id FROM users WHERE id = current_setting('app.current_user_id')::integer
            ));
    """)

    # Enable RLS on smart_lists
    op.execute("""
        ALTER TABLE smart_lists ENABLE ROW LEVEL SECURITY;

        CREATE POLICY smart_lists_team_isolation ON smart_lists
            FOR ALL
            USING (team_id IN (
                SELECT team_id FROM users WHERE id = current_setting('app.current_user_id')::integer
            ));

        CREATE POLICY smart_lists_team_insert ON smart_lists
            FOR INSERT
            WITH CHECK (team_id IN (
                SELECT team_id FROM users WHERE id = current_setting('app.current_user_id')::integer
            ));
    """)

    # Enable RLS on cadence_rules
    op.execute("""
        ALTER TABLE cadence_rules ENABLE ROW LEVEL SECURITY;

        CREATE POLICY cadence_rules_team_isolation ON cadence_rules
            FOR ALL
            USING (team_id IN (
                SELECT team_id FROM users WHERE id = current_setting('app.current_user_id')::integer
            ));

        CREATE POLICY cadence_rules_team_insert ON cadence_rules
            FOR INSERT
            WITH CHECK (team_id IN (
                SELECT team_id FROM users WHERE id = current_setting('app.current_user_id')::integer
            ));
    """)

    # Enable RLS on deliverability_metrics
    op.execute("""
        ALTER TABLE deliverability_metrics ENABLE ROW LEVEL SECURITY;

        CREATE POLICY deliverability_metrics_team_isolation ON deliverability_metrics
            FOR ALL
            USING (team_id IN (
                SELECT team_id FROM users WHERE id = current_setting('app.current_user_id')::integer
            ));
    """)

    # Enable RLS on budget_tracking
    op.execute("""
        ALTER TABLE budget_tracking ENABLE ROW LEVEL SECURITY;

        CREATE POLICY budget_tracking_team_isolation ON budget_tracking
            FOR ALL
            USING (team_id IN (
                SELECT team_id FROM users WHERE id = current_setting('app.current_user_id')::integer
            ));
    """)

    # Enable RLS on users table (users can see all users in their team)
    op.execute("""
        ALTER TABLE users ENABLE ROW LEVEL SECURITY;

        CREATE POLICY users_team_isolation ON users
            FOR ALL
            USING (team_id IN (
                SELECT team_id FROM users WHERE id = current_setting('app.current_user_id')::integer
            ));
    """)

    # Create helper function to set current user context
    op.execute("""
        CREATE OR REPLACE FUNCTION set_current_user_id(user_id INTEGER)
        RETURNS VOID AS $$
        BEGIN
            PERFORM set_config('app.current_user_id', user_id::text, false);
        END;
        $$ LANGUAGE plpgsql;
    """)


def downgrade():
    """Remove Row-Level Security policies"""

    # Drop helper function
    op.execute("DROP FUNCTION IF EXISTS set_current_user_id(INTEGER);")

    # Disable RLS on all tables
    tables = [
        'properties', 'communications', 'templates', 'tasks', 'deals',
        'share_links', 'deal_rooms', 'investors', 'smart_lists',
        'cadence_rules', 'deliverability_metrics', 'budget_tracking', 'users'
    ]

    for table in tables:
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;")
        op.execute(f"DROP POLICY IF EXISTS {table}_team_isolation ON {table};")
        op.execute(f"DROP POLICY IF EXISTS {table}_team_insert ON {table};")

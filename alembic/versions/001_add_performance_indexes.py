"""Add performance indexes

Revision ID: 001_add_performance_indexes
Revises: 
Create Date: 2024-12-30

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '001_add_performance_indexes'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Add indexes for transaction queries
    op.create_index(
        'idx_transactions_user_timestamp',
        'transactions',
        ['user_id', 'timestamp'],
        unique=False
    )
    op.create_index(
        'idx_transactions_timestamp',
        'transactions',
        ['timestamp'],
        unique=False
    )
    op.create_index(
        'idx_transactions_risk_score',
        'transactions',
        ['risk_score'],
        unique=False
    )
    op.create_index(
        'idx_transactions_category',
        'transactions',
        ['category'],
        unique=False
    )
    
    # Add indexes for portfolio queries
    op.create_index(
        'idx_portfolios_user_id',
        'portfolios',
        ['user_id'],
        unique=False
    )
    op.create_index(
        'idx_portfolios_last_updated',
        'portfolios',
        ['last_updated'],
        unique=False
    )
    
    # Add indexes for market data queries
    op.create_index(
        'idx_market_data_symbol_timestamp',
        'market_data',
        ['symbol', 'timestamp'],
        unique=False
    )
    op.create_index(
        'idx_market_data_timestamp',
        'market_data',
        ['timestamp'],
        unique=False
    )


def downgrade():
    # Remove indexes
    op.drop_index('idx_transactions_user_timestamp', table_name='transactions')
    op.drop_index('idx_transactions_timestamp', table_name='transactions')
    op.drop_index('idx_transactions_risk_score', table_name='transactions')
    op.drop_index('idx_transactions_category', table_name='transactions')
    op.drop_index('idx_portfolios_user_id', table_name='portfolios')
    op.drop_index('idx_portfolios_last_updated', table_name='portfolios')
    op.drop_index('idx_market_data_symbol_timestamp', table_name='market_data')
    op.drop_index('idx_market_data_timestamp', table_name='market_data')


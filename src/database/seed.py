"""
Seed database with realistic sample data
"""
import random
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from src.database.connection import database, Base
from src.database.models import Transaction, Portfolio, MarketData
from src.config.settings import settings


# Sample data constants
CURRENCIES = ["USD", "EUR", "GBP", "JPY", "CAD", "AUD"]
TRANSACTION_CATEGORIES = [
    "Stock Purchase", "Stock Sale", "Dividend", "Interest", "Fee",
    "Transfer", "Withdrawal", "Deposit", "Options Trade", "Bond Purchase",
    "Mutual Fund", "ETF", "Crypto", "Forex", "Commodities"
]

STOCK_SYMBOLS = [
    "AAPL", "GOOGL", "MSFT", "AMZN", "TSLA", "META", "NVDA", "JPM",
    "V", "JNJ", "WMT", "PG", "MA", "DIS", "NFLX", "AMD", "INTC",
    "CSCO", "PEP", "COST", "AVGO", "TXN", "CMCSA", "ADBE", "NKE",
    "QCOM", "PYPL", "INTU", "AMGN", "TMO", "BKNG", "SBUX", "GILD",
    "ISRG", "VRTX", "ADI", "REGN", "CDNS", "FISV", "KLAC", "SNPS"
]

PORTFOLIO_NAMES = [
    "Growth Portfolio", "Conservative Portfolio", "Tech Focus", "Dividend Strategy",
    "Balanced Fund", "Aggressive Growth", "Income Portfolio", "Value Investing",
    "Index Tracking", "Sector Rotation", "International Mix", "ESG Portfolio",
    "Small Cap Focus", "Blue Chip Holdings", "Emerging Markets"
]


def create_users(db: Session, count: int = 15) -> list:
    """Generate user IDs for seeding data (no users table maintained)"""
    # No users table - just return a list of user IDs to use for transactions/portfolios
    user_ids = list(range(1, count + 1))
    print(f"Using user IDs: {user_ids}")
    return user_ids


def create_transactions(db: Session, user_ids: list, count: int = 150):
    """Create realistic transactions"""
    transactions = []
    
    for i in range(count):
        # Random user
        user_id = random.choice(user_ids)
        
        # Realistic transaction amounts
        if random.random() < 0.3:  # 30% small transactions
            amount = round(random.uniform(10, 500), 2)
        elif random.random() < 0.7:  # 40% medium transactions
            amount = round(random.uniform(500, 5000), 2)
        else:  # 30% large transactions
            amount = round(random.uniform(5000, 50000), 2)
        
        # Random currency
        currency = random.choice(CURRENCIES)
        
        # Random timestamp within last 90 days
        days_ago = random.randint(0, 90)
        hours_ago = random.randint(0, 23)
        minutes_ago = random.randint(0, 59)
        timestamp = datetime.utcnow() - timedelta(days=days_ago, hours=hours_ago, minutes=minutes_ago)
        
        # Random category
        category = random.choice(TRANSACTION_CATEGORIES)
        
        # Risk score based on amount and category
        base_risk = random.uniform(0.1, 0.9)
        if amount > 10000:
            base_risk += 0.1
        if category in ["Crypto", "Options Trade", "Forex"]:
            base_risk += 0.2
        risk_score = min(round(base_risk, 2), 1.0)
        
        transaction = Transaction(
            user_id=user_id,
            amount=amount,
            currency=currency,
            timestamp=timestamp,
            category=category,
            risk_score=risk_score
        )
        transactions.append(transaction)
    
    db.add_all(transactions)
    db.commit()
    print(f"Created {len(transactions)} transactions")
    return transactions


def create_portfolios(db: Session, user_ids: list, count: int = 15):
    """Create realistic portfolios"""
    portfolios = []
    
    for i in range(count):
        user_id = random.choice(user_ids)
        
        # Create portfolio with realistic assets
        num_assets = random.randint(3, 12)
        assets = {}
        total_value = 0.0
        
        for _ in range(num_assets):
            symbol = random.choice(STOCK_SYMBOLS)
            shares = random.randint(1, 1000)
            # Get a recent price for this symbol (or use a random price)
            price = round(random.uniform(50, 500), 2)
            value = shares * price
            assets[symbol] = {
                "shares": shares,
                "price": price,
                "value": value
            }
            total_value += value
        
        # Random timestamp within last 30 days
        days_ago = random.randint(0, 30)
        last_updated = datetime.utcnow() - timedelta(days=days_ago)
        
        portfolio = Portfolio(
            user_id=user_id,
            assets=assets,
            total_value=round(total_value, 2),
            last_updated=last_updated
        )
        portfolios.append(portfolio)
    
    db.add_all(portfolios)
    db.commit()
    print(f"Created {len(portfolios)} portfolios")
    return portfolios


def create_market_data(db: Session, symbols: list = None, days_back: int = 90):
    """Create realistic market data
    
    Note: Since symbol is the primary key in MarketData model,
    we can only store one entry per symbol (the latest).
    For historical data, consider modifying the model to use
    a composite primary key (symbol, timestamp) or add an id field.
    """
    if symbols is None:
        symbols = STOCK_SYMBOLS
    
    # Base prices for each symbol (realistic ranges)
    base_prices = {
        "AAPL": 175.0, "GOOGL": 140.0, "MSFT": 380.0, "AMZN": 150.0,
        "TSLA": 250.0, "META": 320.0, "NVDA": 480.0, "JPM": 150.0,
        "V": 250.0, "JNJ": 160.0, "WMT": 160.0, "PG": 150.0,
        "MA": 400.0, "DIS": 90.0, "NFLX": 450.0, "AMD": 120.0,
        "INTC": 45.0, "CSCO": 55.0, "PEP": 170.0, "COST": 550.0,
        "AVGO": 900.0, "TXN": 160.0, "CMCSA": 45.0, "ADBE": 550.0,
        "NKE": 100.0, "QCOM": 120.0, "PYPL": 60.0, "INTU": 550.0,
        "AMGN": 250.0, "TMO": 550.0, "BKNG": 3500.0, "SBUX": 100.0,
        "GILD": 75.0, "ISRG": 350.0, "VRTX": 400.0, "ADI": 180.0,
        "REGN": 800.0, "CDNS": 250.0, "FISV": 120.0, "KLAC": 500.0,
        "SNPS": 500.0
    }
    
    market_data_entries = []
    
    # Create one entry per symbol with realistic current price
    for symbol in symbols:
        base_price = base_prices.get(symbol, random.uniform(50, 500))
        
        # Simulate price movement over the past period
        current_price = base_price
        for _ in range(days_back):
            # Random walk with slight upward bias
            change_percent = random.uniform(-0.02, 0.03)
            current_price = current_price * (1 + change_percent)
            # Keep price within reasonable bounds
            current_price = max(current_price, base_price * 0.7)
            current_price = min(current_price, base_price * 1.3)
        
        # Realistic volume based on market cap (simplified)
        if base_price > 1000:
            volume = random.randint(500000, 3000000)  # High-priced stocks
        elif base_price > 200:
            volume = random.randint(1000000, 10000000)  # Mid-range stocks
        else:
            volume = random.randint(2000000, 15000000)  # Lower-priced stocks
        
        # Latest timestamp (market close today)
        timestamp = datetime.utcnow().replace(hour=16, minute=0, second=0, microsecond=0)
        
        market_data = MarketData(
            symbol=symbol,
            price=round(current_price, 2),
            volume=volume,
            timestamp=timestamp
        )
        market_data_entries.append(market_data)
    
    # Use merge to handle existing entries (update if exists, insert if not)
    for entry in market_data_entries:
        db.merge(entry)
    
    db.commit()
    print(f"Created/updated {len(market_data_entries)} market data entries")
    return market_data_entries


def seed_database(force: bool = False):
    """
    Main function to seed the database.
    
    Args:
        force: If True, seed even if data already exists. If False, skip if data exists.
    """
    print("Starting database seeding...")
    
    # Initialize database connection
    database.initialize(
        database_url=settings.DATABASE_URL,
        echo=settings.DB_ECHO
    )
    
    # Create all tables
    database.create_tables()
    
    # Get database session using context manager pattern
    db_gen = database.get_session()
    db = next(db_gen)
    
    try:
        # Check if data already exists (unless force is True)
        if not force:
            transaction_count = db.query(Transaction).count()
            portfolio_count = db.query(Portfolio).count()
            market_data_count = db.query(MarketData).count()
            
            if transaction_count > 0 or portfolio_count > 0 or market_data_count > 0:
                print("\n" + "="*80)
                print("⚠️  Database already contains data:")
                print(f"   - Transactions: {transaction_count}")
                print(f"   - Portfolios: {portfolio_count}")
                print(f"   - Market Data: {market_data_count}")
                print("\n✅ Skipping seed (data already exists).")
                print("   To force re-seed, use: python -m src.database.seed --force")
                print("="*80 + "\n")
                return
        
        # Create users (or get user IDs)
        user_ids = create_users(db, count=15)
        
        # Create transactions
        print("\nCreating transactions...")
        create_transactions(db, user_ids, count=150)
        
        # Create portfolios
        print("\nCreating portfolios...")
        create_portfolios(db, user_ids, count=15)
        
        # Create market data
        print("\nCreating market data...")
        create_market_data(db, symbols=STOCK_SYMBOLS, days_back=30)
        
        # Commit all changes
        db.commit()
        
        print("\n" + "="*80)
        print("✅ Database seeding completed successfully!")
        print(f"   - Users: {len(user_ids)}")
        print(f"   - Transactions: 150")
        print(f"   - Portfolios: 15")
        print(f"   - Market Data: {len(STOCK_SYMBOLS)} symbols")
        print("="*80 + "\n")
        
    except Exception as e:
        db.rollback()
        print(f"\n❌ Error seeding database: {e}")
        raise
    finally:
        # Close the session (generator will handle cleanup)
        try:
            next(db_gen, None)  # Consume the generator to trigger finally block
        except StopIteration:
            pass


if __name__ == "__main__":
    import sys
    force = "--force" in sys.argv or "-f" in sys.argv
    seed_database(force=force)


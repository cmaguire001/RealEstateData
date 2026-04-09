CREATE TABLE IF NOT EXISTS listing_snapshots (
    id SERIAL PRIMARY KEY,
    city TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    total_listings INT,
    avg_price NUMERIC,
    median_price NUMERIC,
    avg_price_per_sqft NUMERIC,
    inventory_growth NUMERIC,
    status TEXT
);

CREATE INDEX IF NOT EXISTS idx_city_time ON listing_snapshots(city, timestamp);

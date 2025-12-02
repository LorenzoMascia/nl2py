-- PostgreSQL Initialization Script for NL2Py

-- Create sample tables
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    age INTEGER,
    status VARCHAR(50) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS orders (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    product_name VARCHAR(255),
    quantity INTEGER,
    price NUMERIC(10, 2),
    order_date DATE DEFAULT CURRENT_DATE,
    status VARCHAR(50) DEFAULT 'pending'
);

CREATE TABLE IF NOT EXISTS products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    category VARCHAR(100),
    price NUMERIC(10, 2),
    stock INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert sample data
INSERT INTO users (username, email, age, status) VALUES
    ('alice', 'alice@example.com', 28, 'active'),
    ('bob', 'bob@example.com', 35, 'active'),
    ('charlie', 'charlie@example.com', 22, 'inactive'),
    ('diana', 'diana@example.com', 31, 'active')
ON CONFLICT DO NOTHING;

INSERT INTO products (name, category, price, stock) VALUES
    ('Laptop Pro', 'Electronics', 1299.99, 50),
    ('Wireless Mouse', 'Electronics', 29.99, 200),
    ('Office Chair', 'Furniture', 249.99, 30),
    ('Desk Lamp', 'Furniture', 49.99, 100),
    ('USB-C Cable', 'Electronics', 12.99, 500)
ON CONFLICT DO NOTHING;

INSERT INTO orders (user_id, product_name, quantity, price, order_date, status) VALUES
    (1, 'Laptop Pro', 1, 1299.99, '2025-01-15', 'completed'),
    (2, 'Wireless Mouse', 2, 29.99, '2025-01-16', 'completed'),
    (1, 'Office Chair', 1, 249.99, '2025-01-17', 'pending'),
    (3, 'Desk Lamp', 3, 49.99, '2025-01-18', 'shipped'),
    (4, 'USB-C Cable', 5, 12.99, '2025-01-19', 'completed')
ON CONFLICT DO NOTHING;

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_status ON users(status);
CREATE INDEX IF NOT EXISTS idx_orders_user_id ON orders(user_id);
CREATE INDEX IF NOT EXISTS idx_orders_date ON orders(order_date);
CREATE INDEX IF NOT EXISTS idx_products_category ON products(category);

-- Grant privileges
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO nl2py;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO nl2py;

\echo 'PostgreSQL initialization completed successfully!'

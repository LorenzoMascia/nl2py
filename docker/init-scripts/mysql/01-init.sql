-- MySQL Initialization Script for NL2Py

USE nl2py_db;

-- Create sample tables
CREATE TABLE IF NOT EXISTS customers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    country VARCHAR(100),
    revenue DECIMAL(10, 2) DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS sales (
    id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id INT,
    product VARCHAR(255),
    quantity INT,
    amount DECIMAL(10, 2),
    sale_date DATE,
    region VARCHAR(100),
    FOREIGN KEY (customer_id) REFERENCES customers(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS inventory (
    id INT AUTO_INCREMENT PRIMARY KEY,
    product VARCHAR(255) NOT NULL UNIQUE,
    category VARCHAR(100),
    stock INT DEFAULT 0,
    unit_price DECIMAL(10, 2),
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Insert sample data
INSERT INTO customers (name, email, country, revenue) VALUES
    ('Acme Corp', 'contact@acme.com', 'USA', 50000.00),
    ('Global Tech', 'info@globaltech.com', 'Germany', 75000.00),
    ('Pacific Trade', 'sales@pacific.com', 'Japan', 30000.00),
    ('Euro Systems', 'hello@eurosys.com', 'France', 45000.00)
ON DUPLICATE KEY UPDATE name=VALUES(name);

INSERT INTO inventory (product, category, stock, unit_price) VALUES
    ('Server Rack', 'Hardware', 25, 2500.00),
    ('Network Switch', 'Hardware', 100, 450.00),
    ('Software License', 'Software', 1000, 199.00),
    ('Support Contract', 'Services', 50, 5000.00)
ON DUPLICATE KEY UPDATE stock=VALUES(stock);

INSERT INTO sales (customer_id, product, quantity, amount, sale_date, region) VALUES
    (1, 'Server Rack', 2, 5000.00, '2025-01-10', 'North America'),
    (2, 'Network Switch', 10, 4500.00, '2025-01-12', 'Europe'),
    (3, 'Software License', 50, 9950.00, '2025-01-15', 'Asia'),
    (4, 'Support Contract', 3, 15000.00, '2025-01-18', 'Europe'),
    (1, 'Network Switch', 5, 2250.00, '2025-01-20', 'North America')
ON DUPLICATE KEY UPDATE quantity=VALUES(quantity);

-- Create indexes
CREATE INDEX idx_customers_country ON customers(country);
CREATE INDEX idx_sales_date ON sales(sale_date);
CREATE INDEX idx_sales_region ON sales(region);
CREATE INDEX idx_inventory_category ON inventory(category);

SELECT 'MySQL initialization completed successfully!' AS Status;

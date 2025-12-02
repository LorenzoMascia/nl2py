// MongoDB Initialization Script for NL2Py

// Switch to nl2py_db database
db = db.getSiblingDB('nl2py_db');

// Create collections and insert sample data

// Products collection
db.createCollection('products');
db.products.insertMany([
    {
        name: "Laptop Pro 15",
        category: "Electronics",
        price: 1299.99,
        stock: 50,
        specs: {
            cpu: "Intel i7",
            ram: "16GB",
            storage: "512GB SSD"
        },
        tags: ["laptop", "computer", "electronics"],
        created_at: new Date("2025-01-01")
    },
    {
        name: "Wireless Keyboard",
        category: "Accessories",
        price: 79.99,
        stock: 200,
        specs: {
            type: "Mechanical",
            connectivity: "Bluetooth"
        },
        tags: ["keyboard", "wireless", "accessories"],
        created_at: new Date("2025-01-02")
    },
    {
        name: "4K Monitor",
        category: "Electronics",
        price: 449.99,
        stock: 30,
        specs: {
            size: "27 inch",
            resolution: "3840x2160",
            refresh_rate: "60Hz"
        },
        tags: ["monitor", "display", "electronics"],
        created_at: new Date("2025-01-03")
    }
]);

// Orders collection
db.createCollection('orders');
db.orders.insertMany([
    {
        order_id: "ORD-2025-001",
        customer: {
            name: "John Doe",
            email: "john@example.com"
        },
        items: [
            { product: "Laptop Pro 15", quantity: 1, price: 1299.99 }
        ],
        total: 1299.99,
        status: "completed",
        order_date: new Date("2025-01-15"),
        shipping_address: {
            street: "123 Main St",
            city: "New York",
            country: "USA"
        }
    },
    {
        order_id: "ORD-2025-002",
        customer: {
            name: "Jane Smith",
            email: "jane@example.com"
        },
        items: [
            { product: "Wireless Keyboard", quantity: 2, price: 79.99 },
            { product: "4K Monitor", quantity: 1, price: 449.99 }
        ],
        total: 609.97,
        status: "shipped",
        order_date: new Date("2025-01-18"),
        shipping_address: {
            street: "456 Oak Ave",
            city: "Los Angeles",
            country: "USA"
        }
    }
]);

// Logs collection
db.createCollection('logs');
db.logs.insertMany([
    {
        level: "INFO",
        message: "Application started",
        timestamp: new Date("2025-01-20T10:00:00Z"),
        source: "app.main"
    },
    {
        level: "WARNING",
        message: "High memory usage detected",
        timestamp: new Date("2025-01-20T11:30:00Z"),
        source: "system.monitor"
    },
    {
        level: "ERROR",
        message: "Database connection timeout",
        timestamp: new Date("2025-01-20T12:15:00Z"),
        source: "db.connection"
    }
]);

// Create indexes
db.products.createIndex({ category: 1 });
db.products.createIndex({ name: "text" });
db.products.createIndex({ price: 1 });
db.orders.createIndex({ "customer.email": 1 });
db.orders.createIndex({ order_date: -1 });
db.orders.createIndex({ status: 1 });
db.logs.createIndex({ timestamp: -1 });
db.logs.createIndex({ level: 1 });

// Create user with read/write permissions
db.createUser({
    user: 'nl2py',
    pwd: 'nl2py123',
    roles: [
        { role: 'readWrite', db: 'nl2py_db' },
        { role: 'dbAdmin', db: 'nl2py_db' }
    ]
});

print('MongoDB initialization completed successfully!');

// Neo4j Initialization Script for AIbasic
// This script creates sample graph data for testing

// Create indexes for better performance
CREATE INDEX person_name IF NOT EXISTS FOR (p:Person) ON (p.name);
CREATE INDEX product_name IF NOT EXISTS FOR (p:Product) ON (p.name);
CREATE INDEX company_name IF NOT EXISTS FOR (c:Company) ON (c.name);

// Create constraints for data integrity
CREATE CONSTRAINT person_name_unique IF NOT EXISTS FOR (p:Person) REQUIRE p.name IS UNIQUE;
CREATE CONSTRAINT product_name_unique IF NOT EXISTS FOR (p:Product) REQUIRE p.name IS UNIQUE;
CREATE CONSTRAINT company_name_unique IF NOT EXISTS FOR (c:Company) REQUIRE c.name IS UNIQUE;

// Example 1: Social Network
// Create people
CREATE (alice:Person {name: 'Alice', age: 30, city: 'New York', email: 'alice@example.com'})
CREATE (bob:Person {name: 'Bob', age: 35, city: 'London', email: 'bob@example.com'})
CREATE (charlie:Person {name: 'Charlie', age: 28, city: 'Paris', email: 'charlie@example.com'})
CREATE (diana:Person {name: 'Diana', age: 32, city: 'Berlin', email: 'diana@example.com'})
CREATE (eve:Person {name: 'Eve', age: 27, city: 'Tokyo', email: 'eve@example.com'})
CREATE (frank:Person {name: 'Frank', age: 40, city: 'Sydney', email: 'frank@example.com'});

// Create friendships (KNOWS relationships)
MATCH (alice:Person {name: 'Alice'}), (bob:Person {name: 'Bob'})
CREATE (alice)-[:KNOWS {since: 2020, closeness: 8}]->(bob);

MATCH (bob:Person {name: 'Bob'}), (charlie:Person {name: 'Charlie'})
CREATE (bob)-[:KNOWS {since: 2019, closeness: 9}]->(charlie);

MATCH (alice:Person {name: 'Alice'}), (charlie:Person {name: 'Charlie'})
CREATE (alice)-[:KNOWS {since: 2021, closeness: 7}]->(charlie);

MATCH (charlie:Person {name: 'Charlie'}), (diana:Person {name: 'Diana'})
CREATE (charlie)-[:KNOWS {since: 2022, closeness: 6}]->(diana);

MATCH (diana:Person {name: 'Diana'}), (eve:Person {name: 'Eve'})
CREATE (diana)-[:KNOWS {since: 2020, closeness: 8}]->(eve);

MATCH (bob:Person {name: 'Bob'}), (frank:Person {name: 'Frank'})
CREATE (bob)-[:KNOWS {since: 2018, closeness: 9}]->(frank);

// Example 2: Company Structure
// Create companies
CREATE (techcorp:Company {name: 'TechCorp', industry: 'Technology', founded: 2010, employees: 500})
CREATE (datalab:Company {name: 'DataLab', industry: 'Analytics', founded: 2015, employees: 150})
CREATE (cloudservices:Company {name: 'CloudServices', industry: 'Cloud Computing', founded: 2012, employees: 300});

// Create WORKS_FOR relationships
MATCH (alice:Person {name: 'Alice'}), (techcorp:Company {name: 'TechCorp'})
CREATE (alice)-[:WORKS_FOR {position: 'Data Scientist', since: 2019, salary: 95000}]->(techcorp);

MATCH (bob:Person {name: 'Bob'}), (techcorp:Company {name: 'TechCorp'})
CREATE (bob)-[:WORKS_FOR {position: 'Senior Engineer', since: 2017, salary: 110000}]->(techcorp);

MATCH (charlie:Person {name: 'Charlie'}), (datalab:Company {name: 'DataLab'})
CREATE (charlie)-[:WORKS_FOR {position: 'Analyst', since: 2020, salary: 75000}]->(datalab);

MATCH (diana:Person {name: 'Diana'}), (datalab:Company {name: 'DataLab'})
CREATE (diana)-[:WORKS_FOR {position: 'Manager', since: 2018, salary: 95000}]->(datalab);

MATCH (eve:Person {name: 'Eve'}), (cloudservices:Company {name: 'CloudServices'})
CREATE (eve)-[:WORKS_FOR {position: 'DevOps Engineer', since: 2021, salary: 90000}]->(cloudservices);

MATCH (frank:Person {name: 'Frank'}), (cloudservices:Company {name: 'CloudServices'})
CREATE (frank)-[:WORKS_FOR {position: 'CTO', since: 2012, salary: 150000}]->(cloudservices);

// Create PARTNERS_WITH relationships between companies
MATCH (techcorp:Company {name: 'TechCorp'}), (datalab:Company {name: 'DataLab'})
CREATE (techcorp)-[:PARTNERS_WITH {since: 2020, contract_value: 500000}]->(datalab);

MATCH (techcorp:Company {name: 'TechCorp'}), (cloudservices:Company {name: 'CloudServices'})
CREATE (techcorp)-[:PARTNERS_WITH {since: 2019, contract_value: 750000}]->(cloudservices);

// Example 3: E-commerce Graph
// Create products
CREATE (laptop:Product {name: 'Laptop Pro 15', category: 'Electronics', price: 1299, stock: 50})
CREATE (mouse:Product {name: 'Wireless Mouse', category: 'Electronics', price: 29, stock: 200})
CREATE (keyboard:Product {name: 'Mechanical Keyboard', category: 'Electronics', price: 89, stock: 150})
CREATE (monitor:Product {name: '27" 4K Monitor', category: 'Electronics', price: 399, stock: 75})
CREATE (headphones:Product {name: 'Noise-Canceling Headphones', category: 'Electronics', price: 249, stock: 100})
CREATE (webcam:Product {name: 'HD Webcam', category: 'Electronics', price: 79, stock: 120});

// Create PURCHASED relationships
MATCH (alice:Person {name: 'Alice'}), (laptop:Product {name: 'Laptop Pro 15'})
CREATE (alice)-[:PURCHASED {date: '2025-01-10', quantity: 1, rating: 5, review: 'Excellent laptop!'}]->(laptop);

MATCH (alice:Person {name: 'Alice'}), (mouse:Product {name: 'Wireless Mouse'})
CREATE (alice)-[:PURCHASED {date: '2025-01-11', quantity: 1, rating: 4, review: 'Good quality'}]->(mouse);

MATCH (bob:Person {name: 'Bob'}), (laptop:Product {name: 'Laptop Pro 15'})
CREATE (bob)-[:PURCHASED {date: '2025-01-12', quantity: 1, rating: 5, review: 'Perfect for work'}]->(laptop);

MATCH (bob:Person {name: 'Bob'}), (monitor:Product {name: '27" 4K Monitor'})
CREATE (bob)-[:PURCHASED {date: '2025-01-13', quantity: 2, rating: 5, review: 'Amazing display'}]->(monitor);

MATCH (charlie:Person {name: 'Charlie'}), (keyboard:Product {name: 'Mechanical Keyboard'})
CREATE (charlie)-[:PURCHASED {date: '2025-01-14', quantity: 1, rating: 4, review: 'Nice typing experience'}]->(keyboard);

MATCH (diana:Person {name: 'Diana'}), (headphones:Product {name: 'Noise-Canceling Headphones'})
CREATE (diana)-[:PURCHASED {date: '2025-01-15', quantity: 1, rating: 5, review: 'Great sound quality'}]->(headphones);

MATCH (eve:Person {name: 'Eve'}), (webcam:Product {name: 'HD Webcam'})
CREATE (eve)-[:PURCHASED {date: '2025-01-16', quantity: 1, rating: 4, review: 'Clear video'}]->(webcam);

MATCH (frank:Person {name: 'Frank'}), (laptop:Product {name: 'Laptop Pro 15'})
CREATE (frank)-[:PURCHASED {date: '2025-01-17', quantity: 3, rating: 5, review: 'Bought for team'}]->(laptop);

// Create VIEWED relationships (browsing history)
MATCH (alice:Person {name: 'Alice'}), (keyboard:Product {name: 'Mechanical Keyboard'})
CREATE (alice)-[:VIEWED {timestamp: '2025-01-18 10:15:00', duration_seconds: 120}]->(keyboard);

MATCH (alice:Person {name: 'Alice'}), (monitor:Product {name: '27" 4K Monitor'})
CREATE (alice)-[:VIEWED {timestamp: '2025-01-18 10:20:00', duration_seconds: 180}]->(monitor);

MATCH (charlie:Person {name: 'Charlie'}), (laptop:Product {name: 'Laptop Pro 15'})
CREATE (charlie)-[:VIEWED {timestamp: '2025-01-18 11:00:00', duration_seconds: 240}]->(laptop);

// Example 4: Skills Graph
// Create skills
CREATE (python:Skill {name: 'Python', category: 'Programming', difficulty: 'Medium'})
CREATE (java:Skill {name: 'Java', category: 'Programming', difficulty: 'Medium'})
CREATE (ml:Skill {name: 'Machine Learning', category: 'AI', difficulty: 'Hard'})
CREATE (devops:Skill {name: 'DevOps', category: 'Operations', difficulty: 'Hard'})
CREATE (sql:Skill {name: 'SQL', category: 'Database', difficulty: 'Easy'})
CREATE (react:Skill {name: 'React', category: 'Frontend', difficulty: 'Medium'});

// Create HAS_SKILL relationships
MATCH (alice:Person {name: 'Alice'}), (python:Skill {name: 'Python'})
CREATE (alice)-[:HAS_SKILL {level: 'Expert', years: 5}]->(python);

MATCH (alice:Person {name: 'Alice'}), (ml:Skill {name: 'Machine Learning'})
CREATE (alice)-[:HAS_SKILL {level: 'Advanced', years: 3}]->(ml);

MATCH (bob:Person {name: 'Bob'}), (java:Skill {name: 'Java'})
CREATE (bob)-[:HAS_SKILL {level: 'Expert', years: 10}]->(java);

MATCH (bob:Person {name: 'Bob'}), (sql:Skill {name: 'SQL'})
CREATE (bob)-[:HAS_SKILL {level: 'Expert', years: 8}]->(sql);

MATCH (charlie:Person {name: 'Charlie'}), (sql:Skill {name: 'SQL'})
CREATE (charlie)-[:HAS_SKILL {level: 'Intermediate', years: 2}]->(sql);

MATCH (diana:Person {name: 'Diana'}), (python:Skill {name: 'Python'})
CREATE (diana)-[:HAS_SKILL {level: 'Advanced', years: 4}]->(python);

MATCH (eve:Person {name: 'Eve'}), (devops:Skill {name: 'DevOps'})
CREATE (eve)-[:HAS_SKILL {level: 'Expert', years: 4}]->(devops);

MATCH (frank:Person {name: 'Frank'}), (react:Skill {name: 'React'})
CREATE (frank)-[:HAS_SKILL {level: 'Advanced', years: 3}]->(react);

// Display summary statistics
MATCH (n) RETURN labels(n)[0] as NodeType, count(*) as Count;
MATCH ()-[r]->() RETURN type(r) as RelationshipType, count(*) as Count;

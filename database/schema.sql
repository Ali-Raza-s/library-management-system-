CREATE DATABASE IF NOT EXISTS smart_shelf;
USE smart_shelf;

CREATE TABLE users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100),
    email VARCHAR(100) UNIQUE,
    password VARCHAR(255),
    role ENUM('Admin','Librarian','Student'),
    cnic VARCHAR(20) UNIQUE,
    phone_number VARCHAR(20) UNIQUE,
    address TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE categories (
    category_id INT AUTO_INCREMENT PRIMARY KEY,
    category_name VARCHAR(100)
);

CREATE TABLE books (
    book_id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(255),
    author VARCHAR(255),
    isbn VARCHAR(50) UNIQUE,
    description TEXT,
    publication_year INT,
    total_copies INT,
    available_copies INT,
    category_id INT,
    CONSTRAINT fk_books_category
        FOREIGN KEY (category_id) REFERENCES categories(category_id)
);

CREATE TABLE borrows (
    borrow_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    book_id INT,
    borrow_date DATE,
    due_date DATE,
    return_date DATE NULL,
    status VARCHAR(20),
    CONSTRAINT fk_borrows_user
        FOREIGN KEY (user_id) REFERENCES users(user_id),
    CONSTRAINT fk_borrows_book
        FOREIGN KEY (book_id) REFERENCES books(book_id)
);

CREATE TABLE IF NOT EXISTS activity_logs (
    log_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    action_type VARCHAR(100),
    action_description TEXT,
    action_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    ip_address VARCHAR(45),
    created_by_role VARCHAR(50),
    CONSTRAINT fk_activity_logs_user
        FOREIGN KEY (user_id) REFERENCES users(user_id)
);

CREATE TABLE IF NOT EXISTS book_reviews (
    review_id INT AUTO_INCREMENT PRIMARY KEY,
    book_id INT,
    user_id INT,
    rating INT,
    review_text TEXT,
    review_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_book_reviews_book
        FOREIGN KEY (book_id) REFERENCES books(book_id),
    CONSTRAINT fk_book_reviews_user
        FOREIGN KEY (user_id) REFERENCES users(user_id)
);

INSERT INTO users (name, email, password, role, cnic, phone_number, address) VALUES
('Admin User', 'admin@smart_shelf.edu', 'admin123', 'Admin', '12345-1234567-1', '03001234567', 'Main Campus, Lahore'),
('Sara Librarian', 'librarian@smart_shelf.edu', 'lib123', 'Librarian', '12345-7654321-2', '03009876543', 'Library Block, Lahore'),
('Ali Raza', 'ali@student.edu', 'student123', 'Student', '12345-9876543-3', '03121234567', 'Model Town, Lahore'),
('Fatima Khan', 'fatima@student.edu', 'student123', 'Student', '12345-4567890-4', '03221234567', 'Gulberg, Lahore');

INSERT INTO categories (category_name) VALUES
('Computer Science'),
('Mathematics'),
('Fiction'),
('History');

INSERT INTO books (title, author, isbn, description, publication_year, total_copies, available_copies, category_id) VALUES
('Introduction to Python', 'John Smith', '978-111-0001', 'This book teaches Python programming fundamentals including variables, loops, functions, object-oriented programming, and file handling.', 2021, 5, 4, 1),
('Database Systems', 'Alice Brown', '978-111-0002', 'This book explains database design, SQL queries, normalization, and transaction management.', 2020, 3, 3, 1),
('Calculus Made Easy', 'Silvanus Thompson', '978-222-0001', 'This book introduces limits, derivatives, integrals, and advanced problem-solving in calculus.', 2019, 2, 2, 2),
('The Great Gatsby', 'F. Scott Fitzgerald', '978-333-0001', 'A classic novel about ambition, wealth, and the American dream.', 1925, 4, 3, 3),
('World History Basics', 'Emma Wilson', '978-444-0001', 'This book covers major historical events, civilizations, and the development of societies.', 2018, 2, 2, 4),
('Flask Web Development', 'Miguel Grinberg', '978-111-0003', 'This book introduces Flask concepts such as routing, templates, forms, and database integration.', 2022, 4, 4, 1),
('Clean Code', 'Robert C. Martin', '978-111-0004', 'This book teaches code readability, refactoring, testing, and maintainable software design.', 2008, 3, 3, 1),
('The Pragmatic Programmer', 'Andrew Hunt', '978-111-0005', 'This book explains practical software engineering habits and modern programming techniques.', 1999, 5, 5, 1),
('Data Structures in Java', 'Robert Lafore', '978-111-0006', 'This book covers arrays, linked lists, stacks, queues, trees, and sorting algorithms.', 2017, 2, 2, 1),
('Machine Learning Basics', 'Tom Mitchell', '978-111-0007', 'This book introduces supervised learning, classification, regression, and evaluation methods.', 2018, 3, 3, 1),
('Computer Networks', 'Andrew Tanenbaum', '978-111-0008', 'This book explains networking layers, protocols, TCP/IP, and data communication.', 2020, 4, 3, 1),
('Operating System Concepts', 'Abraham Silberschatz', '978-111-0009', 'This book teaches process scheduling, memory management, file systems, and concurrency.', 2019, 2, 2, 1),
('Artificial Intelligence', 'Stuart Russell', '978-111-0010', 'This book introduces search, logic, machine learning, and intelligent systems.', 2021, 3, 3, 1),
('Web Programming with PHP', 'Luke Welling', '978-111-0011', 'This book teaches PHP, forms, sessions, databases, and web application development.', 2016, 2, 2, 1),
('Linear Algebra Done Right', 'Sheldon Axler', '978-222-0002', 'This book covers vector spaces, linear transformations, eigenvalues, and geometry.', 2015, 3, 3, 2),
('Discrete Mathematics', 'Kenneth Rosen', '978-222-0003', 'This book introduces logic, sets, graphs, combinatorics, and proof techniques.', 2012, 4, 4, 2),
('Statistics for Engineers', 'Montgomery', '978-222-0004', 'This book explains statistical methods used in engineering and quality control.', 2014, 2, 2, 2),
('Probability Theory', 'Sheldon Ross', '978-222-0005', 'This book teaches probability concepts, random variables, and distributions.', 2010, 3, 3, 2),
('Differential Equations', 'Paul Blanchard', '978-222-0006', 'This book explains solving ordinary differential equations and applications.', 2006, 2, 2, 2),
('Number Theory', 'Ivan Niven', '978-222-0007', 'This book introduces divisibility, congruences, prime numbers, and number patterns.', 2003, 1, 1, 2),
('Mathematical Analysis', 'Tom Apostol', '978-222-0008', 'This book provides foundation concepts in calculus, limits, continuity, and sequences.', 1974, 2, 2, 2),
('Geometry and Topology', 'James Munkres', '978-222-0009', 'This book teaches geometry, topology, and spatial reasoning.', 2000, 3, 3, 2),
('To Kill a Mockingbird', 'Harper Lee', '978-333-0002', 'This novel explores justice, morality, and social prejudice through a young narrator.', 1960, 5, 5, 3),
('1984', 'George Orwell', '978-333-0003', 'This novel discusses government control, truth, and freedom of thought.', 1949, 4, 4, 3),
('Pride and Prejudice', 'Jane Austen', '978-333-0004', 'This classic novel explains social class, relationships, and personal growth.', 1813, 3, 3, 3),
('The Catcher in the Rye', 'J.D. Salinger', '978-333-0005', 'This novel explores teenage identity, loneliness, and emotional confusion.', 1951, 2, 2, 3),
('Lord of the Flies', 'William Golding', '978-333-0006', 'This novel presents themes of leadership, fear, and human nature.', 1954, 3, 3, 3),
('Brave New World', 'Aldous Huxley', '978-333-0007', 'This novel introduces readers to technology, society, and the cost of comfort.', 1932, 4, 4, 3),
('The Alchemist', 'Paulo Coelho', '978-333-0008', 'This novel teaches self-discovery, dreams, and the value of persistence.', 1988, 5, 4, 3),
('Animal Farm', 'George Orwell', '978-333-0009', 'This allegorical novel explains power, politics, and the danger of corruption.', 1945, 3, 3, 3),
('Sapiens', 'Yuval Noah Harari', '978-444-0002', 'This book explains human history, culture, and the growth of civilizations.', 2011, 4, 4, 4),
('A Brief History of Time', 'Stephen Hawking', '978-444-0003', 'This book introduces cosmology, black holes, and the universe in simple language.', 1988, 3, 3, 4),
('The Diary of Anne Frank', 'Anne Frank', '978-444-0004', 'This diary shares personal experiences during war and the importance of hope.', 1947, 2, 2, 4),
('Guns Germs and Steel', 'Jared Diamond', '978-444-0005', 'This book explains how geography shaped human societies and civilizations.', 1997, 3, 3, 4),
('Ancient Civilizations', 'Christopher Scarre', '978-444-0007', 'This book introduces early civilizations, their growth, and cultural achievements.', 2013, 4, 4, 4);

INSERT INTO borrows (user_id, book_id, borrow_date, due_date, return_date, status) VALUES
(3, 1, '2026-05-01', '2026-05-15', NULL, 'active'),
(4, 4, '2026-05-10', '2026-05-24', NULL, 'active'),
(3, 2, '2026-04-01', '2026-04-15', '2026-04-12', 'returned');

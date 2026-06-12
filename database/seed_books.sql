-- Smart-Shelf: Additional 30 books seed data
-- Run once on existing database

USE smart_shelf;

INSERT INTO books (title, author, isbn, total_copies, available_copies, category_id) VALUES
('Flask Web Development', 'Miguel Grinberg', '978-111-0003', 4, 4, 1),
('Clean Code', 'Robert C. Martin', '978-111-0004', 3, 3, 1),
('The Pragmatic Programmer', 'Andrew Hunt', '978-111-0005', 5, 5, 1),
('Data Structures in Java', 'Robert Lafore', '978-111-0006', 2, 2, 1),
('Machine Learning Basics', 'Tom Mitchell', '978-111-0007', 3, 3, 1),
('Computer Networks', 'Andrew Tanenbaum', '978-111-0008', 4, 3, 1),
('Operating System Concepts', 'Abraham Silberschatz', '978-111-0009', 2, 2, 1),
('Artificial Intelligence', 'Stuart Russell', '978-111-0010', 3, 3, 1),
('Web Programming with PHP', 'Luke Welling', '978-111-0011', 2, 2, 1),
('Linear Algebra Done Right', 'Sheldon Axler', '978-222-0002', 3, 3, 2),
('Discrete Mathematics', 'Kenneth Rosen', '978-222-0003', 4, 4, 2),
('Statistics for Engineers', 'Montgomery', '978-222-0004', 2, 2, 2),
('Probability Theory', 'Sheldon Ross', '978-222-0005', 3, 3, 2),
('Differential Equations', 'Paul Blanchard', '978-222-0006', 2, 2, 2),
('Number Theory', 'Ivan Niven', '978-222-0007', 1, 1, 2),
('Mathematical Analysis', 'Tom Apostol', '978-222-0008', 2, 2, 2),
('Geometry and Topology', 'James Munkres', '978-222-0009', 3, 3, 2),
('To Kill a Mockingbird', 'Harper Lee', '978-333-0002', 5, 5, 3),
('1984', 'George Orwell', '978-333-0003', 4, 4, 3),
('Pride and Prejudice', 'Jane Austen', '978-333-0004', 3, 3, 3),
('The Catcher in the Rye', 'J.D. Salinger', '978-333-0005', 2, 2, 3),
('Lord of the Flies', 'William Golding', '978-333-0006', 3, 3, 3),
('Brave New World', 'Aldous Huxley', '978-333-0007', 4, 4, 3),
('The Alchemist', 'Paulo Coelho', '978-333-0008', 5, 4, 3),
('Animal Farm', 'George Orwell', '978-333-0009', 3, 3, 3),
('Sapiens', 'Yuval Noah Harari', '978-444-0002', 4, 4, 4),
('A Brief History of Time', 'Stephen Hawking', '978-444-0003', 3, 3, 4),
('The Diary of Anne Frank', 'Anne Frank', '978-444-0004', 2, 2, 4),
('Guns Germs and Steel', 'Jared Diamond', '978-444-0005', 3, 3, 4),
('Ancient Civilizations', 'Christopher Scarre', '978-444-0007', 4, 4, 4);

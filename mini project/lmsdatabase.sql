CREATE DATABASE digital_library;

USE digital_library;

CREATE TABLE students (
    id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(100),
    email VARCHAR(100),
    password VARCHAR(255)
);

CREATE TABLE staff (
    id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(100),
    libpass varchar(40) default 'lib001',
    password VARCHAR(255)
);
CREATE TABLE books (
    book_id INT PRIMARY KEY,
    book_name VARCHAR(255),
    author_name VARCHAR(255),
    publication_year INT,
    number_of_books INT
);
CREATE TABLE issue_requests (
    request_id INT PRIMARY KEY,
    student_id VARCHAR(50),
    book_id INT,
    status VARCHAR(50),
    approval_date DATE,
    due_date DATE,
    return_date DATE,
    FOREIGN KEY (student_id) REFERENCES students(id),
    FOREIGN KEY (book_id) REFERENCES books(book_id)
);

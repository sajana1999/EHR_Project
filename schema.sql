-- Database Re-Creation Script for EHR System
-- Generated based on app.py analysis

SET FOREIGN_KEY_CHECKS = 0;

-- 1. Create Database
CREATE DATABASE IF NOT EXISTS ehr_system;
USE ehr_system;

-- 2. Drop Tables if they exist (Clean Slate)
DROP TABLE IF EXISTS documents;
DROP TABLE IF EXISTS appointments;
DROP TABLE IF EXISTS patients;
DROP TABLE IF EXISTS doctors;

SET FOREIGN_KEY_CHECKS = 1;

-- 3. Create 'doctors' Table
CREATE TABLE doctors (
    id INT AUTO_INCREMENT PRIMARY KEY,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    doctor_medical_id VARCHAR(50) NOT NULL,
    category VARCHAR(100),
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(120) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    is_verified TINYINT(1) DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. Create 'patients' Table
CREATE TABLE patients (
    id INT AUTO_INCREMENT PRIMARY KEY,
    doctor_id INT NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    insurance_number VARCHAR(50),
    gender VARCHAR(20),
    age INT,
    has_allergies TEXT, -- Changed to TEXT to store comma-separated list
    image_path VARCHAR(255),
    email VARCHAR(120),
    phone VARCHAR(20),
    address TEXT,
    medical_history TEXT,
    is_seen TINYINT(1) DEFAULT 0,
    is_active TINYINT(1) DEFAULT 1, -- Default to Active
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (doctor_id) REFERENCES doctors(id) ON DELETE CASCADE
);

-- 5. Create 'appointments' Table
CREATE TABLE appointments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    patient_id INT NOT NULL,
    doctor_id INT NOT NULL,
    appointment_date DATE NOT NULL,
    appointment_time TIME,
    status VARCHAR(50) DEFAULT 'Scheduled',
    reason_for_visit VARCHAR(255),
    
    -- Vitals (Added from improved workflow)
    blood_pressure VARCHAR(20),
    temperature VARCHAR(10), -- Stored as string or decimal (decided on VARCHAR based on app usage flexibility)
    pulse_rate INT,
    sp_o2 INT,
    weight DECIMAL(5,2),
    
    -- Clinical Data
    final_diagnosis TEXT,
    clinical_notes TEXT,
    prescription TEXT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE CASCADE,
    FOREIGN KEY (doctor_id) REFERENCES doctors(id) ON DELETE CASCADE
);

-- 6. Create 'documents' Table
CREATE TABLE documents (
    id INT AUTO_INCREMENT PRIMARY KEY,
    patient_id INT NOT NULL,
    doctor_id INT NOT NULL,
    file_path VARCHAR(255) NOT NULL,
    document_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE CASCADE,
    FOREIGN KEY (doctor_id) REFERENCES doctors(id) ON DELETE CASCADE
);

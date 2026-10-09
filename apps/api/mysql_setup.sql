-- ==========================================================
-- StudyFlow Database Schema (MySQL 8.0+)
-- Lightweight MCA College Project
-- ==========================================================

CREATE DATABASE IF NOT EXISTS `studyflow` 
  DEFAULT CHARACTER SET utf8mb4 
  DEFAULT COLLATE utf8mb4_unicode_ci;

USE `studyflow`;

-- ----------------------------------------------------------
-- 1. Users Table
-- ----------------------------------------------------------
CREATE TABLE IF NOT EXISTS `users` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `email` VARCHAR(255) NOT NULL UNIQUE,
  `password_hash` VARCHAR(255) NOT NULL,
  `display_name` VARCHAR(100) NOT NULL,
  `college_name` VARCHAR(200) DEFAULT NULL,
  `course_name` VARCHAR(100) DEFAULT NULL,
  `is_active` TINYINT(1) NOT NULL DEFAULT 1,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX `idx_users_email` (`email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------------------------------------
-- 2. Semesters Table
-- ----------------------------------------------------------
CREATE TABLE IF NOT EXISTS `semesters` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `user_id` INT NOT NULL,
  `name` VARCHAR(100) NOT NULL,
  `semester_number` INT DEFAULT NULL,
  `start_date` DATE DEFAULT NULL,
  `end_date` DATE DEFAULT NULL,
  `is_active` TINYINT(1) NOT NULL DEFAULT 1,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX `idx_semesters_user` (`user_id`),
  CONSTRAINT `fk_semesters_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------------------------------------
-- 3. Subjects Table
-- ----------------------------------------------------------
CREATE TABLE IF NOT EXISTS `subjects` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `user_id` INT NOT NULL,
  `semester_id` INT NOT NULL,
  `name` VARCHAR(150) NOT NULL,
  `code` VARCHAR(50) DEFAULT NULL,
  `color` VARCHAR(30) DEFAULT '#4F46E5',
  `credits` INT DEFAULT 3,
  `target_grade` VARCHAR(20) DEFAULT NULL,
  `difficulty_level` VARCHAR(20) DEFAULT 'Medium',
  `description` TEXT DEFAULT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX `idx_subjects_user` (`user_id`),
  INDEX `idx_subjects_semester` (`semester_id`),
  CONSTRAINT `fk_subjects_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_subjects_semester` FOREIGN KEY (`semester_id`) REFERENCES `semesters` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------------------------------------
-- 4. Topics Table
-- ----------------------------------------------------------
CREATE TABLE IF NOT EXISTS `topics` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `user_id` INT NOT NULL,
  `subject_id` INT NOT NULL,
  `name` VARCHAR(200) NOT NULL,
  `description` TEXT DEFAULT NULL,
  `unit_number` INT DEFAULT 1,
  `priority` VARCHAR(20) DEFAULT 'Medium',
  `status` VARCHAR(30) DEFAULT 'Pending',
  `estimated_hours` FLOAT DEFAULT 1.0,
  `completed_hours` FLOAT DEFAULT 0.0,
  `importance_score` INT DEFAULT 3,
  `order_index` INT DEFAULT 0,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX `idx_topics_user` (`user_id`),
  INDEX `idx_topics_subject` (`subject_id`),
  CONSTRAINT `fk_topics_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_topics_subject` FOREIGN KEY (`subject_id`) REFERENCES `subjects` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------------------------------------
-- 5. Exams Table
-- ----------------------------------------------------------
CREATE TABLE IF NOT EXISTS `exams` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `user_id` INT NOT NULL,
  `semester_id` INT DEFAULT NULL,
  `subject_id` INT NOT NULL,
  `title` VARCHAR(150) NOT NULL,
  `exam_type` VARCHAR(50) DEFAULT 'Theory',
  `exam_date` DATE NOT NULL,
  `start_time` VARCHAR(20) DEFAULT NULL,
  `duration_minutes` INT DEFAULT 180,
  `total_marks` FLOAT DEFAULT 100.0,
  `passing_marks` FLOAT DEFAULT 40.0,
  `target_marks` FLOAT DEFAULT NULL,
  `obtained_marks` FLOAT DEFAULT NULL,
  `location` VARCHAR(150) DEFAULT NULL,
  `notes` TEXT DEFAULT NULL,
  `status` VARCHAR(30) DEFAULT 'Upcoming',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX `idx_exams_user` (`user_id`),
  INDEX `idx_exams_semester` (`semester_id`),
  INDEX `idx_exams_subject` (`subject_id`),
  CONSTRAINT `fk_exams_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_exams_semester` FOREIGN KEY (`semester_id`) REFERENCES `semesters` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_exams_subject` FOREIGN KEY (`subject_id`) REFERENCES `subjects` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

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

-- ----------------------------------------------------------
-- 6. Notes Table
-- ----------------------------------------------------------
CREATE TABLE IF NOT EXISTS `notes` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `user_id` INT NOT NULL,
  `subject_id` INT DEFAULT NULL,
  `topic_id` INT DEFAULT NULL,
  `title` VARCHAR(180) NOT NULL,
  `content` MEDIUMTEXT NOT NULL,
  `tags` JSON NOT NULL,
  `is_pinned` TINYINT(1) NOT NULL DEFAULT 0,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX `idx_notes_user` (`user_id`),
  INDEX `idx_notes_subject` (`subject_id`),
  INDEX `idx_notes_topic` (`topic_id`),
  INDEX `idx_notes_user_pinned_updated` (`user_id`, `is_pinned`, `updated_at`),
  CONSTRAINT `fk_notes_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_notes_subject` FOREIGN KEY (`subject_id`) REFERENCES `subjects` (`id`) ON DELETE SET NULL,
  CONSTRAINT `fk_notes_topic` FOREIGN KEY (`topic_id`) REFERENCES `topics` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ==========================================================
-- Phase 4: PDF Intelligence (documents, summaries, quizzes)
-- All statements are additive and idempotent: existing tables and
-- rows are untouched, and re-running this file is safe.
-- The API also creates these tables automatically on startup via
-- SQLAlchemy metadata.create_all.
-- ==========================================================

-- ----------------------------------------------------------
-- 7. Documents (uploaded PDFs + extracted text)
-- ----------------------------------------------------------
CREATE TABLE IF NOT EXISTS `documents` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `user_id` INT NOT NULL,
  `semester_id` INT DEFAULT NULL,
  `subject_id` INT DEFAULT NULL,
  `title` VARCHAR(180) NOT NULL,
  `original_filename` VARCHAR(255) NOT NULL,
  `stored_filename` VARCHAR(255) NOT NULL,
  `file_size_bytes` INT NOT NULL DEFAULT 0,
  `content_hash` VARCHAR(64) NOT NULL,
  `processing_status` VARCHAR(20) NOT NULL DEFAULT 'pending',  -- pending | processing | completed | failed
  `page_count` INT NOT NULL DEFAULT 0,
  `extracted_text` MEDIUMTEXT DEFAULT NULL,
  `page_offsets` JSON DEFAULT NULL,
  `extracted_chars` INT NOT NULL DEFAULT 0,
  `word_count` INT NOT NULL DEFAULT 0,
  `text_truncated` TINYINT(1) NOT NULL DEFAULT 0,
  `error_code` VARCHAR(40) DEFAULT NULL,
  `error_message` VARCHAR(500) DEFAULT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY `uq_documents_user_content_hash` (`user_id`, `content_hash`),
  INDEX `idx_documents_user` (`user_id`),
  INDEX `idx_documents_status` (`processing_status`),
  INDEX `idx_documents_hash` (`content_hash`),
  CONSTRAINT `fk_documents_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_documents_semester` FOREIGN KEY (`semester_id`) REFERENCES `semesters` (`id`) ON DELETE SET NULL,
  CONSTRAINT `fk_documents_subject` FOREIGN KEY (`subject_id`) REFERENCES `subjects` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------------------------------------
-- 8. Document summaries (extractive, generated offline)
-- ----------------------------------------------------------
CREATE TABLE IF NOT EXISTS `document_summaries` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `user_id` INT NOT NULL,
  `document_id` INT DEFAULT NULL,
  `note_id` INT DEFAULT NULL,
  `method` VARCHAR(40) NOT NULL DEFAULT 'extractive',
  `engine_version` VARCHAR(40) NOT NULL,
  `summary_text` MEDIUMTEXT NOT NULL,
  `key_points` JSON NOT NULL,
  `source_chars` INT NOT NULL DEFAULT 0,
  `source_sentences` INT NOT NULL DEFAULT 0,
  `chunk_count` INT NOT NULL DEFAULT 1,
  `word_count` INT NOT NULL DEFAULT 0,
  `warnings` JSON NOT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX `idx_summaries_user` (`user_id`),
  INDEX `idx_summaries_document` (`document_id`),
  INDEX `idx_summaries_note` (`note_id`),
  CONSTRAINT `fk_summaries_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_summaries_document` FOREIGN KEY (`document_id`) REFERENCES `documents` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_summaries_note` FOREIGN KEY (`note_id`) REFERENCES `notes` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------------------------------------
-- 9. Quizzes generated from a document or note
-- ----------------------------------------------------------
CREATE TABLE IF NOT EXISTS `quizzes` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `user_id` INT NOT NULL,
  `document_id` INT DEFAULT NULL,
  `note_id` INT DEFAULT NULL,
  `semester_id` INT DEFAULT NULL,
  `subject_id` INT DEFAULT NULL,
  `title` VARCHAR(180) NOT NULL,
  `method` VARCHAR(40) NOT NULL DEFAULT 'extractive-cloze',
  `engine_version` VARCHAR(40) NOT NULL,
  `requested_count` INT NOT NULL DEFAULT 5,
  `question_count` INT NOT NULL DEFAULT 0,
  `source_chars` INT NOT NULL DEFAULT 0,
  `warnings` JSON NOT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX `idx_quizzes_user` (`user_id`),
  INDEX `idx_quizzes_document` (`document_id`),
  INDEX `idx_quizzes_note` (`note_id`),
  INDEX `idx_quizzes_subject` (`subject_id`),
  CONSTRAINT `fk_quizzes_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_quizzes_document` FOREIGN KEY (`document_id`) REFERENCES `documents` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_quizzes_note` FOREIGN KEY (`note_id`) REFERENCES `notes` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_quizzes_semester` FOREIGN KEY (`semester_id`) REFERENCES `semesters` (`id`) ON DELETE SET NULL,
  CONSTRAINT `fk_quizzes_subject` FOREIGN KEY (`subject_id`) REFERENCES `subjects` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------------------------------------
-- 10. Quiz questions (options + the source text they came from)
-- ----------------------------------------------------------
CREATE TABLE IF NOT EXISTS `quiz_questions` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `quiz_id` INT NOT NULL,
  `order_index` INT NOT NULL DEFAULT 0,
  `question_type` VARCHAR(30) NOT NULL DEFAULT 'cloze',
  `prompt` TEXT NOT NULL,
  `options` JSON NOT NULL,
  `correct_index` INT NOT NULL DEFAULT 0,
  `explanation` TEXT NOT NULL,
  `source_excerpt` VARCHAR(600) DEFAULT NULL,
  `source_page` INT DEFAULT NULL,
  INDEX `idx_questions_quiz` (`quiz_id`),
  CONSTRAINT `fk_questions_quiz` FOREIGN KEY (`quiz_id`) REFERENCES `quizzes` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------------------------------------
-- 11. Quiz attempts (score + timestamp)
-- ----------------------------------------------------------
CREATE TABLE IF NOT EXISTS `quiz_attempts` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `quiz_id` INT NOT NULL,
  `user_id` INT NOT NULL,
  `total_questions` INT NOT NULL DEFAULT 0,
  `correct_count` INT NOT NULL DEFAULT 0,
  `score_percent` FLOAT NOT NULL DEFAULT 0,
  `duration_seconds` INT DEFAULT NULL,
  `submitted_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX `idx_attempts_quiz` (`quiz_id`),
  INDEX `idx_attempts_user` (`user_id`),
  CONSTRAINT `fk_attempts_quiz` FOREIGN KEY (`quiz_id`) REFERENCES `quizzes` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_attempts_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------------------------------------
-- 12. Answers inside an attempt
-- ----------------------------------------------------------
CREATE TABLE IF NOT EXISTS `quiz_attempt_answers` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `attempt_id` INT NOT NULL,
  `question_id` INT NOT NULL,
  `selected_index` INT DEFAULT NULL,
  `is_correct` TINYINT(1) NOT NULL DEFAULT 0,
  INDEX `idx_answers_attempt` (`attempt_id`),
  INDEX `idx_answers_question` (`question_id`),
  CONSTRAINT `fk_answers_attempt` FOREIGN KEY (`attempt_id`) REFERENCES `quiz_attempts` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_answers_question` FOREIGN KEY (`question_id`) REFERENCES `quiz_questions` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

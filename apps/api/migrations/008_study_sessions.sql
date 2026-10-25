-- Phase 6: Study-time tracking (manual-start sessions with pause/resume)
-- Backend-validated elapsed time; no browser-only countdown.

CREATE TABLE IF NOT EXISTS `study_sessions` (
  `active_slot` INT DEFAULT 1,
  `version` INT NOT NULL DEFAULT 1,
  UNIQUE KEY `uq_session_open` (`user_id`, `active_slot`),
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `user_id` INT NOT NULL,
  `subject_id` INT DEFAULT NULL,
  `topic_id` INT DEFAULT NULL,
  `status` VARCHAR(20) NOT NULL DEFAULT 'active',
  `started_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `paused_at` DATETIME DEFAULT NULL,
  `accumulated_seconds` INT NOT NULL DEFAULT 0,
  `duration_seconds` INT DEFAULT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX `idx_study_sessions_user` (`user_id`),
  INDEX `idx_study_sessions_subject` (`subject_id`),
  INDEX `idx_study_sessions_status` (`status`),
  CONSTRAINT `fk_study_sessions_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_study_sessions_subject` FOREIGN KEY (`subject_id`) REFERENCES `subjects` (`id`) ON DELETE SET NULL,
  CONSTRAINT `fk_study_sessions_topic` FOREIGN KEY (`topic_id`) REFERENCES `topics` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

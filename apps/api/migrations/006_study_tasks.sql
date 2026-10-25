-- Phase 6: Standalone Study Tasks (general planner, distinct from Sprint tasks)
-- Additive and idempotent: safe to rerun; preserves existing data.

CREATE TABLE IF NOT EXISTS `study_tasks` (
  `content_key` VARCHAR(64) NOT NULL,
  UNIQUE KEY `uq_task_content` (`user_id`, `content_key`),
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `user_id` INT NOT NULL,
  `subject_id` INT DEFAULT NULL,
  `topic_id` INT DEFAULT NULL,
  `exam_id` INT DEFAULT NULL,
  `title` VARCHAR(180) NOT NULL,
  `description` TEXT DEFAULT NULL,
  `due_date` DATE DEFAULT NULL,
  `estimated_minutes` INT DEFAULT NULL,
  `priority` VARCHAR(20) NOT NULL DEFAULT 'Medium',
  `status` VARCHAR(30) NOT NULL DEFAULT 'Pending',
  `completed_at` DATETIME DEFAULT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX `idx_study_tasks_user` (`user_id`),
  INDEX `idx_study_tasks_subject` (`subject_id`),
  INDEX `idx_study_tasks_topic` (`topic_id`),
  INDEX `idx_study_tasks_exam` (`exam_id`),
  INDEX `idx_study_tasks_status` (`status`),
  INDEX `idx_study_tasks_due` (`due_date`),
  CONSTRAINT `fk_study_tasks_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_study_tasks_subject` FOREIGN KEY (`subject_id`) REFERENCES `subjects` (`id`) ON DELETE SET NULL,
  CONSTRAINT `fk_study_tasks_topic` FOREIGN KEY (`topic_id`) REFERENCES `topics` (`id`) ON DELETE SET NULL,
  CONSTRAINT `fk_study_tasks_exam` FOREIGN KEY (`exam_id`) REFERENCES `exams` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

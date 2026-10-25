-- Phase 6: Flashcards (basic flip-card review, no spaced repetition scheduler)
-- Additive and idempotent.

CREATE TABLE IF NOT EXISTS `flashcards` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `user_id` INT NOT NULL,
  `subject_id` INT DEFAULT NULL,
  `topic_id` INT DEFAULT NULL,
  `front` TEXT NOT NULL,
  `back` TEXT NOT NULL,
  `review_status` VARCHAR(20) NOT NULL DEFAULT 'needs_revision',
  `is_generated` TINYINT(1) NOT NULL DEFAULT 0,
  `source_type` VARCHAR(20) DEFAULT NULL,
  `source_id` INT DEFAULT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `last_reviewed_at` DATETIME DEFAULT NULL,
  INDEX `idx_flashcards_user` (`user_id`),
  INDEX `idx_flashcards_subject` (`subject_id`),
  INDEX `idx_flashcards_topic` (`topic_id`),
  INDEX `idx_flashcards_review` (`review_status`),
  CONSTRAINT `fk_flashcards_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_flashcards_subject` FOREIGN KEY (`subject_id`) REFERENCES `subjects` (`id`) ON DELETE SET NULL,
  CONSTRAINT `fk_flashcards_topic` FOREIGN KEY (`topic_id`) REFERENCES `topics` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

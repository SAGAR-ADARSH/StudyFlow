-- Phase 5: Sprint Mode (additive, preserves existing data)
CREATE TABLE IF NOT EXISTS `sprints` (
	`id` INTEGER NOT NULL AUTO_INCREMENT,
	`user_id` INTEGER NOT NULL,
	`exam_id` INTEGER NOT NULL,
	`status` VARCHAR(20) NOT NULL,
	`daily_minutes` INTEGER NOT NULL,
	`timezone` VARCHAR(64) NOT NULL,
	`created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (id),
	CONSTRAINT uq_sprint_user_exam UNIQUE (user_id, exam_id),
	INDEX ix_sprints_user_id (user_id),
	INDEX ix_sprints_exam_id (exam_id),
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE,
	FOREIGN KEY(exam_id) REFERENCES exams (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
CREATE TABLE IF NOT EXISTS `sprint_days` (
	`id` INTEGER NOT NULL AUTO_INCREMENT,
	`sprint_id` INTEGER NOT NULL,
	`plan_date` DATE NOT NULL,
	`budget_minutes` INTEGER NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_sprint_day UNIQUE (sprint_id, plan_date),
	INDEX ix_sprint_days_sprint_id (sprint_id),
	FOREIGN KEY(sprint_id) REFERENCES sprints (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
CREATE TABLE IF NOT EXISTS `sprint_tasks` (
	`id` INTEGER NOT NULL AUTO_INCREMENT,
	`day_id` INTEGER NOT NULL,
	`topic_id` INTEGER,
	`task_key` VARCHAR(80) NOT NULL,
	`kind` VARCHAR(20) NOT NULL,
	`title` VARCHAR(255) NOT NULL,
	`minutes` INTEGER NOT NULL,
	`priority` INTEGER NOT NULL,
	`reason` VARCHAR(600) NOT NULL,
	`completed` BOOL NOT NULL,
	`completed_at` DATETIME,
	PRIMARY KEY (id),
	CONSTRAINT uq_sprint_day_task UNIQUE (day_id, task_key),
	INDEX ix_sprint_tasks_day_id (day_id),
	FOREIGN KEY(day_id) REFERENCES sprint_days (id) ON DELETE CASCADE,
	FOREIGN KEY(topic_id) REFERENCES topics (id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

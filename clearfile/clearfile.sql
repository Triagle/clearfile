BEGIN TRANSACTION;
CREATE TABLE IF NOT EXISTS `tags` (
	`id`	INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
	`uuid`	TEXT,
	`tag`	TEXT,
	FOREIGN KEY(`uuid`) REFERENCES `notes`(`uuid`) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS `notebooks` (
  `id` INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
  `name` TEXT
);
CREATE TABLE IF NOT EXISTS `notes` (
	`uuid`	TEXT,
	`name`	TEXT,
	`ocr_text`	TEXT,
  `notebook` INTEGER,
	PRIMARY KEY(`uuid`),
  FOREIGN KEY(`notebook`) REFERENCES `notebooks`(`id`) ON DELETE SET NULL
);
COMMIT;
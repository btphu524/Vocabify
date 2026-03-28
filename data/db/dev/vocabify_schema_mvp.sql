--CREATE DATABASE Vocabify

/*
  Vocabify schema v3 (single clean version)
  - 1 user -> 1 role
  - Placement test: only new user, one-time
  - Learning model: level -> topic -> lesson -> exercise
  - Unlock next level when user completes all lessons/topics of current level
*/

SET ANSI_NULLS ON;
SET QUOTED_IDENTIFIER ON;
GO

CREATE TABLE dbo.roles (
    id INT IDENTITY(1,1) NOT NULL PRIMARY KEY,
    code NVARCHAR(30) NOT NULL,
    name NVARCHAR(100) NOT NULL,
    description NVARCHAR(500) NULL,
    created_at DATETIME2 NOT NULL CONSTRAINT DF_roles_created_at DEFAULT SYSUTCDATETIME(),
    CONSTRAINT UQ_roles_code UNIQUE (code)
);
GO

CREATE TABLE dbo.levels (
    id INT IDENTITY(1,1) NOT NULL PRIMARY KEY,
    code NVARCHAR(50) NOT NULL,
    name NVARCHAR(100) NOT NULL,
    [order] INT NOT NULL,
    description NVARCHAR(500) NULL,
    created_at DATETIME2 NOT NULL CONSTRAINT DF_levels_created_at DEFAULT SYSUTCDATETIME(),
    updated_at DATETIME2 NOT NULL CONSTRAINT DF_levels_updated_at DEFAULT SYSUTCDATETIME(),
    CONSTRAINT UQ_levels_code UNIQUE (code),
    CONSTRAINT UQ_levels_order UNIQUE ([order])
);
GO

CREATE TABLE dbo.users (
    id UNIQUEIDENTIFIER NOT NULL CONSTRAINT PK_users PRIMARY KEY DEFAULT NEWID(),
    email NVARCHAR(320) NOT NULL,
    password_hash NVARCHAR(500) NOT NULL,
    display_name NVARCHAR(100) NULL,
    role_id INT NOT NULL,
    current_level_id INT NULL,
    streak_days INT NOT NULL CONSTRAINT DF_users_streak_days DEFAULT 0,
    created_at DATETIME2 NOT NULL CONSTRAINT DF_users_created_at DEFAULT SYSUTCDATETIME(),
    updated_at DATETIME2 NOT NULL CONSTRAINT DF_users_updated_at DEFAULT SYSUTCDATETIME(),
    CONSTRAINT UQ_users_email UNIQUE (email),
    CONSTRAINT FK_users_role FOREIGN KEY (role_id) REFERENCES dbo.roles(id),
    CONSTRAINT FK_users_current_level FOREIGN KEY (current_level_id) REFERENCES dbo.levels(id)
);
GO

CREATE TABLE dbo.topics (
    id UNIQUEIDENTIFIER NOT NULL CONSTRAINT PK_topics PRIMARY KEY DEFAULT NEWID(),
    level_id INT NOT NULL,
    slug NVARCHAR(120) NOT NULL,
    name NVARCHAR(200) NOT NULL,
    description NVARCHAR(500) NULL,
    [order] INT NOT NULL,
    is_active BIT NOT NULL CONSTRAINT DF_topics_is_active DEFAULT 1,
    created_at DATETIME2 NOT NULL CONSTRAINT DF_topics_created_at DEFAULT SYSUTCDATETIME(),
    updated_at DATETIME2 NOT NULL CONSTRAINT DF_topics_updated_at DEFAULT SYSUTCDATETIME(),
    CONSTRAINT FK_topics_level FOREIGN KEY (level_id) REFERENCES dbo.levels(id),
    CONSTRAINT UQ_topics_level_slug UNIQUE (level_id, slug),
    CONSTRAINT UQ_topics_level_order UNIQUE (level_id, [order])
);
GO

CREATE TABLE dbo.vocabulary (
    id UNIQUEIDENTIFIER NOT NULL CONSTRAINT PK_vocabulary PRIMARY KEY DEFAULT NEWID(),
    topic_id UNIQUEIDENTIFIER NOT NULL,
    word NVARCHAR(120) NOT NULL,
    phonetic NVARCHAR(120) NULL,
    audio_url NVARCHAR(500) NULL,
    part_of_speech NVARCHAR(50) NULL,
    definition_en NVARCHAR(MAX) NULL,
    definition_vi NVARCHAR(MAX) NULL,
    meaning_vi NVARCHAR(500) NULL,
    created_at DATETIME2 NOT NULL CONSTRAINT DF_vocabulary_created_at DEFAULT SYSUTCDATETIME(),
    updated_at DATETIME2 NOT NULL CONSTRAINT DF_vocabulary_updated_at DEFAULT SYSUTCDATETIME(),
    CONSTRAINT FK_vocabulary_topic FOREIGN KEY (topic_id) REFERENCES dbo.topics(id),
    CONSTRAINT UQ_vocabulary_topic_word UNIQUE (topic_id, word)
);
GO

CREATE TABLE dbo.vocab_examples (
    id UNIQUEIDENTIFIER NOT NULL CONSTRAINT PK_vocab_examples PRIMARY KEY DEFAULT NEWID(),
    vocabulary_id UNIQUEIDENTIFIER NOT NULL,
    example_en NVARCHAR(1000) NOT NULL,
    example_vi NVARCHAR(1000) NULL,
    order_no INT NOT NULL,
    created_at DATETIME2 NOT NULL CONSTRAINT DF_vocab_examples_created_at DEFAULT SYSUTCDATETIME(),
    CONSTRAINT FK_vocab_examples_vocabulary FOREIGN KEY (vocabulary_id) REFERENCES dbo.vocabulary(id) ON DELETE CASCADE,
    CONSTRAINT UQ_vocab_examples_vocab_order UNIQUE (vocabulary_id, order_no)
);
GO

CREATE TABLE dbo.lessons (
    id UNIQUEIDENTIFIER NOT NULL CONSTRAINT PK_lessons PRIMARY KEY DEFAULT NEWID(),
    topic_id UNIQUEIDENTIFIER NOT NULL,
    title NVARCHAR(200) NOT NULL,
    description NVARCHAR(1000) NULL,
    [order] INT NOT NULL,
    pass_score INT NOT NULL CONSTRAINT DF_lessons_pass_score DEFAULT 70,
    is_active BIT NOT NULL CONSTRAINT DF_lessons_is_active DEFAULT 1,
    created_at DATETIME2 NOT NULL CONSTRAINT DF_lessons_created_at DEFAULT SYSUTCDATETIME(),
    updated_at DATETIME2 NOT NULL CONSTRAINT DF_lessons_updated_at DEFAULT SYSUTCDATETIME(),
    CONSTRAINT FK_lessons_topic FOREIGN KEY (topic_id) REFERENCES dbo.topics(id) ON DELETE CASCADE,
    CONSTRAINT UQ_lessons_topic_order UNIQUE (topic_id, [order])
);
GO

CREATE TABLE dbo.lesson_items (
    id UNIQUEIDENTIFIER NOT NULL CONSTRAINT PK_lesson_items PRIMARY KEY DEFAULT NEWID(),
    lesson_id UNIQUEIDENTIFIER NOT NULL,
    vocabulary_id UNIQUEIDENTIFIER NOT NULL,
    order_no INT NOT NULL,
    is_required BIT NOT NULL CONSTRAINT DF_lesson_items_is_required DEFAULT 1,
    created_at DATETIME2 NOT NULL CONSTRAINT DF_lesson_items_created_at DEFAULT SYSUTCDATETIME(),
    CONSTRAINT FK_lesson_items_lesson FOREIGN KEY (lesson_id) REFERENCES dbo.lessons(id) ON DELETE CASCADE,
    CONSTRAINT FK_lesson_items_vocabulary FOREIGN KEY (vocabulary_id) REFERENCES dbo.vocabulary(id),
    CONSTRAINT UQ_lesson_items_lesson_order UNIQUE (lesson_id, order_no),
    CONSTRAINT UQ_lesson_items_lesson_vocab UNIQUE (lesson_id, vocabulary_id)
);
GO

CREATE TABLE dbo.lesson_exercises (
    id UNIQUEIDENTIFIER NOT NULL CONSTRAINT PK_lesson_exercises PRIMARY KEY DEFAULT NEWID(),
    lesson_id UNIQUEIDENTIFIER NOT NULL,
    vocabulary_id UNIQUEIDENTIFIER NULL,
    exercise_type NVARCHAR(40) NOT NULL,
    prompt_text NVARCHAR(1000) NULL,
    prompt_json NVARCHAR(MAX) NULL,
    audio_url NVARCHAR(500) NULL,
    correct_answer_text NVARCHAR(1000) NULL,
    correct_answer_json NVARCHAR(MAX) NULL,
    [order] INT NOT NULL,
    points INT NOT NULL CONSTRAINT DF_lesson_exercises_points DEFAULT 1,
    created_at DATETIME2 NOT NULL CONSTRAINT DF_lesson_exercises_created_at DEFAULT SYSUTCDATETIME(),
    updated_at DATETIME2 NOT NULL CONSTRAINT DF_lesson_exercises_updated_at DEFAULT SYSUTCDATETIME(),
    CONSTRAINT FK_lesson_exercises_lesson FOREIGN KEY (lesson_id) REFERENCES dbo.lessons(id) ON DELETE CASCADE,
    CONSTRAINT FK_lesson_exercises_vocabulary FOREIGN KEY (vocabulary_id) REFERENCES dbo.vocabulary(id),
    CONSTRAINT UQ_lesson_exercises_lesson_order UNIQUE (lesson_id, [order]),
    CONSTRAINT CK_lesson_exercises_type CHECK (exercise_type IN (
        N'en_to_vi_choice',
        N'vi_to_en_choice',
        N'sentence_order',
        N'audio_choice'
    ))
);
GO

CREATE TABLE dbo.lesson_exercise_options (
    id UNIQUEIDENTIFIER NOT NULL CONSTRAINT PK_lesson_exercise_options PRIMARY KEY DEFAULT NEWID(),
    exercise_id UNIQUEIDENTIFIER NOT NULL,
    option_text NVARCHAR(500) NULL,
    option_json NVARCHAR(MAX) NULL,
    is_correct BIT NOT NULL,
    [order] INT NOT NULL,
    created_at DATETIME2 NOT NULL CONSTRAINT DF_lesson_exercise_options_created_at DEFAULT SYSUTCDATETIME(),
    CONSTRAINT FK_lesson_exercise_options_exercise FOREIGN KEY (exercise_id) REFERENCES dbo.lesson_exercises(id) ON DELETE CASCADE,
    CONSTRAINT UQ_lesson_exercise_options_order UNIQUE (exercise_id, [order])
);
GO

CREATE TABLE dbo.lesson_attempts (
    id UNIQUEIDENTIFIER NOT NULL CONSTRAINT PK_lesson_attempts PRIMARY KEY DEFAULT NEWID(),
    user_id UNIQUEIDENTIFIER NOT NULL,
    lesson_id UNIQUEIDENTIFIER NOT NULL,
    started_at DATETIME2 NOT NULL CONSTRAINT DF_lesson_attempts_started_at DEFAULT SYSUTCDATETIME(),
    finished_at DATETIME2 NULL,
    score INT NOT NULL CONSTRAINT DF_lesson_attempts_score DEFAULT 0,
    max_score INT NOT NULL CONSTRAINT DF_lesson_attempts_max_score DEFAULT 0,
    accuracy_percent DECIMAL(5,2) NOT NULL CONSTRAINT DF_lesson_attempts_accuracy DEFAULT 0,
    is_passed BIT NOT NULL CONSTRAINT DF_lesson_attempts_is_passed DEFAULT 0,
    created_at DATETIME2 NOT NULL CONSTRAINT DF_lesson_attempts_created_at DEFAULT SYSUTCDATETIME(),
    CONSTRAINT FK_lesson_attempts_user FOREIGN KEY (user_id) REFERENCES dbo.users(id) ON DELETE CASCADE,
    CONSTRAINT FK_lesson_attempts_lesson FOREIGN KEY (lesson_id) REFERENCES dbo.lessons(id) ON DELETE CASCADE
);
GO

CREATE TABLE dbo.lesson_attempt_answers (
    id UNIQUEIDENTIFIER NOT NULL CONSTRAINT PK_lesson_attempt_answers PRIMARY KEY DEFAULT NEWID(),
    attempt_id UNIQUEIDENTIFIER NOT NULL,
    exercise_id UNIQUEIDENTIFIER NOT NULL,
    selected_option_id UNIQUEIDENTIFIER NULL,
    answer_text NVARCHAR(1000) NULL,
    answer_json NVARCHAR(MAX) NULL,
    is_correct BIT NOT NULL CONSTRAINT DF_lesson_attempt_answers_is_correct DEFAULT 0,
    earned_points INT NOT NULL CONSTRAINT DF_lesson_attempt_answers_points DEFAULT 0,
    created_at DATETIME2 NOT NULL CONSTRAINT DF_lesson_attempt_answers_created_at DEFAULT SYSUTCDATETIME(),
    CONSTRAINT FK_lesson_attempt_answers_attempt FOREIGN KEY (attempt_id) REFERENCES dbo.lesson_attempts(id) ON DELETE CASCADE,
    CONSTRAINT FK_lesson_attempt_answers_exercise FOREIGN KEY (exercise_id) REFERENCES dbo.lesson_exercises(id),
    CONSTRAINT FK_lesson_attempt_answers_selected_option FOREIGN KEY (selected_option_id) REFERENCES dbo.lesson_exercise_options(id),
    CONSTRAINT UQ_lesson_attempt_answer_once UNIQUE (attempt_id, exercise_id)
);
GO

CREATE TABLE dbo.placement_questions (
    id UNIQUEIDENTIFIER NOT NULL CONSTRAINT PK_placement_questions PRIMARY KEY DEFAULT NEWID(),
    level_id INT NOT NULL,
    question_text NVARCHAR(1000) NOT NULL,
    explanation NVARCHAR(1000) NULL,
    is_active BIT NOT NULL CONSTRAINT DF_placement_questions_is_active DEFAULT 1,
    created_at DATETIME2 NOT NULL CONSTRAINT DF_placement_questions_created_at DEFAULT SYSUTCDATETIME(),
    updated_at DATETIME2 NOT NULL CONSTRAINT DF_placement_questions_updated_at DEFAULT SYSUTCDATETIME(),
    CONSTRAINT FK_placement_questions_level FOREIGN KEY (level_id) REFERENCES dbo.levels(id)
);
GO

CREATE TABLE dbo.placement_options (
    id UNIQUEIDENTIFIER NOT NULL CONSTRAINT PK_placement_options PRIMARY KEY DEFAULT NEWID(),
    question_id UNIQUEIDENTIFIER NOT NULL,
    option_text NVARCHAR(500) NOT NULL,
    is_correct BIT NOT NULL,
    score INT NOT NULL CONSTRAINT DF_placement_options_score DEFAULT 0,
    created_at DATETIME2 NOT NULL CONSTRAINT DF_placement_options_created_at DEFAULT SYSUTCDATETIME(),
    CONSTRAINT FK_placement_options_question FOREIGN KEY (question_id) REFERENCES dbo.placement_questions(id) ON DELETE CASCADE
);
GO

CREATE TABLE dbo.placement_attempts (
    id UNIQUEIDENTIFIER NOT NULL CONSTRAINT PK_placement_attempts PRIMARY KEY DEFAULT NEWID(),
    user_id UNIQUEIDENTIFIER NOT NULL,
    started_at DATETIME2 NOT NULL CONSTRAINT DF_placement_attempts_started_at DEFAULT SYSUTCDATETIME(),
    finished_at DATETIME2 NULL,
    total_score INT NOT NULL CONSTRAINT DF_placement_attempts_total_score DEFAULT 0,
    assigned_level_id INT NOT NULL,
    created_at DATETIME2 NOT NULL CONSTRAINT DF_placement_attempts_created_at DEFAULT SYSUTCDATETIME(),
    CONSTRAINT FK_placement_attempts_user FOREIGN KEY (user_id) REFERENCES dbo.users(id),
    CONSTRAINT FK_placement_attempts_assigned_level FOREIGN KEY (assigned_level_id) REFERENCES dbo.levels(id),
    CONSTRAINT UQ_placement_attempts_user UNIQUE (user_id)
);
GO

CREATE TABLE dbo.placement_attempt_answers (
    id UNIQUEIDENTIFIER NOT NULL CONSTRAINT PK_placement_attempt_answers PRIMARY KEY DEFAULT NEWID(),
    attempt_id UNIQUEIDENTIFIER NOT NULL,
    question_id UNIQUEIDENTIFIER NOT NULL,
    selected_option_id UNIQUEIDENTIFIER NULL,
    is_correct BIT NOT NULL CONSTRAINT DF_placement_attempt_answers_is_correct DEFAULT 0,
    earned_score INT NOT NULL CONSTRAINT DF_placement_attempt_answers_earned_score DEFAULT 0,
    created_at DATETIME2 NOT NULL CONSTRAINT DF_placement_attempt_answers_created_at DEFAULT SYSUTCDATETIME(),
    CONSTRAINT FK_placement_answers_attempt FOREIGN KEY (attempt_id) REFERENCES dbo.placement_attempts(id) ON DELETE CASCADE,
    CONSTRAINT FK_placement_answers_question FOREIGN KEY (question_id) REFERENCES dbo.placement_questions(id),
    CONSTRAINT FK_placement_answers_option FOREIGN KEY (selected_option_id) REFERENCES dbo.placement_options(id),
    CONSTRAINT UQ_placement_attempt_question UNIQUE (attempt_id, question_id)
);
GO

CREATE TABLE dbo.user_vocab_progress (
    id UNIQUEIDENTIFIER NOT NULL CONSTRAINT PK_user_vocab_progress PRIMARY KEY DEFAULT NEWID(),
    user_id UNIQUEIDENTIFIER NOT NULL,
    vocabulary_id UNIQUEIDENTIFIER NOT NULL,
    status NVARCHAR(20) NOT NULL CONSTRAINT DF_user_vocab_progress_status DEFAULT N'new',
    correct_count INT NOT NULL CONSTRAINT DF_user_vocab_progress_correct_count DEFAULT 0,
    wrong_count INT NOT NULL CONSTRAINT DF_user_vocab_progress_wrong_count DEFAULT 0,
    last_reviewed_at DATETIME2 NULL,
    next_review_at DATETIME2 NULL,
    created_at DATETIME2 NOT NULL CONSTRAINT DF_user_vocab_progress_created_at DEFAULT SYSUTCDATETIME(),
    updated_at DATETIME2 NOT NULL CONSTRAINT DF_user_vocab_progress_updated_at DEFAULT SYSUTCDATETIME(),
    CONSTRAINT FK_user_vocab_progress_user FOREIGN KEY (user_id) REFERENCES dbo.users(id) ON DELETE CASCADE,
    CONSTRAINT FK_user_vocab_progress_vocabulary FOREIGN KEY (vocabulary_id) REFERENCES dbo.vocabulary(id) ON DELETE CASCADE,
    CONSTRAINT UQ_user_vocab_progress_user_vocab UNIQUE (user_id, vocabulary_id),
    CONSTRAINT CK_user_vocab_progress_status CHECK (status IN (N'new', N'learning', N'review', N'mastered'))
);
GO

CREATE TABLE dbo.user_lesson_progress (
    id UNIQUEIDENTIFIER NOT NULL CONSTRAINT PK_user_lesson_progress PRIMARY KEY DEFAULT NEWID(),
    user_id UNIQUEIDENTIFIER NOT NULL,
    lesson_id UNIQUEIDENTIFIER NOT NULL,
    best_score INT NOT NULL CONSTRAINT DF_user_lesson_progress_best_score DEFAULT 0,
    best_accuracy_percent DECIMAL(5,2) NOT NULL CONSTRAINT DF_user_lesson_progress_best_acc DEFAULT 0,
    attempts_count INT NOT NULL CONSTRAINT DF_user_lesson_progress_attempts DEFAULT 0,
    status NVARCHAR(20) NOT NULL CONSTRAINT DF_user_lesson_progress_status DEFAULT N'not_started',
    first_completed_at DATETIME2 NULL,
    last_activity_at DATETIME2 NULL,
    created_at DATETIME2 NOT NULL CONSTRAINT DF_user_lesson_progress_created_at DEFAULT SYSUTCDATETIME(),
    updated_at DATETIME2 NOT NULL CONSTRAINT DF_user_lesson_progress_updated_at DEFAULT SYSUTCDATETIME(),
    CONSTRAINT FK_user_lesson_progress_user FOREIGN KEY (user_id) REFERENCES dbo.users(id) ON DELETE CASCADE,
    CONSTRAINT FK_user_lesson_progress_lesson FOREIGN KEY (lesson_id) REFERENCES dbo.lessons(id) ON DELETE CASCADE,
    CONSTRAINT UQ_user_lesson_progress_user_lesson UNIQUE (user_id, lesson_id),
    CONSTRAINT CK_user_lesson_progress_status CHECK (status IN (N'not_started', N'in_progress', N'completed'))
);
GO

CREATE TABLE dbo.user_topic_progress (
    id UNIQUEIDENTIFIER NOT NULL CONSTRAINT PK_user_topic_progress PRIMARY KEY DEFAULT NEWID(),
    user_id UNIQUEIDENTIFIER NOT NULL,
    topic_id UNIQUEIDENTIFIER NOT NULL,
    total_lessons INT NOT NULL CONSTRAINT DF_user_topic_progress_total_lessons DEFAULT 0,
    completed_lessons INT NOT NULL CONSTRAINT DF_user_topic_progress_completed_lessons DEFAULT 0,
    completion_percent DECIMAL(5,2) NOT NULL CONSTRAINT DF_user_topic_progress_completion DEFAULT 0,
    status NVARCHAR(20) NOT NULL CONSTRAINT DF_user_topic_progress_status DEFAULT N'not_started',
    completed_at DATETIME2 NULL,
    updated_at DATETIME2 NOT NULL CONSTRAINT DF_user_topic_progress_updated_at DEFAULT SYSUTCDATETIME(),
    CONSTRAINT FK_user_topic_progress_user FOREIGN KEY (user_id) REFERENCES dbo.users(id) ON DELETE CASCADE,
    CONSTRAINT FK_user_topic_progress_topic FOREIGN KEY (topic_id) REFERENCES dbo.topics(id) ON DELETE CASCADE,
    CONSTRAINT UQ_user_topic_progress_user_topic UNIQUE (user_id, topic_id),
    CONSTRAINT CK_user_topic_progress_status CHECK (status IN (N'not_started', N'in_progress', N'completed'))
);
GO

CREATE TABLE dbo.user_level_progress (
    id UNIQUEIDENTIFIER NOT NULL CONSTRAINT PK_user_level_progress PRIMARY KEY DEFAULT NEWID(),
    user_id UNIQUEIDENTIFIER NOT NULL,
    level_id INT NOT NULL,
    total_topics INT NOT NULL CONSTRAINT DF_user_level_progress_total_topics DEFAULT 0,
    completed_topics INT NOT NULL CONSTRAINT DF_user_level_progress_completed_topics DEFAULT 0,
    completion_percent DECIMAL(5,2) NOT NULL CONSTRAINT DF_user_level_progress_completion DEFAULT 0,
    is_unlocked BIT NOT NULL CONSTRAINT DF_user_level_progress_unlocked DEFAULT 0,
    unlocked_at DATETIME2 NULL,
    is_completed BIT NOT NULL CONSTRAINT DF_user_level_progress_completed DEFAULT 0,
    completed_at DATETIME2 NULL,
    updated_at DATETIME2 NOT NULL CONSTRAINT DF_user_level_progress_updated_at DEFAULT SYSUTCDATETIME(),
    CONSTRAINT FK_user_level_progress_user FOREIGN KEY (user_id) REFERENCES dbo.users(id) ON DELETE CASCADE,
    CONSTRAINT FK_user_level_progress_level FOREIGN KEY (level_id) REFERENCES dbo.levels(id),
    CONSTRAINT UQ_user_level_progress_user_level UNIQUE (user_id, level_id)
);
GO

CREATE INDEX IX_users_role_id ON dbo.users(role_id);
CREATE INDEX IX_users_current_level_id ON dbo.users(current_level_id);
CREATE INDEX IX_topics_level_id ON dbo.topics(level_id);
CREATE INDEX IX_vocabulary_topic_id ON dbo.vocabulary(topic_id);
CREATE INDEX IX_lessons_topic_id ON dbo.lessons(topic_id);
CREATE INDEX IX_lesson_items_lesson_id ON dbo.lesson_items(lesson_id);
CREATE INDEX IX_lesson_exercises_lesson_id ON dbo.lesson_exercises(lesson_id);
CREATE INDEX IX_lesson_exercises_vocab_id ON dbo.lesson_exercises(vocabulary_id);
CREATE INDEX IX_lesson_attempts_user_lesson ON dbo.lesson_attempts(user_id, lesson_id);
CREATE INDEX IX_placement_questions_level_id ON dbo.placement_questions(level_id);
CREATE INDEX IX_user_vocab_progress_user_id ON dbo.user_vocab_progress(user_id);
CREATE INDEX IX_user_lesson_progress_user_id ON dbo.user_lesson_progress(user_id);
CREATE INDEX IX_user_topic_progress_user_id ON dbo.user_topic_progress(user_id);
CREATE INDEX IX_user_level_progress_user_id ON dbo.user_level_progress(user_id);
GO

IF NOT EXISTS (SELECT 1 FROM dbo.roles WHERE code = N'learner')
INSERT INTO dbo.roles (code, name, description) VALUES
(N'learner', N'Learner', N'Normal user account');

IF NOT EXISTS (SELECT 1 FROM dbo.roles WHERE code = N'admin')
INSERT INTO dbo.roles (code, name, description) VALUES
(N'admin', N'Administrator', N'Admin account');

IF NOT EXISTS (SELECT 1 FROM dbo.levels WHERE code = N'easy')
INSERT INTO dbo.levels (code, name, [order], description) VALUES
(N'easy', N'Easy', 1, N'Beginner vocabulary');

IF NOT EXISTS (SELECT 1 FROM dbo.levels WHERE code = N'medium')
INSERT INTO dbo.levels (code, name, [order], description) VALUES
(N'medium', N'Medium', 2, N'Elementary vocabulary');

IF NOT EXISTS (SELECT 1 FROM dbo.levels WHERE code = N'intermediate')
INSERT INTO dbo.levels (code, name, [order], description) VALUES
(N'intermediate', N'Intermediate', 3, N'Intermediate vocabulary');

IF NOT EXISTS (SELECT 1 FROM dbo.levels WHERE code = N'upper_intermediate')
INSERT INTO dbo.levels (code, name, [order], description) VALUES
(N'upper_intermediate', N'Upper Intermediate', 4, N'Upper-intermediate vocabulary');

IF NOT EXISTS (SELECT 1 FROM dbo.levels WHERE code = N'advanced')
INSERT INTO dbo.levels (code, name, [order], description) VALUES
(N'advanced', N'Advanced', 5, N'Advanced vocabulary');
GO

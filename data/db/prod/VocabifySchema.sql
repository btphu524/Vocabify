--CREATE DATABASE Vocabify;
USE Vocabify;
-- GO
-- USE Vocabify;
-- GO

/*
  Vocabify Schema V4
  - 1 user -> 1 role
  - Placement test: one-time per user
  - Learning model: Level -> Topic -> Lesson -> Exercise
  - Lesson pass rule: Accuracy >= 80
  - Exercise kinds: dbo.ExerciseTypes + LessonExercises.ExerciseTypeId
  - PromptJson / CorrectAnswerJson: flexible payloads per type (see comment above LessonExercises)
*/

SET ANSI_NULLS ON;
SET QUOTED_IDENTIFIER ON;
GO

/* ==================================================
   Table: Roles
================================================== */
CREATE TABLE dbo.Roles (
    Id INT IDENTITY(1,1) NOT NULL CONSTRAINT PkRoles PRIMARY KEY,
    Code NVARCHAR(30) NOT NULL,
    Name NVARCHAR(100) NOT NULL,
    Description NVARCHAR(500) NULL,
    CreatedAt DATETIME2 NOT NULL CONSTRAINT DfRolesCreatedAt DEFAULT SYSUTCDATETIME(),
    UpdatedAt DATETIME2 NULL,
    IsActive BIT NOT NULL CONSTRAINT DfRolesIsActive DEFAULT 1,
    IsDeleted BIT NOT NULL CONSTRAINT DfRolesIsDeleted DEFAULT 0,
    CONSTRAINT UqRolesCode UNIQUE (Code),
    CONSTRAINT UqRolesName UNIQUE (Name)
);
GO

/* ==================================================
   Table: Levels
================================================== */
CREATE TABLE dbo.Levels (
    Id INT IDENTITY(1,1) NOT NULL CONSTRAINT PkLevels PRIMARY KEY,
    Code NVARCHAR(30) NOT NULL,
    Name NVARCHAR(100) NOT NULL,
    SortOrder INT NOT NULL,
    Description NVARCHAR(500) NULL,
    CreatedAt DATETIME2 NOT NULL CONSTRAINT DfLevelsCreatedAt DEFAULT SYSUTCDATETIME(),
    UpdatedAt DATETIME2 NULL,
    IsActive BIT NOT NULL CONSTRAINT DfLevelsIsActive DEFAULT 1,
    IsDeleted BIT NOT NULL CONSTRAINT DfLevelsIsDeleted DEFAULT 0,
    CONSTRAINT UqLevelsCode UNIQUE (Code),
    CONSTRAINT UqLevelsSortOrder UNIQUE (SortOrder)
);
GO

/* ==================================================
   Table: Users
================================================== */
CREATE TABLE dbo.Users (
    Id INT IDENTITY(1,1) NOT NULL CONSTRAINT PkUsers PRIMARY KEY,
    Username NVARCHAR(100) NOT NULL,
    Password NVARCHAR(100) NOT NULL,
    Name NVARCHAR(100) NOT NULL,
    Email NVARCHAR(100) NOT NULL,
    EmailVerified BIT NOT NULL CONSTRAINT DfUsersEmailVerified DEFAULT 0,
    EmailVerifiedAt DATETIME2 NULL,
    RoleId INT NOT NULL,
    CurrentLevelId INT NULL,
    StreakDays INT NOT NULL CONSTRAINT DfUsersStreakDays DEFAULT 0,
    Phone NVARCHAR(20) NULL,
    AvatarUrl NVARCHAR(500) NULL,
    Gender NVARCHAR(10) NULL,
    DateOfBirth DATETIME2 NULL,
    Address NVARCHAR(500) NULL,
    LastActiveAt DATETIME2 NULL,
    CreatedAt DATETIME2 NOT NULL CONSTRAINT DfUsersCreatedAt DEFAULT SYSUTCDATETIME(),
    UpdatedAt DATETIME2 NULL,
    IsDeleted BIT NOT NULL CONSTRAINT DfUsersIsDeleted DEFAULT 0,
    CONSTRAINT UqUsersUsername UNIQUE (Username),
    CONSTRAINT UqUsersEmail UNIQUE (Email),
    CONSTRAINT UqUsersPhone UNIQUE (Phone),
    CONSTRAINT FkUsersRole FOREIGN KEY (RoleId) REFERENCES dbo.Roles(Id),
    CONSTRAINT FkUsersCurrentLevel FOREIGN KEY (CurrentLevelId) REFERENCES dbo.Levels(Id)
);
GO

/* ==================================================
   Table: EmailVerificationOtps
================================================== */
CREATE TABLE dbo.EmailVerificationOtps (
    Id INT IDENTITY(1,1) NOT NULL CONSTRAINT PkEmailVerificationOtps PRIMARY KEY,
    UserId INT NOT NULL,
    Purpose NVARCHAR(100) NOT NULL CONSTRAINT DfEmailVerificationOtpsPurpose DEFAULT N'Verify Email',
    CodeHash NVARCHAR(300) NOT NULL,
    ExpiresAt DATETIME2 NOT NULL,
    AttemptCount INT NOT NULL CONSTRAINT DfEmailVerificationOtpsAttemptCount DEFAULT 0,
    MaxAttempts INT NOT NULL CONSTRAINT DfEmailVerificationOtpsMaxAttempts DEFAULT 5,
    ConsumedAt DATETIME2 NULL,
    CreatedAt DATETIME2 NOT NULL CONSTRAINT DfEmailVerificationOtpsCreatedAt DEFAULT SYSUTCDATETIME(),
    UpdatedAt DATETIME2 NULL,
    IsDeleted BIT NOT NULL CONSTRAINT DfEmailVerificationOtpsIsDeleted DEFAULT 0,
    CONSTRAINT FkEmailVerificationOtpsUser FOREIGN KEY (UserId) REFERENCES dbo.Users(Id),
    CONSTRAINT UqEmailVerificationOtpsUserPurposeConsumed UNIQUE (UserId, Purpose, ConsumedAt)
);
GO

/* ==================================================
   Table: Topics
================================================== */
CREATE TABLE dbo.Topics (
    Id INT IDENTITY(1,1) NOT NULL CONSTRAINT PkTopics PRIMARY KEY,
    LevelId INT NOT NULL,
    Slug NVARCHAR(100) NOT NULL,
    Name NVARCHAR(200) NOT NULL,
    Description NVARCHAR(500) NULL,
    SortOrder INT NOT NULL,
    CreatedAt DATETIME2 NOT NULL CONSTRAINT DfTopicsCreatedAt DEFAULT SYSUTCDATETIME(),
    UpdatedAt DATETIME2 NULL,
    IsActive BIT NOT NULL CONSTRAINT DfTopicsIsActive DEFAULT 1,
    IsDeleted BIT NOT NULL CONSTRAINT DfTopicsIsDeleted DEFAULT 0,
    CONSTRAINT FkTopicsLevel FOREIGN KEY (LevelId) REFERENCES dbo.Levels(Id),
    CONSTRAINT UqTopicsLevelSlug UNIQUE (LevelId, Slug),
    CONSTRAINT UqTopicsName UNIQUE (Name),
    CONSTRAINT UqTopicsLevelSortOrder UNIQUE (LevelId, SortOrder)
);
GO

/* ==================================================
   Table: Vocabulary
================================================== */
CREATE TABLE dbo.Vocabulary (
    Id INT IDENTITY(1,1) NOT NULL CONSTRAINT PkVocabulary PRIMARY KEY,
    TopicId INT NOT NULL,
    Word NVARCHAR(100) NOT NULL,
    Phonetic NVARCHAR(100) NULL,
    AudioUrl NVARCHAR(500) NULL,
    PartOfSpeech NVARCHAR(50) NULL,
    DefinitionEn NVARCHAR(MAX) NULL,
    DefinitionVi NVARCHAR(MAX) NULL,
    MeaningVi NVARCHAR(100) NULL,
    CreatedAt DATETIME2 NOT NULL CONSTRAINT DfVocabularyCreatedAt DEFAULT SYSUTCDATETIME(),
    UpdatedAt DATETIME2 NULL,
    IsDeleted BIT NOT NULL CONSTRAINT DfVocabularyIsDeleted DEFAULT 0,
    CONSTRAINT FkVocabularyTopic FOREIGN KEY (TopicId) REFERENCES dbo.Topics(Id),
    CONSTRAINT UqVocabularyTopicWord UNIQUE (TopicId, Word)
);
GO

/* ==================================================
   Table: VocabExamples
================================================== */
CREATE TABLE dbo.VocabExamples (
    Id INT IDENTITY(1,1) NOT NULL CONSTRAINT PkVocabExamples PRIMARY KEY,
    VocabularyId INT NOT NULL,
    ExampleEn NVARCHAR(1000) NOT NULL,
    ExampleVi NVARCHAR(1000) NULL,
    CreatedAt DATETIME2 NOT NULL CONSTRAINT DfVocabExamplesCreatedAt DEFAULT SYSUTCDATETIME(),
    UpdatedAt DATETIME2 NULL,
    IsDeleted BIT NOT NULL CONSTRAINT DfVocabExamplesIsDeleted DEFAULT 0,
    CONSTRAINT FkVocabExamplesVocabulary FOREIGN KEY (VocabularyId) REFERENCES dbo.Vocabulary(Id) ON DELETE CASCADE,
    CONSTRAINT UqVocabExamplesVocabularyExample UNIQUE (VocabularyId, ExampleEn)
);
GO

/* ==================================================
   Table: Lessons
================================================== */
CREATE TABLE dbo.Lessons (
    Id INT IDENTITY(1,1) NOT NULL CONSTRAINT PkLessons PRIMARY KEY,
    TopicId INT NOT NULL,
    Title NVARCHAR(200) NOT NULL,
    Description NVARCHAR(1000) NULL,
    SortOrder INT NOT NULL,
    PassScore INT NOT NULL CONSTRAINT DfLessonsPassScore DEFAULT 80,
    CreatedAt DATETIME2 NOT NULL CONSTRAINT DfLessonsCreatedAt DEFAULT SYSUTCDATETIME(),
    UpdatedAt DATETIME2 NULL,
    IsActive BIT NOT NULL CONSTRAINT DfLessonsIsActive DEFAULT 1,
    IsDeleted BIT NOT NULL CONSTRAINT DfLessonsIsDeleted DEFAULT 0,
    IsTest BIT NOT NULL CONSTRAINT DfLessonsIsTest DEFAULT 0,
    CONSTRAINT FkLessonsTopic FOREIGN KEY (TopicId) REFERENCES dbo.Topics(Id) ON DELETE CASCADE,
    CONSTRAINT UqLessonsTopicSortOrder UNIQUE (TopicId, SortOrder),
    CONSTRAINT CkLessonsPassScoreRange CHECK (PassScore BETWEEN 0 AND 100)
);
GO

/* ==================================================
   Table: LessonItems
================================================== */
CREATE TABLE dbo.LessonItems (
    Id INT IDENTITY(1,1) NOT NULL CONSTRAINT PkLessonItems PRIMARY KEY,
    LessonId INT NOT NULL,
    VocabularyId INT NOT NULL,
    SortOrder INT NOT NULL,
    CreatedAt DATETIME2 NOT NULL CONSTRAINT DfLessonItemsCreatedAt DEFAULT SYSUTCDATETIME(),
    UpdatedAt DATETIME2 NULL,
    IsDeleted BIT NOT NULL CONSTRAINT DfLessonItemsIsDeleted DEFAULT 0,
    CONSTRAINT FkLessonItemsLesson FOREIGN KEY (LessonId) REFERENCES dbo.Lessons(Id) ON DELETE CASCADE,
    CONSTRAINT FkLessonItemsVocabulary FOREIGN KEY (VocabularyId) REFERENCES dbo.Vocabulary(Id),
    CONSTRAINT UqLessonItemsLessonSortOrder UNIQUE (LessonId, SortOrder),
    CONSTRAINT UqLessonItemsLessonVocabulary UNIQUE (LessonId, VocabularyId)
);
GO

/* ==================================================
   Table: ExerciseTypes
   Lookup for lesson exercise kinds. Rules per type are enforced in application;
   PromptJson / CorrectAnswerJson hold structured payloads where relational columns are not enough.
================================================== */
CREATE TABLE dbo.ExerciseTypes (
    Id INT IDENTITY(1,1) NOT NULL CONSTRAINT PkExerciseTypes PRIMARY KEY,
    Code NVARCHAR(40) NOT NULL,
    Name NVARCHAR(100) NOT NULL,
    Description NVARCHAR(500) NULL,
    CreatedAt DATETIME2 NOT NULL CONSTRAINT DfExerciseTypesCreatedAt DEFAULT SYSUTCDATETIME(),
    UpdatedAt DATETIME2 NULL,
    IsActive BIT NOT NULL CONSTRAINT DfExerciseTypesIsActive DEFAULT 1,
    IsDeleted BIT NOT NULL CONSTRAINT DfExerciseTypesIsDeleted DEFAULT 0,
    CONSTRAINT UqExerciseTypesCode UNIQUE (Code)
);
GO

/*
  LessonExercises column guide:
  - PromptText / AudioUrl: short prompt or audio for MC (e.g. show English word, play audio).
  - PromptLanguage / AnswerLanguage (En|Vi): MC direction, e.g. prompt En -> choose Vi.
  - PromptJson: structured UI/state — e.g. SentenceReorder token list + shuffle; MatchPairs left/right lists;
    PatternFollow template + word bank + slots; mini reorder using lesson word ids.
  - CorrectAnswerJson: canonical answer for auto-grading — ordered tokens, pair mapping, built phrase, etc.
  - CorrectAnswerText: optional flat answer or display string.
  - VocabularyId: required — anchor word for this exercise (the “main” word the item is about). Multi-word / lesson-wide drills still pick one anchor (e.g. first word in lesson or the word the template focuses on); extra words stay in PromptJson / LessonItems.
  - ExampleId: VocabExamples row for SentenceReorder / example-based tasks when applicable.
  - MultipleChoice: use LessonExerciseOptions (wrong + right distractors); ExampleId usually NULL.
*/
CREATE TABLE dbo.LessonExercises (
    Id INT IDENTITY(1,1) NOT NULL CONSTRAINT PkLessonExercises PRIMARY KEY,
    LessonId INT NOT NULL,
    VocabularyId INT NOT NULL,
    ExampleId INT NULL,
    ExerciseTypeId INT NOT NULL,
    PromptLanguage NVARCHAR(2) NULL,
    AnswerLanguage NVARCHAR(2) NULL,
    PromptText NVARCHAR(1000) NULL,
    PromptJson NVARCHAR(MAX) NULL,
    AudioUrl NVARCHAR(500) NULL,
    CorrectAnswerText NVARCHAR(1000) NULL,
    CorrectAnswerJson NVARCHAR(MAX) NULL,
    SortOrder INT NOT NULL,
    Points INT NOT NULL CONSTRAINT DfLessonExercisesPoints DEFAULT 1,
    CreatedAt DATETIME2 NOT NULL CONSTRAINT DfLessonExercisesCreatedAt DEFAULT SYSUTCDATETIME(),
    UpdatedAt DATETIME2 NULL,
    IsDeleted BIT NOT NULL CONSTRAINT DfLessonExercisesIsDeleted DEFAULT 0,
    CONSTRAINT FkLessonExercisesLesson FOREIGN KEY (LessonId) REFERENCES dbo.Lessons(Id) ON DELETE CASCADE,
    CONSTRAINT FkLessonExercisesVocabulary FOREIGN KEY (VocabularyId) REFERENCES dbo.Vocabulary(Id),
    CONSTRAINT FkLessonExercisesExample FOREIGN KEY (ExampleId) REFERENCES dbo.VocabExamples(Id),
    CONSTRAINT FkLessonExercisesExerciseType FOREIGN KEY (ExerciseTypeId) REFERENCES dbo.ExerciseTypes(Id),
    CONSTRAINT UqLessonExercisesLessonSortOrder UNIQUE (LessonId, SortOrder),
    CONSTRAINT CkLessonExercisesPromptLang CHECK (PromptLanguage IS NULL OR PromptLanguage IN (N'En', N'Vi')),
    CONSTRAINT CkLessonExercisesAnswerLang CHECK (AnswerLanguage IS NULL OR AnswerLanguage IN (N'En', N'Vi'))
);
GO

/* ==================================================
   Table: LessonExerciseOptions
================================================== */
CREATE TABLE dbo.LessonExerciseOptions (
    Id INT IDENTITY(1,1) NOT NULL CONSTRAINT PkLessonExerciseOptions PRIMARY KEY,
    ExerciseId INT NOT NULL,
    OptionText NVARCHAR(500) NULL,
    OptionJson NVARCHAR(MAX) NULL,
    IsCorrect BIT NOT NULL,
    SortOrder INT NOT NULL,
    CreatedAt DATETIME2 NOT NULL CONSTRAINT DfLessonExerciseOptionsCreatedAt DEFAULT SYSUTCDATETIME(),
    UpdatedAt DATETIME2 NULL,
    IsDeleted BIT NOT NULL CONSTRAINT DfLessonExerciseOptionsIsDeleted DEFAULT 0,
    CONSTRAINT FkLessonExerciseOptionsExercise FOREIGN KEY (ExerciseId) REFERENCES dbo.LessonExercises(Id) ON DELETE CASCADE,
    CONSTRAINT UqLessonExerciseOptionsSortOrder UNIQUE (ExerciseId, SortOrder)
);
GO

/* ==================================================
   Table: LessonAttempts
================================================== */
CREATE TABLE dbo.LessonAttempts (
    Id INT IDENTITY(1,1) NOT NULL CONSTRAINT PkLessonAttempts PRIMARY KEY,
    UserId INT NOT NULL,
    LessonId INT NOT NULL,
    StartedAt DATETIME2 NOT NULL CONSTRAINT DfLessonAttemptsStartedAt DEFAULT SYSUTCDATETIME(),
    FinishedAt DATETIME2 NULL,
    Score INT NOT NULL CONSTRAINT DfLessonAttemptsScore DEFAULT 0,
    MaxScore INT NOT NULL CONSTRAINT DfLessonAttemptsMaxScore DEFAULT 0,
    AccuracyPercent DECIMAL(5,2) NOT NULL CONSTRAINT DfLessonAttemptsAccuracyPercent DEFAULT 0,
    IsPassed BIT NOT NULL CONSTRAINT DfLessonAttemptsIsPassed DEFAULT 0,
    CreatedAt DATETIME2 NOT NULL CONSTRAINT DfLessonAttemptsCreatedAt DEFAULT SYSUTCDATETIME(),
    UpdatedAt DATETIME2 NULL,
    IsDeleted BIT NOT NULL CONSTRAINT DfLessonAttemptsIsDeleted DEFAULT 0,
    CONSTRAINT FkLessonAttemptsUser FOREIGN KEY (UserId) REFERENCES dbo.Users(Id) ON DELETE CASCADE,
    CONSTRAINT FkLessonAttemptsLesson FOREIGN KEY (LessonId) REFERENCES dbo.Lessons(Id) ON DELETE CASCADE,
    CONSTRAINT CkLessonAttemptsAccuracyRange CHECK (AccuracyPercent BETWEEN 0 AND 100)
);
GO

/* ==================================================
   Table: LessonAttemptAnswers
================================================== */
CREATE TABLE dbo.LessonAttemptAnswers (
    Id INT IDENTITY(1,1) NOT NULL CONSTRAINT PkLessonAttemptAnswers PRIMARY KEY,
    AttemptId INT NOT NULL,
    ExerciseId INT NOT NULL,
    SelectedOptionId INT NULL,
    AnswerText NVARCHAR(1000) NULL,
    AnswerJson NVARCHAR(MAX) NULL,
    IsCorrect BIT NOT NULL CONSTRAINT DfLessonAttemptAnswersIsCorrect DEFAULT 0,
    EarnedPoints INT NOT NULL CONSTRAINT DfLessonAttemptAnswersEarnedPoints DEFAULT 0,
    CreatedAt DATETIME2 NOT NULL CONSTRAINT DfLessonAttemptAnswersCreatedAt DEFAULT SYSUTCDATETIME(),
    UpdatedAt DATETIME2 NULL,
    IsDeleted BIT NOT NULL CONSTRAINT DfLessonAttemptAnswersIsDeleted DEFAULT 0,
    CONSTRAINT FkLessonAttemptAnswersAttempt FOREIGN KEY (AttemptId) REFERENCES dbo.LessonAttempts(Id) ON DELETE CASCADE,
    CONSTRAINT FkLessonAttemptAnswersExercise FOREIGN KEY (ExerciseId) REFERENCES dbo.LessonExercises(Id),
    CONSTRAINT FkLessonAttemptAnswersSelectedOption FOREIGN KEY (SelectedOptionId) REFERENCES dbo.LessonExerciseOptions(Id),
    CONSTRAINT UqLessonAttemptAnswersAttemptExercise UNIQUE (AttemptId, ExerciseId)
);
GO

/* ==================================================
   Table: PlacementQuestions
================================================== */
CREATE TABLE dbo.PlacementQuestions (
    Id INT IDENTITY(1,1) NOT NULL CONSTRAINT PkPlacementQuestions PRIMARY KEY,
    LevelId INT NOT NULL,
    QuestionText NVARCHAR(1000) NOT NULL,
    Explanation NVARCHAR(1000) NULL,
    CreatedAt DATETIME2 NOT NULL CONSTRAINT DfPlacementQuestionsCreatedAt DEFAULT SYSUTCDATETIME(),
    UpdatedAt DATETIME2 NULL,
    IsActive BIT NOT NULL CONSTRAINT DfPlacementQuestionsIsActive DEFAULT 1,
    IsDeleted BIT NOT NULL CONSTRAINT DfPlacementQuestionsIsDeleted DEFAULT 0,
    CONSTRAINT FkPlacementQuestionsLevel FOREIGN KEY (LevelId) REFERENCES dbo.Levels(Id)
);
GO

/* ==================================================
   Table: PlacementOptions
================================================== */
CREATE TABLE dbo.PlacementOptions (
    Id INT IDENTITY(1,1) NOT NULL CONSTRAINT PkPlacementOptions PRIMARY KEY,
    QuestionId INT NOT NULL,
    OptionText NVARCHAR(500) NOT NULL,
    IsCorrect BIT NOT NULL,
    Score INT NOT NULL CONSTRAINT DfPlacementOptionsScore DEFAULT 0,
    CreatedAt DATETIME2 NOT NULL CONSTRAINT DfPlacementOptionsCreatedAt DEFAULT SYSUTCDATETIME(),
    UpdatedAt DATETIME2 NULL,
    IsDeleted BIT NOT NULL CONSTRAINT DfPlacementOptionsIsDeleted DEFAULT 0,
    CONSTRAINT FkPlacementOptionsQuestion FOREIGN KEY (QuestionId) REFERENCES dbo.PlacementQuestions(Id) ON DELETE CASCADE
);
GO

/* ==================================================
   Table: PlacementAttempts
================================================== */
CREATE TABLE dbo.PlacementAttempts (
    Id INT IDENTITY(1,1) NOT NULL CONSTRAINT PkPlacementAttempts PRIMARY KEY,
    UserId INT NOT NULL,
    StartedAt DATETIME2 NOT NULL CONSTRAINT DfPlacementAttemptsStartedAt DEFAULT SYSUTCDATETIME(),
    FinishedAt DATETIME2 NULL,
    TotalScore INT NOT NULL CONSTRAINT DfPlacementAttemptsTotalScore DEFAULT 0,
    AssignedLevelId INT NOT NULL,
    CreatedAt DATETIME2 NOT NULL CONSTRAINT DfPlacementAttemptsCreatedAt DEFAULT SYSUTCDATETIME(),
    UpdatedAt DATETIME2 NULL,
    IsDeleted BIT NOT NULL CONSTRAINT DfPlacementAttemptsIsDeleted DEFAULT 0,
    CONSTRAINT FkPlacementAttemptsUser FOREIGN KEY (UserId) REFERENCES dbo.Users(Id),
    CONSTRAINT FkPlacementAttemptsAssignedLevel FOREIGN KEY (AssignedLevelId) REFERENCES dbo.Levels(Id),
    CONSTRAINT UqPlacementAttemptsUser UNIQUE (UserId)
);
GO

/* ==================================================
   Table: PlacementAttemptAnswers
================================================== */
CREATE TABLE dbo.PlacementAttemptAnswers (
    Id INT IDENTITY(1,1) NOT NULL CONSTRAINT PkPlacementAttemptAnswers PRIMARY KEY,
    AttemptId INT NOT NULL,
    QuestionId INT NOT NULL,
    SelectedOptionId INT NULL,
    IsCorrect BIT NOT NULL CONSTRAINT DfPlacementAttemptAnswersIsCorrect DEFAULT 0,
    EarnedScore INT NOT NULL CONSTRAINT DfPlacementAttemptAnswersEarnedScore DEFAULT 0,
    CreatedAt DATETIME2 NOT NULL CONSTRAINT DfPlacementAttemptAnswersCreatedAt DEFAULT SYSUTCDATETIME(),
    UpdatedAt DATETIME2 NULL,
    IsDeleted BIT NOT NULL CONSTRAINT DfPlacementAttemptAnswersIsDeleted DEFAULT 0,
    CONSTRAINT FkPlacementAttemptAnswersAttempt FOREIGN KEY (AttemptId) REFERENCES dbo.PlacementAttempts(Id) ON DELETE CASCADE,
    CONSTRAINT FkPlacementAttemptAnswersQuestion FOREIGN KEY (QuestionId) REFERENCES dbo.PlacementQuestions(Id),
    CONSTRAINT FkPlacementAttemptAnswersOption FOREIGN KEY (SelectedOptionId) REFERENCES dbo.PlacementOptions(Id),
    CONSTRAINT UqPlacementAttemptAnswersAttemptQuestion UNIQUE (AttemptId, QuestionId)
);
GO

/* ==================================================
   Table: UserVocabProgress
================================================== */
CREATE TABLE dbo.UserVocabProgress (
    Id INT IDENTITY(1,1) NOT NULL CONSTRAINT PkUserVocabProgress PRIMARY KEY,
    UserId INT NOT NULL,
    VocabularyId INT NOT NULL,
    Status NVARCHAR(20) NOT NULL CONSTRAINT DfUserVocabProgressStatus DEFAULT N'New',
    CorrectCount INT NOT NULL CONSTRAINT DfUserVocabProgressCorrectCount DEFAULT 0,
    WrongCount INT NOT NULL CONSTRAINT DfUserVocabProgressWrongCount DEFAULT 0,
    LastReviewedAt DATETIME2 NULL,
    NextReviewAt DATETIME2 NULL,
    CreatedAt DATETIME2 NOT NULL CONSTRAINT DfUserVocabProgressCreatedAt DEFAULT SYSUTCDATETIME(),
    UpdatedAt DATETIME2 NULL,
    CONSTRAINT FkUserVocabProgressUser FOREIGN KEY (UserId) REFERENCES dbo.Users(Id) ON DELETE CASCADE,
    CONSTRAINT FkUserVocabProgressVocabulary FOREIGN KEY (VocabularyId) REFERENCES dbo.Vocabulary(Id) ON DELETE CASCADE,
    CONSTRAINT UqUserVocabProgressUserVocabulary UNIQUE (UserId, VocabularyId),
    CONSTRAINT CkUserVocabProgressStatus CHECK (Status IN (N'New', N'Learning', N'Review', N'Mastered'))
);
GO

/* ==================================================
   Table: UserLessonProgress
================================================== */
CREATE TABLE dbo.UserLessonProgress (
    Id INT IDENTITY(1,1) NOT NULL CONSTRAINT PkUserLessonProgress PRIMARY KEY,
    UserId INT NOT NULL,
    LessonId INT NOT NULL,
    BestScore INT NOT NULL CONSTRAINT DfUserLessonProgressBestScore DEFAULT 0,
    BestAccuracyPercent DECIMAL(5,2) NOT NULL CONSTRAINT DfUserLessonProgressBestAccuracyPercent DEFAULT 0,
    AttemptsCount INT NOT NULL CONSTRAINT DfUserLessonProgressAttemptsCount DEFAULT 0,
    Status NVARCHAR(20) NOT NULL CONSTRAINT DfUserLessonProgressStatus DEFAULT N'NotStarted',
    FirstCompletedAt DATETIME2 NULL,
    LastActivityAt DATETIME2 NULL,
    CreatedAt DATETIME2 NOT NULL CONSTRAINT DfUserLessonProgressCreatedAt DEFAULT SYSUTCDATETIME(),
    UpdatedAt DATETIME2 NULL,
    CONSTRAINT FkUserLessonProgressUser FOREIGN KEY (UserId) REFERENCES dbo.Users(Id) ON DELETE CASCADE,
    CONSTRAINT FkUserLessonProgressLesson FOREIGN KEY (LessonId) REFERENCES dbo.Lessons(Id) ON DELETE CASCADE,
    CONSTRAINT UqUserLessonProgressUserLesson UNIQUE (UserId, LessonId),
    CONSTRAINT CkUserLessonProgressStatus CHECK (Status IN (N'NotStarted', N'InProgress', N'Completed'))
);
GO

/* ==================================================
   Table: UserTopicProgress
================================================== */
CREATE TABLE dbo.UserTopicProgress (
    Id INT IDENTITY(1,1) NOT NULL CONSTRAINT PkUserTopicProgress PRIMARY KEY,
    UserId INT NOT NULL,
    TopicId INT NOT NULL,
    TotalLessons INT NOT NULL CONSTRAINT DfUserTopicProgressTotalLessons DEFAULT 0,
    CompletedLessons INT NOT NULL CONSTRAINT DfUserTopicProgressCompletedLessons DEFAULT 0,
    CompletionPercent DECIMAL(5,2) NOT NULL CONSTRAINT DfUserTopicProgressCompletionPercent DEFAULT 0,
    Status NVARCHAR(20) NOT NULL CONSTRAINT DfUserTopicProgressStatus DEFAULT N'NotStarted',
    CompletedAt DATETIME2 NULL,
    UpdatedAt DATETIME2 NULL,
    CONSTRAINT FkUserTopicProgressUser FOREIGN KEY (UserId) REFERENCES dbo.Users(Id) ON DELETE CASCADE,
    CONSTRAINT FkUserTopicProgressTopic FOREIGN KEY (TopicId) REFERENCES dbo.Topics(Id) ON DELETE CASCADE,
    CONSTRAINT UqUserTopicProgressUserTopic UNIQUE (UserId, TopicId),
    CONSTRAINT CkUserTopicProgressStatus CHECK (Status IN (N'NotStarted', N'InProgress', N'Completed'))
);
GO

/* ==================================================
   Table: UserLevelProgress
================================================== */
CREATE TABLE dbo.UserLevelProgress (
    Id INT IDENTITY(1,1) NOT NULL CONSTRAINT PkUserLevelProgress PRIMARY KEY,
    UserId INT NOT NULL,
    LevelId INT NOT NULL,
    TotalTopics INT NOT NULL CONSTRAINT DfUserLevelProgressTotalTopics DEFAULT 0,
    CompletedTopics INT NOT NULL CONSTRAINT DfUserLevelProgressCompletedTopics DEFAULT 0,
    CompletionPercent DECIMAL(5,2) NOT NULL CONSTRAINT DfUserLevelProgressCompletionPercent DEFAULT 0,
    IsUnlocked BIT NOT NULL CONSTRAINT DfUserLevelProgressIsUnlocked DEFAULT 0,
    UnlockedAt DATETIME2 NULL,
    IsCompleted BIT NOT NULL CONSTRAINT DfUserLevelProgressIsCompleted DEFAULT 0,
    CompletedAt DATETIME2 NULL,
    UpdatedAt DATETIME2 NULL,
    CONSTRAINT FkUserLevelProgressUser FOREIGN KEY (UserId) REFERENCES dbo.Users(Id) ON DELETE CASCADE,
    CONSTRAINT FkUserLevelProgressLevel FOREIGN KEY (LevelId) REFERENCES dbo.Levels(Id),
    CONSTRAINT UqUserLevelProgressUserLevel UNIQUE (UserId, LevelId)
);
GO

/* ==================================================
   Indexes
================================================== */
CREATE UNIQUE INDEX UxEmailVerificationOtpsActive
ON dbo.EmailVerificationOtps (UserId, Purpose)
WHERE ConsumedAt IS NULL AND IsDeleted = 0;
GO

CREATE INDEX IxUsersRoleId ON dbo.Users(RoleId);
CREATE INDEX IxUsersCurrentLevelId ON dbo.Users(CurrentLevelId);
CREATE INDEX IxEmailVerificationOtpsUserId ON dbo.EmailVerificationOtps(UserId);
CREATE INDEX IxTopicsLevelId ON dbo.Topics(LevelId);
CREATE INDEX IxVocabularyTopicId ON dbo.Vocabulary(TopicId);
CREATE INDEX IxLessonsTopicId ON dbo.Lessons(TopicId);
CREATE INDEX IxLessonItemsLessonId ON dbo.LessonItems(LessonId);
CREATE INDEX IxLessonExercisesLessonId ON dbo.LessonExercises(LessonId);
CREATE INDEX IxLessonExercisesVocabularyId ON dbo.LessonExercises(VocabularyId);
CREATE INDEX IxLessonExercisesExampleId ON dbo.LessonExercises(ExampleId);
CREATE INDEX IxLessonExercisesExerciseTypeId ON dbo.LessonExercises(ExerciseTypeId);
CREATE INDEX IxLessonExerciseOptionsExerciseId ON dbo.LessonExerciseOptions(ExerciseId);
CREATE INDEX IxLessonAttemptsUserLesson ON dbo.LessonAttempts(UserId, LessonId);
CREATE INDEX IxLessonAttemptAnswersAttemptId ON dbo.LessonAttemptAnswers(AttemptId);
CREATE INDEX IxPlacementQuestionsLevelId ON dbo.PlacementQuestions(LevelId);
CREATE INDEX IxPlacementOptionsQuestionId ON dbo.PlacementOptions(QuestionId);
CREATE INDEX IxPlacementAttemptAnswersAttemptId ON dbo.PlacementAttemptAnswers(AttemptId);
CREATE INDEX IxPlacementAttemptAnswersQuestionId ON dbo.PlacementAttemptAnswers(QuestionId);
CREATE INDEX IxUserVocabProgressUserId ON dbo.UserVocabProgress(UserId);
CREATE INDEX IxUserVocabProgressVocabularyId ON dbo.UserVocabProgress(VocabularyId);
CREATE INDEX IxUserLessonProgressUserId ON dbo.UserLessonProgress(UserId);
CREATE INDEX IxUserLessonProgressLessonId ON dbo.UserLessonProgress(LessonId);
CREATE INDEX IxUserTopicProgressUserId ON dbo.UserTopicProgress(UserId);
CREATE INDEX IxUserTopicProgressTopicId ON dbo.UserTopicProgress(TopicId);
CREATE INDEX IxUserLevelProgressUserId ON dbo.UserLevelProgress(UserId);
CREATE INDEX IxUserLevelProgressLevelId ON dbo.UserLevelProgress(LevelId);
GO

/* ==================================================
   Seed Data
================================================== */
IF NOT EXISTS (SELECT 1 FROM dbo.Roles WHERE Code = N'AD')
    INSERT INTO dbo.Roles (Code, Name, Description)
    VALUES (N'AD', N'ADMIN', N'Admin system');

IF NOT EXISTS (SELECT 1 FROM dbo.Roles WHERE Code = N'LE')
    INSERT INTO dbo.Roles (Code, Name, Description)
    VALUES (N'LE', N'LEARNER', N'Learner want to learn English');

IF NOT EXISTS (SELECT 1 FROM dbo.Levels WHERE Code = N'E')
    INSERT INTO dbo.Levels (Code, Name, SortOrder, Description)
    VALUES (N'E', N'EASY', 1, N'Beginner vocabulary');

IF NOT EXISTS (SELECT 1 FROM dbo.Levels WHERE Code = N'M')
    INSERT INTO dbo.Levels (Code, Name, SortOrder, Description)
    VALUES (N'M', N'MEDIUM', 2, N'Elementary vocabulary');

IF NOT EXISTS (SELECT 1 FROM dbo.Levels WHERE Code = N'I')
    INSERT INTO dbo.Levels (Code, Name, SortOrder, Description)
    VALUES (N'I', N'INTERMEDIATE', 3, N'Intermediate vocabulary');

IF NOT EXISTS (SELECT 1 FROM dbo.Levels WHERE Code = N'UI')
    INSERT INTO dbo.Levels (Code, Name, SortOrder, Description)
    VALUES (N'UI', N'UPPER INTERMEDIATE', 4, N'Upper-intermediate vocabulary');

IF NOT EXISTS (SELECT 1 FROM dbo.Levels WHERE Code = N'A')
    INSERT INTO dbo.Levels (Code, Name, SortOrder, Description)
    VALUES (N'A', N'ADVANCED', 5, N'Advanced vocabulary');
GO

/* Exercise types (lesson); Code short keys: MC, SR, MP, PF */
IF NOT EXISTS (SELECT 1 FROM dbo.ExerciseTypes WHERE Code = N'MC')
    INSERT INTO dbo.ExerciseTypes (Code, Name, Description)
    VALUES (N'MC', N'Multiple choice', N'Options in LessonExerciseOptions; MC En/Vi/audio prompts.');

IF NOT EXISTS (SELECT 1 FROM dbo.ExerciseTypes WHERE Code = N'SR')
    INSERT INTO dbo.ExerciseTypes (Code, Name, Description)
    VALUES (N'SR', N'Sentence reorder', N'Reorder tokens/phrases; often uses ExampleId + PromptJson/CorrectAnswerJson.');

IF NOT EXISTS (SELECT 1 FROM dbo.ExerciseTypes WHERE Code = N'MP')
    INSERT INTO dbo.ExerciseTypes (Code, Name, Description)
    VALUES (N'MP', N'Match pairs', N'Connect EN column to VI column; pairs in PromptJson/CorrectAnswerJson or options.');

IF NOT EXISTS (SELECT 1 FROM dbo.ExerciseTypes WHERE Code = N'PF')
    INSERT INTO dbo.ExerciseTypes (Code, Name, Description)
    VALUES (N'PF', N'Pattern follow', N'Follow a template (e.g. word + connector + word) using words from bank; JSON payloads.');
GO

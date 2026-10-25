-- Curated vocabulary only. No generated clubs, posts, users, or event facts.
USE ROLE HACKATHON_OWNER;
MERGE INTO HACKATHON_DB.APP.TAGS AS target
USING (
    SELECT COLUMN1 AS TAG_ID, COLUMN2 AS LABEL, COLUMN3 AS CATEGORY
    FROM VALUES
        ('artificial-intelligence', 'Artificial intelligence', 'topic'),
        ('robotics', 'Robotics', 'topic'),
        ('arts', 'Arts', 'topic'),
        ('sports', 'Sports', 'topic'),
        ('volunteering', 'Volunteering', 'topic'),
        ('workshop', 'Workshop', 'activity'),
        ('social', 'Social', 'activity'),
        ('career', 'Career', 'activity'),
        ('beginner-friendly', 'Beginner friendly', 'audience'),
        ('virtual', 'Virtual', 'format')
) AS source ON target.TAG_ID = source.TAG_ID
WHEN NOT MATCHED THEN INSERT (TAG_ID, SLUG, LABEL, CATEGORY)
VALUES (source.TAG_ID, source.TAG_ID, source.LABEL, source.CATEGORY);

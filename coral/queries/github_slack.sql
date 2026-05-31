
-- github_slack.sql

SELECT *
FROM github.issues g
JOIN slack.messages s
ON g.author = s.user

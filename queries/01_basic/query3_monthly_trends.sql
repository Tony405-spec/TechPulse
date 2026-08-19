-- Monthly adoption/community trend analysis for all observed technologies.
SELECT 
    tag,
    DATE_TRUNC('month', date) AS month,
    SUM(question_count) AS monthly_questions,
    SUM(unanswered_count) AS monthly_unanswered,
    (100.0 * SUM(unanswered_count) / NULLIF(SUM(question_count), 0))::numeric(10,2) AS unanswered_percentage,
    LAG(SUM(question_count), 3) OVER (
        PARTITION BY tag
        ORDER BY DATE_TRUNC('month', date)
    ) AS questions_three_months_prior
FROM stackoverflow
GROUP BY tag, DATE_TRUNC('month', date)
ORDER BY tag, month;

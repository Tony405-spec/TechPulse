-- Growth momentum using the latest 30-day window versus the previous 30-day window.
WITH date_range AS (
    SELECT 
        MIN(date) as earliest,
        MAX(date) as latest
    FROM stackoverflow
),
tech_comparison AS (
    SELECT 
        s.tag,
        SUM(CASE WHEN s.date >= (SELECT latest - INTERVAL '30 days' FROM date_range) 
                 THEN s.question_count ELSE 0 END) AS recent_questions,
        SUM(CASE WHEN s.date < (SELECT latest - INTERVAL '30 days' FROM date_range)
                  AND s.date >= (SELECT latest - INTERVAL '60 days' FROM date_range) 
                 THEN s.question_count ELSE 0 END) AS past_questions
    FROM stackoverflow s
    CROSS JOIN date_range
    GROUP BY s.tag
)
SELECT 
    tag,
    recent_questions,
    past_questions,
    CASE 
        WHEN past_questions > 0 
        THEN (100.0 * (recent_questions - past_questions) / past_questions)::numeric(10,2)
        ELSE 0
    END AS growth_percentage
FROM tech_comparison
WHERE recent_questions > 0 OR past_questions > 0
ORDER BY growth_percentage DESC
LIMIT 20;

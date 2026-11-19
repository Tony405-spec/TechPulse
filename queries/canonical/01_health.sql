SELECT n.nspname AS schema_name, count(c.relname) AS tables
FROM pg_namespace n LEFT JOIN pg_class c ON c.relnamespace=n.oid AND c.relkind='r'
WHERE n.nspname IN ('raw','staging','core','analytics','ml','audit')
GROUP BY n.nspname ORDER BY n.nspname;

SELECT version, applied_at, checksum FROM audit.schema_migrations ORDER BY applied_at;

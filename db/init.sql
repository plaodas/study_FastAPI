CREATE TABLE IF NOT EXISTS items (
        id SERIAL PRIMARY KEY,
        name VARCHAR(100)
);

-- seed only if table is empty
DO $$
BEGIN
    IF (SELECT COUNT(*) FROM items) = 0 THEN
        INSERT INTO items (name) VALUES ('Apple'), ('Banana'), ('Cherry');
    END IF;
END
$$;
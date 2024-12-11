-- setup.sql
DROP TABLE IF EXISTS ingredients;
DROP TABLE IF EXISTS recipes;

CREATE TABLE recipes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    category TEXT,
    preparation_time INTEGER,
    cooking_time INTEGER,
    instructions TEXT,
    notes TEXT
);

CREATE TABLE ingredients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    recipe_id INTEGER,
    quantity REAL,
    unit TEXT,
    ingredient_name TEXT,
    FOREIGN KEY(recipe_id) REFERENCES recipes(id)
);


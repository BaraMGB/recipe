DROP TABLE IF EXISTS ingredients;
DROP TABLE IF EXISTS recipes;
DROP TABLE IF EXISTS photos;

CREATE TABLE recipes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    category TEXT,
    in_menu BOOLEAN DEFAULT 0,
    menu_description TEXT,
    allergens TEXT,
    approximate_cost REAL,
    selling_price REAL,
    created_by TEXT,
    created_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    edited_by TEXT,
    edited_time TIMESTAMP,
    instructions TEXT,
    notes TEXT
);

CREATE TABLE ingredients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    recipe_id INTEGER,
    quantity REAL,
    unit TEXT,
    ingredient_name TEXT,
    display_order INTEGER,
    FOREIGN KEY(recipe_id) REFERENCES recipes(id)
);

CREATE TABLE photos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    recipe_id INTEGER,
    filename TEXT NOT NULL,
    FOREIGN KEY(recipe_id) REFERENCES recipes(id)
);

CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    role TEXT NOT NULL
);


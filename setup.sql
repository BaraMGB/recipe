DROP TABLE IF EXISTS ingredients;
DROP TABLE IF EXISTS recipes;
DROP TABLE IF EXISTS photos;

CREATE TABLE recipes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    category TEXT,
    menu_description TEXT,
    preparation_time INTEGER,
    cooking_time INTEGER,
    allergens TEXT,
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

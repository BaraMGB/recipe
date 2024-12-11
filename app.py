from flask import Flask, render_template, request, redirect, url_for
import sqlite3

app = Flask(__name__)

def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def index():
    # Zeige eine Liste aller Rezepte an
    conn = get_db_connection()
    recipes = conn.execute('SELECT id, name, category FROM recipes').fetchall()
    conn.close()
    return render_template('index.html', recipes=recipes)

@app.route('/recipe/<int:recipe_id>')
def show_recipe(recipe_id):
    # Einzelnes Rezept anzeigen, inklusive Zutaten
    conn = get_db_connection()
    recipe = conn.execute('SELECT * FROM recipes WHERE id = ?', (recipe_id,)).fetchone()
    if recipe is None:
        conn.close()
        return "Rezept nicht gefunden", 404

    ingredients = conn.execute('SELECT * FROM ingredients WHERE recipe_id = ?', (recipe_id,)).fetchall()
    conn.close()
    return render_template('recipe_detail.html', recipe=recipe, ingredients=ingredients)

@app.route('/new_recipe', methods=['GET', 'POST'])
def new_recipe():
    if request.method == 'POST':
        # Daten aus dem Formular holen
        name = request.form.get('name')
        category = request.form.get('category')
        preparation_time = request.form.get('preparation_time')
        cooking_time = request.form.get('cooking_time')
        instructions = request.form.get('instructions')
        notes = request.form.get('notes')

        # Zutaten sammeln (Felder heißen z. B. ingredient_name_1, unit_1, quantity_1, etc.)
        # Wir wissen nicht, wie viele Felder es gibt. Wir suchen nach allen Keys, die mit ingredient_name_ anfangen.
        ingredient_names = [key for key in request.form.keys() if key.startswith('ingredient_name_')]
        
        conn = get_db_connection()
        # Neues Rezept einfügen
        conn.execute('INSERT INTO recipes (name, category, preparation_time, cooking_time, instructions, notes) VALUES (?,?,?,?,?,?)',
                     (name, category, preparation_time, cooking_time, instructions, notes))
        recipe_id = conn.execute('SELECT last_insert_rowid()').fetchone()[0]

        # Jetzt die Zutaten einfügen
        for ingredient_key in ingredient_names:
            # Index extrahieren
            # ingredient_name_1 -> 1
            idx = ingredient_key.split('_')[-1]

            ingredient_name = request.form.get(f'ingredient_name_{idx}')
            unit = request.form.get(f'unit_{idx}')
            quantity = request.form.get(f'quantity_{idx}')

            # Nur einfügen, wenn tatsächlich ein Name und Menge angegeben wurde
            if ingredient_name and quantity:
                conn.execute('INSERT INTO ingredients (recipe_id, quantity, unit, ingredient_name) VALUES (?,?,?,?)',
                             (recipe_id, quantity, unit, ingredient_name))

        conn.commit()
        conn.close()

        return redirect(url_for('show_recipe', recipe_id=recipe_id))

    # GET-Anfrage: Formular anzeigen
    return render_template('new_recipe.html')


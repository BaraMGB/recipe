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

    ingredients = conn.execute('SELECT * FROM ingredients WHERE recipe_id = ? ORDER BY display_order', (recipe_id,)).fetchall()
    conn.close()
    return render_template('recipe_detail.html', recipe=recipe, ingredients=ingredients)

@app.route('/new_recipe', methods=['GET', 'POST'])
def new_recipe():
    if request.method == 'POST':
        # Daten aus dem Formular holen
        name = request.form.get('name')
        category = request.form.get('category')
        menu_description = request.form.get('menu_description')
        preparation_time = request.form.get('preparation_time')
        cooking_time = request.form.get('cooking_time')
        allergens = request.form.get('allergens')
        instructions = request.form.get('instructions')
        notes = request.form.get('notes')

        # Zutaten sammeln (Felder heißen z. B. ingredient_name_1, unit_1, quantity_1, etc.)
        # Wir wissen nicht, wie viele Felder es gibt. Wir suchen nach allen Keys, die mit ingredient_name_ anfangen.
        ingredient_names = [key for key in request.form.keys() if key.startswith('ingredient_name_')]
        
        conn = get_db_connection()
        # Neues Rezept einfügen
        conn.execute('INSERT INTO recipes (name, category, menu_description, preparation_time, cooking_time, allergens, instructions, notes) VALUES (?,?,?,?,?,?,?,?)',
                     (name, category, menu_description, preparation_time, cooking_time, allergens, instructions, notes))
        recipe_id = conn.execute('SELECT last_insert_rowid()').fetchone()[0]

        # Jetzt die Zutaten einfügen
        for ingredient_key in ingredient_names:
            # Index extrahieren
            # ingredient_name_1 -> 1
            idx = ingredient_key.split('_')[-1]

            ingredient_name = request.form.get(f'ingredient_name_{idx}')
            unit = request.form.get(f'unit_{idx}')
            quantity = request.form.get(f'quantity_{idx}')

            # Setze die display_order basierend auf dem Index
            display_order = ingredient_names.index(ingredient_key) + 1

            # Nur einfügen, wenn tatsächlich ein Name und Menge angegeben wurde
            if ingredient_name and quantity:
                conn.execute('INSERT INTO ingredients (recipe_id, quantity, unit, ingredient_name, display_order) VALUES (?,?,?,?,?)',
                             (recipe_id, quantity, unit, ingredient_name, display_order))

        conn.commit()
        conn.close()

        return redirect(url_for('show_recipe', recipe_id=recipe_id))

    # GET-Anfrage: Formular anzeigen
    return render_template('new_recipe.html')




@app.route('/edit_recipe/<int:recipe_id>', methods=['GET', 'POST'])
def edit_recipe(recipe_id):
    conn = get_db_connection()
    recipe = conn.execute('SELECT * FROM recipes WHERE id = ?', (recipe_id,)).fetchone()
    if recipe is None:
        conn.close()
        return "Rezept nicht gefunden", 404

    ingredients = conn.execute('SELECT * FROM ingredients WHERE recipe_id = ? ORDER BY display_order', (recipe_id,)).fetchall()
    conn.close()

    if request.method == 'POST':
        # Rezept-Daten aktualisieren
        name = request.form.get('name')
        category = request.form.get('category')
        menu_description = request.form.get('menu_description')
        preparation_time = request.form.get('preparation_time')
        cooking_time = request.form.get('cooking_time')
        allergens = request.form.get('allergens')
        instructions = request.form.get('instructions')
        notes = request.form.get('notes')

        conn = get_db_connection()
        conn.execute('UPDATE recipes SET name = ?, category = ?, menu_description = ?, preparation_time = ?, cooking_time = ?, allergens = ?, instructions = ?, notes = ? WHERE id = ?',
                     (name, category, menu_description, preparation_time, cooking_time, allergens, instructions, notes, recipe_id))

        # Zutaten aktualisieren oder löschen
        # Hier wird es etwas komplexer, da wir hinzugefügte, gelöschte und bearbeitete Zutaten berücksichtigen müssen.
        # Zunächst holen wir die IDs der vorhandenen Zutaten aus der Datenbank.
        existing_ingredient_ids = [ingr['id'] for ingr in ingredients]

        # Dann iterieren wir über die submitted ingredient IDs im Formular
        submitted_ingredient_ids = []
        for key in request.form.keys():
            if key.startswith('ingredient_id_'):
                value = request.form.get(key)
                if value:  # Überprüfe, ob der Wert nicht leer ist
                    submitted_ingredient_ids.append(int(value))

        # Zutaten löschen, die nicht mehr im Formular sind
        for ingr_id in existing_ingredient_ids:
            if ingr_id not in submitted_ingredient_ids:
                conn.execute('DELETE FROM ingredients WHERE id = ?', (ingr_id,))
        
        # Zutaten aktualisieren oder neu hinzufügen
        ingredient_names = [key for key in request.form.keys() if key.startswith('ingredient_name_')]
        for ingredient_index, ingredient_key in enumerate(ingredient_names):
            # Index extrahieren, falls vorhanden
            if '_' in ingredient_key:
                idx = ingredient_key.split('_')[-1]
            else:
                idx = None

            ingredient_id = request.form.get(f'ingredient_id_{idx}')
            ingredient_name = request.form.get(f'ingredient_name_{idx}')
            unit = request.form.get(f'unit_{idx}')
            quantity = request.form.get(f'quantity_{idx}')

            # Setze die display_order basierend auf dem aktuellen Index
            display_order = ingredient_index + 1

            if ingredient_name and quantity:
                if ingredient_id and int(ingredient_id) in existing_ingredient_ids:
                    # Zutat aktualisieren
                    conn.execute('UPDATE ingredients SET quantity = ?, unit = ?, ingredient_name = ?, display_order = ? WHERE id = ?',
                                 (quantity, unit, ingredient_name, display_order, ingredient_id))
                else:
                    # Neue Zutat hinzufügen
                    conn.execute('INSERT INTO ingredients (recipe_id, quantity, unit, ingredient_name, display_order) VALUES (?,?,?,?,?)',
                                 (recipe_id, quantity, unit, ingredient_name, display_order))

        conn.commit()
        conn.close()

        return redirect(url_for('show_recipe', recipe_id=recipe_id))

    return render_template('edit_recipe.html', recipe=recipe, ingredients=ingredients)
@app.route('/delete_recipe/<int:recipe_id>', methods=['POST'])
def delete_recipe(recipe_id):
    conn = get_db_connection()
    conn.execute('DELETE FROM ingredients WHERE recipe_id = ?', (recipe_id,))
    conn.execute('DELETE FROM recipes WHERE id = ?', (recipe_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

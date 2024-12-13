from flask import Flask, render_template, request, redirect, url_for, send_from_directory
import sqlite3
import os
import secrets
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Konfiguration für Uploads
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB

def get_db_connection():
    conn = sqlite3.connect('database.db', timeout=10, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/')
def index():
    conn = get_db_connection()
    recipes = conn.execute('SELECT id, name, category FROM recipes').fetchall()
    conn.close()
    return render_template('index.html', recipes=recipes)

@app.route('/recipe/<int:recipe_id>')
def show_recipe(recipe_id):
    conn = get_db_connection()
    recipe = conn.execute('SELECT * FROM recipes WHERE id = ?', (recipe_id,)).fetchone()
    if recipe is None:
        conn.close()
        return "Rezept nicht gefunden", 404

    ingredients = conn.execute('SELECT * FROM ingredients WHERE recipe_id = ?', (recipe_id,)).fetchall()
    photos = conn.execute('SELECT * FROM photos WHERE recipe_id = ?', (recipe_id,)).fetchall()
    conn.close()
    return render_template('recipe_detail.html', recipe=recipe, ingredients=ingredients, photos=photos)

@app.route('/new_recipe', methods=['GET', 'POST'])
def new_recipe():
    if request.method == 'POST':
        name = request.form.get('name')
        category = request.form.get('category')
        preparation_time = request.form.get('preparation_time')
        cooking_time = request.form.get('cooking_time')
        instructions = request.form.get('instructions')
        notes = request.form.get('notes')

        conn = get_db_connection()
        cursor = conn.execute('INSERT INTO recipes (name, category, preparation_time, cooking_time, instructions, notes) VALUES (?,?,?,?,?,?)',
                     (name, category, preparation_time, cooking_time, instructions, notes))
        recipe_id = cursor.lastrowid

        ingredient_names = [key for key in request.form.keys() if key.startswith('ingredient_name_')]
        for ingredient_key in ingredient_names:
            idx = ingredient_key.split('_')[-1]
            ingredient_name = request.form.get(f'ingredient_name_{idx}')
            unit = request.form.get(f'unit_{idx}')
            quantity = request.form.get(f'quantity_{idx}')

            if ingredient_name and quantity:
                conn.execute('INSERT INTO ingredients (recipe_id, quantity, unit, ingredient_name) VALUES (?,?,?,?)',
                             (recipe_id, quantity, unit, ingredient_name))

        # Fotos verarbeiten
        if 'photos' in request.files:
            for file in request.files.getlist('photos'):
                if file and allowed_file(file.filename):
                    random_hex = secrets.token_hex(8)
                    _, f_ext = os.path.splitext(file.filename)
                    filename = random_hex + f_ext
                    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    file.save(filepath)
                    conn.execute('INSERT INTO photos (recipe_id, filename) VALUES (?, ?)', (recipe_id, filename))

        conn.commit()
        conn.close()
        return redirect(url_for('show_recipe', recipe_id=recipe_id))

    return render_template('new_recipe.html')

@app.route('/edit_recipe/<int:recipe_id>', methods=['GET', 'POST'])
def edit_recipe(recipe_id):
    if request.method == 'POST':
        name = request.form.get('name')
        category = request.form.get('category')
        preparation_time = request.form.get('preparation_time')
        cooking_time = request.form.get('cooking_time')
        instructions = request.form.get('instructions')
        notes = request.form.get('notes')

        ingredients_data = []
        for key in request.form.keys():
            if key.startswith('ingredient_name_'):
                idx = key.split('_')[-1]
                ingredient_name = request.form.get(f'ingredient_name_{idx}')
                unit = request.form.get(f'unit_{idx}')
                quantity = request.form.get(f'quantity_{idx}')
                if ingredient_name and quantity:
                    ingredients_data.append({
                        'name': ingredient_name,
                        'unit': unit,
                        'quantity': quantity,
                    })

        with get_db_connection() as conn:
            conn.execute('UPDATE recipes SET name = ?, category = ?, preparation_time = ?, cooking_time = ?, instructions = ?, notes = ? WHERE id = ?',
                         (name, category, preparation_time, cooking_time, instructions, notes, recipe_id))

            conn.execute('DELETE FROM ingredients WHERE recipe_id = ?', (recipe_id,))
            for ingredient in ingredients_data:
                conn.execute('INSERT INTO ingredients (recipe_id, quantity, unit, ingredient_name) VALUES (?,?,?,?)',
                             (recipe_id, ingredient['quantity'], ingredient['unit'], ingredient['name']))

            if 'photos' in request.files:
                for file in request.files.getlist('photos'):
                    if file and allowed_file(file.filename):
                        random_hex = secrets.token_hex(8)
                        _, f_ext = os.path.splitext(file.filename)
                        filename = random_hex + f_ext
                        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                        file.save(filepath)
                        conn.execute('INSERT INTO photos (recipe_id, filename) VALUES (?, ?)', (recipe_id, filename))

            conn.commit()

        return redirect(url_for('show_recipe', recipe_id=recipe_id))

    conn = get_db_connection()
    recipe = conn.execute('SELECT * FROM recipes WHERE id = ?', (recipe_id,)).fetchone()
    ingredients = conn.execute('SELECT * FROM ingredients WHERE recipe_id = ?', (recipe_id,)).fetchall()
    photos = conn.execute('SELECT * FROM photos WHERE recipe_id = ?', (recipe_id,)).fetchall()
    conn.close()

    if recipe is None:
        return "Rezept nicht gefunden", 404

    return render_template('edit_recipe.html', recipe=recipe, ingredients=ingredients, photos=photos)

@app.route('/delete_recipe/<int:recipe_id>', methods=['POST'])
def delete_recipe(recipe_id):
    with get_db_connection() as conn:
        photos = conn.execute('SELECT filename FROM photos WHERE recipe_id = ?', (recipe_id,)).fetchall()
        for photo in photos:
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], photo['filename'])
            if os.path.exists(filepath):
                os.remove(filepath)

        conn.execute('DELETE FROM photos WHERE recipe_id = ?', (recipe_id,))
        conn.execute('DELETE FROM ingredients WHERE recipe_id = ?', (recipe_id,))
        conn.execute('DELETE FROM recipes WHERE id = ?', (recipe_id,))
        conn.commit()

    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)


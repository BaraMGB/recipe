from flask import Flask, render_template, request, redirect, url_for, send_from_directory, flash, session
import sqlite3
import os
import secrets
from werkzeug.utils import secure_filename
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from dotenv import load_dotenv
app = Flask(__name__)


# Konfiguration für Uploads
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB

app.secret_key = os.urandom(24)

# .env laden
load_dotenv()

# Beispiel: Passwort aus .env
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "default_password")

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin):
    def __init__(self, id, username, password, role):
        self.id = id
        self.username = username
        self.password = password
        self.role = role

users = {
    "Admin": User(id=1, username="Admin", password=ADMIN_PASSWORD, role="Admin"),
    "Rudi": User(id=2, username="Rudi", password=os.getenv("RUDI_PASSWORD", "default_rudi_password"), role="Editor"),
    "Franzi": User(id=3, username="Franzi", password=os.getenv("FRANZI_PASSWORD", "default_franzi_password"), role="Viewer"),
    "Anton": User(id=4, username="Anton", password=os.getenv("ANTON_PASSWORD", "default_anton_password"), role="Viewer"),
    "Steffen": User(id=5, username="Steffen", password=os.getenv("STEFFEN_PASSWORD", "default_steffen_password"), role="Editor"),
    "Service": User(id=6, username="Service", password=os.getenv("SERVICE_PASSWORD", "default_service_password"), role="Service"),
}

def has_permission(permission):
    role_permissions = {
        "Admin": ["add", "delete", "edit", "view"],
        "Editor": ["add", "delete", "edit", "view"],
        "Viewer": ["view"],
    }
    return permission in role_permissions.get(current_user.role, [])

@login_manager.user_loader
def load_user(user_id):
    for user in users.values():
        if str(user.id) == user_id:
            return user
    return None

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = next((u for u in users.values() if u.username == username and u.password == password), None)
        if user:
            login_user(user)
            return redirect(url_for('index'))
        flash('Ungültige Anmeldedaten', 'danger')
    return render_template('login.html')

@app.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))


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
@login_required
def index():
    search_query = request.args.get('search', '').strip()  # Suchbegriff aus der URL abrufen
    conn = get_db_connection()

    # SQL-Basisabfrage
    base_query = 'SELECT id, name, category FROM recipes'
    photos_query = 'SELECT recipe_id, filename FROM photos'
    params = []

    # Filter hinzufügen, falls Suchbegriff vorhanden
    if search_query:
        base_query += ' WHERE name LIKE ? OR category LIKE ?'
        params.extend([f'%{search_query}%', f'%{search_query}%'])

    recipes = conn.execute(base_query, params).fetchall()
    photos_result = conn.execute(photos_query).fetchall()
    conn.close()

    # Fotos nach Rezept gruppieren
    photos = {}
    for photo in photos_result:
        if photo['recipe_id'] not in photos:
            photos[photo['recipe_id']] = []
        photos[photo['recipe_id']].append(photo)

    return render_template('index.html', recipes=recipes, photos=photos, search=search_query)


@app.route('/recipe/<int:recipe_id>')
@login_required
def show_recipe(recipe_id):
    conn = get_db_connection()
    recipe = conn.execute('SELECT * FROM recipes WHERE id = ?', (recipe_id,)).fetchone()
    if recipe is None:
        conn.close()
        return "Rezept nicht gefunden", 404

    ingredients = conn.execute('SELECT * FROM ingredients WHERE recipe_id = ?', (recipe_id,)).fetchall()
    photos = conn.execute('SELECT * FROM photos WHERE recipe_id = ?', (recipe_id,)).fetchall()
    conn.close()

    # Überprüfe die Rolle des Benutzers
    if current_user.role == "Service":
        return render_template('recipe_detail_service.html', recipe=recipe, ingredients=ingredients, photos=photos)
    else:
        return render_template('recipe_detail.html', recipe=recipe, ingredients=ingredients, photos=photos)

@app.route('/new_recipe', methods=['GET', 'POST'])
@login_required
def new_recipe():
    if not has_permission("add"):
        return "Nicht erlaubt", 403
    if request.method == 'POST':
        name = request.form.get('name')
        menu_description = request.form.get('menu_description')
        category = request.form.get('category')
        preparation_time = request.form.get('preparation_time')
        cooking_time = request.form.get('cooking_time')
        allergens = request.form.get('allergens')
        instructions = request.form.get('instructions')
        notes = request.form.get('notes')

        conn = get_db_connection()
        cursor = conn.execute('INSERT INTO recipes (name, menu_description, category, preparation_time, cooking_time, allergens, instructions, notes) VALUES (?,?,?,?,?,?)',
                     (name, menu_description, category, preparation_time, cooking_time, allergens, instructions, notes))
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
    if not has_permission("edit"):  # Berechtigung prüfen
        return "Nicht erlaubt", 403
    if request.method == 'POST':
        name = request.form.get('name')
        menu_description = request.form.get('menu_description')
        category = request.form.get('category')
        preparation_time = request.form.get('preparation_time')
        cooking_time = request.form.get('cooking_time')
        allergens = request.form.get('allergens')
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
            conn.execute('UPDATE recipes SET name = ?, menu_description = ?,  category = ?, preparation_time = ?, cooking_time = ?, allergens = ?, instructions = ?, notes = ? WHERE id = ?',
                         (name, menu_description, category, preparation_time, cooking_time, allergens, instructions, notes, recipe_id))

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

            # Fotos zum Löschen prüfen
            delete_photo_ids = [key.split('_')[-1] for key in request.form.keys() if key.startswith('delete_photo_')]
            for photo_id in delete_photo_ids:
                if request.form.get(f'delete_photo_{photo_id}') == '1':  # Nur markierte Fotos löschen
                    photo = conn.execute('SELECT filename FROM photos WHERE id = ?', (photo_id,)).fetchone()
                    if photo:
                        filepath = os.path.join(app.config['UPLOAD_FOLDER'], photo['filename'])
                        if os.path.exists(filepath):
                            os.remove(filepath)
                        conn.execute('DELETE FROM photos WHERE id = ?', (photo_id,))

            conn.commit()

        return redirect(url_for('show_recipe', recipe_id=recipe_id))

    conn = get_db_connection()
    recipe = conn.execute('SELECT * FROM recipes WHERE id = ?', (recipe_id,)).fetchone()
    ingredients = conn.execute('SELECT * FROM ingredients WHERE recipe_id = ?', (recipe_id,)).fetchall()
    photos = conn.execute('SELECT id, filename FROM photos WHERE recipe_id = ?', (recipe_id,)).fetchall()

    conn.close()

    if recipe is None:
        return "Rezept nicht gefunden", 404

    return render_template('edit_recipe.html', recipe=recipe, ingredients=ingredients, photos=photos)

@app.route('/delete_recipe/<int:recipe_id>', methods=['POST'])
def delete_recipe(recipe_id):
    if not has_permission("delete"):
        return "Nicht erlaubt", 403
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

@app.route('/delete_photo/<int:photo_id>', methods=['POST'])
def delete_photo(photo_id):
    with get_db_connection() as conn:
        photo = conn.execute('SELECT filename FROM photos WHERE id = ?', (photo_id,)).fetchone()
        if photo:
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], photo['filename'])
            if os.path.exists(filepath):
                os.remove(filepath)
            conn.execute('DELETE FROM photos WHERE id = ?', (photo_id,))
            conn.commit()
    return redirect(request.referrer)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)


from flask import Flask, render_template, request, redirect, url_for, send_from_directory, flash, session
import sqlite3
import os
import secrets
from werkzeug.utils import secure_filename
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from dotenv import load_dotenv
from datetime import timedelta
import bcrypt
import logging


logging.basicConfig(
    level=logging.INFO,  # Loglevel auf INFO setzen
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()  # Logs an stdout senden
    ]
)


app = Flask(__name__)

app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)  # Sitzungsdauer auf 30 Minuten festlegen
app.config['SESSION_PERMANENT'] = True

@app.before_request
def make_session_permanent():
    session.permanent = True


def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

def check_password(password, hashed_password):
    return bcrypt.checkpw(password.encode('utf-8'), hashed_password)


# Konfiguration für Uploads
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB

app.secret_key = os.urandom(24)

# .env laden
load_dotenv()

# Beispiel: Passwort aus .env

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin):
    def __init__(self, id, username, password, role):
        self.id = id
        self.username = username
        self.password = password
        self.role = role


def has_permission(permission):
    role_permissions = {
        "Admin": ["add", "delete", "edit", "view"],
        "Editor": ["add", "delete", "edit", "view"],
        "Viewer": ["view"],
    }
    return permission in role_permissions.get(current_user.role, [])


@app.route('/register', methods=['GET', 'POST'])
def register():
    if not REGISTRATION_ENABLED:
        flash("Registrierung ist derzeit deaktiviert.", "warning")
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        conn = get_db_connection()

        # Überprüfe, ob bereits Benutzer existieren
        existing_users = conn.execute('SELECT COUNT(*) FROM users').fetchone()[0]

        if existing_users == 0:
            # Erster Benutzer wird als Admin registriert
            role = "Admin"
        else:
            # Standardrolle für neue Benutzer
            role = "Service"

        hashed_pw = hash_password(password)
        try:
            conn.execute('INSERT INTO users (username, password, role) VALUES (?, ?, ?)', (username, hashed_pw, role))
            conn.commit()
            flash('Registrierung erfolgreich. Sie können sich jetzt einloggen.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Benutzername existiert bereits.', 'danger')
        finally:
            conn.close()

    return render_template('register.html')

@login_manager.user_loader
def load_user(user_id):
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    conn.close()
    if user:
        return User(id=user['id'], username=user['username'], password=user['password'], role=user['role'])
    return None


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        conn.close()

        if user and check_password(password, user['password']):
            user_obj = User(id=user['id'], username=user['username'], password=user['password'], role=user['role'])
            login_user(user_obj)
            logging.info(f"User {username} logged in successfully.")
            return redirect(url_for('index'))
        client_ip = request.remote_addr
        logging.warning(f"Failed login attempt for username: {username} from IP: {client_ip}")
        flash('Ungültige Anmeldedaten', 'danger')
    return render_template('login.html')

@app.route('/logout', methods=['POST'])
@login_required
def logout():
    logging.info(f"User {current_user.username} logged out.")
    session.clear()  # Sitzung löschen
    logout_user()    # Benutzer abmelden
    return redirect(url_for('index'))

DATABASE_PATH = os.path.join('/data', 'database.db')

def get_db_connection():
    conn = sqlite3.connect(DATABASE_PATH, timeout=10, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_categories():
    conn = get_db_connection()
    categories_string = conn.execute('SELECT value FROM settings WHERE key = ?', ('categories',)).fetchone()
    conn.close()
    if categories_string:
        return [cat.strip() for cat in categories_string['value'].split(',')]
    return []

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

REGISTRATION_ENABLED = True  # Globale Variable für die Registrierung
@app.route('/admin', methods=['GET', 'POST'])
@login_required
def admin():
    if current_user.role != "Admin":
        return "Nicht erlaubt", 403

    conn = get_db_connection()

    if request.method == 'POST':
        # Kategorien aktualisieren
        if 'categories' in request.form:
            categories_string = request.form.get('categories')
            conn.execute('UPDATE settings SET value = ? WHERE key = ?', (categories_string, 'categories'))
            conn.commit()
            flash('Kategorien wurden aktualisiert.', 'success')

    # Benutzer und Kategorien laden
    users = conn.execute('SELECT * FROM users').fetchall()
    categories_string = conn.execute('SELECT value FROM settings WHERE key = ?', ('categories',)).fetchone()
    conn.close()

    return render_template('admin.html', users=users, categories_string=categories_string['value'] if categories_string else '')

@app.route('/edit_user_role/<int:user_id>', methods=['POST'])
@login_required
def edit_user_role(user_id):
    if current_user.role != "Admin":
        return "Nicht erlaubt", 403

    # Verhindere, dass der Admin seine eigene Rolle ändert
    if current_user.id == user_id:
        flash("Du kannst deine eigene Rolle nicht ändern!", "danger")
        return redirect(url_for('admin'))

    new_role = request.form.get('role')

    conn = get_db_connection()
    conn.execute('UPDATE users SET role = ? WHERE id = ?', (new_role, user_id))
    conn.commit()
    conn.close()

    return redirect(url_for('admin'))

@app.route('/delete_user/<int:user_id>', methods=['POST'])
@login_required
def delete_user(user_id):
    if current_user.role != "Admin":
        return "Nicht erlaubt", 403

    # Verhindere, dass der Admin sich selbst löscht
    if current_user.id == user_id:
        flash("Du kannst dich nicht selbst löschen!", "danger")
        return redirect(url_for('admin'))

    conn = get_db_connection()
    conn.execute('DELETE FROM users WHERE id = ?', (user_id,))
    conn.commit()
    conn.close()

    return redirect(url_for('admin'))

@app.route('/toggle_registration', methods=['POST'])
@login_required
def toggle_registration():
    if current_user.role != "Admin":
        return "Nicht erlaubt", 403

    global REGISTRATION_ENABLED
    REGISTRATION_ENABLED = not REGISTRATION_ENABLED

    return redirect(url_for('admin'))

@app.route('/')
@login_required
def index():
    search_query = request.args.get('search', '').strip()  # Suchbegriff aus der URL abrufen
    conn = get_db_connection()

    # Kategorien aus der Datenbank laden
    categories = conn.execute('SELECT value FROM settings WHERE key = ?', ('categories',)).fetchone()
    categories_list = [cat.strip() for cat in categories['value'].split(',')] if categories else []

    # Rezepte mit ihrem ersten Foto abrufen
    recipes = conn.execute('''
        SELECT r.id, r.name, r.category, r.menu_description, CAST(r.selling_price AS REAL) AS selling_price,
               (SELECT filename FROM photos WHERE photos.recipe_id = r.id LIMIT 1) AS photo
        FROM recipes r
        WHERE r.name LIKE ? OR r.category LIKE ?
    ''', (f'%{search_query}%', f'%{search_query}%')).fetchall()
    conn.close()

    # Sortierung basierend auf Kategorien und Preisen
    sorted_recipes = sorted(recipes, key=lambda r: (categories_list.index(r['category']) if r['category'] in categories_list else len(categories_list), r['selling_price']))

    # Fotos nach Rezept gruppieren
    photos = {}
    for recipe in recipes:
        if recipe['id'] not in photos:
            photos[recipe['id']] = []
        photo = recipe['photo']
        if photo:
            photos[recipe['id']].append({'filename': photo})

    return render_template('index.html', recipes=sorted_recipes, photos=photos, search=search_query)

@app.route('/recipe/<int:recipe_id>')
@login_required
def show_recipe(recipe_id):
    conn = get_db_connection()
    recipe = conn.execute('SELECT * FROM recipes WHERE id = ?', (recipe_id,)).fetchone()
    if recipe is None:
        conn.close()
        return "Rezept nicht gefunden", 404

    ingredients = conn.execute('SELECT * FROM ingredients WHERE recipe_id = ?', (recipe_id,)).fetchall()

    # Prüfen, ob Zutaten einem Rezeptnamen entsprechen
    linked_ingredients = []
    for ingredient in ingredients:
        linked_recipe = conn.execute('SELECT id FROM recipes WHERE name = ?', (ingredient['ingredient_name'],)).fetchone()
        linked_ingredients.append({
            'name': ingredient['ingredient_name'],
            'quantity': ingredient['quantity'],
            'unit': ingredient['unit'],
            'linked_recipe_id': linked_recipe['id'] if linked_recipe else None
        })

    photos = conn.execute('SELECT * FROM photos WHERE recipe_id = ?', (recipe_id,)).fetchall()
    conn.close()

    # Konvertiere das Rezept zu einem Dictionary und stelle sicher, dass selling_price und approximate_cost Floats sind
    recipe = dict(recipe)
    recipe['selling_price'] = float(recipe['selling_price']) if recipe['selling_price'] else 0.0
    recipe['approximate_cost'] = float(recipe['approximate_cost']) if recipe['approximate_cost'] else 0.0

    # Überprüfe die Rolle des Benutzers
    if current_user.role == "Service":
        return render_template('recipe_detail_service.html', recipe=recipe, ingredients=ingredients, photos=photos)
    else:
        return render_template('recipe_detail.html', recipe=recipe, ingredients=linked_ingredients, photos=photos)
@app.route('/new_recipe', methods=['GET', 'POST'])
@login_required
def new_recipe():
    if not has_permission("add"):
        return "Nicht erlaubt", 403
    if request.method == 'POST':
        name = request.form.get('name')
        menu_description = request.form.get('menu_description')
        category = request.form.get('category')
        in_menu = request.form.get('in_menu') == 'on'  # Checkbox-Wert
        allergens = request.form.get('allergens')
        approximate_cost = request.form.get('approximate_cost')
        selling_price = request.form.get('selling_price')
        instructions = request.form.get('instructions')
        notes = request.form.get('notes')

        conn = get_db_connection()
        user = current_user.username  # Benutzername des aktuell angemeldeten Benutzers
        cursor = conn.execute(
            'INSERT INTO recipes (name, menu_description, category, in_menu, approximate_cost, selling_price, allergens, instructions, notes, created_by) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (name, menu_description, category, in_menu, approximate_cost, selling_price, allergens, instructions, notes, user)
        )
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

    categories = get_categories()
    return render_template('new_recipe.html', categories=categories)

@app.route('/edit_recipe/<int:recipe_id>', methods=['GET', 'POST'])
def edit_recipe(recipe_id):
    if not has_permission("edit"):  # Berechtigung prüfen
        return "Nicht erlaubt", 403
    if request.method == 'POST':
        name = request.form.get('name')
        menu_description = request.form.get('menu_description')
        category = request.form.get('category')
        in_menu = request.form.get('in_menu') == 'on'
        approximate_cost = request.form.get('approximate_cost')
        selling_price = request.form.get('selling_price')
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
            user = current_user.username  # Benutzername des aktuell angemeldeten Benutzers
            conn.execute(
                'UPDATE recipes SET name=?, menu_description=?, category=?, in_menu=?, approximate_cost=?, selling_price=?, allergens=?, instructions=?, notes=?, edited_by=?, edited_time=CURRENT_TIMESTAMP WHERE id=?',
                (name, menu_description, category, in_menu,  approximate_cost, selling_price, allergens, instructions, notes, user, recipe_id)
            )
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

    categories = get_categories()
    return render_template('edit_recipe.html', categories=categories, recipe=recipe, ingredients=ingredients, photos=photos)

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

@app.route('/menu')
def menu():
    conn = get_db_connection()
    categories = get_categories()
    # Rezepte mit ihrem ersten Foto abrufen, sortiert nach Kategorie und Preis
    recipes = conn.execute('''
        SELECT r.name, r.category, r.menu_description, CAST(r.selling_price AS REAL) AS selling_price, r.id,
            (SELECT filename FROM photos WHERE photos.recipe_id = r.id LIMIT 1) AS photo
        FROM recipes r
        WHERE r.in_menu = 1
        ORDER BY r.category, r.selling_price
    ''').fetchall()
    conn.close()

    # Kategorien gruppieren
    categorized_recipes = {category: [] for category in categories}
    for recipe in recipes:
        category = recipe['category']
        if category in categorized_recipes:
            categorized_recipes[category].append(recipe)

    # Entfernen von Kategorien ohne Rezepte
    categorized_recipes = {k: v for k, v in categorized_recipes.items() if v}


    return render_template('menu.html', categorized_recipes=categorized_recipes)

# if __name__ == "__main__":
#     app.run(host="0.0.0.0", port=5000)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, ssl_context=(
        "/etc/ssl/certs/fullchain.pem",
        "/etc/ssl/private/privkey.pem"
    ))

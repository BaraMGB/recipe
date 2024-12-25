# Recipes App

A simple web application to manage, upload, and share recipes.

## Features
- **Recipe Management:** Create, edit, and delete recipes.
- **Image Uploads:** Support for uploading recipe images.
- **User-Friendly Design:** A clean and straightforward user interface.

## Project Structure

```plaintext
.
├── app
│   ├── app.py              # Main Flask application
│   ├── setup.sql           # SQL script to initialize the database
│   ├── static              # Static files (CSS, images)
│   ├── templates           # HTML templates
│   └── uploads             # Uploaded recipe images
├── data
│   └── database.db         # SQLite database (created at first run)
├── docker-compose.yml      # Docker configuration for the app
├── requirements.txt        # Python dependencies
└── README.md               # This file
```
## Installation

Clone the repository:
```
git clone <repository-url>
cd rezepte_app
```
## Install dependencies:

```
pip install -r requirements.txt
```
## Initialize the database:

```
sqlite3 data/database.db < app/setup.sql
```

## Set up environment variables: Create a .env file with the required variables:

```
FLASK_ENV=production
FLASK_APP=app.py
```

## Run the application:

```
python app/app.py
```

## Using Docker

You can also run the application using Docker:

Start the container:
```
docker-compose up -d
```
Access the app: Visit http://localhost:5000 in your browser.

## To-Do

 - User registration and authentication
 - Multi-language support
 - Improved recipe categorization

## License

This project is licensed under the MIT License.

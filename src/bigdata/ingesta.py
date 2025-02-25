import requests
import sqlite3
import json

def obtener_datos_api(url="", params={}):
    try:
        response = requests.get(url, params=params)  
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as error:
        print(f"Error al hacer la solicitud: {error}")
        return {}

# Solicitar búsqueda desde la terminal
busqueda = input("Ingrese el término de búsqueda para Google Books: ")

# API de Google Books
url = "https://www.googleapis.com/books/v1/volumes"

# Parámetros para buscar libros
parametros = {
    "q": busqueda,  # Se usa el término ingresado en la terminal
    "maxResults": 20,      
    "printType": "books"
}

# Llamada a la API
datos = obtener_datos_api(url, parametros)

# Conexión a SQLite
conexion = sqlite3.connect("ingesta.db")
cursor = conexion.cursor()

# Creación de tablas
cursor.execute('''
    CREATE TABLE IF NOT EXISTS books (
        id TEXT PRIMARY KEY,
        title TEXT,
        description TEXT,
        publishedDate TEXT
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS authors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS books_authors (
        book_id TEXT,
        author_id INTEGER,
        PRIMARY KEY (book_id, author_id),
        FOREIGN KEY (book_id) REFERENCES books (id) ON DELETE CASCADE,
        FOREIGN KEY (author_id) REFERENCES authors (id) ON DELETE CASCADE
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS books_categories (
        book_id TEXT,
        category_id INTEGER,
        PRIMARY KEY (book_id, category_id),
        FOREIGN KEY (book_id) REFERENCES books (id) ON DELETE CASCADE,
        FOREIGN KEY (category_id) REFERENCES categories (id) ON DELETE CASCADE
    )
''')

# Limpiar las relaciones antes de insertar nuevos datos
cursor.execute("DELETE FROM books_authors")
cursor.execute("DELETE FROM books_categories")
cursor.execute("DELETE FROM books")
cursor.execute("DELETE FROM authors")
conexion.commit()

# Recolectar los datos desde la API y rellenar la base de datos
if datos and "items" in datos:
    for item in datos["items"]:
        try:
            book_id = item["id"]
            title = item["volumeInfo"].get("title", "Desconocido")
            description = item["volumeInfo"].get("description", "Desconocido")
            published_date = item["volumeInfo"].get("publishedDate", "Desconocido")

            # Insertar o actualizar en books
            cursor.execute('INSERT OR REPLACE INTO books (id, title, description, publishedDate) VALUES (?, ?, ?, ?)',
                           (book_id, title, description, published_date))

            # Insertar autores y establecer relación
            authors = item["volumeInfo"].get("authors", [])
            for author in authors:
                cursor.execute('INSERT OR IGNORE INTO authors (name) VALUES (?)', (author,))
                cursor.execute('SELECT id FROM authors WHERE name = ?', (author,))
                author_id = cursor.fetchone()[0]

                cursor.execute('INSERT OR IGNORE INTO books_authors (book_id, author_id) VALUES (?, ?)',
                               (book_id, author_id))

            # Insertar categorías y establecer relación
            categories = item["volumeInfo"].get("categories", [])
            for category in categories:
                cursor.execute('INSERT OR IGNORE INTO categories (name) VALUES (?)', (category,))
                cursor.execute('SELECT id FROM categories WHERE name = ?', (category,))
                category_id = cursor.fetchone()[0]

                cursor.execute('INSERT OR IGNORE INTO books_categories (book_id, category_id) VALUES (?, ?)',
                               (book_id, category_id))

        except KeyError as e:
            print(f"Error al procesar un libro: {e}")

    # Guardar datos
    conexion.commit()
    print(f"Datos insertados correctamente en SQLite para la búsqueda: '{busqueda}'.")
else:
    print("No se obtuvieron datos para insertar en la base de datos.")

conexion.close()

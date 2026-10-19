"""Acceso a la base de datos SQLite de DevPythonQuiz.

Toda la persistencia vive aquí: creación de tablas, consultas de usuarios,
preguntas y partidas. Todas las funciones abren y cierran su propia
conexión mediante `get_connection()`, por lo que no hace falta gestionar
conexiones fuera de este módulo.

La base de datos es un fichero `devquiz.db` junto al código (ignorado por
git para no versionar datos de usuarios).
"""

import sqlite3
from contextlib import contextmanager
from pathlib import Path

# Ruta del fichero de base de datos: siempre junto a este módulo.
# Los tests lo redefinen (monkeypatch) para usar una BD temporal.
DB_PATH = Path(__file__).parent / "devquiz.db"


@contextmanager
def get_connection():
    """Devuelve una conexión a la base de datos y la cierra al terminar.

    Uso::

        with get_connection() as conn:
            cursor = conn.cursor()
            ...

    `row_factory = sqlite3.Row` permite acceder a las columnas por nombre
    (`row["id"]`) en lugar de por posición; conviene hacer `dict(row)` para
    devolver dicts normales.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_database() -> None:
    """Crea las tablas de la aplicación si no existen.

    Se llama al arrancar la app; `IF NOT EXISTS` hace que sea idempotente.
    """
    with get_connection() as conn:
        cursor = conn.cursor()

        # Usuarios: nombre único porque se usa como identificador del jugador
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Preguntas: 4 opciones fijas y una sola respuesta válida (restringida
        # por la cláusula CHECK a 'A', 'B', 'C' o 'D')
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question_text TEXT NOT NULL,
                option_a TEXT NOT NULL,
                option_b TEXT NOT NULL,
                option_c TEXT NOT NULL,
                option_d TEXT NOT NULL,
                correct_option TEXT NOT NULL CHECK (correct_option IN ('A', 'B', 'C', 'D')),
                explanation TEXT NOT NULL
            )
        """)

        # Partidas terminadas: alimenta las estadísticas de la pantalla de inicio
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS quiz_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                score INTEGER NOT NULL,
                total_questions INTEGER NOT NULL,
                time_taken REAL NOT NULL,
                percentage REAL NOT NULL,
                completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)

        conn.commit()


def get_or_create_user(name: str) -> int:
    """Devuelve el id del usuario con ese nombre, creándolo si no existe.

    Es la función que se usa al empezar un quiz: dos partidas seguidas con
    el mismo nombre reutilizan la misma fila y, por tanto, el mismo historial.
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE name = ?", (name,))
        row = cursor.fetchone()
        if row:
            return row["id"]
        cursor.execute("INSERT INTO users (name) VALUES (?)", (name,))
        conn.commit()
        # id generado por AUTOINCREMENT en la inserción anterior
        return cursor.lastrowid


def get_user_by_name(name: str) -> dict | None:
    """Devuelve los datos del usuario o None si ese nombre no existe."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE name = ?", (name,))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_last_active_user() -> dict | None:
    """Usuario más recientemente activo, para mostrar sus stats al abrir la app.

    Prioriza al que tiene la partida más reciente; si nadie ha jugado todavía,
    devuelve el último usuario creado; y si no hay ninguno, None.
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT u.* FROM users u
            JOIN quiz_sessions s ON s.user_id = u.id
            ORDER BY s.completed_at DESC, s.id DESC
            LIMIT 1
        """)
        row = cursor.fetchone()
        if row:
            return dict(row)

        # Sin partidas todavía: nos quedamos con el último usuario creado
        cursor.execute("SELECT * FROM users ORDER BY id DESC LIMIT 1")
        row = cursor.fetchone()
        return dict(row) if row else None


def get_user_stats(user_id: int) -> list[dict]:
    """Todas las partidas de un usuario, de la más reciente a la más antigua.

    Cada dict contiene `score`, `total_questions`, `time_taken`,
    `percentage` y `completed_at`, que es lo que pinta el panel de
    estadísticas de la pantalla de inicio.
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT score, total_questions, time_taken, percentage, completed_at
            FROM quiz_sessions
            WHERE user_id = ?
            ORDER BY completed_at DESC
        """, (user_id,))
        return [dict(row) for row in cursor.fetchall()]


def save_quiz_session(
    user_id: int,
    score: int,
    total_questions: int,
    time_taken: float,
    percentage: float
) -> None:
    """Guarda una partida terminada para las estadísticas."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO quiz_sessions (user_id, score, total_questions, time_taken, percentage)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, score, total_questions, time_taken, percentage))
        conn.commit()


def get_all_questions() -> list[dict]:
    """Todas las preguntas en orden de id (es el orden en que se muestran)."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM questions ORDER BY id")
        return [dict(row) for row in cursor.fetchall()]


def insert_questions(questions: list[dict]) -> None:
    """Carga el banco de preguntas inicial, solo si la tabla está vacía.

    Se ejecuta en cada arranque (ver `main.DevPythonQuiz.on_mount`); el
    recuento previo hace que sea idempotente: si ya hay preguntas en la BD
    (quizás editadas a mano) no se duplican ni se pisan.
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM questions")
        if cursor.fetchone()["count"] > 0:
            return  # Ya hay preguntas: no hacemos nada

        for q in questions:
            cursor.execute("""
                INSERT INTO questions (question_text, option_a, option_b, option_c, option_d, correct_option, explanation)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                q["question"],
                q["options"]["A"],
                q["options"]["B"],
                q["options"]["C"],
                q["options"]["D"],
                q["correct"],
                q["explanation"]
            ))
        conn.commit()


def get_question_count() -> int:
    """Número total de preguntas disponibles."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM questions")
        return cursor.fetchone()["count"]

"""Banco de preguntas inicial de DevPythonQuiz.

Son las 10 preguntas con las que arranca la aplicación. Si la tabla
`questions` de la base de datos está vacía, se cargan estas (ver
`database.insert_questions`); si ya hay preguntas, no se pisan.
"""

# Formato de cada pregunta:
#   question    -> enunciado
#   options     -> dict con las 4 opciones ('A'..'D')
#   correct     -> letra de la respuesta válida
#   explanation -> texto que se muestra tras responder
INITIAL_QUESTIONS = [
    {
        "question": "¿Cuál de las siguientes es la forma correcta de crear un comentario de una sola línea en Python?",
        "options": {
            "A": "// Esto es un comentario",
            "B": "# Esto es un comentario",
            "C": "/* Esto es un comentario */",
            "D": "-- Esto es un comentario"
        },
        "correct": "B",
        "explanation": "En Python, los comentarios de una sola línea empiezan con #."
    },
    {
        "question": "¿Qué función se usa para mostrar texto en la consola en Python?",
        "options": {
            "A": "echo()",
            "B": "print()",
            "C": "console.log()",
            "D": "display()"
        },
        "correct": "B",
        "explanation": "print() es la función incorporada para mostrar salida en la consola."
    },
    {
        "question": "¿Cuál de estos NO es un tipo de dato básico en Python?",
        "options": {
            "A": "int",
            "B": "float",
            "C": "string",
            "D": "char"
        },
        "correct": "D",
        "explanation": "Python no tiene tipo 'char'; las cadenas de un carácter son de tipo 'str'."
    },
    {
        "question": "¿Cómo se define una función en Python?",
        "options": {
            "A": "function mi_funcion():",
            "B": "def mi_funcion():",
            "C": "func mi_funcion():",
            "D": "define mi_funcion():"
        },
        "correct": "B",
        "explanation": "Las funciones en Python se definen con la palabra clave 'def'."
    },
    {
        "question": "¿Qué operador se usa para la división entera en Python?",
        "options": {
            "A": "/",
            "B": "//",
            "C": "%",
            "D": "**"
        },
        "correct": "B",
        "explanation": "// realiza división entera (floor division), / hace división normal."
    },
    {
        "question": "¿Cuál es el resultado de: 2 ** 3 en Python?",
        "options": {
            "A": 6,
            "B": 8,
            "C": 9,
            "D": 5
        },
        "correct": "B",
        "explanation": "** es el operador de potenciación: 2 ** 3 = 2³ = 8."
    },
    {
        "question": "¿Cómo se accede al primer elemento de una lista llamada 'mi_lista'?",
        "options": {
            "A": "mi_lista[1]",
            "B": "mi_lista[0]",
            "C": "mi_lista.first()",
            "D": "mi_lista[-1]"
        },
        "correct": "B",
        "explanation": "En Python, los índices empiezan en 0, así que el primer elemento es [0]."
    },
    {
        "question": "¿Qué método se usa para agregar un elemento al final de una lista?",
        "options": {
            "A": "add()",
            "B": "push()",
            "C": "append()",
            "D": "insert()"
        },
        "correct": "C",
        "explanation": "append() agrega un elemento al final de la lista."
    },
    {
        "question": "¿Cuál de estas estructuras de datos es inmutable en Python?",
        "options": {
            "A": "list",
            "B": "dict",
            "C": "set",
            "D": "tuple"
        },
        "correct": "D",
        "explanation": "Las tuplas (tuple) son inmutables; listas, diccionarios y sets son mutables."
    },
    {
        "question": "¿Qué palabra clave se usa para manejar excepciones en Python?",
        "options": {
            "A": "try/catch",
            "B": "try/except",
            "C": "try/handle",
            "D": "catch/throw"
        },
        "correct": "B",
        "explanation": "Python usa try/except para el manejo de excepciones (no try/catch)."
    }
]


def get_initial_questions() -> list[dict]:
    """Devuelve la lista de preguntas iniciales (copia del literal de arriba).

    Devolvemos la propia lista (no una copia): solo la consume
    `database.insert_questions`, que la recorre una sola vez al arrancar.
    """
    return INITIAL_QUESTIONS
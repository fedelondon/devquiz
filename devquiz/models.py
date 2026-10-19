"""Modelos de datos de DevPythonQuiz.

Aquí se definen los objetos que circulan entre la base de datos y las
pantallas: preguntas, usuarios, sesiones de quiz y el estado de la partida
en curso (`QuizState`).
"""

import time
from dataclasses import dataclass


@dataclass
class Question:
    """Una pregunta del quiz.

    Cada campo `option_*` corresponde a la columna homónima de la tabla
    `questions`; `correct_option` es la letra ("A".."D") de la respuesta
    válida y `explanation` el texto que se muestra tras responder.
    """

    id: int
    question_text: str
    option_a: str
    option_b: str
    option_c: str
    option_d: str
    correct_option: str
    explanation: str

    @property
    def options(self) -> dict[str, str]:
        """Devuelve las opciones como dict ``{"A": ..., "D": ...}``.

        Es la estructura que consume la interfaz para pintar los botones de
        opción y para comparar con la respuesta seleccionada.
        """
        return {
            "A": self.option_a,
            "B": self.option_b,
            "C": self.option_c,
            "D": self.option_d,
        }

    @classmethod
    def from_db_row(cls, row: dict) -> "Question":
        """Crea una `Question` a partir de una fila de la tabla `questions`.

        `row` es un dict (la conexión usa `sqlite3.Row`, que se puede
        convertir con `dict()`), no una tupla.
        """
        return cls(
            id=row["id"],
            question_text=row["question_text"],
            option_a=row["option_a"],
            option_b=row["option_b"],
            option_c=row["option_c"],
            option_d=row["option_d"],
            correct_option=row["correct_option"],
            explanation=row["explanation"]
        )


@dataclass
class User:
    """Un usuario identificado por su nombre/alias."""

    id: int
    name: str
    created_at: str

    @classmethod
    def from_db_row(cls, row: dict) -> "User":
        """Crea un `User` a partir de una fila de la tabla `users`."""
        return cls(
            id=row["id"],
            name=row["name"],
            created_at=row["created_at"]
        )


@dataclass
class QuizSession:
    """Una partida terminada, tal y como se guarda en `quiz_sessions`."""

    id: int
    user_id: int
    score: int
    total_questions: int
    time_taken: float
    percentage: float
    completed_at: str

    @classmethod
    def from_db_row(cls, row: dict) -> "QuizSession":
        """Crea una `QuizSession` a partir de una fila de `quiz_sessions`."""
        return cls(
            id=row["id"],
            user_id=row["user_id"],
            score=row["score"],
            total_questions=row["total_questions"],
            time_taken=row["time_taken"],
            percentage=row["percentage"],
            completed_at=row["completed_at"]
        )


@dataclass
class QuizState:
    """Estado de la partida en curso.

    Vive en memoria mientras dura el quiz (lo crea `quiz.QuizScreen` y se lo
    pasa a `estadisticas.ResultsScreen` al terminar). Aquí se guarda en qué
    pregunta vamos, cuántos aciertos llevamos y qué opción está seleccionada.
    """

    user_id: int
    user_name: str
    questions: list[Question]
    # Índice (base 0) de la pregunta que se está mostrando ahora mismo
    current_index: int = 0
    score: int = 0
    # Marca de tiempo en la que empezó el quiz, para calcular el tiempo total
    start_time: float = 0.0
    # ¿Se ha contestado ya la pregunta actual? Controla si Enter envía o avanza
    answered: bool = False
    # Letra ("A".."D") elegida por el usuario, o None si aún no ha elegido
    selected_option: str | None = None
    # ¿La última respuesta fue correcta? None hasta que se comprueba
    is_correct: bool | None = None

    def __post_init__(self):
        # Si nadie indicó una hora de inicio, tomamos la actual. Permite
        # inyectar `start_time` explícitamente (p. ej. en tests).
        if self.start_time == 0.0:
            self.start_time = time.time()

    @property
    def current_question(self) -> Question:
        """Pregunta que corresponde al índice actual.

        Lanza `IndexError` si el índice está fuera de rango: los que llaman
        deben comprobar antes `is_finished`.
        """
        return self.questions[self.current_index]

    @property
    def progress(self) -> float:
        """Progreso del quiz como porcentaje (0-100), para la barra."""
        # Guarda contra una base de datos sin preguntas: sin ellas no hay
        # nada que repartir y la división fallaría.
        if not self.questions:
            return 0.0
        return ((self.current_index + 1) / len(self.questions)) * 100

    @property
    def is_finished(self) -> bool:
        """True cuando estamos en la última pregunta y ya está respondida.

        Es la condición que usa `next_question()` para decidir si avanza o
        termina el quiz y muestra los resultados.
        """
        return self.current_index >= len(self.questions) - 1 and self.answered

    @property
    def elapsed_time(self) -> float:
        """Segundos transcurridos desde el inicio del quiz."""
        return time.time() - self.start_time

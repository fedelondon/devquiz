"""Punto de entrada de DevPythonQuiz.

Este módulo define la aplicación (`DevPythonQuiz`) y centraliza en un solo
lugar la navegación entre pantallas (`show_home`, `show_quiz`,
`show_results`), de modo que el resto de módulos no tienen que preocuparse
de cómo se cambia de pantalla.
"""

from typing import ClassVar

from textual.app import App
from textual.await_complete import AwaitComplete

from devquiz.database import init_database, insert_questions
from devquiz.estadisticas import ResultsScreen
from devquiz.inicio import HomeScreen
from devquiz.models import QuizState
from devquiz.questions import get_initial_questions
from devquiz.quiz import QuizScreen


class DevPythonQuiz(App):
    """Aplicación principal: gestiona la BD y el cambio de pantallas."""

    TITLE = "DevPythonQuiz"
    SUB_TITLE = "Quiz de Python para principiantes"
    # Hoja de estilos global compartida por todas las pantallas
    CSS_PATH = "app.tcss"

    # Pantallas registradas por nombre. Solo HomeScreen puede declararse aquí
    # porque es la única que se construye sin argumentos: las demás
    # (quiz/results) reciben datos y se crean desde los métodos show_*.
    SCREENS: ClassVar[dict[str, type[HomeScreen]]] = {"home": HomeScreen}

    # Atajos globales: "q" y Ctrl+C salen de la aplicación. No son prioritarios,
    # así que no se activan mientras se escribe en un campo de texto.
    BINDINGS: ClassVar[list[tuple[str, str, str]]] = [
        ("q", "quit", "Salir"),
        ("ctrl+c", "quit", "Salir"),
    ]

    def on_mount(self) -> None:
        """Arranque: prepara la base de datos y muestra la pantalla de inicio."""
        # Crea las tablas si faltan y carga el banco de preguntas inicial
        init_database()
        insert_questions(get_initial_questions())
        # La primera navegación tiene que ser un *push* (y no un switch):
        # la pantalla por defecto con la que arranca Textual no tiene
        # "result callback" y `switch_screen` trataría de sacarlo de la pila
        # fallando con IndexError. Todas las demás navegaciones sí usan switch.
        self.push_screen(HomeScreen())

    def show_home(self) -> AwaitComplete:
        """Muestra una pantalla de inicio nueva (sustituyendo la actual).

        Se crea siempre una instancia nueva para que las estadísticas se
        recalculen al volver de un quiz.
        """
        return self.switch_screen(HomeScreen())

    def show_quiz(self, user_id: int, user_name: str) -> AwaitComplete:
        """Pasa a un quiz nuevo para el usuario indicado.

        `switch_screen` reemplaza la pantalla de arriba de la pila (en lugar
        de apilarla), así que la pila no crece y las pantallas antiguas se
        destruyen y liberan.
        """
        return self.switch_screen(
            QuizScreen(user_id=user_id, user_name=user_name)
        )

    def show_results(
        self,
        quiz_state: QuizState,
        time_taken: float,
        percentage: float,
    ) -> AwaitComplete:
        """Pasa a la pantalla de resultados de una partida terminada.

        Recibe el `QuizState` completo para poder mostrar el desglose
        (aciertos, número de preguntas, etc.) sin volver a tocar la BD.
        """
        return self.switch_screen(
            ResultsScreen(
                quiz_state=quiz_state,
                time_taken=time_taken,
                percentage=percentage,
            )
        )


def main():
    """Crea la aplicación y la arranca en la terminal actual."""
    app = DevPythonQuiz()
    app.run()


# Permite ejecutar el paquete con `python -m devquiz.main`
if __name__ == "__main__":
    main()

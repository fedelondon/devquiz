"""Pantalla de resultados/estadísticas de DevPythonQuiz.

Se muestra al terminar una partida: puntuación, tiempo, porcentaje, un
mensaje según el rendimiento y los botones para repetir o volver al inicio.
"""

from typing import TYPE_CHECKING, ClassVar, cast

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Label, ProgressBar, Static

from devquiz.models import QuizState

if TYPE_CHECKING:
    from devquiz.main import DevPythonQuiz


class ResultsScreen(Screen):
    """Pantalla final con el resumen de la partida terminada."""

    # Enter repite el quiz (el foco arranca en el botón de reinicio, que
    # también responde a Enter) y Escape vuelve a la pantalla de inicio.
    BINDINGS: ClassVar[list[Binding]] = [
        Binding("enter", "restart_quiz", "Reiniciar Quiz"),
        Binding("escape", "go_home", "Volver al inicio"),
    ]

    # Alturas y márgenes ajustados para que todo quepa en 80x24 sin scroll;
    # igual que en el quiz, `max-height: 100%` + `overflow-y` cubren las
    # terminales pequeñas o textos largos.
    # Las clases .feedback-* dan color al mensaje de rendimiento.
    CSS = """
    ResultsScreen {
        align: center middle;
    }
    #results-container {
        width: 80%;
        max-width: 80;
        height: auto;
        max-height: 100%;
        overflow-y: auto;
        border: solid $primary;
        padding: 1;
    }
    #results-title {
        text-align: center;
        text-style: bold;
        color: $primary;
        margin-bottom: 0;
    }
    #score-container {
        margin: 0;
        padding: 1;
        border: solid $secondary;
        background: $surface;
    }
    #score-main {
        text-align: center;
        text-style: bold;
        color: $success;
    }
    #score-detail {
        text-align: center;
        color: $foreground;
        margin-top: 0;
    }
    /* Una fila por dato (etiqueta 40% + valor 60%) */
    .stat-row {
        height: 1;
        margin: 0 1;
    }
    .stat-label {
        color: $secondary;
        width: 40%;
    }
    .stat-value {
        text-style: bold;
        text-align: right;
        width: 60%;
    }
    #percentage-bar {
        margin: 0 2;
        height: 1;
    }
    #performance-message {
        height: auto;
        margin-top: 0;
    }
    .feedback-success {
        color: $success;
        text-style: bold;
    }
    .feedback-warning {
        color: $warning;
        text-style: bold;
    }
    .feedback-error {
        color: $error;
        text-style: bold;
    }
    #buttons-container {
        margin-top: 0;
        height: auto;
    }
    #restart-button {
        width: 100%;
        margin-bottom: 1;
    }
    #home-button {
        width: 100%;
    }
    #hints {
        text-align: center;
        color: $secondary;
        margin-top: 0;
    }
    """

    def __init__(self, quiz_state: QuizState, time_taken: float, percentage: float):
        """Recibe el resultado de la partida terminada.

        Args:
            quiz_state: estado final (aciertos, preguntas, usuario...).
            time_taken: segundos que se tardó en completar el quiz.
            percentage: porcentaje de aciertos (0-100).
        """
        super().__init__()
        self.quiz_state = quiz_state
        self.time_taken = time_taken
        self.percentage = percentage

    def compose(self) -> ComposeResult:
        """Construye el resumen: puntuación, datos, barra y botones."""
        yield Header(show_clock=True)
        with Container(id="results-container"):
            yield Label("🏁 ¡Quiz Completado!", id="results-title")

            # Puntuación absoluta y porcentaje
            with Container(id="score-container"):
                yield Label(f"{self.quiz_state.score} / {len(self.quiz_state.questions)}", id="score-main")
                yield Label(f"{self.percentage:.1f}% de aciertos", id="score-detail")

            # Filas de datos: etiqueta a la izquierda, valor a la derecha
            with Horizontal(classes="stat-row"):
                yield Label("⏱️ Tiempo:", classes="stat-label")
                yield Label(f"{self.time_taken:.1f} segundos", classes="stat-value")

            with Horizontal(classes="stat-row"):
                yield Label("✅ Correctas:", classes="stat-label")
                yield Label(str(self.quiz_state.score), classes="stat-value")

            with Horizontal(classes="stat-row"):
                yield Label("❌ Incorrectas:", classes="stat-label")
                yield Label(str(len(self.quiz_state.questions) - self.quiz_state.score), classes="stat-value")

            with Horizontal(classes="stat-row"):
                yield Label("📝 Preguntas totales:", classes="stat-label")
                yield Label(str(len(self.quiz_state.questions)), classes="stat-value")

            # Barra con el porcentaje de aciertos
            yield Label("Progreso:", classes="stat-label")
            progress_bar = ProgressBar(total=100, show_eta=False, id="percentage-bar")
            progress_bar.progress = self.percentage
            yield progress_bar

            # Mensaje de rendimiento (se rellena en on_mount)
            yield Static(id="performance-message")

            with Container(id="buttons-container"):
                yield Button("🔄 Reiniciar Quiz", id="restart-button", variant="primary")
                yield Button("🏠 Volver al Inicio", id="home-button", variant="default")

            yield Label("Enter: Reiniciar | Esc: Inicio", id="hints")

        yield Footer()

    def on_mount(self) -> None:
        """Al montarse: mensaje de rendimiento y foco en "Reiniciar Quiz"."""
        self.update_performance_message()
        # El foco en el botón permite repetir con solo pulsar Enter
        self.query_one("#restart-button", Button).focus()

    def update_performance_message(self) -> None:
        """Escribe un mensaje y un color según el porcentaje obtenido.

        Las clases `feedback-success|warning|error` (definidas en el CSS de
        esta pantalla) son las que colorean el texto.
        """
        message_widget = self.query_one("#performance-message", Static)
        # Se recomponen los hijos porque esta pantalla puede llamarse más de
        # una vez en la misma sesión; no llevan id, así que no hay conflicto.
        message_widget.remove_children()

        if self.percentage == 100:
            msg = "🎉 ¡Perfecto! Dominas los conceptos básicos de Python."
            color = "success"
        elif self.percentage >= 80:
            msg = "🌟 ¡Excelente! Tienes una base muy sólida."
            color = "success"
        elif self.percentage >= 60:
            msg = "👍 ¡Bien hecho! Repasa los fallos para mejorar."
            color = "warning"
        elif self.percentage >= 40:
            msg = "📚 Necesitas practicar más. ¡No te rindas!"
            color = "warning"
        else:
            msg = "💪 Sigue estudiando. Cada error es una oportunidad de aprender."
            color = "error"

        message_widget.add_class(f"feedback-{color}")
        message_widget.mount(Label(msg))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Clic en "Reiniciar Quiz" o "Volver al Inicio"."""
        if event.button.id == "restart-button":
            self.action_restart_quiz()
        elif event.button.id == "home-button":
            self.action_go_home()

    def action_restart_quiz(self) -> None:
        """Crea un quiz nuevo con el mismo usuario (pantalla reemplazada)."""
        cast("DevPythonQuiz", self.app).show_quiz(
            user_id=self.quiz_state.user_id,
            user_name=self.quiz_state.user_name,
        )

    def action_go_home(self) -> None:
        """Vuelve a la pantalla de inicio."""
        cast("DevPythonQuiz", self.app).show_home()

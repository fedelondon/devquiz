"""Pantalla del quiz de DevPythonQuiz.

Muestra una pregunta por pantalla con sus cuatro opciones. Gestiona la
selección (ratón o teclado), la comprobación de la respuesta, el feedback y
el paso a la siguiente pregunta; al terminar delega en la pantalla de
resultados (`estadisticas.ResultsScreen`).
"""

from typing import TYPE_CHECKING, ClassVar, cast

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container
from textual.screen import Screen
from textual.timer import Timer
from textual.widgets import (
    Button,
    Footer,
    Header,
    Label,
    ProgressBar,
    RadioButton,
    RadioSet,
)

from devquiz.database import get_all_questions, save_quiz_session
from devquiz.models import Question, QuizState

if TYPE_CHECKING:
    from devquiz.main import DevPythonQuiz

# Teclas 1-4, en este orden exacto, coinciden con los ids "opt-A".."opt-D"
OPTION_KEYS = ("A", "B", "C", "D")


class QuizScreen(Screen):
    """Pantalla del quiz: una pregunta en pantalla con sus cuatro opciones."""

    # Atajos de teclado de esta pantalla:
    #  * Enter usa priority=True para que funcione aunque el foco esté en el
    #    RadioSet (que si no se lo comería con su binding "enter,space").
    #  * Escape vuelve al inicio; 1-4 eligen opción; →/N avanzan tras responder.
    BINDINGS: ClassVar[list[Binding]] = [
        Binding("enter", "submit_or_next", "Responder / Siguiente", priority=True),
        Binding("escape", "go_home", "Volver al inicio"),
        Binding("1", "select_a", "Opción A"),
        Binding("2", "select_b", "Opción B"),
        Binding("3", "select_c", "Opción C"),
        Binding("4", "select_d", "Opción D"),
        Binding("right,n", "next_question", "Siguiente"),
    ]

    # Notas de layout:
    #  * Todos los contenedores usan `height: auto` porque el valor por
    #    defecto de `Container` es `1fr` con `overflow: hidden`, lo que
    #    recortaba las opciones.
    #  * `max-height: 100%` + `overflow-y: auto` permiten hacer scroll en
    #    terminales pequeños (p. ej. 80x24) sin que se corte el contenido.
    CSS = """
    QuizScreen {
        align: center middle;
    }
    #quiz-container {
        width: 90%;
        max-width: 100;
        height: auto;
        max-height: 100%;
        overflow-y: auto;
        border: solid $primary;
        padding: 1 2;
    }
    #progress-container {
        height: auto;
        margin-bottom: 1;
    }
    #progress-label {
        text-align: right;
        color: $secondary;
        margin-bottom: 0;
    }
    #question-container {
        height: auto;
        margin: 1 0;
        padding: 0 1;
        border: solid $secondary;
        background: $surface;
    }
    #question-text {
        text-style: bold;
        margin-bottom: 1;
    }
    #options-container {
        height: auto;
        margin-top: 1;
    }
    RadioSet {
        margin: 0;
        height: auto;
    }
    RadioButton {
        margin: 0 0 0 2;
        height: 1;
    }
    RadioButton:focus {
        background: $boost;
    }
    #answer-feedback {
        height: auto;
        min-height: 2;
        margin-top: 1;
        padding: 0 1;
    }
    .feedback-correct {
        color: $success;
        text-style: bold;
    }
    .feedback-incorrect {
        color: $error;
        text-style: bold;
    }
    .feedback-explanation {
        color: $foreground;
        margin-top: 0;
    }
    /* Oculto hasta que se responde; se muestra añadiendo la clase .visible */
    #next-button {
        width: 100%;
        margin-top: 1;
        display: none;
        height: 5;
        content-align: center middle;
    }
    #next-button.visible {
        display: block;
        background: $success;
        color: $text;
        border: solid $success;
    }
    #next-button.visible:focus {
        background: $accent;
        border: solid $accent;
    }
    #timer {
        text-align: right;
        color: $secondary;
        margin-top: 0;
    }
    #hints {
        text-align: center;
        color: $secondary;
        margin-top: 0;
    }
    """

    def __init__(self, user_id: int, user_name: str):
        """Prepara la pantalla para un usuario concreto.

        Args:
            user_id: id en la tabla `users` (para guardar la partida).
            user_name: nombre/alias que se mostrará en los resultados.
        """
        super().__init__()
        self.user_id = user_id
        self.user_name = user_name
        # Estado de la partida; se crea en `init_quiz` al montarse la pantalla
        self.quiz_state: QuizState | None = None
        # Referencia directa al RadioSet actual (se recrea en cada pregunta)
        self.radio_set: RadioSet | None = None
        # Temporizador que refresca la etiqueta de tiempo (se para al salir)
        self.timer: Timer | None = None

    def compose(self) -> ComposeResult:
        """Construye la estructura: progreso, pregunta, feedback y botones."""
        yield Header(show_clock=True)
        with Container(id="quiz-container"):
            with Container(id="progress-container"):
                yield ProgressBar(total=100, show_eta=False, id="progress-bar")
                yield Label("Pregunta 1 de 10", id="progress-label")

            with Container(id="question-container"):
                yield Label("", id="question-text")
                # El contenedor sale vacío: las opciones se montan en cada
                # pregunta desde `update_display`, de forma que no queda
                # preseleccionada ninguna de la pregunta anterior.
                yield Container(id="options-container")

            # Feedback: dos etiquetas que se rellenan con update() tras responder
            with Container(id="answer-feedback"):
                yield Label("", id="feedback-title")
                yield Label("", id="feedback-explanation")

            yield Button("Siguiente ▶", id="next-button", variant="primary")
            yield Label("Tiempo: 0.0s", id="timer")
            yield Label(
                "1-4: Seleccionar | Enter: Responder/Siguiente | →/N: Siguiente | Esc: Salir",
                id="hints",
            )

        yield Footer()

    async def on_mount(self) -> None:
        """Al montarse: carga las preguntas y arranca el cronómetro."""
        await self.init_quiz()
        # Cada 0.1s refresca la etiqueta de tiempo; el timer se detiene solo
        # cuando la pantalla se destruye (y explícitamente al salir).
        self.timer = self.set_interval(0.1, self.update_timer)

    async def init_quiz(self) -> None:
        """Carga las preguntas de la BD y crea el estado de la partida."""
        questions_data = get_all_questions()
        questions = [Question.from_db_row(q) for q in questions_data]

        # BD vacía (o tablas rotas): avisamos y volvemos al inicio en lugar
        # de reventar con un índice fuera de rango.
        if not questions:
            self.notify("No hay preguntas disponibles en la base de datos",
                        severity="error")
            await cast("DevPythonQuiz", self.app).show_home()
            return

        self.quiz_state = QuizState(
            user_id=self.user_id,
            user_name=self.user_name,
            questions=questions,
        )
        await self.update_display()

    async def update_display(self) -> None:
        """Pinta la pregunta actual y reconstruye las opciones.

        Es `async` porque hay que esperar a que se eliminen los widgets de la
        pregunta anterior antes de montar los nuevos: montar con los mismos
        ids antes de que el borrado se aplique lanzaría `DuplicateIds`.
        """
        if not self.quiz_state:
            return

        qs = self.quiz_state
        q = qs.current_question

        # Reiniciamos el estado de respuesta ANTES de tocar los widgets:
        # al recrear el RadioSet se emiten mensajes `Changed` que, si se
        # procesaran después, dejarían una opción marcada por accidente.
        qs.answered = False
        qs.selected_option = None
        qs.is_correct = None

        # Barra de progreso y contador "Pregunta X de Y"
        progress_bar = self.query_one("#progress-bar", ProgressBar)
        progress_bar.progress = qs.progress
        progress_label = self.query_one("#progress-label", Label)
        progress_label.update(f"Pregunta {qs.current_index + 1} de {len(qs.questions)}")

        # Enunciado
        question_text = self.query_one("#question-text", Label)
        question_text.update(f"{qs.current_index + 1}. {q.question_text}")

        # Nuevas opciones: RadioSet nuevo y vacío, así no arrastramos la
        # selección de la pregunta anterior.
        options = self.query_one("#options-container", Container)
        await options.remove_children()
        self.radio_set = RadioSet(
            *[
                RadioButton(f"{key}) {q.options[key]}", id=f"opt-{key}")
                for key in OPTION_KEYS
            ],
            id="options-radio",
        )
        await options.mount(self.radio_set)
        # El foco vuelve a las opciones para poder navegar con el teclado
        self.radio_set.focus()

        # Limpiamos el feedback de la pregunta anterior
        title = self.query_one("#feedback-title", Label)
        title.update("")
        title.remove_class("feedback-correct", "feedback-incorrect")
        explanation = self.query_one("#feedback-explanation", Label)
        explanation.update("")
        explanation.remove_class("feedback-explanation")

        # El botón de avance se oculta hasta responder
        next_button = self.query_one("#next-button", Button)
        next_button.label = "Siguiente ▶"
        next_button.remove_class("visible")
        next_button.disabled = True

    def update_timer(self) -> None:
        """Actualiza la etiqueta con los segundos transcurridos."""
        if self.quiz_state:
            timer_label = self.query_one("#timer", Label)
            timer_label.update(f"Tiempo: {self.quiz_state.elapsed_time:.1f}s")

    def on_radio_set_changed(self, event: RadioSet.Changed) -> None:
        """Guarda la opción elegida al marcar un RadioButton (ratón o teclado).

        `event.pressed` es el botón recién marcado; si la pregunta ya está
        respondida ignoramos el evento para que no se cambie la respuesta.
        """
        if not self.quiz_state or self.quiz_state.answered:
            return

        option_id = event.pressed.id
        if option_id and option_id.startswith("opt-"):
            # Del id "opt-B" nos quedamos con la letra: "B"
            self.quiz_state.selected_option = option_id[4:]

    def action_select_a(self) -> None:
        """Atajo de teclado: elige la opción A."""
        self._select_option("A")

    def action_select_b(self) -> None:
        """Atajo de teclado: elige la opción B."""
        self._select_option("B")

    def action_select_c(self) -> None:
        """Atajo de teclado: elige la opción C."""
        self._select_option("C")

    def action_select_d(self) -> None:
        """Atajo de teclado: elige la opción D."""
        self._select_option("D")

    def _select_option(self, option: str) -> None:
        """Marca la opción indicada (1-4) y actualiza la selección del estado.

        Solo marca; la comprobación la hace `action_submit_or_next` con Enter.
        No hace falta desmarcar la anterior: al marcar una, el propio RadioSet
        apaga la que estaba encendida.
        """
        if not self.quiz_state or self.quiz_state.answered:
            return

        radio_set = self.radio_set
        if radio_set is None:
            return

        target_id = f"opt-{option}"
        for child in radio_set.children:
            if isinstance(child, RadioButton) and child.id == target_id:
                child.value = True
                self.quiz_state.selected_option = option
                break

    async def action_submit_or_next(self) -> None:
        """Acción de Enter (prioritaria): responde, o pasa de pregunta si ya
        se había respondido.

        Al usar priority=True se procesa antes que el binding `enter,space`
        del RadioSet enfocado, que si no capturaría la tecla.
        """
        if not self.quiz_state:
            return

        if self.quiz_state.answered:
            await self.next_question()
        else:
            if not self.quiz_state.selected_option:
                self.notify("Selecciona una opción primero", severity="warning")
                return
            self.check_answer()

    def check_answer(self) -> None:
        """Compara la opción elegida con la correcta y muestra el feedback."""
        qs = self.quiz_state
        if not qs:
            return
        q = qs.current_question

        qs.answered = True
        qs.is_correct = qs.selected_option == q.correct_option

        if qs.is_correct:
            qs.score += 1

        # Mensaje de acierto/fallo más la explicación
        title = self.query_one("#feedback-title", Label)
        explanation = self.query_one("#feedback-explanation", Label)

        if qs.is_correct:
            title.update("✅ ¡Correcto!")
            title.set_class("feedback-correct")
            title.remove_class("feedback-incorrect")
        else:
            title.update("❌ Incorrecto")
            title.set_class("feedback-incorrect")
            title.remove_class("feedback-correct")

        explanation.update(f"💡 {q.explanation}")
        explanation.set_class("feedback-explanation")

        # Las opciones quedan bloqueadas hasta la siguiente pregunta
        # (se vuelven a habilitar al recrearlas en `update_display`)
        if self.radio_set is not None:
            self.radio_set.disabled = True

        # Aparece el botón de avance y toma el foco; en la última pregunta
        # su texto cambia a "Ver Resultados ▶".
        next_button = self.query_one("#next-button", Button)
        if qs.is_finished:
            next_button.label = "Ver Resultados ▶"
        next_button.add_class("visible")
        next_button.disabled = False
        next_button.focus()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Clic en "Siguiente ▶" / "Ver Resultados ▶"."""
        if event.button.id == "next-button":
            await self.next_question()

    async def action_next_question(self) -> None:
        """Atajo →/N: avanza solo si la pregunta ya está respondida."""
        if self.quiz_state and self.quiz_state.answered:
            await self.next_question()

    async def next_question(self) -> None:
        """Avanza a la siguiente pregunta o termina el quiz."""
        if not self.quiz_state:
            return

        if self.quiz_state.is_finished:
            # Estábamos en la última pregunta ya respondida: resultados
            self.finish_quiz()
        else:
            self.quiz_state.current_index += 1
            await self.update_display()

    def finish_quiz(self) -> None:
        """Para el cronómetro, guarda la partida y muestra los resultados."""
        if self.timer:
            self.timer.stop()

        qs = self.quiz_state
        if not qs:
            return
        time_taken = qs.elapsed_time
        # Protección extra por si la lista de preguntas estuviera vacía
        percentage = (qs.score / len(qs.questions)) * 100 if qs.questions else 0.0

        # Guardamos la partida para que aparezca en el historial del inicio
        save_quiz_session(
            user_id=qs.user_id,
            score=qs.score,
            total_questions=len(qs.questions),
            time_taken=time_taken,
            percentage=percentage,
        )

        # Pasamos a la pantalla de resultados con el estado completo
        cast("DevPythonQuiz", self.app).show_results(
            qs, time_taken, percentage
        )

    async def action_go_home(self) -> None:
        """Escape: abandona el quiz (sin guardar) y vuelve al inicio."""
        if self.timer:
            self.timer.stop()
        await cast("DevPythonQuiz", self.app).show_home()

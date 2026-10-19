"""Pantalla de inicio de DevPythonQuiz.

Aquí el usuario escribe su nombre (o alias) y arranca el quiz; mientras
tanto, el panel de la parte inferior muestra sus estadísticas y su historial
de partidas anteriores.
"""

from typing import TYPE_CHECKING, ClassVar, cast

from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Input, Label, Static

from devquiz.database import (
    get_last_active_user,
    get_or_create_user,
    get_user_by_name,
    get_user_stats,
)
from devquiz.models import User

if TYPE_CHECKING:
    from devquiz.main import DevPythonQuiz


def build_stats_text(user: User | None, stats: list[dict]) -> Text:
    """Construye el texto con formato del panel de estadísticas.

    Args:
        user: Usuario al que pertenecen las estadísticas, o None si no hay
            ninguno (BD recién creada o nombre sin partidas).
        stats: Partidas del usuario, de la más reciente a la más antigua
            (lo que devuelve `database.get_user_stats`).

    Returns:
        Un `rich.Text` listo para pintar en el `Static` del panel.
    """
    # Sin usuario no hay nada que mostrar
    if user is None:
        return Text("No hay estadísticas previas.", style="italic")

    text = Text()
    text.append(f"📊 Estadísticas de {user.name}\n", style="bold")

    # Usuario creado pero que todavía no ha terminado ninguna partida
    if not stats:
        text.append("Aún no has completado ningún quiz.", style="italic")
        return text

    # Resumen global a partir de todas las partidas
    total_quizzes = len(stats)
    best_score = max(s["percentage"] for s in stats)
    avg_score = sum(s["percentage"] for s in stats) / total_quizzes
    total_time = sum(s["time_taken"] for s in stats)

    text.append(f"Quizzes completados: {total_quizzes}\n")
    text.append(f"Mejor puntuación: {best_score:.1f}%\n")
    text.append(f"Puntuación media: {avg_score:.1f}%\n")
    text.append(f"Tiempo total: {total_time:.0f}s\n")

    # Historial: las 5 partidas más recientes (la consulta ya viene ordenada
    # de más reciente a más antigua)
    text.append("\n📋 Historial reciente:\n", style="bold")
    for session in stats[:5]:  # las 5 partidas más recientes
        text.append(
            f"  {session['completed_at'][:16]} - "
            f"{session['score']}/{session['total_questions']} "
            f"({session['percentage']:.1f}%) - "
            f"{session['time_taken']:.0f}s\n"
        )

    return text


class HomeScreen(Screen):
    """Pantalla de inicio: nombre del usuario, botón de empezar y estadísticas."""

    # Enter arranca el quiz (también lo hace el botón o el campo de texto);
    # Escape, en esta pantalla, cierra la aplicación.
    BINDINGS: ClassVar[list[Binding]] = [
        Binding("enter", "start_quiz", "Iniciar Quiz"),
        Binding("escape", "quit", "Salir"),
    ]

    # `max-height` + `overflow-y` permiten hacer scroll cuando el contenido
    # no cabe en terminales pequeños (p. ej. 80x24)
    CSS = """
    HomeScreen {
        align: center middle;
    }
    #home-container {
        width: 80%;
        max-width: 80;
        height: auto;
        max-height: 100%;
        overflow-y: auto;
        border: solid $primary;
        padding: 1;
    }
    #title {
        text-align: center;
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }
    #subtitle {
        text-align: center;
        color: $secondary;
        margin-bottom: 1;
    }
    #name-input {
        margin-bottom: 1;
    }
    #start-button {
        width: 100%;
        margin-top: 1;
    }
    #stats-container {
        margin-top: 1;
        padding: 0 1;
        border: solid $secondary;
        height: auto;
        min-height: 4;
    }
    .stats-title {
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }
    """

    def __init__(self):
        super().__init__()
        # Usuario y partidas que se muestran ahora mismo en el panel
        self.user: User | None = None
        self.stats: list[dict] = []

    def compose(self) -> ComposeResult:
        """Construye el contenido de la pantalla (cabecera, formulario y stats)."""
        yield Header(show_clock=True)
        with Container(id="home-container"):
            yield Label("🐍 DevPythonQuiz", id="title")
            yield Label("Quiz de Python para principiantes", id="subtitle")
            yield Input(
                placeholder="Introduce tu nombre o alias...",
                id="name-input",
                type="text",
            )
            yield Button("▶ Iniciar Quiz", id="start-button", variant="primary")
            # El contenido de este contenedor se reemplaza con update()
            with Container(id="stats-container"):
                yield Label("Estadísticas", classes="stats-title")
                yield Static(id="stats-content")

        yield Footer()

    def on_mount(self) -> None:
        """Al montarse: foco en el campo de nombre y stats del último usuario."""
        self.query_one("#name-input", Input).focus()
        # Nombre vacío => mostramos al último usuario que jugó (si lo hay)
        self._refresh_stats_for_name("")

    def on_input_changed(self, event: Input.Changed) -> None:
        """Al escribir en el campo de nombre, actualizamos sus estadísticas.

        Así, al terminar de escribir un nombre conocido se ve el historial
        antes de pulsar Enter.
        """
        if event.input.id == "name-input":
            self._refresh_stats_for_name(event.value.strip())

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Enter dentro del campo de nombre => empezar el quiz."""
        if event.input.id == "name-input":
            self.action_start_quiz()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Clic en el botón "▶ Iniciar Quiz"."""
        if event.button.id == "start-button":
            self.action_start_quiz()

    def _refresh_stats_for_name(self, name: str) -> None:
        """Muestra las estadísticas del nombre indicado (o del último usuario).

        Con el campo vacío se usa `get_last_active_user` para que, al volver
        de una partida, la pantalla de inicio muestre el historial recién
        actualizado sin tener que volver a escribir el nombre.
        """
        row = get_user_by_name(name) if name else get_last_active_user()
        if row is None:
            # BD sin usuarios todavía
            self.update_stats_display(None, [])
            return

        self.user = User.from_db_row(row)
        self.stats = get_user_stats(self.user.id)
        self.update_stats_display(self.user, self.stats)

    def action_start_quiz(self) -> None:
        """Valida el nombre y pasa a la pantalla del quiz."""
        name_input = self.query_one("#name-input", Input)
        name = name_input.value.strip()

        if not name:
            self.notify("Por favor, introduce un nombre", severity="warning")
            return

        # Crea el usuario si es la primera vez que juega con ese nombre
        user_id = get_or_create_user(name)
        # `cast` solo cambia la anotación de tipos: DevPythonQuiz define los
        # métodos show_* y, en tiempo de ejecución, self.app ya es esa app.
        app = cast("DevPythonQuiz", self.app)
        app.show_quiz(user_id=user_id, user_name=name)

    def action_quit(self) -> None:
        """Acción del atajo Escape: cierra la aplicación."""
        self.app.exit()

    def update_stats_display(self, user: User | None, stats: list[dict]) -> None:
        """Pinta el panel de estadísticas con el texto calculado.

        Se usa `Static.update()` (y no montar/desmontar etiquetas) para
        reemplazar el contenido de forma atómica y sin duplicados.
        """
        self.query_one("#stats-content", Static).update(
            build_stats_text(user, stats)
        )
        # Volvemos al principio *después* de que Textual maquetee el nuevo
        # contenido: si no, el scroll automático del foco dejaría el título
        # fuera de la pantalla en terminales pequeños.
        self.call_after_refresh(self._scroll_home)

    def _scroll_home(self) -> None:
        """Lleva el panel al principio para que el título y el input se vean."""
        self.query_one("#home-container", Container).scroll_home(animate=False)

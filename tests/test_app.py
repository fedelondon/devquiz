"""Pruebas de integración de DevPythonQuiz (Textual en modo headless).

Se ejecutan con ``pytest`` y no necesitan terminal: ``App.run_test`` simula
el teclado y el ratón. Cada test usa una base de datos temporal para no
tocar la ``devquiz.db`` real.
"""

import asyncio

import pytest

from devquiz import database
from devquiz.estadisticas import ResultsScreen
from devquiz.inicio import HomeScreen
from devquiz.main import DevPythonQuiz
from devquiz.quiz import QuizScreen


@pytest.fixture()
def temp_db(tmp_path, monkeypatch):
    """Redirige la base de datos a un fichero temporal del test.

    Evita tocar la `devquiz.db` real. `monkeypatch` revierte el cambio al
    terminar el test, así que cada uno arranca con una BD limpia.
    """
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "devquiz-test.db")
    return database.DB_PATH


async def start_quiz(app, pilot, name="tester"):
    """Escribe un nombre en la pantalla de inicio y arranca el quiz.

    Los `pilot.pause()` adicionales dejan asentarse los cambios de pantalla
    y la maquetación antes de seguir (en Textual la navegación es asíncrona).
    """
    await pilot.pause()
    await pilot.pause()
    assert isinstance(app.screen, HomeScreen), app.screen
    app.screen.query_one("#name-input").value = name
    await pilot.press("enter")
    await pilot.pause()
    await pilot.pause()
    assert isinstance(app.screen, QuizScreen), app.screen


async def answer_and_next(app, pilot, key="1"):
    """Responde con la opción de la tecla ``key`` y avanza de pregunta.

    Se necesitan dos pulsaciones de Enter: la primera envía la respuesta y
    la segunda pasa a la siguiente pregunta (o termina el quiz).
    """
    await pilot.press(key)
    await pilot.pause()
    await pilot.press("enter")  # responder
    await pilot.pause()
    assert app.screen.quiz_state.answered
    await pilot.press("enter")  # siguiente
    await pilot.pause()


def test_home_se_muestra_al_arrancar(temp_db):
    """La app arranca en la pantalla de inicio con el campo de nombre listo."""

    async def scenario():
        app = DevPythonQuiz()
        async with app.run_test(size=(100, 30)) as pilot:
            await pilot.pause()
            await pilot.pause()
            assert isinstance(app.screen, HomeScreen)
            assert app.screen.query_one("#name-input")

    asyncio.run(scenario())


def test_enter_responde_la_pregunta(temp_db):
    """Regresión: el RadioSet capturaba Enter y la pregunta no se podía responder."""
    async def scenario():
        app = DevPythonQuiz()
        async with app.run_test(size=(100, 30)) as pilot:
            await start_quiz(app, pilot)
            assert app.focused is not None and app.focused.id == "options-radio"

            await pilot.press("2")
            await pilot.pause()
            assert app.screen.quiz_state.selected_option == "B"

            await pilot.press("enter")
            await pilot.pause()
            assert app.screen.quiz_state.answered is True
            assert app.screen.quiz_state.is_correct is True

    asyncio.run(scenario())


def test_siguiente_pregunta_sin_errores(temp_db):
    """Regresión: DuplicateIds y RadioSet deshabilitado al pasar de pregunta."""
    async def scenario():
        app = DevPythonQuiz()
        async with app.run_test(size=(100, 30)) as pilot:
            await start_quiz(app, pilot)
            await answer_and_next(app, pilot)

            state = app.screen.quiz_state
            assert state.current_index == 1

            radio_set = app.screen.query_one("#options-radio")
            assert radio_set.disabled is False
            assert len(radio_set.children) == 4
            assert [child.id for child in radio_set.children] == [
                "opt-A", "opt-B", "opt-C", "opt-D",
            ]
            assert all(child.value is False for child in radio_set.children)
            assert state.selected_option is None

    asyncio.run(scenario())


def test_flujo_completo_hasta_resultados(temp_db):
    """Juega las 10 preguntas y comprueba que se llega a resultados."""

    async def scenario():
        app = DevPythonQuiz()
        async with app.run_test(size=(100, 30)) as pilot:
            await start_quiz(app, pilot)
            # La pila de pantallas no debe crecer (antes se acumulaban)
            assert len(app.screen_stack) == 2

            questions = len(app.screen.quiz_state.questions)
            assert questions == 10
            for _ in range(questions):
                await answer_and_next(app, pilot)

            assert isinstance(app.screen, ResultsScreen), app.screen
            assert len(app.screen_stack) == 2
            # Siempre elegimos la opción A, que no es la correcta en ninguna
            # de las preguntas actuales.
            assert app.screen.quiz_state.score == 0

    asyncio.run(scenario())


def test_reiniciar_y_volver_al_inicio(temp_db):
    """Regresión: reiniciar o volver a empezar lanzaba ScreenStackError."""
    async def scenario():
        app = DevPythonQuiz()
        async with app.run_test(size=(100, 30)) as pilot:
            await start_quiz(app, pilot)
            for _ in range(10):
                await answer_and_next(app, pilot)
            assert isinstance(app.screen, ResultsScreen)

            # "Reiniciar Quiz" (botón con foco)
            await pilot.press("enter")
            await pilot.pause()
            await pilot.pause()
            assert isinstance(app.screen, QuizScreen)
            assert app.screen.quiz_state.current_index == 0
            assert len(app.screen_stack) == 2

            # Volver al inicio con Escape y empezar otra vez
            await pilot.press("escape")
            await pilot.pause()
            await pilot.pause()
            assert isinstance(app.screen, HomeScreen)
            assert len(app.screen_stack) == 2

            await start_quiz(app, pilot, "tester")
            assert isinstance(app.screen, QuizScreen)
            assert len(app.screen_stack) == 2

    asyncio.run(scenario())


def test_estadisticas_visibles_en_el_inicio(temp_db):
    """Tras jugar, volver al inicio muestra el resumen y el historial."""

    async def scenario():
        app = DevPythonQuiz()
        async with app.run_test(size=(100, 40)) as pilot:
            await start_quiz(app, pilot)
            for _ in range(10):
                await answer_and_next(app, pilot)

            await pilot.click("#home-button")
            await pilot.pause()
            await pilot.pause()
            assert isinstance(app.screen, HomeScreen)

            stats = str(app.screen.query_one("#stats-content").render())
            assert "tester" in stats
            assert "Quizzes completados: 1" in stats
            assert "Historial reciente" in stats

    asyncio.run(scenario())


def test_click_en_cualquier_opcion(temp_db):
    """Regresión: las opciones se desbordaban y el feedback tapaba la última."""
    async def scenario():
        app = DevPythonQuiz()
        async with app.run_test(size=(100, 40)) as pilot:
            await start_quiz(app, pilot)

            for option in ("opt-A", "opt-B", "opt-C", "opt-D"):
                region = app.screen.query_one(f"#{option}").region
                widget, _ = app.get_widget_at(region.x + 5, region.y)
                assert widget.id == option, f"El click en {option} llega a {widget.id}"

                await pilot.click(f"#{option}", offset=(5, 0))
                await pilot.pause()
                assert app.screen.quiz_state.selected_option == option[-1]

    asyncio.run(scenario())


def test_feedback_se_muestra_al_responder(temp_db):
    """Al responder aparecen el mensaje, la explicación y el botón de avance."""

    async def scenario():
        app = DevPythonQuiz()
        async with app.run_test(size=(100, 40)) as pilot:
            await start_quiz(app, pilot)
            await pilot.press("2")  # respuesta correcta de la primera pregunta
            await pilot.pause()
            await pilot.press("enter")
            await pilot.pause()

            title = str(app.screen.query_one("#feedback-title").render())
            explanation = str(app.screen.query_one("#feedback-explanation").render())
            assert "Correcto" in title
            assert "#" in explanation
            assert app.screen.query_one("#next-button").disabled is False

    asyncio.run(scenario())


def test_base_de_datos(temp_db):
    """Carga idempotente de preguntas, usuarios repetidos y guardado de partida."""
    database.init_database()
    database.insert_questions(
        [
            {
                "question": "pregunta",
                "options": {"A": "a", "B": "b", "C": "c", "D": "d"},
                "correct": "A",
                "explanation": "explicación",
            }
        ]
    )
    assert database.get_question_count() == 1
    # Volver a insertar no duplica
    database.insert_questions([])
    assert database.get_question_count() == 1

    user_id = database.get_or_create_user("ana")
    assert database.get_or_create_user("ana") == user_id
    assert database.get_last_active_user()["name"] == "ana"

    database.save_quiz_session(user_id, 1, 1, 2.5, 100.0)
    stats = database.get_user_stats(user_id)
    assert len(stats) == 1
    assert stats[0]["percentage"] == 100.0

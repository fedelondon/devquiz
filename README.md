# DevPythonQuiz

A TUI (Text User Interface) quiz application for Python beginners, built with [Textual](https://textual.textualize.io/).

## Features

- 🎯 **10 basic Python questions** with 4 options each
- 📊 **Progress bar** showing quiz progress
- ✅ **Immediate feedback** - green for correct, red for incorrect with explanation
- ⏱️ **Timer** tracking time taken
- 📈 **Final statistics** - score, percentage, time taken
- 💾 **SQLite3 database** for persistence
- 👤 **User profiles** - enter name/alias, view history
- 🔄 **Restart quiz** or return to home screen

## Installation

```bash
# Using uv (recommended)
uv sync

# Or using pip
pip install -e .
```

## Running

```bash
# With uv
uv run devquiz

# Or directly
python -m devquiz.main
```

## Project Structure

```
devquiz/
├── devquiz/
│   ├── __init__.py
│   ├── main.py          # Entry point and screen navigation
│   ├── database.py      # SQLite3 operations
│   ├── models.py        # Data models (Question, User, QuizState, etc.)
│   ├── questions.py     # Initial question data
│   ├── inicio.py        # Home screen
│   ├── quiz.py          # Quiz screen
│   ├── estadisticas.py  # Results/Statistics screen
│   └── app.tcss         # Custom CSS styling
├── tests/
│   └── test_app.py      # Headless integration tests (pytest + Textual pilot)
├── pyproject.toml
└── README.md
```

## Screens

1. **Home Screen** - Enter your name/alias, see previous statistics (typing a
   known name shows its history)
2. **Quiz Screen** - One question at a time with progress bar and options
3. **Results Screen** - Final statistics with option to restart or go home

## Keyboard Shortcuts

- `1-4` - Select option A-D
- `Enter` - Submit answer / next question / start quiz / restart quiz
- `←` `→` `↑` `↓` - Move between the options
- `N` or `→` - Next question (after answering)
- `Esc` - Back to the home screen (on the home screen: quit)
- `q` / `Ctrl+C` - Quit application

## Tests

```bash
uv run pytest
```

The tests run the whole application headlessly (no terminal needed) and use a
temporary database, so your real `devquiz.db` is never touched.

## Lint

```bash
uv run ruff check devquiz tests
```

## Database

The application uses SQLite3 (`devquiz.db`) with three tables:
- `users` - User profiles
- `questions` - Quiz questions
- `quiz_sessions` - Completed quiz statistics

The database file is ignored by git, so no user data is committed.

## Requirements

- Python 3.10+
- Textual 8.0+ (tested with 8.2.8)

## License

MIT
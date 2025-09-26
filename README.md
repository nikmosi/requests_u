# requests-u

requests-u is an asynchronous book downloader that scrapes supported light-novel
platforms and compiles the chapters into portable formats. It abstracts away the
per-site quirks and gives you a single command-line interface for collecting a
book, saving the chapters, and packaging them for offline reading.

## Features

- **Site-aware loaders** for `tl.rulate.ru` and `renovels.org`, with a
  dependency-injection container that makes it easy to plug in additional
  loaders.
- **Concurrent chapter downloads** powered by `asyncio` task groups, with a rate
  limiter to stay polite to upstream sites.
- **Flexible saving backends** – choose between the bundled `EbookSaver` and
  `FilesSaver`, or register your own saver implementation.
- **CLI trimming tools** to download a specific slice of chapters or pick the
  range interactively.
- **Structured configuration** backed by `pydantic` models so defaults and user
  input stay consistent.

## Installation

Prerequisites:

- Python 3.12
- [uv](https://github.com/astral-sh/uv) for dependency management (install with
  `pip install uv` or `pipx install uv`)

Clone the repository and install the project dependencies with uv:

```bash
uv sync
```

This will create an isolated `.venv` directory managed by uv and install both
runtime and development dependencies declared in `pyproject.toml`.

## Usage

Invoke the CLI through uv so it runs inside the managed environment:

```bash
uv run src/main.py https://tl.rulate.ru/book/12345 \
    --chunk-size 20 \
    --from 1 \
    --to 50 \
    --saver EbookSaver
```

Useful flags:

| Flag | Description |
| --- | --- |
| `url` | Required positional argument pointing to the book page you want to download. |
| `-c, --chunk-size` | Number of chapters to download concurrently (default `40`). |
| `-f, --from` | Lower bound (inclusive) for the chapter index to download. Defaults to the beginning. |
| `-t, --to` | Upper bound (inclusive) for the chapter index. Defaults to the last chapter. |
| `-i, --interactive` | Select chapter bounds interactively instead of passing numeric values. |
| `-w, --working-directory` | Directory where the downloader stores its output (default current directory). |
| `-s, --saver` | Saver backend to use. `EbookSaver` bundles chapters into an EPUB, `FilesSaver` writes raw chapter files. |
| `-r, --max-rate` | Maximum number of requests permitted within the limiter period (default `20`). |
| `-p, --period-time` | Time window, in seconds, used by the rate limiter (default `10`). |

The downloader automatically chooses an appropriate loader for the domain in the
provided URL. If you implement a new loader under `src/logic/main_page`, it will
be picked up once you register it in `LoaderService.get`.

### Running tests

```bash
uv run pytest
```

## Configuration and extensibility

- **Settings model** – All CLI arguments are validated and stored via the
  `Settings` model (`src/config/data.py`), ensuring consistent types throughout
  the app.
- **Savers** – Add a custom saver by subclassing `core.Saver` and placing the
  implementation in `src/logic/saver`. The CLI automatically discovers subclasses
  so they can be selected via `--saver`.
- **Rate limiter** – `AsyncLimiter` protects the remote services. Adjust
  `--max-rate` and `--period-time` to tune throughput.

## Contributing

1. Fork the repository and create a feature branch.
2. Install dependencies with `uv sync` and make your changes.
3. Run the test suite with `uv run pytest` and ensure everything passes.
4. Open a pull request describing your changes. Please follow the Conventional
   Commits spec for your commit messages.

## License

This project is licensed under the MIT License. See the `LICENSE` file for
details.

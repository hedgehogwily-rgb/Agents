# Agents

Учебный агент на LangChain, LangGraph и LangSmith. Принимает задачу, строит план, вызывает инструменты, хранит рабочую память и возвращает финальный ответ вместе со следом выполнения.

## Что умеет

- принимает цель текстом;
- составляет план и 2–4 критерия готовности;
- за один шаг вызывает один инструмент;
- после наблюдения обновляет память и решает, продолжать или остановиться;
- останавливается по ответу, лимиту шагов, повторной ошибке инструмента или повтору уже успешного вызова.

## Инструменты

| Tool | Вход | Что делает |
|---|---|---|
| `calculator` | `expression` | Считает арифметику через разбор AST, без `eval` |
| `read_local_file` | `path` | Читает текстовый файл внутри проекта |
| `text_search` | `path`, `query` | Ищет подстроку в файле и возвращает совпавшие строки |

Файловые инструменты принимают только пути внутри каталога проекта. Пример данных лежит в `examples/notes.txt`.

## Граф

```text
START → planner → actor → tools → state_updater → actor → …
                      └→ END
```

- `planner` один раз пишет план и критерии готовности, инструменты не вызывает.
- `actor` выбирает действие или финальный ответ. Если причина остановки уже стоит, новый вызов модели не делает.
- `tools` выполняет заявку через `ToolNode`.
- `state_updater` записывает observation в память и при необходимости ставит `tool_error` или `no_progress`.

`should_continue` ведёт в `tools`, только если у последнего ответа модели есть `tool_calls` и `stop_reason` пуст.

## State

Состояние описано в `schemas.py` как `AgentState` и целиком передаётся между узлами.

- `goal`, `plan`, `done_criteria` — задача, план и условия завершения.
- `messages` — диалог, список с reducer `add_messages`.
- `current_step`, `max_steps` — счётчик и лимит шагов актора.
- `observations`, `tool_results`, `notes` — рабочая память. Хранятся последние 5 записей, результат инструмента обрезается до 180 символов. `notes` копирует `tool_results`.
- `last_tool_name`, `last_observation` — последний вызов.
- `final_answer`, `stop_reason` — ответ и причина остановки: `final_answer`, `max_steps`, `tool_error`, `no_progress`.
- `trace` — локальный след: `node`, `plan`, `action`, `observation`, `state`, `stop`.

## LangSmith

Трассировка включается окружением, граф для этого не меняется. Ключи читаются из `.env`:

```text
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=...
LANGCHAIN_PROJECT=agents-project
LANGCHAIN_ENDPOINT=https://eu.api.smith.langchain.com
```

Если `LANGCHAIN_PROJECT` или `LANGCHAIN_ENDPOINT` не заданы, `settings.py` подставляет `agents-project` и EU-хост. `ChatOpenAI` эти ключи не получает: клиент LangSmith берёт их из окружения сам.

## Запуск

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt
```

В `.env` нужен `OPENAI_API_KEY`. Модель по умолчанию — `gpt-4o-mini`.

Все demo-задачи в терминале:

```bash
.venv/bin/python main.py
```

HTTP-сервис:

```bash
.venv/bin/uvicorn app:app --reload
```

- `GET /health` — сервис жив.
- `GET /demos` — список demo-задач.
- `POST /tasks` — запуск агента. Тело: `{"goal": "...", "max_steps": 5}`. `max_steps` необязателен, по умолчанию 5, диапазон 1–20.
- `GET /docs` — схема запросов.

Пример:

```bash
curl -s -X POST http://127.0.0.1:8000/tasks \
  -H 'content-type: application/json' \
  -d '{"goal":"Посчитай 15 + 27 через calculator"}'
```

Ответ содержит `final_answer`, `stop_reason`, `plan`, `trace` и память.

## Demo-задачи

Обычные, `max_steps=5`:

1. Посчитай 15 + 27 через calculator.
2. Прочитай `examples/notes.txt` и кратко скажи, о чём он.
3. Найди в `examples/notes.txt` строки про LangGraph через `text_search`.
4. Найди строку со словом `arithmetic`, затем посчитай 15 + 27 и ответь обоими результатами.

Проверки остановки:

5. Та же задача с поиском и сложением, но `max_steps=1`. Ожидается `max_steps` после первого инструмента.
6. Дважды прочитать `examples/missing.txt`. Ожидается `tool_error`.
7. Посчитать 15 + 27 и вызвать `calculator` с тем же выражением ещё раз. Если модель повторяет вызов, ожидается `no_progress` до выполнения инструмента.

## След целиком

Успешный прогон, цель «Посчитай 15 + 27 через calculator», остановка `final_answer`:

```text
node: planner
plan: 1. Открой калькулятор.
2. Введи число 15.
3. Добавь к нему 27.
4. Нажми кнопку равенства для получения результата.
done_criteria: ['15 + 27 = 42.']
node: actor
action: calculator {'expression': '15 + 27'}
node: tools
node: state_updater
observation: calculator: 42
state: tool_results=["calculator {'expression': '15 + 27'} => 42"] notes=["calculator {'expression': '15 + 27'} => 42"] done_criteria=['15 + 27 = 42.']
node: actor
action: 15 + 27 = 42.
stop: final_answer
```

Ошибочный прогон, два чтения `examples/missing.txt`, остановка `tool_error`:

```text
node: planner
plan: 1. Вызови функцию `read_local_file` с аргументом `path` равным `examples/missing.txt` и зафиксируй результат.
2. Независимо от результата первого вызова, снова вызови `read_local_file` с тем же аргументом `path`.
node: actor
action: read_local_file {'path': 'examples/missing.txt'}
node: tools
node: state_updater
observation: read_local_file: error: file not found: examples/missing.txt
node: actor
action: read_local_file {'path': 'examples/missing.txt'}
node: tools
node: state_updater
observation: read_local_file: error: file not found: examples/missing.txt
stop: tool_error
```

По следу видно, где ход совпал с планом, а где второй одинаковый вызов оборвал задачу.

## Ограничения

Агент умеет считать арифметику, читать локальные текстовые файлы и искать в них подстроку.

Пока не умеет:

- искать в интернете, ходить в базы и вызывать внешние API;
- читать файлы вне каталога проекта и выполнять произвольный Python;
- гарантировать, что модель повторит вызов, если цель этого просит: тогда след заканчивается `final_answer`, а `no_progress` не срабатывает;
- помнить больше пяти последних результатов и больше 180 символов одного результата;
- продолжать задачу после `max_steps`, повторной одинаковой ошибки или повтора успешного вызова.

Это один агент с одним графом, не многоагентная система.

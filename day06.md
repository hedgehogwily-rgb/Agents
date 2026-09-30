# День 6. Разбор trace

LangSmith включается переменными в `.env` (`LANGCHAIN_TRACING_V2`, `LANGCHAIN_API_KEY`, `LANGCHAIN_PROJECT`, `LANGCHAIN_ENDPOINT`). Граф для этого не меняется. Ниже разбор по локальному следу: строки `node:`, `action:`, `observation:`, `state:` и `stop:`.

## Успешный

Цель: «Посчитай 15 + 27 через calculator».

`stop: final_answer`.

`node: planner` пишет план. `node: actor` выбирает `calculator {'expression': '15 + 27'}`. `node: tools` выполняет вызов. `node: state_updater` кладёт observation `42` и обновляет `tool_results`. Следующий `node: actor` отвечает текстом «15 + 27 = 42» и останавливается. Поведение совпало с планом.

## Частично успешный

Цель: найти в `examples/notes.txt` строку со словом arithmetic и затем посчитать 15 + 27. Лимит: `max_steps=1`.

`stop: max_steps`.

Поиск проходит: `node: actor` → `node: tools` → `node: state_updater`, observation содержит строку про arithmetic. Калькулятор не начинается: следующий вход в `node: actor` упирается в лимит до нового вызова модели. Задача выполнена наполовину, место обрыва видно по `stop: max_steps` сразу после первой observation.

## Ошибочный

Цель: два раза подряд прочитать `examples/missing.txt`.

`stop: tool_error`.

Оба раза `node: tools` вызывает `read_local_file` с одним и тем же путём. `node: state_updater` дважды получает `error: file not found`. Граф не падает: вторая одинаковая ошибка записывает `stop: tool_error` и финальный текст. По следу видно, что прогресса не было: два одинаковых action и две одинаковые observation.

## Failure modes

- Модель не повторяет tool, хотя цель просила второй вызов, и след заканчивается `stop: final_answer` вместо `stop: no_progress`. Детектор повтора срабатывает только если заявка с теми же аргументами реально пришла.
- Плохие аргументы приходят от `ToolNode` обычным текстом, не JSON. Без разбора в `state_updater` граф падает на `ValidationError` до `stop_reason`.
- `max_steps` обрывает многошаговую задачу после первого инструмента: observation уже есть, следующий action нет.
- Повтор одной и той же ошибки файла — это не новый шаг, а `stop: tool_error`.
- Успешный повтор того же вызова (`calculator` с тем же выражением) снимается в `node: actor` до `node: tools` и пишется как `stop: no_progress`.

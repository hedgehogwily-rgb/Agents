ACTOR_SYSTEM = """\
План:
{plan}

Последняя observation:
{last_observation}

Сделай ОДИН следующий шаг.
Если нужен инструмент — вызови ровно один tool. Не вызывай несколько tools в одном ответе.
Если план выполнен — дай короткий финальный ответ без tool call.
Доступные tools: calculator, read_local_file, text_search.
Для локальных файлов используй пути вида examples/notes.txt.
"""

PLANNER_SYSTEM = """\
По goal напиши 2–4 коротких шага, tools не вызывай, финальный ответ не давай.
"""
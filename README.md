🛠️ 🛠️ Agents

📝 День 1: agents_day01

День 1 — Каркас агента на LangGraph и базовый graph state

🎯 Цель дня
Создать базовый graph-based agent skeleton на LangGraph, описать state и собрать минимальный execution flow.

📋 Задачи
1. 🧱 Установить зависимости:
   - langchain
   - langgraph
   - langsmith
   - pydantic
2. 📦 Описать базовый AgentState:
   - goal
   - messages / history
   - current_step
   - max_steps
   - final_answer
3. 🕸️ Собрать минимальный graph в LangGraph
4. 🧠 Добавить первый узел, который получает goal и предлагает следующий action
5. 🧪 Протестировать на 2–3 простых задачах

🎉 Критерии успеха
- ✅ LangGraph graph создаётся и запускается
- ✅ Есть AgentState
- ✅ Агент делает хотя бы один осмысленный шаг
- ✅ Используется именно graph-based структура, а не просто один вызов модели

---
Удачи с реализацией! 🚀
🛠️ 🛠️ Agents

📝 День 3: agents_day03

День 3 — Planning node и graph orchestration

🎯 Цель дня
Добавить planning-логику и разделить роли узлов графа: planning, acting, observation.

📋 Задачи
1. 🧭 Добавить planning node, который формирует краткий план
2. 🧠 Разделить роли узлов как минимум на:
   - planner
   - actor / tool node
   - state updater
3. 🔄 Настроить переходы между узлами графа
4. 🧪 Проверить, что multi-step задача проходит через несколько узлов осмысленно
5. 📊 Вывести trace: plan → action → observation → next action

🎉 Критерии успеха
- ✅ Есть planning node
- ✅ Есть минимум 3 понятных узла графа
- ✅ Переходы между узлами работают корректно
- ✅ Multi-step execution стал последовательным и читаемым

---
Удачи с реализацией! 🚀
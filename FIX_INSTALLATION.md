# Решение проблемы с конфликтом зависимостей

## Проблема
Конфликт версий `httpx` между `python-telegram-bot` и `mistralai`.

## Решение 1: Обновить версии (Рекомендуется)

```bash
# Удалите старые пакеты
pip uninstall python-telegram-bot mistralai -y

# Установите обновленные версии
pip install --upgrade pip
pip install python-telegram-bot>=21.0 mistralai>=1.1.0
pip install -r requirements.txt
```

## Решение 2: Использовать более старую версию mistralai (если решение 1 не работает)

Если решение 1 не работает, попробуйте зафиксировать версии, которые точно работают:

```bash
pip install python-telegram-bot==20.8 mistralai==1.0.2
```

## Решение 3: Использовать альтернативный клиент Mistral

Если конфликт не решается, можно использовать HTTP-клиент напрямую вместо официального SDK.

## Проверка установки

После установки проверьте:

```bash
python -c "from telegram import Update; print('OK')"
python -c "from mistralai import Mistral; print('OK')"
```

Если оба команды выполняются без ошибок, установка прошла успешно.


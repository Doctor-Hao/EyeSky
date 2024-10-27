# Дроный

## Docker
1. Redis
2. Nginx

## Python
**Запускает нативно**

---
### Пример команд для первого запуска
1. Пример для UNIX:
```[bash]
docker compose -f docker-compose.yaml up -d && \
    pip3 install -r requirements.txt && \
    source ~/.venv/bin/activate && \
    python3 main.py
```

2. Пример для Windows:
```[bash]
docker compose up -d && \
python -m venv .venv && \
. .venv/Scripts/activate && \
pip install -r requirements.txt && \
python main.py
```

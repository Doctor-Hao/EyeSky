# Этап 1: Сборка приложения
FROM node:18 AS builder

# Установка рабочей директории
WORKDIR /app

# Копирование файлов package.json и package-lock.json для установки зависимостей
COPY package*.json ./

# Установка зависимостей
RUN npm install --no-cache

# Копирование остальных файлов проекта
COPY . .

# Сборка приложения
RUN npm run build

# Этап 2: Запуск приложения с Nginx
FROM nginx:alpine

# Копирование собранных файлов из этапа сборки в Nginx
COPY --from=builder /app/dist /usr/share/nginx/html

# Копирование конфигурации Nginx (при необходимости)
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Экспонирование порта 80
EXPOSE 80

# Команда для запуска Nginx
CMD ["nginx", "-g", "daemon off;"]

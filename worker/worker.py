import logging
import cv2
import numpy as np
import json
import tensorflow as tf
import base64
import asyncio
from sqlalchemy import create_engine, Column, Integer, String, LargeBinary, DateTime, ARRAY
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime
import uuid
from sqlalchemy.exc import IntegrityError
from collections import deque
import pytz
from confluent_kafka import Consumer, KafkaException, KafkaError
from io import BytesIO  # Импорт BytesIO для работы с буферами
from minio import Minio  # Импорт Minio для работы с MinIO

# Конфигурация Kafka Consumer
conf = {
    'bootstrap.servers': 'kafka:9092',  # Адрес вашего Kafka сервера
    'group.id': 'my_group',  # Группа для Consumer'ов
    'auto.offset.reset': 'earliest',  # Начинаем чтение с самого начала, если нет смещений
    'security.protocol': 'PLAINTEXT'
}

# Создаем Consumer
consumer = Consumer(conf)
consumer.subscribe(['frames'])

moscow_tz = pytz.timezone('Europe/Moscow')

# Health check для базы данных
def check_database():
    session = Session()
    try:
        session.query(FrameData).first()
        return True
    except Exception as e:
        logging.error(f"Проблема с базой данных: {e}")
        exit(1)
    finally:
        session.close()

# Логирование
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

IMG_SIZE = 224
FRAMES_PER_VIDEO = 20
TRANSFER_VALUES_SIZE = 4096

# Настройка базы данных
DATABASE_URI = "postgresql://postgres:postgres@postgres:5432/database"
engine = create_engine(DATABASE_URI)
Base = declarative_base()

class PredictionFrame(Base):
    __tablename__ = "predictions"
    
    uid = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))  # Генерация UUID
    images = Column(ARRAY(PG_UUID), nullable=False)
    predict = Column(Integer)
    
class FrameData(Base):
    __tablename__ = "frames"

    uid = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))  # Генерация UUID
    connection_uid = Column(String)
    frame_id = Column(Integer)  # Поле для frame_id
    date = Column(DateTime, default=lambda: datetime.now(moscow_tz))  # Дата по умолчанию
    data = Column(String, nullable=True)  # Поле для URL изображения

try:
    Base.metadata.create_all(engine)
    logging.info('Таблица "frames" успешно создана или уже существует.')
except IntegrityError as e:
    logging.error(f"Ошибка при создании таблицы: {e}")

Session = sessionmaker(bind=engine)

# Загрузка модели
logging.info("Загрузка моделей ...")
model_vgg16 = tf.keras.models.load_model("models/model_vgg16.keras")
model_lstm = tf.keras.models.load_model("models/violence_detection_model.keras")
logging.info("Модели загружены")

# Преобразование кадра
def preprocess_frame(frame):
    resized_frame = cv2.resize(frame, (224, 224))
    normalized_frame = resized_frame.astype(np.float32) / 255.0
    return normalized_frame

# Асинхронная обработка кадров
def process_frames():
    session = Session()
    frames = deque(maxlen=20)  # Очередь с максимальной длиной 20 кадров
    windows_uids = deque(maxlen=20)
    try:
        while True:
            msg = consumer.poll(timeout=1.0)
            if msg is None:
                continue
            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    print(f"End of partition reached {msg.partition()}")
                elif msg.error():
                    raise KafkaException(msg.error())
            else:
                frames.append(json.loads(msg.value().decode('utf-8')))

            if len(frames) >= 20:
                frames_array = []

                # Препроцессинг кадров в массив изображений
                for i in frames:
                    decoded_frame = base64.b64decode(i["data"])
                    np_frame = np.frombuffer(decoded_frame, np.uint8)
                    img = cv2.imdecode(np_frame, cv2.IMREAD_COLOR)
                    preprocessed_frame = preprocess_frame(img)
                    frames_array.append(preprocessed_frame)

                # Получение признаков и предсказание класса
                transfer_values = model_vgg16.predict(np.array(frames_array))            
                transfer_values = np.expand_dims(transfer_values, axis=0)
                min_frame_id, max_frame_id = min(frames, key=lambda x: x['frame_id'])['frame_id'], max(frames, key=lambda x: x['frame_id'])['frame_id']
                prediction = model_lstm.predict(transfer_values)
                predicted_class = int(np.argmax(prediction))

                logging.info(f"Min -> Max: {min_frame_id} -> {max_frame_id}\nПредсказанный класс: {predicted_class}")

                # Сохранение каждого кадра в MinIO и в базе данных
                for frame_data in frames:
                    decoded_image = base64.b64decode(frame_data["data"])
                    _, buffer = cv2.imencode(".jpg", cv2.imdecode(np.frombuffer(decoded_image, np.uint8), cv2.IMREAD_COLOR))

                    # Создание нового объекта в базе данных
                    new_image_data = FrameData(
                        connection_uid=frame_data['connection_uid'],
                        frame_id=frame_data['frame_id'],
                        date=frame_data['date']  # Текущая дата
                    )
                    session.add(new_image_data)
                    session.flush()  # Обязательно для получения uid

                    # Загрузка изображения в MinIO и получение URL с использованием uid
                    image_url = upload_image_to_minio(buffer, new_image_data.uid)

                    # Обновляем запись с URL изображения
                    new_image_data.data = image_url
                    session.add(new_image_data)

                    windows_uids.append(new_image_data.uid)

                newPredictionFrame = PredictionFrame(
                    images=list(windows_uids),
                    predict=predicted_class
                )
                session.add(newPredictionFrame)    
                
                session.commit()
                
                frames.popleft()
                windows_uids.popleft()

    except KeyboardInterrupt:
        pass
    finally:
        consumer.close()

def upload_image_to_minio(buffer, uid):
    """Загружает изображение в MinIO и возвращает URL для доступа к изображению."""
    # Создаем клиент MinIO без авторизации
    minio_client = Minio('minio:9000',
                          access_key='',  # Пустой ключ, так как доступ без авторизации
                          secret_key='',  # Пустой секретный ключ
                          secure=False)  # Убедитесь, что у вас не включен HTTPS

    # Уникальное имя для изображения (основанное на uid)
    object_name = f"{uid}.jpg"
    
    # Загружаем изображение в MinIO
    try:
        minio_client.put_object(
            'frames',  # Название вашего бакета
            object_name,
            BytesIO(buffer),  # Используем BytesIO для передачи данных
            len(buffer),
            content_type='image/jpeg'
        )
    except Exception as e:
        logging.error(f"Ошибка при загрузке изображения в MinIO: {e}")
        return None  # Вернуть None в случае ошибки

    # Возвращаем URL для доступа к изображению
    return f"http://minio:9000/{object_name}"

if __name__ == "__main__":
    logging.info("Запуск обработки кадров")
    check_database()
    process_frames()

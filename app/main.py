import logging
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, WebSocket, Query, HTTPException
import json
import cv2
import numpy as np
import base64
import websockets
from sqlalchemy import create_engine, Column, Integer, String, DateTime, ARRAY, cast
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime
import uuid
from confluent_kafka import Producer
import base64
from minio import Minio
import config
import pytz

# Настройка часового пояса
moscow_tz = pytz.timezone('Europe/Moscow')

# Настройка базы данных
engine = create_engine(config.DATABASE_URI)
Base = declarative_base()
Session = sessionmaker(bind=engine)

# Конфигурация Kafka Producer
producer = Producer(config.KAFKA_CONFIG)

# Инициализациия FastAPI
app = FastAPI()

# Настройка Redis
# redis_client = redis.StrictRedis(host=config.REDIS_HOST, port=config.REDIS_PORT, db=0, decode_responses=True)

# Набор подключенных клиентов
connected_clients = set()

# Настройка логирования
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def delivery_report(err, msg):
    if err is not None:
        print(f'Ошибка доставки: {err}')
    else:
        print(f'Сообщение доставлено: {msg.topic()} [{msg.partition()}]')
    

def check_kafka():
    try:
        producer.produce('healthcheck', value='health_check')
        producer.flush(timeout=1.0)
    except Exception as e:
        logging.error(f"Проблема с kafka: {e}")
        exit(1)

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
        logging.info("[Postgresql]: OK")
        session.close()

def get_description(value):
    match value:
        case 0: return "Насилие"
        case 1: return "Норма"
        case _: return "Неизвестный тип преступления"


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

# Конфигурация клиента MinIO
minio_client = Minio(config.AWS_S3_URI,
                      access_key=config.AWS_S3_ACCESS_KEY,
                      secret_key=config.AWS_S3_SECRET_KEY, 
                      secure=False)  

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/images")
async def get_predictions_json(page: int = Query(1, ge=1), limit: int = Query(10, ge=1)):
    session = Session()
    
    total_predictions = session.query(PredictionFrame).count()
    offset = (page - 1) * limit
    predictions = session.query(PredictionFrame).offset(offset).limit(limit).all()
    
    if not predictions:
        raise HTTPException(status_code=404, detail="No predictions found")

    response_data = []

    for prediction in predictions:
        images = session.query(FrameData).filter(cast(FrameData.uid, PG_UUID).in_(prediction.images)).all()
        image_data = []

        for image in images:
            # Генерация URL для скачивания изображения
            image_url = f"http://{config.AWS_S3_URI}/frames/{image.uid}.jpg"
            
            image_data.append({
                "uid": image.uid,
                "data": image_url
            })

        response_data.append({
            "prediction": get_description(int(prediction.predict)),
            "images": image_data 
        })

    return {
        "total_predictions": total_predictions,
        "current_page": page,
        "total_pages": (total_predictions + limit - 1) // limit,
        "predictions": response_data
    }

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    logging.info("Client connected")
    connection_uid = uuid.uuid4()
    frame_id = 0
    try:
        while True:
            message = await websocket.receive_text()
            data = json.loads(message)

            if "data" in data:
                frame_data = data["data"]
                logging.info(f"Frame data received for - {connection_uid}")

                img_array = np.frombuffer(base64.b64decode(frame_data), np.uint8)
                frame = cv2.imdecode(img_array, cv2.IMREAD_COLOR)  # Преобразуем в цветное изображение

                resized_frame = cv2.resize(frame, (224, 224))  # Изменение размера до 224x224

                _, buffer = cv2.imencode(".jpg", resized_frame)
                gray_resized_data = base64.b64encode(buffer).decode("utf-8")
                
                frame_id += 1
                date = datetime.now()
                data = gray_resized_data
                # Сохраняем преобразованный кадр в Kafka
                producer.produce('frames', value=json.dumps({"connection_uid": str(connection_uid), "frame_id": frame_id, "date": str(date), "data": gray_resized_data}), callback=delivery_report)
                producer.flush()
        
                logging.info("Processed frame pushed to Kafka")
                
    except websockets.ConnectionClosed:
        logging.info("Client disconnected")
    except Exception as e:
        logging.error(f"An error occurred: {e}")

if __name__ == "__main__":
    import uvicorn
    logging.info("Starting WebSocket server on port 8080")
    check_database()
    check_kafka()
    uvicorn.run(app, host="0.0.0.0", port=8080)

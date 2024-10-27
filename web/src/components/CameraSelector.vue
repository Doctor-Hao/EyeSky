<template>
  <h1 class="mb-4">Используйте камеру или загрузите видео</h1>
  <v-sheet class="d-flex align-center justify-center mb-5 ga-2">
    <v-card width="400" outlined>
      <v-card-title class="text-h5">
        Загрузка видео
      </v-card-title>
      <v-divider></v-divider>
      <v-card-text>
        <v-file-input
            accept="video/*"
            density="comfortable"
            label="Видеофайл"
            @change="handleFileUpload"
        />
      </v-card-text>
    </v-card>

    <v-card width="400"  outlined>

      <v-card-title class="text-h5">Выбор камеры</v-card-title>
      <v-divider></v-divider>
      <v-card-text>
        <v-select
            v-model="selectedCamera"
            :items="cameras"
            item-value="deviceId"
            item-title="label"
            label="Выберите камеру"
            density="comfortable"
        >
          <template #no-data>
            <v-list-item>
              <v-list-item-title>Нет доступных камер</v-list-item-title>
            </v-list-item>
          </template>
        </v-select>
      </v-card-text>
    </v-card>
  </v-sheet>

  <v-sheet>
    <v-btn class="mr-2" @click="startSendingFrames">Начать запись</v-btn>
    <v-btn @click="stopSendingFrames">Остановить запись</v-btn>
  </v-sheet>

  <v-card flat class="my-2">
    <video class="video" ref="video" autoplay muted @ended="onVideoEnded"></video>
  </v-card>

</template>

<script setup>
import {ref, onMounted} from 'vue';

const cameras = ref();
const selectedCamera = ref();
const mediaStream = ref(null);
const frameInterval = ref(null);
const socket = ref(null);
const currentFrameSrc = ref('');
const videoFile = ref(null);
const video = ref();

const getCameraList = async () => {
  try {
    const devices = await navigator.mediaDevices.enumerateDevices();
    cameras.value = devices.filter(device => device.kind === 'videoinput');
    if (cameras.value) {
      selectedCamera.value = cameras.value[0].deviceId
    }
  } catch (error) {
    console.error('Ошибка при получении камер:', error);
  }
};

const handleFileUpload = (event) => {
  const file = event.target.files[0];
  if (file && file.type.startsWith('video/')) {
    videoFile.value = URL.createObjectURL(file);
    video.value.src = videoFile.value;
    video.value.style.display = 'block';
  }
};

const startSendingFrames = async () => {
  if (videoFile.value) {
    video.value.play();
  } else {
    const constraints = {
      video: {deviceId: selectedCamera.value, frameRate: 24},
    };
    mediaStream.value = await navigator.mediaDevices.getUserMedia(constraints);
    video.value.srcObject = mediaStream.value;
  }

  socket.value = new WebSocket(`ws://${window.location.host}/ws`);

  socket.value.onopen = () => console.log('Connected to WebSocket server');
  socket.value.onmessage = (event) => alert(`[message] Data received: ${event.data}`);
  socket.value.onclose = (event) => {
    const msg = event.wasClean
        ? `[close] Connection closed cleanly, code=${event.code}, reason=${event.reason}`
        : '[close] Connection interrupted';
    console.log(msg);
  };
  socket.value.onerror = (error) => console.error('Connection error:', error);

  const canvas = document.createElement('canvas');
  const context = canvas.getContext('2d');

  const sendFrame = () => {
    if (video.value.readyState === video.value.HAVE_ENOUGH_DATA) {
      canvas.width = video.value.videoWidth;
      canvas.height = video.value.videoHeight;
      context.drawImage(video.value, 0, 0, canvas.width, canvas.height);

      canvas.toBlob((blob) => {
        if (blob) {
          const reader = new FileReader();
          reader.onloadend = () => {
            const base64data = reader.result.split(',')[1];
            socket.value.send(JSON.stringify({data: base64data}));
            currentFrameSrc.value = reader.result;
          };
          reader.readAsDataURL(blob);
        }
      });
    }
  };

  frameInterval.value = setInterval(sendFrame, 500);
};

const onVideoEnded = () => stopSendingFrames();

const stopSendingFrames = () => {
  if (mediaStream.value) {
    mediaStream.value.getTracks().forEach((track) => track.stop());
    mediaStream.value = null;
  }
  if (frameInterval.value) {
    clearInterval(frameInterval.value);
  }
  if (socket.value) {
    socket.value.close();
  }
  if (videoFile.value) {
    video.value.pause();
  }
};

onMounted(() => {
  getCameraList();
});
</script>

<style scoped>
#current-frame {
  width: 100%;
  height: auto;
  object-fit: fill;
}

#frame-container {
  margin-top: 20px;
  max-width: 500px;
  width: 100%;
  height: 90%;
  overflow: hidden;
}

.video {
  max-width: 400px;
}
</style>

<template>
  <div>
    <h1 class="mb-4">Галерея</h1>

    <!-- Фильтр по категории -->
    <v-card flat outlined class="d-flex align-center mb-3">
      <v-card-title class="pb-6">Категория:</v-card-title>
      <v-card-text class="ma-0 pa-0">
        <v-select
          v-model="selectedCategory"
          :items="uniqueCategories"
          density="compact"
          @change="filterPredictions"
        />
      </v-card-text>
    </v-card>

    <div v-if="predictions.length === 0">No predictions found</div>
    <v-row class="justify-center">
      <v-col cols="12" md="3" lg="2" v-for="(prediction, index) in displayedPredictions" :key="index">
        <v-card :color="'surface'" outlined>
          <v-img
            :src="prediction.gif"
            height="200px"
            class="white--text"
            :alt="prediction.category_type"
          />
          <v-card-text>
            <strong>Результат:</strong> {{ prediction.category_type }}
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <div class="pagination">
      <v-btn :disabled="page <= 1" @click="updatePage(page - 1)">Previous</v-btn>
      <span>Page {{ page }} of {{ totalPages }}</span>
      <v-btn :disabled="page >= totalPages" @click="updatePage(page + 1)">Next</v-btn>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import axios from 'axios';
import gifshot from 'gifshot'; // Import gifshot

// State management
const predictions = ref([]);
const page = ref(1);
const limit = ref(10);
const totalPages = ref(1);
const selectedCategory = ref('Все');
const filteredPredictions = ref([]);

const displayedPredictions = computed(() => filteredPredictions.value);

const uniqueCategories = computed(() => {
  const categories = predictions.value.map(prediction => prediction.category_type);
  return ['Все', ...new Set(categories)];
});

// Function to fetch predictions from the server
const fetchPredictions = async () => {
  try {
    const response = await axios.get(`http://localhost:80/api/all?page=${page.value}&limit=${limit.value}`);
    
    // Ensure response structure is valid before using it
    if (response.data && response.data.predictions) {
      predictions.value = await Promise.all(response.data.predictions.map(formatPrediction));
      totalPages.value = response.data.total_pages; // Make sure total_pages exists
      filterPredictions(); // Apply filtering after fetching
    }
  } catch (error) {
    console.error("Error fetching predictions:", error);
  }
};

// Format each prediction
const formatPrediction = async (prediction) => {
  return {
    gif: await createGifUrl(prediction.images),
    category_type: prediction.prediction,
  };
};

// Create URL for GIF from images
const createGifUrl = async (images) => {
  const gifImages = await Promise.all(images.map(fetchImageBlob));
  return createGifBlob(gifImages);
};

// Fetch images via HTTP request
const fetchImageBlob = async (image) => {
  try {
    const response = await axios.get(`http://localhost:80/s3/frames/${image.uid}.jpg`, {
      responseType: 'blob', // Fetch image as Blob
    });

    if (response.status !== 200) {
      throw new Error(`Failed to load image: ${response.status}`);
    }

    // Check for empty Blob
    if (response.data.size === 0) {
      throw new Error("Received an empty blob");
    }

    console.log(`Fetched image blob: ${image.uid}, Size: ${response.data.size}`);
    return response.data;
  } catch (error) {
    console.error("Error fetching image blob:", error);
    throw error; // Propagate error
  }
};

// Create GIF from images using gifshot
const createGifBlob = async (imageBlobs) => {
  return new Promise((resolve, reject) => {
    gifshot.createGIF(
      {
        images: imageBlobs.map((blob) => URL.createObjectURL(blob)),
        gifWidth: 224,
        gifHeight: 224,
        interval: 0, // Set interval to 0 for no delay between frames
        numFrames: imageBlobs.length,
      },
      (obj) => {
        if (!obj.error) {
          resolve(obj.image); // Returns the base64-encoded GIF
        } else {
          reject(obj.error); // Handle errors if GIF creation fails
        }
      }
    );
  });
};

// Filter predictions based on the selected category
const filterPredictions = () => {
  if (selectedCategory.value && selectedCategory.value !== 'Все') {
    filteredPredictions.value = predictions.value.filter(prediction => prediction.category_type === selectedCategory.value);
  } else {
    filteredPredictions.value = [...predictions.value];
  }
};

// Update page and fetch new predictions
const updatePage = async (newPage) => {
  if (newPage > 0 && newPage <= totalPages.value) { // Ensure newPage is valid
    page.value = newPage;
    await fetchPredictions();
  }
};

// Fetch predictions when component is mounted
onMounted(fetchPredictions);
</script>

<style scoped>
.mb-4 {
  margin-bottom: 16px; /* Adjust the margin as needed */
}
.prediction {
  margin: 20px;
}
.pagination {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 20px;
}
.v-card {
  margin: 10px; /* Space between cards */
}
</style>

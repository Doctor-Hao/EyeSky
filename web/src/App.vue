<template>
  <v-app class="ma-3">
    <v-app-bar app class="px-2" color="primary">
      <v-btn title="Главная" @click="navigateToHome">
        Главная
        <v-icon class="ml-2">mdi-video-outline</v-icon>
      </v-btn>
      <v-btn title="Галерея" @click="navigateToGallery">
        Галерея
        <v-icon class="ml-2">mdi-image-multiple-outline</v-icon>
      </v-btn>
      <v-spacer></v-spacer>
    </v-app-bar>

    <v-main>
      <v-container class="d-flex flex-column align-center py-5" fluid>
        <router-view />
      </v-container>
    </v-main>

    <v-footer app class="d-flex justify-end" color="surface">
      <v-col class="text-center">&copy; 2024 Drone Security "EyeSky"</v-col>
    </v-footer>
  </v-app>
</template>

<script setup>
import { useRouter } from 'vue-router';

const router = useRouter();

const navigateToHome = () => {
  router.push('/');
};

const navigateToGallery = () => {
  router.push('/images');
};
</script>

<style scoped>
body {
  margin: 0;
  font-family: 'Roboto', sans-serif;
}
</style>

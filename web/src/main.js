import { createApp } from 'vue';
import App from './App.vue';
import router from './router.js';
import { createVuetify } from 'vuetify';
import 'vuetify/styles';
import '@mdi/font/css/materialdesignicons.css';

const vuetify = createVuetify({
  theme: {
    defaultTheme: 'light',
  },
});

createApp(App)
  .use(router)
  .use(vuetify)
  .mount('#app');

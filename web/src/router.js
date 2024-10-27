import { createRouter, createWebHistory } from 'vue-router';
import CameraSelector from './components/CameraSelector.vue';
import ImageGallery from './components/ImageGallery.vue';

const routes = [
	{
		path: '/',
		name: 'CameraSelector',
		component: CameraSelector,
	},
	{
		path: '/images',
		name: 'ImageGallery',
		component: ImageGallery,
	},
];

const router = createRouter({
	history: createWebHistory(),
	routes,
});

export default router;

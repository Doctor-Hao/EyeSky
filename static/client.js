// // Подключаемся к WebSocket серверу через Nginx
// const socket = io('http://localhost/socket.io/');
// let sendingFrames = false; // Флаг для отслеживания состояния отправки кадров

// // Обрабатываем полученные данные
// socket.on('latest_frame', (data) => {
// 	console.log('Received frame:', data); // Debugging line

// 	// Проверяем, есть ли данные
// 	if (data && data.data) {
// 		const img = new Image();
// 		img.src = 'data:image/jpeg;base64,' + data.data;
// 		img.style.width = '100%'; // Устанавливаем ширину изображения
// 		img.style.height = 'auto'; // Автоматическая высота для сохранения пропорций
// 		img.alt = 'Latest frame'; // Альтернативный текст для изображения
// 		document.body.appendChild(img); // Добавляем изображение на страницу
// 	} else {
// 		console.warn('No data received for the image.');
// 	}
// });

// // Сообщение о подключении
// socket.on('connect', () => {
// 	console.log('WebSocket connected!');
// });

// // Обработка ошибок
// socket.on('connect_error', (error) => {
// 	console.error('WebSocket connection error:', error);
// });

// // Функция для отправки кадров
// function toggleFrameSending() {
// 	sendingFrames = !sendingFrames; // Переключаем состояние отправки

// 	if (sendingFrames) {
// 		console.log('Started sending frames');
// 		socket.emit('start_sending'); // Отправляем событие на сервер
// 	} else {
// 		console.log('Stopped sending frames');
// 		socket.emit('stop_sending'); // Отправляем событие на сервер
// 	}
// }

// // Проверяем URL и автоматически запускаем видео, если это нужный URL
// if (window.location.pathname === '/video/start') {
// 	// Замените '/video' на ваш URL
// 	toggleFrameSending(); // Запускаем отправку кадров
// }

// // Создание кнопки для управления отправкой кадров
// const button = document.createElement('button');
// button.innerText = 'Toggle Frame Sending';
// button.onclick = toggleFrameSending; // Привязываем функцию к событию onclick
// document.body.appendChild(button); // Добавляем кнопку на страницу

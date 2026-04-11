import axios from 'axios';

const client = axios.create({
  baseURL: '/api/v1',
  timeout: 60000, // 60s — model inference can be slow on CPU
});

export default client;

import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';
export default defineConfig({plugins:[react(),tailwindcss()],server:{host:'127.0.0.1',port:5174,proxy:{'/api':{target:'http://127.0.0.1:8001',changeOrigin:true}}},build:{chunkSizeWarningLimit:1500,rollupOptions:{output:{manualChunks:{react:['react','react-dom','react-router-dom']}}}}});

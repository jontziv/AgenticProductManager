import { defineConfig, loadEnv } from 'vite';
import path from 'path';
import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
export default defineConfig(function (_a) {
    var mode = _a.mode;
    var env = loadEnv(mode, process.cwd(), '');
    return {
        plugins: [
            react(),
            tailwindcss(),
        ],
        resolve: {
            alias: {
                '@': path.resolve(__dirname, './src'),
            },
        },
        assetsInclude: ['**/*.svg', '**/*.csv'],
        server: {
            port: 5173,
            proxy: {
                '/api': {
                    target: env.API_BASE_URL || 'http://localhost:8000',
                    changeOrigin: true,
                },
            },
        },
        build: {
            sourcemap: true,
            rollupOptions: {
                output: {
                    manualChunks: {
                        vendor: ['react', 'react-dom', 'react-router'],
                        ui: ['lucide-react', 'recharts'],
                    },
                },
            },
        },
    };
});

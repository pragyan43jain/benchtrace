import {defineConfig} from '@playwright/test';
export default defineConfig({testDir:'./e2e',timeout:120000,workers:1,use:{baseURL:process.env.BENCHTRACE_URL||'http://localhost:8080',headless:true,launchOptions:process.env.CHROME_PATH?{executablePath:process.env.CHROME_PATH}:{},screenshot:'only-on-failure'},reporter:'list'});

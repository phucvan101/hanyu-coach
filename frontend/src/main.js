import { createApp } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import '@fontsource/nunito/400.css'
import '@fontsource/nunito/500.css'
import '@fontsource/nunito/600.css'
import '@fontsource/nunito/700.css'
import '@fontsource/nunito/800.css'
import '@fontsource/nunito/900.css'
import './styles.css'
import './composables/useTheme'
import App from './App.vue'
import { loadSettings } from './composables/useSettings'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: () => import('./views/Home.vue') },
    { path: '/hanzi', component: () => import('./views/Drill.vue') },
    { path: '/game', component: () => import('./views/GameHub.vue') },
    { path: '/game/ban-chu', component: () => import('./views/TypeShooter.vue') },
    { path: '/flashcards', component: () => import('./views/Flashcards.vue') },
    { path: '/talk', component: () => import('./views/Talk.vue') },
    { path: '/task/:id', component: () => import('./views/TaskRewrite.vue') },
    { path: '/library', component: () => import('./views/Library.vue') },
    { path: '/library/:id', component: () => import('./views/BookDetail.vue') },
    { path: '/session/:id', component: () => import('./views/Session.vue'), meta: { focus: true } },
    { path: '/report/:id', component: () => import('./views/Report.vue') },
    { path: '/history', component: () => import('./views/History.vue') },
    { path: '/notebook', component: () => import('./views/Notebook.vue') },
    { path: '/settings', component: () => import('./views/Settings.vue') },
  ],
  scrollBehavior: () => ({ top: 0 }),
})

loadSettings()
createApp(App).use(router).mount('#app')

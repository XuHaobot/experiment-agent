import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'home',
    component: () => import('../views/ProjectDetailView.vue'),
  },
  {
    path: '/projects',
    name: 'projects',
    component: () => import('../views/ProjectDetailView.vue'),
  },
  {
    path: '/projects/:projectId',
    name: 'project-detail',
    component: () => import('../views/ProjectDetailView.vue'),
    props: true,
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/',
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router

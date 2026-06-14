import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'upload',
    component: () => import('../views/UploadView.vue'),
  },
  {
    path: '/analysis/:recordId',
    name: 'analysis',
    component: () => import('../views/AnalysisView.vue'),
    props: true,
  },
  {
    path: '/report/:recordId',
    name: 'report',
    component: () => import('../views/ReportView.vue'),
    props: true,
  },
  {
    path: '/graph/:graphFile?',
    name: 'graph',
    component: () => import('../views/GraphView.vue'),
  },
  {
    path: '/history',
    name: 'history',
    component: () => import('../views/HistoryView.vue'),
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router

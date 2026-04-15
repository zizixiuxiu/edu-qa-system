import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'Layout',
    component: () => import('../views/Layout.vue'),
    children: [
      {
        path: '',
        name: 'Dashboard',
        component: () => import('../views/Dashboard.vue'),
        meta: { title: '首页概览', icon: 'HomeFilled' }
      },
      {
        path: 'chat',
        name: 'Chat',
        component: () => import('../views/Chat.vue'),
        meta: { title: '智能问答', icon: 'ChatDotRound' }
      },
      {
        path: 'experts',
        name: 'Experts',
        component: () => import('../views/Experts.vue'),
        meta: { title: '专家池管理', icon: 'UserFilled' }
      },
      {
        path: 'knowledge',
        name: 'Knowledge',
        component: () => import('../views/Knowledge.vue'),
        meta: { title: '知识库管理', icon: 'Collection' }
      },
      {
        path: 'analytics',
        name: 'Analytics',
        component: () => import('../views/Analytics.vue'),
        meta: { title: '数据分析', icon: 'TrendCharts', hidden: true }
      },
      {
        path: 'experiments',
        name: 'Experiments',
        component: () => import('../views/Experiments.vue'),
        meta: { title: '实验控制', icon: 'Setting' }
      },
      {
        path: 'benchmark',
        name: 'Benchmark',
        component: () => import('../views/Benchmark.vue'),
        meta: { title: '基准测试', icon: 'Trophy' }
      },
      {
        path: 'training',
        name: 'Training',
        component: () => import('../views/Training.vue'),
        meta: { title: '训练任务', icon: 'Cpu' }
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router

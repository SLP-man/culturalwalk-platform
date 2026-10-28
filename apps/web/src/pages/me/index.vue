<script setup lang="ts">
// 任务卡 FE-09：用户名、简介、已发布路线 + 我的通知 + 退出登录
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import type { Schemas } from '@/api/types'

import { ApiError, api } from '@/shared/api'
import { relativeTime, shortDate } from '@/shared/format'
import { isAdmin, isLoggedIn, logout } from '@/shared/session'
import EmptyState from '@/shared/ui/EmptyState.vue'
import Skeleton from '@/shared/ui/Skeleton.vue'

import {
  EMPTY_ROUTES,
  avatarInitial,
  bioText,
  isUnread,
  notificationKindLabel,
  payloadText,
  profileStats,
  roleLabel,
  routeMeta,
} from './logic'

type User = Schemas['User']
type UserProfile = Schemas['UserProfile']
type Notification = Schemas['Notification']

const router = useRouter()

const loading = ref(false)
const needsLogin = ref(!isLoggedIn.value)
const errorText = ref('')
const actionError = ref('')
const me = ref<User | null>(null)
const profile = ref<UserProfile | null>(null)
const notifications = ref<Notification[]>([])
const markingId = ref<string | null>(null)
const loggingOut = ref(false)

const routeCards = computed(() =>
  (profile.value?.published_routes ?? []).map((route) => ({ route, meta: routeMeta(route) })),
)
const stats = computed(() => profileStats(profile.value))
const unreadCount = computed(() => notifications.value.filter(isUnread).length)
// 会话里缓存的 role 可能过期，以 /users/me 返回的为准
const showAdmin = computed(() => me.value?.role === 'admin' || isAdmin.value)

function describe(error: unknown, fallback: string): string {
  return error instanceof ApiError ? error.message : fallback
}

async function load(): Promise<void> {
  if (!isLoggedIn.value) {
    needsLogin.value = true
    return
  }
  loading.value = true
  errorText.value = ''
  try {
    const user = await api.get<User>('/users/me')
    me.value = user
    const [loadedProfile, loadedNotifications] = await Promise.all([
      api.get<UserProfile>(`/users/${user.id}/profile`),
      api.get<{ items: Notification[] }>('/notifications?limit=20'),
    ])
    profile.value = loadedProfile
    notifications.value = loadedNotifications.items ?? []
    needsLogin.value = false
  } catch (error) {
    // 令牌过期时后端回 401：退回未登录态，而不是甩一屏红字
    if (error instanceof ApiError && error.status === 401) needsLogin.value = true
    else errorText.value = describe(error, '加载失败，请稍后重试')
  } finally {
    loading.value = false
  }
}

async function markRead(item: Notification): Promise<void> {
  if (!item.id || markingId.value) return
  markingId.value = item.id
  actionError.value = ''
  try {
    const updated = await api.post<Notification>(`/notifications/${item.id}/read`)
    const index = notifications.value.findIndex((entry) => entry.id === item.id)
    if (index >= 0) notifications.value.splice(index, 1, updated)
  } catch (error) {
    actionError.value = describe(error, '标记失败，请重试')
  } finally {
    markingId.value = null
  }
}

async function handleLogout(): Promise<void> {
  loggingOut.value = true
  await logout()
  await router.push('/login')
}

onMounted(load)
</script>

<template>
  <div>
    <h2 class="page-title">我的主页</h2>

    <Skeleton v-if="loading" :lines="6" />

    <EmptyState
      v-else-if="needsLogin"
      title="登录后查看我的主页"
      hint="简介、已发布路线和审核通知都在这里"
    >
      <RouterLink class="btn small" to="/login">去登录</RouterLink>
    </EmptyState>

    <template v-else>
      <p v-if="errorText" class="error-text">{{ errorText }}</p>

      <div class="card">
        <div class="row">
          <div class="avatar" aria-hidden="true">{{ avatarInitial(me?.username) }}</div>
          <div class="who">
            <div class="row">
              <strong class="name">{{ me?.username }}</strong>
              <span class="badge">{{ roleLabel(me?.role) }}</span>
            </div>
            <p class="muted" :class="{ 'bio-empty': !me?.bio }">{{ bioText(me?.bio) }}</p>
          </div>
        </div>
        <p class="muted joined">加入于 {{ shortDate(me?.created_at) }}</p>
      </div>

      <div class="card stats">
        <div class="stat">
          <strong>{{ stats.published }}</strong>
          <span class="muted">已发布路线</span>
        </div>
        <div class="stat">
          <strong>{{ stats.comments }}</strong>
          <span class="muted">收到的评论</span>
        </div>
      </div>

      <h3 class="section-title">
        我的通知
        <span v-if="unreadCount" class="badge">{{ unreadCount }} 条未读</span>
      </h3>
      <p v-if="actionError" class="error-text">{{ actionError }}</p>
      <EmptyState v-if="!notifications.length" title="还没有通知" hint="审核结果会在这里提醒你" />
      <ul v-else class="list">
        <li
          v-for="item in notifications"
          :key="item.id"
          class="card notice"
          :class="{ unread: isUnread(item) }"
        >
          <div class="row notice-head">
            <span v-if="isUnread(item)" class="dot" aria-label="未读" />
            <strong>{{ notificationKindLabel(item.type) }}</strong>
            <span class="muted">{{ relativeTime(item.created_at) }}</span>
          </div>
          <p v-if="payloadText(item.payload, 'title')" class="notice-title">
            {{ payloadText(item.payload, 'title') }}
          </p>
          <p v-if="payloadText(item.payload, 'reason')" class="notice-reason">
            理由：{{ payloadText(item.payload, 'reason') }}
          </p>
          <button
            v-if="isUnread(item)"
            class="btn ghost small"
            type="button"
            :disabled="markingId === item.id"
            @click="markRead(item)"
          >
            {{ markingId === item.id ? '处理中…' : '标为已读' }}
          </button>
          <span v-else class="muted read-flag">已读</span>
        </li>
      </ul>

      <h3 class="section-title">已发布路线</h3>
      <EmptyState
        v-if="!routeCards.length"
        :title="EMPTY_ROUTES"
        hint="写一条路线，把走过的巷子留给别人"
      >
        <RouterLink class="btn small" to="/authoring">去创作</RouterLink>
      </EmptyState>
      <ul v-else class="list">
        <li v-for="card in routeCards" :key="card.route.id" class="card route-card">
          <RouterLink class="route-link" :to="`/routes/${card.route.id}`">
            <strong>{{ card.route.title }}</strong>
            <p class="muted">{{ card.meta.duration }} · {{ card.meta.cost }}</p>
            <p class="muted">{{ card.meta.comments }} 条评论 · {{ card.meta.favorites }} 次收藏</p>
          </RouterLink>
        </li>
      </ul>

      <RouterLink v-if="showAdmin" class="btn ghost admin-entry" to="/admin">审核队列</RouterLink>

      <button class="btn ghost logout" type="button" :disabled="loggingOut" @click="handleLogout">
        {{ loggingOut ? '退出中…' : '退出登录' }}
      </button>
    </template>
  </div>
</template>

<style scoped>
.page-title {
  font-size: 18px;
  margin: 0 0 12px;
}

.avatar {
  flex: 0 0 auto;
  width: 52px;
  height: 52px;
  border-radius: 50%;
  background: var(--brand);
  color: #fff;
  font-size: 20px;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
}

.who {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.name {
  font-size: 16px;
}

.who p {
  margin: 0;
}

.bio-empty {
  color: var(--muted);
  font-style: italic;
}

.joined {
  margin: 12px 0 0;
}

.stats {
  display: grid;
  grid-template-columns: 1fr 1fr;
  text-align: center;
}

.stat {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.stat strong {
  font-size: 20px;
  color: var(--brand);
}

.section-title .badge {
  margin-left: 6px;
  vertical-align: middle;
}

.list {
  list-style: none;
  margin: 0;
  padding: 0;
}

.notice-head {
  gap: 8px;
}

.dot {
  flex: 0 0 auto;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--brand);
}

.notice.unread {
  border-color: var(--brand);
  background: #fffaf6;
}

.notice-title,
.notice-reason {
  margin: 8px 0 0;
  font-size: 14px;
}

.notice-reason {
  color: var(--brand);
  font-size: 13px;
}

.notice .btn {
  margin-top: 10px;
}

.read-flag {
  display: inline-block;
  margin-top: 10px;
}

.route-link {
  display: block;
}

.route-link p {
  margin: 6px 0 0;
}

.admin-entry,
.logout {
  display: block;
  width: 100%;
  text-align: center;
  margin-top: 16px;
}

.logout {
  margin-bottom: 8px;
}
</style>

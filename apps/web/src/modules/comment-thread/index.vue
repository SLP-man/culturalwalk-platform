<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'

import type { Schemas } from '@/api/types'
import { ApiError, api } from '@/shared/api'
import { relativeTime } from '@/shared/format'
import { isAdmin, isLoggedIn } from '@/shared/session'
import EmptyState from '@/shared/ui/EmptyState.vue'
import Skeleton from '@/shared/ui/Skeleton.vue'

import { sortComments } from './logic'

type Comment = Schemas['Comment']

const props = defineProps<{ routeId: string }>()

const items = ref<Comment[]>([])
const loading = ref(true)
const loadError = ref('')
const body = ref('')
const posting = ref(false)
const formError = ref('')
const pinningId = ref('')

// 置顶是编辑动作，普通用户看不到按钮（真实接口会再校验一次）
const canPin = computed(() => isAdmin.value)

async function load(): Promise<void> {
  if (!props.routeId) {
    loading.value = false
    return
  }
  loading.value = true
  loadError.value = ''
  try {
    const res = await api.get<{ items?: Comment[] }>(
      '/routes/' + encodeURIComponent(props.routeId) + '/comments',
    )
    items.value = sortComments(res.items ?? [])
  } catch (error) {
    items.value = []
    loadError.value = error instanceof ApiError ? error.message : '评论加载失败'
  } finally {
    loading.value = false
  }
}

onMounted(load)
watch(() => props.routeId, load)

async function submit(): Promise<void> {
  formError.value = ''
  const text = body.value.trim()
  if (!text) {
    formError.value = '评论不能为空'
    return
  }
  posting.value = true
  try {
    await api.post<Comment>('/routes/' + encodeURIComponent(props.routeId) + '/comments', {
      body: text,
    })
    body.value = ''
    await load()
  } catch (error) {
    formError.value = error instanceof ApiError ? error.message : '发表失败，稍后再试'
  } finally {
    posting.value = false
  }
}

async function pin(id: string): Promise<void> {
  pinningId.value = id
  formError.value = ''
  try {
    await api.post<Comment>('/comments/' + encodeURIComponent(id) + '/pin')
    await load()
  } catch (error) {
    formError.value = error instanceof ApiError ? error.message : '置顶失败'
  } finally {
    pinningId.value = ''
  }
}
</script>

<template>
  <div class="card comment-thread">
    <div v-if="loading" class="stack">
      <Skeleton :lines="2" />
      <Skeleton :lines="2" />
    </div>

    <EmptyState v-else-if="loadError" title="评论加载失败" :hint="loadError" />

    <template v-else>
      <p v-if="!items.length" class="muted no-comment">还没有评论，来写第一条。</p>
      <ul v-else class="comment-list">
        <li v-for="comment in items" :key="comment.id" class="comment">
          <div class="row head">
            <strong class="author">{{ comment.author?.username ?? '匿名用户' }}</strong>
            <span class="badge pinned" v-if="comment.pinned">置顶</span>
            <span class="muted time">{{ relativeTime(comment.created_at) }}</span>
          </div>
          <p class="body">{{ comment.body }}</p>
          <button
            v-if="canPin && !comment.pinned"
            class="btn ghost small"
            type="button"
            :disabled="pinningId === comment.id"
            @click="pin(comment.id)"
          >
            置顶
          </button>
        </li>
      </ul>
    </template>

    <form v-if="isLoggedIn" class="form" @submit.prevent="submit">
      <label class="field">
        <span class="label">写评论</span>
        <textarea v-model="body" class="textarea" placeholder="路况、门票、讲解时间都可以写" />
      </label>
      <p v-if="formError" class="error-text">{{ formError }}</p>
      <button class="btn small" type="submit" :disabled="posting">
        {{ posting ? '发表中…' : '发表评论' }}
      </button>
    </form>
    <p v-else class="muted login-hint">
      <RouterLink class="link" to="/login">登录</RouterLink>
      后可以发表评论。
    </p>
  </div>
</template>

<style scoped>
.comment-list {
  list-style: none;
  margin: 0 0 12px;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.comment {
  border-bottom: 1px solid var(--line);
  padding-bottom: 10px;
}

.comment:last-child {
  border-bottom: none;
}

.head {
  flex-wrap: wrap;
  gap: 8px;
}

.author {
  font-size: 14px;
}

.time {
  font-size: 12px;
}

.pinned {
  color: #fff;
  background: var(--brand);
}

.body {
  margin: 6px 0;
  line-height: 1.6;
  white-space: pre-wrap;
}

.no-comment {
  margin: 0 0 12px;
}

.form {
  border-top: 1px solid var(--line);
  padding-top: 12px;
}

.login-hint {
  margin: 0;
}

.link {
  color: var(--brand);
  text-decoration: underline;
}
</style>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute } from 'vue-router'

import type { Schemas } from '@/api/types'
import CommentThread from '@/modules/comment-thread/index.vue'
import { ApiError, api } from '@/shared/api'
import {
  channelLabel,
  confidenceLabel,
  durationLabel,
  moneyRange,
  transportLabel,
} from '@/shared/format'
import { isLoggedIn } from '@/shared/session'
import EmptyState from '@/shared/ui/EmptyState.vue'
import Skeleton from '@/shared/ui/Skeleton.vue'

import RouteMap from './RouteMap.vue'
import {
  amapMarkerUrl,
  buildMapPins,
  confidenceTone,
  dayLabel,
  startTimeLabel,
} from './logic'

type RouteDetail = Schemas['RouteDetail']
type RouteItem = NonNullable<NonNullable<RouteDetail['days']>[number]['items']>[number]

const route = useRoute()

const routeId = computed(() => {
  const raw = route.params.id
  return Array.isArray(raw) ? (raw[0] ?? '') : String(raw ?? '')
})

const detail = ref<RouteDetail | null>(null)
const loading = ref(true)
const loadError = ref('')
const notFound = ref(false)
const favoriteBusy = ref(false)
const favoriteHint = ref('')

async function load(): Promise<void> {
  const id = routeId.value
  loading.value = true
  loadError.value = ''
  notFound.value = false
  favoriteHint.value = ''
  try {
    detail.value = await api.get<RouteDetail>('/routes/' + encodeURIComponent(id))
  } catch (error) {
    detail.value = null
    notFound.value = error instanceof ApiError && error.status === 404
    loadError.value = error instanceof ApiError ? error.message : '网络异常，稍后再试'
  } finally {
    loading.value = false
  }
}

onMounted(load)
watch(routeId, load)

const days = computed(() => detail.value?.days ?? [])
const allItems = computed<RouteItem[]>(() => days.value.flatMap((day) => day.items ?? []))
const mapPins = computed(() => buildMapPins(allItems.value))
const errorTitle = computed(() => (notFound.value ? '这条路线不存在或已下架' : '路线加载失败'))

async function toggleFavorite(): Promise<void> {
  if (!detail.value || favoriteBusy.value) return
  if (!isLoggedIn.value) {
    favoriteHint.value = '登录后才能收藏'
    return
  }
  favoriteBusy.value = true
  favoriteHint.value = ''
  try {
    const res = await api.post<{ is_favorited: boolean }>(
      '/routes/' + encodeURIComponent(routeId.value) + '/favorite',
    )
    detail.value.is_favorited = res.is_favorited
  } catch (error) {
    favoriteHint.value = error instanceof ApiError ? error.message : '收藏失败，稍后再试'
  } finally {
    favoriteBusy.value = false
  }
}
</script>

<template>
  <div class="route-detail">
    <div v-if="loading" class="stack">
      <div class="card"><Skeleton :lines="3" height="20px" /></div>
      <div class="card"><Skeleton :lines="5" /></div>
    </div>

    <div v-else-if="loadError" class="card">
      <EmptyState :title="errorTitle" :hint="loadError">
        <RouterLink class="btn small back" to="/">返回路线列表</RouterLink>
      </EmptyState>
    </div>

    <template v-else-if="detail">
      <header class="card">
        <div class="row head">
          <h2 class="title">{{ detail.title }}</h2>
          <span class="badge">{{ channelLabel(detail.channel) }}</span>
        </div>
        <p v-if="detail.summary" class="summary">{{ detail.summary }}</p>
        <p class="muted meta">
          <span>{{ detail.author?.username ?? '匿名作者' }}</span>
          <span>·</span>
          <span>{{ durationLabel(detail.duration_minutes) }}</span>
          <span>·</span>
          <span>{{ moneyRange(detail.cost?.min_total, detail.cost?.max_total) }}</span>
          <span>·</span>
          <span>{{ detail.comment_count ?? 0 }} 条评论</span>
        </p>
        <div v-if="detail.theme_tags?.length" class="chips">
          <RouterLink
            v-for="tag in detail.theme_tags"
            :key="tag"
            class="chip"
            :to="{ path: '/', query: { theme: tag } }"
          >
            {{ tag }}
          </RouterLink>
        </div>
        <div class="row actions">
          <button class="btn small" type="button" :disabled="favoriteBusy" @click="toggleFavorite">
            {{ detail.is_favorited ? '已收藏' : '收藏' }}
          </button>
          <RouterLink v-if="!isLoggedIn" class="muted" to="/login">登录后收藏</RouterLink>
          <span v-if="favoriteHint" class="error-text">{{ favoriteHint }}</span>
        </div>
      </header>

      <h3 class="section-title">点位示意</h3>
      <div class="card">
        <RouteMap v-if="mapPins.length" :pins="mapPins" />
        <p v-else class="muted">这条路线还没有带坐标的节点。</p>
      </div>

      <h3 class="section-title">路线节点</h3>
      <p v-if="!days.length" class="muted">这条路线还没有排节点。</p>
      <div v-for="day in days" :key="day.day_index ?? 0" class="card">
        <p class="day-head">
          {{ dayLabel(day.day_index) }}
          <span class="muted">· {{ day.items?.length ?? 0 }} 个点位</span>
        </p>
        <ol class="timeline">
          <li v-for="(item, index) in day.items ?? []" :key="(item.place?.id ?? 'item') + '-' + index" class="node">
            <div class="node-head">
              <span class="seq">{{ item.position ?? index + 1 }}</span>
              <span class="time mono">{{ startTimeLabel(item.start_time) }}</span>
              <span class="badge" :class="'tone-' + confidenceTone(item.confidence)">
                {{ confidenceLabel(item.confidence) }}
              </span>
            </div>

            <p class="place">
              <strong>{{ item.place?.name ?? '未命名点位' }}</strong>
              <span v-if="item.place?.district" class="muted"> · {{ item.place?.district }}</span>
            </p>

            <p class="muted facts-line">
              <span>停留 {{ durationLabel(item.stay_minutes) }}</span>
              <span>{{ transportLabel(item.transport) }}</span>
              <span>{{ moneyRange(item.price_min, item.price_max) }}</span>
            </p>

            <details v-if="item.place" class="sources">
              <summary>文化说明与来源（{{ item.place?.facts?.length ?? 0 }} 条）</summary>
              <p v-if="item.place?.summary" class="muted place-summary">{{ item.place?.summary }}</p>
              <ul v-if="item.place?.facts?.length" class="fact-list">
                <li v-for="fact in item.place.facts" :key="fact.id">
                  <p class="claim">
                    {{ fact.claim }}
                    <span class="badge" :class="'tone-' + confidenceTone(fact.confidence)">
                      {{ confidenceLabel(fact.confidence) }}
                    </span>
                  </p>
                  <ul v-if="fact.sources?.length" class="source-list">
                    <li v-for="(source, sourceIndex) in fact.sources" :key="sourceIndex">
                      <a v-if="source.url" :href="source.url" target="_blank" rel="noreferrer">
                        {{ source.title ?? source.url }}
                      </a>
                      <span v-else>{{ source.title ?? '未命名来源' }}</span>
                      <span v-if="source.publisher" class="muted"> · {{ source.publisher }}</span>
                    </li>
                  </ul>
                  <p v-else class="muted no-source">暂无来源</p>
                </li>
              </ul>
              <p v-else class="muted no-source">暂无来源</p>
            </details>

            <a
              v-if="item.place"
              class="btn ghost small nav"
              :href="amapMarkerUrl(item.place.name, item.place.lat, item.place.lon)"
              target="_blank"
              rel="noreferrer"
            >
              在地图里打开
            </a>
          </li>
        </ol>
      </div>

      <h3 class="section-title">评论</h3>
      <CommentThread :route-id="routeId" />
    </template>
  </div>
</template>

<style scoped>
.head {
  flex-wrap: wrap;
  gap: 8px;
}

.title {
  margin: 0;
  font-size: 20px;
  line-height: 1.35;
}

.summary {
  margin: 8px 0;
  line-height: 1.6;
}

.meta {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin: 0 0 10px;
}

.actions {
  margin-top: 10px;
  flex-wrap: wrap;
}

.back {
  margin-top: 10px;
}

.day-head {
  margin: 0 0 10px;
  font-weight: 600;
}

.timeline {
  list-style: none;
  margin: 0;
  padding: 0;
  border-left: 2px solid var(--line);
}

.node {
  position: relative;
  padding: 0 0 16px 16px;
}

.node:last-child {
  padding-bottom: 0;
}

.node::before {
  content: '';
  position: absolute;
  left: -6px;
  top: 6px;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--brand);
}

.node-head {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}

.seq {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 22px;
  height: 22px;
  padding: 0 6px;
  border-radius: 999px;
  background: var(--brand);
  color: #fff;
  font-size: 12px;
  font-weight: 600;
}

.time {
  color: var(--muted);
}

.place {
  margin: 6px 0 2px;
  font-size: 15px;
}

.facts-line {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin: 0 0 6px;
}

.tone-ok {
  color: #1b7a3d;
  background: #e6f4ea;
}

.tone-warn {
  color: #8a5a00;
  background: #fdf1d8;
}

.tone-dim {
  color: var(--muted);
  background: #f1ece5;
}

.sources {
  margin: 6px 0;
  font-size: 13px;
}

.sources summary {
  cursor: pointer;
  color: var(--brand);
}

.place-summary {
  margin: 8px 0 6px;
  line-height: 1.6;
}

.fact-list,
.source-list {
  margin: 6px 0;
  padding-left: 18px;
  line-height: 1.6;
}

.claim {
  margin: 0 0 4px;
}

.no-source {
  margin: 4px 0;
}

.nav {
  margin-top: 4px;
}
</style>

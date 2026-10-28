<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { api } from '@/shared/api'
import type { paths, Schemas } from '@/api/types'
import Skeleton from '@/shared/ui/Skeleton.vue'
import EmptyState from '@/shared/ui/EmptyState.vue'
import RouteCard from '@/modules/route-card/index.vue'
import {
  CHANNEL_OPTIONS,
  DURATION_OPTIONS,
  EMPTY_FILTERS,
  buildRouteQuery,
  hasActiveFilter,
  rankThemes,
} from './filters'
import type { BrowseFilters } from './filters'

/** 列表响应在契约里是内联的 200，从 paths 上取，避免手写 DTO */
type RoutePage = paths['/routes']['get']['responses'][200]['content']['application/json']

const PAGE_SIZE = 6
const SEARCH_DEBOUNCE_MS = 300

const filters = ref<BrowseFilters>({ ...EMPTY_FILTERS })
const searchInput = ref('')
const items = ref<Schemas['RouteSummary'][]>([])
const themePool = ref<string[]>([])
const nextCursor = ref<string | null>(null)
const loading = ref(true)
const loadingMore = ref(false)
const errorMessage = ref('')

const themes = computed(() => rankThemes(themePool.value, filters.value.theme))
const active = computed(() => hasActiveFilter(filters.value))

let searchTimer: ReturnType<typeof setTimeout> | null = null
/** 只认最后一次请求的结果，避免快速改筛选时旧响应把新结果覆盖掉 */
let requestSeq = 0

function stopSearchTimer(): void {
  if (searchTimer) {
    clearTimeout(searchTimer)
    searchTimer = null
  }
}

watch(searchInput, (value) => {
  stopSearchTimer()
  searchTimer = setTimeout(() => {
    searchTimer = null
    filters.value.q = value.trim()
  }, SEARCH_DEBOUNCE_MS)
})

/** 回车立即搜索，不用等防抖 */
function commitSearch(): void {
  stopSearchTimer()
  filters.value.q = searchInput.value.trim()
}

watch(filters, () => { load(true) }, { deep: true })

function rememberThemes(routes: Schemas['RouteSummary'][]): void {
  const tags: string[] = []
  for (const route of routes) {
    for (const tag of route.theme_tags ?? []) if (tag) tags.push(tag)
  }
  // 保留历史见过的标签：筛完主题后 chip 不会全部消失
  themePool.value = [...themePool.value, ...tags].slice(-500)
}

async function load(reset: boolean): Promise<void> {
  const seq = ++requestSeq
  if (reset) {
    loading.value = true
    errorMessage.value = ''
  } else {
    loadingMore.value = true
  }
  const cursor = reset ? null : nextCursor.value
  const query = buildRouteQuery(filters.value, cursor, PAGE_SIZE)
  const path = query ? '/routes?' + query : '/routes'
  try {
    const page = await api.get<RoutePage>(path)
    if (seq !== requestSeq) return
    const fresh = page.items ?? []
    items.value = reset ? fresh : [...items.value, ...fresh]
    nextCursor.value = page.next_cursor ?? null
    rememberThemes(fresh)
  } catch (error) {
    if (seq !== requestSeq) return
    errorMessage.value = error instanceof Error ? error.message : '加载失败，请重试'
    if (reset) {
      items.value = []
      nextCursor.value = null
    }
  } finally {
    if (seq === requestSeq) {
      loading.value = false
      loadingMore.value = false
    }
  }
}

function clearFilters(): void {
  stopSearchTimer()
  searchInput.value = ''
  filters.value = { ...EMPTY_FILTERS }
  nextCursor.value = null
  items.value = []
}

function toggleTheme(tag: string): void {
  filters.value.theme = filters.value.theme === tag ? '' : tag
}

function loadMore(): void {
  if (loadingMore.value || !nextCursor.value) return
  load(false)
}

function retry(): void {
  load(items.value.length === 0)
}

onMounted(() => { load(true) })
onBeforeUnmount(stopSearchTimer)
</script>

<template>
  <div>
    <h2>发现</h2>
    <p class="muted">按主题、时长与来源，找一条长沙的文化路线</p>

    <section class="card filter-bar">
      <div class="field">
        <label class="label" for="browse-q">搜索</label>
        <input
          id="browse-q"
          v-model="searchInput"
          class="input"
          type="search"
          placeholder="路线名、摘要或主题，回车立即搜索"
          @keydown.enter.prevent="commitSearch"
        />
      </div>

      <div class="field">
        <span class="label">主题</span>
        <div v-if="themes.length" class="chips">
          <button
            v-for="tag in themes"
            :key="tag"
            type="button"
            class="chip"
            :class="{ active: filters.theme === tag }"
            @click="toggleTheme(tag)"
          >
            {{ tag }}
          </button>
        </div>
        <p v-else class="muted">还没有可用的主题标签</p>
      </div>

      <div class="row selects">
        <label class="field">
          <span class="label">时长</span>
          <select v-model="filters.duration" class="select">
            <option v-for="option in DURATION_OPTIONS" :key="option.value" :value="option.value">
              {{ option.label }}
            </option>
          </select>
        </label>
        <label class="field">
          <span class="label">来源</span>
          <select v-model="filters.channel" class="select">
            <option v-for="option in CHANNEL_OPTIONS" :key="option.value" :value="option.value">
              {{ option.label }}
            </option>
          </select>
        </label>
      </div>

      <div class="row bar-foot">
        <button type="button" class="btn ghost small" :disabled="!active" @click="clearFilters">
          清空筛选
        </button>
        <span v-if="!loading" class="muted">共 {{ items.length }} 条</span>
      </div>
    </section>

    <div v-if="loading" class="stack" aria-busy="true" data-testid="browse-loading">
      <div v-for="index in PAGE_SIZE" :key="index" class="card">
        <Skeleton :lines="3" />
      </div>
    </div>

    <div v-else-if="errorMessage" class="card">
      <p class="error-text">{{ errorMessage }}</p>
      <button type="button" class="btn small" @click="retry">重试</button>
    </div>

    <EmptyState
      v-else-if="!items.length"
      title="没有符合条件的路线"
      hint="换个关键词，或清空筛选看看全部路线"
    >
      <button type="button" class="btn ghost small" @click="clearFilters">清空筛选</button>
    </EmptyState>

    <template v-else>
      <RouteCard v-for="route in items" :key="route.id" :route="route" />
      <div class="more">
        <button
          v-if="nextCursor"
          type="button"
          class="btn ghost small"
          :disabled="loadingMore"
          @click="loadMore"
        >
          {{ loadingMore ? '加载中…' : '加载更多' }}
        </button>
        <p v-else class="muted">已经到底了</p>
      </div>
    </template>
  </div>
</template>

<style scoped>
.selects {
  align-items: flex-end;
  gap: 12px;
}

.selects .field {
  flex: 1;
  margin-bottom: 0;
}

.bar-foot {
  margin-top: 12px;
  justify-content: space-between;
}

.more {
  display: flex;
  justify-content: center;
  padding: 8px 0 4px;
}
</style>

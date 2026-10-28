<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import type { Schemas } from '@/api/types'
import { channelLabel, durationLabel, moneyRange } from '@/shared/format'

const props = defineProps<{ route: Schemas['RouteSummary'] }>()

const themes = computed(() => (props.route.theme_tags ?? []).slice(0, 4))
const priceText = computed(() =>
  moneyRange(props.route.cost?.min_total, props.route.cost?.max_total),
)
</script>

<template>
  <RouterLink :to="`/routes/${route.id}`" class="card route-card">
    <div class="head">
      <h3 class="title">{{ route.title }}</h3>
      <span class="badge">{{ channelLabel(route.channel) }}</span>
    </div>

    <p v-if="route.summary" class="summary">{{ route.summary }}</p>

    <div v-if="themes.length" class="chips">
      <span v-for="tag in themes" :key="tag" class="chip">{{ tag }}</span>
    </div>

    <div class="meta muted">
      <span>{{ durationLabel(route.duration_minutes) }}</span>
      <span>{{ priceText }}</span>
      <span>{{ route.comment_count ?? 0 }} 评论</span>
      <span>{{ route.favorite_count ?? 0 }} 收藏</span>
    </div>

    <p class="author muted">by {{ route.author?.username ?? '匿名作者' }}</p>
  </RouterLink>
</template>

<style scoped>
.route-card {
  display: block;
}

.head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
}

.title {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  line-height: 1.35;
}

.summary {
  margin: 6px 0 0;
  font-size: 13px;
  line-height: 1.5;
  color: var(--muted);
  /* 摘要最多两行，超出截断 */
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.chips {
  margin-top: 8px;
}

.chip {
  cursor: default;
}

.meta {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 8px;
}

.author {
  margin: 6px 0 0;
  font-size: 12px;
}
</style>

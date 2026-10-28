<script setup lang="ts">
// 草稿状态与提交审核 · 任务卡 FE-06
import { computed, onMounted, ref } from 'vue'

import type { Schemas } from '@/api/types'
import { ApiError, api } from '@/shared/api'
import { draftStateLabel, shortDate } from '@/shared/format'
import { isLoggedIn } from '@/shared/session'
import EmptyState from '@/shared/ui/EmptyState.vue'
import Modal from '@/shared/ui/Modal.vue'
import Skeleton from '@/shared/ui/Skeleton.vue'

import {
  canSubmit,
  draftCostLabel,
  latestReviewReason,
  markSubmitted,
  nodeCountLabel,
  stateTone,
  submitButtonLabel,
  type Draft,
  type DraftState,
} from './draft-state'

type RouteDraftDetail = Schemas['RouteDraftDetail']

const drafts = ref<Draft[]>([])
const loading = ref(true)
const listError = ref('')
const successText = ref('')
const reviewReason = ref<string | null>(null)

const details = ref<Record<string, RouteDraftDetail>>({})
const detailLoading = ref<Record<string, boolean>>({})
const detailError = ref<Record<string, string>>({})
const expandedId = ref<string | null>(null)

const pendingDraft = ref<Draft | null>(null)
const submitting = ref(false)
const submitError = ref('')

const modalOpen = computed(() => pendingDraft.value !== null)

function messageOf(error: unknown): string {
  return error instanceof ApiError ? error.message : '网络开小差了，稍后再试'
}

async function loadDrafts(quiet = false): Promise<void> {
  if (!quiet) loading.value = true
  listError.value = ''
  try {
    const data = await api.get<{ items: Draft[] }>('/route-drafts')
    drafts.value = data.items ?? []
  } catch (error) {
    listError.value = messageOf(error)
  } finally {
    loading.value = false
  }
}

/** 退回理由没有独立端点，只能从通知里捞；捞不到就不展示，不能编。 */
async function loadReviewReason(): Promise<void> {
  try {
    const data = await api.get<{ items: Schemas['Notification'][] }>('/notifications')
    reviewReason.value = latestReviewReason(data.items ?? [])
  } catch {
    reviewReason.value = null
  }
}

async function toggle(draft: Draft): Promise<void> {
  if (expandedId.value === draft.id) {
    expandedId.value = null
    return
  }
  expandedId.value = draft.id
  if (details.value[draft.id] || detailLoading.value[draft.id]) return

  detailLoading.value = { ...detailLoading.value, [draft.id]: true }
  detailError.value = { ...detailError.value, [draft.id]: '' }
  try {
    const detail = await api.get<RouteDraftDetail>(`/route-drafts/${draft.id}`)
    details.value = { ...details.value, [draft.id]: detail }
  } catch (error) {
    detailError.value = { ...detailError.value, [draft.id]: messageOf(error) }
  } finally {
    detailLoading.value = { ...detailLoading.value, [draft.id]: false }
  }
}

function openConfirm(draft: Draft): void {
  pendingDraft.value = draft
  submitError.value = ''
}

function closeConfirm(): void {
  if (submitting.value) return
  pendingDraft.value = null
  submitError.value = ''
}

async function confirmSubmit(): Promise<void> {
  const draft = pendingDraft.value
  if (!draft || submitting.value) return

  submitting.value = true
  submitError.value = ''
  try {
    await api.post<Schemas['Submission']>(`/route-drafts/${draft.id}/submit`)
    drafts.value = markSubmitted(drafts.value, draft.id)
    successText.value = `「${draft.title}」已提交，正在审核中`
    pendingDraft.value = null
    await loadDrafts(true)
  } catch (error) {
    // 422 节点不足、409 DRAFT_LOCKED 都以 error.message 呈现
    submitError.value = messageOf(error)
  } finally {
    submitting.value = false
  }
}

function stateOf(draft: Draft): DraftState {
  return draft.state
}

onMounted(() => {
  if (!isLoggedIn.value) {
    loading.value = false
    return
  }
  void loadDrafts()
  void loadReviewReason()
})
</script>

<template>
  <div>
    <div class="page-head">
      <h2>我的路线</h2>
      <p class="muted">草稿状态与提交审核</p>
    </div>

    <div v-if="!isLoggedIn" class="card">
      <EmptyState title="登录后才能管理草稿" hint="草稿列表和提交审核都需要登录。">
        <RouterLink class="btn small" to="/login">去登录</RouterLink>
      </EmptyState>
    </div>

    <template v-else>
      <div v-if="successText" class="banner-success" role="status">
        <span>{{ successText }}</span>
        <button class="btn ghost small" type="button" @click="successText = ''">知道了</button>
      </div>

      <div v-if="reviewReason" class="card reason-card">
        <div class="row">
          <span class="badge state-changes">已退回</span>
          <span class="muted">审核编辑的退回理由</span>
        </div>
        <p class="reason-text">{{ reviewReason }}</p>
      </div>

      <div v-if="loading" class="stack">
        <div class="card"><Skeleton :lines="3" /></div>
        <div class="card"><Skeleton :lines="3" /></div>
      </div>

      <div v-else-if="listError && drafts.length === 0" class="card">
        <p class="error-text">{{ listError }}</p>
        <button class="btn ghost small" type="button" @click="loadDrafts()">重试</button>
      </div>

      <EmptyState
        v-else-if="drafts.length === 0"
        title="还没有草稿"
        hint="去「创作」新建一条路线，攒够 2 个节点再回来提交。"
      />

      <div v-else class="stack">
        <p v-if="listError" class="error-text">{{ listError }}</p>
        <article v-for="draft in drafts" :key="draft.id" class="card draft-card">
          <div class="draft-head">
            <h3 class="draft-title">{{ draft.title }}</h3>
            <span class="badge" :class="stateTone(stateOf(draft))">
              {{ draftStateLabel(draft.state) }}
            </span>
          </div>

          <p v-if="draft.summary" class="muted draft-summary">{{ draft.summary }}</p>
          <p class="muted">更新于 {{ shortDate(draft.updated_at) }}</p>

          <div class="row actions">
            <button
              v-if="canSubmit(stateOf(draft))"
              class="btn small"
              type="button"
              @click="openConfirm(draft)"
            >
              提交审核
            </button>
            <button v-else class="btn small" type="button" disabled>
              {{ submitButtonLabel(stateOf(draft)) }}
            </button>
            <RouterLink
              v-if="canSubmit(stateOf(draft))"
              class="btn ghost small"
              :to="`/authoring/${draft.id}`"
            >
              继续编辑
            </RouterLink>
            <button class="btn ghost small" type="button" @click="toggle(draft)">
              {{ expandedId === draft.id ? '收起' : '展开' }}
            </button>
          </div>

          <div v-if="expandedId === draft.id" class="detail">
            <Skeleton v-if="detailLoading[draft.id]" :lines="2" />
            <p v-else-if="detailError[draft.id]" class="error-text">
              {{ detailError[draft.id] }}
            </p>
            <div v-else-if="details[draft.id]" class="detail-row">
              <span>{{ nodeCountLabel(details[draft.id].nodes) }}</span>
              <span class="muted">费用区间</span>
              <strong>{{ draftCostLabel(details[draft.id].cost) }}</strong>
            </div>
          </div>
        </article>
      </div>
    </template>

    <Modal :open="modalOpen" title="提交审核" @close="closeConfirm">
      <p>提交后草稿会被锁定，审核通过前不能再修改，也不能再提交新版本。</p>
      <p class="muted">{{ pendingDraft?.title }}</p>
      <p v-if="submitError" class="error-text">{{ submitError }}</p>
      <template #footer>
        <button class="btn ghost" type="button" :disabled="submitting" @click="closeConfirm">
          再想想
        </button>
        <button class="btn" type="button" :disabled="submitting" @click="confirmSubmit">
          {{ submitting ? '提交中…' : '确认提交' }}
        </button>
      </template>
    </Modal>
  </div>
</template>

<style scoped>
.page-head {
  margin-bottom: 12px;
}

.page-head h2 {
  margin: 0 0 4px;
}

.banner-success {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 12px;
  padding: 10px 12px;
  font-size: 14px;
  color: #1f5d33;
  background: #e8f4ea;
  border: 1px solid #bfe0c8;
  border-radius: 10px;
}

.badge.state-editing {
  color: #8a4a12;
  background: #fbeee0;
}

.badge.state-reviewing {
  color: #2f4f9e;
  background: #e8eefb;
}

.badge.state-approved {
  color: #256b3f;
  background: #e5f4ea;
}

.badge.state-archived {
  color: var(--muted);
  background: #f1ece5;
}

.badge.state-changes {
  color: #8a3b12;
  background: #fdeee0;
}

.reason-card {
  border-color: #f0d6bd;
  background: #fffaf4;
}

.reason-text {
  margin: 8px 0 0;
  font-size: 14px;
  line-height: 1.6;
}

.draft-card {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.draft-head {
  display: flex;
  align-items: flex-start;
  gap: 10px;
}

.draft-title {
  flex: 1;
  margin: 0;
  font-size: 15px;
  line-height: 1.45;
}

.draft-summary {
  margin: 0;
  line-height: 1.5;
}

.actions {
  flex-wrap: wrap;
  margin-top: 2px;
}

.detail {
  padding-top: 10px;
  border-top: 1px dashed var(--line);
}

.detail-row {
  flex-wrap: wrap;
  gap: 8px;
  font-size: 14px;
}
</style>

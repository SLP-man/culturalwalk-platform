<script setup lang="ts">
// 审核队列与发布
// 任务卡：FE-08
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'

import type { Schemas } from '@/api/types'
import DiffView from '@/modules/review-queue/diff-view.vue'
import ReviewQueue from '@/modules/review-queue/index.vue'
import { snapshotText } from '@/modules/review-queue/diff'
import {
  decisionBlockedReason,
  isPendingTask,
  reviewTaskStateLabel,
  type ReviewDecision,
} from '@/modules/review-queue/state'
import { ApiError, api } from '@/shared/api'
import { reviewActionLabel } from '@/shared/format'
import { isAdmin, isLoggedIn, refreshMe } from '@/shared/session'
import EmptyState from '@/shared/ui/EmptyState.vue'
import Modal from '@/shared/ui/Modal.vue'
import Skeleton from '@/shared/ui/Skeleton.vue'

type ReviewTask = Schemas['ReviewTask']
type SubmissionDetail = Schemas['SubmissionDetail']

const tasks = ref<ReviewTask[]>([])
const loading = ref(true)
const listError = ref('')
const busyId = ref<string | null>(null)
const notice = ref('')

const activeTask = ref<ReviewTask | null>(null)
const submission = ref<SubmissionDetail | null>(null)
const detailLoading = ref(false)
const detailError = ref('')

const modalAction = ref<ReviewDecision | null>(null)
const note = ref('')
const actionError = ref('')
const submitting = ref(false)

const pendingTasks = computed(() => tasks.value.filter((task) => isPendingTask(task)))
const doneTasks = computed(() => tasks.value.filter((task) => !isPendingTask(task)))

const submissionTitle = computed(() => snapshotText(submission.value?.snapshot, 'title') || '未命名路线')
const authorName = computed(() => submission.value?.author?.username ?? '未知作者')
const previousContent = computed(() => snapshotText(submission.value?.previous_snapshot, 'content'))
const currentContent = computed(() => snapshotText(submission.value?.snapshot, 'content'))
const noteError = computed(() => decisionBlockedReason(modalAction.value, note.value))

function errorMessage(error: unknown): string {
  return error instanceof ApiError ? error.message : '操作失败，请稍后重试'
}

function upsert(task: ReviewTask): void {
  const index = tasks.value.findIndex((item) => item.id === task.id)
  if (index >= 0) tasks.value[index] = { ...tasks.value[index], ...task }
  else tasks.value = [task, ...tasks.value]
}

async function loadTasks(): Promise<void> {
  if (!isAdmin.value) {
    loading.value = false
    return
  }
  loading.value = true
  listError.value = ''
  try {
    const data = await api.get<{ items: ReviewTask[] }>('/review/tasks')
    tasks.value = data.items ?? []
  } catch (error) {
    listError.value = errorMessage(error)
  } finally {
    loading.value = false
  }
}

async function claim(taskId: string): Promise<void> {
  busyId.value = taskId
  listError.value = ''
  try {
    const claimed = await api.post<ReviewTask>('/review/tasks/' + taskId + '/claim')
    upsert(claimed)
    if (activeTask.value?.id === taskId) activeTask.value = { ...activeTask.value, ...claimed }
    notice.value = '已领取任务 ' + taskId
  } catch (error) {
    listError.value = errorMessage(error)
  } finally {
    busyId.value = null
  }
}

async function selectTask(task: ReviewTask): Promise<void> {
  activeTask.value = task
  submission.value = null
  detailError.value = ''
  notice.value = ''
  const submissionId = task.submission_id
  if (!submissionId) {
    detailError.value = '该任务没有关联的提交'
    return
  }
  detailLoading.value = true
  try {
    submission.value = await api.get<SubmissionDetail>('/submissions/' + submissionId)
  } catch (error) {
    detailError.value = errorMessage(error)
  } finally {
    detailLoading.value = false
  }
}

function openModal(action: ReviewDecision): void {
  modalAction.value = action
  note.value = ''
  actionError.value = ''
}

function closeModal(): void {
  if (submitting.value) return
  modalAction.value = null
  note.value = ''
  actionError.value = ''
}

async function submitDecision(): Promise<void> {
  const task = activeTask.value
  const action = modalAction.value
  if (!task?.id || !action) return
  if (noteError.value) {
    actionError.value = noteError.value
    return
  }
  submitting.value = true
  actionError.value = ''
  try {
    const decided = await api.post<ReviewTask>('/review/tasks/' + task.id + '/decision', {
      action,
      note: note.value.trim(),
    })
    // 后端返回的任务已 COMPLETED；再兜一层，保证它一定从待审列表消失
    upsert({ ...task, ...decided, state: 'COMPLETED', completed_action: action })
    notice.value = '已' + reviewActionLabel(action) + '，任务 ' + task.id + ' 已完成'
    modalAction.value = null
    note.value = ''
    activeTask.value = null
    submission.value = null
  } catch (error) {
    actionError.value = errorMessage(error)
  } finally {
    submitting.value = false
  }
}

onMounted(async () => {
  await refreshMe()
  await loadTasks()
})
</script>

<template>
  <div>
    <h2>审核后台</h2>
    <p class="muted">领取待审任务，对照上一版做通过 / 退回</p>

    <EmptyState v-if="!isLoggedIn" title="请先登录" hint="审核后台需要登录后才能使用">
      <RouterLink class="btn small" to="/login">去登录</RouterLink>
    </EmptyState>

    <EmptyState v-else-if="!isAdmin" title="需要审核权限" hint="当前账号不是审核编辑，换一个身份再试">
      <RouterLink class="btn small" to="/login">用审核编辑身份登录</RouterLink>
    </EmptyState>

    <template v-else>
      <p v-if="notice" class="ok-banner">{{ notice }}</p>
      <p v-if="listError" class="error-text">{{ listError }}</p>

      <Skeleton v-if="loading" :lines="4" />

      <template v-else>
        <div class="section-title">待审任务（{{ pendingTasks.length }}）</div>
        <EmptyState
          v-if="!pendingTasks.length"
          title="暂无待审任务"
          hint="用户提交后，任务会出现在这里"
        />
        <ReviewQueue
          v-else
          :tasks="pendingTasks"
          :active-id="activeTask?.id ?? null"
          :busy-id="busyId"
          @select="selectTask"
          @claim="claim"
        />

        <template v-if="activeTask">
          <div class="section-title">版本对照 · {{ submissionTitle }}</div>
          <div class="card">
            <p class="muted">
              作者 {{ authorName }} · 任务 <span class="mono">{{ activeTask.id }}</span> · 状态
              {{ reviewTaskStateLabel(activeTask.state) }}
            </p>
            <Skeleton v-if="detailLoading" :lines="6" />
            <p v-else-if="detailError" class="error-text">{{ detailError }}</p>
            <DiffView v-else :previous="previousContent" :current="currentContent" />
          </div>
          <div v-if="!detailLoading && !detailError" class="row actions">
            <button class="btn small" type="button" @click="openModal('approve')">通过</button>
            <button class="btn ghost small" type="button" @click="openModal('request_changes')">
              退回修改
            </button>
          </div>
        </template>

        <div class="section-title">最近处理</div>
        <EmptyState v-if="!doneTasks.length" title="还没有处理记录" />
        <ReviewQueue
          v-else
          :tasks="doneTasks"
          :active-id="activeTask?.id ?? null"
          @select="selectTask"
        />
      </template>
    </template>

    <Modal :open="modalAction === 'approve'" title="确认通过" @close="closeModal">
      <p class="muted">通过后这次提交进入发布流程，备注可以先留空。</p>
      <label class="field">
        <span class="label">备注（可空）</span>
        <textarea v-model="note" class="textarea" placeholder="例如：内容无误，可以发布" />
      </label>
      <p v-if="actionError" class="error-text">{{ actionError }}</p>
      <template #footer>
        <button class="btn ghost small" type="button" @click="closeModal">取消</button>
        <button class="btn small" type="button" :disabled="submitting" @click="submitDecision">
          {{ submitting ? '提交中…' : '确认通过' }}
        </button>
      </template>
    </Modal>

    <Modal :open="modalAction === 'request_changes'" title="退回修改" @close="closeModal">
      <label class="field">
        <span class="label">退回理由（必填）</span>
        <textarea v-model="note" class="textarea" placeholder="写清楚要改什么，作者会收到通知" />
      </label>
      <p v-if="noteError" class="error-text">{{ noteError }}</p>
      <p v-if="actionError" class="error-text">{{ actionError }}</p>
      <template #footer>
        <button class="btn ghost small" type="button" @click="closeModal">取消</button>
        <button
          class="btn small"
          type="button"
          :disabled="!!noteError || submitting"
          @click="submitDecision"
        >
          {{ submitting ? '提交中…' : '确认退回' }}
        </button>
      </template>
    </Modal>
  </div>
</template>

<style scoped>
.ok-banner {
  margin: 0 0 12px;
  padding: 8px 12px;
  border-radius: 10px;
  background: #e6f5ea;
  color: #14622a;
  font-size: 13px;
}

.actions {
  margin: 4px 0 12px;
}
</style>

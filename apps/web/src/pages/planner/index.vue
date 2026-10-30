<script setup lang="ts">
// 输入条件 → 生成 → 转草稿
// 任务卡：FE-07
import { computed, onBeforeUnmount, ref } from 'vue'
import { RouterLink } from 'vue-router'

import type { PlanDetail, PlanInput, RouteDraftDetail } from '@/api/types'
import { ApiError, api } from '@/shared/api'
import { confidenceLabel, durationLabel, moneyRange, transportLabel } from '@/shared/format'
import { isLoggedIn } from '@/shared/session'
import EmptyState from '@/shared/ui/EmptyState.vue'

import PlannerForm from '@/modules/planner-form/index.vue'
import {
  CITY_OPTIONS,
  defaultForm,
  stepState,
  type PlannerForm as PlannerFormState,
} from '@/modules/planner-form/plan-form'

type PlanDay = NonNullable<PlanDetail['days_plan']>[number]

const PLAN_STEPS: { agent: string; label: string }[] = [
  { agent: 'researcher', label: '查资料' },
  { agent: 'planner', label: '排行程' },
  { agent: 'critic', label: '挑问题' },
  { agent: 'verifier', label: '核价格' },
]

const STEP_INTERVAL_MS = 700
const POLL_INTERVAL_MS = 1000
const POLL_MAX_ATTEMPTS = 20

const form = ref<PlannerFormState>(defaultForm())
const phase = ref<'form' | 'loading' | 'result'>('form')
const errorMessage = ref('')
const errorStatus = ref(0)
const lastPayload = ref<PlanInput | null>(null)
const plan = ref<PlanDetail | null>(null)
const revealed = ref(0)

const converting = ref(false)
const draftError = ref('')
const draftId = ref('')
const draftTitle = ref('')

let stepTimer: ReturnType<typeof setInterval> | null = null

const visibleSteps = computed(() =>
  PLAN_STEPS.slice(0, revealed.value).map((step, index) => ({
    ...step,
    state: stepState(index, revealed.value),
  })),
)

const days = computed<PlanDay[]>(() => {
  const planDays = plan.value?.days_plan ?? []
  return planDays.map((day) => ({
    day_index: day.day_index,
    items: [...(day.items ?? [])].sort((a, b) => (a.order ?? 0) - (b.order ?? 0)),
  }))
})

const costText = computed(() => moneyRange(plan.value?.cost?.min_total, plan.value?.cost?.max_total))
const unknownCount = computed(() => plan.value?.cost?.unknown_count ?? 0)
const cityText = computed(
  () => CITY_OPTIONS.find((city) => city.value === plan.value?.city)?.label ?? plan.value?.city ?? '',
)

function stopSteps(): void {
  if (stepTimer !== null) {
    clearInterval(stepTimer)
    stepTimer = null
  }
}

function startSteps(): void {
  stopSteps()
  revealed.value = 1
  stepTimer = setInterval(() => {
    if (revealed.value < PLAN_STEPS.length) revealed.value += 1
    else stopSteps()
  }, STEP_INTERVAL_MS)
}

function describeError(error: unknown): string {
  if (error instanceof ApiError) return error.message
  return '生成失败，请稍后再试'
}

function agentLabel(agent: string | undefined): string {
  return PLAN_STEPS.find((step) => step.agent === agent)?.label ?? agent ?? ''
}

function seconds(durationMs: number | null | undefined): string {
  if (durationMs == null) return ''
  return (durationMs / 1000).toFixed(1) + 's'
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => {
    setTimeout(resolve, ms)
  })
}

/** 契约里 POST 可能先返回 GENERATING，等到 READY 才能展示日计划 */
async function waitUntilReady(created: PlanDetail): Promise<PlanDetail> {
  let current = created
  for (let attempt = 0; attempt < POLL_MAX_ATTEMPTS; attempt += 1) {
    if (current.state === 'READY' || current.state === 'FAILED') return current
    await sleep(POLL_INTERVAL_MS)
    current = await api.get<PlanDetail>(`/plans/${created.id}`)
  }
  return current
}

/** mock 不到 1 秒就返回，四步进度会一闪而过；至少让四步都露个面再切结果 */
async function holdStepReveal(startedAtMs: number): Promise<void> {
  const minVisible = STEP_INTERVAL_MS * (PLAN_STEPS.length - 1)
  const rest = minVisible - (Date.now() - startedAtMs)
  if (rest > 0) await sleep(rest)
}

async function startPlan(payload: PlanInput): Promise<void> {
  errorMessage.value = ''
  errorStatus.value = 0
  draftError.value = ''
  draftId.value = ''
  draftTitle.value = ''
  plan.value = null
  lastPayload.value = payload

  if (!isLoggedIn.value) {
    errorMessage.value = '登录后才能生成行程'
    errorStatus.value = 401
    return
  }

  phase.value = 'loading'
  const startedAt = Date.now()
  startSteps()
  try {
    const created = await api.post<PlanDetail>('/plans', payload)
    const ready = await waitUntilReady(created)
    await holdStepReveal(startedAt)
    if (ready.state === 'FAILED') {
      throw new ApiError(502, ready.error_code ?? 'PLAN_FAILED', '行程生成失败，请调整条件后重试')
    }
    plan.value = ready
    revealed.value = PLAN_STEPS.length
    stopSteps()
    phase.value = 'result'
  } catch (error) {
    stopSteps()
    revealed.value = 0
    phase.value = 'form'
    errorStatus.value = error instanceof ApiError ? error.status : 0
    errorMessage.value = describeError(error)
  }
}

function retry(): void {
  if (lastPayload.value) void startPlan(lastPayload.value)
}

async function convertToDraft(): Promise<void> {
  if (!plan.value || converting.value) return
  converting.value = true
  draftError.value = ''
  try {
    const draft = await api.post<RouteDraftDetail>(`/plans/${plan.value.id}/to-draft`)
    draftId.value = draft.id
    draftTitle.value = draft.title
  } catch (error) {
    draftError.value = describeError(error)
  } finally {
    converting.value = false
  }
}

function backToForm(): void {
  plan.value = null
  draftId.value = ''
  draftTitle.value = ''
  draftError.value = ''
  errorMessage.value = ''
  errorStatus.value = 0
  phase.value = 'form'
}

onBeforeUnmount(stopSteps)
</script>

<template>
  <div>
    <h2>规划行程</h2>
    <p class="muted">填好条件，四位助手排一版行程，满意就转成自己的草稿。</p>

    <div v-if="!isLoggedIn" class="card notice">
      <p><strong>登录后才能生成行程</strong></p>
      <p class="muted">规划接口需要登录态，登录后回来即可开始。</p>
      <RouterLink class="btn small" to="/login">去登录</RouterLink>
    </div>

    <div v-if="phase === 'form'">
      <div v-if="errorMessage" class="card error-card">
        <p class="error-text" role="alert">{{ errorMessage }}</p>
        <div class="row">
          <button v-if="lastPayload" class="btn small" type="button" @click="retry">重试</button>
          <RouterLink v-if="errorStatus === 401" class="btn small ghost" to="/login">去登录</RouterLink>
        </div>
      </div>

      <PlannerForm v-model="form" @submit="startPlan" />
    </div>

    <div v-else-if="phase === 'loading'" class="card">
      <p class="section-title">助手们正在工作</p>
      <p class="muted">大约需要 10 秒，请先不要离开这个页面。</p>

      <ol class="steps">
        <li v-for="step in visibleSteps" :key="step.agent" class="step">
          <span class="dot" :class="step.state" aria-hidden="true"></span>
          <span class="step-agent mono">{{ step.agent }}</span>
          <span class="step-label">{{ step.label }}</span>
          <span class="muted">{{ step.state === 'running' ? '进行中' : '已完成' }}</span>
        </li>
      </ol>

      <button class="btn" type="button" disabled>开始规划</button>
    </div>

    <div v-else-if="phase === 'result' && plan" class="stack">
      <div class="card">
        <div class="row spread">
          <p class="section-title flush">行程结果</p>
          <span class="badge">{{ cityText }} · {{ plan.days }} 天 · {{ plan.people }} 人</span>
        </div>
        <p>费用区间：<strong>{{ costText }}</strong></p>
        <p v-if="unknownCount" class="muted">其中 {{ unknownCount }} 个点价格待核实</p>

        <div v-if="plan.steps?.length" class="chips steps-summary">
          <span v-for="step in plan.steps" :key="step.agent" class="badge">
            {{ agentLabel(step.agent) }} · {{ step.status === 'done' ? '完成' : step.status }}
            <template v-if="seconds(step.duration_ms)"> · {{ seconds(step.duration_ms) }}</template>
          </span>
        </div>

        <div class="row actions">
          <button
            class="btn"
            type="button"
            :disabled="converting || draftId !== ''"
            @click="convertToDraft"
          >
            {{ converting ? '正在转换…' : '转成我的草稿' }}
          </button>
          <button class="btn ghost small" type="button" @click="backToForm">再规划一次</button>
        </div>

        <p v-if="draftError" class="error-text" role="alert">{{ draftError }}</p>
        <p v-if="draftId" class="ok-text">
          已转成草稿{{ draftTitle ? '：' + draftTitle : '' }}，
          <RouterLink class="link" to="/authoring">去我的草稿继续编辑</RouterLink>
        </p>
      </div>

      <EmptyState
        v-if="!days.length"
        title="这次没有排出日程"
        hint="换个天数或放宽主题，再规划一次试试"
      />

      <section v-for="day in days" :key="day.day_index" class="card">
        <p class="section-title flush">第 {{ day.day_index }} 天</p>
        <EmptyState v-if="!day.items?.length" title="这一天还是空的" hint="可以回上一页调整条件" />
        <ol v-else class="items">
          <li v-for="(item, index) in day.items" :key="`${day.day_index}-${item.order ?? index}`" class="item">
            <div class="row">
              <span class="order mono">{{ item.order ?? index + 1 }}</span>
              <strong>{{ item.place?.name ?? '待定地点' }}</strong>
              <span class="badge conf" :class="'conf-' + (item.confidence ?? 'unverified')">
                {{ confidenceLabel(item.confidence) }}
              </span>
            </div>
            <p class="muted meta">
              {{ durationLabel(item.stay_minutes) }} · {{ transportLabel(item.transport) }} ·
              {{ moneyRange(item.price_min, item.price_max) }}
            </p>
            <p v-if="item.reason" class="reason">{{ item.reason }}</p>
          </li>
        </ol>
      </section>
    </div>
  </div>
</template>

<style scoped>
.notice {
  border-color: var(--brand);
}

.error-card {
  border-color: #b3261e;
}

.section-title.flush {
  margin: 0;
}

.row.spread {
  justify-content: space-between;
  align-items: baseline;
}

.row.actions {
  margin: 14px 0 6px;
  flex-wrap: wrap;
}

.steps-summary {
  margin: 10px 0;
}

.ok-text {
  color: var(--brand);
  font-size: 13px;
}

.link {
  text-decoration: underline;
}

.steps {
  list-style: none;
  margin: 0 0 14px;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.step {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 14px;
}

.step-agent {
  color: var(--muted);
  min-width: 78px;
}

.dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--line);
  flex: none;
}

.dot.running {
  background: var(--brand);
  animation: pulse 1.1s ease-in-out infinite;
}

.dot.done {
  background: var(--brand);
  opacity: 0.5;
}

@keyframes pulse {
  0%,
  100% {
    transform: scale(1);
    opacity: 1;
  }
  50% {
    transform: scale(1.4);
    opacity: 0.5;
  }
}

.items {
  list-style: none;
  margin: 10px 0 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.item {
  border-top: 1px dashed var(--line);
  padding-top: 10px;
}

.item:first-child {
  border-top: none;
  padding-top: 0;
}

.order {
  color: var(--muted);
  width: 20px;
}

.meta {
  margin: 6px 0 0;
}

.reason {
  margin: 4px 0 0;
  font-size: 13px;
  color: var(--ink);
}

.conf-verified {
  background: #e6f2e9;
  color: #2f6b40;
}

.conf-likely {
  background: #f6efe0;
  color: #7a5c1e;
}

.conf-unverified {
  background: #f7e7e5;
  color: #8c3b2e;
}
</style>

<script setup lang="ts">
// 创作页：左栏草稿列表，右栏节点编辑器。
// 排序/删除/新增只改本地数组，点「保存」才一次性 PUT 回接口。
import { computed, reactive, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'

import type { Schemas } from '@/api/types'
import { ApiError, api, request } from '@/shared/api'
import { draftStateLabel, shortDate, transportLabel } from '@/shared/format'
import { isLoggedIn } from '@/shared/session'
import EmptyState from '@/shared/ui/EmptyState.vue'
import Skeleton from '@/shared/ui/Skeleton.vue'

import {
  TRANSPORT_OPTIONS,
  buildNodePayload,
  costText,
  costUnknownHint,
  fenToYuan,
  moveNode,
  normalizeTransport,
  removeNode,
  validateNodes,
} from './draft'
import type { EditableNode } from './draft'

type Draft = Schemas['RouteDraft']
type DraftDetail = Schemas['RouteDraftDetail']
type Place = Schemas['Place']

const route = useRoute()
const router = useRouter()

const loggedIn = isLoggedIn
const authError = ref(false)

const drafts = ref<Draft[]>([])
const loadingDrafts = ref(false)
const listError = ref('')

const detail = ref<DraftDetail | null>(null)
const nodes = ref<EditableNode[]>([])
const loadingDetail = ref(false)
const detailError = ref('')
const saving = ref(false)
const saveNotice = ref('')
const savedSnapshot = ref('')

const createOpen = ref(false)
const creating = ref(false)
const createError = ref('')
const createForm = reactive({ title: '', summary: '' })

const addOpen = ref(false)
const addError = ref('')
const addForm = reactive({ placeId: '', stayMinutes: 60 })
const places = ref<Place[]>([])
let placesLoaded = false

const editable = computed(() => detail.value?.state === 'EDITING')
const dirty = computed(
  () => editable.value && savedSnapshot.value !== JSON.stringify(buildNodePayload(nodes.value)),
)

function errorText(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 401) authError.value = true
    return error.message
  }
  return '网络异常，请稍后再试'
}

function toEditable(node: NonNullable<DraftDetail['nodes']>[number]): EditableNode {
  return {
    uid: crypto.randomUUID(),
    place_id: node.place?.id ?? '',
    name: node.place?.name ?? '未命名地点',
    district: node.place?.district ?? null,
    stay_minutes: node.stay_minutes ?? 60,
    transport: normalizeTransport(node.transport),
    note: node.note ?? '',
    price_yuan: fenToYuan(node.price_min ?? node.price_max),
  }
}

function applyDetail(res: DraftDetail): void {
  detail.value = res
  nodes.value = (res.nodes ?? []).map(toEditable)
  savedSnapshot.value = JSON.stringify(buildNodePayload(nodes.value))
  addOpen.value = false
  addError.value = ''
}

async function loadDrafts(): Promise<void> {
  if (!loggedIn.value) return
  loadingDrafts.value = true
  listError.value = ''
  try {
    const res = await api.get<{ items: Draft[] }>('/route-drafts')
    drafts.value = res.items ?? []
  } catch (error) {
    listError.value = errorText(error)
  } finally {
    loadingDrafts.value = false
  }
}

async function loadDetail(id: string): Promise<void> {
  if (!loggedIn.value) return
  loadingDetail.value = true
  detailError.value = ''
  saveNotice.value = ''
  try {
    applyDetail(await api.get<DraftDetail>('/route-drafts/' + id))
  } catch (error) {
    detail.value = null
    nodes.value = []
    savedSnapshot.value = ''
    detailError.value = errorText(error)
  } finally {
    loadingDetail.value = false
  }
}

async function openDraft(id: string): Promise<void> {
  const current = typeof route.params.id === 'string' ? route.params.id : null
  if (current === id) {
    await loadDetail(id)
    return
  }
  await router.push({ name: 'authoring-edit', params: { id } })
}

function toggleCreate(): void {
  createOpen.value = !createOpen.value
  createError.value = ''
}

function closeCreate(): void {
  createOpen.value = false
  createError.value = ''
  createForm.title = ''
  createForm.summary = ''
}

async function createDraft(): Promise<void> {
  createError.value = ''
  const title = createForm.title.trim()
  if (!title) {
    createError.value = '标题必填'
    return
  }
  creating.value = true
  try {
    const created = await api.post<Draft>('/route-drafts', {
      title,
      summary: createForm.summary.trim(),
    })
    closeCreate()
    await loadDrafts()
    await openDraft(created.id)
  } catch (error) {
    createError.value = errorText(error)
  } finally {
    creating.value = false
  }
}

async function save(): Promise<void> {
  if (!detail.value || !editable.value || saving.value) return
  detailError.value = ''
  saveNotice.value = ''
  const invalid = validateNodes(nodes.value)
  if (invalid) {
    detailError.value = invalid
    return
  }
  saving.value = true
  const draftId = detail.value.id
  try {
    // shared/api 只暴露 get/post/patch/del，PUT 走同模块的 request，仍然不碰 fetch
    const res = await request<DraftDetail>('/route-drafts/' + draftId + '/nodes', {
      method: 'PUT',
      body: JSON.stringify({ nodes: buildNodePayload(nodes.value) }),
    })
    applyDetail(res)
    saveNotice.value = '已保存'
    await loadDrafts()
  } catch (error) {
    detailError.value = errorText(error)
  } finally {
    saving.value = false
  }
}

async function ensurePlaces(): Promise<void> {
  if (placesLoaded) return
  const res = await api.get<{ items: Place[] }>('/places')
  places.value = res.items ?? []
  placesLoaded = true
}

function openAddNode(): void {
  addOpen.value = true
  addError.value = ''
  void ensurePlaces().catch((error: unknown) => {
    addError.value = errorText(error)
  })
}

function addNode(): void {
  addError.value = ''
  const place = places.value.find((item) => item.id === addForm.placeId)
  if (!place) {
    addError.value = '先选一个地点'
    return
  }
  const stay = Number(addForm.stayMinutes)
  if (!Number.isFinite(stay) || stay <= 0) {
    addError.value = '停留分钟要大于 0'
    return
  }
  nodes.value.push({
    uid: crypto.randomUUID(),
    place_id: place.id,
    name: place.name,
    district: place.district ?? null,
    stay_minutes: Math.round(stay),
    transport: 'walk',
    note: '',
    price_yuan: '',
  })
  addOpen.value = false
  addForm.placeId = ''
  addForm.stayMinutes = 60
}

function move(index: number, delta: number): void {
  nodes.value = moveNode(nodes.value, index, index + delta)
}

function remove(index: number): void {
  nodes.value = removeNode(nodes.value, index)
}

watch(
  loggedIn,
  (value) => {
    if (value) {
      void loadDrafts()
      const id = typeof route.params.id === 'string' ? route.params.id : null
      if (id) void loadDetail(id)
    } else {
      drafts.value = []
      detail.value = null
      nodes.value = []
    }
  },
  { immediate: true },
)

watch(
  () => route.params.id,
  (id) => {
    if (typeof id === 'string' && id) void loadDetail(id)
    else {
      detail.value = null
      nodes.value = []
      savedSnapshot.value = ''
      saveNotice.value = ''
      detailError.value = ''
    }
  },
)
</script>

<template>
  <div class="authoring">
    <template v-if="!loggedIn || authError">
      <h2>创作路线</h2>
      <p class="muted">把你的走法写成一条可发布的路线。</p>
      <EmptyState title="请先登录" hint="登录后才能新建和保存草稿。">
        <RouterLink class="btn" to="/login">去登录</RouterLink>
      </EmptyState>
    </template>

    <template v-else>
      <div class="head">
        <div>
          <h2>创作路线</h2>
          <p class="muted">排序、加减节点都在本地改，点「保存」才写回。</p>
        </div>
        <button class="btn small" type="button" @click="toggleCreate">
          {{ createOpen ? '收起' : '新建草稿' }}
        </button>
      </div>

      <form v-if="createOpen" class="card create" @submit.prevent="createDraft">
        <div class="field">
          <label class="label" for="new-title">标题（必填）</label>
          <input
            id="new-title"
            v-model="createForm.title"
            class="input"
            maxlength="60"
            placeholder="例如：城南旧事：第一师范与白沙井"
          />
        </div>
        <div class="field">
          <label class="label" for="new-summary">摘要（选填）</label>
          <textarea
            id="new-summary"
            v-model="createForm.summary"
            class="textarea"
            rows="2"
            placeholder="一句话说清这条线讲什么"
          />
        </div>
        <p v-if="createError" class="error-text">{{ createError }}</p>
        <div class="row">
          <button class="btn" type="submit" :disabled="creating">
            {{ creating ? '创建中…' : '创建' }}
          </button>
          <button class="btn ghost small" type="button" @click="closeCreate">取消</button>
        </div>
      </form>

      <div class="columns">
        <aside class="card">
          <p class="section-title">我的草稿</p>
          <Skeleton v-if="loadingDrafts" :lines="4" />
          <p v-else-if="listError" class="error-text">{{ listError }}</p>
          <EmptyState v-else-if="!drafts.length" title="还没有草稿" hint="点右上角「新建草稿」开始。" />
          <ul v-else class="drafts">
            <li v-for="draft in drafts" :key="draft.id">
              <button
                type="button"
                class="draft"
                :class="{ active: draft.id === detail?.id }"
                @click="openDraft(draft.id)"
              >
                <span class="draft-title">{{ draft.title }}</span>
                <span class="badge">{{ draftStateLabel(draft.state) }}</span>
                <span class="muted mono">{{ shortDate(draft.updated_at) }}</span>
              </button>
            </li>
          </ul>
        </aside>

        <section class="card editor">
          <Skeleton v-if="loadingDetail" :lines="6" />
          <EmptyState v-else-if="!detail" title="从左边选一个草稿" hint="或者先新建一个。" />

          <template v-else>
            <div class="editor-head">
              <div>
                <p class="section-title">{{ detail.title }}</p>
                <p class="muted">
                  {{ draftStateLabel(detail.state) }} · 更新于 {{ shortDate(detail.updated_at) }}
                </p>
              </div>
              <span v-if="dirty" class="badge">未保存</span>
            </div>

            <p v-if="!editable" class="locked">
              {{ draftStateLabel(detail.state) }}：已提交审核，不能再改
            </p>

            <p class="cost">
              预算：<strong>{{ costText(detail.cost) }}</strong>
              <span v-if="costUnknownHint(detail.cost)" class="warn">
                {{ costUnknownHint(detail.cost) }}
              </span>
            </p>

            <EmptyState v-if="!nodes.length" title="还没有节点" hint="先「添加节点」，至少 2 个才能提交审核。" />

            <ol v-else class="nodes">
              <li v-for="(node, index) in nodes" :key="node.uid" class="node">
                <div class="node-head">
                  <span class="index mono">{{ index + 1 }}</span>
                  <strong>{{ node.name }}</strong>
                  <span v-if="node.district" class="muted">{{ node.district }}</span>
                </div>

                <div class="node-grid">
                  <label class="field">
                    <span class="label">停留（分钟）</span>
                    <input
                      v-model.number="node.stay_minutes"
                      class="input"
                      type="number"
                      min="1"
                      :disabled="!editable"
                    />
                  </label>
                  <label class="field">
                    <span class="label">交通</span>
                    <select v-model="node.transport" class="select" :disabled="!editable">
                      <option v-for="option in TRANSPORT_OPTIONS" :key="option" :value="option">
                        {{ transportLabel(option) }}
                      </option>
                    </select>
                  </label>
                  <label class="field">
                    <span class="label">门票（元）</span>
                    <input
                      v-model="node.price_yuan"
                      class="input"
                      inputmode="decimal"
                      placeholder="留空＝待核实"
                      :disabled="!editable"
                    />
                  </label>
                </div>

                <label class="field">
                  <span class="label">备注</span>
                  <input
                    v-model="node.note"
                    class="input"
                    placeholder="开放时间、排队情况…"
                    :disabled="!editable"
                  />
                </label>

                <div v-if="editable" class="row node-actions">
                  <button
                    class="btn ghost small"
                    type="button"
                    :disabled="index === 0"
                    @click="move(index, -1)"
                  >
                    上移
                  </button>
                  <button
                    class="btn ghost small"
                    type="button"
                    :disabled="index === nodes.length - 1"
                    @click="move(index, 1)"
                  >
                    下移
                  </button>
                  <button class="btn ghost small" type="button" @click="remove(index)">删除</button>
                </div>
              </li>
            </ol>

            <div v-if="editable" class="add">
              <button v-if="!addOpen" class="btn ghost small" type="button" @click="openAddNode">
                添加节点
              </button>
              <div v-else class="add-card">
                <label class="field">
                  <span class="label">地点</span>
                  <select v-model="addForm.placeId" class="select">
                    <option value="" disabled>从地点库里选</option>
                    <option v-for="place in places" :key="place.id" :value="place.id">
                      {{ place.name }}{{ place.district ? ' · ' + place.district : '' }}
                    </option>
                  </select>
                </label>
                <label class="field">
                  <span class="label">停留（分钟）</span>
                  <input v-model.number="addForm.stayMinutes" class="input" type="number" min="1" />
                </label>
                <div class="row">
                  <button class="btn small" type="button" @click="addNode">加入末尾</button>
                  <button class="btn ghost small" type="button" @click="addOpen = false">
                    取消
                  </button>
                </div>
                <p v-if="addError" class="error-text">{{ addError }}</p>
              </div>
            </div>

            <p v-if="detailError" class="error-text">{{ detailError }}</p>
            <p v-if="saveNotice" class="saved">{{ saveNotice }}</p>
            <div v-if="editable" class="row save-row">
              <button class="btn" type="button" :disabled="saving" @click="save">
                {{ saving ? '保存中…' : '保存' }}
              </button>
            </div>
          </template>
        </section>
      </div>
    </template>
  </div>
</template>

<style scoped>
.head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.create {
  margin: 12px 0;
}

.columns {
  display: grid;
  gap: 12px;
}

@media (min-width: 880px) {
  .columns {
    grid-template-columns: 280px minmax(0, 1fr);
    align-items: start;
  }
}

.drafts {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.draft {
  width: 100%;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  padding: 10px;
  text-align: left;
  background: var(--bg);
  border: 1px solid var(--line);
  border-radius: 10px;
  cursor: pointer;
  font: inherit;
  color: inherit;
}

.draft.active {
  border-color: var(--brand);
  background: #fff;
}

.draft-title {
  flex: 1 1 100%;
  font-weight: 600;
}

.editor-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.locked {
  margin: 12px 0;
  padding: 10px 12px;
  border-radius: 10px;
  border: 1px dashed var(--line);
  background: var(--bg);
  color: var(--muted);
}

.cost {
  margin: 8px 0 16px;
}

.warn {
  color: var(--brand);
}

.nodes {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.node {
  padding: 12px;
  border: 1px solid var(--line);
  border-radius: 10px;
}

.node-head {
  display: flex;
  align-items: baseline;
  gap: 8px;
  margin-bottom: 8px;
}

.index {
  width: 22px;
  height: 22px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: var(--bg);
  border: 1px solid var(--line);
  font-size: 12px;
}

.node-grid {
  display: grid;
  gap: 8px;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
}

.node-actions {
  margin-top: 8px;
}

.add {
  margin-top: 16px;
}

.add-card {
  padding: 12px;
  border: 1px dashed var(--line);
  border-radius: 10px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.saved {
  margin: 8px 0 0;
  color: var(--brand);
}

.save-row {
  margin-top: 12px;
}
</style>

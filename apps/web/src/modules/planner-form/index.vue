<script setup lang="ts">
// 可复用业务组件：规划表单（受控表单 + 校验，输出 PlanInput）
// 约定：只通过 props 接收数据、通过 emit 抛事件，不自己发请求
import { ref } from 'vue'

import type { PlanInput } from '@/api/types'

import {
  CITY_OPTIONS,
  DAYS_MAX,
  DAYS_MIN,
  DAY_PART_OPTIONS,
  PACE_OPTIONS,
  PEOPLE_MAX,
  PEOPLE_MIN,
  THEME_OPTIONS,
  TRANSPORT_OPTIONS,
  toggleValue,
  toPlanInput,
  validatePlanForm,
  type PlanDayPart,
  type PlannerForm,
  type PlanTransport,
} from './plan-form'

const props = withDefaults(
  defineProps<{
    modelValue: PlannerForm
    disabled?: boolean
  }>(),
  { disabled: false },
)

const emit = defineEmits<{
  'update:modelValue': [value: PlannerForm]
  submit: [payload: PlanInput]
}>()

const errorText = ref('')

function patch(next: Partial<PlannerForm>): void {
  errorText.value = ''
  emit('update:modelValue', { ...props.modelValue, ...next })
}

function readNumber(event: Event): number {
  const raw = Number((event.target as HTMLInputElement).value)
  return Number.isFinite(raw) ? raw : 0
}

function toggleDayPart(value: PlanDayPart): void {
  patch({ dayParts: toggleValue(props.modelValue.dayParts, value) })
}

function toggleTheme(value: string): void {
  patch({ themes: toggleValue(props.modelValue.themes, value) })
}

function toggleTransport(value: PlanTransport): void {
  patch({ transport: toggleValue(props.modelValue.transport, value) })
}

function onSubmit(): void {
  const message = validatePlanForm(props.modelValue)
  if (message) {
    errorText.value = message
    return
  }
  errorText.value = ''
  emit('submit', toPlanInput(props.modelValue))
}
</script>

<template>
  <form class="card" novalidate @submit.prevent="onSubmit">
    <div class="grid">
      <div class="field">
        <label class="label" for="planner-city">城市</label>
        <select
          id="planner-city"
          class="select"
          :value="modelValue.city"
          :disabled="disabled"
          @change="patch({ city: ($event.target as HTMLSelectElement).value })"
        >
          <option v-for="city in CITY_OPTIONS" :key="city.value" :value="city.value">
            {{ city.label }}
          </option>
        </select>
      </div>

      <div class="field">
        <label class="label" for="planner-days">天数（{{ DAYS_MIN }}-{{ DAYS_MAX }}）</label>
        <input
          id="planner-days"
          class="input"
          type="number"
          :min="DAYS_MIN"
          :max="DAYS_MAX"
          step="1"
          :value="modelValue.days"
          :disabled="disabled"
          @input="patch({ days: readNumber($event) })"
        />
      </div>

      <div class="field">
        <label class="label" for="planner-people">人数（{{ PEOPLE_MIN }}-{{ PEOPLE_MAX }}）</label>
        <input
          id="planner-people"
          class="input"
          type="number"
          :min="PEOPLE_MIN"
          :max="PEOPLE_MAX"
          step="1"
          :value="modelValue.people"
          :disabled="disabled"
          @input="patch({ people: readNumber($event) })"
        />
      </div>

      <div class="field">
        <label class="label" for="planner-budget">总预算（元）</label>
        <input
          id="planner-budget"
          class="input"
          type="number"
          min="1"
          step="1"
          :value="modelValue.budgetYuan"
          :disabled="disabled"
          @input="patch({ budgetYuan: readNumber($event) })"
        />
        <span class="muted">全队总额，提交时按分计算</span>
      </div>
    </div>

    <label class="checkbox">
      <input
        type="checkbox"
        :checked="modelValue.includeLodging"
        :disabled="disabled"
        @change="patch({ includeLodging: ($event.target as HTMLInputElement).checked })"
      />
      <span>包含住宿</span>
    </label>

    <div class="field">
      <span class="label">出行时段</span>
      <div class="chips">
        <button
          v-for="part in DAY_PART_OPTIONS"
          :key="part.value"
          type="button"
          class="chip"
          :class="{ active: modelValue.dayParts.includes(part.value) }"
          :disabled="disabled"
          :aria-pressed="modelValue.dayParts.includes(part.value)"
          @click="toggleDayPart(part.value)"
        >
          {{ part.label }}
        </button>
      </div>
    </div>

    <div class="field">
      <span class="label">主题（可多选，不选则不限制）</span>
      <div class="chips">
        <button
          v-for="theme in THEME_OPTIONS"
          :key="theme"
          type="button"
          class="chip"
          :class="{ active: modelValue.themes.includes(theme) }"
          :disabled="disabled"
          :aria-pressed="modelValue.themes.includes(theme)"
          @click="toggleTheme(theme)"
        >
          {{ theme }}
        </button>
      </div>
    </div>

    <div class="field">
      <span class="label">交通方式（可多选）</span>
      <div class="chips">
        <button
          v-for="item in TRANSPORT_OPTIONS"
          :key="item.value"
          type="button"
          class="chip"
          :class="{ active: modelValue.transport.includes(item.value) }"
          :disabled="disabled"
          :aria-pressed="modelValue.transport.includes(item.value)"
          @click="toggleTransport(item.value)"
        >
          {{ item.label }}
        </button>
      </div>
    </div>

    <div class="field">
      <span class="label">节奏</span>
      <div class="radios">
        <label v-for="option in PACE_OPTIONS" :key="option.value" class="radio">
          <input
            type="radio"
            name="planner-pace"
            :value="option.value"
            :checked="modelValue.pace === option.value"
            :disabled="disabled"
            @change="patch({ pace: option.value })"
          />
          <span>{{ option.label }}</span>
        </label>
      </div>
    </div>

    <div class="field">
      <label class="label" for="planner-start">起点（可空）</label>
      <input
        id="planner-start"
        class="input"
        type="text"
        placeholder="例如：五一广场地铁站"
        :value="modelValue.startPoint"
        :disabled="disabled"
        @input="patch({ startPoint: ($event.target as HTMLInputElement).value })"
      />
    </div>

    <p v-if="errorText" class="error-text" role="alert">{{ errorText }}</p>

    <button class="btn" type="submit" :disabled="disabled">开始规划</button>
  </form>
</template>

<style scoped>
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 0 12px;
}

.checkbox {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
  font-size: 14px;
  cursor: pointer;
}

.radios {
  display: flex;
  flex-wrap: wrap;
  gap: 14px;
}

.radio {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  cursor: pointer;
}

.chip:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}
</style>

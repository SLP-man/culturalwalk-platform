<script setup lang="ts">
// 账号入口：登录 / 注册两个 tab，成功后回跳 ?redirect= 指定的页面。
// 任务卡：FE-04
import { computed, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { ApiError } from '@/shared/api'
import { currentUser, isLoggedIn, login, logout, register } from '@/shared/session'

import {
  DEMO_ACCOUNTS,
  authErrorText,
  redirectTarget,
  validateLogin,
  validateRegister,
} from './validation'
import type { AuthField, DemoAccount } from './validation'

const route = useRoute()
const router = useRouter()

const tab = ref<'login' | 'register'>('login')
const submitting = ref(false)
const loggingOut = ref(false)
const formError = ref('')

const form = reactive({ username: '', password: '', confirm: '' })
const fieldError = reactive<Record<AuthField, string>>({
  username: '',
  password: '',
  confirm: '',
})

const submitLabel = computed(() => {
  if (submitting.value) return tab.value === 'login' ? '登录中…' : '注册中…'
  return tab.value === 'login' ? '登录' : '注册'
})

function clearErrors(): void {
  formError.value = ''
  fieldError.username = ''
  fieldError.password = ''
  fieldError.confirm = ''
}

function switchTab(next: 'login' | 'register'): void {
  if (tab.value === next) return
  tab.value = next
  // 换 tab 就清确认密码，避免把登录密码残留成"确认密码已填"
  form.confirm = ''
  clearErrors()
}

function fillDemo(account: DemoAccount): void {
  tab.value = 'login'
  form.username = account.username
  form.password = account.password
  form.confirm = ''
  clearErrors()
}

/** 前端校验先跑：不过就不发请求，省一次 422 往返。 */
async function submit(): Promise<void> {
  if (submitting.value) return
  clearErrors()

  const problem = tab.value === 'login' ? validateLogin(form) : validateRegister(form)
  if (problem) {
    fieldError[problem.field] = problem.message
    return
  }

  submitting.value = true
  try {
    const username = form.username.trim()
    if (tab.value === 'login') await login(username, form.password)
    else await register(username, form.password)
    await router.replace(redirectTarget(route.query.redirect))
  } catch (error) {
    const known = error instanceof ApiError ? error : null
    formError.value = authErrorText(known?.code ?? null, known?.message ?? '')
  } finally {
    submitting.value = false
  }
}

async function onLogout(): Promise<void> {
  if (loggingOut.value) return
  loggingOut.value = true
  try {
    await logout()
    clearErrors()
    form.password = ''
    form.confirm = ''
  } finally {
    loggingOut.value = false
  }
}
</script>

<template>
  <section>
    <h2>登录 / 注册</h2>

    <div v-if="isLoggedIn" class="card">
      <p>你已登录为 <strong>{{ currentUser?.username }}</strong></p>
      <p class="muted">要换账号的话，先退出登录。</p>
      <div class="row">
        <button class="btn ghost small" type="button" :disabled="loggingOut" @click="onLogout">
          {{ loggingOut ? '退出中…' : '退出登录' }}
        </button>
        <RouterLink class="btn small" to="/">去发现</RouterLink>
      </div>
    </div>

    <template v-else>
      <div class="chips tabs">
        <button
          v-for="item in ([['login', '登录'], ['register', '注册']] as const)"
          :key="item[0]"
          class="chip"
          :class="{ active: tab === item[0] }"
          type="button"
          @click="switchTab(item[0])"
        >
          {{ item[1] }}
        </button>
      </div>

      <form class="card" novalidate @submit.prevent="submit">
        <div class="field">
          <label class="label" for="login-username">用户名</label>
          <input
            id="login-username"
            v-model="form.username"
            class="input"
            type="text"
            autocomplete="username"
            :aria-invalid="Boolean(fieldError.username)"
          />
          <p v-if="fieldError.username" class="error-text">{{ fieldError.username }}</p>
        </div>

        <div class="field">
          <label class="label" for="login-password">密码</label>
          <input
            id="login-password"
            v-model="form.password"
            class="input"
            type="password"
            :autocomplete="tab === 'login' ? 'current-password' : 'new-password'"
            :aria-invalid="Boolean(fieldError.password)"
          />
          <p v-if="fieldError.password" class="error-text">{{ fieldError.password }}</p>
        </div>

        <div v-if="tab === 'register'" class="field">
          <label class="label" for="login-confirm">确认密码</label>
          <input
            id="login-confirm"
            v-model="form.confirm"
            class="input"
            type="password"
            autocomplete="new-password"
            :aria-invalid="Boolean(fieldError.confirm)"
          />
          <p v-if="fieldError.confirm" class="error-text">{{ fieldError.confirm }}</p>
        </div>

        <p v-if="formError" class="error-text">{{ formError }}</p>

        <button class="btn" type="submit" :disabled="submitting">{{ submitLabel }}</button>
      </form>
    </template>

    <div v-if="!isLoggedIn" class="card">
      <p class="section-title">演示账号</p>
      <p class="muted">密码都是 cw123456，点一下自动填入表单。</p>
      <div class="stack">
        <button
          v-for="account in DEMO_ACCOUNTS"
          :key="account.username"
          class="btn ghost small"
          type="button"
          @click="fillDemo(account)"
        >
          {{ account.username }}（{{ account.label }}）
        </button>
      </div>
    </div>
  </section>
</template>

<style scoped>
.tabs {
  margin: 12px 0;
}

h2 {
  margin: 0 0 4px;
}
</style>

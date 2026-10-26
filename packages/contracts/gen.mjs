#!/usr/bin/env node
/**
 * 从 docs/api/openapi.yaml 生成 TS 类型。
 *
 * 为什么不手写 interface：契约一改前端就静默错位，这是这类项目最常见的返工来源。
 *
 * 用法：
 *   node packages/contracts/gen.mjs          # 生成 src/types.ts
 *   node packages/contracts/gen.mjs --check  # CI：只校验生成物是否与契约同步
 *
 * 注意：调用生成器时统一用「相对仓库根目录」的 ASCII 路径，并把 cwd 设为仓库根。
 * 绝对路径里一旦有中文/空格，redoc 的 resolver 会做 URL 编码，导致 ENOENT。
 */
import { spawnSync } from 'node:child_process'
import { readFile, writeFile, rm } from 'node:fs/promises'
import { existsSync } from 'node:fs'
import { dirname, resolve, relative } from 'node:path'
import { fileURLToPath } from 'node:url'

const here = dirname(fileURLToPath(import.meta.url))
const repoRoot = resolve(here, '../..')
const contractRel = 'docs/api/openapi.yaml'
const outRel = 'packages/contracts/src/types.ts'
const tmpRel = 'packages/contracts/.types.check.ts'
const cliPath = resolve(here, 'node_modules/openapi-typescript/bin/cli.js')
const checkOnly = process.argv.includes('--check')

const banner = `/* eslint-disable */
/**
 * 自动生成，请勿手改。
 * 来源：docs/api/openapi.yaml
 * 重新生成：在 apps/web 下执行 pnpm gen
 */
`

if (!existsSync(resolve(repoRoot, contractRel))) {
  console.error(`找不到契约文件：${contractRel}`)
  process.exit(1)
}
if (!existsSync(cliPath)) {
  console.error('缺少依赖 openapi-typescript。先执行：cd packages/contracts && pnpm install')
  process.exit(1)
}

function build(targetRel) {
  const result = spawnSync(process.execPath, [cliPath, contractRel, '-o', targetRel], {
    cwd: repoRoot,
    stdio: 'inherit',
  })
  if (result.status !== 0) process.exit(result.status ?? 1)
}

if (checkOnly) {
  try {
    build(tmpRel)
    const fresh = await readFile(resolve(repoRoot, tmpRel), 'utf8')
    const current = existsSync(resolve(repoRoot, outRel))
      ? await readFile(resolve(repoRoot, outRel), 'utf8')
      : ''
    if (current !== banner + fresh) {
      console.error('契约与生成类型不一致：请运行 pnpm gen 并提交 src/types.ts')
      process.exit(1)
    }
    console.log('生成类型与契约一致。')
  } finally {
    await rm(resolve(repoRoot, tmpRel), { force: true })
  }
} else {
  build(outRel)
  const generated = await readFile(resolve(repoRoot, outRel), 'utf8')
  await writeFile(resolve(repoRoot, outRel), banner + generated, 'utf8')
  console.log(`已生成 ${relative(process.cwd(), resolve(repoRoot, outRel)) || outRel}`)
}

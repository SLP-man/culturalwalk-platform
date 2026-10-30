<script setup lang="ts">
import { computed } from 'vue'

import { MAX_DIFF_LINES, diffLines, toDiffRows, type DiffKind } from './diff'

const props = defineProps<{
  previous?: string | null
  current?: string | null
}>()

const result = computed(() => diffLines(props.previous, props.current))
const rows = computed(() => toDiffRows(result.value.ops))

/** 删除只标左栏、新增只标右栏，其余留白 */
function cellClass(kind: DiffKind, side: 'left' | 'right'): string {
  if (kind === 'same') return 'same'
  return (kind === 'del') === (side === 'left') ? kind : 'blank'
}
</script>

<template>
  <div class="diff">
    <div class="diff-head mono">
      <span>上一版</span>
      <span>本次</span>
    </div>
    <div class="diff-body mono">
      <div v-for="row in rows" :key="row.key" class="diff-row">
        <div class="diff-cell" :class="cellClass(row.kind, 'left')">
          <span class="ln">{{ row.left ? row.left.no : '' }}</span>
          <span class="txt">{{ row.left ? row.left.text : '' }}</span>
        </div>
        <div class="diff-cell" :class="cellClass(row.kind, 'right')">
          <span class="ln">{{ row.right ? row.right.no : '' }}</span>
          <span class="txt">{{ row.right ? row.right.text : '' }}</span>
        </div>
      </div>
    </div>
    <p v-if="!rows.length" class="muted">没有可对照的文本内容</p>
    <p v-if="result.truncated" class="muted">
      差异共 {{ result.totalOps }} 行，只显示前 {{ MAX_DIFF_LINES }} 行
    </p>
  </div>
</template>

<style scoped>
.diff {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.diff-head {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  color: var(--muted);
}

.diff-body {
  display: flex;
  flex-direction: column;
  border: 1px solid var(--line);
  border-radius: 10px;
  overflow-x: auto;
}

.diff-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  gap: 8px;
  border-top: 1px solid var(--line);
}

.diff-row:first-child {
  border-top: none;
}

.diff-cell {
  display: flex;
  gap: 8px;
  padding: 3px 6px;
  min-width: 0;
}

.ln {
  flex: none;
  width: 22px;
  text-align: right;
  color: var(--muted);
}

.txt {
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}

.same {
  background: #faf8f5;
  color: var(--muted);
}

.del {
  background: #fdecec;
  color: #8a1d18;
}

.add {
  background: #e9f7ec;
  color: #14622a;
}

.blank {
  background: #fff;
}
</style>

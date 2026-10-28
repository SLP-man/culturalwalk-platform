import type { Schemas } from '@/api/types'

type Comment = Schemas['Comment']

/** 置顶优先，其余按时间倒序；created_at 缺失的排到最后。 */
export function sortComments(items: Comment[]): Comment[] {
  return [...items].sort((a, b) => {
    const pinnedA = Boolean(a.pinned)
    const pinnedB = Boolean(b.pinned)
    if (pinnedA !== pinnedB) return pinnedA ? -1 : 1
    return (b.created_at ?? '').localeCompare(a.created_at ?? '')
  })
}

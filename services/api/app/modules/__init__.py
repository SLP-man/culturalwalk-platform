"""业务模块集合。

依赖方向（禁止反向）：
    routes -> catalog
    planner -> catalog, routes(只读)
    moderation -> routes, audit
    community -> routes(只读), identity
    discovery -> routes, catalog, community(只读)
    （只读查询层，不拥有表；公开列表/详情/首页聚合都走它）
    media -> identity
    notifications -> identity
    audit <- 所有模块（只写）

出现循环依赖先写 docs/adr 的 ADR，不许"先 import 了再说"。
"""

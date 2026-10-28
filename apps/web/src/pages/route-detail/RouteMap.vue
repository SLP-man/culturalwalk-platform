<script setup lang="ts">
import type { MapPin } from './logic'

defineProps<{ pins: MapPin[] }>()

// 与 projectPoints 的默认 view 保持一致，两边都改才生效
const VIEW = 100
</script>

<template>
  <figure class="map-wrap">
    <svg
      class="map"
      :viewBox="'0 0 ' + VIEW + ' ' + VIEW"
      role="img"
      aria-label="路线点位示意图"
      preserveAspectRatio="xMidYMid meet"
    >
      <rect x="0" y="0" :width="VIEW" :height="VIEW" class="map-bg" />
      <g class="grid">
        <line v-for="n in 4" :key="'v' + n" :x1="n * 20" y1="0" :x2="n * 20" :y2="VIEW" />
        <line v-for="n in 4" :key="'h' + n" x1="0" :y1="n * 20" :x2="VIEW" :y2="n * 20" />
      </g>
      <g v-for="pin in pins" :key="pin.index">
        <circle :cx="pin.x" :cy="pin.y" r="4.6" class="pin-dot" />
        <text :x="pin.x" :y="pin.y + 1.7" class="pin-index">{{ pin.index }}</text>
      </g>
    </svg>
    <figcaption class="muted">
      仅展示点位，不代表最短路径或实时路况；需要导航请用每个节点的「在地图里打开」。
    </figcaption>
  </figure>
</template>

<style scoped>
.map-wrap {
  margin: 0;
}

.map {
  width: 100%;
  height: auto;
  aspect-ratio: 1 / 1;
  max-height: 340px;
  border: 1px solid var(--line);
  border-radius: 12px;
  background: #faf7f2;
}

.map-bg {
  fill: transparent;
}

.grid line {
  stroke: var(--line);
  stroke-width: 0.4;
}

.pin-dot {
  fill: var(--brand);
  stroke: #fff;
  stroke-width: 0.9;
}

.pin-index {
  fill: #fff;
  font-size: 4.4px;
  font-weight: 600;
  text-anchor: middle;
}

figcaption {
  margin-top: 8px;
  line-height: 1.5;
}
</style>

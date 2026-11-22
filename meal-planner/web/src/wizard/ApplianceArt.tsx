// Line drawings of kitchen appliances (lucide has no oven or toaster). Decorative: the tile's text names them.

const P = { fill: 'none', stroke: 'currentColor', strokeWidth: 2, strokeLinecap: 'round' as const, strokeLinejoin: 'round' as const }

export function ApplianceArt({ kind, size = 56 }: { kind: string; size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 48 48" aria-hidden="true" focusable="false">
      {kind === 'stovetop' && (
        <g {...P}>
          <rect x="4" y="14" width="40" height="22" rx="4" />
          <circle cx="15" cy="25" r="5" /><circle cx="33" cy="25" r="5" />
          <circle cx="15" cy="25" r="1.5" /><circle cx="33" cy="25" r="1.5" />
          <path d="M10 40h28" />
        </g>
      )}
      {kind === 'oven' && (
        <g {...P}>
          <rect x="6" y="6" width="36" height="36" rx="4" />
          <path d="M6 15h36" />
          <circle cx="13" cy="10.5" r="1.5" /><circle cx="19" cy="10.5" r="1.5" /><circle cx="25" cy="10.5" r="1.5" />
          <rect x="12" y="20" width="24" height="16" rx="2" />
          <path d="M16 24h16" />
        </g>
      )}
      {kind === 'microwave' && (
        <g {...P}>
          <rect x="4" y="11" width="40" height="26" rx="4" />
          <rect x="9" y="16" width="22" height="16" rx="2" />
          <path d="M36 17v2M36 23v2M36 29v2" />
        </g>
      )}
      {kind === 'air_fryer' && (
        <g {...P}>
          <path d="M12 8h24l4 30a4 4 0 0 1-4 4H12a4 4 0 0 1-4-4z" />
          <circle cx="24" cy="15" r="3" />
          <rect x="13" y="24" width="22" height="12" rx="3" />
          <path d="M20 30h8" />
        </g>
      )}
      {kind === 'toaster' && (
        <g {...P}>
          <path d="M8 22a8 8 0 0 1 8-8h16a8 8 0 0 1 8 8v16H8z" />
          <path d="M18 14v-4M30 14v-4" />
          <path d="M8 38h32M40 26h3" />
          <circle cx="15" cy="31" r="1.5" />
        </g>
      )}
      {kind === 'blender' && (
        <g {...P}>
          <path d="M14 6h20l-3 22H17z" />
          <path d="M14 12h-4v10h5" />
          <rect x="12" y="28" width="24" height="14" rx="3" />
          <circle cx="24" cy="35" r="2" />
        </g>
      )}
      {kind === 'slow_cooker' && (
        <g {...P}>
          <path d="M9 20h30v14a8 8 0 0 1-8 8H17a8 8 0 0 1-8-8z" />
          <path d="M7 20h34M18 20a6 6 0 0 1 12 0" />
          <path d="M22 13h4M5 26h4M39 26h4" />
        </g>
      )}
    </svg>
  )
}

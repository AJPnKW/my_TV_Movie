/*
FILE: web/js/card_renderer.js
VERSION: v1.1.0
UPDATED: 2026-04-29T00:00:00Z
CHANGE NOTES:
- Centralized normalized shared block metadata for the main app runtime.
- Exposes provider fallback helper for shared card/detail rendering paths.
- Keeps text/action rows outside the image and removes card-surface availability overlays.
*/

export const NORMALIZED_BLOCKS = Object.freeze([
  'media_block',
  'action_bar',
  'title_block',
  'meta_row',
  'provider_group',
  'source_chooser',
  'status_control',
  'tag_group',
  'context_block'
]);

export function applyRuntimeContract(doc = document){
  const root = doc.documentElement;
  if (!root) return;
  root.setAttribute('data-normalized-blocks', NORMALIZED_BLOCKS.join(','));
}

export function providerFallbackLabel(name){
  return String(name || 'Provider').trim() || 'Provider';
}

function esc(value){
  return String(value || '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;');
}


function safeCardImage(image, kind, title){
  const src = String(image || '').trim();
  if (src) return `<img loading="lazy" decoding="async" src="${esc(src)}" alt="" />`;
  const label = kind === 'episode' ? 'No Still' : 'No Poster';
  const tag = title ? esc(String(title).slice(0,42)) : label;
  return `<div class="posterFallback posterFallback--${esc(kind)}" aria-label="${esc(label)}"><span class="posterFallback__label">${esc(label)}</span><span class="posterFallback__title">${tag}</span></div>`;
}
export function renderCompactCardHtml(options = {}){
  const kind = options.kind || 'show';
  const idAttr = kind === 'movie'
    ? ` data-movie-open="${esc(options.id)}"`
    : (kind === 'season' ? '' : ` data-show-open="${esc(options.id)}"`);
  const articleAttrs = options.articleAttrs || {};
  const posterAttrs = options.posterAttrs || {};
  const titleAttrs = options.titleAttrs || {};
  const overlay = !!options.overlay;
  const renderKeyAttr = options.renderKey ? ` data-render-key="${esc(options.renderKey)}"` : '';
  return `
    <article class="card media-card media-card--${esc(kind)}${options.extraClass ? ` ${esc(options.extraClass)}` : ''}"${renderKeyAttr}${attrString(articleAttrs)}>
      <button type="button" class="imgbox media-card__poster media-card__poster--${esc(kind)} media_block"${idAttr}${attrString(posterAttrs)} style="padding:0;border:0;background:none;color:inherit;cursor:pointer;">
        ${safeCardImage(options.image, kind, options.title)}
        ${overlay ? `<div class="media-card__overlay"><div class="media-card__overlay-copy">${options.eyebrow ? `<span class="media-card__overlay-eyebrow">${esc(options.eyebrow)}</span>` : ''}<span class="media-card__overlay-title">${esc(options.title)}</span>${options.meta ? `<span class="media-card__overlay-meta">${esc(options.meta)}</span>` : ''}${options.submeta ? `<span class="media-card__overlay-meta media-card__overlay-meta--subtle">${esc(options.submeta)}</span>` : ''}</div></div>` : ''}
      </button>
      <div class="cardbody media-card__body media-card__body--${esc(kind)}">
        <div class="media-card__copy">
          ${options.eyebrow ? `<div class="media-card__eyebrow">${esc(options.eyebrow)}</div>` : ''}
          <button type="button" class="media-card__title"${idAttr}${attrString(titleAttrs)} style="padding:0;border:0;background:none;color:inherit;text-align:left;cursor:pointer;">${esc(options.title)}</button>
          ${options.meta ? `<div class="media-card__meta">${esc(options.meta)}</div>` : ''}
          ${options.submeta ? `<div class="media-card__submeta">${esc(options.submeta)}</div>` : ''}
          ${options.description ? `<div class="media-card__summary">${esc(options.description)}</div>` : ''}
        </div>
        ${options.actionBarHtml || ''}
      </div>
    </article>
  `;
}

export function renderCompactEpisodeCardHtml(options = {}){
  return renderCompactCardHtml({
    ...options,
    kind: 'episode',
    extraClass: `episode-row episode_row${options.extraClass ? ` ${options.extraClass}` : ''}`
  });
}

function attrString(attrs = {}){
  return Object.entries(attrs)
    .filter(([, value]) => value != null && value !== '')
    .map(([key, value]) => ` ${esc(key)}="${esc(value)}"`)
    .join('');
}

if (typeof window !== 'undefined'){
  window.MyTVHubCardRenderer = Object.assign(window.MyTVHubCardRenderer || {}, {
    NORMALIZED_BLOCKS,
    applyRuntimeContract,
    providerFallbackLabel,
    renderCompactCardHtml,
    renderCompactEpisodeCardHtml
  });
}

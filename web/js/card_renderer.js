/*
FILE: web/js/card_renderer.js
VERSION: v1.0.0
UPDATED: 2026-03-15T04:28:23Z
CHANGE NOTES:
- Centralized normalized shared block metadata for the main app runtime.
- Exposes provider fallback helper for shared card/detail rendering paths.
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

export function renderCompactCardHtml(options = {}){
  const kind = options.kind || 'show';
  const idAttr = kind === 'movie' ? ` data-movie-open="${esc(options.id)}"` : ` data-show-open="${esc(options.id)}"`;
  const articleAttrs = options.articleAttrs || {};
  const posterAttrs = options.posterAttrs || {};
  const titleAttrs = options.titleAttrs || {};
  const overlay = !!options.overlay;
  return `
    <article class="card media-card media-card--${esc(kind)}${options.extraClass ? ` ${esc(options.extraClass)}` : ''}"${attrString(articleAttrs)}>
      <button type="button" class="imgbox media-card__poster media_block"${idAttr}${attrString(posterAttrs)} style="padding:0;border:0;background:none;cursor:pointer;">
        ${options.image ? `<img loading="lazy" src="${esc(options.image)}" alt="" />` : `<div class="posterFallback">No Poster</div>`}
        ${overlay ? `<div class="media-card__overlay"><div class="media-card__overlay-copy"><span class="media-card__overlay-title">${esc(options.title)}</span>${options.meta ? `<span class="media-card__overlay-meta">${esc(options.meta)}</span>` : ''}${options.submeta ? `<span class="media-card__overlay-meta media-card__overlay-meta--subtle">${esc(options.submeta)}</span>` : ''}</div></div>` : ''}
      </button>
      <div class="cardbody media-card__body">
        <div class="media-card__copy${overlay ? ' media-card__copy--hidden' : ''}">
          <button type="button" class="media-card__title"${idAttr}${attrString(titleAttrs)} style="padding:0;border:0;background:none;color:inherit;text-align:left;cursor:pointer;">${esc(options.title)}</button>
          ${options.meta ? `<div class="media-card__meta">${esc(options.meta)}</div>` : ''}
          ${options.submeta ? `<div class="media-card__meta media-card__meta--subtle">${esc(options.submeta)}</div>` : ''}
        </div>
        ${options.actionBarHtml || ''}
      </div>
    </article>
  `;
}

export function renderCompactEpisodeCardHtml(options = {}){
  const articleAttrs = options.articleAttrs || {};
  const overlay = !!options.overlay;
  return `
    <article class="episode-row episode_row${options.extraClass ? ` ${esc(options.extraClass)}` : ''}"${attrString(articleAttrs)}>
      <div class="media_block">
        ${options.image ? `<img loading="lazy" src="${esc(options.image)}" alt="" />` : `<div class="posterFallback">No Still</div>`}
        ${overlay ? `<div class="media-card__overlay"><div class="media-card__overlay-copy"><span class="media-card__overlay-title">${esc(options.title)}</span>${options.meta ? `<span class="media-card__overlay-meta">${esc(options.meta)}</span>` : ''}${options.submeta ? `<span class="media-card__overlay-meta media-card__overlay-meta--subtle">${esc(options.submeta)}</span>` : ''}</div></div>` : ''}
      </div>
      <div class="episode-row__body${overlay ? ' episode-row__body--compact' : ''}">
        <div class="title_block"><div class="primary">${esc(options.title)}</div>${options.meta ? `<div class="secondary">${esc(options.meta)}</div>` : ''}${options.submeta ? `<div class="secondary">${esc(options.submeta)}</div>` : ''}</div>
        ${options.actionBarHtml || ''}
        ${options.description ? `<div class="secondary">${esc(options.description)}</div>` : ''}
      </div>
    </article>
  `;
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

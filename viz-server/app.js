(function () {
  'use strict';

  const byId = id => document.getElementById(id);
  const escapeHtml = value => String(value ?? '').replace(/[&<>"']/g, character => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[character]));
  const formatValue = value => typeof value === 'object' && value !== null ? JSON.stringify(value, null, 2) : String(value ?? '—');
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const palette = ['#dfece1', '#e8e3ce', '#dce8e9', '#e6dfeb', '#ede0d3', '#dce6d0'];
  const registered = { fcose: false, 'cose-bilkent': false };
  let state = null;
  let cy = null;
  let view = 'tbox';
  let selectedId = null;
  let focusIds = null;
  let queryResult = null;
  let querying = false;
  let loading = false;
  let toastTimer = null;
  let graphValid = true;
  let resizeTimer = null;
  let lastHistory = '';
  let lastQueryHistory = '';
  const positions = { tbox: new Map(), abox: new Map() };
  const filters = { entity: null, relation: null, phase: null, persona: null, context: null };

  function notify(message) {
    byId('toast').textContent = message;
    byId('toast').hidden = false;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => { byId('toast').hidden = true; }, 5000);
  }

  async function api(path, payload) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), payload ? 30000 : 10000);
    try {
      const options = { cache: 'no-store', signal: controller.signal };
      if (payload !== undefined) {
        options.method = 'POST';
        options.headers = { 'Content-Type': 'application/json', 'X-Ontology-Token': state?.session_token || '' };
        options.body = JSON.stringify(payload);
      }
      const response = await fetch(path, options);
      const result = await response.json();
      if (!response.ok) throw new Error(result.error || `HTTP ${response.status}`);
      return result;
    } finally {
      clearTimeout(timer);
    }
  }

  function typeOfNode(data) {
    return data.entity_type || data.etype || data.type || 'unknown';
  }

  function typeOfEdge(data) {
    return data.relation_type || data.rtype || data.type || 'related-to';
  }

  function typeColor(type) {
    const hash = Array.from(type).reduce((total, character) => total * 31 + character.charCodeAt(0) | 0, 0);
    return palette[Math.abs(hash) % palette.length];
  }

  function initializeGraph() {
    if (typeof cytoscape === 'undefined') throw new Error('Cytoscape 라이브러리를 불러오지 못했습니다.');
    if (typeof window.cytoscapeFcose === 'function') {
      cytoscape.use(window.cytoscapeFcose);
      registered.fcose = true;
    }
    if (typeof window.cytoscapeCoseBilkent === 'function') {
      cytoscape.use(window.cytoscapeCoseBilkent);
      registered['cose-bilkent'] = true;
    }
    for (const name of Object.keys(registered)) {
      if (!registered[name]) byId('layout-select').querySelector(`option[value="${name}"]`).disabled = true;
    }
    if (!registered.fcose) {
      byId('layout-select').value = 'cose';
      notify('확장 레이아웃을 사용할 수 없어 CoSE 기본 레이아웃을 사용합니다.');
    }
    cy = cytoscape({
      container: byId('cy'),
      elements: [],
      layout: { name: 'preset' },
      minZoom: .08,
      maxZoom: 4,
      style: [
        { selector: 'node', style: { label: 'data(label)', 'background-color': element => typeColor(typeOfNode(element.data())), shape: 'round-rectangle', width: 108, height: 46, 'border-width': 1.5, 'border-color': '#819d89', color: '#294237', 'font-size': 11, 'font-family': 'Avenir Next, Apple SD Gothic Neo, sans-serif', 'text-valign': 'center', 'text-halign': 'center', 'text-wrap': 'wrap', 'text-max-width': 92, 'overlay-opacity': 0 } },
        { selector: 'node[type = "instance"]', style: { shape: 'ellipse', width: 65, height: 65, 'text-max-width': 78, 'background-color': '#fdfef9' } },
        { selector: 'node[type = "persona"]', style: { 'background-color': '#f2d989' } },
        { selector: 'node[type = "domain-event"]', style: { 'background-color': '#f4d1a9' } },
        { selector: 'node[type = "command"]', style: { 'background-color': '#cce2ed' } },
        { selector: 'node[type = "policy"]', style: { 'background-color': '#e0d2e8' } },
        { selector: 'node[type = "concept"]', style: { shape: 'diamond', 'background-color': '#dce8e9' } },
        { selector: 'node[type = "data-source"]', style: { shape: 'barrel', 'background-color': '#e0e5dd' } },
        { selector: 'node[?candidate]', style: { 'border-style': 'dashed', 'border-width': 2 } },
        { selector: 'edge', style: { label: element => element.data('label') || '', 'curve-style': 'bezier', width: 1.5, 'line-color': '#97aaa0', 'target-arrow-color': '#97aaa0', 'target-arrow-shape': 'triangle', 'arrow-scale': .8, 'font-size': 9, color: '#667d70', 'text-background-color': '#f7f7f3', 'text-background-opacity': .94, 'text-background-padding': '3px', 'text-rotation': 'autorotate', 'overlay-opacity': 0, 'loop-direction': '-35deg', 'loop-sweep': '60deg' } },
        { selector: 'edge[type = "trace-link"]', style: { 'line-style': 'dashed', 'target-arrow-shape': 'none' } },
        { selector: '.quality-warning', style: { 'border-color': '#c18a3f', 'border-width': 3, 'line-color': '#c18a3f', 'target-arrow-color': '#c18a3f' } },
        { selector: '.quality-error', style: { 'border-color': '#bf4c43', 'border-width': 3, 'line-color': '#bf4c43', 'target-arrow-color': '#bf4c43' } },
        { selector: '.quality-reviewed', style: { 'border-color': '#a4aaa5', 'border-style': 'dotted', 'line-color': '#a4aaa5' } },
        { selector: '.dim', style: { opacity: .17 } },
        { selector: '.spotlight-dim', style: { opacity: .2 } },
        { selector: '.highlight', style: { opacity: 1, 'underlay-color': '#b6d9c2', 'underlay-opacity': .3, 'underlay-padding': 8 } },
        { selector: ':selected', style: { 'underlay-color': '#93bea3', 'underlay-opacity': .3, 'underlay-padding': 9 } }
      ]
    });
    cy.on('tap', 'node, edge', event => selectElement(event.target));
    cy.on('tap', event => { if (event.target === cy) clearFocus(); });
    cy.on('dragfree', 'node', event => positions[view].set(event.target.id(), event.target.position()));
    new ResizeObserver(() => {
      cy.resize();
      clearTimeout(resizeTimer);
      resizeTimer = setTimeout(() => { if (cy.nodes(':visible').length) cy.fit(cy.elements(':visible'), 55); }, 120);
    }).observe(byId('cy'));
  }

  function runLayout() {
    if (!cy || !cy.nodes().length) return;
    cy.stop();
    cy.elements().stop();
    const name = byId('layout-select').value;
    const options = { name, animate: !reducedMotion, animationDuration: 350, padding: 60, fit: true };
    if (name === 'fcose') Object.assign(options, { quality: 'default', idealEdgeLength: 145, nodeRepulsion: 7000, nodeDimensionsIncludeLabels: true });
    if (name === 'cose-bilkent' || name === 'cose') Object.assign(options, { idealEdgeLength: 135, nodeRepulsion: 7000 });
    if (name === 'breadthfirst') Object.assign(options, { directed: true, spacingFactor: 1.5 });
    if (name === 'concentric') Object.assign(options, { minNodeSpacing: 60 });
    try {
      const layout = cy.layout(options);
      layout.one('layoutstop', () => {
        cy.nodes().forEach(node => positions[view].set(node.id(), node.position()));
        reportRender(graphValid, graphValid ? null : '일부 그래프 요소의 구조가 유효하지 않습니다.');
      });
      layout.run();
    } catch (error) {
      reportRender(false, error.message);
      notify(`레이아웃 오류: ${error.message}`);
    }
  }

  function reportRender(ok, error) {
    if (!state) return;
    api('/render-status', { ok, revision: state.revision, view, nodes_rendered: cy.nodes().length, edges_rendered: cy.edges().length, extensions: registered, errors: error ? [error] : [] }).catch(() => {});
  }

  function buildGraph(preserve = false) {
    if (!cy || !state) return;
    const previous = new Map(cy.nodes().map(node => [node.id(), node.position()]));
    const graph = state.graphs[view];
    const seen = new Set();
    const validNodes = graph.nodes.filter(item => {
      if (seen.has(item.data.id)) return false;
      seen.add(item.data.id);
      return true;
    });
    const nodeIds = new Set(seen);
    const validEdges = graph.edges.filter(item => {
      if (seen.has(item.data.id) || !nodeIds.has(item.data.source) || !nodeIds.has(item.data.target)) return false;
      seen.add(item.data.id);
      return true;
    });
    const elements = structuredClone(validNodes.concat(validEdges));
    graphValid = validNodes.length === graph.nodes.length && validEdges.length === graph.edges.length;
    elements.forEach(element => {
      const position = preserve ? previous.get(element.data.id) : positions[view].get(element.data.id);
      if (position) element.position = position;
      if (element.data.status === 'candidate') element.data.candidate = true;
    });
    cy.batch(() => {
      cy.elements().remove();
      cy.add(elements);
    });
    applyQualityStyles();
    applyFilters();
    const allPositioned = validNodes.length && validNodes.every(item => (preserve ? previous : positions[view]).has(item.data.id));
    if (!allPositioned) runLayout();
    else cy.fit(cy.elements(':visible'), 50);
    if (selectedId && cy.getElementById(selectedId).length) showInspector(cy.getElementById(selectedId));
    else clearSelection();
    reportRender(graphValid, graphValid ? null : '중복 ID 또는 끝점이 없는 관계가 있어 일부 요소를 표시하지 못했습니다.');
  }

  function applyQualityStyles() {
    cy.elements().removeClass('quality-warning quality-error quality-reviewed');
    const priorities = new Map();
    state.quality.findings.filter(finding => finding.view === view).forEach(finding => {
      const rank = finding.status !== 'open' ? 1 : finding.severity === 'error' ? 3 : finding.severity === 'warning' ? 2 : 0;
      finding.element_ids.forEach(id => priorities.set(id, Math.max(priorities.get(id) || 0, rank)));
    });
    priorities.forEach((rank, id) => {
      if (rank) cy.getElementById(id).addClass({ 1: 'quality-reviewed', 2: 'quality-warning', 3: 'quality-error' }[rank]);
    });
  }

  function included(kind, value) {
    return filters[kind] === null || filters[kind].has(value);
  }

  function applyFilters() {
    if (!cy || !state) return;
    const search = byId('graph-search').value.trim().toLocaleLowerCase();
    const spotlight = byId('persona-spotlight').checked;
    cy.batch(() => {
      cy.nodes().forEach(node => {
        const data = node.data();
        const personas = data.type === 'persona' ? [data.id] : data.personas || [];
        const personaMatch = filters.persona === null || personas.some(persona => filters.persona.has(persona));
        const phaseMatch = included('phase', data.phase_introduced || 'unspecified');
        const contextMatch = included('context', data.bounded_context || 'unspecified');
        const searchMatch = !search || JSON.stringify(data).toLocaleLowerCase().includes(search);
        const visible = included('entity', typeOfNode(data)) && phaseMatch && contextMatch && searchMatch && (personaMatch || spotlight);
        node.style('display', visible ? 'element' : 'none');
        node.toggleClass('spotlight-dim', spotlight && !personaMatch);
      });
      cy.edges().forEach(edge => {
        const visible = edge.source().style('display') !== 'none' && edge.target().style('display') !== 'none' && included('relation', typeOfEdge(edge.data()));
        edge.style('display', visible ? 'element' : 'none');
      });
    });
    const nodeCount = cy.nodes(':visible').length;
    const edgeCount = cy.edges(':visible').length;
    byId('graph-count').textContent = `${nodeCount} nodes · ${edgeCount} relations`;
    byId('graph-empty').hidden = nodeCount > 0;
    byId('empty-title').textContent = state.empty ? '아직 게시된 모델이 없습니다' : state.graphs[view].nodes.length ? '조건에 맞는 노드가 없습니다' : view === 'abox' ? '아직 인스턴스가 없습니다' : '아직 스키마가 없습니다';
    byId('empty-description').textContent = state.graphs[view].nodes.length ? '필터나 검색 조건을 변경해 보세요.' : '모델과 실제 자료는 로컬 AI 도구에서 게시합니다. 브라우저는 데이터를 임의로 생성하지 않습니다.';
    const filterCount = Object.values(filters).filter(value => value !== null).length + (search ? 1 : 0);
    byId('filter-count').textContent = filterCount ? `(${filterCount})` : '';
    if (focusIds) highlight(focusIds);
  }

  function renderCheckboxes(containerId, values, kind, labels = {}) {
    const container = byId(containerId);
    container.innerHTML = values.length ? values.map(value => `<label><input type="checkbox" data-filter="${kind}" value="${escapeHtml(value)}" ${included(kind, value) ? 'checked' : ''}>${escapeHtml(labels[value] || value)}</label>`).join('') : '<span class="hint">아직 없음</span>';
  }

  function renderTypes() {
    const graph = state.graphs[view];
    const entityNames = new Set(Object.keys(state.schema.entities));
    const relationNames = new Set(Object.keys(state.schema.relations));
    if (state.legacy) {
      graph.nodes.forEach(item => entityNames.add(typeOfNode(item.data)));
      graph.edges.forEach(item => relationNames.add(typeOfEdge(item.data)));
    }
    const countNodes = state.legacy ? graph.nodes : state.graphs.abox.nodes;
    const countEdges = state.legacy ? graph.edges : state.graphs.abox.edges;
    const renderType = (name, kind) => {
      const definition = state.schema[kind === 'entity' ? 'entities' : 'relations'][name];
      const count = kind === 'entity' ? countNodes.filter(item => typeOfNode(item.data) === name).length : countEdges.filter(item => typeOfEdge(item.data) === name).length;
      return `<div class="type-row"><label><input type="checkbox" data-filter="${kind}" value="${escapeHtml(name)}" ${included(kind, name) ? 'checked' : ''}><span title="${escapeHtml(name)}">${escapeHtml(definition?.label || name)}</span></label><span class="type-count">${count}</span><button data-inspect-type="${escapeHtml(name)}" data-kind="${kind}" aria-label="${escapeHtml(name)} 타입 상세">↗</button></div>`;
    };
    byId('entity-types').innerHTML = Array.from(entityNames).sort().map(name => renderType(name, 'entity')).join('') || '<div class="hint">아직 정의된 타입이 없습니다</div>';
    byId('relation-types').innerHTML = Array.from(relationNames).sort().map(name => renderType(name, 'relation')).join('') || '<div class="hint">아직 정의된 관계가 없습니다</div>';
    const allNodes = state.graphs.tbox.nodes.concat(state.graphs.abox.nodes);
    const phases = [...new Set(allNodes.map(item => item.data.phase_introduced || 'unspecified'))].sort();
    const contexts = [...new Set(allNodes.map(item => item.data.bounded_context || 'unspecified'))].sort();
    const personas = [...new Set(allNodes.flatMap(item => item.data.type === 'persona' ? [item.data.id] : item.data.personas || []))].sort();
    renderCheckboxes('phase-filters', phases, 'phase', { unspecified: '단계 미지정' });
    renderCheckboxes('bc-filters', contexts, 'context', { unspecified: '컨텍스트 미지정' });
    renderCheckboxes('persona-filters', personas, 'persona');
  }

  function renderQuality() {
    const quality = state.quality;
    byId('quality-count').textContent = `${quality.open_count} open`;
    byId('quality-summary').innerHTML = `<span class="severity-pill error">오류 ${quality.counts.error}</span><span class="severity-pill warning">경고 ${quality.counts.warning}</span><span class="severity-pill">확인 ${quality.counts.info}</span><span class="severity-pill">${escapeHtml(quality.depth)}</span>`;
    const showReviewed = byId('show-reviewed').checked;
    const findings = quality.findings.filter(finding => showReviewed || finding.status === 'open');
    byId('quality-list').innerHTML = findings.map(finding => `<article class="finding ${escapeHtml(finding.severity)} ${finding.status !== 'open' ? 'reviewed' : ''}"><button data-finding="${escapeHtml(finding.id)}">${escapeHtml(finding.title)} ↗</button><p>${escapeHtml(finding.detail)}</p><details><summary>${escapeHtml(finding.view.toUpperCase())} · ${escapeHtml(finding.code)} · 근거 / 권고</summary><p>${escapeHtml(finding.recommendation)}</p><pre>${escapeHtml(JSON.stringify(finding.evidence, null, 2))}</pre><p>${escapeHtml(finding.element_ids.join(', '))}</p>${finding.decision ? `<p>검토: ${escapeHtml(finding.decision.actor)} · ${escapeHtml(finding.decision.reason)}</p>` : ''}<code>${escapeHtml(finding.id)}</code></details></article>`).join('') || '<div class="empty-note">열린 품질 경고가 없습니다.<br>의미상 정확성은 도메인 검토가 필요합니다.</div>';
    quality.notes.forEach(note => {
      const paragraph = document.createElement('p');
      paragraph.className = 'hint';
      paragraph.textContent = note;
      byId('quality-list').append(paragraph);
    });
  }

  function renderMetadata() {
    const metadata = state.metadata;
    byId('project-title').textContent = metadata.title;
    byId('phase-label').textContent = metadata.phase;
    byId('demo-badge').hidden = !metadata.demo;
    byId('schema-count').innerHTML = `${state.counts.entity_types} <small>타입</small>`;
    byId('relation-count').textContent = `관계 타입 ${state.counts.relation_types}`;
    byId('instance-count').innerHTML = `${state.counts.nodes} <small>노드</small>`;
    byId('edge-count').textContent = `관계 ${state.counts.edges}`;
    byId('legacy-notice').hidden = !state.legacy;
    byId('render-time').textContent = state.publication?.published_at || metadata.rendered_at || '게시 시각 미기록';
    byId('model-revision').textContent = state.empty ? '' : `rev ${state.revision.slice(0, 8)}`;
    byId('query-capability').textContent = state.query.available ? `${state.query.engine} · A-box 읽기 전용 복제본 · 최대 ${state.query.max_rows}행 / 3초` : state.query.reason;
    byId('run-query').disabled = !state.query.available || querying;
    const selectedPreset = byId('query-presets').value;
    byId('query-presets').innerHTML = '<option value="">직접 작성</option>' + state.queries.map((query, index) => `<option value="${index}">${escapeHtml(query.title || query.question || `Query ${index + 1}`)}</option>`).join('');
    if (selectedPreset !== '' && state.queries[Number(selectedPreset)]) byId('query-presets').value = selectedPreset;
    if (!byId('cypher-input').value && state.query.available) {
      byId('cypher-input').value = state.queries[0]?.cypher || 'MATCH (node)\nRETURN node\nLIMIT 25';
      if (state.queries.length) byId('query-presets').value = '0';
    }
  }

  function highlight(ids) {
    cy.elements().removeClass('highlight dim');
    if (!ids?.size) return;
    cy.elements().addClass('dim');
    ids.forEach(id => cy.getElementById(id).removeClass('dim').addClass('highlight'));
    cy.edges().forEach(edge => {
      if (ids.has(edge.source().id()) && ids.has(edge.target().id())) edge.removeClass('dim').addClass('highlight');
    });
  }

  function clearFocus() {
    focusIds = null;
    if (cy) cy.elements().removeClass('highlight dim');
    byId('focus-bar').hidden = true;
  }

  function focus(ids, label) {
    focusIds = new Set(ids);
    highlight(focusIds);
    byId('focus-label').textContent = label;
    byId('focus-bar').hidden = false;
  }

  function traceIds(element) {
    const found = new Set([element.id()]);
    const queue = [element];
    if (element.isEdge()) {
      [element.source(), element.target()].forEach(node => { found.add(node.id()); queue.push(node); });
    }
    while (queue.length) {
      const current = queue.pop();
      (current.data('trace_links') || []).forEach(id => {
        const target = cy.getElementById(id);
        if (target.length && !found.has(id)) { found.add(id); queue.push(target); }
      });
    }
    return found;
  }

  function selectElement(element) {
    if (!element?.length) return;
    selectedId = element.id();
    cy.elements().unselect();
    element.select();
    showInspector(element);
    focus(traceIds(element), `${element.data('label')} · trace chain`);
    byId('node-detail').scrollIntoView({ behavior: reducedMotion ? 'instant' : 'smooth', block: 'nearest' });
  }

  function sourceLink(path) {
    if (typeof path !== 'string' || !path.endsWith('.md') || path.startsWith('/') || path.split('/').some(part => part.startsWith('.'))) return '';
    return `<a class="inspector-source" target="_blank" rel="noopener" href="/source/${path.split('/').map(encodeURIComponent).join('/')}">원문 ↗ ${escapeHtml(path)}</a>`;
  }

  function showInspector(element) {
    const data = element.data();
    byId('inspector-title').textContent = element.isEdge() ? 'Relation inspector' : 'Node inspector';
    byId('clear-selection').hidden = false;
    const properties = data.props || data.properties || {};
    const pairs = { id: data.id, type: element.isEdge() ? typeOfEdge(data) : typeOfNode(data), ...(data.bounded_context ? { bounded_context: data.bounded_context } : {}), ...(data.phase_introduced ? { phase: data.phase_introduced } : {}), ...(data.primary_key || data.identifier ? { identifier: data.primary_key || data.identifier } : {}), ...(element.isEdge() ? { source: data.source, target: data.target, cardinality: data.cardinality || '미지정' } : {}), ...properties };
    const findings = state.quality.findings.filter(finding => finding.view === view && finding.element_ids.includes(data.id));
    byId('node-detail').innerHTML = `<div class="inspector-name">${escapeHtml(data.label)}</div><div class="inspector-tags"><span class="badge teal">${view.toUpperCase()}</span><span class="badge">${escapeHtml(data.candidate || data.status === 'candidate' ? 'candidate · 사용자 검토 필요' : data.status || '확정 상태 미지정')}</span></div><dl class="kv">${Object.entries(pairs).map(([key, value]) => `<dt>${escapeHtml(key)}</dt><dd>${escapeHtml(formatValue(value))}</dd>`).join('')}</dl>${data.description ? `<p class="hint">${escapeHtml(data.description)}</p>` : ''}<h4>Trace / 근거</h4><div class="trace-list">${(data.trace_links || []).map(id => `<button data-jump="${escapeHtml(id)}">${escapeHtml(id)}</button>`).join('') || '<span class="hint">추적 근거가 없습니다</span>'}</div>${(data.source_files || (data.source_file ? [data.source_file] : [])).map(sourceLink).join('')}${findings.map(finding => `<div class="inspector-warning">${escapeHtml(finding.title)} · ${escapeHtml(finding.status)}<br>${escapeHtml(finding.recommendation)}</div>`).join('')}<details><summary class="hint">모든 메타데이터</summary><pre>${escapeHtml(JSON.stringify(data, null, 2))}</pre></details><button id="report-issue" class="full-width">로컬 AI에 검토 요청</button>`;
  }

  function clearSelection() {
    selectedId = null;
    if (cy) cy.elements().unselect();
    byId('inspector-title').textContent = 'Node inspector';
    byId('clear-selection').hidden = true;
    byId('node-detail').innerHTML = '<div class="empty-note">노드·관계 또는 타입을 선택하면<br>속성과 추적 근거를 확인할 수 있습니다.</div>';
  }

  function setView(next) {
    if (!state || !['tbox', 'abox'].includes(next)) return;
    if (cy) cy.nodes().forEach(node => positions[view].set(node.id(), node.position()));
    view = next;
    selectedId = null;
    clearFocus();
    document.querySelectorAll('.view-switch [data-view]').forEach(button => button.setAttribute('aria-pressed', String(button.dataset.view === view)));
    byId('view-eyebrow').textContent = view === 'tbox' ? (state.legacy ? 'LEGACY WORKFLOW GRAPH' : 'SCHEMA GRAPH') : 'INSTANCE GRAPH';
    renderTypes();
    buildGraph();
  }

  function jumpTo(id) {
    let target = cy.getElementById(id);
    if (!target.length) {
      const other = view === 'tbox' ? 'abox' : 'tbox';
      if (state.graphs[other].nodes.concat(state.graphs[other].edges).some(item => item.data.id === id)) {
        setView(other);
        target = cy.getElementById(id);
      }
    }
    if (!target.length) { notify(`현재 게시된 그래프에 ${id}가 없습니다. 로컬 AI에서 해당 근거를 확인하세요.`); return; }
    resetFilters();
    selectElement(target);
    cy.center(target);
    byId('node-detail').scrollIntoView({ behavior: reducedMotion ? 'instant' : 'smooth', block: 'nearest' });
  }

  function resetFilters() {
    Object.keys(filters).forEach(kind => { filters[kind] = null; });
    byId('graph-search').value = '';
    renderTypes();
    applyFilters();
  }

  async function loadHistory() {
    const [history, queries] = await Promise.all([api('/api/history'), api('/api/queries')]);
    const historyKey = JSON.stringify(history.entries);
    const queryKey = JSON.stringify(queries.entries);
    byId('change-count').textContent = history.entries.length;
    if (historyKey !== lastHistory) {
      const openEntries = new Set(Array.from(byId('change-history').querySelectorAll('[data-history-id]')).filter(entry => entry.querySelector('details[open]')).map(entry => entry.dataset.historyId));
      byId('change-history').innerHTML = history.entries.map(entry => {
      const summary = entry.changes.reduce((counts, change) => { counts[change.operation] = (counts[change.operation] || 0) + 1; return counts; }, {});
      return `<article class="history-entry" data-history-id="${escapeHtml(entry.id)}"><time>${escapeHtml(entry.published_at)}</time><strong>${escapeHtml(entry.summary)}</strong><span class="hint">${escapeHtml(entry.actor)} · +${summary.added || 0} / ~${summary.updated || 0} / −${summary.removed || 0}</span>${entry.approval_note ? `<p class="hint">검토 근거: ${escapeHtml(entry.approval_note)}</p>` : '<p class="hint">승인 근거 미기록 · 확정으로 간주하지 않음</p>'}<details ${openEntries.has(entry.id) ? 'open' : ''}><summary>변경 상세 ${entry.changes.length}건</summary>${entry.changes.map(change => `<div class="change-row"><span class="${escapeHtml(change.operation)}">${escapeHtml(change.operation)}</span> · ${escapeHtml(change.view.toUpperCase())} · <button class="text-button" data-jump="${escapeHtml(change.id)}">${escapeHtml(change.id)}</button><pre>${escapeHtml(JSON.stringify({ before: change.before, after: change.after }, null, 2))}</pre></div>`).join('')}</details></article>`;
    }).join('') || '<div class="empty-note">아직 기록된 게시 이력이 없습니다.<br>로컬 AI가 agent.py로 게시하면<br>실제 before / after가 기록됩니다.</div>';
      lastHistory = historyKey;
    }
    if (queryKey !== lastQueryHistory) {
      byId('query-history').innerHTML = queries.entries.map(entry => `<article class="history-entry"><time>${escapeHtml(entry.at)}</time><strong>${entry.ok ? `${entry.count}행 · ${entry.elapsed_ms}ms${entry.truncated ? ' · 일부 결과' : ''}` : '실행 실패 / 차단'}</strong><pre>${escapeHtml(entry.cypher)}</pre>${entry.error ? `<p class="hint error-text">${escapeHtml(entry.error)}</p>` : ''}<span class="hint">${escapeHtml(entry.actor || 'browser-query')} · </span><span class="hint mono">rev ${escapeHtml(entry.revision.slice(0, 8))}</span><button class="text-button" data-reuse-query="${escapeHtml(entry.cypher)}">쿼리 다시 사용</button></article>`).join('') || '<div class="empty-note">실행한 Cypher가 여기에 기록됩니다.</div>';
      lastQueryHistory = queryKey;
    }
  }

  async function loadState() {
    if (loading) return;
    loading = true;
    try {
      const incoming = await api('/api/state');
      const changed = !state || incoming.document_revision !== state.document_revision;
      const graphChanged = !state || incoming.revision !== state.revision;
      const capabilityChanged = !state || JSON.stringify(incoming.query) !== JSON.stringify(state.query);
      const serverChanged = state && incoming.session_token !== state.session_token;
      if (queryResult && queryResult.revision !== incoming.revision) {
        queryResult = null;
        byId('query-results').replaceChildren();
        byId('focus-results').hidden = true;
        byId('query-message').textContent = '모델이 변경되었습니다. 최신 버전에서 쿼리를 다시 실행하세요.';
        clearFocus();
      }
      state = incoming;
      if (graphChanged) clearFocus();
      byId('connection').textContent = '로컬 연결됨';
      byId('connection').classList.remove('offline');
      byId('app-error').hidden = true;
      if (changed) {
        renderMetadata();
        renderTypes();
        renderQuality();
        if (graphChanged) buildGraph(true);
        else { applyQualityStyles(); if (selectedId) showInspector(cy.getElementById(selectedId)); }
      }
      if (capabilityChanged && !changed) renderMetadata();
      if (serverChanged && !graphChanged) reportRender(graphValid, graphValid ? null : '현재 그래프 구조를 확인하세요.');
      await loadHistory();
    } catch (error) {
      byId('connection').textContent = '연결 / 데이터 확인 필요';
      byId('connection').classList.add('offline');
      byId('app-error').textContent = `${error.message} · 마지막으로 확인한 그래프를 유지합니다.`;
      byId('app-error').hidden = false;
    } finally {
      loading = false;
    }
  }

  async function runQuery() {
    if (!state?.query.available || querying) return;
    querying = true;
    byId('run-query').disabled = true;
    byId('run-query').textContent = '실행 중…';
    byId('query-message').classList.remove('failure');
    byId('query-message').textContent = '현재 A-box 조회 복제본에서 실행합니다…';
    const revision = state.revision;
    try {
      const parameters = JSON.parse(byId('query-parameters').value || '{}');
      const result = await api('/api/query', { cypher: byId('cypher-input').value, parameters, revision });
      if (state.revision !== result.revision) throw new Error('실행 중 모델이 변경됐습니다. 다시 조회하세요.');
      queryResult = result;
      byId('query-message').textContent = `${result.count}행 · ${result.elapsed_ms}ms · rev ${result.revision.slice(0, 8)}${result.truncated ? ' · 결과 제한 도달, LIMIT/조건으로 범위를 좁히세요' : ''}`;
      byId('query-results').innerHTML = result.rows.length ? `<table><thead><tr>${result.columns.map(column => `<th scope="col">${escapeHtml(column)}</th>`).join('')}</tr></thead><tbody>${result.rows.map(row => `<tr>${row.map(value => `<td><pre>${escapeHtml(formatValue(value))}</pre></td>`).join('')}</tr>`).join('')}</tbody></table>` : '<p class="empty-note">조회 결과가 없습니다.</p>';
      byId('focus-results').hidden = !result.matched_ids.length;
    } catch (error) {
      queryResult = null;
      byId('query-message').textContent = error.message;
      byId('query-message').classList.add('failure');
      byId('query-results').replaceChildren();
      byId('focus-results').hidden = true;
    } finally {
      querying = false;
      byId('run-query').disabled = !state.query.available;
      byId('run-query').textContent = '쿼리 실행 ↗';
      loadHistory().catch(() => {});
    }
  }

  function download(content, type, filename) {
    const url = URL.createObjectURL(new Blob([content], { type }));
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = filename;
    document.body.append(anchor);
    anchor.click();
    anchor.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  function exportSvg() {
    if (!cy?.nodes(':visible').length) return;
    const visible = cy.elements(':visible');
    const bounds = visible.boundingBox();
    const margin = 40;
    const pieces = [`<svg xmlns="http://www.w3.org/2000/svg" width="${Math.ceil(bounds.w + margin * 2)}" height="${Math.ceil(bounds.h + margin * 2)}" viewBox="${bounds.x1 - margin} ${bounds.y1 - margin} ${bounds.w + margin * 2} ${bounds.h + margin * 2}"><title>${escapeHtml(state.metadata.title)} — ${view}</title><desc>현재 보이는 그래프의 간소화된 벡터 표현. 속성과 전체 모델은 JSON에 포함됩니다.</desc><defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#81998c"/></marker></defs><rect x="${bounds.x1 - margin}" y="${bounds.y1 - margin}" width="${bounds.w + margin * 2}" height="${bounds.h + margin * 2}" fill="#f7f7f3"/>`];
    visible.edges().forEach(edge => {
      const source = edge.source().position();
      const target = edge.target().position();
      const color = edge.hasClass('quality-error') ? '#bf4c43' : edge.hasClass('quality-warning') ? '#c18a3f' : '#97aaa0';
      const self = edge.source().id() === edge.target().id();
      const path = self ? `M ${source.x - 15} ${source.y - 20} C ${source.x - 100} ${source.y - 135}, ${source.x + 100} ${source.y - 135}, ${source.x + 15} ${source.y - 20}` : `M ${source.x} ${source.y} L ${target.x} ${target.y}`;
      pieces.push(`<path d="${path}" fill="none" stroke="${color}" stroke-width="1.5" marker-end="url(#arrow)"${edge.data('type') === 'trace-link' ? ' stroke-dasharray="5 4"' : ''}/><text x="${self ? source.x : (source.x + target.x) / 2}" y="${self ? source.y - 105 : (source.y + target.y) / 2 - 5}" text-anchor="middle" font-family="sans-serif" font-size="9" fill="#667d70">${escapeHtml(edge.data('label'))}</text>`);
    });
    visible.nodes().forEach(node => {
      const position = node.position();
      const width = node.width();
      const height = node.height();
      const color = node.style('border-color');
      const fill = node.style('background-color');
      const border = node.style('border-width');
      const dash = node.data('candidate') || node.data('status') === 'candidate' ? ' stroke-dasharray="5 4"' : '';
      pieces.push(`<g><title>${escapeHtml(node.id())}</title><rect x="${position.x - width / 2}" y="${position.y - height / 2}" width="${width}" height="${height}" rx="${view === 'abox' ? height / 2 : 8}" fill="${fill}" stroke="${color}" stroke-width="${border}"${dash}/><text x="${position.x}" y="${position.y + 4}" text-anchor="middle" font-family="sans-serif" font-size="11" fill="#294237">${escapeHtml(node.data('label'))}</text></g>`);
    });
    pieces.push('</svg>');
    download(pieces.join(''), 'image/svg+xml;charset=utf-8', `ontology-${view}.svg`);
    notify('현재 보이는 그래프를 간소화된 벡터 SVG로 내보냈습니다.');
  }

  async function exportCypher(scope) {
    if (!state || state.empty) return;
    const button = byId(`export-cypher-${scope}`);
    button.disabled = true;
    try {
      const result = await api(`/api/export/cypher?scope=${scope}&revision=${encodeURIComponent(state.revision)}`);
      if (result.revision !== state.revision) throw new Error('모델이 변경됐습니다. 다시 내보내세요.');
      download(result.content, 'text/plain;charset=utf-8', result.filename);
      notify(`${result.filename}을 저장했습니다.`);
    } catch (error) {
      notify(error.message);
    } finally {
      button.disabled = false;
    }
  }

  function setupControls() {
    document.addEventListener('change', event => {
      const kind = event.target.dataset.filter;
      if (kind) {
        filters[kind] = new Set(Array.from(document.querySelectorAll(`[data-filter="${kind}"]:checked`)).map(input => input.value));
        applyFilters();
      }
    });
    document.addEventListener('click', event => {
      const viewButton = event.target.closest('[data-view]');
      if (viewButton) setView(viewButton.dataset.view);
      const jump = event.target.closest('[data-jump]');
      if (jump) jumpTo(jump.dataset.jump);
      const type = event.target.closest('[data-inspect-type]');
      if (type) {
        const id = `${type.dataset.kind === 'entity' ? 'type' : 'relation'}:${type.dataset.inspectType}`;
        if (state.legacy) notify('이전 형식 그래프는 개별 노드를 선택해 상세를 확인하세요.');
        else { if (view !== 'tbox') setView('tbox'); jumpTo(id); }
      }
      const findingButton = event.target.closest('[data-finding]');
      if (findingButton) {
        const finding = state.quality.findings.find(item => item.id === findingButton.dataset.finding);
        if (view !== finding.view) setView(finding.view);
        resetFilters();
        const target = finding.element_ids.map(id => cy.getElementById(id)).find(element => element.length);
        if (target) selectElement(target);
        focus(finding.element_ids, finding.title);
        if (cy.elements('.highlight:visible').length) cy.fit(cy.elements('.highlight:visible'), 70);
      }
      const reuse = event.target.closest('[data-reuse-query]');
      if (reuse) { byId('cypher-input').value = reuse.dataset.reuseQuery; byId('cypher-input').focus(); }
      if (event.target.closest('#report-issue')) {
        byId('feedback-target').textContent = selectedId;
        byId('feedback-note').value = '';
        byId('feedback-status').textContent = '';
        byId('feedback-dialog').dataset.revision = state.revision;
        byId('feedback-dialog').dataset.target = selectedId;
        byId('feedback-dialog').showModal();
      }
    });
    byId('graph-search').addEventListener('input', applyFilters);
    byId('persona-spotlight').addEventListener('change', applyFilters);
    byId('show-reviewed').addEventListener('change', () => state && renderQuality());
    byId('reset-filters').addEventListener('click', resetFilters);
    byId('all-entities').addEventListener('click', () => { filters.entity = null; renderTypes(); applyFilters(); });
    byId('all-relations').addEventListener('click', () => { filters.relation = null; renderTypes(); applyFilters(); });
    byId('layout-select').addEventListener('change', runLayout);
    byId('fit-graph').addEventListener('click', () => cy?.fit(cy.elements(':visible'), 55));
    byId('clear-focus').addEventListener('click', clearFocus);
    byId('clear-selection').addEventListener('click', () => { clearSelection(); clearFocus(); });
    byId('run-query').addEventListener('click', runQuery);
    byId('cypher-input').addEventListener('keydown', event => { if (event.key === 'Enter' && (event.metaKey || event.ctrlKey)) { event.preventDefault(); runQuery(); } });
    byId('query-presets').addEventListener('change', event => {
      const preset = event.target.value === '' ? null : state.queries[Number(event.target.value)];
      if (preset) { byId('cypher-input').value = preset.cypher; byId('query-parameters').value = JSON.stringify(preset.parameters || {}, null, 2); }
    });
    byId('focus-results').addEventListener('click', () => {
      if (!queryResult || queryResult.revision !== state.revision) return;
      if (view !== 'abox') setView('abox');
      resetFilters();
      focus(queryResult.matched_ids, `Cypher 결과 · ${queryResult.count}행`);
      const collection = cy.elements('.highlight:visible');
      if (collection.length) cy.fit(collection, 60);
    });
    for (const side of ['left', 'right']) {
      byId(`toggle-${side}`).addEventListener('click', () => {
        const panel = byId(`${side}-panel`);
        panel.hidden = !panel.hidden;
        byId('workspace').classList.toggle(`${side}-hidden`, panel.hidden);
        byId(`toggle-${side}`).setAttribute('aria-expanded', String(!panel.hidden));
        cy?.resize();
      });
    }
    const tabs = [byId('changes-tab'), byId('queries-tab')];
    const activateTab = index => tabs.forEach((tab, current) => {
      const active = current === index;
      tab.setAttribute('aria-selected', String(active));
      tab.tabIndex = active ? 0 : -1;
      byId(tab.getAttribute('aria-controls')).hidden = !active;
    });
    tabs.forEach((tab, index) => {
      tab.addEventListener('click', () => activateTab(index));
      tab.addEventListener('keydown', event => {
        if (['ArrowLeft', 'ArrowRight'].includes(event.key)) { event.preventDefault(); activateTab(1 - index); tabs[1 - index].focus(); }
      });
    });
    byId('cancel-feedback').addEventListener('click', () => byId('feedback-dialog').close());
    byId('feedback-form').addEventListener('submit', async event => {
      event.preventDefault();
      const button = event.submitter;
      button.disabled = true;
      try {
        await api('/feedback', { nodeId: byId('feedback-dialog').dataset.target, note: byId('feedback-note').value, revision: byId('feedback-dialog').dataset.revision });
        byId('feedback-dialog').close();
        notify('피드백을 기록했습니다. 다음 게이트에서 로컬 AI가 확인합니다.');
      } catch (error) { byId('feedback-status').textContent = error.message; }
      finally { button.disabled = false; }
    });
    byId('export-png').addEventListener('click', () => { if (cy?.nodes(':visible').length) download(cy.png({ output: 'blob', scale: 2, full: true, bg: '#f7f7f3' }), 'image/png', `ontology-${view}.png`); });
    byId('export-svg').addEventListener('click', exportSvg);
    for (const scope of ['schema', 'data', 'model']) {
      byId(`export-cypher-${scope}`).addEventListener('click', () => exportCypher(scope));
    }
    byId('export-json').addEventListener('click', async () => {
      try { download(JSON.stringify(await api('/data/current.json'), null, 2), 'application/json;charset=utf-8', 'ontology-model.json'); }
      catch (error) { notify(error.message); }
    });
  }

  try {
    initializeGraph();
    setupControls();
    loadState();
    setInterval(loadState, 5000);
  } catch (error) {
    byId('app-error').textContent = `초기화 실패: ${error.message}`;
    byId('app-error').hidden = false;
    console.error(error);
  }
})();

/* Marquez 0.51.1 public Datasets presentation. No API/data changes. */
(function () {
  'use strict';
  var preferred = 's3://health-processing';
  var originalHeaders = ['NAME', 'NAMESPACE', 'SOURCE'];
  var publicHeaders = ['DATASET', 'BATCH', 'INGEST DATE'];
  var choosing = false;

  function onDatasetsRoute() { return window.location.pathname === '/datasets'; }

  function selectFirstUsefulNamespace() {
    // Only on Datasets, and only if the visitor never selected any namespace.
    if (!onDatasetsRoute() || choosing) return;
    try {
      if (window.localStorage.getItem('selectedNamespace') !== null) return;
    } catch (_) { return; }
    var selector = document.getElementById('namespace-select');
    if (!selector || (selector.textContent || '').indexOf(preferred) !== -1) return;
    var options = document.querySelectorAll('[role="option"]');
    for (var i = 0; i < options.length; i++) {
      if ((options[i].textContent || '').trim() === preferred) {
        choosing = true;
        options[i].click(); // Upstream MUI Select -> Redux selection.
        choosing = false;
        return;
      }
    }
    if (selector.getAttribute('data-public-default-opened') !== 'true') {
      selector.setAttribute('data-public-default-opened', 'true');
      selector.click(); // Open options once; no direct Redux/localStorage mutation.
    }
  }

  function metadataFromHref(href) {
    var pathname;
    try { pathname = new URL(href, window.location.href).pathname; }
    catch (_) { return null; }
    var match = pathname.match(/\/lineage\/dataset\/([^/]+)\/([^/]+)\/?$/i);
    if (!match) return null;
    try {
      var namespace = decodeURIComponent(match[1]);
      var rawName = decodeURIComponent(match[2]);
      if (namespace !== preferred) return null;
      var params = {};
      rawName.split('/').forEach(function (part) {
        var split = part.indexOf('=');
        if (split > 0) params[part.slice(0, split)] = part.slice(split + 1);
      });
      if (!/^[a-z_]+$/i.test(params.entity || '') ||
          !/^\d{4}-\d{2}-\d{2}$/.test(params.ingest_date || '') ||
          !params.batch_id || !params.run_id) return null;
      return {
        namespace: namespace, rawName: rawName,
        entity: params.entity.charAt(0).toUpperCase() + params.entity.slice(1),
        batch: params.batch_id,
        batchLabel: params.batch_id.replace(/^synthea-new-only-gh-/, ''),
        date: params.ingest_date, run: params.run_id,
        source: params.source || 'source unspecified',
        version: params.source_version || ''
      };
    } catch (_) { return null; }
  }

  function putText(node, value) {
    if (!node || node.textContent === value) return;
    // Reuse React-owned text node when possible (do not remove React's children).
    if (node.childNodes && node.childNodes.length === 1 &&
        node.firstChild && node.firstChild.nodeType === 3) {
      node.firstChild.nodeValue = value;
    } else { node.textContent = value; }
  }
  function putAttr(node, key, value) {
    if (node && node.getAttribute(key) !== value) node.setAttribute(key, value);
  }
  function datasetTable(table) {
    var head = table.querySelector('thead tr');
    if (!head) return;
    var th = head.querySelectorAll('th');
    if (th.length !== 6 ||
        (th[5].textContent || '').trim().toUpperCase() !== 'COLUMN LINEAGE') return;

    var rows = table.querySelectorAll('tbody tr');
    var selector = document.getElementById('namespace-select');
    var eligible = selector &&
      (selector.textContent || '').indexOf(preferred) !== -1 && rows.length > 0;
    var parsed = [];
    for (var i = 0; i < rows.length; i++) {
      var cells = rows[i].querySelectorAll('td');
      var link = cells.length === 6 && cells[0].querySelector('a[href*="/lineage/dataset/"]');
      var data = link && metadataFromHref(link.href || link.getAttribute('href'));
      parsed.push({ cells: cells, link: link, data: data });
      if (!data) eligible = false;
    }
    // Mixed or unknown datasets retain the official Marquez layout.
    for (var h = 0; h < 3; h++) {
      var headerText = th[h].querySelector('div,span') || th[h];
      putText(headerText, eligible ? publicHeaders[h] : originalHeaders[h]);
    }
    if (!eligible) {
      parsed.forEach(function (item) {
        var c = item.cells, a = item.link;
        if (!a || c.length !== 6) return;
        var text = a.querySelector('span');
        if (text && text.getAttribute('data-public-original-text') !== null) {
          putText(text, text.getAttribute('data-public-original-text'));
          text.removeAttribute('data-public-original-text');
        }
        [1, 2].forEach(function (idx) {
          var target = c[idx].querySelector('div,span') || c[idx];
          var original = target.getAttribute('data-public-original-text');
          if (original !== null) {
            putText(target, original);
            target.removeAttribute('data-public-original-text');
          }
          target.removeAttribute('title');
        });
        a.removeAttribute('data-public-run');
        a.removeAttribute('data-public-dataset');
        a.removeAttribute('aria-label');
        a.removeAttribute('title');
      });
      return;
    }
    parsed.forEach(function (item) {
      var c = item.cells, a = item.link, d = item.data;
      var text = a.querySelector('span');
      if (!text) return;
      if (text.getAttribute('data-public-original-text') === null)
        text.setAttribute('data-public-original-text', text.textContent || '');
      putText(text, d.entity);
      putAttr(a, 'data-public-dataset', 'true');
      putAttr(a, 'data-public-run', 'Run: ' + d.run);
      putAttr(a, 'aria-label', d.entity + ', batch ' + d.batch + ', ingested ' + d.date + ', run ' + d.run);
      putAttr(a, 'title', d.rawName);
      var batch = c[1].querySelector('div,span') || c[1];
      var date = c[2].querySelector('div,span') || c[2];
      [[batch, d.batchLabel, 'Namespace: ' + d.namespace + '\nBatch: ' + d.batch],
       [date, d.date, 'Marquez Source: ' +
         (date.getAttribute('data-public-original-text') || date.textContent) +
         '\nProducer: ' + d.source + (d.version ? '\nVersion: ' + d.version : '')]]
        .forEach(function (part) {
          if (part[0].getAttribute('data-public-original-text') === null)
            part[0].setAttribute('data-public-original-text', part[0].textContent || '');
          putText(part[0], part[1]);
          putAttr(part[0], 'title', part[2]);
        });
    });
  }

  function update() {
    selectFirstUsefulNamespace();
    if (!onDatasetsRoute()) return;
    document.querySelectorAll('table').forEach(datasetTable);
  }
  function run() {
    update();
    new MutationObserver(update).observe(document.body, { childList: true, subtree: true });
    window.addEventListener('popstate', update);
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', run, { once: true });
  else run();
})();

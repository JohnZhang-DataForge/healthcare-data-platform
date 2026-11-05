/* Marquez 0.51.1 public Datasets presentation. No API/data changes. */
(function () {
  'use strict';
  var preferred = 's3://health-landing';
  var processingNamespace = 's3://health-processing';
  var rootLandingKey = 'publicMarquezRootLandingOnce';
  // The native Marquez Redux/localStorage selector is global across routes.
  // Keep the PUBLIC presentation preference per section instead.
  var jobsPreferred = 'healthcare-platform-airflow';
  var jobsFallback = 'healthcare-platform-spark-business';
  var sectionKeys = { datasets: 'publicMarquezDatasetsNamespace', jobs: 'publicMarquezJobsNamespace' };
  var lastSection = null;
  var pendingChoice = null;
  var requestedChoice = false;
  var originalHeaders = ['NAME', 'NAMESPACE', 'SOURCE'];
  var publicHeaders = ['DATASET', 'BATCH', 'INGEST DATE'];
  var choosing = false;

  function onDatasetsRoute() { return window.location.pathname === '/datasets' || window.location.pathname === '/datasets/'; }

  // Only exact root visits take visitors to the Landing-first home. The one-shot
  // marker overrides a previously saved Processing choice for this navigation,
  // without resetting manual Namespace choices during later browsing.
  function navigateRootToLanding() {
    if (window.location.pathname !== '/') return false;
    try { window.sessionStorage.setItem(rootLandingKey, '1'); } catch (_) {}
    window.location.replace('/datasets' + (window.location.search || '') + (window.location.hash || ''));
    return true;
  }
  if (navigateRootToLanding()) return;

  function clearRootLandingMarker() {
    try { window.sessionStorage.removeItem(rootLandingKey); } catch (_) {}
  }
  function sectionForPath() {
    if (onDatasetsRoute()) return 'datasets';
    if (window.location.pathname === '/jobs' || window.location.pathname === '/jobs/') return 'jobs';
    return null; // Job/Run/Dataset/Lineage details must keep native context.
  }
  function readSectionChoice(section) {
    try { return window.sessionStorage.getItem(sectionKeys[section]); } catch (_) { return null; }
  }
  function rememberSectionChoice(section, value) {
    if (!section || !value) return;
    try { window.sessionStorage.setItem(sectionKeys[section], value); } catch (_) {}
  }
  function rootLandingRequested() {
    try { return window.sessionStorage.getItem(rootLandingKey) === '1'; } catch (_) { return false; }
  }

  function onManualNamespaceOption(event) {
    // The owner-selected MUI option is authoritative. Auto-selection clicks
    // are deliberately excluded, so the observer won't undo a manual switch.
    if (choosing) return;
    var target = event && event.target;
    var option = target && target.closest && target.closest('[role="option"]');
    if (!option) return;
    var section = sectionForPath();
    if (!section || !document.getElementById('namespace-select')) return;
    var value = (option.textContent || '').trim();
    // Do not confuse other page filters' MUI options with Namespace choices.
    var known = ['default', 'file', preferred, processingNamespace,
      jobsPreferred, jobsFallback, 'healthcare-platform-spark-probe'];
    if (known.indexOf(value) < 0) return;
    rememberSectionChoice(section, value);
    pendingChoice = null;
    requestedChoice = false;
    if (section === 'datasets') clearRootLandingMarker();
  }

  function selectFirstUsefulNamespace() {
    var section = sectionForPath();
    if (section !== lastSection) {
      var previous = lastSection;
      lastSection = section;
      pendingChoice = null;
      requestedChoice = false;
      if (section) {
        var saved = readSectionChoice(section);
        if (section === 'jobs') {
          // LIVE GET evidence: Airflow and Spark Business have real Jobs.
          // Landing/Processing are Datasets-only namespaces.
          pendingChoice = saved || jobsPreferred;
        } else {
          var persisted = null;
          try { persisted = window.localStorage.getItem('selectedNamespace'); } catch (_) {}
          // Preserve an explicit direct Dataset bookmark's known useful
          // selection; section navigation always returns to its own choice.
          pendingChoice = rootLandingRequested() ? preferred :
            (saved || (previous === null &&
              (persisted === preferred || persisted === processingNamespace) ? persisted : preferred));
        }
        var newSelector = document.getElementById('namespace-select');
        if (newSelector) newSelector.removeAttribute('data-public-default-opened');
      }
    }
    if (!section || choosing) return;
    var selector = document.getElementById('namespace-select');
    if (!selector) return;
    var active = (selector.textContent || '').trim();
    if (!pendingChoice) {
      // A visitor may use keyboard navigation; observe the rendered selection.
      rememberSectionChoice(section, active);
      return;
    }
    if (active === pendingChoice) {
      rememberSectionChoice(section, pendingChoice);
      pendingChoice = null;
      requestedChoice = false;
      if (section === 'datasets') clearRootLandingMarker();
      return;
    }
    var options = document.querySelectorAll('[role="option"]');
    for (var i = 0; i < options.length; i++) {
      if ((options[i].textContent || '').trim() === pendingChoice) {
        if (requestedChoice) return; // Wait for React to apply selection.
        requestedChoice = true;
        choosing = true;
        try { options[i].click(); } finally { choosing = false; }
        return;
      }
    }
    // If the verified Airflow namespace is absent, use the verified
    // nonempty Spark Business namespace. Never pick an arbitrary empty one.
    if (section === 'jobs' && pendingChoice === jobsPreferred && options.length) {
      for (var j = 0; j < options.length; j++) {
        if ((options[j].textContent || '').trim() === jobsFallback) {
          pendingChoice = jobsFallback;
          requestedChoice = false;
          choosing = true;
          try { options[j].click(); requestedChoice = true; }
          finally { choosing = false; }
          return;
        }
      }
    }
    if (selector.getAttribute('data-public-default-opened') !== 'true') {
      selector.setAttribute('data-public-default-opened', 'true');
      selector.click(); // MUI selector only; do not write Redux state directly.
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
      var isLanding = namespace === 's3://health-landing';
      if (!isLanding && namespace !== processingNamespace) return null;
      var segments = rawName.split('/');
      var params = {};
      segments.forEach(function (part) {
        var split = part.indexOf('=');
        if (split > 0) params[part.slice(0, split)] = part.slice(split + 1);
      });
      if (!/^\d{4}-\d{2}-\d{2}$/.test(params.ingest_date || '') ||
          !/^[a-zA-Z0-9_-]{1,120}$/.test(params.batch_id || '')) return null;
      var label, detail;
      if (isLanding) {
        // Real Landing records: manifest.json, encounters.csv, patients.csv.
        // These are raw files, not processing runs; no run_id is required.
        var leaf = segments[segments.length - 1];
        var labels = {
          'manifest.json': 'Batch Manifest',
          'encounters.csv': 'Encounters CSV',
          'patients.csv': 'Patients CSV'
        };
        if (!Object.prototype.hasOwnProperty.call(labels, leaf)) return null;
        label = labels[leaf];
        detail = 'File: ' + leaf;
      } else {
        if (!/^[a-z_]+$/i.test(params.entity || '') ||
            !/^[a-zA-Z0-9_.:-]{1,160}$/.test(params.run_id || '')) return null;
        label = params.entity.charAt(0).toUpperCase() + params.entity.slice(1);
        detail = 'Run: ' + params.run_id;
      }
      return {
        namespace: namespace, rawName: rawName,
        label: label, detail: detail, isLanding: isLanding,
        batch: params.batch_id,
        batchLabel: params.batch_id.replace(/^synthea-new-only-gh-/, ''),
        date: params.ingest_date,
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
    var activeNamespace = selector && (selector.textContent || '').trim();
    var eligible = (activeNamespace === preferred || activeNamespace === processingNamespace) &&
      rows.length > 0;
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
        a.removeAttribute('data-public-description');
        a.removeAttribute('data-public-dataset');
        a.removeAttribute('aria-label');
        a.removeAttribute('title');
        c[5].removeAttribute('title');
      });
      return;
    }
    parsed.forEach(function (item) {
      var c = item.cells, a = item.link, d = item.data;
      var text = a.querySelector('span');
      if (!text) return;
      if (text.getAttribute('data-public-original-text') === null)
        text.setAttribute('data-public-original-text', text.textContent || '');
      putText(text, d.label);
      putAttr(a, 'data-public-dataset', 'true');
      putAttr(a, 'data-public-description', d.detail);
      putAttr(a, 'aria-label', d.label + ', batch ' + d.batch + ', ingested ' + d.date + ', ' + d.detail);
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
      if (d.isLanding && (c[5].textContent || '').trim() === 'N/A')
        putAttr(c[5], 'title', 'Landing input file: column-level mappings are shown in Processing.');
    });
  }

  function update() {
    selectFirstUsefulNamespace();
    if (!onDatasetsRoute()) return;
    document.querySelectorAll('table').forEach(datasetTable);
  }
  function run() {
    update();
    document.addEventListener('click', onManualNamespaceOption, true);
    new MutationObserver(update).observe(document.body, { childList: true, subtree: true });
    window.addEventListener('popstate', update);
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', run, { once: true });
  else run();
})();

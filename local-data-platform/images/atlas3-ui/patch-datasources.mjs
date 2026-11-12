#!/usr/bin/env node
// Fail-closed overlay for the pinned OHDSI/Atlas3 v3.0.0 checkout.
// GitHub-hosted build only. Does not touch WebAPI, PostgreSQL or Kubernetes.
import fs from 'node:fs'
import path from 'node:path'

const root = process.argv[2]
if (!root) throw new Error('usage: node patch-datasources.mjs <atlas-checkout>')

function replaceOnce(filename, before, after, label) {
  const target = path.join(root, filename)
  const source = fs.readFileSync(target, 'utf8')
  const count = source.split(before).length - 1
  if (count !== 1) throw new Error(label + ': expected one pinned upstream anchor; found ' + count)
  fs.writeFileSync(target, source.replace(before, after))
}

const store = 'src/stores/datasources.ts'
replaceOnce(store,
  '  let fetchPromise: Promise<void> | null = null\n',
  [
    '  let fetchPromise: Promise<void> | null = null',
    '  // Only the latest selected source/report may own visible loading and errors.',
    '  let reportRequestGeneration = 0',
    '  function resetReportRequest() {',
    '    reportRequestGeneration += 1',
    '    error.value.report = null',
    '    loading.value.report = false',
    '  }',
    ''
  ].join('\n'), 'report generation')
replaceOnce(store,
  '    selectedSourceId.value = sourceId\n\n    // If a report type is selected',
  '    selectedSourceId.value = sourceId\n    resetReportRequest()\n\n    // If a report type is selected',
  'source switch')
replaceOnce(store,
  '    selectedReportType.value = reportType\n\n    // Plugin surfaces',
  '    selectedReportType.value = reportType\n    resetReportRequest()\n\n    // Plugin surfaces',
  'report switch')
replaceOnce(store,
  '    // Return cached if available\n',
  '    const requestGeneration = ++reportRequestGeneration\n    error.value.report = null\n\n    // Return cached if available\n',
  'request ID')
replaceOnce(store,
  [
    '    if (reportCache.value.has(cacheKey)) {',
    "      logger.debug('DataSourcesStore', 'Using cached report', cacheKey)",
    '      return',
    '    }',
    '',
    "    // Don't start a new fetch if already loading",
    '    if (loading.value.report) {',
    "      logger.debug('DataSourcesStore', 'Already loading a report, skipping', cacheKey)",
    '      return',
    '    }',
    '',
    '    loading.value.report = true',
    '    error.value.report = null',
  ].join('\n'),
  [
    '    if (reportCache.value.has(cacheKey)) {',
    "      logger.debug('DataSourcesStore', 'Using cached report', cacheKey)",
    '      loading.value.report = false',
    '      return',
    '    }',
    '',
    '    // A newly selected report must not be skipped by a stale in-flight fetch.',
    '    // Its completion is guarded by requestGeneration below.',
    '    loading.value.report = true',
  ].join('\n'), 'in-flight switch')
replaceOnce(store,
  '    } catch (err) {\n      // Ignore abort errors - user switched reports before this one loaded',
  '    } catch (err) {\n      if (requestGeneration !== reportRequestGeneration) return\n      // Ignore abort errors - user switched reports before this one loaded',
  'old response suppression')
replaceOnce(store,
  '    } finally {\n      loading.value.report = false\n    }\n  }\n\n  function cacheReport(',
  '    } finally {\n      if (requestGeneration === reportRequestGeneration) loading.value.report = false\n    }\n  }\n\n  function cacheReport(',
  'spinner ownership')

const tests = 'tests/unit/stores/datasources.spec.ts'
replaceOnce(tests,
  [
    "    it('should not start new fetch if already loading', async () => {",
    '      const store = useDataSourcesStore()',
    '      store.sources = mockDataSources',
    '      store.selectedSourceId = 1',
    '      store.loading.report = true',
    '',
    "      await store.fetchReport('dashboard')",
    '',
    '      expect(getDashboardReport).not.toHaveBeenCalled()',
    '    })',
  ].join('\n'),
  [
    "    it('fetches a newly selected report even when another fetch is loading', async () => {",
    '      const store = useDataSourcesStore()',
    '      store.sources = mockDataSources',
    '      store.selectedSourceId = 1',
    '      store.loading.report = true',
    '      vi.mocked(getDashboardReport).mockResolvedValue({ summary: {} })',
    '',
    "      await store.fetchReport('dashboard')",
    '',
    '      expect(getDashboardReport).toHaveBeenCalledTimes(1)',
    '      expect(store.loading.report).toBe(false)',
    '    })',
    '',
    "    it('clears a drugEra error when returning to a cached Person report', async () => {",
    '      const store = useDataSourcesStore()',
    '      store.sources = mockDataSources',
    '      store.selectedSourceId = 1',
    "      store.reportCache.set('1-person', { type: 'person', data: {} } as any)",
    "      vi.mocked(getClinicalDomainReport).mockRejectedValue(new Error('drugEra failed'))",
    '',
    "      await store.selectReportType('drugEra')",
    "      expect(store.error.report).toBe('drugEra failed')",
    "      await store.selectReportType('person')",
    '      expect(store.error.report).toBeNull()',
    "      expect(store.currentReport?.type).toBe('person')",
    '      expect(getPersonReport).not.toHaveBeenCalled()',
    '    })',
    '',
    "    it('ignores a late drugEra failure after switching to Person', async () => {",
    '      const store = useDataSourcesStore()',
    '      store.sources = mockDataSources',
    '      store.selectedSourceId = 1',
    '      let rejectOld: (reason?: unknown) => void = () => {}',
    '      vi.mocked(getClinicalDomainReport).mockImplementation(',
    '        () => new Promise<Awaited<ReturnType<typeof getClinicalDomainReport>>>((_, reject) => {',
    '          rejectOld = reject',
    '        })',
    '      )',
    '      vi.mocked(getPersonReport).mockResolvedValue({} as never)',
    '',
    "      const oldRequest = store.selectReportType('drugEra')",
    "      const currentRequest = store.selectReportType('person')",
    '      await currentRequest',
    '      expect(store.error.report).toBeNull()',
    "      expect(getPersonReport).toHaveBeenCalledWith('TEST_CDM_1')",
    "      rejectOld(new Error('late drugEra failure'))",
    '      await oldRequest',
    '      expect(store.error.report).toBeNull()',
    '      expect(store.loading.report).toBe(false)',
    "      expect(store.currentReport?.type).toBe('person')",
    '    })',
  ].join('\n'), 'store regression tests')

console.log('ATLAS3_DATASOURCES_REPORT_SWITCH_PATCH=PASS')

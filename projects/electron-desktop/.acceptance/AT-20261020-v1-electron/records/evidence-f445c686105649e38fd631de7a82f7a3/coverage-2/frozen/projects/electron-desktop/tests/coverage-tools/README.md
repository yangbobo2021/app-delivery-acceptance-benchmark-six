# Electron application coverage preparation

There was no tests directory, test script or previous coverage adapter in revision
be952659. Product build.mjs emits bundled main/preload and browser renderer with
source maps. Coverage tools live in this separate locked test package; do not
change the product package manifests to install them.

Rebuild on a new host: prepare and independently verify that acceptance's Node,
npm, Electron and esbuild runtime first; run npm ci --prefix
projects/electron-desktop/tests/coverage-tools. Run the independent host probe gate in
a new acceptance workflow directory. No previous acceptance's artifacts or
success receipts establish current capability.

Tool APIs: esbuild.transform(TypeScript, external source map),
createInstrumenter().instrumentSync(js, generatedFilename, inputSourceMap),
lastFileCoverage() for zero units; esbuild.build bundles instrumented units in a
separate application. Native snapshots contain Istanbul counters with their
inputSourceMap. createCoverageMap().merge and
createSourceMapStore().transformCoverage do all merging/remapping;
FileCoverage.toSummary supplies counts and percentages. No adapter defines
executable lines, branches or hit rules.

Official references:
- https://github.com/istanbuljs/istanbuljs/blob/main/packages/istanbul-lib-instrument/api.md
- https://github.com/istanbuljs/istanbuljs/tree/main/packages/istanbul-lib-source-maps
- https://github.com/istanbuljs/istanbuljs/tree/main/packages/istanbul-lib-coverage
- https://esbuild.github.io/api/#sourcemap
- https://www.electronjs.org/docs/latest/api/web-contents
  (executeJavaScriptInIsolatedWorld: world 0 and Electron isolated world 999)

Business tests run through the host run_evidence_v2 / run_coverage chain and
import launch() from launch.cjs. This launches the isolated instrumented app
identified by ACCEPTANCE_ELECTRON_APP; pass a fresh --user-data-dir to launch.
Use the actual window and preserve normal business assertions and test exit.
After the business command exits the adapter requests app.quit and waits for
final snapshots. Alternatively close the window normally. Bypassing launch()
or running the original npm start produces unavailable metrics, never zero.
No business test or scenario is supplied by this preparation.

The wrapper observes both renderer worlds and saves independent cumulative
snapshots keyed by document/world token. Poll snapshots overwrite earlier
snapshots for the same token; Istanbul merges different documents and processes.
pagehide sends a final navigation snapshot. Normal close and quit flush worlds
before destruction, then main. Every Electron PID has a lifecycle file. Forced
kill or missing lifecycle finalization yields incomplete metrics; a source with
no native snapshot remains unavailable. A vanished context cannot be recovered;
normal navigation is supported by pagehide but crashes, abrupt process exit,
new worker worlds, and applications opening external uninstrumented code are
outside complete collection guarantees. User-data and instrumented build copies
stay in the current local execution output, never product source.

Zero probes use only Istanbul-generated initial coverage data in an empty
Electron fixture in the same main / isolated preload / renderer contexts; they
do not execute app behavior. Both probes reload the same document once to check navigation snapshots.
Nonzero probes perform only startup, that reload, and normal quit; they do not click controls, save/delete notes, or assert business outcomes.
Raw snapshots must exist and finalization must succeed. probe.cjs is the adapter
reader; direct.cjs independently calls Istanbul APIs on identical native bytes.
Both readers are read-only. failure-paths.json records missing/no-start and
unfinished-collector fault injection at the reader boundary outside raw data.
These capability probe numbers must never enter business reports.

Application source coverage targets are main.ts/store.ts and
preload.ts/renderer.ts. src/index.html has no executable JavaScript (its script
reference is covered separately). build.mjs is executable build tooling, outside
the instrumented app; its disposition is unsupported and therefore preparation
is partial even if all four application targets pass. Changed-file and
changed-line metrics are unavailable for the supplied requirements-only baseline
because its frozen inventory has no PR delta. This does not redefine partial.

The previous ignored adapter and workflow remain frozen. This tracked copy keeps
the same directory depth, so project dependency resolution and source-map roots
remain unchanged. The final profile uses spec.runtime_manifest and
spec.probe_report; it does not depend on private legacy probe fields.
Build tooling is retained as unsupported in this attempt: the Electron
collector cannot observe its separate Node process. A dedicated build collector
is deferred rather than attributing application counts to build.mjs.

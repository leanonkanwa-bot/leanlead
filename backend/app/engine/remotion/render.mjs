#!/usr/bin/env node
/**
 * Remotion render entry point.
 * Called from Python: node render.mjs <manifest.json> <output.mp4>
 *
 * The manifest JSON contains everything needed:
 *   { videoSrc, zoomEntries, defaultZoom, durationFrames, fps, width, height }
 */
import { bundle } from "@remotion/bundler";
import { renderMedia, selectComposition } from "@remotion/renderer";
import { readFileSync } from "fs";
import { resolve, dirname } from "path";
import { fileURLToPath } from "url";

const __dirname = dirname(fileURLToPath(import.meta.url));

const [manifestPath, outputPath] = process.argv.slice(2);
if (!manifestPath || !outputPath) {
  console.error("Usage: node render.mjs <manifest.json> <output.mp4>");
  process.exit(1);
}

const manifest = JSON.parse(readFileSync(manifestPath, "utf-8"));
const {
  videoSrc,
  zoomEntries,
  defaultZoom,
  durationFrames,
  fps = 30,
  width = 1920,
  height = 1080,
} = manifest;

console.log(`[REMOTION] Bundling composition...`);
const bundleLocation = await bundle({
  entryPoint: resolve(__dirname, "src/index.ts"),
  webpackOverride: (config) => config,
});

console.log(`[REMOTION] Selecting composition ZoomSegment...`);
const composition = await selectComposition({
  serveUrl: bundleLocation,
  id: "ZoomSegment",
  inputProps: { videoSrc, zoomEntries, defaultZoom },
});

composition.durationInFrames = durationFrames;
composition.fps = fps;
composition.width = width;
composition.height = height;

console.log(`[REMOTION] Rendering ${durationFrames} frames at ${fps}fps (${width}x${height})...`);
await renderMedia({
  composition,
  serveUrl: bundleLocation,
  codec: "h264",
  outputLocation: resolve(outputPath),
  inputProps: { videoSrc, zoomEntries, defaultZoom },
  chromiumOptions: { disableWebSecurity: true },
  onProgress: ({ progress }) => {
    if (Math.round(progress * 100) % 10 === 0) {
      process.stdout.write(`\r[REMOTION] Progress: ${Math.round(progress * 100)}%`);
    }
  },
});

console.log(`\n[REMOTION] Done: ${outputPath}`);

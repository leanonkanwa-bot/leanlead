import { AbsoluteFill, OffthreadVideo, useCurrentFrame, useVideoConfig, staticFile } from "remotion";

export type ZoomEntry = {
  start: number;
  end: number;
  from: number;
  to: number;
  kind: "drift" | "punch_in" | "pull_out";
};

type Props = {
  videoSrc: string;
  zoomEntries: ZoomEntry[];
  defaultZoom: number;
};

function getZoomAtTime(timeSec: number, entries: ZoomEntry[], defaultZoom: number): number {
  for (const e of entries) {
    if (timeSec >= e.start && timeSec <= e.end) {
      const progress = (timeSec - e.start) / Math.max(0.001, e.end - e.start);
      if (e.kind === "punch_in" || e.kind === "pull_out") {
        const eased = progress * progress;
        return e.from + (e.to - e.from) * eased;
      }
      const eased = (1 - Math.cos(progress * Math.PI)) / 2;
      return e.from + (e.to - e.from) * eased;
    }
  }
  return defaultZoom;
}

export const ZoomSegment: React.FC<Props> = ({ videoSrc, zoomEntries, defaultZoom }) => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();
  const timeSec = frame / fps;

  const zoom = getZoomAtTime(timeSec, zoomEntries, defaultZoom);
  const scale = zoom;
  const translateX = -(scale - 1) * width / 2;
  const translateY = -(scale - 1) * height / 2;

  return (
    <AbsoluteFill style={{ backgroundColor: "black" }}>
      <div
        style={{
          width,
          height,
          transform: `translate(${translateX}px, ${translateY}px) scale(${scale})`,
          transformOrigin: "top left",
          overflow: "hidden",
        }}
      >
        <OffthreadVideo
          src={staticFile(videoSrc)}
          style={{ width: "100%", height: "100%" }}
        />
      </div>
    </AbsoluteFill>
  );
};

import { Composition } from "remotion";
import { ZoomSegment } from "./ZoomSegment";
import { z } from "zod";

const zoomEntrySchema = z.object({
  start: z.number(),
  end: z.number(),
  from: z.number(),
  to: z.number(),
  kind: z.enum(["drift", "punch_in", "pull_out"]),
});

const propsSchema = z.object({
  videoSrc: z.string(),
  zoomEntries: z.array(zoomEntrySchema),
  defaultZoom: z.number(),
});

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="ZoomSegment"
        component={ZoomSegment}
        durationInFrames={300}
        fps={30}
        width={1920}
        height={1080}
        schema={propsSchema}
        defaultProps={{
          videoSrc: "",
          zoomEntries: [],
          defaultZoom: 1.3,
        }}
        calculateMetadata={async ({ props }) => {
          return {
            durationInFrames: 300,
            fps: 30,
            width: 1920,
            height: 1080,
            props,
          };
        }}
      />
    </>
  );
};

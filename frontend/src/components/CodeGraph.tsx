import { useEffect, useMemo, useRef, useState } from "react";
import ForceGraph2D, {
  type ForceGraphMethods,
  type LinkObject,
  type NodeObject,
} from "react-force-graph-2d";
import type { CodeGraph, CodeGraphLink, CodeGraphNode } from "../api";

type CodeGraphMode = "compact" | "full";
type GraphNode = NodeObject<CodeGraphNode>;
type GraphLink = LinkObject<CodeGraphNode, CodeGraphLink>;

interface CodeGraphProps {
  data: CodeGraph;
  mode: CodeGraphMode;
}

const LANGUAGE_COLOR_KEYS: Record<string, keyof GraphColors> = {
  javascript: "chart4",
  typescript: "chart2",
  tsx: "chart2",
  jsx: "chart4",
  python: "chart1",
  markdown: "chart5",
  md: "chart5",
  css: "chart3",
  html: "chart4",
  rust: "destructive",
  go: "chart2",
  java: "chart4",
};

interface GraphColors {
  chart1: string;
  chart2: string;
  chart3: string;
  chart4: string;
  chart5: string;
  destructive: string;
  foreground: string;
  mutedForeground: string;
  fontFamily: string;
}

const DEFAULT_COLORS: GraphColors = {
  chart1: "#72e3ad",
  chart2: "#3b82f6",
  chart3: "#8b5cf6",
  chart4: "#f59e0b",
  chart5: "#10b981",
  destructive: "#ca3214",
  foreground: "#171717",
  mutedForeground: "#707070",
  fontFamily: "Outfit, sans-serif",
};

function languageColor(language: string | null | undefined, colors: GraphColors): string {
  if (!language) return colors.mutedForeground;
  const key = LANGUAGE_COLOR_KEYS[language.toLowerCase()];
  return key ? colors[key] : colors.mutedForeground;
}

function endpointId(endpoint: string | number | { id?: string | number } | null | undefined): string {
  return typeof endpoint === "object" && endpoint !== null ? String(endpoint.id) : String(endpoint);
}

function cssVar(styles: CSSStyleDeclaration, name: string, fallback: string): string {
  return styles.getPropertyValue(name).trim() || fallback;
}

function withAlpha(color: string, alpha: number): string {
  const canvas = document.createElement("canvas");
  const ctx = canvas.getContext("2d");
  if (!ctx) return color;
  ctx.fillStyle = color;
  const normalized = ctx.fillStyle;

  if (normalized.startsWith("#")) {
    const hex = normalized.slice(1);
    const value = hex.length === 3
      ? hex.split("").map((part) => part + part).join("")
      : hex.padEnd(6, "0").slice(0, 6);
    const r = parseInt(value.slice(0, 2), 16);
    const g = parseInt(value.slice(2, 4), 16);
    const b = parseInt(value.slice(4, 6), 16);
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
  }

  const rgbMatch = normalized.match(/^rgba?\(([^)]+)\)$/);
  if (!rgbMatch) return normalized;
  const [r, g, b] = rgbMatch[1].split(",").slice(0, 3).map((part) => part.trim());
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

function useGraphColors(): GraphColors {
  const [colors, setColors] = useState(DEFAULT_COLORS);

  useEffect(() => {
    const styles = getComputedStyle(document.body);
    setColors({
      chart1: cssVar(styles, "--chart-1", DEFAULT_COLORS.chart1),
      chart2: cssVar(styles, "--chart-2", DEFAULT_COLORS.chart2),
      chart3: cssVar(styles, "--chart-3", DEFAULT_COLORS.chart3),
      chart4: cssVar(styles, "--chart-4", DEFAULT_COLORS.chart4),
      chart5: cssVar(styles, "--chart-5", DEFAULT_COLORS.chart5),
      destructive: cssVar(styles, "--destructive", DEFAULT_COLORS.destructive),
      foreground: cssVar(styles, "--foreground", DEFAULT_COLORS.foreground),
      mutedForeground: cssVar(styles, "--muted-foreground", DEFAULT_COLORS.mutedForeground),
      fontFamily: cssVar(styles, "--font-sans", DEFAULT_COLORS.fontFamily),
    });
  }, []);

  return colors;
}

function useElementSize<T extends HTMLElement>() {
  const ref = useRef<T | null>(null);
  const [size, setSize] = useState({ width: 0, height: 0 });

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    const update = () => {
      setSize({
        width: Math.floor(el.clientWidth),
        height: Math.floor(el.clientHeight),
      });
    };

    update();
    const observer = new ResizeObserver(update);
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  return { ref, size };
}

export default function CodeGraph({ data, mode }: CodeGraphProps) {
  const graphRef = useRef<ForceGraphMethods<CodeGraphNode, CodeGraphLink>>();
  const [hoveredNode, setHoveredNode] = useState<GraphNode | null>(null);
  const [hoveredLink, setHoveredLink] = useState<GraphLink | null>(null);
  const { ref: wrapRef, size } = useElementSize<HTMLDivElement>();
  const colors = useGraphColors();
  const mutedNodeColor = useMemo(() => withAlpha(colors.mutedForeground, 0.28), [colors.mutedForeground]);
  const mutedLinkColor = useMemo(() => withAlpha(colors.mutedForeground, 0.18), [colors.mutedForeground]);
  const defaultLinkColor = useMemo(() => withAlpha(colors.foreground, 0.42), [colors.foreground]);

  const graphData = useMemo(
    () => ({
      nodes: data.nodes.map((node) => ({ ...node })),
      links: data.links.map((link) => ({ ...link })),
    }),
    [data],
  );

  const connectedNodeIds = useMemo(() => {
    const ids = new Set<string>();
    if (hoveredNode) {
      ids.add(String(hoveredNode.id));
      graphData.links.forEach((link) => {
        const source = endpointId(link.source);
        const target = endpointId(link.target);
        if (source === String(hoveredNode.id)) ids.add(target);
        if (target === String(hoveredNode.id)) ids.add(source);
      });
    }
    if (hoveredLink) {
      ids.add(endpointId(hoveredLink.source));
      ids.add(endpointId(hoveredLink.target));
    }
    return ids;
  }, [graphData.links, hoveredLink, hoveredNode]);

  useEffect(() => {
    if (!graphRef.current || graphData.nodes.length === 0) return;
    const padding = mode === "full" ? 56 : 24;
    const timer = window.setTimeout(() => {
      graphRef.current?.zoomToFit(350, padding);
      const zoom = graphRef.current?.zoom();
      if (typeof zoom === "number" && zoom > 1.2) {
        graphRef.current?.zoom(1.2, 250);
      }
    }, 250);
    return () => window.clearTimeout(timer);
  }, [graphData.nodes.length, graphData.links.length, mode, size.width, size.height]);

  if (graphData.nodes.length === 0) {
    return <div className="code-graph-canvas code-graph-empty">No graph data available.</div>;
  }

  const highlighted = hoveredNode || hoveredLink;
  const nodeRelSize = mode === "full" ? 3.5 : 3;

  return (
    <div ref={wrapRef} className={`code-graph code-graph-${mode}`}>
      {size.width > 0 && size.height > 0 ? (
        <ForceGraph2D<CodeGraphNode, CodeGraphLink>
          ref={graphRef}
          graphData={graphData}
          width={size.width}
          height={size.height}
          backgroundColor="rgba(0,0,0,0)"
          nodeId="id"
          nodeRelSize={nodeRelSize}
          nodeVal={() => 1}
          nodeColor={(node) =>
            highlighted && !connectedNodeIds.has(String(node.id))
              ? mutedNodeColor
              : languageColor(node.language, colors)
          }
          nodeLabel={(node) =>
            `${node.label}${node.language ? ` (${node.language})` : ""}: ${node.symbol_count} symbols`
          }
          linkLabel={(link) => {
            const symbols = Array.isArray(link.symbols) ? link.symbols.join(", ") : "";
            return symbols || `${endpointId(link.source)} -> ${endpointId(link.target)}`;
          }}
          linkColor={(link) => {
            const isActive =
              hoveredLink === link ||
              (hoveredNode &&
                (endpointId(link.source) === String(hoveredNode.id) ||
                  endpointId(link.target) === String(hoveredNode.id)));
            if (highlighted && !isActive) {
              return mutedLinkColor;
            }
            return defaultLinkColor;
          }}
          linkWidth={(link) => {
            const active =
              hoveredLink === link ||
              (hoveredNode &&
                (endpointId(link.source) === String(hoveredNode.id) ||
                  endpointId(link.target) === String(hoveredNode.id)));
            return active ? 2.4 : Math.max(0.6, Math.min(3, link.weight || 1));
          }}
          linkDirectionalArrowLength={mode === "full" ? 4 : 0}
          linkDirectionalArrowRelPos={1}
          linkDirectionalParticles={mode === "full" ? 1 : 0}
          linkDirectionalParticleWidth={(link) => Math.max(1, Math.min(3, link.weight || 1))}
          linkDirectionalParticleSpeed={0.004}
          onNodeHover={(node) => setHoveredNode(node)}
          onLinkHover={(link) => setHoveredLink(link)}
          linkHoverPrecision={6}
          enableNodeDrag={mode === "full"}
          enableZoomInteraction={mode === "full"}
          enablePanInteraction={mode === "full"}
          cooldownTicks={mode === "full" ? 120 : 80}
          warmupTicks={mode === "full" ? 60 : 30}
          nodeCanvasObjectMode={() => "after"}
          nodeCanvasObject={(node, ctx, globalScale) => {
            const showLabel = hoveredNode?.id === node.id;
            if (!showLabel) return;

            const label = node.label;
            const fontSize = mode === "full" ? 12 / globalScale : 10 / globalScale;
            ctx.font = `${fontSize}px ${colors.fontFamily}`;
            ctx.fillStyle = colors.foreground;
            ctx.textAlign = "center";
            ctx.textBaseline = "top";
            ctx.fillText(label, node.x ?? 0, (node.y ?? 0) + 7);
          }}
        />
      ) : null}
    </div>
  );
}

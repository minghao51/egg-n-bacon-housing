/**
 * Catalog lineage graph (slice S9, SVG 15).
 *
 * Receives slim node/edge projections (S10-F1): placement, labels, links and
 * colours need only an id, a layer and a label per node plus a `from`/`to` pair
 * per edge, so the island no longer takes whole catalog datasets as props.
 */

import { useMemo } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  Handle,
  Position,
  MarkerType,
  type Node,
  type Edge,
  type NodeProps,
  type NodeTypes,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import type { CatalogDagEdge, CatalogDagNode } from "@/utils/catalog-payload";
import { LAYER_COLORS, datasetIdToSlug } from "@/types/catalog";

interface DagGraphProps {
  nodes: CatalogDagNode[];
  edges: CatalogDagEdge[];
  baseUrl: string;
}

const LAYER_ORDER = ["bronze", "silver", "gold", "platinum"];

interface CatalogNodeData {
  label: string;
  href: string;
  layer: string;
}

function CatalogNode({ data }: NodeProps) {
  // SAFETY: React Flow returns the `data` object this module attached to every
  // node in `initialNodes`, so these fields are always present strings; no other
  // producer creates a `catalog` node.
  const { label, href, layer } = data as unknown as CatalogNodeData;
  const color = LAYER_COLORS[layer] || "#64748b";
  return (
    <>
      <Handle
        type="target"
        position={Position.Left}
        style={{ background: color, width: 6, height: 6 }}
      />
      <a
        href={href}
        className="catalog-node"
        style={{
          background: `${color}25`,
          border: `1px solid ${color}`,
          color: "#e2e8f0",
          fontSize: 11,
          padding: "8px 12px",
          borderRadius: 6,
          display: "block",
          width: 196,
          textDecoration: "none",
          cursor: "pointer",
        }}
      >
        {label}
      </a>
      <Handle
        type="source"
        position={Position.Right}
        style={{ background: color, width: 6, height: 6 }}
      />
    </>
  );
}

// Defined at module scope so React Flow doesn't warn on re-creation.
const nodeTypes: NodeTypes = { catalog: CatalogNode };

export default function DagGraph({
  nodes: datasetNodes,
  edges,
  baseUrl,
}: DagGraphProps) {
  const { initialNodes, initialEdges, layerById } = useMemo(() => {
    // Filter to datasets that actually appear in edges
    const connectedIds = new Set<string>();
    for (const [from, to] of edges) {
      connectedIds.add(from);
      connectedIds.add(to);
    }

    // Build node list
    const nodes: Node[] = [];
    const dsByLayer: Map<string, CatalogDagNode[]> = new Map();

    // Node id → layer, so the minimap can colour a node without a dataset lookup.
    const layers: Map<string, string> = new Map();

    for (const ds of datasetNodes) {
      if (!connectedIds.has(ds.id)) continue;
      const layer = ds.layer;
      if (!dsByLayer.has(layer)) dsByLayer.set(layer, []);
      dsByLayer.get(layer)!.push(ds);
      layers.set(ds.id, layer);
    }

    const LAYER_X_GAP = 320;
    const NODE_Y_GAP = 60;

    for (const [layerIdx, layer] of LAYER_ORDER.entries()) {
      const layerDatasets = dsByLayer.get(layer) || [];
      if (layerDatasets.length === 0) continue;

      const x = layerIdx * LAYER_X_GAP + 50;

      for (let i = 0; i < layerDatasets.length; i++) {
        const ds = layerDatasets[i];
        const y = i * NODE_Y_GAP + 50;

        nodes.push({
          id: ds.id,
          type: "catalog",
          data: {
            label: ds.label || ds.id,
            href: `${baseUrl}${ds.layer}/${datasetIdToSlug(ds.id)}`,
            layer: ds.layer,
          },
          position: { x, y },
        });
      }
    }

    // Build edge list
    const flowEdges: Edge[] = edges.map(([source, target], idx) => ({
      id: `e-${idx}`,
      source,
      target,
      style: { stroke: "#64748b", strokeWidth: 1.5 },
      markerEnd: { type: MarkerType.ArrowClosed, color: "#64748b" },
    }));

    return { initialNodes: nodes, initialEdges: flowEdges, layerById: layers };
  }, [datasetNodes, edges, baseUrl]);

  const nodeCount = initialNodes.length;
  const edgeCount = initialEdges.length;

  return (
    <div className="space-y-2">
      <div className="text-sm text-muted-foreground">
        {nodeCount} nodes, {edgeCount} edges — click a node to inspect its
        dataset
      </div>
      <div
        style={{ height: Math.max(400, nodeCount * 30 + 100) }}
        className="border border-border rounded-lg overflow-hidden bg-card"
      >
        <ReactFlow
          nodes={initialNodes}
          edges={initialEdges}
          nodeTypes={nodeTypes}
          fitView
          fitViewOptions={{ padding: 0.2 }}
          defaultViewport={{ x: 0, y: 0, zoom: 0.8 }}
          nodesDraggable={false}
          nodesConnectable={false}
          elementsSelectable={true}
          proOptions={{ hideAttribution: true }}
        >
          <Background color="#334155" gap={20} />
          <Controls
            className="[&>button]:!bg-card [&>button]:!border-border [&>button]:!text-foreground [&>button:hover]:!bg-accent"
            showInteractive={false}
          />
          <MiniMap
            style={{ backgroundColor: "hsl(var(--card))" }}
            nodeColor={(node) =>
              LAYER_COLORS[layerById.get(node.id) ?? ""] || "#b45309"
            }
          />
        </ReactFlow>
      </div>

      {/* Legend */}
      <div className="flex flex-wrap gap-3">
        {LAYER_ORDER.map((layer) => (
          <div
            key={layer}
            className="flex items-center gap-1.5 text-xs text-muted-foreground"
          >
            <div
              className="h-3 w-3 rounded"
              style={{ backgroundColor: LAYER_COLORS[layer] }}
            />
            {layer.charAt(0).toUpperCase() + layer.slice(1)}
          </div>
        ))}
      </div>
    </div>
  );
}

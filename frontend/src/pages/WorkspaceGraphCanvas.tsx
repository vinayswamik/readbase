import type { MouseEvent, ReactNode, RefObject } from "react";

import type { HierarchyNode } from "../types";

export type Viewport = {
  x: number;
  y: number;
  scale: number;
};

export type BoardSize = {
  width: number;
  height: number;
};

export type EdgeSegment = {
  connectionId: string;
  x: number;
  y: number;
  length: number;
  angle: number;
};

export type NodeEditAnchor = {
  nodeId: string;
  offsetX: number;
  offsetY: number;
};

export function WorkspaceGraphCanvas({
  workspaceName,
  graphRevision,
  boardRef,
  nodes,
  visibleNodes,
  selectedNodeId,
  nodeEditAnchor,
  viewport,
  edgeSegments,
  chatOpen,
  messageCount,
  children,
  onBack,
  onAddNode,
  onZoom,
  onViewportReset,
  onBoardMouseDown,
  onBoardMouseMove,
  onBoardMouseUp,
  onNodeClick,
  onEditNode,
  onOpenChat,
}: {
  workspaceName: string;
  graphRevision: number;
  boardRef: RefObject<HTMLDivElement | null>;
  nodes: HierarchyNode[];
  visibleNodes: HierarchyNode[];
  selectedNodeId: string | null;
  nodeEditAnchor: NodeEditAnchor | null;
  viewport: Viewport;
  edgeSegments: EdgeSegment[];
  chatOpen: boolean;
  messageCount: number;
  children: ReactNode;
  onBack: () => void;
  onAddNode: () => void;
  onZoom: (delta: number) => void;
  onViewportReset: () => void;
  onBoardMouseDown: (event: MouseEvent<HTMLDivElement>) => void;
  onBoardMouseMove: (event: MouseEvent<HTMLDivElement>) => void;
  onBoardMouseUp: () => void;
  onNodeClick: (event: MouseEvent<HTMLButtonElement>, node: HierarchyNode) => void;
  onEditNode: (node: HierarchyNode) => void;
  onOpenChat: () => void;
}) {
  return (
    <section className="graph-stage" aria-label="Hierarchy graph board">
      <div className="graph-stage-topbar">
        <button type="button" className="graph-back-button" onClick={onBack}>
          Back
        </button>
        <div className="graph-stage-title">
          <strong>{workspaceName}</strong>
          <span>Hierarchy graph</span>
        </div>
      </div>
      <div className="graph-toolbar" aria-label="Board controls">
        <button type="button" className="graph-toolbar-add-node" onClick={onAddNode}>
          Add node
        </button>
        <span className="graph-toolbar-divider" aria-hidden="true" />
        <button type="button" onClick={() => onZoom(0.1)} aria-label="Zoom in">
          +
        </button>
        <button type="button" onClick={() => onZoom(-0.1)} aria-label="Zoom out">
          -
        </button>
        <button type="button" onClick={onViewportReset}>
          Reset
        </button>
      </div>
      <div
        ref={boardRef}
        key={graphRevision}
        className="graph-board"
        onMouseDown={onBoardMouseDown}
        onMouseMove={onBoardMouseMove}
        onMouseUp={onBoardMouseUp}
        onMouseLeave={onBoardMouseUp}
        onWheel={(event) => {
          event.preventDefault();
          onZoom(event.deltaY > 0 ? -0.08 : 0.08);
        }}
        onContextMenu={(event) => event.preventDefault()}
      >
        {!nodes.length ? (
          <div className="graph-empty">
            Use Add node in the toolbar to start the hierarchy.
          </div>
        ) : null}
        <div
          className="graph-canvas"
          style={{
            transform: `translate(${viewport.x}px, ${viewport.y}px) scale(${viewport.scale})`,
          }}
        >
          <div className="graph-edges">
            {edgeSegments.map((edge) => (
              <GraphEdge key={edge.connectionId} edge={edge} />
            ))}
          </div>
          {visibleNodes.map((node) => (
            <div
              key={node.node_id}
              className="graph-node-shell"
              style={{ left: node.x, top: node.y }}
            >
              <button
                type="button"
                className={`graph-node${node.node_id === selectedNodeId ? " selected" : ""}`}
                onClick={(event) => onNodeClick(event, node)}
              >
                <strong>{node.display_name}</strong>
                <span>{node.assigned_user_name || node.assigned_user_email || "Assigned user"}</span>
              </button>
              {nodeEditAnchor?.nodeId === node.node_id ? (
                <button
                  type="button"
                  className="graph-node-edit-button"
                  style={{
                    left: nodeEditAnchor.offsetX,
                    top: nodeEditAnchor.offsetY,
                  }}
                  onClick={(event) => {
                    event.stopPropagation();
                    onEditNode(node);
                  }}
                >
                  Edit
                </button>
              ) : null}
            </div>
          ))}
        </div>
      </div>
      {children}
      {!chatOpen ? (
        <button type="button" className="floating-ask-button" onClick={onOpenChat}>
          Ask
          {messageCount ? <span>{messageCount}</span> : null}
        </button>
      ) : null}
    </section>
  );
}

function GraphEdge({ edge }: { edge: EdgeSegment }) {
  return (
    <div
      className="graph-edge"
      style={{
        left: edge.x,
        top: edge.y,
        width: edge.length,
        transform: `rotate(${edge.angle}rad)`,
      }}
    />
  );
}

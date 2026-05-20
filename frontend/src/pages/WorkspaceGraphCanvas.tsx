import type { MouseEvent, ReactNode, RefObject } from "react";

import type { AuthUser, HierarchyNode } from "../types";

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

export function WorkspaceGraphCanvas({
  userRole,
  panelOpen,
  graphRevision,
  boardRef,
  nodes,
  visibleNodes,
  selectedNodeId,
  viewport,
  edgeSegments,
  chatOpen,
  messageCount,
  children,
  onPanelToggle,
  onZoom,
  onViewportReset,
  onBoardMouseDown,
  onBoardMouseMove,
  onBoardMouseUp,
  onNodeMouseDown,
  onOpenChat,
}: {
  userRole: AuthUser["role"];
  panelOpen: boolean;
  graphRevision: number;
  boardRef: RefObject<HTMLDivElement | null>;
  nodes: HierarchyNode[];
  visibleNodes: HierarchyNode[];
  selectedNodeId: string | null;
  viewport: Viewport;
  edgeSegments: EdgeSegment[];
  chatOpen: boolean;
  messageCount: number;
  children: ReactNode;
  onPanelToggle: () => void;
  onZoom: (delta: number) => void;
  onViewportReset: () => void;
  onBoardMouseDown: (event: MouseEvent<HTMLDivElement>) => void;
  onBoardMouseMove: (event: MouseEvent<HTMLDivElement>) => void;
  onBoardMouseUp: (event: MouseEvent<HTMLDivElement>) => void;
  onNodeMouseDown: (event: MouseEvent<HTMLButtonElement>, node: HierarchyNode) => void;
  onOpenChat: () => void;
}) {
  return (
    <section className="graph-stage" aria-label="Hierarchy graph board">
      <button
        type="button"
        className="panel-toggle"
        aria-expanded={panelOpen}
        onClick={onPanelToggle}
      >
        {panelOpen ? "Hide panel" : "Show panel"}
      </button>
      <div className="graph-toolbar" aria-label="Board controls">
        <button type="button" onClick={() => onZoom(0.1)}>
          +
        </button>
        <button type="button" onClick={() => onZoom(-0.1)}>
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
            {userRole === "admin"
              ? "Create a parent node from the panel to start the hierarchy."
              : "The board is empty. Wait for an admin to create a parent node."}
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
            <button
              key={node.node_id}
              type="button"
              className={`graph-node${node.node_id === selectedNodeId ? " selected" : ""}`}
              style={{ left: node.x, top: node.y }}
              onMouseDown={(event) => onNodeMouseDown(event, node)}
            >
              <strong>{node.display_name}</strong>
              <span>{node.assigned_user_name || node.assigned_user_email || "Assigned user"}</span>
            </button>
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

import type { MouseEvent, ReactNode, RefObject } from "react";

import userPlusIconMarkup from "../assets/icons/user-plus.svg?raw";

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
        <div
          className="graph-toolbar-cluster"
          aria-label="Board controls"
          onMouseDown={(event) => event.stopPropagation()}
        >
          <div className="graph-toolbar graph-toolbar-circle">
            <button
              type="button"
              className="graph-toolbar-add-node"
              onClick={onAddNode}
              aria-label="Add User"
              data-tooltip="Add User"
            >
              <AddNodeIcon />
            </button>
          </div>
          <div className="graph-toolbar">
            <div className="graph-toolbar-view" role="group" aria-label="View controls">
              <button
                type="button"
                onClick={() => onZoom(-0.1)}
                aria-label="Zoom out"
                data-tooltip="Zoom out"
              >
                −
              </button>
              <button
                type="button"
                onClick={() => onZoom(0.1)}
                aria-label="Zoom in"
                data-tooltip="Zoom in"
              >
                +
              </button>
              <button
                type="button"
                className="graph-toolbar-reset"
                aria-label="Reset view"
                data-tooltip="Reset view"
                onClick={onViewportReset}
              >
                <ResetViewportIcon />
              </button>
            </div>
          </div>
        </div>
        {!nodes.length ? (
          <div className="graph-empty">
            Use Add User in the toolbar to start the hierarchy.
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
        <button
          type="button"
          className="floating-ask-button"
          onClick={onOpenChat}
          aria-label="Ask"
        >
          <ChatIcon />
          {messageCount ? <span className="floating-ask-button-badge">{messageCount}</span> : null}
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

function ChatIcon() {
  return (
    <svg className="floating-ask-button-icon" viewBox="0 0 24 24" focusable="false" aria-hidden="true">
      <path
        d="M7.5 6.75h9a2.25 2.25 0 0 1 2.25 2.25v6.5a2.25 2.25 0 0 1-2.25 2.25h-5.1l-3.18 2.6a.75.75 0 0 1-1.22-.6v-2H7.5a2.25 2.25 0 0 1-2.25-2.25v-6.5A2.25 2.25 0 0 1 7.5 6.75z"
        fill="none"
        stroke="currentColor"
        strokeLinejoin="round"
        strokeWidth="1.75"
      />
    </svg>
  );
}

function AddNodeIcon() {
  return (
    <span
      className="graph-toolbar-add-node-icon"
      aria-hidden="true"
      dangerouslySetInnerHTML={{ __html: userPlusIconMarkup }}
    />
  );
}

function ResetViewportIcon() {
  return (
    <svg viewBox="0 0 24 24" focusable="false" aria-hidden="true">
      <circle cx="12" cy="12" r="7.25" fill="none" stroke="currentColor" strokeWidth="1.75" />
      <path
        d="M12 5.5v2.75M12 15.75V18.5M5.5 12h2.75M15.75 12H18.5"
        fill="none"
        stroke="currentColor"
        strokeLinecap="round"
        strokeWidth="1.75"
      />
      <circle cx="12" cy="12" r="1.75" fill="currentColor" />
    </svg>
  );
}

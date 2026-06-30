export const DOCKED_MODAL_WIDTH = 560;
export const DOCKED_MODAL_PREFERRED_HEIGHT = 520;
const VIEWPORT_PADDING = 12;
const ANCHOR_GAP = 12;

export type ConnectorModalDockAnchor = {
  button: DOMRectReadOnly;
  panel: DOMRectReadOnly;
};

export function computeManageAnchorFromButton(
  button: HTMLElement,
): ConnectorModalDockAnchor {
  const buttonRect = button.getBoundingClientRect();
  const panelElement = button.closest(".workspace-sources-panel");
  const panelRect = panelElement?.getBoundingClientRect() ?? buttonRect;
  return { button: buttonRect, panel: panelRect };
}

export function getViewportDockedModalHeight(
  preferredHeight = DOCKED_MODAL_PREFERRED_HEIGHT,
): number {
  return Math.max(
    240,
    Math.min(preferredHeight, window.innerHeight - VIEWPORT_PADDING * 2),
  );
}

export function computeDockedConnectorModalPosition(
  anchor: ConnectorModalDockAnchor,
  options?: { modalHeight?: number },
) {
  const reservedHeight = options?.modalHeight ?? 80;
  const panelEdgeLeft = anchor.panel.right + ANCHOR_GAP;
  const viewportMaxLeft = window.innerWidth - VIEWPORT_PADDING - DOCKED_MODAL_WIDTH;
  const left = Math.max(VIEWPORT_PADDING, Math.min(panelEdgeLeft, viewportMaxLeft));

  const top = Math.max(
    VIEWPORT_PADDING,
    Math.min(anchor.button.top, window.innerHeight - VIEWPORT_PADDING - reservedHeight),
  );

  return { top, left };
}

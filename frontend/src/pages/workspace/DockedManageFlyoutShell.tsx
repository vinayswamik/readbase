import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { createPortal } from "react-dom";

import { useDismissOnOutsideInteraction } from "../homepage/useDismissOnOutsideInteraction";
import {
  computeDockedConnectorModalPosition,
  getViewportDockedModalHeight,
  type ConnectorModalDockAnchor,
} from "./connectors/connectorModalPosition";

const DOCKED_MODAL_MOTION_MS = 220;
const MANAGE_BUTTON_IGNORE_SELECTOR = ".workspace-sources-manage, .workspace-sources-connect";

export type DockedManageFlyoutVariant = "connector" | "document";

export function DockedManageFlyoutShell({
  open,
  variant,
  dockAnchor,
  onClose,
  onAnimatedCloseChange,
  modalClassName,
  ariaLabelledBy,
  children,
}: {
  open: boolean;
  variant: DockedManageFlyoutVariant;
  dockAnchor: ConnectorModalDockAnchor | null;
  onClose: () => void;
  onAnimatedCloseChange?: (requestClose: (() => void) | null) => void;
  modalClassName?: string;
  ariaLabelledBy: string;
  children: ReactNode;
}) {
  const modalRef = useRef<HTMLDivElement>(null);
  const wasOpenRef = useRef(false);
  const [dockMotion, setDockMotion] = useState<"entering" | "open" | "closing">("entering");

  const requestClose = useCallback(() => {
    setDockMotion((current) => (current === "closing" ? current : "closing"));
  }, []);

  useEffect(() => {
    onAnimatedCloseChange?.(requestClose);
    return () => {
      onAnimatedCloseChange?.(null);
    };
  }, [onAnimatedCloseChange, requestClose]);

  useEffect(() => {
    if (!open) {
      wasOpenRef.current = false;
      return;
    }
    if (wasOpenRef.current) {
      return;
    }
    wasOpenRef.current = true;
    setDockMotion("entering");
    const frame = window.requestAnimationFrame(() => {
      setDockMotion("open");
    });
    return () => {
      window.cancelAnimationFrame(frame);
    };
  }, [open]);

  useEffect(() => {
    if (!open || dockMotion !== "closing") {
      return;
    }
    const modal = modalRef.current;
    const finishClose = () => {
      onClose();
    };
    const timer = window.setTimeout(finishClose, DOCKED_MODAL_MOTION_MS + 80);
    if (!modal) {
      return () => {
        window.clearTimeout(timer);
      };
    }
    const handleTransitionEnd = (event: TransitionEvent) => {
      if (event.target !== modal) {
        return;
      }
      window.clearTimeout(timer);
      finishClose();
    };
    modal.addEventListener("transitionend", handleTransitionEnd);
    return () => {
      window.clearTimeout(timer);
      modal.removeEventListener("transitionend", handleTransitionEnd);
    };
  }, [dockMotion, onClose, open]);

  useDismissOnOutsideInteraction(
    open && dockMotion === "open",
    modalRef,
    requestClose,
    MANAGE_BUTTON_IGNORE_SELECTOR,
  );

  const dockedStyle = useMemo(() => {
    if (!open || !dockAnchor) {
      return undefined;
    }
    if (variant === "document") {
      const modalHeight = getViewportDockedModalHeight();
      const { top, left } = computeDockedConnectorModalPosition(dockAnchor, { modalHeight });
      return {
        top: `${top}px`,
        left: `${left}px`,
        height: `${modalHeight}px`,
        maxHeight: `${modalHeight}px`,
      };
    }
    const { top, left } = computeDockedConnectorModalPosition(dockAnchor);
    return {
      top: `${top}px`,
      left: `${left}px`,
      maxHeight: `calc(100dvh - ${top}px - 12px)`,
    };
  }, [dockAnchor, open, variant]);

  if (!open) {
    return null;
  }

  const dockMotionClass =
    dockMotion === "open"
      ? "connector-modal-dock-open"
      : dockMotion === "closing"
        ? "connector-modal-dock-closing"
        : "connector-modal-dock-entering";

  const backdropClassName =
    variant === "document"
      ? "connector-modal-backdrop connector-modal-backdrop-docked document-manage-modal-backdrop"
      : "connector-modal-backdrop connector-modal-backdrop-docked";

  return createPortal(
    <div className={`${backdropClassName} ${dockMotionClass}`} style={dockedStyle} role="presentation">
      <div
        ref={modalRef}
        className={modalClassName ? `connector-modal ${modalClassName}` : "connector-modal"}
        role="dialog"
        aria-modal="true"
        aria-labelledby={ariaLabelledBy}
      >
        {children}
      </div>
    </div>,
    document.body,
  );
}

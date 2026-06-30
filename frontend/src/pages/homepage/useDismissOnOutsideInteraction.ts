import { useEffect, type RefObject } from "react";

export function useDismissOnOutsideInteraction(
  open: boolean,
  containerRef: RefObject<HTMLElement | null>,
  onDismiss: () => void,
  ignoreSelector?: string,
) {
  useEffect(() => {
    if (!open) {
      return;
    }
    const handleDocumentClick = (event: MouseEvent) => {
      const target = event.target;
      if (!(target instanceof Node)) {
        return;
      }
      if (target instanceof Element && ignoreSelector && target.closest(ignoreSelector)) {
        return;
      }
      if (!containerRef.current?.contains(target)) {
        onDismiss();
      }
    };
    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onDismiss();
      }
    };

    document.addEventListener("mousedown", handleDocumentClick);
    document.addEventListener("keydown", handleEscape);
    return () => {
      document.removeEventListener("mousedown", handleDocumentClick);
      document.removeEventListener("keydown", handleEscape);
    };
  }, [open, containerRef, onDismiss, ignoreSelector]);
}

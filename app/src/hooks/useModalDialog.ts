/**
 * Shared modal-dialog keyboard contract (slice S10).
 *
 * Opened dialogs must move focus inside, keep Tab inside, close on Escape,
 * lock body scroll and restore focus to the trigger. The visuals live in each
 * modal; this hook owns only that behaviour so the leaderboard metric guide,
 * the segment evidence guide and the mobile filters sheet cannot drift apart.
 */

import { useEffect, useRef } from "react";

const FOCUSABLE =
  'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

/**
 * Open dialog identities, innermost last. Only the top dialog handles Escape
 * and Tab, and body scroll/focus are restored only when the last dialog closes.
 * This keeps nested dialogs from closing together or fighting over the page.
 */
const dialogStack: symbol[] = [];
let overflowBefore: string | null = null;

export function useModalDialog(isOpen: boolean, onClose: () => void) {
  const panelRef = useRef<HTMLDivElement | null>(null);
  const onCloseRef = useRef(onClose);
  const dialogId = useRef(Symbol("dialog"));

  useEffect(() => {
    onCloseRef.current = onClose;
  }, [onClose]);

  useEffect(() => {
    if (!isOpen) return;

    const panel = panelRef.current;
    const id = dialogId.current;
    const previous =
      document.activeElement instanceof HTMLElement
        ? document.activeElement
        : null;
    if (dialogStack.length === 0) {
      overflowBefore = document.body.style.overflow;
      document.body.style.overflow = "hidden";
    }
    dialogStack.push(id);

    const focusableItems = (): HTMLElement[] => {
      if (!panel) return [];
      return Array.from(panel.querySelectorAll<HTMLElement>(FOCUSABLE)).filter(
        (element) => element.offsetParent !== null,
      );
    };

    const first = focusableItems()[0] ?? panel;
    first?.focus();

    const handleKeyDown = (event: KeyboardEvent) => {
      if (dialogStack[dialogStack.length - 1] !== id) return;
      if (event.key === "Escape") {
        event.preventDefault();
        onCloseRef.current();
        return;
      }
      if (event.key !== "Tab") return;

      const items = focusableItems();
      if (items.length === 0) {
        event.preventDefault();
        panel?.focus();
        return;
      }

      const firstItem = items[0];
      const lastItem = items[items.length - 1];
      const active = document.activeElement;
      const inside = panel?.contains(active) ?? false;

      if (event.shiftKey) {
        if (!inside || active === firstItem) {
          event.preventDefault();
          lastItem.focus();
        }
        return;
      }
      if (!inside || active === lastItem) {
        event.preventDefault();
        firstItem.focus();
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      const index = dialogStack.lastIndexOf(id);
      const wasTop = index === dialogStack.length - 1;
      if (index !== -1) dialogStack.splice(index, 1);
      if (dialogStack.length === 0) {
        document.body.style.overflow = overflowBefore ?? "";
        overflowBefore = null;
      }
      if (wasTop && previous?.isConnected) previous.focus();
    };
  }, [isOpen]);

  return panelRef;
}

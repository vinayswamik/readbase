import { useCallback, useEffect, useRef } from "react";

import { CONNECTORS } from "../workspace/connectors/connectors";
import { ConnectorLogo } from "../workspace/connectors/ConnectorLogo";

const MARQUEE_SET_COUNT = 2;

function scaleForDistance(distanceRatio: number): number {
  const clamped = Math.min(Math.max(distanceRatio, 0), 1);
  return 1 - clamped * 0.5;
}

function opacityForDistance(distanceRatio: number): number {
  const clamped = Math.min(Math.max(distanceRatio, 0), 1);
  return 1 - clamped * 0.55;
}

export function HomeConnectorMarquee() {
  const viewportRef = useRef<HTMLDivElement>(null);
  const itemRefs = useRef(new Map<string, HTMLSpanElement>());

  useEffect(() => {
    const viewport = viewportRef.current;
    if (!viewport) {
      return;
    }

    const motionQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
    if (motionQuery.matches) {
      return;
    }

    let frameId = 0;

    const updateItemTransforms = () => {
      const viewportRect = viewport.getBoundingClientRect();
      const centerX = viewportRect.left + viewportRect.width / 2;
      const halfWidth = viewportRect.width / 2;

      itemRefs.current.forEach((element) => {
        const itemRect = element.getBoundingClientRect();
        const itemCenterX = itemRect.left + itemRect.width / 2;
        const distanceRatio = halfWidth > 0 ? Math.abs(itemCenterX - centerX) / halfWidth : 0;
        element.style.transform = `scale(${scaleForDistance(distanceRatio)})`;
        element.style.opacity = String(opacityForDistance(distanceRatio));
      });

      frameId = window.requestAnimationFrame(updateItemTransforms);
    };

    frameId = window.requestAnimationFrame(updateItemTransforms);
    return () => window.cancelAnimationFrame(frameId);
  }, []);

  const registerItem = useCallback(
    (key: string) => (element: HTMLSpanElement | null) => {
      if (element) {
        itemRefs.current.set(key, element);
        return;
      }
      itemRefs.current.delete(key);
    },
    [],
  );

  return (
    <footer className="home-connector-marquee" aria-hidden="true">
      <div className="home-connector-marquee-viewport" ref={viewportRef}>
        <div className="home-connector-marquee-track">
          {Array.from({ length: MARQUEE_SET_COUNT }, (_, setIndex) => (
            <div className="home-connector-marquee-group" key={setIndex}>
              {CONNECTORS.map((connector) => {
                const itemKey = `${setIndex}-${connector.id}`;
                return (
                  <span
                    className="home-connector-marquee-item"
                    key={itemKey}
                    ref={registerItem(itemKey)}
                  >
                    <ConnectorLogo connectorId={connector.id} />
                  </span>
                );
              })}
            </div>
          ))}
        </div>
      </div>
    </footer>
  );
}

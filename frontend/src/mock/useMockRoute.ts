import { useCallback, useEffect, useState } from "react";

import { isMockApi } from "./dev";
import { pushMockRoute, readMockRoute, replaceMockRoute, type MockRoute } from "./navigation";

export function useMockRoute(): [
  MockRoute,
  (route: MockRoute) => void,
  (route: MockRoute) => void,
] {
  const [route, setRoute] = useState<MockRoute>(() => readMockRoute());

  useEffect(() => {
    if (!isMockApi()) {
      return;
    }

    const syncFromBrowser = () => {
      setRoute(readMockRoute());
    };

    if (window.location.pathname === "/") {
      replaceMockRoute({ screen: "login" });
      setRoute({ screen: "login" });
    }

    window.addEventListener("popstate", syncFromBrowser);
    return () => {
      window.removeEventListener("popstate", syncFromBrowser);
    };
  }, []);

  const navigate = useCallback((nextRoute: MockRoute) => {
    if (!isMockApi()) {
      return;
    }
    pushMockRoute(nextRoute);
    setRoute(nextRoute);
  }, []);

  const replaceNavigate = useCallback((nextRoute: MockRoute) => {
    if (!isMockApi()) {
      return;
    }
    replaceMockRoute(nextRoute);
    setRoute(nextRoute);
  }, []);

  return [route, navigate, replaceNavigate];
}

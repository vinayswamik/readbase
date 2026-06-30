import { useCallback, useEffect, useState } from "react";

import {
  pushAppRoute,
  readAppRoute,
  replaceAppRoute,
  routesEqual,
  type AppRoute,
} from "./appRoute";

export function useAppRoute(): [
  AppRoute,
  (route: AppRoute) => void,
  (route: AppRoute) => void,
] {
  const [route, setRoute] = useState<AppRoute>(() => readAppRoute());

  useEffect(() => {
    const syncFromBrowser = () => {
      setRoute(readAppRoute());
    };

    window.addEventListener("popstate", syncFromBrowser);
    return () => {
      window.removeEventListener("popstate", syncFromBrowser);
    };
  }, []);

  const navigate = useCallback((nextRoute: AppRoute) => {
    pushAppRoute(nextRoute);
    setRoute((currentRoute) => (routesEqual(currentRoute, nextRoute) ? currentRoute : nextRoute));
  }, []);

  const replaceNavigate = useCallback((nextRoute: AppRoute) => {
    replaceAppRoute(nextRoute);
    setRoute((currentRoute) => (routesEqual(currentRoute, nextRoute) ? currentRoute : nextRoute));
  }, []);

  return [route, navigate, replaceNavigate];
}

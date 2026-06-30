export type AppRoute =
  | { screen: "login" }
  | { screen: "workspaces" }
  | { screen: "workspace"; workspaceId: string };

/** @deprecated Use AppRoute */
export type MockRoute = AppRoute;

export function readAppRoute(pathname = window.location.pathname): AppRoute {
  if (pathname === "/login" || pathname === "/") {
    return { screen: "login" };
  }

  const workspaceMatch = pathname.match(/^\/workspaces\/([^/]+)\/?$/);
  if (workspaceMatch) {
    return {
      screen: "workspace",
      workspaceId: decodeURIComponent(workspaceMatch[1]),
    };
  }

  if (pathname === "/workspaces" || pathname === "/workspaces/") {
    return { screen: "workspaces" };
  }

  return { screen: "login" };
}

/** @deprecated Use readAppRoute */
export const readMockRoute = readAppRoute;

export function appRouteToPath(route: AppRoute): string {
  if (route.screen === "login") {
    return "/login";
  }
  if (route.screen === "workspaces") {
    return "/workspaces";
  }
  return `/workspaces/${encodeURIComponent(route.workspaceId)}`;
}

/** @deprecated Use appRouteToPath */
export const mockRouteToPath = appRouteToPath;

export function routesEqual(left: AppRoute, right: AppRoute): boolean {
  if (left.screen !== right.screen) {
    return false;
  }
  if (left.screen === "workspace" && right.screen === "workspace") {
    return left.workspaceId === right.workspaceId;
  }
  return true;
}

export function pushAppRoute(route: AppRoute): void {
  const path = appRouteToPath(route);
  if (window.location.pathname + window.location.search === path) {
    return;
  }
  window.history.pushState({ appRoute: route }, "", path);
}

/** @deprecated Use pushAppRoute */
export const pushMockRoute = pushAppRoute;

export function replaceAppRoute(route: AppRoute): void {
  const path = appRouteToPath(route);
  if (window.location.pathname + window.location.search === path) {
    return;
  }
  window.history.replaceState({ appRoute: route }, "", path);
}

/** @deprecated Use replaceAppRoute */
export const replaceMockRoute = replaceAppRoute;

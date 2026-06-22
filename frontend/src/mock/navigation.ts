export type MockPanel = "invites" | "sources";

export type MockRoute =
  | { screen: "login" }
  | { screen: "workspaces" }
  | { screen: "workspace"; workspaceId: string; panel?: MockPanel };

export function readMockRoute(pathname = window.location.pathname, search = window.location.search): MockRoute {
  const params = new URLSearchParams(search);
  const panel = params.get("panel");
  const normalizedPanel = panel === "invites" || panel === "sources" ? panel : undefined;

  if (pathname === "/login" || pathname === "/") {
    return { screen: "login" };
  }

  const workspaceMatch = pathname.match(/^\/workspaces\/([^/]+)\/?$/);
  if (workspaceMatch) {
    return {
      screen: "workspace",
      workspaceId: decodeURIComponent(workspaceMatch[1]),
      panel: normalizedPanel,
    };
  }

  if (pathname === "/workspaces" || pathname === "/workspaces/") {
    return { screen: "workspaces" };
  }

  return { screen: "login" };
}

export function mockRouteToPath(route: MockRoute): string {
  if (route.screen === "login") {
    return "/login";
  }
  if (route.screen === "workspaces") {
    return "/workspaces";
  }
  const base = `/workspaces/${encodeURIComponent(route.workspaceId)}`;
  if (!route.panel) {
    return base;
  }
  return `${base}?panel=${route.panel}`;
}

export function pushMockRoute(route: MockRoute): void {
  const path = mockRouteToPath(route);
  if (window.location.pathname + window.location.search === path) {
    return;
  }
  window.history.pushState({ mockRoute: route }, "", path);
}

export function replaceMockRoute(route: MockRoute): void {
  const path = mockRouteToPath(route);
  window.history.replaceState({ mockRoute: route }, "", path);
}

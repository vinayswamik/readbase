import { useMemo } from "react";

import type { ConnectorSetupModalProps } from "./ConnectorSetupModalTypes";
import type { JiraProject } from "../../../types";

type ProjectRow = JiraProject & {
  sourceId?: string;
  connected: boolean;
};

export function JiraConnectorBody({
  jiraConnection,
  jiraWorkspaceSite,
  jiraSources,
  jiraProjects,
  jiraProjectQuery,
  jiraLoading,
  onJiraConnect,
  onConnectJiraSite,
  onRemoveJiraSite,
  onJiraProjectQueryChange,
  onJiraProjectSearch,
  onAddJiraProject,
  onRemoveJiraSource,
}: ConnectorSetupModalProps) {
  const workspaceSiteConnected = Boolean(jiraWorkspaceSite?.connected && jiraWorkspaceSite.site);
  const availableSites = jiraConnection?.sites || [];

  const projectRows = useMemo(() => {
    const connectedKeys = new Set(
      jiraSources.map((source) => `${source.cloud_id}:${source.project_id}`),
    );
    const rows: ProjectRow[] = jiraSources.map((source) => ({
      cloud_id: source.cloud_id,
      site_name: source.site_name,
      site_url: source.site_url,
      project_id: source.project_id,
      project_key: source.project_key,
      project_name: source.project_name,
      sourceId: source.source_id,
      connected: true,
    }));
    for (const project of jiraProjects) {
      const key = `${project.cloud_id}:${project.project_id}`;
      if (!connectedKeys.has(key)) {
        rows.push({ ...project, connected: false });
      }
    }
    return rows;
  }, [jiraProjects, jiraSources]);

  return (
    <div className="connector-modal-body">
      {!jiraConnection?.connected ? (
        <div className="connector-account-row">
          <div>
            <strong>Jira account</strong>
            <span>Connect your Atlassian account on the home page before linking a site.</span>
          </div>
          <button type="button" className="primary-button" disabled={jiraLoading} onClick={onJiraConnect}>
            Connect Jira
          </button>
        </div>
      ) : null}

      {jiraConnection?.connected && !workspaceSiteConnected ? (
        <section className="connector-access-list">
          <h3>Connect a site</h3>
          {!availableSites.length ? (
            <div className="status-text compact">No Jira sites available on your account.</div>
          ) : null}
          {availableSites.map((site) => (
            <div className="connector-access-row" key={site.cloud_id}>
              <span>{site.name}</span>
              <strong>{site.url.replace(/^https?:\/\//, "")}</strong>
              <button
                type="button"
                className="primary-button compact-button"
                disabled={jiraLoading}
                onClick={() => onConnectJiraSite(site)}
              >
                Connect site
              </button>
            </div>
          ))}
        </section>
      ) : null}

      {jiraConnection?.connected && workspaceSiteConnected && jiraWorkspaceSite?.site ? (
        <>
          <div className="connector-account-row">
            <div>
              <strong>{jiraWorkspaceSite.site.name}</strong>
              <span>{jiraWorkspaceSite.site.url.replace(/^https?:\/\//, "")}</span>
            </div>
            <button
              type="button"
              className="danger-button compact-button"
              disabled={jiraLoading}
              onClick={onRemoveJiraSite}
            >
              Remove site
            </button>
          </div>

          <div className="connector-search-row">
            <input
              value={jiraProjectQuery}
              placeholder="Search Jira projects"
              onChange={(event) => onJiraProjectQueryChange(event.target.value)}
            />
            <button type="button" className="secondary-action-button" disabled={jiraLoading} onClick={onJiraProjectSearch}>
              Search
            </button>
          </div>

          <section className="connector-access-list">
            <h3>Available projects</h3>
            {jiraLoading && !projectRows.length ? (
              <div className="status-text compact">Loading Jira projects...</div>
            ) : null}
            {!jiraLoading && !projectRows.length ? (
              <div className="status-text compact">No visible Jira projects found.</div>
            ) : null}
            {projectRows.length ? (
              <div className="jira-project-list-scroll">
                {projectRows.map((project) => (
                  <div className="connector-access-row" key={`${project.cloud_id}:${project.project_id}`}>
                    <span>{project.project_key} · {project.project_name}</span>
                    {project.connected && project.sourceId ? (
                      <button
                        type="button"
                        className="danger-button compact-button"
                        disabled={jiraLoading}
                        onClick={() => onRemoveJiraSource(project.sourceId!)}
                      >
                        Remove
                      </button>
                    ) : (
                      <button
                        type="button"
                        className="secondary-action-button compact-button"
                        disabled={jiraLoading}
                        onClick={() => onAddJiraProject(project)}
                      >
                        Add
                      </button>
                    )}
                  </div>
                ))}
              </div>
            ) : null}
          </section>
        </>
      ) : null}
    </div>
  );
}

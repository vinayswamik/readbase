import type { ConnectorSetupModalProps } from "./ConnectorSetupModalTypes";

export function JiraConnectorBody({
  jiraConnection,
  jiraSources,
  jiraProjects,
  jiraProjectQuery,
  jiraLoading,
  members,
  loadingMembers,
  canManageWorkspace,
  error,
  status,
  onJiraConnect,
  onJiraDisconnect,
  onJiraProjectQueryChange,
  onJiraProjectSearch,
  onAddJiraProject,
  onSyncJiraSource,
  onRemoveJiraSource,
  onConnectorManagerToggle,
  onClose,
}: ConnectorSetupModalProps) {
  return (<div className="connector-modal-body">
            <div className="connector-account-row">
              <div>
                <strong>{jiraConnection?.connected ? jiraConnection.account_name || "Jira connected" : "Jira account"}</strong>
                <span>
                  {jiraConnection?.connected
                    ? jiraConnection.account_email || `${jiraConnection.sites.length} site${jiraConnection.sites.length === 1 ? "" : "s"} connected`
                    : "Connect your Atlassian account before adding workspace projects."}
                </span>
              </div>
              {jiraConnection?.connected ? (
                <button type="button" className="secondary-action-button" disabled={jiraLoading} onClick={onJiraDisconnect}>
                  Disconnect
                </button>
              ) : (
                <button type="button" className="primary-button" disabled={jiraLoading} onClick={onJiraConnect}>
                  Connect Jira
                </button>
              )}
            </div>

            {jiraConnection?.connected ? (
              <>
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
                  {jiraLoading && !jiraProjects.length ? <div className="status-text compact">Loading Jira projects...</div> : null}
                  {!jiraLoading && !jiraProjects.length ? <div className="status-text compact">No visible Jira projects found.</div> : null}
                  {jiraProjects.slice(0, 8).map((project) => {
                    const alreadyAdded = jiraSources.some(
                      (source) => source.cloud_id === project.cloud_id && source.project_id === project.project_id,
                    );
                    return (
                      <div className="connector-access-row" key={`${project.cloud_id}:${project.project_id}`}>
                        <span>{project.project_key} · {project.project_name}</span>
                        <strong>{project.site_name}</strong>
                        <button
                          type="button"
                          className="secondary-action-button compact-button"
                          disabled={jiraLoading || alreadyAdded}
                          onClick={() => onAddJiraProject(project)}
                        >
                          {alreadyAdded ? "Added" : "Add"}
                        </button>
                      </div>
                    );
                  })}
                </section>

                <section className="connector-access-list">
                  <h3>Connector managers</h3>
                  {loadingMembers ? <div className="status-text compact">Loading workspace users...</div> : null}
                  {members.map((member) => (
                    <label className="connector-access-row" key={member.email}>
                      <input
                        type="checkbox"
                        checked={member.connector_manager}
                        disabled={!canManageWorkspace || member.is_owner}
                        onChange={() => onConnectorManagerToggle(member)}
                      />
                      <span>{member.email}</span>
                      <strong>{member.is_owner ? "Owner" : member.connector_manager ? "Manager" : "Member"}</strong>
                    </label>
                  ))}
                </section>

                <section className="connector-access-list">
                  <h3>Workspace Jira sources</h3>
                  {!jiraSources.length ? <div className="status-text compact">No Jira projects connected to this workspace.</div> : null}
                  {jiraSources.map((source) => (
                    <div className="connector-access-row" key={source.source_id}>
                      <span>{source.project_key} · {source.project_name}</span>
                      <strong>{source.sync_status}</strong>
                      <button
                        type="button"
                        className="secondary-action-button compact-button"
                        disabled={jiraLoading}
                        onClick={() => onSyncJiraSource(source.source_id)}
                      >
                        Sync
                      </button>
                      <button
                        type="button"
                        className="danger-button compact-button"
                        disabled={jiraLoading}
                        onClick={() => onRemoveJiraSource(source.source_id)}
                      >
                        Remove
                      </button>
                    </div>
                  ))}
                </section>
              </>
            ) : null}

            {error ? <div className="status-text error-text">{error}</div> : null}
            {status ? <div className="status-text">{status}</div> : null}
            <div className="connector-modal-actions">
              <button type="button" className="primary-button" onClick={onClose}>
                Done
              </button>
            </div>
          </div>
  );
}

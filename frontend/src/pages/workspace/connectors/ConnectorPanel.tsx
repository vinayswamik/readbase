import { useMemo, useState } from "react";

import { CONNECTOR_CATEGORY_ORDER, type ConnectorConfig, type ConnectorId, type ConnectorCategoryId } from "./connectors";
import { ConnectorLogo } from "./ConnectorLogo";

export function ConnectorPanel({
  connectors,
  onOpen,
}: {
  connectors: ConnectorConfig[];
  onOpen: (connectorId: ConnectorId) => void;
}) {
  const [open, setOpen] = useState(true);
  const groupedConnectors = useMemo(() => {
    const connectorsByCategory = new Map<ConnectorCategoryId, ConnectorConfig[]>();
    for (const connector of connectors) {
      const currentConnectors = connectorsByCategory.get(connector.category) || [];
      currentConnectors.push(connector);
      connectorsByCategory.set(connector.category, currentConnectors);
    }
    return CONNECTOR_CATEGORY_ORDER.map((category) => ({
      ...category,
      connectors: connectorsByCategory.get(category.id) || [],
    })).filter((category) => category.connectors.length);
  }, [connectors]);

  return (
    <section className="connector-panel" aria-labelledby="connectors-heading">
      <button
        type="button"
        className="connector-panel-trigger"
        aria-expanded={open}
        aria-controls="connector-list"
        onClick={() => setOpen((currentOpen) => !currentOpen)}
      >
        <span id="connectors-heading">Connectors</span>
        <span className="connector-chevron" aria-hidden="true">
          {open ? "⌃" : "⌄"}
        </span>
      </button>
      {open ? (
        <div className="connector-list" id="connector-list">
          {groupedConnectors.map((group) => (
            <div className="connector-category-group" key={group.id}>
              <div className="connector-category-heading">{group.label}</div>
              {group.connectors.map((connector) => (
                <button
                  type="button"
                  className="connector-row connector-open"
                  key={connector.id}
                  onClick={() => onOpen(connector.id)}
                >
                  <ConnectorLogo connectorId={connector.id} />
                  <span>{connector.name}</span>
                </button>
              ))}
            </div>
          ))}
        </div>
      ) : null}
    </section>
  );
}


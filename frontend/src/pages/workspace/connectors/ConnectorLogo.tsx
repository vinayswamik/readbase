import type { ConnectorId } from "./connectors";
import { CONNECTOR_LOGOS } from "./connectorLogos";

export function ConnectorLogo({ connectorId }: { connectorId: ConnectorId }) {
  const logoSrc = CONNECTOR_LOGOS[connectorId];

  return (
    <span className="connector-logo" aria-hidden="true">
      <img src={logoSrc} alt="" draggable={false} />
    </span>
  );
}

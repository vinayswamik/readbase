import type { ConnectorId } from "./connectors";

import bitbucketLogo from "../../../assets/connectors/bitbucket.svg";
import confluenceLogo from "../../../assets/connectors/confluence.svg";
import githubLogo from "../../../assets/connectors/github.svg";
import gitlabLogo from "../../../assets/connectors/gitlab.svg";
import jiraLogo from "../../../assets/connectors/jira.svg";
import linearLogo from "../../../assets/connectors/linear.svg";
import microsoftTeamsLogo from "../../../assets/connectors/microsoftteams.svg";
import notionLogo from "../../../assets/connectors/notion.svg";
import slackLogo from "../../../assets/connectors/slack.svg";

export const CONNECTOR_LOGOS: Record<ConnectorId, string> = {
  github: githubLogo,
  gitlab: gitlabLogo,
  bitbucket: bitbucketLogo,
  confluence: confluenceLogo,
  notion: notionLogo,
  jira: jiraLogo,
  linear: linearLogo,
  slack: slackLogo,
  teams: microsoftTeamsLogo,
};

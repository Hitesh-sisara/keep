import dataclasses
import pydantic
import requests

from keep.contextmanager.contextmanager import ContextManager
from keep.exceptions.provider_exception import ProviderException
from keep.providers.base.base_provider import BaseProvider
from keep.providers.models.provider_config import ProviderConfig


@pydantic.dataclasses.dataclass
class LinearProviderAuthConfig:
    """Linear authentication configuration."""

    api_token: str = dataclasses.field(
        metadata={
            "required": True,
            "description": "Linear API Token",
            "sensitive": True,
        }
    )
    team_id: str = dataclasses.field(
        metadata={
            "required": True,
            "description": "Linear Team ID",
        }
    )


class LinearProvider(BaseProvider):
    BASE_URL = "https://api.linear.app/graphql"

    def __init__(self, context_manager: ContextManager, provider_id: str, config: ProviderConfig):
        super().__init__(context_manager, provider_id, config)
        self.validate_config()

    def validate_config(self):
        self.authentication_config = LinearProviderAuthConfig(**self.config.authentication)

    def dispose(self):
        pass

    def _make_request(self, query: str, variables: dict = None):
        """Utility function to make GraphQL requests to Linear API."""
        headers = {
            "Authorization": f"Bearer {self.authentication_config.api_token}",
            "Content-Type": "application/json",
        }

        response = requests.post(self.BASE_URL, headers=headers, json={"query": query, "variables": variables})

        if not response.ok:
            raise ProviderException(
                f"{self.__class__.__name__} failed with response: {response.text}"
            )

        return response.json()

    def fetch_issues(self):
        query = """
        query Team {
          team(id: $teamId) {
            issues {
              nodes {
                id
                title
                description
              }
            }
          }
        }
        """
        variables = {"teamId": self.authentication_config.team_id}
        return self._make_request(query, variables)

    def create_issue(self, title: str, description: str):
        query = """
        mutation IssueCreate($input: IssueCreateInput!) {
          issueCreate(input: $input) {
            success
            issue {
              id
              title
            }
          }
        }
        """
        variables = {
            "input": {
                "title": title,
                "description": description,
                "teamId": self.authentication_config.team_id
            }
        }
        return self._make_request(query, variables)

    def edit_issue(self, issue_id: str, title: str = None, description: str = None):
        query = """
        mutation IssueUpdate($id: String!, $input: IssueUpdateInput!) {
          issueUpdate(id: $id, input: $input) {
            success
            issue {
              id
              title
              description
            }
          }
        }
        """
        input_data = {}
        if title:
            input_data["title"] = title
        if description:
            input_data["description"] = description

        variables = {"id": issue_id, "input": input_data}
        return self._make_request(query, variables)

    def delete_issue(self, issue_id: str):
        query = """
        mutation IssueDelete($id: String!) {
          issueDelete(id: $id) {
            success
          }
        }
        """
        variables = {"id": issue_id}
        return self._make_request(query, variables)


if __name__ == "__main__":
    import logging

    logging.basicConfig(level=logging.DEBUG, handlers=[logging.StreamHandler()])
    context_manager = ContextManager(
        tenant_id="singletenant",
        workflow_id="test",
    )

    import os

    linear_api_token = os.environ.get("LINEAR_API_TOKEN")
    linear_team_id = os.environ.get("LINEAR_TEAM_ID")

    config = ProviderConfig(
        description="Linear Input Provider",
        authentication={
            "api_token": linear_api_token,
            "team_id": linear_team_id,
        },
    )
    provider = LinearProvider(context_manager, provider_id="linear", config=config)
    provider.fetch_issues()

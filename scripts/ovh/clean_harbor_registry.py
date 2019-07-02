# Import python dependencies
import argparse
import json
import os
from datetime import datetime, timedelta
import pip
from pip._internal.utils.misc import get_installed_distributions

# Automatic install of non native python module for docker runtime
required_pkgs = ['requests']
installed_pkgs = [pkg.key for pkg in get_installed_distributions()]

for package in required_pkgs:
    if package not in installed_pkgs:
        pip._internal.main(['install', package])

# Import extern dependencies
import requests


# HARBOR CLIENT
class HarborClient:
    def __init__(self, url: str, project: str, headers: dict):
        self.page_size = 100
        self.url = url
        self.project = project
        self.headers = headers
        self.project_id = self.get_project_id()

        print(f'Founded ID for project {self.project} => {self.project_id}')

    def get_project_id(self) -> int:
        json_response = requests.get(f'{self.url}/api/projects', headers=self.headers).json()
        project_id = [x['project_id'] for x in json_response if x['name'] == self.project]
        return project_id[0]

    def get_all_repositories(self, max_datetime: datetime = None):
        all_repo = []
        current_page = 1
        stop = False
        while not stop:
            print(f'Asking for repository page number {current_page}')
            repo_on_page = self.get_repository_page(page=current_page, max_datetime=max_datetime)

            for x in repo_on_page:
                all_repo.append(x)

            if len(repo_on_page) < self.page_size:
                stop = True

            current_page = current_page + 1

        return all_repo

    def get_repository_page(self, page: int, max_datetime: datetime = None):
        url_params = {'page': page, 'page_size': self.page_size, 'project_id': self.project_id, 'sort': 'update_time'}
        json_response = requests.get(f'{self.url}/api/repositories', params=url_params, headers=self.headers).json()
        if max_datetime:
            return [x for x in json_response if datetime.strptime(x['update_time'], "%Y-%m-%dT%H:%M:%S.%fZ") < max_datetime]
        else:
            return json_response

    def delete_repository(self, name: str, dry_run: bool = False):
        if not dry_run:
            response = requests.delete(f'{self.url}/api/repositories/{name}', headers=self.headers)
            status_code = response.status_code
        else:
            status_code = 'Skipped (dry-run)'
        print(f'Status code = {status_code}')


def main(harbor_url: str, project: str, days_time_delta: int, dry_run: bool):
    print('Reading HOME from environment variables...')
    home = os.environ.get('HOME')
    docker_config_file = f'{home}/.docker/config.json'
    print(f'Reading docker config \'{docker_config_file}\'')
    with open(docker_config_file, 'r') as f:
        docker_config = json.load(f)

    headers = {}
    if docker_config:
        base64_user_password = docker_config['auths'][harbor_url]['auth']
        headers['Authorization'] = f'Basic {base64_user_password}'

    client = HarborClient(url=harbor_url, project=project, headers=headers)
    max_datetime = datetime.now() - timedelta(days=days_time_delta)
    print(f'Going to delete all images that were last updated before {str(max_datetime)}')
    results = client.get_all_repositories(max_datetime=max_datetime)

    for result in results:
        name = result['name']
        update_time_str = result['update_time']
        print(f'Last pulled {update_time_str} => Deleting {name}...')
        client.delete_repository(name, dry_run)

    print(f'Total deleted : {len(results)}')


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("harbor_url", help="URL of the harbor registry")
    parser.add_argument("harbor_project", help="Name of the harbor project to scan")
    parser.add_argument("keep_days", type=int, help="Number of days to keep from now (will delete all images before)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Number of days to keep from now (will delete all images before)")

    args = parser.parse_args()

    main(args.harbor_url, args.harbor_project, args.keep_days, args.dry_run)

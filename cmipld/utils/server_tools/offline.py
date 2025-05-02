import os
import shutil
import subprocess
import tempfile
from typing import List, Tuple
import tarfile
import datetime
# from .. import locations
from .server import LocalServer
# from ...locations import reverse_mapping
from ..git import io2repo
from ..logging.unique import UniqueLogger
log = UniqueLogger()

class LD_server:
    def __init__(self, repos=None, zipfile=None, copy=None, override=None):
        '''
        If None provided all the cmipld repositories will be generated. 

        repos: List of tuples where each tuple is (repo_url, target_name).
        zipfile: Path to the tar.gz file.

        '''
        self.temp_dir = None
        self.create_temp_dir()

        # ignore
        # if not repos and not zipfile:
        #     print('No repositories or zip file provided. Generating all repositories')
        #     repos = location.reverse_mapping()

        if zipfile:
            self.from_zip(zipfile, override=override)
        if repos:
            self.clone_repos(repos, override=override)
        if copy:
            self.copy_existing_repos(copy, override=override)

    def create_temp_dir(self):
        """Create a temporary directory to hold repositories."""
        if not self.temp_dir:
            self.temp_dir = tempfile.TemporaryDirectory(
                prefix='cmipld_local_', suffix=datetime.datetime.now().isoformat().split('.')[0])
        return self.temp_dir.name

    def delete_temp_dir(self):
        """Delete the temporary directory."""
        if self.temp_dir:
            self.temp_dir.cleanup()
            self.temp_dir = None

    def clone_repos(self, repos: List[Tuple[str, str]], branch="production", dir='src-data', override='n'):
        """
        Clone a list of git repositories into the temporary directory.
        Args:
            repos: List of tuples where each tuple is (repo_url, target_name).
            branch: Branch to clone (default: 'production').
        """
        for repo_url, target_name in repos:
            print(repo_url, target_name, self.temp_dir.name)
            repo_path = os.path.join(self.temp_dir.name, target_name)

            if '.io' in repo_url:
                repo_url = io2repo(repo_url)

            if os.path.exists(repo_path):
                if override != 'y':
                    override = input(
                        f"Repo '{target_name}' already exists. Delete and replace? (y/n): ").lower()

                if override == 'y':
                    shutil.rmtree(repo_path)
                else:
                    log.warn(f'Repo {target_name} not replaced')
                    continue

            clone = os.popen(' '.join(
                ["git", "clone", "--branch", branch, "--single-branch", repo_url, repo_path])).read()
            log.debug(clone)

            assert 'fatal' not in clone

            # move the relevant repo into place. This is because our production branch serves only the src-data directory
            log.debug(os.popen(f'mv {repo_path}/{dir}/* {repo_path}').read())

        log.info(f"Repositories cloned into {self.temp_dir}")

    def copy_existing_repos(self, repo_paths: List[str], override='n'):
        """
        Copy existing repositories into the temporary directory.
        Args:
            repo_paths: List of file paths to existing repositories.

        E.g. [[path1,name1],[path2,name2]]
        """
        for tocopy in repo_paths:
            if len(tocopy) == 2:
                repo_path, repo_name = tocopy
            else:
                repo_path = tocopy
                repo_name = tocopy

            log.debug(f'Copying the repo into LocalServer [#FF7900] {repo_path} --> {repo_name} [/]')
            
            # add to monkeypatch
            
            target_name = os.path.basename(repo_name)
            target_path = os.path.join(self.temp_dir.name, target_name)

            if os.path.exists(target_path):
                if override != 'y':
                    override = input(
                        f"Repo '{target_name}' already exists. Delete and replace? (y/n): ").lower()

                if override == 'y':
                    shutil.rmtree(target_path)
                else:
                    continue
            shutil.copytree(repo_path, target_path)

        log.debug(f"Repositories copied into [#FF7900] {self.temp_dir} [/]")

    def rollback_repo(self, repo_name: str, commit_hash: str):
        """
        Roll back a repository to a specific commit.
        Args:
            repo_name: Name of the repository to roll back.
            commit_hash: Commit hash to roll back to.
        """
        temp_dir = self.create_temp_dir()
        repo_path = os.path.join(temp_dir.name, repo_name)

        if not os.path.exists(repo_path):
            raise FileNotFoundError(
                f"Repository '{repo_name}' not found in {temp_dir}")

        subprocess.run(["git", "checkout", commit_hash],
                       cwd=repo_path, check=True)
        log.warn(f"Repository '{repo_name}' rolled back to commit {commit_hash}")

    def to_zip(self, output_file: str):
        """
        Create a gzipped tarball of the temporary directory.
        Args:
            output_file: Output tar.gz file path.
        """
        temp_dir = self.create_temp_dir()
        with tarfile.open(output_file, "w:gz") as tar:
            tar.add(temp_dir, arcname=os.path.basename(temp_dir.name))
        log.info(f"Repositories compressed into {output_file}")

    def from_zip(self, zip_path: str):
        """
        Extract repositories from a gzipped tarball.
        Args:
            zip_path: Path to the tar.gz file.
        """
        temp_dir = self.create_temp_dir()
        with tarfile.open(zip_path, "r:gz") as tar:
            tar.extractall(temp_dir.name)
        log.info(f"Repositories extracted into {temp_dir}")

    def start_server(self, port=8080):
        '''
        Serve the directory at the specified port.
        '''
        for _ in range(9):
            try:
                self.server = LocalServer(self.temp_dir.name, port)
                break
            except:
                port += 1
                log.debug('Port in use, trying:'+ port)

        self.url = self.server.start_server()
        # print('add the mappings here to the server')
        
        return self.url

    def stop_server(self):
        self.server.stop_server()
        self.server = None
        self.url = None
        log.info("Server stopped.")

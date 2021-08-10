import requests, json, git, sys
import errno, stat, os, shutil, argparse
from pathlib import Path


### For this script to work you will need the folowing ###
# 1. A Gitlab token with both api_read & read_repository access
# 2. Your group_id from your gitlab group
# 3. Pip modules: requests, gitpython, pathlib


parser = argparse.ArgumentParser(description="This script will clone projects from a group and its subgroups from Gitlab")
parser.add_argument('-t', '--token', type=str, help='Gitlab API token')
parser.add_argument('-g', '--group', type=int, help='Gitlab group ID')
parser.add_argument('-d', '--directory', type=str, help='Backup directory path for the gitlab group (OPTIONAL)')
args = parser.parse_args()

token = args.token
groupID = args.group

cloneBaseURL = f'https://oauth2:{token}@gitlab.com/'
apiBaseURL = f'http://gitlab.com/api/v4/groups/{groupID}/projects?private_token={token}&include_subgroups=true'

backupPath = f'gitlab_{groupID}_backups'
parentPath = (args.directory, Path.cwd())[args.directory is None]
directoryPath = os.path.join(parentPath, backupPath)

gitlabGroupProjectLink = []
gitlabGroupPathNamespace = []


def handleRemoveReadonly(func, path, exc):
  # Use the command below with this function if you want to remove the repo instead of pull --rebase
  # shutil.rmtree(filePath, ignore_errors=False, onerror=handleRemoveReadonly)
  excvalue = exc[1]
  if func in (os.rmdir, os.remove) and excvalue.errno == errno.EACCES:
      os.chmod(path, stat.S_IRWXU| stat.S_IRWXG| stat.S_IRWXO) # 0777
      func(path)
  else:
      raise


def makeDir(path_in):
    pathExists = os.path.exists(path_in)
    if not pathExists:
        os.makedirs(path_in)
        print(f"directory created: {path_in}")


def fetchGroupProjects():
    request = requests.get(apiBaseURL)
    data = json.loads(request.text)
    count = 0

    while count < len(data):
        gitlabGroupProjectLink.append(data[count]['http_url_to_repo'])
        gitlabGroupPathNamespace.append(data[count]['path_with_namespace'].split('/',1))
        count += 1
    

def cloneGroupProjects():
    count = 0

    for p in gitlabGroupProjectLink:
        repoName = gitlabGroupPathNamespace[count][1]
        filePath = os.path.join(directoryPath, repoName)
        pathExists = os.path.exists(os.path.abspath(filePath))

        # handles repository updating
        if pathExists:
            os.chdir(filePath)
            git.Git().remote('update')
            gitStatus = git.Git().status("-uno")

            if "up to date" not in gitStatus:
                git.Git().pull("-r", "--autostash")
                print(f"pulled repository changes: {repoName}")
                os.chdir(directoryPath)
            else:
                print(f"repository up to date: {repoName}")
                os.chdir(directoryPath)

        # handles repository cloning
        if not pathExists:
            os.chdir(directoryPath)
            git.Git().clone(cloneBaseURL + p.split("https://gitlab.com/")[1],
                            os.path.join(directoryPath,gitlabGroupPathNamespace[count][1]))
            print(f"cloned repository: {repoName}")

        count += 1


try:
    fetchGroupProjects()
    makeDir(directoryPath)
    cloneGroupProjects()
except:
    print(
        "ERROR: Ensure that you're running the script with the right arguments \n\n"
        "gitlab_group_cloner.py -t <API_TOKEN> -g <GROUP_ID> -d <DIRECTORY_PATH> (OPTIONAL) \n")
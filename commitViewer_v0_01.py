#repoURL = https://github.com/pvenancio/helloworld
#repoURL = "https://api.github.com/repos/pvenancio/helloworld/commits"
#repoURL = "https://github.com/tootsuite/mastodon"

# Não esquecer de fechar os open
# o que é preciso. instalar python3, git, requests
#-------------------------------------------------------------------------------
# Note: code written under PEP 8 layout guidelines (mostly)

# TODO:
#   - include flag to force download even file exist
#   - include flag to force download via API
#   - include flag to force download via CLI
#   - include flag to check commit lists in archive
#   - validate content of API response (if it still has expected keys)
#   - validate content of CLI response

import subprocess
from subprocess import Popen, PIPE
import sys
import json
import os
import shutil
import time
import threading
import requests

# Simple lambda functions for colouring
red = lambda text: '\033[0;31m' + text + '\033[0m'
green = lambda text: '\033[0;32m' + text + '\033[0m'
yellow = lambda text: '\033[0;33m' + text + '\033[0m'

# Setup variables
repoAuxName = "localRepo" # Auxiliar local folder to temporary clone repository
archiveName = "safebox" # Folder name for archiving downloaded commit lists
header = "\
  _____                          _ _    __      ___                        \n\
 / ____|                        (_) |   \ \    / (_)                       \n\
| |     ___  _ __ ___  _ __ ___  _| |_   \ \  / / _  _____      _____ _ __ \n\
| |    / _ \| '_ ` _ \| '_ ` _ \| | __|   \ \/ / | |/ _ \ \ /\ / / _ \ '__|\n\
| |___| (_) | | | | | | | | | | | | |_     \  /  | |  __/\ V  V /  __/ |   \n\
 \_____\___/|_| |_| |_|_| |_| |_|_|\__|     \/   |_|\___| \_/\_/ \___|_|   \n\
\n"
version = "v1.0 - Nov. 2019\n"
author = "Author: Pedro Venancio\n"
guide = "Guide: enter repository url for commit list, h for help, e for exit.\n"
help = "Nothing to see here, just paste a valid url for the commit list! :)\n"
bye = "Bye!\n"
errorURL = red("ERROR! ") + "URL not ok. Valid URL -> https://github.com/<user>/<repository>\n"
errorArchive = red("ERROR! ") + "Creation of " + archiveName + " directory failed. Please create directory manually. Exiting...\n"
errorPrinting = red("ERROR! ") + "Hash, author, date, or message of commit not found.\n"
errorSaving = red("ERROR! ") + "Unable to save list into file.\n"
errorUserPass = red("ERROR! ") + "Invalid user name and password.\n"
errorAuxFolder = red("ERROR! ") + "Unable to remove auxiliar cloning folder. Please delete it manually.\n"
errorGit = red("ERROR! ") + "Unable to get commit list via Git CLI. Please install Git.\n"
errorOverall = red("ERROR! ") + "Unable to get commit list from repository.\n"

# Clearing screen and print banner
subprocess.call('clear')
print(header + version + author + "\n" + guide)

def invalid_url():
    """ Info: Error function to display custom message when inserted url is not valid.
    """
    print(errorURL)

def check_for_archive():
    """ Info: Check if archive folder exists (to persist downloaded commit lists).
              If not, creates one. If unable to create, exits program since archive folder is mandatory.
    """
    if not os.path.exists(archiveName):
        try:
            os.mkdir(archiveName)
        except:
            print(errorArchive)
            sys.exit(0)

def print_commits(jsonData):
    """ Info: Prints commit list to terminal
        Args: jsonData (type list) - List containing commits
    """
    print("Commit list:")
    for i in range(len(jsonData)):
        try:
            print(green(jsonData[i]["hash"]) + " - " + jsonData[i]["author"] + \
                  " (" + yellow(jsonData[i]["date"]) + "): " + jsonData[i]["message"])
        except:
            print(errorPrinting)
    print("")

def check_for_file(user, repo):
    """ Info: Checks if requested commit list already exists in the archive
        Return: (boolean) - If file is found or not
    """
    check_for_archive() # Checking if archive folder exists
    if os.path.isfile(archiveName + "/" + user + "_" + repo + ".json"): # Checks if json file exists
        with open(archiveName + "/" + user + "_" + repo + ".json", "r") as jsonFile:
            try:
                 jsonData = json.load(jsonFile) # Loads json file
                 print_commits(jsonData) # Prints commit list stored in json file
                 return True
            except:
                return False
    else:
        return False

def persist_commit_list(commitList, user, repo):
    """ Info: Saves commit list into external json file (in archive folder)
        Args: commitList (type list) - List containing commits
              user (string) - Owner of repository to fetch commits
              repo (string) - Name of repository to fetch commits
    """
    check_for_archive() # Check for archive in case folder has been deleted during runtime
    with open(archiveName + "/" + user + "_" + repo + ".json", 'w') as outfile: # Json file to save commit list
        try:
            json.dump(commitList, outfile) # Writes list to file
        except:
            print(errorSaving)

def transform_api_response(response, commitList):
    """ Info: Transforms GitHub API response into a structured list
        Args: response (object) - GET response from API
              commitList (list) - List to write transformed data
        Return: commitList (list) - List with received commits
    """
    # Parsing API response into structure
    for i in range(len(response)): # Missing validation of keys (TODO for next version)
        commitHashAbr = response[i]["sha"][0:7]
        commitAuthor = response[i]["commit"]["author"]["name"]
        commitDate = response[i]["commit"]["author"]["date"].split("T")[0]
        commitMessage = response[i]["commit"]["message"].replace("\n", " ")
        commitList.append({"hash":commitHashAbr, "author":commitAuthor, "date":commitDate, "message":commitMessage})
    return commitList

def transform_cli_response(response, commitList):
    """ Info: Transforms GitHub CLI response into a structured list
        Args: response (object) - Response from CLI
              commitList (list) - List to write transformed data
        Return: commitList (list) - List with received commits
    """
    commits = response.split("\n")
    # Parsing CLI response into structure
    for eachCommit in commits: # Missing validation of CLI response (TODO for next version)
        commitHashAbr = eachCommit.split(";")[0][1:]
        commitAuthor = eachCommit.split(";")[1]
        commitDate = eachCommit.split(";")[2][0:10]
        commitMessage = eachCommit.split(";")[3][:-1]
        commitList.append({"hash":commitHashAbr, "author":commitAuthor, "date":commitDate, "message":commitMessage})
    return commitList

def get_commits_viaAPI(user, repo):
    """ Info: Gets commit list via GitHub API request
        Args: user (string) - Owner of repository to fetch commits
              repo (string) - Name of repository to fetch commits
        Return: (boolean) - If commit list could be received via API or not
    """
    repoURLAPI = "https://api.github.com/repos/" + user + "/" + repo + "/commits"
    try:
        r = requests.get(repoURLAPI, timeout = 5) # Request timeout of 5 seconds
    except:
        return False

    if r.headers["status"] == "200 OK":
        commitList = []
        pageCounter = 0 # Counter to limit API requests (to not surpass the 60 per hour available)
        commitList = transform_api_response(r.json(),commitList) # Transformation of API response data
        print_commits(commitList) # Printing commits to terminal
        persist_commit_list(commitList, user, repo) # Saving commits to file
        while "Link" in r.headers: # If more commit pages exist, fetch them
            try:
                r = requests.get(r.headers["link"].split(";")[0][1:-1])
            except:
                return False
            commitList = transform_api_response(r.json(),commitList)
            print_commits(commitList)
            persist_commit_list(commitList, user, repo)
            pageCounter+=1 # Incremental page counter. DELETE if unlimited API requests is permited
            if(pageCounter > 2): break # Break on page limit. DELETE if unlimited API requests is permited
        return True
    else:
        return False

def verify_local_aux_repo(repoAuxName):
    """ Info: Verifies if auxiliar folder for cloning exist. If so, removes it.
        Args: repoAuxName (string) - Auxiliar folder name
    """
    if os.path.exists(repoAuxName):
        try:
            shutil.rmtree(repoAuxName)
        except:
            print(errorAuxFolder)
            sys.exit(0)

def get_commits_viaCLI(user, repo, repoAuxName):
    """ Info: Gets commit list via GitHub CLI request
        Args: user (string) - Owner of repository to fetch commits
              repo (string) - Name of repository to fetch commits
              repoAuxName (string) - Folder name of local folder to clone repository
        Return: (boolean) - If commit list could be received via CLI or not
    """
    workingDir = os.getcwd() # Find current working directory
    verify_local_aux_repo(repoAuxName) # Verifies if auxiliar folder already exists
    repoURL = "https://github.com/" + user + "/" + repo
    FNULL = open(os.devnull, 'w')
    try:
        pOut = subprocess.Popen(["git", "clone", repoURL, repoAuxName], stdin = PIPE, stdout = PIPE, stderr = PIPE)
    except:
        print(errorGit)
        sys.exit(0)
    output = pOut.communicate()
    if not "Invalid username or password" in output[1].decode("utf-8"):
        processOutput = subprocess.getoutput("git -C " + workingDir + "/" + repoAuxName + " log --pretty=format:'%h;%an;%ci;%s'")
        commitList = []
        commitList = transform_cli_response(processOutput,commitList)
        print_commits(commitList)
        persist_commit_list(commitList, user, repo)
        return True
    else:
        print(errorUserPass)
        return False

# Main loop
while 1:
    repoURL = input("input: ")
    if repoURL == "e": # Command "e" (exit)
        print(bye)
        sys.exit(0)
    if repoURL == "h": # Command "h" (help)
        print(help)
    else:
        if repoURL[0:19] == "https://github.com/": # Validation of url
            if(len(repoURL.split("https://github.com/")[1]))>0:
                userAndRepo = repoURL.split("https://github.com/")[1]
                if(len(userAndRepo.split("/"))) == 2:
                    user = userAndRepo.split("/")[0]
                    repo = userAndRepo.split("/")[1]
                    if len(user) > 0 and len(repo) > 0: # Last validation of url
                        if not check_for_file(user, repo): # First check if repo commit list already exists in archive
                            if not get_commits_viaAPI(user, repo): # If not, fetches it via API
                                if not get_commits_viaCLI(user, repo, repoAuxName): # As last resort, fetches it via CLI
                                    print(errorOverall)
                    else:
                        invalid_url()
                else:
                    invalid_url()
            else:
                invalid_url()
        else:
            invalid_url()

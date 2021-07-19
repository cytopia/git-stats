#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# The MIT License (MIT)
#
# Copyright (c) 2019 cytopia <cytopia@everythingcli.org>
"""Get git statistics."""


# -------------------------------------------------------------------------------------------------
# IMPORTS
# -------------------------------------------------------------------------------------------------

# Default import
import os
import getopt
import tempfile
import re
import sys
from operator import itemgetter

# External dependencies
from git import Repo, GitError, Git
# External dependencies
import yaml


# -------------------------------------------------------------------------------------------------
# GLOBALS
# -------------------------------------------------------------------------------------------------

REPO_PATH = '/home/cytopia/repo/cytopia/git-stats/_build/'

CONFIG_PATH = os.sep.join((os.path.expanduser('~'), '.config/git-stats/conf.yml'))
TMPDIR_PATH = tempfile.gettempdir() if tempfile.gettempdir() is not None else '/tmp'

CONFIG_DEFS = {
    'tmpdir': TMPDIR_PATH,
    'wordlist': [],
    'repositories': []
}


# -------------------------------------------------------------------------------------------------
# HELPER FUNCTIONS
# -------------------------------------------------------------------------------------------------

def print_help():
    """Show git-stats help."""
    print('Help')


def print_version():
    """Show git-stats version."""
    print('Version')


# -------------------------------------------------------------------------------------------------
# GIT FUNCTIONS
# -------------------------------------------------------------------------------------------------
def validate_repos(repo_paths):
    """Ensure repositories already exist."""
    for repo_path in repo_paths:
        try:
            # pylint: disable=unused-variable
            Repo(repo_path)
        except GitError:
            print('[ERR] Repo does not yet exist: %s' % repo_path, file=sys.stderr)
            print('Run with --init first, see --help', file=sys.stderr)
            sys.exit(1)


def clone(git_url, tmp_dir, init):
    """Clone a git repository and return its path."""
    # Get repository name and path
    repo_name = re.search('^.+?/([-_a-zA-Z0-9\\.]+)(\\.git)$', git_url, re.IGNORECASE)
    repo_name = repo_name.group(1)
    repo_path = os.path.join(os.sep, tmp_dir, repo_name)

    if not init:
        return repo_path

    # If repo already exists fetch remote and checkout master
    try:
        repo = Repo(repo_path)
        print('Updating: ' + repo_path)
        repo.remotes.origin.fetch()
    # Otherwise clone repository
    except (GitError):
        print('Cloning : ' + repo_path)
        repo = Repo.clone_from(git_url, repo_path)

    return repo_path


def _get_git_log(git_path, start_date, end_date, *args):
    """Get commit logs and return empty in case of no branch."""
    try:
        git = Git(git_path)

        # Start and End time range
        if start_date and end_date:
            return git.log(
                '--after="'+start_date+'"',
                '--before="'+end_date+'"',
                args
            )
        # Only Start date
        if start_date:
            return git.log(
                '--after="'+start_date+'"',
                args
            )
        # Only End date
        if end_date:
            return git.log(
                '--before="'+end_date+'"',
                args
            )
        # No time range
        return git.log(
            args
        )
    except GitError:
        return ''


def _get_git_words(git_paths, email, wordlist, start_date=None, end_date=None):
    """Get count on words per commit message."""
    # initialize
    words = dict()
    for word in wordlist:
        words[word] = 0

    # For all Git repositories by specified user
    for path in git_paths:

        messages = _get_git_log(
            path,
            start_date,
            end_date,
            '--author='+email,
            '--oneline'
        ).splitlines()

        # For all words we are looking for
        for word in wordlist:
            # Loop over all commit messages
            for message in messages:
                # Apply forgiving regex
                match = re.match(r'.*\b('+word+')(\b|s|z|d|es|ed|er|rs|ers|or|ors|ing|in|-)?(\b|\\s|-|_|$).*', message, re.I)
                # Did the regex succeed?
                if match:
                    # Did it really find something?
                    if match.group(1) is not None:
                        words[word] += 1

    return words


def _get_git_files_adds_dels(git_paths, email, start_date=None, end_date=None):
    """Return count for changed diles, additions and delettion per email."""
    # Total across all commits
    files = 0
    adds = 0
    dels = 0
    # Max per commit
    max_files = 0
    max_adds = 0
    max_dels = 0

    for path in git_paths:

        lines = _get_git_log(
            path,
            start_date,
            end_date,
            '--author='+email,
            '--oneline',
            '--shortstat'
        ).splitlines()

        for line in lines:
            match_files = re.match(r'.*(\s+([0-9]+)\s+file)', line, re.I)
            match_adds = re.match(r'.*(\s+([0-9]+)\s+inser)', line, re.I)
            match_dels = re.match(r'.*(\s+([0-9]+)\s+delet)', line, re.I)

            if match_files:
                if match_files.group(2) is not None:
                    files += int(match_files.group(2))
                    if int(match_files.group(2)) > max_files:
                        max_files = int(match_files.group(2))
            if match_adds:
                if match_adds.group(2) is not None:
                    adds += int(match_adds.group(2))
                    if int(match_adds.group(2)) > max_adds:
                        max_adds = int(match_adds.group(2))
            if match_dels:
                if match_dels.group(2) is not None:
                    dels += int(match_dels.group(2))
                    if int(match_dels.group(2)) > max_dels:
                        max_dels = int(match_dels.group(2))

    return {
        'files': files,
        'adds': adds,
        'dels': dels,
        'max_files': max_files,
        'max_adds': max_adds,
        'max_dels': max_dels
    }


def _get_git_contributor_commit_count(git_paths, email, start_date=None, end_date=None):
    """Retrieve list of commit hashes across all repositories for one contributor email."""
    commits = list()

    for path in git_paths:

        hashes = _get_git_log(
            path,
            start_date,
            end_date,
            '--author='+email,
            '--format="%H"'
        ).splitlines()

        commits += hashes

    return len(commits)


def _get_git_contributor_emails(git_paths, start_date=None, end_date=None):
    """Retrieve all contributor emails on all repositories uniquely."""
    contributors = list()

    for path in git_paths:

        committers = _get_git_log(
            path,
            start_date,
            end_date,
            '--format=%cE'
        ).split()
        authors = _get_git_log(
            path,
            start_date,
            end_date,
            '--format=%aE'
        ).split()

        # Add to contributors
        contributors = list(set(authors + committers + contributors))

    return contributors


def get_statistics(git_paths, start_date, end_date, wordlist):
    """Get all unique contributor emails across all repositories."""
    stats = list()

    # Get contributors
    contributors = _get_git_contributor_emails(git_paths, start_date, end_date)

    for email in contributors:
        changes = _get_git_files_adds_dels(git_paths, email, start_date, end_date)
        commits = _get_git_contributor_commit_count(git_paths, email, start_date, end_date)
        # Search for words in commit messages
        words = _get_git_words(git_paths, email, wordlist, start_date, end_date)

        stats.append({
            'email': email,
            'commits': commits,
            'files': changes['files'],
            'adds': changes['adds'],
            'dels': changes['dels'],
            'max_files': changes['max_files'],
            'max_adds': changes['max_adds'],
            'max_dels': changes['max_dels'],
            'words': words
        })
    return stats


# -------------------------------------------------------------------------------------------------
# SYSTEM FUNCTIONS
# -------------------------------------------------------------------------------------------------


def read_config(path):
    """Read configuration from file."""
    data = dict()
    if os.path.isfile(path):
        with open(path, 'r') as stream:
            try:
                data = yaml.load(stream)
            except yaml.YAMLError as err:
                print('[ERR] Cannot read yaml file', file=sys.stderr)
                print(str(err), file=sys.stderr)

            if data is None:
                return CONFIG_DEFS

    # Normalize
    if 'tmpdir' not in data:
        data['tmpdir'] = TMPDIR_PATH
    if 'repositories' not in data:
        data['repositories'] = list()
    if 'wordlist' not in data:
        data['wordlist'] = list()

    return data


def parse_args(argv):
    """Parse command line arguments."""
    # Dictionary for cmd options
    options = dict()

    try:
        opts, argv = getopt.getopt(argv, 'c:t:hvi', [
            'config=',
            'tmpdir=',
            'init',
            'version',
            'help'
        ])
    except getopt.GetoptError as err:
        print(''.join(map(str, err)), file=sys.stderr)
        print('Type --help for help', file=sys.stderr)
        sys.exit(2)

    # Get command line options
    for opt, arg in opts:
        # Show help screen
        if opt in ('-h', '--help'):
            print_help()
            sys.exit()
        # Show version
        elif opt in ('-v', '--version'):
            print_version()
            sys.exit()
        # Do we initialize?
        elif opt in ('-i', '--init'):
            options['init'] = True
        # Get alternative configuration file
        elif opt in ('-c', '--config'):
            if not os.path.isfile(arg):
                print('[ERR] ' + opt + ' specified config does not exist: ' + arg, file=sys.stderr)
                sys.exit(2)
            options['config'] = arg
        # Get alternative configuration file
        elif opt in ('-t', '--tmpdir'):
            if not os.path.isdir(arg):
                print('[ERR] ' + opt + ' specified directory does not exist: ' + arg,
                      file=sys.stderr)
                sys.exit(2)
            options['tmpdir'] = arg

    return options


# -------------------------------------------------------------------------------------------------
# MAIN
# -------------------------------------------------------------------------------------------------

def main(argv):
    """Start of main entrypoint."""
    show_top = 10
    start_date = '2019-01-01'
    end_date = '2019-12-31'

    # Parse command line options and read config file
    options = parse_args(argv)
    settings = read_config(options.get('config', CONFIG_PATH))

    # Overwrite settings with command line options
    settings['tmpdir'] = options.get('tmpdir', settings['tmpdir'])

    # Get Git repositories
    repo_paths = list()
    for repo in settings['repositories']:
        repo_paths.append(clone(repo, settings['tmpdir'], options.get('init', False)))

    # Ensure repositories have been cloned already
    validate_repos(repo_paths)

    # Get Statistics
    statistics = get_statistics(repo_paths, start_date, end_date, settings['wordlist'])

    # Sort by git statistics
    by_comms = (sorted(statistics, key=lambda d: d['commits'], reverse=True))
    by_files = (sorted(statistics, key=lambda d: d['files'], reverse=True))
    by_adds = (sorted(statistics, key=lambda d: d['adds'], reverse=True))
    by_dels = (sorted(statistics, key=lambda d: d['dels'], reverse=True))
    by_mfiles = (sorted(statistics, key=lambda d: d['max_files'], reverse=True))
    by_madds = (sorted(statistics, key=lambda d: d['max_adds'], reverse=True))
    by_mdels = (sorted(statistics, key=lambda d: d['max_dels'], reverse=True))

    print()
    print('---------------------------------------------------------------------------------------')
    print(' NUMBER OF COMMITS')
    print('---------------------------------------------------------------------------------------')
    for cnt, item in enumerate(by_comms):
        if item['commits'] > 0 and cnt < show_top:
            print('{:9,d}   {}'.format(item['commits'], item['email']))

    print()
    print('---------------------------------------------------------------------------------------')
    print(' CHANGED FILES')
    print('---------------------------------------------------------------------------------------')
    for cnt, item in enumerate(by_files):
        if item['files'] > 0 and cnt < show_top:
            print('{:9,d}   {}'.format(item['files'], item['email']))

    print()
    print('---------------------------------------------------------------------------------------')
    print(' MAX CHANGED FILES PER COMMIT')
    print('---------------------------------------------------------------------------------------')
    for cnt, item in enumerate(by_mfiles):
        if item['max_files'] > 0 and cnt < show_top:
            print('{:9,d}   {}'.format(item['max_files'], item['email']))

    print()
    print('---------------------------------------------------------------------------------------')
    print(' LINES OF ADDITIONS')
    print('---------------------------------------------------------------------------------------')
    for cnt, item in enumerate(by_adds):
        if item['adds'] > 0 and cnt < show_top:
            print('{:9,d}   {}'.format(item['adds'], item['email']))

    print()
    print('---------------------------------------------------------------------------------------')
    print(' MAX LINES OF ADDITIONS PER COMMIT')
    print('---------------------------------------------------------------------------------------')
    for cnt, item in enumerate(by_madds):
        if item['max_adds'] > 0 and cnt < show_top:
            print('{:9,d}   {}'.format(item['max_adds'], item['email']))

    print()
    print('---------------------------------------------------------------------------------------')
    print(' LINES OF DELETIONS')
    print('---------------------------------------------------------------------------------------')
    for cnt, item in enumerate(by_dels):
        if item['dels'] > 0 and cnt < show_top:
            print('{:9,d}   {}'.format(item['dels'], item['email']))

    print()
    print('---------------------------------------------------------------------------------------')
    print(' MAX LINES OF DELETIONS PER COMMIT')
    print('---------------------------------------------------------------------------------------')
    for cnt, item in enumerate(by_mdels):
        if item['max_dels'] > 0 and cnt < show_top:
            print('{:9,d}   {}'.format(item['max_dels'], item['email']))

    for word in settings['wordlist']:
        print()
        print('---------------------------------------------------------------------------------------')
        print(' WORD: ' + word)
        print('---------------------------------------------------------------------------------------')
        by_word = sorted(statistics, key=lambda d: d['words'][word] if word in d['words'] else 0, reverse=True)
        for cnt, item in enumerate(by_word):
            if item['words'][word] > 0 and cnt < show_top:
                print('{:9,d}   {}'.format(item['words'][word], item['email']))


if __name__ == '__main__':
    main(sys.argv[1:])

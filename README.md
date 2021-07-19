# git-stats

## Usage

```bash
# Initialize or update repositories
./bin/git-stats -c etc/conf.yml -i

# Gather statistics
./bin/git-stats -c etc/conf.yml
```

```bash
# Search for a word in all commit messages
# Must have run `./bin/git-stats -c etc/conf.yml -i` first
./quickfind.sh <word>
```

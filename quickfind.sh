#!/bin/sh

if [ "${#}" -ne "1" ]; then
	echo "Usage: ./quickfind.sh <commit-message-word>"
	exit 1
fi

WORD="${1}"

find . \
	-type d \
	-name \.git \
	-print0 \
| xargs \
	-0 \
	-n1 \
	-P"$(nproc)" \
	sh -c "cd \$1; git log 2>/dev/null | grep -Ei '.*\b(${WORD})(\b|s|z|d|es|ed|er|rs|ers|or|ors|ing|in|-)?(\b|\s|-|_|$).*' && echo repository \$1" --


#	sh -c "cd \$1; git log --before='2019-01-01' --after='2017-12-31' 2>/dev/null | grep -Ei '.*\b(${WORD})(\b|s|z|d|es|ed|er|rs|ers|or|ors|ing|in|-)?(\b|\s|-|_|$).*' && echo repository \$1" --


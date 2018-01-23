#!/usr/bin/env bash
# coding: utf-8
#
#  F5 BigIP configuration reader (f5reader)
#
#  Copyright (C) 2018 Denis Pompilio (jawa) <dpompilio@vente-privee.com>
#
#  This file is part of f5reader
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the MIT License.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  MIT License for more details.
#
#  You should have received a copy of the MIT License along with this
#  program; if not, see <https://opensource.org/licenses/MIT>.

usage() {
    [ -z "$1" ] || echo "$1" >&2
    echo "Usage: $0 [-l <ssh_user>] -c <f5-address>" >&2; exit 1;
}

gather_f5_data() {
    ip="$1"
    shift
    ssh "$@" "$ip" '
        if [ -d /config/partitions ]; then
            echo "F5 is using partitions." >&2
            tmsh cd / \;\
            modify sys db bigpipe.displayservicenames value false \;\
            list recursive all-properties
        else
            echo "F5 has no partition." >&2
            tmsh modify sys db bigpipe.displayservicenames value false \;\
            list all-properties
        fi
    '
}


# --- Main ---
[ $# -eq 0 ] && usage
while getopts :c:l:h opt; do
    case "$opt" in
        h) usage ;;
        l) ssh_user=$OPTARG ;;
        c) f5_address=$OPTARG ;;
        \?) usage "Unknown option $OPTARG"; exit 2 ;;
        :) usage "Option -$OPTARG requires an argument."; exit 2 ;;
    esac
done

[ -z "$ssh_user" ] && ssh_user=$(whoami)

data_file="${f5_address}-data.txt"
echo "extracting data to $data_file"

gather_f5_data "$f5_address" -l "$ssh_user" > "$data_file" &&
echo "extraction done" ||
echo "extraction failed"
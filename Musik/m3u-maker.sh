#!/bin/bash
dir="$1"
#echo "Create playlist for $1 ..."
if [[ $2 ]]; then list="$2"; else list="$1"; fi
 
#pushd "$dir" 2>&1 >/dev/null
find "$1" -type f -not -name "*.m3u" > "$list.m3u" -exec ls -1rt "{}" +;
wc -l "$list.m3u"
#sed -i 's/ /%20/g' "$list.m3u"
#popd 2>&1 >/dev/null


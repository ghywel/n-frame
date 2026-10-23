#!/bin/bash
D=~/np-scratch-int/defects-20261023; P=~/np-scratch-int/prospect-20261023; FF=~/np-build/ffmpeg/ffmpeg; PY=~/np-build/venv/bin/python3
while read name dir W H full half; do
  mkdir -p $D/$name-fade
  $FF -v error -y -i $P/$dir/ref.mkv -vf "select='eq(n\,39)'" -frames:v 1 -c:v ffv1 $D/$name-still.mkv
  $PY $D/fade.py $D/$name-still.mkv $D/$name-fade/raw $W $H 1.06 12 $full
  $FF -v error -y -f rawvideo -pix_fmt rgb48le -video_size ${W}x$H -framerate $full -i $D/$name-fade/raw-full.rgb48 -c:v ffv1 -pix_fmt yuv420p10le $D/$name-fade/ref.mkv
  $FF -v error -y -f rawvideo -pix_fmt rgb48le -video_size ${W}x$H -framerate $half -i $D/$name-fade/raw-half.rgb48 -c:v ffv1 -pix_fmt yuv420p10le $D/$name-fade/half.mkv
  echo "$name: $(ls $D/$name-fade | tr '\n' ' ')"
done <<LIST
tv tv/native-73 1440 1080 25 25/2
cartoon cartoon/native-6525 1280 720 24000/1001 12000/1001
LIST

# Need something to drive the placement of files in a realtime directory

import mx.DateTime
import glob, os, time

ABASE_TS = mx.DateTime.DateTime(2012,2,29,0,30)
# 6 hours of data in 3 hours of time
RT_START = mx.DateTime.DateTime(2012,12,15,18,10) # GMT!
speedup = 2.0

def doit( fp, ts ):
  cmd = "../l2munger KDMX %s %s" % (ts.strftime("%Y/%m/%d %H:%M:%S"), fp)
  os.system(cmd)
  fp = "KDMX%s" % (ts.strftime("%Y%m%d_%H%M%S"),)
  os.system("compress %s" % (fp,))
  os.rename("%s.Z" % (fp,), "../../htdocs/l2data/KDMX/%s.Z" % (fp,)) 
  os.chdir("../../htdocs/l2data/KDMX/")
  os.system("ls -l KDMX* | awk '{print $5 \" \" $9}' > dir.list")
  os.chdir("../../../scripts/l2data")

# Load Filenames, figure if they should be immediately moved
os.chdir("l2data")
files = glob.glob("*")
files.sort()
delayed = []
left = len(files)
for file in files:
  # KTLX20090210_180130_V03
  ts = mx.DateTime.strptime(file[4:19], '%Y%m%d_%H%M%S')
  offset = (ts - ABASE_TS).minutes / speedup
  fakets = RT_START + mx.DateTime.RelativeDateTime(minutes=offset)
  print "Process: %s TS: %s Left: %s" % (file, 
     fakets.strftime("%Y-%m-%d %H:%M"), left )
  if fakets > mx.DateTime.gmt():
    time.sleep( int((fakets - mx.DateTime.gmt()).seconds) )
  left -= 1
  doit( file, fakets )

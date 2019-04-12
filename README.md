MT417 Timing
------------

| Workshop UTC | Event UTC |
| ----- | ---- |
|  11 Apr 2019 1930 | 24 May 2011 2000 |
|  11 Apr 2019 2100 | 24 May 2011 2300 |


National Guard Workshop
-----------------------

We'd like to have the severe wind event (Derecho of June 29, 1998) hit Sioux
City, IA at 0815, and progress across Iowa to the Des Moines area by 1030,
then slow the progress in crossing the eastern half of Iowa so that it takes
about 4 hours to reach the Mississippi River.  This slow-down will allow us
to develop some flood concerns in the Iowa and Cedar River valleys which
will trigger additional Guard response. 

| Workshop UTC | Event UTC |
| --- | --- |
| 23 Apr 2018 1300 | 29 Jun 1998 1600 |
| 23 Apr 2018 2100 | 29 Jun 1998 2030 |

nwa
===

This repository contains code used to drive the annual Central Iowa NWA
RADAR workshop.  Here are some notes on the setup and usage of this
exercise.

A local area network (LAN) is established so to provide a reliable and
fast network for a room of laptops to use.  Using the hotel's wireless
is unreliable and has issues with having local data servers in the same
room.  (This is often firewalled.) Two laptops (servers) are connected to a wired LAN along with the
wireless controllers.  A local and open WiFi is established called
'RADAR Workshop' for the local users to connect to.

One of the servers runs an Apache web server, which contains some custom
PHP code and a directory to serve out Archive Level II RADAR data.  A
script runs on this computer to 'replay' an archive of NEXRAD data as if
it were in realtime.  This is necessary to 'trick' Gibson Ridge software
into polling this server and requesting data thinking it is in realtime.
The script keeps track of the wall clock time and replays the archive
of data to match a predefined mesh period.

This NEXRAD displaced place and time script modifies the header in the Archive
Level II format to effectively move the file in space in time.  One tricky
aspect of this moving is that the cases are often speed up, so for example,
6 hours of wall clock time are replayed in 3 hours of workshop time.  This 
creates one issue of storm motion within Gibson Ridge as with a 2x time speed
increase implies a 2x ground speed increase with storm motion.

*Note* One issue with Gibson Ridge is that it downloads a RUC environmental
sounding from the Internet and thus getting a cold season sounding with a
spring/summer case when mess with the hail algorithms.  We have not attempted
to address this by providing faked environmental data.  Our cases typically
focus on the tornadoes anyway.

The workshop participants run a custom written software called "WarnGen" by
Dr Chris Karstens, which interacts with Gibson Ridge to allow users to draw
fake warning polygons and issue those warnings to the local warning server.  The
local warning server ingests these warnings into a local database and then
generates scoring based on actual Local Storm Reports for the displaced case.

The displaced Local Storm Reports are hand quality controlled by the workshop
leaders to modify the event comments to match the displaced location reality
and to remove any hints of rememberable remarks.  These remarks may tip some
users off to which case it was.

How are Local Storm Reports (LSR)s displaced?
---------------------------------------------

The `scripts/shirt_lsrs.py` script queries the IEM's archive for NWS issued
Local Storm Reports nearby in space and time to the transposed event.  The
script computes the spatial offset from the transposed RADAR that the report
occurred and then applies that same offset to the target RADAR location. That
offset is them used to find the nearest city location so to compute the
traditional NWS location and offset to its LSR reports (i.e. 10 N Ames). The
location is also used to compute the new WFO associated with the report.  The
free-form remark text in the LSR is then hand edited by the organizers within
a Google Spreadsheet.  This Google Spreadsheet information is then synced to
the local database by the `scripts/sync_google.py` script.

Some things we have learned doing this
--------------------------------------

1. Invariably, some weather nerd in the room is able to guess which event this
was based on the SPC outlook shown during the case warm up.  This hasn't ruined
the experience though as typically the events are looking at some tricky events
and not EF-5 monster supercells.
2. Students will issue smaller warnings than what was actually issued by the
NWS for the events.  There are a few likely reasons for this, but the main one
being students are not easily able to draw warnings to local county borders and
they are likely not attempting to cover Hail, Wind threats with their tornado
warnings.
3. The local Wifi and local server have no issues servicing ~30 users in the room.
The bandwidth utilized by the local laptop server is trivial for a Gigabit LAN
connection and modern wifi.
4. Some years, a second laptop was setup to be a NAT gateway so that local LAN
computers can still reach the Internet.  This is useful for the local computers
not to complain about loosing DNS or web access, but it also allows students to
check Facebook, etc during the event.  This gateway laptop though often gets
blocked by the hotel's network for excessive bandwidth / suspicious activity.
For recent years, this functionality was dropped.

